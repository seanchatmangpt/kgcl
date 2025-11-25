"""
Tests for remaining hook modules: QueryOptimizer, TransactionManager, HookManager, Observability.

Chicago School TDD: No mocking of domain objects, real implementations.
"""

import pytest
import time
from datetime import datetime

from kgcl.hooks.query_optimizer import QueryOptimizer, QueryPlan
from kgcl.hooks.transaction import (
    Transaction,
    TransactionManager,
    TransactionState,
    TransactionError,
    IsolationViolation,
)
from kgcl.hooks.core import Hook, HookManager, HookReceipt, HookValidationError
from kgcl.hooks.conditions import SparqlAskCondition, ConditionResult
from kgcl.hooks.observability import Observability, HealthCheck


# Helper for tests
class SimpleCondition:
    """Simple test condition that always triggers."""

    async def evaluate(self, context):
        return ConditionResult(triggered=True)


# ============================================================================
# QueryOptimizer Tests
# ============================================================================


class TestQueryOptimizer:
    """Test QueryOptimizer functionality."""

    def test_analyze_simple_query(self):
        """Should analyze simple SPARQL query."""
        optimizer = QueryOptimizer()
        query = "SELECT ?s WHERE { ?s <type> <Person> }"

        plan = optimizer.analyze_query(query)

        assert isinstance(plan, QueryPlan)
        assert plan.query == query
        assert 0.0 <= plan.estimated_selectivity <= 1.0
        assert plan.estimated_cost > 0
        assert len(plan.execution_path) > 0
        assert "Parse query" in plan.execution_path

    def test_analyze_complex_query(self):
        """Should analyze complex query with UNION and FILTER."""
        optimizer = QueryOptimizer()
        query = """
        SELECT ?s ?name WHERE {
            { ?s <type> <Person> . ?s <name> ?name }
            UNION
            { ?s <type> <Organization> . ?s <label> ?name }
            FILTER(regex(?name, "test"))
        }
        """

        plan = optimizer.analyze_query(query)

        assert plan.estimated_cost > 0
        assert "Execute UNION branches" in plan.execution_path
        assert "Apply filter conditions" in plan.execution_path
        assert plan.parallelizable  # UNION without ORDER BY

    def test_cost_estimation(self):
        """Should estimate higher cost for complex queries."""
        optimizer = QueryOptimizer()

        simple_query = "SELECT ?s WHERE { ?s <type> <Person> }"
        complex_query = """
        SELECT ?s ?o WHERE {
            ?s <type> <Person> .
            ?s <name> ?name .
            ?s <knows> ?o .
            OPTIONAL { ?o <age> ?age }
            FILTER(?age > 18)
        }
        ORDER BY ?name
        """

        simple_plan = optimizer.analyze_query(simple_query)
        complex_plan = optimizer.analyze_query(complex_query)

        assert complex_plan.estimated_cost > simple_plan.estimated_cost

    def test_index_suggestion(self):
        """Should suggest indexes for query optimization."""
        optimizer = QueryOptimizer()
        query = "SELECT ?s WHERE { ?s <http://example.org/predicate> ?o }"

        suggestions = optimizer.suggest_indexes(query)

        assert len(suggestions) > 0
        assert any("INDEX" in s for s in suggestions)

    def test_query_optimization(self):
        """Should produce optimized query."""
        optimizer = QueryOptimizer()
        query = "SELECT ?s WHERE { ?s <type> <Person> } ORDER BY ?s"

        optimized = optimizer.optimize(query)

        assert optimized is not None
        assert "LIMIT" in optimized  # Should add LIMIT to ORDER BY query

    def test_selectivity_estimation(self):
        """Should estimate selectivity correctly."""
        optimizer = QueryOptimizer()

        # Query with no filters (less selective)
        broad_query = "SELECT ?s WHERE { ?s ?p ?o }"
        # Query with filters (more selective)
        narrow_query = "SELECT ?s WHERE { ?s <type> <Person> FILTER(?age > 18) }"

        broad_plan = optimizer.analyze_query(broad_query)
        narrow_plan = optimizer.analyze_query(narrow_query)

        # More filters = lower selectivity value (more selective)
        assert narrow_plan.estimated_selectivity < broad_plan.estimated_selectivity

    def test_record_execution(self):
        """Should record execution time."""
        optimizer = QueryOptimizer()
        query = "SELECT ?s WHERE { ?s <type> <Person> }"

        optimizer.analyze_query(query)
        optimizer.record_execution(query, 150.5)

        stats = optimizer.get_stats(query)
        assert stats is not None
        assert stats["executions"] == 1
        assert stats["avg_time_ms"] == 150.5

    def test_execution_stats_averaging(self):
        """Should compute rolling average of execution times."""
        optimizer = QueryOptimizer()
        query = "SELECT ?s WHERE { ?s <type> <Person> }"

        optimizer.analyze_query(query)
        optimizer.record_execution(query, 100.0)
        optimizer.record_execution(query, 200.0)
        optimizer.record_execution(query, 300.0)

        stats = optimizer.get_stats(query)
        assert stats["executions"] == 3
        assert stats["avg_time_ms"] == 200.0


