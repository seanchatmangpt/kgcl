"""Time-travel query utilities for temporal orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kgcl.hybrid.temporal.application.temporal_orchestrator import TemporalOrchestrator
    from kgcl.hybrid.temporal.domain.event import WorkflowEvent


@dataclass(frozen=True)
class TimelineEntry:
    """Entry in workflow timeline.

    Parameters
    ----------
    timestamp : datetime
        Event timestamp
    tick_number : int
        Tick number
    event_type : str
        Event type name
    event_id : str
        Event identifier
    summary : str
        Human-readable summary
    """

    timestamp: datetime
    tick_number: int
    event_type: str
    event_id: str
    summary: str


@dataclass(frozen=True)
class DiffResult:
    """Result of comparing two points in time.

    Parameters
    ----------
    from_timestamp : datetime
        Start timestamp
    to_timestamp : datetime
        End timestamp
    events_between : int
        Number of events between timestamps
    ticks_between : int
        Number of ticks between timestamps
    state_changed : bool
        Whether state changed
    changes : list[str]
        List of detected changes
    """

    from_timestamp: datetime
    to_timestamp: datetime
    events_between: int
    ticks_between: int
    state_changed: bool
    changes: list[str]


class TimeTravelQuery:
    """Query interface for temporal navigation.

    Provides high-level time-travel queries over
    the temporal orchestrator.

    Parameters
    ----------
    orchestrator : TemporalOrchestrator
        Temporal orchestrator to query
    """

    def __init__(self, orchestrator: TemporalOrchestrator) -> None:
        self._orchestrator = orchestrator

    def get_timeline(
        self, start: datetime | None = None, end: datetime | None = None, limit: int = 100
    ) -> list[TimelineEntry]:
        """Get workflow timeline as list of entries.

        Parameters
        ----------
        start : datetime | None
            Start time (inclusive)
        end : datetime | None
            End time (inclusive)
        limit : int
            Maximum number of entries

        Returns
        -------
        list[TimelineEntry]
            Timeline entries
        """
        query_result = self._orchestrator.event_store.query_range(
            workflow_id=self._orchestrator.workflow_id, start=start, end=end, limit=limit
        )

        entries = []
        for event in query_result.events:
            entries.append(
                TimelineEntry(
                    timestamp=event.timestamp,
                    tick_number=event.tick_number,
                    event_type=event.event_type.name,
                    event_id=event.event_id,
                    summary=self._summarize_event(event),
                )
            )

        return entries

    def diff_times(self, from_time: datetime, to_time: datetime) -> DiffResult:
        """Compare state at two points in time.

        Parameters
        ----------
        from_time : datetime
            Start timestamp
        to_time : datetime
            End timestamp

        Returns
        -------
        DiffResult
            Comparison result
        """
        from_state = self._orchestrator.query_at_time(from_time)
        to_state = self._orchestrator.query_at_time(to_time)

        # Count events between
        events = list(
            self._orchestrator.event_store.query_range(
                workflow_id=self._orchestrator.workflow_id, start=from_time, end=to_time
            ).events
        )

        # Detect changes
        changes = []
        if from_state.state_hash != to_state.state_hash:
            changes.append(f"State hash changed: {from_state.state_hash} -> {to_state.state_hash}")
        if from_state.tick_number != to_state.tick_number:
            changes.append(f"Tick advanced: {from_state.tick_number} -> {to_state.tick_number}")

        return DiffResult(
            from_timestamp=from_time,
            to_timestamp=to_time,
            events_between=len(events),
            ticks_between=to_state.tick_number - from_state.tick_number,
            state_changed=from_state.state_hash != to_state.state_hash,
            changes=changes,
        )

    def find_event_by_type(self, event_type: str, after: datetime | None = None) -> WorkflowEvent | None:
        """Find first event of given type.

        Parameters
        ----------
        event_type : str
            Event type to search for
        after : datetime | None
            Optional start time

        Returns
        -------
        WorkflowEvent | None
            First matching event or None
        """
        events = list(
            self._orchestrator.event_store.query_range(workflow_id=self._orchestrator.workflow_id, start=after).events
        )

        for event in events:
            if event.event_type.name == event_type:
                return event
        return None

    def replay_to_tick(self, target_tick: int) -> list[WorkflowEvent]:
        """Get all events up to and including a tick.

        Parameters
        ----------
        target_tick : int
            Target tick number

        Returns
        -------
        list[WorkflowEvent]
            Events up to and including tick
        """
        all_events = list(self._orchestrator.event_store.replay(workflow_id=self._orchestrator.workflow_id))
        return [e for e in all_events if e.tick_number <= target_tick]

    def _summarize_event(self, event: WorkflowEvent) -> str:
        """Create human-readable event summary.

        Parameters
        ----------
        event : WorkflowEvent
            Event to summarize

        Returns
        -------
        str
            Human-readable summary
        """
        payload = event.payload

        if event.event_type.name == "TICK_START":
            return f"Tick {event.tick_number} started"
        elif event.event_type.name == "TICK_END":
            rules = payload.get("rules_fired", 0)
            return f"Tick {event.tick_number} ended ({rules} rules fired)"
        elif event.event_type.name == "STATUS_CHANGE":
            added = payload.get("triples_added", 0)
            removed = payload.get("triples_removed", 0)
            return f"State changed (+{added}/-{removed} triples)"
        else:
            return event.event_type.name


def create_time_travel_query(orchestrator: TemporalOrchestrator) -> TimeTravelQuery:
    """Factory for TimeTravelQuery.

    Parameters
    ----------
    orchestrator : TemporalOrchestrator
        Temporal orchestrator to wrap

    Returns
    -------
    TimeTravelQuery
        Query interface
    """
    return TimeTravelQuery(orchestrator)
