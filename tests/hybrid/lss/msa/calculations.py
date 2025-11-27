"""MSA calculation functions with comprehensive doctests.

This module provides statistical calculations for Measurement System Analysis,
including precision, repeatability, reproducibility, and Gage R&R metrics.
"""

from __future__ import annotations

import statistics

from tests.hybrid.lss.msa.metrics import GageRR, MeasurementResult


def calculate_precision(measurements: list[MeasurementResult]) -> float:
    """Calculate precision as coefficient of variation (CV%).

    Parameters
    ----------
    measurements : list[MeasurementResult]
        List of measurement trials

    Returns
    -------
    float
        Coefficient of variation as percentage (std_dev / mean * 100)

    Notes
    -----
    CV% = (σ / μ) * 100
    - Lower CV% indicates better precision
    - Acceptance criterion: CV% < 5%

    Examples
    --------
    >>> # Excellent precision (CV < 5%)
    >>> m1 = MeasurementResult(1, 10.0, "op1")
    >>> m2 = MeasurementResult(2, 10.1, "op1")
    >>> m3 = MeasurementResult(3, 9.9, "op1")
    >>> cv = calculate_precision([m1, m2, m3])
    >>> 0.0 < cv < 5.0
    True

    >>> # Poor precision (high variation)
    >>> m4 = MeasurementResult(1, 10.0, "op2")
    >>> m5 = MeasurementResult(2, 15.0, "op2")
    >>> m6 = MeasurementResult(3, 8.0, "op2")
    >>> cv2 = calculate_precision([m4, m5, m6])
    >>> cv2 > 10.0
    True

    >>> # Single measurement (zero std dev)
    >>> m7 = MeasurementResult(1, 10.0, "op3")
    >>> calculate_precision([m7])
    0.0

    >>> # Perfect repeatability (identical values)
    >>> m8 = MeasurementResult(1, 10.0, "op4")
    >>> m9 = MeasurementResult(2, 10.0, "op4")
    >>> m10 = MeasurementResult(3, 10.0, "op4")
    >>> calculate_precision([m8, m9, m10])
    0.0
    """
    values = [m.value for m in measurements]
    mean = statistics.mean(values)
    std_dev = statistics.stdev(values) if len(values) > 1 else 0.0

    if mean == 0:
        return 0.0

    return (std_dev / mean) * 100.0


