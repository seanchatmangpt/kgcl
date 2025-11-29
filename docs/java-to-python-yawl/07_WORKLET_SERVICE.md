# Gap 7: Worklet Service (Exception Handling Runtime)

## Problem Statement

The Worklet Service provides dynamic exception handling and runtime workflow modifications. Exception handlers are defined but never triggered at runtime.

## YAWL Worklet Concepts

| Concept | Description |
|---------|-------------|
| **Worklet** | Small workflow that handles a specific exception |
| **Ripple-Down Rules (RDR)** | Decision tree for selecting appropriate worklet |
| **Exception Type** | Constraint violation, timeout, resource unavailable, etc. |
| **Compensation** | Workflow to undo completed work |

## Current State

```python
# src/kgcl/yawl/engine/y_exception.py
@dataclass
class YExceptionService:
    """Exception handling service for YAWL workflows."""

    handlers: dict[str, YExceptionHandler]

    def raise_exception(self, exception_type, context):
        # Looks up handler and returns it
        # Does NOT execute handler or trigger worklet
        pass
```

```python
# src/kgcl/yawl/elements/y_exception_handler.py
@dataclass(frozen=True)
class YExceptionHandler:
    exception_type: ExceptionType
    action: ExceptionAction  # CONTINUE, SUSPEND, COMPENSATE, RESTART, etc.
    worklet_id: str | None = None
```

**Problem**: Exception service finds handlers but doesn't execute them.

## Target Behavior

```
Exception Raised
      │
      ▼
┌─────────────────────────────────┐
│  ExceptionService.raise()       │
│  - Classify exception type      │
│  - Find matching handler        │
└─────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────┐
│  Execute handler action:        │
│  - CONTINUE: Log and proceed    │
│  - SUSPEND: Pause work item     │
│  - CANCEL: Cancel work item     │
│  - COMPENSATE: Run compensation │
│  - RESTART: Re-execute task     │
│  - FORCE_COMPLETE: Skip task    │
│  - WORKLET: Run exception flow  │
└─────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────┐
│  If worklet specified:          │
│  - Load worklet definition      │
│  - Create subprocess runner     │
│  - Execute to completion        │
│  - Apply results to main flow   │
└─────────────────────────────────┘
```

## Implementation Plan

### Step 1: Extend Exception Types

```python
# src/kgcl/yawl/engine/y_exception.py

from enum import Enum


class ExceptionType(Enum):
    """Types of workflow exceptions."""

    # Work item exceptions
    CONSTRAINT_VIOLATION = "constraint_violation"
    TIMEOUT = "timeout"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    EXTERNAL_FAILURE = "external_failure"
    INVALID_DATA = "invalid_data"

    # Case exceptions
    DEADLINE_EXPIRED = "deadline_expired"
    CASE_CANCELLED = "case_cancelled"
    PARENT_CASE_FAILED = "parent_case_failed"

    # System exceptions
    SERVICE_UNAVAILABLE = "service_unavailable"
    SPECIFICATION_ERROR = "specification_error"

    # Custom
    CUSTOM = "custom"


class ExceptionAction(Enum):
    """Actions to take when exception occurs."""

    CONTINUE = "continue"           # Log and proceed normally
    SUSPEND = "suspend"             # Pause work item for manual resolution
    CANCEL = "cancel"               # Cancel work item
    FAIL = "fail"                   # Fail work item
    COMPENSATE = "compensate"       # Run compensation workflow
    RESTART = "restart"             # Re-execute from beginning
    FORCE_COMPLETE = "force_complete"  # Mark complete without execution
    ROLLBACK = "rollback"           # Undo and retry
    WORKLET = "worklet"             # Execute exception worklet
```

### Step 2: Exception Handler with Worklet Support

```python
# src/kgcl/yawl/elements/y_exception_handler.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class YExceptionHandler:
    """Exception handler definition.

    Parameters
    ----------
    id : str
        Handler identifier
    exception_type : ExceptionType
        Type of exception this handles
    action : ExceptionAction
        Action to take
    worklet_id : str | None
        ID of worklet specification to execute
    compensation_id : str | None
        ID of compensation workflow
    condition : str | None
        Expression to evaluate for handler selection
    priority : int
        Handler priority (higher = checked first)
    """

    id: str
    exception_type: ExceptionType
    action: ExceptionAction
    worklet_id: str | None = None
    compensation_id: str | None = None
    condition: str | None = None
    priority: int = 0


@dataclass
class YExceptionContext:
    """Context information for exception handling.

    Parameters
    ----------
    exception_type : ExceptionType
        Type of exception
    case_id : str
        Affected case
    work_item_id : str | None
        Affected work item (if applicable)
    task_id : str | None
        Affected task (if applicable)
    message : str
        Exception message
    data : dict[str, Any]
        Additional context data
    """

    exception_type: ExceptionType
    case_id: str
    work_item_id: str | None = None
    task_id: str | None = None
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
```

