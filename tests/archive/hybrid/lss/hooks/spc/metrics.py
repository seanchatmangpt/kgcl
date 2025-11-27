"""SPC metrics for Knowledge Hooks execution analysis.

This module provides Statistical Process Control metrics specifically adapted
for analyzing hook execution performance from HookReceipt data. It tracks
execution times, calculates control limits, and determines process capability
following Six Sigma methodology.

Examples
--------
Calculate SPC metrics for hook execution durations:

>>> from kgcl.hybrid.knowledge_hooks import HookReceipt, HookPhase, HookAction
>>> from datetime import datetime, UTC
>>> receipts = [
...     HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.0),
...     HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.5),
...     HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 9.8),
...     HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.2),
...     HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.1),
... ]
>>> spc = calculate_hook_spc_metrics(receipts, usl=15.0, lsl=5.0)
>>> 9.9 < spc.mean_duration_ms < 10.3
True
>>> spc.is_capable()
True
>>> spc.is_in_control(10.5)
True

Calculate moving range to detect variation:

>>> mr = calculate_hook_moving_range(receipts)
>>> len(mr)
4
>>> all(x >= 0 for x in mr)
True

Check hook execution stability:

>>> stability = check_hook_stability(receipts)
>>> stability["runs_test"]
True
>>> stability["trend_test"]
True
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from kgcl.hybrid.knowledge_hooks import HookReceipt

__all__ = ["HookSPCMetrics", "calculate_hook_spc_metrics", "calculate_hook_moving_range", "check_hook_stability"]


@dataclass(frozen=True)
class HookSPCMetrics:
    """Statistical Process Control metrics for hook execution.

    This class encapsulates complete SPC analysis results for hook execution
    performance, including control limits, capability indices, and variation
    metrics following Six Sigma methodology.

    Parameters
    ----------
    mean_duration_ms : float
        Mean execution duration in milliseconds.
    std_dev : float
        Standard deviation of execution durations (measure of variation).
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
    min_duration : float
        Minimum observed execution duration in milliseconds.
    max_duration : float
        Maximum observed execution duration in milliseconds.
    sample_size : int
        Number of hook executions analyzed.

    Notes
    -----
    Control limits use 3-sigma (99.73% coverage) per Shewhart methodology.
    Process capability: Cpk ≥ 1.33 for capable, Cpk ≥ 2.0 for Six Sigma.

    Examples
    --------
    Create metrics and check capability:

    >>> metrics = HookSPCMetrics(
    ...     mean_duration_ms=10.0,
    ...     std_dev=0.5,
    ...     ucl=11.5,
    ...     lcl=8.5,
    ...     cp=2.0,
    ...     cpk=1.8,
    ...     cv=5.0,
    ...     min_duration=9.0,
    ...     max_duration=11.0,
    ...     sample_size=20,
    ... )
    >>> metrics.is_capable()
    True
    >>> metrics.is_in_control(10.5)
    True
    >>> metrics.is_in_control(12.0)
    False

    Check borderline capability:

    >>> borderline = HookSPCMetrics(10.0, 1.0, 13.0, 7.0, 1.5, 1.32, 10.0, 8.0, 12.0, 15)
    >>> borderline.is_capable()
    False
    """

    mean_duration_ms: float
    std_dev: float
    ucl: float
    lcl: float
    cp: float
    cpk: float
    cv: float
    min_duration: float
    max_duration: float
    sample_size: int

    def is_capable(self) -> bool:
        """Check if hook execution process is capable (Cpk >= 1.33).

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
        >>> metrics = HookSPCMetrics(10.0, 0.3, 10.9, 9.1, 2.2, 2.0, 3.0, 9.5, 10.5, 30)
        >>> metrics.is_capable()
        True

        >>> poor_metrics = HookSPCMetrics(10.0, 1.5, 14.5, 5.5, 1.1, 1.0, 15.0, 7.0, 13.0, 30)
        >>> poor_metrics.is_capable()
        False
        """
        return self.cpk >= 1.33

    def is_in_control(self, duration: float) -> bool:
        """Check if hook execution duration is within control limits.

        Parameters
        ----------
        duration : float
            Execution duration in milliseconds to check.

        Returns
        -------
        bool
            True if duration is within LCL and UCL.

        Examples
        --------
        >>> metrics = HookSPCMetrics(10.0, 0.5, 11.5, 8.5, 2.0, 1.8, 5.0, 9.0, 11.0, 20)
        >>> metrics.is_in_control(10.0)
        True
        >>> metrics.is_in_control(11.0)
        True
        >>> metrics.is_in_control(12.0)
        False
        >>> metrics.is_in_control(8.0)
        False
        """
        return self.lcl <= duration <= self.ucl


def calculate_hook_spc_metrics(
    receipts: list[HookReceipt], usl: float | None = None, lsl: float | None = None
) -> HookSPCMetrics:
    """Calculate complete SPC metrics for hook execution durations.

    Computes mean, standard deviation, control limits (3σ), and process
    capability indices (Cp/Cpk) for hook execution times following Six Sigma
    methodology.

    Parameters
    ----------
    receipts : list[HookReceipt]
        Hook execution receipts to analyze.
    usl : float | None, optional
        Upper Specification Limit in milliseconds (customer requirement).
    lsl : float | None, optional
        Lower Specification Limit in milliseconds (customer requirement).

    Returns
    -------
    HookSPCMetrics
        Complete SPC analysis with control limits and capability indices.

    Raises
    ------
    ValueError
        If receipts list is empty or has fewer than 2 entries.

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

    >>> from kgcl.hybrid.knowledge_hooks import HookReceipt, HookPhase, HookAction
    >>> from datetime import datetime, UTC
    >>> receipts = [
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.5),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 9.8),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.2),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.1),
    ... ]
    >>> metrics = calculate_hook_spc_metrics(receipts, usl=15.0, lsl=5.0)
    >>> 9.9 < metrics.mean_duration_ms < 10.3
    True
    >>> metrics.is_capable()
    True

    Calculate without specification limits (no Cp/Cpk):

    >>> metrics = calculate_hook_spc_metrics(receipts)
    >>> metrics.cp
    0.0
    >>> metrics.cpk
    0.0

    Verify control limits:

    >>> tight_receipts = [
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.1),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 9.9),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.1),
    ... ]
    >>> spc = calculate_hook_spc_metrics(tight_receipts)
    >>> spc.ucl > spc.mean_duration_ms
    True
    >>> spc.lcl < spc.mean_duration_ms
    True
    """
    if len(receipts) < 2:
        raise ValueError("Need at least 2 receipts for SPC analysis")

    # Extract durations from receipts
    durations = [r.duration_ms for r in receipts]

    mean_val = statistics.mean(durations)
    std_dev = statistics.stdev(durations)
    min_val = min(durations)
    max_val = max(durations)

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

    return HookSPCMetrics(
        mean_duration_ms=mean_val,
        std_dev=std_dev,
        ucl=ucl,
        lcl=lcl,
        cp=cp,
        cpk=cpk,
        cv=cv,
        min_duration=min_val,
        max_duration=max_val,
        sample_size=len(receipts),
    )


def calculate_hook_moving_range(receipts: list[HookReceipt]) -> list[float]:
    """Calculate moving range between consecutive hook execution durations.

    Moving range is the absolute difference between consecutive duration values,
    used to detect process variation and stability over time.

    Parameters
    ----------
    receipts : list[HookReceipt]
        Sequential hook execution receipts.

    Returns
    -------
    list[float]
        Absolute differences between consecutive duration values.

    Notes
    -----
    Moving range length is n-1 for n receipts.
    MR[i] = |duration[i] - duration[i-1]| for i in 1..n-1

    Examples
    --------
    Calculate moving range:

    >>> from kgcl.hybrid.knowledge_hooks import HookReceipt, HookPhase, HookAction
    >>> from datetime import datetime, UTC
    >>> receipts = [
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.5),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 9.8),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.2),
    ... ]
    >>> mr = calculate_hook_moving_range(receipts)
    >>> len(mr)
    3
    >>> abs(mr[0] - 0.5) < 0.01
    True
    >>> abs(mr[1] - 0.7) < 0.01
    True

    Empty list for insufficient data:

    >>> single = [HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.0)]
    >>> calculate_hook_moving_range(single)
    []
    >>> calculate_hook_moving_range([])
    []

    Verify all differences are positive:

    >>> receipts2 = [
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 5.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 3.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 7.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 4.0),
    ... ]
    >>> mr = calculate_hook_moving_range(receipts2)
    >>> all(x >= 0 for x in mr)
    True
    """
    if len(receipts) < 2:
        return []

    durations = [r.duration_ms for r in receipts]
    return [abs(durations[i] - durations[i - 1]) for i in range(1, len(durations))]


def check_hook_stability(receipts: list[HookReceipt]) -> dict[str, bool]:
    """Check for special cause variation in hook execution using run chart rules.

    Applies Western Electric Rules to detect non-random patterns in hook
    execution durations indicating special cause variation: runs, trends, and
    zone violations.

    Parameters
    ----------
    receipts : list[HookReceipt]
        Sequential hook execution receipts.

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

    >>> from kgcl.hybrid.knowledge_hooks import HookReceipt, HookPhase, HookAction
    >>> from datetime import datetime, UTC
    >>> stable = [
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.2),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 9.8),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.1),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 9.9),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.3),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 9.7),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.4),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 9.9),
    ... ]
    >>> stability = check_hook_stability(stable)
    >>> stability["runs_test"]
    True
    >>> stability["trend_test"]
    True

    Trending process fails trend test:

    >>> trending = [
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 8.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 8.5),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 9.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 9.5),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.5),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 11.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 11.5),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 12.0),
    ... ]
    >>> stability = check_hook_stability(trending)
    >>> stability["trend_test"]
    False

    Insufficient data returns all True:

    >>> few = [
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.0),
    ...     HookReceipt("h1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.NOTIFY, 10.1),
    ... ]
    >>> check_hook_stability(few)
    {'runs_test': True, 'trend_test': True, 'zone_test': True}
    """
    if len(receipts) < 8:
        return {"runs_test": True, "trend_test": True, "zone_test": True}

    durations = [r.duration_ms for r in receipts]
    median = statistics.median(durations)

    # Rule 1: Check for runs (8+ consecutive on same side of median)
    max_run = 1
    current_run = 1
    for i in range(1, len(durations)):
        if (durations[i] > median) == (durations[i - 1] > median):
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1

    runs_stable = max_run < 8

    # Rule 2: Check for trends (6+ consecutive increasing or decreasing)
    max_trend = 1
    current_trend = 1
    for i in range(1, len(durations)):
        if durations[i] > durations[i - 1]:
            if i > 1 and durations[i - 1] > durations[i - 2]:
                current_trend += 1
                max_trend = max(max_trend, current_trend)
            else:
                current_trend = 1
        elif durations[i] < durations[i - 1]:
            if i > 1 and durations[i - 1] < durations[i - 2]:
                current_trend += 1
                max_trend = max(max_trend, current_trend)
            else:
                current_trend = 1

    trend_stable = max_trend < 6

    # Rule 3: Check zone violations (simplified: check for outliers beyond 2-sigma)
    mean_val = statistics.mean(durations)
    std_dev = statistics.stdev(durations) if len(durations) > 1 else 0.0
    zone_upper = mean_val + (2 * std_dev)
    zone_lower = mean_val - (2 * std_dev)

    outliers = sum(1 for d in durations if d > zone_upper or d < zone_lower)
    zone_stable = outliers < (len(durations) * 0.33)  # Less than 1/3 outliers

    return {"runs_test": runs_stable, "trend_test": trend_stable, "zone_test": zone_stable}


if __name__ == "__main__":
    import doctest

    doctest.testmod()
