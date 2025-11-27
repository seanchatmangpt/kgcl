"""Tests for RDF Event Store with 4D Ontology - Chicago School TDD.

Tests verify behavior of the PyOxigraph-based event store:
- Event append and replay via SPARQL
- 4D temporal vectors (sequence, timestamp, tick)
- Time-travel reconstruction
- Named graph snapshots
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest
from pyoxigraph import Store

from kgcl.daemon.event_store import (
    KGCL_VOCAB,
    STATE_GRAPH,
    STATE_GRAPH_URI,
    DomainEvent,
    EventType,
    RDFEventStore,
    TemporalVector,
    compute_state_hash,
)

if TYPE_CHECKING:
    from collections.abc import Generator


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def store() -> RDFEventStore:
    """Create in-memory RDF event store for testing."""
    return RDFEventStore()


@pytest.fixture
def sample_event() -> DomainEvent:
    """Create a sample triple-added event."""
    return DomainEvent(
        event_id="evt-001",
        event_type=EventType.TRIPLE_ADDED,
        timestamp=1700000000.0,
        sequence=0,  # Will be assigned by store
        payload={"s": "urn:task:1", "p": "urn:status", "o": "Complete"},
    )


@pytest.fixture
def populated_store(store: RDFEventStore) -> RDFEventStore:
    """Create store with 5 events for testing."""
    for i in range(5):
        event = DomainEvent(
            event_id=f"evt-{i:03d}",
            event_type=EventType.TRIPLE_ADDED,
            timestamp=1700000000.0 + i,
            sequence=0,
            payload={"s": f"urn:task:{i}", "p": "urn:status", "o": "Pending"},
        )
        store.append(event)
    return store


# =============================================================================
# EventType Tests
# =============================================================================


class TestEventType:
    """Tests for EventType enum."""

    def test_triple_added_value(self) -> None:
        """EventType.TRIPLE_ADDED has correct string value."""
        assert EventType.TRIPLE_ADDED.value == "triple.added"

    def test_triple_removed_value(self) -> None:
        """EventType.TRIPLE_REMOVED has correct string value."""
        assert EventType.TRIPLE_REMOVED.value == "triple.removed"

    def test_all_event_types_have_dot_notation(self) -> None:
        """All event types use dot notation for values."""
        for event_type in EventType:
            assert "." in event_type.value, f"{event_type.name} missing dot notation"


# =============================================================================
# DomainEvent Tests
# =============================================================================


class TestDomainEvent:
    """Tests for DomainEvent dataclass."""

    def test_event_is_frozen(self, sample_event: DomainEvent) -> None:
        """DomainEvent instances are immutable."""
        with pytest.raises(AttributeError):
            sample_event.event_id = "modified"  # type: ignore[misc]

    def test_event_fields_accessible(self, sample_event: DomainEvent) -> None:
        """All DomainEvent fields are accessible."""
        assert sample_event.event_id == "evt-001"
        assert sample_event.event_type == EventType.TRIPLE_ADDED
        assert sample_event.timestamp == 1700000000.0
        assert sample_event.sequence == 0
        assert sample_event.payload["s"] == "urn:task:1"

    def test_state_hash_defaults_to_none(self, sample_event: DomainEvent) -> None:
        """state_hash defaults to None when not provided."""
        assert sample_event.state_hash is None

    def test_event_with_state_hash(self) -> None:
        """DomainEvent can include state hash."""
        event = DomainEvent(
            event_id="evt-hash",
            event_type=EventType.TRIPLE_ADDED,
            timestamp=1700000000.0,
            sequence=1,
            payload={},
            state_hash="abc123",
        )
        assert event.state_hash == "abc123"


# =============================================================================
# TemporalVector Tests
# =============================================================================


class TestTemporalVector:
    """Tests for TemporalVector dataclass."""

    def test_temporal_vector_fields(self) -> None:
        """TemporalVector stores all temporal coordinates."""
        vec = TemporalVector(sequence=100, timestamp=1700000000.0, tick=50)
        assert vec.sequence == 100
        assert vec.timestamp == 1700000000.0
        assert vec.tick == 50

    def test_temporal_vector_is_frozen(self) -> None:
        """TemporalVector is immutable."""
        vec = TemporalVector(sequence=1, timestamp=1.0, tick=0)
        with pytest.raises(AttributeError):
            vec.sequence = 2  # type: ignore[misc]

    def test_tick_defaults_to_zero(self) -> None:
        """tick defaults to 0."""
        vec = TemporalVector(sequence=1, timestamp=1.0)
        assert vec.tick == 0


# =============================================================================
# RDFEventStore Initialization Tests
# =============================================================================


class TestEventStoreInit:
    """Tests for RDFEventStore initialization."""

    def test_new_store_has_sequence_zero(self, store: RDFEventStore) -> None:
        """New event store starts with sequence 0."""
        assert store.sequence == 0

    def test_new_store_has_tick_zero(self, store: RDFEventStore) -> None:
        """New event store starts with tick 0."""
        assert store.tick == 0

    def test_store_exposes_underlying_pyoxigraph(self, store: RDFEventStore) -> None:
        """Store exposes underlying PyOxigraph Store."""
        assert isinstance(store.store, Store)

    def test_custom_store_accepted(self) -> None:
        """Can initialize with existing PyOxigraph store."""
        custom_store = Store()
        rdf_store = RDFEventStore(store=custom_store)
        assert rdf_store.store is custom_store


# =============================================================================
# Event Append Tests
# =============================================================================


class TestEventAppend:
    """Tests for appending events to the store."""

    def test_append_returns_sequence_number(self, store: RDFEventStore, sample_event: DomainEvent) -> None:
        """Append returns the assigned sequence number."""
        seq = store.append(sample_event)
        assert seq == 1

    def test_append_increments_sequence(self, store: RDFEventStore, sample_event: DomainEvent) -> None:
        """Each append increments the sequence number."""
        seq1 = store.append(sample_event)

        event2 = DomainEvent(
            event_id="evt-002", event_type=EventType.TRIPLE_ADDED, timestamp=time.time(), sequence=0, payload={}
        )
        seq2 = store.append(event2)

        assert seq1 == 1
        assert seq2 == 2

    def test_append_updates_store_sequence(self, store: RDFEventStore, sample_event: DomainEvent) -> None:
        """Append updates the store's sequence property."""
        assert store.sequence == 0
        store.append(sample_event)
        assert store.sequence == 1

    def test_append_persists_event_as_rdf(self, store: RDFEventStore, sample_event: DomainEvent) -> None:
        """Appended event is stored as RDF and retrievable."""
        store.append(sample_event)
        retrieved = store.get_event("evt-001")

        assert retrieved is not None
        assert retrieved.event_id == "evt-001"
        assert retrieved.event_type == EventType.TRIPLE_ADDED

    def test_append_stores_triple_in_state_graph(self, store: RDFEventStore, sample_event: DomainEvent) -> None:
        """TRIPLE_ADDED event adds triple to state graph."""
        store.append(sample_event)

        # Query state graph for the triple
        query = f"""
        SELECT ?o WHERE {{
            GRAPH <{STATE_GRAPH_URI}> {{
                <urn:task:1> <urn:status> ?o .
            }}
        }}
        """
        results = list(store.store.query(query))
        assert len(results) == 1


