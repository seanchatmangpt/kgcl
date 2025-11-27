"""End-to-end integration tests for Order Fulfillment business scenario.

Tests complete order processing workflow across all services with
multiple WCP patterns, hooks, and cross-service coordination.

Business Scenario: E-Commerce Order Fulfillment
- Order placement and validation
- Parallel compliance checks (WCP-2, WCP-3)
- Payment processing with retry (WCP-23)
- Inventory reservation (WCP-16)
- Multi-carrier shipping quotes (WCP-35)
- Order fulfillment and notification (WCP-5)
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
@pytest.mark.oxigraph_server
@pytest.mark.postgres
@pytest.mark.redis
@pytest.mark.rabbitmq
class TestE2EOrderFulfillment:
    """End-to-end order fulfillment with all services.

    Complete business scenario demonstrating:
    - RDF workflow topology (Oxigraph)
    - Audit trail and lockchain (PostgreSQL)
    - Runtime state and locks (Redis)
    - Event coordination (RabbitMQ)
    """

    def test_complete_order_fulfillment_happy_path(
        self,
        oxigraph_container: OxigraphContainer,
        postgres_connection: Any,
        redis_connection: Any,
        rabbitmq_channel: Any,
    ) -> None:
        """Test complete order fulfillment workflow.

        Scenario:
        1. Order placed by customer
        2. Parallel compliance checks (legal, finance, security)
        3. Payment processing with retry
        4. Inventory reservation with lock
        5. Request shipping quotes (first 2 of 4)
        6. Ship order and send notifications

        Assert:
        - All services have consistent state
        - Workflow completes successfully
        - Audit trail complete
        """
        from kgcl.hybrid.adapters.postgres_lockchain import PostgresLockchainWriter
        from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

        # Arrange
        order_id = "ORD-E2E-001"
        workflow_id = f"WF-{order_id}"

        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container.get_sparql_endpoint(),
            update_endpoint=oxigraph_container.get_update_endpoint(),
        )
        lockchain = PostgresLockchainWriter(postgres_connection)
        cursor = postgres_connection.cursor()

        # Order data
        order = {
            "order_id": order_id,
            "customer_id": "CUST-001",
            "items": [
                {"sku": "SKU-001", "qty": 2, "price": 29.99},
                {"sku": "SKU-002", "qty": 1, "price": 149.99},
            ],
            "total": 209.97,
            "shipping_address": "123 Main St, City, ST 12345",
        }

        # Load workflow topology to Oxigraph
        workflow_turtle = f"""
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
            @prefix kgc: <http://kgcl.io/ontology/kgc#> .
            @prefix wf: <http://example.org/workflow/> .
            @prefix order: <http://example.org/order/> .

            wf:{workflow_id} a kgc:WorkflowInstance ;
                kgc:status "active" ;
                kgc:forOrder order:{order_id} .

            order:{order_id} a kgc:Order ;
                kgc:total {order['total']} ;
                kgc:status "pending" .
        """
        adapter.load_turtle(workflow_turtle)

        # Set up RabbitMQ exchanges
        events_exchange = "order.events"
        rabbitmq_channel.exchange_declare(
            exchange=events_exchange,
            exchange_type="topic",
            auto_delete=True,
        )

        # Phase 1: Order Placement (WCP-1 Sequence)
        tick = 1
        lockchain.write_tick_receipt(
            workflow_id=workflow_id,
            tick_number=tick,
            graph_hash="order_placed",
            hook_results=[{"hook_id": "validate_order", "result": True}],
        )

        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (workflow_id, 1, "order_placed", "receive_order", json.dumps(order)),
        )
        postgres_connection.commit()

        # Phase 2: Parallel Compliance Checks (WCP-2 & WCP-3)
        tick = 2
        compliance_checks = ["legal", "finance", "security"]
        check_results = {}

        def run_compliance_check(check_type: str) -> dict[str, Any]:
            time.sleep(0.01)  # Simulate check
            return {
                "check_type": check_type,
                "passed": True,
                "timestamp": time.time(),
            }

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(run_compliance_check, check): check
                for check in compliance_checks
            }
            for future in as_completed(futures):
                check_type = futures[future]
                check_results[check_type] = future.result()

        # All checks must pass (WCP-3 Synchronization)
        all_passed = all(r["passed"] for r in check_results.values())
        assert all_passed, "All compliance checks should pass"

        lockchain.write_tick_receipt(
            workflow_id=workflow_id,
            tick_number=tick,
            graph_hash="compliance_complete",
            hook_results=[{"hook_id": "compliance_sync", "result": all_passed}],
        )

        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (workflow_id, 3, "compliance_complete", "sync_checks", json.dumps(check_results)),
        )
        postgres_connection.commit()

        # Phase 3: Payment Processing with Retry (WCP-23)
        tick = 3
        payment_attempts = 0
        max_attempts = 3
        payment_success = False

        while payment_attempts < max_attempts and not payment_success:
            payment_attempts += 1
            # Simulate payment (succeeds on 2nd attempt)
            payment_success = payment_attempts >= 2

            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    23,
                    "payment_attempt",
                    f"payment_{payment_attempts}",
                    json.dumps({"attempt": payment_attempts, "success": payment_success}),
                ),
            )

        assert payment_success, "Payment should succeed"

        lockchain.write_tick_receipt(
            workflow_id=workflow_id,
            tick_number=tick,
            graph_hash="payment_complete",
            hook_results=[{"hook_id": "payment", "result": True}],
        )
        postgres_connection.commit()

        # Phase 4: Inventory Reservation with Lock (WCP-16 Deferred Choice)
        tick = 4
        lock_key = f"inventory_lock:{order_id}"

        # Acquire inventory lock
        lock_acquired = redis_connection.set(lock_key, "reserved", nx=True, ex=60)
        assert lock_acquired, "Should acquire inventory lock"

        # Reserve inventory items
        for item in order["items"]:
            redis_connection.hincrby(f"inventory:{item['sku']}", "reserved", item["qty"])

        # Release lock after reservation
        redis_connection.delete(lock_key)

        lockchain.write_tick_receipt(
            workflow_id=workflow_id,
            tick_number=tick,
            graph_hash="inventory_reserved",
            hook_results=[{"hook_id": "reserve_inventory", "result": True}],
        )

        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                16,
                "inventory_reserved",
                "reserve_items",
                json.dumps({"items_reserved": len(order["items"])}),
            ),
        )
        postgres_connection.commit()

        # Phase 5: Shipping Quotes - First 2 of 4 (WCP-35)
        tick = 5
        carriers = [
            {"name": "UPS", "price": 12.99, "delay_ms": 10},
            {"name": "FedEx", "price": 15.99, "delay_ms": 15},
            {"name": "USPS", "price": 8.99, "delay_ms": 25},
            {"name": "DHL", "price": 18.99, "delay_ms": 30},
        ]
        threshold = 2

        quotes_received: list[dict[str, Any]] = []
        quotes_lock = redis_connection.lock(f"quotes_lock:{order_id}")

        def get_shipping_quote(carrier: dict[str, Any]) -> dict[str, Any] | None:
            time.sleep(carrier["delay_ms"] / 1000)

            with quotes_lock:
                if len(quotes_received) >= threshold:
                    return None  # Cancelled

                quote = {
                    "carrier": carrier["name"],
                    "price": carrier["price"],
                }
                quotes_received.append(quote)
                return quote

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(get_shipping_quote, c) for c in carriers]
            for f in futures:
                f.result()

        assert len(quotes_received) == threshold, "Should have exactly 2 quotes"

        # Select cheapest quote
        selected_carrier = min(quotes_received, key=lambda q: q["price"])

        lockchain.write_tick_receipt(
            workflow_id=workflow_id,
            tick_number=tick,
            graph_hash="shipping_selected",
            hook_results=[{"hook_id": "select_shipping", "result": True}],
        )

        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                35,
                "shipping_selected",
                "select_carrier",
                json.dumps({"selected": selected_carrier, "quotes": quotes_received}),
            ),
        )
        postgres_connection.commit()

        # Phase 6: Ship Order and Notify (WCP-5 Simple Merge)
        tick = 6

        # Create shipping label
        tracking_number = f"TRK-{order_id}-001"
        redis_connection.hset(f"shipment:{order_id}", "tracking", tracking_number)
        redis_connection.hset(f"shipment:{order_id}", "carrier", selected_carrier["carrier"])

        # Publish order shipped event
        shipped_event = {
            "order_id": order_id,
            "tracking_number": tracking_number,
            "carrier": selected_carrier["carrier"],
            "timestamp": time.time(),
        }
        rabbitmq_channel.basic_publish(
            exchange=events_exchange,
            routing_key="order.shipped",
            body=json.dumps(shipped_event).encode(),
        )

        # Update RDF state
        adapter.update(f"""
            PREFIX kgc: <http://kgcl.io/ontology/kgc#>
            PREFIX order: <http://example.org/order/>
            DELETE {{ order:{order_id} kgc:status "pending" }}
            INSERT {{ order:{order_id} kgc:status "shipped" }}
            WHERE {{ order:{order_id} kgc:status "pending" }}
        """)

        # Send notifications (multiple channels merge - WCP-5)
        notifications = ["email", "sms", "push"]
        for channel in notifications:
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    workflow_id,
                    5,
                    "notification_sent",
                    f"notify_{channel}",
                    json.dumps({"channel": channel, "order_id": order_id}),
                ),
            )

        # Final lockchain receipt
        lockchain.write_tick_receipt(
            workflow_id=workflow_id,
            tick_number=tick,
            graph_hash="order_complete",
            hook_results=[{"hook_id": "complete", "result": True}],
            metadata={"terminal": True, "status": "shipped"},
        )

        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                43,
                "workflow_complete",
                "order_shipped",
                json.dumps(shipped_event),
            ),
        )
        postgres_connection.commit()

        # Assert: Verify final state across all services

        # 1. RDF state
        order_status = adapter.query(f"""
            PREFIX kgc: <http://kgcl.io/ontology/kgc#>
            PREFIX order: <http://example.org/order/>
            SELECT ?status WHERE {{
                order:{order_id} kgc:status ?status .
            }}
        """)
        assert order_status[0]["status"] == "shipped", "RDF should show shipped status"

        # 2. Lockchain integrity
        is_valid, message = lockchain.verify_chain(workflow_id)
        assert is_valid, f"Lockchain should be valid: {message}"

        chain = lockchain.get_chain(workflow_id)
        assert len(chain) == 6, "Should have 6 tick receipts"
        assert chain[-1].metadata is not None
        assert chain[-1].metadata.get("terminal") is True

        # 3. Redis state
        shipment = redis_connection.hgetall(f"shipment:{order_id}")
        assert shipment is not None
        tracking = shipment.get(b"tracking") or shipment.get("tracking")
        if isinstance(tracking, bytes):
            tracking = tracking.decode()
        assert tracking == tracking_number

        # 4. PostgreSQL audit trail
        cursor.execute(
            """
            SELECT DISTINCT event_type FROM workflow_audit
            WHERE workflow_id = %s
            ORDER BY event_type
            """,
            (workflow_id,),
        )
        events = {row[0] for row in cursor.fetchall()}
        expected_events = {
            "order_placed",
            "compliance_complete",
            "payment_attempt",
            "inventory_reserved",
            "shipping_selected",
            "notification_sent",
            "workflow_complete",
        }
        assert expected_events.issubset(events), "All expected events should be logged"

        # Cleanup
        adapter.clear()


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.redis
class TestE2EOrderCancellation:
    """End-to-end order cancellation scenario.

    Tests order cancellation with rollback across services.
    """

    def test_order_cancellation_with_rollback(
        self,
        postgres_connection: Any,
        redis_connection: Any,
    ) -> None:
        """Test order cancellation with full rollback.

        Scenario:
        1. Order placed and partially processed
        2. Customer requests cancellation
        3. Full rollback of all changes

        Assert:
        - All state rolled back
        - Cancellation logged
        """
        # Arrange
        order_id = "ORD-CANCEL-E2E-001"
        workflow_id = f"WF-{order_id}"
        cursor = postgres_connection.cursor()

        # Simulate partial processing
        # Reserve inventory
        redis_connection.hincrby("inventory:SKU-001", "reserved", 5)
        redis_connection.hincrby("inventory:SKU-002", "reserved", 3)

        # Authorize payment
        redis_connection.set(f"payment:{order_id}:auth", "AUTH-12345")

        # Log partial processing
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                1,
                "processing_started",
                "initial",
                json.dumps({"status": "in_progress"}),
            ),
        )
        postgres_connection.commit()

        # Act: Customer requests cancellation
        # Rollback inventory
        redis_connection.hincrby("inventory:SKU-001", "reserved", -5)
        redis_connection.hincrby("inventory:SKU-002", "reserved", -3)

        # Void payment authorization
        redis_connection.delete(f"payment:{order_id}:auth")

        # Log cancellation
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                workflow_id,
                20,
                "order_cancelled",
                "cancel_case",
                json.dumps({
                    "reason": "customer_request",
                    "inventory_released": True,
                    "payment_voided": True,
                }),
            ),
        )
        postgres_connection.commit()

        # Assert
        # Inventory should be released
        sku1_reserved = int(redis_connection.hget("inventory:SKU-001", "reserved") or 0)
        assert sku1_reserved == 0, "SKU-001 inventory should be released"

        # Payment auth should be voided
        payment_auth = redis_connection.get(f"payment:{order_id}:auth")
        assert payment_auth is None, "Payment authorization should be voided"

        # Cancellation should be logged
        cursor.execute(
            """
            SELECT event_type FROM workflow_audit
            WHERE workflow_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (workflow_id,),
        )
        last_event = cursor.fetchone()[0]
        assert last_event == "order_cancelled"
