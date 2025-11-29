"""Tests for YNetRunner - mirrors TestYNetRunner.java.

Verifies token execution, task firing, and workflow completion.
"""

from __future__ import annotations

import pytest

from kgcl.yawl.elements.y_condition import ConditionType, YCondition
from kgcl.yawl.elements.y_flow import YFlow
from kgcl.yawl.elements.y_net import YNet
from kgcl.yawl.elements.y_task import JoinType, SplitType, YTask
from kgcl.yawl.engine.y_net_runner import YNetRunner


def build_simple_net() -> YNet:
    """Build simple net: start -> A -> end."""
    net = YNet(id="simple")
    start = YCondition(id="start", condition_type=ConditionType.INPUT)
    end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
    task = YTask(id="A")

    net.add_condition(start)
    net.add_condition(end)
    net.add_task(task)
    net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
    net.add_flow(YFlow(id="f2", source_id="A", target_id="end"))

    return net


def build_sequential_net() -> YNet:
    """Build sequential net: start -> A -> c1 -> B -> end."""
    net = YNet(id="sequential")
    start = YCondition(id="start", condition_type=ConditionType.INPUT)
    end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
    c1 = YCondition(id="c1")

    net.add_condition(start)
    net.add_condition(end)
    net.add_condition(c1)

    net.add_task(YTask(id="A"))
    net.add_task(YTask(id="B"))

    net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
    net.add_flow(YFlow(id="f2", source_id="A", target_id="c1"))
    net.add_flow(YFlow(id="f3", source_id="c1", target_id="B"))
    net.add_flow(YFlow(id="f4", source_id="B", target_id="end"))

    return net


def build_parallel_net() -> YNet:
    """Build parallel net with AND-split and AND-join."""
    net = YNet(id="parallel")
    start = YCondition(id="start", condition_type=ConditionType.INPUT)
    end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

    net.add_condition(start)
    net.add_condition(end)

    # Split task
    split = YTask(id="Split", split_type=SplitType.AND)
    net.add_task(split)

    # Parallel branches
    c_a = YCondition(id="c_a")
    c_b = YCondition(id="c_b")
    net.add_condition(c_a)
    net.add_condition(c_b)

    task_a = YTask(id="A")
    task_b = YTask(id="B")
    net.add_task(task_a)
    net.add_task(task_b)

    c_post_a = YCondition(id="c_post_a")
    c_post_b = YCondition(id="c_post_b")
    net.add_condition(c_post_a)
    net.add_condition(c_post_b)

    # Join task
    join = YTask(id="Join", join_type=JoinType.AND)
    net.add_task(join)

    # Flows
    net.add_flow(YFlow(id="f1", source_id="start", target_id="Split"))
    net.add_flow(YFlow(id="f2", source_id="Split", target_id="c_a"))
    net.add_flow(YFlow(id="f3", source_id="Split", target_id="c_b"))
    net.add_flow(YFlow(id="f4", source_id="c_a", target_id="A"))
    net.add_flow(YFlow(id="f5", source_id="c_b", target_id="B"))
    net.add_flow(YFlow(id="f6", source_id="A", target_id="c_post_a"))
    net.add_flow(YFlow(id="f7", source_id="B", target_id="c_post_b"))
    net.add_flow(YFlow(id="f8", source_id="c_post_a", target_id="Join"))
    net.add_flow(YFlow(id="f9", source_id="c_post_b", target_id="Join"))
    net.add_flow(YFlow(id="f10", source_id="Join", target_id="end"))

    return net


class TestNetRunnerCreation:
    """Tests for net runner creation."""

    def test_create_runner(self) -> None:
        """Create net runner."""
        net = build_simple_net()
        runner = YNetRunner(net=net)

        assert runner.net is net
        assert runner.case_id is not None
        assert not runner.completed
        assert runner.marking.is_empty()

    def test_create_runner_with_case_id(self) -> None:
        """Create runner with specific case ID."""
        net = build_simple_net()
        runner = YNetRunner(net=net, case_id="case-001")

        assert runner.case_id == "case-001"


class TestStartCase:
    """Tests for starting a case."""

    def test_start_places_token(self) -> None:
        """Start places token at input condition."""
        net = build_simple_net()
        runner = YNetRunner(net=net)

        token = runner.start()

        assert token is not None
        assert token.location == "start"
        assert runner.marking.has_tokens("start")
        assert runner.marking.token_count("start") == 1

    def test_start_tracks_token(self) -> None:
        """Start records token in runner."""
        net = build_simple_net()
        runner = YNetRunner(net=net)

        token = runner.start()

        assert token.id in runner.tokens
        assert runner.tokens[token.id] is token

    def test_start_without_input_condition(self) -> None:
        """Start without input condition raises error."""
        net = YNet(id="invalid")
        runner = YNetRunner(net=net)

        with pytest.raises(ValueError, match="no input condition"):
            runner.start()


