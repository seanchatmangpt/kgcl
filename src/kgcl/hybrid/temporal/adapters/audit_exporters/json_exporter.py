"""JSON audit exporter with schema validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from kgcl.hybrid.temporal.domain.event import WorkflowEvent
from kgcl.hybrid.temporal.ports.audit_exporter_port import (
    AuditReport,
    ChainIntegrityReport,
    ComplianceReport,
    ExportFormat,
)
from kgcl.hybrid.temporal.ports.event_store_port import EventStore

# JSON Schema for audit log
AUDIT_LOG_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "KGCL Workflow Audit Log",
    "type": "object",
    "required": ["version", "workflow_id", "generated_at", "events"],
    "properties": {
        "version": {"const": "2.0.0"},
        "workflow_id": {"type": "string"},
        "generated_at": {"type": "string", "format": "date-time"},
        "chain_integrity": {
            "type": "object",
            "properties": {
                "verified": {"type": "boolean"},
                "genesis_hash": {"type": "string"},
                "final_hash": {"type": "string"},
            },
        },
        "events": {"type": "array", "items": {"$ref": "#/$defs/WorkflowEvent"}},
    },
    "$defs": {
        "WorkflowEvent": {
            "type": "object",
            "required": ["event_id", "event_type", "timestamp", "tick_number"],
            "properties": {
                "event_id": {"type": "string"},
                "event_type": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "tick_number": {"type": "integer"},
                "workflow_id": {"type": "string"},
                "actor": {"type": "string"},
                "caused_by": {"type": "array", "items": {"type": "string"}},
                "payload": {"type": "object"},
                "event_hash": {"type": "string"},
                "previous_hash": {"type": "string"},
            },
        }
    },
}


@dataclass
class JSONAuditExporter:
    """JSON exporter with schema compliance."""

    event_store: EventStore

    def export(
        self,
        workflow_id: str,
        format: ExportFormat = ExportFormat.JSON,
        start: datetime | None = None,
        end: datetime | None = None,
        include_causal: bool = True,
    ) -> AuditReport:
        """Export workflow events to JSON.

        Parameters
        ----------
        workflow_id : str
            Workflow identifier
        format : ExportFormat
            Output format (must be JSON)
        start : datetime | None
            Start of time range
        end : datetime | None
            End of time range
        include_causal : bool
            Include causal chain analysis

        Returns
        -------
        AuditReport
            Generated JSON audit report
        """
        events = list(self.event_store.query_range(start=start, end=end, workflow_id=workflow_id).events)

        # Build causal chains if requested
        causal_chains: dict[str, list[str]] = {}
        if include_causal:
            for event in events:
                chain = self.event_store.get_causal_chain(event.event_id)
                causal_chains[event.event_id] = [e.event_id for e in chain]

        # Verify chain integrity
        is_valid, error = self.event_store.verify_chain_integrity(workflow_id)

        # Build JSON structure
        audit_log = {
            "version": "2.0.0",
            "workflow_id": workflow_id,
            "generated_at": datetime.now().isoformat(),
            "chain_integrity": {
                "verified": is_valid,
                "genesis_hash": events[0].previous_hash if events else "",
                "final_hash": events[-1].event_hash if events else "",
                "error": error if not is_valid else None,
            },
            "event_count": len(events),
            "time_range": {"start": start.isoformat() if start else None, "end": end.isoformat() if end else None},
            "events": [self._event_to_dict(e) for e in events],
            "causal_chains": causal_chains if include_causal else None,
        }

        content = json.dumps(audit_log, indent=2, default=str).encode("utf-8")

        return AuditReport(
            format=ExportFormat.JSON,
            workflow_id=workflow_id,
            generated_at=datetime.now(),
            event_count=len(events),
            time_range_start=start,
            time_range_end=end,
            content=content,
            filename=f"audit_{workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )

    def export_range(
        self, start: datetime, end: datetime, format: ExportFormat, workflow_ids: list[str] | None = None
    ) -> AuditReport:
        """Export audit trail for time range across workflows.

        Parameters
        ----------
        start : datetime
            Start of time range
        end : datetime
            End of time range
        format : ExportFormat
            Output format (must be JSON)
        workflow_ids : list[str] | None
            Optional list of workflow IDs to include

        Returns
        -------
        AuditReport
            Generated JSON audit report
        """
        query_result = self.event_store.query_range(start=start, end=end)
        events = list(query_result.events)

        # Filter by workflow IDs if specified
        if workflow_ids:
            events = [e for e in events if e.workflow_id in workflow_ids]

        # Group events by workflow
        workflows: dict[str, list[WorkflowEvent]] = {}
        for event in events:
            if event.workflow_id not in workflows:
                workflows[event.workflow_id] = []
            workflows[event.workflow_id].append(event)

        # Build JSON structure
        audit_log = {
            "version": "2.0.0",
            "workflow_id": "MULTI",
            "generated_at": datetime.now().isoformat(),
            "event_count": len(events),
            "time_range": {"start": start.isoformat(), "end": end.isoformat()},
            "workflows": {wf_id: [self._event_to_dict(e) for e in wf_events] for wf_id, wf_events in workflows.items()},
        }

        content = json.dumps(audit_log, indent=2, default=str).encode("utf-8")

        return AuditReport(
            format=ExportFormat.JSON,
            workflow_id="MULTI",
            generated_at=datetime.now(),
            event_count=len(events),
            time_range_start=start,
            time_range_end=end,
            content=content,
            filename=f"audit_range_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )

    def verify_chain_integrity(self, workflow_id: str) -> ChainIntegrityReport:
        """Verify hash chain integrity for audit.

        Parameters
        ----------
        workflow_id : str
            Workflow identifier

        Returns
        -------
        ChainIntegrityReport
            Integrity verification results
        """
        events = list(self.event_store.query_range(workflow_id=workflow_id).events)

        is_valid, error = self.event_store.verify_chain_integrity(workflow_id)

        # Find first invalid event if chain is broken
        first_invalid = None
        if not is_valid:
            for i, event in enumerate(events):
                if i == 0:
                    continue
                expected_prev = events[i - 1].event_hash
                if event.previous_hash != expected_prev:
                    first_invalid = event.event_id
                    break

        return ChainIntegrityReport(
            workflow_id=workflow_id,
            verified_at=datetime.now(),
            is_valid=is_valid,
            events_checked=len(events),
            first_invalid_event=first_invalid,
            error_message=error if not is_valid else None,
        )

    def generate_compliance_report(self, workflow_id: str, compliance_standard: str) -> ComplianceReport:
        """Generate full compliance report.

        Parameters
        ----------
        workflow_id : str
            Workflow identifier
        compliance_standard : str
            Compliance standard name ("SOX", "GDPR", "GENERAL")

        Returns
        -------
        ComplianceReport
            Full compliance report
        """
        # Generate audit report
        audit_report = self.export(workflow_id)

        # Verify chain integrity
        integrity_report = self.verify_chain_integrity(workflow_id)

        # Check temporal properties based on compliance standard
        events = list(self.event_store.query_range(workflow_id=workflow_id).events)
        temporal_properties = self._check_compliance_properties(events, compliance_standard)

        # Generate summary
        summary = self._generate_compliance_summary(compliance_standard, integrity_report, temporal_properties)

        return ComplianceReport(
            workflow_id=workflow_id,
            generated_at=datetime.now(),
            audit_report=audit_report,
            integrity_report=integrity_report,
            temporal_properties=temporal_properties,
            summary=summary,
        )

    def _event_to_dict(self, event: WorkflowEvent) -> dict[str, Any]:
        """Convert event to JSON-serializable dict.

        Parameters
        ----------
        event : WorkflowEvent
            Event to convert

        Returns
        -------
        dict[str, Any]
            JSON-serializable dictionary
        """
        return {
            "event_id": event.event_id,
            "event_type": event.event_type.name,
            "timestamp": event.timestamp.isoformat(),
            "tick_number": event.tick_number,
            "workflow_id": event.workflow_id,
            "caused_by": list(event.caused_by),
            "vector_clock": {k: v for k, v in event.vector_clock},
            "payload": event.payload,
            "previous_hash": event.previous_hash,
            "event_hash": event.event_hash,
        }

    def _check_compliance_properties(self, events: list[WorkflowEvent], standard: str) -> list[tuple[str, bool, str]]:
        """Check compliance-specific temporal properties.

        Parameters
        ----------
        events : list[WorkflowEvent]
            Events to check
        standard : str
            Compliance standard

        Returns
        -------
        list[tuple[str, bool, str]]
            List of (property_name, holds, explanation)
        """
        properties: list[tuple[str, bool, str]] = []

        if standard == "SOX":
            # SOX-specific checks
            all_have_actor = all("actor" in e.payload for e in events)
            properties.append(
                (
                    "all_events_have_actor",
                    all_have_actor,
                    "All events have authorized actor" if all_have_actor else "Some events missing actor information",
                )
            )

            # Check approval precedes execution
            approval_exec_valid = self._check_approval_execution_order(events)
            properties.append(
                (
                    "approval_precedes_execution",
                    approval_exec_valid,
                    "Approvals precede executions" if approval_exec_valid else "Some executions before approval",
                )
            )

        elif standard == "GDPR":
            # GDPR-specific checks
            has_retention = any("retention_period" in e.payload for e in events)
            properties.append(
                (
                    "retention_policy_documented",
                    has_retention,
                    "Retention period documented" if has_retention else "No retention period found",
                )
            )

        return properties

    def _check_approval_execution_order(self, events: list[WorkflowEvent]) -> bool:
        """Check that approvals precede executions.

        Parameters
        ----------
        events : list[WorkflowEvent]
            Events to check

        Returns
        -------
        bool
            True if all executions have prior approvals
        """
        from kgcl.hybrid.temporal.domain.event import EventType

        # Look for status changes indicating approval
        approvals = {
            e.event_id
            for e in events
            if e.event_type == EventType.STATUS_CHANGE and e.payload.get("new_status") == "approved"
        }

        # Look for status changes indicating execution
        executions = [
            e for e in events if e.event_type == EventType.STATUS_CHANGE and e.payload.get("new_status") == "executed"
        ]

        for execution in executions:
            # Check if any approval is in causal chain
            has_approval = any(cause_id in approvals for cause_id in execution.caused_by)
            if not has_approval:
                return False

        return True

    def _generate_compliance_summary(
        self, standard: str, integrity: ChainIntegrityReport, properties: list[tuple[str, bool, str]]
    ) -> str:
        """Generate compliance summary text.

        Parameters
        ----------
        standard : str
            Compliance standard
        integrity : ChainIntegrityReport
            Integrity report
        properties : list[tuple[str, bool, str]]
            Temporal properties

        Returns
        -------
        str
            Summary text
        """
        passed = sum(1 for _, holds, _ in properties if holds)
        total = len(properties)

        summary_lines = [
            f"Compliance Report: {standard}",
            f"Workflow: {integrity.workflow_id}",
            f"Generated: {integrity.verified_at.isoformat()}",
            "",
            f"Chain Integrity: {'PASS' if integrity.is_valid else 'FAIL'}",
            f"Events Checked: {integrity.events_checked}",
            "",
            f"Compliance Checks: {passed}/{total} passed",
        ]

        for name, holds, explanation in properties:
            status = "✓" if holds else "✗"
            summary_lines.append(f"  {status} {name}: {explanation}")

        return "\n".join(summary_lines)
