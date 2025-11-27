"""KGCL Daemon - Long-running knowledge graph service with asyncio.

This module provides the main daemon class combining:
1. PyOxigraph state management with 4D ontology
2. Async tick loop for temporal orchestration
3. Add/query/subscribe operations
4. Hook execution on mutations

Architecture
------------
The daemon maintains a warm PyOxigraph store with event sourcing.
Every mutation is recorded as an event with temporal coordinates,
enabling time-travel queries and state reconstruction.

Example
-------
>>> from kgcl.daemon import KGCLDaemon, DaemonConfig
>>> async with KGCLDaemon(DaemonConfig()) as daemon:
...     await daemon.add("urn:task:1", "urn:status", "Pending")
...     results = await daemon.query("SELECT * WHERE { ?s ?p ?o }")
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pyoxigraph import NamedNode, Store

from kgcl.daemon.event_store import (
    STATE_GRAPH,
    STATE_GRAPH_URI,
    DomainEvent,
    EventType,
    RDFEventStore,
    compute_state_hash,
)


class DaemonState(Enum):
    """Daemon lifecycle states.

    Examples
    --------
    >>> DaemonState.RUNNING.value
    'running'
    """

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class DaemonConfig:
    """Configuration for KGCL daemon.

    Parameters
    ----------
    tick_interval : float
        Seconds between tick cycles (default: 1.0)
    snapshot_interval : int
        Create snapshot every N events (default: 100)
    max_batch_size : int
        Maximum mutations per transaction (default: 1000)
    enable_hooks : bool
        Enable hook execution on mutations (default: True)

    Examples
    --------
    >>> config = DaemonConfig(tick_interval=0.5, snapshot_interval=50)
    >>> config.tick_interval
    0.5
    """

    tick_interval: float = 1.0
    snapshot_interval: int = 100
    max_batch_size: int = 1000
    enable_hooks: bool = True


@dataclass
class MutationReceipt:
    """Receipt for a mutation operation.

    Parameters
    ----------
    event_id : str
        Unique event identifier
    sequence : int
        Assigned sequence number
    timestamp : float
        When mutation occurred
    triples_added : int
        Number of triples added
    triples_removed : int
        Number of triples removed
    state_hash : str
        SHA-256 hash of state after mutation

    Examples
    --------
    >>> receipt = MutationReceipt(
    ...     event_id="evt-001",
    ...     sequence=1,
    ...     timestamp=1700000000.0,
    ...     triples_added=1,
    ...     triples_removed=0,
    ...     state_hash="abc123...",
    ... )
    """

    event_id: str
    sequence: int
    timestamp: float
    triples_added: int
    triples_removed: int
    state_hash: str


@dataclass
class QueryResult:
    """Result of a SPARQL query.

    Parameters
    ----------
    bindings : list[dict[str, Any]]
        Query result bindings
    execution_time_ms : float
        Query execution time in milliseconds
    at_sequence : int
        Sequence number at query time

    Examples
    --------
    >>> result = QueryResult(bindings=[{"s": "urn:x", "p": "urn:y", "o": "z"}], execution_time_ms=1.5, at_sequence=100)
    """

    bindings: list[dict[str, Any]]
    execution_time_ms: float
    at_sequence: int


# Type alias for mutation callbacks
MutationCallback = Callable[[DomainEvent], None]


@dataclass
class KGCLDaemon:
    """Long-running KGCL daemon with asyncio event loop.

    Provides a warm PyOxigraph store with event sourcing,
    tick-based temporal orchestration, and mutation hooks.

    Parameters
    ----------
    config : DaemonConfig
        Daemon configuration
    store : RDFEventStore | None
        Optional existing event store (creates new if None)

    Attributes
    ----------
    state : DaemonState
        Current daemon lifecycle state
    sequence : int
        Current event sequence number
    tick : int
        Current tick cycle count

    Examples
    --------
    >>> async with KGCLDaemon(DaemonConfig()) as daemon:
    ...     receipt = await daemon.add("urn:x", "urn:y", "z")
    ...     print(f"Added at sequence {receipt.sequence}")
    """

    config: DaemonConfig = field(default_factory=DaemonConfig)
    _store: RDFEventStore | None = field(default=None, repr=False)
    _state: DaemonState = field(default=DaemonState.CREATED, repr=False)
    _tick_task: asyncio.Task[None] | None = field(default=None, repr=False)
    _subscribers: list[MutationCallback] = field(default_factory=list, repr=False)
    _events_since_snapshot: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        """Initialize event store if not provided."""
        if self._store is None:
            self._store = RDFEventStore()

    @property
    def state(self) -> DaemonState:
        """Current daemon lifecycle state."""
        return self._state

    @property
    def sequence(self) -> int:
        """Current event sequence number."""
        return self._store.sequence if self._store else 0

    @property
    def tick(self) -> int:
        """Current tick cycle count."""
        return self._store.tick if self._store else 0

    @property
    def store(self) -> RDFEventStore:
        """Underlying event store."""
        if self._store is None:
            msg = "Daemon not initialized"
            raise RuntimeError(msg)
        return self._store

    async def start(self) -> None:
        """Start the daemon and tick loop.

        Transitions daemon to RUNNING state and starts
        the background tick loop.

        Examples
        --------
        >>> daemon = KGCLDaemon(DaemonConfig())
        >>> await daemon.start()
        >>> daemon.state
        <DaemonState.RUNNING: 'running'>
        """
        if self._state != DaemonState.CREATED:
            msg = f"Cannot start daemon in state {self._state}"
            raise RuntimeError(msg)

        self._state = DaemonState.STARTING

        # Start tick loop
        self._tick_task = asyncio.create_task(self._tick_loop())

        self._state = DaemonState.RUNNING

    async def stop(self) -> None:
        """Stop the daemon gracefully.

        Cancels the tick loop and transitions to STOPPED state.

        Examples
        --------
        >>> await daemon.stop()
        >>> daemon.state
        <DaemonState.STOPPED: 'stopped'>
        """
        if self._state != DaemonState.RUNNING:
            return

        self._state = DaemonState.STOPPING

        # Cancel tick loop
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass

        # Create final snapshot
        if self._events_since_snapshot > 0:
            self.store.create_snapshot(self.sequence)

        self._state = DaemonState.STOPPED

    async def __aenter__(self) -> KGCLDaemon:
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.stop()

    async def _tick_loop(self) -> None:
        """Background tick loop for temporal orchestration."""
        while self._state == DaemonState.RUNNING:
            try:
                await asyncio.sleep(self.config.tick_interval)
                if self._state == DaemonState.RUNNING:
                    self.store.advance_tick()
                    self._check_snapshot()
            except asyncio.CancelledError:
                break

    def _check_snapshot(self) -> None:
        """Create snapshot if interval reached."""
        if self._events_since_snapshot >= self.config.snapshot_interval:
            self.store.create_snapshot(self.sequence)
            self._events_since_snapshot = 0

    def _notify_subscribers(self, event: DomainEvent) -> None:
        """Notify all subscribers of a mutation event."""
        for callback in self._subscribers:
            try:
                callback(event)
            except Exception:  # noqa: BLE001, S110
                pass  # Don't let subscriber errors crash daemon

    async def add(self, subject: str, predicate: str, obj: str, *, graph: str | None = None) -> MutationReceipt:
        """Add a triple to the graph.

        Parameters
        ----------
        subject : str
            Subject URI
        predicate : str
            Predicate URI
        obj : str
            Object value (URI or literal)
        graph : str | None
            Named graph URI (default: state graph)

        Returns
        -------
        MutationReceipt
            Receipt with sequence number and state hash

        Examples
        --------
        >>> receipt = await daemon.add("urn:task:1", "urn:status", "Complete")
        >>> receipt.sequence
        1
        """
        if self._state != DaemonState.RUNNING:
            msg = f"Cannot add in state {self._state}"
            raise RuntimeError(msg)

        event_id = f"add-{uuid.uuid4()}"
        timestamp = time.time()

        event = DomainEvent(
            event_id=event_id,
            event_type=EventType.TRIPLE_ADDED,
            timestamp=timestamp,
            sequence=0,  # Will be assigned
            payload={"s": subject, "p": predicate, "o": obj},
        )

        sequence = self.store.append(event)
        self._events_since_snapshot += 1

        # Compute state hash
        state_hash = compute_state_hash(self.store.store, STATE_GRAPH)

        # Notify subscribers
        self._notify_subscribers(event)

        return MutationReceipt(
            event_id=event_id,
            sequence=sequence,
            timestamp=timestamp,
            triples_added=1,
            triples_removed=0,
            state_hash=state_hash,
        )

    async def remove(self, subject: str, predicate: str, obj: str, *, graph: str | None = None) -> MutationReceipt:
        """Remove a triple from the graph.

        Parameters
        ----------
        subject : str
            Subject URI
        predicate : str
            Predicate URI
        obj : str
            Object value (URI or literal)
        graph : str | None
            Named graph URI (default: state graph)

        Returns
        -------
        MutationReceipt
            Receipt with sequence number and state hash

        Examples
        --------
        >>> receipt = await daemon.remove("urn:task:1", "urn:status", "Pending")
        """
        if self._state != DaemonState.RUNNING:
            msg = f"Cannot remove in state {self._state}"
            raise RuntimeError(msg)

        event_id = f"remove-{uuid.uuid4()}"
        timestamp = time.time()

        event = DomainEvent(
            event_id=event_id,
            event_type=EventType.TRIPLE_REMOVED,
            timestamp=timestamp,
            sequence=0,
            payload={"s": subject, "p": predicate, "o": obj},
        )

        sequence = self.store.append(event)
        self._events_since_snapshot += 1

        state_hash = compute_state_hash(self.store.store, STATE_GRAPH)
        self._notify_subscribers(event)

        return MutationReceipt(
            event_id=event_id,
            sequence=sequence,
            timestamp=timestamp,
            triples_added=0,
            triples_removed=1,
            state_hash=state_hash,
        )

    async def query(self, sparql: str, *, at_sequence: int | None = None) -> QueryResult:
        """Execute a SPARQL query.

        Parameters
        ----------
        sparql : str
            SPARQL SELECT query
        at_sequence : int | None
            Query at specific sequence (time-travel). Default: current state.

        Returns
        -------
        QueryResult
            Query results with bindings and timing

        Examples
        --------
        >>> result = await daemon.query("SELECT * WHERE { ?s ?p ?o } LIMIT 10")
        >>> len(result.bindings)
        10
        """
        start_time = time.perf_counter()

        if at_sequence is not None:
            # Time-travel query
            reconstructed = self.store.reconstruct_at(at_sequence)
            bindings = []
            for row in reconstructed.query(sparql):
                binding: dict[str, Any] = {}
                for var in row:
                    value = row[var]
                    if value is not None:
                        binding[var] = str(value.value) if hasattr(value, "value") else str(value)
                bindings.append(binding)
            query_sequence = at_sequence
        else:
            # Current state query - wrap to query state graph
            if "GRAPH" not in sparql.upper():
                # Auto-wrap in state graph context
                wrapped = f"""
                SELECT * WHERE {{
                    GRAPH <{STATE_GRAPH_URI}> {{
                        {sparql.replace("SELECT", "").replace("WHERE", "").strip().strip("{}")}
                    }}
                }}
                """
                bindings = self.store.query_state(wrapped)
            else:
                bindings = self.store.query_state(sparql)
            query_sequence = self.sequence

        execution_time = (time.perf_counter() - start_time) * 1000

        return QueryResult(bindings=bindings, execution_time_ms=execution_time, at_sequence=query_sequence)

    async def query_raw(self, sparql: str) -> list[dict[str, Any]]:
        """Execute raw SPARQL query against entire store.

        Parameters
        ----------
        sparql : str
            SPARQL query

        Returns
        -------
        list[dict[str, Any]]
            Query result bindings
        """
        return self.store.query_state(sparql)

    def subscribe(self, callback: MutationCallback) -> Callable[[], None]:
        """Subscribe to mutation events.

        Parameters
        ----------
        callback : MutationCallback
            Function called with each mutation event

        Returns
        -------
        Callable[[], None]
            Unsubscribe function

        Examples
        --------
        >>> def on_mutation(event):
        ...     print(f"Mutation: {event.event_type}")
        >>> unsubscribe = daemon.subscribe(on_mutation)
        >>> # Later...
        >>> unsubscribe()
        """
        self._subscribers.append(callback)

        def unsubscribe() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

        return unsubscribe

    async def replay_events(
        self, from_seq: int = 0, to_seq: int | None = None, event_types: list[EventType] | None = None
    ) -> AsyncIterator[DomainEvent]:
        """Replay events from the log.

        Parameters
        ----------
        from_seq : int
            Start sequence (exclusive)
        to_seq : int | None
            End sequence (inclusive)
        event_types : list[EventType] | None
            Filter by event types

        Yields
        ------
        DomainEvent
            Events in sequence order

        Examples
        --------
        >>> async for event in daemon.replay_events(from_seq=0):
        ...     print(event.event_type)
        """
        for event in self.store.replay(from_seq, to_seq, event_types):
            yield event

    async def get_state_at(self, sequence: int) -> Store:
        """Get graph state at specific sequence (time-travel).

        Parameters
        ----------
        sequence : int
            Target sequence number

        Returns
        -------
        Store
            PyOxigraph store with reconstructed state

        Examples
        --------
        >>> past_state = await daemon.get_state_at(50)
        """
        return self.store.reconstruct_at(sequence)

    def triple_count(self) -> int:
        """Count triples in current state graph.

        Returns
        -------
        int
            Number of triples

        Examples
        --------
        >>> daemon.triple_count()
        100
        """
        query = f"""
        SELECT (COUNT(*) AS ?count) WHERE {{
            GRAPH <{STATE_GRAPH_URI}> {{ ?s ?p ?o }}
        }}
        """
        results = self.store.query_state(query)
        if results and "count" in results[0]:
            return int(results[0]["count"])
        return 0

    def event_count(self) -> int:
        """Count total events in the log.

        Returns
        -------
        int
            Number of events
        """
        return self.store.count_events()
