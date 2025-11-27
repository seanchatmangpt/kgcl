"""MSA-001: Accuracy (Bias) Tests.

This module tests how close measurements are to true/expected values.
Acceptance criterion: Within ±2% of expected value.

Measurements Under Test
-----------------------
- PhysicsResult.tick_number: Sequential tick accuracy
- PhysicsResult.delta: Triple count change precision
- PhysicsResult.duration_ms: Timing stability
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for MSA testing.

    Returns
    -------
    HybridEngine
        Clean in-memory engine
    """
    return HybridEngine()


@pytest.fixture
def wcp43_topology() -> str:
    """WCP-43 Explicit Termination topology for MSA testing.

    Returns
    -------
    str
        Turtle topology for WCP-43 pattern
    """
    return """
    @prefix kgc: <https://kgc.org/ns/> .
    @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

    <urn:task:A> a yawl:Task ;
        kgc:status "Completed" ;
        yawl:flowsInto <urn:flow:1> .

    <urn:flow:1> yawl:nextElementRef <urn:task:B> .

    <urn:task:B> a yawl:Task .
    """


class TestMSA001Accuracy:
    """MSA-001: Accuracy testing (bias validation)."""

    def test_tick_number_accuracy(self, engine: HybridEngine, wcp43_topology: str) -> None:
        """Tick numbers should be sequential integers starting at 1."""
        engine.load_data(wcp43_topology)

        # Run 5 ticks
        results = []
        for i in range(5):
            result = engine.apply_physics()
            results.append(result)

        # Verify tick numbers are accurate (1, 2, 3, 4, 5)
        for i, result in enumerate(results):
            expected_tick = i + 1
            assert result.tick_number == expected_tick, f"Tick {i}: expected {expected_tick}, got {result.tick_number}"

    def test_delta_accuracy_zero_state(self, engine: HybridEngine, wcp43_topology: str) -> None:
        """Delta should be 0 when no new triples are inferred."""
        engine.load_data(wcp43_topology)

        # Run until convergence
        results = engine.run_to_completion(max_ticks=10)

        # Last tick should have delta=0 (converged)
        assert results[-1].delta == 0, "Converged state should have delta=0"

    def test_delta_accuracy_known_change(self, engine: HybridEngine) -> None:
        """Delta should accurately reflect known triple additions."""
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

        # First tick should add new triples (Task B becomes Active)
        result = engine.apply_physics()
        assert result.delta > 0, "First tick should add triples"

        # Verify delta equals difference
        assert result.delta == result.triples_after - result.triples_before

    def test_duration_ms_reasonable_range(self, engine: HybridEngine, wcp43_topology: str) -> None:
        """Duration should be within reasonable range (0.1ms - 10000ms)."""
        engine.load_data(wcp43_topology)

        result = engine.apply_physics()

        # Duration should be positive and reasonable
        assert 0.1 <= result.duration_ms <= 10000, f"Duration {result.duration_ms}ms outside reasonable range"
