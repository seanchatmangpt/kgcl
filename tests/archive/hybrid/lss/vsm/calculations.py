"""VSM Calculation Functions.

This module provides functions for calculating Value Stream Mapping metrics
from HybridEngine execution results.

All metrics MUST be calculated from REAL HybridEngine execution.
NO hardcoded values. NO simulated timing.
"""

from __future__ import annotations

from kgcl.hybrid.hybrid_engine import PhysicsResult
from tests.hybrid.lss.vsm.metrics import ValueStreamMetrics


def calculate_vsm_metrics(
    results: list[PhysicsResult], task_value_map: dict[str, bool] | None = None
) -> ValueStreamMetrics:
    """Calculate Value Stream Mapping metrics from execution results.

    Parameters
    ----------
    results : list[PhysicsResult]
        List of physics results from workflow execution
    task_value_map : dict[str, bool] | None
        Map of task IDs to value-add status (True = value-add)

    Returns
    -------
    ValueStreamMetrics
        Complete VSM analysis

    Examples
    --------
    >>> from kgcl.hybrid.hybrid_engine import PhysicsResult
    >>> # Example: Simple 3-tick execution with processing and wait time
    >>> results = [
    ...     PhysicsResult(tick_number=0, duration_ms=10.0, triples_before=5, triples_after=7, delta=2),
    ...     PhysicsResult(tick_number=1, duration_ms=5.0, triples_before=7, triples_after=7, delta=0),
    ...     PhysicsResult(tick_number=2, duration_ms=10.0, triples_before=7, triples_after=5, delta=-2),
    ... ]
    >>> vsm = calculate_vsm_metrics(results)
    >>> vsm.lead_time_ms
    25.0
    >>> vsm.total_cycle_time_ms  # Only tick 0 has delta > 0
    10.0
    >>> vsm.total_wait_time_ms
    5.0
    >>> vsm.total_ticks
    3
    >>> vsm.max_wip
    2

    >>> # Example: Empty results
    >>> empty_vsm = calculate_vsm_metrics([])
    >>> empty_vsm.lead_time_ms
    0.0
    >>> empty_vsm.process_efficiency
    0.0
    >>> empty_vsm.waste_percentage
    0.0

    >>> # Example: All productive work (no delta==0 ticks)
    >>> all_work = [PhysicsResult(0, 10.0, 5, 6, 1), PhysicsResult(1, 10.0, 6, 7, 1), PhysicsResult(2, 10.0, 7, 5, -2)]
    >>> efficient = calculate_vsm_metrics(all_work)
    >>> round(efficient.process_efficiency, 2)  # 20ms work (delta>0) / 30ms total
    0.67
    >>> efficient.waste_percentage  # No delta==0 ticks, so 0% waste
    0.0

    >>> # Example: High waste scenario (only delta > 0 counts as work)
    >>> high_waste = [
    ...     PhysicsResult(0, 10.0, 5, 6, 1),  # Work
    ...     PhysicsResult(1, 40.0, 6, 6, 0),  # Wait (delta=0)
    ...     PhysicsResult(2, 40.0, 6, 6, 0),  # Wait (delta=0)
    ...     PhysicsResult(3, 10.0, 6, 5, -1),  # Not work (delta < 0)
    ... ]
    >>> wasteful = calculate_vsm_metrics(high_waste)
    >>> wasteful.lead_time_ms
    100.0
    >>> wasteful.total_cycle_time_ms  # Only tick 0 has delta > 0
    10.0
    >>> wasteful.total_wait_time_ms  # Ticks 1, 2 have delta == 0
    80.0
    >>> wasteful.waste_percentage
    80.0
    """
    if not results:
        return ValueStreamMetrics(
            lead_time_ms=0.0,
            total_cycle_time_ms=0.0,
            total_wait_time_ms=0.0,
            value_add_time_ms=0.0,
            non_value_add_time_ms=0.0,
            process_efficiency=0.0,
            max_wip=0,
            total_ticks=0,
            bottleneck_task=None,
            waste_percentage=0.0,
        )

    # Lead time: sum of all tick durations
    lead_time_ms = sum(r.duration_ms for r in results)

    # Total cycle time: time spent processing (active work)
    # For simplicity, assume each tick's duration is cycle time if delta > 0
    total_cycle_time_ms = sum(r.duration_ms for r in results if r.delta > 0)

    # Wait time: ticks with no changes (waste)
    total_wait_time_ms = sum(r.duration_ms for r in results if r.delta == 0)

    # Value-add vs non-value-add (if task map provided)
    # For this POC, assume processing ticks are value-add
    value_add_time_ms = total_cycle_time_ms
    non_value_add_time_ms = total_wait_time_ms

    # Process efficiency: value_add / lead_time
    process_efficiency = value_add_time_ms / lead_time_ms if lead_time_ms > 0 else 0.0

    # Max WIP: approximate by max delta in single tick
    max_wip = max((r.delta for r in results), default=0)

    # Total ticks
    total_ticks = len(results)

    # Waste percentage
    waste_percentage = (total_wait_time_ms / lead_time_ms * 100) if lead_time_ms > 0 else 0.0

    # Bottleneck: tick with longest duration
    bottleneck_tick = max(results, key=lambda r: r.duration_ms, default=None)
    bottleneck_task = f"Tick {bottleneck_tick.tick_number}" if bottleneck_tick else None

    return ValueStreamMetrics(
        lead_time_ms=lead_time_ms,
        total_cycle_time_ms=total_cycle_time_ms,
        total_wait_time_ms=total_wait_time_ms,
        value_add_time_ms=value_add_time_ms,
        non_value_add_time_ms=non_value_add_time_ms,
        process_efficiency=process_efficiency,
        max_wip=max_wip,
        total_ticks=total_ticks,
        bottleneck_task=bottleneck_task,
        waste_percentage=waste_percentage,
    )


