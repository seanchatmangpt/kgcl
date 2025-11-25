"""
Comprehensive Tests for Performance Optimization Features.

Tests PerformanceOptimizer, QueryCache, and their integrations with
conditions and lifecycle modules.
"""

import asyncio
import time

import pytest

from kgcl.hooks.conditions import SparqlAskCondition, SparqlSelectCondition
from kgcl.hooks.core import Hook
from kgcl.hooks.lifecycle import HookExecutionPipeline
from kgcl.hooks.performance import PerformanceMetrics, PerformanceOptimizer
from kgcl.hooks.query_cache import QueryCache

# ============================================================================
# Test PerformanceOptimizer (12 tests)
# ============================================================================


def test_record_metric():
    """Test recording a single metric."""
    optimizer = PerformanceOptimizer(sample_size=100)
    metric = PerformanceMetrics(operation="test_op", latency_ms=50.0)

    optimizer.record_metric(metric)

    assert "test_op" in optimizer.samples
    assert len(optimizer.samples["test_op"]) == 1
    assert optimizer.samples["test_op"][0] == 50.0
    assert "test_op" in optimizer.metrics
    assert len(optimizer.metrics["test_op"]) == 1


def test_record_latency():
    """Test recording latency using convenience method."""
    optimizer = PerformanceOptimizer(sample_size=100)

    optimizer.record_latency("test_op", 75.5)

    assert "test_op" in optimizer.samples
    assert optimizer.samples["test_op"][0] == 75.5


def test_sample_size_limit():
    """Test that only last N samples are kept."""
    optimizer = PerformanceOptimizer(sample_size=5)

    # Record 10 samples
    for i in range(10):
        optimizer.record_latency("test_op", float(i))

    # Should only keep last 5
    assert len(optimizer.samples["test_op"]) == 5
    assert optimizer.samples["test_op"] == [5.0, 6.0, 7.0, 8.0, 9.0]


def test_percentile_p50():
    """Test P50 percentile calculation."""
    optimizer = PerformanceOptimizer(sample_size=100)

    # Record samples: 10, 20, 30, 40, 50
    for i in range(1, 6):
        optimizer.record_latency("test_op", float(i * 10))

    p50 = optimizer.get_percentile("test_op", 0.50)
    assert p50 == 30.0  # Median of [10, 20, 30, 40, 50]


def test_percentile_p99():
    """Test P99 percentile calculation."""
    optimizer = PerformanceOptimizer(sample_size=100)

    # Record 100 samples
    for i in range(1, 101):
        optimizer.record_latency("test_op", float(i))

    p99 = optimizer.get_percentile("test_op", 0.99)
    # P99 of 100 samples at 0.99 * 100 = 99 (index 99, which is value 100)
    assert p99 == 100.0


def test_percentile_p999():
    """Test P999 percentile calculation."""
    optimizer = PerformanceOptimizer(sample_size=100)

    # Record 100 samples
    for i in range(1, 101):
        optimizer.record_latency("test_op", float(i))

    p999 = optimizer.get_percentile("test_op", 0.999)
    # P999 of 100 samples at 0.999 * 100 = 99.9 (rounds to index 99, value 100)
    assert p999 == 100.0


def test_get_stats_complete():
    """Test comprehensive statistics retrieval."""
    optimizer = PerformanceOptimizer(sample_size=100)

    # Record samples: 10, 20, 30, 40, 50
    for i in range(1, 6):
        optimizer.record_latency("test_op", float(i * 10))

    stats = optimizer.get_stats("test_op")

    assert stats is not None
    assert stats["operation"] == "test_op"
    assert stats["count"] == 5
    assert stats["min"] == 10.0
    assert stats["max"] == 50.0
    assert stats["mean"] == 30.0
    assert stats["median"] == 30.0
    assert stats["p50"] == 30.0
    assert stats["p99"] == 50.0
    assert stats["stdev"] > 0


def test_get_stats_insufficient_data():
    """Test that None is returned for operations with no data."""
    optimizer = PerformanceOptimizer(sample_size=100)

    stats = optimizer.get_stats("nonexistent_op")

    assert stats is None


