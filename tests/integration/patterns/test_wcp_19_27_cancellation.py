"""Integration tests for Cancellation and Force Completion Patterns (WCP-19 to WCP-27).

Tests workflow patterns with PostgreSQL transaction rollback for cancellation,
RabbitMQ for cancellation events, and Redis for state management.

Real-world scenarios:
- WCP-19 Cancel Activity: Cancel pending order item
- WCP-20 Cancel Case: Cancel entire order
- WCP-21 Cancel Region: Cancel order fulfillment region
- WCP-22 Cancel MI Activity: Cancel all parallel shipment tracking
- WCP-23 Structured Loop: Retry payment processing
- WCP-24 Recursion: Hierarchical approval escalation
- WCP-25 Transient Trigger: Flash sale timeout
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from tests.containers.rdf_stores import OxigraphContainer


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.wcp(19)
class TestWCP19CancelActivityWithRollback:
    """WCP-19: Cancel Activity with transaction rollback.

    Scenario: Cancel Pending Order Item
    - Order has multiple items in various states
    - Cancel specific item and rollback its processing
    - Other items continue unaffected
    """

    def test_cancel_single_activity_with_rollback(
        self,
        postgres_connection: Any,
    ) -> None:
        """Test cancelling single activity with database rollback.

        Arrange:
        - Create order with multiple items
        - Start processing all items in transaction

        Act:
        - Cancel one specific item
        - Rollback its transaction

        Assert:
        - Cancelled item rolled back
        - Other items complete normally
        """
        # Arrange
        workflow_id = "WF-CANCEL-ACT-001"
        cursor = postgres_connection.cursor()

        items = [
            {"item_id": "ITEM-001", "status": "pending", "amount": 50.00},
            {"item_id": "ITEM-002", "status": "pending", "amount": 75.00},  # Will be cancelled
            {"item_id": "ITEM-003", "status": "pending", "amount": 100.00},
        ]

        # Log workflow start
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                19,
                "workflow_started",
                "order_processing",
                json.dumps({"items": [i["item_id"] for i in items]}),
            ),
        )
        postgres_connection.commit()

        # Act: Process items with potential cancellation
        processed_items = []
        cancelled_items = []

        for item in items:
            # Start transaction for this item
            try:
                # Begin nested transaction (savepoint)
                cursor.execute(f"SAVEPOINT item_{item['item_id']}")

                # Simulate processing
                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        workflow_id,
                        19,
                        "item_processing",
                        f"process_{item['item_id']}",
                        json.dumps({"item": item, "status": "in_progress"}),
                    ),
                )

                # Check if this item should be cancelled
                if item["item_id"] == "ITEM-002":
                    # Cancel this activity - rollback savepoint
                    cursor.execute(f"ROLLBACK TO SAVEPOINT item_{item['item_id']}")

                    # Log cancellation
                    cursor.execute(
                        """
                        INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            workflow_id,
                            19,
                            "activity_cancelled",
                            f"cancel_{item['item_id']}",
                            json.dumps({"item_id": item["item_id"], "reason": "customer_request"}),
                        ),
                    )
                    cancelled_items.append(item["item_id"])
                else:
                    # Complete this item
                    cursor.execute(f"RELEASE SAVEPOINT item_{item['item_id']}")
                    processed_items.append(item["item_id"])

            except Exception as e:
                cursor.execute(f"ROLLBACK TO SAVEPOINT item_{item['item_id']}")
                cancelled_items.append(item["item_id"])

        postgres_connection.commit()

        # Assert
        assert "ITEM-002" in cancelled_items, "ITEM-002 should be cancelled"
        assert "ITEM-001" in processed_items, "ITEM-001 should be processed"
        assert "ITEM-003" in processed_items, "ITEM-003 should be processed"
        assert len(processed_items) == 2
        assert len(cancelled_items) == 1

        # Verify audit trail shows cancellation
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'activity_cancelled'
            """,
            (workflow_id,),
        )
        cancel_count = cursor.fetchone()[0]
        assert cancel_count == 1


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.rabbitmq
@pytest.mark.wcp(20)
class TestWCP20CancelCaseWithFullRollback:
    """WCP-20: Cancel Case with full transaction rollback.

    Scenario: Cancel Entire Order
    - Customer requests order cancellation
    - All order activities must be rolled back
    - Inventory released, payments refunded
    """

    def test_cancel_entire_case(
        self,
        postgres_connection: Any,
        rabbitmq_channel: Any,
    ) -> None:
        """Test cancelling entire workflow case.

        Arrange:
        - Create order with multiple processing stages
        - Each stage has committed work

        Act:
        - Issue cancel case command
        - Rollback all work

        Assert:
        - All activities cancelled
        - All transactions rolled back
        """
        # Arrange
        order_id = "ORD-CANCEL-001"
        cursor = postgres_connection.cursor()

        # Set up cancellation exchange
        cancel_exchange = "order.cancellation"
        rabbitmq_channel.exchange_declare(
            exchange=cancel_exchange,
            exchange_type="fanout",
            auto_delete=True,
        )

        # Create subscribers for cancellation
        queues = {}
        for service in ["inventory", "payment", "shipping"]:
            result = rabbitmq_channel.queue_declare(queue="", exclusive=True, auto_delete=True)
            rabbitmq_channel.queue_bind(exchange=cancel_exchange, queue=result.method.queue)
            queues[service] = result.method.queue

        # Simulate order in progress with various stages
        stages = [
            {"stage": "inventory_reserved", "service": "inventory"},
            {"stage": "payment_authorized", "service": "payment"},
            {"stage": "shipping_scheduled", "service": "shipping"},
        ]

        # Log each stage completion
        for stage in stages:
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    order_id,
                    20,
                    "stage_completed",
                    stage["stage"],
                    json.dumps({"service": stage["service"], "status": "active"}),
                ),
            )
        postgres_connection.commit()

        # Act: Cancel entire case
        # Publish cancellation event
        cancel_event = {
            "order_id": order_id,
            "cancel_type": "full_case",
            "reason": "customer_request",
            "timestamp": time.time(),
        }
        rabbitmq_channel.basic_publish(
            exchange=cancel_exchange,
            routing_key="",
            body=json.dumps(cancel_event).encode(),
        )

        # Each service receives cancellation and rolls back
        rollback_results = []
        for service, queue in queues.items():
            method, _, body = rabbitmq_channel.basic_get(queue, auto_ack=True)
            if body:
                event = json.loads(body.decode())

                # Simulate rollback for this service
                rollback_result = {
                    "service": service,
                    "order_id": event["order_id"],
                    "action": "rollback",
                    "status": "completed",
                }
                rollback_results.append(rollback_result)

                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        order_id,
                        20,
                        "service_rollback",
                        f"rollback_{service}",
                        json.dumps(rollback_result),
                    ),
                )

        # Log case cancellation complete
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                order_id,
                20,
                "case_cancelled",
                "cancel_complete",
                json.dumps({
                    "services_rolled_back": [r["service"] for r in rollback_results],
                    "total_rollbacks": len(rollback_results),
                }),
            ),
        )
        postgres_connection.commit()

        # Assert
        assert len(rollback_results) == 3, "All 3 services should rollback"
        services_rolled_back = {r["service"] for r in rollback_results}
        assert services_rolled_back == {"inventory", "payment", "shipping"}

        # Verify audit trail
        cursor.execute(
            """
            SELECT event_type FROM workflow_audit
            WHERE workflow_id = %s AND pattern_id = 20
            ORDER BY id
            """,
            (order_id,),
        )
        events = [row[0] for row in cursor.fetchall()]
        assert events.count("stage_completed") == 3
        assert events.count("service_rollback") == 3
        assert "case_cancelled" in events


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.wcp(21)
class TestWCP21CancelRegionWithPartialRollback:
    """WCP-21: Cancel Region with partial rollback.

    Scenario: Cancel Fulfillment Region
    - Order has multiple regions (domestic, international)
    - Cancel only the international fulfillment region
    - Domestic fulfillment continues
    """

    def test_cancel_region_partial_rollback(
        self,
        postgres_connection: Any,
    ) -> None:
        """Test cancelling a workflow region while others continue.

        Arrange:
        - Create order with domestic and international items
        - Both regions processing in parallel

        Act:
        - Cancel international region only
        - Domestic region continues

        Assert:
        - International tasks cancelled
        - Domestic tasks complete
        """
        # Arrange
        order_id = "ORD-REGION-001"
        cursor = postgres_connection.cursor()

        regions = {
            "domestic": [
                {"task": "pick_domestic", "status": "active"},
                {"task": "pack_domestic", "status": "pending"},
                {"task": "ship_domestic", "status": "pending"},
            ],
            "international": [
                {"task": "customs_check", "status": "active"},
                {"task": "international_pack", "status": "pending"},
                {"task": "international_ship", "status": "pending"},
            ],
        }

        # Log initial state
        for region_name, tasks in regions.items():
            for task in tasks:
                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        order_id,
                        21,
                        "task_created",
                        task["task"],
                        json.dumps({"region": region_name, "status": task["status"]}),
                    ),
                )
        postgres_connection.commit()

        # Act: Cancel international region
        cancelled_region = "international"
        cancelled_tasks = []
        completed_tasks = []

        for region_name, tasks in regions.items():
            if region_name == cancelled_region:
                # Cancel all tasks in this region
                for task in tasks:
                    cursor.execute(
                        """
                        INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            order_id,
                            21,
                            "region_task_cancelled",
                            task["task"],
                            json.dumps({
                                "region": region_name,
                                "reason": "region_cancellation",
                            }),
                        ),
                    )
                    cancelled_tasks.append(task["task"])
            else:
                # Complete tasks in other regions
                for task in tasks:
                    cursor.execute(
                        """
                        INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            order_id,
                            21,
                            "task_completed",
                            task["task"],
                            json.dumps({"region": region_name, "status": "completed"}),
                        ),
                    )
                    completed_tasks.append(task["task"])

        # Log region cancellation
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                order_id,
                21,
                "region_cancelled",
                f"cancel_{cancelled_region}",
                json.dumps({
                    "region": cancelled_region,
                    "tasks_cancelled": cancelled_tasks,
                    "other_regions_continuing": ["domestic"],
                }),
            ),
        )
        postgres_connection.commit()

        # Assert
        assert len(cancelled_tasks) == 3, "All international tasks cancelled"
        assert len(completed_tasks) == 3, "All domestic tasks completed"
        assert all("international" in t or "customs" in t for t in cancelled_tasks)
        assert all("domestic" in t for t in completed_tasks)


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
@pytest.mark.wcp(22)
class TestWCP22CancelMIActivityWithInstanceCleanup:
    """WCP-22: Cancel Multiple Instance Activity.

    Scenario: Cancel Parallel Shipment Tracking
    - Order shipped in 5 parallel packages
    - Cancel all tracking instances when delivery confirmed
    """

    def test_cancel_all_mi_instances(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test cancelling all instances of a MI task.

        Arrange:
        - Create 5 parallel tracking instances
        - Instances in various states

        Act:
        - Issue MI cancellation
        - Clean up all instances

        Assert:
        - All 5 instances cancelled
        - Redis state cleared
        """
        # Arrange
        workflow_id = "WF-MI-CANCEL-001"
        cursor = postgres_connection.cursor()

        # Create tracking instances in Redis
        instance_count = 5
        for i in range(instance_count):
            redis_connection.hset(
                f"mi_instances:{workflow_id}",
                f"tracking_{i}",
                json.dumps({
                    "instance_id": i,
                    "package_id": f"PKG-{i:03d}",
                    "status": "tracking",
                    "last_update": time.time(),
                }),
            )

            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    22,
                    "mi_instance_created",
                    f"tracking_{i}",
                    json.dumps({"instance_id": i, "status": "active"}),
                ),
            )
        postgres_connection.commit()

        # Verify instances exist
        initial_count = redis_connection.hlen(f"mi_instances:{workflow_id}")
        assert initial_count == instance_count

        # Act: Cancel all MI instances
        cancelled_instances = []

        # Get all instance keys
        instance_keys = redis_connection.hgetall(f"mi_instances:{workflow_id}")

        for key, value in instance_keys.items():
            instance_data = json.loads(value.decode() if isinstance(value, bytes) else value)
            key_str = key.decode() if isinstance(key, bytes) else key

            # Cancel instance
            redis_connection.hdel(f"mi_instances:{workflow_id}", key_str)
            cancelled_instances.append(instance_data["instance_id"])

            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    22,
                    "mi_instance_cancelled",
                    key_str,
                    json.dumps({"instance_id": instance_data["instance_id"], "cancelled": True}),
                ),
            )

        # Log MI activity cancellation complete
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                22,
                "mi_activity_cancelled",
                "tracking_complete",
                json.dumps({
                    "total_instances": instance_count,
                    "cancelled_instances": len(cancelled_instances),
                }),
            ),
        )
        postgres_connection.commit()

        # Assert
        assert len(cancelled_instances) == instance_count
        final_count = redis_connection.hlen(f"mi_instances:{workflow_id}")
        assert final_count == 0, "All instances should be removed from Redis"

        # Verify audit trail
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'mi_instance_cancelled'
            """,
            (workflow_id,),
        )
        cancel_audit_count = cursor.fetchone()[0]
        assert cancel_audit_count == instance_count


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.wcp(23)
class TestWCP23StructuredLoopWithRetry:
    """WCP-23: Structured Loop for retry processing.

    Scenario: Payment Processing Retry
    - Payment may fail due to temporary issues
    - Retry with exponential backoff
    - Exit on success or max retries
    """

    def test_payment_retry_loop(
        self,
        postgres_connection: Any,
    ) -> None:
        """Test structured loop for payment retry.

        Arrange:
        - Configure retry parameters
        - Simulate payment processor

        Act:
        - Execute loop until success or max retries

        Assert:
        - Correct number of iterations
        - Proper exit condition
        """
        # Arrange
        workflow_id = "WF-LOOP-001"
        cursor = postgres_connection.cursor()

        max_retries = 5
        # Simulate: fail first 2 attempts, succeed on 3rd
        payment_results = [False, False, True]

        # Act: Execute structured loop
        iteration = 0
        success = False

        while iteration < max_retries and not success:
            iteration += 1
            backoff_ms = 50 * (2 ** (iteration - 1))  # 50, 100, 200, ...

            # Log iteration start
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    23,
                    "loop_iteration_start",
                    f"payment_attempt_{iteration}",
                    json.dumps({
                        "iteration": iteration,
                        "backoff_ms": backoff_ms,
                        "max_retries": max_retries,
                    }),
                ),
            )

            # Attempt payment
            if iteration <= len(payment_results):
                success = payment_results[iteration - 1]
            else:
                success = False

            # Log iteration result
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    23,
                    "loop_iteration_end",
                    f"payment_result_{iteration}",
                    json.dumps({"iteration": iteration, "success": success}),
                ),
            )

            if not success and iteration < max_retries:
                time.sleep(backoff_ms / 1000)  # Apply backoff

        # Log loop exit
        exit_reason = "success" if success else "max_retries"
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                23,
                "loop_exit",
                "payment_complete",
                json.dumps({
                    "exit_reason": exit_reason,
                    "total_iterations": iteration,
                    "success": success,
                }),
            ),
        )
        postgres_connection.commit()

        # Assert
        assert success, "Payment should succeed on 3rd attempt"
        assert iteration == 3, "Should take exactly 3 iterations"

        # Verify audit trail
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'loop_iteration_start'
            """,
            (workflow_id,),
        )
        iteration_count = cursor.fetchone()[0]
        assert iteration_count == 3


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.wcp(24)
class TestWCP24RecursionWithApprovalEscalation:
    """WCP-24: Recursion for hierarchical approval.

    Scenario: Approval Escalation
    - Request starts with team lead approval
    - If rejected, escalate to manager
    - If still rejected, escalate to director
    - Base case: approval granted or top level reached
    """

    def test_approval_escalation_recursion(
        self,
        postgres_connection: Any,
    ) -> None:
        """Test recursive approval escalation.

        Arrange:
        - Define approval hierarchy
        - Configure rejection simulation

        Act:
        - Execute recursive approval
        - Escalate on rejections

        Assert:
        - Correct recursion depth
        - Proper base case termination
        """
        # Arrange
        workflow_id = "WF-RECURSE-001"
        cursor = postgres_connection.cursor()

        approval_hierarchy = ["team_lead", "manager", "director", "vp"]
        # Simulate: team_lead rejects, manager approves
        approval_decisions = {
            "team_lead": False,
            "manager": True,
            "director": True,
            "vp": True,
        }

        # Act: Recursive approval
        def request_approval(level_index: int, recursion_depth: int) -> dict[str, Any]:
            """Recursive approval request."""
            if level_index >= len(approval_hierarchy):
                # Base case: top of hierarchy reached
                return {
                    "approved": False,
                    "final_level": approval_hierarchy[-1],
                    "reason": "top_level_reached",
                    "depth": recursion_depth,
                }

            current_approver = approval_hierarchy[level_index]

            # Log approval request
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    24,
                    "approval_requested",
                    f"request_{current_approver}",
                    json.dumps({
                        "approver": current_approver,
                        "level": level_index,
                        "recursion_depth": recursion_depth,
                    }),
                ),
            )

            # Get decision
            approved = approval_decisions.get(current_approver, False)

            # Log decision
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    24,
                    "approval_decision",
                    f"decision_{current_approver}",
                    json.dumps({"approver": current_approver, "approved": approved}),
                ),
            )

            if approved:
                # Base case: approval granted
                return {
                    "approved": True,
                    "final_level": current_approver,
                    "depth": recursion_depth,
                }
            else:
                # Recursive case: escalate to next level
                cursor.execute(
                    """
                    INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        workflow_id,
                        24,
                        "escalation",
                        f"escalate_from_{current_approver}",
                        json.dumps({
                            "from": current_approver,
                            "to": approval_hierarchy[level_index + 1] if level_index + 1 < len(approval_hierarchy) else None,
                        }),
                    ),
                )
                return request_approval(level_index + 1, recursion_depth + 1)

        # Execute recursion
        result = request_approval(0, 1)
        postgres_connection.commit()

        # Assert
        assert result["approved"], "Should be approved by manager"
        assert result["final_level"] == "manager"
        assert result["depth"] == 2, "Should have recursion depth of 2"

        # Verify escalation happened
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'escalation'
            """,
            (workflow_id,),
        )
        escalation_count = cursor.fetchone()[0]
        assert escalation_count == 1, "Should escalate once (team_lead -> manager)"


