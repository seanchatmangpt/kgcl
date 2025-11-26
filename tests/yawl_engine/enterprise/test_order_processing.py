"""Enterprise Order Processing Tests - Jobs-To-Be-Done using YAWL Patterns.

This test suite validates realistic enterprise order processing workflows using
multiple instance patterns, data patterns, and cancellation/compensation patterns.

**ENTERPRISE JTBD COVERAGE:**
1. Batch Order Processing (Pattern 13 - MI Design-Time)
2. Dynamic Order Line Items (Pattern 14 - MI Runtime)
3. Streaming Order Processing (Pattern 15 - MI Dynamic)
4. Order with Compensation (Pattern 19-20 + Cancellation)
5. Order Splitting by Warehouse (Pattern 12 - MI No Sync)
6. Order Status Tracking (Pattern 28-30 - Data Visibility)

**TEST PHILOSOPHY:**
- Chicago School TDD - tests drive behavior with real RDF graphs
- No mocking of domain objects (Order, Receipt, etc.)
- Observable state verification (not just assert success)
- Full end-to-end scenarios reflecting production workflows

References
----------
YAWL Patterns: http://www.workflowpatterns.com/
Enterprise Integration Patterns: https://www.enterpriseintegrationpatterns.com/
"""

# Magic values OK in tests

from __future__ import annotations

from typing import Any, cast

import pytest
from rdflib import Dataset, Graph, Literal, Namespace, URIRef

from kgcl.yawl_engine.patterns.cancellation import CancelCase, CancelTask
from kgcl.yawl_engine.patterns.data_patterns import DataContext, DataInteractionTaskToTask
from kgcl.yawl_engine.patterns.multiple_instance import (
    MIDesignTime,
    MIDynamic,
    MIRunTimeKnown,
    MIState,
    MIWithoutSync,
    check_completion,
    mark_instance_complete,
)

# RDF namespaces
# NOTE: Two YAWL namespaces due to different source modules
YAWL_MI = Namespace("http://www.yawlsystem.com/yawl/elements/")  # multiple_instance.py
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")  # cancellation.py
EX = Namespace("http://example.org/enterprise/")
ORDER = Namespace("http://bitflow.ai/ontology/order/v1#")


@pytest.fixture
def order_graph() -> Graph:
    """Create RDF graph for order processing workflows."""
    return Graph()


@pytest.fixture
def order_dataset() -> Dataset:
    """Create RDF dataset for cancellation patterns."""
    return Dataset()


@pytest.fixture
def data_context() -> DataContext:
    """Create unified data context for order processing."""
    return DataContext()


# ============================================================================
# JTBD 1: Batch Order Processing (Pattern 13 - MI Design-Time)
# ============================================================================


