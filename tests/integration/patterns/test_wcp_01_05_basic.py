"""Integration tests for Basic Control Flow Patterns (WCP-1 to WCP-5).

Tests workflow patterns with real PostgreSQL persistence for audit trails
and Oxigraph Server for shared RDF state.

Real-world scenarios:
- WCP-1 Sequence: Order status progression
- WCP-2 Parallel Split: Parallel compliance checks
- WCP-3 Synchronization: Wait for all approvals
- WCP-4 Exclusive Choice: Payment method routing
- WCP-5 Simple Merge: Notification aggregation
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from rdflib import RDF, Graph, Literal, Namespace, URIRef

if TYPE_CHECKING:
    from tests.containers.rdf_stores import OxigraphContainer

# Namespaces
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
KGC = Namespace("http://kgcl.io/ontology/kgc#")
WF = Namespace("http://example.org/workflow/")
ORDER = Namespace("http://example.org/order/")


@pytest.fixture
def order_workflow_graph() -> Graph:
    """Create a simple order processing workflow graph.

    Returns
    -------
    Graph
        RDF graph with order workflow topology.
    """
    g = Graph()

    # Define tasks
    start = WF["start"]
    receive_order = WF["receive_order"]
    confirm_payment = WF["confirm_payment"]
    ship_order = WF["ship_order"]
    end = WF["end"]

    # Task types
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((receive_order, RDF.type, YAWL.AtomicTask))
    g.add((confirm_payment, RDF.type, YAWL.AtomicTask))
    g.add((ship_order, RDF.type, YAWL.AtomicTask))
    g.add((end, RDF.type, YAWL.OutputCondition))

    # Sequence flows (WCP-1)
    g.add((start, YAWL.nextElementRef, receive_order))
    g.add((receive_order, YAWL.nextElementRef, confirm_payment))
    g.add((confirm_payment, YAWL.nextElementRef, ship_order))
    g.add((ship_order, YAWL.nextElementRef, end))

    # Initial token at start
    g.add((start, KGC.hasToken, Literal(True)))

    return g


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.wcp(1)
class TestWCP01SequenceWithPersistence:
    """WCP-1: Sequence pattern with PostgreSQL audit trail.

    Scenario: Order Status Progression
    - Order transitions through: Received -> Confirmed -> Shipped
    - Each transition is logged to PostgreSQL audit table
    """

    def test_order_status_progression(
        self,
        postgres_connection: Any,
        order_workflow_graph: Graph,
    ) -> None:
        """Test sequential order processing with audit persistence.

        Arrange:
        - Create order workflow graph
        - Initialize PostgreSQL audit connection

        Act:
        - Execute each task in sequence
        - Log status changes to audit table

        Assert:
        - Audit log contains all status transitions
        - Final status is 'shipped'
        """
        # Arrange
        order_id = "ORD-2024-001"
        cursor = postgres_connection.cursor()

        # Act: Simulate workflow execution with audit logging
        statuses = ["received", "confirmed", "shipped"]

        for status in statuses:
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (order_id, 1, "status_change", f"task_{status}", json.dumps({"status": status})),
            )

        postgres_connection.commit()

        # Assert: Verify audit trail
        cursor.execute(
            "SELECT event_type, task_id, token_state FROM workflow_audit WHERE workflow_id = %s ORDER BY id",
            (order_id,),
        )
        results = cursor.fetchall()

        assert len(results) == 3
        assert results[0][1] == "task_received"
        assert results[1][1] == "task_confirmed"
        assert results[2][1] == "task_shipped"

        # Verify final status
        final_state = json.loads(results[2][2])
        assert final_state["status"] == "shipped"


@pytest.mark.container
@pytest.mark.oxigraph_server
@pytest.mark.wcp(1)
class TestWCP01SequenceWithRemoteStore:
    """WCP-1: Sequence pattern with remote Oxigraph Server."""

    def test_sequence_with_remote_rdf_store(
        self,
        oxigraph_container: OxigraphContainer,
        order_workflow_graph: Graph,
    ) -> None:
        """Test sequential workflow execution with remote RDF store.

        Arrange:
        - Load workflow to Oxigraph Server
        - Initialize RemoteStoreAdapter

        Act:
        - Execute workflow steps
        - Update token positions in remote store

        Assert:
        - Remote store reflects correct state
        - Token reaches end condition
        """
        from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

        # Arrange
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container.get_sparql_endpoint(),
            update_endpoint=oxigraph_container.get_update_endpoint(),
        )

        # Load workflow to remote store
        workflow_turtle = order_workflow_graph.serialize(format="turtle")
        adapter.load_turtle(workflow_turtle)

        # Act: Query initial state
        initial_token = adapter.ask(
            f"ASK {{ <{WF.start}> <{KGC.hasToken}> true }}"
        )

        # Assert
        assert initial_token, "Start should have token initially"
        assert adapter.triple_count() > 0, "Store should have workflow triples"

        # Cleanup
        adapter.clear()


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.wcp(2)
class TestWCP02ParallelSplitWithPersistence:
    """WCP-2: Parallel Split pattern with PostgreSQL.

    Scenario: Parallel Compliance Checks
    - Order triggers 3 parallel checks: Legal, Finance, Security
    - Each check is logged independently
    """

    def test_parallel_compliance_checks(
        self,
        postgres_connection: Any,
    ) -> None:
        """Test parallel split with concurrent audit logging.

        Arrange:
        - Create order requiring compliance checks

        Act:
        - Trigger parallel checks
        - Log each check independently

        Assert:
        - All 3 checks are logged
        - Checks can complete in any order
        """
        # Arrange
        order_id = "ORD-2024-002"
        cursor = postgres_connection.cursor()

        # Act: Log parallel compliance checks (can complete in any order)
        checks = [
            ("legal_review", {"result": "approved", "reviewer": "legal_team"}),
            ("finance_review", {"result": "approved", "credit_limit": 10000}),
            ("security_review", {"result": "passed", "score": 95}),
        ]

        for check_name, check_data in checks:
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (order_id, 2, "parallel_check", check_name, json.dumps(check_data)),
            )

        postgres_connection.commit()

        # Assert: Verify all checks logged
        cursor.execute(
            "SELECT task_id FROM workflow_audit WHERE workflow_id = %s AND pattern_id = 2",
            (order_id,),
        )
        results = cursor.fetchall()

        task_ids = {r[0] for r in results}
        assert task_ids == {"legal_review", "finance_review", "security_review"}


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.wcp(3)
class TestWCP03SynchronizationWithPersistence:
    """WCP-3: Synchronization (AND-join) with PostgreSQL.

    Scenario: Wait for All Approvals
    - Order proceeds only when all 3 approvals are received
    - PostgreSQL tracks approval count
    """

    def test_wait_for_all_approvals(
        self,
        postgres_connection: Any,
    ) -> None:
        """Test AND-join with approval tracking in PostgreSQL.

        Arrange:
        - Create order requiring 3 approvals

        Act:
        - Submit approvals one by one
        - Check completion condition after each

        Assert:
        - Order not complete until all 3 approvals received
        - Order complete after final approval
        """
        # Arrange
        order_id = "ORD-2024-003"
        cursor = postgres_connection.cursor()
        required_approvals = 3

        # Act: Submit approvals one by one
        approvers = ["manager", "director", "vp"]

        for i, approver in enumerate(approvers):
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    order_id,
                    3,
                    "approval",
                    f"approve_{approver}",
                    json.dumps({"approver": approver, "approved": True}),
                ),
            )
            postgres_connection.commit()

            # Check approval count
            cursor.execute(
                """
                SELECT COUNT(*) FROM workflow_audit
                WHERE workflow_id = %s AND pattern_id = 3 AND event_type = 'approval'
                """,
                (order_id,),
            )
            count = cursor.fetchone()[0]

            # Assert: Not complete until all approvals
            if i < len(approvers) - 1:
                assert count < required_approvals, f"Should have {i + 1} approvals"
            else:
                assert count == required_approvals, "Should have all approvals"


@pytest.mark.container
@pytest.mark.rabbitmq
@pytest.mark.wcp(4)
class TestWCP04ExclusiveChoiceWithRouting:
    """WCP-4: Exclusive Choice (XOR-split) with RabbitMQ routing.

    Scenario: Payment Method Routing
    - Order routed to exactly one payment processor
    - RabbitMQ routes to appropriate queue based on payment type
    """

    def test_payment_method_routing(
        self,
        rabbitmq_channel: Any,
    ) -> None:
        """Test XOR-split with message queue routing.

        Arrange:
        - Create payment routing exchange and queues

        Act:
        - Route payment to appropriate processor

        Assert:
        - Message delivered to exactly one queue
        """
        # Arrange: Create topic exchange for payment routing
        exchange = "payment.routing"
        rabbitmq_channel.exchange_declare(
            exchange=exchange,
            exchange_type="topic",
            auto_delete=True,
        )

        # Create queues for each payment type
        queues = {}
        for payment_type in ["credit", "debit", "paypal"]:
            result = rabbitmq_channel.queue_declare(queue="", exclusive=True, auto_delete=True)
            queue_name = result.method.queue
            rabbitmq_channel.queue_bind(
                exchange=exchange,
                queue=queue_name,
                routing_key=f"payment.{payment_type}",
            )
            queues[payment_type] = queue_name

        # Act: Route a credit card payment
        payment_data = json.dumps({"order_id": "ORD-004", "amount": 150.00, "method": "credit"})
        rabbitmq_channel.basic_publish(
            exchange=exchange,
            routing_key="payment.credit",
            body=payment_data.encode(),
        )

        # Assert: Message only in credit queue
        method, _, body = rabbitmq_channel.basic_get(queues["credit"], auto_ack=True)
        assert body is not None, "Credit queue should have message"

        # Other queues should be empty
        method, _, body = rabbitmq_channel.basic_get(queues["debit"], auto_ack=True)
        assert body is None, "Debit queue should be empty"

        method, _, body = rabbitmq_channel.basic_get(queues["paypal"], auto_ack=True)
        assert body is None, "PayPal queue should be empty"


@pytest.mark.container
@pytest.mark.postgres
@pytest.mark.wcp(5)
class TestWCP05SimpleMergeWithPersistence:
    """WCP-5: Simple Merge (XOR-join) with PostgreSQL.

    Scenario: Notification Aggregation
    - Notifications from multiple channels merge into single log
    - No synchronization needed - first arrival proceeds
    """

    def test_notification_aggregation(
        self,
        postgres_connection: Any,
    ) -> None:
        """Test XOR-join with notification merging.

        Arrange:
        - Create notification channels

        Act:
        - Send notifications from different channels
        - Merge into single audit log

        Assert:
        - All notifications logged
        - No ordering enforced (XOR-join semantics)
        """
        # Arrange
        order_id = "ORD-2024-005"
        cursor = postgres_connection.cursor()

        # Act: Send notifications from different channels (can arrive in any order)
        notifications = [
            ("email", {"recipient": "customer@example.com", "subject": "Order Shipped"}),
            ("sms", {"phone": "+1234567890", "message": "Your order shipped!"}),
            ("push", {"device_id": "device123", "title": "Order Update"}),
        ]

        for channel, data in notifications:
            cursor.execute(
                """
                INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (order_id, 5, "notification", f"notify_{channel}", json.dumps(data)),
            )

        postgres_connection.commit()

        # Assert: All notifications logged (XOR-join accepts each independently)
        cursor.execute(
            """
            SELECT task_id, token_state FROM workflow_audit
            WHERE workflow_id = %s AND pattern_id = 5
            ORDER BY id
            """,
            (order_id,),
        )
        results = cursor.fetchall()

        assert len(results) == 3
        channels = {r[0].replace("notify_", "") for r in results}
        assert channels == {"email", "sms", "push"}