@pytest.mark.container
@pytest.mark.redis
@pytest.mark.postgres
@pytest.mark.wcp(25)
class TestWCP25TransientTriggerWithTimeout:
    """WCP-25: Transient Trigger (time-sensitive event).

    Scenario: Flash Sale Timeout
    - Flash sale offer is time-limited
    - Must be accepted within window
    - Offer expires if not acted upon
    """

    def test_transient_trigger_flash_sale(
        self,
        redis_connection: Any,
        postgres_connection: Any,
    ) -> None:
        """Test transient trigger with timeout.

        Arrange:
        - Create flash sale offer with short TTL
        - Set up acceptance window

        Act:
        - Try to accept offer within and outside window

        Assert:
        - Offer accepted within window
        - Offer rejected after timeout
        """
        # Arrange
        workflow_id = "WF-TRANSIENT-001"
        cursor = postgres_connection.cursor()

        # Create transient trigger (flash sale offer) with 200ms TTL
        offer_key = f"flash_sale:{workflow_id}"
        redis_connection.set(
            offer_key,
            json.dumps({"discount": 50, "product": "PROD-001"}),
            px=200,  # 200ms TTL
        )

        # Log offer creation
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                25,
                "transient_trigger_created",
                "flash_sale_offer",
                json.dumps({"ttl_ms": 200, "discount": 50}),
            ),
        )
        postgres_connection.commit()

        # Act: Try to accept within window
        offer_data = redis_connection.get(offer_key)
        if offer_data:
            offer = json.loads(offer_data.decode())
            within_window_result = {"accepted": True, "offer": offer}
        else:
            within_window_result = {"accepted": False, "reason": "offer_expired"}

        # Log within-window attempt
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                25,
                "trigger_response",
                "accept_within_window",
                json.dumps(within_window_result),
            ),
        )

        # Wait for offer to expire
        time.sleep(0.3)  # 300ms

        # Try to accept after expiry
        offer_data_after = redis_connection.get(offer_key)
        if offer_data_after:
            after_window_result = {"accepted": True, "offer": json.loads(offer_data_after.decode())}
        else:
            after_window_result = {"accepted": False, "reason": "offer_expired"}

        # Log after-window attempt
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                25,
                "trigger_response",
                "accept_after_window",
                json.dumps(after_window_result),
            ),
        )
        postgres_connection.commit()

        # Assert
        assert within_window_result["accepted"], "Should accept within window"
        assert not after_window_result["accepted"], "Should NOT accept after window"
        assert after_window_result["reason"] == "offer_expired"


