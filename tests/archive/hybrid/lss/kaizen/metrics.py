"""Kaizen measurement framework with comprehensive doctests.

Provides KaizenMetric and KaizenReport for tracking continuous improvement cycles.

Examples
--------
Create a simple metric showing 50% improvement:

>>> metric = KaizenMetric("Tick Count", 10.0, 5.0, 3.0, "ticks")
>>> metric.improvement_pct
50.0
>>> metric.meets_target
False

Create a report with multiple metrics:

>>> m1 = KaizenMetric("Ticks", 10.0, 5.0, 3.0, "ticks")
>>> m2 = KaizenMetric("Time", 100.0, 80.0, 50.0, "ms")
>>> report = KaizenReport("Cycle 1", [m1, m2], ["Optimize LAW 3"])
>>> report.overall_improvement
35.0
>>> report.targets_met
0

Show a metric that meets target:

>>> metric = KaizenMetric("Latency", 100.0, 30.0, 50.0, "ms")
>>> metric.improvement_pct
70.0
>>> metric.meets_target
True
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KaizenMetric:
    """Metric for measuring continuous improvement.

    Parameters
    ----------
    name : str
        Metric name
    before : float
        Baseline measurement
    after : float
        Improved measurement
    target : float
        Target value for excellence
    unit : str
        Unit of measurement

    Examples
    --------
    Basic improvement calculation:

    >>> metric = KaizenMetric("Response Time", 100.0, 80.0, 50.0, "ms")
    >>> metric.improvement_pct
    20.0
    >>> metric.meets_target
    False

    Zero baseline (no improvement possible):

    >>> metric = KaizenMetric("Count", 0.0, 5.0, 10.0, "items")
    >>> metric.improvement_pct
    0.0

    Perfect improvement (meets target):

    >>> metric = KaizenMetric("Ticks", 10.0, 3.0, 5.0, "ticks")
    >>> metric.improvement_pct
    70.0
    >>> metric.meets_target
    True

    Exact target match:

    >>> metric = KaizenMetric("Memory", 100.0, 50.0, 50.0, "MB")
    >>> metric.meets_target
    True

    Negative improvement (regression):

    >>> metric = KaizenMetric("Errors", 5.0, 10.0, 3.0, "count")
    >>> metric.improvement_pct
    -100.0
    >>> metric.meets_target
    False
    """

    name: str
    before: float
    after: float
    target: float
    unit: str

    @property
    def improvement_pct(self) -> float:
        """Calculate improvement percentage.

        Returns
        -------
        float
            Percentage improvement from before to after.

        Examples
        --------
        50% improvement:

        >>> metric = KaizenMetric("Ticks", 10.0, 5.0, 3.0, "ticks")
        >>> metric.improvement_pct
        50.0

        20% improvement:

        >>> metric = KaizenMetric("Time", 100.0, 80.0, 50.0, "ms")
        >>> metric.improvement_pct
        20.0

        Zero baseline:

        >>> metric = KaizenMetric("New", 0.0, 10.0, 5.0, "x")
        >>> metric.improvement_pct
        0.0

        75% improvement:

        >>> metric = KaizenMetric("Complexity", 20.0, 5.0, 3.0, "score")
        >>> metric.improvement_pct
        75.0
        """
        if self.before == 0:
            return 0.0
        return ((self.before - self.after) / self.before) * 100

    @property
    def meets_target(self) -> bool:
        """Check if target is met.

        Returns
        -------
        bool
            True if after meets or exceeds target.

        Examples
        --------
        Meets target (lower is better):

        >>> metric = KaizenMetric("Ticks", 10.0, 3.0, 5.0, "ticks")
        >>> metric.meets_target
        True

        Does not meet target:

        >>> metric = KaizenMetric("Time", 100.0, 80.0, 50.0, "ms")
        >>> metric.meets_target
        False

        Exact target:

        >>> metric = KaizenMetric("Memory", 100.0, 50.0, 50.0, "MB")
        >>> metric.meets_target
        True

        Exceeds target:

        >>> metric = KaizenMetric("Latency", 100.0, 20.0, 30.0, "ms")
        >>> metric.meets_target
        True
        """
        return self.after <= self.target


@dataclass(frozen=True)
class KaizenReport:
    """Report of continuous improvement cycle.

    Parameters
    ----------
    cycle : str
        Improvement cycle identifier
    metrics : list[KaizenMetric]
        Metrics tracked during cycle
    action_items : list[str]
        Action items for next cycle

    Examples
    --------
    Simple report with one metric:

    >>> metrics = [KaizenMetric("Ticks", 10.0, 5.0, 3.0, "ticks")]
    >>> report = KaizenReport("Cycle 1", metrics, ["Optimize LAW 3"])
    >>> report.overall_improvement
    50.0
    >>> report.targets_met
    0

    Report with multiple metrics:

    >>> m1 = KaizenMetric("Ticks", 10.0, 5.0, 3.0, "ticks")
    >>> m2 = KaizenMetric("Time", 100.0, 80.0, 50.0, "ms")
    >>> report = KaizenReport("Cycle 2", [m1, m2], ["Action 1", "Action 2"])
    >>> report.overall_improvement
    35.0
    >>> report.targets_met
    0
    >>> len(report.action_items)
    2

    Report with target-meeting metrics:

    >>> m1 = KaizenMetric("A", 10.0, 2.0, 3.0, "x")
    >>> m2 = KaizenMetric("B", 100.0, 40.0, 50.0, "y")
    >>> report = KaizenReport("C1", [m1, m2], [])
    >>> report.targets_met
    2

    Empty report:

    >>> report = KaizenReport("Empty", [], ["TODO"])
    >>> report.overall_improvement
    0.0
    >>> report.targets_met
    0
    """

    cycle: str
    metrics: list[KaizenMetric]
    action_items: list[str]

    @property
    def overall_improvement(self) -> float:
        """Calculate overall improvement across metrics.

        Returns
        -------
        float
            Average improvement percentage.

        Examples
        --------
        Two metrics averaging to 35%:

        >>> m1 = KaizenMetric("A", 10.0, 5.0, 3.0, "x")
        >>> m2 = KaizenMetric("B", 100.0, 80.0, 50.0, "y")
        >>> report = KaizenReport("C1", [m1, m2], [])
        >>> report.overall_improvement
        35.0

        Single metric:

        >>> m = KaizenMetric("Single", 100.0, 25.0, 10.0, "z")
        >>> report = KaizenReport("C2", [m], [])
        >>> report.overall_improvement
        75.0

        Empty metrics:

        >>> report = KaizenReport("Empty", [], [])
        >>> report.overall_improvement
        0.0

        Three metrics:

        >>> m1 = KaizenMetric("A", 10.0, 5.0, 2.0, "a")
        >>> m2 = KaizenMetric("B", 20.0, 10.0, 5.0, "b")
        >>> m3 = KaizenMetric("C", 30.0, 15.0, 10.0, "c")
        >>> report = KaizenReport("C3", [m1, m2, m3], [])
        >>> report.overall_improvement
        50.0
        """
        if not self.metrics:
            return 0.0
        return sum(m.improvement_pct for m in self.metrics) / len(self.metrics)

    @property
    def targets_met(self) -> int:
        """Count how many targets were met.

        Returns
        -------
        int
            Number of metrics meeting target.

        Examples
        --------
        One target met:

        >>> m1 = KaizenMetric("A", 10.0, 2.0, 3.0, "x")
        >>> m2 = KaizenMetric("B", 100.0, 80.0, 50.0, "y")
        >>> report = KaizenReport("C1", [m1, m2], [])
        >>> report.targets_met
        1

        All targets met:

        >>> m1 = KaizenMetric("A", 10.0, 2.0, 5.0, "x")
        >>> m2 = KaizenMetric("B", 100.0, 40.0, 50.0, "y")
        >>> report = KaizenReport("C2", [m1, m2], [])
        >>> report.targets_met
        2

        No targets met:

        >>> m1 = KaizenMetric("A", 10.0, 8.0, 5.0, "x")
        >>> m2 = KaizenMetric("B", 100.0, 90.0, 50.0, "y")
        >>> report = KaizenReport("C3", [m1, m2], [])
        >>> report.targets_met
        0

        Empty metrics:

        >>> report = KaizenReport("Empty", [], [])
        >>> report.targets_met
        0
        """
        return sum(1 for m in self.metrics if m.meets_target)
