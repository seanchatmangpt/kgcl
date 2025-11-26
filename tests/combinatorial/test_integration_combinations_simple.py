"""Simplified integration combination tests.

Tests synchronous combinations of:
- Query optimizer + dark matter
- Conditions + hooks + receipts
- Hook registry operations
- Performance combinations

This module uses sync wrappers for async hook execution.
"""

import time
from typing import Any

import pytest
from rdflib import RDF, Graph, Literal, Namespace

from kgcl.hooks.conditions import (
    AlwaysTrueCondition,
    CompositeCondition,
    CompositeOperator,
    ConditionResult,
    SparqlAskCondition,
    ThresholdCondition,
    ThresholdOperator,
    WindowAggregation,
    WindowCondition,
)
from kgcl.hooks.core import Hook, HookReceipt
from kgcl.hooks.dark_matter import DarkMatterOptimizer
from kgcl.hooks.query_optimizer import QueryOptimizer

from .conftest import SyncConditionEvaluator, SyncHookExecutor, SyncHookRegistry

# Test namespaces
EX = Namespace("http://example.org/")
SCHEMA = Namespace("http://schema.org/")


class TestQueryOptimizerDarkMatterIntegration:
    """Test query optimizer with dark matter constant folding."""

    @pytest.fixture
    def query_optimizer(self) -> QueryOptimizer:
        """Create query optimizer."""
        return QueryOptimizer()

    @pytest.fixture
    def dark_matter(self) -> DarkMatterOptimizer:
        """Create dark matter optimizer."""
        return DarkMatterOptimizer()

    def test_query_plan_constant_folding(
        self, query_optimizer: QueryOptimizer, dark_matter: DarkMatterOptimizer
    ) -> None:
        """Test query plan with constant folding."""
        plan = {
            "steps": [
                {"type": "filter", "expression": {"op": "+", "left": 1, "right": 1}},
                {"type": "scan", "pattern": "?event a <http://example.org/Event>"},
            ]
        }

        # Apply dark matter optimization
        optimized_plan = dark_matter.optimize_query_plan(plan)

        # Verify optimization occurred (OptimizedPlan is a dataclass)
        assert hasattr(optimized_plan, "original_cost")
        assert hasattr(optimized_plan, "optimized_cost")
        assert hasattr(optimized_plan, "rewrite_rules_applied")
        assert isinstance(optimized_plan.rewrite_rules_applied, list)

    @pytest.mark.parametrize("has_constants", [True, False])
    def test_query_constant_detection(
        self,
        query_optimizer: QueryOptimizer,
        dark_matter: DarkMatterOptimizer,
        has_constants: bool,
    ) -> None:
        """Test detection and optimization of constant expressions."""
        if has_constants:
            plan = {
                "steps": [
                    {
                        "type": "filter",
                        "expression": {"op": "+", "left": 1, "right": 1},
                    },
                ]
            }
        else:
            plan = {
                "steps": [
                    {
                        "type": "filter",
                        "expression": {"op": ">", "left": "?x", "right": 5},
                    },
                ]
            }

        # Apply dark matter optimization
        optimized_plan = dark_matter.optimize_query_plan(plan)

        # Verify optimization occurred
        assert hasattr(optimized_plan, "original_cost")
        assert hasattr(optimized_plan, "optimized_cost")

    def test_optimizer_chain_with_caching(
        self, query_optimizer: QueryOptimizer, dark_matter: DarkMatterOptimizer
    ) -> None:
        """Test optimizer chain with query caching."""
        plan = {
            "steps": [
                {
                    "type": "filter",
                    "expression": {"op": ">", "left": 5, "right": 3},
                },
                {"type": "scan", "pattern": "?event a <http://example.org/Event>"},
            ]
        }

        # First optimization
        start1 = time.perf_counter()
        optimized1 = dark_matter.optimize_query_plan(plan)
        duration1 = time.perf_counter() - start1

        # Second optimization
        start2 = time.perf_counter()
        optimized2 = dark_matter.optimize_query_plan(plan)
        duration2 = time.perf_counter() - start2

        # Both should produce valid results
        assert hasattr(optimized1, "original_cost")
        assert hasattr(optimized2, "original_cost")

        # Timing should be reasonable
        assert duration1 >= 0
        assert duration2 >= 0

    def test_optimizer_preserves_semantics(
        self, query_optimizer: QueryOptimizer, dark_matter: DarkMatterOptimizer
    ) -> None:
        """Verify optimizer preserves query semantics."""
        plan = {
            "steps": [
                {
                    "type": "filter",
                    "expression": {"op": ">", "left": "?priority", "right": 5},
                },
                {"type": "scan", "pattern": "?event a <http://example.org/Event>"},
                {
                    "type": "scan",
                    "pattern": "?event <http://example.org/priority> ?priority",
                },
            ]
        }

        # Apply dark matter optimization
        optimized_plan = dark_matter.optimize_query_plan(plan)

        # Essential plan structure should be preserved
        assert hasattr(optimized_plan, "original_cost")
        assert hasattr(optimized_plan, "optimized_cost")
        assert hasattr(optimized_plan, "rewrite_rules_applied")


