"""Resource types for workflow assignment (mirrors Java resource service).

Resources in YAWL include roles, participants, positions, capabilities,
and organizational groups. These enable sophisticated work distribution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from kgcl.yawl.resources.y_distribution import (
    DistributionContext,
    DistributionStrategy,
    Distributor,
    ParticipantMetrics,
)
from kgcl.yawl.resources.y_filters import CompositeFilter, FilterContext, FilterExpression, WorkItemHistoryEntry

if TYPE_CHECKING:
    pass


class ResourceStatus(Enum):
    """Status of a resource.

    Attributes
    ----------
    AVAILABLE : auto
        Resource is available for work
    BUSY : auto
        Resource is currently busy
    UNAVAILABLE : auto
        Resource is unavailable
    ON_LEAVE : auto
        Resource is on leave
    """

    AVAILABLE = auto()
    BUSY = auto()
    UNAVAILABLE = auto()
    ON_LEAVE = auto()


@dataclass
class YRole:
    """Role definition (mirrors Java Role).

    A role represents a functional grouping that participants can hold.
    Roles are used for task assignment - a task might be offered to
    all participants with a specific role.

    Parameters
    ----------
    id : str
        Unique identifier
    name : str
        Human-readable name
    description : str
        Role description
    belongs_to_id : str | None
        Parent role ID (role hierarchy)
    participants : set[str]
        IDs of participants with this role

    Examples
    --------
    >>> role = YRole(id="R001", name="Order Reviewer")
    >>> role.add_participant("P001")
    """

    id: str
    name: str = ""
    description: str = ""
    belongs_to_id: str | None = None
    participants: set[str] = field(default_factory=set)

    def add_participant(self, participant_id: str) -> None:
        """Add participant to role.

        Parameters
        ----------
        participant_id : str
            Participant ID
        """
        self.participants.add(participant_id)

    def remove_participant(self, participant_id: str) -> None:
        """Remove participant from role.

        Parameters
        ----------
        participant_id : str
            Participant ID
        """
        self.participants.discard(participant_id)

    def has_participant(self, participant_id: str) -> bool:
        """Check if participant has role.

        Parameters
        ----------
        participant_id : str
            Participant ID

        Returns
        -------
        bool
            True if participant has role
        """
        return participant_id in self.participants

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)


@dataclass
class YPosition:
    """Position in organizational structure (mirrors Java Position).

    A position represents a job position that can be held by participants.
    Positions can form a hierarchy (reports-to relationship).

    Parameters
    ----------
    id : str
        Unique identifier
    name : str
        Position title
    description : str
        Position description
    reports_to_id : str | None
        Manager position ID
    org_group_id : str | None
        Organizational group ID
    participants : set[str]
        IDs of participants in this position

    Examples
    --------
    >>> position = YPosition(id="POS001", name="Senior Analyst")
    """

    id: str
    name: str = ""
    description: str = ""
    reports_to_id: str | None = None
    org_group_id: str | None = None
    participants: set[str] = field(default_factory=set)

    def add_participant(self, participant_id: str) -> None:
        """Add participant to position.

        Parameters
        ----------
        participant_id : str
            Participant ID
        """
        self.participants.add(participant_id)

    def remove_participant(self, participant_id: str) -> None:
        """Remove participant from position.

        Parameters
        ----------
        participant_id : str
            Participant ID
        """
        self.participants.discard(participant_id)

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)


@dataclass
class YCapability:
    """Capability/skill (mirrors Java Capability).

    A capability represents a skill or certification that participants
    can possess. Tasks can require specific capabilities.

    Parameters
    ----------
    id : str
        Unique identifier
    name : str
        Capability name
    description : str
        Capability description
    category : str
        Capability category
    participants : set[str]
        IDs of participants with this capability

    Examples
    --------
    >>> cap = YCapability(id="CAP001", name="Python Programming")
    """

    id: str
    name: str = ""
    description: str = ""
    category: str = ""
    participants: set[str] = field(default_factory=set)

    def add_participant(self, participant_id: str) -> None:
        """Add participant with capability.

        Parameters
        ----------
        participant_id : str
            Participant ID
        """
        self.participants.add(participant_id)

    def remove_participant(self, participant_id: str) -> None:
        """Remove participant capability.

        Parameters
        ----------
        participant_id : str
            Participant ID
        """
        self.participants.discard(participant_id)

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)


@dataclass
class YOrgGroup:
    """Organizational group (mirrors Java OrgGroup).

    An organizational group represents a department, team, or other
    organizational unit. Groups can be nested.

    Parameters
    ----------
    id : str
        Unique identifier
    name : str
        Group name
    description : str
        Group description
    group_type : str
        Type: "department", "team", "division", etc.
    belongs_to_id : str | None
        Parent group ID
    positions : set[str]
        Position IDs in this group

    Examples
    --------
    >>> group = YOrgGroup(id="ORG001", name="IT Department")
    """

    id: str
    name: str = ""
    description: str = ""
    group_type: str = "team"
    belongs_to_id: str | None = None
    positions: set[str] = field(default_factory=set)

    def add_position(self, position_id: str) -> None:
        """Add position to group.

        Parameters
        ----------
        position_id : str
            Position ID
        """
        self.positions.add(position_id)

    def remove_position(self, position_id: str) -> None:
        """Remove position from group.

        Parameters
        ----------
        position_id : str
            Position ID
        """
        self.positions.discard(position_id)

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)


@dataclass
class YParticipant:
    """Participant who performs work (mirrors Java Participant).

    A participant represents a human resource who can be assigned
    work items. Participants have roles, positions, and capabilities.

    Parameters
    ----------
    id : str
        Unique identifier
    user_id : str
        Login/user identifier
    first_name : str
        First name
    last_name : str
        Last name
    description : str
        Description
    notes : str
        Additional notes
    is_administrator : bool
        Whether participant is admin
    status : ResourceStatus
        Availability status
    roles : set[str]
        Role IDs held
    positions : set[str]
        Position IDs held
    capabilities : set[str]
        Capability IDs possessed
    privileges : set[str]
        System privileges
    attributes : dict[str, Any]
        Extended attributes

    Examples
    --------
    >>> participant = YParticipant(id="P001", user_id="jdoe", first_name="John", last_name="Doe")
    """

    id: str
    user_id: str = ""
    first_name: str = ""
    last_name: str = ""
    description: str = ""
    notes: str = ""
    is_administrator: bool = False
    status: ResourceStatus = ResourceStatus.AVAILABLE

    # Associations
    roles: set[str] = field(default_factory=set)
    positions: set[str] = field(default_factory=set)
    capabilities: set[str] = field(default_factory=set)

    # Privileges
    privileges: set[str] = field(default_factory=set)

    # Extended attributes
    attributes: dict[str, Any] = field(default_factory=dict)

    def get_full_name(self) -> str:
        """Get full name.

        Returns
        -------
        str
            Full name
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.user_id

    def add_role(self, role_id: str) -> None:
        """Add role to participant.

        Parameters
        ----------
        role_id : str
            Role ID
        """
        self.roles.add(role_id)

    def remove_role(self, role_id: str) -> None:
        """Remove role from participant.

        Parameters
        ----------
        role_id : str
            Role ID
        """
        self.roles.discard(role_id)

    def has_role(self, role_id: str) -> bool:
        """Check if participant has role.

        Parameters
        ----------
        role_id : str
            Role ID

        Returns
        -------
        bool
            True if has role
        """
        return role_id in self.roles

    def add_position(self, position_id: str) -> None:
        """Add position to participant.

        Parameters
        ----------
        position_id : str
            Position ID
        """
        self.positions.add(position_id)

    def remove_position(self, position_id: str) -> None:
        """Remove position from participant.

        Parameters
        ----------
        position_id : str
            Position ID
        """
        self.positions.discard(position_id)

    def has_position(self, position_id: str) -> bool:
        """Check if participant holds position.

        Parameters
        ----------
        position_id : str
            Position ID

        Returns
        -------
        bool
            True if holds position
        """
        return position_id in self.positions

    def add_capability(self, capability_id: str) -> None:
        """Add capability to participant.

        Parameters
        ----------
        capability_id : str
            Capability ID
        """
        self.capabilities.add(capability_id)

    def remove_capability(self, capability_id: str) -> None:
        """Remove capability from participant.

        Parameters
        ----------
        capability_id : str
            Capability ID
        """
        self.capabilities.discard(capability_id)

    def has_capability(self, capability_id: str) -> bool:
        """Check if participant has capability.

        Parameters
        ----------
        capability_id : str
            Capability ID

        Returns
        -------
        bool
            True if has capability
        """
        return capability_id in self.capabilities

    def add_privilege(self, privilege: str) -> None:
        """Add system privilege.

        Parameters
        ----------
        privilege : str
            Privilege name
        """
        self.privileges.add(privilege)

    def has_privilege(self, privilege: str) -> bool:
        """Check if participant has privilege.

        Parameters
        ----------
        privilege : str
            Privilege name

        Returns
        -------
        bool
            True if has privilege
        """
        return privilege in self.privileges

    def is_available(self) -> bool:
        """Check if participant is available.

        Returns
        -------
        bool
            True if available
        """
        return self.status == ResourceStatus.AVAILABLE

    def set_status(self, status: ResourceStatus) -> None:
        """Set availability status.

        Parameters
        ----------
        status : ResourceStatus
            New status
        """
        self.status = status

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)