@pytest.mark.container
@pytest.mark.oxigraph_server
@pytest.mark.postgres
@pytest.mark.rabbitmq
class TestCancellationWithCrossServiceCoordination:
    """Test cancellation patterns with cross-service coordination.

    Demonstrates cancellation across:
    - Oxigraph (RDF state)
    - PostgreSQL (audit/transactions)
    - RabbitMQ (cancellation events)
    """

    def test_coordinated_case_cancellation(
        self,
        oxigraph_container: OxigraphContainer,
        postgres_connection: Any,
        rabbitmq_channel: Any,
    ) -> None:
        """Test case cancellation with coordinated rollback across services.

        Arrange:
        - Create workflow state in Oxigraph
        - Create audit records in PostgreSQL
        - Set up cancellation event routing

        Act:
        - Issue coordinated cancellation

        Assert:
        - RDF state cleared
        - PostgreSQL rollback logged
        - Cancellation events delivered
        """
        from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

        # Arrange
        workflow_id = "WF-COORD-CANCEL-001"

        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container.get_sparql_endpoint(),
            update_endpoint=oxigraph_container.get_update_endpoint(),
        )

        # Load workflow state to Oxigraph
        workflow_turtle = f"""
            @prefix kgc: <http://kgcl.io/ontology/kgc#> .
            @prefix wf: <http://example.org/workflow/> .

            wf:{workflow_id} a kgc:WorkflowInstance ;
                kgc:status "active" ;
                kgc:hasTask wf:task_1, wf:task_2, wf:task_3 .

            wf:task_1 kgc:status "completed" .
            wf:task_2 kgc:status "active" .
            wf:task_3 kgc:status "pending" .
        """
        adapter.load_turtle(workflow_turtle)

        # Set up cancellation exchange
        cancel_exchange = "workflow.cancel"
        rabbitmq_channel.exchange_declare(
            exchange=cancel_exchange,
            exchange_type="fanout",
            auto_delete=True,
        )

        result_queue = rabbitmq_channel.queue_declare(queue="", exclusive=True, auto_delete=True)
        rabbitmq_channel.queue_bind(exchange=cancel_exchange, queue=result_queue.method.queue)

        cursor = postgres_connection.cursor()

        # Act: Issue coordinated cancellation
        # 1. Clear RDF state
        adapter.update(f"""
            PREFIX kgc: <http://kgcl.io/ontology/kgc#>
            PREFIX wf: <http://example.org/workflow/>
            DELETE WHERE {{
                wf:{workflow_id} ?p ?o .
            }}
        """)

        # 2. Log cancellation to PostgreSQL
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                20,
                "coordinated_cancellation",
                "cancel_all_services",
                json.dumps({
                    "rdf_cleared": True,
                    "services_notified": ["oxigraph", "postgres", "rabbitmq"],
                }),
            ),
        )
        postgres_connection.commit()

        # 3. Publish cancellation event
        rabbitmq_channel.basic_publish(
            exchange=cancel_exchange,
            routing_key="",
            body=json.dumps({
                "workflow_id": workflow_id,
                "action": "cancel",
                "timestamp": time.time(),
            }).encode(),
        )

        # Assert
        # RDF state should be cleared
        exists = adapter.ask(f"""
            PREFIX wf: <http://example.org/workflow/>
            ASK {{ wf:{workflow_id} ?p ?o }}
        """)
        assert not exists, "Workflow should be removed from RDF store"

        # Cancellation event should be delivered
        method, _, body = rabbitmq_channel.basic_get(result_queue.method.queue, auto_ack=True)
        assert body is not None, "Cancellation event should be delivered"
        event = json.loads(body.decode())
        assert event["workflow_id"] == workflow_id
        assert event["action"] == "cancel"

        # Audit trail should reflect cancellation
        cursor.execute(
            """
            SELECT COUNT(*) FROM workflow_audit
            WHERE workflow_id = %s AND event_type = 'coordinated_cancellation'
            """,
            (workflow_id,),
        )
        audit_count = cursor.fetchone()[0]
        assert audit_count == 1

        # Cleanup
        adapter.clear()
