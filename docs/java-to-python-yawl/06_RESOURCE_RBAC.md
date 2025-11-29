# Gap 6: Resource Service (RBAC)

## Problem Statement

YAWL has a sophisticated Resource Service for work item allocation with role-based access control. Currently, Python implementation uses simple user ID strings without roles, capabilities, or constraints.

## YAWL Resource Model

```
Participant (human user)
     │
     ├─► Roles (job functions)
     │     └─► Privileges (capabilities)
     │
     ├─► Positions (org chart)
     │     └─► Reports-to hierarchy
     │
     ├─► Capabilities (skills)
     │
     └─► OrgGroups (teams/departments)
```

## Current State

```python
# src/kgcl/yawl/engine/y_engine.py
def offer_work_item(self, work_item_id: str, resource_ids: list[str]) -> bool:
    """Offer work item to resources."""
    # Just sets resource_ids list - no validation
    work_item.resource_ids = resource_ids
    work_item.status = WorkItemStatus.OFFERED


def allocate_work_item(self, work_item_id: str, resource_id: str) -> bool:
    """Allocate work item to single resource."""
    # No role/capability check
    work_item.resource_id = resource_id
    work_item.status = WorkItemStatus.ALLOCATED
```

**Problems**:
- No resource definition (just string IDs)
- No role-based filtering
- No capability matching
- No delegation rules
- No workload balancing

## Target Behavior

```
Work Item needs resourcing
         │
         ▼
┌─────────────────────────────────┐
│  Get task's resourcing spec:    │
│  - Required roles               │
│  - Required capabilities        │
│  - Filters (constraints)        │
│  - Allocation strategy          │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Query resource service for     │
│  eligible participants          │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Apply distribution strategy:   │
│  - Offer to all eligible        │
│  - Round-robin allocation       │
│  - Shortest queue               │
│  - Random selection             │
└─────────────────────────────────┘
```

## Implementation Plan

### New Module: `src/kgcl/yawl/resource/`

```
src/kgcl/yawl/resource/
├── __init__.py
├── y_participant.py    # Participant/user definition
├── y_role.py          # Role definitions
├── y_capability.py    # Capability/skill definitions
├── y_org_data.py      # Organizational data (positions, groups)
├── y_resourcing.py    # Resourcing rules (task → participants)
└── y_resource_service.py  # Main service orchestrator
```

### Step 1: Core Resource Types

```python
# src/kgcl/yawl/resource/y_participant.py
"""Participant (human resource) definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kgcl.yawl.resource.y_role import YRole
    from kgcl.yawl.resource.y_capability import YCapability


@dataclass
class YParticipant:
    """Human participant (resource) in the workflow.

    Parameters
    ----------
    id : str
        Unique participant identifier
    userid : str
        Login username
    firstname : str
        First name
    lastname : str
        Last name
    admin : bool
        Whether participant has admin privileges
    roles : set[str]
        Role IDs assigned to participant
    capabilities : set[str]
        Capability IDs possessed by participant
    positions : set[str]
        Position IDs in org hierarchy
    """

    id: str
    userid: str
    firstname: str = ""
    lastname: str = ""
    admin: bool = False
    roles: set[str] = field(default_factory=set)
    capabilities: set[str] = field(default_factory=set)
    positions: set[str] = field(default_factory=set)

    @property
    def fullname(self) -> str:
        """Get full name."""
        return f"{self.firstname} {self.lastname}".strip() or self.userid

    def has_role(self, role_id: str) -> bool:
        """Check if participant has role."""
        return role_id in self.roles

    def has_capability(self, capability_id: str) -> bool:
        """Check if participant has capability."""
        return capability_id in self.capabilities

    def has_any_role(self, role_ids: set[str]) -> bool:
        """Check if participant has any of the roles."""
        return bool(self.roles & role_ids)

    def has_all_capabilities(self, capability_ids: set[str]) -> bool:
        """Check if participant has all capabilities."""
        return capability_ids <= self.capabilities


# src/kgcl/yawl/resource/y_role.py
"""Role definitions for RBAC."""

from dataclasses import dataclass, field


@dataclass
class YRole:
    """Role definition for role-based access control.

    Parameters
    ----------
    id : str
        Unique role identifier
    name : str
        Human-readable role name
    description : str
        Role description
    belongs_to : str | None
        Parent role ID for hierarchy
    """

    id: str
    name: str
    description: str = ""
    belongs_to: str | None = None


# src/kgcl/yawl/resource/y_capability.py
"""Capability/skill definitions."""

from dataclasses import dataclass


@dataclass
class YCapability:
    """Capability (skill) definition.

    Parameters
    ----------
    id : str
        Unique capability identifier
    name : str
        Capability name
    description : str
        Capability description
    category : str
        Category for grouping
    """

    id: str
    name: str
    description: str = ""
    category: str = ""
```

