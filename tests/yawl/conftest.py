"""Test fixtures for YAWL tests.

Provides builder functions for common workflow patterns.
"""

from __future__ import annotations

import pytest

from kgcl.yawl.elements.y_condition import ConditionType, YCondition
from kgcl.yawl.elements.y_flow import YFlow
from kgcl.yawl.elements.y_net import YNet
from kgcl.yawl.elements.y_task import JoinType, SplitType, YTask


def build_sequence_net() -> YNet:
    """Build a simple sequence: start -> A -> B -> C -> end.

    WCP-1: Sequence pattern.
    """
    net = YNet(id="sequence")

    # Conditions
    start = YCondition(id="start", condition_type=ConditionType.INPUT)
    c1 = YCondition(id="c1")
    c2 = YCondition(id="c2")
    c3 = YCondition(id="c3")
    end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

    # Tasks
    task_a = YTask(id="A", name="Task A")
    task_b = YTask(id="B", name="Task B")
    task_c = YTask(id="C", name="Task C")

    # Add to net
    for cond in [start, c1, c2, c3, end]:
        net.add_condition(cond)
    for task in [task_a, task_b, task_c]:
        net.add_task(task)

    # Flows: start -> A -> c1 -> B -> c2 -> C -> c3 -> end
    net.add_flow(YFlow(id="f0", source_id="start", target_id="A"))
    net.add_flow(YFlow(id="f1", source_id="A", target_id="c1"))
    net.add_flow(YFlow(id="f2", source_id="c1", target_id="B"))
    net.add_flow(YFlow(id="f3", source_id="B", target_id="c2"))
    net.add_flow(YFlow(id="f4", source_id="c2", target_id="C"))
    net.add_flow(YFlow(id="f5", source_id="C", target_id="end"))

    return net


def build_and_split_net() -> YNet:
    """Build AND-split pattern: start -> A -AND-> B, C.

    WCP-2: Parallel Split pattern.
    """
    net = YNet(id="and_split")

    # Conditions
    start = YCondition(id="start", condition_type=ConditionType.INPUT)
    c1 = YCondition(id="c1")  # After A, before B
    c2 = YCondition(id="c2")  # After A, before C
    c3 = YCondition(id="c3")  # After B
    c4 = YCondition(id="c4")  # After C
    end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

    # Tasks
    task_a = YTask(id="A", name="Task A", split_type=SplitType.AND)
    task_b = YTask(id="B", name="Task B")
    task_c = YTask(id="C", name="Task C")
    task_d = YTask(id="D", name="Task D", join_type=JoinType.AND)

    # Add to net
    for cond in [start, c1, c2, c3, c4, end]:
        net.add_condition(cond)
    for task in [task_a, task_b, task_c, task_d]:
        net.add_task(task)

    # Flows
    net.add_flow(YFlow(id="f0", source_id="start", target_id="A"))
    net.add_flow(YFlow(id="f1", source_id="A", target_id="c1"))  # AND split
    net.add_flow(YFlow(id="f2", source_id="A", target_id="c2"))  # AND split
    net.add_flow(YFlow(id="f3", source_id="c1", target_id="B"))
    net.add_flow(YFlow(id="f4", source_id="c2", target_id="C"))
    net.add_flow(YFlow(id="f5", source_id="B", target_id="c3"))
    net.add_flow(YFlow(id="f6", source_id="C", target_id="c4"))
    net.add_flow(YFlow(id="f7", source_id="c3", target_id="D"))  # AND join
    net.add_flow(YFlow(id="f8", source_id="c4", target_id="D"))  # AND join
    net.add_flow(YFlow(id="f9", source_id="D", target_id="end"))

    return net


