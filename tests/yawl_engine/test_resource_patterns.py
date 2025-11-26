"""Tests for YAWL Resource Patterns (36-40)."""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, Namespace

from kgcl.yawl_engine.core import YawlNamespace
from kgcl.yawl_engine.patterns.resource_patterns import (
    AllocationResult,
    Authorization,
    ConstraintType,
    DeferredAllocation,
    DirectAllocation,
    RoleBasedAllocation,
    SeparationOfDuties,
    WorkItemStatus,
)

# Test namespaces
ROLE = Namespace("urn:org:role:")
USER = Namespace("urn:org:user:")
TASK = Namespace("urn:task:")


@pytest.fixture
def empty_graph() -> Graph:
    """Create empty RDF graph for testing."""
    return Graph()


@pytest.fixture
def graph_with_users() -> Graph:
    """Create RDF graph with user-role mappings."""
    graph = Graph()

    # Define role membership
    graph.add((USER.alice, ROLE.hasRole, Literal("role:Manager")))
    graph.add((USER.bob, ROLE.hasRole, Literal("role:Manager")))
    graph.add((USER.charlie, ROLE.hasRole, Literal("role:Employee")))

    # Define user capabilities
    graph.add((USER.alice, USER.hasCapability, Literal("sign_contracts")))
    graph.add((USER.alice, USER.hasCapability, Literal("approve_requests")))
    graph.add((USER.bob, USER.hasCapability, Literal("approve_requests")))
    graph.add((USER.charlie, USER.hasCapability, Literal("submit_requests")))

    return graph


# ============================================================================
# Pattern 36: Direct Allocation Tests
# ============================================================================


def test_direct_allocation_success(empty_graph: Graph) -> None:
    """Test direct allocation assigns task to specific user."""
    direct = DirectAllocation()
    task = TASK.ReviewDocument

    result = direct.allocate(empty_graph, task, "user:alice")

    assert result.success
    assert result.task == task
    assert result.allocated_to == "user:alice"
    assert result.status == WorkItemStatus.ALLOCATED
    assert result.metadata["pattern_id"] == DirectAllocation().pattern_id

    # Verify RDF updates
    assert (task, YawlNamespace.YAWL.allocatedTo, Literal("user:alice")) in empty_graph
    assert (task, YawlNamespace.YAWL.status, Literal("allocated")) in empty_graph


def test_direct_allocation_invalid_user() -> None:
    """Test direct allocation rejects invalid user."""
    direct = DirectAllocation()
    graph = Graph()

    with pytest.raises(ValueError, match="Invalid user identifier"):
        direct.allocate(graph, TASK.T1, "")

    with pytest.raises(ValueError, match="Invalid user identifier"):
        direct.allocate(graph, TASK.T1, None)  # type: ignore[arg-type]


# ============================================================================
# Pattern 37: Role-Based Allocation Tests
# ============================================================================


def test_rbac_get_eligible_users(graph_with_users: Graph) -> None:
    """Test retrieving users with specific role."""
    rbac = RoleBasedAllocation()
    task = TASK.ApproveRequest
    expected_manager_count = 2

    users = rbac.get_eligible_users(graph_with_users, task, "role:Manager")

    assert len(users) == expected_manager_count
    assert "urn:org:user:alice" in users
    assert "urn:org:user:bob" in users
    assert "urn:org:user:charlie" not in users


def test_rbac_offer_to_role(graph_with_users: Graph) -> None:
    """Test offering task to role makes it available to eligible users."""
    rbac = RoleBasedAllocation()
    task = TASK.ApproveRequest
    expected_manager_count = 2

    result = rbac.offer(graph_with_users, task, "role:Manager")

    assert result.success
    assert result.status == WorkItemStatus.OFFERED
    assert isinstance(result.allocated_to, list)
    assert len(result.allocated_to) == expected_manager_count
    assert result.metadata["role"] == "role:Manager"

    # Verify RDF updates
    assert (
        task,
        YawlNamespace.YAWL.offeredTo,
        Literal("role:Manager"),
    ) in graph_with_users
    assert (task, YawlNamespace.YAWL.status, Literal("offered")) in graph_with_users


