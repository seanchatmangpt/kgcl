"""Audit exporter port for compliance reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Protocol, runtime_checkable


class ExportFormat(Enum):
    """Supported export formats."""

    JSON = auto()
    CSV = auto()
    PDF = auto()


@dataclass(frozen=True)
class AuditReport:
    """Generated audit report."""

    format: ExportFormat
    workflow_id: str
    generated_at: datetime
    event_count: int
    time_range_start: datetime | None
    time_range_end: datetime | None
    content: bytes  # Raw export data
    filename: str

    def save(self, path: Path) -> Path:
        """Save report to file.

        Parameters
        ----------
        path : Path
            Directory or full file path to save report

        Returns
        -------
        Path
            Path to saved file
        """
        if path.is_dir():
            file_path = path / self.filename
        else:
            file_path = path

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(self.content)
        return file_path


@dataclass(frozen=True)
class ChainIntegrityReport:
    """Hash chain integrity verification report."""

    workflow_id: str
    verified_at: datetime
    is_valid: bool
    events_checked: int
    first_invalid_event: str | None
    error_message: str | None


@dataclass(frozen=True)
class ComplianceReport:
    """Combined compliance report with multiple sections."""

    workflow_id: str
    generated_at: datetime
    audit_report: AuditReport
    integrity_report: ChainIntegrityReport
    temporal_properties: list[tuple[str, bool, str]]  # (name, holds, explanation)
    summary: str


@runtime_checkable
class AuditExporter(Protocol):
    """Protocol for audit trail export."""

    def export(
        self,
        workflow_id: str,
        format: ExportFormat,
        start: datetime | None = None,
        end: datetime | None = None,
        include_causal: bool = True,
    ) -> AuditReport:
        """Export audit trail for workflow.

        Parameters
        ----------
        workflow_id : str
            Workflow identifier
        format : ExportFormat
            Output format
        start : datetime | None
            Start of time range
        end : datetime | None
            End of time range
        include_causal : bool
            Include causal chain analysis

        Returns
        -------
        AuditReport
            Generated report
        """
        ...

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
            Output format
        workflow_ids : list[str] | None
            Optional list of workflow IDs to include

        Returns
        -------
        AuditReport
            Generated report
        """
        ...

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
        ...

    def generate_compliance_report(
        self,
        workflow_id: str,
        compliance_standard: str,  # "SOX", "GDPR", "GENERAL"
    ) -> ComplianceReport:
        """Generate full compliance report.

        Parameters
        ----------
        workflow_id : str
            Workflow identifier
        compliance_standard : str
            Compliance standard name

        Returns
        -------
        ComplianceReport
            Full compliance report
        """
        ...
