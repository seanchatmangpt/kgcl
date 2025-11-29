"""Case management (mirrors Java YCase concepts).

A case represents a running instance of a specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_identifier import YIdentifier
    from kgcl.yawl.engine.y_work_item import YWorkItem
    from kgcl.yawl.state.y_marking import YMarking


class CaseStatus(Enum):
    """Status of a case instance.

    Attributes
    ----------
    CREATED : auto
        Case created but not started
    RUNNING : auto
        Case is executing
    SUSPENDED : auto
        Case execution suspended
    COMPLETED : auto
        Case completed successfully
    FAILED : auto
        Case failed
    CANCELLED : auto
        Case was cancelled
    DEADLOCKED : auto
        Case reached deadlock
    """

    CREATED = auto()
    RUNNING = auto()
    SUSPENDED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    DEADLOCKED = auto()


@dataclass
class CaseData:
    """Data container for case variables.

    Parameters
    ----------
    variables : dict[str, Any]
        Net-level variables and their values
    input_data : dict[str, Any]
        Input data provided at case start
    output_data : dict[str, Any]
        Output data at case completion
    """

    variables: dict[str, Any] = field(default_factory=dict)
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)

    def get_variable(self, name: str) -> Any | None:
        """Get variable value.

        Parameters
        ----------
        name : str
            Variable name

        Returns
        -------
        Any | None
            Variable value or None
        """
        return self.variables.get(name)

    def set_variable(self, name: str, value: Any) -> None:
        """Set variable value.

        Parameters
        ----------
        name : str
            Variable name
        value : Any
            Variable value
        """
        self.variables[name] = value

    def merge_input(self, data: dict[str, Any]) -> None:
        """Merge input data.

        Parameters
        ----------
        data : dict[str, Any]
            Input data to merge
        """
        self.input_data.update(data)
        self.variables.update(data)


@dataclass
class CaseLog:
    """Log entry for case events.

    Parameters
    ----------
    timestamp : datetime
        When event occurred
    event : str
        Event type
    detail : str
        Event details
    data : dict[str, Any]
        Additional event data
    """

    timestamp: datetime
    event: str
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class YCase:
    """Running instance of a specification (mirrors Java case handling).

    A case represents a single execution of a workflow specification.
    It tracks the state of execution, work items, and case data.

    Parameters
    ----------
    id : str
        Unique case identifier
    specification_id : str
        ID of the specification being executed
    root_net_id : str
        ID of the root net
    status : CaseStatus
        Current status
    created : datetime
        Creation timestamp
    started : datetime | None
        Start timestamp
    completed : datetime | None
        Completion timestamp
    data : CaseData
        Case data
    work_items : dict[str, YWorkItem]
        Work items by ID
    active_work_items : set[str]
        IDs of active work items
    net_runners : dict[str, Any]
        Net runners by net ID (for sub-cases)
    parent_case_id : str | None
        Parent case ID (for sub-cases)
    sub_cases : list[str]
        IDs of sub-cases
    logs : list[CaseLog]
        Event log

    Examples
    --------
    >>> case = YCase(id="case-001", specification_id="spec-order-process", root_net_id="OrderNet")
    """

    id: str
    specification_id: str
    root_net_id: str

    # Status
    status: CaseStatus = CaseStatus.CREATED
    created: datetime = field(default_factory=datetime.now)
    started: datetime | None = None
    completed: datetime | None = None

    # Data
    data: CaseData = field(default_factory=CaseData)

    # Work items
    work_items: dict[str, Any] = field(default_factory=dict)  # YWorkItem
    active_work_items: set[str] = field(default_factory=set)

    # Net runners for sub-cases
    net_runners: dict[str, Any] = field(default_factory=dict)

    # Sub-case hierarchy
    parent_case_id: str | None = None
    sub_cases: list[str] = field(default_factory=list)

    # Logs
    logs: list[CaseLog] = field(default_factory=list)

    def start(self, input_data: dict[str, Any] | None = None) -> None:
        """Start case execution.

        Parameters
        ----------
        input_data : dict[str, Any] | None
            Input data for case
        """
        if input_data:
            self.data.merge_input(input_data)
        self.status = CaseStatus.RUNNING
        self.started = datetime.now()
        self._log("STARTED", "Case execution started")

    def complete(self, output_data: dict[str, Any] | None = None) -> None:
        """Complete case.

        Parameters
        ----------
        output_data : dict[str, Any] | None
            Output data from case
        """
        if output_data:
            self.data.output_data.update(output_data)
        self.status = CaseStatus.COMPLETED
        self.completed = datetime.now()
        self._log("COMPLETED", "Case completed successfully")

    def fail(self, reason: str = "") -> None:
        """Fail case.

        Parameters
        ----------
        reason : str
            Failure reason
        """
        self.status = CaseStatus.FAILED
        self.completed = datetime.now()
        self._log("FAILED", f"Case failed: {reason}")

    def cancel(self, reason: str = "") -> None:
        """Cancel case.

        Parameters
        ----------
        reason : str
            Cancellation reason
        """
        self.status = CaseStatus.CANCELLED
        self.completed = datetime.now()
        self._log("CANCELLED", f"Case cancelled: {reason}")
        # Cancel all active work items
        for wi_id in list(self.active_work_items):
            wi = self.work_items.get(wi_id)
            if wi and wi.is_active():
                wi.cancel(reason)

    def suspend(self, reason: str = "") -> None:
        """Suspend case execution.

        Parameters
        ----------
        reason : str
            Suspension reason
        """
        self.status = CaseStatus.SUSPENDED
        self._log("SUSPENDED", f"Case suspended: {reason}")

    def resume(self) -> None:
        """Resume suspended case."""
        self.status = CaseStatus.RUNNING
        self._log("RESUMED", "Case resumed")

    def add_work_item(self, work_item: Any) -> None:
        """Add work item to case.

        Parameters
        ----------
        work_item : YWorkItem
            Work item to add
        """
        work_item.case_id = self.id
        self.work_items[work_item.id] = work_item
        if work_item.is_active():
            self.active_work_items.add(work_item.id)
        self._log("WORK_ITEM_ADDED", f"Work item {work_item.id} added")

    def update_work_item_status(self, work_item_id: str) -> None:
        """Update tracking based on work item status.

        Parameters
        ----------
        work_item_id : str
            ID of work item that changed
        """
        work_item = self.work_items.get(work_item_id)
        if work_item:
            if work_item.is_finished():
                self.active_work_items.discard(work_item_id)
            elif work_item.is_active():
                self.active_work_items.add(work_item_id)

    def get_work_item(self, work_item_id: str) -> Any | None:
        """Get work item by ID.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        YWorkItem | None
            Work item or None
        """
        return self.work_items.get(work_item_id)

    def get_work_items_for_task(self, task_id: str) -> list[Any]:
        """Get all work items for a task.

        Parameters
        ----------
        task_id : str
            Task ID

        Returns
        -------
        list[YWorkItem]
            Work items for task
        """
        return [wi for wi in self.work_items.values() if wi.task_id == task_id]

    def get_active_work_items(self) -> list[Any]:
        """Get all active work items.

        Returns
        -------
        list[YWorkItem]
            Active work items
        """
        return [self.work_items[wi_id] for wi_id in self.active_work_items if wi_id in self.work_items]

    def add_sub_case(self, sub_case_id: str) -> None:
        """Add sub-case.

        Parameters
        ----------
        sub_case_id : str
            Sub-case ID
        """
        self.sub_cases.append(sub_case_id)
        self._log("SUB_CASE_ADDED", f"Sub-case {sub_case_id} added")

    def is_running(self) -> bool:
        """Check if case is running.

        Returns
        -------
        bool
            True if running
        """
        return self.status == CaseStatus.RUNNING

    def is_finished(self) -> bool:
        """Check if case is finished.

        Returns
        -------
        bool
            True if finished
        """
        return self.status in (CaseStatus.COMPLETED, CaseStatus.FAILED, CaseStatus.CANCELLED)

    def get_duration(self) -> float | None:
        """Get case duration in seconds.

        Returns
        -------
        float | None
            Duration or None if not complete
        """
        if self.started and self.completed:
            return (self.completed - self.started).total_seconds()
        return None

    def _log(self, event: str, detail: str, data: dict[str, Any] | None = None) -> None:
        """Add log entry.

        Parameters
        ----------
        event : str
            Event type
        detail : str
            Event details
        data : dict[str, Any] | None
            Additional data
        """
        self.logs.append(CaseLog(timestamp=datetime.now(), event=event, detail=detail, data=data or {}))

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality by ID."""
        if not isinstance(other, YCase):
            return NotImplemented
        return self.id == other.id