def test_rbac_claim_task(graph_with_users: Graph) -> None:
    """Test user claiming offered task."""
    rbac = RoleBasedAllocation()
    task = TASK.ReviewCode

    # First offer to role
    rbac.offer(graph_with_users, task, "role:Manager")

    # User claims task
    result = rbac.claim(graph_with_users, task, "urn:org:user:alice")

    assert result.success
    assert result.status == WorkItemStatus.ALLOCATED
    assert result.allocated_to == "urn:org:user:alice"

    # Verify task is now allocated
    assert (
        task,
        YawlNamespace.YAWL.allocatedTo,
        Literal("urn:org:user:alice"),
    ) in graph_with_users
    assert (task, YawlNamespace.YAWL.status, Literal("allocated")) in graph_with_users


def test_rbac_claim_not_eligible_fails(graph_with_users: Graph) -> None:
    """Test claiming task by ineligible user fails."""
    rbac = RoleBasedAllocation()
    task = TASK.ManagerTask

    # Offer to Manager role
    rbac.offer(graph_with_users, task, "role:Manager")

    # Employee tries to claim (not eligible)
    with pytest.raises(PermissionError, match="not eligible"):
        rbac.claim(graph_with_users, task, "urn:org:user:charlie")


def test_rbac_claim_not_offered_fails(graph_with_users: Graph) -> None:
    """Test claiming task not in OFFERED state fails."""
    rbac = RoleBasedAllocation()
    task = TASK.SomeTask

    # Try to claim without offering first
    with pytest.raises(RuntimeError, match="not in OFFERED state"):
        rbac.claim(graph_with_users, task, "urn:org:user:alice")


# ============================================================================
# Pattern 38: Deferred Allocation Tests
# ============================================================================


def test_deferred_allocation_from_context(empty_graph: Graph) -> None:
    """Test deferred allocation using runtime context data."""
    deferred = DeferredAllocation(allocation_expression="data['assigned_manager']")
    task = TASK.ApproveExpense
    context = {"assigned_manager": "user:bob"}

    result = deferred.allocate(empty_graph, task, context)

    assert result.success
    assert result.allocated_to == "user:bob"
    assert result.status == WorkItemStatus.ALLOCATED
    assert result.metadata["expression"] == "data['assigned_manager']"

    # Verify RDF updates
    assert (task, YawlNamespace.YAWL.allocatedTo, Literal("user:bob")) in empty_graph


def test_deferred_allocation_complex_expression(empty_graph: Graph) -> None:
    """Test deferred allocation with conditional expression."""
    deferred = DeferredAllocation(
        allocation_expression=(
            "data['manager'] if data['amount'] > 1000 else data['supervisor']"
        )
    )
    task = TASK.Approve

    # High amount - allocate to manager
    context = {"amount": 5000, "manager": "user:director", "supervisor": "user:lead"}
    result = deferred.allocate(empty_graph, task, context)

    assert result.success
    assert result.allocated_to == "user:director"


def test_deferred_allocation_invalid_expression_fails(empty_graph: Graph) -> None:
    """Test deferred allocation with invalid expression fails."""
    deferred = DeferredAllocation(allocation_expression="data['nonexistent_key']")
    task = TASK.T1
    context = {"other_key": "value"}

    with pytest.raises(RuntimeError, match="Failed to evaluate"):
        deferred.allocate(empty_graph, task, context)


def test_deferred_allocation_invalid_result_fails(empty_graph: Graph) -> None:
    """Test deferred allocation with non-string result fails."""
    deferred = DeferredAllocation(allocation_expression="data['number']")
    task = TASK.T1
    context = {"number": 42}

    with pytest.raises(RuntimeError, match="Invalid allocation target"):
        deferred.allocate(empty_graph, task, context)


# ============================================================================
# Pattern 39: Authorization Tests
# ============================================================================


def test_authorization_with_capabilities(graph_with_users: Graph) -> None:
    """Test authorization checks user capabilities."""
    authz = Authorization(required_capabilities=["approve_requests"])
    task = TASK.ApproveRequest

    # Alice has capability
    result = authz.check_authorization(graph_with_users, task, "urn:org:user:alice")

    assert result.success
    assert result.status == WorkItemStatus.ALLOCATED
    assert "approve_requests" in result.metadata["required_capabilities"]


