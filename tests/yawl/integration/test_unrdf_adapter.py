"""Tests for UNRDFAdapter - YAWL-UNRDF integration.

Chicago TDD: Tests verify YAWL events integrate with UNRDF hook system.
"""

import time

import pytest

from kgcl.yawl.integration.unrdf_adapter import ProvenanceRecord, UNRDFAdapter, UNRDFHookEvent, YAWLEvent, YAWLEventType


@pytest.fixture
def adapter() -> UNRDFAdapter:
    """Create UNRDF adapter."""
    return UNRDFAdapter()


@pytest.fixture
def sample_event() -> YAWLEvent:
    """Create sample YAWL event."""
    return YAWLEvent(
        event_type=YAWLEventType.TASK_COMPLETED,
        case_id="case-001",
        timestamp=1700000000.0,
        spec_id="maketrip",
        task_id="register",
        workitem_id="wi-001",
        data={"customer": "John"},
    )


class TestYAWLEventType:
    """Tests for YAWLEventType enum."""

    def test_case_events_exist(self) -> None:
        """Case lifecycle events exist."""
        assert YAWLEventType.CASE_STARTED.value == "case_started"
        assert YAWLEventType.CASE_COMPLETED.value == "case_completed"
        assert YAWLEventType.CASE_CANCELLED.value == "case_cancelled"

    def test_task_events_exist(self) -> None:
        """Task lifecycle events exist."""
        assert YAWLEventType.TASK_ENABLED.value == "task_enabled"
        assert YAWLEventType.TASK_STARTED.value == "task_started"
        assert YAWLEventType.TASK_COMPLETED.value == "task_completed"
        assert YAWLEventType.TASK_FAILED.value == "task_failed"

    def test_workitem_events_exist(self) -> None:
        """Work item lifecycle events exist."""
        assert YAWLEventType.WORKITEM_CREATED.value == "workitem_created"
        assert YAWLEventType.WORKITEM_STARTED.value == "workitem_started"
        assert YAWLEventType.WORKITEM_COMPLETED.value == "workitem_completed"

    def test_token_events_exist(self) -> None:
        """Token lifecycle events exist."""
        assert YAWLEventType.TOKEN_CREATED.value == "token_created"
        assert YAWLEventType.TOKEN_MOVED.value == "token_moved"
        assert YAWLEventType.TOKEN_SPLIT.value == "token_split"
        assert YAWLEventType.TOKEN_JOINED.value == "token_joined"


class TestYAWLEvent:
    """Tests for YAWLEvent dataclass."""

    def test_event_is_frozen(self) -> None:
        """Event is immutable."""
        event = YAWLEvent(event_type=YAWLEventType.CASE_STARTED, case_id="case-001", timestamp=time.time())
        with pytest.raises(Exception):
            event.case_id = "modified"  # type: ignore[misc]

    def test_to_dict_includes_all_fields(self, sample_event: YAWLEvent) -> None:
        """to_dict includes all fields."""
        result = sample_event.to_dict()

        assert result["event_type"] == "task_completed"
        assert result["case_id"] == "case-001"
        assert result["timestamp"] == 1700000000.0
        assert result["spec_id"] == "maketrip"
        assert result["task_id"] == "register"
        assert result["workitem_id"] == "wi-001"
        assert result["data"] == {"customer": "John"}

    def test_default_values(self) -> None:
        """Default values are applied."""
        event = YAWLEvent(event_type=YAWLEventType.CASE_STARTED, case_id="case-001", timestamp=time.time())

        assert event.spec_id == ""
        assert event.task_id == ""
        assert event.workitem_id == ""
        assert event.data == {}


class TestUNRDFHookEvent:
    """Tests for UNRDFHookEvent dataclass."""

    def test_hook_event_structure(self) -> None:
        """Hook event has correct structure."""
        hook = UNRDFHookEvent(name="yawl:task_completed", payload={"task_id": "register"}, context={"graph": "test"})

        assert hook.name == "yawl:task_completed"
        assert hook.payload == {"task_id": "register"}
        assert hook.context == {"graph": "test"}

    def test_to_dict_format(self) -> None:
        """to_dict matches UNRDF format."""
        hook = UNRDFHookEvent(name="yawl:task_completed", payload={"task_id": "register"})

        result = hook.to_dict()

        assert result["name"] == "yawl:task_completed"
        assert result["payload"] == {"task_id": "register"}
        assert result["context"] == {}


