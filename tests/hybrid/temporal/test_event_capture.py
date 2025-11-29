"""Tests for EventCaptureHook integration with v1 tick controller."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from typing import Any

import pytest

from kgcl.hybrid.temporal.adapters.in_memory_event_store import InMemoryEventStore
from kgcl.hybrid.temporal.application.event_capture_hook import (
    EventCaptureHook,
    TickSnapshot,
    create_event_capture_hook,
)
from kgcl.hybrid.temporal.domain.event import EventType
from kgcl.hybrid.tick_controller import TickResult


# Mock engine for testing
@dataclass
class MockEngine:
    """Mock engine simulating HybridOrchestrator."""

    state_turtle: str = field(default="")
    _store: Any = field(default=None, init=False)

    def __post_init__(self) -> None:
        """Initialize mock store."""

        @dataclass
        class MockStore:
            """Mock PyOxigraph store."""

            triple_count: int = 1

            def __len__(self) -> int:
                return self.triple_count

        object.__setattr__(self, "_store", MockStore())

    def _dump_state(self) -> str:
        """Simulate _dump_state method."""
        return self.state_turtle


# Mock rule for testing
@dataclass(frozen=True)
class MockRule:
    """Mock rule for testing rule firing."""

    id: str
    name: str


class TestTickSnapshot:
    """Tests for TickSnapshot value object."""

    def test_snapshot_is_frozen(self) -> None:
        """Verify TickSnapshot is immutable."""
        snapshot = TickSnapshot(
            tick_number=1,
            timestamp=datetime.now(UTC),
            graph_hash="abc123",
            triple_count=10,
            state_turtle="@prefix ex: .",
        )

        with pytest.raises(AttributeError):
            snapshot.tick_number = 2  # type: ignore[misc]

    def test_snapshot_equality(self) -> None:
        """Verify snapshots with same data are equal."""
        ts = datetime.now(UTC)
        snap1 = TickSnapshot(tick_number=1, timestamp=ts, graph_hash="abc", triple_count=5, state_turtle="data")
        snap2 = TickSnapshot(tick_number=1, timestamp=ts, graph_hash="abc", triple_count=5, state_turtle="data")

        assert snap1 == snap2


class TestEventCaptureHook:
    """Tests for EventCaptureHook TickHook implementation."""

    @pytest.fixture
    def event_store(self) -> InMemoryEventStore:
        """Create in-memory event store."""
        return InMemoryEventStore()

    @pytest.fixture
    def hook(self, event_store: InMemoryEventStore) -> EventCaptureHook:
        """Create event capture hook."""
        return create_event_capture_hook(event_store=event_store, workflow_id="test-workflow", actor_id="test-actor")

    @pytest.fixture
    def engine(self) -> MockEngine:
        """Create mock engine."""
        return MockEngine(state_turtle="@prefix ex: <http://example.org/>.\nex:s ex:p ex:o .")

    def test_on_pre_tick_creates_snapshot(self, hook: EventCaptureHook, engine: MockEngine) -> None:
        """Test on_pre_tick captures state snapshot."""
        result = hook.on_pre_tick(engine, tick_number=1)

        assert result is True
        assert hook._pre_tick_snapshot is not None
        assert hook._pre_tick_snapshot.tick_number == 1
        assert hook._pre_tick_snapshot.triple_count == 1
        assert hook._pre_tick_snapshot.state_turtle == engine.state_turtle

    def test_on_pre_tick_emits_tick_start_event(
        self, hook: EventCaptureHook, engine: MockEngine, event_store: InMemoryEventStore
    ) -> None:
        """Test on_pre_tick emits TICK_START event."""
        hook.on_pre_tick(engine, tick_number=1)

        result = event_store.query_range(workflow_id="test-workflow")
        assert result.total_count == 1
        assert len(result.events) == 1
        assert result.events[0].event_type == EventType.TICK_START
        assert result.events[0].tick_number == 1
        assert result.events[0].payload["phase"] == "pre_tick"

    def test_on_pre_tick_increments_vector_clock(self, hook: EventCaptureHook, engine: MockEngine) -> None:
        """Test on_pre_tick increments vector clock."""
        initial_clock_value = dict(hook.vector_clock.clocks).get("test-actor", 0)

        hook.on_pre_tick(engine, tick_number=1)

        new_clock_value = dict(hook.vector_clock.clocks).get("test-actor", 0)
        assert new_clock_value == initial_clock_value + 1

    def test_on_rule_fired_buffers_event(self, hook: EventCaptureHook, engine: MockEngine) -> None:
        """Test on_rule_fired buffers rule event."""
        hook.on_pre_tick(engine, tick_number=1)

        rule = MockRule(id="rule-1", name="Test Rule")
        hook.on_rule_fired(engine, rule, tick_number=1)

        assert len(hook._pending_rule_events) == 1
        event = hook._pending_rule_events[0]
        assert event.event_type == EventType.HOOK_EXECUTION
        assert event.payload["rule_id"] == "rule-1"
        assert event.payload["rule_name"] == "Test Rule"

    def test_on_rule_fired_multiple_rules(self, hook: EventCaptureHook, engine: MockEngine) -> None:
        """Test on_rule_fired buffers multiple rules."""
        hook.on_pre_tick(engine, tick_number=1)

        rule1 = MockRule(id="rule-1", name="Rule 1")
        rule2 = MockRule(id="rule-2", name="Rule 2")

        hook.on_rule_fired(engine, rule1, tick_number=1)
        hook.on_rule_fired(engine, rule2, tick_number=1)

        assert len(hook._pending_rule_events) == 2

    def test_on_post_tick_flushes_rule_events(
        self, hook: EventCaptureHook, engine: MockEngine, event_store: InMemoryEventStore
    ) -> None:
        """Test on_post_tick flushes buffered rule events."""
        hook.on_pre_tick(engine, tick_number=1)

        rule = MockRule(id="rule-1", name="Test Rule")
        hook.on_rule_fired(engine, rule, tick_number=1)

        result = TickResult(
            tick_number=1, rules_fired=1, triples_added=0, triples_removed=0, duration_ms=10.0, converged=False
        )

        hook.on_post_tick(engine, result)

        result = event_store.query_range(workflow_id="test-workflow")
        events = result.events
        # TICK_START + HOOK_EXECUTION + TICK_END
        assert len(events) == 3
        assert events[1].event_type == EventType.HOOK_EXECUTION

    def test_on_post_tick_emits_tick_end(
        self, hook: EventCaptureHook, engine: MockEngine, event_store: InMemoryEventStore
    ) -> None:
        """Test on_post_tick emits TICK_END event."""
        hook.on_pre_tick(engine, tick_number=1)

        result = TickResult(
            tick_number=1, rules_fired=2, triples_added=3, triples_removed=1, duration_ms=15.5, converged=False
        )

        hook.on_post_tick(engine, result)

        result = event_store.query_range(workflow_id="test-workflow")
        events = result.events
        tick_end = events[-1]

        assert tick_end.event_type == EventType.TICK_END
        assert tick_end.payload["rules_fired"] == 2
        assert tick_end.payload["triples_added"] == 3
        assert tick_end.payload["triples_removed"] == 1
        assert tick_end.payload["duration_ms"] == 15.5
        assert tick_end.payload["converged"] is False

    def test_on_post_tick_emits_status_change_when_triples_added(
        self, hook: EventCaptureHook, engine: MockEngine, event_store: InMemoryEventStore
    ) -> None:
        """Test on_post_tick emits STATUS_CHANGE when triples change."""
        hook.on_pre_tick(engine, tick_number=1)

        result = TickResult(
            tick_number=1, rules_fired=1, triples_added=5, triples_removed=2, duration_ms=10.0, converged=False
        )

        hook.on_post_tick(engine, result)

        result = event_store.query_range(workflow_id="test-workflow")
        events = result.events
        status_change_events = [e for e in events if e.event_type == EventType.STATUS_CHANGE]

        assert len(status_change_events) == 1
        assert status_change_events[0].payload["triples_added"] == 5
        assert status_change_events[0].payload["triples_removed"] == 2
        assert status_change_events[0].payload["net_change"] == 3

    def test_on_post_tick_no_status_change_when_no_triples_changed(
        self, hook: EventCaptureHook, engine: MockEngine, event_store: InMemoryEventStore
    ) -> None:
        """Test on_post_tick does not emit STATUS_CHANGE when no triples change."""
        hook.on_pre_tick(engine, tick_number=1)

        result = TickResult(
            tick_number=1, rules_fired=0, triples_added=0, triples_removed=0, duration_ms=5.0, converged=True
        )

        hook.on_post_tick(engine, result)

        result = event_store.query_range(workflow_id="test-workflow")
        events = result.events
        status_change_events = [e for e in events if e.event_type == EventType.STATUS_CHANGE]

        assert len(status_change_events) == 0

    def test_on_post_tick_emits_split_events(
        self, hook: EventCaptureHook, engine: MockEngine, event_store: InMemoryEventStore
    ) -> None:
        """Test on_post_tick emits SPLIT events from metadata."""
        hook.on_pre_tick(engine, tick_number=1)

        result = TickResult(
            tick_number=1,
            rules_fired=1,
            triples_added=2,
            triples_removed=0,
            duration_ms=10.0,
            converged=False,
            metadata={"splits": [{"parent": "task-1", "children": ["task-2", "task-3"]}]},
        )

        hook.on_post_tick(engine, result)

        result = event_store.query_range(workflow_id="test-workflow")
        events = result.events
        split_events = [e for e in events if e.event_type == EventType.SPLIT]

        assert len(split_events) == 1
        assert "split_info" in split_events[0].payload

    def test_on_post_tick_emits_join_events(
        self, hook: EventCaptureHook, engine: MockEngine, event_store: InMemoryEventStore
    ) -> None:
        """Test on_post_tick emits JOIN events from metadata."""
        hook.on_pre_tick(engine, tick_number=1)

        result = TickResult(
            tick_number=1,
            rules_fired=1,
            triples_added=1,
            triples_removed=2,
            duration_ms=10.0,
            converged=False,
            metadata={"joins": [{"children": ["task-2", "task-3"], "parent": "task-1"}]},
        )

        hook.on_post_tick(engine, result)

        result = event_store.query_range(workflow_id="test-workflow")
        events = result.events
        join_events = [e for e in events if e.event_type == EventType.JOIN]

        assert len(join_events) == 1
        assert "join_info" in join_events[0].payload

    def test_on_post_tick_emits_cancellation_events(
        self, hook: EventCaptureHook, engine: MockEngine, event_store: InMemoryEventStore
    ) -> None:
        """Test on_post_tick emits CANCELLATION events from metadata."""
        hook.on_pre_tick(engine, tick_number=1)

        result = TickResult(
            tick_number=1,
            rules_fired=1,
            triples_added=0,
            triples_removed=1,
            duration_ms=10.0,
            converged=False,
            metadata={"cancellations": [{"task": "task-1", "reason": "timeout"}]},
        )

        hook.on_post_tick(engine, result)

        result = event_store.query_range(workflow_id="test-workflow")
        events = result.events
        cancel_events = [e for e in events if e.event_type == EventType.CANCELLATION]

        assert len(cancel_events) == 1
        assert "cancellation_info" in cancel_events[0].payload

    def test_on_post_tick_clears_snapshot(self, hook: EventCaptureHook, engine: MockEngine) -> None:
        """Test on_post_tick clears snapshot after processing."""
        hook.on_pre_tick(engine, tick_number=1)

        assert hook._pre_tick_snapshot is not None

        result = TickResult(
            tick_number=1, rules_fired=0, triples_added=0, triples_removed=0, duration_ms=5.0, converged=True
        )

        hook.on_post_tick(engine, result)

        assert hook._pre_tick_snapshot is None

    def test_on_post_tick_no_snapshot_does_nothing(
        self, hook: EventCaptureHook, engine: MockEngine, event_store: InMemoryEventStore
    ) -> None:
        """Test on_post_tick does nothing if no snapshot exists."""
        result = TickResult(
            tick_number=1, rules_fired=0, triples_added=0, triples_removed=0, duration_ms=5.0, converged=True
        )

        hook.on_post_tick(engine, result)

        result = event_store.query_range(workflow_id="test-workflow")
        events = result.events
        assert len(events) == 0

    def test_causality_chain_maintained(
        self, hook: EventCaptureHook, engine: MockEngine, event_store: InMemoryEventStore
    ) -> None:
        """Test causality chain is maintained across events."""
        hook.on_pre_tick(engine, tick_number=1)

        rule = MockRule(id="rule-1", name="Test Rule")
        hook.on_rule_fired(engine, rule, tick_number=1)

        result = TickResult(
            tick_number=1, rules_fired=1, triples_added=1, triples_removed=0, duration_ms=10.0, converged=False
        )

        hook.on_post_tick(engine, result)

        result = event_store.query_range(workflow_id="test-workflow")
        events = result.events

        # Verify causality chain
        assert len(events[0].caused_by) == 0  # TICK_START has no cause
        assert events[1].caused_by == (events[0].event_id,)  # HOOK_EXECUTION caused by TICK_START
        assert events[2].caused_by == (events[1].event_id,)  # STATUS_CHANGE caused by last rule
        assert events[3].caused_by == (events[2].event_id,)  # TICK_END caused by STATUS_CHANGE

    def test_vector_clock_in_events(
        self, hook: EventCaptureHook, engine: MockEngine, event_store: InMemoryEventStore
    ) -> None:
        """Test vector clock is included in events."""
        hook.on_pre_tick(engine, tick_number=1)

        result = TickResult(
            tick_number=1, rules_fired=0, triples_added=0, triples_removed=0, duration_ms=5.0, converged=True
        )

        hook.on_post_tick(engine, result)

        result = event_store.query_range(workflow_id="test-workflow")
        events = result.events

        for event in events:
            assert event.vector_clock is not None
            assert len(event.vector_clock) > 0

    def test_full_tick_cycle(self, hook: EventCaptureHook, engine: MockEngine, event_store: InMemoryEventStore) -> None:
        """Test complete tick cycle with all phases."""
        # Pre-tick
        hook.on_pre_tick(engine, tick_number=1)

        # Rule firings
        rule1 = MockRule(id="rule-1", name="Rule 1")
        rule2 = MockRule(id="rule-2", name="Rule 2")
        hook.on_rule_fired(engine, rule1, tick_number=1)
        hook.on_rule_fired(engine, rule2, tick_number=1)

        # Post-tick with state change
        result = TickResult(
            tick_number=1,
            rules_fired=2,
            triples_added=5,
            triples_removed=1,
            duration_ms=25.5,
            converged=False,
            metadata={
                "splits": [{"parent": "t1", "children": ["t2", "t3"]}],
                "joins": [{"children": ["t4", "t5"], "parent": "t6"}],
            },
        )

        hook.on_post_tick(engine, result)

        result = event_store.query_range(workflow_id="test-workflow")
        events = result.events

        # Expected events:
        # 1. TICK_START
        # 2. HOOK_EXECUTION (rule-1)
        # 3. HOOK_EXECUTION (rule-2)
        # 4. STATUS_CHANGE
        # 5. SPLIT
        # 6. JOIN
        # 7. TICK_END

        assert len(events) == 7

        event_types = [e.event_type for e in events]
        assert event_types[0] == EventType.TICK_START
        assert event_types[1] == EventType.HOOK_EXECUTION
        assert event_types[2] == EventType.HOOK_EXECUTION
        assert event_types[3] == EventType.STATUS_CHANGE
        assert event_types[4] == EventType.SPLIT
        assert event_types[5] == EventType.JOIN
        assert event_types[6] == EventType.TICK_END

    def test_multiple_tick_cycles(
        self, hook: EventCaptureHook, engine: MockEngine, event_store: InMemoryEventStore
    ) -> None:
        """Test multiple consecutive tick cycles."""
        for tick_num in range(1, 4):
            hook.on_pre_tick(engine, tick_number=tick_num)

            result = TickResult(
                tick_number=tick_num,
                rules_fired=1,
                triples_added=1,
                triples_removed=0,
                duration_ms=10.0,
                converged=False,
            )

            hook.on_post_tick(engine, result)

        result = event_store.query_range(workflow_id="test-workflow")
        events = result.events

        # Each tick: TICK_START + STATUS_CHANGE + TICK_END = 3 events
        assert len(events) == 9

        # Verify tick numbers
        tick_starts = [e for e in events if e.event_type == EventType.TICK_START]
        assert [e.tick_number for e in tick_starts] == [1, 2, 3]


class TestEventCaptureHookWithStore:
    """Integration tests with PyOxigraph store."""

    @pytest.fixture
    def engine_with_store(self) -> MockEngine:
        """Create engine with store-like interface."""

        @dataclass
        class MockStore:
            triples: list[str] = field(default_factory=list)

            def dump(self, callback: Any, format: Any) -> None:
                """Simulate dump method."""
                turtle = "\n".join(self.triples)
                callback(turtle.encode("utf-8"))

            def __len__(self) -> int:
                return len(self.triples)

        @dataclass
        class EngineWithStore:
            _store: MockStore = field(default_factory=MockStore)

        engine = EngineWithStore()
        engine._store.triples = ["ex:s1 ex:p1 ex:o1 ."]
        return engine  # type: ignore[return-value]

    def test_dump_engine_state_with_store(self, engine_with_store: MockEngine) -> None:
        """Test _dump_engine_state with PyOxigraph store."""
        event_store = InMemoryEventStore()
        hook = create_event_capture_hook(event_store=event_store, workflow_id="test-workflow")

        state = hook._dump_engine_state(engine_with_store)

        assert "ex:s1 ex:p1 ex:o1 ." in state

    def test_count_triples_with_store(self, engine_with_store: MockEngine) -> None:
        """Test _count_triples with PyOxigraph store."""
        event_store = InMemoryEventStore()
        hook = create_event_capture_hook(event_store=event_store, workflow_id="test-workflow")

        count = hook._count_triples(engine_with_store)

        assert count == 1


class TestFactoryFunction:
    """Tests for create_event_capture_hook factory."""

    def test_create_event_capture_hook_returns_hook(self) -> None:
        """Test factory creates EventCaptureHook."""
        event_store = InMemoryEventStore()

        hook = create_event_capture_hook(event_store=event_store, workflow_id="test-workflow", actor_id="test-actor")

        assert isinstance(hook, EventCaptureHook)
        assert hook.workflow_id == "test-workflow"
        assert hook.actor_id == "test-actor"
        assert hook.event_store is event_store

    def test_create_event_capture_hook_default_actor(self) -> None:
        """Test factory uses default actor_id."""
        event_store = InMemoryEventStore()

        hook = create_event_capture_hook(event_store=event_store, workflow_id="test-workflow")

        assert hook.actor_id == "temporal_hook"
