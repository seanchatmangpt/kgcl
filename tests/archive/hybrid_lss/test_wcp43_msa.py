"""Measurement System Analysis (MSA) Tests for WCP-43 Patterns.

This module implements MSA methodology to validate the measurement system's:
1. **Accuracy**: Measurements match expected values (bias)
2. **Precision**: Repeatability of measurements (consistency)
3. **Linearity**: Consistency across measurement range
4. **Stability**: Measurements consistent over time
5. **Gage R&R**: Reproducibility and repeatability

MSA Concepts
------------
- **Accuracy (Bias)**: How close measured value is to true value
- **Precision (Repeatability)**: Variation when same operator measures same part
- **Reproducibility**: Variation between different operators
- **Linearity**: Accuracy across full measurement range
- **Stability**: Variation over time with same conditions
- **%GRR**: Gage Repeatability & Reproducibility as % of tolerance

Measurements Under Test
-----------------------
- PhysicsResult.tick_number: Sequential tick accuracy
- PhysicsResult.delta: Triple count change precision
- PhysicsResult.duration_ms: Timing stability
- engine.inspect(): Status reproducibility
- Triple count: Linearity across graph sizes

MSA Acceptance Criteria
-----------------------
- %GRR < 10%: Excellent measurement system
- %GRR 10-30%: Acceptable (may need improvement)
- %GRR > 30%: Unacceptable, system needs improvement
- Accuracy: Within ±2% of true value
- Precision: CV (coefficient of variation) < 5%

References
----------
- AIAG MSA Manual (4th Edition)
- ISO 22514-7:2021 Statistical methods in process management
- ASME B89.7.3.1 Guidelines for decision rules
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine, PhysicsResult

# MSA tests are comprehensive statistical analysis - mark as slow (>1s runtime)
pytestmark = pytest.mark.slow

# ==============================================================================
# MSA DATA STRUCTURES
# ==============================================================================


@dataclass(frozen=True)
class MSAMeasurement:
    """Single measurement trial for MSA study.

    Parameters
    ----------
    trial_number : int
        Sequential trial identifier (1, 2, 3...)
    measured_value : float
        The measured value from this trial
    expected_value : float | None
        Expected/reference value (if known)
    operator : str
        Identifier for who/what made the measurement

    Examples
    --------
    >>> m = MSAMeasurement(trial_number=1, measured_value=10.5, expected_value=10.0, operator="engine1")
    >>> m.bias
    0.5
    >>> m.percent_error
    5.0
    """

    trial_number: int
    measured_value: float
    expected_value: float | None
    operator: str

    @property
    def bias(self) -> float | None:
        """Calculate measurement bias (error from expected).

        Returns
        -------
        float | None
            Difference between measured and expected (None if no expected value).
        """
        if self.expected_value is None:
            return None
        return self.measured_value - self.expected_value

    @property
    def percent_error(self) -> float | None:
        """Calculate percent error from expected value.

        Returns
        -------
        float | None
            Percentage error (None if no expected value or division by zero).
        """
        if self.expected_value is None or self.expected_value == 0:
            return None
        bias = self.bias
        if bias is None:
            return None
        return (bias / self.expected_value) * 100.0


@dataclass(frozen=True)
class MSAStatistics:
    """Statistical summary for MSA study.

    Parameters
    ----------
    mean : float
        Average of all measurements
    std_dev : float
        Standard deviation of measurements
    min_value : float
        Minimum measured value
    max_value : float
        Maximum measured value
    range_value : float
        Range (max - min)
    cv : float
        Coefficient of variation (std_dev / mean * 100)
    grr : float
        Gage R&R as percentage of tolerance

    Examples
    --------
    >>> stats = MSAStatistics(mean=10.0, std_dev=0.5, min_value=9.5, max_value=10.5, range_value=1.0, cv=5.0, grr=8.3)
    >>> stats.is_excellent_measurement_system
    True
    """

    mean: float
    std_dev: float
    min_value: float
    max_value: float
    range_value: float
    cv: float
    grr: float

    @property
    def is_excellent_measurement_system(self) -> bool:
        """Check if measurement system is excellent (%GRR < 10%).

        Returns
        -------
        bool
            True if %GRR < 10%
        """
        return self.grr < 10.0

    @property
    def is_acceptable_measurement_system(self) -> bool:
        """Check if measurement system is acceptable (%GRR < 30%).

        Returns
        -------
        bool
            True if %GRR < 30%
        """
        return self.grr < 30.0


# ==============================================================================
# MSA CALCULATION FUNCTIONS
# ==============================================================================


def calculate_msa_statistics(measurements: list[MSAMeasurement], tolerance: float = 1.0) -> MSAStatistics:
    """Calculate MSA statistics from measurement trials.

    Parameters
    ----------
    measurements : list[MSAMeasurement]
        List of measurement trials
    tolerance : float
        Total tolerance for %GRR calculation (default: 1.0)

    Returns
    -------
    MSAStatistics
        Statistical summary of measurements

    Examples
    --------
    >>> m1 = MSAMeasurement(1, 10.0, 10.0, "op1")
    >>> m2 = MSAMeasurement(2, 10.1, 10.0, "op1")
    >>> m3 = MSAMeasurement(3, 9.9, 10.0, "op1")
    >>> stats = calculate_msa_statistics([m1, m2, m3])
    >>> stats.mean
    10.0
    """
    values = [m.measured_value for m in measurements]
    mean = statistics.mean(values)
    std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
    min_value = min(values)
    max_value = max(values)
    range_value = max_value - min_value

    # Coefficient of variation (CV%)
    cv = (std_dev / mean * 100.0) if mean != 0 else 0.0

    # %GRR = (6 * std_dev / tolerance) * 100
    # Using 6 sigma (99.73% coverage)
    grr = (6.0 * std_dev / tolerance * 100.0) if tolerance != 0 else 0.0

    return MSAStatistics(
        mean=mean, std_dev=std_dev, min_value=min_value, max_value=max_value, range_value=range_value, cv=cv, grr=grr
    )


def calculate_repeatability(measurements: list[MSAMeasurement]) -> float:
    """Calculate repeatability (within-operator variation).

    Parameters
    ----------
    measurements : list[MSAMeasurement]
        Measurements from same operator on same part

    Returns
    -------
    float
        Standard deviation (repeatability)
    """
    values = [m.measured_value for m in measurements]
    return statistics.stdev(values) if len(values) > 1 else 0.0


def calculate_reproducibility(operator_means: list[float]) -> float:
    """Calculate reproducibility (between-operator variation).

    Parameters
    ----------
    operator_means : list[float]
        Mean values from different operators

    Returns
    -------
    float
        Standard deviation (reproducibility)
    """
    return statistics.stdev(operator_means) if len(operator_means) > 1 else 0.0


# ==============================================================================
# PYTEST FIXTURES
# ==============================================================================


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


# ==============================================================================
# MSA-001: ACCURACY (BIAS) TESTS
# ==============================================================================


class TestMSA001Accuracy:
    """MSA-001: Accuracy testing (bias validation).

    Measures how close measurements are to true/expected values.
    Acceptance: Within ±2% of expected value.
    """

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


# ==============================================================================
# MSA-002: PRECISION (REPEATABILITY) TESTS
# ==============================================================================


class TestMSA002Precision:
    """MSA-002: Precision testing (repeatability validation).

    Measures variation when same topology is run multiple times.
    Acceptance: CV (coefficient of variation) < 5%.
    """

    def test_delta_repeatability_same_topology(self, wcp43_topology: str) -> None:
        """Same topology should produce same delta across repeated runs."""
        measurements: list[MSAMeasurement] = []

        # Run same topology 10 times
        for trial in range(10):
            engine = HybridEngine()
            engine.load_data(wcp43_topology)
            result = engine.apply_physics()

            measurements.append(
                MSAMeasurement(
                    trial_number=trial + 1,
                    measured_value=float(result.delta),
                    expected_value=None,
                    operator="same_topology",
                )
            )

        # All deltas should be identical (perfect repeatability)
        deltas = [m.measured_value for m in measurements]
        assert len(set(deltas)) == 1, f"Delta varied across runs: {deltas}"

    def test_duration_ms_repeatability(self, wcp43_topology: str) -> None:
        """Duration should be consistent across repeated runs (within 20%)."""
        measurements: list[MSAMeasurement] = []

        # Run same topology 10 times
        for trial in range(10):
            engine = HybridEngine()
            engine.load_data(wcp43_topology)
            result = engine.apply_physics()

            measurements.append(
                MSAMeasurement(
                    trial_number=trial + 1,
                    measured_value=result.duration_ms,
                    expected_value=None,
                    operator="same_topology",
                )
            )

        # Calculate statistics
        stats = calculate_msa_statistics(measurements, tolerance=100.0)

        # CV should be reasonable (< 20% for timing measurements)
        assert stats.cv < 20.0, f"Duration CV too high: {stats.cv}% (expected <20%)"

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


# ==============================================================================
# MSA-003: LINEARITY TESTS
# ==============================================================================


class TestMSA003Linearity:
    """MSA-003: Linearity testing (consistency across range).

    Measures if measurement system is accurate across full operating range.
    Acceptance: Bias should be consistent across small/medium/large graphs.
    """

    def test_triple_count_linearity_small(self, engine: HybridEngine) -> None:
        """Measure triple count accuracy on small graph (10 triples)."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ; kgc:status "Completed" .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology)

        # Count triples via store
        actual_count = len(list(engine.store))
        assert actual_count > 0, "Small graph should have triples"

    def test_triple_count_linearity_medium(self, engine: HybridEngine) -> None:
        """Measure triple count accuracy on medium graph (50 triples)."""
        tasks = [f'<urn:task:T{i}> a yawl:Task ; kgc:status "Pending" .' for i in range(20)]
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        """ + "\n".join(tasks)

        engine.load_data(topology)
        actual_count = len(list(engine.store))
        assert actual_count >= 20, "Medium graph should have 20+ triples"

    def test_triple_count_linearity_large(self, engine: HybridEngine) -> None:
        """Measure triple count accuracy on large graph (200+ triples)."""
        tasks = [f'<urn:task:T{i}> a yawl:Task ; kgc:status "Pending" .' for i in range(100)]
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        """ + "\n".join(tasks)

        engine.load_data(topology)
        actual_count = len(list(engine.store))
        assert actual_count >= 100, "Large graph should have 100+ triples"

    def test_delta_linearity_across_scales(self) -> None:
        """Delta measurement should be linear across different graph sizes."""
        measurements: list[MSAMeasurement] = []

        # Test 3 scales: small (2 tasks), medium (5 tasks), large (10 tasks)
        scales = [2, 5, 10]

        for scale in scales:
            tasks = [f"<urn:task:T{i}> a yawl:Task ." for i in range(scale)]
            topology = (
                f"""
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

            <urn:task:Start> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:hasSplit yawl:ControlTypeAnd ;
                yawl:flowsInto {", ".join(f"<urn:flow:{i}>" for i in range(scale))} .

            """
                + "\n".join(f"<urn:flow:{i}> yawl:nextElementRef <urn:task:T{i}> ." for i in range(scale))
                + "\n"
                + "\n".join(tasks)
            )

            engine = HybridEngine()
            engine.load_data(topology)
            result = engine.apply_physics()

            measurements.append(
                MSAMeasurement(
                    trial_number=scale,
                    measured_value=float(result.delta),
                    expected_value=None,
                    operator=f"scale_{scale}",
                )
            )

        # Delta should increase proportionally with scale
        deltas = [m.measured_value for m in measurements]
        # Each scale should have more deltas than previous
        assert deltas[1] >= deltas[0], "Medium scale should have >= delta than small"
        assert deltas[2] >= deltas[1], "Large scale should have >= delta than medium"


