"""Tests for XES event log exporter (IEEE 1849-2016 compliance)."""

from __future__ import annotations

import tempfile
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import pytest

from kgcl.hybrid.temporal.adapters.xes_exporter import (
    LifecycleTransition,
    XESAttribute,
    XESEvent,
    XESExporter,
    XESLog,
    XESTrace,
    create_xes_exporter,
)
from kgcl.hybrid.temporal.domain.event import EventType, WorkflowEvent


class TestLifecycleTransition:
    """Test XES lifecycle transition enum."""

    def test_lifecycle_transitions_are_strings(self) -> None:
        """Lifecycle transitions have correct string values."""
        assert LifecycleTransition.START.value == "start"
        assert LifecycleTransition.COMPLETE.value == "complete"
        assert LifecycleTransition.ATE_ABORT.value == "ate_abort"
        assert LifecycleTransition.SCHEDULE.value == "schedule"

    def test_all_transitions_defined(self) -> None:
        """All IEEE 1849-2016 lifecycle transitions are defined."""
        expected = {
            "schedule",
            "assign",
            "reassign",
            "start",
            "suspend",
            "resume",
            "complete",
            "ate_abort",
            "pi_abort",
            "withdraw",
            "manualskip",
            "autoskip",
        }
        actual = {t.value for t in LifecycleTransition}
        assert actual == expected


class TestXESAttribute:
    """Test XES attribute data structure."""

    def test_create_string_attribute(self) -> None:
        """Create string attribute with default type."""
        attr = XESAttribute(key="concept:name", value="Task_A")
        assert attr.key == "concept:name"
        assert attr.value == "Task_A"
        assert attr.attr_type == "string"

    def test_create_int_attribute(self) -> None:
        """Create integer attribute with explicit type."""
        attr = XESAttribute(key="tick:number", value=42, attr_type="int")
        assert attr.key == "tick:number"
        assert attr.value == 42
        assert attr.attr_type == "int"

    def test_attribute_is_immutable(self) -> None:
        """XESAttribute is frozen dataclass."""
        attr = XESAttribute(key="test", value="value")
        with pytest.raises(AttributeError):
            attr.key = "modified"  # type: ignore[misc]


class TestXESEvent:
    """Test XES event data structure."""

    def test_create_minimal_event(self) -> None:
        """Create event with minimal required fields."""
        timestamp = datetime.now(UTC)
        event = XESEvent(concept_name="Task_A", timestamp=timestamp)

        assert event.concept_name == "Task_A"
        assert event.timestamp == timestamp
        assert event.lifecycle == LifecycleTransition.COMPLETE
        assert event.resource is None
        assert event.attributes == ()

    def test_create_full_event(self) -> None:
        """Create event with all fields populated."""
        timestamp = datetime.now(UTC)
        attrs = (
            XESAttribute(key="event:id", value="evt-123"),
            XESAttribute(key="tick:number", value=5, attr_type="int"),
        )

        event = XESEvent(
            concept_name="Task_B",
            timestamp=timestamp,
            lifecycle=LifecycleTransition.START,
            resource="worker-1",
            attributes=attrs,
        )

        assert event.concept_name == "Task_B"
        assert event.lifecycle == LifecycleTransition.START
        assert event.resource == "worker-1"
        assert len(event.attributes) == 2

    def test_event_is_immutable(self) -> None:
        """XESEvent is frozen dataclass."""
        event = XESEvent(concept_name="Task_A", timestamp=datetime.now(UTC))
        with pytest.raises(AttributeError):
            event.concept_name = "modified"  # type: ignore[misc]


class TestXESTrace:
    """Test XES trace data structure."""

    def test_create_trace_with_events(self) -> None:
        """Create trace with multiple events."""
        ts = datetime.now(UTC)
        events = (
            XESEvent(concept_name="Task_A", timestamp=ts),
            XESEvent(concept_name="Task_B", timestamp=ts, lifecycle=LifecycleTransition.START),
        )

        trace = XESTrace(case_id="case-001", events=events)

        assert trace.case_id == "case-001"
        assert len(trace.events) == 2
        assert trace.events[0].concept_name == "Task_A"
        assert trace.events[1].concept_name == "Task_B"

    def test_trace_is_immutable(self) -> None:
        """XESTrace is frozen dataclass."""
        trace = XESTrace(case_id="case-001", events=())
        with pytest.raises(AttributeError):
            trace.case_id = "modified"  # type: ignore[misc]


