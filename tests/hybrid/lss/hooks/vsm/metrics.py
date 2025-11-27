"""VSM Metrics for Knowledge Hooks.

This module defines Value Stream Mapping metrics for Knowledge Hooks,
capturing lean manufacturing KPIs for hook execution lifecycle analysis.

The metrics distinguish between:
- Value-add time: Hook actions that transform/assert data (ASSERT, TRANSFORM)
- Non-value-add time: Hook overhead (NOTIFY, REJECT, condition evaluation)
- Wait time: Time waiting for hook conditions to be evaluated

References
----------
- Rother, M., & Shook, J. (2003). Learning to See: Value Stream Mapping
- Womack, J. P., & Jones, D. T. (1996). Lean Thinking
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HookTaskMetrics:
    """Metrics for a single hook execution in the value stream.

    Parameters
    ----------
    hook_id : str
        Hook identifier (URI)
    phase : str
        Hook phase (pre_tick, on_change, post_tick, etc.)
    cycle_time_ms : float
        Time spent in active hook execution (ms)
    wait_time_ms : float
        Time spent waiting for condition evaluation (ms)
    condition_eval_start_tick : int
        Tick when condition evaluation started
    condition_eval_end_tick : int
        Tick when condition evaluation completed
    value_add : bool
        Whether hook action adds value (ASSERT/TRANSFORM) vs overhead (NOTIFY/REJECT)

    Notes
    -----
    Value-adding actions:
    - ASSERT: Adds triples to knowledge graph (direct value)
    - TRANSFORM: Modifies triples before commit (direct value)

    Non-value-adding actions (overhead):
    - NOTIFY: Creates notification records (audit overhead)
    - REJECT: Rejects changes and triggers rollback (validation overhead)

    Condition evaluation is always non-value-add (pre-processing overhead).

    Examples
    --------
    >>> # Value-adding hook: ASSERT action
    >>> assert_hook = HookTaskMetrics(
    ...     hook_id="urn:hook:add-timestamp",
    ...     phase="post_tick",
    ...     cycle_time_ms=5.0,
    ...     wait_time_ms=2.0,
    ...     condition_eval_start_tick=0,
    ...     condition_eval_end_tick=0,
    ...     value_add=True,
    ... )
    >>> assert_hook.hook_id
    'urn:hook:add-timestamp'
    >>> assert_hook.cycle_time_ms
    5.0
    >>> assert_hook.value_add
    True

    >>> # Non-value-add hook: NOTIFY action (audit overhead)
    >>> notify_hook = HookTaskMetrics(
    ...     hook_id="urn:hook:audit-log",
    ...     phase="on_change",
    ...     cycle_time_ms=3.0,
    ...     wait_time_ms=1.0,
    ...     condition_eval_start_tick=1,
    ...     condition_eval_end_tick=1,
    ...     value_add=False,
    ... )
    >>> notify_hook.value_add
    False

    >>> # Validation hook: REJECT action (quality gate overhead)
    >>> reject_hook = HookTaskMetrics(
    ...     hook_id="urn:hook:validate-person",
    ...     phase="pre_validation",
    ...     cycle_time_ms=8.0,
    ...     wait_time_ms=4.0,
    ...     condition_eval_start_tick=0,
    ...     condition_eval_end_tick=1,
    ...     value_add=False,
    ... )
    >>> reject_hook.cycle_time_ms
    8.0
    >>> reject_hook.wait_time_ms
    4.0
    """

    hook_id: str
    phase: str
    cycle_time_ms: float
    wait_time_ms: float
    condition_eval_start_tick: int
    condition_eval_end_tick: int
    value_add: bool


@dataclass(frozen=True)
class HookValueStreamMetrics:
    """Complete value stream analysis metrics for hook execution lifecycle.

    Captures all key VSM metrics including lead time, cycle time, waste,
    efficiency, and bottleneck identification for Knowledge Hooks.

    Parameters
    ----------
    lead_time_ms : float
        Total time from hook trigger to completion (ms)
    total_cycle_time_ms : float
        Sum of all hook execution times (ms)
    total_wait_time_ms : float
        Sum of all condition evaluation wait times (waste) (ms)
    value_add_time_ms : float
        Time spent in value-adding actions (ASSERT/TRANSFORM) (ms)
    non_value_add_time_ms : float
        Time spent in non-value actions (NOTIFY/REJECT/conditions) (ms)
    process_efficiency : float
        Ratio: value_add_time / lead_time (0-1)
    max_concurrent_hooks : int
        Maximum hooks executing simultaneously observed
    bottleneck_hook : str | None
        Hook ID with longest execution duration
    waste_percentage : float
        Percentage of lead time that is waste (0-100)

    Notes
    -----
    Process efficiency is the ratio of value-add time to lead time:
        efficiency = value_add_time_ms / lead_time_ms

    Waste percentage is the ratio of non-value time to lead time:
        waste_pct = (non_value_add_time_ms / lead_time_ms) * 100

    In Lean terminology:
    - Lead time = Total elapsed time (customer perspective)
    - Cycle time = Active processing time
    - Wait time = Queue time (pure waste)
    - Value-add ratio = Efficiency target (aim for >0.7)

    Examples
    --------
    >>> # High-efficiency hook workflow (mostly ASSERT/TRANSFORM)
    >>> efficient_hooks = HookValueStreamMetrics(
    ...     lead_time_ms=100.0,
    ...     total_cycle_time_ms=90.0,
    ...     total_wait_time_ms=10.0,
    ...     value_add_time_ms=85.0,
    ...     non_value_add_time_ms=15.0,
    ...     process_efficiency=0.85,
    ...     max_concurrent_hooks=4,
    ...     bottleneck_hook="urn:hook:complex-transform",
    ...     waste_percentage=15.0,
    ... )
    >>> efficient_hooks.process_efficiency
    0.85
    >>> efficient_hooks.waste_percentage
    15.0
    >>> efficient_hooks.lead_time_ms == efficient_hooks.value_add_time_ms + efficient_hooks.non_value_add_time_ms
    True

    >>> # Low-efficiency workflow (mostly validation/notifications)
    >>> inefficient_hooks = HookValueStreamMetrics(
    ...     lead_time_ms=100.0,
    ...     total_cycle_time_ms=40.0,
    ...     total_wait_time_ms=60.0,
    ...     value_add_time_ms=20.0,
    ...     non_value_add_time_ms=80.0,
    ...     process_efficiency=0.2,
    ...     max_concurrent_hooks=8,
    ...     bottleneck_hook="urn:hook:slow-validator",
    ...     waste_percentage=80.0,
    ... )
    >>> inefficient_hooks.process_efficiency
    0.2
    >>> inefficient_hooks.waste_percentage
    80.0
    >>> inefficient_hooks.total_wait_time_ms > inefficient_hooks.total_cycle_time_ms
    True

    >>> # Verify efficiency calculation
    >>> expected_efficiency = efficient_hooks.value_add_time_ms / efficient_hooks.lead_time_ms
    >>> abs(efficient_hooks.process_efficiency - expected_efficiency) < 0.001
    True

    >>> # Verify waste calculation
    >>> expected_waste = (inefficient_hooks.non_value_add_time_ms / inefficient_hooks.lead_time_ms) * 100
    >>> abs(inefficient_hooks.waste_percentage - expected_waste) < 0.001
    True

    >>> # Bottleneck identification
    >>> efficient_hooks.bottleneck_hook
    'urn:hook:complex-transform'
    >>> inefficient_hooks.bottleneck_hook
    'urn:hook:slow-validator'

    >>> # Parallel execution capacity
    >>> efficient_hooks.max_concurrent_hooks
    4
    >>> inefficient_hooks.max_concurrent_hooks
    8
    """

    lead_time_ms: float
    total_cycle_time_ms: float
    total_wait_time_ms: float
    value_add_time_ms: float
    non_value_add_time_ms: float
    process_efficiency: float
    max_concurrent_hooks: int
    bottleneck_hook: str | None
    waste_percentage: float


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
