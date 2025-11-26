"""YAWL Resource Patterns (36-40) - Resource Allocation & Authorization.

Implements YAWL Foundation resource allocation patterns for human resources:
- Pattern 36: Direct Allocation - Task assigned to specific user
- Pattern 37: Role-Based Allocation - Task offered to role, any member can claim
- Pattern 38: Deferred Allocation - Allocation decision made at runtime
- Pattern 39: Authorization - Access control for task execution
- Pattern 40: Separation of Duties - Constraints on related task execution

These patterns integrate with YAWL's Resource Perspective and work item lifecycle:
offered → allocated → started → completed

References
----------
- YAWL Foundation: http://www.yawlfoundation.org/
- Resource Patterns: http://www.workflowpatterns.com/patterns/resource/
- Java YAWL: https://github.com/yawlfoundation/yawl

Examples
--------
>>> from rdflib import Graph, URIRef
>>> graph = Graph()
>>> # Direct allocation to specific user
>>> direct = DirectAllocation()
>>> result = direct.allocate(graph, URIRef("urn:task:ReviewDocument"), "user:john")
>>> assert result.success
>>>
>>> # Role-based allocation
>>> rbac = RoleBasedAllocation()
>>> result = rbac.offer(graph, URIRef("urn:task:ApproveRequest"), "role:Manager")
>>> users = rbac.get_eligible_users(
...     graph, URIRef("urn:task:ApproveRequest"), "role:Manager"
... )
>>> claim_result = rbac.claim(graph, URIRef("urn:task:ApproveRequest"), users[0])
>>>
>>> # Separation of duties (4-eyes principle)
>>> sod = SeparationOfDuties(constraint_type="4-eyes")
>>> valid = sod.check_constraint(
...     graph,
...     URIRef("urn:task:Approve"),
...     "user:alice",
...     ["user:bob"],  # Different user submitted
... )
>>> assert valid  # Alice can approve Bob's submission
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.query import ResultRow

from kgcl.yawl_engine.core import YawlNamespace

# YAWL Resource Namespace
YAWL_RESOURCE = Namespace("http://www.yawlfoundation.org/yawlschema/resource#")

logger = logging.getLogger(__name__)


# ============================================================================
# Work Item Lifecycle
# ============================================================================


class WorkItemStatus(str, Enum):
    """Work item lifecycle states in YAWL resource management.

    States
    ------
    CREATED
        Work item created but not yet offered
    OFFERED
        Offered to user(s) based on allocation strategy
    ALLOCATED
        Allocated to specific user (claimed or directly assigned)
    STARTED
        User has started working on the task
    COMPLETED
        Task execution completed successfully
    SUSPENDED
        Temporarily paused by user or system
    CANCELLED
        Cancelled before completion
    """

    CREATED = "created"
    OFFERED = "offered"
    ALLOCATED = "allocated"
    STARTED = "started"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class AllocationResult:
    """Immutable result of resource allocation operation.

    Parameters
    ----------
    success : bool
        Whether allocation succeeded
    task : URIRef
        Task that was allocated
    allocated_to : str | list[str]
        User(s) or role(s) the task was allocated to
    status : WorkItemStatus
        Resulting work item status
    message : str
        Human-readable result message
    metadata : dict[str, Any]
        Additional allocation metadata (constraints, permissions, etc.)

    Examples
    --------
    >>> result = AllocationResult(
    ...     success=True,
    ...     task=URIRef("urn:task:Review"),
    ...     allocated_to="user:alice",
    ...     status=WorkItemStatus.ALLOCATED,
    ...     message="Task allocated to alice",
    ...     metadata={"allocation_time": "2024-11-25T10:00:00Z"},
    ... )
    """

    success: bool
    task: URIRef
    allocated_to: str | list[str]
    status: WorkItemStatus
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Pattern 36: Direct Allocation
# ============================================================================


@dataclass(frozen=True)
class DirectAllocation:
    """YAWL Pattern 36: Direct Allocation.

    Task is assigned directly to a specific user. No offer phase - the work
    item goes straight from created to allocated state for the designated user.

    Java YAWL Requirements:
    - Work item created with specific participant
    - State transitions: created → allocated
    - No distribution to work queues
    - Authorization checked before allocation

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (36)
    name : str
        Pattern name

    Examples
    --------
    >>> from rdflib import Graph, URIRef
    >>> graph = Graph()
    >>> direct = DirectAllocation()
    >>> result = direct.allocate(graph, URIRef("urn:task:SignContract"), "user:ceo")
    >>> assert result.success
    >>> assert result.status == WorkItemStatus.ALLOCATED
    """

    pattern_id: int = 36
    name: str = "Direct Allocation"

    def allocate(self, graph: Graph, task: URIRef, user: str) -> AllocationResult:
        """Allocate task directly to specific user.

        Parameters
        ----------
        graph : Graph
            RDF workflow graph with task definitions
        task : URIRef
            Task to allocate
        user : str
            User identifier (e.g., "user:alice")

        Returns
        -------
        AllocationResult
            Allocation result with status and metadata

        Raises
        ------
        ValueError
            If user identifier is invalid

        Examples
        --------
        >>> graph = Graph()
        >>> direct = DirectAllocation()
        >>> result = direct.allocate(graph, URIRef("urn:task:T1"), "user:bob")
        >>> assert result.allocated_to == "user:bob"
        """
        if not user or not isinstance(user, str):
            msg = f"Invalid user identifier: {user}"
            raise ValueError(msg)

        logger.info(
            "Direct allocation",
            extra={"task": str(task), "user": user, "pattern_id": self.pattern_id},
        )

        # Mark task as allocated to user
        graph.add((task, YawlNamespace.YAWL.allocatedTo, Literal(user)))
        graph.add(
            (task, YawlNamespace.YAWL.status, Literal(WorkItemStatus.ALLOCATED.value))
        )
        graph.add(
            (task, YawlNamespace.YAWL.allocationPattern, Literal(str(self.pattern_id)))
        )

        return AllocationResult(
            success=True,
            task=task,
            allocated_to=user,
            status=WorkItemStatus.ALLOCATED,
            message=f"Task {task} directly allocated to {user}",
            metadata={"pattern": self.name, "pattern_id": self.pattern_id},
        )


# ============================================================================
# Pattern 37: Role-Based Allocation (RBAC)
# ============================================================================


@dataclass(frozen=True)
class RoleBasedAllocation:
    """YAWL Pattern 37: Role-Based Allocation (RBAC).

    Task is offered to all users with a specific role. Any eligible user can
    claim the task, moving it from offered to allocated state.

    Java YAWL Requirements:
    - Query organizational model for role membership
    - Offer work item to all role members
    - Support claim operation (user pulls from work queue)
    - Track offer list and allocation timestamp

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (37)
    name : str
        Pattern name

    Examples
    --------
    >>> from rdflib import Graph, URIRef, Literal, Namespace
    >>> graph = Graph()
    >>> ROLE = Namespace("urn:org:role:")
    >>> USER = Namespace("urn:org:user:")
    >>>
    >>> # Define role membership
    >>> graph.add((USER.alice, ROLE.hasRole, Literal("role:Manager")))
    >>> graph.add((USER.bob, ROLE.hasRole, Literal("role:Manager")))
    >>>
    >>> rbac = RoleBasedAllocation()
    >>> # Offer task to role
    >>> result = rbac.offer(graph, URIRef("urn:task:Approve"), "role:Manager")
    >>> assert result.success
    >>>
    >>> # Get eligible users
    >>> users = rbac.get_eligible_users(
    ...     graph, URIRef("urn:task:Approve"), "role:Manager"
    ... )
    >>> assert "urn:org:user:alice" in users
    >>>
    >>> # User claims task
    >>> claim = rbac.claim(graph, URIRef("urn:task:Approve"), "urn:org:user:alice")
    >>> assert claim.success
    >>> assert claim.allocated_to == "urn:org:user:alice"
    """

    pattern_id: int = 37
    name: str = "Role-Based Allocation"

    def get_eligible_users(self, graph: Graph, task: URIRef, role: str) -> list[str]:
        """Get all users eligible for task based on role membership.

        Parameters
        ----------
        graph : Graph
            RDF graph with organizational model
        task : URIRef
            Task requiring role
        role : str
            Role identifier (e.g., "role:Manager")

        Returns
        -------
        list[str]
            User URIs with the specified role

        Examples
        --------
        >>> from rdflib import Graph, Literal, Namespace
        >>> graph = Graph()
        >>> ROLE = Namespace("urn:org:role:")
        >>> USER = Namespace("urn:org:user:")
        >>> graph.add((USER.alice, ROLE.hasRole, Literal("role:Manager")))
        >>>
        >>> rbac = RoleBasedAllocation()
        >>> users = rbac.get_eligible_users(
        ...     graph, URIRef("urn:task:T1"), "role:Manager"
        ... )
        >>> assert len(users) >= 0
        """
        # Query for users with specified role
        query = f"""
        PREFIX role: <urn:org:role:>
        SELECT ?user WHERE {{
            ?user role:hasRole "{role}" .
        }}
        """
        results = graph.query(query)

        users = [
            str(cast(ResultRow, row).user)
            for row in results
            if hasattr(row, "user")
        ]

        logger.debug(
            "Eligible users for role",
            extra={"task": str(task), "role": role, "user_count": len(users)},
        )

        return users

    def offer(self, graph: Graph, task: URIRef, role: str) -> AllocationResult:
        """Offer task to all users with specified role.

        Parameters
        ----------
        graph : Graph
            RDF workflow graph
        task : URIRef
            Task to offer
        role : str
            Role identifier (e.g., "role:Approver")

        Returns
        -------
        AllocationResult
            Result with list of users task was offered to

        Examples
        --------
        >>> graph = Graph()
        >>> rbac = RoleBasedAllocation()
        >>> result = rbac.offer(graph, URIRef("urn:task:Review"), "role:Reviewer")
        >>> assert result.status == WorkItemStatus.OFFERED
        """
        eligible_users = self.get_eligible_users(graph, task, role)

        logger.info(
            "Offering task to role",
            extra={
                "task": str(task),
                "role": role,
                "eligible_count": len(eligible_users),
                "pattern_id": self.pattern_id,
            },
        )

        # Mark task as offered to role
        graph.add((task, YawlNamespace.YAWL.offeredTo, Literal(role)))
        graph.add(
            (task, YawlNamespace.YAWL.status, Literal(WorkItemStatus.OFFERED.value))
        )
        graph.add(
            (task, YawlNamespace.YAWL.allocationPattern, Literal(str(self.pattern_id)))
        )

        # Store eligible user list
        for user in eligible_users:
            graph.add((task, YAWL_RESOURCE.eligibleUser, Literal(user)))

        return AllocationResult(
            success=True,
            task=task,
            allocated_to=eligible_users,
            status=WorkItemStatus.OFFERED,
            message=f"Task {task} offered to role {role} ({len(eligible_users)} users)",
            metadata={
                "pattern": self.name,
                "pattern_id": self.pattern_id,
                "role": role,
                "eligible_users": eligible_users,
            },
        )

    def claim(self, graph: Graph, task: URIRef, user: str) -> AllocationResult:
        """User claims an offered task (pull from work queue).

        Parameters
        ----------
        graph : Graph
            RDF workflow graph
        task : URIRef
            Task to claim
        user : str
            User claiming the task

        Returns
        -------
        AllocationResult
            Result showing task is now allocated to user

        Raises
        ------
        PermissionError
            If user is not eligible to claim the task
        RuntimeError
            If task is not in OFFERED state

        Examples
        --------
        >>> graph = Graph()
        >>> rbac = RoleBasedAllocation()
        >>> # First offer to role
        >>> rbac.offer(graph, URIRef("urn:task:T1"), "role:Worker")
        >>> # User claims
        >>> result = rbac.claim(graph, URIRef("urn:task:T1"), "urn:org:user:alice")
        >>> assert result.status == WorkItemStatus.ALLOCATED
        """
        # Check task is in OFFERED state
        status_query = f"""
        PREFIX yawl: <{YawlNamespace.YAWL}>
        ASK {{
            <{task}> yawl:status "{WorkItemStatus.OFFERED.value}" .
        }}
        """
        if not graph.query(status_query).askAnswer:
            msg = f"Task {task} is not in OFFERED state"
            raise RuntimeError(msg)

        # Check user is eligible
        eligible_query = f"""
        PREFIX yawl-resource: <{YAWL_RESOURCE}>
        ASK {{
            <{task}> yawl-resource:eligibleUser "{user}" .
        }}
        """
        if not graph.query(eligible_query).askAnswer:
            msg = f"User {user} is not eligible to claim task {task}"
            raise PermissionError(msg)

        logger.info(
            "Task claimed",
            extra={"task": str(task), "user": user, "pattern_id": self.pattern_id},
        )

        # Update allocation
        graph.set(
            (task, YawlNamespace.YAWL.status, Literal(WorkItemStatus.ALLOCATED.value))
        )
        graph.add((task, YawlNamespace.YAWL.allocatedTo, Literal(user)))

        return AllocationResult(
            success=True,
            task=task,
            allocated_to=user,
            status=WorkItemStatus.ALLOCATED,
            message=f"Task {task} claimed by {user}",
            metadata={"pattern": self.name, "pattern_id": self.pattern_id},
        )


# ============================================================================
# Pattern 38: Deferred Allocation
# ============================================================================


@dataclass(frozen=True)
class DeferredAllocation:
    """YAWL Pattern 38: Deferred Allocation.

    Allocation decision is deferred until runtime, using workflow data or
    external service to determine the target user/role dynamically.

    Java YAWL Requirements:
    - Evaluate allocation expression at runtime
    - Support data-driven allocation (XPath, XQuery)
    - Allow external service invocation for allocation
    - Handle allocation failures gracefully

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (38)
    name : str
        Pattern name
    allocation_expression : str
        Expression to evaluate for determining allocation target

    Examples
    --------
    >>> from rdflib import Graph, URIRef
    >>> graph = Graph()
    >>> deferred = DeferredAllocation(allocation_expression="data['assigned_manager']")
    >>> context = {"assigned_manager": "user:alice"}
    >>> result = deferred.allocate(graph, URIRef("urn:task:T1"), context)
    >>> assert result.allocated_to == "user:alice"
    """

    pattern_id: int = 38
    name: str = "Deferred Allocation"
    allocation_expression: str = "data['allocated_user']"

    def allocate(
        self, graph: Graph, task: URIRef, context: dict[str, Any]
    ) -> AllocationResult:
        """Allocate task using runtime-evaluated expression.

        Parameters
        ----------
        graph : Graph
            RDF workflow graph
        task : URIRef
            Task to allocate
        context : dict[str, Any]
            Runtime data for expression evaluation

        Returns
        -------
        AllocationResult
            Allocation result with dynamically determined user

        Raises
        ------
        RuntimeError
            If allocation expression evaluation fails

        Examples
        --------
        >>> graph = Graph()
        >>> deferred = DeferredAllocation(allocation_expression="data['approver']")
        >>> ctx = {"approver": "user:manager1"}
        >>> result = deferred.allocate(graph, URIRef("urn:task:Approve"), ctx)
        >>> assert result.allocated_to == "user:manager1"
        """
        try:
            # Evaluate allocation expression with context
            # Safe evaluation limited to data access
            allowed_names = {"data": context}
            allocated_to = eval(
                self.allocation_expression, {"__builtins__": {}}, allowed_names
            )

            if not allocated_to or not isinstance(allocated_to, str):
                msg = f"Invalid allocation target: {allocated_to}"
                raise RuntimeError(msg)

        except Exception as e:
            msg = f"Failed to evaluate allocation expression: {e}"
            logger.exception("Deferred allocation failed", extra={"task": str(task)})
            raise RuntimeError(msg) from e

        logger.info(
            "Deferred allocation",
            extra={
                "task": str(task),
                "allocated_to": allocated_to,
                "expression": self.allocation_expression,
                "pattern_id": self.pattern_id,
            },
        )

        # Apply allocation
        graph.add((task, YawlNamespace.YAWL.allocatedTo, Literal(allocated_to)))
        graph.add(
            (task, YawlNamespace.YAWL.status, Literal(WorkItemStatus.ALLOCATED.value))
        )
        graph.add(
            (task, YawlNamespace.YAWL.allocationPattern, Literal(str(self.pattern_id)))
        )

        return AllocationResult(
            success=True,
            task=task,
            allocated_to=allocated_to,
            status=WorkItemStatus.ALLOCATED,
            message=f"Task {task} allocated to {allocated_to} (deferred)",
            metadata={
                "pattern": self.name,
                "pattern_id": self.pattern_id,
                "expression": self.allocation_expression,
            },
        )


# ============================================================================
# Pattern 39: Authorization
# ============================================================================


@dataclass(frozen=True)
class Authorization:
    """YAWL Pattern 39: Authorization.

    Access control for task execution. Validates that user has required
    permissions, roles, or capabilities before allowing task operations.

    Java YAWL Requirements:
    - Check user privileges against task requirements
    - Support role-based and capability-based authorization
    - Validate at offer, allocate, start, and complete phases
    - Maintain audit trail of authorization decisions

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (39)
    name : str
        Pattern name
    required_capabilities : list[str]
        Capabilities required for task execution

    Examples
    --------
    >>> from rdflib import Graph, URIRef, Literal, Namespace
    >>> graph = Graph()
    >>> USER = Namespace("urn:org:user:")
    >>> graph.add((USER.alice, USER.hasCapability, Literal("sign_contracts")))
    >>>
    >>> authz = Authorization(required_capabilities=["sign_contracts"])
    >>> result = authz.check_authorization(
    ...     graph, URIRef("urn:task:SignContract"), "urn:org:user:alice"
    ... )
    >>> assert result.success
    """

    pattern_id: int = 39
    name: str = "Authorization"
    required_capabilities: list[str] = field(default_factory=list)

    def check_authorization(
        self, graph: Graph, task: URIRef, user: str
    ) -> AllocationResult:
        """Check if user is authorized to execute task.

        Parameters
        ----------
        graph : Graph
            RDF graph with user capabilities and task requirements
        task : URIRef
            Task requiring authorization
        user : str
            User requesting access

        Returns
        -------
        AllocationResult
            Authorization result (success=True if authorized)

        Examples
        --------
        >>> from rdflib import Graph, Literal, Namespace
        >>> graph = Graph()
        >>> USER = Namespace("urn:org:user:")
        >>> graph.add((USER.bob, USER.hasCapability, Literal("approve_requests")))
        >>>
        >>> authz = Authorization(required_capabilities=["approve_requests"])
        >>> result = authz.check_authorization(
        ...     graph, URIRef("urn:task:Approve"), "urn:org:user:bob"
        ... )
        >>> assert result.success
        """
        missing_capabilities = []

        for capability in self.required_capabilities:
            # Check if user has capability
            query = f"""
            PREFIX user: <urn:org:user:>
            ASK {{
                <{user}> user:hasCapability "{capability}" .
            }}
            """
            has_capability = graph.query(query).askAnswer

            if not has_capability:
                missing_capabilities.append(capability)

        authorized = len(missing_capabilities) == 0

        logger.info(
            "Authorization check",
            extra={
                "task": str(task),
                "user": user,
                "authorized": authorized,
                "missing": missing_capabilities,
                "pattern_id": self.pattern_id,
            },
        )

        if not authorized:
            return AllocationResult(
                success=False,
                task=task,
                allocated_to=user,
                status=WorkItemStatus.CREATED,
                message=f"User {user} not authorized: missing {missing_capabilities}",
                metadata={
                    "pattern": self.name,
                    "pattern_id": self.pattern_id,
                    "required_capabilities": self.required_capabilities,
                    "missing_capabilities": missing_capabilities,
                },
            )

        return AllocationResult(
            success=True,
            task=task,
            allocated_to=user,
            status=WorkItemStatus.ALLOCATED,
            message=f"User {user} authorized for task {task}",
            metadata={
                "pattern": self.name,
                "pattern_id": self.pattern_id,
                "required_capabilities": self.required_capabilities,
            },
        )


# ============================================================================
# Pattern 40: Separation of Duties (SoD)
# ============================================================================


class ConstraintType(str, Enum):
    """Separation of duties constraint types.

    Types
    -----
    FOUR_EYES
        Different users must perform related tasks (maker-checker)
    MUST_DO_SAME
        Same user must perform all related tasks
    MUST_DO_DIFFERENT
        Different users must perform each task
    """

    FOUR_EYES = "4-eyes"
    MUST_DO_SAME = "must-do-same"
    MUST_DO_DIFFERENT = "must-do-different"


@dataclass(frozen=True)
class SeparationOfDuties:
    """YAWL Pattern 40: Separation of Duties (SoD).

    Enforces constraints on who can perform related tasks. Critical for
    compliance and fraud prevention (e.g., maker-checker, 4-eyes principle).

    Java YAWL Requirements:
    - Track user history for related tasks
    - Validate constraints before allocation
    - Support multiple constraint types (4-eyes, same-user, different-user)
    - Maintain task relationship graph

    Parameters
    ----------
    pattern_id : int
        YAWL pattern identifier (40)
    name : str
        Pattern name
    constraint_type : str
        Type of separation constraint (see ConstraintType enum)
    related_tasks : list[str]
        Task URIs that are related for constraint checking

    Examples
    --------
    >>> from rdflib import Graph, URIRef
    >>> graph = Graph()
    >>>
    >>> # 4-eyes principle: Different users for submit and approve
    >>> sod = SeparationOfDuties(
    ...     constraint_type="4-eyes",
    ...     related_tasks=["urn:task:SubmitRequest", "urn:task:ApproveRequest"],
    ... )
    >>>
    >>> # Check if Alice can approve Bob's submission
    >>> valid = sod.check_constraint(
    ...     graph,
    ...     URIRef("urn:task:ApproveRequest"),
    ...     "user:alice",
    ...     ["user:bob"],  # Bob submitted
    ... )
    >>> assert valid  # Different users - constraint satisfied
    >>>
    >>> # Check if Bob can approve his own submission
    >>> invalid = sod.check_constraint(
    ...     graph,
    ...     URIRef("urn:task:ApproveRequest"),
    ...     "user:bob",
    ...     ["user:bob"],  # Bob submitted
    ... )
    >>> assert not invalid  # Same user - constraint violated
    """

    pattern_id: int = 40
    name: str = "Separation of Duties"
    constraint_type: str = ConstraintType.FOUR_EYES.value
    related_tasks: list[str] = field(default_factory=list)

    def check_constraint(
        self, graph: Graph, task: URIRef, user: str, history: list[str]
    ) -> bool:
        """Check if user assignment satisfies separation of duties constraint.

        Parameters
        ----------
        graph : Graph
            RDF workflow graph
        task : URIRef
            Task being assigned
        user : str
            User being assigned to task
        history : list[str]
            Users who performed related predecessor tasks

        Returns
        -------
        bool
            True if constraint is satisfied, False if violated

        Examples
        --------
        >>> graph = Graph()
        >>> sod = SeparationOfDuties(constraint_type="4-eyes")
        >>>
        >>> # Valid: Different users
        >>> assert sod.check_constraint(
        ...     graph, URIRef("urn:task:Approve"), "user:manager", ["user:employee"]
        ... )
        >>>
        >>> # Invalid: Same user (4-eyes violated)
        >>> assert not sod.check_constraint(
        ...     graph, URIRef("urn:task:Approve"), "user:employee", ["user:employee"]
        ... )
        """
        constraint_satisfied = True
        violation_reason = ""

        if self.constraint_type == ConstraintType.FOUR_EYES.value:
            # Different user must perform this task
            if user in history:
                constraint_satisfied = False
                violation_reason = (
                    f"4-eyes violated: {user} already performed related task"
                )

        elif self.constraint_type == ConstraintType.MUST_DO_SAME.value:
            # Same user must perform all related tasks
            if history and user not in history:
                constraint_satisfied = False
                violation_reason = (
                    f"Must-do-same violated: {user} not in history {history}"
                )

        elif self.constraint_type == ConstraintType.MUST_DO_DIFFERENT.value:
            # Each task must have different user
            if user in history:
                constraint_satisfied = False
                violation_reason = (
                    f"Must-do-different violated: {user} already in history"
                )

        logger.info(
            "Separation of duties check",
            extra={
                "task": str(task),
                "user": user,
                "constraint_type": self.constraint_type,
                "history": history,
                "satisfied": constraint_satisfied,
                "pattern_id": self.pattern_id,
            },
        )

        if not constraint_satisfied:
            logger.warning(
                "SoD constraint violation",
                extra={"task": str(task), "user": user, "reason": violation_reason},
            )

        return constraint_satisfied

    def validate_allocation(
        self, graph: Graph, task: URIRef, user: str
    ) -> AllocationResult:
        """Validate user allocation against separation of duties constraints.

        Parameters
        ----------
        graph : Graph
            RDF workflow graph with task history
        task : URIRef
            Task being allocated
        user : str
            User being allocated to task

        Returns
        -------
        AllocationResult
            Result indicating if allocation violates constraints

        Examples
        --------
        >>> from rdflib import Graph, URIRef, Literal, Namespace
        >>> graph = Graph()
        >>> YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
        >>>
        >>> # Record previous task execution
        >>> graph.add(
        ...     (URIRef("urn:task:Submit"), YAWL.completedBy, Literal("user:alice"))
        ... )
        >>>
        >>> sod = SeparationOfDuties(
        ...     constraint_type="4-eyes",
        ...     related_tasks=["urn:task:Submit", "urn:task:Approve"],
        ... )
        >>>
        >>> # Validate allocation
        >>> result = sod.validate_allocation(
        ...     graph, URIRef("urn:task:Approve"), "user:bob"
        ... )
        >>> assert result.success  # Different user - OK
        """
        # Query for users who completed related tasks
        history = []
        for related_task in self.related_tasks:
            query = f"""
            PREFIX yawl: <{YawlNamespace.YAWL}>
            SELECT ?user WHERE {{
                <{related_task}> yawl:completedBy ?user .
            }}
            """
            results = graph.query(query)
            history.extend(
                [
                    str(cast(ResultRow, row).user)
                    for row in results
                    if hasattr(row, "user")
                ]
            )

        # Check constraint
        satisfied = self.check_constraint(graph, task, user, history)

        if not satisfied:
            return AllocationResult(
                success=False,
                task=task,
                allocated_to=user,
                status=WorkItemStatus.CREATED,
                message=f"SoD constraint violated: {self.constraint_type}",
                metadata={
                    "pattern": self.name,
                    "pattern_id": self.pattern_id,
                    "constraint_type": self.constraint_type,
                    "history": history,
                    "related_tasks": self.related_tasks,
                },
            )

        return AllocationResult(
            success=True,
            task=task,
            allocated_to=user,
            status=WorkItemStatus.ALLOCATED,
            message=f"SoD constraint satisfied for user {user}",
            metadata={
                "pattern": self.name,
                "pattern_id": self.pattern_id,
                "constraint_type": self.constraint_type,
            },
        )
