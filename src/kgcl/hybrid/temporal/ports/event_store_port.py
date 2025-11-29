"""Event store port for append-only event log."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Iterator, Protocol, Sequence, runtime_checkable

if TYPE_CHECKING:
    from kgcl.hybrid.temporal.domain.event import WorkflowEvent


@dataclass(frozen=True)
class AppendResult:
    """Result of appending event(s).

    Parameters
    ----------
    event_ids : tuple[str, ...]
        IDs of appended events
    sequence_numbers : tuple[int, ...]
        Assigned sequence numbers
    success : bool
        Whether append succeeded
    error : str | None
        Error message if failed
    """

    event_ids: tuple[str, ...]
    sequence_numbers: tuple[int, ...]
    success: bool
    error: str | None = None


@dataclass(frozen=True)
class QueryResult:
    """Result of querying events.

    Parameters
    ----------
    events : tuple[WorkflowEvent, ...]
        Matching events
    total_count : int
        Total matching events (before pagination)
    has_more : bool
        Whether more events exist beyond limit
    """

    events: tuple[WorkflowEvent, ...]
    total_count: int
    has_more: bool


@runtime_checkable
class EventStore(Protocol):
    """Protocol for append-only event store.

    Provides temporal event persistence with:
    - Append-only semantics (no updates/deletes)
    - Sequential ordering
    - Hash chain integrity
    - Causal chain queries
    - Time-based and filtered queries
    """

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
        ...

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
        ...

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
        ...

    def get_by_sequence(self, sequence: int) -> WorkflowEvent | None:
        """Get event by sequence number.

        Parameters
        ----------
        sequence : int
            Sequence number

        Returns
        -------
        WorkflowEvent | None
            Event if found, None otherwise
        """
        ...

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
            Filter by event types
        limit : int
            Maximum events to return
        offset : int
            Number of events to skip

        Returns
        -------
        QueryResult
            Query results with pagination info
        """
        ...

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
        ...

    def get_causal_chain(self, event_id: str, max_depth: int = 100) -> list[WorkflowEvent]:
        """Get causal ancestors of an event.

        Traverses parent_event_id links to build causal chain.
        Useful for "Why did this fire?" queries.

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
        ...

    def get_latest_sequence(self) -> int:
        """Get latest sequence number.

        Returns
        -------
        int
            Latest sequence number, 0 if empty
        """
        ...

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
        ...

    def verify_chain_integrity(self, workflow_id: str) -> tuple[bool, str]:
        """Verify hash chain integrity.

        Parameters
        ----------
        workflow_id : str
            Workflow to verify

        Returns
        -------
        tuple[bool, str]
            (valid, error_message) - error_message empty if valid
        """
        ...
