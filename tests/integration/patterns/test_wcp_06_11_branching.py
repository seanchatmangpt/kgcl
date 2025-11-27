"""Integration tests for Advanced Branching and Synchronization Patterns (WCP-6 to WCP-11).

Tests workflow patterns with RabbitMQ routing for message-based coordination
and PostgreSQL for audit persistence.

Real-world scenarios:
- WCP-6 Multi-Choice: Risk assessment routing (multiple departments)
- WCP-7 Structured Sync Merge: OR-join with dead path elimination
- WCP-8 Multi-Merge: Event aggregation (audit trail)
- WCP-9 Structured Discriminator: First responder pattern
- WCP-10 Arbitrary Cycles: Retry loop with backoff
- WCP-11 Implicit Termination: Natural workflow completion
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

import pytest
from rdflib import RDF, Graph, Literal, Namespace, URIRef

if TYPE_CHECKING:
    from tests.containers.rdf_stores import OxigraphContainer

# Namespaces
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
KGC = Namespace("http://kgcl.io/ontology/kgc#")
WF = Namespace("http://example.org/workflow/")


@pytest.mark.container
@pytest.mark.rabbitmq
@pytest.mark.postgres
@pytest.mark.wcp(6)
class TestWCP06MultiChoiceWithRouting:
    """WCP-6: Multi-Choice (OR-split) with RabbitMQ routing.

    Scenario: Risk Assessment Routing
    - Order triggers risk assessment with multiple departments based on conditions
    - Legal: high-value orders (>$10k)
    - Finance: all orders
    - Security: flagged customers or international orders
    - Compliance: regulated products
    """

    def test_risk_assessment_multi_routing(
        self,
        rabbitmq_channel: Any,
        postgres_connection: Any,
    ) -> None:
        """Test OR-split routing to multiple departments based on order attributes.

        Arrange:
        - Create topic exchange for risk routing
        - Set up queues for each department

        Act:
        - Route order to multiple departments based on conditions

        Assert:
        - Message delivered to all matching departments
        - Departments can be 1, 2, 3, or 4 depending on conditions
        """
        # Arrange
        exchange = "risk.routing"
        rabbitmq_channel.exchange_declare(
            exchange=exchange,
            exchange_type="topic",
            auto_delete=True,
        )

        # Create queues for each department
        queues: dict[str, str] = {}
        departments = ["legal", "finance", "security", "compliance"]
        for dept in departments:
            result = rabbitmq_channel.queue_declare(queue="", exclusive=True, auto_delete=True)
            queue_name = result.method.queue
            rabbitmq_channel.queue_bind(
                exchange=exchange,
                queue=queue_name,
                routing_key=f"risk.{dept}",
            )
            queues[dept] = queue_name

        # Order attributes that trigger multiple routing paths
        order = {
            "order_id": "ORD-MULTI-001",
            "amount": 15000.00,  # High value -> legal
            "customer_flagged": True,  # Flagged -> security
            "product_type": "pharmaceutical",  # Regulated -> compliance
            # Finance always gets it
        }

        # Act: OR-split - route to multiple departments
        active_routes = []

        # Legal: high-value orders
        if order["amount"] > 10000:
            active_routes.append("legal")
            rabbitmq_channel.basic_publish(
                exchange=exchange,
                routing_key="risk.legal",
                body=json.dumps(order).encode(),
            )

        # Finance: all orders
        active_routes.append("finance")
        rabbitmq_channel.basic_publish(
            exchange=exchange,
            routing_key="risk.finance",
            body=json.dumps(order).encode(),
        )

        # Security: flagged customers
        if order.get("customer_flagged"):
            active_routes.append("security")
            rabbitmq_channel.basic_publish(
                exchange=exchange,
                routing_key="risk.security",
                body=json.dumps(order).encode(),
            )

        # Compliance: regulated products
        if order.get("product_type") in ["pharmaceutical", "weapons", "crypto"]:
            active_routes.append("compliance")
            rabbitmq_channel.basic_publish(
                exchange=exchange,
                routing_key="risk.compliance",
                body=json.dumps(order).encode(),
            )

        # Log routing decision to PostgreSQL
        cursor = postgres_connection.cursor()
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                order["order_id"],
                6,
                "or_split",
                "risk_router",
                json.dumps({"active_routes": active_routes, "route_count": len(active_routes)}),
            ),
        )
        postgres_connection.commit()

        # Assert: All activated routes received messages
        assert len(active_routes) == 4, "All 4 departments should be activated for this order"

        for dept in active_routes:
            method, _, body = rabbitmq_channel.basic_get(queues[dept], auto_ack=True)
            assert body is not None, f"{dept} queue should have message"
            data = json.loads(body.decode())
            assert data["order_id"] == order["order_id"]

        # Non-activated routes (none in this case) should be empty
        for dept in set(departments) - set(active_routes):
            method, _, body = rabbitmq_channel.basic_get(queues[dept], auto_ack=True)
            assert body is None, f"{dept} queue should be empty"


@pytest.mark.container
@pytest.mark.rabbitmq
@pytest.mark.postgres
@pytest.mark.wcp(7)
class TestWCP07StructuredSyncMergeWithDeadPath:
    """WCP-7: Structured Synchronizing Merge (OR-join) with dead path elimination.

    Scenario: Multi-Department Approval with Smart Sync
    - OR-split routes to departments based on conditions
    - OR-join waits ONLY for activated branches (dead path elimination)
    - Uses RabbitMQ for completion signals
    """

    def test_or_join_with_dead_path_elimination(
        self,
        rabbitmq_channel: Any,
        postgres_connection: Any,
    ) -> None:
        """Test OR-join that waits only for active branches.

        Arrange:
        - Create completion exchange for department signals
        - Activate only legal and finance branches (not security)

        Act:
        - Departments complete their reviews
        - OR-join tracks completions

        Assert:
        - OR-join fires when all ACTIVE branches complete
        - Does not wait for inactive (dead) branches
        """
        # Arrange
        order_id = "ORD-ORJOIN-001"
        exchange = "completion.signals"
        rabbitmq_channel.exchange_declare(
            exchange=exchange,
            exchange_type="fanout",
            auto_delete=True,
        )

        # OR-join collector queue
        result = rabbitmq_channel.queue_declare(queue="", exclusive=True, auto_delete=True)
        collector_queue = result.method.queue
        rabbitmq_channel.queue_bind(exchange=exchange, queue=collector_queue)

        cursor = postgres_connection.cursor()

        # Track which branches are active (set by OR-split)
        active_branches = {"legal", "finance"}  # Security is dead path
        completed_branches: set[str] = set()

        # Act: Simulate branch completions
        for branch in ["legal", "finance"]:
            # Department completes review
            completion_msg = {
                "order_id": order_id,
                "department": branch,
                "result": "approved",
                "timestamp": time.time(),
            }
            rabbitmq_channel.basic_publish(
                exchange=exchange,
                routing_key="",
                body=json.dumps(completion_msg).encode(),
            )

            # Log completion
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (order_id, 7, "branch_complete", f"review_{branch}", json.dumps(completion_msg)),
            )
            completed_branches.add(branch)

        postgres_connection.commit()

        # Collect completions from queue
        collected = []
        while True:
            method, _, body = rabbitmq_channel.basic_get(collector_queue, auto_ack=True)
            if body is None:
                break
            collected.append(json.loads(body.decode()))

        # OR-join semantics: fire when all ACTIVE branches complete
        or_join_can_fire = completed_branches >= active_branches

        # Assert
        assert len(collected) == 2, "Should have 2 completion messages"
        assert or_join_can_fire, "OR-join should fire - all active branches completed"
        assert "security" not in completed_branches, "Security was dead path - not expected"

        # Log OR-join firing
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                order_id,
                7,
                "or_join_fired",
                "sync_merge",
                json.dumps({
                    "active_branches": list(active_branches),
                    "completed_branches": list(completed_branches),
                    "dead_branches": ["security"],
                }),
            ),
        )
        postgres_connection.commit()


@pytest.mark.container
@pytest.mark.rabbitmq
@pytest.mark.postgres
@pytest.mark.wcp(8)
class TestWCP08MultiMergeEventAggregation:
    """WCP-8: Multi-Merge for event aggregation.

    Scenario: Audit Trail Aggregation
    - Multiple systems send events independently
    - Multi-merge task fires for EACH incoming event
    - No synchronization - each event triggers downstream
    """

    def test_multi_merge_event_aggregation(
        self,
        rabbitmq_channel: Any,
        postgres_connection: Any,
    ) -> None:
        """Test multi-merge that triggers for each incoming event.

        Arrange:
        - Create audit event queue
        - Multiple sources send events

        Act:
        - Each event triggers the aggregation task

        Assert:
        - Aggregation task fires once per event
        - No synchronization delays
        """
        # Arrange
        workflow_id = "WF-MULTIMERGE-001"
        queue_name = "audit.events"
        rabbitmq_channel.queue_declare(queue=queue_name, auto_delete=True)

        cursor = postgres_connection.cursor()

        # Simulate events from 3 different sources
        events = [
            {"source": "payment_system", "event": "payment_processed", "amount": 150.00},
            {"source": "inventory_system", "event": "stock_reserved", "sku": "PROD-001"},
            {"source": "shipping_system", "event": "label_created", "tracking": "TRK123"},
        ]

        # Act: Each source sends an event
        for event in events:
            event["workflow_id"] = workflow_id
            rabbitmq_channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=json.dumps(event).encode(),
            )

        # Multi-merge consumer: process EACH event independently
        aggregated_count = 0
        while True:
            method, _, body = rabbitmq_channel.basic_get(queue_name, auto_ack=True)
            if body is None:
                break

            event_data = json.loads(body.decode())
            aggregated_count += 1

            # Each event triggers downstream task (multi-merge semantics)
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    8,
                    "multi_merge_trigger",
                    f"aggregate_{event_data['source']}",
                    json.dumps(event_data),
                ),
            )

        postgres_connection.commit()

        # Assert: Each event triggered the downstream task
        assert aggregated_count == 3, "Multi-merge should fire 3 times (once per event)"

        # Verify audit trail
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND pattern_id = 8 AND event_type = 'multi_merge_trigger'
            """,
            (workflow_id,),
        )
        audit_count = cursor.fetchone()[0]
        assert audit_count == 3, "Should have 3 audit records (one per multi-merge trigger)"


