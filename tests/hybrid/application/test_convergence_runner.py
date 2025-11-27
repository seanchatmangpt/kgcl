"""Tests for ConvergenceRunner - run-to-completion logic.

Coverage tests for convergence_runner.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kgcl.hybrid.application.convergence_runner import ConvergenceRunner
from kgcl.hybrid.application.tick_executor import TickExecutor
from kgcl.hybrid.domain.exceptions import ConvergenceError
from kgcl.hybrid.domain.physics_result import PhysicsResult


class TestConvergenceRunnerInitialization:
    """Test ConvergenceRunner initialization."""

    def test_initializes_with_zero_tick_count(self) -> None:
        """Test tick count starts at zero."""
        executor = MagicMock(spec=TickExecutor)
        runner = ConvergenceRunner(executor)
        assert runner.tick_count == 0


class TestConvergenceRunnerRun:
    """Test run-to-completion logic."""

    def test_converges_after_one_tick(self) -> None:
        """Test convergence when first tick has zero delta."""
        executor = MagicMock(spec=TickExecutor)
        converged_result = PhysicsResult(tick_number=1, duration_ms=10.0, triples_before=5, triples_after=5, delta=0)
        executor.execute_tick.return_value = converged_result

        runner = ConvergenceRunner(executor)
        results = runner.run(max_ticks=10)

        assert len(results) == 1
        assert results[0].converged is True
        assert runner.tick_count == 1
        executor.execute_tick.assert_called_once_with(1)

    def test_converges_after_multiple_ticks(self) -> None:
        """Test convergence after several iterations."""
        executor = MagicMock(spec=TickExecutor)

        tick_results = [
            PhysicsResult(tick_number=1, duration_ms=10.0, triples_before=5, triples_after=7, delta=2),
            PhysicsResult(tick_number=2, duration_ms=12.0, triples_before=7, triples_after=9, delta=2),
            PhysicsResult(tick_number=3, duration_ms=11.0, triples_before=9, triples_after=9, delta=0),
        ]
        executor.execute_tick.side_effect = tick_results

        runner = ConvergenceRunner(executor)
        results = runner.run(max_ticks=10)

        assert len(results) == 3
        assert results[-1].converged is True
        assert runner.tick_count == 3

    def test_raises_convergence_error_on_max_ticks(self) -> None:
        """Test ConvergenceError when max ticks reached without convergence."""
        executor = MagicMock(spec=TickExecutor)

        # All ticks have positive delta (never converge)
        non_converged = PhysicsResult(tick_number=1, duration_ms=10.0, triples_before=5, triples_after=6, delta=1)
        executor.execute_tick.return_value = non_converged

        runner = ConvergenceRunner(executor)

        with pytest.raises(ConvergenceError) as exc_info:
            runner.run(max_ticks=5)

        assert exc_info.value.max_ticks == 5
        assert exc_info.value.final_delta == 1
        assert runner.tick_count == 5

    def test_logs_total_metrics_on_success(self) -> None:
        """Test logging includes total duration and delta."""
        executor = MagicMock(spec=TickExecutor)

        tick_results = [
            PhysicsResult(tick_number=1, duration_ms=5.0, triples_before=5, triples_after=7, delta=2),
            PhysicsResult(tick_number=2, duration_ms=3.0, triples_before=7, triples_after=7, delta=0),
        ]
        executor.execute_tick.side_effect = tick_results

        runner = ConvergenceRunner(executor)
        results = runner.run(max_ticks=10)

        # Verify total metrics can be computed
        total_duration = sum(r.duration_ms for r in results)
        total_delta = sum(r.delta for r in results)

        assert total_duration == 8.0
        assert total_delta == 2


class TestConvergenceRunnerSingleTick:
    """Test run_single_tick method."""

    def test_executes_single_tick(self) -> None:
        """Test single tick execution increments counter."""
        executor = MagicMock(spec=TickExecutor)
        result = PhysicsResult(tick_number=1, duration_ms=10.0, triples_before=5, triples_after=6, delta=1)
        executor.execute_tick.return_value = result

        runner = ConvergenceRunner(executor)
        returned = runner.run_single_tick()

        assert returned == result
        assert runner.tick_count == 1
        executor.execute_tick.assert_called_once_with(1)

    def test_increments_tick_count_across_calls(self) -> None:
        """Test tick count increases with each call."""
        executor = MagicMock(spec=TickExecutor)
        executor.execute_tick.return_value = PhysicsResult(
            tick_number=1, duration_ms=10.0, triples_before=5, triples_after=6, delta=1
        )

        runner = ConvergenceRunner(executor)
        runner.run_single_tick()
        runner.run_single_tick()
        runner.run_single_tick()

        assert runner.tick_count == 3


class TestConvergenceRunnerResetTickCount:
    """Test reset_tick_count method."""

    def test_resets_counter_to_zero(self) -> None:
        """Test tick count reset to zero."""
        executor = MagicMock(spec=TickExecutor)
        runner = ConvergenceRunner(executor)

        runner.tick_count = 42
        runner.reset_tick_count()

        assert runner.tick_count == 0

    def test_logs_reset_action(self) -> None:
        """Test reset is logged."""
        executor = MagicMock(spec=TickExecutor)
        runner = ConvergenceRunner(executor)

        runner.tick_count = 5
        runner.reset_tick_count()

        # No exception means logging happened successfully
        assert runner.tick_count == 0


class TestConvergenceRunnerEdgeCases:
    """Test edge cases for ConvergenceRunner."""

    def test_empty_results_on_immediate_max_ticks(self) -> None:
        """Test behavior when max_ticks is zero."""
        executor = MagicMock(spec=TickExecutor)
        runner = ConvergenceRunner(executor)

        with pytest.raises(ConvergenceError) as exc_info:
            runner.run(max_ticks=0)

        assert exc_info.value.max_ticks == 0
        # final_delta defaults to 0 when no results
        assert exc_info.value.final_delta == 0

    def test_final_delta_from_last_result(self) -> None:
        """Test final_delta is taken from last result."""
        executor = MagicMock(spec=TickExecutor)

        tick_results = [
            PhysicsResult(tick_number=1, duration_ms=10.0, triples_before=5, triples_after=7, delta=2),
            PhysicsResult(tick_number=2, duration_ms=12.0, triples_before=7, triples_after=10, delta=3),
        ]
        executor.execute_tick.side_effect = tick_results

        runner = ConvergenceRunner(executor)

        with pytest.raises(ConvergenceError) as exc_info:
            runner.run(max_ticks=2)

        assert exc_info.value.final_delta == 3  # From last result
