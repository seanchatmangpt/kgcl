"""Integration tests for Multiple Instance Join Patterns (WCP-34 to WCP-36).

Tests workflow patterns with partial joins, cancelling joins, and dynamic
thresholds using PostgreSQL for aggregation and Redis for state tracking.

Real-world scenarios:
- WCP-34 Static Partial Join: Quorum-based approval (7 of 10)
- WCP-35 Cancelling Partial Join: First N responses, cancel rest
- WCP-36 Dynamic Partial Join: Runtime-determined threshold
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from tests.containers.rdf_stores import OxigraphContainer


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
@pytest.mark.wcp(34)
class TestWCP34StaticPartialJoin:
    """WCP-34: Static Partial Join (N of M at design time).

    Scenario: Quorum-Based Approval
    - 10 board members vote
    - Need 7 approvals to proceed (quorum)
    - Continue once threshold reached
    """

    def test_quorum_based_approval(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test static partial join with fixed quorum threshold.

        Arrange:
        - Create 10 voting instances
        - Set threshold to 7

        Act:
        - Collect votes until threshold reached

        Assert:
        - Join fires at exactly 7 approvals
        - Remaining votes not required
        """
        # Arrange
        workflow_id = "WF-QUORUM-001"
        cursor = postgres_connection.cursor()

        total_members = 10
        threshold = 7

        # Initialize vote counter in Redis
        vote_key = f"votes:{workflow_id}"
        redis_connection.set(vote_key, 0)

        # Log join setup
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                34,
                "partial_join_setup",
                "quorum_join",
                json.dumps({
                    "total_instances": total_members,
                    "threshold": threshold,
                    "join_type": "static_partial",
                }),
            ),
        )
        postgres_connection.commit()

        # Act: Simulate voting (some approve, some reject)
        # Vote pattern: 8 approve, 2 reject
        votes = ["approve"] * 8 + ["reject"] * 2
        approvals_received = 0
        join_fired = False
        join_fired_at_vote = None

        for i, vote in enumerate(votes):
            member_id = f"member_{i + 1}"

            # Record vote
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    34,
                    "vote_received",
                    f"vote_{member_id}",
                    json.dumps({"member": member_id, "vote": vote, "vote_number": i + 1}),
                ),
            )

            if vote == "approve":
                approvals_received = redis_connection.incr(vote_key)

                # Check if threshold reached
                if approvals_received >= threshold and not join_fired:
                    join_fired = True
                    join_fired_at_vote = i + 1

                    cursor.execute(
                        """
                        INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            workflow_id,
                            34,
                            "partial_join_fired",
                            "proceed_with_decision",
                            json.dumps({
                                "threshold_met": threshold,
                                "total_approvals": approvals_received,
                                "votes_processed": i + 1,
                                "votes_remaining": total_members - (i + 1),
                            }),
                        ),
                    )

        postgres_connection.commit()

        # Assert
        assert join_fired, "Join should fire when threshold reached"
        assert join_fired_at_vote == 7, "Join should fire at vote 7 (first to reach threshold)"

        final_approvals = int(redis_connection.get(vote_key) or 0)
        assert final_approvals == 8, "Total approvals should be 8"

        # Verify audit trail
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'vote_received'
            """,
            (workflow_id,),
        )
        vote_count = cursor.fetchone()[0]
        assert vote_count == total_members, "All votes should be recorded"


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
@pytest.mark.wcp(35)
class TestWCP35CancellingPartialJoin:
    """WCP-35: Cancelling Partial Join (N of M, cancel rest).

    Scenario: First N Shipping Quotes
    - Request quotes from 5 carriers
    - Accept first 3 quotes received
    - Cancel remaining quote requests
    """

    def test_first_n_quotes_cancel_rest(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test cancelling partial join that cancels remaining after threshold.

        Arrange:
        - Request quotes from 5 carriers
        - Set threshold to 3

        Act:
        - Receive quotes with varying delays
        - Cancel remaining after 3 received

        Assert:
        - Exactly 3 quotes accepted
        - Remaining 2 cancelled
        """
        # Arrange
        workflow_id = "WF-QUOTES-001"
        cursor = postgres_connection.cursor()

        carriers = [
            {"id": "UPS", "delay_ms": 10, "price": 25.00},
            {"id": "FedEx", "delay_ms": 20, "price": 28.00},
            {"id": "USPS", "delay_ms": 30, "price": 22.00},
            {"id": "DHL", "delay_ms": 50, "price": 35.00},
            {"id": "OnTrac", "delay_ms": 60, "price": 20.00},
        ]
        threshold = 3

        # State tracking
        quotes_key = f"quotes:{workflow_id}"
        cancelled_key = f"cancelled:{workflow_id}"
        redis_connection.delete(quotes_key, cancelled_key)

        received_quotes: list[dict[str, Any]] = []
        cancelled_carriers: list[str] = []
        join_fired = False
        lock = threading.Lock()

        def request_quote(carrier: dict[str, Any]) -> dict[str, Any]:
            """Request quote from carrier."""
            nonlocal join_fired

            # Simulate network delay
            time.sleep(carrier["delay_ms"] / 1000)

            with lock:
                # Check if already cancelled
                if redis_connection.sismember(cancelled_key, carrier["id"]):
                    return {"carrier": carrier["id"], "status": "cancelled_before_response"}

                # Check if join already fired
                current_count = redis_connection.scard(quotes_key)
                if current_count >= threshold:
                    # This quote came too late - cancel it
                    redis_connection.sadd(cancelled_key, carrier["id"])
                    cancelled_carriers.append(carrier["id"])

                    cursor.execute(
                        """
                        INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            workflow_id,
                            35,
                            "quote_cancelled",
                            f"cancel_{carrier['id']}",
                            json.dumps({"carrier": carrier["id"], "reason": "threshold_reached"}),
                        ),
                    )

                    return {"carrier": carrier["id"], "status": "cancelled"}

                # Accept quote
                quote_result = {
                    "carrier": carrier["id"],
                    "price": carrier["price"],
                    "status": "accepted",
                }
                received_quotes.append(quote_result)
                redis_connection.sadd(quotes_key, carrier["id"])

                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        workflow_id,
                        35,
                        "quote_received",
                        f"quote_{carrier['id']}",
                        json.dumps(quote_result),
                    ),
                )

                # Check if threshold reached
                if len(received_quotes) == threshold and not join_fired:
                    join_fired = True

                    # Cancel remaining
                    for c in carriers:
                        if c["id"] not in [q["carrier"] for q in received_quotes]:
                            redis_connection.sadd(cancelled_key, c["id"])
                            cancelled_carriers.append(c["id"])

                    cursor.execute(
                        """
                        INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            workflow_id,
                            35,
                            "cancelling_partial_join_fired",
                            "select_shipping",
                            json.dumps({
                                "quotes_received": len(received_quotes),
                                "cancelled_carriers": cancelled_carriers,
                            }),
                        ),
                    )

                return quote_result

        # Act: Request quotes in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(request_quote, carrier) for carrier in carriers]
            results = [f.result() for f in futures]

        postgres_connection.commit()

        # Assert
        assert len(received_quotes) == threshold, f"Should have exactly {threshold} quotes"
        assert join_fired, "Join should have fired"

        # Verify cancelled carriers
        accepted_carriers = {q["carrier"] for q in received_quotes}
        expected_cancelled = {c["id"] for c in carriers} - accepted_carriers
        assert len(expected_cancelled) == 2, "Should have 2 cancelled carriers"

        # Verify audit trail
        cursor.execute(
            """
            SELECT event_type, COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s
            GROUP BY event_type
            """,
            (workflow_id,),
        )
        event_counts = dict(cursor.fetchall())
        assert event_counts.get("quote_received", 0) == 3


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
@pytest.mark.wcp(36)
class TestWCP36DynamicPartialJoin:
    """WCP-36: Dynamic Partial Join (threshold at runtime).

    Scenario: Dynamic Approval Threshold
    - Approval threshold based on purchase amount
    - Small orders: 1 approver
    - Medium orders: 2 approvers
    - Large orders: 3 approvers
    """

    def test_dynamic_threshold_approval(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test dynamic partial join with runtime threshold.

        Arrange:
        - Create order with amount-based threshold
        - Determine threshold at runtime

        Act:
        - Collect approvals until dynamic threshold met

        Assert:
        - Join fires at correct dynamic threshold
        """
        # Arrange
        workflow_id = "WF-DYNAMIC-001"
        cursor = postgres_connection.cursor()

        # Runtime data determines threshold
        order = {
            "order_id": "PO-2024-001",
            "amount": 75000.00,  # Large order -> 3 approvers
            "department": "Engineering",
        }

        # Determine threshold at runtime
        def calculate_threshold(amount: float) -> int:
            if amount < 10000:
                return 1  # Small order
            elif amount < 50000:
                return 2  # Medium order
            else:
                return 3  # Large order

        threshold = calculate_threshold(order["amount"])
        total_approvers = 4

        # Log dynamic threshold determination
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                36,
                "dynamic_threshold_set",
                "calculate_threshold",
                json.dumps({
                    "order_amount": order["amount"],
                    "calculated_threshold": threshold,
                    "rule": "amount >= 50000 -> 3 approvers",
                }),
            ),
        )
        postgres_connection.commit()

        # Initialize approval counter
        approval_key = f"approvals:{workflow_id}"
        redis_connection.set(approval_key, 0)

        # Act: Collect approvals
        approvers = [
            {"name": "team_lead", "decision": "approve"},
            {"name": "manager", "decision": "approve"},
            {"name": "director", "decision": "approve"},
            {"name": "vp", "decision": "approve"},
        ]

        approvals_received = 0
        join_fired = False
        join_fired_at_approval = None

        for i, approver in enumerate(approvers):
            if join_fired:
                # Join already fired, remaining approvals not needed
                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        workflow_id,
                        36,
                        "approval_skipped",
                        f"skip_{approver['name']}",
                        json.dumps({"approver": approver["name"], "reason": "threshold_already_met"}),
                    ),
                )
                continue

            # Record approval
            if approver["decision"] == "approve":
                approvals_received = redis_connection.incr(approval_key)

            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    36,
                    "approval_received",
                    f"approve_{approver['name']}",
                    json.dumps({
                        "approver": approver["name"],
                        "decision": approver["decision"],
                        "approval_count": approvals_received,
                        "threshold": threshold,
                    }),
                ),
            )

            # Check dynamic threshold
            if approvals_received >= threshold:
                join_fired = True
                join_fired_at_approval = i + 1

                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        workflow_id,
                        36,
                        "dynamic_partial_join_fired",
                        "proceed_with_order",
                        json.dumps({
                            "dynamic_threshold": threshold,
                            "approvals_received": approvals_received,
                            "order_amount": order["amount"],
                        }),
                    ),
                )

        postgres_connection.commit()

        # Assert
        assert join_fired, "Join should fire when dynamic threshold reached"
        assert join_fired_at_approval == threshold, f"Join should fire at approval {threshold}"
        assert threshold == 3, "Large order should require 3 approvals"

        # Verify audit trail shows dynamic threshold
        cursor.execute(
            """
            SELECT token_state FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'dynamic_threshold_set'
            """,
            (workflow_id,),
        )
        threshold_state = json.loads(cursor.fetchone()[0])
        assert threshold_state["calculated_threshold"] == 3


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
class TestMIJoinWithAggregation:
    """Test MI join patterns with result aggregation.

    Demonstrates collecting and aggregating results from
    multiple instances before join fires.
    """

    def test_aggregate_results_at_join(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test aggregating MI results when partial join fires.

        Arrange:
        - Create MI task with 5 instances
        - Each produces numeric result

        Act:
        - Collect results with partial join (3 of 5)
        - Aggregate at join

        Assert:
        - Aggregation includes only completed instances
        """
        # Arrange
        workflow_id = "WF-AGGREGATE-001"
        cursor = postgres_connection.cursor()

        threshold = 3
        results_key = f"results:{workflow_id}"
        redis_connection.delete(results_key)

        # Simulate MI instances with results
        instances = [
            {"instance_id": 0, "result": 100, "delay_ms": 10},
            {"instance_id": 1, "result": 150, "delay_ms": 20},
            {"instance_id": 2, "result": 200, "delay_ms": 15},
            {"instance_id": 3, "result": 175, "delay_ms": 50},
            {"instance_id": 4, "result": 225, "delay_ms": 60},
        ]

        completed_results: list[int] = []
        join_fired = False
        aggregation: dict[str, Any] = {}
        lock = threading.Lock()

        def process_instance(instance: dict[str, Any]) -> dict[str, Any]:
            nonlocal join_fired, aggregation

            time.sleep(instance["delay_ms"] / 1000)

            with lock:
                if join_fired:
                    return {"instance_id": instance["instance_id"], "status": "skipped"}

                # Store result
                redis_connection.rpush(results_key, instance["result"])
                completed_results.append(instance["result"])

                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        workflow_id,
                        34,
                        "instance_completed",
                        f"instance_{instance['instance_id']}",
                        json.dumps({"result": instance["result"]}),
                    ),
                )

                # Check threshold
                if len(completed_results) >= threshold and not join_fired:
                    join_fired = True

                    # Aggregate results
                    aggregation = {
                        "count": len(completed_results),
                        "sum": sum(completed_results),
                        "average": sum(completed_results) / len(completed_results),
                        "min": min(completed_results),
                        "max": max(completed_results),
                    }

                    cursor.execute(
                        """
                        INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            workflow_id,
                            34,
                            "aggregation_complete",
                            "join_aggregation",
                            json.dumps(aggregation),
                        ),
                    )

                return {"instance_id": instance["instance_id"], "status": "completed"}

        # Act: Process instances in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_instance, inst) for inst in instances]
            for f in futures:
                f.result()

        postgres_connection.commit()

        # Assert
        assert join_fired, "Join should fire"
        assert len(completed_results) >= threshold, f"Should have at least {threshold} results"
        assert aggregation["count"] == threshold, "Aggregation should include threshold results"

        # Verify aggregation math
        expected_sum = sum(completed_results[:threshold])
        assert aggregation["sum"] == expected_sum