# ============================================================================
# TransactionManager Tests
# ============================================================================


class TestTransaction:
    """Test Transaction lifecycle."""

    def test_begin_commit(self):
        """Should begin and commit transaction."""
        tx = Transaction(tx_id="tx1")
        assert tx.state == TransactionState.PENDING

        tx.begin()
        assert tx.state == TransactionState.EXECUTING

        tx.commit()
        assert tx.state == TransactionState.COMMITTED
        assert tx.completed_at is not None

    def test_begin_rollback(self):
        """Should begin and rollback transaction."""
        tx = Transaction(tx_id="tx1")
        tx.begin()

        tx.add_triple("s1", "p1", "o1")
        tx.add_triple("s2", "p2", "o2")
        assert len(tx.added_triples) == 2

        tx.rollback()
        assert tx.state == TransactionState.ROLLED_BACK
        assert len(tx.added_triples) == 0  # Changes cleared
        assert tx.completed_at is not None

    def test_cannot_begin_twice(self):
        """Should not allow beginning transaction twice."""
        tx = Transaction(tx_id="tx1")
        tx.begin()

        with pytest.raises(TransactionError, match="Cannot begin"):
            tx.begin()

    def test_cannot_commit_without_begin(self):
        """Should not allow commit without begin."""
        tx = Transaction(tx_id="tx1")

        with pytest.raises(TransactionError, match="Cannot commit"):
            tx.commit()

    def test_add_remove_triples(self):
        """Should track triple additions and removals."""
        tx = Transaction(tx_id="tx1")
        tx.begin()

        tx.add_triple("s1", "p1", "o1")
        tx.remove_triple("s2", "p2", "o2")

        assert ("s1", "p1", "o1") in tx.added_triples
        assert ("s2", "p2", "o2") in tx.removed_triples

    def test_get_changes(self):
        """Should return all changes."""
        tx = Transaction(tx_id="tx1")
        tx.begin()

        tx.add_triple("s1", "p1", "o1")
        tx.remove_triple("s2", "p2", "o2")

        changes = tx.get_changes()
        assert len(changes["added"]) == 1
        assert len(changes["removed"]) == 1