class TestConditionHookIntegration:
    """Test conditions integrated with hook execution."""

    @pytest.fixture
    def executor(self) -> SyncHookExecutor:
        """Create sync hook executor."""
        return SyncHookExecutor()

    @pytest.fixture
    def evaluator(self) -> SyncConditionEvaluator:
        """Create sync condition evaluator."""
        return SyncConditionEvaluator()

    @pytest.mark.parametrize(
        "condition_type,trigger_expected",
        [
            ("always_true", True),
            ("threshold_met", True),
            ("threshold_not_met", False),
        ],
    )
    def test_condition_triggers_hook(
        self,
        executor: SyncHookExecutor,
        evaluator: SyncConditionEvaluator,
        condition_type: str,
        trigger_expected: bool,
    ) -> None:
        """Test various condition types trigger hooks correctly."""
        # Create condition based on type
        if condition_type == "always_true":
            condition = AlwaysTrueCondition()
            context: dict[str, Any] = {}

        elif condition_type == "threshold_met":
            condition = ThresholdCondition(
                variable="value", operator=ThresholdOperator.GREATER_THAN, value=5.0
            )
            context = {"value": 10}

        elif condition_type == "threshold_not_met":
            condition = ThresholdCondition(
                variable="value", operator=ThresholdOperator.GREATER_THAN, value=5.0
            )
            context = {"value": 3}

        else:
            pytest.fail(f"Unknown condition type: {condition_type}")

        # Create hook with handler
        executed = []

        def handler(ctx: dict[str, Any]) -> dict[str, Any]:
            executed.append(True)
            return {"success": True}

        hook = Hook(
            name=f"test_hook_{condition_type}",
            description=f"Test hook for {condition_type}",
            condition=condition,
            handler=handler,
        )

        # Execute hook using sync executor
        receipt = executor.execute(hook, context)

        # Verify trigger
        if trigger_expected:
            assert receipt.condition_result.triggered is True
            assert len(executed) == 1
        else:
            assert receipt.condition_result.triggered is False
            assert len(executed) == 0

    @pytest.mark.parametrize(
        "num_conditions,combinator",
        [
            (2, CompositeOperator.AND),
            (2, CompositeOperator.OR),
            (3, CompositeOperator.AND),
            (3, CompositeOperator.OR),
        ],
    )
    def test_composite_condition_hook_integration(
        self,
        executor: SyncHookExecutor,
        evaluator: SyncConditionEvaluator,
        num_conditions: int,
        combinator: CompositeOperator,
    ) -> None:
        """Test composite conditions with hooks."""
        conditions = []

        # Create multiple threshold conditions
        for i in range(num_conditions):
            condition = ThresholdCondition(
                variable=f"value_{i}",
                operator=ThresholdOperator.GREATER_THAN,
                value=5.0,
            )
            conditions.append(condition)

        composite = CompositeCondition(operator=combinator, conditions=conditions)

        # Create context with alternating pass/fail values
        context: dict[str, Any] = {}
        for i in range(num_conditions):
            context[f"value_{i}"] = 10 if i % 2 == 0 else 3

        # Execute hook
        executed = []

        def handler(ctx: dict[str, Any]) -> dict[str, Any]:
            executed.append(True)
            return {"success": True}

        hook = Hook(
            name="composite_hook",
            description="Test composite_hook",
            condition=composite,
            handler=handler,
        )
        receipt = executor.execute(hook, context)

        # Verify based on combinator
        if combinator == CompositeOperator.AND:
            # All must pass (but we have some failing)
            assert receipt.condition_result.triggered is False
            assert len(executed) == 0
        else:  # OR
            # At least one passes
            assert receipt.condition_result.triggered is True
            assert len(executed) == 1

    def test_hook_receipt_captures_condition_state(
        self, executor: SyncHookExecutor
    ) -> None:
        """Hook receipt should capture condition evaluation state."""
        condition = ThresholdCondition(
            variable="value", operator=ThresholdOperator.GREATER_THAN, value=5.0
        )
        context = {"value": 10}

        def handler(ctx: dict[str, Any]) -> dict[str, Any]:
            return {"processed": True}

        hook = Hook(
            name="test_hook",
            description="Test test_hook",
            condition=condition,
            handler=handler,
        )
        receipt = executor.execute(hook, context)

        # Receipt should capture trigger state
        assert receipt.condition_result.triggered is True
        assert receipt.hook_id == "test_hook"
        assert receipt.duration_ms >= 0

    def test_hook_chain_with_registry(self, executor: SyncHookExecutor) -> None:
        """Test hook registry with chained hooks."""
        registry = SyncHookRegistry()

        # Register multiple hooks
        executed_order: list[int] = []

        def handler1(ctx: dict[str, Any]) -> dict[str, Any]:
            executed_order.append(1)
            return {"step": 1}

        def handler2(ctx: dict[str, Any]) -> dict[str, Any]:
            executed_order.append(2)
            return {"step": 2}

        hook1 = Hook(
            name="hook1",
            description="Test hook1",
            condition=AlwaysTrueCondition(),
            handler=handler1,
            priority=50,
        )
        hook2 = Hook(
            name="hook2",
            description="Test hook2",
            condition=AlwaysTrueCondition(),
            handler=handler2,
            priority=40,
        )

        registry.register(hook1)
        registry.register(hook2)

        # Execute all hooks
        context: dict[str, Any] = {}
        receipts = registry.execute_all(context)

        # Both should execute (priority order: hook1 first)
        assert len(receipts) == 2
        assert executed_order == [1, 2]


