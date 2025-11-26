"""
Chicago School TDD Tests for UNRDF Integration.

Tests define how hooks interact with UNRDF store with real graph operations.
Real object collaboration - hooks modify actual graphs.
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from kgcl.hooks.conditions import Condition, ConditionResult
from kgcl.hooks.core import Hook, HookExecutor
from kgcl.hooks.lifecycle import HookExecutionPipeline


class GraphQueryCondition(Condition):
    """Test condition that queries graph state."""

    def __init__(self, query: str, expected_count: int = 1):
        super().__init__()
        self.query = query
        self.expected_count = expected_count

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        graph = context.get("graph")
        if graph is None:
            return ConditionResult(triggered=False, metadata={"error": "no_graph"})

        # Simulate SPARQL query
        count = graph.count_triples(self.query)
        triggered = count >= self.expected_count

        return ConditionResult(
            triggered=triggered,
            metadata={"count": count, "expected": self.expected_count},
        )


class GraphDeltaCondition(Condition):
    """Test condition that detects graph changes."""

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        before_count = context.get("before_triple_count", 0)
        after_count = context.get("after_triple_count", 0)
        delta = after_count - before_count

        return ConditionResult(
            triggered=delta > 0,
            metadata={"delta": delta, "before": before_count, "after": after_count},
        )


def add_triple_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Handler that adds triples to graph."""
    graph = context.get("graph")
    if graph:
        triple = context.get("triple", ("s", "p", "o"))
        graph.add_triple(*triple)
        return {"added": True, "triple": triple}
    return {"added": False}


def modify_graph_handler(context: dict[str, Any]) -> dict[str, Any]:
    """Handler that modifies graph."""
    graph = context.get("graph")
    if graph:
        graph.update(context.get("update", ""))
        return {"modified": True}
    return {"modified": False}


class MockGraph:
    """Mock UNRDF graph for testing."""

    def __init__(self):
        self.triples = []
        self.version = 0

    def add_triple(self, subject, predicate, obj):
        """Add a triple to the graph."""
        self.triples.append((subject, predicate, obj))
        self.version += 1

    def remove_triple(self, subject, predicate, obj):
        """Remove a triple from the graph."""
        self.triples.remove((subject, predicate, obj))
        self.version += 1

    def count_triples(self, query: str | None = None) -> int:
        """Count triples matching query."""
        if query is None:
            return len(self.triples)
        # Simplified query matching
        return len(self.triples)

    def update(self, update_query: str):
        """Execute update query."""
        self.version += 1

    def get_state_hash(self) -> str:
        """Get hash of current graph state."""
        import hashlib

        content = "\n".join([f"{s} {p} {o}" for s, p, o in self.triples])
        return hashlib.sha256(content.encode()).hexdigest()


class TestHookGraphQuery:
    """Test hook querying UNRDF store during condition evaluation."""

    @pytest.mark.asyncio
    async def test_hook_can_query_unrdf_store_during_condition_evaluation(self):
        """Hook can query UNRDF store during condition evaluation."""
        graph = MockGraph()
        graph.add_triple("http://ex.org/s1", "http://ex.org/p", "http://ex.org/o1")
        graph.add_triple("http://ex.org/s2", "http://ex.org/p", "http://ex.org/o2")

        condition = GraphQueryCondition(
            query="SELECT * WHERE { ?s ?p ?o }", expected_count=2
        )

        hook = Hook(
            name="query_test",
            description="Test graph query",
            condition=condition,
            handler=lambda ctx: {"queried": True},
        )

        executor = HookExecutor()
        receipt = await executor.execute(hook, context={"graph": graph})

        assert receipt.condition_result.triggered is True
        assert receipt.condition_result.metadata["count"] == 2


class TestHookGraphModification:
    """Test hook modifying UNRDF store via handler."""

    @pytest.mark.asyncio
    async def test_hook_can_modify_unrdf_store_via_handler(self):
        """Hook can modify UNRDF store via handler."""
        graph = MockGraph()
        initial_count = len(graph.triples)

        hook = Hook(
            name="modify_test",
            description="Test graph modification",
            condition=GraphQueryCondition(query="*", expected_count=0),
            handler=add_triple_handler,
        )

        executor = HookExecutor()
        receipt = await executor.execute(
            hook,
            context={
                "graph": graph,
                "triple": ("http://ex.org/s", "http://ex.org/p", "http://ex.org/o"),
            },
        )

        assert receipt.handler_result["added"] is True
        assert len(graph.triples) == initial_count + 1


