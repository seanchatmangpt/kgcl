"""MSA-002: Precision (Repeatability) Tests.

This module tests variation when same topology is run multiple times.
Acceptance criterion: CV (coefficient of variation) < 5%.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from tests.hybrid.lss.msa.calculations import calculate_precision
from tests.hybrid.lss.msa.metrics import MeasurementResult


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


class TestMSA002Precision:
    """MSA-002: Precision testing (repeatability validation)."""

    def test_delta_repeatability_same_topology(self, wcp43_topology: str) -> None:
        """Same topology should produce same delta across repeated runs."""
        measurements: list[MeasurementResult] = []

        # Run same topology 10 times
        for trial in range(10):
            engine = HybridEngine()
            engine.load_data(wcp43_topology)
            result = engine.apply_physics()

            measurements.append(MeasurementResult(trial=trial + 1, value=float(result.delta), operator="same_topology"))

        # All deltas should be identical (perfect repeatability)
        deltas = [m.value for m in measurements]
        assert len(set(deltas)) == 1, f"Delta varied across runs: {deltas}"

    def test_duration_ms_repeatability(self, wcp43_topology: str) -> None:
        """Duration should be consistent across repeated runs (within 20%)."""
        measurements: list[MeasurementResult] = []

        # Run same topology 10 times
        for trial in range(10):
            engine = HybridEngine()
            engine.load_data(wcp43_topology)
            result = engine.apply_physics()

            measurements.append(MeasurementResult(trial=trial + 1, value=result.duration_ms, operator="same_topology"))

        # Calculate CV
        cv = calculate_precision(measurements)

        # CV should be reasonable (< 20% for timing measurements)
        assert cv < 20.0, f"Duration CV too high: {cv}% (expected <20%)"

    def test_inspect_repeatability(self, wcp43_topology: str) -> None:
        """inspect() should return consistent results for same state."""
        engine = HybridEngine()
        engine.load_data(wcp43_topology)
        engine.apply_physics()

        # Call inspect() 10 times on same state
        statuses_list = []
        for _ in range(10):
            statuses = engine.inspect()
            statuses_list.append(statuses)

        # All inspect() calls should return identical results
        first_statuses = statuses_list[0]
        for statuses in statuses_list[1:]:
            assert statuses == first_statuses, "inspect() returned different results"

    def test_precision_calculation_perfect(self) -> None:
        """Test precision calculation with perfect repeatability."""
        # Perfect repeatability (identical values)
        m1 = MeasurementResult(1, 10.0, "op1")
        m2 = MeasurementResult(2, 10.0, "op1")
        m3 = MeasurementResult(3, 10.0, "op1")

        cv = calculate_precision([m1, m2, m3])
        assert cv == 0.0, f"Perfect repeatability should have CV=0, got {cv}"

    def test_precision_calculation_good(self) -> None:
        """Test precision calculation with good repeatability."""
        # Good repeatability (low variation)
        m1 = MeasurementResult(1, 10.0, "op1")
        m2 = MeasurementResult(2, 10.1, "op1")
        m3 = MeasurementResult(3, 9.9, "op1")

        cv = calculate_precision([m1, m2, m3])
        assert 0.0 < cv < 5.0, f"Good repeatability should have CV < 5%, got {cv}"