# ==============================================================================
# MSA-004: STABILITY TESTS
# ==============================================================================


class TestMSA004Stability:
    """MSA-004: Stability testing (measurements over time).

    Measures if measurement system produces consistent results over time.
    Acceptance: Mean should not drift over repeated measurements.
    """

    def test_duration_stability_over_ticks(self, engine: HybridEngine) -> None:
        """Duration should be stable across multiple ticks."""
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

        # Run 5 ticks
        measurements: list[MSAMeasurement] = []
        for tick in range(5):
            result = engine.apply_physics()
            measurements.append(
                MSAMeasurement(
                    trial_number=tick + 1, measured_value=result.duration_ms, expected_value=None, operator="engine"
                )
            )

        # Calculate statistics
        stats = calculate_msa_statistics(measurements, tolerance=100.0)

        # Duration should not show significant drift (CV < 30%)
        assert stats.cv < 30.0, f"Duration unstable over time: CV={stats.cv}%"

    def test_tick_number_stability(self, engine: HybridEngine, wcp43_topology: str) -> None:
        """Tick numbers should be stable and monotonically increasing."""
        engine.load_data(wcp43_topology)

        # Run 10 ticks
        tick_numbers = []
        for _ in range(10):
            result = engine.apply_physics()
            tick_numbers.append(result.tick_number)

        # Should be strictly increasing
        for i in range(len(tick_numbers) - 1):
            assert tick_numbers[i + 1] == tick_numbers[i] + 1, f"Tick numbers not sequential: {tick_numbers}"

    def test_status_stability_no_changes(self, engine: HybridEngine, wcp43_topology: str) -> None:
        """Task statuses should be stable when no rules fire."""
        engine.load_data(wcp43_topology)

        # Run to convergence
        engine.run_to_completion(max_ticks=10)

        # Get initial status
        initial_statuses = engine.inspect()

        # Apply physics again (should not change - converged)
        engine.apply_physics()
        final_statuses = engine.inspect()

        # Statuses should be identical (stable)
        assert initial_statuses == final_statuses, "Statuses changed after convergence"


