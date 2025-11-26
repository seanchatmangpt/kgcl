"""
Chicago School TDD Tests for Hook Core Domain Model.

These tests define the BEHAVIOR of the hooks system and drive the implementation.
No mocking of core domain objects - real object collaboration testing.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest

from kgcl.hooks.conditions import Condition, ConditionResult
from kgcl.hooks.core import (
    Hook,
    HookExecutor,
    HookReceipt,
    HookRegistry,
    HookState,
    HookValidationError,
)


class AlwaysTrueCondition(Condition):
    """Test condition that always evaluates to true."""

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        return ConditionResult(triggered=True, metadata={"test": "always_true"})


class AlwaysFalseCondition(Condition):
    """Test condition that always evaluates to false."""

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        return ConditionResult(triggered=False, metadata={"test": "always_false"})


class SlowCondition(Condition):
    """Test condition that takes time to evaluate."""

    def __init__(self, delay: float):
        super().__init__()
        self.delay = delay

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        await asyncio.sleep(self.delay)
        return ConditionResult(triggered=True, metadata={"delay": self.delay})


def simple_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Simple test handler that returns context."""
    return {"processed": True, "input": context}


def failing_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Handler that always raises an error."""
    raise ValueError("Handler failed intentionally")


class TestHookCreation:
    """Test hook creation and validation behaviors."""

    def test_hook_can_be_defined_with_name_description_condition_and_handler(self):
        """Hook can be defined with name, description, condition, and handler."""
        hook = Hook(
            name="test_hook",
            description="A test hook",
            condition=AlwaysTrueCondition(),
            handler=simple_handler,
        )

        assert hook.name == "test_hook"
        assert hook.description == "A test hook"
        assert isinstance(hook.condition, AlwaysTrueCondition)
        assert hook.handler == simple_handler

    def test_hook_validates_structure_on_creation(self):
        """Hook validates structure on creation (must have name, condition, handler)."""
        # Missing name
        with pytest.raises(HookValidationError, match="name"):
            Hook(
                name="",
                description="Test",
                condition=AlwaysTrueCondition(),
                handler=simple_handler,
            )

        # Missing condition
        with pytest.raises(HookValidationError, match="condition"):
            Hook(
                name="test", description="Test", condition=None, handler=simple_handler
            )

        # Missing handler
        with pytest.raises(HookValidationError, match="handler"):
            Hook(
                name="test",
                description="Test",
                condition=AlwaysTrueCondition(),
                handler=None,
            )


class TestHookLifecycle:
    """Test hook lifecycle state transitions."""

    def test_hook_starts_in_pending_state(self):
        """Hook lifecycle: starts in PENDING state."""
        hook = Hook(
            name="test_hook",
            description="Test",
            condition=AlwaysTrueCondition(),
            handler=simple_handler,
        )

        assert hook.state == HookState.PENDING

    def test_hook_has_all_lifecycle_states(self):
        """Hook lifecycle: PENDING → ACTIVE → EXECUTED → COMPLETED (or FAILED)."""
        # Verify all states exist
        assert HookState.PENDING
        assert HookState.ACTIVE
        assert HookState.EXECUTED
        assert HookState.COMPLETED
        assert HookState.FAILED


class TestHookMetadata:
    """Test hook metadata tracking behaviors."""

    def test_hook_tracks_created_at_timestamp(self):
        """Hook tracks metadata: created_at timestamp."""
        before = datetime.now(UTC)
        hook = Hook(
            name="test_hook",
            description="Test",
            condition=AlwaysTrueCondition(),
            handler=simple_handler,
        )
        after = datetime.now(UTC)

        assert before <= hook.created_at <= after

    def test_hook_tracks_executed_at_after_execution(self):
        """Hook tracks metadata: executed_at after execution."""
        hook = Hook(
            name="test_hook",
            description="Test",
            condition=AlwaysTrueCondition(),
            handler=simple_handler,
        )

        assert hook.executed_at is None
        # Execution will be tested in lifecycle tests

    def test_hook_tracks_actor(self):
        """Hook tracks metadata: actor who created/executed it."""
        hook = Hook(
            name="test_hook",
            description="Test",
            condition=AlwaysTrueCondition(),
            handler=simple_handler,
            actor="test_user",
        )

        assert hook.actor == "test_user"


class TestHookPriority:
    """Test hook priority behaviors."""

    def test_hook_has_priority_affecting_execution_order(self):
        """Hook has priority (0-100) affecting execution order."""
        high_priority = Hook(
            name="high",
            description="High priority",
            condition=AlwaysTrueCondition(),
            handler=simple_handler,
            priority=90,
        )

        low_priority = Hook(
            name="low",
            description="Low priority",
            condition=AlwaysTrueCondition(),
            handler=simple_handler,
            priority=10,
        )

        assert high_priority.priority == 90
        assert low_priority.priority == 10
        assert high_priority.priority > low_priority.priority

    def test_hook_priority_defaults_to_50(self):
        """Hook priority defaults to 50 if not specified."""
        hook = Hook(
            name="test",
            description="Test",
            condition=AlwaysTrueCondition(),
            handler=simple_handler,
        )

        assert hook.priority == 50

    def test_hook_priority_validates_range(self):
        """Hook priority must be in range 0-100."""
        with pytest.raises(HookValidationError, match="priority"):
            Hook(
                name="test",
                description="Test",
                condition=AlwaysTrueCondition(),
                handler=simple_handler,
                priority=-1,
            )

        with pytest.raises(HookValidationError, match="priority"):
            Hook(
                name="test",
                description="Test",
                condition=AlwaysTrueCondition(),
                handler=simple_handler,
                priority=101,
            )


class TestHookEnableDisable:
    """Test hook enable/disable behaviors."""

    def test_hook_can_be_disabled_without_deletion(self):
        """Hook can be enabled/disabled without deletion."""
        hook = Hook(
            name="test",
            description="Test",
            condition=AlwaysTrueCondition(),
            handler=simple_handler,
        )

        assert hook.enabled is True  # Default enabled

        hook.disable()
        assert hook.enabled is False

        hook.enable()
        assert hook.enabled is True


class TestHookRegistry:
    """Test hook registry behaviors."""

    def test_hook_registry_manages_multiple_hooks(self):
        """Hook registry manages multiple hooks."""
        registry = HookRegistry()

        hook1 = Hook("hook1", "Test 1", AlwaysTrueCondition(), simple_handler)
        hook2 = Hook("hook2", "Test 2", AlwaysTrueCondition(), simple_handler)

        registry.register(hook1)
        registry.register(hook2)

        assert len(registry.get_all()) == 2
        assert registry.get("hook1") == hook1
        assert registry.get("hook2") == hook2

    def test_hook_registry_prevents_name_duplication(self):
        """Hook registry manages hooks with name deduplication."""
        registry = HookRegistry()

        hook1 = Hook("duplicate", "Test 1", AlwaysTrueCondition(), simple_handler)
        hook2 = Hook("duplicate", "Test 2", AlwaysTrueCondition(), simple_handler)

        registry.register(hook1)

        with pytest.raises(HookValidationError, match="already exists"):
            registry.register(hook2)

    def test_hook_registry_can_unregister_hooks(self):
        """Hook registry can unregister hooks."""
        registry = HookRegistry()
        hook = Hook("test", "Test", AlwaysTrueCondition(), simple_handler)

        registry.register(hook)
        assert registry.get("test") == hook

        registry.unregister("test")
        assert registry.get("test") is None

    def test_hook_registry_returns_hooks_sorted_by_priority(self):
        """Hook registry returns hooks sorted by priority."""
        registry = HookRegistry()

        registry.register(
            Hook("low", "Low", AlwaysTrueCondition(), simple_handler, priority=10)
        )
        registry.register(
            Hook("high", "High", AlwaysTrueCondition(), simple_handler, priority=90)
        )
        registry.register(
            Hook("mid", "Mid", AlwaysTrueCondition(), simple_handler, priority=50)
        )

        hooks = registry.get_all_sorted()
        priorities = [h.priority for h in hooks]

        assert priorities == [90, 50, 10]  # High to low


class TestHookExecution:
    """Test hook execution behaviors."""

    @pytest.mark.asyncio
    async def test_hook_execution_produces_receipt(self):
        """Hook execution produces receipt with timestamp, result, error."""
        hook = Hook(
            name="test",
            description="Test",
            condition=AlwaysTrueCondition(),
            handler=simple_handler,
        )

        executor = HookExecutor()
        receipt = await executor.execute(hook, context={})

        assert isinstance(receipt, HookReceipt)
        assert receipt.hook_id == "test"
        assert receipt.timestamp is not None
        assert receipt.condition_result is not None
        assert receipt.handler_result is not None
        assert receipt.error is None

    @pytest.mark.asyncio
    async def test_hook_execution_captures_errors(self):
        """Hook execution receipt includes error information."""
        hook = Hook(
            name="failing",
            description="Failing hook",
            condition=AlwaysTrueCondition(),
            handler=failing_handler,
        )

        executor = HookExecutor()
        receipt = await executor.execute(hook, context={})

        assert receipt.error is not None
        assert "Handler failed intentionally" in receipt.error
        assert receipt.handler_result is None


class TestHookReceipt:
    """Test hook receipt behaviors."""

    def test_receipts_are_immutable_after_creation(self):
        """Receipts are immutable after creation."""
        receipt = HookReceipt(
            hook_id="test",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"success": True},
            duration_ms=100.0,
        )

        # Should not be able to modify
        with pytest.raises(AttributeError):
            receipt.hook_id = "modified"


class TestHookTimeout:
    """Test hook timeout behaviors."""

    @pytest.mark.asyncio
    async def test_hook_timeout_prevents_runaway_execution(self):
        """Hook timeout prevents runaway execution."""
        slow_hook = Hook(
            name="slow",
            description="Slow hook",
            condition=SlowCondition(delay=2.0),
            handler=simple_handler,
            timeout=0.5,  # 500ms timeout
        )

        executor = HookExecutor()
        receipt = await executor.execute(slow_hook, context={})

        # Should timeout and have error
        assert receipt.error is not None
        assert "timeout" in receipt.error.lower() or "exceeded" in receipt.error.lower()
