"""Tests for YNet (workflow net) - mirrors TestYNet.java.

Verifies net structure, validation, flows, and element management.
"""

from __future__ import annotations

import pytest

from kgcl.yawl.elements.y_condition import ConditionType, YCondition
from kgcl.yawl.elements.y_flow import YFlow
from kgcl.yawl.elements.y_net import YNet
from kgcl.yawl.elements.y_task import JoinType, SplitType, YTask


class TestNetCreation:
    """Tests for net creation and initialization."""

    def test_create_empty_net(self) -> None:
        """Create net with just ID."""
        net = YNet(id="test-net")

        assert net.id == "test-net"
        assert net.name == ""
        assert net.input_condition is None
        assert net.output_condition is None
        assert len(net.conditions) == 0
        assert len(net.tasks) == 0
        assert len(net.flows) == 0

    def test_create_net_with_name(self) -> None:
        """Create net with ID and name."""
        net = YNet(id="net-001", name="Order Processing")

        assert net.id == "net-001"
        assert net.name == "Order Processing"

    def test_net_hash_and_equality(self) -> None:
        """Net identity based on ID."""
        n1 = YNet(id="same")
        n2 = YNet(id="same")
        n3 = YNet(id="different")

        assert n1 == n2
        assert n1 != n3
        assert hash(n1) == hash(n2)

        # Can use in set
        net_set = {n1, n2, n3}
        assert len(net_set) == 2


class TestConditionManagement:
    """Tests for adding and managing conditions."""

    def test_add_condition(self) -> None:
        """Add condition to net."""
        net = YNet(id="test")
        cond = YCondition(id="c1", name="Condition 1")

        net.add_condition(cond)

        assert "c1" in net.conditions
        assert net.conditions["c1"] == cond
        assert cond.net_id == "test"

    def test_add_input_condition(self) -> None:
        """Add input condition auto-sets input_condition."""
        net = YNet(id="test")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)

        net.add_condition(start)

        assert net.input_condition == start
        assert "start" in net.conditions

    def test_add_output_condition(self) -> None:
        """Add output condition auto-sets output_condition."""
        net = YNet(id="test")
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        net.add_condition(end)

        assert net.output_condition == end
        assert "end" in net.conditions

    def test_get_condition_count(self) -> None:
        """Count conditions in net."""
        net = YNet(id="test")
        net.add_condition(YCondition(id="c1"))
        net.add_condition(YCondition(id="c2"))
        net.add_condition(YCondition(id="c3"))

        assert net.get_condition_count() == 3


class TestTaskManagement:
    """Tests for adding and managing tasks."""

    def test_add_task(self) -> None:
        """Add task to net."""
        net = YNet(id="test")
        task = YTask(id="A", name="Task A")

        net.add_task(task)

        assert "A" in net.tasks
        assert net.tasks["A"] == task
        assert task.net_id == "test"

    def test_add_multiple_tasks(self) -> None:
        """Add multiple tasks."""
        net = YNet(id="test")
        net.add_task(YTask(id="A"))
        net.add_task(YTask(id="B"))
        net.add_task(YTask(id="C"))

        assert net.get_task_count() == 3
        assert "A" in net.tasks
        assert "B" in net.tasks
        assert "C" in net.tasks


class TestFlowManagement:
    """Tests for adding and managing flows."""

    def test_add_flow(self) -> None:
        """Add flow to net."""
        net = YNet(id="test")
        cond = YCondition(id="c1")
        task = YTask(id="A")
        net.add_condition(cond)
        net.add_task(task)

        flow = YFlow(id="f1", source_id="c1", target_id="A")
        net.add_flow(flow)

        assert "f1" in net.flows
        assert net.flows["f1"] == flow

    def test_flow_updates_preset_postset(self) -> None:
        """Flow updates connected elements' preset/postset."""
        net = YNet(id="test")
        c1 = YCondition(id="c1")
        c2 = YCondition(id="c2")
        task = YTask(id="A")

        net.add_condition(c1)
        net.add_condition(c2)
        net.add_task(task)

        net.add_flow(YFlow(id="f1", source_id="c1", target_id="A"))
        net.add_flow(YFlow(id="f2", source_id="A", target_id="c2"))

        # Check postset of c1
        assert "f1" in c1.postset_flows
        # Check preset of task
        assert "f1" in task.preset_flows
        # Check postset of task
        assert "f2" in task.postset_flows
        # Check preset of c2
        assert "f2" in c2.preset_flows

    def test_get_flow_count(self) -> None:
        """Count flows in net."""
        net = YNet(id="test")
        c1 = YCondition(id="c1")
        c2 = YCondition(id="c2")
        task = YTask(id="A")

        net.add_condition(c1)
        net.add_condition(c2)
        net.add_task(task)
        net.add_flow(YFlow(id="f1", source_id="c1", target_id="A"))
        net.add_flow(YFlow(id="f2", source_id="A", target_id="c2"))

        assert net.get_flow_count() == 2