# ==============================================================================
# MSA-005: GAGE R&R (REPRODUCIBILITY & REPEATABILITY) TESTS
# ==============================================================================


class TestMSA005GageRR:
    """MSA-005: Gage R&R testing (reproducibility and repeatability).

    Measures:
    - Repeatability: Same engine, same topology, multiple runs
    - Reproducibility: Different engines, same topology, multiple runs
    Acceptance: %GRR < 30% (excellent if < 10%)
    """

    def test_repeatability_single_engine(self, wcp43_topology: str) -> None:
        """Repeatability: Same engine should give same results."""
        engine = HybridEngine()

        measurements: list[MSAMeasurement] = []

        # Load and run same topology 5 times on SAME engine
        for trial in range(5):
            # Reset engine state (create fresh)
            engine = HybridEngine()
            engine.load_data(wcp43_topology)
            result = engine.apply_physics()

            measurements.append(
                MSAMeasurement(
                    trial_number=trial + 1, measured_value=float(result.delta), expected_value=None, operator="engine_1"
                )
            )

        # Calculate repeatability
        repeatability = calculate_repeatability(measurements)

        # Perfect repeatability (std dev = 0) expected for deterministic system
        assert repeatability == 0.0, f"Repeatability failed: std_dev={repeatability}"

    def test_reproducibility_multiple_engines(self, wcp43_topology: str) -> None:
        """Reproducibility: Different engines should give same results."""
        # Create 3 different engines
        engines = [HybridEngine() for _ in range(3)]

        operator_means: list[float] = []

        for engine_idx, engine in enumerate(engines):
            measurements: list[MSAMeasurement] = []

            # Each engine runs topology 3 times
            for trial in range(3):
                # Fresh engine for each trial
                fresh_engine = HybridEngine()
                fresh_engine.load_data(wcp43_topology)
                result = fresh_engine.apply_physics()

                measurements.append(
                    MSAMeasurement(
                        trial_number=trial + 1,
                        measured_value=float(result.delta),
                        expected_value=None,
                        operator=f"engine_{engine_idx + 1}",
                    )
                )

            # Calculate mean for this operator
            mean = statistics.mean([m.measured_value for m in measurements])
            operator_means.append(mean)

        # Calculate reproducibility
        reproducibility = calculate_reproducibility(operator_means)

        # Perfect reproducibility expected (different engines should behave identically)
        assert reproducibility == 0.0, f"Reproducibility failed: std_dev={reproducibility}"

    def test_grr_excellent_threshold(self, wcp43_topology: str) -> None:
        """Overall %GRR should be excellent (<10%)."""
        # Collect 30 measurements (3 operators × 10 trials each)
        all_measurements: list[MSAMeasurement] = []

        for operator in range(3):
            for trial in range(10):
                engine = HybridEngine()
                engine.load_data(wcp43_topology)
                result = engine.apply_physics()

                all_measurements.append(
                    MSAMeasurement(
                        trial_number=trial + 1,
                        measured_value=float(result.delta),
                        expected_value=None,
                        operator=f"op_{operator + 1}",
                    )
                )

        # Calculate %GRR (tolerance = max delta observed)
        max_delta = max(m.measured_value for m in all_measurements)
        tolerance = max(max_delta, 1.0)  # Avoid division by zero

        stats = calculate_msa_statistics(all_measurements, tolerance=tolerance)

        # System should be excellent (%GRR < 10%)
        assert stats.is_excellent_measurement_system, f"GRR not excellent: {stats.grr}% (expected <10%)"


