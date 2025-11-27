"""Tests for KGCL Daemon - Chicago School TDD.

Tests verify behavior of the async daemon:
- Lifecycle management (start/stop)
- Add/remove/query operations
- Tick loop and temporal orchestration
- Subscription and event replay
- Time-travel queries
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from kgcl.daemon.event_store import DomainEvent, EventType, RDFEventStore
from kgcl.daemon.kgcld import DaemonConfig, DaemonState, KGCLDaemon, MutationReceipt, QueryResult

if TYPE_CHECKING:
    pass


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def config() -> DaemonConfig:
    """Create test daemon configuration with fast tick."""
    return DaemonConfig(tick_interval=0.1, snapshot_interval=10)


@pytest.fixture
def daemon(config: DaemonConfig) -> KGCLDaemon:
    """Create daemon instance (not started)."""
    return KGCLDaemon(config=config)


@pytest.fixture
async def running_daemon(config: DaemonConfig) -> KGCLDaemon:
    """Create and start a daemon."""
    daemon = KGCLDaemon(config=config)
    await daemon.start()
    yield daemon
    await daemon.stop()


# =============================================================================
# DaemonConfig Tests
# =============================================================================


class TestDaemonConfig:
    """Tests for DaemonConfig dataclass."""

    def test_default_config(self) -> None:
        """Default config has sensible values."""
        config = DaemonConfig()
        assert config.tick_interval == 1.0
        assert config.snapshot_interval == 100
        assert config.max_batch_size == 1000
        assert config.enable_hooks is True

    def test_custom_config(self) -> None:
        """Can create custom configuration."""
        config = DaemonConfig(tick_interval=0.5, snapshot_interval=50)
        assert config.tick_interval == 0.5
        assert config.snapshot_interval == 50


# =============================================================================
# DaemonState Tests
# =============================================================================


class TestDaemonState:
    """Tests for DaemonState enum."""

    def test_state_values(self) -> None:
        """DaemonState has expected values."""
        assert DaemonState.CREATED.value == "created"
        assert DaemonState.RUNNING.value == "running"
        assert DaemonState.STOPPED.value == "stopped"


# =============================================================================
# Daemon Lifecycle Tests
# =============================================================================


class TestDaemonLifecycle:
    """Tests for daemon lifecycle management."""

    def test_initial_state_is_created(self, daemon: KGCLDaemon) -> None:
        """New daemon starts in CREATED state."""
        assert daemon.state == DaemonState.CREATED

    @pytest.mark.asyncio
    async def test_start_transitions_to_running(self, daemon: KGCLDaemon) -> None:
        """start() transitions daemon to RUNNING state."""
        await daemon.start()
        assert daemon.state == DaemonState.RUNNING
        await daemon.stop()

    @pytest.mark.asyncio
    async def test_stop_transitions_to_stopped(self, daemon: KGCLDaemon) -> None:
        """stop() transitions daemon to STOPPED state."""
        await daemon.start()
        await daemon.stop()
        assert daemon.state == DaemonState.STOPPED

    @pytest.mark.asyncio
    async def test_cannot_start_twice(self, daemon: KGCLDaemon) -> None:
        """Cannot start an already started daemon."""
        await daemon.start()
        with pytest.raises(RuntimeError, match="Cannot start daemon"):
            await daemon.start()
        await daemon.stop()

    @pytest.mark.asyncio
    async def test_context_manager_starts_and_stops(self, config: DaemonConfig) -> None:
        """Context manager handles start/stop."""
        async with KGCLDaemon(config=config) as daemon:
            assert daemon.state == DaemonState.RUNNING
        assert daemon.state == DaemonState.STOPPED

    def test_initial_sequence_is_zero(self, daemon: KGCLDaemon) -> None:
        """New daemon has sequence 0."""
        assert daemon.sequence == 0

    def test_initial_tick_is_zero(self, daemon: KGCLDaemon) -> None:
        """New daemon has tick 0."""
        assert daemon.tick == 0


# =============================================================================
# Add Operation Tests
# =============================================================================


class TestAddOperation:
    """Tests for add() operation."""

    @pytest.mark.asyncio
    async def test_add_returns_receipt(self, running_daemon: KGCLDaemon) -> None:
        """add() returns a MutationReceipt."""
        receipt = await running_daemon.add("urn:s", "urn:p", "o")
        assert isinstance(receipt, MutationReceipt)

    @pytest.mark.asyncio
    async def test_add_increments_sequence(self, running_daemon: KGCLDaemon) -> None:
        """add() increments sequence number."""
        assert running_daemon.sequence == 0
        await running_daemon.add("urn:s", "urn:p", "o")
        assert running_daemon.sequence == 1

    @pytest.mark.asyncio
    async def test_add_receipt_has_sequence(self, running_daemon: KGCLDaemon) -> None:
        """Receipt contains assigned sequence."""
        receipt = await running_daemon.add("urn:s", "urn:p", "o")
        assert receipt.sequence == 1

    @pytest.mark.asyncio
    async def test_add_receipt_has_event_id(self, running_daemon: KGCLDaemon) -> None:
        """Receipt contains unique event ID."""
        receipt = await running_daemon.add("urn:s", "urn:p", "o")
        assert receipt.event_id.startswith("add-")

    @pytest.mark.asyncio
    async def test_add_receipt_has_state_hash(self, running_daemon: KGCLDaemon) -> None:
        """Receipt contains state hash."""
        receipt = await running_daemon.add("urn:s", "urn:p", "o")
        assert len(receipt.state_hash) == 64  # SHA-256 hex

    @pytest.mark.asyncio
    async def test_add_persists_triple(self, running_daemon: KGCLDaemon) -> None:
        """add() persists triple to state graph."""
        await running_daemon.add("urn:task:1", "urn:status", "Complete")
        assert running_daemon.triple_count() == 1

    @pytest.mark.asyncio
    async def test_cannot_add_when_not_running(self, daemon: KGCLDaemon) -> None:
        """Cannot add when daemon not running."""
        with pytest.raises(RuntimeError, match="Cannot add in state"):
            await daemon.add("urn:s", "urn:p", "o")


# =============================================================================
# Remove Operation Tests
# =============================================================================


class TestRemoveOperation:
    """Tests for remove() operation."""

    @pytest.mark.asyncio
    async def test_remove_returns_receipt(self, running_daemon: KGCLDaemon) -> None:
        """remove() returns a MutationReceipt."""
        await running_daemon.add("urn:s", "urn:p", "o")
        receipt = await running_daemon.remove("urn:s", "urn:p", "o")
        assert isinstance(receipt, MutationReceipt)

    @pytest.mark.asyncio
    async def test_remove_removes_triple(self, running_daemon: KGCLDaemon) -> None:
        """remove() removes triple from state graph."""
        await running_daemon.add("urn:s", "urn:p", "o")
        assert running_daemon.triple_count() == 1
        await running_daemon.remove("urn:s", "urn:p", "o")
        assert running_daemon.triple_count() == 0

    @pytest.mark.asyncio
    async def test_remove_increments_sequence(self, running_daemon: KGCLDaemon) -> None:
        """remove() increments sequence."""
        await running_daemon.add("urn:s", "urn:p", "o")
        seq_before = running_daemon.sequence
        await running_daemon.remove("urn:s", "urn:p", "o")
        assert running_daemon.sequence == seq_before + 1


# =============================================================================
# Query Operation Tests
# =============================================================================


class TestQueryOperation:
    """Tests for query() operation."""

    @pytest.mark.asyncio
    async def test_query_returns_result(self, running_daemon: KGCLDaemon) -> None:
        """query() returns QueryResult."""
        await running_daemon.add("urn:s", "urn:p", "o")
        result = await running_daemon.query("?s ?p ?o")
        assert isinstance(result, QueryResult)

    @pytest.mark.asyncio
    async def test_query_returns_bindings(self, running_daemon: KGCLDaemon) -> None:
        """query() returns matching bindings."""
        await running_daemon.add("urn:task:1", "urn:status", "Complete")
        result = await running_daemon.query("?s ?p ?o")
        assert len(result.bindings) >= 1

    @pytest.mark.asyncio
    async def test_query_has_execution_time(self, running_daemon: KGCLDaemon) -> None:
        """QueryResult includes execution time."""
        await running_daemon.add("urn:s", "urn:p", "o")
        result = await running_daemon.query("?s ?p ?o")
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_query_has_at_sequence(self, running_daemon: KGCLDaemon) -> None:
        """QueryResult includes sequence at query time."""
        await running_daemon.add("urn:s", "urn:p", "o")
        result = await running_daemon.query("?s ?p ?o")
        assert result.at_sequence == running_daemon.sequence


# =============================================================================
# Subscription Tests
# =============================================================================


class TestSubscription:
    """Tests for event subscription."""

    @pytest.mark.asyncio
    async def test_subscribe_receives_events(self, running_daemon: KGCLDaemon) -> None:
        """Subscriber receives mutation events."""
        events: list[DomainEvent] = []

        def on_mutation(event: DomainEvent) -> None:
            events.append(event)

        running_daemon.subscribe(on_mutation)
        await running_daemon.add("urn:s", "urn:p", "o")

        assert len(events) == 1
        assert events[0].event_type == EventType.TRIPLE_ADDED

    @pytest.mark.asyncio
    async def test_unsubscribe_stops_events(self, running_daemon: KGCLDaemon) -> None:
        """Unsubscribe stops receiving events."""
        events: list[DomainEvent] = []

        def on_mutation(event: DomainEvent) -> None:
            events.append(event)

        unsubscribe = running_daemon.subscribe(on_mutation)
        await running_daemon.add("urn:s1", "urn:p", "o")
        unsubscribe()
        await running_daemon.add("urn:s2", "urn:p", "o")

        assert len(events) == 1  # Only first event

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, running_daemon: KGCLDaemon) -> None:
        """Multiple subscribers all receive events."""
        events1: list[DomainEvent] = []
        events2: list[DomainEvent] = []

        running_daemon.subscribe(lambda e: events1.append(e))
        running_daemon.subscribe(lambda e: events2.append(e))

        await running_daemon.add("urn:s", "urn:p", "o")

        assert len(events1) == 1
        assert len(events2) == 1


# =============================================================================
# Event Replay Tests
# =============================================================================


class TestEventReplay:
    """Tests for event replay."""

    @pytest.mark.asyncio
    async def test_replay_events(self, running_daemon: KGCLDaemon) -> None:
        """Can replay events from log."""
        await running_daemon.add("urn:s1", "urn:p", "o")
        await running_daemon.add("urn:s2", "urn:p", "o")

        events = [e async for e in running_daemon.replay_events()]
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_replay_from_sequence(self, running_daemon: KGCLDaemon) -> None:
        """Can replay from specific sequence."""
        await running_daemon.add("urn:s1", "urn:p", "o")
        await running_daemon.add("urn:s2", "urn:p", "o")
        await running_daemon.add("urn:s3", "urn:p", "o")

        events = [e async for e in running_daemon.replay_events(from_seq=1)]
        assert len(events) == 2


# =============================================================================
# Time-Travel Tests
# =============================================================================


class TestTimeTravel:
    """Tests for time-travel functionality."""

    @pytest.mark.asyncio
    async def test_get_state_at_sequence(self, running_daemon: KGCLDaemon) -> None:
        """Can reconstruct state at past sequence."""
        await running_daemon.add("urn:s1", "urn:p", "o1")
        seq1 = running_daemon.sequence
        await running_daemon.add("urn:s2", "urn:p", "o2")
        await running_daemon.add("urn:s3", "urn:p", "o3")

        # Get state at seq1 (should have 1 triple)
        past_state = await running_daemon.get_state_at(seq1)
        count = sum(1 for _ in past_state.quads_for_pattern(None, None, None, None))
        assert count == 1


# =============================================================================
# Tick Loop Tests
# =============================================================================


class TestTickLoop:
    """Tests for tick loop."""

    @pytest.mark.asyncio
    async def test_tick_advances(self, config: DaemonConfig) -> None:
        """Tick advances over time."""
        config.tick_interval = 0.05
        async with KGCLDaemon(config=config) as daemon:
            initial_tick = daemon.tick
            await asyncio.sleep(0.15)  # Wait for ~3 ticks
            assert daemon.tick > initial_tick


# =============================================================================
# Count Tests
# =============================================================================


class TestCounts:
    """Tests for count operations."""

    @pytest.mark.asyncio
    async def test_triple_count(self, running_daemon: KGCLDaemon) -> None:
        """triple_count returns correct count."""
        assert running_daemon.triple_count() == 0
        await running_daemon.add("urn:s1", "urn:p", "o")
        assert running_daemon.triple_count() == 1
        await running_daemon.add("urn:s2", "urn:p", "o")
        assert running_daemon.triple_count() == 2

    @pytest.mark.asyncio
    async def test_event_count(self, running_daemon: KGCLDaemon) -> None:
        """event_count returns correct count."""
        initial = running_daemon.event_count()
        await running_daemon.add("urn:s", "urn:p", "o")
        assert running_daemon.event_count() == initial + 1