class TestTransactionalModifications:
    """Test transactional hook modifications."""

    @pytest.mark.asyncio
    async def test_hook_modifications_are_transactional(self):
        """Hook modifications are transactional."""
        graph = MockGraph()
        graph.add_triple("http://ex.org/s1", "http://ex.org/p", "http://ex.org/o1")

        def transactional_handler(context: dict[str, Any]) -> dict[str, Any]:
            graph = context.get("graph")
            # Start transaction
            version_before = graph.version

            try:
                graph.add_triple(
                    "http://ex.org/s2", "http://ex.org/p", "http://ex.org/o2"
                )
                graph.add_triple(
                    "http://ex.org/s3", "http://ex.org/p", "http://ex.org/o3"
                )
                # Commit transaction
                return {"committed": True, "version": graph.version}
            except Exception as e:
                # Rollback transaction
                return {"committed": False, "error": str(e)}

        hook = Hook(
            name="transactional_test",
            description="Test transactional modification",
            condition=GraphQueryCondition(query="*", expected_count=1),
            handler=transactional_handler,
        )

        executor = HookExecutor()
        receipt = await executor.execute(hook, context={"graph": graph})

        assert receipt.handler_result["committed"] is True
        assert len(graph.triples) == 3  # Initial + 2 added


class TestGraphDeltaDetection:
    """Test hook triggering on graph changes."""

    @pytest.mark.asyncio
    async def test_hook_can_trigger_on_graph_changes_delta(self):
        """Hook can trigger on graph changes (delta)."""
        graph = MockGraph()

        # Initial state
        before_count = len(graph.triples)

        # Make changes
        graph.add_triple("http://ex.org/s1", "http://ex.org/p", "http://ex.org/o1")
        graph.add_triple("http://ex.org/s2", "http://ex.org/p", "http://ex.org/o2")

        after_count = len(graph.triples)

        hook = Hook(
            name="delta_test",
            description="Test delta detection",
            condition=GraphDeltaCondition(),
            handler=lambda ctx: {"detected": True},
        )

        executor = HookExecutor()
        receipt = await executor.execute(
            hook,
            context={
                "graph": graph,
                "before_triple_count": before_count,
                "after_triple_count": after_count,
            },
        )

        assert receipt.condition_result.triggered is True
        assert receipt.condition_result.metadata["delta"] == 2


class TestMultipleHooksExecution:
    """Test multiple hooks executing in priority order."""

    @pytest.mark.asyncio
    async def test_multiple_hooks_can_execute_in_priority_order(self):
        """Multiple hooks can execute in priority order."""
        graph = MockGraph()
        execution_order = []

        def make_handler(name: str):
            def handler(ctx: dict[str, Any]) -> dict[str, Any]:
                execution_order.append(name)
                return {"handler": name}

            return handler

        hooks = [
            Hook(
                name="low_priority",
                description="Low priority",
                condition=GraphQueryCondition(query="*", expected_count=0),
                handler=make_handler("low"),
                priority=10,
            ),
            Hook(
                name="high_priority",
                description="High priority",
                condition=GraphQueryCondition(query="*", expected_count=0),
                handler=make_handler("high"),
                priority=90,
            ),
            Hook(
                name="mid_priority",
                description="Mid priority",
                condition=GraphQueryCondition(query="*", expected_count=0),
                handler=make_handler("mid"),
                priority=50,
            ),
        ]

        pipeline = HookExecutionPipeline()
        await pipeline.execute_batch(hooks, context={"graph": graph})

        # Should execute in priority order (high to low)
        assert execution_order == ["high", "mid", "low"]


class TestHookFailurePrevention:
    """Test hook failure preventing subsequent hooks."""

    @pytest.mark.asyncio
    async def test_hook_failure_prevents_subsequent_hooks(self):
        """Hook failure prevents subsequent hooks."""
        graph = MockGraph()
        executed = []

        def success_handler(ctx: dict[str, Any]) -> dict[str, Any]:
            executed.append("success")
            return {"success": True}

        def failing_handler(ctx: dict[str, Any]) -> dict[str, Any]:
            executed.append("failing")
            raise RuntimeError("Handler failed")

        hooks = [
            Hook(
                name="first",
                description="First hook",
                condition=GraphQueryCondition(query="*", expected_count=0),
                handler=success_handler,
                priority=90,
            ),
            Hook(
                name="failing",
                description="Failing hook",
                condition=GraphQueryCondition(query="*", expected_count=0),
                handler=failing_handler,
                priority=50,
            ),
            Hook(
                name="third",
                description="Third hook",
                condition=GraphQueryCondition(query="*", expected_count=0),
                handler=success_handler,
                priority=10,
            ),
        ]

        pipeline = HookExecutionPipeline(stop_on_error=True)
        await pipeline.execute_batch(hooks, context={"graph": graph})

        # Should execute first and failing, but not third
        assert "success" in executed
        assert "failing" in executed
        assert len(executed) == 2  # Third hook not executed