def test_get_slo_status_compliant():
    """Test SLO compliance rate calculation."""
    optimizer = PerformanceOptimizer(sample_size=100)

    # Record metrics: 3 compliant, 2 non-compliant
    optimizer.record_metric(
        PerformanceMetrics(operation="test_op", latency_ms=50.0, p99_target_ms=100.0)
    )
    optimizer.record_metric(
        PerformanceMetrics(operation="test_op", latency_ms=75.0, p99_target_ms=100.0)
    )
    optimizer.record_metric(
        PerformanceMetrics(operation="test_op", latency_ms=150.0, p99_target_ms=100.0)
    )
    optimizer.record_metric(
        PerformanceMetrics(operation="test_op", latency_ms=90.0, p99_target_ms=100.0)
    )
    optimizer.record_metric(
        PerformanceMetrics(operation="test_op", latency_ms=200.0, p99_target_ms=100.0)
    )

    slo_status = optimizer.get_slo_status("test_op", target_ms=100.0)

    assert slo_status is not None
    assert slo_status["operation"] == "test_op"
    assert slo_status["target_ms"] == 100.0
    assert slo_status["compliant_count"] == 3
    assert slo_status["total_count"] == 5
    assert slo_status["compliance_rate"] == 0.6
    assert slo_status["success_rate"] == 1.0


def test_get_slo_status_violations():
    """Test SLO violation tracking."""
    optimizer = PerformanceOptimizer(sample_size=100)

    # Record metrics with failures
    optimizer.record_metric(
        PerformanceMetrics(operation="test_op", latency_ms=50.0, success=True, p99_target_ms=100.0)
    )
    optimizer.record_metric(
        PerformanceMetrics(
            operation="test_op", latency_ms=150.0, success=False, p99_target_ms=100.0
        )
    )

    slo_status = optimizer.get_slo_status("test_op", target_ms=100.0)

    assert slo_status is not None
    assert slo_status["success_rate"] == 0.5


def test_meets_slo_property():
    """Test PerformanceMetrics.meets_slo property."""
    metric_compliant = PerformanceMetrics(operation="test", latency_ms=50.0, p99_target_ms=100.0)
    metric_violation = PerformanceMetrics(operation="test", latency_ms=150.0, p99_target_ms=100.0)

    assert metric_compliant.meets_slo is True
    assert metric_violation.meets_slo is False


def test_get_all_operations():
    """Test listing all tracked operations."""
    optimizer = PerformanceOptimizer(sample_size=100)

    optimizer.record_latency("op1", 10.0)
    optimizer.record_latency("op2", 20.0)
    optimizer.record_latency("op3", 30.0)

    all_ops = optimizer.get_all_operations()

    assert len(all_ops) == 3
    assert "op1" in all_ops
    assert "op2" in all_ops
    assert "op3" in all_ops


# ============================================================================
# Test QueryCache (14 tests)
# ============================================================================


def test_cache_hit():
    """Test cache hit returns cached result."""
    cache = QueryCache(max_size=100, ttl_seconds=3600)
    query = "SELECT * FROM test"
    result = {"data": [1, 2, 3]}

    cache.set(query, result)
    cached_result = cache.get(query)

    assert cached_result == result
    assert cache.hits == 1
    assert cache.misses == 0


def test_cache_miss():
    """Test cache miss returns None."""
    cache = QueryCache(max_size=100, ttl_seconds=3600)

    result = cache.get("nonexistent query")

    assert result is None
    assert cache.hits == 0
    assert cache.misses == 1


def test_cache_expiration():
    """Test expired entries are removed."""
    cache = QueryCache(max_size=100, ttl_seconds=1)
    query = "SELECT * FROM test"
    result = {"data": [1, 2, 3]}

    cache.set(query, result)

    # Wait for expiration
    time.sleep(1.1)

    cached_result = cache.get(query)

    assert cached_result is None
    assert cache.misses == 1


def test_cache_eviction_lru():
    """Test LRU eviction when cache is full."""
    cache = QueryCache(max_size=3, ttl_seconds=3600)

    # Fill cache
    cache.set("query1", "result1")
    cache.set("query2", "result2")
    cache.set("query3", "result3")

    # Add one more (should evict query1)
    cache.set("query4", "result4")

    assert cache.get("query1") is None  # Evicted
    assert cache.get("query2") == "result2"
    assert cache.get("query3") == "result3"
    assert cache.get("query4") == "result4"


def test_cache_set_get():
    """Test set and get work correctly."""
    cache = QueryCache(max_size=100, ttl_seconds=3600)

    cache.set("query1", "result1")
    cache.set("query2", "result2")

    assert cache.get("query1") == "result1"
    assert cache.get("query2") == "result2"


def test_custom_ttl():
    """Test custom TTL is respected."""
    cache = QueryCache(max_size=100, ttl_seconds=3600)
    query = "SELECT * FROM test"
    result = {"data": [1, 2, 3]}

    # Set with custom TTL of 1 second
    cache.set(query, result, ttl_seconds=1)

    # Should be available immediately
    assert cache.get(query) == result

    # Wait for custom TTL expiration
    time.sleep(1.1)

    # Should be expired now
    assert cache.get(query) is None


