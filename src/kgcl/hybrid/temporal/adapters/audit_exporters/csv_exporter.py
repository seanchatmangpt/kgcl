"""CSV audit exporter for spreadsheet analysis."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime

from kgcl.hybrid.temporal.ports.audit_exporter_port import (
    AuditReport,
    ChainIntegrityReport,
    ComplianceReport,
    ExportFormat,
)
from kgcl.hybrid.temporal.ports.event_store_port import EventStore

CSV_COLUMNS = [
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


@dataclass
class CSVAuditExporter:
    """CSV exporter for spreadsheet analysis."""

    event_store: EventStore

    def export(
        self,
        workflow_id: str,
        format: ExportFormat = ExportFormat.CSV,
        start: datetime | None = None,
        end: datetime | None = None,
        include_causal: bool = True,
    ) -> AuditReport:
        """Export to CSV format.

        Parameters
        ----------
        workflow_id : str
            Workflow identifier
        format : ExportFormat
            Output format (must be CSV)
        start : datetime | None
            Start of time range
        end : datetime | None
            End of time range
        include_causal : bool
            Include causal chain count

        Returns
        -------
        AuditReport
            Generated CSV audit report
        """
        events = list(self.event_store.query_range(start=start, end=end, workflow_id=workflow_id).events)

        # Build CSV content
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for event in events:
            row = {
                "event_id": event.event_id,
                "event_type": event.event_type.name,
                "timestamp": event.timestamp.isoformat(),
                "tick_number": event.tick_number,
                "workflow_id": event.workflow_id,
                "actor": event.payload.get("actor", ""),
                "subject": event.payload.get("subject", ""),
                "previous_status": event.payload.get("previous_status", ""),
                "new_status": event.payload.get("new_status", ""),
                "caused_by_count": len(event.caused_by),
                "event_hash": event.event_hash,
            }
            writer.writerow(row)

        content = output.getvalue().encode("utf-8")

        return AuditReport(
            format=ExportFormat.CSV,
            workflow_id=workflow_id,
            generated_at=datetime.now(),
            event_count=len(events),
            time_range_start=start,
            time_range_end=end,
            content=content,
            filename=f"audit_{workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
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
            Output format (must be CSV)
        workflow_ids : list[str] | None
            Optional list of workflow IDs to include

        Returns
        -------
        AuditReport
            Generated CSV audit report
        """
        query_result = self.event_store.query_range(start=start, end=end)
        events = list(query_result.events)

        # Filter by workflow IDs if specified
        if workflow_ids:
            events = [e for e in events if e.workflow_id in workflow_ids]

        # Build CSV content
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for event in events:
            row = {
                "event_id": event.event_id,
                "event_type": event.event_type.name,
                "timestamp": event.timestamp.isoformat(),
                "tick_number": event.tick_number,
                "workflow_id": event.workflow_id,
                "actor": event.payload.get("actor", ""),
                "subject": event.payload.get("subject", ""),
                "previous_status": event.payload.get("previous_status", ""),
                "new_status": event.payload.get("new_status", ""),
                "caused_by_count": len(event.caused_by),
                "event_hash": event.event_hash,
            }
            writer.writerow(row)

        content = output.getvalue().encode("utf-8")

        return AuditReport(
            format=ExportFormat.CSV,
            workflow_id="MULTI",
            generated_at=datetime.now(),
            event_count=len(events),
            time_range_start=start,
            time_range_end=end,
            content=content,
            filename=f"audit_range_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
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
            Full compliance report with CSV format
        """
        # Generate CSV audit report
        audit_report = self.export(workflow_id)

        # Verify chain integrity
        integrity_report = self.verify_chain_integrity(workflow_id)

        # Check temporal properties
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
        from kgcl.hybrid.temporal.domain.event import WorkflowEvent

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
