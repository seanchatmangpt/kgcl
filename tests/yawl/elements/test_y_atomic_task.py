"""Tests for YAtomicTask - mirrors TestYAtomicTask.java.

Verifies atomic task creation, resourcing, bindings, and lifecycle.
"""

from __future__ import annotations

import pytest

from kgcl.yawl.elements.y_atomic_task import (
    ResourcingType,
    TaskType,
    YAtomicTask,
    YCompositeTask,
    YDataBinding,
    YMultipleInstanceTask,
    YResourcingSpec,
)
from kgcl.yawl.elements.y_task import JoinType, SplitType


class TestAtomicTaskCreation:
    """Tests for atomic task creation."""

    def test_create_atomic_task(self) -> None:
        """Create atomic task with ID."""
        task = YAtomicTask(id="TaskA")

        assert task.id == "TaskA"
        assert task.task_type == TaskType.ATOMIC
        assert task.join_type == JoinType.XOR
        assert task.split_type == SplitType.AND

    def test_create_task_with_name(self) -> None:
        """Create atomic task with name."""
        task = YAtomicTask(id="TaskA", name="Review Order")

        assert task.id == "TaskA"
        assert task.name == "Review Order"

    def test_default_resourcing(self) -> None:
        """Default resourcing is system task."""
        task = YAtomicTask(id="TaskA")

        assert task.resourcing is not None
        assert task.resourcing.offer_type == ResourcingType.OFFER
        assert task.resourcing.allocate_type == ResourcingType.ALLOCATE
        assert task.resourcing.start_type == ResourcingType.SYSTEM


class TestResourcingSpec:
    """Tests for resourcing specification."""

    def test_add_role(self) -> None:
        """Add role to resourcing."""
        spec = YResourcingSpec()
        spec.add_role("OrderClerk")
        spec.add_role("Manager")

        assert "OrderClerk" in spec.role_ids
        assert "Manager" in spec.role_ids
        assert len(spec.role_ids) == 2

    def test_add_participant(self) -> None:
        """Add participant to resourcing."""
        spec = YResourcingSpec()
        spec.add_participant("user-001")

        assert "user-001" in spec.participant_ids

    def test_is_system_task(self) -> None:
        """Check system task detection."""
        # Empty resourcing is system task
        spec = YResourcingSpec()
        assert spec.is_system_task()

        # With role, not system task
        spec.add_role("Clerk")
        assert not spec.is_system_task()

    def test_is_not_system_task_with_participant(self) -> None:
        """Task with participant is not system task."""
        spec = YResourcingSpec()
        spec.add_participant("user-001")

        assert not spec.is_system_task()


class TestDataBindings:
    """Tests for data bindings."""

    def test_create_input_binding(self) -> None:
        """Create input data binding."""
        binding = YDataBinding(name="orderId", expression="case_data.order_id", target="orderIdentifier", is_input=True)

        assert binding.name == "orderId"
        assert binding.expression == "case_data.order_id"
        assert binding.target == "orderIdentifier"
        assert binding.is_input is True

    def test_create_output_binding(self) -> None:
        """Create output data binding."""
        binding = YDataBinding(name="result", expression="task_result", target="approvalStatus", is_input=False)

        assert binding.is_input is False

    def test_add_input_binding_to_task(self) -> None:
        """Add input binding to task."""
        task = YAtomicTask(id="TaskA")
        binding = YDataBinding(name="input1", expression="expr", target="target")

        task.add_input_binding(binding)

        assert "input1" in task.input_bindings
        assert task.input_bindings["input1"] == binding

    def test_add_output_binding_to_task(self) -> None:
        """Add output binding to task."""
        task = YAtomicTask(id="TaskA")
        binding = YDataBinding(name="output1", expression="expr", target="target", is_input=False)

        task.add_output_binding(binding)

        assert "output1" in task.output_bindings


class TestTaskTypes:
    """Tests for task type detection."""

    def test_is_manual_task(self) -> None:
        """Manual task requires human work."""
        task = YAtomicTask(id="TaskA")
        task.resourcing.add_role("Clerk")

        assert task.is_manual_task()
        assert not task.is_automated_task()

    def test_is_automated_task(self) -> None:
        """Automated task has codelet."""
        task = YAtomicTask(id="TaskA")
        task.codelet = "org.yawl.CodeletImplementation"

        assert task.is_automated_task()
        assert not task.is_manual_task()

    def test_system_task_not_manual(self) -> None:
        """System task (no resources, no codelet) is not manual."""
        task = YAtomicTask(id="TaskA")

        # System task (empty resourcing, no codelet)
        assert not task.is_manual_task()  # is_manual_task checks for resources


class TestTimerSupport:
    """Tests for timer configuration."""

    def test_has_timer(self) -> None:
        """Check timer detection."""
        task = YAtomicTask(id="TaskA")

        assert not task.has_timer()

        task.timer_expression = "PT1H"
        assert task.has_timer()

    def test_timer_trigger(self) -> None:
        """Timer trigger configuration."""
        task = YAtomicTask(id="TaskA")
        task.timer_expression = "PT2H"
        task.timer_trigger = "OnStarted"

        assert task.timer_trigger == "OnStarted"


