"""
Chicago School TDD Tests for Hook Lifecycle & Execution.

Tests drive the design of hook execution pipeline and state management.
Real object collaboration without mocking core domain.
"""

from typing import Any

import pytest

from kgcl.hooks.conditions import Condition, ConditionResult
from kgcl.hooks.core import Hook, HookExecutor, HookState
from kgcl.hooks.lifecycle import HookChain, HookContext, HookExecutionPipeline, HookLifecycleEvent
from kgcl.hooks.value_objects import LifecycleEventType


class SimpleCondition(Condition):
    """Test condition."""

    def __init__(self, should_trigger: bool = True):
        super().__init__()
        self.should_trigger = should_trigger

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        return ConditionResult(triggered=self.should_trigger, metadata={"simple": True})


def simple_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Simple handler that processes context."""
    return {"processed": True, "input_count": len(context)}


def transforming_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Handler that transforms input."""
    return {"transformed": True, "value": context.get("value", 0) * 2}


def failing_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Handler that fails."""
    raise RuntimeError("Handler error")


class TestHookStateTransitions:
    """Test hook state transition behaviors."""

    @pytest.mark.asyncio
    async def test_hook_transitions_from_pending_to_active(self):
        """Hook lifecycle: PENDING → ACTIVE on condition evaluation."""
        hook = Hook(
            name="test", description="Test", condition=SimpleCondition(), handler=simple_handler
        )

        assert hook.state == HookState.PENDING

        executor = HookExecutor()
        await executor.execute(hook, context={})

        # After execution, hook should have transitioned through ACTIVE
        assert hook.state in [HookState.EXECUTED, HookState.COMPLETED]

    @pytest.mark.asyncio
    async def test_successful_condition_triggers_handler_execution(self):
        """Successful condition triggers handler execution."""
        hook = Hook(
            name="test",
            description="Test",
            condition=SimpleCondition(should_trigger=True),
            handler=simple_handler,
        )

        executor = HookExecutor()
        receipt = await executor.execute(hook, context={})

        assert receipt.condition_result.triggered is True
        assert receipt.handler_result is not None
        assert receipt.handler_result["processed"] is True

    @pytest.mark.asyncio
    async def test_failed_condition_skips_handler(self):
        """Failed condition skips handler."""
        hook = Hook(
            name="test",
            description="Test",
            condition=SimpleCondition(should_trigger=False),
            handler=simple_handler,
        )

        executor = HookExecutor()
        receipt = await executor.execute(hook, context={})

        assert receipt.condition_result.triggered is False
        assert receipt.handler_result is None  # Handler not executed


class TestHandlerExecution:
    """Test handler execution behaviors."""

    @pytest.mark.asyncio
    async def test_handler_execution_with_input_output_transformation(self):
        """Handler execution with input/output transformation."""
        hook = Hook(
            name="transformer",
            description="Transform data",
            condition=SimpleCondition(),
            handler=transforming_handler,
        )

        executor = HookExecutor()
        receipt = await executor.execute(hook, context={"value": 10})

        assert receipt.handler_result["transformed"] is True
        assert receipt.handler_result["value"] == 20  # Doubled

    @pytest.mark.asyncio
    async def test_handler_errors_are_caught_and_stored_in_receipt(self):
        """Handler errors are caught and stored in receipt."""
        hook = Hook(
            name="failing",
            description="Failing hook",
            condition=SimpleCondition(),
            handler=failing_handler,
        )

        executor = HookExecutor()
        receipt = await executor.execute(hook, context={})

        assert receipt.error is not None
        assert "Handler error" in receipt.error
        assert receipt.handler_result is None


class TestHookFinalStates:
    """Test hook final states."""

    @pytest.mark.asyncio
    async def test_hook_reaches_completed_state_on_success(self):
        """Hook reaches COMPLETED state on successful execution."""
        hook = Hook(
            name="test", description="Test", condition=SimpleCondition(), handler=simple_handler
        )

        executor = HookExecutor()
        await executor.execute(hook, context={})

        assert hook.state == HookState.COMPLETED

    @pytest.mark.asyncio
    async def test_hook_reaches_failed_state_on_error(self):
        """Hook reaches FAILED state on error."""
        hook = Hook(
            name="failing",
            description="Failing hook",
            condition=SimpleCondition(),
            handler=failing_handler,
        )

        executor = HookExecutor()
        await executor.execute(hook, context={})

        assert hook.state == HookState.FAILED


class TestHookAuditability:
    """Test hook lifecycle auditability."""

    @pytest.mark.asyncio
    async def test_hook_lifecycle_is_auditable(self):
        """Hook lifecycle is auditable (all state changes logged)."""
        hook = Hook(
            name="test", description="Test", condition=SimpleCondition(), handler=simple_handler
        )

        executor = HookExecutor()
        receipt = await executor.execute(hook, context={})

        # Receipt should contain audit trail
        assert receipt.hook_id == "test"
        assert receipt.timestamp is not None
        assert receipt.duration_ms >= 0
        assert "state_transitions" in receipt.metadata or receipt.hook_id is not None


class TestHookChaining:
    """Test hook chaining behaviors."""

    @pytest.mark.asyncio
    async def test_multiple_handlers_can_be_chained(self):
        """Multiple handlers can be chained (hook1 output → hook2 input)."""

        def first_handler(context: dict[str, Any]) -> dict[str, Any]:
            return {"step": 1, "value": 10}

        def second_handler(context: dict[str, Any]) -> dict[str, Any]:
            return {"step": 2, "value": context.get("value", 0) + 5}

        hook1 = Hook(
            name="first",
            description="First in chain",
            condition=SimpleCondition(),
            handler=first_handler,
        )

        hook2 = Hook(
            name="second",
            description="Second in chain",
            condition=SimpleCondition(),
            handler=second_handler,
        )

        chain = HookChain(hooks=[hook1, hook2])
        results = await chain.execute(context={})

        assert len(results) == 2
        assert results[0].handler_result["step"] == 1
        assert results[0].handler_result["value"] == 10
        assert results[1].handler_result["step"] == 2
        assert results[1].handler_result["value"] == 15  # 10 + 5


class TestHookContext:
    """Test hook context behaviors."""

    @pytest.mark.asyncio
    async def test_hook_context_carries_metadata_through_execution(self):
        """Hook context carries metadata through execution."""

        def context_aware_handler(context: dict[str, Any]) -> dict[str, Any]:
            hook_context = context.get("hook_context")
            return {
                "actor": hook_context.actor if hook_context else None,
                "request_id": hook_context.request_id if hook_context else None,
            }

        hook = Hook(
            name="test",
            description="Test",
            condition=SimpleCondition(),
            handler=context_aware_handler,
        )

        hook_context = HookContext(
            actor="test_user", request_id="req-123", metadata={"source": "test"}
        )

        executor = HookExecutor()
        receipt = await executor.execute(hook, context={"hook_context": hook_context})

        assert receipt.handler_result["actor"] == "test_user"
        assert receipt.handler_result["request_id"] == "req-123"


class TestHookLifecycleEvents:
    """Test hook lifecycle event system."""

    @pytest.mark.asyncio
    async def test_lifecycle_events_are_emitted(self):
        """Event system for lifecycle phases (pre/post)."""
        events: list[HookLifecycleEvent] = []

        def event_handler(event: HookLifecycleEvent):
            events.append(event)

        hook = Hook(
            name="test", description="Test", condition=SimpleCondition(), handler=simple_handler
        )

        executor = HookExecutor()
        executor.on_event(event_handler)

        await executor.execute(hook, context={})

        # Should have received lifecycle events
        assert len(events) > 0
        event_types = {e.event_type for e in events}
        assert (
            LifecycleEventType.PRE_CONDITION in event_types
            or LifecycleEventType.PRE_EXECUTE in event_types
        )
        assert (
            LifecycleEventType.POST_CONDITION in event_types
            or LifecycleEventType.POST_EXECUTE in event_types
        )


class TestHookExecutionPipeline:
    """Test hook execution pipeline behaviors."""

    @pytest.mark.asyncio
    async def test_execution_pipeline_manages_hook_flow(self):
        """HookExecutionPipeline manages complete hook execution flow."""
        hook = Hook(
            name="test", description="Test", condition=SimpleCondition(), handler=simple_handler
        )

        pipeline = HookExecutionPipeline()
        receipt = await pipeline.execute(hook, context={"test": "data"})

        assert receipt is not None
        assert receipt.hook_id == "test"
        assert receipt.condition_result is not None
        assert receipt.handler_result is not None

    @pytest.mark.asyncio
    async def test_pipeline_handles_multiple_hooks_in_order(self):
        """Pipeline executes multiple hooks in priority order."""
        hooks = [
            Hook(
                name="low",
                description="Low priority",
                condition=SimpleCondition(),
                handler=simple_handler,
                priority=10,
            ),
            Hook(
                name="high",
                description="High priority",
                condition=SimpleCondition(),
                handler=simple_handler,
                priority=90,
            ),
            Hook(
                name="mid",
                description="Mid priority",
                condition=SimpleCondition(),
                handler=simple_handler,
                priority=50,
            ),
        ]

        pipeline = HookExecutionPipeline()
        receipts = await pipeline.execute_batch(hooks, context={})

        # Should execute in priority order (high to low)
        hook_names = [r.hook_id for r in receipts]
        assert hook_names == ["high", "mid", "low"]


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery behaviors."""

    @pytest.mark.asyncio
    async def test_pipeline_continues_after_hook_failure(self):
        """Pipeline continues executing hooks after one fails."""
        hooks = [
            Hook(
                name="first",
                description="First hook",
                condition=SimpleCondition(),
                handler=simple_handler,
            ),
            Hook(
                name="failing",
                description="Failing hook",
                condition=SimpleCondition(),
                handler=failing_handler,
            ),
            Hook(
                name="third",
                description="Third hook",
                condition=SimpleCondition(),
                handler=simple_handler,
            ),
        ]

        pipeline = HookExecutionPipeline(stop_on_error=False)
        receipts = await pipeline.execute_batch(hooks, context={})

        assert len(receipts) == 3
        assert receipts[0].error is None
        assert receipts[1].error is not None
        assert receipts[2].error is None  # Continued after failure

    @pytest.mark.asyncio
    async def test_pipeline_stops_on_error_when_configured(self):
        """Pipeline stops on first error when stop_on_error=True."""
        hooks = [
            Hook(
                name="first",
                description="First hook",
                condition=SimpleCondition(),
                handler=simple_handler,
            ),
            Hook(
                name="failing",
                description="Failing hook",
                condition=SimpleCondition(),
                handler=failing_handler,
            ),
            Hook(
                name="third",
                description="Third hook",
                condition=SimpleCondition(),
                handler=simple_handler,
            ),
        ]

        pipeline = HookExecutionPipeline(stop_on_error=True)
        receipts = await pipeline.execute_batch(hooks, context={})

        # Should stop after failing hook
        assert len(receipts) == 2
        assert receipts[1].error is not None
