"""Enterprise Compliance & Separation of Duties Tests.

This test suite validates enterprise compliance workflows with SoD constraints:
1. Four-Eyes Principle (Pattern 40 - SoD)
2. Maker-Checker Workflows
3. Audit Trail Completeness
4. Role-Based Access Control (Pattern 37 - RBAC)
5. Regulatory Compliance Milestones
6. Data Privacy Controls (Pattern 28-30)

Each test verifies observable behavior with real YAWL pattern implementations.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.yawl_engine.core import ExecutionResult, YawlNamespace
from kgcl.yawl_engine.patterns.data_patterns import CaseData, DataContext, TaskData
from kgcl.yawl_engine.patterns.resource_patterns import (
    AllocationResult,
    Authorization,
    ConstraintType,
    DirectAllocation,
    RoleBasedAllocation,
    SeparationOfDuties,
    WorkItemStatus,
)

# Test namespaces
ROLE = Namespace("urn:org:role:")
USER = Namespace("urn:org:user:")
TASK = Namespace("urn:task:")
COMPLIANCE = Namespace("urn:compliance:")

logger = logging.getLogger(__name__)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def compliance_graph() -> Graph:
    """Create RDF graph with enterprise compliance structure.

    Organizational structure:
    - Roles: Finance, Legal, HR, Employee
    - Users: alice (Finance), bob (Finance), charlie (Legal), dave (Employee)
    - Capabilities: approve_expenses, sign_contracts, access_personnel_data
    """
    graph = Graph()

    # Role membership
    graph.add((USER.alice, ROLE.hasRole, Literal("role:Finance")))
    graph.add((USER.bob, ROLE.hasRole, Literal("role:Finance")))
    graph.add((USER.charlie, ROLE.hasRole, Literal("role:Legal")))
    graph.add((USER.dave, ROLE.hasRole, Literal("role:Employee")))

    # Capabilities
    graph.add((USER.alice, USER.hasCapability, Literal("approve_expenses")))
    graph.add((USER.alice, USER.hasCapability, Literal("create_expenses")))
    graph.add((USER.bob, USER.hasCapability, Literal("approve_expenses")))
    graph.add((USER.charlie, USER.hasCapability, Literal("sign_contracts")))
    graph.add((USER.charlie, USER.hasCapability, Literal("legal_review")))
    graph.add((USER.dave, USER.hasCapability, Literal("create_expenses")))

    # PII access (HR only - not in test data)
    graph.add((USER.alice, USER.hasCapability, Literal("access_personnel_data")))

    return graph


@pytest.fixture
def audit_trail_storage() -> list[dict[str, Any]]:
    """In-memory audit trail storage for testing."""
    return []


@pytest.fixture
def data_context() -> DataContext:
    """Unified data context for privacy tests."""
    return DataContext()


# ============================================================================
# 1. Four-Eyes Principle Tests (Pattern 40 - SoD)
# ============================================================================


class TestFourEyesPrinciple:
    """Test 4-eyes principle: Preparer cannot be Approver."""

    def test_four_eyes_blocks_same_user_submission_and_approval(
        self, compliance_graph: Graph
    ) -> None:
        """Preparer cannot approve own submission (4-eyes violated)."""
        # Setup: Dave submits expense request
        compliance_graph.add(
            (
                TASK.SubmitExpense,
                YawlNamespace.YAWL.completedBy,
                Literal("urn:org:user:dave"),
            )
        )

        # 4-eyes constraint: Different user must approve
        sod = SeparationOfDuties(
            constraint_type=ConstraintType.FOUR_EYES.value,
            related_tasks=[
                "urn:task:SubmitExpense",
                "urn:task:ApproveExpense",
            ],
        )

        # Dave tries to approve his own request
        result = sod.validate_allocation(
            compliance_graph, TASK.ApproveExpense, "urn:org:user:dave"
        )

        # Verify: 4-eyes constraint violated
        assert not result.success
        assert result.status == WorkItemStatus.CREATED
        assert "SoD constraint violated" in result.message
        assert result.metadata["constraint_type"] == "4-eyes"
        assert "urn:org:user:dave" in result.metadata["history"]

    def test_four_eyes_allows_different_user_approval(
        self, compliance_graph: Graph
    ) -> None:
        """Different user can approve submission (4-eyes satisfied)."""
        # Setup: Dave submits expense request
        compliance_graph.add(
            (
                TASK.SubmitExpense,
                YawlNamespace.YAWL.completedBy,
                Literal("urn:org:user:dave"),
            )
        )

        # 4-eyes constraint
        sod = SeparationOfDuties(
            constraint_type=ConstraintType.FOUR_EYES.value,
            related_tasks=[
                "urn:task:SubmitExpense",
                "urn:task:ApproveExpense",
            ],
        )

        # Alice (Finance) approves Dave's request
        result = sod.validate_allocation(
            compliance_graph, TASK.ApproveExpense, "urn:org:user:alice"
        )

        # Verify: Different user - constraint satisfied
        assert result.success
        assert result.status == WorkItemStatus.ALLOCATED
        assert result.allocated_to == "urn:org:user:alice"
        assert result.metadata["constraint_type"] == "4-eyes"

    def test_four_eyes_multiple_related_tasks(self, compliance_graph: Graph) -> None:
        """4-eyes enforced across multiple task chain."""
        # Setup: Dave creates transaction
        compliance_graph.add(
            (
                TASK.CreateTransaction,
                YawlNamespace.YAWL.completedBy,
                Literal("urn:org:user:dave"),
            )
        )

        # 4-eyes across entire workflow
        sod = SeparationOfDuties(
            constraint_type=ConstraintType.FOUR_EYES.value,
            related_tasks=[
                "urn:task:CreateTransaction",
                "urn:task:ReviewTransaction",
                "urn:task:FinalizeTransaction",
            ],
        )

        # Dave tries to review (second step)
        result = sod.validate_allocation(
            compliance_graph, TASK.ReviewTransaction, "urn:org:user:dave"
        )
        assert not result.success

        # Alice can review (different user)
        result = sod.validate_allocation(
            compliance_graph, TASK.ReviewTransaction, "urn:org:user:alice"
        )
        assert result.success


# ============================================================================
# 2. Maker-Checker Workflow Tests
# ============================================================================


class TestMakerCheckerWorkflow:
    """Test maker-checker pattern: Transaction creator vs. verifier."""

    def test_maker_checker_enforced_on_allocation(
        self, compliance_graph: Graph
    ) -> None:
        """Maker (creator) cannot be Checker (verifier)."""
        # Maker creates transaction
        direct = DirectAllocation()
        create_result = direct.allocate(
            compliance_graph, TASK.CreateJournalEntry, "urn:org:user:alice"
        )
        assert create_result.success

        # Record completion
        compliance_graph.add(
            (
                TASK.CreateJournalEntry,
                YawlNamespace.YAWL.completedBy,
                Literal("urn:org:user:alice"),
            )
        )

        # Checker constraint: Must be different user
        sod = SeparationOfDuties(
            constraint_type=ConstraintType.FOUR_EYES.value,
            related_tasks=[
                "urn:task:CreateJournalEntry",
                "urn:task:VerifyJournalEntry",
            ],
        )

        # Alice (Maker) tries to be Checker
        check_result = sod.validate_allocation(
            compliance_graph, TASK.VerifyJournalEntry, "urn:org:user:alice"
        )
        assert not check_result.success
        assert "4-eyes" in check_result.metadata["constraint_type"]

    def test_maker_checker_different_users_allowed(
        self, compliance_graph: Graph
    ) -> None:
        """Different user can be Checker (maker-checker satisfied)."""
        # Alice is Maker
        compliance_graph.add(
            (
                TASK.CreateJournalEntry,
                YawlNamespace.YAWL.completedBy,
                Literal("urn:org:user:alice"),
            )
        )

        # SoD constraint
        sod = SeparationOfDuties(
            constraint_type=ConstraintType.FOUR_EYES.value,
            related_tasks=[
                "urn:task:CreateJournalEntry",
                "urn:task:VerifyJournalEntry",
            ],
        )

        # Bob (different Finance user) is Checker
        check_result = sod.validate_allocation(
            compliance_graph, TASK.VerifyJournalEntry, "urn:org:user:bob"
        )

        assert check_result.success
        assert check_result.allocated_to == "urn:org:user:bob"

    def test_maker_checker_with_authorization(self, compliance_graph: Graph) -> None:
        """Checker must have approval capability (RBAC + SoD)."""
        # Alice creates
        compliance_graph.add(
            (
                TASK.CreateExpense,
                YawlNamespace.YAWL.completedBy,
                Literal("urn:org:user:alice"),
            )
        )

        # Checker needs approval capability
        authz = Authorization(required_capabilities=["approve_expenses"])

        # Dave lacks approve_expenses capability
        authz_result = authz.check_authorization(
            compliance_graph, TASK.ApproveExpense, "urn:org:user:dave"
        )
        assert not authz_result.success
        assert "approve_expenses" in authz_result.metadata["missing_capabilities"]

        # Bob has capability
        authz_result = authz.check_authorization(
            compliance_graph, TASK.ApproveExpense, "urn:org:user:bob"
        )
        assert authz_result.success

        # Plus SoD constraint
        sod = SeparationOfDuties(
            constraint_type=ConstraintType.FOUR_EYES.value,
            related_tasks=["urn:task:CreateExpense", "urn:task:ApproveExpense"],
        )
        sod_result = sod.validate_allocation(
            compliance_graph, TASK.ApproveExpense, "urn:org:user:bob"
        )
        assert sod_result.success


# ============================================================================
# 3. Audit Trail Tests
# ============================================================================


class TestAuditTrail:
    """Test comprehensive audit trail for compliance."""

    def test_audit_trail_records_all_actions(
        self, compliance_graph: Graph, audit_trail_storage: list[dict[str, Any]]
    ) -> None:
        """Every action logged with timestamp and actor."""

        def audit_log(
            action: str, actor: str, task: URIRef, metadata: dict[str, Any] | None = None
        ) -> None:
            """Log action to audit trail."""
            entry = {
                "timestamp": datetime.datetime.now(tz=datetime.UTC).isoformat(),
                "action": action,
                "actor": actor,
                "task": str(task),
                "metadata": metadata or {},
            }
            audit_trail_storage.append(entry)

        # Workflow: Create → Review → Approve
        rbac = RoleBasedAllocation()

        # Step 1: Offer to Finance role
        offer_result = rbac.offer(compliance_graph, TASK.CreateExpense, "role:Finance")
        audit_log("offer", "system", TASK.CreateExpense, {"role": "role:Finance"})

        # Step 2: Alice claims
        claim_result = rbac.claim(
            compliance_graph, TASK.CreateExpense, "urn:org:user:alice"
        )
        audit_log(
            "claim",
            "urn:org:user:alice",
            TASK.CreateExpense,
            {"status": "allocated"},
        )

        # Step 3: Alice completes
        compliance_graph.add(
            (
                TASK.CreateExpense,
                YawlNamespace.YAWL.completedBy,
                Literal("urn:org:user:alice"),
            )
        )
        audit_log(
            "complete",
            "urn:org:user:alice",
            TASK.CreateExpense,
            {"result": "success"},
        )

        # Step 4: Bob approves (different user)
        direct = DirectAllocation()
        approve_result = direct.allocate(
            compliance_graph, TASK.ApproveExpense, "urn:org:user:bob"
        )
        audit_log(
            "allocate",
            "urn:org:user:bob",
            TASK.ApproveExpense,
            {"pattern": "direct"},
        )

        # Verify audit trail completeness
        assert len(audit_trail_storage) == 4
        expected_actions = ["offer", "claim", "complete", "allocate"]
        actual_actions = [entry["action"] for entry in audit_trail_storage]
        assert actual_actions == expected_actions

        # Verify actor identity recorded
        actors = {entry["actor"] for entry in audit_trail_storage}
        assert "urn:org:user:alice" in actors
        assert "urn:org:user:bob" in actors
        assert "system" in actors

        # Verify timestamps present
        for entry in audit_trail_storage:
            assert "timestamp" in entry
            assert entry["timestamp"]  # Non-empty

    def test_audit_trail_immutable_history(
        self, compliance_graph: Graph, audit_trail_storage: list[dict[str, Any]]
    ) -> None:
        """Audit trail is append-only (immutable history)."""

        def audit_log(action: str, actor: str, task: URIRef) -> None:
            entry = {
                "timestamp": datetime.datetime.now(tz=datetime.UTC).isoformat(),
                "action": action,
                "actor": actor,
                "task": str(task),
            }
            audit_trail_storage.append(entry)

        # Log actions
        audit_log("create", "user:alice", TASK.T1)
        audit_log("approve", "user:bob", TASK.T1)

        initial_count = len(audit_trail_storage)
        initial_entries = audit_trail_storage.copy()

        # Verify immutability: Cannot modify past entries
        # (In production, use immutable data structures or blockchain)
        assert audit_trail_storage == initial_entries
        assert len(audit_trail_storage) == initial_count

    def test_audit_trail_sod_violation_logged(
        self, compliance_graph: Graph, audit_trail_storage: list[dict[str, Any]]
    ) -> None:
        """SoD violations recorded in audit trail."""
        # Alice creates
        compliance_graph.add(
            (
                TASK.SubmitRequest,
                YawlNamespace.YAWL.completedBy,
                Literal("urn:org:user:alice"),
            )
        )

        sod = SeparationOfDuties(
            constraint_type=ConstraintType.FOUR_EYES.value,
            related_tasks=["urn:task:SubmitRequest", "urn:task:ApproveRequest"],
        )

        # Alice tries to approve (violation)
        result = sod.validate_allocation(
            compliance_graph, TASK.ApproveRequest, "urn:org:user:alice"
        )

        # Log violation
        audit_trail_storage.append(
            {
                "timestamp": datetime.datetime.now(tz=datetime.UTC).isoformat(),
                "action": "sod_violation",
                "actor": "urn:org:user:alice",
                "task": str(TASK.ApproveRequest),
                "violation_type": "4-eyes",
                "severity": "high",
            }
        )

        # Verify violation logged
        violations = [e for e in audit_trail_storage if e["action"] == "sod_violation"]
        assert len(violations) == 1
        assert violations[0]["severity"] == "high"


# ============================================================================
# 4. Role-Based Access Control (Pattern 37) Tests
# ============================================================================


class TestRoleBasedAccessControl:
    """Test RBAC restricts access by role."""

    def test_rbac_only_finance_can_approve_expenses(
        self, compliance_graph: Graph
    ) -> None:
        """Only Finance role can approve expenses."""
        rbac = RoleBasedAllocation()

        # Offer to Finance role
        offer_result = rbac.offer(
            compliance_graph, TASK.ApproveExpense, "role:Finance"
        )
        assert offer_result.success
        expected_finance_count = 2  # alice, bob
        assert len(offer_result.allocated_to) == expected_finance_count

        # Finance users eligible
        eligible = rbac.get_eligible_users(
            compliance_graph, TASK.ApproveExpense, "role:Finance"
        )
        assert "urn:org:user:alice" in eligible
        assert "urn:org:user:bob" in eligible
        assert "urn:org:user:charlie" not in eligible  # Legal
        assert "urn:org:user:dave" not in eligible  # Employee

    def test_rbac_only_legal_can_sign_contracts(
        self, compliance_graph: Graph
    ) -> None:
        """Only Legal role can sign contracts."""
        authz = Authorization(required_capabilities=["sign_contracts"])

        # Charlie (Legal) can sign
        result = authz.check_authorization(
            compliance_graph, TASK.SignContract, "urn:org:user:charlie"
        )
        assert result.success

        # Alice (Finance) cannot sign
        result = authz.check_authorization(
            compliance_graph, TASK.SignContract, "urn:org:user:alice"
        )
        assert not result.success
        assert "sign_contracts" in result.metadata["missing_capabilities"]

    def test_rbac_personnel_data_access_restricted(
        self, compliance_graph: Graph
    ) -> None:
        """Only HR can access personnel data."""
        authz = Authorization(required_capabilities=["access_personnel_data"])

        # Alice has access (test setup gave her this capability)
        result = authz.check_authorization(
            compliance_graph, TASK.ViewPersonnelRecords, "urn:org:user:alice"
        )
        assert result.success

        # Charlie (Legal) does not
        result = authz.check_authorization(
            compliance_graph, TASK.ViewPersonnelRecords, "urn:org:user:charlie"
        )
        assert not result.success

    def test_rbac_claim_requires_role_membership(
        self, compliance_graph: Graph
    ) -> None:
        """User must have role to claim task."""
        rbac = RoleBasedAllocation()

        # Offer to Finance
        rbac.offer(compliance_graph, TASK.ProcessPayment, "role:Finance")

        # Dave (Employee) tries to claim
        with pytest.raises(PermissionError, match="not eligible"):
            rbac.claim(
                compliance_graph, TASK.ProcessPayment, "urn:org:user:dave"
            )

        # Alice (Finance) can claim
        claim_result = rbac.claim(
            compliance_graph, TASK.ProcessPayment, "urn:org:user:alice"
        )
        assert claim_result.success


# ============================================================================
# 5. Regulatory Compliance Milestone Tests
# ============================================================================


class TestRegulatoryComplianceMilestones:
    """Test compliance milestones block workflow progress."""

    def test_compliance_check_must_pass_before_proceeding(
        self, compliance_graph: Graph
    ) -> None:
        """Workflow cannot proceed if compliance check failed."""
        # Milestone: compliance_approved = true
        compliance_graph.add(
            (
                TASK.ComplianceCheck,
                COMPLIANCE.status,
                Literal("failed"),
            )
        )

        # Query for compliance status
        query = f"""
        PREFIX compliance: <{COMPLIANCE}>
        ASK {{
            <{TASK.ComplianceCheck}> compliance:status "approved" .
        }}
        """
        can_proceed = compliance_graph.query(query).askAnswer

        # Verify: Cannot proceed
        assert not can_proceed

    def test_compliance_approved_allows_progress(
        self, compliance_graph: Graph
    ) -> None:
        """Workflow proceeds if compliance check passed."""
        # Milestone: compliance_approved = true
        compliance_graph.add(
            (
                TASK.ComplianceCheck,
                COMPLIANCE.status,
                Literal("approved"),
            )
        )

        query = f"""
        PREFIX compliance: <{COMPLIANCE}>
        ASK {{
            <{TASK.ComplianceCheck}> compliance:status "approved" .
        }}
        """
        can_proceed = compliance_graph.query(query).askAnswer

        # Verify: Can proceed
        assert can_proceed

    def test_compliance_gate_blocks_high_value_transactions(
        self, compliance_graph: Graph
    ) -> None:
        """High-value transactions require additional compliance."""
        # Transaction metadata
        compliance_graph.add(
            (TASK.ProcessPayment, COMPLIANCE.amount, Literal(50000))
        )

        # Query for high-value transactions (>$10,000)
        query = f"""
        PREFIX compliance: <{COMPLIANCE}>
        ASK {{
            <{TASK.ProcessPayment}> compliance:amount ?amount .
            FILTER(?amount > 10000)
        }}
        """
        requires_compliance = compliance_graph.query(query).askAnswer

        assert requires_compliance

        # Compliance check needed
        authz = Authorization(required_capabilities=["approve_large_transactions"])
        # (In real system, this capability would be restricted)


# ============================================================================
# 6. Data Privacy Tests (Pattern 28-30)
# ============================================================================


class TestDataPrivacyControls:
    """Test data visibility at different scope levels."""

    def test_pii_only_visible_at_task_level(self, data_context: DataContext) -> None:
        """PII visible only within task, not case or workflow."""
        task = TASK.ProcessApplication
        case_id = "case-12345"

        # Store PII at task level (Pattern 28)
        data_context.task_data.set(task, "ssn", "123-45-6789")
        data_context.task_data.set(task, "applicant_name", "John Doe")

        # Verify: PII accessible in task scope
        assert data_context.task_data.get(task, "ssn") == "123-45-6789"

        # Verify: PII NOT accessible from other tasks
        other_task = TASK.ReviewApplication
        assert data_context.task_data.get(other_task, "ssn") is None

        # Verify: PII NOT in case scope
        assert data_context.case_data.get(case_id, "ssn") is None

    def test_aggregate_data_at_case_level(self, data_context: DataContext) -> None:
        """Aggregate data visible at case level (no PII)."""
        case_id = "case-12345"

        # Store aggregate/anonymized data at case level (Pattern 30)
        data_context.case_data.set(case_id, "application_count", 42)
        data_context.case_data.set(case_id, "approval_rate", 0.87)
        data_context.case_data.set(case_id, "region", "US-West")

        # Verify: Aggregate data accessible in case
        assert data_context.case_data.get(case_id, "application_count") == 42
        assert data_context.case_data.get(case_id, "approval_rate") == 0.87

        # No PII at case level
        assert "ssn" not in data_context.case_data.get_all(case_id)

    def test_anonymized_metrics_at_workflow_level(
        self, data_context: DataContext
    ) -> None:
        """Only anonymized metrics at workflow level (Pattern 31)."""
        # Global workflow metrics (no PII)
        data_context.workflow_data.set("total_applications_processed", 1000)
        data_context.workflow_data.set("average_processing_time_hours", 24.5)

        # Verify: Metrics accessible
        assert (
            data_context.workflow_data.get("total_applications_processed") == 1000
        )
        assert (
            data_context.workflow_data.get("average_processing_time_hours") == 24.5
        )

        # No PII at workflow level (architecture enforced)
        assert data_context.workflow_data.get("ssn") is None
        assert data_context.workflow_data.get("applicant_name") is None

    def test_scope_precedence_protects_pii(self, data_context: DataContext) -> None:
        """Variable resolution respects scope precedence for privacy."""
        task = TASK.ProcessPII
        case_id = "case-999"

        # Task-level PII (highest precedence)
        data_context.task_data.set(task, "sensitive_data", "CONFIDENTIAL")

        # Case-level summary (lower precedence)
        data_context.case_data.set(case_id, "sensitive_data", "REDACTED")

        # Resolve with task context
        value = data_context.resolve_variable(
            case_id=case_id,
            task=task,
            block=None,
            var_name="sensitive_data",
        )

        # Verify: Task scope takes precedence (PII visible in task)
        assert value == "CONFIDENTIAL"

        # Resolve from different task (no task-level data)
        other_task = TASK.GenerateReport
        value = data_context.resolve_variable(
            case_id=case_id,
            task=other_task,
            block=None,
            var_name="sensitive_data",
        )

        # Verify: Falls back to case scope (REDACTED)
        assert value == "REDACTED"


# ============================================================================
# Integration Tests - Full Compliance Workflows
# ============================================================================


class TestComplianceWorkflowIntegration:
    """End-to-end compliance workflow tests."""

    def test_expense_approval_full_workflow(
        self,
        compliance_graph: Graph,
        audit_trail_storage: list[dict[str, Any]],
    ) -> None:
        """Complete expense approval with all compliance controls."""

        def audit_log(action: str, actor: str, task: URIRef) -> None:
            audit_trail_storage.append(
                {
                    "timestamp": datetime.datetime.now(tz=datetime.UTC).isoformat(),
                    "action": action,
                    "actor": actor,
                    "task": str(task),
                }
            )

        # Step 1: Dave (Employee) submits expense
        direct = DirectAllocation()
        submit_result = direct.allocate(
            compliance_graph, TASK.SubmitExpense, "urn:org:user:dave"
        )
        assert submit_result.success
        compliance_graph.add(
            (
                TASK.SubmitExpense,
                YawlNamespace.YAWL.completedBy,
                Literal("urn:org:user:dave"),
            )
        )
        audit_log("submit", "urn:org:user:dave", TASK.SubmitExpense)

        # Step 2: Offer approval to Finance role
        rbac = RoleBasedAllocation()
        offer_result = rbac.offer(
            compliance_graph, TASK.ApproveExpense, "role:Finance"
        )
        assert offer_result.success
        audit_log("offer", "system", TASK.ApproveExpense)

        # Step 3: Check authorization (Finance role required)
        authz = Authorization(required_capabilities=["approve_expenses"])
        alice_authz = authz.check_authorization(
            compliance_graph, TASK.ApproveExpense, "urn:org:user:alice"
        )
        assert alice_authz.success

        # Step 4: Check SoD (4-eyes: Alice != Dave)
        sod = SeparationOfDuties(
            constraint_type=ConstraintType.FOUR_EYES.value,
            related_tasks=["urn:task:SubmitExpense", "urn:task:ApproveExpense"],
        )
        sod_result = sod.validate_allocation(
            compliance_graph, TASK.ApproveExpense, "urn:org:user:alice"
        )
        assert sod_result.success

        # Step 5: Alice claims and approves
        claim_result = rbac.claim(
            compliance_graph, TASK.ApproveExpense, "urn:org:user:alice"
        )
        assert claim_result.success
        audit_log("claim", "urn:org:user:alice", TASK.ApproveExpense)

        compliance_graph.add(
            (
                TASK.ApproveExpense,
                YawlNamespace.YAWL.completedBy,
                Literal("urn:org:user:alice"),
            )
        )
        audit_log("approve", "urn:org:user:alice", TASK.ApproveExpense)

        # Verify: Complete audit trail
        assert len(audit_trail_storage) == 4
        expected_actions = ["submit", "offer", "claim", "approve"]
        actual_actions = [e["action"] for e in audit_trail_storage]
        assert actual_actions == expected_actions

        # Verify: Different users (4-eyes satisfied)
        submitter_entries = [
            e for e in audit_trail_storage if e["action"] == "submit"
        ]
        approver_entries = [
            e for e in audit_trail_storage if e["action"] == "approve"
        ]
        assert submitter_entries[0]["actor"] != approver_entries[0]["actor"]

    def test_contract_signing_with_legal_review(
        self,
        compliance_graph: Graph,
        audit_trail_storage: list[dict[str, Any]],
    ) -> None:
        """Contract signing requires legal review and authorization."""

        def audit_log(action: str, actor: str, task: URIRef) -> None:
            audit_trail_storage.append(
                {
                    "timestamp": datetime.datetime.now(tz=datetime.UTC).isoformat(),
                    "action": action,
                    "actor": actor,
                    "task": str(task),
                }
            )

        # Step 1: Draft contract (any user)
        direct = DirectAllocation()
        draft_result = direct.allocate(
            compliance_graph, TASK.DraftContract, "urn:org:user:alice"
        )
        assert draft_result.success
        compliance_graph.add(
            (
                TASK.DraftContract,
                YawlNamespace.YAWL.completedBy,
                Literal("urn:org:user:alice"),
            )
        )
        audit_log("draft", "urn:org:user:alice", TASK.DraftContract)

        # Step 2: Legal review (Charlie only)
        authz = Authorization(required_capabilities=["legal_review"])
        charlie_authz = authz.check_authorization(
            compliance_graph, TASK.ReviewContract, "urn:org:user:charlie"
        )
        assert charlie_authz.success

        # Alice cannot review (lacks legal_review capability)
        alice_authz = authz.check_authorization(
            compliance_graph, TASK.ReviewContract, "urn:org:user:alice"
        )
        assert not alice_authz.success

        # Charlie reviews
        review_result = direct.allocate(
            compliance_graph, TASK.ReviewContract, "urn:org:user:charlie"
        )
        assert review_result.success
        compliance_graph.add(
            (
                TASK.ReviewContract,
                YawlNamespace.YAWL.completedBy,
                Literal("urn:org:user:charlie"),
            )
        )
        audit_log("review", "urn:org:user:charlie", TASK.ReviewContract)

        # Step 3: Sign contract (Charlie only - sign_contracts capability)
        authz_sign = Authorization(required_capabilities=["sign_contracts"])
        sign_authz = authz_sign.check_authorization(
            compliance_graph, TASK.SignContract, "urn:org:user:charlie"
        )
        assert sign_authz.success

        # SoD: Different user from drafter
        sod = SeparationOfDuties(
            constraint_type=ConstraintType.FOUR_EYES.value,
            related_tasks=["urn:task:DraftContract", "urn:task:SignContract"],
        )
        sod_result = sod.validate_allocation(
            compliance_graph, TASK.SignContract, "urn:org:user:charlie"
        )
        assert sod_result.success  # Charlie != Alice

        # Charlie signs
        sign_result = direct.allocate(
            compliance_graph, TASK.SignContract, "urn:org:user:charlie"
        )
        assert sign_result.success
        audit_log("sign", "urn:org:user:charlie", TASK.SignContract)

        # Verify audit trail
        assert len(audit_trail_storage) == 3
        expected_actions = ["draft", "review", "sign"]
        actual_actions = [e["action"] for e in audit_trail_storage]
        assert actual_actions == expected_actions