class TestXESLog:
    """Test XES log data structure."""

    def test_create_log_with_default_extensions(self) -> None:
        """Log includes standard XES extensions by default."""
        log = XESLog(traces=())

        assert "Concept" in log.extensions
        assert "Time" in log.extensions
        assert "Lifecycle" in log.extensions
        assert "Organizational" in log.extensions

    def test_create_log_with_custom_extensions(self) -> None:
        """Log can have custom extensions."""
        log = XESLog(traces=(), extensions=("Concept", "Time", "Custom"))

        assert len(log.extensions) == 3
        assert "Custom" in log.extensions

    def test_log_has_default_classifier(self) -> None:
        """Log has Activity classifier by default."""
        log = XESLog(traces=())

        assert len(log.classifiers) == 1
        assert log.classifiers[0] == ("Activity", "concept:name")


class TestXESExporter:
    """Test XES exporter conversion logic."""

    def test_exporter_initialization(self) -> None:
        """Exporter initializes with correct namespace."""
        exporter = XESExporter()
        assert exporter._ns == "http://www.xes-standard.org/"

    def test_event_type_to_lifecycle_mapping(self) -> None:
        """All KGCL EventTypes map to XES lifecycle transitions."""
        exporter = XESExporter()

        # Test key mappings
        assert exporter.EVENT_TYPE_TO_LIFECYCLE["TICK_START"] == LifecycleTransition.START
        assert exporter.EVENT_TYPE_TO_LIFECYCLE["TICK_END"] == LifecycleTransition.COMPLETE
        assert exporter.EVENT_TYPE_TO_LIFECYCLE["CANCELLATION"] == LifecycleTransition.ATE_ABORT
        assert exporter.EVENT_TYPE_TO_LIFECYCLE["MI_SPAWN"] == LifecycleTransition.START
        assert exporter.EVENT_TYPE_TO_LIFECYCLE["MI_COMPLETE"] == LifecycleTransition.COMPLETE

    def test_convert_workflow_event_to_xes_event(self) -> None:
        """Convert WorkflowEvent to XESEvent."""
        exporter = XESExporter()
        workflow_event = WorkflowEvent.create(
            event_type=EventType.STATUS_CHANGE,
            workflow_id="wf-001",
            tick_number=10,
            payload={"activity": "Process_Order", "resource": "order-service", "status": "completed"},
        )

        xes_event = exporter.convert_event(workflow_event)

        assert xes_event.concept_name == "Process_Order"
        assert xes_event.resource == "order-service"
        assert xes_event.lifecycle == LifecycleTransition.COMPLETE
        assert xes_event.timestamp == workflow_event.timestamp

        # Check attributes
        attr_keys = {attr.key for attr in xes_event.attributes}
        assert "event:id" in attr_keys
        assert "tick:number" in attr_keys
        assert "event:hash" in attr_keys
        assert "status" in attr_keys

    def test_convert_event_with_default_activity_name(self) -> None:
        """Use event type as activity name when not in payload."""
        exporter = XESExporter()
        workflow_event = WorkflowEvent.create(
            event_type=EventType.TOKEN_MOVE, workflow_id="wf-001", tick_number=5, payload={"from": "A", "to": "B"}
        )

        xes_event = exporter.convert_event(workflow_event)

        assert xes_event.concept_name == "TOKEN_MOVE"

    def test_convert_event_with_causal_dependencies(self) -> None:
        """Convert event with causal dependencies."""
        exporter = XESExporter()
        workflow_event = WorkflowEvent.create(
            event_type=EventType.JOIN,
            workflow_id="wf-001",
            tick_number=15,
            payload={"activity": "Join_Gateway"},
            caused_by=("evt-1", "evt-2", "evt-3"),
        )

        xes_event = exporter.convert_event(workflow_event)

        # Find caused_by attribute
        caused_by_attr = next((a for a in xes_event.attributes if a.key == "event:caused_by"), None)
        assert caused_by_attr is not None
        assert caused_by_attr.value == "evt-1,evt-2,evt-3"

    def test_convert_event_with_vector_clock(self) -> None:
        """Convert event with vector clock."""
        exporter = XESExporter()
        workflow_event = WorkflowEvent.create(
            event_type=EventType.SPLIT,
            workflow_id="wf-001",
            tick_number=8,
            payload={"activity": "Split_Gateway"},
            vector_clock=(("node-1", 5), ("node-2", 3)),
        )

        xes_event = exporter.convert_event(workflow_event)

        # Find vector_clock attribute
        vc_attr = next((a for a in xes_event.attributes if a.key == "event:vector_clock"), None)
        assert vc_attr is not None
        assert vc_attr.value == "node-1:5;node-2:3"

    def test_lifecycle_transition_for_all_event_types(self) -> None:
        """All EventTypes map to a lifecycle transition."""
        exporter = XESExporter()

        for event_type in EventType:
            workflow_event = WorkflowEvent.create(
                event_type=event_type, workflow_id="wf-001", tick_number=1, payload={}
            )

            xes_event = exporter.convert_event(workflow_event)

            # Should have a valid lifecycle (default is COMPLETE)
            assert xes_event.lifecycle in LifecycleTransition

    def test_convert_trace(self) -> None:
        """Convert workflow events to XES trace."""
        exporter = XESExporter()

        events = [
            WorkflowEvent.create(
                event_type=EventType.TICK_START, workflow_id="wf-001", tick_number=1, payload={"activity": "Start"}
            ),
            WorkflowEvent.create(
                event_type=EventType.STATUS_CHANGE, workflow_id="wf-001", tick_number=2, payload={"activity": "Task_A"}
            ),
            WorkflowEvent.create(
                event_type=EventType.TICK_END, workflow_id="wf-001", tick_number=3, payload={"activity": "End"}
            ),
        ]

        trace = exporter.convert_trace("wf-001", events)

        assert trace.case_id == "wf-001"
        assert len(trace.events) == 3
        assert trace.events[0].concept_name == "Start"
        assert trace.events[1].concept_name == "Task_A"
        assert trace.events[2].concept_name == "End"

    def test_convert_log_with_multiple_traces(self) -> None:
        """Convert multiple workflow traces to XES log."""
        exporter = XESExporter()

        trace1_events = [
            WorkflowEvent.create(
                event_type=EventType.STATUS_CHANGE, workflow_id="wf-001", tick_number=1, payload={"activity": "A"}
            )
        ]

        trace2_events = [
            WorkflowEvent.create(
                event_type=EventType.STATUS_CHANGE, workflow_id="wf-002", tick_number=1, payload={"activity": "B"}
            )
        ]

        traces = [("wf-001", trace1_events), ("wf-002", trace2_events)]

        log = exporter.convert_log(traces)

        assert len(log.traces) == 2
        assert log.traces[0].case_id == "wf-001"
        assert log.traces[1].case_id == "wf-002"

    def test_infer_type_for_boolean(self) -> None:
        """Infer XES type for boolean value."""
        exporter = XESExporter()
        assert exporter._infer_type(True) == "boolean"
        assert exporter._infer_type(False) == "boolean"

    def test_infer_type_for_int(self) -> None:
        """Infer XES type for integer value."""
        exporter = XESExporter()
        assert exporter._infer_type(42) == "int"
        assert exporter._infer_type(0) == "int"
        assert exporter._infer_type(-100) == "int"

    def test_infer_type_for_float(self) -> None:
        """Infer XES type for float value."""
        exporter = XESExporter()
        assert exporter._infer_type(3.14) == "float"
        assert exporter._infer_type(0.0) == "float"

    def test_infer_type_for_datetime(self) -> None:
        """Infer XES type for datetime value."""
        exporter = XESExporter()
        assert exporter._infer_type(datetime.now(UTC)) == "date"

    def test_infer_type_for_string(self) -> None:
        """Infer XES type for string value."""
        exporter = XESExporter()
        assert exporter._infer_type("test") == "string"
        assert exporter._infer_type("") == "string"

    def test_infer_type_for_other_types(self) -> None:
        """Other types default to string."""
        exporter = XESExporter()
        assert exporter._infer_type([1, 2, 3]) == "string"
        assert exporter._infer_type({"key": "value"}) == "string"
        assert exporter._infer_type(None) == "string"


