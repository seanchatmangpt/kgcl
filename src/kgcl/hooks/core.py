from __future__ import annotations

"""
Hook Core Domain Model.

This module implements the core hook abstractions including Hook, HookState,
HookReceipt, HookRegistry, and HookExecutor following Chicago School TDD principles.
"""

import asyncio
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from kgcl.hooks.conditions import Condition, ConditionResult
from kgcl.hooks.value_objects import HookName, LifecycleEventType


class HookValidationError(Exception):
    """Raised when hook validation fails.

    Attributes
    ----------
    message : str
        Validation failure message
    hook_name : str | None
        Name of the hook that failed validation (optional)
    reason : str | None
        Validation failure reason (optional)
    """

    def __init__(self, message: str, hook_name: str | None = None, reason: str | None = None) -> None:
        """Initialize HookValidationError.

        Parameters
        ----------
        message : str
            Validation failure message (required)
        hook_name : str | None, optional
            Name of the hook that failed validation
        reason : str | None, optional
            Validation failure reason
        """
        self.message = message
        self.hook_name = hook_name
        self.reason = reason
        if hook_name and reason:
            super().__init__(f"Hook '{hook_name}' validation failed: {reason}")
        else:
            super().__init__(message)


class HookState(Enum):
    """Hook lifecycle states."""

    PENDING = "pending"
    ACTIVE = "active"
    EXECUTED = "executed"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class HookReceipt:
    """
    Immutable receipt of hook execution.

    Captures complete execution provenance including condition evaluation,
    handler execution, timing, and any errors.

    Parameters
    ----------
    hook_id : str
        Unique identifier of the executed hook
    timestamp : datetime
        Time of execution
    condition_result : ConditionResult
        Result of condition evaluation
    handler_result : Optional[Dict[str, Any]]
        Result from handler execution (None if condition failed or handler errored)
    duration_ms : float
        Execution duration in milliseconds
    actor : Optional[str]
        Actor who triggered the execution
    error : Optional[str]
        Error message if execution failed
    stack_trace : Optional[str]
        Stack trace if execution failed
    memory_delta_bytes : Optional[int]
        Memory change during execution
    input_context : Optional[Dict[str, Any]]
        Input context (may be truncated)
    metadata : Dict[str, Any]
        Additional metadata
    receipt_id : str
        Unique receipt identifier
    truncated : bool
        Whether data was truncated due to size
    """

    hook_id: HookName
    timestamp: datetime
    condition_result: ConditionResult
    handler_result: dict[str, Any] | None
    duration_ms: float
    actor: str | None = None
    error: str | None = None
    stack_trace: str | None = None
    memory_delta_bytes: int | None = None
    input_context: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    receipt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    truncated: bool = field(default=False, init=False)
    max_size_bytes: int | None = None
    merkle_anchor: Any | None = None

    def __post_init__(self) -> None:
        """Finalize validated fields and enforce truncation rules."""
        object.__setattr__(self, "hook_id", HookName.ensure(self.hook_id))

        # Truncate oversized data if needed
        if self.max_size_bytes and self.handler_result:
            import json

            result_size = len(json.dumps(self.handler_result))
            if result_size > self.max_size_bytes:
                object.__setattr__(self, "truncated", True)
                object.__setattr__(self, "handler_result", {"_truncated": True, "_size": result_size})


@dataclass
class Hook:
    """
    Hook definition with condition and handler.

    Hooks monitor knowledge graph changes and execute handlers when conditions are met.

    Parameters
    ----------
    name : str
        Unique hook name
    description : str
        Human-readable description
    condition : Condition
        Condition that triggers the hook
    handler : Callable
        Function to execute when condition is met
    priority : int
        Execution priority (0-100, higher = earlier)
    timeout : float
        Maximum execution time in seconds
    enabled : bool
        Whether hook is enabled
    actor : Optional[str]
        Actor who created the hook
    metadata : Dict[str, Any]
        Additional metadata
    """

    name: HookName
    description: str
    condition: Condition
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    priority: int = 50
    timeout: float = 30.0
    enabled: bool = True
    actor: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Lifecycle tracking
    state: HookState = field(default=HookState.PENDING, init=False)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC), init=False)
    executed_at: datetime | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        """Validate hook structure."""
        try:
            object.__setattr__(self, "name", HookName.ensure(str(self.name)))
        except ValueError as exc:
            raise HookValidationError(str(exc)) from exc

        if self.condition is None:
            raise HookValidationError("Hook condition is required")

        if self.handler is None:
            raise HookValidationError("Hook handler is required")

        if not (0 <= self.priority <= 100):
            raise HookValidationError("Hook priority must be between 0 and 100")

    def enable(self) -> None:
        """Enable the hook."""
        self.enabled = True

    def disable(self) -> None:
        """Disable the hook."""
        self.enabled = False

    def _transition_state(self, new_state: HookState) -> None:
        """Transition to a new state."""
        self.state = new_state
        if new_state in [HookState.EXECUTED, HookState.COMPLETED, HookState.FAILED]:
            self.executed_at = datetime.now(UTC)


