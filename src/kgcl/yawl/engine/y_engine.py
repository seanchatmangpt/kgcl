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
from typing import TYPE_CHECKING, Any

from kgcl.yawl.elements.y_identifier import YIdentifier
from kgcl.yawl.elements.y_specification import SpecificationStatus, YSpecification
from kgcl.yawl.engine.y_case import CaseFactory, CaseStatus, YCase
from kgcl.yawl.engine.y_net_runner import FireResult, YNetRunner
from kgcl.yawl.engine.y_timer import TimerAction, TimerTrigger, YTimer, YTimerService
from kgcl.yawl.engine.y_work_item import WorkItemEvent, WorkItemStatus, YWorkItem
from kgcl.yawl.resources.y_distribution import DistributionContext, ParticipantMetrics
from kgcl.yawl.resources.y_filters import FilterContext, WorkItemHistoryEntry
from kgcl.yawl.resources.y_resource import YParticipant, YResourceManager
from kgcl.yawl.state.y_marking import YMarking

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_net import YNet
    from kgcl.yawl.elements.y_task import YTask


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
        # Fire the work item
        work_item.fire()

        # Check for composite task (has net decomposition)
        if self._is_composite_task(task):
            self._execute_composite_task(work_item, task)
            return

        # Check if it's a system task (no human resourcing needed)
        from kgcl.yawl.elements.y_atomic_task import YAtomicTask

        if isinstance(task, YAtomicTask):
            if task.is_automated_task() or task.resourcing.is_system_task():
                # System task - auto-start execution
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
                # Offer to selected participants
                participant_ids = {p.id for p in participants}
                work_item.offer(participant_ids)
                # Maybe create timer
                self._maybe_create_timer_for_work_item(work_item, task)
        else:
            # Non-atomic task - auto-start
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

    def start_work_item(self, work_item_id: str, participant_id: str) -> bool:
        """Start work on a work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID
        participant_id : str
            Participant ID

        Returns
        -------
        bool
            True if started
        """
        work_item = self._find_work_item(work_item_id)
        if work_item and work_item.status in (WorkItemStatus.OFFERED, WorkItemStatus.ALLOCATED):
            # If offered, allocate first
            if work_item.status == WorkItemStatus.OFFERED:
                work_item.allocate(participant_id)
            work_item.start(participant_id)
            self._emit_event(
                "WORK_ITEM_STARTED", case_id=work_item.case_id, work_item_id=work_item_id, participant_id=participant_id
            )
            return True
        return False

    def complete_work_item(self, work_item_id: str, output_data: dict[str, Any] | None = None) -> bool:
        """Complete a work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID
        output_data : dict[str, Any] | None
            Output data

        Returns
        -------
        bool
            True if completed
        """
        work_item = self._find_work_item(work_item_id)
        if work_item and work_item.status in (WorkItemStatus.STARTED, WorkItemStatus.EXECUTING):
            # Cancel any timers for this work item
            self._cancel_timers_for_work_item(work_item_id)

            work_item.complete(output_data)

            # Record completion for RBAC history (Gap 7)
            if work_item.resource_id:
                self.resource_manager.record_work_item_completion(
                    case_id=work_item.case_id,
                    task_id=work_item.task_id,
                    work_item_id=work_item_id,
                    participant_id=work_item.resource_id,
                    task_name=work_item.task_id,  # Use task_id as name
                    history=self.work_item_history,
                )
                # Update participant metrics
                if work_item.resource_id in self.participant_metrics:
                    metrics = self.participant_metrics[work_item.resource_id]
                    if metrics.active_work_items > 0:
                        metrics.active_work_items -= 1

            # Get case and runner
            case = self.cases.get(work_item.case_id)
            if case:
                case.update_work_item_status(work_item_id)

                # Fire the task in the net runner
                runner_key = f"{case.id}:{work_item.net_id}"
                runner = self.net_runners.get(runner_key)
                if runner:
                    try:
                        runner.fire_task(work_item.task_id, output_data)
                    except ValueError:
                        pass  # Task may have been disabled

                    # Check for subnet completion (sub-case)
                    if runner.completed:
                        # Check if this is a sub-case
                        sub_case_context = self._find_sub_case_context_by_subnet(case.id, work_item.net_id)
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

            self._emit_event("WORK_ITEM_COMPLETED", case_id=work_item.case_id, work_item_id=work_item_id)
            return True
        return False

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