class TestGetEnabledTasks:
    """Tests for getting enabled tasks."""

    def test_enabled_after_start(self) -> None:
        """Task is enabled after start."""
        net = build_simple_net()
        runner = YNetRunner(net=net)
        runner.start()

        enabled = runner.get_enabled_tasks()

        assert "A" in enabled

    def test_no_enabled_before_start(self) -> None:
        """No tasks enabled before start."""
        net = build_simple_net()
        runner = YNetRunner(net=net)

        enabled = runner.get_enabled_tasks()

        assert len(enabled) == 0

    def test_sequential_enabled(self) -> None:
        """Sequential tasks enable one at a time."""
        net = build_sequential_net()
        runner = YNetRunner(net=net)
        runner.start()

        enabled = runner.get_enabled_tasks()

        assert enabled == ["A"]
        assert "B" not in enabled


class TestFireTask:
    """Tests for firing tasks - mirrors TestYNetRunner.testFireAtomicTask."""

    def test_fire_simple_task(self) -> None:
        """Fire simple task moves token."""
        net = build_simple_net()
        runner = YNetRunner(net=net)
        runner.start()

        result = runner.fire_task("A")

        assert result.task_id == "A"
        assert len(result.consumed_tokens) == 1
        assert len(result.produced_tokens) == 1
        assert runner.marking.has_tokens("end")
        assert not runner.marking.has_tokens("start")

    def test_fire_completes_case(self) -> None:
        """Fire task that reaches end completes case."""
        net = build_simple_net()
        runner = YNetRunner(net=net)
        runner.start()

        runner.fire_task("A")

        assert runner.completed

    def test_fire_unknown_task(self) -> None:
        """Fire unknown task raises error."""
        net = build_simple_net()
        runner = YNetRunner(net=net)
        runner.start()

        with pytest.raises(ValueError, match="Unknown task"):
            runner.fire_task("Z")

    def test_fire_disabled_task(self) -> None:
        """Fire disabled task raises error."""
        net = build_sequential_net()
        runner = YNetRunner(net=net)
        runner.start()

        # B is not enabled yet
        with pytest.raises(ValueError, match="not enabled"):
            runner.fire_task("B")

    def test_fire_sequential(self) -> None:
        """Fire sequential tasks."""
        net = build_sequential_net()
        runner = YNetRunner(net=net)
        runner.start()

        # Fire A
        runner.fire_task("A")
        assert not runner.completed
        assert runner.marking.has_tokens("c1")
        assert "B" in runner.get_enabled_tasks()

        # Fire B
        runner.fire_task("B")
        assert runner.completed
        assert runner.marking.has_tokens("end")


class TestParallelExecution:
    """Tests for parallel execution (AND-split/AND-join)."""

    def test_and_split(self) -> None:
        """AND-split produces tokens to all branches."""
        net = build_parallel_net()
        runner = YNetRunner(net=net)
        runner.start()

        # Fire split
        result = runner.fire_task("Split")

        assert len(result.produced_tokens) == 2
        assert runner.marking.has_tokens("c_a")
        assert runner.marking.has_tokens("c_b")
        assert "A" in runner.get_enabled_tasks()
        assert "B" in runner.get_enabled_tasks()

    def test_and_join_waits(self) -> None:
        """AND-join waits for all branches."""
        net = build_parallel_net()
        runner = YNetRunner(net=net)
        runner.start()

        runner.fire_task("Split")
        runner.fire_task("A")

        # Join not enabled yet (B not done)
        assert "Join" not in runner.get_enabled_tasks()
        assert runner.marking.has_tokens("c_post_a")
        assert not runner.marking.has_tokens("c_post_b")

    def test_and_join_fires_when_ready(self) -> None:
        """AND-join fires when all branches complete."""
        net = build_parallel_net()
        runner = YNetRunner(net=net)
        runner.start()

        runner.fire_task("Split")
        runner.fire_task("A")
        runner.fire_task("B")

        # Now join is enabled
        assert "Join" in runner.get_enabled_tasks()

        runner.fire_task("Join")
        assert runner.completed


class TestXorSplit:
    """Tests for XOR-split behavior."""

    def test_xor_split_one_path(self) -> None:
        """XOR-split produces token to one branch."""
        net = YNet(id="xor")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        c_a = YCondition(id="c_a")
        c_b = YCondition(id="c_b")

        net.add_condition(start)
        net.add_condition(end)
        net.add_condition(c_a)
        net.add_condition(c_b)

        choice = YTask(id="Choice", split_type=SplitType.XOR)
        net.add_task(choice)

        net.add_flow(YFlow(id="f1", source_id="start", target_id="Choice"))
        f2 = YFlow(id="f2", source_id="Choice", target_id="c_a", ordering=1)
        f3 = YFlow(id="f3", source_id="Choice", target_id="c_b", ordering=2)
        net.add_flow(f2)
        net.add_flow(f3)

        runner = YNetRunner(net=net)
        runner.start()

        result = runner.fire_task("Choice")

        # Only one token produced
        assert len(result.produced_tokens) == 1


