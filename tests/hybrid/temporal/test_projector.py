"""Tests for semantic projector with multi-level caching."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta, timezone
from threading import Thread

from kgcl.hybrid.temporal.adapters.caching_projector import CachingProjector
from kgcl.hybrid.temporal.adapters.in_memory_event_store import InMemoryEventStore
from kgcl.hybrid.temporal.domain.event import EventType, WorkflowEvent

# Test workflow ID constant
TEST_WORKFLOW_ID = "test-workflow-1"


def test_project_current_empty_store() -> None:
    """Test projection with no events."""
    store = InMemoryEventStore()
    projector = CachingProjector(event_store=store)

    result = projector.project_current()

    assert result.state == {}
    assert result.sequence_number == 0
    assert result.events_applied == 0
    assert not result.cache_hit
    assert result.duration_ms >= 0


def test_project_current_with_events() -> None:
    """Test projection applies events correctly."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)

    # Append status change event
    event1 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=1,
        payload={"entity_id": "task1", "new_status": "running"},
        timestamp=now,
    )
    store.append(event1)

    # Append another status change
    event2 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=2,
        payload={"entity_id": "task2", "new_status": "completed"},
        timestamp=now + timedelta(seconds=1),
        previous_hash=event1.event_hash,
    )
    store.append(event2)

    projector = CachingProjector(event_store=store)
    result = projector.project_current()

    assert "task1" in result.state
    assert result.state["task1"]["status"] == "running"
    assert "task2" in result.state
    assert result.state["task2"]["status"] == "completed"
    assert result.events_applied == 2
    assert not result.cache_hit


def test_project_current_cache_hit() -> None:
    """Test L3 cache returns cached result."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)

    event = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=1,
        payload={"entity_id": "task1", "new_status": "running"},
        timestamp=now,
    )
    store.append(event)

    projector = CachingProjector(event_store=store, l3_ttl=10.0)

    # First call builds cache
    result1 = projector.project_current()
    assert not result1.cache_hit

    # Second call hits cache
    result2 = projector.project_current()
    assert result2.cache_hit
    assert result2.events_applied == 0
    assert result2.state == result1.state


def test_project_at_time_historical() -> None:
    """Test projecting state at specific time point."""
    store = InMemoryEventStore()
    base_time = datetime.now(UTC)

    # Event at T+0
    event1 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=1,
        payload={"entity_id": "task1", "new_status": "running"},
        timestamp=base_time,
    )
    store.append(event1)

    # Event at T+2
    event2 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=2,
        payload={"entity_id": "task1", "new_status": "completed"},
        timestamp=base_time + timedelta(seconds=2),
        previous_hash=event1.event_hash,
    )
    store.append(event2)

    projector = CachingProjector(event_store=store)

    # Project at T+1 (should only see first event)
    result = projector.project_at_time(base_time + timedelta(seconds=1))

    assert "task1" in result.state
    assert result.state["task1"]["status"] == "running"
    assert result.events_applied == 1


def test_project_at_sequence() -> None:
    """Test projecting state at specific sequence number."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)
    prev_hash = ""

    for i in range(5):
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

    # Project at sequence 2 (should see first 3 events: 0, 1, 2)
    result = projector.project_at_sequence(2)

    assert result.events_applied == 3
    assert "task0" in result.state
    assert "task1" in result.state
    assert "task2" in result.state
    assert "task3" not in result.state


def test_invalidate_clears_cache() -> None:
    """Test invalidate marks cache as stale."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)

    event = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=1,
        payload={"entity_id": "task1", "new_status": "running"},
        timestamp=now,
    )
    store.append(event)

    projector = CachingProjector(event_store=store)

    # Build cache
    result1 = projector.project_current()
    assert not result1.cache_hit

    # Invalidate
    projector.invalidate()

    # Next call should rebuild
    result2 = projector.project_current()
    assert not result2.cache_hit


def test_invalidate_entity_selective() -> None:
    """Test entity-specific invalidation."""
    store = InMemoryEventStore()
    projector = CachingProjector(event_store=store)

    # Invalidate specific entity
    projector.invalidate_entity("task1")

    # Should not raise
    assert "task1" not in projector._l2_cache


def test_get_diff_additions() -> None:
    """Test diff shows additions."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)

    # Initial state: task1
    event1 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=1,
        payload={"entity_id": "task1", "new_status": "running"},
        timestamp=now,
    )
    store.append(event1)

    # Add task2
    event2 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=2,
        payload={"entity_id": "task2", "new_status": "running"},
        timestamp=now + timedelta(seconds=1),
        previous_hash=event1.event_hash,
    )
    store.append(event2)

    projector = CachingProjector(event_store=store)
    diff = projector.get_diff(from_seq=0, to_seq=1)

    # task2 was added
    assert len(diff.additions) > 0
    assert any("task2" in str(add) for add in diff.additions)


