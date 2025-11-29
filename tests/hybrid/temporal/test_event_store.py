"""Tests for event store port and in-memory implementation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from kgcl.hybrid.temporal.adapters.in_memory_event_store import InMemoryEventStore
from kgcl.hybrid.temporal.domain.event import EventType, WorkflowEvent

if TYPE_CHECKING:
    from kgcl.hybrid.temporal.ports.event_store_port import EventStore


@pytest.fixture
def store() -> EventStore:
    """Create in-memory event store."""
    return InMemoryEventStore(max_hot_events=10)


@pytest.fixture
def base_time() -> datetime:
    """Base timestamp for tests."""
    return datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)


def create_event(
    event_id: str,
    workflow_id: str,
    event_type: EventType,
    timestamp: datetime,
    tick_number: int = 0,
    parent_id: str | None = None,
    previous_hash: str = "",
) -> WorkflowEvent:
    """Create test event.

    Parameters
    ----------
    event_id : str
        Event identifier
    workflow_id : str
        Workflow identifier
    event_type : EventType
        Type of event
    timestamp : datetime
        Event timestamp
    tick_number : int
        Tick number
    parent_id : str | None
        Parent event ID for causal chain
    previous_hash : str
        Previous event hash for verification

    Returns
    -------
    WorkflowEvent
        Test event instance
    """
    return WorkflowEvent(
        event_id=event_id,
        workflow_id=workflow_id,
        event_type=event_type,
        timestamp=timestamp,
        tick_number=tick_number,
        payload={"data": "test", "parent": parent_id} if parent_id else {"data": "test"},
        caused_by=(parent_id,) if parent_id else (),
        vector_clock=(("node1", 1),),
        previous_hash=previous_hash,
    )


def test_append_single_event(store: EventStore, base_time: datetime) -> None:
    """Test appending single event."""
    event = create_event("e1", "wf1", EventType.TICK_START, base_time)
    result = store.append(event)

    assert result.success
    assert result.event_ids == ("e1",)
    assert result.sequence_numbers == (1,)
    assert result.error is None


def test_append_batch_atomic(store: EventStore, base_time: datetime) -> None:
    """Test appending multiple events atomically."""
    events = [
        create_event("e1", "wf1", EventType.TICK_START, base_time),
        create_event("e2", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=1)),
        create_event("e3", "wf1", EventType.TICK_END, base_time + timedelta(seconds=2)),
    ]

    result = store.append_batch(events)

    assert result.success
    assert result.event_ids == ("e1", "e2", "e3")
    assert result.sequence_numbers == (1, 2, 3)
    assert store.count() == 3


def test_get_by_id(store: EventStore, base_time: datetime) -> None:
    """Test retrieving event by ID."""
    event = create_event("e1", "wf1", EventType.TICK_START, base_time)
    store.append(event)

    retrieved = store.get_by_id("e1")
    assert retrieved is not None
    assert retrieved.event_id == "e1"
    assert retrieved.workflow_id == "wf1"

    assert store.get_by_id("nonexistent") is None


def test_get_by_sequence(store: EventStore, base_time: datetime) -> None:
    """Test retrieving event by sequence number."""
    events = [
        create_event("e1", "wf1", EventType.TICK_START, base_time),
        create_event("e2", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=1)),
    ]
    store.append_batch(events)

    event1 = store.get_by_sequence(1)
    assert event1 is not None
    assert event1.event_id == "e1"

    event2 = store.get_by_sequence(2)
    assert event2 is not None
    assert event2.event_id == "e2"

    assert store.get_by_sequence(0) is None
    assert store.get_by_sequence(999) is None


def test_query_range_by_time(store: EventStore, base_time: datetime) -> None:
    """Test querying events by time range."""
    events = [
        create_event("e1", "wf1", EventType.TICK_START, base_time),
        create_event("e2", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=5)),
        create_event("e3", "wf1", EventType.TICK_END, base_time + timedelta(seconds=10)),
    ]
    store.append_batch(events)

    # Query middle event
    result = store.query_range(start=base_time + timedelta(seconds=3), end=base_time + timedelta(seconds=7))

    assert result.total_count == 1
    assert len(result.events) == 1
    assert result.events[0].event_id == "e2"
    assert not result.has_more


def test_query_range_by_workflow(store: EventStore, base_time: datetime) -> None:
    """Test querying events by workflow ID."""
    events = [
        create_event("e1", "wf1", EventType.TICK_START, base_time),
        create_event("e2", "wf2", EventType.TICK_START, base_time),
        create_event("e3", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=1)),
    ]
    store.append_batch(events)

    result = store.query_range(workflow_id="wf1")

    assert result.total_count == 2
    assert len(result.events) == 2
    assert {e.event_id for e in result.events} == {"e1", "e3"}


def test_query_range_by_event_type(store: EventStore, base_time: datetime) -> None:
    """Test querying events by event type."""
    events = [
        create_event("e1", "wf1", EventType.TICK_START, base_time),
        create_event("e2", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=1)),
        create_event("e3", "wf1", EventType.TICK_END, base_time + timedelta(seconds=2)),
    ]
    store.append_batch(events)

    result = store.query_range(event_types=[EventType.STATUS_CHANGE, EventType.TICK_END])

    assert result.total_count == 2
    assert {e.event_id for e in result.events} == {"e2", "e3"}


def test_replay_from_sequence(store: EventStore, base_time: datetime) -> None:
    """Test replaying events from sequence number."""
    events = [
        create_event("e1", "wf1", EventType.TICK_START, base_time),
        create_event("e2", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=1)),
        create_event("e3", "wf1", EventType.TICK_END, base_time + timedelta(seconds=2)),
    ]
    store.append_batch(events)

    replayed = list(store.replay(from_sequence=1))

    assert len(replayed) == 2
    assert replayed[0].event_id == "e2"
    assert replayed[1].event_id == "e3"


def test_replay_filtered_by_workflow(store: EventStore, base_time: datetime) -> None:
    """Test replaying events filtered by workflow."""
    events = [
        create_event("e1", "wf1", EventType.TICK_START, base_time),
        create_event("e2", "wf2", EventType.TICK_START, base_time),
        create_event("e3", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=1)),
    ]
    store.append_batch(events)

    replayed = list(store.replay(workflow_id="wf1"))

    assert len(replayed) == 2
    assert {e.event_id for e in replayed} == {"e1", "e3"}


def test_get_causal_chain_simple(store: EventStore, base_time: datetime) -> None:
    """Test getting causal chain for simple parent-child relationship."""
    e1 = create_event("e1", "wf1", EventType.TICK_START, base_time)
    store.append(e1)

    e1_hash = e1.event_hash
    e2 = create_event(
        "e2", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=1), parent_id="e1", previous_hash=e1_hash
    )
    store.append(e2)

    chain = store.get_causal_chain("e2")

    assert len(chain) == 2
    assert chain[0].event_id == "e1"
    assert chain[1].event_id == "e2"


def test_get_causal_chain_deep(store: EventStore, base_time: datetime) -> None:
    """Test getting deep causal chain."""
    events: list[WorkflowEvent] = []
    prev_hash = ""

    for i in range(5):
        event = create_event(
            f"e{i + 1}",
            "wf1",
            EventType.STATUS_CHANGE,
            base_time + timedelta(seconds=i),
            parent_id=f"e{i}" if i > 0 else None,
            previous_hash=prev_hash,
        )
        events.append(event)
        store.append(event)
        prev_hash = event.event_hash

    chain = store.get_causal_chain("e5")

    assert len(chain) == 5
    assert [e.event_id for e in chain] == ["e1", "e2", "e3", "e4", "e5"]


def test_get_causal_chain_max_depth(store: EventStore, base_time: datetime) -> None:
    """Test causal chain respects max_depth limit."""
    events: list[WorkflowEvent] = []
    prev_hash = ""

    for i in range(10):
        event = create_event(
            f"e{i + 1}",
            "wf1",
            EventType.STATUS_CHANGE,
            base_time + timedelta(seconds=i),
            parent_id=f"e{i}" if i > 0 else None,
            previous_hash=prev_hash,
        )
        events.append(event)
        store.append(event)
        prev_hash = event.event_hash

    chain = store.get_causal_chain("e10", max_depth=5)

    assert len(chain) == 5
    assert chain[-1].event_id == "e10"


def test_verify_chain_integrity_valid(store: EventStore, base_time: datetime) -> None:
    """Test verifying valid hash chain."""
    e1 = create_event("e1", "wf1", EventType.TICK_START, base_time)
    store.append(e1)

    e1_hash = e1.event_hash
    e2 = create_event("e2", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=1), previous_hash=e1_hash)
    store.append(e2)

    valid, error = store.verify_chain_integrity("wf1")

    assert valid
    assert error == ""


def test_verify_chain_integrity_detects_tampering(store: EventStore, base_time: datetime) -> None:
    """Test detecting tampered hash chain."""
    e1 = create_event("e1", "wf1", EventType.TICK_START, base_time)
    store.append(e1)

    # Append event with invalid previous_hash
    e2 = create_event(
        "e2", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=1), previous_hash="invalid_hash"
    )
    store.append(e2)

    valid, error = store.verify_chain_integrity("wf1")

    assert not valid
    assert "Hash chain broken" in error
    assert "e2" in error


def test_hot_buffer_overflow(store: EventStore, base_time: datetime) -> None:
    """Test hot buffer overflow (ring buffer behavior)."""
    # Store has max_hot_events=10
    events = [
        create_event(f"e{i}", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=i)) for i in range(15)
    ]

    store.append_batch(events)

    # All events should still be retrievable
    assert store.count() == 15
    for i in range(15):
        event = store.get_by_id(f"e{i}")
        assert event is not None
        assert event.event_id == f"e{i}"


def test_thread_safety(store: EventStore, base_time: datetime) -> None:
    """Test concurrent appends are thread-safe."""
    num_threads = 10
    events_per_thread = 20

    def append_events(thread_id: int) -> int:
        for i in range(events_per_thread):
            event = create_event(
                f"t{thread_id}_e{i}", f"wf{thread_id}", EventType.STATUS_CHANGE, base_time + timedelta(seconds=i)
            )
            store.append(event)
        return thread_id

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(append_events, i) for i in range(num_threads)]
        for future in as_completed(futures):
            future.result()

    # Verify all events were stored
    assert store.count() == num_threads * events_per_thread

    # Verify sequence numbers are unique and sequential
    assert store.get_latest_sequence() == num_threads * events_per_thread


def test_count_all_and_filtered(store: EventStore, base_time: datetime) -> None:
    """Test counting all events and filtered by workflow."""
    events = [
        create_event("e1", "wf1", EventType.TICK_START, base_time),
        create_event("e2", "wf2", EventType.TICK_START, base_time),
        create_event("e3", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=1)),
    ]
    store.append_batch(events)

    assert store.count() == 3
    assert store.count(workflow_id="wf1") == 2
    assert store.count(workflow_id="wf2") == 1
    assert store.count(workflow_id="wf3") == 0


def test_query_range_pagination(store: EventStore, base_time: datetime) -> None:
    """Test query range pagination."""
    events = [
        create_event(f"e{i}", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=i)) for i in range(25)
    ]
    store.append_batch(events)

    # First page
    page1 = store.query_range(workflow_id="wf1", limit=10, offset=0)
    assert len(page1.events) == 10
    assert page1.total_count == 25
    assert page1.has_more

    # Second page
    page2 = store.query_range(workflow_id="wf1", limit=10, offset=10)
    assert len(page2.events) == 10
    assert page2.total_count == 25
    assert page2.has_more

    # Last page
    page3 = store.query_range(workflow_id="wf1", limit=10, offset=20)
    assert len(page3.events) == 5
    assert page3.total_count == 25
    assert not page3.has_more


def test_replay_with_to_sequence(store: EventStore, base_time: datetime) -> None:
    """Test replaying events with to_sequence limit."""
    events = [
        create_event(f"e{i}", "wf1", EventType.STATUS_CHANGE, base_time + timedelta(seconds=i)) for i in range(10)
    ]
    store.append_batch(events)

    replayed = list(store.replay(from_sequence=2, to_sequence=5))

    assert len(replayed) == 3
    assert [e.event_id for e in replayed] == ["e2", "e3", "e4"]


def test_empty_store_operations(store: EventStore) -> None:
    """Test operations on empty store."""
    assert store.get_latest_sequence() == 0
    assert store.count() == 0
    assert store.get_by_id("e1") is None
    assert store.get_by_sequence(1) is None

    result = store.query_range()
    assert result.total_count == 0
    assert len(result.events) == 0
    assert not result.has_more

    replayed = list(store.replay())
    assert len(replayed) == 0

    chain = store.get_causal_chain("e1")
    assert len(chain) == 0

    valid, error = store.verify_chain_integrity("wf1")
    assert valid
    assert error == ""


def test_append_empty_batch(store: EventStore) -> None:
    """Test appending empty batch."""
    result = store.append_batch([])

    assert result.success
    assert result.event_ids == ()
    assert result.sequence_numbers == ()
    assert store.count() == 0
