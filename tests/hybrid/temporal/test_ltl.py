"""Tests for LTL temporal reasoning."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from kgcl.hybrid.temporal.adapters.in_memory_event_store import InMemoryEventStore
from kgcl.hybrid.temporal.adapters.ltl_evaluator import LTLEvaluator
from kgcl.hybrid.temporal.domain.event import EventType, WorkflowEvent
from kgcl.hybrid.temporal.domain.ltl_formula import LTLFormula, LTLOperator
from kgcl.hybrid.temporal.ports.temporal_reasoner_port import TemporalProperty


@pytest.fixture
def event_store() -> InMemoryEventStore:
    """Create empty event store."""
    return InMemoryEventStore()


@pytest.fixture
def evaluator(event_store: InMemoryEventStore) -> LTLEvaluator:
    """Create LTL evaluator."""
    return LTLEvaluator(event_store=event_store)


@pytest.fixture
def base_time() -> datetime:
    """Base timestamp for events."""
    return datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)


def create_event(
    event_id: str,
    workflow_id: str,
    event_type: EventType,
    timestamp: datetime,
    tick_number: int = 0,
    payload: dict[str, object] | None = None,
    previous_hash: str = "",
) -> WorkflowEvent:
    """Helper to create workflow event."""
    return WorkflowEvent(
        event_id=event_id,
        event_type=event_type,
        workflow_id=workflow_id,
        timestamp=timestamp,
        tick_number=tick_number,
        payload=payload or {},
        caused_by=(),
        vector_clock=(("node1", 1),),
        previous_hash=previous_hash,
    )


def test_evaluate_always_holds(event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime) -> None:
    """Test ALWAYS operator when condition holds for all events."""
    workflow_id = "wf-1"

    for i in range(5):
        event = create_event(
            event_id=f"evt-{i}",
            workflow_id=workflow_id,
            event_type=EventType.STATUS_CHANGE,
            timestamp=base_time + timedelta(seconds=i),
            tick_number=i,
            payload={"valid": True},
        )
        event_store.append(event)

    result = evaluator.check_always(condition=lambda e: e.payload.get("valid") is True, workflow_id=workflow_id)

    assert result.holds is True
    assert "all events" in result.explanation.lower()


def test_evaluate_always_violated(
    event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime
) -> None:
    """Test ALWAYS operator with violation."""
    workflow_id = "wf-1"

    event_store.append(create_event("evt-0", workflow_id, EventType.STATUS_CHANGE, base_time, 0, {"valid": True}))
    event_store.append(
        create_event(
            "evt-1", workflow_id, EventType.STATUS_CHANGE, base_time + timedelta(seconds=1), 1, {"valid": True}
        )
    )
    violation_event = create_event(
        "evt-2", workflow_id, EventType.STATUS_CHANGE, base_time + timedelta(seconds=2), 2, {"valid": False}
    )
    event_store.append(violation_event)

    result = evaluator.check_always(condition=lambda e: e.payload.get("valid") is True, workflow_id=workflow_id)

    assert result.holds is False
    assert result.violating_event_id == "evt-2"
    assert result.violated_at == violation_event.timestamp


def test_evaluate_eventually_found(
    event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime
) -> None:
    """Test EVENTUALLY operator when condition is satisfied."""
    workflow_id = "wf-1"

    event_store.append(create_event("evt-0", workflow_id, EventType.STATUS_CHANGE, base_time, 0, {}))
    event_store.append(
        create_event("evt-1", workflow_id, EventType.STATUS_CHANGE, base_time + timedelta(seconds=1), 1, {})
    )
    event_store.append(
        create_event("evt-2", workflow_id, EventType.TICK_END, base_time + timedelta(seconds=2), 2, {"complete": True})
    )

    result = evaluator.check_eventually(condition=lambda e: e.event_type == EventType.TICK_END, workflow_id=workflow_id)

    assert result.holds is True
    assert "evt-2" in result.explanation


def test_evaluate_eventually_not_found(
    event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime
) -> None:
    """Test EVENTUALLY operator when condition never satisfied."""
    workflow_id = "wf-1"

    for i in range(3):
        event_store.append(
            create_event(f"evt-{i}", workflow_id, EventType.STATUS_CHANGE, base_time + timedelta(seconds=i), i, {})
        )

    result = evaluator.check_eventually(condition=lambda e: e.event_type == EventType.TICK_END, workflow_id=workflow_id)

    assert result.holds is False
    assert "never satisfied" in result.explanation.lower()


def test_evaluate_until_satisfied(
    event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime
) -> None:
    """Test UNTIL operator when phi holds until psi becomes true."""
    workflow_id = "wf-1"

    event_store.append(create_event("evt-0", workflow_id, EventType.STATUS_CHANGE, base_time, 0, {"status": "active"}))
    event_store.append(
        create_event(
            "evt-1", workflow_id, EventType.STATUS_CHANGE, base_time + timedelta(seconds=1), 1, {"status": "active"}
        )
    )
    event_store.append(
        create_event("evt-2", workflow_id, EventType.TICK_END, base_time + timedelta(seconds=2), 2, {"status": "done"})
    )

    result = evaluator.check_until(
        condition_phi=lambda e: e.payload.get("status") == "active",
        condition_psi=lambda e: e.event_type == EventType.TICK_END,
        workflow_id=workflow_id,
    )

    assert result.holds is True
    assert "until condition reached" in result.explanation.lower()


def test_evaluate_until_phi_violated_early(
    event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime
) -> None:
    """Test UNTIL operator when phi is violated before psi."""
    workflow_id = "wf-1"

    event_store.append(create_event("evt-0", workflow_id, EventType.STATUS_CHANGE, base_time, 0, {"status": "active"}))
    violation_event = create_event(
        "evt-1", workflow_id, EventType.CANCELLATION, base_time + timedelta(seconds=1), 1, {"status": "error"}
    )
    event_store.append(violation_event)

    result = evaluator.check_until(
        condition_phi=lambda e: e.payload.get("status") == "active",
        condition_psi=lambda e: e.event_type == EventType.TICK_END,
        workflow_id=workflow_id,
    )

    assert result.holds is False
    assert result.violating_event_id == "evt-1"
    assert "phi violated" in result.explanation.lower()


def test_evaluate_until_psi_never_true(
    event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime
) -> None:
    """Test UNTIL operator when psi never becomes true."""
    workflow_id = "wf-1"

    for i in range(3):
        event_store.append(
            create_event(
                f"evt-{i}",
                workflow_id,
                EventType.STATUS_CHANGE,
                base_time + timedelta(seconds=i),
                i,
                {"status": "active"},
            )
        )

    result = evaluator.check_until(
        condition_phi=lambda e: e.payload.get("status") == "active",
        condition_psi=lambda e: e.event_type == EventType.TICK_END,
        workflow_id=workflow_id,
    )

    assert result.holds is False
    assert "psi never became true" in result.explanation.lower()


def test_evaluate_next_holds(event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime) -> None:
    """Test NEXT operator when condition holds in next state."""
    workflow_id = "wf-1"

    event_store.append(create_event("evt-0", workflow_id, EventType.TICK_START, base_time, 0, {}))
    event_store.append(create_event("evt-1", workflow_id, EventType.TICK_END, base_time + timedelta(seconds=1), 1, {}))

    # Sequence numbers are 1-indexed, so after sequence 1 is sequence 2
    result = evaluator.check_next(
        condition=lambda e: e.event_type == EventType.TICK_END, after_sequence=1, workflow_id=workflow_id
    )

    assert result.holds is True


def test_evaluate_next_violated(event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime) -> None:
    """Test NEXT operator when condition doesn't hold in next state."""
    workflow_id = "wf-1"

    event_store.append(create_event("evt-0", workflow_id, EventType.TICK_START, base_time, 0, {}))
    next_event = create_event("evt-1", workflow_id, EventType.STATUS_CHANGE, base_time + timedelta(seconds=1), 1, {})
    event_store.append(next_event)

    # Sequence numbers are 1-indexed, so after sequence 1 is sequence 2
    result = evaluator.check_next(
        condition=lambda e: e.event_type == EventType.TICK_END, after_sequence=1, workflow_id=workflow_id
    )

    assert result.holds is False
    assert result.violating_event_id == "evt-1"
    assert result.violated_at == next_event.timestamp


