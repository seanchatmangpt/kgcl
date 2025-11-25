"""Conflict report generator for detecting scheduling and resource conflicts.

Detects overlapping calendar events, resource conflicts, and suggests
resolutions for optimal scheduling.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from rdflib import Graph, Namespace
from rdflib.namespace import RDF, RDFS

from .base import ProjectionGenerator


# Define namespaces
KGC = Namespace("http://example.org/kgc/")
ICAL = Namespace("http://www.w3.org/2002/12/cal/ical#")


@dataclass
class TimeConflict:
    """Domain object for overlapping time conflicts."""

    event1_uri: str
    event1_title: str
    event1_start: datetime
    event1_end: datetime
    event2_uri: str
    event2_title: str
    event2_start: datetime
    event2_end: datetime
    overlap_minutes: int = 0

    def calculate_overlap(self) -> int:
        """Calculate overlap duration in minutes."""
        overlap_start = max(self.event1_start, self.event2_start)
        overlap_end = min(self.event1_end, self.event2_end)
        delta = overlap_end - overlap_start
        return int(delta.total_seconds() / 60)


@dataclass
class ResourceConflict:
    """Domain object for resource allocation conflicts."""

    resource_uri: str
    resource_name: str
    events: List[str] = field(default_factory=list)
    conflict_time: Optional[datetime] = None

    def event_count(self) -> int:
        """Count number of conflicting events."""
        return len(self.events)


@dataclass
class ConflictResolution:
    """Domain object for suggested conflict resolutions."""

    conflict_type: str  # "time" or "resource"
    suggestion: str
    priority: int = 3  # 1=high, 3=normal, 5=low
    estimated_impact: str = "medium"  # "high", "medium", "low"


class ConflictReportGenerator(ProjectionGenerator):
    """Generate conflict reports for scheduling and resources.

    Detects:
    - Overlapping calendar events
    - Double-booked resources
    - Meeting conflicts

    Suggests resolutions for optimal scheduling.
    """

    def __init__(self, graph: Graph, lookahead_days: int = 7) -> None:
        """Initialize conflict report generator.

        Args:
            graph: RDF graph containing calendar and resource data
            lookahead_days: Number of days to check for conflicts
        """
        super().__init__(graph)
        self.lookahead_days = lookahead_days
        self.start_date = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def gather_data(self) -> Dict[str, Any]:
        """Gather conflicts from RDF graph.

        Returns:
            Dictionary with time conflicts, resource conflicts, and resolutions
        """
        events = self._query_events()
        time_conflicts = self._detect_time_conflicts(events)
        resource_conflicts = self._detect_resource_conflicts()
        resolutions = self._generate_resolutions(time_conflicts, resource_conflicts)

        return {
            "date_range": {
                "start": self.start_date,
                "end": self.start_date + timedelta(days=self.lookahead_days)
            },
            "total_conflicts": len(time_conflicts) + len(resource_conflicts),
            "time_conflicts": time_conflicts,
            "resource_conflicts": resource_conflicts,
            "resolutions": resolutions,
        }

    def _query_events(self) -> List[Dict[str, Any]]:
        """Query RDF graph for calendar events."""
        events = []

        query = f"""
        PREFIX kgc: <{KGC}>
        PREFIX ical: <{ICAL}>

        SELECT ?event ?title ?start ?end ?location ?attendees
        WHERE {{
            ?event a ical:Vevent .
            ?event ical:dtstart ?start .
            ?event ical:summary ?title .
            OPTIONAL {{ ?event ical:dtend ?end }}
            OPTIONAL {{ ?event ical:location ?location }}
            OPTIONAL {{ ?event ical:attendee ?attendees }}
        }}
        """

        results = self.graph.query(query)
        end_range = self.start_date + timedelta(days=self.lookahead_days)

        for row in results:
            start_dt = self._parse_datetime(row.start)
            end_dt = self._parse_datetime(row.end) if row.end else start_dt + timedelta(hours=1)

            # Filter events within date range
            if start_dt < self.start_date or start_dt > end_range:
                continue

            events.append({
                "uri": str(row.event),
                "title": str(row.title),
                "start": start_dt,
                "end": end_dt,
                "location": str(row.location) if row.location else "",
                "attendees": self._parse_attendees(row.attendees) if row.attendees else []
            })

        return events

    def _detect_time_conflicts(self, events: List[Dict[str, Any]]) -> List[TimeConflict]:
        """Detect overlapping time conflicts in events."""
        conflicts = []

        # Sort events by start time
        sorted_events = sorted(events, key=lambda e: e["start"])

        for i in range(len(sorted_events)):
            for j in range(i + 1, len(sorted_events)):
                event1 = sorted_events[i]
                event2 = sorted_events[j]

                # Check if events overlap
                if self._events_overlap(event1, event2):
                    conflict = TimeConflict(
                        event1_uri=event1["uri"],
                        event1_title=event1["title"],
                        event1_start=event1["start"],
                        event1_end=event1["end"],
                        event2_uri=event2["uri"],
                        event2_title=event2["title"],
                        event2_start=event2["start"],
                        event2_end=event2["end"]
                    )
                    conflict.overlap_minutes = conflict.calculate_overlap()
                    conflicts.append(conflict)

        return conflicts

    def _detect_resource_conflicts(self) -> List[ResourceConflict]:
        """Detect resource allocation conflicts."""
        conflicts = []

        query = f"""
        PREFIX kgc: <{KGC}>
        PREFIX ical: <{ICAL}>

        SELECT ?resource ?resourceName ?event ?start ?end
        WHERE {{
            ?event a ical:Vevent .
            ?event ical:dtstart ?start .
            ?event ical:dtend ?end .
            ?event kgc:requiresResource ?resource .
            ?resource rdfs:label ?resourceName .
        }}
        """

        results = self.graph.query(query)

        # Group events by resource
        resource_events: Dict[str, List[Dict[str, Any]]] = {}
        end_range = self.start_date + timedelta(days=self.lookahead_days)

        for row in results:
            start_dt = self._parse_datetime(row.start)
            if start_dt < self.start_date or start_dt > end_range:
                continue

            resource_uri = str(row.resource)
            if resource_uri not in resource_events:
                resource_events[resource_uri] = []

            resource_events[resource_uri].append({
                "uri": str(row.event),
                "start": start_dt,
                "end": self._parse_datetime(row.end) if row.end else start_dt,
                "resource_name": str(row.resourceName)
            })

        # Check for overlapping usage
        for resource_uri, events in resource_events.items():
            sorted_events = sorted(events, key=lambda e: e["start"])

            for i in range(len(sorted_events)):
                for j in range(i + 1, len(sorted_events)):
                    event1 = sorted_events[i]
                    event2 = sorted_events[j]

                    if self._events_overlap(event1, event2):
                        conflicts.append(ResourceConflict(
                            resource_uri=resource_uri,
                            resource_name=event1["resource_name"],
                            events=[event1["uri"], event2["uri"]],
                            conflict_time=max(event1["start"], event2["start"])
                        ))

        return conflicts

    def _generate_resolutions(
        self,
        time_conflicts: List[TimeConflict],
        resource_conflicts: List[ResourceConflict]
    ) -> List[ConflictResolution]:
        """Generate suggested resolutions for conflicts."""
        resolutions = []

        for conflict in time_conflicts:
            resolutions.append(ConflictResolution(
                conflict_type="time",
                suggestion=f"Reschedule '{conflict.event2_title}' to avoid overlap with '{conflict.event1_title}'",
                priority=1 if conflict.overlap_minutes > 30 else 3,
                estimated_impact="high" if conflict.overlap_minutes > 60 else "medium"
            ))

        for conflict in resource_conflicts:
            resolutions.append(ConflictResolution(
                conflict_type="resource",
                suggestion=f"Find alternative resource for {conflict.resource_name} or reschedule one event",
                priority=2,
                estimated_impact="medium"
            ))

        return sorted(resolutions, key=lambda r: r.priority)

    def _events_overlap(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> bool:
        """Check if two events overlap in time."""
        return (
            event1["start"] < event2["end"] and
            event2["start"] < event1["end"]
        )

    def _parse_datetime(self, value: Any) -> datetime:
        """Parse datetime from RDF literal."""
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def _parse_attendees(self, attendees: Any) -> List[str]:
        """Parse attendees from RDF."""
        if isinstance(attendees, str):
            return [attendees]
        return []

    def generate(self, template_name: str = "default.md") -> str:
        """Generate conflict report artifact.

        Args:
            template_name: Template file name

        Returns:
            Rendered markdown conflict report
        """
        data = self.gather_data()
        self.validate_data(data, ["total_conflicts", "time_conflicts"])
        return self.render_template(template_name, data)
