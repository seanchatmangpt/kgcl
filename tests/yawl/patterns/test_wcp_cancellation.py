"""Tests for Cancellation Workflow Control Patterns (WCP 43).

WCP-43: Explicit Termination - A given activity should cause the
immediate and complete termination of the workflow.
"""

from __future__ import annotations

from kgcl.yawl.elements.y_condition import ConditionType, YCondition
from kgcl.yawl.elements.y_flow import YFlow
from kgcl.yawl.elements.y_net import YNet
from kgcl.yawl.elements.y_task import SplitType, YTask
from kgcl.yawl.engine.y_net_runner import YNetRunner
from tests.yawl.conftest import build_cancellation_net


class TestWCP43Termination:
    """WCP-43: Explicit Termination.

    Tests cancellation regions (reset net semantics) where firing
    a task can void tokens in specified conditions.
    """

    def test_cancellation_removes_tokens(self) -> None:
        """Firing a task with cancellation set removes specified tokens."""
        net = build_cancellation_net()
        runner = YNetRunner(net)
        runner.start()

        # Split puts tokens in c1 and c2
        runner.fire_task("Split")
        assert runner.marking.has_tokens("c1")
        assert runner.marking.has_tokens("c2")

        # Fire A which cancels c2
        result = runner.fire_task("A")

        # c2 should be empty (cancelled)
        assert not runner.marking.has_tokens("c2")
        assert len(result.cancelled_tokens) == 1

        # B should no longer be enabled
        assert "B" not in runner.get_enabled_tasks()

    def test_cancellation_voids_parallel_path(self) -> None:
        """Cancellation effectively voids parallel branch."""
        net = build_cancellation_net()
        runner = YNetRunner(net)
        runner.start()
        runner.fire_task("Split")

        # Before cancellation, both A and B are enabled
        enabled_before = set(runner.get_enabled_tasks())
        assert "A" in enabled_before
        assert "B" in enabled_before

        # Fire A (cancels c2)
        runner.fire_task("A")

        # After cancellation, B is no longer enabled
        enabled_after = set(runner.get_enabled_tasks())
        assert "B" not in enabled_after
        assert "Join" in enabled_after

    def test_multiple_cancellation_targets(self) -> None:
        """Task can cancel multiple conditions."""
        # Build net where A cancels both c2 and c3
        net = YNet(id="multi_cancel")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        c1 = YCondition(id="c1")
        c2 = YCondition(id="c2")
        c3 = YCondition(id="c3")
        c4 = YCondition(id="c4")
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        split = YTask(id="Split", split_type=SplitType.AND)
        task_a = YTask(id="A", cancellation_set={"c2", "c3"})  # Cancels both
        task_b = YTask(id="B")
        task_c = YTask(id="C")

        for cond in [start, c1, c2, c3, c4, end]:
            net.add_condition(cond)
        for task in [split, task_a, task_b, task_c]:
            net.add_task(task)

        net.add_flow(YFlow(id="f0", source_id="start", target_id="Split"))
        net.add_flow(YFlow(id="f1", source_id="Split", target_id="c1"))
        net.add_flow(YFlow(id="f2", source_id="Split", target_id="c2"))
        net.add_flow(YFlow(id="f3", source_id="Split", target_id="c3"))
        net.add_flow(YFlow(id="f4", source_id="c1", target_id="A"))
        net.add_flow(YFlow(id="f5", source_id="c2", target_id="B"))
        net.add_flow(YFlow(id="f6", source_id="c3", target_id="C"))
        net.add_flow(YFlow(id="f7", source_id="A", target_id="end"))
        net.add_flow(YFlow(id="f8", source_id="B", target_id="c4"))
        net.add_flow(YFlow(id="f9", source_id="C", target_id="c4"))

        runner = YNetRunner(net)
        runner.start()
        runner.fire_task("Split")

        # All three tasks enabled
        assert {"A", "B", "C"} == set(runner.get_enabled_tasks())

        # Fire A (cancels c2 and c3)
        result = runner.fire_task("A")

        # Both conditions cancelled
        assert not runner.marking.has_tokens("c2")
        assert not runner.marking.has_tokens("c3")
        assert len(result.cancelled_tokens) == 2

        # B and C no longer enabled
        assert "B" not in runner.get_enabled_tasks()
        assert "C" not in runner.get_enabled_tasks()

        # Workflow completes (A went to end)
        assert runner.completed

    def test_cancellation_does_not_affect_other_conditions(self) -> None:
        """Cancellation only affects specified conditions."""
        net = build_cancellation_net()
        runner = YNetRunner(net)
        runner.start()
        runner.fire_task("Split")

        # Get token in c1 before firing A
        c1_token_before = runner.marking.get_tokens("c1").copy()

        # Fire A (cancels c2 only)
        runner.fire_task("A")

        # c1 should still have its token (via c3 from A)
        # Actually A moves the token, so check c3
        assert runner.marking.has_tokens("c3")

    def test_empty_cancellation_set(self) -> None:
        """Task without cancellation set fires normally."""
        net = build_cancellation_net()
        runner = YNetRunner(net)
        runner.start()
        runner.fire_task("Split")

        # Fire B (has no cancellation set)
        result = runner.fire_task("B")

        # No tokens cancelled
        assert len(result.cancelled_tokens) == 0

        # c1 still has token (for A)
        assert runner.marking.has_tokens("c1")
