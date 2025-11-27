"""Tests for Hook VSM Metrics.

Verifies that HookTaskMetrics and HookValueStreamMetrics correctly
capture Value Stream Mapping metrics for Knowledge Hook execution.
"""

from __future__ import annotations

from kgcl.hybrid.knowledge_hooks import HookAction, HookPhase
from tests.hybrid.lss.hooks.vsm.metrics import HookTaskMetrics, HookValueStreamMetrics


def test_hook_task_metrics_value_add_classification() -> None:
    """Verify value-add classification matches hook action types."""
    # ASSERT is value-adding (creates knowledge)
    assert_metrics = HookTaskMetrics(
        hook_id="urn:hook:add-data",
        phase=HookPhase.POST_TICK.value,
        cycle_time_ms=10.0,
        wait_time_ms=2.0,
        condition_eval_start_tick=0,
        condition_eval_end_tick=1,
        value_add=True,
    )
    assert assert_metrics.value_add is True

    # TRANSFORM is value-adding (modifies knowledge)
    transform_metrics = HookTaskMetrics(
        hook_id="urn:hook:normalize-data",
        phase=HookPhase.ON_CHANGE.value,
        cycle_time_ms=15.0,
        wait_time_ms=3.0,
        condition_eval_start_tick=1,
        condition_eval_end_tick=2,
        value_add=True,
    )
    assert transform_metrics.value_add is True

    # NOTIFY is non-value-add (audit overhead)
    notify_metrics = HookTaskMetrics(
        hook_id="urn:hook:log-event",
        phase=HookPhase.POST_TICK.value,
        cycle_time_ms=5.0,
        wait_time_ms=1.0,
        condition_eval_start_tick=2,
        condition_eval_end_tick=2,
        value_add=False,
    )
    assert notify_metrics.value_add is False

    # REJECT is non-value-add (validation overhead)
    reject_metrics = HookTaskMetrics(
        hook_id="urn:hook:validate",
        phase=HookPhase.PRE_VALIDATION.value,
        cycle_time_ms=8.0,
        wait_time_ms=4.0,
        condition_eval_start_tick=0,
        condition_eval_end_tick=1,
        value_add=False,
    )
    assert reject_metrics.value_add is False


def test_hook_value_stream_metrics_efficiency_calculation() -> None:
    """Verify process efficiency calculation matches VSM formula."""
    # High-efficiency workflow: 80% value-add
    high_eff = HookValueStreamMetrics(
        lead_time_ms=100.0,
        total_cycle_time_ms=80.0,
        total_wait_time_ms=20.0,
        value_add_time_ms=80.0,
        non_value_add_time_ms=20.0,
        process_efficiency=0.8,
        max_concurrent_hooks=3,
        bottleneck_hook="urn:hook:transform",
        waste_percentage=20.0,
    )

    expected_efficiency = high_eff.value_add_time_ms / high_eff.lead_time_ms
    assert abs(high_eff.process_efficiency - expected_efficiency) < 0.001

    expected_waste = (high_eff.non_value_add_time_ms / high_eff.lead_time_ms) * 100
    assert abs(high_eff.waste_percentage - expected_waste) < 0.001


def test_hook_value_stream_metrics_bottleneck_identification() -> None:
    """Verify bottleneck hook identification in metrics."""
    vsm = HookValueStreamMetrics(
        lead_time_ms=200.0,
        total_cycle_time_ms=150.0,
        total_wait_time_ms=50.0,
        value_add_time_ms=100.0,
        non_value_add_time_ms=100.0,
        process_efficiency=0.5,
        max_concurrent_hooks=5,
        bottleneck_hook="urn:hook:slow-validator",
        waste_percentage=50.0,
    )

    assert vsm.bottleneck_hook == "urn:hook:slow-validator"
    assert vsm.max_concurrent_hooks == 5


def test_hook_task_metrics_timing_bounds() -> None:
    """Verify tick boundary tracking for condition evaluation."""
    metrics = HookTaskMetrics(
        hook_id="urn:hook:multi-tick",
        phase=HookPhase.ON_CHANGE.value,
        cycle_time_ms=50.0,
        wait_time_ms=20.0,
        condition_eval_start_tick=5,
        condition_eval_end_tick=8,
        value_add=True,
    )

    assert metrics.condition_eval_end_tick >= metrics.condition_eval_start_tick
    tick_span = metrics.condition_eval_end_tick - metrics.condition_eval_start_tick
    assert tick_span == 3


def test_hook_value_stream_metrics_time_accounting() -> None:
    """Verify total time equals sum of value-add and non-value-add."""
    vsm = HookValueStreamMetrics(
        lead_time_ms=150.0,
        total_cycle_time_ms=120.0,
        total_wait_time_ms=30.0,
        value_add_time_ms=90.0,
        non_value_add_time_ms=60.0,
        process_efficiency=0.6,
        max_concurrent_hooks=4,
        bottleneck_hook="urn:hook:bottleneck",
        waste_percentage=40.0,
    )

    # Lead time must equal value-add + non-value-add
    assert abs(vsm.lead_time_ms - (vsm.value_add_time_ms + vsm.non_value_add_time_ms)) < 0.001


def test_hook_metrics_frozen_immutability() -> None:
    """Verify metrics dataclasses are frozen (immutable)."""
    task_metrics = HookTaskMetrics(
        hook_id="urn:hook:test",
        phase=HookPhase.POST_TICK.value,
        cycle_time_ms=10.0,
        wait_time_ms=2.0,
        condition_eval_start_tick=0,
        condition_eval_end_tick=1,
        value_add=True,
    )

    try:
        task_metrics.cycle_time_ms = 20.0  # type: ignore[misc]
        raise AssertionError("Should not allow mutation of frozen dataclass")
    except AttributeError:
        pass  # Expected

    vsm = HookValueStreamMetrics(
        lead_time_ms=100.0,
        total_cycle_time_ms=80.0,
        total_wait_time_ms=20.0,
        value_add_time_ms=70.0,
        non_value_add_time_ms=30.0,
        process_efficiency=0.7,
        max_concurrent_hooks=3,
        bottleneck_hook="urn:hook:test",
        waste_percentage=30.0,
    )

    try:
        vsm.process_efficiency = 0.5  # type: ignore[misc]
        raise AssertionError("Should not allow mutation of frozen dataclass")
    except AttributeError:
        pass  # Expected
