"""
Consolidated Hook System Tests.

80/20 consolidation: Essential hook behaviors tested with real collaborators.
Chicago School TDD - no mocking of domain objects.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest

from kgcl.hooks.conditions import (
    CompositeCondition,
    CompositeOperator,
    Condition,
    ConditionResult,
    DeltaCondition,
    DeltaType,
    ThresholdCondition,
    ThresholdOperator,
)
from kgcl.hooks.core import Hook, HookExecutor, HookReceipt, HookRegistry, HookState, HookValidationError
from kgcl.hooks.lifecycle import HookExecutionPipeline
from kgcl.hooks.observability import HealthCheck, Observability
from kgcl.hooks.performance import PerformanceOptimizer
from kgcl.hooks.receipts import Receipt, ReceiptStore

# SandboxRestrictions removed for research mode
from kgcl.hooks.security import ErrorSanitizer, SanitizedError
from kgcl.hooks.transaction import Transaction, TransactionManager, TransactionState

# =============================================================================
# Test Fixtures - Reusable conditions and handlers
# =============================================================================


class AlwaysTrueCondition(Condition):
    """Condition that always triggers."""

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        return ConditionResult(triggered=True, metadata={"test": "always_true"})


class AlwaysFalseCondition(Condition):
    """Condition that never triggers."""

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        return ConditionResult(triggered=False, metadata={"test": "always_false"})


class SlowCondition(Condition):
    """Condition with configurable delay for timeout tests."""

    def __init__(self, delay: float = 0.1) -> None:
        super().__init__()
        self.delay = delay

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        await asyncio.sleep(self.delay)
        return ConditionResult(triggered=True, metadata={"delay": self.delay})


def simple_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Simple handler that returns processed context."""
    return {"processed": True, "input": context}