@pytest.mark.container
@pytest.mark.rabbitmq
@pytest.mark.postgres
@pytest.mark.wcp(9)
class TestWCP09StructuredDiscriminatorFirstResponder:
    """WCP-9: Structured Discriminator (first responder pattern).

    Scenario: First Available Support Agent
    - Request routed to multiple support agents in parallel
    - First agent to respond handles the ticket
    - Other responses are discarded
    """

    def test_first_responder_discriminator(
        self,
        rabbitmq_channel: Any,
        postgres_connection: Any,
    ) -> None:
        """Test discriminator that activates on first response.

        Arrange:
        - Create response queue for agents
        - Multiple agents can respond

        Act:
        - Send responses from multiple agents with delays
        - Only first response triggers downstream

        Assert:
        - Only one downstream task activated
        - Subsequent responses are consumed but ignored
        """
        # Arrange
        ticket_id = "TKT-DISC-001"
        response_queue = "support.responses"
        rabbitmq_channel.queue_declare(queue=response_queue, auto_delete=True)

        cursor = postgres_connection.cursor()

        # Simulate agents responding at different times
        responses = [
            {"agent": "agent_1", "response_time": 0.1, "action": "claim"},
            {"agent": "agent_2", "response_time": 0.15, "action": "claim"},
            {"agent": "agent_3", "response_time": 0.2, "action": "claim"},
        ]

        # Act: All agents respond (simulated)
        for response in responses:
            response["ticket_id"] = ticket_id
            rabbitmq_channel.basic_publish(
                exchange="",
                routing_key=response_queue,
                body=json.dumps(response).encode(),
            )

        # Discriminator: Only first wins
        first_responder = None
        discarded_responses = []

        while True:
            method, _, body = rabbitmq_channel.basic_get(response_queue, auto_ack=True)
            if body is None:
                break

            response_data = json.loads(body.decode())

            if first_responder is None:
                # First response wins!
                first_responder = response_data["agent"]
                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        ticket_id,
                        9,
                        "discriminator_fired",
                        "handle_ticket",
                        json.dumps({"winner": first_responder, "response": response_data}),
                    ),
                )
            else:
                # Subsequent responses discarded
                discarded_responses.append(response_data["agent"])

        postgres_connection.commit()

        # Assert
        assert first_responder == "agent_1", "First agent should win the discriminator"
        assert len(discarded_responses) == 2, "Two subsequent responses should be discarded"
        assert "agent_2" in discarded_responses
        assert "agent_3" in discarded_responses

        # Verify only ONE downstream activation
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND pattern_id = 9 AND event_type = 'discriminator_fired'
            """,
            (ticket_id,),
        )
        activation_count = cursor.fetchone()[0]
        assert activation_count == 1, "Discriminator should fire exactly once"


@pytest.mark.container
@pytest.mark.rabbitmq
@pytest.mark.postgres
@pytest.mark.wcp(10)
class TestWCP10ArbitraryCyclesRetryLoop:
    """WCP-10: Arbitrary Cycles with retry loop.

    Scenario: Payment Processing with Retry
    - Payment attempt may fail
    - Retry up to 3 times with exponential backoff
    - Exit loop on success or max retries
    """

    def test_retry_loop_with_backoff(
        self,
        rabbitmq_channel: Any,
        postgres_connection: Any,
    ) -> None:
        """Test arbitrary cycle implementing retry with backoff.

        Arrange:
        - Create retry queue with DLQ
        - Configure max retries

        Act:
        - Simulate payment attempts with failures
        - Retry until success or max attempts

        Assert:
        - Correct number of attempts logged
        - Proper exit condition triggered
        """
        # Arrange
        payment_id = "PAY-RETRY-001"
        max_retries = 3
        cursor = postgres_connection.cursor()

        # Simulate payment processor (fails first 2 times)
        attempt_results = [False, False, True]  # Fail, Fail, Success

        # Act: Execute retry loop
        attempt = 0
        success = False

        while attempt < max_retries and not success:
            attempt += 1
            backoff_ms = 100 * (2 ** (attempt - 1))  # 100, 200, 400ms

            # Log attempt
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    payment_id,
                    10,
                    "cycle_iteration",
                    f"payment_attempt_{attempt}",
                    json.dumps({
                        "attempt": attempt,
                        "backoff_ms": backoff_ms,
                        "max_retries": max_retries,
                    }),
                ),
            )

            # Attempt payment
            if attempt <= len(attempt_results):
                success = attempt_results[attempt - 1]

            if not success and attempt < max_retries:
                # Publish retry message with backoff (simulated)
                rabbitmq_channel.queue_declare(queue="payment.retries", auto_delete=True)
                rabbitmq_channel.basic_publish(
                    exchange="",
                    routing_key="payment.retries",
                    body=json.dumps({
                        "payment_id": payment_id,
                        "attempt": attempt,
                        "backoff_ms": backoff_ms,
                    }).encode(),
                )

        # Log exit condition
        exit_reason = "success" if success else "max_retries_exceeded"
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                payment_id,
                10,
                "cycle_exit",
                "payment_complete",
                json.dumps({
                    "exit_reason": exit_reason,
                    "total_attempts": attempt,
                    "success": success,
                }),
            ),
        )
        postgres_connection.commit()

        # Assert
        assert success, "Payment should succeed on 3rd attempt"
        assert attempt == 3, "Should take exactly 3 attempts"

        # Verify audit trail
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND pattern_id = 10 AND event_type = 'cycle_iteration'
            """,
            (payment_id,),
        )
        iteration_count = cursor.fetchone()[0]
        assert iteration_count == 3, "Should have 3 iteration records"

        cursor.execute(
            """
            SELECT token_state FROM workflow_audit
            WHERE workflow_id = %s AND pattern_id = 10 AND event_type = 'cycle_exit'
            """,
            (payment_id,),
        )
        exit_state = json.loads(cursor.fetchone()[0])
        assert exit_state["exit_reason"] == "success"


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.wcp(11)
class TestWCP11ImplicitTerminationNaturalCompletion:
    """WCP-11: Implicit Termination (natural workflow completion).

    Scenario: Order Fulfillment with Optional Steps
    - Workflow completes when no more tasks can execute
    - No explicit end condition required
    - Tasks complete when their conditions are met
    """

    def test_implicit_termination_detection(
        self,
        postgres_connection: Any,
    ) -> None:
        """Test workflow that terminates implicitly when no tasks remain.

        Arrange:
        - Create workflow with multiple paths
        - Some paths may not be activated

        Act:
        - Execute tasks until none remain executable

        Assert:
        - Workflow terminates when all active paths complete
        - Implicit termination detected correctly
        """
        # Arrange
        order_id = "ORD-IMPLICIT-001"
        cursor = postgres_connection.cursor()

        # Task execution state
        tasks = {
            "receive_order": {"enabled": True, "completed": False, "depends_on": []},
            "validate_inventory": {"enabled": True, "completed": False, "depends_on": ["receive_order"]},
            "process_payment": {"enabled": True, "completed": False, "depends_on": ["receive_order"]},
            "apply_discount": {"enabled": False, "completed": False, "depends_on": ["receive_order"]},  # Disabled
            "ship_order": {"enabled": True, "completed": False, "depends_on": ["validate_inventory", "process_payment"]},
            "send_notification": {"enabled": True, "completed": False, "depends_on": ["ship_order"]},
        }

        # Act: Execute workflow until implicit termination
        tick = 0
        max_ticks = 10  # Safety limit

        while tick < max_ticks:
            tick += 1
            executed_any = False

            for task_name, task in tasks.items():
                # Skip disabled or completed tasks
                if not task["enabled"] or task["completed"]:
                    continue

                # Check dependencies
                deps_met = all(
                    tasks[dep]["completed"]
                    for dep in task["depends_on"]
                )

                if deps_met:
                    # Execute task
                    task["completed"] = True
                    executed_any = True

                    cursor.execute(
                        """
                        INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            order_id,
                            11,
                            "task_completed",
                            task_name,
                            json.dumps({"tick": tick, "dependencies": task["depends_on"]}),
                        ),
                    )

            # Check for implicit termination
            if not executed_any:
                # No tasks executed - workflow terminates
                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        order_id,
                        11,
                        "implicit_termination",
                        "workflow_end",
                        json.dumps({
                            "final_tick": tick,
                            "completed_tasks": [
                                name for name, t in tasks.items()
                                if t["completed"]
                            ],
                            "skipped_tasks": [
                                name for name, t in tasks.items()
                                if not t["enabled"]
                            ],
                        }),
                    ),
                )
                break

        postgres_connection.commit()

        # Assert
        assert tick < max_ticks, "Workflow should terminate before max ticks"

        # Verify completed tasks
        completed_tasks = [name for name, t in tasks.items() if t["completed"]]
        assert len(completed_tasks) == 5, "Should complete 5 tasks (excluding disabled one)"
        assert "apply_discount" not in completed_tasks, "Disabled task should not complete"

        # Verify implicit termination was logged
        cursor.execute(
            """
            SELECT token_state FROM workflow_audit
            WHERE workflow_id = %s AND pattern_id = 11 AND event_type = 'implicit_termination'
            """,
            (order_id,),
        )
        result = cursor.fetchone()
        assert result is not None, "Implicit termination should be logged"
        termination_state = json.loads(result[0])
        assert len(termination_state["completed_tasks"]) == 5
        assert termination_state["skipped_tasks"] == ["apply_discount"]


@pytest.mark.container
@pytest.mark.oxigraph_server
@pytest.mark.rabbitmq
@pytest.mark.postgres
class TestCrossServiceBranchingPatterns:
    """Test advanced branching patterns across multiple services.

    Demonstrates integration between:
    - Oxigraph Server (RDF workflow state)
    - RabbitMQ (routing and coordination)
    - PostgreSQL (audit trail)
    """

    def test_full_branching_workflow(
        self,
        oxigraph_container: OxigraphContainer,
        rabbitmq_channel: Any,
        postgres_connection: Any,
    ) -> None:
        """Test complete OR-split/OR-join workflow across services.

        Arrange:
        - Load workflow topology to Oxigraph
        - Set up RabbitMQ routing
        - Initialize PostgreSQL audit

        Act:
        - Execute OR-split routing
        - Process branches
        - Execute OR-join with dead path elimination

        Assert:
        - RDF state consistent with execution
        - RabbitMQ messages routed correctly
        - PostgreSQL has complete audit trail
        """
        from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

        # Arrange
        workflow_id = "WF-BRANCH-FULL-001"

        # Set up Oxigraph with workflow topology
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container.get_sparql_endpoint(),
            update_endpoint=oxigraph_container.get_update_endpoint(),
        )

        # Load minimal OR-split/OR-join topology
        workflow_turtle = f"""
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
            @prefix kgc: <http://kgcl.io/ontology/kgc#> .
            @prefix wf: <http://example.org/workflow/> .

            wf:start a yawl:InputCondition ;
                kgc:hasToken true .

            wf:router a yawl:AtomicTask ;
                yawl:split yawl:ControlTypeOr ;
                yawl:nextElementRef wf:branch_a, wf:branch_b, wf:branch_c .

            wf:branch_a a yawl:AtomicTask .
            wf:branch_b a yawl:AtomicTask .
            wf:branch_c a yawl:AtomicTask .

            wf:merger a yawl:AtomicTask ;
                yawl:join yawl:ControlTypeOr .

            wf:branch_a yawl:nextElementRef wf:merger .
            wf:branch_b yawl:nextElementRef wf:merger .
            wf:branch_c yawl:nextElementRef wf:merger .
        """
        adapter.load_turtle(workflow_turtle)

        # Set up RabbitMQ exchange
        exchange = "branch.routing"
        rabbitmq_channel.exchange_declare(
            exchange=exchange,
            exchange_type="topic",
            auto_delete=True,
        )

        cursor = postgres_connection.cursor()

        # Act: Execute OR-split (activate branches A and B, skip C)
        active_branches = ["branch_a", "branch_b"]

        for branch in active_branches:
            # Update RDF state
            adapter.update(f"""
                PREFIX kgc: <http://kgcl.io/ontology/kgc#>
                PREFIX wf: <http://example.org/workflow/>
                INSERT DATA {{
                    wf:{branch} kgc:hasToken true .
                }}
            """)

            # Route via RabbitMQ
            rabbitmq_channel.basic_publish(
                exchange=exchange,
                routing_key=f"branch.{branch}",
                body=json.dumps({"workflow_id": workflow_id, "branch": branch}).encode(),
            )

            # Log to PostgreSQL
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (workflow_id, 7, "branch_activated", branch, json.dumps({"active": True})),
            )

        postgres_connection.commit()

        # Assert: Verify all services have consistent state
        # 1. RDF store has tokens on active branches
        for branch in active_branches:
            has_token = adapter.ask(f"""
                PREFIX kgc: <http://kgcl.io/ontology/kgc#>
                PREFIX wf: <http://example.org/workflow/>
                ASK {{ wf:{branch} kgc:hasToken true }}
            """)
            assert has_token, f"{branch} should have token in RDF store"

        # 2. PostgreSQL has audit records
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'branch_activated'
            """,
            (workflow_id,),
        )
        audit_count = cursor.fetchone()[0]
        assert audit_count == 2, "Should have 2 branch activation records"

        # 3. RDF store triple count increased
        assert adapter.triple_count() > 0, "RDF store should have workflow triples"

        # Cleanup
        adapter.clear()