class TestSkipCapability:
    """Tests for skip capability."""

    def test_can_skip_default(self) -> None:
        """Skip disabled by default."""
        task = YAtomicTask(id="TaskA")

        assert not task.can_skip()

    def test_enable_skip(self) -> None:
        """Enable task skipping."""
        task = YAtomicTask(id="TaskA")
        task.enable_skipper = True
        task.skip_expression = "order_total < 100"

        assert task.can_skip()
        assert task.skip_expression == "order_total < 100"


class TestCompositeTask:
    """Tests for composite tasks."""

    def test_create_composite_task(self) -> None:
        """Create composite task with subnet."""
        task = YCompositeTask(id="ProcessOrder", subnet_id="OrderSubnet")

        assert task.id == "ProcessOrder"
        assert task.task_type == TaskType.COMPOSITE
        assert task.subnet_id == "OrderSubnet"
        assert task.decomposition_id == "OrderSubnet"

    def test_has_subnet(self) -> None:
        """Check subnet detection."""
        task = YCompositeTask(id="Task")

        assert not task.has_subnet()

        task.subnet_id = "SubNet"
        assert task.has_subnet()

    def test_composite_task_bindings(self) -> None:
        """Composite task can have bindings."""
        task = YCompositeTask(id="Task", subnet_id="Net")
        binding = YDataBinding(name="data", expression="expr", target="target")

        task.add_input_binding(binding)

        assert "data" in task.input_bindings


class TestMultipleInstanceTask:
    """Tests for multiple instance tasks - mirrors TestYMultiInstanceAttributes.java."""

    def test_create_mi_task(self) -> None:
        """Create multiple instance task."""
        task = YMultipleInstanceTask(id="ReviewItems", mi_minimum=1, mi_maximum=10, mi_threshold=5)

        assert task.id == "ReviewItems"
        assert task.task_type == TaskType.MULTIPLE_ATOMIC
        assert task.mi_minimum == 1
        assert task.mi_maximum == 10
        assert task.mi_threshold == 5

    def test_default_mi_values(self) -> None:
        """Default MI values."""
        task = YMultipleInstanceTask(id="Task")

        assert task.mi_minimum == 1
        assert task.mi_maximum == 1
        assert task.mi_threshold == 1
        assert task.mi_creation_mode == "static"

    def test_is_static_creation(self) -> None:
        """Check static creation mode."""
        task = YMultipleInstanceTask(id="Task")

        assert task.is_static_creation()
        assert not task.is_dynamic_creation()

    def test_is_dynamic_creation(self) -> None:
        """Check dynamic creation mode."""
        task = YMultipleInstanceTask(id="Task", mi_creation_mode="dynamic")

        assert task.is_dynamic_creation()
        assert not task.is_static_creation()

    def test_get_completion_threshold(self) -> None:
        """Get completion threshold."""
        task = YMultipleInstanceTask(id="Task", mi_threshold=3)

        assert task.get_completion_threshold() == 3

    def test_mi_query_expression(self) -> None:
        """MI query expression for instance generation."""
        task = YMultipleInstanceTask(id="Task", mi_query="/order/items/item", mi_unique_input_expression="./item_id")

        assert task.mi_query == "/order/items/item"
        assert task.mi_unique_input_expression == "./item_id"

    def test_mi_input_joiner(self) -> None:
        """MI input joiner expression."""
        task = YMultipleInstanceTask(id="Task", mi_input_joiner="concat_items")

        assert task.mi_input_joiner == "concat_items"

    def test_mi_output_query(self) -> None:
        """MI output query for aggregation."""
        task = YMultipleInstanceTask(id="Task", mi_output_query="/results/result")

        assert task.mi_output_query == "/results/result"


class TestTaskJoinSplitTypes:
    """Tests for join and split type configuration."""

    def test_and_join(self) -> None:
        """Configure AND-join."""
        task = YAtomicTask(id="Task", join_type=JoinType.AND)

        assert task.join_type == JoinType.AND

    def test_xor_join(self) -> None:
        """Configure XOR-join."""
        task = YAtomicTask(id="Task", join_type=JoinType.XOR)

        assert task.join_type == JoinType.XOR

    def test_or_join(self) -> None:
        """Configure OR-join."""
        task = YAtomicTask(id="Task", join_type=JoinType.OR)

        assert task.join_type == JoinType.OR

    def test_and_split(self) -> None:
        """Configure AND-split."""
        task = YAtomicTask(id="Task", split_type=SplitType.AND)

        assert task.split_type == SplitType.AND

    def test_xor_split(self) -> None:
        """Configure XOR-split."""
        task = YAtomicTask(id="Task", split_type=SplitType.XOR)

        assert task.split_type == SplitType.XOR

    def test_or_split(self) -> None:
        """Configure OR-split."""
        task = YAtomicTask(id="Task", split_type=SplitType.OR)

        assert task.split_type == SplitType.OR


class TestCustomForm:
    """Tests for custom form URL."""

    def test_custom_form_url(self) -> None:
        """Set custom form URL."""
        task = YAtomicTask(id="Task")
        task.custom_form_url = "http://forms.example.com/order-review"

        assert task.custom_form_url == "http://forms.example.com/order-review"

    def test_no_custom_form(self) -> None:
        """Default has no custom form."""
        task = YAtomicTask(id="Task")

        assert task.custom_form_url is None