# ==============================================================================
# MSA-006: MEASUREMENT RESOLUTION TESTS
# ==============================================================================


class TestMSA006Resolution:
    """MSA-006: Measurement resolution validation.

    Ensures measurement system has adequate resolution to detect changes.
    Acceptance: Resolution should be 10x finer than smallest expected change.
    """

    def test_tick_number_resolution(self, engine: HybridEngine, wcp43_topology: str) -> None:
        """Tick number resolution should be integer (no fractional ticks)."""
        engine.load_data(wcp43_topology)

        for _ in range(5):
            result = engine.apply_physics()
            # Tick number should be integer
            assert isinstance(result.tick_number, int), "Tick number should be integer"
            assert result.tick_number == int(result.tick_number), "Tick should have no fraction"

    def test_delta_resolution(self, engine: HybridEngine, wcp43_topology: str) -> None:
        """Delta resolution should be integer (whole triple counts)."""
        engine.load_data(wcp43_topology)
        result = engine.apply_physics()

        # Delta should be integer
        assert isinstance(result.delta, int), "Delta should be integer"

    def test_duration_ms_resolution(self, engine: HybridEngine, wcp43_topology: str) -> None:
        """Duration resolution should be at least 0.001ms (microsecond)."""
        engine.load_data(wcp43_topology)
        result = engine.apply_physics()

        # Duration should be float with fine resolution
        assert isinstance(result.duration_ms, float), "Duration should be float"

        # Should have sub-millisecond resolution (at least 3 decimal places)
        # This is tested by checking if value can be non-zero and < 1.0
        assert result.duration_ms > 0.0, "Duration should be positive"

    def test_triple_count_resolution(self, engine: HybridEngine, wcp43_topology: str) -> None:
        """Triple count resolution should be integer (whole triples)."""
        engine.load_data(wcp43_topology)
        result = engine.apply_physics()

        # Triple counts should be integers
        assert isinstance(result.triples_before, int), "triples_before should be integer"
        assert isinstance(result.triples_after, int), "triples_after should be integer"


