"""Agenda generator for daily/weekly calendar views.

Queries RDF graph for calendar events and reminders, sorts by date/priority,
and formats as markdown agenda with focus time blocks.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDFS

from .base import ProjectionGenerator

# Define namespaces
KGC = Namespace("http://example.org/kgc/")
ICAL = Namespace("http://www.w3.org/2002/12/cal/ical#")


@dataclass
class CalendarEvent:
    """Domain object for calendar events."""

    uri: str
    title: str
    start: datetime
    end: datetime | None = None
    description: str = ""
    location: str = ""
    priority: int = 3  # 1=high, 3=normal, 5=low
    is_multi_day: bool = False

    def duration_hours(self) -> float:
        """Calculate event duration in hours."""
        if self.end:
            delta = self.end - self.start
            return delta.total_seconds() / 3600
        return 0.0

    def format_time_range(self) -> str:
        """Format event time range for display."""
        if self.is_multi_day and self.end:
            return f"{self.start.strftime('%b %d')} - {self.end.strftime('%b %d')}"
        if self.end:
            return f"{self.start.strftime('%H:%M')} - {self.end.strftime('%H:%M')}"
        return self.start.strftime("%H:%M")


@dataclass
class Reminder:
    """Domain object for reminders."""

    uri: str
    title: str
    due_date: datetime
    priority: int = 3
    completed: bool = False
    tags: list[str] = field(default_factory=list)


@dataclass
class FocusBlock:
    """Domain object for focus time blocks."""

    start: datetime
    end: datetime
    purpose: str = "Deep Work"

    def duration_hours(self) -> float:
        """Calculate focus block duration in hours."""
        delta = self.end - self.start
        return delta.total_seconds() / 3600


class AgendaGenerator(ProjectionGenerator):
    """Generate daily/weekly agenda from calendar events and reminders.

    Queries RDF graph for:
    - Calendar events (meetings, appointments)
    - Reminders and tasks
    - Focus time blocks

    Sorts by date/priority and formats as markdown agenda.
    """

    def __init__(self, graph: Graph, start_date: datetime | None = None) -> None:
        """Initialize agenda generator.

        Args:
            graph: RDF graph containing calendar data
            start_date: Start date for agenda, defaults to today
        """
        super().__init__(graph)
        self.start_date = start_date or datetime.now(tz=UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def gather_data(self) -> dict[str, Any]:
        """Gather calendar events and reminders from RDF graph.

        Returns
        -------
            Dictionary with events, reminders, and focus blocks
        """
        events = self._query_events()
        reminders = self._query_reminders()
        focus_blocks = self._find_focus_blocks(events)

        return {
            "date": self.start_date,
            "events": sorted(events, key=lambda e: e.start),
            "reminders": sorted(reminders, key=lambda r: (r.priority, r.due_date)),
            "focus_blocks": sorted(focus_blocks, key=lambda f: f.start),
            "total_event_hours": sum(e.duration_hours() for e in events),
            "total_focus_hours": sum(f.duration_hours() for f in focus_blocks),
        }

    def _query_events(self) -> list[CalendarEvent]:
        """Query RDF graph for calendar events."""
        events = []

        # Query for events with start time
        query = f"""
        PREFIX kgc: <{KGC}>
        PREFIX ical: <{ICAL}>
        PREFIX rdfs: <{RDFS}>

        SELECT ?event ?title ?start ?end ?desc ?location ?priority
        WHERE {{
            ?event a ical:Vevent .
            ?event ical:dtstart ?start .
            ?event ical:summary ?title .
            OPTIONAL {{ ?event ical:dtend ?end }}
            OPTIONAL {{ ?event ical:description ?desc }}
            OPTIONAL {{ ?event ical:location ?location }}
            OPTIONAL {{ ?event ical:priority ?priority }}
        }}
        """

        results = self.graph.query(query)

        for row in results:
            start_dt = self._parse_datetime(row.start)
            end_dt = self._parse_datetime(row.end) if row.end else None

            # Filter events within date range (today + 7 days)
            end_range = self.start_date + timedelta(days=7)
            if start_dt < self.start_date or start_dt > end_range:
                continue

            is_multi_day = False
            if end_dt:
                is_multi_day = (end_dt - start_dt).days > 0

            events.append(
                CalendarEvent(
                    uri=str(row.event),
                    title=str(row.title),
                    start=start_dt,
                    end=end_dt,
                    description=str(row.desc) if row.desc else "",
                    location=str(row.location) if row.location else "",
                    priority=int(row.priority) if row.priority else 3,
                    is_multi_day=is_multi_day,
                )
            )

        return events

    def _query_reminders(self) -> list[Reminder]:
        """Query RDF graph for reminders and tasks."""
        reminders = []

        query = f"""
        PREFIX kgc: <{KGC}>
        PREFIX rdfs: <{RDFS}>

        SELECT ?reminder ?title ?due ?priority ?completed
        WHERE {{
            ?reminder a kgc:Reminder .
            ?reminder rdfs:label ?title .
            ?reminder kgc:dueDate ?due .
            OPTIONAL {{ ?reminder kgc:priority ?priority }}
            OPTIONAL {{ ?reminder kgc:completed ?completed }}
        }}
        """

        results = self.graph.query(query)

        for row in results:
            due_dt = self._parse_datetime(row.due)

            # Filter reminders within date range
            end_range = self.start_date + timedelta(days=7)
            if due_dt < self.start_date or due_dt > end_range:
                continue

            reminders.append(
                Reminder(
                    uri=str(row.reminder),
                    title=str(row.title),
                    due_date=due_dt,
                    priority=int(row.priority) if row.priority else 3,
                    completed=bool(row.completed) if row.completed else False,
                )
            )

        return reminders

    def _find_focus_blocks(self, events: list[CalendarEvent]) -> list[FocusBlock]:
        """Identify focus time blocks between events.

        Args:
            events: List of calendar events

        Returns
        -------
            List of focus blocks (gaps >= 2 hours between events)
        """
        focus_blocks = []

        # Sort events by start time
        sorted_events = sorted(events, key=lambda e: e.start)

        for i in range(len(sorted_events) - 1):
            current_end = sorted_events[i].end or sorted_events[i].start
            next_start = sorted_events[i + 1].start

            gap = next_start - current_end
            gap_hours = gap.total_seconds() / 3600

            # Identify focus blocks (gaps >= 2 hours during work hours)
            if gap_hours >= 2.0 and self._is_work_hours(current_end):
                focus_blocks.append(
                    FocusBlock(start=current_end, end=next_start, purpose="Deep Work")
                )

        return focus_blocks

    def _parse_datetime(self, value: Any) -> datetime:
        """Parse datetime from RDF literal."""
        if isinstance(value, Literal):
            return value.toPython()
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def _is_work_hours(self, dt: datetime) -> bool:
        """Check if datetime falls within work hours (8am-6pm weekdays)."""
        return (
            dt.weekday() < 5  # Monday-Friday
            and 8 <= dt.hour < 18  # 8am-6pm
        )

    def generate(self, template_name: str = "default.md") -> str:
        """Generate agenda artifact.

        Args:
            template_name: Template file name

        Returns
        -------
            Rendered markdown agenda
        """
        data = self.gather_data()
        self.validate_data(data, ["date", "events", "reminders"])
        return self.render_template(template_name, data)
