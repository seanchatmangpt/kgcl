"""Exception handling for workflow execution (mirrors Java worklet service).

Provides patterns for handling exceptions during workflow execution,
including retry, skip, escalate, and worklet invocation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from kgcl.yawl.engine.y_case import YCase
    from kgcl.yawl.engine.y_work_item import YWorkItem


class ExceptionType(Enum):
    """Type of workflow exception.

    Attributes
    ----------
    TASK_FAILURE : auto
        Task execution failed
    TIMEOUT : auto
        Task timed out
    RESOURCE_UNAVAILABLE : auto
        No resources available
    DATA_ERROR : auto
        Data validation/mapping error
    CONSTRAINT_VIOLATION : auto
        Business constraint violation
    EXTERNAL_FAILURE : auto
        External service failure
    CANCELLATION : auto
        Task/case cancelled
    DEADLOCK : auto
        Execution deadlocked
    SYSTEM_ERROR : auto
        System-level error
    CUSTOM : auto
        Custom exception type
    """

    TASK_FAILURE = auto()
    TIMEOUT = auto()
    RESOURCE_UNAVAILABLE = auto()
    DATA_ERROR = auto()
    CONSTRAINT_VIOLATION = auto()
    EXTERNAL_FAILURE = auto()
    CANCELLATION = auto()
    DEADLOCK = auto()
    SYSTEM_ERROR = auto()
    CUSTOM = auto()


class ExceptionAction(Enum):
    """Action to take for an exception.

    Attributes
    ----------
    IGNORE : auto
        Ignore and continue
    RETRY : auto
        Retry the operation
    SKIP : auto
        Skip the task
    COMPLETE : auto
        Force complete
    FAIL : auto
        Fail the work item
    CANCEL_TASK : auto
        Cancel just the task
    CANCEL_CASE : auto
        Cancel the whole case
    SUSPEND : auto
        Suspend execution
    ESCALATE : auto
        Escalate to handler
    WORKLET : auto
        Invoke exception worklet
    COMPENSATE : auto
        Run compensation
    """

    IGNORE = auto()
    RETRY = auto()
    SKIP = auto()
    COMPLETE = auto()
    FAIL = auto()
    CANCEL_TASK = auto()
    CANCEL_CASE = auto()
    SUSPEND = auto()
    ESCALATE = auto()
    WORKLET = auto()
    COMPENSATE = auto()


@dataclass
class YWorkflowException:
    """Exception during workflow execution.

    Parameters
    ----------
    id : str
        Unique identifier
    exception_type : ExceptionType
        Type of exception
    message : str
        Exception message
    timestamp : datetime
        When exception occurred
    case_id : str | None
        Related case ID
    work_item_id : str | None
        Related work item ID
    task_id : str | None
        Related task ID
    stack_trace : str
        Stack trace if available
    data : dict[str, Any]
        Additional context data
    handled : bool
        Whether exception was handled
    action_taken : ExceptionAction | None
        Action that was taken

    Examples
    --------
    >>> exc = YWorkflowException(
    ...     id="exc-001",
    ...     exception_type=ExceptionType.TASK_FAILURE,
    ...     message="External service unavailable",
    ...     work_item_id="wi-001",
    ... )
    """

    id: str
    exception_type: ExceptionType
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    case_id: str | None = None
    work_item_id: str | None = None
    task_id: str | None = None
    stack_trace: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    handled: bool = False
    action_taken: ExceptionAction | None = None

    def mark_handled(self, action: ExceptionAction) -> None:
        """Mark exception as handled.

        Parameters
        ----------
        action : ExceptionAction
            Action that was taken
        """
        self.handled = True
        self.action_taken = action


@dataclass
class ExceptionRule:
    """Rule for handling exceptions (mirrors Java exlet rules).

    Defines conditions and actions for exception handling.

    Parameters
    ----------
    id : str
        Unique identifier
    name : str
        Rule name
    description : str
        Rule description
    exception_types : set[ExceptionType]
        Exception types this rule handles
    task_ids : set[str] | None
        Specific task IDs (None = all)
    condition : str | None
        Additional condition expression
    action : ExceptionAction
        Action to take
    action_params : dict[str, Any]
        Parameters for the action
    priority : int
        Rule priority (higher = more important)
    enabled : bool
        Whether rule is enabled

    Examples
    --------
    >>> rule = ExceptionRule(
    ...     id="r1",
    ...     name="Retry on timeout",
    ...     exception_types={ExceptionType.TIMEOUT},
    ...     action=ExceptionAction.RETRY,
    ...     action_params={"max_retries": 3},
    ... )
    """

    id: str
    name: str = ""
    description: str = ""
    exception_types: set[ExceptionType] = field(default_factory=set)
    task_ids: set[str] | None = None
    condition: str | None = None
    action: ExceptionAction = ExceptionAction.FAIL
    action_params: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    enabled: bool = True

    def matches(self, exception: YWorkflowException) -> bool:
        """Check if rule matches exception.

        Parameters
        ----------
        exception : YWorkflowException
            Exception to check

        Returns
        -------
        bool
            True if rule matches
        """
        if not self.enabled:
            return False

        # Check exception type
        if self.exception_types and exception.exception_type not in self.exception_types:
            return False

        # Check task ID
        if self.task_ids and exception.task_id not in self.task_ids:
            return False

        # Condition expression evaluation: if no condition specified, rule matches
        # If condition IS specified, we cannot evaluate it (no expression engine)
        # so we match conservatively (rule applies) and log warning
        if self.condition:
            import warnings

            warnings.warn(
                f"ExceptionRule '{self.id}' has condition '{self.condition}' "
                "but condition evaluation is not implemented. Rule will match unconditionally.",
                UserWarning,
                stacklevel=2,
            )
        return True


@dataclass
class RetryContext:
    """Context for retry operations.

    Parameters
    ----------
    work_item_id : str
        Work item being retried
    max_retries : int
        Maximum retry attempts
    retry_count : int
        Current retry count
    retry_delay : float
        Delay between retries (seconds)
    last_retry : datetime | None
        When last retry occurred
    """

    work_item_id: str
    max_retries: int = 3
    retry_count: int = 0
    retry_delay: float = 1.0
    last_retry: datetime | None = None

    def can_retry(self) -> bool:
        """Check if more retries available.

        Returns
        -------
        bool
            True if can retry
        """
        return self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment retry count."""
        self.retry_count += 1
        self.last_retry = datetime.now()


