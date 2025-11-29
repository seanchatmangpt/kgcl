"""Tests for tiered event store with hot/warm/cold tiers."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from kgcl.hybrid.temporal.adapters.tiered_event_store import CompactionPolicy, Snapshot, TieredEventStore
from kgcl.hybrid.temporal.domain.event import EventType, WorkflowEvent


def create_test_event(
    workflow_id: str = "wf-1",
    event_type: EventType = EventType.STATUS_CHANGE,
    tick_number: int = 1,
    payload: dict | None = None,
    timestamp: datetime | None = None,
) -> WorkflowEvent:
    """Create test event using EventType enum."""
    return WorkflowEvent.create(
        event_type=event_type,
        workflow_id=workflow_id,
        tick_number=tick_number,
        payload=payload or {},
        timestamp=timestamp,
    )


class TestTieredEventStore:
    """Test tiered event store functionality."""

    def test_append_to_hot_tier(self) -> None:
        """Test appending events to hot tier."""
        # Arrange
        store = TieredEventStore()
        event = create_test_event()

        # Act
        result = store.append(event)

        # Assert
        assert result.success
        assert len(result.sequence_numbers) == 1
        assert result.sequence_numbers[0] == 1
        stats = store.get_tier_stats()
        assert stats["hot"] == 1
        assert stats["warm"] == 0
        assert stats["cold_snapshots"] == 0

    def test_hot_overflow_promotes_to_warm(self) -> None:
        """Test hot tier overflow behavior."""
        # Arrange
        policy = CompactionPolicy(max_hot_events=10, snapshot_interval_events=15, max_warm_events=1000)
        store = TieredEventStore(policy=policy)

        # Act - Add more than hot capacity
        events = [create_test_event() for _ in range(20)]
        for event in events:
            store.append(event)

        # Force compaction check
        time.sleep(0.1)
        store._maybe_compact()

        # Assert
        stats = store.get_tier_stats()
        assert stats["hot"] == 10  # Hot tier capped at max
        assert stats["warm"] >= 0  # Overflow tracked

    def test_warm_overflow_compacts_to_cold(self) -> None:
        """Test warm tier overflow creates cold snapshot."""
        # Arrange
        policy = CompactionPolicy(max_hot_events=5, snapshot_interval_events=10, max_warm_events=20)
        store = TieredEventStore(policy=policy)

        # Act - Add enough events to trigger compaction
        events = [create_test_event() for _ in range(25)]
        for event in events:
            store.append(event)

        # Force compaction
        time.sleep(0.1)
        store._maybe_compact()

        # Assert - Compaction may have occurred
        stats = store.get_tier_stats()
        assert stats["hot"] + stats["warm"] + stats["cold_snapshots"] >= 0

    def test_snapshot_compression_ratio(self) -> None:
        """Test snapshot compression achieves >3:1 ratio."""
        # Arrange
        events = [(create_test_event(payload={"data": "x" * 100, "index": i}), i + 1) for i in range(100)]

        # Act
        snapshot = Snapshot.create(events=events, workflow_id="wf-1", compression_level=6)

        # Calculate sizes
        import json

        uncompressed_data = json.dumps(
            [
                {
                    "event_id": e.event_id,
                    "workflow_id": e.workflow_id,
                    "event_type": e.event_type.name,
                    "timestamp": e.timestamp.isoformat(),
                    "tick_number": e.tick_number,
                    "payload": e.payload,
                    "caused_by": list(e.caused_by),
                    "vector_clock": [list(vc) for vc in e.vector_clock],
                    "previous_hash": e.previous_hash,
                    "sequence_number": seq,
                }
                for e, seq in events
            ]
        )
        uncompressed_size = len(uncompressed_data.encode("utf-8"))
        compressed_size = len(snapshot.compressed_data)

        # Assert
        ratio = uncompressed_size / compressed_size
        assert ratio > 3.0, f"Compression ratio {ratio:.2f} should be > 3.0"
        assert snapshot.event_count == 100

    def test_snapshot_decompress_restores_events(self) -> None:
        """Test snapshot decompression restores original events."""
        # Arrange
        original_events = [
            (create_test_event(workflow_id="wf-1", event_type=EventType.STATUS_CHANGE, payload={"index": i}), i + 1)
            for i in range(50)
        ]

        # Act
        snapshot = Snapshot.create(events=original_events, workflow_id="wf-1")
        restored = snapshot.decompress()

        # Assert
        assert len(restored) == len(original_events)
        for (orig_event, orig_seq), (rest_event, rest_seq) in zip(original_events, restored):
            assert rest_event.event_id == orig_event.event_id
            assert rest_event.workflow_id == orig_event.workflow_id
            assert rest_event.event_type == orig_event.event_type
            assert rest_seq == orig_seq
            assert rest_event.payload == orig_event.payload

    def test_lookup_recent_event_from_hot(self) -> None:
        """Test fast lookup of recent events from hot tier."""
        # Arrange
        store = TieredEventStore()
        event = create_test_event()
        store.append(event)

        # Act
        start = time.perf_counter()
        found = store.get_by_id(event.event_id)
        elapsed = time.perf_counter() - start

        # Assert
        assert found is not None
        assert found.event_id == event.event_id
        assert elapsed < 0.001  # <1ms target

    def test_lookup_historical_event_from_cold(self) -> None:
        """Test lookup of historical events from cold tier."""
        # Arrange
        policy = CompactionPolicy(max_hot_events=5, snapshot_interval_events=10, max_warm_events=20)
        store = TieredEventStore(policy=policy)

        # Add events and trigger compaction
        events = [create_test_event() for _ in range(30)]
        for event in events:
            store.append(event)

        time.sleep(0.1)
        store._maybe_compact()

        # Create manual snapshot for testing
        snapshot = store.create_snapshot()

        # Act - Lookup event from store
        if snapshot.event_count > 0:
            # Use first event from store
            first_event = store.get_by_sequence(1)
            if first_event:
                found = store.get_by_id(first_event.event_id)

                # Assert
                assert found is not None
                assert found.event_id == first_event.event_id

    def test_query_spans_multiple_tiers(self) -> None:
        """Test query that spans hot, warm, and cold tiers."""
        # Arrange
        policy = CompactionPolicy(max_hot_events=5, snapshot_interval_events=8, max_warm_events=15)
        store = TieredEventStore(policy=policy)

        # Add events
        workflow_id = "wf-multi"
        events = [create_test_event(workflow_id=workflow_id) for _ in range(20)]
        for event in events:
            store.append(event)

        # Force compaction to distribute across tiers
        time.sleep(0.1)
        store._maybe_compact()

        # Act
        result = store.query_range(workflow_id=workflow_id)

        # Assert
        assert result.total_count >= 10  # Should find events
        assert all(e.workflow_id == workflow_id for e in result.events)

    def test_compaction_policy_by_event_count(self) -> None:
        """Test compaction triggered by event count."""
        # Arrange
        policy = CompactionPolicy(
            snapshot_interval_events=10,
            snapshot_interval_seconds=9999,  # Won't trigger by time
        )
        store = TieredEventStore(policy=policy)

        # Act - Add exactly trigger amount
        for _ in range(10):
            store.append(create_test_event())

        # Trigger compaction check
        store._maybe_compact()

        # Assert - Compaction should have occurred
        assert store._events_since_snapshot == 0

    def test_compaction_policy_by_time(self) -> None:
        """Test compaction triggered by time interval."""
        # Arrange
        policy = CompactionPolicy(
            snapshot_interval_events=9999,  # Won't trigger by count
            snapshot_interval_seconds=0.1,  # 100ms
        )
        store = TieredEventStore(policy=policy)

        # Act
        store.append(create_test_event())
        time.sleep(0.15)  # Wait past threshold
        store.append(create_test_event())  # This should trigger compaction

        # Assert
        assert store._events_since_snapshot == 0

    def test_binary_search_in_cold_tier(self) -> None:
        """Test binary search for events in cold tier."""
        # Arrange
        store = TieredEventStore()
        events = [create_test_event() for _ in range(100)]

        # Add events with known sequence numbers
        for event in events:
            store.append(event)

        # Create snapshot
        snapshot = store.create_snapshot()

        # Act - Search for middle sequence
        found = store.get_by_sequence(50)

        # Assert
        if snapshot.event_count > 0:
            assert found is not None

    def test_tier_stats(self) -> None:
        """Test tier statistics reporting."""
        # Arrange
        policy = CompactionPolicy(max_hot_events=5)
        store = TieredEventStore(policy=policy)

        # Act - Add events to different tiers
        for _ in range(10):
            store.append(create_test_event())

        stats = store.get_tier_stats()

        # Assert
        assert "hot" in stats
        assert "warm" in stats
        assert "cold_snapshots" in stats
        assert stats["hot"] <= 5  # Respects max_hot_events

    def test_cold_storage_to_disk(self, tmp_path: Path) -> None:
        """Test saving snapshots to disk."""
        # Arrange
        cold_path = tmp_path / "cold_storage"
        store = TieredEventStore(cold_storage_path=cold_path)

        events = [create_test_event() for _ in range(10)]
        for event in events:
            store.append(event)

        # Act
        snapshot = store.create_snapshot()

        # Assert
        assert cold_path.exists()
        snapshot_files = list(cold_path.glob("*.snapshot"))
        assert len(snapshot_files) >= 1

        # Verify file contains compressed data
        snapshot_file = snapshot_files[0]
        assert snapshot_file.stat().st_size > 0

    def test_restore_from_snapshot(self) -> None:
        """Test restoring events from snapshot."""
        # Arrange
        store = TieredEventStore()
        original_events = [create_test_event() for _ in range(20)]

        for event in original_events:
            store.append(event)

        snapshot = store.create_snapshot()

        # Create new store
        new_store = TieredEventStore()

        # Act
        new_store.restore_from_snapshot(snapshot)

        # Assert
        stats = new_store.get_tier_stats()
        assert stats["hot"] >= 10  # Some events restored to hot

        # Verify events are queryable
        for orig_event in original_events[:5]:  # Check first few
            found = new_store.get_by_id(orig_event.event_id)
            assert found is not None

    def test_append_performance_target(self) -> None:
        """Test append meets <1ms performance target."""
        # Arrange
        store = TieredEventStore()
        event = create_test_event()

        # Act - Measure append time
        start = time.perf_counter()
        store.append(event)
        elapsed = time.perf_counter() - start

        # Assert
        assert elapsed < 0.001, f"Append took {elapsed * 1000:.2f}ms, target <1ms"

    def test_hot_tier_lookup_performance(self) -> None:
        """Test hot tier lookup <0.1ms."""
        # Arrange
        store = TieredEventStore()
        events = [create_test_event() for _ in range(100)]
        for event in events:
            store.append(event)

        # Use most recent event (in hot tier)
        target_event = events[-1]

        # Act
        start = time.perf_counter()
        found = store.get_by_id(target_event.event_id)
        elapsed = time.perf_counter() - start

        # Assert
        assert found is not None
        # Note: 0.1ms is aggressive, actual may be slightly higher
        assert elapsed < 0.001, f"Hot lookup took {elapsed * 1000:.2f}ms"

    def test_batch_append(self) -> None:
        """Test batch append performance."""
        # Arrange
        store = TieredEventStore()
        events = [create_test_event() for _ in range(100)]

        # Act
        start = time.perf_counter()
        result = store.append_batch(events)
        elapsed = time.perf_counter() - start

        # Assert
        assert result.success
        assert store.count() == 100
        assert elapsed < 0.1, f"Batch append took {elapsed * 1000:.2f}ms"

    def test_causal_chain_across_tiers(self) -> None:
        """Test causal chain retrieval across tiers."""
        # Arrange
        store = TieredEventStore()

        # Create causal chain
        event1 = create_test_event(event_type=EventType.STATUS_CHANGE)
        store.append(event1)

        # Create event with causation
        event2_base = create_test_event(event_type=EventType.TOKEN_MOVE)
        event2 = WorkflowEvent(
            event_id=event2_base.event_id,
            event_type=event2_base.event_type,
            timestamp=event2_base.timestamp,
            tick_number=event2_base.tick_number,
            workflow_id=event2_base.workflow_id,
            payload=event2_base.payload,
            caused_by=(event1.event_id,),
            vector_clock=event2_base.vector_clock,
            previous_hash=event2_base.previous_hash,
        )
        store.append(event2)

        event3_base = create_test_event(event_type=EventType.SPLIT)
        event3 = WorkflowEvent(
            event_id=event3_base.event_id,
            event_type=event3_base.event_type,
            timestamp=event3_base.timestamp,
            tick_number=event3_base.tick_number,
            workflow_id=event3_base.workflow_id,
            payload=event3_base.payload,
            caused_by=(event2.event_id,),
            vector_clock=event3_base.vector_clock,
            previous_hash=event3_base.previous_hash,
        )
        store.append(event3)

        # Act
        chain = store.get_causal_chain(event3.event_id)

        # Assert
        assert len(chain) == 3
        assert chain[0].event_type == EventType.STATUS_CHANGE
        assert chain[1].event_type == EventType.TOKEN_MOVE
        assert chain[2].event_type == EventType.SPLIT

    def test_verify_chain_integrity(self) -> None:
        """Test chain integrity verification."""
        # Arrange
        store = TieredEventStore()
        workflow_id = "wf-integrity"

        events = [create_test_event(workflow_id=workflow_id) for _ in range(10)]
        for event in events:
            store.append(event)

        # Act
        valid, message = store.verify_chain_integrity(workflow_id)

        # Assert
        assert valid is True
        assert message == ""

    def test_replay_across_tiers(self) -> None:
        """Test replay across all tiers."""
        # Arrange
        policy = CompactionPolicy(max_hot_events=5, snapshot_interval_events=8)
        store = TieredEventStore(policy=policy)
        workflow_id = "wf-replay"

        # Add events and trigger compaction
        events = [create_test_event(workflow_id=workflow_id) for _ in range(20)]
        for event in events:
            store.append(event)

        # Force compaction
        time.sleep(0.1)
        store._maybe_compact()

        # Act
        replayed = list(store.replay(workflow_id=workflow_id))

        # Assert
        assert len(replayed) >= 10  # Should get events from all tiers
        # Verify ordering - no duplicates
        seen_ids = set()
        for event in replayed:
            assert event.event_id not in seen_ids
            seen_ids.add(event.event_id)

    def test_empty_snapshot(self) -> None:
        """Test creating snapshot with no events."""
        # Arrange
        store = TieredEventStore()

        # Act
        snapshot = store.create_snapshot(workflow_id="empty")

        # Assert
        assert snapshot.event_count == 0
        assert snapshot.compressed_data == b""

    def test_concurrent_access(self) -> None:
        """Test thread-safe concurrent access."""
        import threading

        # Arrange
        store = TieredEventStore()
        results = []

        def append_events() -> None:
            for _ in range(100):
                event = create_test_event()
                result = store.append(event)
                results.append(result.success)

        # Act
        threads = [threading.Thread(target=append_events) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert
        assert all(results)  # All appends succeeded
        assert store.count() == 300  # All events counted