class TestOrJoin:
    """Tests for OR-join behavior - mirrors TestOrJoin.java."""

    def test_or_join_single_token(self) -> None:
        """OR-join fires with single token."""
        net = YNet(id="or-join")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        c_a = YCondition(id="c_a")
        c_b = YCondition(id="c_b")

        net.add_condition(start)
        net.add_condition(end)
        net.add_condition(c_a)
        net.add_condition(c_b)

        split = YTask(id="Split", split_type=SplitType.XOR)
        net.add_task(split)
        net.add_flow(YFlow(id="f1", source_id="start", target_id="Split"))
        net.add_flow(YFlow(id="f2", source_id="Split", target_id="c_a", ordering=1))
        net.add_flow(YFlow(id="f3", source_id="Split", target_id="c_b", ordering=2))

        task_a = YTask(id="A")
        net.add_task(task_a)
        net.add_flow(YFlow(id="f4", source_id="c_a", target_id="A"))

        c_post_a = YCondition(id="c_post_a")
        net.add_condition(c_post_a)
        net.add_flow(YFlow(id="f5", source_id="A", target_id="c_post_a"))

        # OR-join
        join = YTask(id="Join", join_type=JoinType.OR)
        net.add_task(join)
        net.add_flow(YFlow(id="f6", source_id="c_post_a", target_id="Join"))
        net.add_flow(YFlow(id="f7", source_id="c_b", target_id="Join"))
        net.add_flow(YFlow(id="f8", source_id="Join", target_id="end"))

        runner = YNetRunner(net=net)
        runner.start()

        runner.fire_task("Split")  # Goes to c_a (first in order)
        runner.fire_task("A")

        # OR-join should be enabled with just one token
        assert "Join" in runner.get_enabled_tasks()

        runner.fire_task("Join")
        assert runner.completed


class TestCancellation:
    """Tests for cancellation set execution."""

    def test_cancellation_removes_tokens(self) -> None:
        """Cancellation set removes tokens."""
        net = YNet(id="cancel")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        c1 = YCondition(id="c1")
        c2 = YCondition(id="c2")

        net.add_condition(start)
        net.add_condition(end)
        net.add_condition(c1)
        net.add_condition(c2)

        # Split to both conditions
        split = YTask(id="Split", split_type=SplitType.AND)
        net.add_task(split)
        net.add_flow(YFlow(id="f1", source_id="start", target_id="Split"))
        net.add_flow(YFlow(id="f2", source_id="Split", target_id="c1"))
        net.add_flow(YFlow(id="f3", source_id="Split", target_id="c2"))

        # Task A has cancellation set for c2
        task_a = YTask(id="A", cancellation_set={"c2"})
        net.add_task(task_a)
        net.add_flow(YFlow(id="f4", source_id="c1", target_id="A"))
        net.add_flow(YFlow(id="f5", source_id="A", target_id="end"))

        runner = YNetRunner(net=net)
        runner.start()
        runner.fire_task("Split")

        # Both conditions have tokens
        assert runner.marking.has_tokens("c1")
        assert runner.marking.has_tokens("c2")

        result = runner.fire_task("A")

        # c2 should be cancelled
        assert len(result.cancelled_tokens) == 1
        assert not runner.marking.has_tokens("c2")
        assert runner.completed


class TestTokenLineage:
    """Tests for token lineage tracking."""

    def test_token_parent_child(self) -> None:
        """Tokens maintain parent-child relationship."""
        net = build_parallel_net()
        runner = YNetRunner(net=net)

        initial_token = runner.start()
        runner.fire_task("Split")

        # Get child tokens
        children = [t for t in runner.tokens.values() if t.parent is not None]

        assert len(children) >= 2
        # All children have parent leading to initial token
        for child in children:
            root = child.get_root()
            assert root.id == initial_token.id


class TestMarkingSnapshot:
    """Tests for marking snapshot."""

    def test_get_marking_snapshot(self) -> None:
        """Get snapshot of current marking."""
        net = build_parallel_net()
        runner = YNetRunner(net=net)
        runner.start()
        runner.fire_task("Split")

        snapshot = runner.get_marking_snapshot()

        assert "c_a" in snapshot
        assert "c_b" in snapshot
        assert len(snapshot["c_a"]) == 1
        assert len(snapshot["c_b"]) == 1


class TestDeadlockDetection:
    """Tests for deadlock detection."""

    def test_not_deadlocked_normal(self) -> None:
        """Normal execution is not deadlocked."""
        net = build_simple_net()
        runner = YNetRunner(net=net)
        runner.start()

        assert not runner.is_deadlocked()

    def test_not_deadlocked_completed(self) -> None:
        """Completed case is not deadlocked."""
        net = build_simple_net()
        runner = YNetRunner(net=net)
        runner.start()
        runner.fire_task("A")

        assert runner.completed
        assert not runner.is_deadlocked()


class TestDataFlow:
    """Tests for data flow through tokens."""

    def test_fire_with_data(self) -> None:
        """Fire task with data payload."""
        net = build_simple_net()
        runner = YNetRunner(net=net)
        runner.start()

        data = {"order_id": "123", "amount": 100.0}
        result = runner.fire_task("A", data=data)

        # Check produced token has data
        produced_id = result.produced_tokens[0]
        token = runner.get_token(produced_id)
        assert token is not None
        assert token.data["order_id"] == "123"
        assert token.data["amount"] == 100.0