class TestUNRDFAdapterConversion:
    """Tests for YAWL-UNRDF event conversion."""

    def test_yawl_to_hook_name_format(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """Hook name has yawl: prefix."""
        hook = adapter.yawl_to_hook(sample_event)

        assert hook.name == "yawl:task_completed"

    def test_yawl_to_hook_payload(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """Hook payload includes event data."""
        hook = adapter.yawl_to_hook(sample_event)

        assert hook.payload["case_id"] == "case-001"
        assert hook.payload["spec_id"] == "maketrip"
        assert hook.payload["task_id"] == "register"
        assert hook.payload["workitem_id"] == "wi-001"
        assert hook.payload["timestamp"] == 1700000000.0
        assert hook.payload["data"] == {"customer": "John"}

    def test_yawl_to_hook_context(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """Hook context includes graph and namespaces."""
        hook = adapter.yawl_to_hook(sample_event)

        assert "graph" in hook.context
        assert "base_uri" in hook.context
        assert "namespaces" in hook.context
        assert "yawl" in hook.context["namespaces"]
        assert "prov" in hook.context["namespaces"]

    def test_hook_to_yawl_roundtrip(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """Events survive roundtrip conversion."""
        hook = adapter.yawl_to_hook(sample_event)
        restored = adapter.hook_to_yawl(hook)

        assert restored is not None
        assert restored.event_type == sample_event.event_type
        assert restored.case_id == sample_event.case_id
        assert restored.spec_id == sample_event.spec_id
        assert restored.task_id == sample_event.task_id

    def test_hook_to_yawl_non_yawl_hook(self, adapter: UNRDFAdapter) -> None:
        """Non-YAWL hooks return None."""
        hook = UNRDFHookEvent(name="other:event", payload={})
        result = adapter.hook_to_yawl(hook)

        assert result is None

    def test_hook_to_yawl_invalid_event_type(self, adapter: UNRDFAdapter) -> None:
        """Invalid event types return None."""
        hook = UNRDFHookEvent(name="yawl:invalid_event", payload={"case_id": "test"})
        result = adapter.hook_to_yawl(hook)

        assert result is None


class TestUNRDFAdapterEventHistory:
    """Tests for event history tracking."""

    def test_record_event(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """Events are recorded in history."""
        adapter.record_event(sample_event)
        history = adapter.get_event_history()

        assert len(history) == 1
        assert history[0] == sample_event

    def test_filter_by_case_id(self, adapter: UNRDFAdapter) -> None:
        """History can be filtered by case ID."""
        event1 = YAWLEvent(event_type=YAWLEventType.CASE_STARTED, case_id="case-001", timestamp=time.time())
        event2 = YAWLEvent(event_type=YAWLEventType.CASE_STARTED, case_id="case-002", timestamp=time.time())

        adapter.record_event(event1)
        adapter.record_event(event2)

        history = adapter.get_event_history(case_id="case-001")

        assert len(history) == 1
        assert history[0].case_id == "case-001"


class TestUNRDFAdapterProvenance:
    """Tests for PROV-O provenance tracking."""

    def test_add_provenance(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """Provenance records are created."""
        record = adapter.add_provenance(sample_event, agent_id="admin")

        assert record.entity_id.startswith(adapter.base_uri)
        assert record.activity_id.endswith("task_completed")
        assert record.agent_id.endswith("admin")
        assert record.timestamp == sample_event.timestamp

    def test_get_provenance(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """Provenance records can be retrieved."""
        adapter.add_provenance(sample_event)
        records = adapter.get_provenance()

        assert len(records) == 1

    def test_filter_provenance_by_case(self, adapter: UNRDFAdapter) -> None:
        """Provenance filtered by case ID."""
        event1 = YAWLEvent(event_type=YAWLEventType.TASK_COMPLETED, case_id="case-001", timestamp=time.time())
        event2 = YAWLEvent(event_type=YAWLEventType.TASK_COMPLETED, case_id="case-002", timestamp=time.time())

        adapter.add_provenance(event1)
        adapter.add_provenance(event2)

        records = adapter.get_provenance(case_id="case-001")

        assert len(records) == 1
        assert records[0].attributes["case_id"] == "case-001"


class TestUNRDFAdapterRDF:
    """Tests for RDF conversion."""

    def test_event_to_rdf_has_type(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """Event RDF has type triple."""
        quads = adapter.event_to_rdf(sample_event)

        type_quads = [q for q in quads if "type" in q[1]]
        assert len(type_quads) >= 1
        assert any("YEvent" in q[2] for q in type_quads)

    def test_event_to_rdf_has_event_type(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """Event RDF includes event type."""
        quads = adapter.event_to_rdf(sample_event)

        event_type_quads = [q for q in quads if "eventType" in q[1]]
        assert len(event_type_quads) == 1
        assert event_type_quads[0][2] == "task_completed"

    def test_event_to_rdf_has_case_id(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """Event RDF includes case ID."""
        quads = adapter.event_to_rdf(sample_event)

        case_quads = [q for q in quads if "caseId" in q[1]]
        assert len(case_quads) == 1
        assert case_quads[0][2] == "case-001"

    def test_event_to_rdf_includes_graph(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """RDF quads include graph name."""
        quads = adapter.event_to_rdf(sample_event)

        assert all(q[3] == adapter.graph_name for q in quads)

    def test_provenance_to_rdf_prov_o(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """Provenance RDF uses PROV-O ontology."""
        record = adapter.add_provenance(sample_event)
        quads = adapter.provenance_to_rdf(record)

        # Should have Entity, Activity, Agent types
        type_quads = [q for q in quads if "type" in q[1]]
        assert any("Entity" in q[2] for q in type_quads)
        assert any("Activity" in q[2] for q in type_quads)
        assert any("Agent" in q[2] for q in type_quads)

        # Should have wasGeneratedBy
        generated_quads = [q for q in quads if "wasGeneratedBy" in q[1]]
        assert len(generated_quads) == 1


class TestUNRDFAdapterHookDefinition:
    """Tests for hook definition generation."""

    def test_generate_hook_definition_meta(self, adapter: UNRDFAdapter) -> None:
        """Hook definition has metadata."""
        hook_def = adapter.generate_hook_definition(YAWLEventType.TASK_COMPLETED)

        assert hook_def["meta"]["name"] == "yawl:task_completed"
        assert "description" in hook_def["meta"]
        assert "yawl" in hook_def["meta"]["ontology"]
        assert "prov" in hook_def["meta"]["ontology"]

    def test_generate_hook_definition_channel(self, adapter: UNRDFAdapter) -> None:
        """Hook definition has channel config."""
        hook_def = adapter.generate_hook_definition(YAWLEventType.TASK_COMPLETED)

        assert adapter.graph_name in hook_def["channel"]["graphs"]
        assert hook_def["channel"]["view"] == "after"

    def test_generate_hook_definition_receipting(self, adapter: UNRDFAdapter) -> None:
        """Hook definition uses lockchain receipting."""
        hook_def = adapter.generate_hook_definition(YAWLEventType.TASK_COMPLETED)

        assert hook_def["deterministic"] is True
        assert hook_def["receipting"] == "lockchain"

    def test_generate_hook_definition_with_condition(self, adapter: UNRDFAdapter) -> None:
        """Hook definition can include condition file."""
        hook_def = adapter.generate_hook_definition(
            YAWLEventType.TASK_COMPLETED, condition_file="hooks/task-complete.ask.rq"
        )

        assert "when" in hook_def
        assert hook_def["when"]["kind"] == "sparql-ask"
        assert "ref" in hook_def["when"]
        assert hook_def["when"]["ref"]["mediaType"] == "application/sparql-query"


class TestUNRDFAdapterJsonLD:
    """Tests for JSON-LD serialization."""

    def test_to_json_ld_context(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """JSON-LD has proper context."""
        adapter.record_event(sample_event)
        doc = adapter.to_json_ld([sample_event])

        assert "@context" in doc
        assert "yawl" in doc["@context"]
        assert "prov" in doc["@context"]

    def test_to_json_ld_graph(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """JSON-LD contains event graph."""
        doc = adapter.to_json_ld([sample_event])

        assert "@graph" in doc
        assert len(doc["@graph"]) == 1
        assert doc["@graph"][0]["eventType"] == "task_completed"

    def test_from_json_ld_roundtrip(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """JSON-LD roundtrip preserves events."""
        doc = adapter.to_json_ld([sample_event])
        restored = adapter.from_json_ld(doc)

        assert len(restored) == 1
        assert restored[0].event_type == sample_event.event_type
        assert restored[0].case_id == sample_event.case_id


class TestUNRDFAdapterExport:
    """Tests for event log export."""

    def test_export_json_format(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """Export to JSON format."""
        adapter.record_event(sample_event)
        output = adapter.export_event_log(format="json")

        import json

        data = json.loads(output)
        assert len(data) == 1
        assert data[0]["event_type"] == "task_completed"

    def test_export_jsonld_format(self, adapter: UNRDFAdapter, sample_event: YAWLEvent) -> None:
        """Export to JSON-LD format."""
        adapter.record_event(sample_event)
        output = adapter.export_event_log(format="jsonld")

        import json

        data = json.loads(output)
        assert "@context" in data
        assert "@graph" in data

    def test_export_filter_by_case(self, adapter: UNRDFAdapter) -> None:
        """Export can filter by case ID."""
        event1 = YAWLEvent(event_type=YAWLEventType.CASE_STARTED, case_id="case-001", timestamp=time.time())
        event2 = YAWLEvent(event_type=YAWLEventType.CASE_STARTED, case_id="case-002", timestamp=time.time())

        adapter.record_event(event1)
        adapter.record_event(event2)

        import json

        output = adapter.export_event_log(case_id="case-001", format="json")
        data = json.loads(output)

        assert len(data) == 1
        assert data[0]["case_id"] == "case-001"