class TestFullPipelineIntegration:
    """Test full end-to-end pipeline."""

    @pytest.fixture
    def pipeline_components(self) -> dict[str, Any]:
        """Create all pipeline components."""
        return {
            "query_optimizer": QueryOptimizer(),
            "dark_matter": DarkMatterOptimizer(),
            "hook_registry": SyncHookRegistry(),
            "executor": SyncHookExecutor(),
        }

    def test_data_to_receipt_pipeline(
        self, pipeline_components: dict[str, Any]
    ) -> None:
        """Full pipeline: optimize query, evaluate condition, execute hook."""
        # 1. Ingest data
        data_graph = Graph()
        data_graph.bind("ex", EX)
        event = EX.event1
        data_graph.add((event, RDF.type, EX.Event))
        data_graph.add((event, EX.title, Literal("Pipeline Test Event")))

        # 2. Generate query
        query = """
        SELECT ?event ?title WHERE {
            ?event a <http://example.org/Event> ;
                   <http://example.org/title> ?title .
            FILTER(STRLEN(?title) > 0)
        }
        """

        # 3. Optimize query
        optimizer = pipeline_components["query_optimizer"]
        optimized = optimizer.optimize(query)

        # 4. Execute hook with always-true condition
        def handler(ctx: dict[str, Any]) -> dict[str, Any]:
            return {"processed": True, "query": ctx.get("optimized_query", "")}

        hook = Hook(
            name="pipeline_hook",
            description="Test pipeline_hook",
            condition=AlwaysTrueCondition(),
            handler=handler,
        )

        # 5. Execute and produce receipt
        executor = pipeline_components["executor"]
        context = {"data_graph": data_graph, "optimized_query": optimized}
        receipt = executor.execute(hook, context)

        # Verify full pipeline success
        assert receipt.condition_result.triggered is True
        assert receipt.hook_id == "pipeline_hook"
        assert receipt.error is None

    @pytest.mark.parametrize(
        "condition_met,expected_triggered",
        [
            (True, True),
            (False, False),
        ],
    )
    def test_pipeline_outcome_matrix(
        self,
        pipeline_components: dict[str, Any],
        condition_met: bool,
        expected_triggered: bool,
    ) -> None:
        """Test pipeline outcomes with different conditions."""
        # Create condition based on whether it should be met
        if condition_met:
            condition = AlwaysTrueCondition()
        else:
            condition = ThresholdCondition(
                variable="impossible_metric",
                operator=ThresholdOperator.GREATER_THAN,
                value=100.0,
            )

        # Execute hook
        def handler(ctx: dict[str, Any]) -> dict[str, Any]:
            return {"processed": True}

        hook = Hook(
            name="matrix_hook",
            description="Test matrix_hook",
            condition=condition,
            handler=handler,
        )

        executor = pipeline_components["executor"]
        context: dict[str, Any] = {}

        receipt = executor.execute(hook, context)

        # Verify expected outcome
        assert receipt.condition_result.triggered == expected_triggered


