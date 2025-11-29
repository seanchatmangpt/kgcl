"""Main YAWL engine orchestrator (mirrors Java YEngine).

The YEngine is the central coordinator for workflow execution,
managing specifications, cases, work items, and resources.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from io import IOBase
from typing import TYPE_CHECKING, Any
from xml.dom.minidom import Document, Element

from kgcl.yawl.clients.models import YSpecificationID
from kgcl.yawl.elements.y_identifier import YIdentifier
from kgcl.yawl.elements.y_specification import SpecificationStatus, YSpecification
from kgcl.yawl.engine.y_case import CaseFactory, CaseStatus, YCase
from kgcl.yawl.engine.y_net_runner import ExecutionStatus, FireResult, YNetRunner
from kgcl.yawl.engine.y_timer import TimerAction, TimerTrigger, YTimer, YTimerService
from kgcl.yawl.engine.y_work_item import WorkItemEvent, WorkItemStatus, YWorkItem
from kgcl.yawl.resources.y_distribution import DistributionContext, ParticipantMetrics
from kgcl.yawl.resources.y_filters import FilterContext, WorkItemHistoryEntry
from kgcl.yawl.resources.y_resource import YParticipant, YResourceManager
from kgcl.yawl.state.y_marking import YMarking

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_net import YNet
    from kgcl.yawl.elements.y_task import YTask


# === Type stubs for Java YAWL classes ===


@dataclass(frozen=True)
class YExternalClient:
    """External client that can interact with the engine.

    Mirrors Java YExternalClient.

    Parameters
    ----------
    id : str
        Client ID
    password : str
        Client password (hashed)
    documentation : str
        Client documentation
    """

    id: str
    password: str
    documentation: str = ""


@dataclass(frozen=True)
class YAWLServiceReference:
    """Reference to a YAWL service.

    Mirrors Java YAWLServiceReference.

    Parameters
    ----------
    service_id : str
        Service ID
    uri : str
        Service URI
    documentation : str
        Service documentation
    """

    service_id: str
    uri: str
    documentation: str = ""


@dataclass
class YClient:
    """Client reference (participant or service).

    Parameters
    ----------
    id : str
        Client ID
    """

    id: str


class WorkItemCompletion(Enum):
    """Work item completion type.

    Attributes
    ----------
    NORMAL : auto
        Normal completion
    FORCE : auto
        Force completion
    FAIL : auto
        Fail completion
    """

    NORMAL = auto()
    FORCE = auto()
    FAIL = auto()


@dataclass
class YNetData:
    """Net data container.

    Parameters
    ----------
    data : dict[str, Any]
        Data dictionary
    """

    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnnouncementContext:
    """Context for announcements.

    Parameters
    ----------
    events : list[str]
        Event list
    """

    events: list[str] = field(default_factory=list)


@dataclass
class YAnnouncer:
    """Event announcer.

    Parameters
    ----------
    listeners : list[Callable[[str], None]]
        Event listeners
    """

    listeners: list[Callable[[str], None]] = field(default_factory=list)


@dataclass
class YBuildProperties:
    """Build properties.

    Parameters
    ----------
    version : str
        Build version
    timestamp : datetime
        Build timestamp
    """

    version: str = "5.2"
    timestamp: datetime = field(default_factory=datetime.now)


class Status(Enum):
    """Engine status.

    Attributes
    ----------
    RUNNING : auto
        Engine running
    STOPPED : auto
        Engine stopped
    """

    RUNNING = auto()
    STOPPED = auto()


@dataclass
class InstanceCache:
    """Instance cache for persistence.

    Parameters
    ----------
    cache : dict[str, Any]
        Cache storage
    """

    cache: dict[str, Any] = field(default_factory=dict)


@dataclass
class YNetRunnerRepository:
    """Repository of net runners.

    Parameters
    ----------
    runners : dict[str, YNetRunner]
        Runners by key
    """

    runners: dict[str, YNetRunner] = field(default_factory=dict)


@dataclass
class YPersistenceManager:
    """Persistence manager.

    Parameters
    ----------
    transaction_active : bool
        Is transaction active
    """

    transaction_active: bool = False

    def start_transaction(self) -> bool:
        """Start transaction."""
        if not self.transaction_active:
            self.transaction_active = True
            return True
        return False

    def commit_transaction(self) -> None:
        """Commit transaction."""
        self.transaction_active = False

    def rollback_transaction(self) -> None:
        """Rollback transaction."""
        self.transaction_active = False

    def store_object(self, obj: object) -> None:
        """Store object."""

    def update_object(self, obj: object) -> None:
        """Update object."""

    def delete_object(self, obj: object) -> None:
        """Delete object."""


@dataclass
class YWorkItemRepository:
    """Repository of work items.

    Parameters
    ----------
    work_items : dict[str, YWorkItem]
        Work items by ID
    """

    work_items: dict[str, YWorkItem] = field(default_factory=dict)


@dataclass
class YSessionCache:
    """Session cache.

    Parameters
    ----------
    sessions : dict[str, dict[str, Any]]
        Sessions
    """

    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class YLogDataItemList:
    """Log data item list.

    Parameters
    ----------
    items : list[dict[str, Any]]
        Log items
    """

    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class YVerificationHandler:
    """Verification handler for spec validation.

    Parameters
    ----------
    errors : list[str]
        Verification errors
    """

    errors: list[str] = field(default_factory=list)


class InterfaceAManagementObserver:
    """Observer for Interface A management."""


class InterfaceBClientObserver:
    """Observer for Interface B events."""


class ObserverGateway:
    """Gateway for observers."""


class EngineStatus(Enum):
    """Status of the engine.

    Attributes
    ----------
    STOPPED : auto
        Engine is stopped
    STARTING : auto
        Engine is starting up
    RUNNING : auto
        Engine is running
    PAUSED : auto
        Engine is paused
    STOPPING : auto
        Engine is stopping
    """

    STOPPED = auto()
    STARTING = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPING = auto()


@dataclass
class EngineEvent:
    """Event emitted by the engine.

    Parameters
    ----------
    event_type : str
        Type of event
    timestamp : datetime
        When event occurred
    case_id : str | None
        Related case ID
    work_item_id : str | None
        Related work item ID
    task_id : str | None
        Related task ID
    participant_id : str | None
        Related participant ID
    data : dict[str, Any]
        Additional event data
    """

    event_type: str
    timestamp: datetime
    case_id: str | None = None
    work_item_id: str | None = None
    task_id: str | None = None
    participant_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubCaseContext:
    """Context for a sub-case (composite task execution).

    When a composite task fires, it launches a sub-case for its
    decomposed subnet. This context tracks the relationship.

    Parameters
    ----------
    sub_case_id : str
        ID of the sub-case
    parent_case_id : str
        ID of the parent case
    parent_work_item_id : str
        ID of the parent work item (composite task)
    composite_task_id : str
        ID of the composite task
    subnet_id : str
        ID of the decomposed subnet
    started : datetime
        When sub-case was started
    """

    sub_case_id: str
    parent_case_id: str
    parent_work_item_id: str
    composite_task_id: str
    subnet_id: str
    started: datetime = field(default_factory=datetime.now)


@dataclass
class YEngine:
    """Main YAWL workflow engine (mirrors Java YEngine).

    The YEngine is the central orchestrator for workflow execution.
    It manages:
    - Specification loading and lifecycle
    - Case creation and execution
    - Work item lifecycle
    - Resource assignment
    - Event notification

    Parameters
    ----------
    engine_id : str
        Unique engine identifier
    status : EngineStatus
        Current engine status
    specifications : dict[str, YSpecification]
        Loaded specifications by ID
    cases : dict[str, YCase]
        Running cases by ID
    net_runners : dict[str, YNetRunner]
        Net runners by case+net ID
    resource_manager : YResourceManager
        Resource manager
    case_factory : CaseFactory
        Factory for creating cases
    work_item_counter : int
        Counter for work item IDs
    event_listeners : list[Callable[[EngineEvent], None]]
        Event listeners
    started : datetime | None
        Engine start time

    Examples
    --------
    >>> engine = YEngine()
    >>> engine.start()
    >>> spec = engine.load_specification(my_spec)
    >>> case = engine.create_case(spec.id)
    >>> engine.start_case(case.id)
    """

    engine_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: EngineStatus = EngineStatus.STOPPED

    # Specifications
    specifications: dict[str, YSpecification] = field(default_factory=dict)

    # Cases
    cases: dict[str, YCase] = field(default_factory=dict)
    net_runners: dict[str, YNetRunner] = field(default_factory=dict)

    # Resources
    resource_manager: YResourceManager = field(default_factory=YResourceManager)

    # Factories
    case_factory: CaseFactory = field(default_factory=CaseFactory)

    # Timer service (Gap 5)
    timer_service: YTimerService = field(default_factory=YTimerService)

    # Sub-case registry for composite tasks (Gap 4)
    sub_case_registry: dict[str, SubCaseContext] = field(default_factory=dict)

    # RBAC tracking (Gap 7)
    work_item_history: list[WorkItemHistoryEntry] = field(default_factory=list)
    distribution_context: DistributionContext = field(
        default_factory=lambda: DistributionContext(task_id="", case_id="")
    )
    participant_metrics: dict[str, ParticipantMetrics] = field(default_factory=dict)

    # Counters
    work_item_counter: int = 0

    # Event handling
    event_listeners: list[Callable[[EngineEvent], None]] = field(default_factory=list)

    # Timestamps
    started: datetime | None = None

    # External clients and services (Gap 8)
    external_clients: dict[str, YExternalClient] = field(default_factory=dict)
    yawl_services: dict[str, YAWLServiceReference] = field(default_factory=dict)
    interface_x_listeners: set[str] = field(default_factory=set)
    interface_a_observers: list[InterfaceAManagementObserver] = field(default_factory=list)
    interface_b_observers: list[InterfaceBClientObserver] = field(default_factory=list)
    observer_gateways: list[ObserverGateway] = field(default_factory=list)

    # Persistence
    persistence_manager: YPersistenceManager = field(default_factory=YPersistenceManager)
    persisting: bool = False

    # Caching
    instance_cache: InstanceCache = field(default_factory=InstanceCache)
    session_cache: YSessionCache = field(default_factory=YSessionCache)
    work_item_repository: YWorkItemRepository = field(default_factory=YWorkItemRepository)
    net_runner_repository: YNetRunnerRepository = field(default_factory=YNetRunnerRepository)

    # Configuration
    engine_classes_root_path: str = ""
    engine_nbr: int = 0
    generate_ui_metadata: bool = False
    allow_generic_admin: bool = False
    hibernate_statistics_enabled: bool = False

    # Logging
    process_logging_enabled: bool = True

    # Build info
    build_properties: YBuildProperties = field(default_factory=YBuildProperties)

    # Announcement
    announcement_context: AnnouncementContext = field(default_factory=AnnouncementContext)
    announcer: YAnnouncer = field(default_factory=YAnnouncer)

    # Default worklist
    default_worklist: YAWLServiceReference | None = None

    # Case numbering
    case_counter: int = 0

    # --- Engine lifecycle ---

    def start(self) -> None:
        """Start the engine."""
        self.status = EngineStatus.STARTING
        self.started = datetime.now()
        self._register_timer_handlers()
        self.timer_service.start()
        self.status = EngineStatus.RUNNING
        self._emit_event("ENGINE_STARTED")

    def _register_timer_handlers(self) -> None:
        """Register handlers for timer expiry actions."""
        self.timer_service.set_timer_handler(TimerAction.FAIL, self._handle_timer_fail)
        self.timer_service.set_timer_handler(TimerAction.COMPLETE, self._handle_timer_complete)
        self.timer_service.set_timer_handler(TimerAction.NOTIFY, self._handle_timer_notify)
        self.timer_service.set_timer_handler(TimerAction.ESCALATE, self._handle_timer_escalate)

    def _handle_timer_fail(self, timer: YTimer) -> None:
        """Handle timer fail action.

        Parameters
        ----------
        timer : YTimer
            Expired timer
        """
        work_item = self._find_work_item(timer.work_item_id)
        if work_item and work_item.is_active():
            work_item.transition(WorkItemEvent.TIMEOUT)
            self._emit_event("WORK_ITEM_TIMED_OUT", case_id=work_item.case_id, work_item_id=work_item.id)

    def _handle_timer_complete(self, timer: YTimer) -> None:
        """Handle timer complete action (force complete).

        Parameters
        ----------
        timer : YTimer
            Expired timer
        """
        work_item = self._find_work_item(timer.work_item_id)
        if work_item and work_item.is_active():
            self.complete_work_item(work_item.id, timer.action_data)

    def _handle_timer_notify(self, timer: YTimer) -> None:
        """Handle timer notify action.

        Parameters
        ----------
        timer : YTimer
            Expired timer
        """
        self._emit_event(
            "TIMER_NOTIFICATION", work_item_id=timer.work_item_id, data={"timer_id": timer.id, **timer.action_data}
        )

    def _handle_timer_escalate(self, timer: YTimer) -> None:
        """Handle timer escalate action.

        Parameters
        ----------
        timer : YTimer
            Expired timer
        """
        self._emit_event(
            "TIMER_ESCALATED", work_item_id=timer.work_item_id, data={"timer_id": timer.id, **timer.action_data}
        )

    def stop(self) -> None:
        """Stop the engine (graceful)."""
        self.status = EngineStatus.STOPPING
        # Stop timer service
        self.timer_service.stop()
        # Cancel all running cases
        for case in self.cases.values():
            if case.is_running():
                case.cancel("Engine stopping")
        self.status = EngineStatus.STOPPED
        self._emit_event("ENGINE_STOPPED")

    def pause(self) -> None:
        """Pause the engine."""
        self.status = EngineStatus.PAUSED
        self._emit_event("ENGINE_PAUSED")

    def resume(self) -> None:
        """Resume the engine."""
        self.status = EngineStatus.RUNNING
        self._emit_event("ENGINE_RESUMED")

    def is_running(self) -> bool:
        """Check if engine is running.

        Returns
        -------
        bool
            True if running
        """
        return self.status == EngineStatus.RUNNING

    # --- Specification management ---

    def load_specification(self, spec: YSpecification) -> YSpecification:
        """Load a specification into the engine.

        Parameters
        ----------
        spec : YSpecification
            Specification to load

        Returns
        -------
        YSpecification
            Loaded specification

        Raises
        ------
        ValueError
            If specification is invalid
        """
        is_valid, errors = spec.is_valid()
        if not is_valid:
            raise ValueError(f"Invalid specification: {errors}")

        spec.status = SpecificationStatus.LOADED
        self.specifications[spec.id] = spec
        self._emit_event("SPECIFICATION_LOADED", data={"spec_id": spec.id})
        return spec

    def unload_specification(self, spec_id: str) -> bool:
        """Unload a specification.

        Parameters
        ----------
        spec_id : str
            Specification ID

        Returns
        -------
        bool
            True if unloaded
        """
        if spec_id in self.specifications:
            # Check no running cases
            for case in self.cases.values():
                if case.specification_id == spec_id and case.is_running():
                    return False
            del self.specifications[spec_id]
            self._emit_event("SPECIFICATION_UNLOADED", data={"spec_id": spec_id})
            return True
        return False

    def get_specification(self, spec_id: str) -> YSpecification | None:
        """Get specification by ID.

        Parameters
        ----------
        spec_id : str
            Specification ID

        Returns
        -------
        YSpecification | None
            Specification or None
        """
        return self.specifications.get(spec_id)

    def activate_specification(self, spec_id: str) -> bool:
        """Activate a specification.

        Parameters
        ----------
        spec_id : str
            Specification ID

        Returns
        -------
        bool
            True if activated
        """
        spec = self.specifications.get(spec_id)
        if spec:
            spec.activate()
            self._emit_event("SPECIFICATION_ACTIVATED", data={"spec_id": spec_id})
            return True
        return False

    # --- Case management ---

    def create_case(self, spec_id: str, case_id: str | None = None, input_data: dict[str, Any] | None = None) -> YCase:
        """Create a new case.

        Parameters
        ----------
        spec_id : str
            Specification ID
        case_id : str | None
            Optional specific case ID
        input_data : dict[str, Any] | None
            Input data for case

        Returns
        -------
        YCase
            New case

        Raises
        ------
        ValueError
            If specification not found or not active
        """
        spec = self.specifications.get(spec_id)
        if spec is None:
            raise ValueError(f"Specification not found: {spec_id}")

        if not spec.can_create_case():
            raise ValueError(f"Specification not active: {spec_id}")

        root_net = spec.get_root_net()
        if root_net is None:
            raise ValueError(f"No root net in specification: {spec_id}")

        case = self.case_factory.create_case(specification_id=spec_id, root_net_id=root_net.id, case_id=case_id)

        if input_data:
            case.data.merge_input(input_data)

        self.cases[case.id] = case
        self._emit_event("CASE_CREATED", case_id=case.id)
        return case

    def start_case(self, case_id: str, input_data: dict[str, Any] | None = None) -> YCase:
        """Start a case.

        Parameters
        ----------
        case_id : str
            Case ID
        input_data : dict[str, Any] | None
            Additional input data

        Returns
        -------
        YCase
            Started case

        Raises
        ------
        ValueError
            If case not found
        """
        case = self.cases.get(case_id)
        if case is None:
            raise ValueError(f"Case not found: {case_id}")

        spec = self.specifications.get(case.specification_id)
        if spec is None:
            raise ValueError(f"Specification not found: {case.specification_id}")

        root_net = spec.get_root_net()
        if root_net is None:
            raise ValueError("No root net")

        # Create net runner
        runner_key = f"{case_id}:{root_net.id}"
        runner = YNetRunner(net=root_net, case_id=case_id)
        self.net_runners[runner_key] = runner
        case.net_runners[root_net.id] = runner

        # Start case
        case.start(input_data)
        runner.start()

        self._emit_event("CASE_STARTED", case_id=case_id)

        # Create initial work items
        self._create_work_items_for_enabled_tasks(case, runner)

        return case

    def cancel_case(self, case_id: str, reason: str = "") -> bool:
        """Cancel a running case.

        Parameters
        ----------
        case_id : str
            Case ID
        reason : str
            Cancellation reason

        Returns
        -------
        bool
            True if cancelled
        """
        case = self.cases.get(case_id)
        if case and case.is_running():
            case.cancel(reason)
            self._emit_event("CASE_CANCELLED", case_id=case_id)
            return True
        return False

    def suspend_case(self, case_id: str, reason: str = "") -> bool:
        """Suspend a running case.

        Parameters
        ----------
        case_id : str
            Case ID
        reason : str
            Suspension reason

        Returns
        -------
        bool
            True if suspended
        """
        case = self.cases.get(case_id)
        if case and case.is_running():
            case.suspend(reason)
            self._emit_event("CASE_SUSPENDED", case_id=case_id)
            return True
        return False

    def resume_case(self, case_id: str) -> bool:
        """Resume a suspended case.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        bool
            True if resumed
        """
        case = self.cases.get(case_id)
        if case and case.status == CaseStatus.SUSPENDED:
            case.resume()
            self._emit_event("CASE_RESUMED", case_id=case_id)
            return True
        return False

    def get_case(self, case_id: str) -> YCase | None:
        """Get case by ID.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        YCase | None
            Case or None
        """
        return self.cases.get(case_id)

    def get_running_cases(self) -> list[YCase]:
        """Get all running cases.

        Returns
        -------
        list[YCase]
            Running cases
        """
        return [c for c in self.cases.values() if c.is_running()]

    def get_case_marking(self, case_id: str) -> YMarking | None:
        """Get current marking for a case.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        YMarking | None
            Current marking or None if case not found
        """
        case = self.get_case(case_id)
        if case is None:
            return None

        # Get root net runner marking
        if case.root_net_id and case.root_net_id in case.net_runners:
            return case.net_runners[case.root_net_id].marking

        return None

    # --- Work item management ---

    def _create_work_item(self, case: YCase, task: YTask, net_id: str) -> YWorkItem:
        """Create work item for task.

        Parameters
        ----------
        case : YCase
            Case
        task : YTask
            Task
        net_id : str
            Net ID

        Returns
        -------
        YWorkItem
            New work item
        """
        self.work_item_counter += 1
        work_item = YWorkItem(
            id=f"{case.id}:{task.id}:{self.work_item_counter}",
            case_id=case.id,
            task_id=task.id,
            specification_id=case.specification_id,
            net_id=net_id,
        )
        case.add_work_item(work_item)
        self._emit_event("WORK_ITEM_CREATED", case_id=case.id, work_item_id=work_item.id, task_id=task.id)
        return work_item

    def _create_work_items_for_enabled_tasks(self, case: YCase, runner: YNetRunner) -> list[YWorkItem]:
        """Create work items for all enabled tasks.

        Parameters
        ----------
        case : YCase
            Case
        runner : YNetRunner
            Net runner

        Returns
        -------
        list[YWorkItem]
            Created work items
        """
        work_items = []
        enabled_task_ids = runner.get_enabled_tasks()

        for task_id in enabled_task_ids:
            # Check if work item already exists for this task
            existing = case.get_work_items_for_task(task_id)
            active_existing = [wi for wi in existing if wi.is_active()]
            if active_existing:
                continue

            task = runner.net.tasks.get(task_id)
            if task:
                work_item = self._create_work_item(case, task, runner.net.id)
                work_items.append(work_item)
                # Auto-resource the work item
                self._resource_work_item(work_item, task)

        return work_items

    def _resource_work_item(self, work_item: YWorkItem, task: YTask) -> None:
        """Resource a work item based on task configuration.

        Uses RBAC filters, four-eyes separation, and distribution
        strategies to select appropriate participants.

        Parameters
        ----------
        work_item : YWorkItem
            Work item to resource
        task : YTask
            Task with resourcing info
        """
        # Check for composite task (has net decomposition)
        if self._is_composite_task(task):
            # Fire and execute composite task immediately
            work_item.fire()
            self._execute_composite_task(work_item, task)
            return

        # Check if it's a system task (no human resourcing needed)
        from kgcl.yawl.elements.y_atomic_task import YAtomicTask

        if isinstance(task, YAtomicTask):
            if task.is_automated_task() or task.resourcing.is_system_task():
                # System task - fire and auto-start execution
                work_item.fire()
                work_item.transition(WorkItemEvent.START)
                # Maybe create timer
                self._maybe_create_timer_for_work_item(work_item, task)
                return

            # Get base participants by role
            participants = self.resource_manager.find_participants(
                role_ids=task.resourcing.role_ids or None, available_only=True
            )

            # Apply RBAC filters if configured (Gap 7)
            if task.resourcing.has_filters():
                filter_context = FilterContext(
                    case_id=work_item.case_id,
                    task_id=task.id,
                    work_item_id=work_item.id,
                    work_item_history=self.work_item_history,
                    four_eyes_tasks=task.resourcing.four_eyes_tasks,
                )
                participants = self.resource_manager.find_participants_with_filters(
                    filters=task.resourcing.filters, context=filter_context, base_participants=participants
                )

            # Apply four-eyes separation if configured
            if task.resourcing.has_four_eyes():
                participants = self.resource_manager.apply_four_eyes_filter(
                    participants=participants,
                    case_id=work_item.case_id,
                    task_ids=task.resourcing.four_eyes_tasks,
                    work_item_history=self.work_item_history,
                )

            # Apply distribution strategy
            if participants:
                participants = self.resource_manager.apply_distribution_strategy(
                    participants=participants,
                    strategy=task.resourcing.distribution_strategy,
                    task_id=task.id,
                    distribution_context=self.distribution_context,
                    participant_metrics=self.participant_metrics,
                )

            if participants:
                # FIRE work item first (ENABLED → FIRED)
                work_item.transition(WorkItemEvent.FIRE)
                # Offer to selected participants (FIRED → OFFERED)
                participant_ids = {p.id for p in participants}
                work_item.offer(participant_ids)
                # Maybe create timer
                self._maybe_create_timer_for_work_item(work_item, task)
        else:
            # Non-atomic task (system task) - fire then auto-start
            # ENABLED → FIRED → EXECUTING
            work_item.transition(WorkItemEvent.FIRE)
            work_item.transition(WorkItemEvent.START)

    def _is_composite_task(self, task: YTask) -> bool:
        """Check if task is a composite task (decomposes to a net).

        Parameters
        ----------
        task : YTask
            Task to check

        Returns
        -------
        bool
            True if composite
        """
        if not task.decomposition_id:
            return False

        # Get the specification
        for spec in self.specifications.values():
            decomp = spec.decompositions.get(task.decomposition_id)
            if decomp:
                from kgcl.yawl.elements.y_decomposition import DecompositionType

                return decomp.decomposition_type == DecompositionType.NET
        return False

    def _execute_composite_task(self, work_item: YWorkItem, task: YTask) -> None:
        """Execute a composite task by launching a sub-case.

        Parameters
        ----------
        work_item : YWorkItem
            Parent work item
        task : YTask
            Composite task
        """
        if not task.decomposition_id:
            return

        # Find the specification and decomposition
        case = self.cases.get(work_item.case_id)
        if not case:
            return

        spec = self.specifications.get(case.specification_id)
        if not spec:
            return

        decomp = spec.decompositions.get(task.decomposition_id)
        if not decomp:
            return

        # The decomposition ID should match a subnet
        subnet = spec.nets.get(task.decomposition_id)
        if not subnet:
            return

        # Start the work item execution
        work_item.transition(WorkItemEvent.START)

        # Create a net runner for the subnet
        sub_runner_key = f"{case.id}:{subnet.id}"
        sub_runner = YNetRunner(net=subnet, case_id=case.id)
        self.net_runners[sub_runner_key] = sub_runner
        case.net_runners[subnet.id] = sub_runner

        # Register sub-case context
        context = SubCaseContext(
            sub_case_id=f"{case.id}:sub:{task.id}",
            parent_case_id=case.id,
            parent_work_item_id=work_item.id,
            composite_task_id=task.id,
            subnet_id=subnet.id,
        )
        self.sub_case_registry[context.sub_case_id] = context

        # Start the subnet
        sub_runner.start()

        self._emit_event(
            "SUBCASE_STARTED",
            case_id=case.id,
            work_item_id=work_item.id,
            task_id=task.id,
            data={"subnet_id": subnet.id},
        )

        # Create work items for the subnet's enabled tasks
        self._create_work_items_for_enabled_tasks(case, sub_runner)

    def _complete_sub_case(self, context: SubCaseContext) -> None:
        """Complete a sub-case and its parent work item.

        Parameters
        ----------
        context : SubCaseContext
            Sub-case context
        """
        # Find the parent work item
        parent_wi = self._find_work_item(context.parent_work_item_id)
        if parent_wi and parent_wi.is_active():
            # Complete the parent work item (which will fire the task)
            self.complete_work_item(parent_wi.id)

        # Clean up context
        if context.sub_case_id in self.sub_case_registry:
            del self.sub_case_registry[context.sub_case_id]

        self._emit_event(
            "SUBCASE_COMPLETED",
            case_id=context.parent_case_id,
            work_item_id=context.parent_work_item_id,
            task_id=context.composite_task_id,
            data={"subnet_id": context.subnet_id},
        )

    def _fail_sub_case(self, context: SubCaseContext, reason: str = "") -> None:
        """Fail a sub-case and its parent work item.

        Parameters
        ----------
        context : SubCaseContext
            Sub-case context
        reason : str
            Failure reason
        """
        # Find the parent work item
        parent_wi = self._find_work_item(context.parent_work_item_id)
        if parent_wi and parent_wi.is_active():
            self.fail_work_item(parent_wi.id, reason)

        # Clean up context
        if context.sub_case_id in self.sub_case_registry:
            del self.sub_case_registry[context.sub_case_id]

        self._emit_event(
            "SUBCASE_FAILED",
            case_id=context.parent_case_id,
            work_item_id=context.parent_work_item_id,
            task_id=context.composite_task_id,
            data={"subnet_id": context.subnet_id, "reason": reason},
        )

    def _maybe_create_timer_for_work_item(self, work_item: YWorkItem, task: YTask) -> None:
        """Create timer for work item if task has timer configuration.

        Parameters
        ----------
        work_item : YWorkItem
            Work item
        task : YTask
            Task with potential timer config
        """
        from kgcl.yawl.elements.y_atomic_task import YAtomicTask

        if not isinstance(task, YAtomicTask):
            return

        timer_config = task.resourcing.timer
        if timer_config:
            self.timer_service.create_timer_for_work_item(
                work_item_id=work_item.id,
                duration=timer_config.get("duration", timedelta(hours=24)),
                trigger=TimerTrigger.ON_OFFERED,
                action=TimerAction[timer_config.get("action", "NOTIFY")],
            )

    def _cancel_timers_for_work_item(self, work_item_id: str) -> None:
        """Cancel all timers for a work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID
        """
        timers = self.timer_service.get_timers_for_work_item(work_item_id)
        for timer in timers:
            self.timer_service.cancel_timer(timer.id)

    def get_work_items_for_participant(
        self, participant_id: str, status: WorkItemStatus | None = None
    ) -> list[YWorkItem]:
        """Get work items for a participant.

        Parameters
        ----------
        participant_id : str
            Participant ID
        status : WorkItemStatus | None
            Filter by status

        Returns
        -------
        list[YWorkItem]
            Matching work items
        """
        work_items = []
        for case in self.cases.values():
            for wi in case.work_items.values():
                # Check if offered or allocated to participant
                if participant_id in wi.offered_to or wi.resource_id == participant_id:
                    if status is None or wi.status == status:
                        work_items.append(wi)
        return work_items

    def get_offered_work_items(self, participant_id: str) -> list[YWorkItem]:
        """Get work items offered to participant.

        Parameters
        ----------
        participant_id : str
            Participant ID

        Returns
        -------
        list[YWorkItem]
            Offered work items
        """
        return self.get_work_items_for_participant(participant_id, WorkItemStatus.OFFERED)

    def get_allocated_work_items(self, participant_id: str) -> list[YWorkItem]:
        """Get work items allocated to participant.

        Parameters
        ----------
        participant_id : str
            Participant ID

        Returns
        -------
        list[YWorkItem]
            Allocated work items
        """
        return self.get_work_items_for_participant(participant_id, WorkItemStatus.ALLOCATED)

    def get_started_work_items(self, participant_id: str) -> list[YWorkItem]:
        """Get work items started by participant.

        Parameters
        ----------
        participant_id : str
            Participant ID

        Returns
        -------
        list[YWorkItem]
            Started work items
        """
        return self.get_work_items_for_participant(participant_id, WorkItemStatus.STARTED)

    def get_enabled_work_items(self, case_id: str | None = None) -> list[YWorkItem]:
        """Get all enabled work items (Java YAWL API).

        Parameters
        ----------
        case_id : str | None
            Optional case ID to filter by

        Returns
        -------
        list[YWorkItem]
            Enabled work items
        """
        enabled = []
        if case_id:
            # Get work items from specific case
            case = self.get_case(case_id)
            if case:
                enabled = [wi for wi in case.work_items.values() if wi.status == WorkItemStatus.ENABLED]
        else:
            # Get enabled work items from all cases
            for case in self.cases.values():
                enabled.extend([wi for wi in case.work_items.values() if wi.status == WorkItemStatus.ENABLED])
        return enabled

    # --- Work item actions ---

    def allocate_work_item(self, work_item_id: str, participant_id: str) -> bool:
        """Allocate work item to participant.

        Parameters
        ----------
        work_item_id : str
            Work item ID
        participant_id : str
            Participant ID

        Returns
        -------
        bool
            True if allocated
        """
        work_item = self._find_work_item(work_item_id)
        if work_item and work_item.status == WorkItemStatus.OFFERED:
            work_item.allocate(participant_id)
            self._emit_event(
                "WORK_ITEM_ALLOCATED",
                case_id=work_item.case_id,
                work_item_id=work_item_id,
                participant_id=participant_id,
            )
            return True
        return False

    def start_work_item(
        self, work_item: YWorkItem | str, client: YExternalClient | str | None = None
    ) -> YWorkItem | bool:
        """Start work on a work item.

        Java signature: YWorkItem startWorkItem(YWorkItem workItem, YClient client)
        Java signature: YWorkItem startWorkItem(String itemID, YClient client, String logPredicate)

        Parameters
        ----------
        work_item : YWorkItem | str
            Work item object or ID
        client : YExternalClient | str | None
            External client or participant ID

        Returns
        -------
        YWorkItem | bool
            Started work item (if YWorkItem passed) or True/False (if ID passed)

        Raises
        ------
        YStateException
            If work item is not in a valid state for starting
        """
        # Handle string ID case (backward compatibility)
        if isinstance(work_item, str):
            work_item_id = work_item
            participant_id = client.id if isinstance(client, YExternalClient) else str(client) if client else ""
            work_item_obj = self._find_work_item(work_item_id)
            if work_item_obj and work_item_obj.status in (WorkItemStatus.OFFERED, WorkItemStatus.ALLOCATED):
                # If offered, allocate first
                if work_item_obj.status == WorkItemStatus.OFFERED:
                    work_item_obj.allocate(participant_id)
                work_item_obj.start(participant_id)
                self._emit_event(
                    "WORK_ITEM_STARTED",
                    case_id=work_item_obj.case_id,
                    work_item_id=work_item_id,
                    participant_id=participant_id,
                )
                return True
            return False

        # Handle YWorkItem object case (Java signature)
        self.check_engine_running()
        participant_id = client.id if isinstance(client, YExternalClient) else str(client) if client else ""

        if work_item.status == WorkItemStatus.ENABLED:
            net_runner = self.get_net_runner(work_item.case_id)
            if net_runner:
                return self.start_enabled_work_item(net_runner, work_item, client)
        elif work_item.status == WorkItemStatus.FIRED:
            # Get parent case for fired work items
            from kgcl.yawl.elements.y_identifier import YIdentifier

            case_id = YIdentifier(work_item.case_id)
            if hasattr(case_id, "get_parent") and case_id.get_parent():
                net_runner = self.get_net_runner(case_id.get_parent())
            else:
                net_runner = self.get_net_runner(work_item.case_id)
            if net_runner:
                return self.start_fired_work_item(net_runner, work_item, client)
        elif work_item.status == WorkItemStatus.DEADLOCKED:
            return work_item
        else:
            raise ValueError(f"Item [{work_item.id}]: status [{work_item.status}] does not permit starting.")

        raise ValueError(f"Could not start work item {work_item.id}")

    def complete_work_item(
        self,
        work_item: YWorkItem | str,
        data: str | dict[str, Any] | None = None,
        log_predicate: str | None = None,
        completion_type: WorkItemCompletion | None = None,
    ) -> None | bool:
        """Complete a work item.

        Java signature: void completeWorkItem(YWorkItem workItem, String data, String logPredicate, WorkItemCompletion completionType)

        Parameters
        ----------
        work_item : YWorkItem | str
            Work item object or ID
        data : str | dict[str, Any] | None
            Output data (XML string or dict)
        log_predicate : str | None
            Log predicate
        completion_type : WorkItemCompletion | None
            Completion type (defaults to NORMAL)

        Returns
        -------
        None | bool
            None if YWorkItem passed (Java signature), bool if ID passed (backward compatibility)

        Raises
        ------
        YStateException
            If work item is not in executing state or is a parent case
        """
        # Handle string ID case (backward compatibility)
        if isinstance(work_item, str):
            work_item_id = work_item
            output_data = data if isinstance(data, dict) else {}
            work_item_obj = self._find_work_item(work_item_id)
            if work_item_obj and work_item_obj.status in (WorkItemStatus.STARTED, WorkItemStatus.EXECUTING):
                # Cancel any timers for this work item
                self._cancel_timers_for_work_item(work_item_id)

                work_item_obj.complete(output_data)

                # Record completion for RBAC history (Gap 7)
                if work_item_obj.resource_id:
                    self.resource_manager.record_work_item_completion(
                        case_id=work_item_obj.case_id,
                        task_id=work_item_obj.task_id,
                        work_item_id=work_item_id,
                        participant_id=work_item_obj.resource_id,
                        task_name=work_item_obj.task_id,  # Use task_id as name
                        history=self.work_item_history,
                    )
                    # Update participant metrics
                    if work_item_obj.resource_id in self.participant_metrics:
                        metrics = self.participant_metrics[work_item_obj.resource_id]
                        if metrics.active_work_items > 0:
                            metrics.active_work_items -= 1

                # Get case and runner
                case = self.cases.get(work_item_obj.case_id)
                if case:
                    case.update_work_item_status(work_item_id)

                    # Fire the task in the net runner
                    runner_key = f"{case.id}:{work_item_obj.net_id}"
                    runner = self.net_runners.get(runner_key)
                    if runner:
                        try:
                            runner.fire_task(work_item_obj.task_id, output_data)
                        except ValueError:
                            pass  # Task may have been disabled

                        # Check for subnet completion (sub-case)
                        if runner.completed:
                            # Check if this is a sub-case
                            sub_case_context = self._find_sub_case_context_by_subnet(case.id, work_item_obj.net_id)
                            if sub_case_context:
                                # Complete the parent composite task
                                self._complete_sub_case(sub_case_context)
                            else:
                                # Main case completed
                                case.complete(output_data)
                                self._emit_event("CASE_COMPLETED", case_id=case.id)
                        else:
                            # Create work items for newly enabled tasks
                            self._create_work_items_for_enabled_tasks(case, runner)

                self._emit_event("WORK_ITEM_COMPLETED", case_id=work_item_obj.case_id, work_item_id=work_item_id)
                return True
            return False

        # Handle YWorkItem object case (Java signature)
        self.check_engine_running()

        if work_item is None:
            raise ValueError("WorkItem argument is equal to None.")

        # Check if work item is a parent case (cannot complete)
        from kgcl.yawl.elements.y_identifier import YIdentifier

        case_id = YIdentifier(work_item.case_id)
        if hasattr(case_id, "has_parent") and not case_id.has_parent():
            raise ValueError(f"WorkItem with ID [{work_item.id}] is a 'parent' and so may not be completed.")

        # Get net runner
        if hasattr(case_id, "get_parent") and case_id.get_parent():
            net_runner = self.get_net_runner(case_id.get_parent())
        else:
            net_runner = self.get_net_runner(work_item.case_id)

        # Convert data string to dict if needed
        data_str = data if isinstance(data, str) else ""
        if isinstance(data, dict):
            # Convert dict to XML string (simplified)
            import xml.etree.ElementTree as ET

            root = ET.Element("data")
            for key, value in data.items():
                elem = ET.SubElement(root, key)
                elem.text = str(value)
            data_str = ET.tostring(root, encoding="unicode")

        completion_type = completion_type or WorkItemCompletion.NORMAL

        if work_item.status == WorkItemStatus.EXECUTING:
            self.complete_executing_work_item(work_item, net_runner, data_str, log_predicate or "", completion_type)
            if net_runner:
                self.announce_events(net_runner.case_id)
        elif work_item.status == WorkItemStatus.DEADLOCKED:
            # Remove deadlocked work item family
            if hasattr(self, "work_item_repository"):
                self.work_item_repository.remove_work_item_family(work_item)
        else:
            raise ValueError(f"WorkItem with ID [{work_item.id}] not in executing state (status: {work_item.status}).")

    def _find_sub_case_context_by_subnet(self, case_id: str, subnet_id: str) -> SubCaseContext | None:
        """Find sub-case context by case and subnet ID.

        Parameters
        ----------
        case_id : str
            Case ID
        subnet_id : str
            Subnet ID

        Returns
        -------
        SubCaseContext | None
            Context or None
        """
        for context in self.sub_case_registry.values():
            if context.parent_case_id == case_id and context.subnet_id == subnet_id:
                return context
        return None

    def fail_work_item(self, work_item_id: str, reason: str = "") -> bool:
        """Fail a work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID
        reason : str
            Failure reason

        Returns
        -------
        bool
            True if failed
        """
        work_item = self._find_work_item(work_item_id)
        if work_item and work_item.is_active():
            work_item.fail(reason)
            case = self.cases.get(work_item.case_id)
            if case:
                case.update_work_item_status(work_item_id)
            self._emit_event("WORK_ITEM_FAILED", case_id=work_item.case_id, work_item_id=work_item_id)
            return True
        return False

    def suspend_work_item(self, work_item_id: str) -> bool:
        """Suspend a work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        bool
            True if suspended
        """
        work_item = self._find_work_item(work_item_id)
        if work_item and work_item.status == WorkItemStatus.STARTED:
            work_item.suspend()
            self._emit_event("WORK_ITEM_SUSPENDED", case_id=work_item.case_id, work_item_id=work_item_id)
            return True
        return False

    def resume_work_item(self, work_item_id: str) -> bool:
        """Resume a suspended work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        bool
            True if resumed
        """
        work_item = self._find_work_item(work_item_id)
        if work_item and work_item.status == WorkItemStatus.SUSPENDED:
            work_item.resume()
            self._emit_event("WORK_ITEM_RESUMED", case_id=work_item.case_id, work_item_id=work_item_id)
            return True
        return False

    def delegate_work_item(self, work_item_id: str) -> bool:
        """Delegate work item back to offer.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        bool
            True if delegated
        """
        work_item = self._find_work_item(work_item_id)
        if work_item and work_item.status == WorkItemStatus.ALLOCATED:
            work_item.delegate()
            self._emit_event("WORK_ITEM_DELEGATED", case_id=work_item.case_id, work_item_id=work_item_id)
            return True
        return False

    def reallocate_work_item(self, work_item_id: str, participant_id: str) -> bool:
        """Reallocate work item to different participant.

        Parameters
        ----------
        work_item_id : str
            Work item ID
        participant_id : str
            New participant ID

        Returns
        -------
        bool
            True if reallocated
        """
        work_item = self._find_work_item(work_item_id)
        if work_item and work_item.status == WorkItemStatus.ALLOCATED:
            work_item.reallocate(participant_id)
            self._emit_event(
                "WORK_ITEM_REALLOCATED",
                case_id=work_item.case_id,
                work_item_id=work_item_id,
                participant_id=participant_id,
            )
            return True
        return False

    def skip_work_item(self, work_item_id: str) -> bool:
        """Skip a work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        bool
            True if skipped
        """
        work_item = self._find_work_item(work_item_id)
        if work_item and work_item.status == WorkItemStatus.ENABLED:
            work_item.skip()
            self._emit_event("WORK_ITEM_SKIPPED", case_id=work_item.case_id, work_item_id=work_item_id)
            return True
        return False

    def _find_work_item(self, work_item_id: str) -> YWorkItem | None:
        """Find work item by ID across all cases.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        YWorkItem | None
            Work item or None
        """
        for case in self.cases.values():
            if work_item_id in case.work_items:
                return case.work_items[work_item_id]
        return None

    # --- Event handling ---

    def add_event_listener(self, listener: Callable[[EngineEvent], None]) -> None:
        """Add event listener.

        Parameters
        ----------
        listener : Callable[[EngineEvent], None]
            Listener function
        """
        self.event_listeners.append(listener)

    def remove_event_listener(self, listener: Callable[[EngineEvent], None]) -> None:
        """Remove event listener.

        Parameters
        ----------
        listener : Callable[[EngineEvent], None]
            Listener function to remove
        """
        if listener in self.event_listeners:
            self.event_listeners.remove(listener)

    def _emit_event(
        self,
        event_type: str,
        case_id: str | None = None,
        work_item_id: str | None = None,
        task_id: str | None = None,
        participant_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Emit an engine event.

        Parameters
        ----------
        event_type : str
            Type of event
        case_id : str | None
            Related case ID
        work_item_id : str | None
            Related work item ID
        task_id : str | None
            Related task ID
        participant_id : str | None
            Related participant ID
        data : dict[str, Any] | None
            Additional data
        """
        event = EngineEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            case_id=case_id,
            work_item_id=work_item_id,
            task_id=task_id,
            participant_id=participant_id,
            data=data or {},
        )
        for listener in self.event_listeners:
            try:
                listener(event)
            except Exception:
                pass  # Don't let listener errors break the engine

    # --- External client management (Gap 8) ---

    def addExternalClient(self, client: YExternalClient) -> bool:
        """Add external client to engine.

        Java signature: boolean addExternalClient(YExternalClient client)

        Parameters
        ----------
        client : YExternalClient
            Client to add

        Returns
        -------
        bool
            True if added successfully
        """
        if client.id in self.external_clients:
            return False
        self.external_clients[client.id] = client
        self._emit_event("EXTERNAL_CLIENT_ADDED", data={"client_id": client.id})
        return True

    def removeExternalClient(self, client_name: str) -> YExternalClient | None:
        """Remove external client from engine.

        Java signature: YExternalClient removeExternalClient(String clientName)

        Parameters
        ----------
        client_name : str
            Client name/ID

        Returns
        -------
        YExternalClient | None
            Removed client or None
        """
        client = self.external_clients.pop(client_name, None)
        if client:
            self._emit_event("EXTERNAL_CLIENT_REMOVED", data={"client_id": client_name})
        return client

    def getExternalClient(self, name: str) -> YExternalClient | None:
        """Get external client by name.

        Java signature: YExternalClient getExternalClient(String name)

        Parameters
        ----------
        name : str
            Client name

        Returns
        -------
        YExternalClient | None
            Client or None
        """
        return self.external_clients.get(name)

    def getExternalClients(self) -> set[YExternalClient]:
        """Get all external clients.

        Java signature: Set getExternalClients()

        Returns
        -------
        set[YExternalClient]
            Set of external clients
        """
        return set(self.external_clients.values())

    def updateExternalClient(self, id: str, password: str, doco: str) -> bool:
        """Update external client credentials.

        Java signature: boolean updateExternalClient(String id, String password, String doco)

        Parameters
        ----------
        id : str
            Client ID
        password : str
            New password
        doco : str
            Documentation

        Returns
        -------
        bool
            True if updated
        """
        if id in self.external_clients:
            # Create new client with updated info (frozen dataclass)
            old_client = self.external_clients[id]
            self.external_clients[id] = YExternalClient(id=id, password=password, documentation=doco)
            return True
        return False

    def loadDefaultClients(self) -> set[YExternalClient]:
        """Load default external clients.

        Java signature: Set loadDefaultClients()

        Returns
        -------
        set[YExternalClient]
            Set of loaded clients
        """
        # Default admin client
        admin = YExternalClient(id="admin", password="YAWL", documentation="Default admin client")
        self.addExternalClient(admin)
        return {admin}

    # --- YAWL service management (Gap 8) ---

    def addYawlService(self, yawl_service: YAWLServiceReference) -> None:
        """Add YAWL service to engine.

        Java signature: void addYawlService(YAWLServiceReference yawlService)

        Parameters
        ----------
        yawl_service : YAWLServiceReference
            Service to add
        """
        self.yawl_services[yawl_service.service_id] = yawl_service
        self._emit_event("YAWL_SERVICE_ADDED", data={"service_id": yawl_service.service_id})

    def removeYawlService(self, service_uri: str) -> YAWLServiceReference | None:
        """Remove YAWL service.

        Java signature: YAWLServiceReference removeYawlService(String serviceURI)

        Parameters
        ----------
        service_uri : str
            Service URI

        Returns
        -------
        YAWLServiceReference | None
            Removed service or None
        """
        for service_id, service in list(self.yawl_services.items()):
            if service.uri == service_uri:
                del self.yawl_services[service_id]
                self._emit_event("YAWL_SERVICE_REMOVED", data={"service_id": service_id})
                return service
        return None

    def getRegisteredYawlService(self, yawl_service_id: str) -> YAWLServiceReference | None:
        """Get registered YAWL service by ID.

        Java signature: YAWLServiceReference getRegisteredYawlService(String yawlServiceID)

        Parameters
        ----------
        yawl_service_id : str
            Service ID

        Returns
        -------
        YAWLServiceReference | None
            Service or None
        """
        return self.yawl_services.get(yawl_service_id)

    def getYAWLServices(self) -> set[YAWLServiceReference]:
        """Get all YAWL services.

        Java signature: Set getYAWLServices()

        Returns
        -------
        set[YAWLServiceReference]
            Set of services
        """
        return set(self.yawl_services.values())

    def setDefaultWorklist(self, param_str: str) -> None:
        """Set default worklist service.

        Java signature: void setDefaultWorklist(String paramStr)

        Parameters
        ----------
        param_str : str
            Service ID or URI
        """
        service = self.getRegisteredYawlService(param_str)
        if service:
            self.default_worklist = service

    def getDefaultWorklist(self) -> YAWLServiceReference | None:
        """Get default worklist service.

        Java signature: YAWLServiceReference getDefaultWorklist()

        Returns
        -------
        YAWLServiceReference | None
            Default worklist or None
        """
        return self.default_worklist

    # --- Interface X listeners ---

    def addInterfaceXListener(self, observer_uri: str) -> bool:
        """Add Interface X listener.

        Java signature: boolean addInterfaceXListener(String observerURI)

        Parameters
        ----------
        observer_uri : str
            Observer URI

        Returns
        -------
        bool
            True if added
        """
        if observer_uri not in self.interface_x_listeners:
            self.interface_x_listeners.add(observer_uri)
            return True
        return False

    def removeInterfaceXListener(self, uri: str) -> bool:
        """Remove Interface X listener.

        Java signature: boolean removeInterfaceXListener(String uri)

        Parameters
        ----------
        uri : str
            Observer URI

        Returns
        -------
        bool
            True if removed
        """
        if uri in self.interface_x_listeners:
            self.interface_x_listeners.remove(uri)
            return True
        return False

    # --- Interface A/B observers ---

    def registerInterfaceAClient(self, observer: InterfaceAManagementObserver) -> None:
        """Register Interface A client.

        Java signature: void registerInterfaceAClient(InterfaceAManagementObserver observer)

        Parameters
        ----------
        observer : InterfaceAManagementObserver
            Observer to register
        """
        if observer not in self.interface_a_observers:
            self.interface_a_observers.append(observer)

    def registerInterfaceBObserver(self, observer: InterfaceBClientObserver) -> None:
        """Register Interface B observer.

        Java signature: void registerInterfaceBObserver(InterfaceBClientObserver observer)

        Parameters
        ----------
        observer : InterfaceBClientObserver
            Observer to register
        """
        if observer not in self.interface_b_observers:
            self.interface_b_observers.append(observer)

    def registerInterfaceBObserverGateway(self, gateway: ObserverGateway) -> None:
        """Register Interface B observer gateway.

        Java signature: void registerInterfaceBObserverGateway(ObserverGateway gateway)

        Parameters
        ----------
        gateway : ObserverGateway
            Gateway to register
        """
        if gateway not in self.observer_gateways:
            self.observer_gateways.append(gateway)

    # --- Case data APIs ---

    def getCaseData(self, id: YIdentifier) -> YNetData:
        """Get case data by identifier.

        Java signature: YNetData getCaseData(YIdentifier id)

        Parameters
        ----------
        id : YIdentifier
            Case identifier

        Returns
        -------
        YNetData
            Case data
        """
        case = self.get_case(id.case_id)
        if case:
            return YNetData(data=case.data.data)
        return YNetData()

    def getCaseData_str(self, case_id: str) -> str:
        """Get case data as string.

        Java signature: String getCaseData(String caseID)

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        str
            Case data as XML string
        """
        case = self.get_case(case_id)
        if case:
            import json

            return json.dumps(case.data.data)
        return ""

    def getCaseDataDocument(self, id: str) -> Document:
        """Get case data as XML document.

        Java signature: Document getCaseDataDocument(String id)

        Parameters
        ----------
        id : str
            Case ID

        Returns
        -------
        Document
            XML document
        """
        # Stub - would need XML serialization
        return Document()

    def updateCaseData(self, id_str: str, data: str) -> bool:
        """Update case data.

        Java signature: boolean updateCaseData(String idStr, String data)

        Parameters
        ----------
        id_str : str
            Case ID
        data : str
            New data (JSON string)

        Returns
        -------
        bool
            True if updated
        """
        case = self.get_case(id_str)
        if case:
            import json

            try:
                data_dict = json.loads(data)
                case.data.merge_input(data_dict)
                return True
            except json.JSONDecodeError:
                return False
        return False

    def getNetData(self, case_id: str) -> str:
        """Get net data for case.

        Java signature: String getNetData(String caseID)

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        str
            Net data as string
        """
        return self.getCaseData_str(case_id)

    # --- Work item data ---

    def updateWorkItemData(self, work_item_id: str, data: str) -> bool:
        """Update work item data.

        Java signature: boolean updateWorkItemData(String workItemID, String data)

        Parameters
        ----------
        work_item_id : str
            Work item ID
        data : str
            New data

        Returns
        -------
        bool
            True if updated
        """
        work_item = self._find_work_item(work_item_id)
        if work_item:
            import json

            try:
                data_dict = json.loads(data)
                if work_item.data is None:
                    work_item.data = {}
                work_item.data.update(data_dict)
                return True
            except json.JSONDecodeError:
                return False
        return False

    # --- Persistence transaction support ---

    def startTransaction(self) -> bool:
        """Start persistence transaction.

        Java signature: boolean startTransaction()

        Returns
        -------
        bool
            True if started
        """
        if self.persisting:
            return self.persistence_manager.start_transaction()
        return False

    def commitTransaction(self) -> None:
        """Commit persistence transaction.

        Java signature: void commitTransaction()
        """
        if self.persisting:
            self.persistence_manager.commit_transaction()

    def rollbackTransaction(self) -> None:
        """Rollback persistence transaction.

        Java signature: void rollbackTransaction()
        """
        if self.persisting:
            self.persistence_manager.rollback_transaction()

    def storeObject(self, obj: object) -> None:
        """Store object to persistence.

        Java signature: void storeObject(Object obj)

        Parameters
        ----------
        obj : object
            Object to store
        """
        if self.persisting:
            self.persistence_manager.store_object(obj)

    def updateObject(self, obj: object) -> None:
        """Update object in persistence.

        Java signature: void updateObject(Object obj)

        Parameters
        ----------
        obj : object
            Object to update
        """
        if self.persisting:
            self.persistence_manager.update_object(obj)

    def deleteObject(self, obj: object) -> None:
        """Delete object from persistence.

        Java signature: void deleteObject(Object obj)

        Parameters
        ----------
        obj : object
            Object to delete
        """
        if self.persisting:
            self.persistence_manager.delete_object(obj)

    def doPersistAction(self, obj: object, action: int) -> None:
        """Perform persistence action.

        Java signature: void doPersistAction(Object obj, int action)

        Parameters
        ----------
        obj : object
            Object
        action : int
            Action code (0=store, 1=update, 2=delete)
        """
        if action == 0:
            self.storeObject(obj)
        elif action == 1:
            self.updateObject(obj)
        elif action == 2:
            self.deleteObject(obj)

    # --- Case ID allocation ---

    def allocateCaseID(self) -> str:
        """Allocate unique case ID.

        Java signature: String allocateCaseID()

        Returns
        -------
        str
            New case ID
        """
        return str(uuid.uuid4())

    def getNextCaseNbr(self) -> str:
        """Get next case number.

        Java signature: String getNextCaseNbr()

        Returns
        -------
        str
            Next case number
        """
        self.case_counter += 1
        return str(self.case_counter)

    # --- Net runners ---

    def addRunner(self, runner: YNetRunner, specification: YSpecification | None = None) -> None:
        """Add net runner.

        Java signature: void addRunner(YNetRunner runner, YSpecification specification)
        Java signature: void addRunner(YNetRunner runner)

        Parameters
        ----------
        runner : YNetRunner
            Runner to add
        specification : YSpecification | None
            Optional specification
        """
        key = f"{runner.case_id}:{runner.net.id}"
        self.net_runners[key] = runner
        self.net_runner_repository.runners[key] = runner

    def getNetRunner(self, identifier: YIdentifier | str | YWorkItem) -> YNetRunner | None:
        """Get net runner.

        Java signature: YNetRunner getNetRunner(YIdentifier identifier)
        Java signature: YNetRunner getNetRunner(YWorkItem workItem)

        Parameters
        ----------
        identifier : YIdentifier | str | YWorkItem
            Case identifier or work item

        Returns
        -------
        YNetRunner | None
            Net runner or None
        """
        if isinstance(identifier, YWorkItem):
            # Get by work item
            key = f"{identifier.case_id}:{identifier.net_id}"
            return self.net_runners.get(key)
        elif isinstance(identifier, YIdentifier):
            # Get by identifier - find root net
            case = self.get_case(identifier.case_id)
            if case and case.root_net_id:
                key = f"{identifier.case_id}:{case.root_net_id}"
                return self.net_runners.get(key)
        return None

    def getNetRunnerRepository(self) -> YNetRunnerRepository:
        """Get net runner repository.

        Java signature: YNetRunnerRepository getNetRunnerRepository()

        Returns
        -------
        YNetRunnerRepository
            Repository
        """
        return self.net_runner_repository

    # --- Specifications ---

    def addSpecifications(
        self, spec_str: str, ignore_errors: bool, verification_handler: YVerificationHandler
    ) -> list[YSpecification]:
        """Add specifications from string.

        Java signature: List addSpecifications(String specStr, boolean ignoreErrors, YVerificationHandler verificationHandler)

        Parameters
        ----------
        spec_str : str
            Specification XML string
        ignore_errors : bool
            Ignore validation errors
        verification_handler : YVerificationHandler
            Verification handler

        Returns
        -------
        list[YSpecification]
            Loaded specifications
        """
        # Stub - would need XML parsing
        return []

    def getLatestSpecification(self, key: str) -> YSpecification | None:
        """Get latest specification by key.

        Java signature: YSpecification getLatestSpecification(String key)

        Parameters
        ----------
        key : str
            Specification key

        Returns
        -------
        YSpecification | None
            Latest specification or None
        """
        # Return first matching spec (simplified)
        for spec in self.specifications.values():
            if spec.id.startswith(key):
                return spec
        return None

    def getLoadedSpecificationIDs(self) -> set[YSpecificationID]:
        """Get loaded specification IDs.

        Java signature: Set getLoadedSpecificationIDs()

        Returns
        -------
        set[YSpecificationID]
            Set of specification IDs
        """
        return {YSpecificationID(uri="", version="", identifier=spec_id) for spec_id in self.specifications.keys()}

    def getLoadStatus(self, spec_id: YSpecificationID) -> str:
        """Get load status of specification.

        Java signature: String getLoadStatus(YSpecificationID specID)

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification ID

        Returns
        -------
        str
            Load status
        """
        spec = self.specifications.get(spec_id.identifier)
        if spec:
            return spec.status.name
        return "NOT_LOADED"

    def getProcessDefinition(self, spec_id: YSpecificationID) -> YSpecification | None:
        """Get process definition.

        Java signature: YSpecification getProcessDefinition(YSpecificationID specID)

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification ID

        Returns
        -------
        YSpecification | None
            Specification or None
        """
        return self.specifications.get(spec_id.identifier)

    def getSpecificationDataSchema(self, spec_id: YSpecificationID) -> str:
        """Get specification data schema.

        Java signature: String getSpecificationDataSchema(YSpecificationID specID)

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification ID

        Returns
        -------
        str
            Data schema as string
        """
        # Stub - would return XML schema
        return ""

    def getSpecificationForCase(self, case_id: YIdentifier) -> YSpecification | None:
        """Get specification for case.

        Java signature: YSpecification getSpecificationForCase(YIdentifier caseID)

        Parameters
        ----------
        case_id : YIdentifier
            Case identifier

        Returns
        -------
        YSpecification | None
            Specification or None
        """
        case = self.get_case(case_id.id)
        if case:
            return self.specifications.get(case.specification_id)
        return None

    # --- Task definitions ---

    def get_task_definition(self, spec_id: YSpecificationID, task_id: str) -> YTask | None:
        """Get task definition.

        Java signature: YTask getTaskDefinition(YSpecificationID specID, String taskID)

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification ID
        task_id : str
            Task ID

        Returns
        -------
        YTask | None
            Task or None
        """
        spec = self.specifications.get(spec_id.identifier)
        if spec:
            # Find task in nets
            for net in spec.nets.values():
                if task_id in net.tasks:
                    return net.tasks[task_id]
        return None

    def get_parameters(self, spec_id: YSpecificationID, task_id: str, input: bool) -> dict[str, Any]:
        """Get task parameters.

        Java signature: Map getParameters(YSpecificationID specID, String taskID, boolean input)

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification ID
        task_id : str
            Task ID
        input : bool
            True for input params, False for output

        Returns
        -------
        dict[str, Any]
            Parameters
        """
        task = self.get_task_definition(spec_id, task_id)
        if task:
            # Get decomposition prototype which contains parameters
            decomp = task.get_decomposition_prototype()
            if decomp:
                return decomp.input_parameters if input else decomp.output_parameters
        return {}

    # --- Case operations ---

    def format_case_params(self, param_str: str, spec: YSpecification) -> Element:
        """Format case parameters.

        Java signature: Element formatCaseParams(String paramStr, YSpecification spec)

        Parameters
        ----------
        param_str : str
            Parameter string
        spec : YSpecification
            Specification

        Returns
        -------
        Element
            XML element
        """
        # Stub - would create XML element
        return Element("data")

    def launch_case(
        self,
        spec_id: YSpecificationID | YSpecification,
        case_params: str = "",
        completion_observer: str | None = None,
        case_id: str | None = None,
        log_data: YLogDataItemList | None = None,
        service_handle: str | None = None,
        delayed: bool = False,
    ) -> str | YNetRunner:
        """Launch case.

        Java signature: String launchCase(YSpecificationID specID, String caseParams, URI completionObserver, String caseID, YLogDataItemList logData, String serviceHandle, boolean delayed)
        Java signature: YNetRunner launchCase(YSpecification spec, String caseID, String caseParams, YLogDataItemList logData)

        Parameters
        ----------
        spec_id : YSpecificationID | YSpecification
            Specification ID or specification
        case_params : str
            Case parameters
        completion_observer : str | None
            Completion observer URI
        case_id : str | None
            Case ID
        log_data : YLogDataItemList | None
            Log data
        service_handle : str | None
            Service handle
        delayed : bool
            Delayed launch

        Returns
        -------
        str | YNetRunner
            Case ID or net runner
        """
        if isinstance(spec_id, YSpecification):
            # Direct spec launch
            case = self.create_case(spec_id.id, case_id)
            if case_params:
                import json

                try:
                    params = json.loads(case_params)
                    case.data.merge_input(params)
                except json.JSONDecodeError:
                    pass
            started_case = self.start_case(case.id)
            root_net_id = spec_id.get_root_net().id if spec_id.get_root_net() else ""
            runner_key = f"{case.id}:{root_net_id}"
            return self.net_runners.get(runner_key) or YNetRunner(net=spec_id.get_root_net(), case_id=case.id)  # type: ignore[arg-type]
        else:
            # Spec ID launch
            case = self.create_case(spec_id.identifier, case_id)
            if case_params:
                import json

                try:
                    params = json.loads(case_params)
                    case.data.merge_input(params)
                except json.JSONDecodeError:
                    pass
            if not delayed:
                self.start_case(case.id)
            if log_data:
                self.logCaseStarted_spec_id(
                    spec_id,
                    self.net_runners.get(f"{case.id}:{case.root_net_id}"),
                    completion_observer,
                    case_params,
                    log_data,
                    service_handle,
                    delayed,  # type: ignore[arg-type]
                )
            return case.id

    def logCaseStarted_spec(
        self, spec: YSpecification, runner: YNetRunner, case_params: str, log_data: YLogDataItemList
    ) -> None:
        """Log case started.

        Java signature: void logCaseStarted(YSpecification spec, YNetRunner runner, String caseParams, YLogDataItemList logData)

        Parameters
        ----------
        spec : YSpecification
            Specification
        runner : YNetRunner
            Net runner
        case_params : str
            Case parameters
        log_data : YLogDataItemList
            Log data
        """
        self._emit_event(
            "CASE_STARTED_LOGGED",
            case_id=runner.case_id,
            data={"spec_id": spec.id, "params": case_params, "log_items": len(log_data.items)},
        )

    def logCaseStarted_spec_id(
        self,
        spec_id: YSpecificationID,
        runner: YNetRunner,
        completion_observer: str | None,
        case_params: str,
        log_data: YLogDataItemList,
        service_ref: str | None,
        delayed: bool,
    ) -> None:
        """Log case started with spec ID.

        Java signature: void logCaseStarted(YSpecificationID specID, YNetRunner runner, URI completionObserver, String caseParams, YLogDataItemList logData, String serviceRef, boolean delayed)

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification ID
        runner : YNetRunner
            Net runner
        completion_observer : str | None
            Completion observer
        case_params : str
            Case parameters
        log_data : YLogDataItemList
            Log data
        service_ref : str | None
            Service reference
        delayed : bool
            Delayed launch
        """
        self._emit_event(
            "CASE_STARTED_LOGGED",
            case_id=runner.case_id,
            data={
                "spec_id": spec_id.identifier,
                "observer": completion_observer,
                "service": service_ref,
                "delayed": delayed,
            },
        )

    # --- Case state ---

    def getCaseID(self, case_id_str: str) -> YIdentifier:
        """Get case identifier from string.

        Java signature: YIdentifier getCaseID(String caseIDStr)

        Parameters
        ----------
        case_id_str : str
            Case ID string

        Returns
        -------
        YIdentifier
            Case identifier
        """
        return YIdentifier(id=case_id_str)

    def getCaseLocations(self, case_id: YIdentifier) -> set[str]:
        """Get case locations (marking).

        Java signature: Set getCaseLocations(YIdentifier caseID)

        Parameters
        ----------
        case_id : YIdentifier
            Case identifier

        Returns
        -------
        set[str]
            Set of location IDs
        """
        marking = self.get_case_marking(case_id.id)
        if marking:
            return set(marking.tokens.keys())
        return set()

    def getCasesForSpecification(self, spec_id: YSpecificationID) -> set[YCase]:
        """Get cases for specification.

        Java signature: Set getCasesForSpecification(YSpecificationID specID)

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification ID

        Returns
        -------
        set[YCase]
            Set of cases
        """
        return {case for case in self.cases.values() if case.specification_id == spec_id.identifier}

    def getRunningCaseIDs(self) -> list[str]:
        """Get running case IDs.

        Java signature: List getRunningCaseIDs()

        Returns
        -------
        list[str]
            List of running case IDs
        """
        return [case.id for case in self.cases.values() if case.is_running()]

    def getRunningCaseMap(self) -> dict[str, YCase]:
        """Get running cases as map.

        Java signature: Map getRunningCaseMap()

        Returns
        -------
        dict[str, YCase]
            Map of running cases
        """
        return {case.id: case for case in self.cases.values() if case.is_running()}

    def getRunnersForPrimaryCase(self, primary_case_id: YIdentifier) -> list[YNetRunner]:
        """Get runners for primary case.

        Java signature: List getRunnersForPrimaryCase(YIdentifier primaryCaseID)

        Parameters
        ----------
        primary_case_id : YIdentifier
            Primary case identifier

        Returns
        -------
        list[YNetRunner]
            List of runners
        """
        case = self.get_case(primary_case_id.id)
        if case:
            return list(case.net_runners.values())
        return []

    def getStateForCase(self, case_id: YIdentifier) -> str:
        """Get state for case (marking XML).

        Java signature: String getStateForCase(YIdentifier caseID)

        Parameters
        ----------
        case_id : YIdentifier
            Case identifier

        Returns
        -------
        str
            State as string
        """
        case = self.get_case(case_id.id)
        if case:
            return case.status.name
        return "UNKNOWN"

    def getStateTextForCase(self, case_id: YIdentifier) -> str:
        """Get state text for case.

        Java signature: String getStateTextForCase(YIdentifier caseID)

        Parameters
        ----------
        case_id : YIdentifier
            Case identifier

        Returns
        -------
        str
            State text
        """
        return self.getStateForCase(case_id)

    # --- Work items ---

    def getAllWorkItems(self) -> set[YWorkItem]:
        """Get all work items.

        Java signature: Set getAllWorkItems()

        Returns
        -------
        set[YWorkItem]
            Set of all work items
        """
        work_items = set()
        for case in self.cases.values():
            work_items.update(case.work_items.values())
        return work_items

    def getAvailableWorkItems(self) -> set[YWorkItem]:
        """Get available work items (offered or allocated).

        Java signature: Set getAvailableWorkItems()

        Returns
        -------
        set[YWorkItem]
            Set of available work items
        """
        work_items = set()
        for case in self.cases.values():
            for wi in case.work_items.values():
                if wi.status in (WorkItemStatus.OFFERED, WorkItemStatus.ALLOCATED):
                    work_items.add(wi)
        return work_items

    def getWorkItem(self, work_item_id: str) -> YWorkItem | None:
        """Get work item by ID.

        Java signature: YWorkItem getWorkItem(String workItemID)

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        YWorkItem | None
            Work item or None
        """
        return self._find_work_item(work_item_id)

    def getWorkItemRepository(self) -> YWorkItemRepository:
        """Get work item repository.

        Java signature: YWorkItemRepository getWorkItemRepository()

        Returns
        -------
        YWorkItemRepository
            Repository
        """
        # Sync repository
        self.work_item_repository.work_items.clear()
        for case in self.cases.values():
            self.work_item_repository.work_items.update(case.work_items)
        return self.work_item_repository

    def getChildrenOfWorkItem(self, work_item: YWorkItem) -> set[YWorkItem]:
        """Get children of work item (for MI tasks).

        Java signature: Set getChildrenOfWorkItem(YWorkItem workItem)

        Parameters
        ----------
        work_item : YWorkItem
            Parent work item

        Returns
        -------
        set[YWorkItem]
            Set of child work items
        """
        # Stub - would track MI children
        return set()

    def getStartingDataSnapshot(self, item_id: str) -> Element:
        """Get starting data snapshot for work item.

        Java signature: Element getStartingDataSnapshot(String itemID)

        Parameters
        ----------
        item_id : str
            Work item ID

        Returns
        -------
        Element
            XML element
        """
        # Stub - would return snapshot
        return Element("snapshot")

    # --- Work item operations ---

    def canAddNewInstances(self, work_item_id: str) -> bool:
        """Check if can add new MI instances.

        Java signature: boolean canAddNewInstances(String workItemID)

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        bool
            True if can add instances
        """
        # Stub - would check MI task
        return False

    def checkElegibilityToAddInstances(self, work_item_id: str) -> None:
        """Check eligibility to add instances.

        Java signature: void checkElegibilityToAddInstances(String workItemID)

        Parameters
        ----------
        work_item_id : str
            Work item ID
        """

    def checkEligibilityToAddInstances(self, item: YWorkItem) -> None:
        """Check eligibility to add instances.

        Java signature: void checkEligibilityToAddInstances(YWorkItem item)

        Parameters
        ----------
        item : YWorkItem
            Work item
        """

    def createNewInstance(self, work_item: YWorkItem, param_value_for_mi_creation: str) -> YWorkItem:
        """Create new MI instance.

        Java signature: YWorkItem createNewInstance(YWorkItem workItem, String paramValueForMICreation)

        Parameters
        ----------
        work_item : YWorkItem
            Parent work item
        param_value_for_mi_creation : str
            Parameter value

        Returns
        -------
        YWorkItem
            New work item instance
        """
        # Stub - would create MI instance
        case = self.cases.get(work_item.case_id)
        if case:
            spec = self.specifications.get(case.specification_id)
            if spec:
                for net in spec.nets.values():
                    if work_item.task_id in net.tasks:
                        task = net.tasks[work_item.task_id]
                        return self._create_work_item(case, task, net.id)
        raise NotImplementedError("MI instance creation not implemented")

    def cancelWorkItem(self, work_item: YWorkItem | str) -> YWorkItem | None:
        """Cancel work item.

        Java signature: YWorkItem cancelWorkItem(YNetRunner caseRunner, YWorkItem workItem)
        Java signature: void cancelWorkItem(YWorkItem workItem)

        Parameters
        ----------
        work_item : YWorkItem | str
            Work item or ID

        Returns
        -------
        YWorkItem | None
            Cancelled work item or None
        """
        if isinstance(work_item, str):
            wi = self._find_work_item(work_item)
            if wi:
                wi.transition(WorkItemEvent.CANCEL)
            return None
        else:
            work_item.transition(WorkItemEvent.CANCEL)
            return work_item

    def rollbackWorkItem(self, work_item: YWorkItem | str) -> YWorkItem | None:
        """Rollback work item.

        Java signature: YWorkItem rollbackWorkItem(YWorkItem workItem)
        Java signature: void rollbackWorkItem(String workItemID)

        Parameters
        ----------
        work_item : YWorkItem | str
            Work item or ID

        Returns
        -------
        YWorkItem | None
            Rolled back work item or None
        """
        if isinstance(work_item, str):
            wi = self._find_work_item(work_item)
            if wi and wi.status in (WorkItemStatus.STARTED, WorkItemStatus.EXECUTING):
                wi.transition(WorkItemEvent.CANCEL)
                wi.transition(WorkItemEvent.FIRE)
            return None
        else:
            if work_item.status in (WorkItemStatus.STARTED, WorkItemStatus.EXECUTING):
                work_item.transition(WorkItemEvent.CANCEL)
                work_item.transition(WorkItemEvent.FIRE)
            return work_item

    def unsuspendWorkItem(self, work_item: YWorkItem | str) -> YWorkItem | None:
        """Unsuspend work item.

        Java signature: YWorkItem unsuspendWorkItem(YWorkItem workItem)
        Java signature: YWorkItem unsuspendWorkItem(String workItemID)

        Parameters
        ----------
        work_item : YWorkItem | str
            Work item or ID

        Returns
        -------
        YWorkItem | None
            Unsuspended work item or None
        """
        if isinstance(work_item, str):
            wi = self._find_work_item(work_item)
            if wi:
                self.resume_work_item(work_item)
                return wi
            return None
        else:
            self.resume_work_item(work_item.id)
            return work_item

    def startEnabledWorkItem(
        self, net_runner: YNetRunner, work_item: YWorkItem, client: YClient | None = None
    ) -> YWorkItem:
        """Start enabled work item.

        Java signature: YWorkItem startEnabledWorkItem(YNetRunner netRunner, YWorkItem workItem)
        Java signature: YWorkItem startEnabledWorkItem(YNetRunner netRunner, YWorkItem workItem, YClient client)

        Parameters
        ----------
        net_runner : YNetRunner
            Net runner
        work_item : YWorkItem
            Work item
        client : YClient | None
            Client

        Returns
        -------
        YWorkItem
            Started work item
        """
        if work_item.status == WorkItemStatus.ENABLED:
            work_item.transition(WorkItemEvent.FIRE)
            if client:
                work_item.allocate(client.id)
                work_item.start(client.id)
            else:
                work_item.transition(WorkItemEvent.START)
        return work_item

    def startFiredWorkItem(
        self, net_runner: YNetRunner, work_item: YWorkItem, client: YClient | None = None
    ) -> YWorkItem:
        """Start fired work item.

        Java signature: YWorkItem startFiredWorkItem(YNetRunner netRunner, YWorkItem workItem)
        Java signature: YWorkItem startFiredWorkItem(YNetRunner netRunner, YWorkItem workItem, YClient client)

        Parameters
        ----------
        net_runner : YNetRunner
            Net runner
        work_item : YWorkItem
            Work item
        client : YClient | None
            Client

        Returns
        -------
        YWorkItem
            Started work item
        """
        if work_item.status in (WorkItemStatus.FIRED, WorkItemStatus.OFFERED, WorkItemStatus.ALLOCATED):
            if client:
                if work_item.status == WorkItemStatus.OFFERED:
                    work_item.allocate(client.id)
                work_item.start(client.id)
            else:
                work_item.transition(WorkItemEvent.START)
        return work_item

    # --- Work item completion ---

    def complete_executing_work_item(
        self,
        work_item: YWorkItem,
        net_runner: YNetRunner,
        data: str,
        log_predicate: str,
        completion_type: WorkItemCompletion,
    ) -> None:
        """Complete executing work item.

        Java signature: void completeExecutingWorkitem(YWorkItem workItem, YNetRunner netRunner, String data, String logPredicate, WorkItemCompletion completionType)

        Mirrors Java: private void completeExecutingWorkitem(YWorkItem workItem, YNetRunner netRunner, String data, String logPredicate, WorkItemCompletion completionType)

        Parameters
        ----------
        work_item : YWorkItem
            Work item
        net_runner : YNetRunner
            Net runner
        data : str
            Output data
        log_predicate : str
            Log predicate
        completion_type : WorkItemCompletion
            Completion type
        """
        # Set external completion log predicate (mirrors Java: workItem.setExternalCompletionLogPredicate(logPredicate))
        work_item.set_external_completion_log_predicate(log_predicate)

        # Cancel timer if any (mirrors Java: workItem.cancelTimer())
        if hasattr(work_item, "cancel_timer"):
            work_item.cancel_timer()

        # Announce if time service timeout (mirrors Java: announceIfTimeServiceTimeout(netRunner, workItem))
        self.announce_if_time_service_timeout(net_runner, work_item)

        # Set status to complete (mirrors Java: workItem.setStatusToComplete(_pmgr, completionType))
        # Note: Would need persistence manager - using None for now
        work_item.set_status_to_complete(None, completion_type)

        # Get data document for completion (mirrors Java: Document doc = getDataDocForWorkItemCompletion(workItem, data, completionType))
        doc = self.get_data_doc_for_work_item_completion(work_item, data, completion_type)

        # Complete data (mirrors Java: workItem.completeData(doc))
        work_item.complete_data(doc)

        # Complete work item in task (mirrors Java: if (netRunner.completeWorkItemInTask(_pmgr, workItem, doc)))
        # Note: Would need persistence manager - using None for now
        if net_runner.complete_work_item_in_task(workItem=work_item, outputData=doc, pmgr=None):
            # Cleanup completed work item (mirrors Java: cleanupCompletedWorkItem(workItem, netRunner, doc))
            self.cleanup_completed_work_item(work_item, net_runner, doc)

            # Continue if possible (mirrors Java: netRunner.continueIfPossible(_pmgr))
            # Note: Would need persistence manager - using None for now
            net_runner.continue_if_possible(None)

    def cleanup_completed_work_item(self, work_item: YWorkItem, net_runner: YNetRunner, data: Document) -> None:
        """Cleanup completed work item.

        Java signature: void cleanupCompletedWorkItem(YWorkItem workItem, YNetRunner netRunner, Document data)

        Mirrors Java: private void cleanupCompletedWorkItem(YWorkItem workItem, YNetRunner netRunner, Document data)

        Parameters
        ----------
        work_item : YWorkItem
            Work item
        net_runner : YNetRunner
            Net runner
        data : Document
            Data document
        """
        # Close work item in instance cache (mirrors Java: _instanceCache.closeWorkItem(workItem, data))
        if hasattr(self.instance_cache, "close_work_item"):
            self.instance_cache.close_work_item(work_item, data)
        elif hasattr(self.instance_cache, "cache"):
            # Fallback: store in cache if close_work_item not implemented
            case_id = work_item.case_id
            if case_id in self.instance_cache.cache:
                case_instance = self.instance_cache.cache[case_id]
                if hasattr(case_instance, "close_work_item"):
                    case_instance.close_work_item(work_item, data)

        # Get parent work item (mirrors Java: YWorkItem parent = workItem.getParent())
        parent = work_item.get_parent()
        if parent is not None:
            # If case is suspending, see if we can progress into a fully suspended state
            # (mirrors Java: if (netRunner.isSuspending()) { progressCaseSuspension(_pmgr, parent.getCaseID()); })
            # Check if net runner is in suspending state (only SUSPENDING, not SUSPENDED)
            if hasattr(net_runner, "execution_status") and net_runner.execution_status == ExecutionStatus.SUSPENDING:
                # Note: Would need persistence manager - using None for now
                from kgcl.yawl.elements.y_identifier import YIdentifier

                parent_case_id = YIdentifier(parent.case_id)
                self.progress_case_suspension(None, parent_case_id)

    def complete_work_item_logging(
        self, work_item: YWorkItem, log_predicate: str, completion_type: WorkItemCompletion, doc: Document
    ) -> None:
        """Complete work item with logging.

        Java signature: void completeWorkItemLogging(YWorkItem workItem, String logPredicate, WorkItemCompletion completionType, Document doc)

        Parameters
        ----------
        work_item : YWorkItem
            Work item
        log_predicate : str
            Log predicate
        completion_type : WorkItemCompletion
            Completion type
        doc : Document
            Document
        """
        # Log work item completion event
        # Note: Event logger integration would go here

        # Log completion data if predicate provided
        if log_predicate and hasattr(work_item, "log_completion_data"):
            work_item.log_completion_data(doc)

    def get_data_doc_for_work_item_completion(
        self, work_item: YWorkItem, data: str, completion_type: WorkItemCompletion
    ) -> Document:
        """Get data document for work item completion.

        Java signature: Document getDataDocForWorkItemCompletion(YWorkItem workItem, String data, WorkItemCompletion completionType)

        Mirrors Java: private Document getDataDocForWorkItemCompletion(YWorkItem workItem, String data, WorkItemCompletion completionType)

        Parameters
        ----------
        work_item : YWorkItem
            Work item
        data : str
            Data string (XML or empty)
        completion_type : WorkItemCompletion
            Completion type

        Returns
        -------
        Document
            Data document
        """
        # If completionType != Normal, map output data for skipped work item
        # (mirrors Java: if (completionType != WorkItemCompletion.Normal) { data = mapOutputDataForSkippedWorkItem(workItem, data); })
        if completion_type != WorkItemCompletion.NORMAL:
            data = self.map_output_data_for_skipped_work_item(work_item, data)

        # Convert string to Document (mirrors Java: Document doc = JDOMUtil.stringToDocument(data))
        if data:
            try:
                from xml.dom.minidom import parseString

                doc = parseString(data)
                # Strip attributes from root element (mirrors Java: JDOMUtil.stripAttributes(doc.getRootElement()))
                if doc.documentElement:
                    # Remove all attributes from root element
                    while doc.documentElement.attributes.length > 0:
                        attr_name = doc.documentElement.attributes.item(0).name
                        doc.documentElement.removeAttribute(attr_name)
                return doc
            except Exception:
                # If parsing fails, return empty document
                return Document()
        return Document()

    def map_output_data_for_skipped_work_item(self, work_item: YWorkItem, data: str) -> str:
        """Map output data for skipped work item.

        Java signature: String mapOutputDataForSkippedWorkItem(YWorkItem workItem, String data)

        Parameters
        ----------
        work_item : YWorkItem
            Work item
        data : str
            Input data

        Returns
        -------
        str
            Mapped output data
        """
        return data

    # --- Announcements ---

    def announceEvents(self, parent: YNetRunner | YIdentifier) -> None:
        """Announce events.

        Java signature: void announceEvents(YNetRunner parent)
        Java signature: void announceEvents(YIdentifier caseID)

        Parameters
        ----------
        parent : YNetRunner | YIdentifier
            Net runner or case ID
        """
        if isinstance(parent, YNetRunner):
            self._emit_event("EVENTS_ANNOUNCED", case_id=parent.case_id)
        else:
            self._emit_event("EVENTS_ANNOUNCED", case_id=parent.case_id)

    def announce_if_time_service_timeout(self, net_runner: YNetRunner, work_item: YWorkItem) -> None:
        """Announce if time service timeout.

        Java signature: void announceIfTimeServiceTimeout(YNetRunner netRunner, YWorkItem workItem)

        Parameters
        ----------
        net_runner : YNetRunner
            Net runner
        work_item : YWorkItem
            Work item
        """
        timers = self.timer_service.get_timers_for_work_item(work_item.id)
        for timer in timers:
            if timer.is_expired():
                self._emit_event("TIME_SERVICE_TIMEOUT", case_id=work_item.case_id, work_item_id=work_item.id)

    def announceItemStarted(self, item: YWorkItem) -> None:
        """Announce item started.

        Java signature: void announceItemStarted(YWorkItem item)

        Parameters
        ----------
        item : YWorkItem
            Work item
        """
        self._emit_event("ITEM_STARTED", case_id=item.case_id, work_item_id=item.id)

    def reannounceEnabledWorkItems(self) -> int:
        """Reannounce enabled work items.

        Java signature: int reannounceEnabledWorkItems()

        Returns
        -------
        int
            Count of reannounced items
        """
        enabled = self.get_enabled_work_items()
        for wi in enabled:
            self._emit_event("WORK_ITEM_REANNOUNCED", case_id=wi.case_id, work_item_id=wi.id)
        return len(enabled)

    def reannounceExecutingWorkItems(self) -> int:
        """Reannounce executing work items.

        Java signature: int reannounceExecutingWorkItems()

        Returns
        -------
        int
            Count of reannounced items
        """
        count = 0
        for case in self.cases.values():
            for wi in case.work_items.values():
                if wi.status == WorkItemStatus.EXECUTING:
                    self._emit_event("WORK_ITEM_REANNOUNCED", case_id=wi.case_id, work_item_id=wi.id)
                    count += 1
        return count

    def reannounceFiredWorkItems(self) -> int:
        """Reannounce fired work items.

        Java signature: int reannounceFiredWorkItems()

        Returns
        -------
        int
            Count of reannounced items
        """
        count = 0
        for case in self.cases.values():
            for wi in case.work_items.values():
                if wi.status == WorkItemStatus.FIRED:
                    self._emit_event("WORK_ITEM_REANNOUNCED", case_id=wi.case_id, work_item_id=wi.id)
                    count += 1
        return count

    def reannounceWorkItem(self, work_item: YWorkItem) -> None:
        """Reannounce work item.

        Java signature: void reannounceWorkItem(YWorkItem workItem)

        Parameters
        ----------
        work_item : YWorkItem
            Work item
        """
        self._emit_event("WORK_ITEM_REANNOUNCED", case_id=work_item.case_id, work_item_id=work_item.id)

    def getAnnouncementContext(self) -> AnnouncementContext:
        """Get announcement context.

        Java signature: AnnouncementContext getAnnouncementContext()

        Returns
        -------
        AnnouncementContext
            Announcement context
        """
        return self.announcement_context

    def getAnnouncer(self) -> YAnnouncer:
        """Get announcer.

        Java signature: YAnnouncer getAnnouncer()

        Returns
        -------
        YAnnouncer
            Announcer
        """
        return self.announcer

    # --- Timers ---

    def cancelTimer(self, work_item: YWorkItem) -> None:
        """Cancel timer for work item.

        Java signature: void cancelTimer(YWorkItem workItem)

        Parameters
        ----------
        work_item : YWorkItem
            Work item
        """
        self._cancel_timers_for_work_item(work_item.id)

    # --- Persistence ---

    def clearCaseFromPersistence(self, id: YIdentifier) -> None:
        """Clear case from persistence.

        Java signature: void clearCaseFromPersistence(YIdentifier id)

        Parameters
        ----------
        id : YIdentifier
            Case identifier
        """
        if self.persisting:
            case = self.get_case(id.case_id)
            if case:
                self.persistence_manager.delete_object(case)

    def clearWorkItemsFromPersistence(self, items: set[YWorkItem]) -> None:
        """Clear work items from persistence.

        Java signature: void clearWorkItemsFromPersistence(Set items)

        Parameters
        ----------
        items : set[YWorkItem]
            Work items to clear
        """
        if self.persisting:
            for item in items:
                self.persistence_manager.delete_object(item)

    def removeCaseFromCaches(self, case_id: YIdentifier) -> None:
        """Remove case from caches.

        Java signature: void removeCaseFromCaches(YIdentifier caseID)

        Parameters
        ----------
        case_id : YIdentifier
            Case identifier
        """
        if case_id.id in self.cases:
            del self.cases[case_id.id]
        # Clear from instance cache
        if case_id.id in self.instance_cache.cache:
            del self.instance_cache.cache[case_id.id]

    def progress_case_suspension(
        self, pmgr: YPersistenceManager | YNetRunner, case_id: YIdentifier | None = None
    ) -> None:
        """Progress case suspension.

        Java signature: void progressCaseSuspension(YPersistenceManager pmgr, YIdentifier caseID)
        Java signature: void progressCaseSuspension(YNetRunner runner)

        Parameters
        ----------
        pmgr : YPersistenceManager | YNetRunner
            Persistence manager or runner
        case_id : YIdentifier | None
            Case identifier
        """
        if isinstance(pmgr, YNetRunner):
            # Runner variant
            runner = pmgr
            case = self.get_case(runner.case_id)
            if case:
                case.suspend("Suspension in progress")
        elif case_id:
            # Manager variant
            case = self.get_case(case_id.id)
            if case:
                case.suspend("Suspension in progress")

    # --- Engine configuration ---

    def checkEngineRunning(self) -> None:
        """Check if engine is running (raises exception if not).

        Java signature: void checkEngineRunning()

        Raises
        ------
        RuntimeError
            If engine not running
        """
        if not self.is_running():
            raise RuntimeError("Engine is not running")

    def getEngineStatus(self) -> Status:
        """Get engine status.

        Java signature: Status getEngineStatus()

        Returns
        -------
        Status
            Engine status
        """
        if self.status == EngineStatus.RUNNING:
            return Status.RUNNING
        return Status.STOPPED

    def setEngineStatus(self, status: Status) -> None:
        """Set engine status.

        Java signature: void setEngineStatus(Status status)

        Parameters
        ----------
        status : Status
            New status
        """
        if status == Status.RUNNING:
            self.status = EngineStatus.RUNNING
        else:
            self.status = EngineStatus.STOPPED

    def isPersisting(self) -> bool:
        """Check if persistence is enabled.

        Java signature: boolean isPersisting()

        Returns
        -------
        bool
            True if persisting
        """
        return self.persisting

    def setPersisting(self, persist: bool) -> None:
        """Set persistence enabled.

        Java signature: void setPersisting(boolean persist)

        Parameters
        ----------
        persist : bool
            Enable persistence
        """
        self.persisting = persist

    def getPersistenceManager(self) -> YPersistenceManager:
        """Get persistence manager.

        Java signature: YPersistenceManager getPersistenceManager()

        Returns
        -------
        YPersistenceManager
            Persistence manager
        """
        return self.persistence_manager

    def getInstanceCache(self) -> InstanceCache:
        """Get instance cache.

        Java signature: InstanceCache getInstanceCache()

        Returns
        -------
        InstanceCache
            Instance cache
        """
        return self.instance_cache

    def getSessionCache(self) -> YSessionCache:
        """Get session cache.

        Java signature: YSessionCache getSessionCache()

        Returns
        -------
        YSessionCache
            Session cache
        """
        return self.session_cache

    def getEngineClassesRootFilePath(self) -> str:
        """Get engine classes root file path.

        Java signature: String getEngineClassesRootFilePath()

        Returns
        -------
        str
            Root file path
        """
        return self.engine_classes_root_path

    def setEngineClassesRootFilePath(self, path: str) -> None:
        """Set engine classes root file path.

        Java signature: void setEngineClassesRootFilePath(String path)

        Parameters
        ----------
        path : str
            Root file path
        """
        self.engine_classes_root_path = path

    def getEngineNbr(self) -> int:
        """Get engine number.

        Java signature: int getEngineNbr()

        Returns
        -------
        int
            Engine number
        """
        return self.engine_nbr

    def generateUIMetaData(self) -> bool:
        """Check if UI metadata generation is enabled.

        Java signature: boolean generateUIMetaData()

        Returns
        -------
        bool
            True if enabled
        """
        return self.generate_ui_metadata

    def setGenerateUIMetaData(self, generate: bool) -> None:
        """Set UI metadata generation.

        Java signature: void setGenerateUIMetaData(boolean generate)

        Parameters
        ----------
        generate : bool
            Enable generation
        """
        self.generate_ui_metadata = generate

    def isGenericAdminAllowed(self) -> bool:
        """Check if generic admin is allowed.

        Java signature: boolean isGenericAdminAllowed()

        Returns
        -------
        bool
            True if allowed
        """
        return self.allow_generic_admin

    def setAllowAdminID(self, allow: bool) -> None:
        """Set allow admin ID.

        Java signature: void setAllowAdminID(boolean allow)

        Parameters
        ----------
        allow : bool
            Allow admin
        """
        self.allow_generic_admin = allow

    def isHibernateStatisticsEnabled(self) -> bool:
        """Check if Hibernate statistics are enabled.

        Java signature: boolean isHibernateStatisticsEnabled()

        Returns
        -------
        bool
            True if enabled
        """
        return self.hibernate_statistics_enabled

    def setHibernateStatisticsEnabled(self, enabled: bool) -> None:
        """Set Hibernate statistics enabled.

        Java signature: void setHibernateStatisticsEnabled(boolean enabled)

        Parameters
        ----------
        enabled : bool
            Enable statistics
        """
        self.hibernate_statistics_enabled = enabled

    def getHibernateStatistics(self) -> str:
        """Get Hibernate statistics.

        Java signature: String getHibernateStatistics()

        Returns
        -------
        str
            Statistics as string
        """
        if self.hibernate_statistics_enabled:
            return "Hibernate statistics: enabled"
        return "Hibernate statistics: disabled"

    def disableProcessLogging(self) -> None:
        """Disable process logging.

        Java signature: void disableProcessLogging()
        """
        self.process_logging_enabled = False

    def getBuildProperties(self) -> YBuildProperties:
        """Get build properties.

        Java signature: YBuildProperties getBuildProperties()

        Returns
        -------
        YBuildProperties
            Build properties
        """
        return self.build_properties

    def initBuildProperties(self, stream: IOBase) -> None:
        """Initialize build properties from stream.

        Java signature: void initBuildProperties(InputStream stream)

        Parameters
        ----------
        stream : IOBase
            Input stream
        """
        # Stub - would parse properties file

    def getUsers(self) -> set[YParticipant]:
        """Get all users (participants).

        Java signature: Set getUsers()

        Returns
        -------
        set[YParticipant]
            Set of participants
        """
        return set(self.resource_manager.participants.values())

    # --- Engine lifecycle (advanced) ---

    def initialise(
        self, pmgr: YPersistenceManager, persisting: bool, gather_hbn_stats: bool, redundant_mode: bool
    ) -> None:
        """Initialize engine.

        Java signature: void initialise(YPersistenceManager pmgr, boolean persisting, boolean gatherHbnStats, boolean redundantMode)

        Parameters
        ----------
        pmgr : YPersistenceManager
            Persistence manager
        persisting : bool
            Enable persistence
        gather_hbn_stats : bool
            Gather Hibernate statistics
        redundant_mode : bool
            Redundant mode
        """
        self.persistence_manager = pmgr
        self.persisting = persisting
        self.hibernate_statistics_enabled = gather_hbn_stats
        # Redundant mode would be for HA setups

    def initialised(self, max_wait_seconds: int) -> None:
        """Wait for engine to be initialized.

        Java signature: void initialised(int maxWaitSeconds)

        Parameters
        ----------
        max_wait_seconds : int
            Maximum wait time
        """
        # Would wait for engine to reach RUNNING state
        import time

        waited = 0
        while self.status != EngineStatus.RUNNING and waited < max_wait_seconds:
            time.sleep(0.1)
            waited += 0.1

    def shutdown(self) -> None:
        """Shutdown engine.

        Java signature: void shutdown()
        """
        self.stop()

    def restore(self, redundant_mode: bool) -> None:
        """Restore engine from persistence.

        Java signature: void restore(boolean redundantMode)

        Parameters
        ----------
        redundant_mode : bool
            Redundant mode
        """
        # Would restore state from persistence

    def promote(self) -> None:
        """Promote engine (HA mode).

        Java signature: void promote()
        """
        # Would promote to active in HA setup
        self.status = EngineStatus.RUNNING

    def demote(self) -> None:
        """Demote engine (HA mode).

        Java signature: void demote()
        """
        # Would demote to standby in HA setup
        self.status = EngineStatus.PAUSED

    def dump(self) -> None:
        """Dump engine state.

        Java signature: void dump()
        """
        # Would dump state for debugging
        print(f"Engine {self.engine_id}: {self.status.name}")
        print(f"  Specifications: {len(self.specifications)}")
        print(f"  Cases: {len(self.cases)}")
        print(f"  Running cases: {len(self.get_running_cases())}")

    # --- Singleton getInstance methods (class methods would be better) ---

    @classmethod
    def getInstance(
        cls, persisting: bool = False, gather_hbn_stats: bool = False, redundant_mode: bool = False
    ) -> YEngine:
        """Get engine instance (singleton pattern).

        Java signature: YEngine getInstance()
        Java signature: YEngine getInstance(boolean persisting, boolean gatherHbnStats)
        Java signature: YEngine getInstance(boolean persisting)
        Java signature: YEngine getInstance(boolean persisting, boolean gatherHbnStats, boolean redundantMode)

        Parameters
        ----------
        persisting : bool
            Enable persistence
        gather_hbn_stats : bool
            Gather Hibernate statistics
        redundant_mode : bool
            Redundant mode

        Returns
        -------
        YEngine
            Engine instance
        """
        # Simplified - would use actual singleton
        engine = cls()
        engine.persisting = persisting
        engine.hibernate_statistics_enabled = gather_hbn_stats
        return engine

    # --- Statistics ---

    def get_statistics(self) -> dict[str, Any]:
        """Get engine statistics.

        Returns
        -------
        dict[str, Any]
            Statistics dictionary
        """
        running_cases = sum(1 for c in self.cases.values() if c.is_running())
        completed_cases = sum(1 for c in self.cases.values() if c.status == CaseStatus.COMPLETED)
        active_work_items = sum(len(c.active_work_items) for c in self.cases.values())

        return {
            "engine_id": self.engine_id,
            "status": self.status.name,
            "started": self.started.isoformat() if self.started else None,
            "specifications_loaded": len(self.specifications),
            "total_cases": len(self.cases),
            "running_cases": running_cases,
            "completed_cases": completed_cases,
            "active_work_items": active_work_items,
            "participants": len(self.resource_manager.participants),
            "roles": len(self.resource_manager.roles),
        }
