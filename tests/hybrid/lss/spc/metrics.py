"""Core SPC metrics data structures and calculation functions.

This module provides dataclasses and functions for Statistical Process Control
analysis, including control limits, process capability indices, and stability
checks following Six Sigma methodology.

Examples
--------
Calculate SPC metrics for process measurements:

>>> measurements = [10.0, 10.5, 9.8, 10.2, 10.1, 9.9, 10.3]
>>> spc = calculate_spc_metrics(measurements, usl=12.0, lsl=8.0)
>>> spc.mean
10.114285714285714
>>> spc.is_capable()
True
>>> spc.is_in_control(10.5)
True

Calculate moving range to detect variation:

>>> data = [10.0, 10.5, 9.8, 10.2]
>>> mr = calculate_moving_range(data)
>>> len(mr)
3
>>> abs(mr[0] - 0.5) < 0.01
True
>>> abs(mr[1] - 0.7) < 0.01
True

Check run chart stability:

>>> stable_data = [10.0, 10.2, 9.8, 10.1, 9.9, 10.3, 9.7, 10.4]
>>> stability = check_run_chart_stability(stable_data)
>>> stability["runs_test"]
True
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

__all__ = [
    "SPCMetrics",
    "ProcessCapability",
    "PatternExecutionMetrics",
    "calculate_spc_metrics",
    "calculate_moving_range",
    "check_run_chart_stability",
]


@dataclass(frozen=True)
class SPCMetrics:
    """Statistical Process Control metrics for pattern execution.

    This class encapsulates complete SPC analysis results including control
    limits, capability indices, and variation metrics following Six Sigma
    methodology.

    Parameters
    ----------
    mean : float
        Mean value of measurements.
    std_dev : float
        Standard deviation (measure of variation).
    ucl : float
        Upper Control Limit (mean + 3σ).
    lcl : float
        Lower Control Limit (mean - 3σ).
    cp : float
        Process Capability index (specification range / process range).
    cpk : float
        Process Capability index adjusted for centering.
    cv : float
        Coefficient of Variation (std_dev / mean) as percentage.
    min_value : float
        Minimum observed value.
    max_value : float
        Maximum observed value.
    sample_size : int
        Number of measurements.

    Notes
    -----
    Control limits use 3-sigma (99.73% coverage) per Shewhart methodology.
    Process capability: Cpk ≥ 1.33 for capable, Cpk ≥ 2.0 for Six Sigma.

    Examples
    --------
    Create metrics and check capability:

    >>> metrics = SPCMetrics(
    ...     mean=10.0,
    ...     std_dev=0.5,
    ...     ucl=11.5,
    ...     lcl=8.5,
    ...     cp=2.0,
    ...     cpk=1.8,
    ...     cv=5.0,
    ...     min_value=9.0,
    ...     max_value=11.0,
    ...     sample_size=20,
    ... )
    >>> metrics.is_capable()
    True
    >>> metrics.is_in_control(10.5)
    True
    >>> metrics.is_in_control(12.0)
    False

    Check borderline capability:

    >>> borderline = SPCMetrics(10.0, 1.0, 13.0, 7.0, 1.5, 1.32, 10.0, 8.0, 12.0, 15)
    >>> borderline.is_capable()
    False
    """

    mean: float
    std_dev: float
    ucl: float
    lcl: float
    cp: float
    cpk: float
    cv: float
    min_value: float
    max_value: float
    sample_size: int

    def is_capable(self) -> bool:
        """Check if process is capable (Cpk >= 1.33).

        Returns
        -------
        bool
            True if process meets capability requirements.

        Notes
        -----
        Industry standard: Cpk >= 1.33 for capable process (4σ quality)
        Six Sigma standard: Cpk >= 2.0 for world-class process (6σ quality)

        Examples
        --------
        >>> metrics = SPCMetrics(10.0, 0.3, 10.9, 9.1, 2.2, 2.0, 3.0, 9.5, 10.5, 30)
        >>> metrics.is_capable()
        True

        >>> poor_metrics = SPCMetrics(10.0, 1.5, 14.5, 5.5, 1.1, 1.0, 15.0, 7.0, 13.0, 30)
        >>> poor_metrics.is_capable()
        False
        """
        return self.cpk >= 1.33

    def is_in_control(self, value: float) -> bool:
        """Check if value is within control limits.

        Parameters
        ----------
        value : float
            Measurement to check.

        Returns
        -------
        bool
            True if value is within LCL and UCL.

        Examples
        --------
        >>> metrics = SPCMetrics(10.0, 0.5, 11.5, 8.5, 2.0, 1.8, 5.0, 9.0, 11.0, 20)
        >>> metrics.is_in_control(10.0)
        True
        >>> metrics.is_in_control(11.0)
        True
        >>> metrics.is_in_control(12.0)
        False
        >>> metrics.is_in_control(8.0)
        False
        """
        return self.lcl <= value <= self.ucl


@dataclass(frozen=True)
class ProcessCapability:
    """Process capability indices (Cp and Cpk).

    Parameters
    ----------
    cp : float
        Potential capability (ignores centering).
    cpk : float
        Actual capability (accounts for centering).
    cpu : float
        Upper capability index.
    cpl : float
        Lower capability index.

    Notes
    -----
    Cp measures potential capability assuming perfect centering.
    Cpk measures actual capability considering process centering.
    Cpk = min(Cpu, Cpl) where:
    - Cpu = (USL - μ) / (3σ)
    - Cpl = (μ - LSL) / (3σ)

    Examples
    --------
    >>> cap = ProcessCapability(cp=2.0, cpk=1.8, cpu=2.0, cpl=1.8)
    >>> cap.cp >= 1.33
    True
    >>> cap.cpk >= 1.33
    True
    """

    cp: float
    cpk: float
    cpu: float
    cpl: float


@dataclass(frozen=True)
class PatternExecutionMetrics:
    """Execution metrics for a single pattern run.

    Parameters
    ----------
    pattern_name : str
        WCP pattern identifier (e.g., "WCP-1", "WCP-2").
    tick_count : int
        Number of ticks to reach fixed point.
    total_duration_ms : float
        Total execution time in milliseconds.
    avg_duration_per_tick_ms : float
        Average duration per tick.
    total_delta : int
        Total triple changes across all ticks.
    convergence_rate : float
        Delta reduction rate (total_delta / tick_count).

    Examples
    --------
    >>> metrics = PatternExecutionMetrics(
    ...     pattern_name="WCP-1",
    ...     tick_count=5,
    ...     total_duration_ms=12.5,
    ...     avg_duration_per_tick_ms=2.5,
    ...     total_delta=10,
    ...     convergence_rate=2.0,
    ... )
    >>> metrics.tick_count
    5
    >>> metrics.convergence_rate
    2.0
    """

    pattern_name: str
    tick_count: int
    total_duration_ms: float
    avg_duration_per_tick_ms: float
    total_delta: int
    convergence_rate: float


def calculate_spc_metrics(measurements: list[float], usl: float | None = None, lsl: float | None = None) -> SPCMetrics:
    """Calculate complete SPC metrics for a set of measurements.

    Computes mean, standard deviation, control limits (3σ), and process
    capability indices (Cp/Cpk) following Six Sigma methodology.

    Parameters
    ----------
    measurements : list[float]
        Sample measurements from process.
    usl : float | None, optional
        Upper Specification Limit (customer requirement).
    lsl : float | None, optional
        Lower Specification Limit (customer requirement).

    Returns
    -------
    SPCMetrics
        Complete SPC analysis with control limits and capability indices.

    Raises
    ------
    ValueError
        If measurements list is empty or has fewer than 2 values.

    Notes
    -----
    Control limits: UCL = μ + 3σ, LCL = max(0, μ - 3σ)
    Process capability:
    - Cp = (USL - LSL) / (6σ)
    - Cpk = min((USL - μ)/(3σ), (μ - LSL)/(3σ))
    Coefficient of Variation: CV = (σ/μ) × 100

    Examples
    --------
    Calculate SPC metrics with specification limits:

    >>> measurements = [10.0, 10.5, 9.8, 10.2, 10.1]
    >>> metrics = calculate_spc_metrics(measurements, usl=12.0, lsl=8.0)
    >>> 9.9 < metrics.mean < 10.3
    True
    >>> metrics.is_capable()
    True

    Calculate without specification limits (no Cp/Cpk):

    >>> measurements = [5.0, 5.2, 4.8, 5.1]
    >>> metrics = calculate_spc_metrics(measurements)
    >>> metrics.cp
    0.0
    >>> metrics.cpk
    0.0

    Verify control limits:

    >>> tight_data = [10.0, 10.1, 9.9, 10.0, 10.1]
    >>> spc = calculate_spc_metrics(tight_data)
    >>> spc.ucl > spc.mean
    True
    >>> spc.lcl < spc.mean
    True
    """
    if len(measurements) < 2:
        raise ValueError("Need at least 2 measurements for SPC analysis")

    mean_val = statistics.mean(measurements)
    std_dev = statistics.stdev(measurements)
    min_val = min(measurements)
    max_val = max(measurements)

    # Control limits (3-sigma)
    ucl = mean_val + (3 * std_dev)
    lcl = max(0.0, mean_val - (3 * std_dev))  # Cannot be negative

    # Process capability indices
    if usl is not None and lsl is not None:
        # Cp: Potential capability (ignores centering)
        cp = (usl - lsl) / (6 * std_dev) if std_dev > 0 else float("inf")

        # Cpk: Actual capability (accounts for centering)
        cpu = (usl - mean_val) / (3 * std_dev) if std_dev > 0 else float("inf")
        cpl = (mean_val - lsl) / (3 * std_dev) if std_dev > 0 else float("inf")
        cpk = min(cpu, cpl)
    else:
        # No specification limits provided
        cp = 0.0
        cpk = 0.0

    # Coefficient of variation (percentage)
    cv = (std_dev / mean_val * 100) if mean_val > 0 else 0.0

    return SPCMetrics(
        mean=mean_val,
        std_dev=std_dev,
        ucl=ucl,
        lcl=lcl,
        cp=cp,
        cpk=cpk,
        cv=cv,
        min_value=min_val,
        max_value=max_val,
        sample_size=len(measurements),
    )


def calculate_moving_range(measurements: list[float]) -> list[float]:
    """Calculate moving range between consecutive measurements.

    Moving range is the absolute difference between consecutive values,
    used to detect process variation and stability over time.

    Parameters
    ----------
    measurements : list[float]
        Sequential measurements.

    Returns
    -------
    list[float]
        Absolute differences between consecutive values.

    Notes
    -----
    Moving range length is n-1 for n measurements.
    MR[i] = |x[i] - x[i-1]| for i in 1..n-1

    Examples
    --------
    Calculate moving range:

    >>> measurements = [10.0, 10.5, 9.8, 10.2]
    >>> mr = calculate_moving_range(measurements)
    >>> len(mr)
    3
    >>> abs(mr[0] - 0.5) < 0.01
    True
    >>> abs(mr[1] - 0.7) < 0.01
    True

    Empty list for insufficient data:

    >>> calculate_moving_range([10.0])
    []
    >>> calculate_moving_range([])
    []

    Verify all differences are positive:

    >>> data = [5.0, 3.0, 7.0, 4.0]
    >>> mr = calculate_moving_range(data)
    >>> all(x >= 0 for x in mr)
    True
    """
    if len(measurements) < 2:
        return []
    return [abs(measurements[i] - measurements[i - 1]) for i in range(1, len(measurements))]


def check_run_chart_stability(measurements: list[float]) -> dict[str, bool]:
    """Check for special cause variation using run chart rules.

    Applies Western Electric Rules to detect non-random patterns indicating
    special cause variation: runs, trends, and zone violations.

    Parameters
    ----------
    measurements : list[float]
        Sequential measurements.

    Returns
    -------
    dict[str, bool]
        Results of stability tests: runs_test, trend_test, zone_test.
        True indicates stable (no special cause), False indicates unstable.

    Notes
    -----
    Western Electric Rules for Run Charts:
    - Rule 1: 8+ consecutive points above/below centerline (shift)
    - Rule 2: 6+ consecutive increasing/decreasing points (trend)
    - Rule 3: >1/3 points beyond 2σ (zone violation)

    Examples
    --------
    Stable process passes all tests:

    >>> stable = [10.0, 10.2, 9.8, 10.1, 9.9, 10.3, 9.7, 10.4, 10.0, 9.9]
    >>> stability = check_run_chart_stability(stable)
    >>> stability["runs_test"]
    True
    >>> stability["trend_test"]
    True

    Trending process fails trend test:

    >>> trending = [8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0]
    >>> stability = check_run_chart_stability(trending)
    >>> stability["trend_test"]
    False

    Insufficient data returns all True:

    >>> check_run_chart_stability([10.0, 10.1])
    {'runs_test': True, 'trend_test': True, 'zone_test': True}
    """
    if len(measurements) < 8:
        return {"runs_test": True, "trend_test": True, "zone_test": True}

    median = statistics.median(measurements)

    # Rule 1: Check for runs (8+ consecutive on same side of median)
    max_run = 1
    current_run = 1
    for i in range(1, len(measurements)):
        if (measurements[i] > median) == (measurements[i - 1] > median):
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1

    runs_stable = max_run < 8

    # Rule 2: Check for trends (6+ consecutive increasing or decreasing)
    max_trend = 1
    current_trend = 1
    for i in range(1, len(measurements)):
        if measurements[i] > measurements[i - 1]:
            if i > 1 and measurements[i - 1] > measurements[i - 2]:
                current_trend += 1
                max_trend = max(max_trend, current_trend)
            else:
                current_trend = 1
        elif measurements[i] < measurements[i - 1]:
            if i > 1 and measurements[i - 1] < measurements[i - 2]:
                current_trend += 1
                max_trend = max(max_trend, current_trend)
            else:
                current_trend = 1

    trend_stable = max_trend < 6

    # Rule 3: Check zone violations (simplified: check for outliers beyond 2-sigma)
    mean_val = statistics.mean(measurements)
    std_dev = statistics.stdev(measurements) if len(measurements) > 1 else 0.0
    zone_upper = mean_val + (2 * std_dev)
    zone_lower = mean_val - (2 * std_dev)

    outliers = sum(1 for m in measurements if m > zone_upper or m < zone_lower)
    zone_stable = outliers < (len(measurements) * 0.33)  # Less than 1/3 outliers

    return {"runs_test": runs_stable, "trend_test": trend_stable, "zone_test": zone_stable}


if __name__ == "__main__":
    import doctest

    doctest.testmod()