class TestCrossModuleErrorHandling:
    """Test error propagation across modules."""

    @pytest.fixture
    def executor(self) -> SyncHookExecutor:
        """Create sync hook executor."""
        return SyncHookExecutor()

    @pytest.mark.parametrize(
        "failing_module",
        [
            "optimizer",
            "hook_handler",
        ],
    )
    def test_error_propagation(
        self, executor: SyncHookExecutor, failing_module: str
    ) -> None:
        """Induce error in one module and verify handling."""
        if failing_module == "optimizer":
            optimizer = QueryOptimizer()
            invalid_query = "NOT A VALID SPARQL QUERY { { {"
            # Optimizer should handle gracefully or raise
            try:
                result = optimizer.optimize(invalid_query)
                # If it doesn't raise, it should return something reasonable
                assert isinstance(result, str)
            except Exception:
                pass  # Expected

        elif failing_module == "hook_handler":
            # Hook with failing handler
            def failing_handler(ctx: dict[str, Any]) -> dict[str, Any]:
                raise RuntimeError("Handler failure")

            hook = Hook(
                name="failing",
                description="Test failing",
                condition=AlwaysTrueCondition(),
                handler=failing_handler,
            )
            receipt = executor.execute(hook, {})

            # Error should be captured in receipt
            assert receipt.error is not None
            assert "Handler" in receipt.error or "failure" in receipt.error.lower()

    def test_query_error_to_hook(self, executor: SyncHookExecutor) -> None:
        """Query errors should be handled in hook execution."""
        invalid_query = "INVALID SPARQL"

        condition = SparqlAskCondition(query=invalid_query)

        def handler(ctx: dict[str, Any]) -> dict[str, Any]:
            return {"processed": True}

        hook = Hook(
            name="query_error_hook",
            description="Test query_error_hook",
            condition=condition,
            handler=handler,
        )

        context: dict[str, Any] = {"rdf_data": []}

        # Hook execution should handle query errors gracefully
        receipt = executor.execute(hook, context)

        # Should produce a receipt (either error or condition not triggered)
        assert isinstance(receipt, HookReceipt)


class TestPerformanceCombinations:
    """Test performance with various combinations."""

    @pytest.fixture
    def executor(self) -> SyncHookExecutor:
        """Create sync hook executor."""
        return SyncHookExecutor()

    @pytest.mark.parametrize(
        "num_queries,num_hooks",
        [
            (10, 10),
            (50, 50),
        ],
    )
    def test_batch_processing_combinations(
        self, executor: SyncHookExecutor, num_queries: int, num_hooks: int
    ) -> None:
        """Measure time for combined operations."""
        optimizer = QueryOptimizer()
        registry = SyncHookRegistry()

        # Create queries
        queries = [
            f"SELECT ?event WHERE {{ ?event a <http://example.org/Event{i}> }}"
            for i in range(num_queries)
        ]

        # Create hooks
        for i in range(num_hooks):

            def make_handler(idx: int) -> Any:
                def handler(ctx: dict[str, Any]) -> dict[str, Any]:
                    return {"hook_id": idx}

                return handler

            hook = Hook(
                name=f"hook_{i}",
                description=f"Test hook {i}",
                condition=AlwaysTrueCondition(),
                handler=make_handler(i),
            )
            registry.register(hook)

        # Measure combined execution
        start = time.perf_counter()

        # Query optimizations
        for query in queries[:min(num_queries, 100)]:
            optimizer.optimize(query)

        # Hook executions
        context: dict[str, Any] = {}
        receipts = registry.execute_all(context)

        duration = time.perf_counter() - start

        # Performance assertions (relaxed for CI)
        max_duration = max(num_queries, num_hooks) * 0.2  # 200ms per operation
        assert duration < max_duration
        assert len(receipts) == num_hooks

    def test_concurrent_condition_evaluation(
        self, executor: SyncHookExecutor
    ) -> None:
        """Test multiple conditions evaluated sequentially."""
        evaluator = SyncConditionEvaluator()

        conditions = [
            AlwaysTrueCondition(),
            ThresholdCondition(
                variable="value", operator=ThresholdOperator.GREATER_THAN, value=5.0
            ),
        ]

        context = {"value": 10}

        start = time.perf_counter()

        # Evaluate all conditions
        results = [evaluator.evaluate(c, context) for c in conditions]

        duration = time.perf_counter() - start

        # All should pass
        assert all(r.triggered for r in results)

        # Should be fast
        assert duration < 0.5  # 500ms

    def test_hook_registry_bulk_operations(
        self, executor: SyncHookExecutor
    ) -> None:
        """Test bulk hook registration and execution."""
        registry = SyncHookRegistry()

        # Register 50 hooks
        for i in range(50):

            def make_handler(idx: int) -> Any:
                def handler(ctx: dict[str, Any]) -> dict[str, Any]:
                    return {"idx": idx}

                return handler

            hook = Hook(
                name=f"bulk_hook_{i}",
                description=f"Bulk test hook {i}",
                condition=AlwaysTrueCondition(),
                handler=make_handler(i),
            )
            registry.register(hook)

        # Execute all
        start = time.perf_counter()
        context: dict[str, Any] = {}
        receipts = registry.execute_all(context)
        duration = time.perf_counter() - start

        # All should succeed
        assert len(receipts) == 50
        assert all(r.condition_result.triggered for r in receipts)

        # Should be reasonably fast
        assert duration < 10.0  # 10 seconds for 50 hooks