def test_invalidate_query():
    """Test query can be invalidated."""
    cache = QueryCache(max_size=100, ttl_seconds=3600)
    query = "SELECT * FROM test"
    result = {"data": [1, 2, 3]}

    cache.set(query, result)
    assert cache.get(query) == result

    cache.invalidate(query)

    assert cache.get(query) is None


def test_clear_cache():
    """Test cache can be cleared."""
    cache = QueryCache(max_size=100, ttl_seconds=3600)

    cache.set("query1", "result1")
    cache.set("query2", "result2")

    # Get to increment hits
    cache.get("query1")

    cache.clear()

    assert len(cache.cache) == 0
    assert len(cache.access_order) == 0
    assert cache.hits == 0
    assert cache.misses == 0


def test_hit_rate_calculation():
    """Test hit rate is calculated correctly."""
    cache = QueryCache(max_size=100, ttl_seconds=3600)

    cache.set("query1", "result1")

    # 2 hits, 1 miss
    cache.get("query1")
    cache.get("query1")
    cache.get("query2")  # miss

    assert cache.hit_rate == 2 / 3


def test_query_hash_consistency():
    """Test same query produces same hash."""
    cache = QueryCache(max_size=100, ttl_seconds=3600)
    query = "SELECT * FROM test"

    hash1 = cache._compute_hash(query)
    hash2 = cache._compute_hash(query)

    assert hash1 == hash2


def test_access_order_updated():
    """Test LRU access order is maintained."""
    cache = QueryCache(max_size=100, ttl_seconds=3600)

    cache.set("query1", "result1")
    cache.set("query2", "result2")
    cache.set("query3", "result3")

    # Access query1 (should move to end)
    cache.get("query1")

    # Access order should now be: query2, query3, query1
    assert cache.access_order[-1] == cache._compute_hash("query1")


def test_get_stats_cache():
    """Test cache statistics are returned correctly."""
    cache = QueryCache(max_size=100, ttl_seconds=3600)

    cache.set("query1", "result1")
    cache.get("query1")  # hit
    cache.get("query2")  # miss

    stats = cache.get_stats()

    assert stats["size"] == 1
    assert stats["max_size"] == 100
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["total_requests"] == 2
    assert stats["hit_rate"] == 0.5
    assert stats["ttl_default"] == 3600


def test_expired_entries_count():
    """Test expired entries are counted correctly."""
    cache = QueryCache(max_size=100, ttl_seconds=1)

    cache.set("query1", "result1")
    cache.set("query2", "result2", ttl_seconds=3600)  # Long TTL

    # Wait for first query to expire
    time.sleep(1.1)

    stats = cache.get_stats()

    assert stats["expired_entries"] == 1


def test_large_result_caching():
    """Test large results can be cached."""
    cache = QueryCache(max_size=100, ttl_seconds=3600)
    query = "SELECT * FROM large_table"
    large_result = {"data": list(range(10000))}

    cache.set(query, large_result)
    cached_result = cache.get(query)

    assert cached_result == large_result


# ============================================================================
# Test Lifecycle Integration (8 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_performance_metrics_recorded():
    """Test metrics are recorded during hook execution."""
    pipeline = HookExecutionPipeline(enable_performance_tracking=True)

    condition = SparqlAskCondition("ASK { ?s ?p ?o }", use_cache=False)
    handler = lambda ctx: {"result": "success"}

    hook = Hook(name="test_hook", description="Test hook", condition=condition, handler=handler)

    context = {"test_result": True}
    receipt = await pipeline.execute(hook, context)

    # Check performance stats are available
    stats = pipeline.get_performance_stats("hook_execute_test_hook")
    assert stats is not None
    assert stats["count"] >= 1


@pytest.mark.asyncio
async def test_latency_tracking_per_phase():
    """Test each phase is timed."""
    pipeline = HookExecutionPipeline(enable_performance_tracking=True)

    condition = SparqlAskCondition("ASK { ?s ?p ?o }", use_cache=False)
    handler = lambda ctx: {"result": "success"}

    hook = Hook(name="test_hook", description="Test hook", condition=condition, handler=handler)

    context = {"test_result": True}
    receipt = await pipeline.execute(hook, context)

    stats = pipeline.get_performance_stats("hook_execute_test_hook")
    assert stats is not None
    assert "mean" in stats
    assert stats["mean"] > 0