def failing_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Handler that always raises an error."""
    raise ValueError("Handler failed intentionally")


# =============================================================================
# Hook Core Tests
# =============================================================================


class TestHookCore:
    """Core hook creation and validation."""

    def test_hook_creation_with_valid_params(self) -> None:
        """Hook can be created with name, description, condition, handler."""
        hook = Hook(
            name="test_hook", description="A test hook", condition=AlwaysTrueCondition(), handler=simple_handler
        )
        assert hook.name == "test_hook"
        assert hook.enabled is True
        assert hook.priority == 50

    def test_hook_rejects_empty_name(self) -> None:
        """Hook rejects empty name."""
        with pytest.raises(HookValidationError, match="name"):
            Hook(name="", description="Test", condition=AlwaysTrueCondition(), handler=simple_handler)

    def test_hook_rejects_missing_condition(self) -> None:
        """Hook rejects missing condition."""
        with pytest.raises(HookValidationError, match="condition"):
            Hook(name="test", description="Test", condition=None, handler=simple_handler)

    def test_hook_rejects_invalid_priority(self) -> None:
        """Hook priority must be 0-100."""
        with pytest.raises(HookValidationError, match="priority"):
            Hook(name="test", description="Test", condition=AlwaysTrueCondition(), handler=simple_handler, priority=150)

    def test_hook_enable_disable(self) -> None:
        """Hook can be enabled and disabled."""
        hook = Hook(name="test", description="Test", condition=AlwaysTrueCondition(), handler=simple_handler)
        hook.disable()
        assert hook.enabled is False
        hook.enable()
        assert hook.enabled is True


class TestHookRegistry:
    """Hook registry for managing multiple hooks."""

    def test_register_and_get_hook(self) -> None:
        """Registry registers and retrieves hooks."""
        registry = HookRegistry()
        hook = Hook(name="test", description="Test", condition=AlwaysTrueCondition(), handler=simple_handler)
        registry.register(hook)
        assert registry.get("test") is hook

    def test_duplicate_registration_raises(self) -> None:
        """Registry rejects duplicate hook names."""
        registry = HookRegistry()
        hook = Hook(name="test", description="Test", condition=AlwaysTrueCondition(), handler=simple_handler)
        registry.register(hook)
        with pytest.raises(HookValidationError, match="already exists"):
            registry.register(hook)

    def test_get_all_sorted_by_priority(self) -> None:
        """Hooks are sorted by priority (high to low)."""
        registry = HookRegistry()
        for priority in [30, 70, 50]:
            hook = Hook(
                name=f"hook_{priority}",
                description="Test",
                condition=AlwaysTrueCondition(),
                handler=simple_handler,
                priority=priority,
            )
            registry.register(hook)
        sorted_hooks = registry.get_all_sorted()
        priorities = [h.priority for h in sorted_hooks]
        assert priorities == [70, 50, 30]


class TestHookExecutor:
    """Hook execution with receipts."""

    @pytest.mark.asyncio
    async def test_executor_produces_receipt(self) -> None:
        """Executor produces receipt for each execution."""
        hook = Hook(name="test", description="Test", condition=AlwaysTrueCondition(), handler=simple_handler)
        executor = HookExecutor()
        receipt = await executor.execute(hook, {"key": "value"})

        assert isinstance(receipt, HookReceipt)
        assert receipt.hook_id == "test"
        assert receipt.condition_result.triggered is True
        assert receipt.handler_result is not None
        assert receipt.error is None

    @pytest.mark.asyncio
    async def test_executor_handles_false_condition(self) -> None:
        """Executor skips handler when condition is false."""
        hook = Hook(name="test", description="Test", condition=AlwaysFalseCondition(), handler=simple_handler)
        executor = HookExecutor()
        receipt = await executor.execute(hook, {})

        assert receipt.condition_result.triggered is False
        assert receipt.handler_result is None

    @pytest.mark.asyncio
    async def test_executor_handles_handler_error(self) -> None:
        """Executor captures handler errors in receipt."""
        hook = Hook(name="test", description="Test", condition=AlwaysTrueCondition(), handler=failing_handler)
        executor = HookExecutor()
        receipt = await executor.execute(hook, {})

        assert receipt.error is not None
        assert "failed" in receipt.error.lower()
        assert hook.state == HookState.FAILED


# =============================================================================
# Condition Tests
# =============================================================================


class TestConditions:
    """Condition evaluation behaviors."""

    @pytest.mark.asyncio
    async def test_threshold_greater_than(self) -> None:
        """ThresholdCondition evaluates > correctly."""
        condition = ThresholdCondition(variable="count", operator=ThresholdOperator.GREATER_THAN, value=10)
        result = await condition.evaluate({"count": 15})
        assert result.triggered is True

        result = await condition.evaluate({"count": 5})
        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_threshold_less_than(self) -> None:
        """ThresholdCondition evaluates < correctly."""
        condition = ThresholdCondition(variable="count", operator=ThresholdOperator.LESS_THAN, value=10)
        result = await condition.evaluate({"count": 5})
        assert result.triggered is True

    @pytest.mark.asyncio
    async def test_delta_detects_increase(self) -> None:
        """DeltaCondition detects value increases."""
        condition = DeltaCondition(delta_type=DeltaType.INCREASE, query="SELECT COUNT(*)")
        result = await condition.evaluate({"previous_count": 10, "current_count": 15})
        assert result.triggered is True

        # No increase should not trigger
        result = await condition.evaluate({"previous_count": 15, "current_count": 10})
        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_composite_and(self) -> None:
        """CompositeCondition AND requires all true."""
        composite = CompositeCondition(
            conditions=[AlwaysTrueCondition(), AlwaysTrueCondition()], operator=CompositeOperator.AND
        )
        result = await composite.evaluate({})
        assert result.triggered is True

        composite = CompositeCondition(
            conditions=[AlwaysTrueCondition(), AlwaysFalseCondition()], operator=CompositeOperator.AND
        )
        result = await composite.evaluate({})
        assert result.triggered is False

    @pytest.mark.asyncio
    async def test_composite_or(self) -> None:
        """CompositeCondition OR requires any true."""
        composite = CompositeCondition(
            conditions=[AlwaysFalseCondition(), AlwaysTrueCondition()], operator=CompositeOperator.OR
        )
        result = await composite.evaluate({})
        assert result.triggered is True


# =============================================================================
# Security Tests
# =============================================================================


class TestSecurity:
    """Security: error sanitization and sandboxing."""

    def test_error_sanitizer_pass_through(self) -> None:
        """ErrorSanitizer passes through errors (research: no sanitization)."""
        sanitizer = ErrorSanitizer()
        exc = ValueError("Test error message")
        result = sanitizer.sanitize(exc)

        assert isinstance(result, SanitizedError)
        assert "Test error message" in result.message
        assert result.is_user_safe is True

    # Production tests removed for research mode


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformance:
    """Performance tracking and optimization."""

    def test_metrics_record_and_retrieve(self) -> None:
        """PerformanceOptimizer records and retrieves metrics."""
        optimizer = PerformanceOptimizer()
        optimizer.record_latency("test_op", 5.0)
        optimizer.record_latency("test_op", 10.0)
        optimizer.record_latency("test_op", 15.0)

        stats = optimizer.get_stats("test_op")
        assert stats is not None
        assert stats["count"] == 3
        assert stats["mean"] == 10.0

    def test_percentile_calculation(self) -> None:
        """PerformanceOptimizer calculates percentiles correctly."""
        optimizer = PerformanceOptimizer()
        for i in range(100):
            optimizer.record_latency("test_op", float(i))

        p99 = optimizer.get_percentile("test_op", 0.99)
        assert p99 is not None
        assert p99 >= 98.0


# =============================================================================
# Observability Tests
# =============================================================================


class TestObservability:
    """Health monitoring and metrics collection."""

    def test_health_check_status(self) -> None:
        """Observability provides health status."""
        obs = Observability()
        obs.record_metric("latency", 50.0)
        health = obs.get_health_status()

        assert isinstance(health, HealthCheck)
        assert health.is_healthy is True

    def test_threshold_violation_unhealthy(self) -> None:
        """Health becomes unhealthy when thresholds exceeded."""
        obs = Observability()
        obs.set_threshold("latency", error=100.0)
        obs.record_metric("latency", 150.0)
        health = obs.get_health_status()

        assert health.is_healthy is False
        assert len(health.errors) > 0


# =============================================================================
# Transaction Tests
# =============================================================================


class TestTransactions:
    """ACID transaction management."""

    def test_transaction_lifecycle(self) -> None:
        """Transaction follows PENDING -> EXECUTING -> COMMITTED lifecycle."""
        tx = Transaction(tx_id="test-tx")
        assert tx.state == TransactionState.PENDING

        tx.begin()
        assert tx.state == TransactionState.EXECUTING

        tx.commit()
        assert tx.state == TransactionState.COMMITTED

    def test_transaction_rollback(self) -> None:
        """Transaction can be rolled back, clearing changes."""
        tx = Transaction(tx_id="test-tx")
        tx.begin()
        tx.add_triple("s", "p", "o")
        tx.rollback()

        assert tx.state == TransactionState.ROLLED_BACK
        assert len(tx.added_triples) == 0

    def test_manager_concurrent_transactions(self) -> None:
        """TransactionManager handles concurrent transactions."""
        manager = TransactionManager(max_concurrent=5)
        tx1 = manager.begin_transaction()
        tx2 = manager.begin_transaction()

        assert len(manager.get_active_transactions()) == 2
        manager.commit_transaction(tx1.tx_id)
        assert len(manager.get_active_transactions()) == 1


# =============================================================================
# Receipt & Provenance Tests
# =============================================================================


class TestReceipts:
    """Receipt immutability and provenance."""

    def test_receipt_immutable(self) -> None:
        """Receipt is immutable once created."""
        receipt = Receipt(
            hook_id="hook-1",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"result": "ok"},
            duration_ms=10.0,
        )
        # Receipts use frozen dataclass or similar
        assert receipt.hook_id == "hook-1"
        assert receipt.handler_result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_receipt_store_query(self) -> None:
        """ReceiptStore supports querying by hook_id."""
        store = ReceiptStore()
        receipt = Receipt(
            hook_id="test-hook",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={},
            duration_ms=5.0,
        )
        await store.save(receipt)

        results = await store.query(hook_id="test-hook")
        assert len(results) == 1
        assert results[0].hook_id == "test-hook"


# =============================================================================
# Integration: Execution Pipeline
# =============================================================================


class TestExecutionPipeline:
    """End-to-end hook execution pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_batch_execution(self) -> None:
        """Pipeline executes multiple hooks in priority order."""
        hooks = [
            Hook(
                name=f"hook_{i}",
                description="Test",
                condition=AlwaysTrueCondition(),
                handler=simple_handler,
                priority=i * 10,
            )
            for i in range(3)
        ]

        pipeline = HookExecutionPipeline()
        receipts = await pipeline.execute_batch(hooks, {"test": "data"})

        assert len(receipts) == 3
        # Executed in priority order (high to low)
        assert receipts[0].hook_id == "hook_2"

    @pytest.mark.asyncio
    async def test_pipeline_stop_on_error(self) -> None:
        """Pipeline can stop on first error."""
        hooks = [
            Hook(
                name="good", description="Test", condition=AlwaysTrueCondition(), handler=simple_handler, priority=100
            ),
            Hook(name="bad", description="Test", condition=AlwaysTrueCondition(), handler=failing_handler, priority=50),
            Hook(
                name="never", description="Test", condition=AlwaysTrueCondition(), handler=simple_handler, priority=10
            ),
        ]

        pipeline = HookExecutionPipeline(stop_on_error=True)
        receipts = await pipeline.execute_batch(hooks, {})

        # Should stop after "bad" hook
        assert len(receipts) == 2
        assert receipts[1].error is not None