class TestBatchOrderProcessing:
    """Pattern 13: Process exactly 100 orders per batch, wait for all to complete."""

    def test_batch_processing_exact_count(self, order_graph: Graph) -> None:
        """Batch processes exactly 100 orders (design-time known)."""
        # JTBD: Process 100 orders per batch (compliance requirement)
        process_order_task = EX.processOrder
        batch_pattern = MIDesignTime(instance_count=100)

        result = batch_pattern.execute(order_graph, process_order_task, context={})

        assert result.success
        assert len(result.instance_ids) == 100
        assert result.metadata["instance_count"] == 100
        assert result.metadata["requires_sync"] is True

        # Verify all instances in graph
        instances = list(order_graph.subjects(YAWL_MI.instanceOf, process_order_task))
        assert len(instances) == 100

    def test_batch_synchronization_barrier(self, order_graph: Graph) -> None:
        """Batch waits for all 100 orders to complete before report generation."""
        process_order_task = EX.processBatchOrder
        batch_pattern = MIDesignTime(instance_count=100)

        result = batch_pattern.execute(order_graph, process_order_task, context={})
        parent_id = result.metadata["parent_id"]
        parent_uri = URIRef(parent_id)

        # Verify synchronization barrier
        required = list(order_graph.objects(parent_uri, YAWL_MI.requiredInstances))
        completed = list(order_graph.objects(parent_uri, YAWL_MI.completedInstances))

        assert len(required) == 1
        assert int(cast(Literal, required[0]).value) == 100
        assert len(completed) == 1
        assert int(cast(Literal, completed[0]).value) == 0

        # Complete all 100 orders
        for instance_id in result.instance_ids:
            mark_instance_complete(order_graph, instance_id)

        # Verify batch completion
        assert check_completion(order_graph, parent_id)

    def test_batch_report_generation_after_completion(self, order_graph: Graph, data_context: DataContext) -> None:
        """Batch report is generated only after all 100 orders complete."""
        process_order_task = EX.processBatchOrder
        generate_report_task = EX.generateBatchReport
        batch_pattern = MIDesignTime(instance_count=100)

        # Process batch
        result = batch_pattern.execute(order_graph, process_order_task, context={})
        parent_id = result.metadata["parent_id"]

        # Track completion in workflow data
        data_context.workflow_data.set("batch_completed", False)

        # Complete first 99 orders
        for instance_id in result.instance_ids[:99]:
            mark_instance_complete(order_graph, instance_id)

        # Batch not complete yet
        assert not check_completion(order_graph, parent_id)
        assert data_context.workflow_data.get("batch_completed") is False

        # Complete final order
        mark_instance_complete(order_graph, result.instance_ids[99])

        # Batch complete → trigger report generation
        assert check_completion(order_graph, parent_id)
        data_context.workflow_data.set("batch_completed", True)

        # Simulate report generation
        data_context.task_data.set(generate_report_task, "report_id", "BATCH_REPORT_001")
        data_context.task_data.set(generate_report_task, "total_orders", len(result.instance_ids))

        assert data_context.task_data.get(generate_report_task, "total_orders") == 100
        assert data_context.task_data.get(generate_report_task, "report_id") == "BATCH_REPORT_001"


# ============================================================================
# JTBD 2: Dynamic Order Line Items (Pattern 14 - MI Runtime)
# ============================================================================


class TestDynamicOrderLineItems:
    """Pattern 14: Process N line items per order (runtime variable)."""

    def test_runtime_line_item_count(self, order_graph: Graph) -> None:
        """Order has N line items determined at runtime."""
        process_line_item_task = EX.processLineItem

        # Order A: 5 line items
        order_a_pattern = MIRunTimeKnown(instance_count_variable="line_item_count")
        result_a = order_a_pattern.execute(order_graph, process_line_item_task, context={"line_item_count": 5})

        assert result_a.success
        assert len(result_a.instance_ids) == 5

        # Order B: 12 line items
        result_b = order_a_pattern.execute(order_graph, process_line_item_task, context={"line_item_count": 12})

        assert result_b.success
        assert len(result_b.instance_ids) == 12

    def test_line_item_parallel_processing(self, order_graph: Graph) -> None:
        """All line items in an order are processed in parallel."""
        process_line_item_task = EX.processLineItem
        pattern = MIRunTimeKnown(instance_count_variable="item_count")

        result = pattern.execute(order_graph, process_line_item_task, context={"item_count": 8})

        assert result.success
        assert len(result.instance_ids) == 8

        # Verify all instances are RUNNING (parallel execution)
        for instance_id in result.instance_ids:
            instance_uri = URIRef(instance_id)
            state_values = list(order_graph.objects(instance_uri, YAWL_MI.state))
            assert len(state_values) == 1
            assert str(state_values[0]) == MIState.RUNNING.value

    def test_line_item_aggregation_after_completion(self, order_graph: Graph, data_context: DataContext) -> None:
        """Order total is aggregated after all line items complete."""
        process_line_item_task = EX.processLineItem
        calculate_total_task = EX.calculateOrderTotal
        pattern = MIRunTimeKnown(instance_count_variable="item_count")

        # Process 4 line items
        line_item_prices = [100.0, 250.0, 75.0, 150.0]
        result = pattern.execute(order_graph, process_line_item_task, context={"item_count": len(line_item_prices)})

        parent_id = result.metadata["parent_id"]

        # Simulate line item processing with prices
        for i, instance_id in enumerate(result.instance_ids):
            data_context.task_data.set(URIRef(instance_id), "item_price", line_item_prices[i])
            mark_instance_complete(order_graph, instance_id)

        # All line items complete
        assert check_completion(order_graph, parent_id)

        # Aggregate total
        total = sum(line_item_prices)
        data_context.task_data.set(calculate_total_task, "order_total", total)

        assert data_context.task_data.get(calculate_total_task, "order_total") == 575.0


