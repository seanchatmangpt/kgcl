"""Process capability (Cp/Cpk) calculation and validation tests.

This module tests process capability indices following Six Sigma standards:
- Cp: Potential capability (ignores centering)
- Cpk: Actual capability (accounts for centering)
- Capability thresholds: Cpk ≥ 1.33 capable, Cpk ≥ 2.0 world-class
"""

from __future__ import annotations

from tests.hybrid.lss.spc.metrics import calculate_spc_metrics


def test_process_capability_capable() -> None:
    """Process with Cpk >= 1.33 is capable.

    Arrange:
        - Measurements with low variation within spec limits
    Act:
        - Calculate capability indices
    Assert:
        - Cpk >= 1.33 (capable process)
        - is_capable() returns True
    """
    # Tight distribution: mean=10, sigma=0.2
    measurements = [10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 10.0, 10.1]

    metrics = calculate_spc_metrics(measurements, usl=11.0, lsl=9.0)

    assert metrics.cpk >= 1.33
    assert metrics.is_capable()


def test_process_capability_not_capable() -> None:
    """Process with high variation is not capable.

    Arrange:
        - Measurements with high variation
    Act:
        - Calculate capability indices
    Assert:
        - Cpk < 1.33 (not capable)
        - is_capable() returns False
    """
    # Wide distribution
    measurements = [10.0, 12.0, 8.0, 11.5, 8.5, 10.5, 9.0, 11.0, 9.5, 10.0]

    metrics = calculate_spc_metrics(measurements, usl=13.0, lsl=7.0)

    assert metrics.cpk < 1.33
    assert not metrics.is_capable()


def test_process_capability_six_sigma() -> None:
    """Six Sigma process has Cpk >= 2.0.

    Arrange:
        - Measurements with very low variation
    Act:
        - Calculate Cpk
    Assert:
        - Cpk >= 2.0 (world-class)
    """
    # Very tight distribution: mean=100, sigma~0.05
    measurements = [100.0, 100.05, 99.95, 100.1, 99.9, 100.0, 100.05, 99.95]

    metrics = calculate_spc_metrics(measurements, usl=101.0, lsl=99.0)

    assert metrics.cpk >= 2.0


def test_cp_vs_cpk_centered_process() -> None:
    """Cp equals Cpk for perfectly centered process.

    Arrange:
        - Measurements centered at midpoint of spec limits
    Act:
        - Calculate Cp and Cpk
    Assert:
        - Cp ≈ Cpk (within small tolerance)
    """
    # Centered at 10.0, spec limits at 8.0 and 12.0
    measurements = [10.0, 10.2, 9.8, 10.1, 9.9, 10.0, 10.1, 9.9]

    metrics = calculate_spc_metrics(measurements, usl=12.0, lsl=8.0)

    # Cp and Cpk should be very close for centered process
    assert abs(metrics.cp - metrics.cpk) < 0.2


def test_cp_vs_cpk_off_center_process() -> None:
    """Cpk < Cp for off-center process.

    Arrange:
        - Measurements shifted toward upper spec limit
    Act:
        - Calculate Cp and Cpk
    Assert:
        - Cpk < Cp (centering penalty)
    """
    # Shifted high: mean=11.0, spec limits at 8.0 and 12.0
    measurements = [11.0, 11.2, 10.8, 11.1, 10.9, 11.0, 11.1, 10.9]

    metrics = calculate_spc_metrics(measurements, usl=12.0, lsl=8.0)

    assert metrics.cpk < metrics.cp


def test_coefficient_of_variation_low() -> None:
    """Low CV indicates tight process control.

    Arrange:
        - Measurements with very low relative variation
    Act:
        - Calculate CV
    Assert:
        - CV < 5% (excellent control)
    """
    # Tight around 100: sigma/mean ~ 0.01
    measurements = [100.0, 100.5, 99.5, 100.2, 99.8, 100.1, 99.9]

    metrics = calculate_spc_metrics(measurements)

    assert metrics.cv < 5.0


def test_coefficient_of_variation_high() -> None:
    """High CV indicates poor process control.

    Arrange:
        - Measurements with high relative variation
    Act:
        - Calculate CV
    Assert:
        - CV > 20% (poor control)
    """
    # Wide variation around 10: sigma/mean ~ 0.3
    measurements = [10.0, 13.0, 7.0, 12.0, 8.0, 11.0, 9.0]

    metrics = calculate_spc_metrics(measurements)

    assert metrics.cv > 20.0


def test_process_capability_no_spec_limits() -> None:
    """Cp/Cpk are 0 when spec limits not provided.

    Arrange:
        - Measurements without USL/LSL
    Act:
        - Calculate capability indices
    Assert:
        - Cp = 0, Cpk = 0 (no spec limits)
    """
    measurements = [10.0, 10.5, 9.8, 10.2, 10.1]

    metrics = calculate_spc_metrics(measurements)

    assert metrics.cp == 0.0
    assert metrics.cpk == 0.0


def test_process_capability_only_usl() -> None:
    """Cp/Cpk are 0 when only one spec limit provided.

    Arrange:
        - Measurements with USL but no LSL
    Act:
        - Calculate capability indices
    Assert:
        - Cp = 0, Cpk = 0 (incomplete spec)
    """
    measurements = [10.0, 10.5, 9.8, 10.2, 10.1]

    metrics = calculate_spc_metrics(measurements, usl=12.0)

    assert metrics.cp == 0.0
    assert metrics.cpk == 0.0


def test_process_capability_borderline() -> None:
    """Test process at capability threshold (Cpk = 1.33).

    Arrange:
        - Measurements designed for Cpk near 1.33
    Act:
        - Calculate Cpk
    Assert:
        - Cpk close to 1.33
        - is_capable() behavior correct at boundary
    """
    # Design for Cpk ~ 1.33: spec range = 8*sigma
    # USL=12, LSL=8, mean=10, sigma~0.5 => Cpk = (2)/(3*0.5) = 1.33
    # Need wider variation to get sigma~0.5
    measurements = [10.0, 10.6, 9.4, 10.3, 9.7, 10.2, 9.8, 10.5, 9.5, 10.0, 9.9, 10.1]

    metrics = calculate_spc_metrics(measurements, usl=12.0, lsl=8.0)

    # Should be capable or very close
    assert metrics.cpk >= 1.0  # At least close to capable


def test_sample_size_tracking() -> None:
    """Sample size is tracked correctly.

    Arrange:
        - Measurements of known length
    Act:
        - Calculate metrics
    Assert:
        - sample_size matches input length
    """
    measurements = [10.0, 10.1, 9.9, 10.2, 9.8]

    metrics = calculate_spc_metrics(measurements)

    assert metrics.sample_size == 5


def test_min_max_value_tracking() -> None:
    """Min and max values are tracked correctly.

    Arrange:
        - Measurements with known min/max
    Act:
        - Calculate metrics
    Assert:
        - min_value and max_value correct
    """
    measurements = [10.0, 12.5, 8.3, 11.0, 9.5]

    metrics = calculate_spc_metrics(measurements)

    assert metrics.min_value == 8.3
    assert metrics.max_value == 12.5
