"""In-memory event store implementation with ring buffer for hot tier."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Iterator, Sequence

from kgcl.hybrid.temporal.domain.event import WorkflowEvent
from kgcl.hybrid.temporal.ports.event_store_port import AppendResult, QueryResult


@dataclass
class InMemoryEventStore:
    """Thread-safe in-memory event store.

    Uses ring buffer for hot tier (recent events) with overflow to main store.
    Supports O(1) append, O(1) lookup by ID/sequence, O(n) range queries.

    Parameters
    ----------
    max_hot_events : int
        Maximum events in hot buffer before overflow
    """

    max_hot_events: int = 1000

    # Internal state (not frozen - mutable store)
    _events: list[WorkflowEvent] = field(default_factory=list, init=False, repr=False)
    _by_id: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _by_workflow: dict[str, list[int]] = field(default_factory=dict, init=False, repr=False)
    _hot_buffer: deque[int] = field(init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _sequence: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize hot buffer with max_hot_events capacity."""
        object.__setattr__(self, "_hot_buffer", deque(maxlen=self.max_hot_events))

    def append(self, event: WorkflowEvent) -> AppendResult:
        """Append single event to store.

        Parameters
        ----------
        event : WorkflowEvent
            Event to append

        Returns
        -------
        AppendResult
            Result with assigned sequence number
        """
        return self.append_batch([event])

    def append_batch(self, events: Sequence[WorkflowEvent]) -> AppendResult:
        """Append multiple events atomically.

        Parameters
        ----------
        events : Sequence[WorkflowEvent]
            Events to append as a batch

        Returns
        -------
        AppendResult
            Result with all assigned sequence numbers
        """
        if not events:
            return AppendResult(event_ids=(), sequence_numbers=(), success=True)

        with self._lock:
            event_ids: list[str] = []
            sequence_numbers: list[int] = []

            for event in events:
                # Assign sequence number
                self._sequence += 1
                seq = self._sequence

                # Store event
                self._events.append(event)
                self._by_id[event.event_id] = seq

                # Index by workflow
                if event.workflow_id not in self._by_workflow:
                    self._by_workflow[event.workflow_id] = []
                self._by_workflow[event.workflow_id].append(seq)

                # Add to hot buffer
                self._hot_buffer.append(seq)

                event_ids.append(event.event_id)
                sequence_numbers.append(seq)

            return AppendResult(event_ids=tuple(event_ids), sequence_numbers=tuple(sequence_numbers), success=True)

    def get_by_id(self, event_id: str) -> WorkflowEvent | None:
        """Get event by ID.

        Parameters
        ----------
        event_id : str
            Event identifier

        Returns
        -------
        WorkflowEvent | None
            Event if found, None otherwise
        """
        with self._lock:
            seq = self._by_id.get(event_id)
            if seq is None:
                return None
            return self._events[seq - 1]  # Sequences are 1-indexed

    def get_by_sequence(self, sequence: int) -> WorkflowEvent | None:
        """Get event by sequence number.

        Parameters
        ----------
        sequence : int
            Sequence number (1-indexed)

        Returns
        -------
        WorkflowEvent | None
            Event if found, None otherwise
        """
        with self._lock:
            if sequence < 1 or sequence > len(self._events):
                return None
            return self._events[sequence - 1]

    def query_range(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        workflow_id: str | None = None,
        event_types: Sequence[str] | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> QueryResult:
        """Query events with filters.

        Parameters
        ----------
        start : datetime | None
            Start timestamp (inclusive)
        end : datetime | None
            End timestamp (inclusive)
        workflow_id : str | None
            Filter by workflow ID
        event_types : Sequence[str] | None
            Filter by event types (EventType enums)
        limit : int
            Maximum events to return
        offset : int
            Number of events to skip

        Returns
        -------
        QueryResult
            Query results with pagination info
        """
        with self._lock:
            # Start with candidate events
            if workflow_id is not None:
                sequences = self._by_workflow.get(workflow_id, [])
                candidates = [self._events[seq - 1] for seq in sequences]
            else:
                candidates = list(self._events)

            # Apply filters
            filtered: list[WorkflowEvent] = []
            for event in candidates:
                # Time range filter
                if start is not None and event.timestamp < start:
                    continue
                if end is not None and event.timestamp > end:
                    continue

                # Event type filter (compare EventType enums)
                if event_types is not None and event.event_type not in event_types:
                    continue

                filtered.append(event)

            total_count = len(filtered)

            # Apply pagination
            paginated = filtered[offset : offset + limit]
            has_more = offset + limit < total_count

            return QueryResult(events=tuple(paginated), total_count=total_count, has_more=has_more)

    def replay(
        self, from_sequence: int = 0, to_sequence: int | None = None, workflow_id: str | None = None
    ) -> Iterator[WorkflowEvent]:
        """Replay events for projection building.

        Parameters
        ----------
        from_sequence : int
            Starting sequence number
        to_sequence : int | None
            Ending sequence number (inclusive), None for all
        workflow_id : str | None
            Filter by workflow ID

        Yields
        ------
        WorkflowEvent
            Events in sequence order
        """
        with self._lock:
            # Get candidate sequences
            if workflow_id is not None:
                sequences = [
                    seq
                    for seq in self._by_workflow.get(workflow_id, [])
                    if seq > from_sequence and (to_sequence is None or seq <= to_sequence)
                ]
            else:
                max_seq = to_sequence if to_sequence is not None else len(self._events)
                sequences = list(range(from_sequence + 1, max_seq + 1))

            # Yield events in order
            for seq in sorted(sequences):
                if seq <= len(self._events):
                    yield self._events[seq - 1]

    def get_causal_chain(self, event_id: str, max_depth: int = 100) -> list[WorkflowEvent]:
        """Get causal ancestors of an event.

        Traverses caused_by links to build causal chain.

        Parameters
        ----------
        event_id : str
            Starting event ID
        max_depth : int
            Maximum chain depth

        Returns
        -------
        list[WorkflowEvent]
            Events in causal order (oldest first)
        """
        with self._lock:
            chain: list[WorkflowEvent] = []
            current_id: str | None = event_id
            depth = 0

            while current_id is not None and depth < max_depth:
                event = self.get_by_id(current_id)
                if event is None:
                    break

                chain.insert(0, event)  # Prepend for oldest-first order

                # Get first parent from caused_by frozenset
                current_id = next(iter(event.caused_by)) if event.caused_by else None
                depth += 1

            return chain

    def get_latest_sequence(self) -> int:
        """Get latest sequence number.

        Returns
        -------
        int
            Latest sequence number, 0 if empty
        """
        with self._lock:
            return self._sequence

    def count(self, workflow_id: str | None = None) -> int:
        """Count events.

        Parameters
        ----------
        workflow_id : str | None
            Filter by workflow ID

        Returns
        -------
        int
            Number of matching events
        """
        with self._lock:
            if workflow_id is None:
                return len(self._events)
            return len(self._by_workflow.get(workflow_id, []))

    def verify_chain_integrity(self, workflow_id: str) -> tuple[bool, str]:
        """Verify hash chain integrity.

        Checks that each event's previous_hash matches the hash of the previous event.

        Parameters
        ----------
        workflow_id : str
            Workflow to verify

        Returns
        -------
        tuple[bool, str]
            (valid, error_message) - error_message empty if valid
        """
        with self._lock:
            sequences = self._by_workflow.get(workflow_id, [])
            if not sequences:
                return (True, "")

            sorted_seqs = sorted(sequences)
            prev_hash = ""

            for seq in sorted_seqs:
                event = self._events[seq - 1]

                # Check if previous_hash matches expected
                if event.previous_hash != prev_hash:
                    return (
                        False,
                        f"Hash chain broken at event {event.event_id}: "
                        f"expected previous_hash={prev_hash}, got {event.previous_hash}",
                    )

                # Use event's own computed hash for next iteration
                prev_hash = event.event_hash

            return (True, "")