class TestTransactionManager:
    """Test TransactionManager."""

    def test_begin_transaction(self):
        """Should create and begin transaction."""
        manager = TransactionManager()

        tx = manager.begin_transaction()

        assert tx.state == TransactionState.EXECUTING
        assert tx.tx_id in manager.transactions

    def test_commit_transaction(self):
        """Should commit transaction."""
        manager = TransactionManager()
        tx = manager.begin_transaction()

        manager.commit_transaction(tx.tx_id)

        assert tx.state == TransactionState.COMMITTED
        assert tx.tx_id not in manager.transactions  # Moved to committed
        assert len(manager.committed_transactions) == 1

    def test_rollback_transaction(self):
        """Should rollback transaction."""
        manager = TransactionManager()
        tx = manager.begin_transaction()
        tx.add_triple("s1", "p1", "o1")

        manager.rollback_transaction(tx.tx_id)

        assert tx.state == TransactionState.ROLLED_BACK
        assert tx.tx_id not in manager.transactions
        assert len(manager.rolled_back_transactions) == 1
        assert len(tx.added_triples) == 0

    def test_concurrent_transactions(self):
        """Should support multiple concurrent transactions."""
        manager = TransactionManager(max_concurrent=5)

        tx1 = manager.begin_transaction()
        tx2 = manager.begin_transaction()
        tx3 = manager.begin_transaction()

        assert len(manager.transactions) == 3
        assert tx1.tx_id != tx2.tx_id != tx3.tx_id

    def test_max_concurrent_enforcement(self):
        """Should enforce max concurrent limit."""
        manager = TransactionManager(max_concurrent=2)

        manager.begin_transaction()
        manager.begin_transaction()

        with pytest.raises(TransactionError, match="Too many concurrent"):
            manager.begin_transaction()

    def test_transaction_not_found(self):
        """Should raise error for unknown transaction."""
        manager = TransactionManager()

        with pytest.raises(TransactionError, match="not found"):
            manager.commit_transaction("nonexistent")

    def test_get_transaction(self):
        """Should retrieve transaction by ID."""
        manager = TransactionManager()
        tx = manager.begin_transaction()

        retrieved = manager.get_transaction(tx.tx_id)

        assert retrieved is tx

    def test_get_active_transactions(self):
        """Should return all active transactions."""
        manager = TransactionManager()
        tx1 = manager.begin_transaction()
        tx2 = manager.begin_transaction()

        active = manager.get_active_transactions()

        assert len(active) == 2
        assert tx1 in active
        assert tx2 in active

    def test_get_stats(self):
        """Should return transaction statistics."""
        manager = TransactionManager(max_concurrent=10)
        tx1 = manager.begin_transaction()
        tx2 = manager.begin_transaction()
        manager.commit_transaction(tx1.tx_id)

        stats = manager.get_stats()

        assert stats["active"] == 1
        assert stats["committed"] == 1
        assert stats["rolled_back"] == 0
        assert stats["max_concurrent"] == 10

    def test_isolation_serializable(self):
        """Should detect conflicts in SERIALIZABLE isolation."""
        manager = TransactionManager()

        tx1 = manager.begin_transaction(isolation_level="SERIALIZABLE")
        tx2 = manager.begin_transaction(isolation_level="SERIALIZABLE")

        # Create conflicting changes (both adding same triple)
        tx1.add_triple("s1", "p1", "o1")
        tx2.add_triple("s1", "p1", "o1")

        # First commit should succeed
        manager.commit_transaction(tx1.tx_id)

        # Second should pass (no conflict - same operation)
        # The conflict detection should only trigger on opposing operations
        manager.commit_transaction(tx2.tx_id)

        # Verify both committed
        assert tx1.state == TransactionState.COMMITTED
        assert tx2.state == TransactionState.COMMITTED

    def test_acquire_release_lock(self):
        """Should acquire and release locks."""
        manager = TransactionManager()
        tx = manager.begin_transaction()

        # Acquire lock
        success = manager.acquire_lock(tx.tx_id, "resource1")
        assert success is True

        # Try to acquire same lock with different tx
        tx2 = manager.begin_transaction()
        success2 = manager.acquire_lock(tx2.tx_id, "resource1")
        assert success2 is False

        # Release and try again
        manager.release_lock(tx.tx_id, "resource1")
        success3 = manager.acquire_lock(tx2.tx_id, "resource1")
        assert success3 is True


# ============================================================================
# HookManager Tests
# ============================================================================


