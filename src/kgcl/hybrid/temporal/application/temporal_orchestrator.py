"""Temporal orchestrator wrapping v1 HybridOrchestrator.

Provides time-travel queries and event sourcing without
modifying v1 code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from typing import TYPE_CHECKING, Any

from kgcl.hybrid.temporal.adapters.caching_projector import CachingProjector
from kgcl.hybrid.temporal.adapters.in_memory_event_store import InMemoryEventStore
from kgcl.hybrid.temporal.application.event_capture_hook import create_event_capture_hook
from kgcl.hybrid.temporal.domain.event import WorkflowEvent
from kgcl.hybrid.tick_controller import TickController

if TYPE_CHECKING:
    from kgcl.hybrid.application.hybrid_orchestrator import HybridOrchestrator, TickOutcome
    from kgcl.hybrid.temporal.ports.event_store_port import EventStore
    from kgcl.hybrid.temporal.ports.projector_port import SemanticProjector


@dataclass(frozen=True)
class TemporalTickResult:
    """Extended tick result with temporal metadata.

    Parameters
    ----------
    tick_outcome : TickOutcome
        Original v1 tick outcome
    events_captured : int
        Number of events captured
    projection_invalidated : bool
        Whether projection cache was invalidated
    causal_depth : int
        Depth of causal chain for this tick
    """

    tick_outcome: Any  # TickOutcome
    events_captured: int
    projection_invalidated: bool
    causal_depth: int


@dataclass(frozen=True)
class HistoricalState:
    """State reconstructed at a point in time.

    Parameters
    ----------
    timestamp : datetime
        Query timestamp
    actual_timestamp : datetime
        Actual event timestamp (nearest)
    tick_number : int
        Tick at this point
    state_hash : str
        Hash of reconstructed state
    event_count : int
        Events replayed to reach state
    state_data : dict[str, Any]
        Reconstructed state data
    """

    timestamp: datetime
    actual_timestamp: datetime
    tick_number: int
    state_hash: str
    event_count: int
    state_data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CausalChainResult:
    """Result of causal chain query.

    Parameters
    ----------
    event_id : str
        Query event ID
    chain : tuple[WorkflowEvent, ...]
        Causal ancestors (oldest first)
    depth : int
        Chain depth
    root_event_id : str | None
        Root cause event ID
    """

    event_id: str
    chain: tuple[WorkflowEvent, ...]
    depth: int
    root_event_id: str | None


class TemporalOrchestrator:
    """Wraps v1 HybridOrchestrator with temporal event sourcing.

    Provides:
    - Transparent v1 execution with event capture
    - Time-travel queries via query_at_time()
    - Causal chain queries via get_causal_chain()
    - Projection cache management

    Parameters
    ----------
    v1_orchestrator : HybridOrchestrator
        The v1 orchestrator to wrap
    workflow_id : str
        Workflow identifier
    event_store : EventStore | None
        Event store (defaults to InMemoryEventStore)
    projector : SemanticProjector | None
        State projector (defaults to CachingProjector)
    """

    def __init__(
        self,
        v1_orchestrator: HybridOrchestrator,
        workflow_id: str,
        event_store: EventStore | None = None,
        projector: SemanticProjector | None = None,
    ) -> None:
        self._v1 = v1_orchestrator
        self._workflow_id = workflow_id

        # Initialize event store
        self._event_store: EventStore = event_store or InMemoryEventStore()

        # Initialize projector
        self._projector: SemanticProjector = projector or CachingProjector(event_store=self._event_store)

        # Create capture hook
        self._capture_hook = create_event_capture_hook(event_store=self._event_store, workflow_id=workflow_id)

        # Create tick controller with hook
        self._tick_controller = TickController(v1_orchestrator)
        self._tick_controller.register_hook(self._capture_hook)

        # Tick counter
        self._tick_count = 0

    def execute_tick(self) -> TemporalTickResult:
        """Execute one tick with event capture.

        Wraps v1 execute_tick() to capture events and
        manage projection cache.

        Returns
        -------
        TemporalTickResult
            Extended result with temporal metadata
        """
        self._tick_count += 1

        # Count events before
        events_before = len(list(self._event_store.replay(workflow_id=self._workflow_id)))

        # Execute v1 tick (hook captures events)
        v1_result = self._v1.execute_tick(self._tick_count)

        # Count events after
        events_after = len(list(self._event_store.replay(workflow_id=self._workflow_id)))
        events_captured = events_after - events_before

        # Invalidate projection if state changed
        projection_invalidated = False
        if v1_result.physics_result.delta != 0:
            self._projector.invalidate()
            projection_invalidated = True

        # Calculate causal depth
        causal_depth = 0
        if self._capture_hook._last_event_id:
            chain = self._event_store.get_causal_chain(self._capture_hook._last_event_id)
            causal_depth = len(chain)

        return TemporalTickResult(
            tick_outcome=v1_result,
            events_captured=events_captured,
            projection_invalidated=projection_invalidated,
            causal_depth=causal_depth,
        )

    def query_at_time(self, timestamp: datetime, *, use_cache: bool = True) -> HistoricalState:
        """Query state at a specific point in time.

        Reconstructs state by replaying events up to timestamp.

        Parameters
        ----------
        timestamp : datetime
            Point in time to query
        use_cache : bool
            Whether to use projection cache

        Returns
        -------
        HistoricalState
            Reconstructed state at timestamp
        """
        # Use projector for cached reconstruction
        if use_cache:
            projection = self._projector.project_at_time(timestamp)
            return HistoricalState(
                timestamp=timestamp,
                actual_timestamp=projection.as_of,
                tick_number=projection.sequence_number,
                state_hash=str(hash(str(projection.state))),
                event_count=projection.events_applied,
                state_data=projection.state,
            )

        # Manual replay without cache
        events = list(self._event_store.query_range(workflow_id=self._workflow_id, end=timestamp).events)

        if not events:
            return HistoricalState(
                timestamp=timestamp, actual_timestamp=datetime.now(UTC), tick_number=0, state_hash="", event_count=0
            )

        # Find latest event before timestamp
        latest = events[-1]

        return HistoricalState(
            timestamp=timestamp,
            actual_timestamp=latest.timestamp,
            tick_number=latest.tick_number,
            state_hash=latest.event_hash,
            event_count=len(events),
            state_data=latest.payload,
        )

    def get_causal_chain(self, event_id: str, max_depth: int = 100) -> CausalChainResult:
        """Get causal ancestors of an event.

        Traces causality back to root cause.

        Parameters
        ----------
        event_id : str
            Event to trace
        max_depth : int
            Maximum chain depth

        Returns
        -------
        CausalChainResult
            Causal chain (oldest first)
        """
        chain = self._event_store.get_causal_chain(event_id, max_depth)

        root_id = chain[0].event_id if chain else None

        return CausalChainResult(event_id=event_id, chain=tuple(chain), depth=len(chain), root_event_id=root_id)

    def get_events_for_tick(self, tick_number: int) -> list[WorkflowEvent]:
        """Get all events from a specific tick.

        Parameters
        ----------
        tick_number : int
            Tick number

        Returns
        -------
        list[WorkflowEvent]
            Events from that tick
        """
        all_events = list(self._event_store.replay(workflow_id=self._workflow_id))
        return [e for e in all_events if e.tick_number == tick_number]

    def verify_chain_integrity(self) -> tuple[bool, str]:
        """Verify event chain integrity.

        Returns
        -------
        tuple[bool, str]
            (valid, message)
        """
        return self._event_store.verify_chain_integrity(self._workflow_id)

    @property
    def event_store(self) -> EventStore:
        """Access to underlying event store.

        Returns
        -------
        EventStore
            Event store instance
        """
        return self._event_store

    @property
    def projector(self) -> SemanticProjector:
        """Access to underlying projector.

        Returns
        -------
        SemanticProjector
            Projector instance
        """
        return self._projector

    @property
    def tick_count(self) -> int:
        """Total ticks executed.

        Returns
        -------
        int
            Number of ticks
        """
        return self._tick_count

    @property
    def workflow_id(self) -> str:
        """Workflow identifier.

        Returns
        -------
        str
            Workflow ID
        """
        return self._workflow_id


def create_temporal_orchestrator(
    v1_orchestrator: HybridOrchestrator,
    workflow_id: str,
    event_store: EventStore | None = None,
    projector: SemanticProjector | None = None,
) -> TemporalOrchestrator:
    """Factory function for TemporalOrchestrator.

    Parameters
    ----------
    v1_orchestrator : HybridOrchestrator
        V1 orchestrator to wrap
    workflow_id : str
        Workflow identifier
    event_store : EventStore | None
        Optional event store
    projector : SemanticProjector | None
        Optional projector

    Returns
    -------
    TemporalOrchestrator
        Configured temporal orchestrator
    """
    return TemporalOrchestrator(
        v1_orchestrator=v1_orchestrator, workflow_id=workflow_id, event_store=event_store, projector=projector
    )