### Step 2: Resourcing Specification

```python
# src/kgcl/yawl/resource/y_resourcing.py
"""Resourcing rules for task-to-participant mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DistributionStrategy(Enum):
    """Work item distribution strategy."""

    OFFER_ALL = "offer_all"           # Offer to all eligible
    ROUND_ROBIN = "round_robin"       # Rotate allocation
    SHORTEST_QUEUE = "shortest_queue"  # Least busy resource
    RANDOM = "random"                 # Random selection
    DIRECT = "direct"                 # Direct allocation to named resource


class FilterType(Enum):
    """Filter type for constraining eligible resources."""

    ROLE = "role"
    CAPABILITY = "capability"
    POSITION = "position"
    ORG_GROUP = "org_group"
    PARTICIPANT = "participant"
    EXPRESSION = "expression"  # Custom filter expression


@dataclass
class ResourceFilter:
    """Filter for constraining eligible resources.

    Parameters
    ----------
    filter_type : FilterType
        Type of filter
    value : str
        Filter value (role ID, capability ID, etc.)
    negated : bool
        If True, exclude matching resources
    """

    filter_type: FilterType
    value: str
    negated: bool = False


@dataclass
class YResourcingSpec:
    """Resourcing specification for a task.

    Defines how work items for a task should be distributed.

    Parameters
    ----------
    offer_filters : list[ResourceFilter]
        Filters for initial offer set
    allocation_filters : list[ResourceFilter]
        Additional filters for allocation
    distribution : DistributionStrategy
        How to distribute work items
    constraints : dict[str, Any]
        Additional constraints (max workload, etc.)
    """

    offer_filters: list[ResourceFilter] = field(default_factory=list)
    allocation_filters: list[ResourceFilter] = field(default_factory=list)
    distribution: DistributionStrategy = DistributionStrategy.OFFER_ALL
    constraints: dict[str, Any] = field(default_factory=dict)

    def add_role_filter(self, role_id: str, negated: bool = False) -> None:
        """Add role-based filter."""
        self.offer_filters.append(
            ResourceFilter(FilterType.ROLE, role_id, negated)
        )

    def add_capability_filter(
        self, capability_id: str, negated: bool = False
    ) -> None:
        """Add capability-based filter."""
        self.offer_filters.append(
            ResourceFilter(FilterType.CAPABILITY, capability_id, negated)
        )
```

### Step 3: Resource Service

