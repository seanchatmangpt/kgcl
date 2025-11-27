"""MSA-005: Gage R&R (Reproducibility & Repeatability) Tests.

This module tests:
- Repeatability: Same engine, same topology, multiple runs
- Reproducibility: Different engines, same topology, multiple runs

Acceptance criterion: %GRR < 30% (excellent if < 10%)
"""

from __future__ import annotations

import statistics

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from tests.hybrid.lss.msa.calculations import calculate_grr, calculate_repeatability, calculate_reproducibility
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


class TestMSA005GageRR:
    """MSA-005: Gage R&R testing (reproducibility and repeatability)."""

    def test_repeatability_single_engine(self, wcp43_topology: str) -> None:
        """Repeatability: Same engine should give same results."""
        measurements: list[MeasurementResult] = []

        # Load and run same topology 5 times on fresh engines
        for trial in range(5):
            engine = HybridEngine()
            engine.load_data(wcp43_topology)
            result = engine.apply_physics()

            measurements.append(MeasurementResult(trial=trial + 1, value=float(result.delta), operator="engine_1"))

        # Calculate repeatability
        repeatability = calculate_repeatability(measurements)

        # Perfect repeatability (std dev = 0) expected for deterministic system
        assert repeatability == 0.0, f"Repeatability failed: std_dev={repeatability}"

    def test_reproducibility_multiple_engines(self, wcp43_topology: str) -> None:
        """Reproducibility: Different engines should give same results."""
        # Create 3 different engine instances
        operator_means: list[float] = []

        for engine_idx in range(3):
            measurements: list[MeasurementResult] = []

            # Each engine runs topology 3 times
            for trial in range(3):
                engine = HybridEngine()
                engine.load_data(wcp43_topology)
                result = engine.apply_physics()

                measurements.append(
                    MeasurementResult(trial=trial + 1, value=float(result.delta), operator=f"engine_{engine_idx + 1}")
                )

            # Calculate mean for this operator
            mean = statistics.mean([m.value for m in measurements])
            operator_means.append(mean)

        # Calculate reproducibility
        reproducibility = calculate_reproducibility(operator_means)

        # Perfect reproducibility expected (different engines should behave identically)
        assert reproducibility == 0.0, f"Reproducibility failed: std_dev={reproducibility}"

    def test_grr_excellent_threshold(self, wcp43_topology: str) -> None:
        """Overall %GRR should be excellent (<10%)."""
        # Collect 30 measurements (3 operators × 10 trials each)
        all_measurements: list[MeasurementResult] = []

        for operator in range(3):
            for trial in range(10):
                engine = HybridEngine()
                engine.load_data(wcp43_topology)
                result = engine.apply_physics()

                all_measurements.append(
                    MeasurementResult(trial=trial + 1, value=float(result.delta), operator=f"op_{operator + 1}")
                )

        # Calculate %GRR (tolerance = max delta observed)
        max_delta = max(m.value for m in all_measurements)
        tolerance = max(max_delta, 1.0)  # Avoid division by zero

        grr = calculate_grr(all_measurements, tolerance=tolerance)

        # System should be excellent (%GRR < 10%)
        assert grr.is_excellent, f"GRR not excellent: {grr.grr_percent}% (expected <10%)"

    def test_grr_calculation_perfect(self) -> None:
        """Test GRR calculation with perfect repeatability and reproducibility."""
        # Perfect measurements (all identical)
        m1 = MeasurementResult(1, 10.0, "op1")
        m2 = MeasurementResult(2, 10.0, "op1")
        m3 = MeasurementResult(3, 10.0, "op2")
        m4 = MeasurementResult(4, 10.0, "op2")

        grr = calculate_grr([m1, m2, m3, m4], tolerance=1.0)

        assert grr.grr_percent == 0.0, f"Perfect measurements should have %GRR=0, got {grr.grr_percent}"
        assert grr.is_excellent, "Perfect measurements should be excellent"
        assert grr.repeatability == 0.0, "Perfect repeatability expected"
        assert grr.reproducibility == 0.0, "Perfect reproducibility expected"

    def test_grr_calculation_excellent(self) -> None:
        """Test GRR calculation with excellent measurement system."""
        # Excellent measurements (very low variation)
        m1 = MeasurementResult(1, 10.0, "op1")
        m2 = MeasurementResult(2, 10.01, "op1")
        m3 = MeasurementResult(3, 10.0, "op2")
        m4 = MeasurementResult(4, 10.01, "op2")

        grr = calculate_grr([m1, m2, m3, m4], tolerance=1.0)

        assert grr.is_excellent, f"Should be excellent, got %GRR={grr.grr_percent}"
        assert grr.grr_percent < 10.0, f"%GRR should be < 10%, got {grr.grr_percent}"

    def test_grr_calculation_acceptable(self) -> None:
        """Test GRR calculation with acceptable measurement system."""
        # Acceptable measurements (moderate variation)
        m1 = MeasurementResult(1, 10.0, "op1")
        m2 = MeasurementResult(2, 10.05, "op1")
        m3 = MeasurementResult(3, 10.02, "op2")
        m4 = MeasurementResult(4, 10.03, "op2")

        grr = calculate_grr([m1, m2, m3, m4], tolerance=1.0)

        # Should be acceptable (< 30%)
        assert grr.grr_percent < 30.0, f"Should be acceptable, got %GRR={grr.grr_percent}"