@pytest.mark.container
@pytest.mark.oxigraph_server
@pytest.mark.postgres
@pytest.mark.redis
class TestMIJoinWithRDFState:
    """Test MI join patterns with RDF state tracking.

    Uses Oxigraph for workflow topology and instance state,
    Redis for counters, PostgreSQL for audit.
    """

    def test_mi_join_with_rdf_instances(
        self,
        oxigraph_container: OxigraphContainer,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test MI partial join with RDF instance tracking.

        Arrange:
        - Load MI workflow to Oxigraph
        - Create instances in RDF

        Act:
        - Complete instances until threshold
        - Update RDF state

        Assert:
        - RDF reflects completed instances
        - Join fires correctly
        """
        from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

        # Arrange
        workflow_id = "WF-RDF-JOIN-001"
        threshold = 3
        total_instances = 5

        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container.get_sparql_endpoint(),
            update_endpoint=oxigraph_container.get_update_endpoint(),
        )

        # Load MI workflow topology
        workflow_turtle = f"""
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
            @prefix kgc: <http://kgcl.io/ontology/kgc#> .
            @prefix wf: <http://example.org/workflow/> .

            wf:mi_task a yawl:AtomicTask ;
                yawl:multipleInstance true ;
                yawl:instances {total_instances} ;
                yawl:threshold {threshold} .
        """
        adapter.load_turtle(workflow_turtle)

        counter_key = f"mi_counter:{workflow_id}"
        redis_connection.set(counter_key, 0)

        cursor = postgres_connection.cursor()

        # Act: Create and complete instances
        for i in range(total_instances):
            # Create instance in RDF
            adapter.update(f"""
                PREFIX kgc: <http://kgcl.io/ontology/kgc#>
                PREFIX wf: <http://example.org/workflow/>
                INSERT DATA {{
                    wf:instance_{i} a kgc:TaskInstance ;
                        kgc:instanceOf wf:mi_task ;
                        kgc:instanceNumber {i} ;
                        kgc:status "pending" .
                }}
            """)

            # Complete instance (first 3 only to test partial)
            if i < threshold:
                adapter.update(f"""
                    PREFIX kgc: <http://kgcl.io/ontology/kgc#>
                    PREFIX wf: <http://example.org/workflow/>
                    DELETE {{ wf:instance_{i} kgc:status "pending" }}
                    INSERT {{ wf:instance_{i} kgc:status "completed" }}
                    WHERE {{ wf:instance_{i} kgc:status "pending" }}
                """)

                completed_count = redis_connection.incr(counter_key)

                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        workflow_id,
                        34,
                        "rdf_instance_completed",
                        f"instance_{i}",
                        json.dumps({"instance": i, "completed_count": completed_count}),
                    ),
                )

        postgres_connection.commit()

        # Assert: Query RDF for completed instances
        results = adapter.query("""
            PREFIX kgc: <http://kgcl.io/ontology/kgc#>
            SELECT (COUNT(?inst) AS ?completed) WHERE {
                ?inst a kgc:TaskInstance ;
                      kgc:status "completed" .
            }
        """)
        completed_in_rdf = results[0]["completed"] if results else 0
        assert completed_in_rdf == threshold, f"RDF should show {threshold} completed instances"

        # Verify Redis counter
        final_count = int(redis_connection.get(counter_key) or 0)
        assert final_count == threshold

        # Cleanup
        adapter.clear()