def test_authorization_missing_capability_fails(graph_with_users: Graph) -> None:
    """Test authorization fails when user lacks required capability."""
    authz = Authorization(required_capabilities=["sign_contracts"])
    task = TASK.SignContract

    # Bob lacks sign_contracts capability
    result = authz.check_authorization(graph_with_users, task, "urn:org:user:bob")

    assert not result.success
    assert result.status == WorkItemStatus.CREATED
    assert "sign_contracts" in result.metadata["missing_capabilities"]
    assert "not authorized" in result.message


def test_authorization_multiple_capabilities(graph_with_users: Graph) -> None:
    """Test authorization with multiple required capabilities."""
    authz = Authorization(required_capabilities=["sign_contracts", "approve_requests"])
    task = TASK.ExecutiveAction

    # Alice has both capabilities
    result = authz.check_authorization(graph_with_users, task, "urn:org:user:alice")

    assert result.success

    # Bob only has approve_requests
    result = authz.check_authorization(graph_with_users, task, "urn:org:user:bob")

    assert not result.success
    assert "sign_contracts" in result.metadata["missing_capabilities"]


# ============================================================================
# Pattern 40: Separation of Duties Tests
# ============================================================================


def test_sod_four_eyes_different_users(empty_graph: Graph) -> None:
    """Test 4-eyes principle allows different users."""
    sod = SeparationOfDuties(
        constraint_type=ConstraintType.FOUR_EYES.value,
        related_tasks=["urn:task:Submit", "urn:task:Approve"],
    )
    task = TASK.Approve

    # Alice approves Bob's submission
    valid = sod.check_constraint(empty_graph, task, "user:alice", ["user:bob"])

    assert valid


def test_sod_four_eyes_same_user_fails(empty_graph: Graph) -> None:
    """Test 4-eyes principle rejects same user."""
    sod = SeparationOfDuties(
        constraint_type=ConstraintType.FOUR_EYES.value,
        related_tasks=["urn:task:Submit", "urn:task:Approve"],
    )
    task = TASK.Approve

    # Bob tries to approve his own submission
    invalid = sod.check_constraint(empty_graph, task, "user:bob", ["user:bob"])

    assert not invalid


def test_sod_must_do_same_requires_same_user(empty_graph: Graph) -> None:
    """Test must-do-same constraint requires same user."""
    sod = SeparationOfDuties(
        constraint_type=ConstraintType.MUST_DO_SAME.value,
        related_tasks=["urn:task:Start", "urn:task:Complete"],
    )
    task = TASK.Complete

    # Same user who started
    valid = sod.check_constraint(empty_graph, task, "user:alice", ["user:alice"])
    assert valid

    # Different user
    invalid = sod.check_constraint(empty_graph, task, "user:bob", ["user:alice"])
    assert not invalid


def test_sod_must_do_different_requires_different_users(empty_graph: Graph) -> None:
    """Test must-do-different constraint requires different users."""
    sod = SeparationOfDuties(
        constraint_type=ConstraintType.MUST_DO_DIFFERENT.value,
        related_tasks=["urn:task:Step1", "urn:task:Step2"],
    )
    task = TASK.Step2

    # Different user
    valid = sod.check_constraint(empty_graph, task, "user:bob", ["user:alice"])
    assert valid

    # Same user
    invalid = sod.check_constraint(empty_graph, task, "user:alice", ["user:alice"])
    assert not invalid


def test_sod_validate_allocation_with_history(empty_graph: Graph) -> None:
    """Test SoD validation with task execution history."""
    # Record previous task execution
    empty_graph.add(
        (TASK.Submit, YawlNamespace.YAWL.completedBy, Literal("user:charlie"))
    )

    sod = SeparationOfDuties(
        constraint_type=ConstraintType.FOUR_EYES.value,
        related_tasks=["urn:task:Submit", "urn:task:Approve"],
    )

    # Alice can approve (different from Charlie)
    result = sod.validate_allocation(empty_graph, TASK.Approve, "user:alice")
    assert result.success

    # Charlie cannot approve (same user)
    result = sod.validate_allocation(empty_graph, TASK.Approve, "user:charlie")
    assert not result.success
    assert "SoD constraint violated" in result.message


