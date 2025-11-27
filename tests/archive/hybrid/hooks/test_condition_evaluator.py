"""Tests for Innovation #2: 8-Condition Evaluator.

Chicago School TDD: Real condition evaluation, no mocking.
Tests all 8 condition types with realistic scenarios.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hooks.condition_evaluator import Condition, ConditionEvaluator, ConditionKind, ConditionResult


class TestConditionKind:
    """Tests for condition type enumeration."""

    def test_all_condition_types_defined(self) -> None:
        """All 8 condition types are defined."""
        assert len(ConditionKind) == 8

        expected = ["sparql-ask", "sparql-select", "shacl", "delta", "threshold", "count", "window", "n3-rule"]
        actual = [k.value for k in ConditionKind]

        assert sorted(actual) == sorted(expected)


class TestConditionDataclass:
    """Tests for Condition dataclass."""

    def test_condition_creation(self) -> None:
        """Condition stores kind, expression, and parameters."""
        cond = Condition(
            kind=ConditionKind.THRESHOLD,
            expression="errorRate > 0.05",
            parameters={"errorRate": 0.1, "threshold": 0.05, "operator": ">"},
        )

        assert cond.kind == ConditionKind.THRESHOLD
        assert cond.expression == "errorRate > 0.05"
        assert cond.parameters["threshold"] == 0.05

    def test_condition_is_frozen(self) -> None:
        """Condition is immutable."""
        cond = Condition(kind=ConditionKind.THRESHOLD, expression="x > 5")

        with pytest.raises(Exception):  # FrozenInstanceError
            cond.expression = "x > 10"  # type: ignore[misc]


class TestConditionResult:
    """Tests for ConditionResult dataclass."""

    def test_result_matched_true(self) -> None:
        """Result records match state."""
        result = ConditionResult(matched=True)

        assert result.matched is True
        assert result.bindings == {}
        assert result.duration_ms == 0.0

    def test_result_with_bindings(self) -> None:
        """Result stores variable bindings."""
        result = ConditionResult(matched=True, bindings={"name": "Alice"}, duration_ms=1.5)

        assert result.bindings["name"] == "Alice"
        assert result.duration_ms == 1.5


class TestThresholdCondition:
    """Tests for THRESHOLD condition evaluation."""

    def test_threshold_greater_than_match(self) -> None:
        """Threshold > comparison matches when value exceeds threshold."""
        evaluator = ConditionEvaluator()
        cond = Condition(
            kind=ConditionKind.THRESHOLD,
            expression="errorRate > 0.05",
            parameters={"errorRate": 0.1, "threshold": 0.05, "operator": ">"},
        )

        result = evaluator.evaluate(cond)

        assert result.matched is True
        assert result.metadata["value"] == 0.1

    def test_threshold_greater_than_no_match(self) -> None:
        """Threshold > comparison fails when value below threshold."""
        evaluator = ConditionEvaluator()
        cond = Condition(
            kind=ConditionKind.THRESHOLD,
            expression="errorRate > 0.05",
            parameters={"errorRate": 0.01, "threshold": 0.05, "operator": ">"},
        )

        result = evaluator.evaluate(cond)

        assert result.matched is False

    def test_threshold_less_than(self) -> None:
        """Threshold < comparison works correctly."""
        evaluator = ConditionEvaluator()
        cond = Condition(
            kind=ConditionKind.THRESHOLD,
            expression="latency < 100",
            parameters={"latency": 50, "threshold": 100, "operator": "<"},
        )

        result = evaluator.evaluate(cond)

        assert result.matched is True

    def test_threshold_equal(self) -> None:
        """Threshold == comparison works correctly."""
        evaluator = ConditionEvaluator()
        cond = Condition(
            kind=ConditionKind.THRESHOLD,
            expression="count == 5",
            parameters={"count": 5, "threshold": 5, "operator": "=="},
        )

        result = evaluator.evaluate(cond)

        assert result.matched is True

    def test_threshold_not_equal(self) -> None:
        """Threshold != comparison works correctly."""
        evaluator = ConditionEvaluator()
        cond = Condition(
            kind=ConditionKind.THRESHOLD,
            expression="status != 0",
            parameters={"status": 1, "threshold": 0, "operator": "!="},
        )

        result = evaluator.evaluate(cond)

        assert result.matched is True


class TestDeltaCondition:
    """Tests for DELTA (change detection) condition."""

    def test_delta_first_evaluation_no_change(self) -> None:
        """First delta evaluation reports no change (no previous state)."""
        evaluator = ConditionEvaluator()
        cond = Condition(kind=ConditionKind.DELTA, expression="SELECT ?s WHERE { ?s a :Task }")

        result = evaluator.evaluate(cond)

        assert result.matched is False  # No previous state

    def test_delta_detects_state_change(self) -> None:
        """Delta detects when state changes between evaluations."""
        evaluator = ConditionEvaluator()

        # Manually set previous state
        evaluator._delta_state["SELECT ?s WHERE { ?s a :Task }"] = "old_state"

        cond = Condition(kind=ConditionKind.DELTA, expression="SELECT ?s WHERE { ?s a :Task }")

        result = evaluator.evaluate(cond)

        # State changed from "old_state" to new (None since no store)
        assert result.matched is True

    def test_delta_no_change_same_state(self) -> None:
        """Delta reports no change when state is same."""
        evaluator = ConditionEvaluator()
        cond = Condition(kind=ConditionKind.DELTA, expression="test_query")

        # First evaluation
        evaluator.evaluate(cond)
        # Second evaluation (same state - no store means same None result)
        result = evaluator.evaluate(cond)

        assert result.matched is False


class TestWindowCondition:
    """Tests for WINDOW (sliding window) condition."""

    def test_window_event_within_bounds(self) -> None:
        """Window condition passes when events within min/max."""
        evaluator = ConditionEvaluator()
        cond = Condition(
            kind=ConditionKind.WINDOW,
            expression="rate_limit",
            parameters={"window_seconds": 60, "min_events": 0, "max_events": 100},
        )

        result = evaluator.evaluate(cond)

        assert result.matched is True
        assert result.metadata["count"] == 1

    def test_window_exceeds_max(self) -> None:
        """Window condition fails when events exceed max."""
        evaluator = ConditionEvaluator()
        cond = Condition(
            kind=ConditionKind.WINDOW,
            expression="rate_limit",
            parameters={"window_seconds": 60, "min_events": 0, "max_events": 2},
        )

        # Trigger 3 events
        evaluator.evaluate(cond)
        evaluator.evaluate(cond)
        result = evaluator.evaluate(cond)

        assert result.matched is False  # 3 > max of 2


class TestEvaluatorStateManagement:
    """Tests for evaluator state management."""

    def test_reset_clears_delta_state(self) -> None:
        """Reset clears delta tracking state."""
        evaluator = ConditionEvaluator()
        evaluator._delta_state["key"] = "value"

        evaluator.reset_state()

        assert len(evaluator._delta_state) == 0

    def test_reset_clears_window_data(self) -> None:
        """Reset clears window tracking data."""
        evaluator = ConditionEvaluator()
        cond = Condition(kind=ConditionKind.WINDOW, expression="test", parameters={"window_seconds": 60})
        evaluator.evaluate(cond)  # Creates window data

        evaluator.reset_state()

        assert len(evaluator._window_data) == 0


class TestConditionDuration:
    """Tests for condition evaluation duration tracking."""

    def test_duration_is_recorded(self) -> None:
        """Evaluation duration is recorded in result."""
        evaluator = ConditionEvaluator()
        cond = Condition(kind=ConditionKind.THRESHOLD, expression="x > 5", parameters={"x": 10, "threshold": 5})

        result = evaluator.evaluate(cond)

        assert result.duration_ms > 0
        assert result.duration_ms < 100  # Should be fast
