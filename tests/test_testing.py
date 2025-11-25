"""Tests for advanced testing utilities."""

from pathlib import Path

import pytest
from src.testing import PropertyBasedTest, SnapshotTest, StateMachine, StateMachineTest

SUCCESS_RATE_FULL: float = 100.0
SUCCESS_RATE_NONE: float = 0.0


class TestPropertyBasedTest:
    """Test property-based testing."""

    def test_property_test_execution(self) -> None:
        """Test property-based test execution."""
        test = PropertyBasedTest("addition_commutative", lambda a, b: a + b == b + a)
        test.add_example(1, 2)
        test.add_example(5, 3)

        assert test.run() is True
        assert test.success_rate() == SUCCESS_RATE_FULL

    def test_property_test_failure(self) -> None:
        """Test property test with failures."""
        test = PropertyBasedTest("always_false", lambda _: False)
        test.add_example(1)

        assert test.run() is False
        assert test.success_rate() == SUCCESS_RATE_NONE


class TestStateMachine:
    """Test state machine functionality."""

    def test_state_transitions(self) -> None:
        """Test state transitions."""
        sm = StateMachine("start")
        sm.add_transition("start", "middle", "go")
        sm.add_transition("middle", "end", "finish")

        assert sm.perform_action("go") is True
        assert sm.current_state() == "middle"

        assert sm.perform_action("finish") is True
        assert sm.current_state() == "end"

    def test_invalid_transitions(self) -> None:
        """Test invalid transitions."""
        sm = StateMachine("start")
        sm.add_transition("start", "end", "go")

        result = sm.perform_action("invalid")
        assert result is False
        assert sm.current_state() == "start"

    def test_valid_actions(self) -> None:
        """Test getting valid actions."""
        sm = StateMachine("start")
        sm.add_transition("start", "end", "go")

        actions = sm.valid_actions()
        assert "go" in actions

    def test_state_history(self) -> None:
        """Test state history."""
        sm = StateMachine("a")
        sm.add_transition("a", "b", "next")
        sm.add_transition("b", "c", "next")

        sm.perform_action("next")
        sm.perform_action("next")

        assert sm.history() == ["a", "b", "c"]


class TestStateMachineTest:
    """Test state machine test harness."""

    def test_state_machine_test(self) -> None:
        """Test state machine test execution."""
        sm = StateMachine("pending")
        sm.add_transition("pending", "active", "start")
        sm.add_transition("active", "done", "finish")

        test = StateMachineTest(
            "workflow", "pending", expected_path=["pending", "active", "done"], machine=sm
        )

        result = test.run([("start", None), ("finish", None)])

        assert result is True


class TestSnapshotTest:
    """Test snapshot testing."""

    def test_snapshot_comparison(self, tmp_path: Path) -> None:
        """Test snapshot comparison."""
        snapshot_file = tmp_path / "snapshot.json"

        # Create first snapshot
        test1 = SnapshotTest("test", {"key": "value"})
        test1.matches_snapshot(str(snapshot_file), update=True)
        assert test1.matched is True

        # Verify snapshot matches
        test2 = SnapshotTest("test", {"key": "value"})
        assert test2.matches_snapshot(str(snapshot_file)) is True

    def test_snapshot_mismatch(self, tmp_path: Path) -> None:
        """Test snapshot mismatch."""
        snapshot_file = tmp_path / "snapshot.json"

        # Create snapshot
        test1 = SnapshotTest("test", {"key": "value1"})
        test1.matches_snapshot(str(snapshot_file), update=True)

        # Test with different value
        test2 = SnapshotTest("test", {"key": "value2"})
        assert test2.matches_snapshot(str(snapshot_file)) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
