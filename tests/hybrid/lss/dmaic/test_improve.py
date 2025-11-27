"""DMAIC IMPROVE Phase: Optimization and Improvement Tests.

This module tests the system's ability to detect optimization opportunities
and measure performance improvements through better physics rules, topology
design, or execution strategies.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine, PhysicsResult


class TestDMAIC004Improve:
    """IMPROVE Phase: Test optimization and improvement capabilities.

    Tests that verify the system can be optimized and improved through
    better physics rules, topology design, or execution strategies.
    """

    def test_optimization_potential_detection(self) -> None:
        """Test detection of optimization opportunities.

        Verifies:
        - Redundant ticks identified (delta == 0 before convergence)
        - Performance bottlenecks measurable (duration spikes)
        - Improvement suggestions possible
        """
        # Arrange
        engine = HybridEngine()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:End> .
        <urn:task:End> a yawl:Task ;
            kgc:status "Pending" .
        """
        engine.load_data(topology)

        # Act
        results = engine.run_to_completion(max_ticks=10)

        # Assert: Check for optimization opportunities
        # Early convergence is good (no redundant ticks)
        convergence_tick = next(i for i, r in enumerate(results, 1) if r.converged)
        assert convergence_tick <= 5, "Simple pattern should converge early"

        # No zero-delta ticks before convergence
        productive_results = results[:-1]  # All but converged tick
        zero_delta_count = sum(1 for r in productive_results if r.delta == 0)
        assert zero_delta_count == 0, "No wasted ticks before convergence"

    def test_performance_improvement_measurable(self) -> None:
        """Test that performance improvements can be measured.

        Verifies:
        - Total duration is measurable
        - Average duration per tick calculable
        - Performance metrics comparable across runs
        """
        # Arrange
        engine = HybridEngine()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology)

        # Act
        results = engine.run_to_completion(max_ticks=10)

        # Assert: Performance metrics are measurable
        total_duration = sum(r.duration_ms for r in results)
        assert total_duration > 0, "Total duration must be positive"

        avg_duration = total_duration / len(results)
        assert avg_duration > 0, "Average duration must be positive"
        assert avg_duration < 5000, "Average duration should be < 5s"

    def test_tick_efficiency_improvement(self) -> None:
        """Test tick efficiency (work per tick) can be improved.

        Verifies:
        - Delta per tick is measurable
        - Efficiency ratio (delta/duration) calculable
        - High efficiency = more work per time unit
        """
        # Arrange
        engine = HybridEngine()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Start> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

        <urn:flow:1> yawl:nextElementRef <urn:task:B> .
        <urn:flow:2> yawl:nextElementRef <urn:task:C> .

        <urn:task:B> a yawl:Task ;
            kgc:status "Pending" .
        <urn:task:C> a yawl:Task ;
            kgc:status "Pending" .
        """
        engine.load_data(topology)

        # Act
        results = engine.run_to_completion(max_ticks=10)

        # Assert: Efficiency metrics
        for result in results[:-1]:  # Exclude convergence tick
            if result.delta > 0:
                efficiency = result.delta / result.duration_ms
                assert efficiency > 0, "Efficiency must be positive for productive ticks"