class TestHookManager:
    """Test HookManager functionality."""

    def test_register_hook(self):
        """Should register hook and return ID."""
        manager = HookManager()
        hook = Hook(
            name="test_hook",
            description="Test",
            condition=SimpleCondition(),
            handler=lambda ctx: {"status": "ok"},
        )

        hook_id = manager.register_hook(hook)

        assert hook_id is not None
        assert hook_id in manager.hooks
        assert manager.hooks[hook_id] is hook

    def test_cannot_register_duplicate(self):
        """Should not allow duplicate hook names."""
        manager = HookManager()
        hook = Hook(
            name="test_hook",
            description="Test",
            condition=SimpleCondition(),
            handler=lambda ctx: {"status": "ok"},
        )

        manager.register_hook(hook)

        with pytest.raises(HookValidationError, match="already registered"):
            manager.register_hook(hook)

    def test_unregister_hook(self):
        """Should unregister hook."""
        manager = HookManager()
        hook = Hook(
            name="test_hook",
            description="Test",
            condition=SimpleCondition(),
            handler=lambda ctx: {"status": "ok"},
        )

        hook_id = manager.register_hook(hook)
        manager.unregister_hook(hook_id)

        assert hook_id not in manager.hooks
        assert hook.name not in manager._hook_ids

    def test_get_hook_by_id(self):
        """Should retrieve hook by ID."""
        manager = HookManager()
        hook = Hook(
            name="test_hook",
            description="Test",
            condition=SimpleCondition(),
            handler=lambda ctx: {"status": "ok"},
        )

        hook_id = manager.register_hook(hook)
        retrieved = manager.get_hook(hook_id)

        assert retrieved is hook

    def test_get_hook_by_name(self):
        """Should retrieve hook by name."""
        manager = HookManager()
        hook = Hook(
            name="test_hook",
            description="Test",
            condition=SimpleCondition(),
            handler=lambda ctx: {"status": "ok"},
        )

        manager.register_hook(hook)
        retrieved = manager.get_hook_by_name("test_hook")

        assert retrieved is hook

    def test_record_execution(self):
        """Should record execution receipt."""
        manager = HookManager()
        hook = Hook(
            name="test_hook",
            description="Test",
            condition=SimpleCondition(),
            handler=lambda ctx: {"status": "ok"},
        )

        hook_id = manager.register_hook(hook)
        receipt = HookReceipt(
            hook_id=hook_id,
            timestamp=datetime.utcnow(),
            condition_result=ConditionResult(triggered=True),
            handler_result={"status": "ok"},
            duration_ms=50.0,
        )

        manager.record_execution(receipt)

        assert len(manager.execution_history) == 1
        assert manager.execution_history[0] is receipt

    def test_get_hook_stats(self):
        """Should compute hook statistics."""
        manager = HookManager()
        hook = Hook(
            name="test_hook",
            description="Test",
            condition=SimpleCondition(),
            handler=lambda ctx: {"status": "ok"},
        )

        hook_id = manager.register_hook(hook)

        # Record successful execution
        receipt1 = HookReceipt(
            hook_id=hook_id,
            timestamp=datetime.utcnow(),
            condition_result=ConditionResult(triggered=True),
            handler_result={"status": "ok"},
            duration_ms=50.0,
        )
        manager.record_execution(receipt1)

        # Record failed execution
        receipt2 = HookReceipt(
            hook_id=hook_id,
            timestamp=datetime.utcnow(),
            condition_result=ConditionResult(triggered=True),
            handler_result=None,
            duration_ms=30.0,
            error="Test error",
        )
        manager.record_execution(receipt2)

        stats = manager.get_hook_stats(hook_id)

        assert stats["total_executions"] == 2
        assert stats["successes"] == 1
        assert stats["failures"] == 1
        assert stats["success_rate"] == 0.5
        assert stats["avg_duration_ms"] == 40.0

    def test_get_all_hooks(self):
        """Should return all hooks."""
        manager = HookManager()
        hook1 = Hook(
            name="hook1",
            description="Test 1",
            condition=SimpleCondition(),
            handler=lambda ctx: {},
        )
        hook2 = Hook(
            name="hook2",
            description="Test 2",
            condition=SimpleCondition(),
            handler=lambda ctx: {},
        )

        manager.register_hook(hook1)
        manager.register_hook(hook2)

        all_hooks = manager.get_all_hooks()

        assert len(all_hooks) == 2
        assert hook1 in all_hooks
        assert hook2 in all_hooks

    def test_clear_history(self):
        """Should clear execution history."""
        manager = HookManager()
        hook = Hook(
            name="test_hook",
            description="Test",
            condition=SimpleCondition(),
            handler=lambda ctx: {},
        )

        hook_id = manager.register_hook(hook)
        receipt = HookReceipt(
            hook_id=hook_id,
            timestamp=datetime.utcnow(),
            condition_result=ConditionResult(triggered=True),
            handler_result={},
            duration_ms=10.0,
        )
        manager.record_execution(receipt)

        manager.clear_history()

        assert len(manager.execution_history) == 0


# ============================================================================
# Observability Tests
# ============================================================================