def calculate_repeatability(measurements: list[MeasurementResult]) -> float:
    """Calculate repeatability (within-operator variation).

    Parameters
    ----------
    measurements : list[MeasurementResult]
        Measurements from same operator on same part

    Returns
    -------
    float
        Standard deviation (repeatability)

    Notes
    -----
    Repeatability is the variation in measurements taken by a single
    operator/instrument on the same part under the same conditions.

    Examples
    --------
    >>> # Perfect repeatability
    >>> m1 = MeasurementResult(1, 10.0, "op1")
    >>> m2 = MeasurementResult(2, 10.0, "op1")
    >>> m3 = MeasurementResult(3, 10.0, "op1")
    >>> calculate_repeatability([m1, m2, m3])
    0.0

    >>> # Good repeatability (low variation)
    >>> m4 = MeasurementResult(1, 10.0, "op1")
    >>> m5 = MeasurementResult(2, 10.1, "op1")
    >>> m6 = MeasurementResult(3, 9.9, "op1")
    >>> r = calculate_repeatability([m4, m5, m6])
    >>> 0.0 < r < 0.2
    True

    >>> # Single measurement
    >>> m7 = MeasurementResult(1, 10.0, "op1")
    >>> calculate_repeatability([m7])
    0.0
    """
    values = [m.value for m in measurements]
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

    Notes
    -----
    Reproducibility is the variation in average measurements taken by
    different operators/instruments on the same parts.

    Examples
    --------
    >>> # Perfect reproducibility (all operators agree)
    >>> calculate_reproducibility([10.0, 10.0, 10.0])
    0.0

    >>> # Good reproducibility (slight operator differences)
    >>> r = calculate_reproducibility([10.0, 10.1, 9.9])
    >>> 0.0 < r < 0.2
    True

    >>> # Poor reproducibility (large operator bias)
    >>> r2 = calculate_reproducibility([10.0, 12.0, 8.0])
    >>> r2 > 1.0
    True

    >>> # Single operator
    >>> calculate_reproducibility([10.0])
    0.0

    >>> # Two operators with difference
    >>> r3 = calculate_reproducibility([10.0, 11.0])
    >>> abs(r3 - 0.7071067811865476) < 0.0001
    True
    """
    return statistics.stdev(operator_means) if len(operator_means) > 1 else 0.0


def calculate_grr(measurements: list[MeasurementResult], tolerance: float) -> GageRR:
    """Calculate Gage Repeatability and Reproducibility (R&R) statistics.

    Parameters
    ----------
    measurements : list[MeasurementResult]
        All measurement trials across operators
    tolerance : float
        Total tolerance for %GRR calculation

    Returns
    -------
    GageRR
        Comprehensive Gage R&R statistics

    Notes
    -----
    %GRR = (6 * σ_total / tolerance) * 100
    - σ_total = √(σ²_repeatability + σ²_reproducibility)
    - %GRR < 10%: Excellent measurement system
    - %GRR 10-30%: Acceptable measurement system
    - %GRR > 30%: Unacceptable measurement system

    Examples
    --------
    >>> # Excellent measurement system (very tight tolerance)
    >>> m1 = MeasurementResult(1, 10.0, "op1")
    >>> m2 = MeasurementResult(2, 10.01, "op1")
    >>> m3 = MeasurementResult(3, 10.0, "op2")
    >>> m4 = MeasurementResult(4, 10.01, "op2")
    >>> grr = calculate_grr([m1, m2, m3, m4], tolerance=1.0)
    >>> grr.is_excellent
    True

    >>> # Acceptable measurement system (moderate variation)
    >>> m5 = MeasurementResult(1, 10.0, "op1")
    >>> m6 = MeasurementResult(2, 10.05, "op1")
    >>> m7 = MeasurementResult(3, 10.02, "op2")
    >>> m8 = MeasurementResult(4, 10.03, "op2")
    >>> grr2 = calculate_grr([m5, m6, m7, m8], tolerance=1.0)
    >>> grr2.grr_percent < 30.0
    True

    >>> # Zero tolerance edge case
    >>> m9 = MeasurementResult(1, 10.0, "op1")
    >>> grr3 = calculate_grr([m9], tolerance=0.0)
    >>> grr3.grr_percent
    0.0

    >>> # Perfect repeatability and reproducibility
    >>> m10 = MeasurementResult(1, 10.0, "op1")
    >>> m11 = MeasurementResult(2, 10.0, "op1")
    >>> m12 = MeasurementResult(3, 10.0, "op2")
    >>> grr4 = calculate_grr([m10, m11, m12], tolerance=1.0)
    >>> grr4.grr_percent
    0.0
    >>> grr4.is_excellent
    True
    """
    # Calculate overall statistics
    values = [m.value for m in measurements]
    mean = statistics.mean(values)
    std_dev = statistics.stdev(values) if len(values) > 1 else 0.0

    # Group measurements by operator
    operators_map: dict[str, list[MeasurementResult]] = {}
    for m in measurements:
        if m.operator not in operators_map:
            operators_map[m.operator] = []
        operators_map[m.operator].append(m)

    # Calculate repeatability (average within-operator variation)
    repeatabilities = [calculate_repeatability(ops) for ops in operators_map.values()]
    repeatability = statistics.mean(repeatabilities) if repeatabilities else 0.0

    # Calculate reproducibility (between-operator variation)
    operator_means = [statistics.mean([m.value for m in ops]) for ops in operators_map.values()]
    reproducibility = calculate_reproducibility(operator_means)

    # Calculate %GRR
    if tolerance == 0:
        grr_percent = 0.0
    else:
        grr_percent = (6.0 * std_dev / tolerance) * 100.0

    return GageRR(
        repeatability=repeatability,
        reproducibility=reproducibility,
        grr_percent=grr_percent,
        tolerance=tolerance,
        mean=mean,
        std_dev=std_dev,
    )