def test_sod_validate_allocation_empty_history(empty_graph: Graph) -> None:
    """Test SoD validation with no execution history."""
    sod = SeparationOfDuties(
        constraint_type=ConstraintType.FOUR_EYES.value,
        related_tasks=["urn:task:Submit", "urn:task:Approve"],
    )

    # No history - should succeed
    result = sod.validate_allocation(empty_graph, TASK.Approve, "user:alice")
    assert result.success


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_rbac_workflow(graph_with_users: Graph) -> None:
    """Test complete RBAC workflow: offer → claim → allocate."""
    rbac = RoleBasedAllocation()
    task = TASK.ApproveExpense
    expected_manager_count = 2

    # 1. Offer to role
    offer_result = rbac.offer(graph_with_users, task, "role:Manager")
    assert offer_result.success
    assert len(offer_result.allocated_to) == expected_manager_count

    # 2. User claims
    claim_result = rbac.claim(graph_with_users, task, "urn:org:user:alice")
    assert claim_result.success
    assert claim_result.allocated_to == "urn:org:user:alice"


def test_authorization_with_sod(graph_with_users: Graph) -> None:
    """Test authorization combined with separation of duties."""
    # Setup: Record submission
    graph_with_users.add(
        (
            TASK.SubmitExpense,
            YawlNamespace.YAWL.completedBy,
            Literal("urn:org:user:charlie"),
        )
    )

    # Check authorization
    authz = Authorization(required_capabilities=["approve_requests"])
    authz_result = authz.check_authorization(
        graph_with_users, TASK.ApproveExpense, "urn:org:user:alice"
    )
    assert authz_result.success

    # Check SoD
    sod = SeparationOfDuties(
        constraint_type=ConstraintType.FOUR_EYES.value,
        related_tasks=["urn:task:SubmitExpense", "urn:task:ApproveExpense"],
    )
    sod_result = sod.validate_allocation(
        graph_with_users, TASK.ApproveExpense, "urn:org:user:alice"
    )
    assert sod_result.success

    # Both checks pass - Alice is authorized and satisfies SoD
    assert authz_result.success and sod_result.success


def test_deferred_then_direct_allocation(empty_graph: Graph) -> None:
    """Test deferred allocation followed by direct allocation override."""
    # Deferred allocation based on context
    deferred = DeferredAllocation(allocation_expression="data['initial_user']")
    task = TASK.ProcessRequest
    context = {"initial_user": "user:alice"}

    result1 = deferred.allocate(empty_graph, task, context)
    assert result1.allocated_to == "user:alice"

    # Direct allocation can override
    direct = DirectAllocation()
    result2 = direct.allocate(empty_graph, task, "user:bob")
    assert result2.allocated_to == "user:bob"

    # Verify final state
    values = list(empty_graph.objects(task, YawlNamespace.YAWL.allocatedTo))
    assert Literal("user:bob") in values


def test_allocation_result_immutability() -> None:
    """Test AllocationResult is immutable."""
    result = AllocationResult(
        success=True,
        task=TASK.T1,
        allocated_to="user:alice",
        status=WorkItemStatus.ALLOCATED,
        message="Success",
    )

    with pytest.raises(AttributeError):
        result.success = False  # type: ignore[misc]

    with pytest.raises(AttributeError):
        result.allocated_to = "user:bob"  # type: ignore[misc]


def test_work_item_lifecycle() -> None:
    """Test work item status transitions."""
    assert WorkItemStatus.CREATED.value == "created"
    assert WorkItemStatus.OFFERED.value == "offered"
    assert WorkItemStatus.ALLOCATED.value == "allocated"
    assert WorkItemStatus.STARTED.value == "started"
    assert WorkItemStatus.COMPLETED.value == "completed"
    assert WorkItemStatus.SUSPENDED.value == "suspended"
    assert WorkItemStatus.CANCELLED.value == "cancelled"


def test_constraint_types() -> None:
    """Test separation of duties constraint type enum."""
    assert ConstraintType.FOUR_EYES.value == "4-eyes"
    assert ConstraintType.MUST_DO_SAME.value == "must-do-same"
    assert ConstraintType.MUST_DO_DIFFERENT.value == "must-do-different"