# ============================================================================
# JTBD 3: Streaming Order Processing (Pattern 15 - MI Dynamic)
# ============================================================================


class TestStreamingOrderProcessing:
    """Pattern 15: Process orders as they arrive (no synchronization)."""

    def test_streaming_no_synchronization(self, order_graph: Graph) -> None:
        """Orders processed as they arrive without waiting for batch."""
        process_order_task = EX.processStreamingOrder
        pattern = MIDynamic(spawn_condition="order_received", termination_condition="queue_empty")

        # Simulate 6 orders arriving
        order_stream = ["ORD-001", "ORD-002", "ORD-003", "ORD-004", "ORD-005", "ORD-006"]
        result = pattern.execute(order_graph, process_order_task, context={"events": order_stream})

        assert result.success
        assert len(result.instance_ids) == 6
        assert result.metadata["requires_sync"] is False  # No synchronization!

        # Verify each instance has trigger event
        for instance_id in result.instance_ids:
            instance_uri = URIRef(instance_id)
            trigger_events = list(order_graph.objects(instance_uri, YAWL_MI.triggerEvent))
            assert len(trigger_events) == 1
            assert str(trigger_events[0]) in order_stream

    def test_streaming_continuous_arrival(self, order_graph: Graph) -> None:
        """New orders can arrive and spawn instances dynamically."""
        process_order_task = EX.processStreamingOrder
        pattern = MIDynamic(spawn_condition="order_received")

        # First batch: 3 orders
        result1 = pattern.execute(
            order_graph, process_order_task, context={"events": ["ORD-001", "ORD-002", "ORD-003"]}
        )

        assert len(result1.instance_ids) == 3

        # Second batch: 2 more orders arrive
        result2 = pattern.execute(order_graph, process_order_task, context={"events": ["ORD-004", "ORD-005"]})

        assert len(result2.instance_ids) == 2

        # Total instances in graph
        all_instances = list(order_graph.subjects(YAWL_MI.instanceOf, process_order_task))
        assert len(all_instances) == 5

    def test_streaming_empty_queue(self, order_graph: Graph) -> None:
        """Empty order queue results in zero instances."""
        process_order_task = EX.processStreamingOrder
        pattern = MIDynamic(spawn_condition="order_received")

        result = pattern.execute(order_graph, process_order_task, context={})

        assert result.success
        assert len(result.instance_ids) == 0


# ============================================================================
# JTBD 4: Order with Compensation (Pattern 19-20 + Cancellation)
# ============================================================================