class TestXMLGeneration:
    """Test XML output generation."""

    def test_to_xml_includes_required_root_attributes(self) -> None:
        """XML root has xes.version and xmlns."""
        exporter = XESExporter()
        log = XESLog(traces=())

        xml_str = exporter.to_xml(log, pretty=False)
        root = ET.fromstring(xml_str)

        # Tag includes namespace, check local name
        assert root.tag.endswith("log")
        assert root.get("xes.version") == "1849.2016"
        # Namespace is embedded in tag when default namespace is used
        assert "http://www.xes-standard.org/" in root.tag

    def test_to_xml_includes_extensions(self) -> None:
        """XML includes all specified extensions."""
        exporter = XESExporter()
        log = XESLog(traces=(), extensions=("Concept", "Time", "Lifecycle"))

        xml_str = exporter.to_xml(log, pretty=False)
        root = ET.fromstring(xml_str)

        # Use namespace in find
        ns = {"xes": "http://www.xes-standard.org/"}
        extensions = root.findall("xes:extension", ns)
        assert len(extensions) == 3

        ext_names = {ext.get("name") for ext in extensions}
        assert ext_names == {"Concept", "Time", "Lifecycle"}

    def test_to_xml_includes_classifiers(self) -> None:
        """XML includes classifiers."""
        exporter = XESExporter()
        log = XESLog(traces=(), classifiers=(("Activity", "concept:name"), ("Resource", "org:resource")))

        xml_str = exporter.to_xml(log, pretty=False)
        root = ET.fromstring(xml_str)

        ns = {"xes": "http://www.xes-standard.org/"}
        classifiers = root.findall("xes:classifier", ns)
        assert len(classifiers) == 2

    def test_to_xml_includes_global_event_scope(self) -> None:
        """XML includes global event scope."""
        exporter = XESExporter()
        log = XESLog(traces=())

        xml_str = exporter.to_xml(log, pretty=False)
        root = ET.fromstring(xml_str)

        ns = {"xes": "http://www.xes-standard.org/"}
        global_elements = root.findall("xes:global", ns)
        global_event = next((g for g in global_elements if g.get("scope") == "event"), None)

        assert global_event is not None

    def test_to_xml_includes_traces(self) -> None:
        """XML includes all traces."""
        exporter = XESExporter()
        ts = datetime.now(UTC)

        trace1 = XESTrace(case_id="case-001", events=(XESEvent(concept_name="Task_A", timestamp=ts),))
        trace2 = XESTrace(case_id="case-002", events=(XESEvent(concept_name="Task_B", timestamp=ts),))

        log = XESLog(traces=(trace1, trace2))

        xml_str = exporter.to_xml(log, pretty=False)
        root = ET.fromstring(xml_str)

        ns = {"xes": "http://www.xes-standard.org/"}
        traces = root.findall("xes:trace", ns)
        assert len(traces) == 2

    def test_to_xml_trace_has_concept_name(self) -> None:
        """Each trace has concept:name attribute."""
        exporter = XESExporter()
        ts = datetime.now(UTC)

        trace = XESTrace(case_id="case-001", events=(XESEvent(concept_name="Task_A", timestamp=ts),))
        log = XESLog(traces=(trace,))

        xml_str = exporter.to_xml(log, pretty=False)
        root = ET.fromstring(xml_str)

        ns = {"xes": "http://www.xes-standard.org/"}
        trace_elem = root.find("xes:trace", ns)
        assert trace_elem is not None

        concept_name = trace_elem.find("xes:string[@key='concept:name']", ns)
        assert concept_name is not None
        assert concept_name.get("value") == "case-001"

    def test_to_xml_event_has_required_attributes(self) -> None:
        """Each event has concept:name, timestamp, lifecycle."""
        exporter = XESExporter()
        ts = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        event = XESEvent(concept_name="Task_A", timestamp=ts, lifecycle=LifecycleTransition.COMPLETE)
        trace = XESTrace(case_id="case-001", events=(event,))
        log = XESLog(traces=(trace,))

        xml_str = exporter.to_xml(log, pretty=False)
        root = ET.fromstring(xml_str)

        ns = {"xes": "http://www.xes-standard.org/"}
        event_elem = root.find(".//xes:event", ns)
        assert event_elem is not None

        concept_name = event_elem.find("xes:string[@key='concept:name']", ns)
        assert concept_name is not None
        assert concept_name.get("value") == "Task_A"

        timestamp = event_elem.find("xes:date[@key='time:timestamp']", ns)
        assert timestamp is not None
        assert timestamp.get("value") == ts.isoformat()

        lifecycle = event_elem.find("xes:string[@key='lifecycle:transition']", ns)
        assert lifecycle is not None
        assert lifecycle.get("value") == "complete"

    def test_to_xml_event_includes_resource(self) -> None:
        """Event includes org:resource when present."""
        exporter = XESExporter()
        ts = datetime.now(UTC)

        event = XESEvent(concept_name="Task_A", timestamp=ts, resource="worker-1")
        trace = XESTrace(case_id="case-001", events=(event,))
        log = XESLog(traces=(trace,))

        xml_str = exporter.to_xml(log, pretty=False)
        root = ET.fromstring(xml_str)

        ns = {"xes": "http://www.xes-standard.org/"}
        resource_elem = root.find(".//xes:string[@key='org:resource']", ns)
        assert resource_elem is not None
        assert resource_elem.get("value") == "worker-1"

    def test_to_xml_event_includes_custom_attributes(self) -> None:
        """Event includes custom attributes."""
        exporter = XESExporter()
        ts = datetime.now(UTC)

        attrs = (
            XESAttribute(key="custom:field", value="test_value"),
            XESAttribute(key="custom:count", value=42, attr_type="int"),
        )
        event = XESEvent(concept_name="Task_A", timestamp=ts, attributes=attrs)
        trace = XESTrace(case_id="case-001", events=(event,))
        log = XESLog(traces=(trace,))

        xml_str = exporter.to_xml(log, pretty=False)
        root = ET.fromstring(xml_str)

        ns = {"xes": "http://www.xes-standard.org/"}
        custom_field = root.find(".//xes:string[@key='custom:field']", ns)
        assert custom_field is not None
        assert custom_field.get("value") == "test_value"

        custom_count = root.find(".//xes:int[@key='custom:count']", ns)
        assert custom_count is not None
        assert custom_count.get("value") == "42"

    def test_to_xml_pretty_print(self) -> None:
        """Pretty print adds indentation and newlines."""
        exporter = XESExporter()
        log = XESLog(traces=())

        xml_pretty = exporter.to_xml(log, pretty=True)
        xml_compact = exporter.to_xml(log, pretty=False)

        # Pretty version should be longer (indentation + newlines)
        assert len(xml_pretty) > len(xml_compact)
        assert "\n" in xml_pretty
        assert "  " in xml_pretty  # Indentation

    def test_to_xml_compact_format(self) -> None:
        """Compact format has no extra whitespace."""
        exporter = XESExporter()
        log = XESLog(traces=())

        xml_compact = exporter.to_xml(log, pretty=False)

        # Should not have indentation (multiple spaces)
        assert "  " not in xml_compact