@dataclass
class CaseFactory:
    """Factory for creating cases.

    Parameters
    ----------
    id_prefix : str
        Prefix for case IDs
    counter : int
        Counter for generating unique IDs
    """

    id_prefix: str = "case"
    counter: int = 0

    def create_case(self, specification_id: str, root_net_id: str, case_id: str | None = None) -> YCase:
        """Create new case.

        Parameters
        ----------
        specification_id : str
            Specification ID
        root_net_id : str
            Root net ID
        case_id : str | None
            Optional specific ID

        Returns
        -------
        YCase
            New case instance
        """
        if case_id is None:
            self.counter += 1
            case_id = f"{self.id_prefix}-{self.counter:06d}"

        return YCase(id=case_id, specification_id=specification_id, root_net_id=root_net_id)

    def create_sub_case(self, parent_case: YCase, sub_net_id: str) -> YCase:
        """Create sub-case for composite task.

        Parameters
        ----------
        parent_case : YCase
            Parent case
        sub_net_id : str
            Sub-net ID

        Returns
        -------
        YCase
            New sub-case instance
        """
        self.counter += 1
        sub_case = YCase(
            id=f"{parent_case.id}.{self.counter}",
            specification_id=parent_case.specification_id,
            root_net_id=sub_net_id,
            parent_case_id=parent_case.id,
        )
        parent_case.add_sub_case(sub_case.id)
        return sub_case