### Step 3: Exception Service with Execution

```python
# src/kgcl/yawl/engine/y_exception.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from kgcl.yawl.elements.y_exception_handler import (
    ExceptionAction,
    ExceptionType,
    YExceptionContext,
    YExceptionHandler,
)

if TYPE_CHECKING:
    from kgcl.yawl.engine.y_engine import YEngine


@dataclass
class YExceptionResult:
    """Result of exception handling.

    Parameters
    ----------
    handled : bool
        Whether exception was handled
    action_taken : ExceptionAction | None
        Action that was executed
    worklet_case_id : str | None
        ID of worklet case if executed
    output : dict[str, Any]
        Output data from handling
    message : str
        Result message
    """

    handled: bool
    action_taken: ExceptionAction | None = None
    worklet_case_id: str | None = None
    output: dict[str, Any] = field(default_factory=dict)
    message: str = ""


@dataclass
class YExceptionService:
    """Exception handling service with worklet execution.

    Parameters
    ----------
    handlers : dict[str, YExceptionHandler]
        Registered exception handlers
    worklets : dict[str, YSpecification]
        Worklet specifications available for execution
    """

    handlers: dict[str, YExceptionHandler] = field(default_factory=dict)
    worklets: dict[str, Any] = field(default_factory=dict)  # YSpecification

    # Engine reference for executing actions
    _engine: YEngine | None = field(default=None, repr=False)

    # Action implementations
    _action_handlers: dict[
        ExceptionAction, Callable[[YExceptionContext, YExceptionHandler], YExceptionResult]
    ] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        """Set up default action handlers."""
        self._action_handlers = {
            ExceptionAction.CONTINUE: self._handle_continue,
            ExceptionAction.SUSPEND: self._handle_suspend,
            ExceptionAction.CANCEL: self._handle_cancel,
            ExceptionAction.FAIL: self._handle_fail,
            ExceptionAction.COMPENSATE: self._handle_compensate,
            ExceptionAction.RESTART: self._handle_restart,
            ExceptionAction.FORCE_COMPLETE: self._handle_force_complete,
            ExceptionAction.ROLLBACK: self._handle_rollback,
            ExceptionAction.WORKLET: self._handle_worklet,
        }

    def set_engine(self, engine: YEngine) -> None:
        """Set engine reference for action execution."""
        self._engine = engine

    def register_handler(self, handler: YExceptionHandler) -> None:
        """Register exception handler."""
        self.handlers[handler.id] = handler

    def register_worklet(self, worklet_id: str, specification: Any) -> None:
        """Register worklet specification."""
        self.worklets[worklet_id] = specification

    def raise_exception(self, context: YExceptionContext) -> YExceptionResult:
        """Raise and handle exception.

        Parameters
        ----------
        context : YExceptionContext
            Exception context with type, case, work item info

        Returns
        -------
        YExceptionResult
            Result of handling
        """
        # Find matching handler
        handler = self._find_handler(context)

        if handler is None:
            return YExceptionResult(
                handled=False,
                message=f"No handler for exception type: {context.exception_type}",
            )

        # Execute handler action
        action_handler = self._action_handlers.get(handler.action)
        if action_handler is None:
            return YExceptionResult(
                handled=False,
                message=f"Unknown action: {handler.action}",
            )

        return action_handler(context, handler)

    def _find_handler(
        self, context: YExceptionContext
    ) -> YExceptionHandler | None:
        """Find best matching handler for exception."""
        matching = []

        for handler in self.handlers.values():
            # Match by exception type
            if handler.exception_type != context.exception_type:
                continue

            # Evaluate condition if present
            if handler.condition:
                if not self._evaluate_condition(handler.condition, context):
                    continue

            matching.append(handler)

        if not matching:
            return None

        # Return highest priority handler
        return max(matching, key=lambda h: h.priority)

    def _evaluate_condition(
        self, condition: str, context: YExceptionContext
    ) -> bool:
        """Evaluate handler condition against context."""
        if self._engine is None:
            return True

        # Use engine's expression evaluator
        return self._engine._evaluate_expression(condition, context.data)

    # --- Action Handlers ---

    def _handle_continue(
        self, context: YExceptionContext, handler: YExceptionHandler
    ) -> YExceptionResult:
        """Log exception and continue normally."""
        return YExceptionResult(
            handled=True,
            action_taken=ExceptionAction.CONTINUE,
            message=f"Exception logged and continuing: {context.message}",
        )

    def _handle_suspend(
        self, context: YExceptionContext, handler: YExceptionHandler
    ) -> YExceptionResult:
        """Suspend work item for manual resolution."""
        if self._engine and context.work_item_id:
            self._engine.suspend_work_item(context.work_item_id)

        return YExceptionResult(
            handled=True,
            action_taken=ExceptionAction.SUSPEND,
            message="Work item suspended pending manual resolution",
        )

    def _handle_cancel(
        self, context: YExceptionContext, handler: YExceptionHandler
    ) -> YExceptionResult:
        """Cancel work item."""
        if self._engine and context.work_item_id:
            self._engine.cancel_work_item(context.work_item_id, context.message)

        return YExceptionResult(
            handled=True,
            action_taken=ExceptionAction.CANCEL,
            message="Work item cancelled",
        )

    def _handle_fail(
        self, context: YExceptionContext, handler: YExceptionHandler
    ) -> YExceptionResult:
        """Fail work item."""
        if self._engine and context.work_item_id:
            self._engine.fail_work_item(context.work_item_id, context.message)

        return YExceptionResult(
            handled=True,
            action_taken=ExceptionAction.FAIL,
            message="Work item failed",
        )

    def _handle_restart(
        self, context: YExceptionContext, handler: YExceptionHandler
    ) -> YExceptionResult:
        """Restart work item execution."""
        if self._engine and context.work_item_id:
            self._engine.restart_work_item(context.work_item_id)

        return YExceptionResult(
            handled=True,
            action_taken=ExceptionAction.RESTART,
            message="Work item restarted",
        )

    def _handle_force_complete(
        self, context: YExceptionContext, handler: YExceptionHandler
    ) -> YExceptionResult:
        """Force complete work item without execution."""
        if self._engine and context.work_item_id:
            self._engine.complete_work_item(
                context.work_item_id,
                {"_force_completed": True, "_reason": context.message},
            )

        return YExceptionResult(
            handled=True,
            action_taken=ExceptionAction.FORCE_COMPLETE,
            message="Work item force completed",
        )

    def _handle_rollback(
        self, context: YExceptionContext, handler: YExceptionHandler
    ) -> YExceptionResult:
        """Rollback and retry."""
        if self._engine and context.work_item_id:
            # Cancel current, create new
            self._engine.cancel_work_item(context.work_item_id, "Rollback")
            # Re-enable task would need to be implemented

        return YExceptionResult(
            handled=True,
            action_taken=ExceptionAction.ROLLBACK,
            message="Work item rolled back",
        )

    def _handle_compensate(
        self, context: YExceptionContext, handler: YExceptionHandler
    ) -> YExceptionResult:
        """Run compensation workflow."""
        if handler.compensation_id is None:
            return YExceptionResult(
                handled=False,
                message="No compensation workflow specified",
            )

        return self._execute_worklet(handler.compensation_id, context)

    def _handle_worklet(
        self, context: YExceptionContext, handler: YExceptionHandler
    ) -> YExceptionResult:
        """Execute exception worklet."""
        if handler.worklet_id is None:
            return YExceptionResult(
                handled=False,
                message="No worklet specified",
            )

        return self._execute_worklet(handler.worklet_id, context)

    def _execute_worklet(
        self, worklet_id: str, context: YExceptionContext
    ) -> YExceptionResult:
        """Execute a worklet workflow.

        Parameters
        ----------
        worklet_id : str
            ID of worklet specification
        context : YExceptionContext
            Exception context passed to worklet

        Returns
        -------
        YExceptionResult
            Worklet execution result
        """
        worklet_spec = self.worklets.get(worklet_id)
        if worklet_spec is None:
            return YExceptionResult(
                handled=False,
                message=f"Worklet not found: {worklet_id}",
            )

        if self._engine is None:
            return YExceptionResult(
                handled=False,
                message="Engine not available for worklet execution",
            )

        # Prepare input data for worklet
        input_data = {
            "exception_type": context.exception_type.value,
            "case_id": context.case_id,
            "work_item_id": context.work_item_id,
            "task_id": context.task_id,
            "message": context.message,
            **context.data,
        }

        # Launch worklet as new case
        worklet_case_id = self._engine.launch_case(
            specification_id=worklet_id,
            case_data=input_data,
        )

        if worklet_case_id is None:
            return YExceptionResult(
                handled=False,
                message="Failed to launch worklet case",
            )

        return YExceptionResult(
            handled=True,
            action_taken=ExceptionAction.WORKLET,
            worklet_case_id=worklet_case_id,
            message=f"Worklet launched: {worklet_case_id}",
        )
```