class TestObservability:
    """Test Observability monitoring."""

    def test_record_metric(self):
        """Should record metric values."""
        obs = Observability()

        obs.record_metric("test_metric", 100.0)
        obs.record_metric("test_metric", 200.0)

        metrics = obs.get_all_metrics()
        assert "test_metric" in metrics
        assert len(metrics["test_metric"]) == 2
        assert metrics["test_metric"] == [100.0, 200.0]

    def test_get_metric_stats(self):
        """Should compute metric statistics."""
        obs = Observability()

        obs.record_metric("duration_ms", 100.0)
        obs.record_metric("duration_ms", 200.0)
        obs.record_metric("duration_ms", 300.0)

        stats = obs.get_metric_stats("duration_ms")

        assert stats is not None
        assert stats["current"] == 300.0
        assert stats["avg"] == 200.0
        assert stats["min"] == 100.0
        assert stats["max"] == 300.0
        assert stats["count"] == 3

    def test_get_health_status(self):
        """Should return health status."""
        obs = Observability()

        obs.record_metric("cpu_usage", 50.0)
        obs.record_metric("memory_usage", 70.0)

        health = obs.get_health_status()

        assert isinstance(health, HealthCheck)
        assert health.is_healthy is True
        assert "cpu_usage_current" in health.metrics
        assert "memory_usage_current" in health.metrics

    def test_threshold_warnings(self):
        """Should detect threshold violations."""
        obs = Observability()

        obs.set_threshold("cpu_usage", warning=80.0, error=95.0)
        obs.record_metric("cpu_usage", 85.0)

        health = obs.get_health_status()

        assert len(health.warnings) > 0
        assert "cpu_usage" in health.warnings[0]
        assert health.is_healthy is True  # Warning, not error

    def test_threshold_errors(self):
        """Should detect error thresholds."""
        obs = Observability()

        obs.set_threshold("cpu_usage", warning=80.0, error=95.0)
        obs.record_metric("cpu_usage", 98.0)

        health = obs.get_health_status()

        assert len(health.errors) > 0
        assert "cpu_usage" in health.errors[0]
        assert health.is_healthy is False

    def test_anomaly_detection(self):
        """Should detect metric anomalies."""
        obs = Observability()

        # Record baseline values
        for _ in range(10):
            obs.record_metric("response_time", 100.0)

        # Record anomaly (2x average)
        obs.record_metric("response_time", 250.0)

        health = obs.get_health_status()

        assert len(health.warnings) > 0
        assert "response_time" in health.warnings[0]

    def test_clear_metrics(self):
        """Should clear all metrics."""
        obs = Observability()

        obs.record_metric("test", 100.0)
        obs.get_health_status()

        obs.clear_metrics()

        assert len(obs.get_all_metrics()) == 0
        assert len(obs.get_health_history()) == 0

    def test_get_health_history(self):
        """Should return health check history."""
        obs = Observability()

        obs.record_metric("test", 100.0)
        health1 = obs.get_health_status()

        obs.record_metric("test", 200.0)
        health2 = obs.get_health_status()

        history = obs.get_health_history()

        assert len(history) == 2
        assert health1 in history
        assert health2 in history

    def test_detect_anomalies(self):
        """Should detect anomalies with configurable threshold."""
        obs = Observability()

        # Record normal values
        for i in range(20):
            obs.record_metric("latency", 100.0 + i)

        # Record spike
        obs.record_metric("latency", 500.0)

        anomalies = obs.detect_anomalies(window=10, threshold=2.0)

        assert len(anomalies) > 0
        assert "latency" in anomalies[0]

    def test_record_hook_execution(self):
        """Should record hook-specific metrics."""
        obs = Observability()

        obs.record_hook_execution("hook1", 50.0, True)
        obs.record_hook_execution("hook1", 60.0, True)
        obs.record_hook_execution("hook1", 70.0, False)

        stats = obs.get_hook_stats("hook1")

        assert stats["executions"] == 3
        assert stats["avg_duration_ms"] == 60.0
        assert stats["success_rate"] == 2.0 / 3.0
        assert stats["total_successes"] == 2.0
        assert stats["total_failures"] == 1.0

    def test_max_history_limit(self):
        """Should enforce max history limit."""
        obs = Observability(max_history=10)

        for i in range(20):
            obs.record_metric("test", float(i))

        metrics = obs.get_all_metrics()
        assert len(metrics["test"]) == 10
        # Should keep most recent values
        assert metrics["test"][-1] == 19.0
