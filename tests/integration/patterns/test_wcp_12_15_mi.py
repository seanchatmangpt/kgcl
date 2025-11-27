"""Integration tests for Multiple Instance Patterns (WCP-12 to WCP-15).

Tests workflow patterns with parallel database writes and concurrent instance
management using PostgreSQL for state tracking and coordination.

Real-world scenarios:
- WCP-12 MI without Sync: Parallel notification broadcast
- WCP-13 MI with Design-Time: Fixed batch processing (5 items)
- WCP-14 MI with Runtime: Dynamic order line processing
- WCP-15 MI without Prior: Streaming event processing
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
@pytest.mark.wcp(12)
class TestWCP12MIWithoutSynchronization:
    """WCP-12: Multiple Instances without Synchronization.

    Scenario: Notification Broadcast
    - Send notifications to multiple recipients in parallel
    - No need to wait for all to complete
    - Downstream processing can start immediately
    """

    def test_parallel_notification_broadcast(
        self,
        postgres_connection: Any,
    ) -> None:
        """Test multiple instances executing without synchronization.

        Arrange:
        - Create notification task for multiple recipients
        - Configure fire-and-forget semantics

        Act:
        - Spawn multiple instances in parallel
        - Continue workflow without waiting

        Assert:
        - All instances started
        - Downstream task activated before all complete
        """
        # Arrange
        workflow_id = "WF-NOTIF-001"
        cursor = postgres_connection.cursor()

        recipients = [
            {"email": "user1@example.com", "channel": "email"},
            {"email": "user2@example.com", "channel": "email"},
            {"phone": "+1234567890", "channel": "sms"},
            {"device": "ios_token_123", "channel": "push"},
            {"device": "android_token_456", "channel": "push"},
        ]

        # Act: Spawn instances without synchronization
        instances_started = []
        downstream_activated_at = None

        def send_notification(recipient: dict[str, str], instance_id: int) -> dict[str, Any]:
            """Simulate notification sending with variable delay."""
            # Simulate variable processing time
            time.sleep(0.01 * (instance_id + 1))  # 10-50ms

            return {
                "instance_id": instance_id,
                "recipient": recipient,
                "status": "sent",
                "timestamp": time.time(),
            }

        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(send_notification, r, i): i
                for i, r in enumerate(recipients)
            }

            # Activate downstream IMMEDIATELY (no synchronization)
            downstream_activated_at = time.time()
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    12,
                    "downstream_activated",
                    "continue_workflow",
                    json.dumps({
                        "instances_launched": len(recipients),
                        "synchronization": False,
                        "activated_at": downstream_activated_at,
                    }),
                ),
            )
            postgres_connection.commit()

            # Collect results (for logging only, not blocking workflow)
            for future in as_completed(futures):
                result = future.result()
                instances_started.append(result)

                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        workflow_id,
                        12,
                        "instance_completed",
                        f"notify_{result['instance_id']}",
                        json.dumps(result),
                    ),
                )

        postgres_connection.commit()

        # Assert: Downstream was activated before all instances completed
        latest_instance_time = max(r["timestamp"] for r in instances_started)
        assert downstream_activated_at < latest_instance_time, (
            "Downstream should activate before all instances complete (no sync)"
        )

        assert len(instances_started) == 5, "All 5 instances should complete eventually"

        # Verify audit trail
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND pattern_id = 12 AND event_type = 'instance_completed'
            """,
            (workflow_id,),
        )
        completed_count = cursor.fetchone()[0]
        assert completed_count == 5


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.wcp(13)
class TestWCP13MIWithDesignTimeKnowledge:
    """WCP-13: Multiple Instances with A Priori Design-Time Knowledge.

    Scenario: Fixed Batch Processing
    - Process exactly 5 items (known at design time)
    - Wait for all 5 to complete before continuing
    - Parallel execution for performance
    """

    def test_fixed_batch_processing(
        self,
        postgres_connection: Any,
    ) -> None:
        """Test multiple instances with fixed count known at design time.

        Arrange:
        - Create batch task with exactly 5 instances
        - Configure synchronization (wait for all)

        Act:
        - Execute all 5 instances in parallel
        - Wait for synchronization

        Assert:
        - Exactly 5 instances executed
        - Downstream activates only after all complete
        """
        # Arrange
        workflow_id = "WF-BATCH-001"
        cursor = postgres_connection.cursor()

        # Design-time knowledge: exactly 5 items
        batch_size = 5
        items = [{"item_id": f"ITEM-{i:03d}", "data": f"Data for item {i}"} for i in range(batch_size)]

        completed_instances: list[dict[str, Any]] = []
        completion_lock = threading.Lock()

        # Act: Process batch with synchronization
        def process_item(item: dict[str, str], instance_id: int) -> dict[str, Any]:
            """Process a single batch item."""
            # Simulate processing
            time.sleep(0.02)  # 20ms per item

            result = {
                "instance_id": instance_id,
                "item": item,
                "status": "processed",
                "timestamp": time.time(),
            }

            # Thread-safe recording
            with completion_lock:
                completed_instances.append(result)

                # Log to database (each thread gets own cursor)
                with postgres_connection.cursor() as thread_cursor:
                    thread_cursor.execute(
                        """
                        INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            workflow_id,
                            13,
                            "instance_completed",
                            f"process_{item['item_id']}",
                            json.dumps(result),
                        ),
                    )
                    postgres_connection.commit()

            return result

        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = [
                executor.submit(process_item, item, i)
                for i, item in enumerate(items)
            ]

            # Wait for ALL to complete (design-time synchronization)
            results = [f.result() for f in futures]

        # NOW activate downstream (after synchronization)
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                13,
                "synchronization_complete",
                "batch_merge",
                json.dumps({
                    "design_time_count": batch_size,
                    "actual_completed": len(completed_instances),
                    "all_results": results,
                }),
            ),
        )
        postgres_connection.commit()

        # Assert
        assert len(completed_instances) == batch_size, "Exactly 5 instances should complete"

        # Verify synchronization happened (downstream after all instances)
        cursor.execute(
            """
            SELECT id FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'synchronization_complete'
            """,
            (workflow_id,),
        )
        sync_record = cursor.fetchone()
        assert sync_record is not None, "Synchronization should be logged"

        # All instance completions should have lower IDs than sync record
        cursor.execute(
            """
            SELECT MAX(id) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'instance_completed'
            """,
            (workflow_id,),
        )
        max_instance_id = cursor.fetchone()[0]
        assert max_instance_id < sync_record[0], "All instances complete before sync"


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.wcp(14)
class TestWCP14MIWithRuntimeKnowledge:
    """WCP-14: Multiple Instances with A Priori Runtime Knowledge.

    Scenario: Order Line Processing
    - Number of instances determined from order data at runtime
    - Process all order lines in parallel
    - Wait for all to complete
    """

    def test_dynamic_order_line_processing(
        self,
        postgres_connection: Any,
    ) -> None:
        """Test multiple instances with count from runtime data.

        Arrange:
        - Create order with variable number of line items
        - Determine instance count from data

        Act:
        - Spawn instances based on runtime count
        - Process in parallel

        Assert:
        - Instance count matches runtime data
        - All instances complete before downstream
        """
        # Arrange
        workflow_id = "WF-ORDERLINES-001"
        cursor = postgres_connection.cursor()

        # Runtime data: order with line items
        order = {
            "order_id": "ORD-2024-001",
            "customer": "CUST-001",
            "lines": [
                {"sku": "SKU-001", "qty": 2, "price": 29.99},
                {"sku": "SKU-002", "qty": 1, "price": 49.99},
                {"sku": "SKU-003", "qty": 3, "price": 19.99},
                {"sku": "SKU-004", "qty": 1, "price": 99.99},
            ],
        }

        # Runtime knowledge: instance count from data
        instance_count = len(order["lines"])

        # Log runtime determination
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                14,
                "runtime_count_determined",
                "count_lines",
                json.dumps({
                    "expression": "count(/order/lines)",
                    "result": instance_count,
                    "order_id": order["order_id"],
                }),
            ),
        )
        postgres_connection.commit()

        # Act: Process order lines in parallel
        def process_line(line: dict[str, Any], index: int) -> dict[str, Any]:
            """Process a single order line."""
            time.sleep(0.01)  # 10ms processing

            return {
                "line_index": index,
                "sku": line["sku"],
                "subtotal": line["qty"] * line["price"],
                "status": "processed",
            }

        processed_lines = []
        with ThreadPoolExecutor(max_workers=instance_count) as executor:
            futures = {
                executor.submit(process_line, line, i): i
                for i, line in enumerate(order["lines"])
            }

            for future in as_completed(futures):
                result = future.result()
                processed_lines.append(result)

                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        workflow_id,
                        14,
                        "line_processed",
                        f"process_line_{result['line_index']}",
                        json.dumps(result),
                    ),
                )

        postgres_connection.commit()

        # Synchronize and aggregate
        total = sum(line["subtotal"] for line in processed_lines)
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                14,
                "lines_aggregated",
                "calculate_total",
                json.dumps({
                    "runtime_instance_count": instance_count,
                    "processed_count": len(processed_lines),
                    "order_total": total,
                }),
            ),
        )
        postgres_connection.commit()

        # Assert
        assert len(processed_lines) == instance_count, "All runtime-determined instances processed"
        assert len(processed_lines) == 4, "Should have 4 line items"

        # Verify runtime count was used
        cursor.execute(
            """
            SELECT token_state FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'runtime_count_determined'
            """,
            (workflow_id,),
        )
        runtime_state = json.loads(cursor.fetchone()[0])
        assert runtime_state["result"] == 4


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.wcp(15)
class TestWCP15MIWithoutRuntimeKnowledge:
    """WCP-15: Multiple Instances without A Priori Runtime Knowledge.

    Scenario: Streaming Event Processing
    - Instances created dynamically as events arrive
    - Number not known until processing completes
    - Use completion signal to know when done
    """

    def test_dynamic_streaming_events(
        self,
        postgres_connection: Any,
    ) -> None:
        """Test multiple instances created dynamically during execution.

        Arrange:
        - Set up event stream with unknown count
        - Configure dynamic instance creation

        Act:
        - Process events as they arrive
        - Create instances on-demand

        Assert:
        - Final count matches actual events
        - All events processed
        """
        # Arrange
        workflow_id = "WF-STREAM-001"
        cursor = postgres_connection.cursor()

        # Simulate streaming events (count unknown a priori)
        # Using a generator to simulate stream
        def event_stream() -> list[dict[str, Any]]:
            """Simulate a stream of events."""
            events = []
            event_count = 7  # Unknown to workflow at start
            for i in range(event_count):
                events.append({
                    "event_id": f"EVT-{i:04d}",
                    "payload": f"Event data {i}",
                    "timestamp": time.time(),
                })
                time.sleep(0.005)  # 5ms between events
            return events

        # Act: Process events dynamically
        instances_created = 0
        processed_events = []

        # Log start (count unknown)
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                15,
                "dynamic_processing_start",
                "stream_processor",
                json.dumps({"instance_count": "unknown", "mode": "dynamic"}),
            ),
        )
        postgres_connection.commit()

        # Process stream (instances created on-demand)
        for event in event_stream():
            instances_created += 1

            # Process event
            result = {
                "event_id": event["event_id"],
                "processed_at": time.time(),
                "instance_number": instances_created,
            }
            processed_events.append(result)

            # Log dynamic instance
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    15,
                    "dynamic_instance_created",
                    f"process_event_{event['event_id']}",
                    json.dumps(result),
                ),
            )

        postgres_connection.commit()

        # Stream complete - now we know the final count
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                15,
                "dynamic_processing_complete",
                "stream_complete",
                json.dumps({
                    "final_instance_count": instances_created,
                    "events_processed": len(processed_events),
                }),
            ),
        )
        postgres_connection.commit()

        # Assert
        assert instances_created == 7, "Should create 7 instances dynamically"
        assert len(processed_events) == instances_created

        # Verify instance creation was truly dynamic
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND pattern_id = 15 AND event_type = 'dynamic_instance_created'
            """,
            (workflow_id,),
        )
        dynamic_count = cursor.fetchone()[0]
        assert dynamic_count == 7


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
@pytest.mark.wcp(14)
class TestMIWithConcurrencyControl:
    """Multiple Instance pattern with Redis-based concurrency control.

    Scenario: Rate-Limited API Calls
    - Multiple instances need to call external API
    - Rate limiting requires coordination
    - Redis semaphore for concurrency control
    """

    def test_rate_limited_parallel_processing(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test MI pattern with Redis-based rate limiting.

        Arrange:
        - Set up Redis semaphore for max 3 concurrent
        - Create 10 instances

        Act:
        - Process instances with rate limiting
        - Track concurrent executions

        Assert:
        - Never exceed 3 concurrent
        - All 10 eventually complete
        """
        # Arrange
        workflow_id = "WF-RATELIMIT-001"
        cursor = postgres_connection.cursor()

        semaphore_key = f"semaphore:{workflow_id}"
        max_concurrent = 3
        total_instances = 10

        # Initialize semaphore in Redis
        redis_connection.set(semaphore_key, max_concurrent)

        max_observed_concurrent = 0
        current_concurrent = 0
        concurrent_lock = threading.Lock()
        processed = []

        def process_with_rate_limit(instance_id: int) -> dict[str, Any]:
            """Process with semaphore-based rate limiting."""
            nonlocal max_observed_concurrent, current_concurrent

            # Acquire semaphore
            while True:
                current = int(redis_connection.get(semaphore_key) or 0)
                if current > 0:
                    if redis_connection.decr(semaphore_key) >= 0:
                        break
                    else:
                        redis_connection.incr(semaphore_key)  # Restore
                time.sleep(0.01)  # Wait and retry

            try:
                # Track concurrent executions
                with concurrent_lock:
                    current_concurrent += 1
                    max_observed_concurrent = max(max_observed_concurrent, current_concurrent)

                # Simulate API call
                time.sleep(0.02)  # 20ms

                result = {
                    "instance_id": instance_id,
                    "concurrent_at_execution": current_concurrent,
                    "timestamp": time.time(),
                }

                with concurrent_lock:
                    current_concurrent -= 1

                return result
            finally:
                # Release semaphore
                redis_connection.incr(semaphore_key)

        # Act: Process all instances with rate limiting
        with ThreadPoolExecutor(max_workers=total_instances) as executor:
            futures = [
                executor.submit(process_with_rate_limit, i)
                for i in range(total_instances)
            ]

            for future in as_completed(futures):
                result = future.result()
                processed.append(result)

                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        workflow_id,
                        14,
                        "rate_limited_instance",
                        f"api_call_{result['instance_id']}",
                        json.dumps(result),
                    ),
                )

        postgres_connection.commit()

        # Assert
        assert len(processed) == total_instances, "All 10 instances should complete"
        assert max_observed_concurrent <= max_concurrent, (
            f"Should never exceed {max_concurrent} concurrent (saw {max_observed_concurrent})"
        )

        # Verify audit trail
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'rate_limited_instance'
            """,
            (workflow_id,),
        )
        audit_count = cursor.fetchone()[0]
        assert audit_count == 10