### Step 4: Engine Integration

```python
# src/kgcl/yawl/engine/y_engine.py

@dataclass
class YEngine:
    # ... existing fields ...

    exception_service: YExceptionService = field(default_factory=YExceptionService)

    def __post_init__(self) -> None:
        """Initialize engine components."""
        self.exception_service.set_engine(self)

    def raise_exception(
        self,
        exception_type: ExceptionType,
        case_id: str,
        work_item_id: str | None = None,
        task_id: str | None = None,
        message: str = "",
        data: dict[str, Any] | None = None,
    ) -> YExceptionResult:
        """Raise workflow exception.

        Parameters
        ----------
        exception_type : ExceptionType
            Type of exception
        case_id : str
            Affected case ID
        work_item_id : str | None
            Affected work item ID
        task_id : str | None
            Affected task ID
        message : str
            Exception message
        data : dict[str, Any] | None
            Additional context data

        Returns
        -------
        YExceptionResult
            Result of exception handling
        """
        context = YExceptionContext(
            exception_type=exception_type,
            case_id=case_id,
            work_item_id=work_item_id,
            task_id=task_id,
            message=message,
            data=data or {},
        )

        result = self.exception_service.raise_exception(context)

        self._emit_event(
            "EXCEPTION_RAISED",
            case_id=case_id,
            work_item_id=work_item_id,
            data={
                "type": exception_type.value,
                "message": message,
                "handled": result.handled,
                "action": result.action_taken.value if result.action_taken else None,
            },
        )

        return result

    # Add methods used by exception handlers

    def suspend_work_item(self, work_item_id: str) -> bool:
        """Suspend a work item."""
        work_item = self._find_work_item(work_item_id)
        if work_item is None:
            return False
        work_item.suspend()
        self._emit_event("WORK_ITEM_SUSPENDED", work_item_id=work_item_id)
        return True

    def cancel_work_item(self, work_item_id: str, reason: str = "") -> bool:
        """Cancel a work item."""
        work_item = self._find_work_item(work_item_id)
        if work_item is None:
            return False
        work_item.cancel(reason)
        self._emit_event(
            "WORK_ITEM_CANCELLED",
            work_item_id=work_item_id,
            data={"reason": reason},
        )
        return True

    def restart_work_item(self, work_item_id: str) -> bool:
        """Restart a work item from beginning."""
        work_item = self._find_work_item(work_item_id)
        if work_item is None:
            return False

        # Reset to fired state
        work_item.status = WorkItemStatus.FIRED
        work_item.started_time = None
        work_item.data_output = {}

        # Re-resource
        case = self.cases.get(work_item.case_id)
        if case:
            spec = self.specifications.get(case.specification_id)
            if spec:
                task = spec.get_task(work_item.task_id)
                if task:
                    self._resource_work_item(work_item, task)

        self._emit_event("WORK_ITEM_RESTARTED", work_item_id=work_item_id)
        return True
```