# =============================================================================
# Event Replay Tests
# =============================================================================


class TestEventReplay:
    """Tests for replaying events from the store."""

    def test_replay_empty_store(self, store: RDFEventStore) -> None:
        """Replaying empty store yields no events."""
        events = list(store.replay())
        assert events == []

    def test_replay_returns_events_in_order(self, populated_store: RDFEventStore) -> None:
        """Replay returns events in sequence order."""
        events = list(populated_store.replay())

        assert len(events) == 5
        for i, event in enumerate(events):
            assert event.sequence == i + 1

    def test_replay_from_sequence(self, populated_store: RDFEventStore) -> None:
        """Replay from specific sequence excludes earlier events."""
        events = list(populated_store.replay(from_seq=3))

        assert len(events) == 2
        assert events[0].sequence == 4
        assert events[1].sequence == 5

    def test_replay_to_sequence(self, populated_store: RDFEventStore) -> None:
        """Replay to specific sequence excludes later events."""
        events = list(populated_store.replay(to_seq=3))

        assert len(events) == 3
        assert events[-1].sequence == 3

    def test_replay_range(self, populated_store: RDFEventStore) -> None:
        """Replay with from_seq and to_seq returns range."""
        events = list(populated_store.replay(from_seq=1, to_seq=4))

        assert len(events) == 3
        assert events[0].sequence == 2
        assert events[-1].sequence == 4

    def test_replay_filter_by_event_type(self, store: RDFEventStore) -> None:
        """Replay can filter by event types."""
        # Add mixed event types
        store.append(
            DomainEvent(
                event_id="evt-add",
                event_type=EventType.TRIPLE_ADDED,
                timestamp=time.time(),
                sequence=0,
                payload={"s": "urn:a", "p": "urn:b", "o": "c"},
            )
        )
        store.append(
            DomainEvent(
                event_id="evt-remove",
                event_type=EventType.TRIPLE_REMOVED,
                timestamp=time.time(),
                sequence=0,
                payload={"s": "urn:x", "p": "urn:y", "o": "z"},
            )
        )

        # Filter for only TRIPLE_ADDED
        events = list(store.replay(event_types=[EventType.TRIPLE_ADDED]))
        assert len(events) == 1
        assert events[0].event_type == EventType.TRIPLE_ADDED

    def test_replay_restores_payload(self, store: RDFEventStore, sample_event: DomainEvent) -> None:
        """Replay correctly restores triple payload."""
        store.append(sample_event)
        events = list(store.replay())

        assert events[0].payload["s"] == "urn:task:1"
        assert events[0].payload["p"] == "urn:status"
        assert events[0].payload["o"] == "Complete"