class TestOrderCompensation:
    """Order compensation using cancellation patterns."""

    def test_payment_failure_rollback_inventory(self, order_dataset: Dataset) -> None:
        """Payment fails → Rollback inventory reservation."""
        reserve_inventory_task = EX.reserveInventory
        process_payment_task = EX.processPayment

        # Reserve inventory (succeeds)
        order_dataset.add((reserve_inventory_task, YAWL.status, Literal("completed")))
        order_dataset.add((reserve_inventory_task, ORDER.reservedQuantity, Literal(10)))

        # Process payment (fails)
        order_dataset.add((process_payment_task, YAWL.status, Literal("failed")))

        # Compensation: Cancel reservation
        cancel = CancelTask()
        result = cancel.cancel(order_dataset, reserve_inventory_task, "Payment failed - rollback inventory")

        assert result.success
        assert str(reserve_inventory_task) in result.cancelled_tasks

        # Verify reservation is cancelled
        cancelled_status = list(order_dataset.triples((reserve_inventory_task, YAWL.status, Literal("cancelled"))))
        assert len(cancelled_status) == 1

    def test_shipping_failure_refund_payment(self, order_graph: Graph, data_context: DataContext) -> None:
        """Shipping fails → Refund payment."""
        process_payment_task = EX.processPayment
        ship_order_task = EX.shipOrder
        refund_payment_task = EX.refundPayment

        # Payment completed
        data_context.task_data.set(process_payment_task, "transaction_id", "TXN-12345")
        data_context.task_data.set(process_payment_task, "amount", 500.0)
        order_graph.add((process_payment_task, YAWL.status, Literal("completed")))

        # Shipping fails
        order_graph.add((ship_order_task, YAWL.status, Literal("failed")))

        # Compensation: Refund payment
        transaction_id = data_context.task_data.get(process_payment_task, "transaction_id")
        refund_amount = data_context.task_data.get(process_payment_task, "amount")

        data_context.task_data.set(refund_payment_task, "refund_txn_id", transaction_id)
        data_context.task_data.set(refund_payment_task, "refund_amount", refund_amount)

        assert data_context.task_data.get(refund_payment_task, "refund_txn_id") == "TXN-12345"
        assert data_context.task_data.get(refund_payment_task, "refund_amount") == 500.0

    def test_cancel_entire_order_on_critical_failure(self, order_dataset: Dataset) -> None:
        """Critical failure cancels entire order workflow."""
        order_workflow = EX.orderWorkflow_W123
        task1 = EX.validateOrder
        task2 = EX.reserveInventory
        task3 = EX.processPayment

        # Setup workflow with 3 active tasks
        order_dataset.add((order_workflow, YAWL.hasTask, task1))
        order_dataset.add((order_workflow, YAWL.hasTask, task2))
        order_dataset.add((order_workflow, YAWL.hasTask, task3))
        order_dataset.add((task1, YAWL.status, Literal("active")))
        order_dataset.add((task2, YAWL.status, Literal("active")))
        order_dataset.add((task3, YAWL.status, Literal("active")))

        # Critical fraud detected → cancel entire order
        cancel = CancelCase()
        result = cancel.cancel(order_dataset, order_workflow, "Fraud detected")

        assert result.success
        assert len(result.cancelled_tasks) == 3

        # Verify workflow aborted
        aborted = list(order_dataset.triples((order_workflow, YAWL.status, Literal("aborted"))))
        assert len(aborted) == 1


# ============================================================================
# JTBD 5: Order Splitting by Warehouse (Pattern 12 - MI No Sync)
# ============================================================================


class TestOrderSplitting:
    """Pattern 12: Split order by warehouse (fire-and-forget)."""

    def test_split_order_by_warehouse(self, order_graph: Graph) -> None:
        """Order split into 3 warehouses, each fulfills independently."""
        fulfill_order_task = EX.fulfillOrder
        pattern = MIWithoutSync()

        # Split order across 3 warehouses (no synchronization needed)
        result = pattern.execute(order_graph, fulfill_order_task, context={"count": 3})

        assert result.success
        assert len(result.instance_ids) == 3
        assert result.metadata["sync"] is False

        # Each warehouse instance is independent
        for i, instance_id in enumerate(result.instance_ids):
            instance_uri = URIRef(instance_id)
            instance_numbers = list(order_graph.objects(instance_uri, YAWL_MI.instanceNumber))
            assert len(instance_numbers) == 1
            assert int(cast(Literal, instance_numbers[0]).value) == i

    def test_split_order_fire_and_forget(self, order_graph: Graph) -> None:
        """Fire-and-forget: No waiting for warehouse fulfillment."""
        fulfill_order_task = EX.fulfillOrder
        pattern = MIWithoutSync()

        result = pattern.execute(order_graph, fulfill_order_task, context={"count": 5})

        assert result.success
        assert len(result.instance_ids) == 5

        # Verify no synchronization barrier (no parent MI)
        for instance_id in result.instance_ids:
            instance_uri = URIRef(instance_id)
            parent_refs = list(order_graph.objects(instance_uri, YAWL_MI.parentMI))
            assert len(parent_refs) == 0  # No parent = no sync