def test_evaluate_next_no_event(event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime) -> None:
    """Test NEXT operator when no next event exists."""
    workflow_id = "wf-1"

    event_store.append(create_event("evt-0", workflow_id, EventType.TICK_START, base_time, 0, {}))

    # Sequence 1 exists, but sequence 2 doesn't
    result = evaluator.check_next(
        condition=lambda e: e.event_type == EventType.TICK_END, after_sequence=1, workflow_id=workflow_id
    )

    assert result.holds is False
    assert "no next event" in result.explanation.lower()


def test_check_precedes_satisfied(
    event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime
) -> None:
    """Test precedes check when A always comes before B."""
    workflow_id = "wf-1"

    event_store.append(create_event("evt-0", workflow_id, EventType.VALIDATION, base_time, 0, {}))
    event_store.append(
        create_event("evt-1", workflow_id, EventType.HOOK_EXECUTION, base_time + timedelta(seconds=1), 1, {})
    )
    event_store.append(
        create_event("evt-2", workflow_id, EventType.HOOK_EXECUTION, base_time + timedelta(seconds=2), 2, {})
    )

    result = evaluator.check_precedes(event_type_a="VALIDATION", event_type_b="HOOK_EXECUTION", workflow_id=workflow_id)

    assert result.holds is True
    assert "always precedes" in result.explanation.lower()


