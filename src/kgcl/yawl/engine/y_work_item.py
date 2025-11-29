"""Work item state machine (mirrors Java YWorkItem).

Work items represent individual units of work for a task instance.
They have a full lifecycle from enabled through completion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl.resources.y_resource import YParticipant


class WorkItemStatus(Enum):
    """Status of a work item in its lifecycle (mirrors Java YWorkItemStatus).

    The work item lifecycle follows this state machine:

    ENABLED → FIRED → EXECUTING → COMPLETED
              ↓           ↓
         OFFERED    SUSPENDED
              ↓           ↓
         ALLOCATED  FAILED
              ↓
         STARTED

    Attributes
    ----------
    ENABLED : auto
        Task enabled, work item created
    FIRED : auto
        Task fired, ready for resourcing
    OFFERED : auto
        Offered to participants
    ALLOCATED : auto
        Allocated to specific participant
    STARTED : auto
        Work has begun
    SUSPENDED : auto
        Work temporarily suspended
    EXECUTING : auto
        System task executing
    COMPLETED : auto
        Work completed successfully
    FAILED : auto
        Work failed
    CANCELLED : auto
        Work item cancelled
    FORCE_COMPLETED : auto
        Administratively completed
    PARENT : auto
        Parent of child work items (MI tasks)
    DEADLOCKED : auto
        Work item is deadlocked
    """

    ENABLED = auto()
    FIRED = auto()
    OFFERED = auto()
    ALLOCATED = auto()
    STARTED = auto()
    SUSPENDED = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    FORCE_COMPLETED = auto()
    PARENT = auto()
    DEADLOCKED = auto()


class WorkItemEvent(Enum):
    """Events that trigger work item transitions.

    Attributes
    ----------
    ENABLE : auto
        Task becomes enabled
    FIRE : auto
        Task fires (token consumed)
    OFFER : auto
        Offer to participants
    ALLOCATE : auto
        Allocate to participant
    START : auto
        Start work
    SUSPEND : auto
        Suspend work
    RESUME : auto
        Resume suspended work
    COMPLETE : auto
        Complete work
    FAIL : auto
        Work failed
    CANCEL : auto
        Cancel work
    FORCE_COMPLETE : auto
        Administrative completion
    TIMEOUT : auto
        Timer expired
    SKIP : auto
        Skip the work item
    DELEGATE : auto
        Delegate to another participant
    REALLOCATE : auto
        Reallocate to different participant
    """

    ENABLE = auto()
    FIRE = auto()
    OFFER = auto()
    ALLOCATE = auto()
    START = auto()
    SUSPEND = auto()
    RESUME = auto()
    COMPLETE = auto()
    FAIL = auto()
    CANCEL = auto()
    FORCE_COMPLETE = auto()
    TIMEOUT = auto()
    SKIP = auto()
    DELEGATE = auto()
    REALLOCATE = auto()


@dataclass
class WorkItemTimer:
    """Timer associated with a work item.

    Parameters
    ----------
    trigger : str
        When timer starts: "OnEnabled", "OnAllocated", "OnStarted"
    duration : str
        Duration expression (ISO 8601 or expression)
    expiry : datetime | None
        Computed expiry time
    action : str
        Action on expiry: "complete", "fail", "notify"
    """

    trigger: str = "OnEnabled"
    duration: str = ""
    expiry: datetime | None = None
    action: str = "notify"

    def is_expired(self) -> bool:
        """Check if timer has expired.

        Returns
        -------
        bool
            True if past expiry time
        """
        if self.expiry is None:
            return False
        return datetime.now() > self.expiry


@dataclass
class WorkItemLog:
    """Log entry for work item history.

    Parameters
    ----------
    timestamp : datetime
        When event occurred
    event : WorkItemEvent
        Event that occurred
    from_status : WorkItemStatus
        Status before event
    to_status : WorkItemStatus
        Status after event
    participant_id : str | None
        Participant involved
    data : dict[str, Any]
        Additional event data
    """

    timestamp: datetime
    event: WorkItemEvent
    from_status: WorkItemStatus
    to_status: WorkItemStatus
    participant_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class YWorkItem:
    """Work item representing a unit of work (mirrors Java YWorkItem).

    A work item is created when a task becomes enabled. It tracks the
    lifecycle of that specific task execution, including who is working
    on it and its current state.

    Parameters
    ----------
    id : str
        Unique identifier
    case_id : str
        ID of containing case
    task_id : str
        ID of task this work item is for
    specification_id : str
        ID of specification
    net_id : str
        ID of net containing task
    status : WorkItemStatus
        Current status
    created : datetime
        Creation timestamp
    enabled_time : datetime | None
        When enabled
    fired_time : datetime | None
        When fired
    started_time : datetime | None
        When work started
    completed_time : datetime | None
        When completed
    data_input : dict[str, Any]
        Input data
    data_output : dict[str, Any]
        Output data
    resource_id : str | None
        ID of allocated resource/participant
    offered_to : set[str]
        IDs of participants work was offered to
    timer : WorkItemTimer | None
        Timer if configured
    parent_id : str | None
        Parent work item ID (for MI children)
    children : list[str]
        Child work item IDs (for MI parent)
    history : list[WorkItemLog]
        Event history

    Examples
    --------
    >>> wi = YWorkItem(id="wi-001", case_id="case-001", task_id="ReviewOrder")
    >>> wi.status
    <WorkItemStatus.ENABLED: 1>
    """

    id: str
    case_id: str
    task_id: str
    specification_id: str = ""
    net_id: str = ""

    # Status
    status: WorkItemStatus = WorkItemStatus.ENABLED
    created: datetime = field(default_factory=datetime.now)

    # Timestamps
    enabled_time: datetime | None = None
    fired_time: datetime | None = None
    started_time: datetime | None = None
    completed_time: datetime | None = None

    # Data
    data_input: dict[str, Any] = field(default_factory=dict)
    data_output: dict[str, Any] = field(default_factory=dict)

    # Resourcing
    resource_id: str | None = None
    offered_to: set[str] = field(default_factory=set)

    # Timer
    timer: WorkItemTimer | None = None

    # Multi-instance
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)

    # History
    history: list[WorkItemLog] = field(default_factory=list)

    # Private - allowed transitions
    _transitions: dict[tuple[WorkItemStatus, WorkItemEvent], WorkItemStatus] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        """Initialize state machine transitions."""
        self.enabled_time = self.created
        self._init_transitions()

    def _init_transitions(self) -> None:
        """Initialize valid state transitions."""
        self._transitions = {
            # From ENABLED
            (WorkItemStatus.ENABLED, WorkItemEvent.FIRE): WorkItemStatus.FIRED,
            (WorkItemStatus.ENABLED, WorkItemEvent.CANCEL): WorkItemStatus.CANCELLED,
            (WorkItemStatus.ENABLED, WorkItemEvent.SKIP): WorkItemStatus.COMPLETED,
            # From FIRED
            (WorkItemStatus.FIRED, WorkItemEvent.OFFER): WorkItemStatus.OFFERED,
            (WorkItemStatus.FIRED, WorkItemEvent.ALLOCATE): WorkItemStatus.ALLOCATED,
            (WorkItemStatus.FIRED, WorkItemEvent.START): WorkItemStatus.EXECUTING,
            (WorkItemStatus.FIRED, WorkItemEvent.CANCEL): WorkItemStatus.CANCELLED,
            # From OFFERED
            (WorkItemStatus.OFFERED, WorkItemEvent.ALLOCATE): WorkItemStatus.ALLOCATED,
            (WorkItemStatus.OFFERED, WorkItemEvent.CANCEL): WorkItemStatus.CANCELLED,
            (WorkItemStatus.OFFERED, WorkItemEvent.TIMEOUT): WorkItemStatus.FAILED,
            # From ALLOCATED
            (WorkItemStatus.ALLOCATED, WorkItemEvent.START): WorkItemStatus.STARTED,
            (WorkItemStatus.ALLOCATED, WorkItemEvent.REALLOCATE): WorkItemStatus.ALLOCATED,
            (WorkItemStatus.ALLOCATED, WorkItemEvent.DELEGATE): WorkItemStatus.OFFERED,
            (WorkItemStatus.ALLOCATED, WorkItemEvent.CANCEL): WorkItemStatus.CANCELLED,
            (WorkItemStatus.ALLOCATED, WorkItemEvent.TIMEOUT): WorkItemStatus.FAILED,
            # From STARTED
            (WorkItemStatus.STARTED, WorkItemEvent.COMPLETE): WorkItemStatus.COMPLETED,
            (WorkItemStatus.STARTED, WorkItemEvent.FAIL): WorkItemStatus.FAILED,
            (WorkItemStatus.STARTED, WorkItemEvent.SUSPEND): WorkItemStatus.SUSPENDED,
            (WorkItemStatus.STARTED, WorkItemEvent.CANCEL): WorkItemStatus.CANCELLED,
            (WorkItemStatus.STARTED, WorkItemEvent.TIMEOUT): WorkItemStatus.FAILED,
            (WorkItemStatus.STARTED, WorkItemEvent.FORCE_COMPLETE): WorkItemStatus.FORCE_COMPLETED,
            # From SUSPENDED
            (WorkItemStatus.SUSPENDED, WorkItemEvent.RESUME): WorkItemStatus.STARTED,
            (WorkItemStatus.SUSPENDED, WorkItemEvent.CANCEL): WorkItemStatus.CANCELLED,
            (WorkItemStatus.SUSPENDED, WorkItemEvent.FORCE_COMPLETE): WorkItemStatus.FORCE_COMPLETED,
            # From EXECUTING (system task)
            (WorkItemStatus.EXECUTING, WorkItemEvent.COMPLETE): WorkItemStatus.COMPLETED,
            (WorkItemStatus.EXECUTING, WorkItemEvent.FAIL): WorkItemStatus.FAILED,
            (WorkItemStatus.EXECUTING, WorkItemEvent.CANCEL): WorkItemStatus.CANCELLED,
            (WorkItemStatus.EXECUTING, WorkItemEvent.TIMEOUT): WorkItemStatus.FAILED,
        }

    def can_transition(self, event: WorkItemEvent) -> bool:
        """Check if transition is valid.

        Parameters
        ----------
        event : WorkItemEvent
            Event to check

        Returns
        -------
        bool
            True if transition is allowed
        """
        return (self.status, event) in self._transitions

    def transition(
        self, event: WorkItemEvent, participant_id: str | None = None, data: dict[str, Any] | None = None
    ) -> bool:
        """Execute state transition.

        Parameters
        ----------
        event : WorkItemEvent
            Event triggering transition
        participant_id : str | None
            Participant involved
        data : dict[str, Any] | None
            Additional event data

        Returns
        -------
        bool
            True if transition succeeded

        Raises
        ------
        ValueError
            If transition is not valid
        """
        if not self.can_transition(event):
            raise ValueError(f"Invalid transition: {self.status} + {event}")

        old_status = self.status
        new_status = self._transitions[(self.status, event)]
        self.status = new_status

        # Update timestamps
        now = datetime.now()
        if new_status == WorkItemStatus.FIRED:
            self.fired_time = now
        elif new_status in (WorkItemStatus.STARTED, WorkItemStatus.EXECUTING):
            self.started_time = now
        elif new_status in (
            WorkItemStatus.COMPLETED,
            WorkItemStatus.FORCE_COMPLETED,
            WorkItemStatus.FAILED,
            WorkItemStatus.CANCELLED,
        ):
            self.completed_time = now

        # Update resource
        if participant_id:
            self.resource_id = participant_id

        # Log
        self.history.append(
            WorkItemLog(
                timestamp=now,
                event=event,
                from_status=old_status,
                to_status=new_status,
                participant_id=participant_id,
                data=data or {},
            )
        )

        return True

    def fire(self) -> bool:
        """Fire the work item (token consumed).

        Returns
        -------
        bool
            True if successful
        """
        return self.transition(WorkItemEvent.FIRE)

    def offer(self, participant_ids: set[str]) -> bool:
        """Offer to participants.

        Parameters
        ----------
        participant_ids : set[str]
            IDs of participants to offer to

        Returns
        -------
        bool
            True if successful
        """
        self.offered_to = participant_ids.copy()
        return self.transition(WorkItemEvent.OFFER)

    def allocate(self, participant_id: str) -> bool:
        """Allocate to specific participant.

        Parameters
        ----------
        participant_id : str
            ID of participant

        Returns
        -------
        bool
            True if successful
        """
        return self.transition(WorkItemEvent.ALLOCATE, participant_id=participant_id)

    def start(self, participant_id: str | None = None) -> bool:
        """Start work on item.

        Parameters
        ----------
        participant_id : str | None
            ID of participant starting work

        Returns
        -------
        bool
            True if successful
        """
        return self.transition(WorkItemEvent.START, participant_id=participant_id)

    def complete(self, output_data: dict[str, Any] | None = None) -> bool:
        """Complete work item.

        Parameters
        ----------
        output_data : dict[str, Any] | None
            Output data from task

        Returns
        -------
        bool
            True if successful
        """
        if output_data:
            self.data_output.update(output_data)
        return self.transition(WorkItemEvent.COMPLETE, data=output_data)

    def fail(self, reason: str = "") -> bool:
        """Fail work item.

        Parameters
        ----------
        reason : str
            Failure reason

        Returns
        -------
        bool
            True if successful
        """
        return self.transition(WorkItemEvent.FAIL, data={"reason": reason})

    def suspend(self) -> bool:
        """Suspend work item.

        Returns
        -------
        bool
            True if successful
        """
        return self.transition(WorkItemEvent.SUSPEND)

    def resume(self) -> bool:
        """Resume suspended work item.

        Returns
        -------
        bool
            True if successful
        """
        return self.transition(WorkItemEvent.RESUME)

    def cancel(self, reason: str = "") -> bool:
        """Cancel work item.

        Parameters
        ----------
        reason : str
            Cancellation reason

        Returns
        -------
        bool
            True if successful
        """
        return self.transition(WorkItemEvent.CANCEL, data={"reason": reason})

    def delegate(self) -> bool:
        """Delegate work item back to offer.

        Returns
        -------
        bool
            True if successful
        """
        return self.transition(WorkItemEvent.DELEGATE)

    def reallocate(self, participant_id: str) -> bool:
        """Reallocate to different participant.

        Parameters
        ----------
        participant_id : str
            New participant ID

        Returns
        -------
        bool
            True if successful
        """
        return self.transition(WorkItemEvent.REALLOCATE, participant_id=participant_id)

    def skip(self) -> bool:
        """Skip work item.

        Returns
        -------
        bool
            True if successful
        """
        return self.transition(WorkItemEvent.SKIP)

    def force_complete(self, reason: str = "") -> bool:
        """Administratively complete work item.

        Parameters
        ----------
        reason : str
            Reason for force completion

        Returns
        -------
        bool
            True if successful
        """
        return self.transition(WorkItemEvent.FORCE_COMPLETE, data={"reason": reason})

    def is_active(self) -> bool:
        """Check if work item is active (in progress).

        Returns
        -------
        bool
            True if work is ongoing
        """
        return self.status in (
            WorkItemStatus.ENABLED,
            WorkItemStatus.FIRED,
            WorkItemStatus.OFFERED,
            WorkItemStatus.ALLOCATED,
            WorkItemStatus.STARTED,
            WorkItemStatus.EXECUTING,
            WorkItemStatus.SUSPENDED,
        )

    def is_finished(self) -> bool:
        """Check if work item is finished.

        Returns
        -------
        bool
            True if work is complete (success or failure)
        """
        return self.status in (
            WorkItemStatus.COMPLETED,
            WorkItemStatus.FORCE_COMPLETED,
            WorkItemStatus.FAILED,
            WorkItemStatus.CANCELLED,
        )

    def is_successful(self) -> bool:
        """Check if work completed successfully.

        Returns
        -------
        bool
            True if completed successfully
        """
        return self.status in (WorkItemStatus.COMPLETED, WorkItemStatus.FORCE_COMPLETED)

    def get_duration(self) -> float | None:
        """Get duration from start to completion in seconds.

        Returns
        -------
        float | None
            Duration or None if not complete
        """
        if self.started_time and self.completed_time:
            return (self.completed_time - self.started_time).total_seconds()
        return None

    def add_child(self, child_id: str) -> None:
        """Add child work item (for MI tasks).

        Parameters
        ----------
        child_id : str
            Child work item ID
        """
        self.children.append(child_id)
        self.status = WorkItemStatus.PARENT

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality by ID."""
        if not isinstance(other, YWorkItem):
            return NotImplemented
        return self.id == other.id