# ============================================================================
# JTBD 6: Order Status Tracking (Pattern 28-30 - Data Visibility)
# ============================================================================


class TestOrderStatusTracking:
    """Multi-level order status tracking using data patterns."""

    def test_task_level_status(self, data_context: DataContext) -> None:
        """Pattern 28: Task-level status (item processing)."""
        process_item_task = URIRef("urn:task:processItem_I1")

        # Task-local status
        data_context.task_data.set(process_item_task, "status", "PROCESSING")
        data_context.task_data.set(process_item_task, "progress_percent", 45)

        assert data_context.task_data.get(process_item_task, "status") == "PROCESSING"
        assert data_context.task_data.get(process_item_task, "progress_percent") == 45

        # Other tasks don't see this data
        other_task = URIRef("urn:task:processItem_I2")
        assert data_context.task_data.get(other_task, "status") is None

    def test_case_level_status(self, data_context: DataContext) -> None:
        """Pattern 30: Case-level status (order-level)."""
        order_case_id = "ORDER-12345"

        # Order-level status visible to all tasks in order
        data_context.case_data.set(order_case_id, "order_status", "IN_PROGRESS")
        data_context.case_data.set(order_case_id, "customer_id", "CUST-999")
        data_context.case_data.set(order_case_id, "total_amount", 1200.0)

        assert data_context.case_data.get(order_case_id, "order_status") == "IN_PROGRESS"
        assert data_context.case_data.get(order_case_id, "customer_id") == "CUST-999"

        # Other orders don't see this data
        other_order_id = "ORDER-67890"
        assert data_context.case_data.get(other_order_id, "order_status") is None

    def test_workflow_level_status(self, data_context: DataContext) -> None:
        """Pattern 31: Workflow-level status (daily totals)."""
        # Global counters across all orders
        data_context.workflow_data.set("daily_order_count", 0)
        data_context.workflow_data.set("daily_revenue", 0.0)

        # Process 5 orders
        for i in range(5):
            order_amount = (i + 1) * 100.0
            data_context.workflow_data.increment("daily_order_count", 1)
            current_revenue = data_context.workflow_data.get("daily_revenue") or 0.0
            data_context.workflow_data.set("daily_revenue", current_revenue + order_amount)

        assert data_context.workflow_data.get("daily_order_count") == 5
        assert data_context.workflow_data.get("daily_revenue") == 1500.0

    def test_status_propagation_task_to_case(self, order_graph: Graph, data_context: DataContext) -> None:
        """Status propagates from task level to case level."""
        process_payment_task = EX.processPayment
        update_order_status_task = EX.updateOrderStatus
        order_case_id = "ORDER-54321"

        # Task completes payment
        data_context.task_data.set(process_payment_task, "payment_status", "COMPLETED")
        data_context.task_data.set(process_payment_task, "transaction_id", "TXN-999")

        # Transfer data from task to case
        interaction = DataInteractionTaskToTask(
            source_task=str(process_payment_task),
            target_task=str(update_order_status_task),
            mappings={"payment_status": "order_payment_status"},
        )

        source_context: dict[str, Any] = {
            "payment_status": data_context.task_data.get(process_payment_task, "payment_status")
        }
        target_context = interaction.transfer(order_graph, source_context)

        # Update case-level status
        data_context.case_data.set(order_case_id, "payment_status", target_context["order_payment_status"])

        assert data_context.case_data.get(order_case_id, "payment_status") == "COMPLETED"


