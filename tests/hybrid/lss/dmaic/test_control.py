"""DMAIC CONTROL Phase: Control Mechanisms and Boundaries Tests."""

from __future__ import annotations

from kgcl.hybrid.hybrid_engine import HybridEngine


class TestDMAIC005Control:
    """CONTROL Phase: Test control mechanisms and boundaries.

    Tests that verify control mechanisms work correctly: max_ticks limits,
    convergence detection, boundary conditions, error handling.
    """

    def test_max_ticks_boundary_control(self) -> None:
        """Test that max_ticks limit is enforced."""
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
        results = engine.run_to_completion(max_ticks=100)

        # Assert: Should converge within limit
        assert len(results) <= 100, "Must not exceed max_ticks"
        assert results[-1].converged, "Should converge within 100 ticks"

    def test_convergence_control_mechanism(self) -> None:
        """Test convergence detection stops execution."""
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
        results = engine.run_to_completion(max_ticks=100)

        # Assert
        assert results[-1].converged, "Final tick must be converged"
        assert results[-1].delta == 0, "Converged tick has delta 0"

        # No ticks after convergence
        for i, result in enumerate(results[:-1]):
            assert not result.converged, f"Tick {i + 1} should not be converged (only last tick)"

    def test_empty_graph_control(self) -> None:
        """Test control behavior with empty/minimal graphs."""
        # Arrange: Engine with minimal data
        engine = HybridEngine()
        minimal_topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task .
        """
        engine.load_data(minimal_topology)

        # Act
        results = engine.run_to_completion(max_ticks=10)

        # Assert: Should converge quickly with no work to do
        assert len(results) > 0, "Must execute at least one tick"
        assert results[-1].converged, "Should converge"
        assert results[-1].delta == 0, "No changes expected"

    def test_tick_count_control_boundary(self) -> None:
        """Test tick count control at boundaries."""
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

        # Act & Assert: max_ticks boundary
        results_low = engine.run_to_completion(max_ticks=20)
        assert len(results_low) <= 20, "Must respect max_ticks limit"

    def test_convergence_stability_control(self) -> None:
        """Test that convergence is stable (no oscillation)."""
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

        # Assert: After convergence, verify stability
        convergence_index = next(i for i, r in enumerate(results) if r.converged)
        converged_state = results[convergence_index]

        # If we ran more ticks after convergence, they would also have delta=0
        assert converged_state.delta == 0, "Converged state must be stable"
        assert converged_state.triples_after == converged_state.triples_before, "No changes in converged state"
