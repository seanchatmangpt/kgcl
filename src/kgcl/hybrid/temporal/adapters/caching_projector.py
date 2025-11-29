"""Caching projector with multi-level cache and event-driven invalidation."""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any

from kgcl.hybrid.temporal.domain.event import EventType, WorkflowEvent
from kgcl.hybrid.temporal.ports.event_store_port import EventStore
from kgcl.hybrid.temporal.ports.projector_port import ProjectionResult, SemanticProjector, StateDiff


@dataclass(frozen=True)
class CacheEntry:
    """Single cache entry with metadata."""

    state: dict[str, Any]
    sequence_number: int
    timestamp: datetime
    created_at: float  # time.monotonic()
    ttl_seconds: float = 30.0

    def is_expired(self) -> bool:
        """Check if cache entry has expired.

        Returns
        -------
        bool
            True if expired

        """
        return (time.monotonic() - self.created_at) > self.ttl_seconds


@dataclass
class CachingProjector:
    """Semantic projector with L1/L2/L3 cache hierarchy.

    Cache Levels:
    - L1 (Query): LRU cache for repeated queries, TTL=5s
    - L2 (Entity): Per-entity state cache, TTL=30s
    - L3 (Full): Complete state projection, invalidate on event

    Invalidation:
    - L3 invalidated on ANY new event
    - L2 invalidated when entity's events arrive
    - L1 invalidated by TTL expiry

    Attributes
    ----------
    event_store : EventStore
        Source of events
    l1_ttl : float
        L1 cache TTL in seconds
    l2_ttl : float
        L2 cache TTL in seconds
    l3_ttl : float
        L3 cache TTL in seconds

    """

    event_store: EventStore
    l1_ttl: float = 5.0
    l2_ttl: float = 30.0
    l3_ttl: float = 300.0

    # Cache state
    _l3_cache: CacheEntry | None = None
    _l2_cache: dict[str, CacheEntry] = field(default_factory=dict)
    _l1_cache: dict[str, CacheEntry] = field(default_factory=dict)
    _last_applied_seq: int = 0
    _is_stale: bool = True
    _lock: RLock = field(default_factory=RLock)

    def project_current(self) -> ProjectionResult:
        """Get current materialized state (O(1) from cache).

        Returns
        -------
        ProjectionResult
            Current state with cache metadata

        """
        start = time.monotonic()
        with self._lock:
            if self._l3_cache and not self._l3_cache.is_expired() and not self._is_stale:
                return ProjectionResult(
                    state=copy.deepcopy(self._l3_cache.state),
                    as_of=self._l3_cache.timestamp,
                    sequence_number=self._l3_cache.sequence_number,
                    events_applied=0,
                    cache_hit=True,
                    duration_ms=(time.monotonic() - start) * 1000,
                )

            # Rebuild projection from events
            return self._rebuild_projection(start)

    def project_at_time(self, timestamp: datetime) -> ProjectionResult:
        """Reconstruct state at specific time point.

        Parameters
        ----------
        timestamp : datetime
            Target time point

        Returns
        -------
        ProjectionResult
            State as of timestamp

        """
        start = time.monotonic()
        state: dict[str, Any] = {}
        events_applied = 0
        last_seq = 0
        last_ts = datetime.now()

        for event in self.event_store.replay():
            if event.timestamp > timestamp:
                break
            self._apply_event_to_state(state, event)
            events_applied += 1
            last_seq = event.sequence_number if hasattr(event, "sequence_number") else last_seq + 1
            last_ts = event.timestamp

        return ProjectionResult(
            state=state,
            as_of=last_ts,
            sequence_number=last_seq,
            events_applied=events_applied,
            cache_hit=False,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    def project_at_sequence(self, sequence: int) -> ProjectionResult:
        """Reconstruct state at specific sequence number.

        Parameters
        ----------
        sequence : int
            Target sequence number (inclusive)

        Returns
        -------
        ProjectionResult
            State at sequence number

        """
        start = time.monotonic()
        state: dict[str, Any] = {}
        events_applied = 0
        current_seq = 0
        last_ts = datetime.now()

        for event in self.event_store.replay():
            # Track current sequence (0-indexed from replay)
            self._apply_event_to_state(state, event)
            events_applied += 1
            last_ts = event.timestamp

            # Check if we've reached target sequence
            # Sequences are 0-indexed in the replay
            if current_seq >= sequence:
                break
            current_seq += 1

        return ProjectionResult(
            state=state,
            as_of=last_ts,
            sequence_number=current_seq,
            events_applied=events_applied,
            cache_hit=False,
            duration_ms=(time.monotonic() - start) * 1000,
        )

    def invalidate(self) -> None:
        """Invalidate cached projection (called on new events)."""
        with self._lock:
            self._is_stale = True

    def invalidate_entity(self, entity_id: str) -> None:
        """Invalidate L2 cache for specific entity.

        Parameters
        ----------
        entity_id : str
            Entity to invalidate

        """
        with self._lock:
            self._l2_cache.pop(entity_id, None)

    def get_diff(self, from_seq: int, to_seq: int) -> StateDiff:
        """Get changes between two sequence numbers.

        Parameters
        ----------
        from_seq : int
            Starting sequence number
        to_seq : int
            Ending sequence number

        Returns
        -------
        StateDiff
            Changes between sequences

        """
        state_from = self.project_at_sequence(from_seq).state
        state_to = self.project_at_sequence(to_seq).state

        # Find additions and modifications
        # Serialize dict values to JSON for hashability
        additions: list[tuple[str, str]] = []
        modifications: list[tuple[str, str, str]] = []
        for key, new_val in state_to.items():
            import json

            new_val_str = json.dumps(new_val, sort_keys=True)
            if key not in state_from:
                additions.append((key, new_val_str))
            elif state_from[key] != new_val:
                old_val_str = json.dumps(state_from[key], sort_keys=True)
                modifications.append((key, old_val_str, new_val_str))

        # Find removals
        removals = [key for key in state_from if key not in state_to]

        return StateDiff(
            additions=frozenset(additions), removals=frozenset(removals), modifications=frozenset(modifications)
        )

    def get_entity_history(self, entity_id: str, limit: int = 100) -> list[tuple[datetime, dict[str, Any]]]:
        """Get historical states of a specific entity.

        Parameters
        ----------
        entity_id : str
            Entity identifier
        limit : int, optional
            Maximum history entries, by default 100

        Returns
        -------
        list[tuple[datetime, dict[str, Any]]]
            List of (timestamp, state) tuples

        """
        history: list[tuple[datetime, dict[str, Any]]] = []
        state: dict[str, Any] = {}

        for event in self.event_store.replay():
            # Track if this event affected the entity
            affected = False
            payload = event.payload

            entity_from_payload = payload.get("entity_id") or payload.get("subject")
            if entity_from_payload == entity_id:
                affected = True

            if affected:
                # Apply event to state
                self._apply_event_to_state({entity_id: state}, event)
                history.append((event.timestamp, copy.deepcopy(state)))

                if len(history) >= limit:
                    break

        return history

    def _rebuild_projection(self, start_time: float) -> ProjectionResult:
        """Replay events to build current state.

        Parameters
        ----------
        start_time : float
            Start time for duration calculation

        Returns
        -------
        ProjectionResult
            Rebuilt projection result

        """
        state: dict[str, Any] = {}
        events_applied = 0
        last_seq = 0
        last_ts = datetime.now()

        for event in self.event_store.replay(from_sequence=self._last_applied_seq):
            self._apply_event_to_state(state, event)
            events_applied += 1
            last_seq = event.sequence_number if hasattr(event, "sequence_number") else last_seq + 1
            last_ts = event.timestamp

        self._l3_cache = CacheEntry(
            state=copy.deepcopy(state),
            sequence_number=last_seq,
            timestamp=last_ts,
            created_at=time.monotonic(),
            ttl_seconds=self.l3_ttl,
        )
        self._last_applied_seq = last_seq
        self._is_stale = False

        return ProjectionResult(
            state=state,
            as_of=last_ts,
            sequence_number=last_seq,
            events_applied=events_applied,
            cache_hit=False,
            duration_ms=(time.monotonic() - start_time) * 1000,
        )

    def _apply_event_to_state(self, state: dict[str, Any], event: WorkflowEvent) -> None:
        """Apply single event to state dict.

        Maps event types to state changes:
        - STATUS_CHANGE: Update task status
        - TOKEN_MOVE: Update token locations
        - CANCELLATION: Mark entities as cancelled

        Parameters
        ----------
        state : dict[str, Any]
            Current state to update
        event : WorkflowEvent
            Event to apply

        """
        payload = event.payload

        match event.event_type:
            case EventType.STATUS_CHANGE:
                entity = payload.get("entity_id")
                if entity:
                    state.setdefault(entity, {})
                    state[entity]["status"] = payload.get("new_status")
                    state[entity]["last_updated"] = event.timestamp.isoformat()

            case EventType.TOKEN_MOVE:
                from_place = payload.get("from_place")
                to_place = payload.get("to_place")
                token_id = payload.get("token_id")

                # Track tokens in state
                if not state.get("_tokens"):
                    state["_tokens"] = {}

                if token_id:
                    state["_tokens"][token_id] = {
                        "from": from_place,
                        "to": to_place,
                        "timestamp": event.timestamp.isoformat(),
                    }

            case EventType.CANCELLATION:
                entity = payload.get("entity_id")
                if entity:
                    state.setdefault(entity, {})
                    state[entity]["cancelled"] = True
                    state[entity]["cancelled_at"] = event.timestamp.isoformat()

            case _:
                # Generic: store event payload under entity
                entity = payload.get("entity_id") or payload.get("subject")
                if entity:
                    state.setdefault(entity, {})
                    state[entity].update(payload)