class TestElementRetrieval:
    """Tests for retrieving elements."""

    def test_get_element_condition(self) -> None:
        """Get condition by ID."""
        net = YNet(id="test")
        cond = YCondition(id="c1")
        net.add_condition(cond)

        result = net.get_element("c1")
        assert result == cond

    def test_get_element_task(self) -> None:
        """Get task by ID."""
        net = YNet(id="test")
        task = YTask(id="A")
        net.add_task(task)

        result = net.get_element("A")
        assert result == task

    def test_get_element_not_found(self) -> None:
        """Get nonexistent element returns None."""
        net = YNet(id="test")

        result = net.get_element("nonexistent")
        assert result is None

    def test_get_flow(self) -> None:
        """Get flow by ID."""
        net = YNet(id="test")
        c1 = YCondition(id="c1")
        task = YTask(id="A")
        net.add_condition(c1)
        net.add_task(task)

        flow = YFlow(id="f1", source_id="c1", target_id="A")
        net.add_flow(flow)

        result = net.get_flow("f1")
        assert result == flow

    def test_get_flow_not_found(self) -> None:
        """Get nonexistent flow returns None."""
        net = YNet(id="test")

        result = net.get_flow("nonexistent")
        assert result is None


class TestPresetPostset:
    """Tests for preset/postset retrieval."""

    def test_get_preset_elements(self) -> None:
        """Get preset elements of a task."""
        net = YNet(id="test")
        c1 = YCondition(id="c1")
        c2 = YCondition(id="c2")
        task = YTask(id="A", join_type=JoinType.AND)

        net.add_condition(c1)
        net.add_condition(c2)
        net.add_task(task)
        net.add_flow(YFlow(id="f1", source_id="c1", target_id="A"))
        net.add_flow(YFlow(id="f2", source_id="c2", target_id="A"))

        preset = net.get_preset_elements("A")

        assert len(preset) == 2
        assert c1 in preset
        assert c2 in preset

    def test_get_postset_elements(self) -> None:
        """Get postset elements of a task."""
        net = YNet(id="test")
        c1 = YCondition(id="c1")
        c2 = YCondition(id="c2")
        task = YTask(id="A", split_type=SplitType.AND)

        net.add_condition(c1)
        net.add_condition(c2)
        net.add_task(task)
        net.add_flow(YFlow(id="f1", source_id="A", target_id="c1"))
        net.add_flow(YFlow(id="f2", source_id="A", target_id="c2"))

        postset = net.get_postset_elements("A")

        assert len(postset) == 2
        assert c1 in postset
        assert c2 in postset

    def test_get_preset_empty(self) -> None:
        """Preset of start condition is empty."""
        net = YNet(id="test")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        net.add_condition(start)

        preset = net.get_preset_elements("start")
        assert len(preset) == 0

    def test_get_preset_nonexistent(self) -> None:
        """Preset of nonexistent element is empty."""
        net = YNet(id="test")

        preset = net.get_preset_elements("nonexistent")
        assert len(preset) == 0


class TestNetValidation:
    """Tests for net validation (mirrors Java verify methods)."""

    def test_valid_simple_net(self) -> None:
        """Valid net has input, output, and task."""
        net = YNet(id="test")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        task = YTask(id="A")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task)
        net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
        net.add_flow(YFlow(id="f2", source_id="A", target_id="end"))

        assert net.is_valid()

    def test_invalid_no_input(self) -> None:
        """Net without input condition is invalid."""
        net = YNet(id="test")
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        task = YTask(id="A")

        net.add_condition(end)
        net.add_task(task)

        assert not net.is_valid()

    def test_invalid_no_output(self) -> None:
        """Net without output condition is invalid."""
        net = YNet(id="test")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        task = YTask(id="A")

        net.add_condition(start)
        net.add_task(task)

        assert not net.is_valid()

    def test_invalid_no_tasks(self) -> None:
        """Net without tasks is invalid."""
        net = YNet(id="test")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        net.add_condition(start)
        net.add_condition(end)

        assert not net.is_valid()


class TestLocalVariables:
    """Tests for local variable management."""

    def test_add_local_variable(self) -> None:
        """Add local variable to net."""
        net = YNet(id="test")

        net.add_local_variable("customer_id", "string")
        net.add_local_variable("order_total", "decimal")

        assert net.local_variables["customer_id"] == "string"
        assert net.local_variables["order_total"] == "decimal"

    def test_empty_local_variables(self) -> None:
        """New net has no local variables."""
        net = YNet(id="test")

        assert len(net.local_variables) == 0