@dataclass
class YExceptionService:
    """Service for handling workflow exceptions (mirrors Java worklet service).

    Manages exception rules and provides exception handling functionality.

    Parameters
    ----------
    rules : list[ExceptionRule]
        Exception handling rules
    exceptions : list[YWorkflowException]
        Recorded exceptions
    retry_contexts : dict[str, RetryContext]
        Retry contexts by work item ID
    exception_handlers : dict[ExceptionAction, Callable]
        Handlers for exception actions
    default_action : ExceptionAction
        Default action when no rule matches

    Examples
    --------
    >>> service = YExceptionService()
    >>> service.add_rule(retry_rule)
    >>> action = service.handle_exception(exception)
    """

    rules: list[ExceptionRule] = field(default_factory=list)
    exceptions: list[YWorkflowException] = field(default_factory=list)
    retry_contexts: dict[str, RetryContext] = field(default_factory=dict)
    exception_handlers: dict[ExceptionAction, Callable[..., Any]] = field(default_factory=dict)
    default_action: ExceptionAction = ExceptionAction.FAIL

    def add_rule(self, rule: ExceptionRule) -> None:
        """Add exception handling rule.

        Parameters
        ----------
        rule : ExceptionRule
            Rule to add
        """
        self.rules.append(rule)
        # Sort by priority (highest first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove rule by ID.

        Parameters
        ----------
        rule_id : str
            Rule ID

        Returns
        -------
        bool
            True if removed
        """
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                del self.rules[i]
                return True
        return False

    def find_matching_rule(self, exception: YWorkflowException) -> ExceptionRule | None:
        """Find first matching rule for exception.

        Parameters
        ----------
        exception : YWorkflowException
            Exception to match

        Returns
        -------
        ExceptionRule | None
            Matching rule or None
        """
        for rule in self.rules:
            if rule.matches(exception):
                return rule
        return None

    def handle_exception(self, exception: YWorkflowException) -> ExceptionAction:
        """Handle an exception.

        Parameters
        ----------
        exception : YWorkflowException
            Exception to handle

        Returns
        -------
        ExceptionAction
            Action taken
        """
        self.exceptions.append(exception)

        # Find matching rule
        rule = self.find_matching_rule(exception)
        action = rule.action if rule else self.default_action
        action_params = rule.action_params if rule else {}

        # Handle retry specially
        if action == ExceptionAction.RETRY:
            action = self._handle_retry(exception, action_params)

        # Execute action handler if registered
        handler = self.exception_handlers.get(action)
        if handler:
            try:
                handler(exception, action_params)
            except Exception:
                pass

        exception.mark_handled(action)
        return action

    def _handle_retry(self, exception: YWorkflowException, params: dict[str, Any]) -> ExceptionAction:
        """Handle retry action.

        Parameters
        ----------
        exception : YWorkflowException
            Exception
        params : dict[str, Any]
            Retry parameters

        Returns
        -------
        ExceptionAction
            RETRY if can retry, FAIL otherwise
        """
        if not exception.work_item_id:
            return ExceptionAction.FAIL

        # Get or create retry context
        ctx = self.retry_contexts.get(exception.work_item_id)
        if ctx is None:
            ctx = RetryContext(
                work_item_id=exception.work_item_id,
                max_retries=params.get("max_retries", 3),
                retry_delay=params.get("retry_delay", 1.0),
            )
            self.retry_contexts[exception.work_item_id] = ctx

        if ctx.can_retry():
            ctx.increment_retry()
            return ExceptionAction.RETRY
        else:
            # Max retries exceeded
            return ExceptionAction.FAIL

    def set_handler(self, action: ExceptionAction, handler: Callable[..., Any]) -> None:
        """Set handler for exception action.

        Parameters
        ----------
        action : ExceptionAction
            Action type
        handler : Callable
            Handler function
        """
        self.exception_handlers[action] = handler

    def get_exceptions_for_case(self, case_id: str) -> list[YWorkflowException]:
        """Get exceptions for a case.

        Parameters
        ----------
        case_id : str
            Case ID

        Returns
        -------
        list[YWorkflowException]
            Exceptions for case
        """
        return [e for e in self.exceptions if e.case_id == case_id]

    def get_exceptions_for_work_item(self, work_item_id: str) -> list[YWorkflowException]:
        """Get exceptions for a work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID

        Returns
        -------
        list[YWorkflowException]
            Exceptions for work item
        """
        return [e for e in self.exceptions if e.work_item_id == work_item_id]

    def get_unhandled_exceptions(self) -> list[YWorkflowException]:
        """Get unhandled exceptions.

        Returns
        -------
        list[YWorkflowException]
            Unhandled exceptions
        """
        return [e for e in self.exceptions if not e.handled]

    def create_exception(
        self,
        exception_type: ExceptionType,
        message: str,
        case_id: str | None = None,
        work_item_id: str | None = None,
        task_id: str | None = None,
        **kwargs: Any,
    ) -> YWorkflowException:
        """Create and record a new exception.

        Parameters
        ----------
        exception_type : ExceptionType
            Type of exception
        message : str
            Exception message
        case_id : str | None
            Case ID
        work_item_id : str | None
            Work item ID
        task_id : str | None
            Task ID
        **kwargs : Any
            Additional exception data

        Returns
        -------
        YWorkflowException
            Created exception
        """
        exc = YWorkflowException(
            id=f"exc-{len(self.exceptions) + 1}",
            exception_type=exception_type,
            message=message,
            case_id=case_id,
            work_item_id=work_item_id,
            task_id=task_id,
            data=kwargs,
        )
        return exc

    def clear_retry_context(self, work_item_id: str) -> None:
        """Clear retry context for work item.

        Parameters
        ----------
        work_item_id : str
            Work item ID
        """
        if work_item_id in self.retry_contexts:
            del self.retry_contexts[work_item_id]


@dataclass
class CompensationHandler:
    """Handler for compensation logic.

    Compensation is the process of undoing the effects of completed
    tasks when later tasks fail.

    Parameters
    ----------
    task_id : str
        Task that this compensates
    compensation_task_id : str | None
        Task to run for compensation
    compensation_logic : Callable[[dict[str, Any]], None] | None
        Custom compensation logic
    """

    task_id: str
    compensation_task_id: str | None = None
    compensation_logic: Callable[[dict[str, Any]], None] | None = None

    def compensate(self, context: dict[str, Any]) -> bool:
        """Execute compensation.

        Parameters
        ----------
        context : dict[str, Any]
            Execution context

        Returns
        -------
        bool
            True if compensation succeeded
        """
        if self.compensation_logic:
            try:
                self.compensation_logic(context)
                return True
            except Exception:
                return False
        return False


@dataclass
class YCompensationService:
    """Service for managing compensation.

    Parameters
    ----------
    handlers : dict[str, CompensationHandler]
        Compensation handlers by task ID
    compensation_stack : list[tuple[str, dict[str, Any]]]
        Stack of completed tasks and their contexts
    """

    handlers: dict[str, CompensationHandler] = field(default_factory=dict)
    compensation_stack: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def register_handler(self, handler: CompensationHandler) -> None:
        """Register compensation handler.

        Parameters
        ----------
        handler : CompensationHandler
            Handler to register
        """
        self.handlers[handler.task_id] = handler

    def record_completion(self, task_id: str, context: dict[str, Any]) -> None:
        """Record task completion for potential compensation.

        Parameters
        ----------
        task_id : str
            Completed task ID
        context : dict[str, Any]
            Execution context
        """
        self.compensation_stack.append((task_id, context.copy()))

    def compensate_all(self) -> list[str]:
        """Compensate all completed tasks (reverse order).

        Returns
        -------
        list[str]
            Task IDs that were compensated
        """
        compensated = []
        while self.compensation_stack:
            task_id, context = self.compensation_stack.pop()
            handler = self.handlers.get(task_id)
            if handler:
                if handler.compensate(context):
                    compensated.append(task_id)
        return compensated

    def compensate_to(self, target_task_id: str) -> list[str]:
        """Compensate back to a specific task.

        Parameters
        ----------
        target_task_id : str
            Task ID to compensate to

        Returns
        -------
        list[str]
            Task IDs that were compensated
        """
        compensated = []
        while self.compensation_stack:
            task_id, context = self.compensation_stack[-1]
            if task_id == target_task_id:
                break
            self.compensation_stack.pop()
            handler = self.handlers.get(task_id)
            if handler:
                if handler.compensate(context):
                    compensated.append(task_id)
        return compensated