```python
# src/kgcl/yawl/resource/y_resource_service.py
"""Resource service for work item distribution."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from kgcl.yawl.resource.y_participant import YParticipant
from kgcl.yawl.resource.y_role import YRole
from kgcl.yawl.resource.y_capability import YCapability
from kgcl.yawl.resource.y_resourcing import (
    DistributionStrategy,
    FilterType,
    ResourceFilter,
    YResourcingSpec,
)

if TYPE_CHECKING:
    from kgcl.yawl.engine.y_work_item import YWorkItem


@dataclass
class YResourceService:
    """Service for managing resources and work item distribution.

    Parameters
    ----------
    participants : dict[str, YParticipant]
        All participants by ID
    roles : dict[str, YRole]
        All roles by ID
    capabilities : dict[str, YCapability]
        All capabilities by ID
    """

    participants: dict[str, YParticipant] = field(default_factory=dict)
    roles: dict[str, YRole] = field(default_factory=dict)
    capabilities: dict[str, YCapability] = field(default_factory=dict)

    # Workload tracking: participant_id → count of allocated items
    _workload: dict[str, int] = field(default_factory=dict, repr=False)

    # Round-robin state: spec_hash → last_index
    _round_robin_state: dict[str, int] = field(default_factory=dict, repr=False)

    # --- Participant Management ---

    def add_participant(self, participant: YParticipant) -> None:
        """Add participant to service."""
        self.participants[participant.id] = participant
        self._workload[participant.id] = 0

    def get_participant(self, participant_id: str) -> YParticipant | None:
        """Get participant by ID."""
        return self.participants.get(participant_id)

    def add_role(self, role: YRole) -> None:
        """Add role definition."""
        self.roles[role.id] = role

    def add_capability(self, capability: YCapability) -> None:
        """Add capability definition."""
        self.capabilities[capability.id] = capability

    def assign_role(self, participant_id: str, role_id: str) -> bool:
        """Assign role to participant."""
        participant = self.participants.get(participant_id)
        if participant and role_id in self.roles:
            participant.roles.add(role_id)
            return True
        return False

    def assign_capability(self, participant_id: str, capability_id: str) -> bool:
        """Assign capability to participant."""
        participant = self.participants.get(participant_id)
        if participant and capability_id in self.capabilities:
            participant.capabilities.add(capability_id)
            return True
        return False

    # --- Resourcing ---

    def get_eligible_participants(
        self,
        spec: YResourcingSpec,
    ) -> list[YParticipant]:
        """Get participants eligible based on resourcing spec.

        Parameters
        ----------
        spec : YResourcingSpec
            Resourcing specification with filters

        Returns
        -------
        list[YParticipant]
            Eligible participants
        """
        eligible = list(self.participants.values())

        for filter_ in spec.offer_filters:
            eligible = self._apply_filter(eligible, filter_)

        for filter_ in spec.allocation_filters:
            eligible = self._apply_filter(eligible, filter_)

        return eligible

    def _apply_filter(
        self,
        participants: list[YParticipant],
        filter_: ResourceFilter,
    ) -> list[YParticipant]:
        """Apply single filter to participant list."""
        result = []

        for p in participants:
            matches = self._matches_filter(p, filter_)

            # Include if matches and not negated, or doesn't match and negated
            if matches != filter_.negated:
                result.append(p)

        return result

    def _matches_filter(
        self,
        participant: YParticipant,
        filter_: ResourceFilter,
    ) -> bool:
        """Check if participant matches filter."""
        if filter_.filter_type == FilterType.ROLE:
            return participant.has_role(filter_.value)
        elif filter_.filter_type == FilterType.CAPABILITY:
            return participant.has_capability(filter_.value)
        elif filter_.filter_type == FilterType.POSITION:
            return filter_.value in participant.positions
        elif filter_.filter_type == FilterType.PARTICIPANT:
            return participant.id == filter_.value
        else:
            return True  # Unknown filter type: include

    def distribute_work_item(
        self,
        work_item_id: str,
        spec: YResourcingSpec,
    ) -> tuple[list[str], str | None]:
        """Distribute work item based on spec.

        Parameters
        ----------
        work_item_id : str
            Work item to distribute
        spec : YResourcingSpec
            Distribution specification

        Returns
        -------
        tuple[list[str], str | None]
            (offer_ids, allocation_id) - who to offer to, who to allocate
        """
        eligible = self.get_eligible_participants(spec)

        if not eligible:
            return [], None

        eligible_ids = [p.id for p in eligible]

        if spec.distribution == DistributionStrategy.OFFER_ALL:
            return eligible_ids, None

        elif spec.distribution == DistributionStrategy.ROUND_ROBIN:
            spec_key = str(id(spec))  # Simple hash
            last_idx = self._round_robin_state.get(spec_key, -1)
            next_idx = (last_idx + 1) % len(eligible)
            self._round_robin_state[spec_key] = next_idx
            return [], eligible_ids[next_idx]

        elif spec.distribution == DistributionStrategy.SHORTEST_QUEUE:
            # Find participant with lowest workload
            min_load = float("inf")
            selected = None
            for p_id in eligible_ids:
                load = self._workload.get(p_id, 0)
                if load < min_load:
                    min_load = load
                    selected = p_id
            return [], selected

        elif spec.distribution == DistributionStrategy.RANDOM:
            return [], random.choice(eligible_ids)

        elif spec.distribution == DistributionStrategy.DIRECT:
            # Direct: first eligible participant
            return [], eligible_ids[0] if eligible_ids else None

        return eligible_ids, None

    # --- Workload Tracking ---

    def on_work_item_allocated(self, participant_id: str) -> None:
        """Track work item allocation."""
        self._workload[participant_id] = self._workload.get(participant_id, 0) + 1

    def on_work_item_completed(self, participant_id: str) -> None:
        """Track work item completion."""
        if participant_id in self._workload:
            self._workload[participant_id] = max(
                0, self._workload[participant_id] - 1
            )

    def get_workload(self, participant_id: str) -> int:
        """Get current workload for participant."""
        return self._workload.get(participant_id, 0)
```