@dataclass
class YResourceManager:
    """Manager for organizational resources (mirrors Java resource service).

    Provides central management of all resource types and supports
    resource queries for task assignment.

    Parameters
    ----------
    roles : dict[str, YRole]
        Roles by ID
    participants : dict[str, YParticipant]
        Participants by ID
    positions : dict[str, YPosition]
        Positions by ID
    capabilities : dict[str, YCapability]
        Capabilities by ID
    org_groups : dict[str, YOrgGroup]
        Organizational groups by ID

    Examples
    --------
    >>> manager = YResourceManager()
    >>> manager.add_role(YRole(id="R001", name="Reviewer"))
    >>> manager.add_participant(YParticipant(id="P001", user_id="jdoe"))
    """

    roles: dict[str, YRole] = field(default_factory=dict)
    participants: dict[str, YParticipant] = field(default_factory=dict)
    positions: dict[str, YPosition] = field(default_factory=dict)
    capabilities: dict[str, YCapability] = field(default_factory=dict)
    org_groups: dict[str, YOrgGroup] = field(default_factory=dict)

    # --- Role management ---

    def add_role(self, role: YRole) -> None:
        """Add role.

        Parameters
        ----------
        role : YRole
            Role to add
        """
        self.roles[role.id] = role

    def get_role(self, role_id: str) -> YRole | None:
        """Get role by ID.

        Parameters
        ----------
        role_id : str
            Role ID

        Returns
        -------
        YRole | None
            Role or None
        """
        return self.roles.get(role_id)

    def get_participants_for_role(self, role_id: str) -> list[YParticipant]:
        """Get all participants with a role.

        Parameters
        ----------
        role_id : str
            Role ID

        Returns
        -------
        list[YParticipant]
            Participants with role
        """
        role = self.roles.get(role_id)
        if role:
            return [self.participants[pid] for pid in role.participants if pid in self.participants]
        return []

    # --- Participant management ---

    def add_participant(self, participant: YParticipant) -> None:
        """Add participant.

        Parameters
        ----------
        participant : YParticipant
            Participant to add
        """
        self.participants[participant.id] = participant

    def get_participant(self, participant_id: str) -> YParticipant | None:
        """Get participant by ID.

        Parameters
        ----------
        participant_id : str
            Participant ID

        Returns
        -------
        YParticipant | None
            Participant or None
        """
        return self.participants.get(participant_id)

    def get_participant_by_user_id(self, user_id: str) -> YParticipant | None:
        """Get participant by user ID.

        Parameters
        ----------
        user_id : str
            User ID

        Returns
        -------
        YParticipant | None
            Participant or None
        """
        for p in self.participants.values():
            if p.user_id == user_id:
                return p
        return None

    def get_available_participants(self) -> list[YParticipant]:
        """Get all available participants.

        Returns
        -------
        list[YParticipant]
            Available participants
        """
        return [p for p in self.participants.values() if p.is_available()]

    # --- Position management ---

    def add_position(self, position: YPosition) -> None:
        """Add position.

        Parameters
        ----------
        position : YPosition
            Position to add
        """
        self.positions[position.id] = position

    def get_position(self, position_id: str) -> YPosition | None:
        """Get position by ID.

        Parameters
        ----------
        position_id : str
            Position ID

        Returns
        -------
        YPosition | None
            Position or None
        """
        return self.positions.get(position_id)

    def get_participants_for_position(self, position_id: str) -> list[YParticipant]:
        """Get participants in a position.

        Parameters
        ----------
        position_id : str
            Position ID

        Returns
        -------
        list[YParticipant]
            Participants in position
        """
        position = self.positions.get(position_id)
        if position:
            return [self.participants[pid] for pid in position.participants if pid in self.participants]
        return []

    # --- Capability management ---

    def add_capability(self, capability: YCapability) -> None:
        """Add capability.

        Parameters
        ----------
        capability : YCapability
            Capability to add
        """
        self.capabilities[capability.id] = capability

    def get_capability(self, capability_id: str) -> YCapability | None:
        """Get capability by ID.

        Parameters
        ----------
        capability_id : str
            Capability ID

        Returns
        -------
        YCapability | None
            Capability or None
        """
        return self.capabilities.get(capability_id)

    def get_participants_with_capability(self, capability_id: str) -> list[YParticipant]:
        """Get participants with a capability.

        Parameters
        ----------
        capability_id : str
            Capability ID

        Returns
        -------
        list[YParticipant]
            Participants with capability
        """
        cap = self.capabilities.get(capability_id)
        if cap:
            return [self.participants[pid] for pid in cap.participants if pid in self.participants]
        return []

    # --- Org group management ---

    def add_org_group(self, org_group: YOrgGroup) -> None:
        """Add organizational group.

        Parameters
        ----------
        org_group : YOrgGroup
            Group to add
        """
        self.org_groups[org_group.id] = org_group

    def get_org_group(self, org_group_id: str) -> YOrgGroup | None:
        """Get organizational group by ID.

        Parameters
        ----------
        org_group_id : str
            Group ID

        Returns
        -------
        YOrgGroup | None
            Group or None
        """
        return self.org_groups.get(org_group_id)

    # --- Assignment helpers ---

    def assign_role_to_participant(self, role_id: str, participant_id: str) -> bool:
        """Assign role to participant.

        Parameters
        ----------
        role_id : str
            Role ID
        participant_id : str
            Participant ID

        Returns
        -------
        bool
            True if successful
        """
        role = self.roles.get(role_id)
        participant = self.participants.get(participant_id)
        if role and participant:
            role.add_participant(participant_id)
            participant.add_role(role_id)
            return True
        return False

    def assign_position_to_participant(self, position_id: str, participant_id: str) -> bool:
        """Assign position to participant.

        Parameters
        ----------
        position_id : str
            Position ID
        participant_id : str
            Participant ID

        Returns
        -------
        bool
            True if successful
        """
        position = self.positions.get(position_id)
        participant = self.participants.get(participant_id)
        if position and participant:
            position.add_participant(participant_id)
            participant.add_position(position_id)
            return True
        return False

    def assign_capability_to_participant(self, capability_id: str, participant_id: str) -> bool:
        """Assign capability to participant.

        Parameters
        ----------
        capability_id : str
            Capability ID
        participant_id : str
            Participant ID

        Returns
        -------
        bool
            True if successful
        """
        capability = self.capabilities.get(capability_id)
        participant = self.participants.get(participant_id)
        if capability and participant:
            capability.add_participant(participant_id)
            participant.add_capability(capability_id)
            return True
        return False

    # --- Query helpers ---

    def find_participants(
        self,
        role_ids: set[str] | None = None,
        position_ids: set[str] | None = None,
        capability_ids: set[str] | None = None,
        available_only: bool = True,
    ) -> list[YParticipant]:
        """Find participants matching criteria.

        Parameters
        ----------
        role_ids : set[str] | None
            Required role IDs (any)
        position_ids : set[str] | None
            Required position IDs (any)
        capability_ids : set[str] | None
            Required capability IDs (all)
        available_only : bool
            Only include available participants

        Returns
        -------
        list[YParticipant]
            Matching participants
        """
        candidates = list(self.participants.values())

        # Filter by availability
        if available_only:
            candidates = [p for p in candidates if p.is_available()]

        # Filter by roles (any match)
        if role_ids:
            candidates = [p for p in candidates if p.roles & role_ids]

        # Filter by positions (any match)
        if position_ids:
            candidates = [p for p in candidates if p.positions & position_ids]

        # Filter by capabilities (all required)
        if capability_ids:
            candidates = [p for p in candidates if capability_ids <= p.capabilities]

        return candidates

    # --- RBAC Filter Methods (Gap 7) ---

    def find_participants_with_filters(
        self,
        filters: list[FilterExpression] | CompositeFilter | None,
        context: FilterContext,
        base_participants: list[YParticipant] | None = None,
    ) -> list[YParticipant]:
        """Find participants matching RBAC filter expressions.

        Parameters
        ----------
        filters : list[FilterExpression] | CompositeFilter | None
            Filter expressions to apply
        context : FilterContext
            Context for filter evaluation
        base_participants : list[YParticipant] | None
            Starting set of participants (all available if None)

        Returns
        -------
        list[YParticipant]
            Participants matching all filters
        """
        # Start with base participants or all available
        if base_participants is None:
            candidates = self.get_available_participants()
        else:
            candidates = list(base_participants)

        if not filters:
            return candidates

        # Apply filters
        if isinstance(filters, CompositeFilter):
            return [p for p in candidates if filters.evaluate(p, context)]

        # List of filter expressions - apply all (AND)
        result = []
        for participant in candidates:
            if all(f.evaluate(participant, context) for f in filters):
                result.append(participant)

        return result

    def apply_four_eyes_filter(
        self,
        participants: list[YParticipant],
        case_id: str,
        task_ids: set[str],
        work_item_history: list[WorkItemHistoryEntry],
    ) -> list[YParticipant]:
        """Apply four-eyes separation filter.

        Excludes participants who completed any of the specified tasks
        in the current case.

        Parameters
        ----------
        participants : list[YParticipant]
            Candidates to filter
        case_id : str
            Current case ID
        task_ids : set[str]
            Task IDs requiring separation
        work_item_history : list[WorkItemHistoryEntry]
            Work item completion history

        Returns
        -------
        list[YParticipant]
            Participants who haven't completed related tasks
        """
        if not task_ids or not work_item_history:
            return participants

        # Find participants who completed any four-eyes task in this case
        excluded_ids: set[str] = set()
        for entry in work_item_history:
            if entry.case_id == case_id and entry.task_id in task_ids:
                excluded_ids.add(entry.participant_id)

        # Exclude them
        return [p for p in participants if p.id not in excluded_ids]

    def apply_distribution_strategy(
        self,
        participants: list[YParticipant],
        strategy: DistributionStrategy,
        task_id: str,
        distribution_context: DistributionContext | None = None,
        participant_metrics: dict[str, ParticipantMetrics] | None = None,
    ) -> list[YParticipant]:
        """Apply distribution strategy to select participants.

        Parameters
        ----------
        participants : list[YParticipant]
            Available participants
        strategy : DistributionStrategy
            Distribution strategy
        task_id : str
            Task ID (for round robin tracking)
        distribution_context : DistributionContext | None
            Context for distribution (created if None)
        participant_metrics : dict[str, ParticipantMetrics] | None
            Metrics for participants (for queue/fastest strategies)

        Returns
        -------
        list[YParticipant]
            Selected participants
        """
        if not participants:
            return []

        # Create context if needed
        if distribution_context is None:
            distribution_context = DistributionContext(task_id=task_id, case_id="", metrics=participant_metrics or {})
        elif participant_metrics:
            distribution_context.metrics = participant_metrics

        # Create distributor and apply
        distributor = Distributor(strategy=strategy, context=distribution_context)

        return distributor.distribute(participants)

    def record_work_item_completion(
        self,
        case_id: str,
        task_id: str,
        work_item_id: str,
        participant_id: str,
        task_name: str = "",
        history: list[WorkItemHistoryEntry] | None = None,
    ) -> WorkItemHistoryEntry:
        """Record a work item completion for history tracking.

        Parameters
        ----------
        case_id : str
            Case ID
        task_id : str
            Task ID
        work_item_id : str
            Work item ID
        participant_id : str
            ID of completing participant
        task_name : str
            Task name for display
        history : list[WorkItemHistoryEntry] | None
            History list to append to

        Returns
        -------
        WorkItemHistoryEntry
            Created history entry
        """
        entry = WorkItemHistoryEntry(
            case_id=case_id,
            task_id=task_id,
            work_item_id=work_item_id,
            participant_id=participant_id,
            completed_at=datetime.now(),
            task_name=task_name,
        )

        if history is not None:
            history.append(entry)

        return entry

    def get_participant_metrics(self, participant_id: str, active_work_items: int = 0) -> ParticipantMetrics:
        """Get or create metrics for a participant.

        Parameters
        ----------
        participant_id : str
            Participant ID
        active_work_items : int
            Current active work item count

        Returns
        -------
        ParticipantMetrics
            Metrics for participant
        """
        return ParticipantMetrics(participant_id=participant_id, active_work_items=active_work_items)
