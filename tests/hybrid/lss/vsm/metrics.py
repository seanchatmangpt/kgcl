"""VSM Metrics Data Structures.

This module defines dataclasses for Value Stream Mapping metrics,
capturing lean manufacturing KPIs for workflow analysis.

References
----------
- Rother, M., & Shook, J. (2003). Learning to See: Value Stream Mapping
- Womack, J. P., & Jones, D. T. (1996). Lean Thinking
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskMetrics:
    """Metrics for a single task in the value stream.

    Parameters
    ----------
    task_id : str
        Task identifier
    cycle_time_ms : float
        Time spent in active processing (ms)
    wait_time_ms : float
        Time spent waiting for activation (ms)
    processing_start_tick : int
        Tick when task activated
    processing_end_tick : int
        Tick when task completed
    value_add : bool
        Whether task adds customer value

    Examples
    --------
    >>> task = TaskMetrics(
    ...     task_id="TaskA",
    ...     cycle_time_ms=50.0,
    ...     wait_time_ms=10.0,
    ...     processing_start_tick=0,
    ...     processing_end_tick=5,
    ...     value_add=True,
    ... )
    >>> task.task_id
    'TaskA'
    >>> task.cycle_time_ms
    50.0
    >>> task.value_add
    True

    >>> # Non-value-add task example
    >>> overhead = TaskMetrics(
    ...     task_id="Logging",
    ...     cycle_time_ms=5.0,
    ...     wait_time_ms=0.0,
    ...     processing_start_tick=2,
    ...     processing_end_tick=2,
    ...     value_add=False,
    ... )
    >>> overhead.value_add
    False
    """

    task_id: str
    cycle_time_ms: float
    wait_time_ms: float
    processing_start_tick: int
    processing_end_tick: int
    value_add: bool


@dataclass(frozen=True)
class ValueStreamMetrics:
    """Complete value stream analysis metrics.

    Captures all key VSM metrics including lead time, cycle time, waste,
    efficiency, and bottleneck identification.

    Parameters
    ----------
    lead_time_ms : float
        Total time from start to completion (ms)
    total_cycle_time_ms : float
        Sum of all task cycle times (ms)
    total_wait_time_ms : float
        Sum of all wait times (waste) (ms)
    value_add_time_ms : float
        Time spent in value-adding work (ms)
    non_value_add_time_ms : float
        Time spent in non-value work (ms)
    process_efficiency : float
        Ratio: value_add_time / lead_time (0-1)
    max_wip : int
        Maximum concurrent active tasks observed
    total_ticks : int
        Total ticks to completion
    bottleneck_task : str | None
        Task with longest cycle time
    waste_percentage : float
        Percentage of lead time that is waste (0-100)

    Notes
    -----
    Process efficiency is the ratio of value-add time to lead time:
        efficiency = value_add_time_ms / lead_time_ms

    Waste percentage is the ratio of non-value time to lead time:
        waste_pct = (total_wait_time_ms / lead_time_ms) * 100

    Examples
    --------
    >>> # High-efficiency workflow
    >>> vsm_good = ValueStreamMetrics(
    ...     lead_time_ms=100.0,
    ...     total_cycle_time_ms=90.0,
    ...     total_wait_time_ms=10.0,
    ...     value_add_time_ms=90.0,
    ...     non_value_add_time_ms=10.0,
    ...     process_efficiency=0.9,
    ...     max_wip=3,
    ...     total_ticks=10,
    ...     bottleneck_task="Tick 5",
    ...     waste_percentage=10.0,
    ... )
    >>> vsm_good.process_efficiency
    0.9
    >>> vsm_good.waste_percentage
    10.0
    >>> vsm_good.lead_time_ms == vsm_good.value_add_time_ms + vsm_good.non_value_add_time_ms
    True

    >>> # Low-efficiency workflow with high waste
    >>> vsm_bad = ValueStreamMetrics(
    ...     lead_time_ms=100.0,
    ...     total_cycle_time_ms=30.0,
    ...     total_wait_time_ms=70.0,
    ...     value_add_time_ms=30.0,
    ...     non_value_add_time_ms=70.0,
    ...     process_efficiency=0.3,
    ...     max_wip=1,
    ...     total_ticks=20,
    ...     bottleneck_task="Tick 15",
    ...     waste_percentage=70.0,
    ... )
    >>> vsm_bad.process_efficiency
    0.3
    >>> vsm_bad.waste_percentage
    70.0
    >>> vsm_bad.total_wait_time_ms > vsm_bad.total_cycle_time_ms
    True

    >>> # Verify efficiency calculation
    >>> expected_efficiency = vsm_good.value_add_time_ms / vsm_good.lead_time_ms
    >>> abs(vsm_good.process_efficiency - expected_efficiency) < 0.001
    True

    >>> # Verify waste calculation
    >>> expected_waste = (vsm_bad.total_wait_time_ms / vsm_bad.lead_time_ms) * 100
    >>> abs(vsm_bad.waste_percentage - expected_waste) < 0.001
    True
    """

    lead_time_ms: float
    total_cycle_time_ms: float
    total_wait_time_ms: float
    value_add_time_ms: float
    non_value_add_time_ms: float
    process_efficiency: float
    max_wip: int
    total_ticks: int
    bottleneck_task: str | None
    waste_percentage: float


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