class TestFileExport:
    """Test file export functionality."""

    def test_export_to_file_creates_file(self) -> None:
        """Export creates file at specified path."""
        exporter = XESExporter()
        log = XESLog(traces=())

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xes") as f:
            filepath = f.name

        try:
            exporter.export_to_file(log, filepath)

            # File should exist
            assert Path(filepath).exists()

            # Should be valid XML
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
                root = ET.fromstring(content)
                assert root.tag.endswith("log")
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_to_file_with_pretty_print(self) -> None:
        """Export with pretty print creates formatted file."""
        exporter = XESExporter()
        ts = datetime.now(UTC)

        event = XESEvent(concept_name="Task_A", timestamp=ts)
        trace = XESTrace(case_id="case-001", events=(event,))
        log = XESLog(traces=(trace,))

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xes") as f:
            filepath = f.name

        try:
            exporter.export_to_file(log, filepath, pretty=True)

            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            # Should have indentation
            assert "  <trace>" in content or "\n  " in content
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_to_file_compact(self) -> None:
        """Export without pretty print creates compact file."""
        exporter = XESExporter()
        log = XESLog(traces=())

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xes") as f:
            filepath = f.name

        try:
            exporter.export_to_file(log, filepath, pretty=False)

            with open(filepath, encoding="utf-8") as f:
                content = f.read()

            # Should not have multiple spaces (indentation)
            lines = content.split("\n")
            # Compact XML should be mostly one line (after XML declaration)
            assert len([line for line in lines if line.strip()]) <= 3
        finally:
            Path(filepath).unlink(missing_ok=True)