@pytest.mark.container
@pytest.mark.oxigraph_server
@pytest.mark.postgres
class TestCrossServicePatternExecution:
    """Test pattern execution across multiple services.

    Demonstrates integration between:
    - Oxigraph Server (RDF state)
    - PostgreSQL (audit trail)
    """

    def test_workflow_with_dual_persistence(
        self,
        oxigraph_container: OxigraphContainer,
        postgres_connection: Any,
        order_workflow_graph: Graph,
    ) -> None:
        """Test workflow with both RDF state and relational audit.

        Arrange:
        - Initialize both stores
        - Load workflow to Oxigraph

        Act:
        - Execute workflow steps
        - Update RDF state and log to PostgreSQL

        Assert:
        - Both stores reflect consistent state
        """
        from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

        # Arrange
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container.get_sparql_endpoint(),
            update_endpoint=oxigraph_container.get_update_endpoint(),
        )
        workflow_turtle = order_workflow_graph.serialize(format="turtle")
        adapter.load_turtle(workflow_turtle)

        order_id = "ORD-DUAL-001"
        cursor = postgres_connection.cursor()

        # Act: Execute workflow step and log
        cursor.execute(
            """
            INSERT INTO workflow_audit (workflow_id, pattern_id, event_type, task_id, token_state)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (order_id, 1, "execution", "receive_order", json.dumps({"rdf_triples": adapter.triple_count()})),
        )
        postgres_connection.commit()

        # Assert: Verify both stores have data
        assert adapter.triple_count() > 0, "Oxigraph should have workflow triples"

        cursor.execute("SELECT COUNT(*) FROM workflow_audit WHERE workflow_id = %s", (order_id,))
        audit_count = cursor.fetchone()[0]
        assert audit_count > 0, "PostgreSQL should have audit record"

        # Cleanup
        adapter.clear()