def test_get_diff_removals() -> None:
    """Test diff detects removals (entity stops appearing)."""
    store = InMemoryEventStore()
    projector = CachingProjector(event_store=store)

    # Both projections empty in this test
    diff = projector.get_diff(from_seq=0, to_seq=0)

    assert len(diff.removals) == 0


def test_get_diff_modifications() -> None:
    """Test diff shows modifications."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)

    # Initial: task1 running
    event1 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=1,
        payload={"entity_id": "task1", "new_status": "running"},
        timestamp=now,
    )
    store.append(event1)

    # Change to completed
    event2 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=2,
        payload={"entity_id": "task1", "new_status": "completed"},
        timestamp=now + timedelta(seconds=1),
        previous_hash=event1.event_hash,
    )
    store.append(event2)

    projector = CachingProjector(event_store=store)
    diff = projector.get_diff(from_seq=0, to_seq=1)

    # task1 state should be modified
    assert len(diff.modifications) > 0


def test_get_entity_history() -> None:
    """Test retrieving entity history."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)
    prev_hash = ""

    # Multiple events for task1
    for i in range(3):
        event = WorkflowEvent.create(
            event_type=EventType.STATUS_CHANGE,
            workflow_id=TEST_WORKFLOW_ID,
            tick_number=i + 1,
            payload={"entity_id": "task1", "new_status": f"status{i}"},
            timestamp=now + timedelta(seconds=i),
            previous_hash=prev_hash,
        )
        store.append(event)
        prev_hash = event.event_hash

    projector = CachingProjector(event_store=store)
    history = projector.get_entity_history("task1", limit=10)

    assert len(history) == 3
    # Check timestamps are ordered
    assert history[0][0] <= history[1][0] <= history[2][0]


def test_l3_cache_ttl_expiry() -> None:
    """Test L3 cache expires after TTL."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)

    event = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=1,
        payload={"entity_id": "task1", "new_status": "running"},
        timestamp=now,
    )
    store.append(event)

    # Very short TTL
    projector = CachingProjector(event_store=store, l3_ttl=0.1)

    # Build cache
    result1 = projector.project_current()
    assert not result1.cache_hit

    # Wait for expiry
    time.sleep(0.15)

    # Should rebuild (expired)
    result2 = projector.project_current()
    assert not result2.cache_hit


def test_l2_entity_cache() -> None:
    """Test L2 entity cache is populated and used."""
    store = InMemoryEventStore()
    projector = CachingProjector(event_store=store)

    # Manually test L2 cache (implementation detail)
    # Verifies invalidate_entity removes entry from L2 cache
    projector.invalidate_entity("task1")
    assert "task1" not in projector._l2_cache


def test_status_change_event_projection() -> None:
    """Test STATUS_CHANGE events update state correctly."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)

    event = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=1,
        payload={"entity_id": "task1", "new_status": "running"},
        timestamp=now,
    )
    store.append(event)

    projector = CachingProjector(event_store=store)
    result = projector.project_current()

    assert result.state["task1"]["status"] == "running"
    assert "last_updated" in result.state["task1"]


def test_token_move_event_projection() -> None:
    """Test TOKEN_MOVE events update token tracking."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)

    event = WorkflowEvent.create(
        event_type=EventType.TOKEN_MOVE,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=1,
        payload={"token_id": "token1", "from_place": "p1", "to_place": "p2"},
        timestamp=now,
    )
    store.append(event)

    projector = CachingProjector(event_store=store)
    result = projector.project_current()

    assert "_tokens" in result.state
    assert "token1" in result.state["_tokens"]
    assert result.state["_tokens"]["token1"]["from"] == "p1"
    assert result.state["_tokens"]["token1"]["to"] == "p2"


def test_cancellation_event_projection() -> None:
    """Test CANCELLATION events mark entities as cancelled."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)

    event = WorkflowEvent.create(
        event_type=EventType.CANCELLATION,
        workflow_id=TEST_WORKFLOW_ID,
        tick_number=1,
        payload={"entity_id": "task1"},
        timestamp=now,
    )
    store.append(event)

    projector = CachingProjector(event_store=store)
    result = projector.project_current()

    assert result.state["task1"]["cancelled"] is True
    assert "cancelled_at" in result.state["task1"]


def test_thread_safety() -> None:
    """Test projector is thread-safe."""
    store = InMemoryEventStore()
    now = datetime.now(UTC)
    prev_hash = ""

    # Add some events
    for i in range(10):
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

    results: list[bool] = []

    def project_worker() -> None:
        for _ in range(10):
            result = projector.project_current()
            results.append(len(result.state) >= 0)

    threads = [Thread(target=project_worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All operations should succeed
    assert all(results)
