"""DMAIC MEASURE Phase: Execution Metrics Validation Tests.

This module tests measurable execution properties: tick counts, deltas, durations,
triple counts, and convergence metrics.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine, PhysicsResult


class TestDMAIC002Measure:
    """MEASURE Phase: Validate measurable execution metrics.

    Tests that measure concrete execution properties: tick counts, deltas,
    durations, triple counts, convergence.
    """

    def test_tick_count_measurement(self) -> None:
        """Test that tick counts increment correctly during execution.

        Verifies:
        - Tick numbers start at 1
        - Tick numbers increment sequentially
        - Tick count matches results length
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
        <urn:task:B> a yawl:Task ;
            kgc:status "Pending" .
        """
        engine.load_data(topology)

        # Act
        results = engine.run_to_completion(max_ticks=10)

        # Assert
        assert len(results) > 0, "Must have at least one tick"
        for i, result in enumerate(results, start=1):
            assert result.tick_number == i, f"Tick {i} number mismatch"

    def test_delta_measurement(self) -> None:
        """Test that delta measurements track triple changes.

        Verifies:
        - Delta = triples_after - triples_before
        - Delta >= 0 (monotonic growth)
        - Convergence when delta == 0
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

        # Assert
        for result in results:
            calculated_delta = result.triples_after - result.triples_before
            assert result.delta == calculated_delta, "Delta calculation must match"
            assert result.delta >= 0, "Delta must be non-negative (monotonic)"

        # Last result should have converged (delta == 0)
        assert results[-1].converged, "Final tick must converge"
        assert results[-1].delta == 0, "Converged tick has delta 0"

    def test_duration_measurement(self) -> None:
        """Test that duration is measured in milliseconds.

        Verifies:
        - Duration is positive
        - Duration is in milliseconds (reasonable range)
        - Duration is measured per tick
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
        results = engine.run_to_completion(max_ticks=5)

        # Assert
        for result in results:
            assert result.duration_ms > 0, "Duration must be positive"
            assert result.duration_ms < 10000, "Duration should be < 10s (10000ms)"

    def test_triple_count_growth(self) -> None:
        """Test that triple counts grow monotonically.

        Verifies:
        - triples_after >= triples_before (always)
        - Total growth matches sum of deltas
        - Final count is maximum
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

        # Assert
        for result in results:
            assert result.triples_after >= result.triples_before, "Triples must grow monotonically"

        # Total growth
        total_delta = sum(r.delta for r in results)
        initial_count = results[0].triples_before
        final_count = results[-1].triples_after
        assert final_count - initial_count == total_delta, "Total growth must match sum of deltas"
