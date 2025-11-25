"""RDF conversion for KGCL events.

Converts JSON events to RDF triples with automatic namespace assignment.
"""

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from rdflib import RDF, XSD, Graph, Literal, Namespace, URIRef

from kgcl.ingestion.config import RDFConfig
from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock


class RDFConverter:
    """Convert events to RDF triples.

    Features:
    - Automatic namespace assignment
    - Timestamp normalization to UTC
    - Property name cleanup
    - Schema version tracking
    """

    def __init__(self, config: RDFConfig) -> None:
        """Initialize RDF converter.

        Parameters
        ----------
        config : RDFConfig
            RDF conversion configuration
        """
        self.config = config
        self.base_ns = Namespace(config.base_namespace)

        # Define standard namespaces
        self.event_ns = Namespace(f"{config.base_namespace}event/")
        self.app_ns = Namespace(f"{config.base_namespace}app/")
        self.browser_ns = Namespace(f"{config.base_namespace}browser/")
        self.calendar_ns = Namespace(f"{config.base_namespace}calendar/")
        self.feature_ns = Namespace(f"{config.base_namespace}feature/")

        # Schema namespace
        self.schema_ns = Namespace(f"{config.base_namespace}schema/")

    def convert_event(
        self,
        event: AppEvent | BrowserVisit | CalendarBlock,
        graph: Graph | None = None,
    ) -> Graph:
        """Convert event to RDF graph.

        Parameters
        ----------
        event : AppEvent | BrowserVisit | CalendarBlock
            Event to convert
        graph : Graph, optional
            Existing graph to add to, creates new if None

        Returns
        -------
        Graph
            RDF graph with event triples
        """
        if graph is None:
            graph = Graph()
            self._bind_namespaces(graph)

        # Route to specific converter
        if isinstance(event, AppEvent):
            return self._convert_app_event(event, graph)
        elif isinstance(event, BrowserVisit):
            return self._convert_browser_visit(event, graph)
        elif isinstance(event, CalendarBlock):
            return self._convert_calendar_block(event, graph)
        else:
            msg = f"Unsupported event type: {type(event)}"
            raise TypeError(msg)

    def _convert_app_event(self, event: AppEvent, graph: Graph) -> Graph:
        """Convert AppEvent to RDF.

        Parameters
        ----------
        event : AppEvent
            Application event
        graph : Graph
            Target graph

        Returns
        -------
        Graph
            Updated graph
        """
        # Create event URI
        event_uri = self._create_uri(self.event_ns, event.event_id)

        # Type assertion
        graph.add((event_uri, RDF.type, self.schema_ns.AppEvent))

        # Add properties
        self._add_property(graph, event_uri, "eventId", event.event_id)
        self._add_timestamp(graph, event_uri, "timestamp", event.timestamp)
        self._add_property(graph, event_uri, "appName", event.app_name)

        if event.app_display_name:
            self._add_property(graph, event_uri, "appDisplayName", event.app_display_name)

        if event.window_title:
            self._add_property(graph, event_uri, "windowTitle", event.window_title)

        if event.duration_seconds is not None:
            self._add_property(
                graph,
                event_uri,
                "durationSeconds",
                event.duration_seconds,
                datatype=XSD.double,
            )

        if event.process_id is not None:
            self._add_property(
                graph,
                event_uri,
                "processId",
                event.process_id,
                datatype=XSD.integer,
            )

        if self.config.include_schema_version:
            self._add_property(graph, event_uri, "schemaVersion", event.schema_version)

        return graph

    def _convert_browser_visit(self, event: BrowserVisit, graph: Graph) -> Graph:
        """Convert BrowserVisit to RDF.

        Parameters
        ----------
        event : BrowserVisit
            Browser visit event
        graph : Graph
            Target graph

        Returns
        -------
        Graph
            Updated graph
        """
        # Create event URI
        event_uri = self._create_uri(self.event_ns, event.event_id)

        # Type assertion
        graph.add((event_uri, RDF.type, self.schema_ns.BrowserVisit))

        # Add properties
        self._add_property(graph, event_uri, "eventId", event.event_id)
        self._add_timestamp(graph, event_uri, "timestamp", event.timestamp)
        self._add_property(graph, event_uri, "url", event.url, datatype=XSD.anyURI)
        self._add_property(graph, event_uri, "domain", event.domain)
        self._add_property(graph, event_uri, "browserName", event.browser_name)

        if event.title:
            self._add_property(graph, event_uri, "title", event.title)

        if event.duration_seconds is not None:
            self._add_property(
                graph,
                event_uri,
                "durationSeconds",
                event.duration_seconds,
                datatype=XSD.double,
            )

        if event.referrer:
            self._add_property(graph, event_uri, "referrer", event.referrer, datatype=XSD.anyURI)

        if event.tab_id:
            self._add_property(graph, event_uri, "tabId", event.tab_id)

        if self.config.include_schema_version:
            self._add_property(graph, event_uri, "schemaVersion", event.schema_version)

        return graph

    def _convert_calendar_block(self, event: CalendarBlock, graph: Graph) -> Graph:
        """Convert CalendarBlock to RDF.

        Parameters
        ----------
        event : CalendarBlock
            Calendar event
        graph : Graph
            Target graph

        Returns
        -------
        Graph
            Updated graph
        """
        # Create event URI
        event_uri = self._create_uri(self.event_ns, event.event_id)

        # Type assertion
        graph.add((event_uri, RDF.type, self.schema_ns.CalendarBlock))

        # Add properties
        self._add_property(graph, event_uri, "eventId", event.event_id)
        self._add_timestamp(graph, event_uri, "timestamp", event.timestamp)
        self._add_timestamp(graph, event_uri, "endTime", event.end_time)
        self._add_property(graph, event_uri, "title", event.title)

        if event.description:
            self._add_property(graph, event_uri, "description", event.description)

        if event.location:
            self._add_property(graph, event_uri, "location", event.location)

        if event.organizer:
            self._add_property(graph, event_uri, "organizer", event.organizer)

        if event.calendar_name:
            self._add_property(graph, event_uri, "calendarName", event.calendar_name)

        self._add_property(
            graph,
            event_uri,
            "isAllDay",
            event.is_all_day,
            datatype=XSD.boolean,
        )

        # Add attendees as list
        for attendee in event.attendees:
            self._add_property(graph, event_uri, "attendee", attendee)

        if self.config.include_schema_version:
            self._add_property(graph, event_uri, "schemaVersion", event.schema_version)

        return graph

    def _create_uri(self, namespace: Namespace, identifier: str) -> URIRef:
        """Create URI with namespace.

        Parameters
        ----------
        namespace : Namespace
            RDF namespace
        identifier : str
            Entity identifier

        Returns
        -------
        URIRef
            Complete URI reference
        """
        if self.config.auto_namespace_assignment:
            # URL-encode identifier for safety
            safe_id = quote(identifier, safe="")
            return namespace[safe_id]
        return URIRef(f"{namespace}{identifier}")

    def _add_property(
        self,
        graph: Graph,
        subject: URIRef,
        predicate: str,
        value: Any,
        datatype: URIRef | None = None,
    ) -> None:
        """Add property triple to graph.

        Parameters
        ----------
        graph : Graph
            Target graph
        subject : URIRef
            Subject URI
        predicate : str
            Property name
        value : Any
            Property value
        datatype : URIRef, optional
            XSD datatype
        """
        # Cleanup property name if enabled
        if self.config.property_cleanup:
            predicate = self._cleanup_property_name(predicate)

        pred_uri = self.schema_ns[predicate]

        # Handle None values
        if value is None:
            return

        # Create literal with appropriate datatype
        if datatype:
            obj = Literal(value, datatype=datatype)
        elif isinstance(value, bool):
            obj = Literal(value, datatype=XSD.boolean)
        elif isinstance(value, int):
            obj = Literal(value, datatype=XSD.integer)
        elif isinstance(value, float):
            obj = Literal(value, datatype=XSD.double)
        else:
            obj = Literal(str(value))

        graph.add((subject, pred_uri, obj))

    def _add_timestamp(
        self,
        graph: Graph,
        subject: URIRef,
        predicate: str,
        timestamp: datetime,
    ) -> None:
        """Add timestamp property.

        Parameters
        ----------
        graph : Graph
            Target graph
        subject : URIRef
            Subject URI
        predicate : str
            Property name
        timestamp : datetime
            Timestamp value
        """
        # Normalize to UTC if enabled
        if self.config.normalize_timestamps:
            if timestamp.tzinfo is not None:
                timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)

        # Format as ISO8601
        iso_str = timestamp.isoformat() + "Z"
        self._add_property(graph, subject, predicate, iso_str, datatype=XSD.dateTime)

    def _cleanup_property_name(self, name: str) -> str:
        """Clean and normalize property name.

        Parameters
        ----------
        name : str
            Original property name

        Returns
        -------
        str
            Cleaned property name
        """
        # Convert snake_case to camelCase
        parts = name.split("_")
        if len(parts) == 1:
            return name

        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    def _bind_namespaces(self, graph: Graph) -> None:
        """Bind standard namespaces to graph.

        Parameters
        ----------
        graph : Graph
            Graph to bind namespaces
        """
        graph.bind("kgcl", self.base_ns)
        graph.bind("event", self.event_ns)
        graph.bind("app", self.app_ns)
        graph.bind("browser", self.browser_ns)
        graph.bind("calendar", self.calendar_ns)
        graph.bind("feature", self.feature_ns)
        graph.bind("schema", self.schema_ns)

    def convert_batch(
        self,
        events: list[AppEvent | BrowserVisit | CalendarBlock],
    ) -> Graph:
        """Convert multiple events to single graph.

        Parameters
        ----------
        events : list[AppEvent | BrowserVisit | CalendarBlock]
            Events to convert

        Returns
        -------
        Graph
            Combined RDF graph
        """
        graph = Graph()
        self._bind_namespaces(graph)

        for event in events:
            self.convert_event(event, graph)

        return graph