class TestFactory:
    """Test factory function."""

    def test_create_xes_exporter(self) -> None:
        """Factory creates XESExporter instance."""
        exporter = create_xes_exporter()

        assert isinstance(exporter, XESExporter)
        assert exporter._ns == "http://www.xes-standard.org/"


class TestEndToEndConversion:
    """End-to-end conversion tests."""

    def test_full_workflow_to_xes_export(self) -> None:
        """Complete workflow: WorkflowEvent -> XES -> XML file."""
        exporter = XESExporter()

        # Create workflow events
        events = [
            WorkflowEvent.create(
                event_type=EventType.TICK_START,
                workflow_id="order-001",
                tick_number=1,
                payload={"activity": "Start", "resource": "system"},
            ),
            WorkflowEvent.create(
                event_type=EventType.STATUS_CHANGE,
                workflow_id="order-001",
                tick_number=2,
                payload={"activity": "Validate_Order", "resource": "validation-service", "status": "completed"},
            ),
            WorkflowEvent.create(
                event_type=EventType.MI_SPAWN,
                workflow_id="order-001",
                tick_number=3,
                payload={"activity": "Process_Items", "resource": "worker-1", "instance_count": 3},
            ),
            WorkflowEvent.create(
                event_type=EventType.MI_COMPLETE,
                workflow_id="order-001",
                tick_number=4,
                payload={"activity": "Process_Items", "resource": "worker-1", "completed_count": 3},
            ),
            WorkflowEvent.create(
                event_type=EventType.TICK_END,
                workflow_id="order-001",
                tick_number=5,
                payload={"activity": "End", "resource": "system"},
            ),
        ]

        # Convert to XES log
        traces = [("order-001", events)]
        log = exporter.convert_log(traces)

        # Export to file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xes") as f:
            filepath = f.name

        try:
            exporter.export_to_file(log, filepath, pretty=True)

            # Verify file is valid XES
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
                root = ET.fromstring(content)

            # Check structure
            assert root.tag.endswith("log")
            assert root.get("xes.version") == "1849.2016"

            # Check extensions
            ns = {"xes": "http://www.xes-standard.org/"}
            extensions = root.findall("xes:extension", ns)
            assert len(extensions) >= 4

            # Check trace
            traces = root.findall("xes:trace", ns)
            assert len(traces) == 1

            # Check events
            events_xml = traces[0].findall("xes:event", ns)
            assert len(events_xml) == 5

            # Verify lifecycle transitions
            lifecycles = [e.find("xes:string[@key='lifecycle:transition']", ns).get("value") for e in events_xml]  # type: ignore[union-attr]
            assert lifecycles[0] == "start"  # TICK_START
            assert lifecycles[1] == "complete"  # STATUS_CHANGE
            assert lifecycles[2] == "start"  # MI_SPAWN
            assert lifecycles[3] == "complete"  # MI_COMPLETE
            assert lifecycles[4] == "complete"  # TICK_END

        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_multiple_workflows_to_xes_export(self) -> None:
        """Export multiple workflows as separate traces."""
        exporter = XESExporter()

        # Workflow 1
        wf1_events = [
            WorkflowEvent.create(
                event_type=EventType.STATUS_CHANGE, workflow_id="wf-001", tick_number=1, payload={"activity": "Task_A"}
            )
        ]

        # Workflow 2
        wf2_events = [
            WorkflowEvent.create(
                event_type=EventType.STATUS_CHANGE, workflow_id="wf-002", tick_number=1, payload={"activity": "Task_B"}
            )
        ]

        # Workflow 3
        wf3_events = [
            WorkflowEvent.create(
                event_type=EventType.CANCELLATION, workflow_id="wf-003", tick_number=1, payload={"activity": "Task_C"}
            )
        ]

        traces = [("wf-001", wf1_events), ("wf-002", wf2_events), ("wf-003", wf3_events)]

        log = exporter.convert_log(traces)

        # Verify
        assert len(log.traces) == 3
        assert log.traces[0].case_id == "wf-001"
        assert log.traces[1].case_id == "wf-002"
        assert log.traces[2].case_id == "wf-003"

        # Check cancellation has ATE_ABORT lifecycle
        cancellation_event = log.traces[2].events[0]
        assert cancellation_event.lifecycle == LifecycleTransition.ATE_ABORT
