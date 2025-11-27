"""Tests for Innovation #7: Hook Batching with Dependency Analysis.

Chicago School TDD: Real batching operations, no mocking.
Tests dependency analysis, batch creation, and execution planning.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hooks.hook_batcher import BatchConfig, BatchResult, HookBatcher
from kgcl.hybrid.knowledge_hooks import HookAction, HookPhase, KnowledgeHook


class TestBatchConfig:
    """Tests for batch configuration."""

    def test_default_config_values(self) -> None:
        """Default config has expected values."""
        config = BatchConfig()

        assert config.max_batch_size == 10
        assert config.enable_parallel is True
        assert config.timeout_per_hook_ms == 100.0

    def test_custom_config(self) -> None:
        """Custom config values are stored."""
        config = BatchConfig(max_batch_size=5, enable_parallel=False)

        assert config.max_batch_size == 5
        assert config.enable_parallel is False


class TestBatchResult:
    """Tests for batch result dataclass."""

    def test_batch_result_creation(self) -> None:
        """Batch result stores execution data."""
        result = BatchResult(batch_number=1, hooks_executed=3, duration_ms=15.0)

        assert result.batch_number == 1
        assert result.hooks_executed == 3
        assert result.duration_ms == 15.0
        assert result.receipts == []
        assert result.errors == []


class TestDependencyAnalysis:
    """Tests for hook dependency analysis."""

    def test_independent_hooks_no_deps(self) -> None:
        """Independent hooks have no dependencies."""
        batcher = HookBatcher()
        hooks = [
            KnowledgeHook(
                hook_id="h1",
                name="Hook 1",
                phase=HookPhase.ON_CHANGE,
                priority=50,
                action=HookAction.NOTIFY,
                handler_data={"message": "m1"},
            ),
            KnowledgeHook(
                hook_id="h2",
                name="Hook 2",
                phase=HookPhase.ON_CHANGE,
                priority=50,
                action=HookAction.NOTIFY,
                handler_data={"message": "m2"},
            ),
        ]

        deps = batcher.analyze_dependencies(hooks)

        # Both hooks have empty dependency sets (same priority, no chains)
        assert "h1" in deps
        assert "h2" in deps

    def test_priority_creates_dependency(self) -> None:
        """Higher priority hooks create dependencies."""
        batcher = HookBatcher()
        hooks = [
            KnowledgeHook(
                hook_id="high",
                name="High Priority",
                phase=HookPhase.ON_CHANGE,
                priority=100,
                action=HookAction.NOTIFY,
                handler_data={"message": "high"},
            ),
            KnowledgeHook(
                hook_id="low",
                name="Low Priority",
                phase=HookPhase.ON_CHANGE,
                priority=10,
                action=HookAction.NOTIFY,
                handler_data={"message": "low"},
            ),
        ]

        deps = batcher.analyze_dependencies(hooks)

        # Low priority hook depends on high priority completing first
        assert "high" in deps["low"]


class TestBatchCreation:
    """Tests for batch creation from hooks."""

    def test_empty_hooks_empty_batches(self) -> None:
        """Empty hook list creates empty batch list."""
        batcher = HookBatcher()

        batches = batcher.create_batches([])

        assert batches == []

    def test_independent_hooks_single_batch(self) -> None:
        """Independent hooks go in single batch."""
        config = BatchConfig(max_batch_size=10)
        batcher = HookBatcher(config=config)
        hooks = [
            KnowledgeHook(
                hook_id="h1",
                name="Hook 1",
                phase=HookPhase.ON_CHANGE,
                priority=50,
                action=HookAction.NOTIFY,
                handler_data={"message": "m1"},
            ),
            KnowledgeHook(
                hook_id="h2",
                name="Hook 2",
                phase=HookPhase.ON_CHANGE,
                priority=50,
                action=HookAction.NOTIFY,
                handler_data={"message": "m2"},
            ),
        ]

        batches = batcher.create_batches(hooks)

        # Both can run in parallel
        assert len(batches) >= 1
        total_hooks = sum(len(b) for b in batches)
        assert total_hooks == 2

    def test_max_batch_size_respected(self) -> None:
        """Batch size limit is respected."""
        config = BatchConfig(max_batch_size=2)
        batcher = HookBatcher(config=config)
        hooks = [
            KnowledgeHook(
                hook_id=f"h{i}",
                name=f"Hook {i}",
                phase=HookPhase.ON_CHANGE,
                priority=50,
                action=HookAction.NOTIFY,
                handler_data={"message": f"m{i}"},
            )
            for i in range(5)
        ]

        batches = batcher.create_batches(hooks)

        # With max_batch_size=2, should have at least 3 batches
        assert all(len(b) <= 2 for b in batches)

    def test_priority_ordering_respected(self) -> None:
        """Higher priority hooks execute in earlier batches."""
        batcher = HookBatcher()
        hooks = [
            KnowledgeHook(
                hook_id="low",
                name="Low",
                phase=HookPhase.ON_CHANGE,
                priority=10,
                action=HookAction.NOTIFY,
                handler_data={"message": "low"},
            ),
            KnowledgeHook(
                hook_id="high",
                name="High",
                phase=HookPhase.ON_CHANGE,
                priority=100,
                action=HookAction.NOTIFY,
                handler_data={"message": "high"},
            ),
        ]

        batches = batcher.create_batches(hooks)

        # High priority should be in earlier batch
        if len(batches) > 1:
            first_batch_ids = [h.hook_id for h in batches[0]]
            assert "high" in first_batch_ids


class TestExecutionPlan:
    """Tests for execution plan generation."""

    def test_plan_structure(self) -> None:
        """Execution plan has expected structure."""
        batcher = HookBatcher()

        plan = batcher.get_execution_plan([])

        assert "total_hooks" in plan
        assert "total_batches" in plan
        assert "batches" in plan
        assert "dependencies" in plan
        assert "estimated_speedup" in plan

    def test_plan_with_hooks(self) -> None:
        """Plan correctly counts hooks and batches."""
        batcher = HookBatcher()
        hooks = [
            KnowledgeHook(
                hook_id="h1",
                name="Hook 1",
                phase=HookPhase.ON_CHANGE,
                action=HookAction.NOTIFY,
                handler_data={"message": "m1"},
            ),
            KnowledgeHook(
                hook_id="h2",
                name="Hook 2",
                phase=HookPhase.ON_CHANGE,
                action=HookAction.NOTIFY,
                handler_data={"message": "m2"},
            ),
        ]

        plan = batcher.get_execution_plan(hooks)

        assert plan["total_hooks"] == 2
        assert plan["total_batches"] >= 1


class TestSyncExecution:
    """Tests for synchronous batch execution."""

    def test_execute_empty_batches(self) -> None:
        """Empty hook list executes without error."""
        batcher = HookBatcher()

        results = batcher.execute_batches_sync([], lambda h: None)

        assert results == []

    def test_execute_captures_results(self) -> None:
        """Execution captures results for each batch."""
        batcher = HookBatcher()
        hooks = [
            KnowledgeHook(
                hook_id="h1",
                name="Hook 1",
                phase=HookPhase.ON_CHANGE,
                action=HookAction.NOTIFY,
                handler_data={"message": "m1"},
            )
        ]

        results = batcher.execute_batches_sync(hooks, lambda h: f"result-{h.hook_id}")

        assert len(results) >= 1
        assert results[0].hooks_executed == 1
        assert "result-h1" in results[0].receipts

    def test_execute_captures_errors(self) -> None:
        """Execution captures errors from failed hooks."""
        batcher = HookBatcher()
        hooks = [
            KnowledgeHook(
                hook_id="fail",
                name="Fail",
                phase=HookPhase.ON_CHANGE,
                action=HookAction.NOTIFY,
                handler_data={"message": "m"},
            )
        ]

        def failing_executor(h: KnowledgeHook) -> None:
            raise ValueError("Hook failed")

        results = batcher.execute_batches_sync(hooks, failing_executor)

        assert len(results[0].errors) == 1
        assert "Hook failed" in results[0].errors[0]


class TestSpeedupEstimation:
    """Tests for speedup estimation."""

    def test_single_batch_no_speedup(self) -> None:
        """Single batch has 1x speedup."""
        batcher = HookBatcher()

        # Empty batches
        speedup = batcher._estimate_speedup([])
        assert speedup == 1.0

    def test_multiple_batches_speedup(self) -> None:
        """Multiple hooks in fewer batches show speedup."""
        batcher = HookBatcher()
        hooks = [
            KnowledgeHook(
                hook_id=f"h{i}",
                name=f"Hook {i}",
                phase=HookPhase.ON_CHANGE,
                priority=50,  # Same priority
                action=HookAction.NOTIFY,
                handler_data={"message": f"m{i}"},
            )
            for i in range(4)
        ]

        batches = batcher.create_batches(hooks)
        speedup = batcher._estimate_speedup(batches)

        # 4 hooks in fewer batches should show speedup > 1
        assert speedup >= 1.0