# =============================================================================
# Event Retrieval Tests
# =============================================================================


class TestEventRetrieval:
    """Tests for retrieving individual events."""

    def test_get_event_by_id(self, store: RDFEventStore, sample_event: DomainEvent) -> None:
        """Can retrieve event by its ID."""
        store.append(sample_event)
        event = store.get_event("evt-001")

        assert event is not None
        assert event.event_id == "evt-001"

    def test_get_nonexistent_event_returns_none(self, store: RDFEventStore) -> None:
        """Getting nonexistent event returns None."""
        assert store.get_event("nonexistent") is None

    def test_get_event_at_sequence(self, populated_store: RDFEventStore) -> None:
        """Can retrieve event by sequence number."""
        event = populated_store.get_event_at_sequence(3)

        assert event is not None
        assert event.sequence == 3

    def test_get_event_at_invalid_sequence(self, store: RDFEventStore) -> None:
        """Getting event at invalid sequence returns None."""
        assert store.get_event_at_sequence(999) is None


# =============================================================================
# Count and Time Query Tests
# =============================================================================


class TestCountAndTimeQueries:
    """Tests for count and time-based queries."""

    def test_count_events_empty(self, store: RDFEventStore) -> None:
        """Count is 0 for empty store."""
        assert store.count_events() == 0

    def test_count_events_all(self, populated_store: RDFEventStore) -> None:
        """Count returns total event count."""
        assert populated_store.count_events() == 5

    def test_count_events_range(self, populated_store: RDFEventStore) -> None:
        """Count events in sequence range."""
        count = populated_store.count_events(from_seq=1, to_seq=3)
        assert count == 2  # Sequences 2 and 3

    def test_count_events_by_type(self, store: RDFEventStore) -> None:
        """Count events filtered by type."""
        store.append(
            DomainEvent(
                event_id="evt-1",
                event_type=EventType.TRIPLE_ADDED,
                timestamp=time.time(),
                sequence=0,
                payload={"s": "urn:a", "p": "urn:b", "o": "c"},
            )
        )
        store.append(
            DomainEvent(
                event_id="evt-2",
                event_type=EventType.TRIPLE_REMOVED,
                timestamp=time.time(),
                sequence=0,
                payload={"s": "urn:x", "p": "urn:y", "o": "z"},
            )
        )

        count = store.count_events(event_type=EventType.TRIPLE_ADDED)
        assert count == 1

    def test_sequence_at_time(self, store: RDFEventStore) -> None:
        """Find sequence number at timestamp."""
        store.append(
            DomainEvent(
                event_id="evt-1",
                event_type=EventType.TRIPLE_ADDED,
                timestamp=1000.0,
                sequence=0,
                payload={"s": "urn:a", "p": "urn:b", "o": "c"},
            )
        )
        store.append(
            DomainEvent(
                event_id="evt-2",
                event_type=EventType.TRIPLE_ADDED,
                timestamp=2000.0,
                sequence=0,
                payload={"s": "urn:d", "p": "urn:e", "o": "f"},
            )
        )

        # Query at timestamp between events
        seq = store.sequence_at_time(1500.0)
        assert seq == 1

    def test_sequence_at_time_before_any_event(self, store: RDFEventStore, sample_event: DomainEvent) -> None:
        """Returns 0 if timestamp is before any events."""
        store.append(sample_event)
        seq = store.sequence_at_time(0.0)
        assert seq == 0


