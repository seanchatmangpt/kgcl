"""
Hook Lifecycle & Execution Management.

Manages hook execution pipeline, context propagation, and lifecycle events.
"""

import asyncio
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from kgcl.hooks.performance import PerformanceMetrics, PerformanceOptimizer
from kgcl.hooks.security import ErrorSanitizer
from kgcl.hooks.value_objects import ExecutionId, LifecycleEventType


@dataclass
class HookContext:
    """
    Execution context passed through hook pipeline.

    Parameters
    ----------
    actor : str
        Actor triggering the execution
    request_id : str
        Unique request identifier
    execution_id : ExecutionId
        Unique execution identifier for this specific execution
    metadata : Dict[str, Any]
        Additional context metadata
    """

    actor: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: ExecutionId = field(default_factory=ExecutionId.new)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class HookLifecycleEvent:
    """
    Event emitted during hook lifecycle.

    Parameters
    ----------
    event_type : LifecycleEventType
        Type of event (pre_condition, post_condition, pre_execute, post_execute)
    hook_id : str
        Hook identifier
    timestamp : datetime
        Event timestamp
    metadata : Dict[str, Any]
        Event metadata
    """

    event_type: LifecycleEventType
    hook_id: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class HookChain:
    """
    Chains multiple hooks for sequential execution.

    Each hook's output becomes the next hook's input.
    """

    def __init__(self, hooks: list[Any]) -> None:
        """
        Initialize hook chain.

        Parameters
        ----------
        hooks : List[Hook]
            Hooks to chain in order
        """
        self.hooks = hooks

    async def execute(self, context: dict[str, Any]) -> list[Any]:
        """
        Execute hook chain.

        Parameters
        ----------
        context : Dict[str, Any]
            Initial context

        Returns
        -------
        List[HookReceipt]
            Receipts from all hooks
        """
        from kgcl.hooks.core import HookExecutor

        executor = HookExecutor()
        receipts = []
        current_context = context.copy()

        for hook in self.hooks:
            receipt = await executor.execute(hook, current_context)
            receipts.append(receipt)

            # Pass handler result to next hook as context
            if receipt.handler_result:
                current_context.update(receipt.handler_result)

        return receipts


