"""Tests for audit trail exporters and compliance reporting."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from kgcl.hybrid.temporal.adapters.audit_exporters.compliance_templates import (
    GDPRArticle30Template,
    GeneralComplianceTemplate,
    SOX404Template,
)
from kgcl.hybrid.temporal.adapters.audit_exporters.csv_exporter import CSVAuditExporter
from kgcl.hybrid.temporal.adapters.audit_exporters.json_exporter import AUDIT_LOG_SCHEMA, JSONAuditExporter
from kgcl.hybrid.temporal.adapters.in_memory_event_store import InMemoryEventStore
from kgcl.hybrid.temporal.domain.event import EventType, WorkflowEvent
from kgcl.hybrid.temporal.ports.audit_exporter_port import ExportFormat


@pytest.fixture
def event_store() -> InMemoryEventStore:
    """Create event store with test data."""
    store = InMemoryEventStore()

    # Create workflow with approval -> execution sequence
    now = datetime.now()

    # Event 1: Workflow created (using STATUS_CHANGE)
    e1 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        timestamp=now,
        tick_number=1,
        workflow_id="wf-001",
        caused_by=(),
        vector_clock=(("node1", 1),),
        payload={"actor": "user@example.com", "subject": "deployment-request", "status": "created"},
    )
    store.append(e1)

    # Event 2: Workflow approved (using STATUS_CHANGE)
    e2 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        timestamp=now + timedelta(seconds=10),
        tick_number=2,
        workflow_id="wf-001",
        caused_by=(e1.event_id,),
        vector_clock=(("node1", 2),),
        payload={
            "actor": "approver@example.com",
            "subject": "deployment-request",
            "previous_status": "pending",
            "new_status": "approved",
        },
        previous_hash=e1.event_hash,
    )
    store.append(e2)

    # Event 3: Workflow executed (using STATUS_CHANGE)
    e3 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        timestamp=now + timedelta(seconds=20),
        tick_number=3,
        workflow_id="wf-001",
        caused_by=(e2.event_id,),
        vector_clock=(("node1", 3),),
        payload={
            "actor": "executor@example.com",
            "subject": "deployment-request",
            "previous_status": "approved",
            "new_status": "executed",
        },
        previous_hash=e2.event_hash,
    )
    store.append(e3)

    return store


@pytest.fixture
def json_exporter(event_store: InMemoryEventStore) -> JSONAuditExporter:
    """Create JSON exporter."""
    return JSONAuditExporter(event_store=event_store)


@pytest.fixture
def csv_exporter(event_store: InMemoryEventStore) -> CSVAuditExporter:
    """Create CSV exporter."""
    return CSVAuditExporter(event_store=event_store)


def test_json_export_basic(json_exporter: JSONAuditExporter) -> None:
    """Test basic JSON export."""
    report = json_exporter.export(workflow_id="wf-001")

    assert report.format == ExportFormat.JSON
    assert report.workflow_id == "wf-001"
    assert report.event_count == 3
    assert report.filename.startswith("audit_wf-001_")
    assert report.filename.endswith(".json")

    # Parse JSON content
    data = json.loads(report.content.decode("utf-8"))
    assert data["version"] == "2.0.0"
    assert data["workflow_id"] == "wf-001"
    assert data["event_count"] == 3
    assert len(data["events"]) == 3


def test_json_export_with_causal_chains(json_exporter: JSONAuditExporter) -> None:
    """Test JSON export includes causal chains."""
    report = json_exporter.export(workflow_id="wf-001", include_causal=True)

    data = json.loads(report.content.decode("utf-8"))

    assert "causal_chains" in data
    assert data["causal_chains"] is not None
    assert len(data["causal_chains"]) == 3

    # Check causal chain for last event includes all predecessors
    last_event_id = data["events"][-1]["event_id"]
    causal_chain = data["causal_chains"][last_event_id]
    assert len(causal_chain) == 3


def test_json_export_time_range(json_exporter: JSONAuditExporter) -> None:
    """Test JSON export with time range filter."""
    now = datetime.now()
    start = now + timedelta(seconds=5)
    end = now + timedelta(seconds=15)

    report = json_exporter.export(workflow_id="wf-001", start=start, end=end)

    data = json.loads(report.content.decode("utf-8"))
    assert data["time_range"]["start"] is not None
    assert data["time_range"]["end"] is not None

    # Should only get event 2 (approval at +10s)
    assert len(data["events"]) == 1
    assert data["events"][0]["event_type"] == "STATUS_CHANGE"


def test_json_schema_validation(json_exporter: JSONAuditExporter) -> None:
    """Test exported JSON matches schema."""
    report = json_exporter.export(workflow_id="wf-001")
    data = json.loads(report.content.decode("utf-8"))

    # Check required fields from schema
    assert "version" in data
    assert data["version"] == "2.0.0"
    assert "workflow_id" in data
    assert "generated_at" in data
    assert "events" in data

    # Check event structure
    for event in data["events"]:
        assert "event_id" in event
        assert "event_type" in event
        assert "timestamp" in event
        assert "tick_number" in event


def test_csv_export_basic(csv_exporter: CSVAuditExporter) -> None:
    """Test basic CSV export."""
    report = csv_exporter.export(workflow_id="wf-001")

    assert report.format == ExportFormat.CSV
    assert report.workflow_id == "wf-001"
    assert report.event_count == 3
    assert report.filename.startswith("audit_wf-001_")
    assert report.filename.endswith(".csv")

    # Parse CSV content
    content = report.content.decode("utf-8")
    lines = content.strip().split("\n")

    # Header + 3 events
    assert len(lines) == 4

    # Check header
    from kgcl.hybrid.temporal.adapters.audit_exporters.csv_exporter import CSV_COLUMNS

    header = lines[0]
    for col in CSV_COLUMNS:
        assert col in header


def test_csv_columns_complete(csv_exporter: CSVAuditExporter) -> None:
    """Test CSV includes all expected columns."""
    report = csv_exporter.export(workflow_id="wf-001")

    content = report.content.decode("utf-8")
    lines = content.strip().split("\n")
    header = lines[0]

    expected_columns = [
        "event_id",
        "event_type",
        "timestamp",
        "tick_number",
        "workflow_id",
        "actor",
        "subject",
        "previous_status",
        "new_status",
        "caused_by_count",
        "event_hash",
    ]

    for col in expected_columns:
        assert col in header


def test_verify_chain_integrity_valid(json_exporter: JSONAuditExporter) -> None:
    """Test chain integrity verification for valid chain."""
    integrity = json_exporter.verify_chain_integrity(workflow_id="wf-001")

    assert integrity.workflow_id == "wf-001"
    assert integrity.is_valid is True
    assert integrity.events_checked == 3
    assert integrity.first_invalid_event is None
    assert integrity.error_message is None


def test_verify_chain_integrity_invalid(event_store: InMemoryEventStore) -> None:
    """Test chain integrity verification detects tampering."""
    # Create event with broken chain
    now = datetime.now()

    # Add event with correct hash
    e1 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        timestamp=now,
        tick_number=1,
        workflow_id="wf-002",
        caused_by=(),
        vector_clock=(("node1", 1),),
        payload={},
    )
    event_store.append(e1)

    # Manually create event with wrong previous_hash
    e2_bad = WorkflowEvent(
        event_id="evt-bad",
        event_type=EventType.STATUS_CHANGE,
        timestamp=now + timedelta(seconds=10),
        tick_number=2,
        workflow_id="wf-002",
        caused_by=(e1.event_id,),
        vector_clock=(("node1", 2),),
        payload={},
        previous_hash="WRONG_HASH",  # Deliberately wrong
    )
    event_store.append(e2_bad)

    exporter = JSONAuditExporter(event_store=event_store)
    integrity = exporter.verify_chain_integrity(workflow_id="wf-002")

    assert integrity.is_valid is False
    assert integrity.first_invalid_event == "evt-bad"


def test_sox_compliance_report(json_exporter: JSONAuditExporter) -> None:
    """Test SOX compliance report generation."""
    compliance = json_exporter.generate_compliance_report(workflow_id="wf-001", compliance_standard="SOX")

    assert compliance.workflow_id == "wf-001"
    assert compliance.audit_report.event_count == 3
    assert compliance.integrity_report.is_valid is True

    # Check SOX-specific properties
    property_names = [p[0] for p in compliance.temporal_properties]
    assert "all_events_have_actor" in property_names
    assert "approval_precedes_execution" in property_names

    # Check all events have actors
    all_have_actor = next((p for p in compliance.temporal_properties if p[0] == "all_events_have_actor"), None)
    assert all_have_actor is not None
    assert all_have_actor[1] is True  # Should pass

    # Check approval precedes execution
    approval_first = next((p for p in compliance.temporal_properties if p[0] == "approval_precedes_execution"), None)
    assert approval_first is not None
    assert approval_first[1] is True  # Should pass


def test_gdpr_compliance_report(json_exporter: JSONAuditExporter) -> None:
    """Test GDPR compliance report generation."""
    compliance = json_exporter.generate_compliance_report(workflow_id="wf-001", compliance_standard="GDPR")

    assert compliance.workflow_id == "wf-001"

    # Check GDPR-specific properties
    property_names = [p[0] for p in compliance.temporal_properties]
    assert "retention_policy_documented" in property_names


def test_audit_report_save_to_file(json_exporter: JSONAuditExporter) -> None:
    """Test saving audit report to file."""
    report = json_exporter.export(workflow_id="wf-001")

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Save to directory (uses default filename)
        saved_path = report.save(output_dir)
        assert saved_path.exists()
        assert saved_path.parent == output_dir
        assert saved_path.name == report.filename

        # Verify content
        saved_content = saved_path.read_bytes()
        assert saved_content == report.content

        # Save to specific file path
        specific_path = output_dir / "custom_audit.json"
        saved_path2 = report.save(specific_path)
        assert saved_path2 == specific_path
        assert saved_path2.exists()


def test_empty_workflow_export(event_store: InMemoryEventStore) -> None:
    """Test exporting empty workflow."""
    exporter = JSONAuditExporter(event_store=event_store)

    report = exporter.export(workflow_id="wf-nonexistent")

    assert report.event_count == 0

    data = json.loads(report.content.decode("utf-8"))
    assert len(data["events"]) == 0
    assert data["chain_integrity"]["genesis_hash"] == ""
    assert data["chain_integrity"]["final_hash"] == ""


def test_export_range_multiple_workflows(event_store: InMemoryEventStore) -> None:
    """Test exporting across multiple workflows."""
    # Add events for second workflow
    now = datetime.now()

    e1 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        timestamp=now + timedelta(seconds=30),
        tick_number=1,
        workflow_id="wf-002",
        caused_by=(),
        vector_clock=(("node2", 1),),
        payload={"actor": "user2@example.com"},
    )
    event_store.append(e1)

    exporter = JSONAuditExporter(event_store=event_store)

    # Export all workflows in time range
    start = now - timedelta(seconds=10)
    end = now + timedelta(seconds=40)

    report = exporter.export_range(start=start, end=end, format=ExportFormat.JSON)

    data = json.loads(report.content.decode("utf-8"))

    # Should have events from both workflows
    assert "workflows" in data
    assert "wf-001" in data["workflows"]
    assert "wf-002" in data["workflows"]
    assert len(data["workflows"]["wf-001"]) == 3
    assert len(data["workflows"]["wf-002"]) == 1


def test_export_range_filtered_workflows(event_store: InMemoryEventStore) -> None:
    """Test exporting with workflow ID filter."""
    # Add events for second workflow
    now = datetime.now()

    e1 = WorkflowEvent.create(
        event_type=EventType.STATUS_CHANGE,
        timestamp=now + timedelta(seconds=30),
        tick_number=1,
        workflow_id="wf-002",
        caused_by=(),
        vector_clock=(("node2", 1),),
        payload={"actor": "user2@example.com"},
    )
    event_store.append(e1)

    exporter = JSONAuditExporter(event_store=event_store)

    # Export only wf-001
    start = now - timedelta(seconds=10)
    end = now + timedelta(seconds=40)

    report = exporter.export_range(start=start, end=end, format=ExportFormat.JSON, workflow_ids=["wf-001"])

    data = json.loads(report.content.decode("utf-8"))

    # Should only have wf-001
    assert "workflows" in data
    assert "wf-001" in data["workflows"]
    assert "wf-002" not in data["workflows"]


def test_sox_template_structure() -> None:
    """Test SOX 404 template structure."""
    template = SOX404Template()

    assert len(template.controls) == 5

    # Check control IDs
    control_ids = template.get_control_ids()
    assert "SOX-AUTH-001" in control_ids
    assert "SOX-SEG-001" in control_ids

    # Get specific control
    control = template.get_control_by_id("SOX-AUTH-001")
    assert control is not None
    assert control[1] == "All changes require authorized actor"


def test_gdpr_template_validation() -> None:
    """Test GDPR Article 30 template validation."""
    template = GDPRArticle30Template()

    # Valid record
    valid_record = {
        "controller_name": "Example Corp",
        "processing_purpose": "Order fulfillment",
        "data_categories": "Contact information",
        "retention_period": "7 years",
        "security_measures": "Encryption at rest",
        "processing_start_date": "2024-01-01",
        "processing_end_date": "2024-12-31",
    }

    is_valid, missing = template.validate_record(valid_record)
    assert is_valid is True
    assert len(missing) == 0

    # Invalid record
    invalid_record = {"controller_name": "Example Corp", "processing_purpose": "Order fulfillment"}

    is_valid, missing = template.validate_record(invalid_record)
    assert is_valid is False
    assert len(missing) == 5
    assert "retention_period" in missing


def test_general_compliance_template() -> None:
    """Test general compliance template."""
    template = GeneralComplianceTemplate()

    assert len(template.requirements) == 5

    # Check requirement IDs
    req_ids = template.get_requirement_ids()
    assert "AUDIT-001" in req_ids
    assert "INTEG-001" in req_ids

    # Get specific requirement
    req = template.get_requirement_by_id("AUDIT-001")
    assert req is not None
    assert req[1] == "Complete audit trail of all operations"


def test_csv_export_range(event_store: InMemoryEventStore, csv_exporter: CSVAuditExporter) -> None:
    """Test CSV export for time range."""
    now = datetime.now()
    start = now - timedelta(seconds=10)
    end = now + timedelta(seconds=40)

    report = csv_exporter.export_range(start=start, end=end, format=ExportFormat.CSV)

    assert report.workflow_id == "MULTI"
    assert report.event_count == 3

    content = report.content.decode("utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 4  # Header + 3 events
