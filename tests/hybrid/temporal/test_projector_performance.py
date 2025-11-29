"""Performance benchmarks for semantic projector."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta, timezone

from kgcl.hybrid.temporal.adapters.caching_projector import CachingProjector
from kgcl.hybrid.temporal.adapters.in_memory_event_store import InMemoryEventStore
from kgcl.hybrid.temporal.domain.event import EventType, WorkflowEvent

TEST_WORKFLOW_ID = "perf-test-workflow"


def test_project_current_cache_hit_under_1ms() -> None:
    """Verify cache hits are under 1ms."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)
    prev_hash = ""

    # Add 100 events
    for i in range(100):
        event = WorkflowEvent.create(
            event_type=EventType.STATUS_CHANGE,
            workflow_id=TEST_WORKFLOW_ID,
            tick_number=i + 1,
            payload={"entity_id": f"task{i}", "new_status": "running"},
            timestamp=now + timedelta(seconds=i),
            previous_hash=prev_hash,
        )
        store.append(event)
        prev_hash = event.event_hash

    projector = CachingProjector(event_store=store)

    # Prime cache
    projector.project_current()

    # Measure cache hit
    start = time.perf_counter()
    result = projector.project_current()
    duration_ms = (time.perf_counter() - start) * 1000

    assert result.cache_hit
    assert duration_ms < 1.0, f"Cache hit took {duration_ms:.2f}ms (target: <1ms)"


def test_project_current_1k_events_under_50ms() -> None:
    """Verify 1K event projection is under 50ms."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)
    prev_hash = ""

    # Add 1000 events
    for i in range(1000):
        event = WorkflowEvent.create(
            event_type=EventType.STATUS_CHANGE,
            workflow_id=TEST_WORKFLOW_ID,
            tick_number=i + 1,
            payload={"entity_id": f"task{i % 100}", "new_status": f"status{i}"},
            timestamp=now + timedelta(seconds=i),
            previous_hash=prev_hash,
        )
        store.append(event)
        prev_hash = event.event_hash

    projector = CachingProjector(event_store=store)

    start = time.perf_counter()
    result = projector.project_current()
    duration_ms = (time.perf_counter() - start) * 1000

    assert not result.cache_hit
    assert result.events_applied == 1000
    assert duration_ms < 50.0, f"1K events took {duration_ms:.2f}ms (target: <50ms)"


def test_project_at_time_1k_events_under_100ms() -> None:
    """Verify historical projection of 1K events is under 100ms."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)
    prev_hash = ""

    # Add 1000 events
    for i in range(1000):
        event = WorkflowEvent.create(
            event_type=EventType.STATUS_CHANGE,
            workflow_id=TEST_WORKFLOW_ID,
            tick_number=i + 1,
            payload={"entity_id": f"task{i % 100}", "new_status": f"status{i}"},
            timestamp=now + timedelta(seconds=i),
            previous_hash=prev_hash,
        )
        store.append(event)
        prev_hash = event.event_hash

    projector = CachingProjector(event_store=store)

    # Project at halfway point
    target_time = now + timedelta(seconds=500)

    start = time.perf_counter()
    result = projector.project_at_time(target_time)
    duration_ms = (time.perf_counter() - start) * 1000

    assert result.events_applied <= 501  # Should stop at 500
    assert duration_ms < 100.0, f"Historical projection took {duration_ms:.2f}ms (target: <100ms)"


def test_invalidate_under_0_1ms() -> None:
    """Verify invalidate is under 0.1ms."""
    store = InMemoryEventStore()
    projector = CachingProjector(event_store=store)

    # Prime cache
    projector.project_current()

    start = time.perf_counter()
    projector.invalidate()
    duration_ms = (time.perf_counter() - start) * 1000

    assert duration_ms < 0.1, f"Invalidate took {duration_ms:.2f}ms (target: <0.1ms)"


def test_get_diff_under_10ms() -> None:
    """Verify get_diff is under 10ms."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)
    prev_hash = ""

    # Add 100 events
    for i in range(100):
        event = WorkflowEvent.create(
            event_type=EventType.STATUS_CHANGE,
            workflow_id=TEST_WORKFLOW_ID,
            tick_number=i + 1,
            payload={"entity_id": f"task{i % 20}", "new_status": f"status{i}"},
            timestamp=now + timedelta(seconds=i),
            previous_hash=prev_hash,
        )
        store.append(event)
        prev_hash = event.event_hash

    projector = CachingProjector(event_store=store)

    start = time.perf_counter()
    diff = projector.get_diff(from_seq=0, to_seq=50)
    duration_ms = (time.perf_counter() - start) * 1000

    assert len(diff.additions) > 0 or len(diff.modifications) > 0
    assert duration_ms < 10.0, f"get_diff took {duration_ms:.2f}ms (target: <10ms)"
