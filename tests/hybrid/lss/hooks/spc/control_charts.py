"""Control Charts for Knowledge Hooks SPC Analysis.

This module implements control chart analysis for Knowledge Hook execution patterns,
applying Statistical Process Control (SPC) to detect out-of-control conditions and
special cause variation in hook performance.

Chart Types
-----------
- **X-bar & R Charts**: For subgroup data (multiple hooks of same type)
- **I-MR Charts**: For individual measurements (single hook executions)
- **p-Charts**: For proportion data (success/failure rates)
- **c-Charts**: For count data (errors per execution)

Examples
--------
Create I-MR chart for individual hook execution times:

>>> from kgcl.hybrid import HookReceipt, HookPhase, HookAction
>>> from datetime import datetime, UTC
>>> receipts = [
...     HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.5),
...     HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 11.2),
...     HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 9.8),
... ]
>>> chart = create_hook_imr_chart(receipts)
>>> chart.i_chart.center_line
10.5

Create X-bar & R chart for hook subgroups:

>>> receipts = [...]  # Multiple hooks per subgroup
>>> chart = create_hook_xbar_r_chart(receipts, subgroup_size=5)
>>> chart.xbar_chart.ucl > chart.xbar_chart.center_line
True

Detect out-of-control conditions:

>>> rules = detect_western_electric_rules(chart.i_chart)
>>> rules["rule1_beyond_3sigma"]
False
>>> rules["rule2_2of3_beyond_2sigma"]
False
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kgcl.hybrid.knowledge_hooks import HookReceipt

__all__ = [
    "HookControlChart",
    "HookXBarRChart",
    "HookIMRChart",
    "create_hook_xbar_r_chart",
    "create_hook_imr_chart",
    "detect_western_electric_rules",
    "detect_nelson_rules",
]


@dataclass(frozen=True)
class HookControlChart:
    """Control chart for Knowledge Hook measurements.

    Represents a single control chart with center line, control limits,
    and detection of out-of-control points.

    Parameters
    ----------
    chart_type : str
        Type of chart: "X-bar", "R", "I-MR", "p", "c"
    center_line : float
        Center line (mean of measurements)
    ucl : float
        Upper Control Limit (3-sigma)
    lcl : float
        Lower Control Limit (3-sigma)
    data_points : list[float]
        Measurement data points
    out_of_control_points : list[int]
        Indices of points beyond control limits

    Examples
    --------
    Create a control chart for individual measurements:

    >>> chart = HookControlChart(
    ...     chart_type="I-MR",
    ...     center_line=10.0,
    ...     ucl=13.0,
    ...     lcl=7.0,
    ...     data_points=[10.1, 9.8, 10.3, 15.0, 9.9],
    ...     out_of_control_points=[3],
    ... )
    >>> chart.has_out_of_control_points()
    True
    >>> chart.percent_in_control()
    80.0
    """

    chart_type: str
    center_line: float
    ucl: float
    lcl: float
    data_points: list[float]
    out_of_control_points: list[int]

    def has_out_of_control_points(self) -> bool:
        """Check if chart has any out-of-control points.

        Returns
        -------
        bool
            True if any points exceed control limits
        """
        return len(self.out_of_control_points) > 0

    def percent_in_control(self) -> float:
        """Calculate percentage of points within control limits.

        Returns
        -------
        float
            Percentage (0-100) of points in control
        """
        if not self.data_points:
            return 100.0
        in_control = len(self.data_points) - len(self.out_of_control_points)
        return (in_control / len(self.data_points)) * 100.0

    def is_stable(self) -> bool:
        """Check if process is stable (all points in control).

        Returns
        -------
        bool
            True if no out-of-control points
        """
        return not self.has_out_of_control_points()


@dataclass(frozen=True)
class HookXBarRChart:
    """X-bar & R chart for hook subgroup analysis.

    Used when hooks are collected in subgroups (e.g., 5 executions of same hook).
    Tracks both average performance (X-bar) and variation (R).

    Parameters
    ----------
    xbar_chart : HookControlChart
        Chart of subgroup averages
    r_chart : HookControlChart
        Chart of subgroup ranges
    subgroup_size : int
        Number of measurements per subgroup

    Examples
    --------
    Create X-bar & R chart:

    >>> xbar = HookControlChart("X-bar", 10.0, 12.0, 8.0, [9.8, 10.1, 10.3], [])
    >>> r = HookControlChart("R", 1.5, 3.0, 0.0, [1.2, 1.8, 1.4], [])
    >>> chart = HookXBarRChart(xbar, r, 5)
    >>> chart.is_stable()
    True
    """

    xbar_chart: HookControlChart
    r_chart: HookControlChart
    subgroup_size: int

    def is_stable(self) -> bool:
        """Check if both charts are stable.

        Returns
        -------
        bool
            True if both X-bar and R charts are in control
        """
        return self.xbar_chart.is_stable() and self.r_chart.is_stable()


@dataclass(frozen=True)
class HookIMRChart:
    """Individual & Moving Range chart for hook analysis.

    Used for individual hook measurements where subgrouping isn't appropriate.
    Tracks individual values (I) and variation between consecutive values (MR).

    Parameters
    ----------
    i_chart : HookControlChart
        Chart of individual measurements
    mr_chart : HookControlChart
        Chart of moving ranges

    Examples
    --------
    Create I-MR chart:

    >>> i = HookControlChart("I", 10.0, 13.0, 7.0, [10.1, 9.8, 10.3], [])
    >>> mr = HookControlChart("MR", 0.5, 1.5, 0.0, [0.3, 0.5, 0.4], [])
    >>> chart = HookIMRChart(i, mr)
    >>> chart.is_stable()
    True
    """

    i_chart: HookControlChart
    mr_chart: HookControlChart

    def is_stable(self) -> bool:
        """Check if both charts are stable.

        Returns
        -------
        bool
            True if both I and MR charts are in control
        """
        return self.i_chart.is_stable() and self.mr_chart.is_stable()


def create_hook_xbar_r_chart(receipts: list[HookReceipt], subgroup_size: int) -> HookXBarRChart:
    """Create X-bar & R chart from hook receipts with subgrouping.

    Parameters
    ----------
    receipts : list[HookReceipt]
        Hook execution receipts
    subgroup_size : int
        Number of measurements per subgroup

    Returns
    -------
    HookXBarRChart
        X-bar & R control charts

    Raises
    ------
    ValueError
        If insufficient data or invalid subgroup size

    Notes
    -----
    X-bar chart control limits:
    - Center line: average of subgroup means
    - UCL = X-bar + A2 * R-bar
    - LCL = X-bar - A2 * R-bar

    R chart control limits:
    - Center line: average range
    - UCL = D4 * R-bar
    - LCL = D3 * R-bar

    A2, D3, D4 are constants based on subgroup size.

    Examples
    --------
    Create chart from receipts:

    >>> from kgcl.hybrid import HookReceipt, HookPhase, HookAction
    >>> from datetime import datetime, UTC
    >>> receipts = [
    ...     HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.0 + i * 0.1)
    ...     for i in range(15)
    ... ]
    >>> chart = create_hook_xbar_r_chart(receipts, subgroup_size=5)
    >>> chart.subgroup_size
    5
    >>> len(chart.xbar_chart.data_points)
    3
    """
    if subgroup_size < 2:
        raise ValueError("Subgroup size must be at least 2")

    if len(receipts) < subgroup_size:
        raise ValueError(f"Need at least {subgroup_size} receipts for subgroup analysis")

    # Extract duration_ms from receipts
    measurements = [r.duration_ms for r in receipts]

    # Constants for control limits (based on subgroup size)
    # A2 constants for X-bar chart
    A2_constants = {2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577, 6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308}
    # D3, D4 constants for R chart
    D3_constants = {2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.076, 8: 0.136, 9: 0.184, 10: 0.223}
    D4_constants = {2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114, 6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777}

    if subgroup_size not in A2_constants:
        raise ValueError(f"Subgroup size {subgroup_size} not supported (must be 2-10)")

    A2 = A2_constants[subgroup_size]
    D3 = D3_constants[subgroup_size]
    D4 = D4_constants[subgroup_size]

    # Calculate subgroup statistics
    subgroup_means: list[float] = []
    subgroup_ranges: list[float] = []

    for i in range(0, len(measurements), subgroup_size):
        subgroup = measurements[i : i + subgroup_size]
        if len(subgroup) == subgroup_size:
            subgroup_means.append(statistics.mean(subgroup))
            subgroup_ranges.append(max(subgroup) - min(subgroup))

    if not subgroup_means:
        raise ValueError("Insufficient data to form complete subgroups")

    # X-bar chart
    xbar = statistics.mean(subgroup_means)
    rbar = statistics.mean(subgroup_ranges)

    xbar_ucl = xbar + (A2 * rbar)
    xbar_lcl = max(0.0, xbar - (A2 * rbar))

    xbar_out_of_control = [i for i, val in enumerate(subgroup_means) if val > xbar_ucl or val < xbar_lcl]

    xbar_chart = HookControlChart(
        chart_type="X-bar",
        center_line=xbar,
        ucl=xbar_ucl,
        lcl=xbar_lcl,
        data_points=subgroup_means,
        out_of_control_points=xbar_out_of_control,
    )

    # R chart
    r_ucl = D4 * rbar
    r_lcl = D3 * rbar

    r_out_of_control = [i for i, val in enumerate(subgroup_ranges) if val > r_ucl or val < r_lcl]

    r_chart = HookControlChart(
        chart_type="R",
        center_line=rbar,
        ucl=r_ucl,
        lcl=r_lcl,
        data_points=subgroup_ranges,
        out_of_control_points=r_out_of_control,
    )

    return HookXBarRChart(xbar_chart=xbar_chart, r_chart=r_chart, subgroup_size=subgroup_size)


def create_hook_imr_chart(receipts: list[HookReceipt]) -> HookIMRChart:
    """Create Individual & Moving Range chart from hook receipts.

    Parameters
    ----------
    receipts : list[HookReceipt]
        Hook execution receipts (at least 2 required)

    Returns
    -------
    HookIMRChart
        I-MR control charts

    Raises
    ------
    ValueError
        If insufficient data (< 2 receipts)

    Notes
    -----
    I chart control limits:
    - Center line: mean of individuals
    - UCL = X-bar + 2.66 * MR-bar
    - LCL = X-bar - 2.66 * MR-bar

    MR chart control limits:
    - Center line: average moving range
    - UCL = 3.267 * MR-bar
    - LCL = 0 (ranges cannot be negative)

    Examples
    --------
    Create I-MR chart:

    >>> from kgcl.hybrid import HookReceipt, HookPhase, HookAction
    >>> from datetime import datetime, UTC
    >>> receipts = [
    ...     HookReceipt("hook1", HookPhase.PRE_TICK, datetime.now(UTC), True, HookAction.ASSERT, 10.0 + i * 0.5)
    ...     for i in range(10)
    ... ]
    >>> chart = create_hook_imr_chart(receipts)
    >>> chart.i_chart.center_line > 0
    True
    >>> chart.mr_chart.lcl
    0.0
    """
    if len(receipts) < 2:
        raise ValueError("Need at least 2 receipts for I-MR chart")

    # Extract duration_ms
    measurements = [r.duration_ms for r in receipts]

    # Calculate moving range
    moving_ranges = [abs(measurements[i] - measurements[i - 1]) for i in range(1, len(measurements))]

    # I chart
    mean_val = statistics.mean(measurements)
    mr_bar = statistics.mean(moving_ranges)

    # Control limits for I chart (using 2.66 constant for MR-based limits)
    i_ucl = mean_val + (2.66 * mr_bar)
    i_lcl = max(0.0, mean_val - (2.66 * mr_bar))

    i_out_of_control = [i for i, val in enumerate(measurements) if val > i_ucl or val < i_lcl]

    i_chart = HookControlChart(
        chart_type="I",
        center_line=mean_val,
        ucl=i_ucl,
        lcl=i_lcl,
        data_points=measurements,
        out_of_control_points=i_out_of_control,
    )

    # MR chart
    mr_ucl = 3.267 * mr_bar
    mr_lcl = 0.0  # Moving ranges cannot be negative

    mr_out_of_control = [i for i, val in enumerate(moving_ranges) if val > mr_ucl]

    mr_chart = HookControlChart(
        chart_type="MR",
        center_line=mr_bar,
        ucl=mr_ucl,
        lcl=mr_lcl,
        data_points=moving_ranges,
        out_of_control_points=mr_out_of_control,
    )

    return HookIMRChart(i_chart=i_chart, mr_chart=mr_chart)


def detect_western_electric_rules(chart: HookControlChart) -> dict[str, bool]:
    """Detect Western Electric Rules violations in control chart.

    Western Electric Rules detect non-random patterns indicating special cause variation:
    - Rule 1: Point beyond 3σ (out of control)
    - Rule 2: 2 of 3 consecutive points beyond 2σ on same side
    - Rule 3: 4 of 5 consecutive points beyond 1σ on same side
    - Rule 4: 8 consecutive points on same side of center line

    Parameters
    ----------
    chart : HookControlChart
        Control chart to analyze

    Returns
    -------
    dict[str, bool]
        Dictionary of rule violations (True = violation detected)

    Examples
    --------
    Detect violations in stable chart:

    >>> chart = HookControlChart("I", 10.0, 13.0, 7.0, [10.1, 9.8, 10.3, 9.9], [])
    >>> rules = detect_western_electric_rules(chart)
    >>> rules["rule1_beyond_3sigma"]
    False

    Detect point beyond 3σ:

    >>> chart = HookControlChart("I", 10.0, 13.0, 7.0, [10.1, 15.0, 9.8], [1])
    >>> rules = detect_western_electric_rules(chart)
    >>> rules["rule1_beyond_3sigma"]
    True
    """
    data = chart.data_points
    center = chart.center_line
    ucl = chart.ucl
    lcl = chart.lcl

    # Calculate sigma (1/3 of control limit range from center)
    sigma = (ucl - center) / 3.0

    # Rule 1: Point beyond 3σ (already captured in out_of_control_points)
    rule1 = len(chart.out_of_control_points) > 0

    # Rule 2: 2 of 3 consecutive points beyond 2σ on same side
    rule2 = False
    if len(data) >= 3:
        sigma2_upper = center + (2 * sigma)
        sigma2_lower = center - (2 * sigma)
        for i in range(len(data) - 2):
            window = data[i : i + 3]
            beyond_2sigma_upper = sum(1 for v in window if v > sigma2_upper)
            beyond_2sigma_lower = sum(1 for v in window if v < sigma2_lower)
            if beyond_2sigma_upper >= 2 or beyond_2sigma_lower >= 2:
                rule2 = True
                break

    # Rule 3: 4 of 5 consecutive points beyond 1σ on same side
    rule3 = False
    if len(data) >= 5:
        sigma1_upper = center + sigma
        sigma1_lower = center - sigma
        for i in range(len(data) - 4):
            window = data[i : i + 5]
            beyond_1sigma_upper = sum(1 for v in window if v > sigma1_upper)
            beyond_1sigma_lower = sum(1 for v in window if v < sigma1_lower)
            if beyond_1sigma_upper >= 4 or beyond_1sigma_lower >= 4:
                rule3 = True
                break

    # Rule 4: 8 consecutive points on same side of center line
    rule4 = False
    if len(data) >= 8:
        for i in range(len(data) - 7):
            window = data[i : i + 8]
            all_above = all(v > center for v in window)
            all_below = all(v < center for v in window)
            if all_above or all_below:
                rule4 = True
                break

    return {
        "rule1_beyond_3sigma": rule1,
        "rule2_2of3_beyond_2sigma": rule2,
        "rule3_4of5_beyond_1sigma": rule3,
        "rule4_8_consecutive_same_side": rule4,
    }


def detect_nelson_rules(chart: HookControlChart) -> dict[str, bool]:
    """Detect Nelson Rules violations in control chart.

    Nelson Rules are an extended set of rules for detecting non-random patterns:
    1. One point beyond 3σ
    2. Nine consecutive points on same side of center
    3. Six consecutive points increasing or decreasing
    4. Fourteen consecutive points alternating up and down
    5. Two of three consecutive points beyond 2σ on same side
    6. Four of five consecutive points beyond 1σ on same side
    7. Fifteen consecutive points within 1σ (both sides)
    8. Eight consecutive points beyond 1σ (either side)

    Parameters
    ----------
    chart : HookControlChart
        Control chart to analyze

    Returns
    -------
    dict[str, bool]
        Dictionary of rule violations (True = violation detected)

    Examples
    --------
    Detect violations in stable chart:

    >>> chart = HookControlChart("I", 10.0, 13.0, 7.0, [10.1, 9.8, 10.3, 9.9], [])
    >>> rules = detect_nelson_rules(chart)
    >>> rules["rule1_beyond_3sigma"]
    False

    Detect trend violation:

    >>> chart = HookControlChart("I", 10.0, 15.0, 5.0, [8.0, 9.0, 10.0, 11.0, 12.0, 13.0], [])
    >>> rules = detect_nelson_rules(chart)
    >>> rules["rule3_six_increasing"]
    True
    """
    data = chart.data_points
    center = chart.center_line
    ucl = chart.ucl
    lcl = chart.lcl

    sigma = (ucl - center) / 3.0

    # Rule 1: One point beyond 3σ
    rule1 = len(chart.out_of_control_points) > 0

    # Rule 2: Nine consecutive points on same side
    rule2 = False
    if len(data) >= 9:
        for i in range(len(data) - 8):
            window = data[i : i + 9]
            all_above = all(v > center for v in window)
            all_below = all(v < center for v in window)
            if all_above or all_below:
                rule2 = True
                break

    # Rule 3: Six consecutive increasing or decreasing
    rule3 = False
    if len(data) >= 6:
        for i in range(len(data) - 5):
            window = data[i : i + 6]
            increasing = all(window[j] < window[j + 1] for j in range(5))
            decreasing = all(window[j] > window[j + 1] for j in range(5))
            if increasing or decreasing:
                rule3 = True
                break

    # Rule 4: Fourteen consecutive alternating
    rule4 = False
    if len(data) >= 14:
        for i in range(len(data) - 13):
            window = data[i : i + 14]
            alternating = all((window[j] < window[j + 1]) != (window[j + 1] < window[j + 2]) for j in range(12))
            if alternating:
                rule4 = True
                break

    # Rule 5: 2 of 3 beyond 2σ
    rule5 = False
    if len(data) >= 3:
        sigma2_upper = center + (2 * sigma)
        sigma2_lower = center - (2 * sigma)
        for i in range(len(data) - 2):
            window = data[i : i + 3]
            beyond_2sigma_upper = sum(1 for v in window if v > sigma2_upper)
            beyond_2sigma_lower = sum(1 for v in window if v < sigma2_lower)
            if beyond_2sigma_upper >= 2 or beyond_2sigma_lower >= 2:
                rule5 = True
                break

    # Rule 6: 4 of 5 beyond 1σ
    rule6 = False
    if len(data) >= 5:
        sigma1_upper = center + sigma
        sigma1_lower = center - sigma
        for i in range(len(data) - 4):
            window = data[i : i + 5]
            beyond_1sigma_upper = sum(1 for v in window if v > sigma1_upper)
            beyond_1sigma_lower = sum(1 for v in window if v < sigma1_lower)
            if beyond_1sigma_upper >= 4 or beyond_1sigma_lower >= 4:
                rule6 = True
                break

    # Rule 7: 15 consecutive within 1σ
    rule7 = False
    if len(data) >= 15:
        sigma1_upper = center + sigma
        sigma1_lower = center - sigma
        for i in range(len(data) - 14):
            window = data[i : i + 15]
            all_within_1sigma = all(sigma1_lower <= v <= sigma1_upper for v in window)
            if all_within_1sigma:
                rule7 = True
                break

    # Rule 8: 8 consecutive beyond 1σ
    rule8 = False
    if len(data) >= 8:
        sigma1_upper = center + sigma
        sigma1_lower = center - sigma
        for i in range(len(data) - 7):
            window = data[i : i + 8]
            all_beyond_1sigma = all(v > sigma1_upper or v < sigma1_lower for v in window)
            if all_beyond_1sigma:
                rule8 = True
                break

    return {
        "rule1_beyond_3sigma": rule1,
        "rule2_nine_same_side": rule2,
        "rule3_six_increasing": rule3,
        "rule4_fourteen_alternating": rule4,
        "rule5_2of3_beyond_2sigma": rule5,
        "rule6_4of5_beyond_1sigma": rule6,
        "rule7_15_within_1sigma": rule7,
        "rule8_8_beyond_1sigma": rule8,
    }