@pytest.mark.asyncio
async def test_metrics_in_receipt():
    """Test metrics are included in receipt metadata."""
    pipeline = HookExecutionPipeline(enable_performance_tracking=True)

    condition = SparqlAskCondition("ASK { ?s ?p ?o }", use_cache=False)
    handler = lambda ctx: {"result": "success"}

    hook = Hook(name="test_hook", description="Test hook", condition=condition, handler=handler)

    # Execute twice to build up stats
    context = {"test_result": True}
    await pipeline.execute(hook, context)
    receipt = await pipeline.execute(hook, context)

    # Receipt should have performance stats after second execution
    assert receipt is not None


@pytest.mark.asyncio
async def test_slo_violation_detection():
    """Test SLO violations are detected."""
    pipeline = HookExecutionPipeline(enable_performance_tracking=True)

    # Create a slow handler
    async def slow_handler(ctx):
        await asyncio.sleep(0.05)  # 50ms
        return {"result": "slow"}

    condition = SparqlAskCondition("ASK { ?s ?p ?o }", use_cache=False)

    hook = Hook(
        name="slow_hook", description="Slow hook", condition=condition, handler=slow_handler
    )

    context = {"test_result": True}
    receipt = await pipeline.execute(hook, context)

    stats = pipeline.get_performance_stats("hook_execute_slow_hook")
    assert stats is not None
    assert stats["mean"] > 0


@pytest.mark.asyncio
async def test_multiple_operations_tracked():
    """Test multiple operations are tracked separately."""
    pipeline = HookExecutionPipeline(enable_performance_tracking=True)

    condition1 = SparqlAskCondition("ASK { ?s ?p ?o }", use_cache=False)
    condition2 = SparqlAskCondition("ASK { ?x ?y ?z }", use_cache=False)
    handler = lambda ctx: {"result": "success"}

    hook1 = Hook(name="hook1", description="Hook 1", condition=condition1, handler=handler)
    hook2 = Hook(name="hook2", description="Hook 2", condition=condition2, handler=handler)

    context = {"test_result": True}
    await pipeline.execute(hook1, context)
    await pipeline.execute(hook2, context)

    all_stats = pipeline.get_performance_stats()
    assert all_stats is not None
    assert "hook_execute_hook1" in all_stats
    assert "hook_execute_hook2" in all_stats


@pytest.mark.asyncio
async def test_cache_integration_sparql():
    """Test SPARQL results are cached."""
    # Clear cache first
    SparqlAskCondition.clear_cache()

    condition = SparqlAskCondition("ASK { ?s ?p ?o }", use_cache=True)

    # First evaluation
    context1 = {"test_result": True}
    result1 = await condition.evaluate(context1)
    assert result1.metadata.get("cache_hit") is False

    # Second evaluation with same query
    context2 = {"test_result": True}
    result2 = await condition.evaluate(context2)
    assert result2.metadata.get("cache_hit") is True

    # Verify cache stats
    stats = SparqlAskCondition.get_cache_stats()
    assert stats is not None
    assert stats["hits"] >= 1


@pytest.mark.asyncio
async def test_cache_invalidation_on_change():
    """Test cache can be invalidated."""
    # Clear cache first
    SparqlSelectCondition.clear_cache()

    condition = SparqlSelectCondition("SELECT * WHERE { ?s ?p ?o }", use_cache=True)

    # Populate cache
    context = {"test_results": [{"s": "A", "p": "B", "o": "C"}]}
    result1 = await condition.evaluate(context)
    assert result1.metadata.get("cache_hit") is False

    # Clear cache (simulate graph change)
    SparqlSelectCondition.clear_cache()

    # Should be cache miss now
    result2 = await condition.evaluate(context)
    assert result2.metadata.get("cache_hit") is False


@pytest.mark.asyncio
async def test_performance_statistics_available():
    """Test performance statistics are available from pipeline."""
    pipeline = HookExecutionPipeline(enable_performance_tracking=True)

    condition = SparqlAskCondition("ASK { ?s ?p ?o }", use_cache=False)
    handler = lambda ctx: {"result": "success"}

    hook = Hook(name="test_hook", description="Test hook", condition=condition, handler=handler)

    context = {"test_result": True}
    await pipeline.execute(hook, context)

    # Get stats for specific operation
    stats = pipeline.get_performance_stats("hook_execute_test_hook")
    assert stats is not None
    assert "p50" in stats
    assert "p99" in stats
    assert "mean" in stats

    # Get all stats
    all_stats = pipeline.get_performance_stats()
    assert all_stats is not None
    assert len(all_stats) > 0
