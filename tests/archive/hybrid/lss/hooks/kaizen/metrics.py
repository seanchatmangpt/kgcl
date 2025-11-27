"""Kaizen waste analysis for Knowledge Hooks.

Applies the 3M waste framework (Muda, Mura, Muri) to hook execution:
- MUDA (無駄): The 7 wastes in hook operations
- MURA (斑): Unevenness in hook performance
- MURI (無理): Overburden in hook execution

Examples
--------
Detect overprocessing waste (unnecessary condition evaluations):

>>> from kgcl.hybrid.knowledge_hooks import HookPhase
>>> metrics = HookMudaMetrics(
...     waste_type=HookMudaType.OVERPROCESSING, count=5, total_duration_ms=250.0, percentage_of_total=25.0
... )
>>> metrics.count
5
>>> metrics.total_duration_ms
250.0

Measure hook timing unevenness:

>>> mura = HookMuraMetrics(coefficient_of_variation=0.85, max_duration_ms=150.0, min_duration_ms=10.0)
>>> mura.coefficient_of_variation
0.85

Detect hook overload:

>>> muri = HookMuriMetrics(hooks_per_tick=12.5, max_concurrent=8, overload_threshold=10, is_overloaded=False)
>>> muri.hooks_per_tick
12.5
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HookMudaType(Enum):
    """Types of waste (Muda) in hook execution.

    The 7 wastes of Lean applied to Knowledge Hooks:
    - OVERPROCESSING: Unnecessary condition evaluations
    - WAITING: Hooks blocked by priority or phase dependencies
    - MOTION: Excessive phase transitions or context switches
    - INVENTORY: Too many pending hooks (queued but not executed)
    - DEFECTS: Failed hook executions or error states
    - OVERPRODUCTION: Redundant assertions or duplicate operations
    - TRANSPORT: Cross-phase data movement or serialization overhead

    Examples
    --------
    >>> waste = HookMudaType.OVERPROCESSING
    >>> waste.value
    'overprocessing'

    >>> HookMudaType.WAITING.value
    'waiting'

    >>> HookMudaType.DEFECTS.value
    'defects'
    """

    OVERPROCESSING = "overprocessing"
    WAITING = "waiting"
    MOTION = "motion"
    INVENTORY = "inventory"
    DEFECTS = "defects"
    OVERPRODUCTION = "overproduction"
    TRANSPORT = "transport"


@dataclass(frozen=True)
class HookMudaMetrics:
    """Metrics for measuring waste (Muda) in hook execution.

    Tracks a specific type of waste with count, duration, and percentage impact.

    Parameters
    ----------
    waste_type : HookMudaType
        Type of waste being measured
    count : int
        Number of wasteful operations
    total_duration_ms : float
        Total time spent on waste (milliseconds)
    percentage_of_total : float
        Percentage of total execution time wasted

    Examples
    --------
    Track overprocessing waste:

    >>> metrics = HookMudaMetrics(
    ...     waste_type=HookMudaType.OVERPROCESSING, count=3, total_duration_ms=45.0, percentage_of_total=15.0
    ... )
    >>> metrics.waste_type
    <HookMudaType.OVERPROCESSING: 'overprocessing'>
    >>> metrics.count
    3
    >>> metrics.total_duration_ms
    45.0

    Track defect waste:

    >>> defects = HookMudaMetrics(
    ...     waste_type=HookMudaType.DEFECTS, count=2, total_duration_ms=80.0, percentage_of_total=20.0
    ... )
    >>> defects.waste_type.value
    'defects'
    >>> defects.count
    2

    Zero waste case:

    >>> zero = HookMudaMetrics(waste_type=HookMudaType.WAITING, count=0, total_duration_ms=0.0, percentage_of_total=0.0)
    >>> zero.count
    0
    """

    waste_type: HookMudaType
    count: int
    total_duration_ms: float
    percentage_of_total: float


@dataclass(frozen=True)
class HookMuraMetrics:
    """Metrics for measuring unevenness (Mura) in hook performance.

    Tracks variation and inconsistency in hook execution times.

    Parameters
    ----------
    coefficient_of_variation : float
        Standard deviation / mean (measures relative variability)
    max_duration_ms : float
        Maximum hook execution time
    min_duration_ms : float
        Minimum hook execution time

    Notes
    -----
    Coefficient of Variation (CV) interpretation:
    - CV < 0.5: Low variability (good consistency)
    - 0.5 <= CV < 1.0: Moderate variability
    - CV >= 1.0: High variability (unevenness problem)

    Examples
    --------
    Low variability (good):

    >>> metrics = HookMuraMetrics(coefficient_of_variation=0.3, max_duration_ms=25.0, min_duration_ms=15.0)
    >>> metrics.coefficient_of_variation < 0.5
    True

    High variability (problem):

    >>> uneven = HookMuraMetrics(coefficient_of_variation=1.2, max_duration_ms=200.0, min_duration_ms=10.0)
    >>> uneven.coefficient_of_variation >= 1.0
    True

    Perfect consistency:

    >>> perfect = HookMuraMetrics(coefficient_of_variation=0.0, max_duration_ms=20.0, min_duration_ms=20.0)
    >>> perfect.coefficient_of_variation
    0.0
    >>> perfect.max_duration_ms == perfect.min_duration_ms
    True
    """

    coefficient_of_variation: float
    max_duration_ms: float
    min_duration_ms: float


@dataclass(frozen=True)
class HookMuriMetrics:
    """Metrics for measuring overburden (Muri) in hook execution.

    Tracks system stress and capacity limits.

    Parameters
    ----------
    hooks_per_tick : float
        Average number of hooks executed per tick
    max_concurrent : int
        Maximum number of hooks executing simultaneously
    overload_threshold : int
        Threshold for considering system overloaded
    is_overloaded : bool
        Whether system is currently overloaded

    Examples
    --------
    Normal load:

    >>> metrics = HookMuriMetrics(hooks_per_tick=5.0, max_concurrent=3, overload_threshold=10, is_overloaded=False)
    >>> metrics.is_overloaded
    False
    >>> metrics.hooks_per_tick < metrics.overload_threshold
    True

    Overloaded system:

    >>> overloaded = HookMuriMetrics(hooks_per_tick=15.0, max_concurrent=12, overload_threshold=10, is_overloaded=True)
    >>> overloaded.is_overloaded
    True
    >>> overloaded.hooks_per_tick > overloaded.overload_threshold
    True

    Approaching capacity:

    >>> near_limit = HookMuriMetrics(hooks_per_tick=9.5, max_concurrent=8, overload_threshold=10, is_overloaded=False)
    >>> near_limit.hooks_per_tick / near_limit.overload_threshold > 0.9
    True

    Zero load:

    >>> idle = HookMuriMetrics(hooks_per_tick=0.0, max_concurrent=0, overload_threshold=10, is_overloaded=False)
    >>> idle.hooks_per_tick
    0.0
    """

    hooks_per_tick: float
    max_concurrent: int
    overload_threshold: int
    is_overloaded: bool


@dataclass(frozen=True)
class HookWasteAnalysis:
    """Comprehensive waste analysis for hook execution cycle.

    Combines all three types of waste (Muda, Mura, Muri) into a single report.

    Parameters
    ----------
    cycle_id : str
        Unique identifier for analysis cycle
    muda_metrics : list[HookMudaMetrics]
        List of Muda (waste) metrics
    mura_metrics : HookMuraMetrics
        Mura (unevenness) metrics
    muri_metrics : HookMuriMetrics
        Muri (overburden) metrics
    total_hooks_executed : int
        Total number of hooks executed
    total_duration_ms : float
        Total execution time (milliseconds)

    Examples
    --------
    Complete waste analysis:

    >>> muda = [
    ...     HookMudaMetrics(HookMudaType.OVERPROCESSING, 3, 45.0, 15.0),
    ...     HookMudaMetrics(HookMudaType.WAITING, 2, 30.0, 10.0),
    ... ]
    >>> mura = HookMuraMetrics(0.5, 80.0, 20.0)
    >>> muri = HookMuriMetrics(8.0, 5, 10, False)
    >>> analysis = HookWasteAnalysis(
    ...     cycle_id="tick-001",
    ...     muda_metrics=muda,
    ...     mura_metrics=mura,
    ...     muri_metrics=muri,
    ...     total_hooks_executed=10,
    ...     total_duration_ms=300.0,
    ... )
    >>> analysis.total_hooks_executed
    10
    >>> len(analysis.muda_metrics)
    2

    Calculate total waste percentage:

    >>> total_waste = sum(m.percentage_of_total for m in analysis.muda_metrics)
    >>> total_waste
    25.0

    Zero waste baseline:

    >>> baseline = HookWasteAnalysis(
    ...     cycle_id="baseline",
    ...     muda_metrics=[],
    ...     mura_metrics=HookMuraMetrics(0.0, 10.0, 10.0),
    ...     muri_metrics=HookMuriMetrics(5.0, 3, 10, False),
    ...     total_hooks_executed=5,
    ...     total_duration_ms=100.0,
    ... )
    >>> len(baseline.muda_metrics)
    0
    """

    cycle_id: str
    muda_metrics: list[HookMudaMetrics]
    mura_metrics: HookMuraMetrics
    muri_metrics: HookMuriMetrics
    total_hooks_executed: int
    total_duration_ms: float

    @property
    def total_waste_percentage(self) -> float:
        """Calculate total waste as percentage of execution time.

        Returns
        -------
        float
            Sum of all waste percentages

        Examples
        --------
        >>> muda = [
        ...     HookMudaMetrics(HookMudaType.OVERPROCESSING, 1, 10.0, 10.0),
        ...     HookMudaMetrics(HookMudaType.WAITING, 1, 15.0, 15.0),
        ... ]
        >>> mura = HookMuraMetrics(0.5, 50.0, 10.0)
        >>> muri = HookMuriMetrics(5.0, 3, 10, False)
        >>> analysis = HookWasteAnalysis("c1", muda, mura, muri, 5, 100.0)
        >>> analysis.total_waste_percentage
        25.0

        >>> no_waste = HookWasteAnalysis("c2", [], mura, muri, 5, 100.0)
        >>> no_waste.total_waste_percentage
        0
        """
        return sum(m.percentage_of_total for m in self.muda_metrics)

    @property
    def has_unevenness_problem(self) -> bool:
        """Check if execution has significant unevenness.

        Returns
        -------
        bool
            True if coefficient of variation >= 1.0

        Examples
        --------
        >>> muda: list[HookMudaMetrics] = []
        >>> mura_uneven = HookMuraMetrics(1.2, 100.0, 10.0)
        >>> muri = HookMuriMetrics(5.0, 3, 10, False)
        >>> analysis = HookWasteAnalysis("c1", muda, mura_uneven, muri, 5, 100.0)
        >>> analysis.has_unevenness_problem
        True

        >>> mura_even = HookMuraMetrics(0.3, 50.0, 40.0)
        >>> good = HookWasteAnalysis("c2", muda, mura_even, muri, 5, 100.0)
        >>> good.has_unevenness_problem
        False
        """
        return self.mura_metrics.coefficient_of_variation >= 1.0

    @property
    def has_overload_problem(self) -> bool:
        """Check if system is overloaded.

        Returns
        -------
        bool
            True if system is marked as overloaded

        Examples
        --------
        >>> muda: list[HookMudaMetrics] = []
        >>> mura = HookMuraMetrics(0.5, 50.0, 10.0)
        >>> muri_ok = HookMuriMetrics(5.0, 3, 10, False)
        >>> analysis = HookWasteAnalysis("c1", muda, mura, muri_ok, 5, 100.0)
        >>> analysis.has_overload_problem
        False

        >>> muri_bad = HookMuriMetrics(15.0, 12, 10, True)
        >>> overloaded = HookWasteAnalysis("c2", muda, mura, muri_bad, 15, 500.0)
        >>> overloaded.has_overload_problem
        True
        """
        return self.muri_metrics.is_overloaded