# =============================================================================
# Time-Travel / Reconstruction Tests
# =============================================================================


class TestTimeTravel:
    """Tests for time-travel reconstruction."""

    def test_reconstruct_at_empty(self, store: RDFEventStore) -> None:
        """Reconstructing at seq 0 returns empty store."""
        reconstructed = store.reconstruct_at(0)
        count = sum(1 for _ in reconstructed.quads_for_pattern(None, None, None, None))
        assert count == 0

    def test_reconstruct_at_sequence(self, store: RDFEventStore) -> None:
        """Reconstruct state at specific sequence."""
        # Add events
        store.append(
            DomainEvent(
                event_id="evt-1",
                event_type=EventType.TRIPLE_ADDED,
                timestamp=1.0,
                sequence=0,
                payload={"s": "urn:a", "p": "urn:b", "o": "c"},
            )
        )
        store.append(
            DomainEvent(
                event_id="evt-2",
                event_type=EventType.TRIPLE_ADDED,
                timestamp=2.0,
                sequence=0,
                payload={"s": "urn:d", "p": "urn:e", "o": "f"},
            )
        )
        store.append(
            DomainEvent(
                event_id="evt-3",
                event_type=EventType.TRIPLE_ADDED,
                timestamp=3.0,
                sequence=0,
                payload={"s": "urn:g", "p": "urn:h", "o": "i"},
            )
        )

        # Reconstruct at seq 2 (should have 2 triples)
        reconstructed = store.reconstruct_at(2)
        count = sum(1 for _ in reconstructed.quads_for_pattern(None, None, None, None))
        assert count == 2


# =============================================================================
# Snapshot Tests
# =============================================================================


class TestSnapshots:
    """Tests for snapshot creation."""

    def test_create_snapshot_returns_uri(self, store: RDFEventStore) -> None:
        """Creating snapshot returns snapshot graph URI."""
        snap_uri = store.create_snapshot(100)
        assert snap_uri.startswith("urn:kgcl:snapshot:")

    def test_snapshot_records_event(self, store: RDFEventStore) -> None:
        """Snapshot creation records an event."""
        initial_count = store.count_events()
        store.create_snapshot(100)
        assert store.count_events() > initial_count


# =============================================================================
# Tick Management Tests
# =============================================================================


class TestTickManagement:
    """Tests for daemon tick management."""

    def test_advance_tick_increments(self, store: RDFEventStore) -> None:
        """advance_tick increments tick counter."""
        assert store.tick == 0
        store.advance_tick()
        assert store.tick == 1

    def test_advance_tick_records_event(self, store: RDFEventStore) -> None:
        """advance_tick records a TICK_COMPLETED event."""
        store.advance_tick()
        events = list(store.replay(event_types=[EventType.TICK_COMPLETED]))
        assert len(events) == 1


# =============================================================================
# State Hash Tests
# =============================================================================


class TestStateHash:
    """Tests for state hash computation."""

    def test_compute_state_hash_empty(self) -> None:
        """Hash of empty store is deterministic."""
        store1 = Store()
        store2 = Store()
        hash1 = compute_state_hash(store1)
        hash2 = compute_state_hash(store2)
        assert hash1 == hash2

    def test_compute_state_hash_deterministic(self, store: RDFEventStore) -> None:
        """Same state produces same hash."""
        store.append(
            DomainEvent(
                event_id="evt-1",
                event_type=EventType.TRIPLE_ADDED,
                timestamp=1.0,
                sequence=0,
                payload={"s": "urn:a", "p": "urn:b", "o": "c"},
            )
        )

        hash1 = compute_state_hash(store.store, STATE_GRAPH)
        hash2 = compute_state_hash(store.store, STATE_GRAPH)
        assert hash1 == hash2

    def test_hash_is_sha256_hex(self) -> None:
        """Hash is 64-character hex string (SHA-256)."""
        store = Store()
        hash_value = compute_state_hash(store)
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)