def test_check_precedes_violated(event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime) -> None:
    """Test precedes check when B occurs before A."""
    workflow_id = "wf-1"

    violation_event = create_event("evt-0", workflow_id, EventType.HOOK_EXECUTION, base_time, 0, {})
    event_store.append(violation_event)
    event_store.append(
        create_event("evt-1", workflow_id, EventType.VALIDATION, base_time + timedelta(seconds=1), 1, {})
    )

    result = evaluator.check_precedes(event_type_a="VALIDATION", event_type_b="HOOK_EXECUTION", workflow_id=workflow_id)

    assert result.holds is False
    assert result.violating_event_id == "evt-0"
    assert "occurred before" in result.explanation.lower()


def test_verify_property_with_timing(
    event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime
) -> None:
    """Test property verification includes timing information."""
    workflow_id = "wf-1"

    for i in range(10):
        event_store.append(
            create_event(
                f"evt-{i}", workflow_id, EventType.STATUS_CHANGE, base_time + timedelta(seconds=i), i, {"valid": True}
            )
        )

    def is_valid(e: WorkflowEvent) -> bool:
        return e.payload.get("valid") is True

    property = TemporalProperty(
        property_id="test-prop",
        name="Test Property",
        description="All events are valid",
        formula=LTLFormula(operator=LTLOperator.ALWAYS, inner=is_valid),
        workflow_id=workflow_id,
    )

    result = evaluator.verify_property(property)

    assert result.property == property
    assert result.result.holds is True
    assert result.checked_events == 10
    assert result.duration_ms >= 0


def test_verify_all_properties(event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime) -> None:
    """Test verifying multiple properties."""
    workflow_id = "wf-1"

    event_store.append(create_event("evt-0", workflow_id, EventType.TICK_START, base_time, 0, {"valid": True}))
    event_store.append(
        create_event("evt-1", workflow_id, EventType.TICK_END, base_time + timedelta(seconds=1), 1, {"valid": True})
    )

    def is_valid(e: WorkflowEvent) -> bool:
        return e.payload.get("valid") is True

    def is_tick_end(e: WorkflowEvent) -> bool:
        return e.event_type == EventType.TICK_END

    properties = [
        TemporalProperty(
            property_id="prop-1",
            name="Always Valid",
            description="All events have valid flag",
            formula=LTLFormula(operator=LTLOperator.ALWAYS, inner=is_valid),
            workflow_id=workflow_id,
        ),
        TemporalProperty(
            property_id="prop-2",
            name="Eventually Completes",
            description="Task eventually completes",
            formula=LTLFormula(operator=LTLOperator.EVENTUALLY, inner=is_tick_end),
            workflow_id=workflow_id,
        ),
    ]

    results = evaluator.verify_all(properties)

    assert len(results) == 2
    assert all(r.result.holds for r in results)
    assert all(r.checked_events == 2 for r in results)


def test_nested_formula_always_eventually(
    event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime
) -> None:
    """Test nested formula evaluation (ALWAYS with nested condition)."""
    workflow_id = "wf-1"

    for i in range(5):
        event_store.append(
            create_event(
                f"evt-{i}", workflow_id, EventType.STATUS_CHANGE, base_time + timedelta(seconds=i), i, {"count": i + 1}
            )
        )

    result = evaluator.check_always(
        condition=lambda e: isinstance(e.payload.get("count"), int) and e.payload["count"] > 0, workflow_id=workflow_id
    )

    assert result.holds is True


def test_empty_event_store(event_store: InMemoryEventStore, evaluator: LTLEvaluator) -> None:
    """Test evaluation on empty event store."""
    workflow_id = "wf-1"

    always_result = evaluator.check_always(condition=lambda e: True, workflow_id=workflow_id)
    assert always_result.holds is True

    eventually_result = evaluator.check_eventually(condition=lambda e: True, workflow_id=workflow_id)
    assert eventually_result.holds is False


def test_formula_unsupported_operator(event_store: InMemoryEventStore, evaluator: LTLEvaluator) -> None:
    """Test formula evaluation with no inner value."""

    # Create a formula with an actual operator but ensure it fails gracefully
    def dummy_check(_: WorkflowEvent) -> bool:
        return True

    formula = LTLFormula(operator=LTLOperator.ALWAYS, inner=dummy_check)
    # Manually set inner to None to test error handling
    object.__setattr__(formula, "inner", None)

    result = evaluator.evaluate(formula)

    assert result.holds is False
    assert "missing" in result.explanation.lower()


def test_check_precedes_with_event_name(
    event_store: InMemoryEventStore, evaluator: LTLEvaluator, base_time: datetime
) -> None:
    """Test check_precedes uses event_type.name properly."""
    workflow_id = "wf-1"

    event_store.append(create_event("evt-0", workflow_id, EventType.VALIDATION, base_time, 0, {}))
    event_store.append(
        create_event("evt-1", workflow_id, EventType.HOOK_EXECUTION, base_time + timedelta(seconds=1), 1, {})
    )

    result = evaluator.check_precedes(event_type_a="VALIDATION", event_type_b="HOOK_EXECUTION", workflow_id=workflow_id)

    assert result.holds is True