def identify_bottlenecks(results: list[PhysicsResult]) -> list[tuple[int, float]]:
    """Identify bottleneck ticks (slowest processing times).

    Parameters
    ----------
    results : list[PhysicsResult]
        Execution results

    Returns
    -------
    list[tuple[int, float]]
        List of (tick_number, duration_ms) sorted by duration (slowest first)

    Examples
    --------
    >>> from kgcl.hybrid.hybrid_engine import PhysicsResult
    >>> results = [
    ...     PhysicsResult(0, 5.0, 5, 6, 1),
    ...     PhysicsResult(1, 20.0, 6, 7, 1),  # Slowest
    ...     PhysicsResult(2, 10.0, 7, 8, 1),
    ... ]
    >>> bottlenecks = identify_bottlenecks(results)
    >>> bottlenecks[0]  # Slowest first
    (1, 20.0)
    >>> bottlenecks[-1]  # Fastest last
    (0, 5.0)

    >>> # Empty results
    >>> identify_bottlenecks([])
    []

    >>> # Single result
    >>> single = [PhysicsResult(0, 15.0, 5, 6, 1)]
    >>> identify_bottlenecks(single)
    [(0, 15.0)]

    >>> # Verify sorting order
    >>> results_unsorted = [
    ...     PhysicsResult(0, 10.0, 5, 6, 1),
    ...     PhysicsResult(1, 30.0, 6, 7, 1),
    ...     PhysicsResult(2, 20.0, 7, 8, 1),
    ... ]
    >>> sorted_bottlenecks = identify_bottlenecks(results_unsorted)
    >>> sorted_bottlenecks[0][1] >= sorted_bottlenecks[1][1] >= sorted_bottlenecks[2][1]
    True
    """
    return sorted([(r.tick_number, r.duration_ms) for r in results], key=lambda x: x[1], reverse=True)


def calculate_takt_time(available_time_ms: float, demand: int) -> float:
    """Calculate takt time (pace of customer demand).

    Takt time is the maximum time per unit to meet customer demand,
    calculated as: available_time / demand

    Parameters
    ----------
    available_time_ms : float
        Available processing time (ms)
    demand : int
        Number of workflow instances demanded

    Returns
    -------
    float
        Takt time per workflow instance (ms)

    Examples
    --------
    >>> # 10 seconds available, 5 instances needed
    >>> calculate_takt_time(10000.0, 5)
    2000.0

    >>> # 1 second available, 10 instances needed
    >>> calculate_takt_time(1000.0, 10)
    100.0

    >>> # Zero demand
    >>> calculate_takt_time(1000.0, 0)
    0.0

    >>> # High demand scenario
    >>> calculate_takt_time(60000.0, 100)  # 1 minute for 100 instances
    600.0

    >>> # Single instance
    >>> calculate_takt_time(5000.0, 1)
    5000.0
    """
    return available_time_ms / demand if demand > 0 else 0.0


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