def build_xor_split_net() -> YNet:
    """Build XOR-split pattern: start -> A -XOR-> B or C.

    WCP-4: Exclusive Choice pattern.
    """
    net = YNet(id="xor_split")

    # Conditions
    start = YCondition(id="start", condition_type=ConditionType.INPUT)
    c1 = YCondition(id="c1")  # After A, before B
    c2 = YCondition(id="c2")  # After A, before C
    c3 = YCondition(id="c3")  # After B
    c4 = YCondition(id="c4")  # After C
    end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

    # Tasks
    task_a = YTask(id="A", name="Task A", split_type=SplitType.XOR)
    task_b = YTask(id="B", name="Task B")
    task_c = YTask(id="C", name="Task C")
    task_d = YTask(id="D", name="Task D", join_type=JoinType.XOR)

    # Set predicates for XOR split
    task_a.flow_predicates["f1"] = "route_b"
    task_a.flow_predicates["f2"] = "route_c"

    # Add to net
    for cond in [start, c1, c2, c3, c4, end]:
        net.add_condition(cond)
    for task in [task_a, task_b, task_c, task_d]:
        net.add_task(task)

    # Flows
    net.add_flow(YFlow(id="f0", source_id="start", target_id="A"))
    net.add_flow(YFlow(id="f1", source_id="A", target_id="c1", ordering=1))  # XOR to B
    net.add_flow(YFlow(id="f2", source_id="A", target_id="c2", ordering=2, is_default=True))  # XOR to C (default)
    net.add_flow(YFlow(id="f3", source_id="c1", target_id="B"))
    net.add_flow(YFlow(id="f4", source_id="c2", target_id="C"))
    net.add_flow(YFlow(id="f5", source_id="B", target_id="c3"))
    net.add_flow(YFlow(id="f6", source_id="C", target_id="c4"))
    net.add_flow(YFlow(id="f7", source_id="c3", target_id="D"))  # XOR join
    net.add_flow(YFlow(id="f8", source_id="c4", target_id="D"))  # XOR join
    net.add_flow(YFlow(id="f9", source_id="D", target_id="end"))

    return net


def build_simple_net() -> YNet:
    """Build simplest net: start -> A -> end."""
    net = YNet(id="simple")

    start = YCondition(id="start", condition_type=ConditionType.INPUT)
    end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
    task_a = YTask(id="A")

    net.add_condition(start)
    net.add_condition(end)
    net.add_task(task_a)

    net.add_flow(YFlow(id="f0", source_id="start", target_id="A"))
    net.add_flow(YFlow(id="f1", source_id="A", target_id="end"))

    return net


def build_cancellation_net() -> YNet:
    """Build net with cancellation: A cancels tokens in c2.

    WCP-43: Explicit Termination pattern variant.
    """
    net = YNet(id="cancellation")

    # Conditions
    start = YCondition(id="start", condition_type=ConditionType.INPUT)
    c1 = YCondition(id="c1")  # After split, before A
    c2 = YCondition(id="c2")  # After split, before B (will be cancelled)
    c3 = YCondition(id="c3")  # After A
    end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

    # Tasks
    task_split = YTask(id="Split", split_type=SplitType.AND)
    task_a = YTask(id="A", cancellation_set={"c2"})  # A cancels c2
    task_b = YTask(id="B")
    task_join = YTask(id="Join", join_type=JoinType.XOR)

    # Add to net
    for cond in [start, c1, c2, c3, end]:
        net.add_condition(cond)
    for task in [task_split, task_a, task_b, task_join]:
        net.add_task(task)

    # Flows
    net.add_flow(YFlow(id="f0", source_id="start", target_id="Split"))
    net.add_flow(YFlow(id="f1", source_id="Split", target_id="c1"))
    net.add_flow(YFlow(id="f2", source_id="Split", target_id="c2"))
    net.add_flow(YFlow(id="f3", source_id="c1", target_id="A"))
    net.add_flow(YFlow(id="f4", source_id="c2", target_id="B"))
    net.add_flow(YFlow(id="f5", source_id="A", target_id="c3"))
    net.add_flow(YFlow(id="f6", source_id="c3", target_id="Join"))
    net.add_flow(YFlow(id="f7", source_id="B", target_id="end"))  # B goes to end
    net.add_flow(YFlow(id="f8", source_id="Join", target_id="end"))

    return net


@pytest.fixture
def simple_net() -> YNet:
    """Fixture for simple net."""
    return build_simple_net()


@pytest.fixture
def sequence_net() -> YNet:
    """Fixture for sequence net."""
    return build_sequence_net()


@pytest.fixture
def and_split_net() -> YNet:
    """Fixture for AND-split net."""
    return build_and_split_net()


@pytest.fixture
def xor_split_net() -> YNet:
    """Fixture for XOR-split net."""
    return build_xor_split_net()


@pytest.fixture
def cancellation_net() -> YNet:
    """Fixture for cancellation net."""
    return build_cancellation_net()