class HookExecutionPipeline:
    """
    Pipeline for executing multiple hooks with ordering and error handling.

    Manages batch execution, priority ordering, error recovery, and performance tracking.
    """

    def __init__(self, stop_on_error: bool = False, enable_performance_tracking: bool = True):
        """
        Initialize execution pipeline.

        Parameters
        ----------
        stop_on_error : bool
            Whether to stop execution on first error
        enable_performance_tracking : bool
            Whether to track performance metrics
        """
        self.stop_on_error = stop_on_error
        self._event_handlers: list[Callable[..., Any]] = []
        self._error_sanitizer = ErrorSanitizer()
        self._performance_optimizer = PerformanceOptimizer() if enable_performance_tracking else None

    def on_event(self, handler: Callable[..., Any]) -> None:
        """Register event handler."""
        self._event_handlers.append(handler)

    async def execute(self, hook: Any, context: dict[str, Any]) -> Any:
        """
        Execute a single hook with error sanitization and performance tracking.

        Parameters
        ----------
        hook : Hook
            Hook to execute
        context : Dict[str, Any]
            Execution context

        Returns
        -------
        HookReceipt
            Execution receipt with sanitized errors and performance metrics
        """
        from kgcl.hooks.core import HookExecutor

        executor = HookExecutor()

        # Forward events
        for handler in self._event_handlers:
            executor.on_event(handler)

        # Track execution time
        start_time = time.perf_counter()

        try:
            receipt = await executor.execute(hook, context)

            # Record performance metrics
            if self._performance_optimizer:
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

                metric = PerformanceMetrics(
                    operation=f"hook_execute_{hook.name}", latency_ms=latency_ms, success=receipt.error is None
                )
                self._performance_optimizer.record_metric(metric)

            # Sanitize error if present
            if receipt.error:
                # Create an exception to sanitize
                class ReceiptException(Exception):
                    """Exception wrapping receipt error for sanitization.

                    Attributes
                    ----------
                    error_code : str
                        Error code for categorization
                    original_error : str
                        The original error message
                    """

                    def __init__(self, message: str, error_code: str = "UNKNOWN") -> None:
                        self.original_error = message
                        self.error_code = error_code
                        super().__init__(message)

                exc = ReceiptException(receipt.error)
                if hasattr(hook, "error_code"):
                    exc.error_code = hook.error_code

                sanitized = self._error_sanitizer.sanitize(exc)

                # Update receipt with sanitized error and performance metrics
                from kgcl.hooks.core import HookReceipt

                perf_metadata = {}
                if self._performance_optimizer:
                    stats = self._performance_optimizer.get_stats(f"hook_execute_{hook.name}")
                    if stats:
                        perf_metadata["performance_stats"] = stats

                receipt = HookReceipt(
                    hook_id=receipt.hook_id,
                    timestamp=receipt.timestamp,
                    actor=receipt.actor,
                    condition_result=receipt.condition_result,
                    handler_result=receipt.handler_result,
                    duration_ms=receipt.duration_ms,
                    error=sanitized.message,
                    stack_trace=None,  # Remove stack trace for security
                    input_context=receipt.input_context,
                    metadata={**receipt.metadata, "error_code": sanitized.code, "sanitized": True, **perf_metadata},
                    receipt_id=receipt.receipt_id,
                )

            return receipt
        except Exception as e:
            # Record failed execution time
            if self._performance_optimizer:
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

                metric = PerformanceMetrics(operation=f"hook_execute_{hook.name}", latency_ms=latency_ms, success=False)
                self._performance_optimizer.record_metric(metric)

            # Sanitize unexpected errors
            sanitized = self._error_sanitizer.sanitize(e)

            # Create a failed receipt with sanitized error
            from datetime import UTC, datetime

            from kgcl.hooks.conditions import ConditionResult
            from kgcl.hooks.core import HookReceipt

            return HookReceipt(
                hook_id=hook.name,
                timestamp=datetime.now(UTC),
                actor=getattr(hook, "actor", None),
                condition_result=ConditionResult(triggered=False, metadata={"error": sanitized.code}),
                handler_result=None,
                duration_ms=0.0,
                error=sanitized.message,
                stack_trace=None,
                metadata={"error_code": sanitized.code, "sanitized": True},
            )

    async def execute_batch(self, hooks: list[Any], context: dict[str, Any]) -> list[Any]:
        """
        Execute multiple hooks in priority order with performance tracking.

        Parameters
        ----------
        hooks : List[Hook]
            Hooks to execute
        context : Dict[str, Any]
            Execution context

        Returns
        -------
        List[HookReceipt]
            Receipts from all executed hooks
        """
        # Track batch execution time
        batch_start_time = time.perf_counter()

        # Sort by priority (high to low)
        sorted_hooks = sorted(hooks, key=lambda h: h.priority, reverse=True)

        receipts = []
        for hook in sorted_hooks:
            receipt = await self.execute(hook, context)
            receipts.append(receipt)

            # Stop on error if configured
            if self.stop_on_error and receipt.error:
                break

        # Record batch metrics
        if self._performance_optimizer:
            batch_end_time = time.perf_counter()
            batch_latency_ms = (batch_end_time - batch_start_time) * 1000

            metric = PerformanceMetrics(
                operation="hook_batch_execute",
                latency_ms=batch_latency_ms,
                success=all(r.error is None for r in receipts),
            )
            self._performance_optimizer.record_metric(metric)

        return receipts

    def get_performance_stats(self, operation: str | None = None) -> dict | None:
        """Get performance statistics.

        Parameters
        ----------
        operation : Optional[str]
            Specific operation to get stats for, or None for all operations

        Returns
        -------
        Optional[Dict]
            Performance statistics or None if tracking is disabled
        """
        if self._performance_optimizer is None:
            return None

        if operation:
            return self._performance_optimizer.get_stats(operation)

        # Return stats for all operations
        all_ops = self._performance_optimizer.get_all_operations()
        return {op: self._performance_optimizer.get_stats(op) for op in all_ops}


class HookStateManager:
    """
    Manages hook state transitions and persistence.

    Tracks state changes and provides audit trail.
    """

    def __init__(self) -> None:
        """Initialize state manager."""
        self._state_history: dict[str, list[dict[str, Any]]] = {}

    def record_transition(self, hook_id: str, from_state: str, to_state: str, metadata: dict[str, Any]) -> None:
        """
        Record state transition.

        Parameters
        ----------
        hook_id : str
            Hook identifier
        from_state : str
            Previous state
        to_state : str
            New state
        metadata : Dict[str, Any]
            Transition metadata
        """
        if hook_id not in self._state_history:
            self._state_history[hook_id] = []

        self._state_history[hook_id].append(
            {"from": from_state, "to": to_state, "timestamp": datetime.now(UTC), "metadata": metadata}
        )

    def get_history(self, hook_id: str) -> list[dict[str, Any]]:
        """
        Get state history for a hook.

        Parameters
        ----------
        hook_id : str
            Hook identifier

        Returns
        -------
        List[Dict[str, Any]]
            State transition history
        """
        return self._state_history.get(hook_id, [])


class HookErrorRecovery:
    """
    Handles error recovery for hook execution.

    Provides retry logic and fallback strategies.
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize error recovery.

        Parameters
        ----------
        max_retries : int
            Maximum retry attempts
        retry_delay : float
            Delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def execute_with_retry(self, hook: Any, context: dict[str, Any]) -> Any:
        """
        Execute hook with retry on failure.

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
        from kgcl.hooks.core import HookExecutor

        executor = HookExecutor()
        last_receipt = None

        for attempt in range(self.max_retries + 1):
            receipt = await executor.execute(hook, context)
            last_receipt = receipt

            if not receipt.error:
                return receipt

            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay)

        return last_receipt
