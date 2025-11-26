"""Tests for RDF converters."""

from datetime import UTC, datetime

from rdflib import RDF, XSD, Graph, Namespace

from kgcl.ingestion.config import RDFConfig
from kgcl.ingestion.converters import RDFConverter
from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock


class TestRDFConverter:
    """Tests for RDFConverter."""

    def test_initialization(self):
        """Test converter initialization."""
        config = RDFConfig()
        converter = RDFConverter(config)

        assert converter.base_ns == Namespace("http://kgcl.example.org/")
        assert converter.config.normalize_timestamps is True

    def test_convert_app_event(self):
        """Test converting app event to RDF."""
        config = RDFConfig()
        converter = RDFConverter(config)

        event = AppEvent(
            event_id="test_001",
            timestamp=datetime(2024, 11, 24, 10, 30, 0),
            app_name="com.apple.Safari",
            app_display_name="Safari",
            duration_seconds=120.5,
        )

        graph = converter.convert_event(event)

        assert len(graph) > 0
        assert isinstance(graph, Graph)

        # Check type assertion
        subjects = list(graph.subjects(RDF.type, converter.schema_ns.AppEvent))
        assert len(subjects) == 1

    def test_convert_browser_visit(self):
        """Test converting browser visit to RDF."""
        config = RDFConfig()
        converter = RDFConverter(config)

        event = BrowserVisit(
            event_id="test_001",
            timestamp=datetime(2024, 11, 24, 10, 30, 0),
            url="https://github.com/user/kgcl",
            domain="github.com",
            browser_name="Safari",
            title="GitHub Repository",
        )

        graph = converter.convert_event(event)

        # Check type assertion
        subjects = list(graph.subjects(RDF.type, converter.schema_ns.BrowserVisit))
        assert len(subjects) == 1

    def test_convert_calendar_block(self):
        """Test converting calendar block to RDF."""
        config = RDFConfig()
        converter = RDFConverter(config)

        event = CalendarBlock(
            event_id="test_001",
            timestamp=datetime(2024, 11, 24, 14, 0, 0),
            end_time=datetime(2024, 11, 24, 15, 0, 0),
            title="Team Meeting",
            attendees=["user1@example.com", "user2@example.com"],
        )

        graph = converter.convert_event(event)

        # Check type assertion
        subjects = list(graph.subjects(RDF.type, converter.schema_ns.CalendarBlock))
        assert len(subjects) == 1

    def test_timestamp_normalization(self):
        """Test timestamp normalization to UTC."""
        config = RDFConfig(normalize_timestamps=True)
        converter = RDFConverter(config)

        event = AppEvent(
            event_id="test_001", timestamp=datetime(2024, 11, 24, 10, 30, 0, tzinfo=UTC), app_name="com.apple.Safari"
        )

        graph = converter.convert_event(event)

        # Verify timestamp format includes Z suffix or +00:00
        timestamps = list(graph.objects(predicate=converter.schema_ns.timestamp))
        assert len(timestamps) > 0
        timestamp_str = str(timestamps[0])
        assert timestamp_str.endswith("Z") or timestamp_str.endswith("+00:00")

    def test_property_name_cleanup(self):
        """Test property name cleanup (snake_case to camelCase)."""
        config = RDFConfig(property_cleanup=True)
        converter = RDFConverter(config)

        # Check that _cleanup_property_name works
        assert converter._cleanup_property_name("app_name") == "appName"
        assert converter._cleanup_property_name("duration_seconds") == "durationSeconds"
        assert converter._cleanup_property_name("simple") == "simple"

    def test_namespace_binding(self):
        """Test namespace binding in graph."""
        config = RDFConfig()
        converter = RDFConverter(config)

        graph = Graph()
        converter._bind_namespaces(graph)

        # Check that namespaces are bound
        namespaces = dict(graph.namespaces())
        assert "kgcl" in namespaces
        assert "event" in namespaces
        assert "schema" in namespaces

    def test_convert_batch(self):
        """Test converting multiple events to single graph."""
        config = RDFConfig()
        converter = RDFConverter(config)

        events = [
            AppEvent(event_id="app_001", timestamp=datetime(2024, 11, 24, 10, 0, 0), app_name="com.apple.Safari"),
            BrowserVisit(
                event_id="browser_001",
                timestamp=datetime(2024, 11, 24, 10, 5, 0),
                url="https://example.com",
                domain="example.com",
                browser_name="Safari",
            ),
        ]

        graph = converter.convert_batch(events)

        # Should have triples for both events
        app_subjects = list(graph.subjects(RDF.type, converter.schema_ns.AppEvent))
        browser_subjects = list(graph.subjects(RDF.type, converter.schema_ns.BrowserVisit))

        assert len(app_subjects) == 1
        assert len(browser_subjects) == 1

    def test_auto_namespace_assignment(self):
        """Test automatic namespace assignment."""
        config = RDFConfig(auto_namespace_assignment=True)
        converter = RDFConverter(config)

        event = AppEvent(
            event_id="test with spaces", timestamp=datetime(2024, 11, 24, 10, 0, 0), app_name="com.apple.Safari"
        )

        graph = converter.convert_event(event)

        # Should handle special characters in URI
        assert len(graph) > 0

    def test_schema_version_inclusion(self):
        """Test schema version inclusion in RDF."""
        config = RDFConfig(include_schema_version=True)
        converter = RDFConverter(config)

        event = AppEvent(
            event_id="test_001",
            timestamp=datetime(2024, 11, 24, 10, 0, 0),
            app_name="com.apple.Safari",
            schema_version="1.0.0",
        )

        graph = converter.convert_event(event)

        # Check for schema version property
        versions = list(graph.objects(predicate=converter.schema_ns.schemaVersion))
        assert len(versions) > 0

    def test_optional_fields_not_added(self):
        """Test that None optional fields are not added to graph."""
        config = RDFConfig()
        converter = RDFConverter(config)

        event = AppEvent(
            event_id="test_001",
            timestamp=datetime(2024, 11, 24, 10, 0, 0),
            app_name="com.apple.Safari",
            # All optional fields left as None
        )

        graph = converter.convert_event(event)

        # Should have basic properties but not optional ones
        subjects = list(graph.subjects(RDF.type, converter.schema_ns.AppEvent))
        subject = subjects[0]

        # Check that optional properties are not present
        window_titles = list(graph.objects(subject, converter.schema_ns.windowTitle))
        assert len(window_titles) == 0

    def test_datatype_handling(self):
        """Test proper datatype handling for different value types."""
        config = RDFConfig(property_cleanup=False)
        converter = RDFConverter(config)

        graph = Graph()
        converter._bind_namespaces(graph)

        subject = converter.event_ns["test"]

        # Test integer
        converter._add_property(graph, subject, "count", 42, XSD.integer)
        values = list(graph.objects(subject, converter.schema_ns["count"]))
        assert len(values) == 1
        assert values[0].datatype == XSD.integer

        # Test double
        converter._add_property(graph, subject, "duration", 12.5, XSD.double)
        values = list(graph.objects(subject, converter.schema_ns["duration"]))
        assert len(values) == 1
        assert values[0].datatype == XSD.double

        # Test boolean
        converter._add_property(graph, subject, "flag", True, XSD.boolean)
        values = list(graph.objects(subject, converter.schema_ns["flag"]))
        assert len(values) == 1
        assert values[0].datatype == XSD.boolean
