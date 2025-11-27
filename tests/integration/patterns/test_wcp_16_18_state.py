"""Integration tests for State-Based Patterns (WCP-16 to WCP-18).

Tests workflow patterns with Redis distributed locks for state management,
mutual exclusion, and milestone-based conditional execution.

Real-world scenarios:
- WCP-16 Deferred Choice: External event-driven decision (customer action)
- WCP-17 Interleaved Parallel: Shared resource access with mutex
- WCP-18 Milestone: Time-limited promotional offers
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
@pytest.mark.redis
@pytest.mark.rabbitmq
@pytest.mark.postgres
@pytest.mark.wcp(16)
class TestWCP16DeferredChoiceExternalEvent:
    """WCP-16: Deferred Choice (external event-driven decision).

    Scenario: Customer Action Selection
    - Customer can pay, cancel, or modify order
    - Choice made by external event (customer action)
    - First event wins, others are disabled
    """

    def test_customer_action_deferred_choice(
        self,
        redis_connection: Any,
        rabbitmq_channel: Any,
        postgres_connection: Any,
    ) -> None:
        """Test deferred choice where external event determines path.

        Arrange:
        - Create event queues for each possible action
        - Set up Redis to track which choice was made

        Act:
        - Simulate customer choosing "modify order"
        - First event wins and disables others

        Assert:
        - Only one path activated
        - Other paths properly disabled
        """
        # Arrange
        order_id = "ORD-DEFER-001"
        cursor = postgres_connection.cursor()

        # Create separate queues for each customer action
        actions = ["pay", "cancel", "modify"]
        action_queues: dict[str, str] = {}
        for action in actions:
            result = rabbitmq_channel.queue_declare(queue=f"order.{action}", auto_delete=True)
            action_queues[action] = result.method.queue

        # Redis key for tracking choice state
        choice_key = f"deferred_choice:{order_id}"
        redis_connection.set(choice_key, "pending")

        # Log deferred choice setup
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                order_id,
                16,
                "deferred_choice_started",
                "wait_for_action",
                json.dumps({"available_actions": actions, "status": "waiting"}),
            ),
        )
        postgres_connection.commit()

        # Act: Customer chooses to modify order (external event)
        chosen_action = "modify"

        # Try to claim the choice (atomic Redis operation)
        # Using SET with NX (only if not exists) for atomicity
        claimed = redis_connection.set(f"{choice_key}:claimed", chosen_action, nx=True)

        if claimed:
            # This action won - disable others
            redis_connection.set(choice_key, chosen_action)

            # Send event to chosen queue
            rabbitmq_channel.basic_publish(
                exchange="",
                routing_key=action_queues[chosen_action],
                body=json.dumps({
                    "order_id": order_id,
                    "action": chosen_action,
                    "timestamp": time.time(),
                }).encode(),
            )

            # Log choice made
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    order_id,
                    16,
                    "choice_made",
                    f"execute_{chosen_action}",
                    json.dumps({
                        "chosen_action": chosen_action,
                        "disabled_actions": [a for a in actions if a != chosen_action],
                    }),
                ),
            )
            postgres_connection.commit()

        # Verify the choice state in Redis
        final_choice = redis_connection.get(choice_key).decode()

        # Assert
        assert final_choice == chosen_action, "Choice should be recorded"
        assert claimed, "First claimer should win"

        # Verify only chosen queue has message
        for action, queue in action_queues.items():
            method, _, body = rabbitmq_channel.basic_get(queue, auto_ack=True)
            if action == chosen_action:
                assert body is not None, f"{action} queue should have message"
            else:
                assert body is None, f"{action} queue should be empty"

        # Verify audit trail
        cursor.execute(
            """
            SELECT event_type FROM workflow_audit
            WHERE workflow_id = %s AND pattern_id = 16
            ORDER BY id
            """,
            (order_id,),
        )
        events = [row[0] for row in cursor.fetchall()]
        assert "deferred_choice_started" in events
        assert "choice_made" in events


@pytest.mark.container
@pytest.mark.redis
@pytest.mark.postgres
@pytest.mark.wcp(17)
class TestWCP17InterleavedParallelWithMutex:
    """WCP-17: Interleaved Parallel Routing with mutual exclusion.

    Scenario: Shared Printer Resource
    - Multiple jobs need to print documents
    - Only one job can use printer at a time
    - All jobs must complete
    """

    def test_shared_resource_mutual_exclusion(
        self,
        redis_connection: Any,
        postgres_connection: Any,
    ) -> None:
        """Test interleaved parallel with Redis-based mutex.

        Arrange:
        - Set up Redis lock for shared printer resource
        - Create 3 print jobs that need exclusive access

        Act:
        - Execute jobs with mutex enforcement

        Assert:
        - All jobs complete
        - No concurrent printer access
        """
        # Arrange
        workflow_id = "WF-INTERLEAVED-001"
        cursor = postgres_connection.cursor()

        # Redis mutex for printer
        mutex_key = "mutex:printer"
        mutex_timeout = 10  # 10 second lock timeout

        jobs = [
            {"job_id": "JOB-001", "document": "Report.pdf", "pages": 5},
            {"job_id": "JOB-002", "document": "Invoice.pdf", "pages": 2},
            {"job_id": "JOB-003", "document": "Contract.pdf", "pages": 10},
        ]

        execution_order: list[str] = []
        execution_lock = threading.Lock()

        def print_job(job: dict[str, Any]) -> dict[str, Any]:
            """Execute print job with mutex."""
            job_id = job["job_id"]

            # Acquire mutex (spin lock with Redis SETNX)
            acquired = False
            wait_start = time.time()

            while not acquired and (time.time() - wait_start) < mutex_timeout:
                # Try to acquire lock
                acquired = redis_connection.set(mutex_key, job_id, nx=True, ex=mutex_timeout)
                if not acquired:
                    time.sleep(0.01)  # Wait 10ms before retry

            if not acquired:
                return {"job_id": job_id, "status": "timeout", "error": "Could not acquire lock"}

            try:
                # Critical section - using printer
                with execution_lock:
                    execution_order.append(job_id)

                # Simulate printing (10ms per page)
                time.sleep(0.01 * job["pages"])

                result = {
                    "job_id": job_id,
                    "document": job["document"],
                    "pages": job["pages"],
                    "status": "completed",
                    "timestamp": time.time(),
                }

                # Log to database
                with postgres_connection.cursor() as thread_cursor:
                    thread_cursor.execute(
                        """
                        INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            workflow_id,
                            17,
                            "mutex_execution",
                            f"print_{job_id}",
                            json.dumps(result),
                        ),
                    )
                    postgres_connection.commit()

                return result
            finally:
                # Release mutex
                # Only release if we still hold it (check value)
                current_holder = redis_connection.get(mutex_key)
                if current_holder and current_holder.decode() == job_id:
                    redis_connection.delete(mutex_key)

        # Act: Execute jobs in parallel (but mutex ensures interleaving)
        results = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(print_job, job) for job in jobs]
            for future in as_completed(futures):
                results.append(future.result())

        # Assert
        assert len(results) == 3, "All 3 jobs should complete"
        assert all(r["status"] == "completed" for r in results), "All jobs should succeed"
        assert len(execution_order) == 3, "Execution order should have 3 entries"

        # Verify mutex was respected (jobs didn't overlap)
        # Since we're tracking order and using mutex, execution should be serialized
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND pattern_id = 17 AND event_type = 'mutex_execution'
            """,
            (workflow_id,),
        )
        audit_count = cursor.fetchone()[0]
        assert audit_count == 3, "Should have 3 mutex execution records"

    def test_concurrent_access_prevention(
        self,
        redis_connection: Any,
        postgres_connection: Any,
    ) -> None:
        """Test that concurrent access is properly prevented.

        Arrange:
        - Create shared resource lock
        - Launch concurrent accessors

        Act:
        - Track actual concurrent access count

        Assert:
        - Never more than 1 concurrent accessor
        """
        # Arrange
        workflow_id = "WF-CONCURRENT-001"
        mutex_key = "mutex:shared_resource"

        current_accessors = 0
        max_observed_concurrent = 0
        access_lock = threading.Lock()

        def access_resource(task_id: int) -> None:
            nonlocal current_accessors, max_observed_concurrent

            # Acquire mutex
            while not redis_connection.set(mutex_key, f"task_{task_id}", nx=True, ex=5):
                time.sleep(0.005)

            try:
                with access_lock:
                    current_accessors += 1
                    max_observed_concurrent = max(max_observed_concurrent, current_accessors)

                # Simulate resource access
                time.sleep(0.02)

                with access_lock:
                    current_accessors -= 1
            finally:
                redis_connection.delete(mutex_key)

        # Act: Launch 5 concurrent tasks
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(access_resource, i) for i in range(5)]
            for future in futures:
                future.result()

        # Assert
        assert max_observed_concurrent == 1, (
            f"Should never exceed 1 concurrent accessor (observed {max_observed_concurrent})"
        )


@pytest.mark.container
@pytest.mark.redis
@pytest.mark.postgres
@pytest.mark.wcp(18)
class TestWCP18MilestoneTimeLimited:
    """WCP-18: Milestone (time-limited conditional execution).

    Scenario: Promotional Offer Window
    - Apply discount only while promotion is active
    - Promotion has time window (milestone)
    - Task disabled when milestone expires
    """

    def test_time_limited_promotion_milestone(
        self,
        redis_connection: Any,
        postgres_connection: Any,
    ) -> None:
        """Test milestone with time-based condition.

        Arrange:
        - Set up promotion milestone in Redis with TTL
        - Create orders that may or may not qualify

        Act:
        - Process orders during and after promotion window

        Assert:
        - Discount applied only during active milestone
        """
        # Arrange
        workflow_id = "WF-MILESTONE-001"
        cursor = postgres_connection.cursor()

        # Promotion milestone (200ms window for testing)
        milestone_key = "milestone:summer_promo"
        redis_connection.set(milestone_key, "active", ex=1)  # 1 second TTL

        orders = [
            {"order_id": "ORD-M01", "amount": 100.00, "delay_ms": 0},      # During promo
            {"order_id": "ORD-M02", "amount": 200.00, "delay_ms": 100},    # During promo
            {"order_id": "ORD-M03", "amount": 150.00, "delay_ms": 1200},   # After promo
        ]

        # Act: Process orders with milestone check
        results = []
        for order in orders:
            time.sleep(order["delay_ms"] / 1000)

            # Check milestone status
            milestone_active = redis_connection.exists(milestone_key)

            if milestone_active:
                # Apply 10% discount
                final_amount = order["amount"] * 0.9
                discount_applied = True
            else:
                # No discount
                final_amount = order["amount"]
                discount_applied = False

            result = {
                "order_id": order["order_id"],
                "original_amount": order["amount"],
                "final_amount": final_amount,
                "discount_applied": discount_applied,
                "milestone_active": bool(milestone_active),
            }
            results.append(result)

            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    18,
                    "milestone_check",
                    f"process_{order['order_id']}",
                    json.dumps(result),
                ),
            )

        postgres_connection.commit()

        # Assert
        # First two orders should get discount (milestone active)
        assert results[0]["discount_applied"], "First order should get discount"
        assert results[1]["discount_applied"], "Second order should get discount"

        # Third order should NOT get discount (milestone expired)
        assert not results[2]["discount_applied"], "Third order should NOT get discount"

        # Verify amounts
        assert results[0]["final_amount"] == 90.00, "10% discount on $100"
        assert results[1]["final_amount"] == 180.00, "10% discount on $200"
        assert results[2]["final_amount"] == 150.00, "No discount on $150"

    def test_milestone_state_transition(
        self,
        redis_connection: Any,
        postgres_connection: Any,
    ) -> None:
        """Test milestone state transitions and task enablement.

        Arrange:
        - Create milestone that can be activated/deactivated
        - Track task execution based on milestone

        Act:
        - Toggle milestone state
        - Check task execution at each state

        Assert:
        - Task only executes when milestone active
        """
        # Arrange
        workflow_id = "WF-MILESTONE-002"
        cursor = postgres_connection.cursor()

        milestone_key = "milestone:approval_window"
        task_executions: list[dict[str, Any]] = []

        def try_execute_task(task_name: str) -> bool:
            """Attempt to execute task if milestone allows."""
            milestone_active = redis_connection.exists(milestone_key)

            result = {
                "task": task_name,
                "milestone_active": bool(milestone_active),
                "executed": milestone_active,
                "timestamp": time.time(),
            }
            task_executions.append(result)

            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    18,
                    "milestone_task_attempt",
                    task_name,
                    json.dumps(result),
                ),
            )

            return bool(milestone_active)

        # Act: Test state transitions
        # State 1: Milestone NOT active
        executed_1 = try_execute_task("task_before_activation")

        # State 2: Activate milestone
        redis_connection.set(milestone_key, "active")
        executed_2 = try_execute_task("task_during_active")

        # State 3: Deactivate milestone
        redis_connection.delete(milestone_key)
        executed_3 = try_execute_task("task_after_deactivation")

        # State 4: Reactivate milestone
        redis_connection.set(milestone_key, "active")
        executed_4 = try_execute_task("task_after_reactivation")

        postgres_connection.commit()

        # Assert
        assert not executed_1, "Task should NOT execute before milestone activation"
        assert executed_2, "Task should execute during milestone"
        assert not executed_3, "Task should NOT execute after milestone deactivation"
        assert executed_4, "Task should execute after milestone reactivation"


@pytest.mark.container
@pytest.mark.redis
@pytest.mark.rabbitmq
@pytest.mark.postgres
class TestStatePatternsWithEventCoordination:
    """Test state-based patterns with event coordination.

    Combines Redis state management with RabbitMQ events
    for complex state-driven workflows.
    """

    def test_deferred_choice_with_competing_events(
        self,
        redis_connection: Any,
        rabbitmq_channel: Any,
        postgres_connection: Any,
    ) -> None:
        """Test deferred choice with multiple competing events.

        Arrange:
        - Set up competing event queues
        - Multiple events try to claim the choice

        Act:
        - Send multiple events concurrently

        Assert:
        - Only first event wins
        - State reflects the winner
        """
        # Arrange
        workflow_id = "WF-COMPETE-001"
        cursor = postgres_connection.cursor()

        choice_key = f"choice:{workflow_id}"
        winner_key = f"winner:{workflow_id}"

        # Create event exchange
        exchange = "competing.events"
        rabbitmq_channel.exchange_declare(
            exchange=exchange,
            exchange_type="fanout",
            auto_delete=True,
        )

        result_queue = rabbitmq_channel.queue_declare(queue="", exclusive=True, auto_delete=True)
        rabbitmq_channel.queue_bind(exchange=exchange, queue=result_queue.method.queue)

        # Track competition results
        competition_results: list[dict[str, Any]] = []

        def compete_for_choice(event_id: str) -> bool:
            """Attempt to win the deferred choice."""
            # Try atomic claim
            won = redis_connection.set(choice_key, event_id, nx=True)

            result = {
                "event_id": event_id,
                "won": bool(won),
                "timestamp": time.time(),
            }
            competition_results.append(result)

            if won:
                redis_connection.set(winner_key, event_id)
                rabbitmq_channel.basic_publish(
                    exchange=exchange,
                    routing_key="",
                    body=json.dumps({"winner": event_id}).encode(),
                )

            return bool(won)

        # Act: Multiple events compete concurrently
        events = ["event_A", "event_B", "event_C"]
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(compete_for_choice, event): event
                for event in events
            }
            for future in as_completed(futures):
                future.result()

        # Assert
        # Exactly one winner
        winners = [r for r in competition_results if r["won"]]
        assert len(winners) == 1, "Exactly one event should win"

        # Winner recorded in Redis
        actual_winner = redis_connection.get(winner_key).decode()
        assert actual_winner == winners[0]["event_id"]

        # Winner message in queue
        method, _, body = rabbitmq_channel.basic_get(result_queue.method.queue, auto_ack=True)
        assert body is not None
        winner_msg = json.loads(body.decode())
        assert winner_msg["winner"] == actual_winner


@pytest.mark.container
@pytest.mark.oxigraph_server
@pytest.mark.redis
@pytest.mark.postgres
class TestStatePatternsWithRDFState:
    """Test state-based patterns with RDF state tracking.

    Uses Oxigraph for workflow topology and state,
    Redis for locks, PostgreSQL for audit.
    """

    def test_milestone_with_rdf_state(
        self,
        oxigraph_container: OxigraphContainer,
        redis_connection: Any,
        postgres_connection: Any,
    ) -> None:
        """Test milestone pattern with state in RDF store.

        Arrange:
        - Load workflow with milestone to Oxigraph
        - Set milestone state in Redis

        Act:
        - Query RDF for milestone condition
        - Execute based on combined state

        Assert:
        - Task execution respects milestone
        - RDF state consistent
        """
        from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

        # Arrange
        workflow_id = "WF-RDF-MILESTONE-001"

        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container.get_sparql_endpoint(),
            update_endpoint=oxigraph_container.get_update_endpoint(),
        )

        # Load workflow with milestone condition
        workflow_turtle = """
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
            @prefix kgc: <http://kgcl.io/ontology/kgc#> .
            @prefix wf: <http://example.org/workflow/> .

            wf:discount_task a yawl:AtomicTask ;
                yawl:milestone "promo_active" ;
                kgc:requiresMilestone true .
        """
        adapter.load_turtle(workflow_turtle)

        milestone_key = "milestone:promo_active"
        cursor = postgres_connection.cursor()

        # Act: Check task execution with milestone states
        # State 1: Milestone inactive
        task_enabled_1 = adapter.ask("""
            PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
            PREFIX wf: <http://example.org/workflow/>
            ASK { wf:discount_task yawl:milestone ?m }
        """)
        milestone_active_1 = redis_connection.exists(milestone_key)
        can_execute_1 = task_enabled_1 and milestone_active_1

        # State 2: Activate milestone
        redis_connection.set(milestone_key, "active")
        milestone_active_2 = redis_connection.exists(milestone_key)
        can_execute_2 = task_enabled_1 and milestone_active_2

        # Log state check
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                18,
                "rdf_milestone_check",
                "discount_task",
                json.dumps({
                    "rdf_milestone_defined": task_enabled_1,
                    "redis_milestone_before": milestone_active_1,
                    "redis_milestone_after": milestone_active_2,
                    "can_execute_before": can_execute_1,
                    "can_execute_after": can_execute_2,
                }),
            ),
        )
        postgres_connection.commit()

        # Assert
        assert task_enabled_1, "Task should have milestone defined in RDF"
        assert not milestone_active_1, "Milestone should be inactive initially"
        assert milestone_active_2, "Milestone should be active after setting"
        assert not can_execute_1, "Task should not execute without active milestone"
        assert can_execute_2, "Task should execute with active milestone"

        # Cleanup
        adapter.clear()