# ============================================================================
# INTEGRATION SCENARIOS - Complete Order Workflows
# ============================================================================


class TestCompleteOrderWorkflows:
    """End-to-end order processing scenarios combining multiple patterns."""

    def test_complete_order_lifecycle(self, order_graph: Graph, data_context: DataContext) -> None:
        """Complete order: Runtime line items → Case status → Workflow totals."""
        order_case_id = "ORDER-COMPLETE-001"
        process_line_item_task = EX.processLineItem

        # Initialize case data
        data_context.case_data.set(order_case_id, "order_status", "PROCESSING")
        data_context.case_data.set(order_case_id, "customer_id", "CUST-123")

        # Dynamic line items (3 items)
        line_item_pattern = MIRunTimeKnown(instance_count_variable="item_count")
        result = line_item_pattern.execute(order_graph, process_line_item_task, context={"item_count": 3})

        assert result.success
        parent_id = result.metadata["parent_id"]

        # Process line items
        line_item_prices = [200.0, 350.0, 150.0]
        for i, instance_id in enumerate(result.instance_ids):
            data_context.task_data.set(URIRef(instance_id), "item_price", line_item_prices[i])
            mark_instance_complete(order_graph, instance_id)

        # All items complete
        assert check_completion(order_graph, parent_id)

        # Update case status
        order_total = sum(line_item_prices)
        data_context.case_data.set(order_case_id, "order_total", order_total)
        data_context.case_data.set(order_case_id, "order_status", "COMPLETED")

        # Update workflow totals
        data_context.workflow_data.increment("total_orders_today", 1)
        current_revenue = data_context.workflow_data.get("total_revenue_today") or 0.0
        data_context.workflow_data.set("total_revenue_today", current_revenue + order_total)

        # Verify end state
        assert data_context.case_data.get(order_case_id, "order_status") == "COMPLETED"
        assert data_context.case_data.get(order_case_id, "order_total") == 700.0
        assert data_context.workflow_data.get("total_orders_today") == 1
        assert data_context.workflow_data.get("total_revenue_today") == 700.0

    def test_batch_with_failed_orders(self, order_graph: Graph, data_context: DataContext) -> None:
        """Batch of 10 orders: 8 succeed, 2 fail with compensation."""
        process_order_task = EX.processBatchOrder
        batch_pattern = MIDesignTime(instance_count=10)

        result = batch_pattern.execute(order_graph, process_order_task, context={})
        parent_id = result.metadata["parent_id"]

        # Complete first 8 successfully
        for instance_id in result.instance_ids[:8]:
            data_context.task_data.set(URIRef(instance_id), "status", "SUCCESS")
            mark_instance_complete(order_graph, instance_id)

        # Orders 9 and 10 fail
        failed_order_9 = result.instance_ids[8]
        failed_order_10 = result.instance_ids[9]

        cancel = CancelTask()
        cancel.cancel(order_graph, URIRef(failed_order_9), "Payment declined")
        cancel.cancel(order_graph, URIRef(failed_order_10), "Inventory unavailable")

        # Mark failures as "complete" for synchronization
        mark_instance_complete(order_graph, failed_order_9)
        mark_instance_complete(order_graph, failed_order_10)

        # Batch completes (including failures)
        assert check_completion(order_graph, parent_id)

        # Report generation includes success/failure stats
        data_context.workflow_data.set("batch_success_count", 8)
        data_context.workflow_data.set("batch_failure_count", 2)

        assert data_context.workflow_data.get("batch_success_count") == 8
        assert data_context.workflow_data.get("batch_failure_count") == 2