class HookRegistry:
    """
    Registry for managing multiple hooks.

    Provides registration, lookup, and querying of hooks with deduplication.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._hooks: dict[HookName, Hook] = {}

    def register(self, hook: Hook) -> None:
        """
        Register a hook.

        Parameters
        ----------
        hook : Hook
            Hook to register

        Raises
        ------
        HookValidationError
            If hook with same name already exists
        """
        if hook.name in self._hooks:
            raise HookValidationError(f"Hook '{hook.name}' already exists")

        self._hooks[hook.name] = hook

    def unregister(self, name: str) -> None:
        """
        Unregister a hook by name.

        Parameters
        ----------
        name : str
            Name of hook to unregister
        """
        self._hooks.pop(HookName.ensure(name), None)

    def get(self, name: str) -> Hook | None:
        """
        Get hook by name.

        Parameters
        ----------
        name : str
            Hook name

        Returns
        -------
        Optional[Hook]
            Hook if found, None otherwise
        """
        return self._hooks.get(HookName.ensure(name))

    def get_all(self) -> list[Hook]:
        """
        Get all registered hooks.

        Returns
        -------
        List[Hook]
            All registered hooks
        """
        return list(self._hooks.values())

    def get_all_sorted(self) -> list[Hook]:
        """
        Get all hooks sorted by priority (high to low).

        Returns
        -------
        List[Hook]
            Hooks sorted by priority descending
        """
        return sorted(self._hooks.values(), key=lambda h: h.priority, reverse=True)


class HookManager:
    """
    Manage hook lifecycle and execution.

    Provides centralized hook management with execution tracking,
    statistics, and failure monitoring.
    """

    def __init__(self) -> None:
        """Initialize hook manager."""
        self.hooks: dict[str, Hook] = {}
        self.execution_history: list[HookReceipt] = []
        self.failed_hooks: dict[str, list[str]] = {}
        self._hook_ids: dict[HookName, str] = {}  # hook_name -> hook_id

    def register_hook(self, hook: Hook) -> str:
        """
        Register hook and return hook ID.

        Parameters
        ----------
        hook : Hook
            Hook to register

        Returns
        -------
        str
            Generated hook ID

        Raises
        ------
        HookValidationError
            If hook with same name already exists
        """
        if hook.name in self._hook_ids:
            raise HookValidationError(f"Hook '{hook.name}' already registered")

        hook_id = str(uuid.uuid4())
        self.hooks[hook_id] = hook
        self._hook_ids[hook.name] = hook_id
        self.failed_hooks[hook_id] = []

        return hook_id

    def unregister_hook(self, hook_id: str) -> None:
        """
        Unregister hook.

        Parameters
        ----------
        hook_id : str
            Hook ID to unregister
        """
        if hook_id in self.hooks:
            hook = self.hooks[hook_id]
            del self.hooks[hook_id]
            if hook.name in self._hook_ids:
                del self._hook_ids[hook.name]
            if hook_id in self.failed_hooks:
                del self.failed_hooks[hook_id]

    def get_hook(self, hook_id: str) -> Hook | None:
        """
        Get hook by ID.

        Parameters
        ----------
        hook_id : str
            Hook ID

        Returns
        -------
        Optional[Hook]
            Hook if found, None otherwise
        """
        return self.hooks.get(hook_id)

    def get_hook_by_name(self, name: str) -> Hook | None:
        """
        Get hook by name.

        Parameters
        ----------
        name : str
            Hook name

        Returns
        -------
        Optional[Hook]
            Hook if found, None otherwise
        """
        hook_id = self._hook_ids.get(HookName.ensure(name))
        if hook_id:
            return self.hooks.get(hook_id)
        return None

    def record_execution(self, receipt: HookReceipt) -> None:
        """
        Record hook execution receipt.

        Parameters
        ----------
        receipt : HookReceipt
            Execution receipt to record
        """
        self.execution_history.append(receipt)

        # Track failures
        if receipt.error:
            hook_id = receipt.hook_id
            if hook_id not in self.failed_hooks:
                self.failed_hooks[hook_id] = []
            self.failed_hooks[hook_id].append(receipt.error)

    def get_hook_stats(self, hook_id: str) -> dict[str, Any]:
        """
        Get execution statistics for hook.

        Parameters
        ----------
        hook_id : str
            Hook ID

        Returns
        -------
        Dict[str, Any]
            Statistics including execution count, success rate, avg duration
        """
        hook = self.hooks.get(hook_id)
        if not hook:
            return {}

        # Find all executions for this hook
        executions = [r for r in self.execution_history if r.hook_id == hook_id]

        if not executions:
            return {"total_executions": 0, "successes": 0, "failures": 0, "success_rate": 0.0}

        successes = sum(1 for r in executions if not r.error)
        failures = sum(1 for r in executions if r.error)

        return {
            "total_executions": len(executions),
            "successes": successes,
            "failures": failures,
            "success_rate": successes / len(executions) if executions else 0.0,
            "avg_duration_ms": sum(r.duration_ms for r in executions) / len(executions),
            "recent_errors": self.failed_hooks.get(hook_id, [])[-5:],  # Last 5 errors
        }

    def get_all_hooks(self) -> list[Hook]:
        """
        Get all registered hooks.

        Returns
        -------
        List[Hook]
            List of all hooks
        """
        return list(self.hooks.values())

    def clear_history(self) -> None:
        """Clear execution history."""
        self.execution_history.clear()
        for hook_id in self.failed_hooks:
            self.failed_hooks[hook_id].clear()


class HookExecutor:
    """
    Executes hooks and produces receipts.

    Manages hook lifecycle, condition evaluation, handler execution,
    and receipt generation.
    """

    def __init__(self) -> None:
        """Initialize executor."""
        self._event_handlers: list[Callable[..., Any]] = []

    def on_event(self, handler: Callable[..., Any]) -> None:
        """
        Register event handler for lifecycle events.

        Parameters
        ----------
        handler : Callable
            Event handler function
        """
        self._event_handlers.append(handler)

    def _emit_event(self, event_type: LifecycleEventType, hook: Hook, **kwargs: Any) -> None:
        """Emit lifecycle event."""
        from kgcl.hooks.lifecycle import HookLifecycleEvent

        event = HookLifecycleEvent(
            event_type=event_type, hook_id=hook.name, timestamp=datetime.now(UTC), metadata=kwargs
        )

        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception:
                # Don't let event handler errors break execution
                pass

    async def execute(self, hook: Hook, context: dict[str, Any]) -> HookReceipt:
        """
        Execute a hook and return receipt.

        Parameters
        ----------
        hook : Hook
            Hook to execute
        context : Dict[str, Any]
            Execution context

        Returns
        -------
        HookReceipt
            Execution receipt
        """
        start_time = datetime.now(UTC)
        condition_result: ConditionResult | None = None
        handler_result: dict[str, Any] | None = None
        error: str | None = None
        stack_trace: str | None = None

        try:
            # Transition to ACTIVE
            hook._transition_state(HookState.ACTIVE)
            self._emit_event(LifecycleEventType.PRE_CONDITION, hook)

            # Evaluate condition with timeout
            try:
                condition_result = await asyncio.wait_for(hook.condition.evaluate(context), timeout=hook.timeout)
            except TimeoutError:
                error = f"Condition evaluation exceeded timeout of {hook.timeout}s"
                hook._transition_state(HookState.FAILED)
                condition_result = ConditionResult(triggered=False, metadata={"error": "timeout"})
            except Exception as e:
                error = f"Condition evaluation failed: {e!s}"
                stack_trace = traceback.format_exc()
                hook._transition_state(HookState.FAILED)
                condition_result = ConditionResult(triggered=False, metadata={"error": str(e)})

            self._emit_event(LifecycleEventType.POST_CONDITION, hook, result=condition_result)

            # Execute handler if condition triggered
            if condition_result and condition_result.triggered and not error:
                hook._transition_state(HookState.EXECUTED)
                self._emit_event(LifecycleEventType.PRE_EXECUTE, hook)

                try:
                    # Execute handler (sync or async)
                    if asyncio.iscoroutinefunction(hook.handler):
                        handler_result = await asyncio.wait_for(hook.handler(context), timeout=hook.timeout)
                    else:
                        handler_result = hook.handler(context)

                    hook._transition_state(HookState.COMPLETED)
                except TimeoutError:
                    error = f"Handler execution exceeded timeout of {hook.timeout}s"
                    hook._transition_state(HookState.FAILED)
                except Exception as e:
                    error = f"Handler execution failed: {e!s}"
                    stack_trace = traceback.format_exc()
                    hook._transition_state(HookState.FAILED)

                self._emit_event(LifecycleEventType.POST_EXECUTE, hook, result=handler_result)
            elif condition_result and not condition_result.triggered:
                # Condition not triggered, mark as completed
                hook._transition_state(HookState.COMPLETED)

        except Exception as e:
            error = f"Unexpected error: {e!s}"
            stack_trace = traceback.format_exc()
            hook._transition_state(HookState.FAILED)

        # Calculate duration
        end_time = datetime.now(UTC)
        duration_ms = (end_time - start_time).total_seconds() * 1000

        # Create receipt
        receipt = HookReceipt(
            hook_id=hook.name,
            timestamp=start_time,
            actor=hook.actor,
            condition_result=condition_result or ConditionResult(triggered=False, metadata={}),
            handler_result=handler_result,
            duration_ms=duration_ms,
            error=error,
            stack_trace=stack_trace,
            input_context=context.copy() if context else {},
            metadata={"final_state": hook.state.value},
        )

        return receipt