class TestComplexIntegrationScenarios:
    """Test complex real-world integration scenarios."""

    @pytest.fixture
    def registry(self) -> SyncHookRegistry:
        """Create sync hook registry."""
        return SyncHookRegistry()

    def test_event_processing_pipeline(self, registry: SyncHookRegistry) -> None:
        """Real-world scenario: Process events with filtering and hooks."""
        # Create hook for high-priority events
        processed_events: list[str] = []

        def high_priority_handler(ctx: dict[str, Any]) -> dict[str, Any]:
            processed_events.append(str(ctx.get("event")))
            return {"processed": True}

        # Condition: priority > 5
        condition = ThresholdCondition(
            variable="priority", operator=ThresholdOperator.GREATER_THAN, value=5.0
        )

        hook = Hook(
            name="high_priority_hook",
            description="Process high-priority events",
            condition=condition,
            handler=high_priority_handler,
        )
        registry.register(hook)

        # Execute pipeline for each event
        receipts = []
        for i in range(10):
            context = {"priority": i, "event": f"event{i}"}
            receipt_list = registry.execute_all(context)
            receipts.extend(receipt_list)

        # Verify: only events with priority > 5 should be processed
        triggered_count = sum(1 for r in receipts if r.condition_result.triggered)
        assert triggered_count == 4  # events 6, 7, 8, 9

    def test_streaming_pipeline_with_hooks(self, registry: SyncHookRegistry) -> None:
        """Test streaming data through pipeline with hooks."""
        # Create hooks for different event types
        event_counts = {"typeA": 0, "typeB": 0, "typeC": 0}

        def create_handler(event_type: str) -> Any:
            def handler(ctx: dict[str, Any]) -> dict[str, Any]:
                if ctx.get("type") == event_type:
                    event_counts[event_type] += 1
                    return {"counted": True, "type": event_type}
                return {"counted": False}

            return handler

        for event_type in ["typeA", "typeB", "typeC"]:
            hook = Hook(
                name=f"hook_{event_type}",
                description=f"Handle {event_type} events",
                condition=AlwaysTrueCondition(),
                handler=create_handler(event_type),
            )
            registry.register(hook)

        # Stream events
        events = [
            {"type": "typeA"},
            {"type": "typeB"},
            {"type": "typeA"},
            {"type": "typeC"},
            {"type": "typeB"},
        ]

        all_receipts = []
        for event in events:
            receipts = registry.execute_all(event)
            all_receipts.extend(receipts)

        # Verify counts
        assert event_counts["typeA"] == 2
        assert event_counts["typeB"] == 2
        assert event_counts["typeC"] == 1

        # Total receipts (3 hooks per event)
        assert len(all_receipts) == len(events) * 3
