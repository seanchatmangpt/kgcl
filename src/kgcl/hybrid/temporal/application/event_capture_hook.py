"""Event capture hook for temporal event sourcing.

Implements v1 TickHook protocol to capture workflow state changes
as immutable events without modifying v1 code.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from typing import TYPE_CHECKING, Any

from kgcl.hybrid.temporal.domain.event import EventType, WorkflowEvent
from kgcl.hybrid.temporal.domain.vector_clock import VectorClock

if TYPE_CHECKING:
    from kgcl.hybrid.temporal.ports.event_store_port import EventStore
    from kgcl.hybrid.tick_controller import TickResult


@dataclass(frozen=True)
class TickSnapshot:
    """Snapshot of state before tick execution.

    Parameters
    ----------
    tick_number : int
        Tick sequence number
    timestamp : datetime
        When snapshot was taken
    graph_hash : str
        Hash of RDF graph state
    triple_count : int
        Number of triples in graph
    state_turtle : str
        Serialized Turtle representation
    """

    tick_number: int
    timestamp: datetime
    graph_hash: str
    triple_count: int
    state_turtle: str


@dataclass
class EventCaptureHook:
    """Captures workflow events from v1 tick execution.

    Implements TickHook protocol to observe state changes and
    convert them to immutable events for the event store.

    Parameters
    ----------
    event_store : EventStore
        Store for appending captured events
    workflow_id : str
        Workflow identifier for events
    actor_id : str, default="temporal_hook"
        Actor identifier for vector clock

    Attributes
    ----------
    _vector_clock : VectorClock
        Lamport vector clock for causality
    _pre_tick_snapshot : TickSnapshot | None
        State snapshot before tick execution
    _pending_rule_events : list[WorkflowEvent]
        Events buffered during rule firing
    _last_event_id : str | None
        Most recent event ID for causality chain
    """

    event_store: EventStore
    workflow_id: str
    actor_id: str = "temporal_hook"
    _vector_clock: VectorClock = field(init=False)
    _pre_tick_snapshot: TickSnapshot | None = field(default=None, init=False)
    _pending_rule_events: list[WorkflowEvent] = field(default_factory=list, init=False)
    _last_event_id: str | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        """Initialize vector clock after dataclass construction."""
        object.__setattr__(self, "_vector_clock", VectorClock.zero(self.actor_id))

    def on_pre_tick(self, engine: Any, tick_number: int) -> bool:
        """Capture state snapshot before tick.

        Parameters
        ----------
        engine : Any
            Hybrid engine (HybridOrchestrator)
        tick_number : int
            Current tick number

        Returns
        -------
        bool
            True to continue (always)
        """
        # Increment vector clock
        self._vector_clock = self._vector_clock.increment(self.actor_id)

        # Create TICK_START event
        tick_start = self._create_event(EventType.TICK_START, tick_number, {"phase": "pre_tick"})

        # Capture state snapshot
        state_turtle = self._dump_engine_state(engine)
        graph_hash = hashlib.sha256(state_turtle.encode()).hexdigest()[:16]
        triple_count = self._count_triples(engine)

        self._pre_tick_snapshot = TickSnapshot(
            tick_number=tick_number,
            timestamp=datetime.now(UTC),
            graph_hash=graph_hash,
            triple_count=triple_count,
            state_turtle=state_turtle,
        )

        # Append tick start event
        self.event_store.append(tick_start)
        self._last_event_id = tick_start.event_id

        return True

    def on_rule_fired(self, engine: Any, rule: Any, tick_number: int) -> None:
        """Capture rule firing as event.

        Parameters
        ----------
        engine : Any
            Hybrid engine
        rule : Any
            Rule that fired
        tick_number : int
            Current tick number
        """
        rule_id = getattr(rule, "id", str(rule))
        rule_name = getattr(rule, "name", rule_id)

        # Create HOOK_EXECUTION event for rule
        event = self._create_event(
            EventType.HOOK_EXECUTION, tick_number, {"rule_id": rule_id, "rule_name": rule_name, "phase": "rule_fired"}
        )

        self._pending_rule_events.append(event)

    def on_post_tick(self, engine: Any, result: TickResult) -> None:
        """Capture state diff and emit events.

        Compares pre/post state to generate:
        - TOKEN_MOVE events for triple changes
        - STATUS_CHANGE for state transitions
        - TICK_END with summary

        Parameters
        ----------
        engine : Any
            Hybrid engine
        result : TickResult
            Tick execution result
        """
        if self._pre_tick_snapshot is None:
            return

        tick_number = result.tick_number

        # Flush pending rule events
        if self._pending_rule_events:
            self.event_store.append_batch(self._pending_rule_events)
            if self._pending_rule_events:
                self._last_event_id = self._pending_rule_events[-1].event_id
            self._pending_rule_events.clear()

        # Capture post-tick state
        post_state = self._dump_engine_state(engine)
        post_hash = hashlib.sha256(post_state.encode()).hexdigest()[:16]
        post_count = self._count_triples(engine)

        # Detect state changes
        events = self._diff_states(tick_number, self._pre_tick_snapshot.state_turtle, post_state, result)

        # Append diff events
        if events:
            self.event_store.append_batch(events)
            self._last_event_id = events[-1].event_id

        # Create TICK_END event with summary
        tick_end = self._create_event(
            EventType.TICK_END,
            tick_number,
            {
                "phase": "post_tick",
                "rules_fired": result.rules_fired,
                "triples_added": result.triples_added,
                "triples_removed": result.triples_removed,
                "duration_ms": result.duration_ms,
                "converged": result.converged,
                "pre_hash": self._pre_tick_snapshot.graph_hash,
                "post_hash": post_hash,
                "delta_triples": post_count - self._pre_tick_snapshot.triple_count,
            },
        )

        self.event_store.append(tick_end)
        self._last_event_id = tick_end.event_id

        # Clear snapshot
        self._pre_tick_snapshot = None

    def _create_event(self, event_type: EventType, tick_number: int, payload: dict[str, Any]) -> WorkflowEvent:
        """Create a new event with vector clock and causality.

        Parameters
        ----------
        event_type : EventType
            Type of event
        tick_number : int
            Tick number
        payload : dict[str, Any]
            Event payload data

        Returns
        -------
        WorkflowEvent
            Created event with causality chain
        """
        event_id = str(uuid.uuid4())
        caused_by = (self._last_event_id,) if self._last_event_id else ()

        return WorkflowEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(UTC),
            tick_number=tick_number,
            workflow_id=self.workflow_id,
            payload=payload,
            caused_by=caused_by,
            vector_clock=self._vector_clock.clocks,
        )

    def _diff_states(
        self, tick_number: int, pre_state: str, post_state: str, result: TickResult
    ) -> list[WorkflowEvent]:
        """Generate events from state diff.

        Parameters
        ----------
        tick_number : int
            Tick number
        pre_state : str
            State before tick
        post_state : str
            State after tick
        result : TickResult
            Tick execution result

        Returns
        -------
        list[WorkflowEvent]
            Events representing state changes
        """
        events: list[WorkflowEvent] = []

        # If state changed, emit STATUS_CHANGE
        if result.triples_added > 0 or result.triples_removed > 0:
            change_event = self._create_event(
                EventType.STATUS_CHANGE,
                tick_number,
                {
                    "triples_added": result.triples_added,
                    "triples_removed": result.triples_removed,
                    "net_change": result.triples_added - result.triples_removed,
                },
            )
            events.append(change_event)

        # Additional events based on metadata
        metadata = result.metadata

        # Detect splits
        if metadata.get("splits"):
            for split in metadata["splits"]:
                events.append(self._create_event(EventType.SPLIT, tick_number, {"split_info": split}))

        # Detect joins
        if metadata.get("joins"):
            for join in metadata["joins"]:
                events.append(self._create_event(EventType.JOIN, tick_number, {"join_info": join}))

        # Detect cancellations
        if metadata.get("cancellations"):
            for cancel in metadata["cancellations"]:
                events.append(self._create_event(EventType.CANCELLATION, tick_number, {"cancellation_info": cancel}))

        return events

    def _dump_engine_state(self, engine: Any) -> str:
        """Extract serialized state from engine.

        Parameters
        ----------
        engine : Any
            Engine to extract state from

        Returns
        -------
        str
            Serialized Turtle representation
        """
        # Try HybridOrchestrator._dump_state()
        if hasattr(engine, "_dump_state"):
            result: str = engine._dump_state()
            return result

        # Try direct store access
        if hasattr(engine, "_store"):
            import pyoxigraph as ox

            chunks: list[bytes] = []
            engine._store.dump(chunks.append, ox.RdfFormat.TURTLE)
            return b"".join(chunks).decode("utf-8")

        # Fallback for other engines
        if hasattr(engine, "graph"):
            serialized: str = engine.graph.serialize(format="turtle")
            return serialized

        return ""

    def _count_triples(self, engine: Any) -> int:
        """Count triples in engine state.

        Parameters
        ----------
        engine : Any
            Engine to count triples from

        Returns
        -------
        int
            Number of triples
        """
        if hasattr(engine, "_store"):
            return len(engine._store)
        if hasattr(engine, "graph"):
            return len(engine.graph)
        return 0

    @property
    def vector_clock(self) -> VectorClock:
        """Current vector clock state.

        Returns
        -------
        VectorClock
            Current vector clock
        """
        return self._vector_clock


def create_event_capture_hook(
    event_store: EventStore, workflow_id: str, actor_id: str = "temporal_hook"
) -> EventCaptureHook:
    """Factory function for EventCaptureHook.

    Parameters
    ----------
    event_store : EventStore
        Store for appending captured events
    workflow_id : str
        Workflow identifier for events
    actor_id : str, default="temporal_hook"
        Actor identifier for vector clock

    Returns
    -------
    EventCaptureHook
        Created hook instance
    """
    return EventCaptureHook(event_store=event_store, workflow_id=workflow_id, actor_id=actor_id)
