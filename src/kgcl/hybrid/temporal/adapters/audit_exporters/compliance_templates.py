"""Compliance report templates for SOX, GDPR, etc."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SOX404Template:
    """SOX Section 404 control checklist.

    Internal controls over financial reporting per Sarbanes-Oxley Act.
    """

    controls: tuple[tuple[str, str, str], ...] = (
        ("SOX-AUTH-001", "All changes require authorized actor", "all_events_have_actor"),
        ("SOX-SEG-001", "Approval/execution by different actors", "approval_execution_segregation"),
        ("SOX-SEQ-001", "Approval precedes execution", "approval_precedes_execution"),
        ("SOX-AUDIT-001", "Complete audit trail maintained", "chain_integrity_verified"),
        ("SOX-INTEG-001", "Data integrity verified", "hash_chain_valid"),
    )

    def get_control_by_id(self, control_id: str) -> tuple[str, str, str] | None:
        """Get control by ID.

        Parameters
        ----------
        control_id : str
            Control identifier (e.g., "SOX-AUTH-001")

        Returns
        -------
        tuple[str, str, str] | None
            Control tuple (id, description, check_name) or None
        """
        for control in self.controls:
            if control[0] == control_id:
                return control
        return None

    def get_control_ids(self) -> list[str]:
        """Get all control IDs.

        Returns
        -------
        list[str]
            List of control IDs
        """
        return [control[0] for control in self.controls]


@dataclass(frozen=True)
class GDPRArticle30Template:
    """GDPR Article 30 record of processing activities.

    Records of processing activities per General Data Protection Regulation.
    """

    required_fields: tuple[str, ...] = (
        "controller_name",
        "processing_purpose",
        "data_categories",
        "retention_period",
        "security_measures",
        "processing_start_date",
        "processing_end_date",
    )

    def validate_record(self, record: dict[str, str]) -> tuple[bool, list[str]]:
        """Validate processing record has all required fields.

        Parameters
        ----------
        record : dict[str, str]
            Processing activity record

        Returns
        -------
        tuple[bool, list[str]]
            (is_valid, missing_fields)
        """
        missing = [field for field in self.required_fields if field not in record]
        return len(missing) == 0, missing

    def get_field_descriptions(self) -> dict[str, str]:
        """Get descriptions for required fields.

        Returns
        -------
        dict[str, str]
            Mapping of field names to descriptions
        """
        return {
            "controller_name": "Name and contact details of the controller",
            "processing_purpose": "Purposes of the processing",
            "data_categories": "Categories of personal data",
            "retention_period": "Envisaged time limits for erasure",
            "security_measures": "General description of technical and organizational security measures",
            "processing_start_date": "Date processing activities commenced",
            "processing_end_date": "Date processing activities ceased (if applicable)",
        }


@dataclass(frozen=True)
class GeneralComplianceTemplate:
    """General compliance template for non-specific standards.

    Basic audit and control requirements applicable to most systems.
    """

    requirements: tuple[tuple[str, str], ...] = (
        ("AUDIT-001", "Complete audit trail of all operations"),
        ("INTEG-001", "Data integrity verification"),
        ("AUTH-001", "All operations have identified actor"),
        ("TIME-001", "Accurate timestamps on all events"),
        ("TRACE-001", "Causal relationships between events tracked"),
    )

    def get_requirement_by_id(self, requirement_id: str) -> tuple[str, str] | None:
        """Get requirement by ID.

        Parameters
        ----------
        requirement_id : str
            Requirement identifier

        Returns
        -------
        tuple[str, str] | None
            Requirement tuple (id, description) or None
        """
        for req in self.requirements:
            if req[0] == requirement_id:
                return req
        return None

    def get_requirement_ids(self) -> list[str]:
        """Get all requirement IDs.

        Returns
        -------
        list[str]
            List of requirement IDs
        """
        return [req[0] for req in self.requirements]