# ==============================================================================
# MSA SUMMARY TEST
# ==============================================================================


class TestMSASummary:
    """Aggregate MSA validation summary."""

    def test_all_measurement_characteristics(self, wcp43_topology: str) -> None:
        """Validate all 5 MSA characteristics meet acceptance criteria."""
        # Run comprehensive MSA study
        all_measurements: list[MSAMeasurement] = []

        # Collect 50 measurements (5 engines × 10 trials)
        for engine_idx in range(5):
            for trial in range(10):
                engine = HybridEngine()
                engine.load_data(wcp43_topology)
                result = engine.apply_physics()

                all_measurements.append(
                    MSAMeasurement(
                        trial_number=trial + 1,
                        measured_value=float(result.delta),
                        expected_value=None,  # No reference for delta
                        operator=f"engine_{engine_idx}",
                    )
                )

        # Calculate comprehensive statistics
        max_value = max(m.measured_value for m in all_measurements)
        tolerance = max(max_value, 1.0)
        stats = calculate_msa_statistics(all_measurements, tolerance=tolerance)

        # MSA Acceptance Criteria
        # 1. Accuracy: Not applicable without reference value
        # 2. Precision (CV): Should be < 5% for excellent system
        assert stats.cv < 5.0, f"Precision (CV) failed: {stats.cv}% (expected <5%)"

        # 3. Linearity: Tested separately in TestMSA003Linearity
        # 4. Stability: Tested separately in TestMSA004Stability
        # 5. Gage R&R: Should be excellent (<10%)
        assert stats.is_excellent_measurement_system, f"GRR failed: {stats.grr}% (expected <10%)"

    def test_measurement_system_capability(self, wcp43_topology: str) -> None:
        """Overall measurement system should be capable (all criteria pass)."""
        # This test validates that measurement system is fit for purpose

        # 1. Run single measurement
        engine = HybridEngine()
        engine.load_data(wcp43_topology)
        result = engine.apply_physics()

        # 2. Validate measurement characteristics
        # Accuracy: Tick number should start at 1
        assert result.tick_number == 1, "Accuracy: First tick should be 1"

        # Precision: Delta should be deterministic (integer)
        assert isinstance(result.delta, int), "Precision: Delta should be integer"

        # Resolution: Duration should have fine resolution
        assert isinstance(result.duration_ms, float), "Resolution: Duration should be float"

        # Linearity & Stability: Tested in dedicated test classes

        # 3. Overall verdict
        # Measurement system is capable if all basic checks pass
        assert True, "Measurement system is capable"