# =============================================================================
# Event Log Size Limit Tests
# =============================================================================


class TestEventLogSizeLimit:
    """Tests for max_event_log_size FIFO compaction."""

    def test_no_limit_by_default(self) -> None:
        """No limit enforced when max_event_log_size is None."""
        store = RDFEventStore(max_event_log_size=None)
        for i in range(100):
            store.append(
                DomainEvent(
                    event_id=f"evt-{i}",
                    event_type=EventType.TRIPLE_ADDED,
                    timestamp=float(i),
                    sequence=0,
                    payload={"s": f"urn:s:{i}", "p": "urn:p", "o": f"{i}"},
                )
            )
        assert store.count_events() == 100

    def test_limit_enforced_on_append(self) -> None:
        """Events are compacted when limit is exceeded."""
        store = RDFEventStore(max_event_log_size=5)
        for i in range(10):
            store.append(
                DomainEvent(
                    event_id=f"evt-{i}",
                    event_type=EventType.TRIPLE_ADDED,
                    timestamp=float(i),
                    sequence=0,
                    payload={"s": f"urn:s:{i}", "p": "urn:p", "o": f"{i}"},
                )
            )
        assert store.count_events() == 5

    def test_fifo_removes_oldest_first(self) -> None:
        """Oldest events are removed first (FIFO)."""
        store = RDFEventStore(max_event_log_size=3)
        for i in range(5):
            store.append(
                DomainEvent(
                    event_id=f"evt-{i}",
                    event_type=EventType.TRIPLE_ADDED,
                    timestamp=float(i),
                    sequence=0,
                    payload={"s": f"urn:s:{i}", "p": "urn:p", "o": f"{i}"},
                )
            )
        # Events 0 and 1 should be removed, events 2,3,4 remain
        events = list(store.replay())
        event_ids = [e.event_id for e in events]
        assert "evt-0" not in event_ids
        assert "evt-1" not in event_ids
        assert "evt-2" in event_ids
        assert "evt-3" in event_ids
        assert "evt-4" in event_ids

    def test_limit_exact_count_not_compacted(self) -> None:
        """Exactly max_event_log_size events are not compacted."""
        store = RDFEventStore(max_event_log_size=5)
        for i in range(5):
            store.append(
                DomainEvent(
                    event_id=f"evt-{i}",
                    event_type=EventType.TRIPLE_ADDED,
                    timestamp=float(i),
                    sequence=0,
                    payload={"s": f"urn:s:{i}", "p": "urn:p", "o": f"{i}"},
                )
            )
        assert store.count_events() == 5
        # All events should remain
        events = list(store.replay())
        assert len(events) == 5

    def test_state_graph_preserved_after_compaction(self) -> None:
        """State graph triples are NOT removed when events are compacted."""
        store = RDFEventStore(max_event_log_size=2)
        # Add 4 events - will compact to 2
        for i in range(4):
            store.append(
                DomainEvent(
                    event_id=f"evt-{i}",
                    event_type=EventType.TRIPLE_ADDED,
                    timestamp=float(i),
                    sequence=0,
                    payload={"s": f"urn:task:{i}", "p": "urn:status", "o": f"value-{i}"},
                )
            )

        # Event log should have 2 events
        assert store.count_events() == 2

        # But state graph should have ALL 4 triples
        query = f"""
        SELECT (COUNT(*) as ?count) WHERE {{
            GRAPH <{STATE_GRAPH_URI}> {{
                ?s ?p ?o .
            }}
        }}
        """
        results = list(store.store.query(query))
        triple_count = int(results[0]["count"].value)
        assert triple_count == 4

    def test_sequence_continues_after_compaction(self) -> None:
        """Sequence numbers continue correctly after compaction."""
        store = RDFEventStore(max_event_log_size=3)
        for i in range(6):
            seq = store.append(
                DomainEvent(
                    event_id=f"evt-{i}",
                    event_type=EventType.TRIPLE_ADDED,
                    timestamp=float(i),
                    sequence=0,
                    payload={"s": f"urn:s:{i}", "p": "urn:p", "o": f"{i}"},
                )
            )
        # Last sequence should be 6
        assert seq == 6
        assert store.sequence == 6