class TestComplexNet:
    """Tests for complex net structures (mirrors Java TestYNet)."""

    def test_sequential_tasks(self) -> None:
        """Build sequential net: start -> A -> B -> C -> end."""
        net = YNet(id="sequential")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        c1 = YCondition(id="c1")
        c2 = YCondition(id="c2")

        net.add_condition(start)
        net.add_condition(end)
        net.add_condition(c1)
        net.add_condition(c2)

        for task_id in ["A", "B", "C"]:
            net.add_task(YTask(id=task_id))

        # start -> A -> c1 -> B -> c2 -> C -> end
        net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
        net.add_flow(YFlow(id="f2", source_id="A", target_id="c1"))
        net.add_flow(YFlow(id="f3", source_id="c1", target_id="B"))
        net.add_flow(YFlow(id="f4", source_id="B", target_id="c2"))
        net.add_flow(YFlow(id="f5", source_id="c2", target_id="C"))
        net.add_flow(YFlow(id="f6", source_id="C", target_id="end"))

        assert net.is_valid()
        assert net.get_task_count() == 3
        assert net.get_condition_count() == 4
        assert net.get_flow_count() == 6

    def test_parallel_split_join(self) -> None:
        """Build parallel net with AND-split and AND-join."""
        net = YNet(id="parallel")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        c_a = YCondition(id="c_a")
        c_b = YCondition(id="c_b")

        net.add_condition(start)
        net.add_condition(end)
        net.add_condition(c_a)
        net.add_condition(c_b)

        split = YTask(id="Split", split_type=SplitType.AND)
        task_a = YTask(id="A")
        task_b = YTask(id="B")
        join = YTask(id="Join", join_type=JoinType.AND)

        net.add_task(split)
        net.add_task(task_a)
        net.add_task(task_b)
        net.add_task(join)

        # start -> Split -> (c_a -> A, c_b -> B) -> join conditions -> Join -> end
        net.add_flow(YFlow(id="f1", source_id="start", target_id="Split"))
        net.add_flow(YFlow(id="f2", source_id="Split", target_id="c_a"))
        net.add_flow(YFlow(id="f3", source_id="Split", target_id="c_b"))
        net.add_flow(YFlow(id="f4", source_id="c_a", target_id="A"))
        net.add_flow(YFlow(id="f5", source_id="c_b", target_id="B"))

        c_post_a = YCondition(id="c_post_a")
        c_post_b = YCondition(id="c_post_b")
        net.add_condition(c_post_a)
        net.add_condition(c_post_b)

        net.add_flow(YFlow(id="f6", source_id="A", target_id="c_post_a"))
        net.add_flow(YFlow(id="f7", source_id="B", target_id="c_post_b"))
        net.add_flow(YFlow(id="f8", source_id="c_post_a", target_id="Join"))
        net.add_flow(YFlow(id="f9", source_id="c_post_b", target_id="Join"))
        net.add_flow(YFlow(id="f10", source_id="Join", target_id="end"))

        assert net.is_valid()
        assert net.get_task_count() == 4

        # Check split postset
        split_postset = net.get_postset_elements("Split")
        assert len(split_postset) == 2

        # Check join preset
        join_preset = net.get_preset_elements("Join")
        assert len(join_preset) == 2

    def test_exclusive_choice(self) -> None:
        """Build XOR-split net."""
        net = YNet(id="choice")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        net.add_condition(start)
        net.add_condition(end)

        choice = YTask(id="Choice", split_type=SplitType.XOR)
        net.add_task(choice)

        # Two branches from choice
        c_a = YCondition(id="c_a")
        c_b = YCondition(id="c_b")
        net.add_condition(c_a)
        net.add_condition(c_b)

        net.add_flow(YFlow(id="f1", source_id="start", target_id="Choice"))
        net.add_flow(YFlow(id="f2", source_id="Choice", target_id="c_a"))
        net.add_flow(YFlow(id="f3", source_id="Choice", target_id="c_b"))

        task_a = YTask(id="A")
        task_b = YTask(id="B")
        net.add_task(task_a)
        net.add_task(task_b)

        net.add_flow(YFlow(id="f4", source_id="c_a", target_id="A"))
        net.add_flow(YFlow(id="f5", source_id="c_b", target_id="B"))

        # Merge with XOR-join (simple merge)
        c_post_a = YCondition(id="c_post_a")
        c_post_b = YCondition(id="c_post_b")
        net.add_condition(c_post_a)
        net.add_condition(c_post_b)

        net.add_flow(YFlow(id="f6", source_id="A", target_id="c_post_a"))
        net.add_flow(YFlow(id="f7", source_id="B", target_id="c_post_b"))

        merge = YTask(id="Merge", join_type=JoinType.XOR)
        net.add_task(merge)

        net.add_flow(YFlow(id="f8", source_id="c_post_a", target_id="Merge"))
        net.add_flow(YFlow(id="f9", source_id="c_post_b", target_id="Merge"))
        net.add_flow(YFlow(id="f10", source_id="Merge", target_id="end"))

        assert net.is_valid()
        assert choice.split_type == SplitType.XOR
        assert merge.join_type == JoinType.XOR
