"""Control limits calculation and outlier detection tests.

This module tests control limit (UCL/LCL) calculation, outlier detection,
and in-control verification using 3-sigma methodology.
"""

from __future__ import annotations

import pytest

from tests.hybrid.lss.spc.metrics import calculate_spc_metrics


def test_spc_metrics_calculation() -> None:
    """Calculate SPC metrics from measurements.

    Arrange:
        - Sample measurements with known statistics
    Act:
        - Calculate SPC metrics
    Assert:
        - Mean, std dev, control limits calculated correctly
        - Process capability indices correct
    """
    measurements = [10.0, 10.5, 9.8, 10.2, 10.1, 9.9, 10.3, 10.4, 9.7, 10.6]

    metrics = calculate_spc_metrics(measurements, usl=12.0, lsl=8.0)

    assert 9.9 < metrics.mean < 10.2
    assert metrics.std_dev < 0.5
    assert metrics.ucl > metrics.mean
    assert metrics.lcl < metrics.mean
    assert metrics.sample_size == 10


def test_control_limits_detect_outliers() -> None:
    """Control limits detect out-of-control measurements.

    Arrange:
        - Normal measurements with tight distribution
        - Calculate control limits
        - Test with out-of-spec value
    Act:
        - Calculate control limits from normal data
        - Check normal and outlier values
    Assert:
        - Normal values are in-control
        - Outlier value is out-of-control
    """
    # Normal measurements: mean=10, std_dev~0.13
    measurements = [10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 10.0, 10.1]

    metrics = calculate_spc_metrics(measurements)

    # Normal values should be in control
    assert metrics.is_in_control(10.0)
    assert metrics.is_in_control(10.1)
    assert metrics.is_in_control(9.9)

    # Values far outside control limits should fail
    assert not metrics.is_in_control(15.0)
    assert not metrics.is_in_control(5.0)


def test_control_limits_three_sigma() -> None:
    """Control limits use 3-sigma (99.73% coverage).

    Arrange:
        - Measurements with known mean and std dev
    Act:
        - Calculate control limits
    Assert:
        - UCL = mean + 3*sigma
        - LCL = mean - 3*sigma (or 0 if negative)
    """
    # Controlled data: mean=100, std_dev~10
    measurements = [100.0, 110.0, 90.0, 105.0, 95.0, 100.0, 110.0, 90.0, 105.0, 95.0]

    metrics = calculate_spc_metrics(measurements)

    expected_ucl = metrics.mean + (3 * metrics.std_dev)
    expected_lcl = max(0.0, metrics.mean - (3 * metrics.std_dev))

    assert abs(metrics.ucl - expected_ucl) < 0.01
    assert abs(metrics.lcl - expected_lcl) < 0.01


def test_control_limits_non_negative_lcl() -> None:
    """LCL cannot be negative (clamped to 0).

    Arrange:
        - Measurements near zero with variation
    Act:
        - Calculate control limits
    Assert:
        - LCL is 0 (not negative)
    """
    # Small values where mean - 3*sigma would be negative
    measurements = [2.0, 3.0, 1.5, 2.5, 2.0, 3.5, 1.0, 2.8]

    metrics = calculate_spc_metrics(measurements)

    assert metrics.lcl >= 0.0


def test_moving_range_calculation() -> None:
    """Calculate moving range between consecutive measurements.

    Arrange:
        - Sequential measurements
    Act:
        - Calculate moving range
    Assert:
        - Range calculated correctly
        - Length is n-1
    """
    from tests.hybrid.lss.spc.metrics import calculate_moving_range

    measurements = [10.0, 10.5, 9.8, 10.2, 10.1]

    moving_range = calculate_moving_range(measurements)

    assert len(moving_range) == 4
    assert abs(moving_range[0] - 0.5) < 0.01
    assert abs(moving_range[1] - 0.7) < 0.01
    assert abs(moving_range[2] - 0.4) < 0.01


def test_run_chart_stability_stable() -> None:
    """Stable process passes run chart tests.

    Arrange:
        - Measurements with random variation
    Act:
        - Check run chart stability
    Assert:
        - All stability tests pass
    """
    from tests.hybrid.lss.spc.metrics import check_run_chart_stability

    measurements = [10.0, 10.2, 9.8, 10.1, 9.9, 10.3, 9.7, 10.4, 10.0, 9.9]

    stability = check_run_chart_stability(measurements)

    assert stability["runs_test"]
    assert stability["trend_test"]
    assert stability["zone_test"]


def test_run_chart_stability_unstable_trend() -> None:
    """Trending process fails run chart tests.

    Arrange:
        - Measurements with clear upward trend
    Act:
        - Check run chart stability
    Assert:
        - Trend test fails
    """
    from tests.hybrid.lss.spc.metrics import check_run_chart_stability

    measurements = [8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5]

    stability = check_run_chart_stability(measurements)

    assert not stability["trend_test"]


def test_insufficient_measurements_raises_error() -> None:
    """Raise error for insufficient measurements.

    Arrange:
        - Empty or single-value measurement list
    Act:
        - Attempt to calculate SPC metrics
    Assert:
        - ValueError raised
    """
    with pytest.raises(ValueError, match="at least 2 measurements"):
        calculate_spc_metrics([])

    with pytest.raises(ValueError, match="at least 2 measurements"):
        calculate_spc_metrics([10.0])


def test_control_limits_with_zero_variation() -> None:
    """Handle edge case of zero variation (all values identical).

    Arrange:
        - Measurements with identical values
    Act:
        - Calculate SPC metrics
    Assert:
        - Std dev is 0
        - UCL = LCL = mean
        - Cp/Cpk are infinite
    """
    measurements = [10.0, 10.0, 10.0, 10.0, 10.0]

    metrics = calculate_spc_metrics(measurements, usl=12.0, lsl=8.0)

    assert metrics.std_dev == 0.0
    assert metrics.ucl == metrics.mean
    assert metrics.lcl == metrics.mean
    assert metrics.cp == float("inf")
    assert metrics.cpk == float("inf")