## Test Cases

```python
class TestExceptionService:
    """Tests for exception handling."""

    def test_handler_found_by_type(self) -> None:
        """Handler found by exception type."""
        # Register handler for TIMEOUT
        # Raise TIMEOUT exception
        # Assert: handler found and executed

    def test_handler_priority(self) -> None:
        """Higher priority handler selected."""
        # Register two handlers for same type
        # Higher priority has different action
        # Assert: high priority action executed

    def test_conditional_handler(self) -> None:
        """Handler condition evaluated."""
        # Handler with condition "amount > 1000"
        # Raise with amount=500 → not matched
        # Raise with amount=1500 → matched

    def test_suspend_action(self) -> None:
        """Suspend action suspends work item."""
        # Raise exception with SUSPEND handler
        # Assert: work item status == SUSPENDED

    def test_worklet_execution(self) -> None:
        """Worklet launched as new case."""
        # Register worklet specification
        # Handler with WORKLET action
        # Raise exception
        # Assert: new case created with worklet spec

    def test_compensation_workflow(self) -> None:
        """Compensation workflow executed."""
        # Handler with COMPENSATE action
        # Assert: compensation case launched

    def test_force_complete(self) -> None:
        """Force complete skips work item."""
        # Raise with FORCE_COMPLETE handler
        # Assert: work item completed with force flag
```

## Dependencies

- Expression evaluation for handler conditions
- Case launching for worklet execution

## Complexity: HIGH

- Multiple exception types
- Action implementations
- Worklet subprocess execution
- Compensation workflows

## Estimated Effort

- Implementation: 8-12 hours
- Testing: 6-8 hours
- Total: 2-3 days

## Priority: MEDIUM

Exception handling is important for production reliability but not blocking basic execution.