### Step 4: Task Resourcing Extension

```python
# src/kgcl/yawl/elements/y_atomic_task.py

from kgcl.yawl.resource.y_resourcing import YResourcingSpec

@dataclass
class YAtomicTask(YTask):
    # ... existing fields ...

    # Resourcing
    resourcing_spec: YResourcingSpec | None = None
```

### Step 5: Engine Integration

```python
# src/kgcl/yawl/engine/y_engine.py

from kgcl.yawl.resource.y_resource_service import YResourceService

@dataclass
class YEngine:
    # ... existing fields ...

    resource_service: YResourceService = field(default_factory=YResourceService)

    def _resource_work_item(
        self,
        work_item: YWorkItem,
        task: YTask,
    ) -> None:
        """Resource a work item based on task configuration."""
        work_item.fire()

        if isinstance(task, YAtomicTask) and task.is_automated():
            self._execute_automated_task(work_item, task)
            return

        # Get resourcing spec
        spec = None
        if isinstance(task, YAtomicTask):
            spec = task.resourcing_spec

        if spec is None:
            # Default: offer to all participants
            all_ids = list(self.resource_service.participants.keys())
            if all_ids:
                self.offer_work_item(work_item.id, all_ids)
            return

        # Use resource service to distribute
        offer_ids, allocate_id = self.resource_service.distribute_work_item(
            work_item.id, spec
        )

        if allocate_id:
            # Direct allocation
            self.allocate_work_item(work_item.id, allocate_id)
        elif offer_ids:
            # Offer to eligible participants
            self.offer_work_item(work_item.id, offer_ids)

    def allocate_work_item(self, work_item_id: str, resource_id: str) -> bool:
        """Allocate work item to resource with validation."""
        work_item = self._find_work_item(work_item_id)
        if work_item is None:
            return False

        # Validate resource exists
        participant = self.resource_service.get_participant(resource_id)
        if participant is None:
            return False

        # Perform allocation
        work_item.allocate(resource_id)

        # Track workload
        self.resource_service.on_work_item_allocated(resource_id)

        self._emit_event(
            "WORK_ITEM_ALLOCATED",
            work_item_id=work_item_id,
            resource_id=resource_id,
        )

        return True

    def complete_work_item(self, work_item_id, output_data=None) -> bool:
        """Complete work item with workload tracking."""
        work_item = self._find_work_item(work_item_id)
        if work_item is None:
            return False

        # Track workload
        if work_item.resource_id:
            self.resource_service.on_work_item_completed(work_item.resource_id)

        # ... existing completion logic ...
```

## Test Cases

```python
class TestResourceService:
    """Tests for resource service RBAC."""

    def test_role_filter_includes_matching(self) -> None:
        """Role filter includes participants with role."""
        # Add participant with "approver" role
        # Filter for "approver"
        # Assert: participant included

    def test_role_filter_excludes_non_matching(self) -> None:
        """Role filter excludes participants without role."""
        # Participant without "approver" role
        # Filter for "approver"
        # Assert: participant excluded

    def test_negated_filter(self) -> None:
        """Negated filter excludes matching participants."""
        # Filter for NOT "admin"
        # Assert: admin excluded, non-admin included

    def test_capability_filter(self) -> None:
        """Capability filter works correctly."""
        # Participant with "java" capability
        # Filter for "java"
        # Assert: included

    def test_round_robin_rotates(self) -> None:
        """Round robin allocates to each participant in turn."""
        # 3 participants
        # Distribute 3 times
        # Assert: each got one

    def test_shortest_queue_selects_least_busy(self) -> None:
        """Shortest queue selects participant with lowest workload."""
        # P1 has 5 items, P2 has 2 items
        # Distribute
        # Assert: P2 selected

    def test_multiple_filters_combine(self) -> None:
        """Multiple filters AND together."""
        # Filter: role="approver" AND capability="finance"
        # Only participant with both included

    def test_workload_tracking(self) -> None:
        """Workload increments/decrements correctly."""
        # Allocate → workload +1
        # Complete → workload -1
```

## Dependencies

- None (standalone module)

## Complexity: MEDIUM

- Role/capability model
- Filter combinations
- Distribution strategies
- Workload tracking

## Estimated Effort

- Implementation: 6-8 hours
- Testing: 4-6 hours
- Total: 1.5-2 days

## Priority: LOW-MEDIUM

Important for enterprise use but not blocking core execution.