@pytest.mark.container
@pytest.mark.oxigraph_server
@pytest.mark.postgres
class TestMICrossServiceCoordination:
    """Test Multiple Instance patterns across multiple services.

    Demonstrates:
    - RDF store for workflow topology
    - PostgreSQL for instance state
    - Parallel writes to both stores
    """

    def test_mi_with_dual_store_tracking(
        self,
        oxigraph_container: OxigraphContainer,
        postgres_connection: Any,
    ) -> None:
        """Test MI pattern with state tracked in both RDF and PostgreSQL.

        Arrange:
        - Load MI workflow to Oxigraph
        - Initialize PostgreSQL tracking

        Act:
        - Execute instances in parallel
        - Update both stores for each instance

        Assert:
        - RDF store has instance tokens
        - PostgreSQL has instance records
        - Both stores consistent
        """
        from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

        # Arrange
        workflow_id = "WF-MI-DUAL-001"
        instance_count = 4

        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container.get_sparql_endpoint(),
            update_endpoint=oxigraph_container.get_update_endpoint(),
        )

        # Load MI workflow topology
        workflow_turtle = """
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
            @prefix kgc: <http://kgcl.io/ontology/kgc#> .
            @prefix wf: <http://example.org/workflow/> .

            wf:mi_task a yawl:AtomicTask ;
                yawl:multipleInstance true ;
                yawl:minInstances 4 ;
                yawl:maxInstances 4 .
        """
        adapter.load_turtle(workflow_turtle)

        cursor = postgres_connection.cursor()

        # Act: Execute instances with dual-store tracking
        def process_instance(instance_id: int) -> None:
            # Update RDF store (instance token)
            adapter.update(f"""
                PREFIX kgc: <http://kgcl.io/ontology/kgc#>
                PREFIX wf: <http://example.org/workflow/>
                INSERT DATA {{
                    wf:instance_{instance_id} a kgc:TaskInstance ;
                        kgc:instanceOf wf:mi_task ;
                        kgc:status "completed" .
                }}
            """)

            # Update PostgreSQL
            with postgres_connection.cursor() as thread_cursor:
                thread_cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        workflow_id,
                        13,
                        "mi_instance",
                        f"instance_{instance_id}",
                        json.dumps({"instance_id": instance_id, "store": "both"}),
                    ),
                )
                postgres_connection.commit()

        with ThreadPoolExecutor(max_workers=instance_count) as executor:
            futures = [executor.submit(process_instance, i) for i in range(instance_count)]
            for future in futures:
                future.result()

        # Assert: Both stores have correct data
        # Check RDF store
        results = adapter.query("""
            PREFIX kgc: <http://kgcl.io/ontology/kgc#>
            SELECT (COUNT(?inst) AS ?count) WHERE {
                ?inst a kgc:TaskInstance .
            }
        """)
        rdf_count = results[0]["count"] if results else 0
        assert rdf_count == instance_count, f"RDF store should have {instance_count} instances"

        # Check PostgreSQL
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'mi_instance'
            """,
            (workflow_id,),
        )
        pg_count = cursor.fetchone()[0]
        assert pg_count == instance_count, f"PostgreSQL should have {instance_count} records"

        # Cleanup
        adapter.clear()