class TestHookSuccessProvenance:
    """Test hook success recorded in graph provenance."""

    @pytest.mark.asyncio
    async def test_hook_success_recorded_in_graph_provenance(self):
        """Hook success recorded in graph provenance."""
        graph = MockGraph()

        def provenance_handler(ctx: dict[str, Any]) -> dict[str, Any]:
            graph = ctx.get("graph")
            hook_id = ctx.get("hook_id", "unknown")

            # Record provenance as triple
            graph.add_triple(
                f"http://ex.org/execution/{hook_id}",
                "http://purl.org/pav/executedAt",
                datetime.now(UTC).isoformat(),
            )

            return {"provenance_recorded": True}

        hook = Hook(
            name="provenance_test",
            description="Test provenance recording",
            condition=GraphQueryCondition(query="*", expected_count=0),
            handler=provenance_handler,
        )

        executor = HookExecutor()
        receipt = await executor.execute(
            hook, context={"graph": graph, "hook_id": "provenance_test"}
        )

        assert receipt.handler_result["provenance_recorded"] is True
        # Check that provenance triple was added
        provenance_triples = [t for t in graph.triples if "executedAt" in str(t[1])]
        assert len(provenance_triples) == 1


class TestGraphStateConsistency:
    """Test graph state consistency during hook execution."""

    @pytest.mark.asyncio
    async def test_graph_state_consistent_during_hook_chain(self):
        """Graph state remains consistent during hook chain."""
        graph = MockGraph()

        state_snapshots = []

        def snapshot_handler(ctx: dict[str, Any]) -> dict[str, Any]:
            graph = ctx.get("graph")
            state_snapshots.append(
                {"count": len(graph.triples), "hash": graph.get_state_hash()}
            )
            # Add a triple
            graph.add_triple(
                f"http://ex.org/s{len(state_snapshots)}",
                "http://ex.org/p",
                "http://ex.org/o",
            )
            return {"snapshot": len(state_snapshots)}

        hooks = [
            Hook(
                name=f"hook{i}",
                description=f"Hook {i}",
                condition=GraphQueryCondition(query="*", expected_count=0),
                handler=snapshot_handler,
            )
            for i in range(3)
        ]

        pipeline = HookExecutionPipeline()
        await pipeline.execute_batch(hooks, context={"graph": graph})

        # Each hook should see the state left by previous hook
        assert len(state_snapshots) == 3
        assert state_snapshots[0]["count"] == 0
        assert state_snapshots[1]["count"] == 1
        assert state_snapshots[2]["count"] == 2

        # Hashes should be different (state changed)
        assert len(set(s["hash"] for s in state_snapshots)) == 3


class TestConcurrentHookExecution:
    """Test concurrent hook execution with graph locking."""

    @pytest.mark.asyncio
    async def test_concurrent_hooks_respect_graph_locks(self):
        """Concurrent hooks respect graph locks."""
        graph = MockGraph()
        graph.lock = False

        async def locking_handler(ctx: dict[str, Any]) -> dict[str, Any]:
            import asyncio

            graph = ctx.get("graph")

            # Acquire lock
            while graph.lock:
                await asyncio.sleep(0.01)

            graph.lock = True

            # Do work
            graph.add_triple("http://ex.org/s", "http://ex.org/p", "http://ex.org/o")
            await asyncio.sleep(0.05)

            # Release lock
            graph.lock = False

            return {"locked": True}

        # Create multiple hooks that will execute concurrently
        hooks = [
            Hook(
                name=f"concurrent{i}",
                description=f"Concurrent hook {i}",
                condition=GraphQueryCondition(query="*", expected_count=0),
                handler=locking_handler,
            )
            for i in range(3)
        ]

        # Execute all hooks
        import asyncio

        executor = HookExecutor()
        results = await asyncio.gather(
            *[executor.execute(hook, context={"graph": graph}) for hook in hooks]
        )

        # All should succeed
        assert all(r.handler_result["locked"] for r in results)
        # All triples should be added (no race condition)
        assert len(graph.triples) == 3
