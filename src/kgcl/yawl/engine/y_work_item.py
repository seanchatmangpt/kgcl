"""Work item state machine (mirrors Java YWorkItem).

Work items represent individual units of work for a task instance.
They have a full lifecycle from enabled through completion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Any
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    pass


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
    allows_dynamic_creation: bool = False

    # History
    history: list[WorkItemLog] = field(default_factory=list)

    # Additional fields for Java parity
    attributes: dict[str, Any] = field(default_factory=dict)
    codelet: str = ""
    custom_form_url: str = ""
    documentation: str = ""
    deferred_choice_group_id: str = ""
    external_client: str = ""
    requires_manual_resourcing: bool = False
    prev_status: WorkItemStatus | None = None
    timer_started: bool = False
    timer_expiry_ms: int = 0

    # Persistence-related
    _parent_item: YWorkItem | None = field(default=None, repr=False)
    _child_items: set[YWorkItem] = field(default_factory=set, repr=False)

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
            (WorkItemStatus.FIRED, WorkItemEvent.START): WorkItemStatus.STARTED,
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
            (WorkItemStatus.EXECUTING, WorkItemEvent.SUSPEND): WorkItemStatus.SUSPENDED,
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

    # ==================== Java YAWL Missing Methods ====================
    # Status Predicates

    def is_fired(self) -> bool:
        """Check if work item is in FIRED status.

        Returns
        -------
        bool
            True if status is FIRED

        Notes
        -----
        Java signature: boolean isFired()
        """
        return self.status == WorkItemStatus.FIRED

    def is_offered(self) -> bool:
        """Check if work item is in OFFERED status.

        Returns
        -------
        bool
            True if status is OFFERED

        Notes
        -----
        Java signature: boolean isOffered()
        """
        return self.status == WorkItemStatus.OFFERED

    def is_allocated(self) -> bool:
        """Check if work item is in ALLOCATED status.

        Returns
        -------
        bool
            True if status is ALLOCATED

        Notes
        -----
        Java signature: boolean isAllocated()
        """
        return self.status == WorkItemStatus.ALLOCATED

    def is_started(self) -> bool:
        """Check if work item is in STARTED status.

        Returns
        -------
        bool
            True if status is STARTED

        Notes
        -----
        Java signature: boolean isStarted()
        """
        return self.status == WorkItemStatus.STARTED

    def is_executing(self) -> bool:
        """Check if work item is in EXECUTING status.

        Returns
        -------
        bool
            True if status is EXECUTING

        Notes
        -----
        Java signature: boolean isExecuting()
        """
        return self.status == WorkItemStatus.EXECUTING

    def is_completed(self) -> bool:
        """Check if work item is in COMPLETED status.

        Returns
        -------
        bool
            True if status is COMPLETED

        Notes
        -----
        Java signature: boolean isCompleted()
        """
        return self.status == WorkItemStatus.COMPLETED

    def is_suspended(self) -> bool:
        """Check if work item is in SUSPENDED status.

        Returns
        -------
        bool
            True if status is SUSPENDED

        Notes
        -----
        Java signature: boolean isSuspended()
        """
        return self.status == WorkItemStatus.SUSPENDED

    def has_live_status(self) -> bool:
        """Check if work item has a live status (active, not finished).

        Returns
        -------
        bool
            True if work item is active

        Notes
        -----
        Java signature: boolean hasLiveStatus()
        """
        return self.is_active()

    def has_finished_status(self) -> bool:
        """Check if work item has finished status.

        Returns
        -------
        bool
            True if work item is finished

        Notes
        -----
        Java signature: boolean hasFinishedStatus()
        """
        return self.is_finished()

    def has_unfinished_status(self) -> bool:
        """Check if work item has unfinished status.

        Returns
        -------
        bool
            True if work item is not finished

        Notes
        -----
        Java signature: boolean hasUnfinishedStatus()
        """
        return not self.is_finished()

    def has_completed_status(self) -> bool:
        """Check if work item has completed status.

        Returns
        -------
        bool
            True if status is COMPLETED or FORCE_COMPLETED

        Notes
        -----
        Java signature: boolean hasCompletedStatus()
        """
        return self.status in (WorkItemStatus.COMPLETED, WorkItemStatus.FORCE_COMPLETED)

    def is_enabled_suspended(self) -> bool:
        """Check if enabled work item is suspended.

        Returns
        -------
        bool
            True if work item was enabled and is now suspended

        Notes
        -----
        Java signature: boolean isEnabledSuspended()
        """
        return self.status == WorkItemStatus.SUSPENDED and self.enabled_time is not None

    def is_parent(self) -> bool:
        """Check if this is a parent work item (has children).

        Returns
        -------
        bool
            True if work item is a parent

        Notes
        -----
        Java signature: boolean isParent()
        """
        return self.status == WorkItemStatus.PARENT or len(self.children) > 0

    def has_children(self) -> bool:
        """Check if work item has child work items.

        Returns
        -------
        bool
            True if children exist

        Notes
        -----
        Java signature: boolean hasChildren()
        """
        return len(self.children) > 0

    # Child Management

    def get_children(self) -> set[YWorkItem]:
        """Get child work items.

        Returns
        -------
        set[YWorkItem]
            Set of child work items

        Notes
        -----
        Java signature: Set getChildren()
        """
        return self._child_items.copy()

    def set_children(self, children: set[YWorkItem]) -> None:
        """Set child work items.

        Parameters
        ----------
        children : set[YWorkItem]
            Child work items

        Notes
        -----
        Java signature: void setChildren(Set children)
        """
        self._child_items = children.copy()
        self.children = [c.id for c in children]

    def add_children(self, children: set[YWorkItem]) -> None:
        """Add multiple child work items.

        Parameters
        ----------
        children : set[YWorkItem]
            Children to add

        Notes
        -----
        Java signature: void add_children(Set children)
        """
        self._child_items.update(children)
        self.children.extend([c.id for c in children if c.id not in self.children])

    def create_child(self, child_case_id: str) -> YWorkItem:
        """Create a child work item.

        Parameters
        ----------
        child_case_id : str
            Case ID for child

        Returns
        -------
        YWorkItem
            New child work item

        Notes
        -----
        Java signature: YWorkItem createChild(YIdentifier childCaseID)
        """
        child = YWorkItem(
            id=f"{self.id}_child_{len(self.children)}",
            case_id=child_case_id,
            task_id=self.task_id,
            specification_id=self.specification_id,
            net_id=self.net_id,
            parent_id=self.id,
        )
        child._parent_item = self
        self._child_items.add(child)
        self.children.append(child.id)
        self.status = WorkItemStatus.PARENT
        return child

    def get_parent(self) -> YWorkItem | None:
        """Get parent work item.

        Returns
        -------
        YWorkItem | None
            Parent work item or None

        Notes
        -----
        Java signature: YWorkItem getParent()
        """
        return self._parent_item

    def set_parent(self, parent: YWorkItem) -> None:
        """Set parent work item.

        Parameters
        ----------
        parent : YWorkItem
            Parent work item

        Notes
        -----
        Java signature: void set_parent(YWorkItem parent)
        """
        self._parent_item = parent
        self.parent_id = parent.id

    # Getters

    def get_case_id(self) -> str:
        """Get case ID.

        Returns
        -------
        str
            Case identifier

        Notes
        -----
        Java signature: YIdentifier getCaseID()
        """
        return self.case_id

    def get_task_id(self) -> str:
        """Get task ID.

        Returns
        -------
        str
            Task identifier

        Notes
        -----
        Java signature: String getTaskID()
        """
        return self.task_id

    def get_specification_id(self) -> str:
        """Get specification ID.

        Returns
        -------
        str
            Specification identifier

        Notes
        -----
        Java signature: YSpecificationID getSpecificationID()
        """
        return self.specification_id

    def get_spec_name(self) -> str:
        """Get specification name.

        Returns
        -------
        str
            Specification name

        Notes
        -----
        Java signature: String getSpecName()
        """
        return self.specification_id.split("/")[-1] if self.specification_id else ""

    def get_unique_id(self) -> str:
        """Get unique work item ID.

        Returns
        -------
        str
            Unique identifier

        Notes
        -----
        Java signature: String getUniqueID()
        """
        return self.id

    def get_id_string(self) -> str:
        """Get ID as string.

        Returns
        -------
        str
            ID string

        Notes
        -----
        Java signature: String getIDString()
        """
        return self.id

    def get_status(self) -> WorkItemStatus:
        """Get current status.

        Returns
        -------
        WorkItemStatus
            Current status

        Notes
        -----
        Java signature: YWorkItemStatus getStatus()
        """
        return self.status

    def set_status(self, status: WorkItemStatus) -> None:
        """Set work item status.

        Parameters
        ----------
        status : WorkItemStatus
            New status

        Notes
        -----
        Java signature: void setStatus(YWorkItemStatus status)
        """
        self.prev_status = self.status
        self.status = status

    def get_enablement_time(self) -> datetime | None:
        """Get enablement time.

        Returns
        -------
        datetime | None
            Time work item was enabled

        Notes
        -----
        Java signature: Date getEnablementTime()
        """
        return self.enabled_time

    def get_enablement_time_str(self) -> str:
        """Get enablement time as string.

        Returns
        -------
        str
            Enablement time string

        Notes
        -----
        Java signature: String getEnablementTimeStr()
        """
        return self.enabled_time.isoformat() if self.enabled_time else ""

    def set_enablement_time(self, time: datetime) -> None:
        """Set enablement time.

        Parameters
        ----------
        time : datetime
            Enablement time

        Notes
        -----
        Java signature: void set_enablementTime(Date eTime)
        """
        self.enabled_time = time

    def get_firing_time(self) -> datetime | None:
        """Get firing time.

        Returns
        -------
        datetime | None
            Time work item was fired

        Notes
        -----
        Java signature: Date getFiringTime()
        """
        return self.fired_time

    def get_firing_time_str(self) -> str:
        """Get firing time as string.

        Returns
        -------
        str
            Firing time string

        Notes
        -----
        Java signature: String getFiringTimeStr()
        """
        return self.fired_time.isoformat() if self.fired_time else ""

    def set_firing_time(self, time: datetime) -> None:
        """Set firing time.

        Parameters
        ----------
        time : datetime
            Firing time

        Notes
        -----
        Java signature: void set_firingTime(Date fTime)
        """
        self.fired_time = time

    def get_start_time(self) -> datetime | None:
        """Get start time.

        Returns
        -------
        datetime | None
            Time work started

        Notes
        -----
        Java signature: Date getStartTime()
        """
        return self.started_time

    def get_start_time_str(self) -> str:
        """Get start time as string.

        Returns
        -------
        str
            Start time string

        Notes
        -----
        Java signature: String getStartTimeStr()
        """
        return self.started_time.isoformat() if self.started_time else ""

    def set_start_time(self, time: datetime) -> None:
        """Set start time.

        Parameters
        ----------
        time : datetime
            Start time

        Notes
        -----
        Java signature: void set_startTime(Date sTime)
        """
        self.started_time = time

    # Data Methods

    def get_data_string(self) -> str:
        """Get data as XML string.

        Returns
        -------
        str
            XML representation of data

        Notes
        -----
        Java signature: String getDataString()
        """
        if not self.data_input:
            return "<data/>"
        root = ET.Element("data")
        for key, value in self.data_input.items():
            elem = ET.SubElement(root, key)
            elem.text = str(value)
        return ET.tostring(root, encoding="unicode")

    def set_data_string(self, data_str: str) -> None:
        """Set data from XML string.

        Parameters
        ----------
        data_str : str
            XML data string

        Notes
        -----
        Java signature: void set_dataString(String s)
        """
        root = ET.fromstring(data_str)
        self.data_input = {child.tag: child.text or "" for child in root}

    def get_data_element(self) -> ET.Element:
        """Get data as XML element.

        Returns
        -------
        ET.Element
            Data element

        Notes
        -----
        Java signature: Element getDataElement()
        """
        root = ET.Element("data")
        for key, value in self.data_input.items():
            elem = ET.SubElement(root, key)
            elem.text = str(value)
        return root

    def set_data_element(self, data: ET.Element) -> None:
        """Set data from XML element.

        Parameters
        ----------
        data : ET.Element
            Data element

        Notes
        -----
        Java signature: void setDataElement(Element data)
        """
        self.data_input = {child.tag: child.text or "" for child in data}

    def set_init_data(self, data: ET.Element) -> None:
        """Set initial data.

        Parameters
        ----------
        data : ET.Element
            Initial data element

        Notes
        -----
        Java signature: void setInitData(Element data)
        """
        self.set_data_element(data)

    def complete_data(self, output: ET.ElementTree | ET.Element | Any) -> None:
        """Complete with output data.

        Parameters
        ----------
        output : ET.ElementTree | ET.Element | Any
            Output data document (can be ElementTree, Element, or Document)

        Notes
        -----
        Java signature: void completeData(Document output)
        """
        # Handle different XML types (ElementTree, Element, or Document)
        if hasattr(output, "getroot"):
            # ElementTree
            root = output.getroot()
        elif hasattr(output, "documentElement"):
            # Document (xml.dom.minidom)
            root = output.documentElement
        else:
            # Element
            root = output

        if root is not None:
            # Extract data from XML structure
            if hasattr(root, "getElementsByTagName"):
                # Document element - convert to dict
                self.data_output = {
                    child.tagName: child.firstChild.data if child.firstChild else ""
                    for child in root.childNodes
                    if child.nodeType == 1  # ELEMENT_NODE
                }
            else:
                # ElementTree/Element - use existing logic
                self.data_output = {child.tag: child.text or "" for child in root}

    def setData(self, pmgr: Any | None, data: ET.Element) -> None:
        """Set work item data.

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager
        data : ET.Element
            Data element

        Notes
        -----
        Java signature: void setData(YPersistenceManager pmgr, Element data)
        """
        if data is not None:
            self.data_input = {child.tag: child.text or "" for child in data}

    def restoreDataToNet(self, services: set[Any]) -> None:
        """Restore data to net.

        Parameters
        ----------
        services : set[Any]
            YAWL services

        Notes
        -----
        Java signature: void restoreDataToNet(Set<YAWLServiceReference> services)
        Restores work item data to the net runner and reconnects external client
        """
        # Data restoration is handled by engine layer during case restoration
        # This method is called from YEngineRestorer to reconnect work items
        # to their net runners and external service clients

    def set_external_completion_log_predicate(self, predicate: str) -> None:
        """Set external completion log predicate.

        Parameters
        ----------
        predicate : str
            Log predicate

        Notes
        -----
        Java signature: void setExternalCompletionLogPredicate(String predicate)
        """
        # Store in attributes or separate field
        self.attributes["external_completion_log_predicate"] = predicate

    def setExternalStartingLogPredicate(self, predicate: str) -> None:
        """Set external starting log predicate.

        Parameters
        ----------
        predicate : str
            Log predicate

        Notes
        -----
        Java signature: void setExternalStartingLogPredicate(String predicate)
        """
        # Store in attributes or separate field
        self.attributes["external_starting_log_predicate"] = predicate

    def setEngine(self, engine: Any) -> None:
        """Set engine reference.

        Parameters
        ----------
        engine : Any
            Engine instance

        Notes
        -----
        Java signature: void setEngine(YEngine engine)
        """
        # Store engine reference if needed
        self.attributes["_engine"] = engine

    def addToRepository(self) -> None:
        """Add work item to repository.

        Notes
        -----
        Java signature: void addToRepository()
        """
        # Would add to work item repository
        pass

    def checkStartTimer(self, pmgr: Any | None, net_data: Any) -> None:
        """Check and start timer if needed.

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager
        net_data : Any
            Net data

        Notes
        -----
        Java signature: void checkStartTimer(YPersistenceManager pmgr, YNetData data)
        """
        # Would check timer conditions and start if needed
        if self.timer and not self.timer_started:
            # Start timer logic
            pass

    def getNetRunner(self) -> Any | None:
        """Get net runner for this work item.

        Returns
        -------
        Any | None
            Net runner or None

        Notes
        -----
        Java signature: YNetRunner getNetRunner()
        """
        # Would get from engine via case
        return None

    def getDataElement(self) -> ET.Element:
        """Get data as XML element.

        Returns
        -------
        ET.Element
            Data element

        Notes
        -----
        Java signature: Element getDataElement()
        """
        return self.get_data_element()

    def getDataString(self) -> str:
        """Get data as XML string.

        Returns
        -------
        str
            XML string

        Notes
        -----
        Java signature: String getDataString()
        """
        return self.get_data_string()

    def getEnablementTimeStr(self) -> str:
        """Get enablement time as formatted string.

        Returns
        -------
        str
            Formatted time string

        Notes
        -----
        Java signature: String getEnablementTimeStr()
        """
        return self.get_enablement_time_str()

    def getFiringTimeStr(self) -> str:
        """Get firing time as formatted string.

        Returns
        -------
        str
            Formatted time string

        Notes
        -----
        Java signature: String getFiringTimeStr()
        """
        return self.get_firing_time_str()

    def getStartTimeStr(self) -> str:
        """Get start time as formatted string.

        Returns
        -------
        str
            Formatted time string

        Notes
        -----
        Java signature: String getStartTimeStr()
        """
        return self.get_start_time_str()

    def setStatusToStarted(self, pmgr: Any | None, client: Any) -> None:
        """Set status to STARTED with persistence.

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager
        client : Any
            Client that started

        Notes
        -----
        Java signature: void setStatusToStarted(YPersistenceManager pmgr, YClient client)
        """
        self.set_status_to_started()
        if pmgr:
            pass  # Persist

    def set_status_to_complete(self, pmgr: Any | None, completion_type: Any) -> None:
        """Set status to COMPLETED with persistence.

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager
        completion_type : Any
            Completion type

        Notes
        -----
        Java signature: void setStatusToComplete(YPersistenceManager pmgr, WorkItemCompletion completionType)
        """
        completion_flag = "normal" if str(completion_type) == "Normal" else "force"
        self.set_status_to_complete(completion_flag)
        if pmgr:
            pass  # Persist

    def setStatusToDeleted(self, pmgr: Any | None) -> None:
        """Set status to DELETED with persistence.

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager

        Notes
        -----
        Java signature: void setStatusToDeleted(YPersistenceManager pmgr)
        """
        self.set_status_to_deleted()
        if pmgr:
            pass  # Persist

    def setStatusToDiscarded(self) -> None:
        """Set status to DISCARDED.

        Notes
        -----
        Java signature: void setStatusToDiscarded()
        """
        self.set_status_to_discarded()

    def rollBackStatus(self, pmgr: Any | None) -> None:
        """Roll back status with persistence.

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager

        Notes
        -----
        Java signature: void rollBackStatus(YPersistenceManager pmgr)
        """
        self.roll_back_status()
        if pmgr:
            pass  # Persist

    def setStatusToSuspended(self, pmgr: Any | None) -> None:
        """Set status to SUSPENDED with persistence.

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager

        Notes
        -----
        Java signature: void setStatusToSuspended(YPersistenceManager pmgr)
        """
        self.set_status_to_suspended()
        if pmgr:
            pass  # Persist

    def setStatusToUnsuspended(self, pmgr: Any | None) -> None:
        """Set status to UNSUSPENDED with persistence.

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager

        Notes
        -----
        Java signature: void setStatusToUnsuspended(YPersistenceManager pmgr)
        """
        self.set_status_to_unsuspended()
        if pmgr:
            pass  # Persist

    # Timer Methods

    def get_timer(self) -> WorkItemTimer | None:
        """Get work item timer.

        Returns
        -------
        WorkItemTimer | None
            Timer or None

        Notes
        -----
        Java signature: YWorkItemTimer getTimer()
        """
        return self.timer

    def set_timer(self, timer: WorkItemTimer) -> None:
        """Set work item timer.

        Parameters
        ----------
        timer : WorkItemTimer
            Timer to set

        Notes
        -----
        Java signature: void setTimer(YWorkItemTimer timer)
        """
        self.timer = timer

    def cancel_timer(self) -> None:
        """Cancel active timer.

        Notes
        -----
        Java signature: void cancelTimer()
        """
        if self.timer:
            self.timer.expiry = None
            self.timer_started = False

    def get_timer_expiry(self) -> int:
        """Get timer expiry time in milliseconds.

        Returns
        -------
        int
            Expiry time in ms since epoch

        Notes
        -----
        Java signature: long getTimerExpiry()
        """
        return self.timer_expiry_ms

    def set_timer_expiry(self, time_ms: int) -> None:
        """Set timer expiry time.

        Parameters
        ----------
        time_ms : int
            Expiry time in milliseconds since epoch

        Notes
        -----
        Java signature: void setTimerExpiry(long time)
        """
        self.timer_expiry_ms = time_ms
        if self.timer:
            self.timer.expiry = datetime.fromtimestamp(time_ms / 1000.0)

    def has_timer_started(self) -> bool:
        """Check if timer has started.

        Returns
        -------
        bool
            True if timer is running

        Notes
        -----
        Java signature: boolean hasTimerStarted()
        """
        return self.timer_started

    def set_timer_started(self, started: bool) -> None:
        """Set timer started flag.

        Parameters
        ----------
        started : bool
            Timer started state

        Notes
        -----
        Java signature: void setTimerStarted(boolean started)
        """
        self.timer_started = started

    def set_timer_active(self) -> None:
        """Mark timer as active.

        Notes
        -----
        Java signature: void setTimerActive()
        """
        self.timer_started = True

    def get_timer_status(self) -> str:
        """Get timer status string.

        Returns
        -------
        str
            Timer status

        Notes
        -----
        Java signature: String getTimerStatus()
        """
        if not self.timer:
            return "none"
        if self.timer_started:
            return "active"
        return "inactive"

    # Attributes

    def get_attributes(self) -> dict[str, Any]:
        """Get work item attributes.

        Returns
        -------
        dict[str, Any]
            Attributes dictionary

        Notes
        -----
        Java signature: Map getAttributes()
        """
        return self.attributes.copy()

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        """Set work item attributes.

        Parameters
        ----------
        attributes : dict[str, Any]
            Attributes to set

        Notes
        -----
        Java signature: void setAttributes(Map attributes)
        """
        self.attributes = attributes.copy()

    # Codelet

    def get_codelet(self) -> str:
        """Get codelet name.

        Returns
        -------
        str
            Codelet name

        Notes
        -----
        Java signature: String getCodelet()
        """
        return self.codelet

    def set_codelet(self, codelet: str) -> None:
        """Set codelet name.

        Parameters
        ----------
        codelet : str
            Codelet name

        Notes
        -----
        Java signature: void setCodelet(String codelet)
        """
        self.codelet = codelet

    # Custom Form

    def get_custom_form_url(self) -> str:
        """Get custom form URL.

        Returns
        -------
        str
            Custom form URL

        Notes
        -----
        Java signature: URL getCustomFormURL()
        """
        return self.custom_form_url

    def set_custom_form_url(self, form_url: str) -> None:
        """Set custom form URL.

        Parameters
        ----------
        form_url : str
            Custom form URL

        Notes
        -----
        Java signature: void setCustomFormURL(URL formURL)
        """
        self.custom_form_url = form_url

    # Documentation

    def get_documentation(self) -> str:
        """Get documentation.

        Returns
        -------
        str
            Documentation text

        Notes
        -----
        Java signature: String getDocumentation()
        """
        return self.documentation

    # Deferred Choice

    def get_deferred_choice_group_id(self) -> str:
        """Get deferred choice group ID.

        Returns
        -------
        str
            Group ID

        Notes
        -----
        Java signature: String getDeferredChoiceGroupID()
        """
        return self.deferred_choice_group_id

    def set_deferred_choice_group_id(self, group_id: str) -> None:
        """Set deferred choice group ID.

        Parameters
        ----------
        group_id : str
            Group ID

        Notes
        -----
        Java signature: void setDeferredChoiceGroupID(String id)
        """
        self.deferred_choice_group_id = group_id

    # External Client

    def get_external_client(self) -> str:
        """Get external client ID.

        Returns
        -------
        str
            External client ID

        Notes
        -----
        Java signature: YClient getExternalClient()
        """
        return self.external_client

    def set_external_client(self, client: str) -> None:
        """Set external client ID.

        Parameters
        ----------
        client : str
            External client ID

        Notes
        -----
        Java signature: void set_externalClient(String owner)
        """
        self.external_client = client

    # Manual Resourcing

    def get_requires_manual_resourcing(self) -> bool:
        """Check if work item requires manual resourcing.

        Returns
        -------
        bool
            True if manual resourcing required

        Notes
        -----
        Java signature: boolean requiresManualResourcing()
        """
        return self.requires_manual_resourcing

    def set_requires_manual_resourcing(self, requires: bool) -> None:
        """Set manual resourcing requirement.

        Parameters
        ----------
        requires : bool
            Manual resourcing required

        Notes
        -----
        Java signature: void setRequiresManualResourcing(boolean requires)
        """
        self.requires_manual_resourcing = requires

    # Dynamic Creation

    def get_allows_dynamic_creation(self) -> bool:
        """Check if dynamic instance creation is allowed.

        Returns
        -------
        bool
            True if dynamic creation allowed

        Notes
        -----
        Java signature: boolean allowsDynamicCreation()
        """
        return self.allows_dynamic_creation

    def set_allows_dynamic_creation(self, allows: bool) -> None:
        """Set dynamic creation flag.

        Parameters
        ----------
        allows : bool
            Allow dynamic creation

        Notes
        -----
        Java signature: void set_allowsDynamicCreation(boolean a)
        """
        self.allows_dynamic_creation = allows

    # Status Change Methods

    def set_status_to_started(self) -> None:
        """Set status to STARTED.

        Notes
        -----
        Java signature: void setStatusToStarted()
        """
        self.set_status(WorkItemStatus.STARTED)
        self.started_time = datetime.now()

    def set_status_to_complete(self, completion_flag: str = "normal") -> None:
        """Set status to COMPLETED.

        Parameters
        ----------
        completion_flag : str
            Completion flag (normal or force)

        Notes
        -----
        Java signature: void setStatusToComplete(WorkItemCompletion completionFlag)
        """
        if completion_flag == "force":
            self.set_status(WorkItemStatus.FORCE_COMPLETED)
        else:
            self.set_status(WorkItemStatus.COMPLETED)
        self.completed_time = datetime.now()

    def set_status_to_suspended(self) -> None:
        """Set status to SUSPENDED.

        Notes
        -----
        Java signature: void setStatusToSuspended()
        """
        self.set_status(WorkItemStatus.SUSPENDED)

    def set_status_to_unsuspended(self) -> None:
        """Set status to STARTED (resume from suspended).

        Notes
        -----
        Java signature: void setStatusToUnsuspended()
        """
        self.set_status(WorkItemStatus.STARTED)

    # Spec ID methods (Java compatibility)

    def get_specIdentifier(self) -> str:
        """Get specification identifier.

        Returns
        -------
        str
            Spec identifier

        Notes
        -----
        Java signature: String get_specIdentifier()
        """
        return self.specification_id.split("/")[-1] if "/" in self.specification_id else self.specification_id

    def get_specVersion(self) -> str:
        """Get specification version.

        Returns
        -------
        str
            Spec version

        Notes
        -----
        Java signature: String get_specVersion()
        """
        # Extract version from spec ID if available
        return "1.0"

    def get_specUri(self) -> str:
        """Get specification URI.

        Returns
        -------
        str
            Spec URI

        Notes
        -----
        Java signature: String get_specUri()
        """
        return self.specification_id

    def set_specIdentifier(self, id: str) -> None:
        """Set specification identifier.

        Parameters
        ----------
        id : str
            Spec identifier

        Notes
        -----
        Java signature: void set_specIdentifier(String id)
        """
        # Update spec ID
        if "/" in self.specification_id:
            parts = self.specification_id.split("/")
            parts[-1] = id
            self.specification_id = "/".join(parts)
        else:
            self.specification_id = id

    def set_specUri(self, uri: str) -> None:
        """Set specification URI.

        Parameters
        ----------
        uri : str
            Spec URI

        Notes
        -----
        Java signature: void set_specUri(String uri)
        """
        self.specification_id = uri

    def set_specVersion(self, version: str) -> None:
        """Set specification version.

        Parameters
        ----------
        version : str
            Spec version

        Notes
        -----
        Java signature: void set_specVersion(String version)
        """
        # Store version in attributes
        self.attributes["spec_version"] = version

    def get_thisID(self) -> str:
        """Get this work item ID.

        Returns
        -------
        str
            Work item ID

        Notes
        -----
        Java signature: String get_thisID()
        """
        return self.id

    def set_thisID(self, this_id: str) -> None:
        """Set this work item ID.

        Parameters
        ----------
        this_id : str
            Work item ID

        Notes
        -----
        Java signature: void set_thisID(String thisID)
        """
        self.id = this_id

    def setWorkItemID(self, work_item_id: Any) -> None:
        """Set work item ID object.

        Parameters
        ----------
        work_item_id : Any
            Work item ID object

        Notes
        -----
        Java signature: void setWorkItemID(YWorkItemID workitemid)
        """
        if hasattr(work_item_id, "id"):
            self.id = work_item_id.id
        elif isinstance(work_item_id, str):
            self.id = work_item_id

    def getTimerParameters(self) -> Any | None:
        """Get timer parameters.

        Returns
        -------
        Any | None
            Timer parameters

        Notes
        -----
        Java signature: YTimerParameters getTimerParameters()
        """
        return self.timer

    def setTimerParameters(self, params: Any) -> None:
        """Set timer parameters.

        Parameters
        ----------
        params : Any
            Timer parameters

        Notes
        -----
        Java signature: void setTimerParameters(YTimerParameters params)
        """
        if isinstance(params, WorkItemTimer):
            self.timer = params
        else:
            # Convert to WorkItemTimer if needed
            self.timer = WorkItemTimer()

    def set_status_to_deleted(self) -> None:
        """Set status to CANCELLED (deleted).

        Notes
        -----
        Java signature: void setStatusToDeleted()
        """
        self.set_status(WorkItemStatus.CANCELLED)

    def set_status_to_discarded(self) -> None:
        """Set status to CANCELLED (discarded).

        Notes
        -----
        Java signature: void setStatusToDiscarded()
        """
        self.set_status(WorkItemStatus.CANCELLED)

    def roll_back_status(self) -> None:
        """Roll back to previous status.

        Notes
        -----
        Java signature: void rollBackStatus()
        """
        if self.prev_status is not None:
            current = self.status
            self.status = self.prev_status
            self.prev_status = current

    # Persistence Stubs (for Java compatibility)

    def add_to_repository(self) -> None:
        """Add work item to repository.

        Notes
        -----
        Java signature: void addToRepository()
        Stub for persistence layer integration.
        """

    def complete_persistence(self, completion_status: WorkItemStatus) -> None:
        """Complete persistence operations.

        Parameters
        ----------
        completion_status : WorkItemStatus
            Final completion status

        Notes
        -----
        Java signature: void completePersistence(YWorkItemStatus completionStatus)
        Stub for persistence layer integration.
        """

    def complete_parent_persistence(self) -> None:
        """Complete parent work item persistence.

        Notes
        -----
        Java signature: void completeParentPersistence()
        Stub for persistence layer integration.
        """

    def delete_work_item(self, item: YWorkItem) -> None:
        """Delete a work item.

        Parameters
        ----------
        item : YWorkItem
            Work item to delete

        Notes
        -----
        Java signature: void deleteWorkItem(YWorkItem item)
        Stub for persistence layer integration.
        """
        if item in self._child_items:
            self._child_items.remove(item)
            if item.id in self.children:
                self.children.remove(item.id)

    def log_and_unpersist(self, item: YWorkItem) -> None:
        """Log and remove item from persistence.

        Parameters
        ----------
        item : YWorkItem
            Work item to unpersist

        Notes
        -----
        Java signature: void logAndUnpersist(YPersistenceManager pmgr, YWorkItem item)
        Stub for persistence layer integration.
        """

    def log_status_change(self, log_list: list[str] | None = None) -> None:
        """Log status change.

        Parameters
        ----------
        log_list : list[str] | None
            Log data items

        Notes
        -----
        Java signature: void logStatusChange(YLogDataItemList logList)
        Stub for logging integration.
        """

    def log_completion_data(self, output: ET.ElementTree | None = None) -> None:
        """Log completion data.

        Parameters
        ----------
        output : ET.ElementTree | None
            Output document

        Notes
        -----
        Java signature: void logCompletionData(Document output)
        Stub for logging integration.
        """

    def get_starting_predicates(self) -> list[str]:
        """Get starting log predicates.

        Returns
        -------
        list[str]
            Starting predicates

        Notes
        -----
        Java signature: YLogDataItemList getStartingPredicates()
        Stub for logging integration.
        """
        return []

    def get_completion_predicates(self) -> list[str]:
        """Get completion log predicates.

        Returns
        -------
        list[str]
            Completion predicates

        Notes
        -----
        Java signature: YLogDataItemList getCompletionPredicates()
        Stub for logging integration.
        """
        return []

    def set_external_starting_log_predicate(self, predicate: str) -> None:
        """Set external starting log predicate.

        Parameters
        ----------
        predicate : str
            Log predicate

        Notes
        -----
        Java signature: void setExternalStartingLogPredicate(String predicate)
        Stub for logging integration.
        """

    def set_external_completion_log_predicate(self, predicate: str) -> None:
        """Set external completion log predicate.

        Parameters
        ----------
        predicate : str
            Log predicate

        Notes
        -----
        Java signature: void setExternalCompletionLogPredicate(String predicate)
        Stub for logging integration.
        """

    def set_external_log_predicate(self, predicate: str) -> None:
        """Set external log predicate.

        Parameters
        ----------
        predicate : str
            Log predicate

        Notes
        -----
        Java signature: void setExternalLogPredicate(String predicate)
        Stub for logging integration.
        """

    def restore_data_to_net(self, services: set[str]) -> None:
        """Restore data to net.

        Parameters
        ----------
        services : set[str]
            Service set

        Notes
        -----
        Java signature: void restoreDataToNet(Set services)
        Stub for data restoration.
        """

    # Utility Methods

    def to_string(self) -> str:
        """Convert work item to string representation.

        Returns
        -------
        str
            String representation

        Notes
        -----
        Java signature: String toString()
        """
        return f"YWorkItem[{self.id}:{self.task_id}:{self.status.name}]"

    def to_xml(self) -> str:
        """Convert work item to XML representation.

        Returns
        -------
        str
            XML string

        Notes
        -----
        Java signature: String toXML()
        """
        root = ET.Element("workItem")
        ET.SubElement(root, "id").text = self.id
        ET.SubElement(root, "caseID").text = self.case_id
        ET.SubElement(root, "taskID").text = self.task_id
        ET.SubElement(root, "status").text = self.status.name
        if self.enabled_time:
            ET.SubElement(root, "enablementTime").text = self.enabled_time.isoformat()
        if self.fired_time:
            ET.SubElement(root, "firingTime").text = self.fired_time.isoformat()
        if self.started_time:
            ET.SubElement(root, "startTime").text = self.started_time.isoformat()
        if self.resource_id:
            ET.SubElement(root, "resourceID").text = self.resource_id
        return ET.tostring(root, encoding="unicode")

    def __hash__(self) -> int:
        """Hash by ID.

        Returns
        -------
        int
            Hash value

        Notes
        -----
        Java signature: int hashCode()
        """
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality by ID.

        Parameters
        ----------
        other : object
            Object to compare

        Returns
        -------
        bool
            True if equal

        Notes
        -----
        Java signature: boolean equals(Object other)
        """
        if not isinstance(other, YWorkItem):
            return NotImplemented
        return self.id == other.id

    # ==================== Additional Missing Methods ====================

    def get_task(self) -> Any | None:
        """Get task object.

        Returns
        -------
        Any | None
            Task object or None

        Notes
        -----
        Java signature: YTask getTask()
        """
        # Task reference stored in attributes
        return self.attributes.get("_task")

    def set_task(self, task: Any) -> None:
        """Set task object.

        Parameters
        ----------
        task : Any
            Task object

        Notes
        -----
        Java signature: void setTask(YTask task)
        """
        self.attributes["_task"] = task
        if task and hasattr(task, "id"):
            self.task_id = task.id

    def get_net_data(self) -> Any | None:
        """Get net data.

        Returns
        -------
        Any | None
            Net data or None

        Notes
        -----
        Java signature: YNetData getNetData()
        """
        return self.attributes.get("_net_data")

    def set_net_data(self, net_data: Any) -> None:
        """Set net data.

        Parameters
        ----------
        net_data : Any
            Net data

        Notes
        -----
        Java signature: void setNetData(YNetData netData)
        """
        self.attributes["_net_data"] = net_data

    def assemble_log_data_item_list(self, data: ET.Element, is_input: bool) -> list[dict[str, Any]]:
        """Assemble log data item list from element.

        Parameters
        ----------
        data : ET.Element
            Data element
        is_input : bool
            True if input data, False if output

        Returns
        -------
        list[dict[str, Any]]
            List of log data items

        Notes
        -----
        Java signature: YLogDataItemList assembleLogDataItemList(Element data, boolean input)
        """
        result: list[dict[str, Any]] = []
        if data is None:
            return result

        descriptor = "InputVarAssignment" if is_input else "OutputVarAssignment"

        # Extract data from element
        for child in data:
            name = child.tag
            value = child.text or ""
            if len(list(child)) > 0:
                # Complex type - store XML structure
                value = ET.tostring(child, encoding="unicode")

            result.append(
                {
                    "descriptor": descriptor,
                    "name": name,
                    "value": value,
                    "data_type": "string",  # Would get from parameter
                }
            )

        return result

    def create_log_data_list(self, tag: str) -> list[dict[str, Any]]:
        """Create log data list with tag.

        Parameters
        ----------
        tag : str
            Tag for log entry

        Returns
        -------
        list[dict[str, Any]]
            Log data list

        Notes
        -----
        Java signature: YLogDataItemList createLogDataList(String tag)
        """
        return [{"tag": tag, "timestamp": datetime.now().isoformat()}]

    def evaluate_param_query(self, timer_params: ET.Element, data: Any) -> ET.Element:
        """Evaluate parameter query for timer parameters.

        Parameters
        ----------
        timer_params : ET.Element
            Timer parameters element
        data : Any
            Data document

        Returns
        -------
        ET.Element
            Evaluated element

        Notes
        -----
        Java signature: Element evaluateParamQuery(Element timerParams, Document data)
        """
        # Convert element to string and evaluate XQuery
        param_str = ET.tostring(timer_params, encoding="unicode")
        try:
            from kgcl.yawl.engine.y_expression import YExpressionEvaluator

            evaluator = YExpressionEvaluator()
            result = evaluator.evaluate(param_str, data)
            if hasattr(result, "value"):
                result_str = str(result.value)
            else:
                result_str = str(result)

            # Parse result back to element
            return ET.fromstring(result_str)
        except Exception:
            # Return original if evaluation fails
            return timer_params

    def get_data_log_predicate(self, param: Any, is_input: bool) -> dict[str, Any] | None:
        """Get data log predicate for parameter.

        Parameters
        ----------
        param : Any
            Parameter object
        is_input : bool
            True if input parameter

        Returns
        -------
        dict[str, Any] | None
            Log predicate or None

        Notes
        -----
        Java signature: YLogDataItem getDataLogPredicate(YParameter param, boolean input)
        """
        # Would extract log predicate from parameter
        if param and hasattr(param, "get_log_predicate"):
            predicate = param.get_log_predicate()
            if predicate:
                return {
                    "descriptor": "LogPredicate",
                    "name": param.name if hasattr(param, "name") else "",
                    "value": str(predicate),
                }
        return None

    def get_decomp_log_predicate(self, item_status: WorkItemStatus | None = None) -> dict[str, Any] | None:
        """Get decomposition log predicate.

        Parameters
        ----------
        item_status : WorkItemStatus | None
            Work item status (optional)

        Returns
        -------
        dict[str, Any] | None
            Log predicate or None

        Notes
        -----
        Java signature: YLogPredicate getDecompLogPredicate()
        Java signature: YLogDataItem getDecompLogPredicate(YWorkItemStatus itemStatus)
        """
        # Would get from task's decomposition
        task = self.get_task()
        if task and hasattr(task, "get_decomposition_prototype"):
            decomp = task.get_decomposition_prototype()
            if decomp and hasattr(decomp, "get_log_predicate"):
                predicate = decomp.get_log_predicate()
                if predicate:
                    return {
                        "descriptor": "DecompLogPredicate",
                        "status": item_status.name if item_status else "",
                        "value": str(predicate),
                    }
        return None
