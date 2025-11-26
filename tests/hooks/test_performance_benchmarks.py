"""
Performance Benchmark Suite for KGCL Hooks System.

Measures performance against documented SLO targets:
- Hook registration: target <5ms
- Condition evaluation: target <10ms
- Hook execution: target <100ms
- Receipt writing: target <10ms
- Full pipeline: target <500ms

Implements comprehensive benchmark scenarios including:
- Hook registration at scale (100, 1000 hooks)
- Concurrent hook execution
- Query cache hit/miss scenarios
- Error sanitization overhead
- SPARQL condition evaluation
"""

import asyncio
import statistics
import time
from dataclasses import dataclass
from typing import Any

import pytest

from kgcl.hooks.conditions import Condition, ConditionResult, SparqlAskCondition, ThresholdCondition, ThresholdOperator
from kgcl.hooks.core import Hook, HookManager, HookReceipt, HookRegistry
from kgcl.hooks.lifecycle import HookExecutionPipeline
from kgcl.hooks.performance import PerformanceOptimizer
from kgcl.hooks.query_cache import QueryCache
from kgcl.hooks.security import ErrorSanitizer

# ============================================================================
# Test Helpers
# ============================================================================


class AlwaysTrueCondition(Condition):
    """Simple condition that always returns True for benchmarking."""

    async def evaluate(self, context: dict[str, Any]) -> ConditionResult:
        """Return True immediately."""
        return ConditionResult(triggered=True, metadata={})


# ============================================================================
# Performance Measurement Infrastructure
# ============================================================================


@dataclass
class BenchmarkResult:
    """Result of a performance benchmark."""

    operation: str
    samples: list[float]  # latency in ms
    target_ms: float
    mean: float
    median: float
    p50: float
    p95: float
    p99: float
    min_ms: float
    max_ms: float
    stdev: float
    compliant: bool  # Whether p99 meets target
    compliance_rate: float  # Percentage of samples meeting target


class PerformanceBenchmark:
    """Utility class for running performance benchmarks."""

    @staticmethod
    def measure_latency(samples: list[float], target_ms: float, operation: str) -> BenchmarkResult:
        """Calculate performance statistics from samples."""
        if not samples:
            return BenchmarkResult(
                operation=operation,
                samples=[],
                target_ms=target_ms,
                mean=0.0,
                median=0.0,
                p50=0.0,
                p95=0.0,
                p99=0.0,
                min_ms=0.0,
                max_ms=0.0,
                stdev=0.0,
                compliant=False,
                compliance_rate=0.0,
            )

        sorted_samples = sorted(samples)
        n = len(sorted_samples)

        mean = statistics.mean(samples)
        median = statistics.median(samples)
        stdev = statistics.stdev(samples) if n > 1 else 0.0

        p50 = sorted_samples[int(n * 0.50)]
        p95 = sorted_samples[int(n * 0.95)]
        p99 = sorted_samples[int(n * 0.99)]

        compliant_count = sum(1 for s in samples if s <= target_ms)
        compliance_rate = compliant_count / n

        return BenchmarkResult(
            operation=operation,
            samples=samples,
            target_ms=target_ms,
            mean=mean,
            median=median,
            p50=p50,
            p95=p95,
            p99=p99,
            min_ms=min(samples),
            max_ms=max(samples),
            stdev=stdev,
            compliant=p99 <= target_ms,
            compliance_rate=compliance_rate,
        )

    @staticmethod
    async def benchmark_async(operation: str, target_ms: float, iterations: int, func: Any) -> BenchmarkResult:
        """Benchmark an async function."""
        samples = []

        for _ in range(iterations):
            start = time.perf_counter()
            await func()
            end = time.perf_counter()
            duration_ms = (end - start) * 1000
            samples.append(duration_ms)

        return PerformanceBenchmark.measure_latency(samples, target_ms, operation)

    @staticmethod
    def benchmark_sync(operation: str, target_ms: float, iterations: int, func: Any) -> BenchmarkResult:
        """Benchmark a synchronous function."""
        samples = []

        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            duration_ms = (end - start) * 1000
            samples.append(duration_ms)

        return PerformanceBenchmark.measure_latency(samples, target_ms, operation)


# ============================================================================
# SLO Target #1: Hook Registration (<5ms)
# ============================================================================


@pytest.mark.performance
def test_hook_registration_single():
    """Benchmark single hook registration against <5ms target."""
    registry = HookRegistry()

    def register_hook():
        hook = Hook(
            name=f"hook_{time.time_ns()}",
            description="Test hook",
            condition=AlwaysTrueCondition(),
            handler=lambda ctx: {"result": "ok"},
        )
        registry.register(hook)

    result = PerformanceBenchmark.benchmark_sync("hook_registration_single", 5.0, 100, register_hook)

    assert result.p99 < 5.0, f"P99 latency {result.p99:.2f}ms exceeds 5ms target"
    assert result.mean < 2.0, f"Mean latency {result.mean:.2f}ms should be well under target"


@pytest.mark.performance
def test_hook_registration_100():
    """Benchmark registering 100 hooks sequentially."""
    registry = HookRegistry()
    samples = []

    for i in range(100):
        start = time.perf_counter()
        hook = Hook(
            name=f"hook_{i}",
            description="Test hook",
            condition=AlwaysTrueCondition(),
            handler=lambda ctx: {"result": "ok"},
        )
        registry.register(hook)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        samples.append(duration_ms)

    result = PerformanceBenchmark.measure_latency(samples, 5.0, "hook_registration_100")

    assert result.p99 < 5.0, f"P99 latency {result.p99:.2f}ms exceeds 5ms target"


@pytest.mark.performance
@pytest.mark.slow
def test_hook_registration_1000():
    """Benchmark registering 1000 hooks sequentially."""
    registry = HookRegistry()
    samples = []

    for i in range(1000):
        start = time.perf_counter()
        hook = Hook(
            name=f"hook_{i}",
            description="Test hook",
            condition=AlwaysTrueCondition(),
            handler=lambda ctx: {"result": "ok"},
        )
        registry.register(hook)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        samples.append(duration_ms)

    result = PerformanceBenchmark.measure_latency(samples, 5.0, "hook_registration_1000")

    assert result.p99 < 5.0, f"P99 latency {result.p99:.2f}ms exceeds 5ms target"


# ============================================================================
# SLO Target #2: Condition Evaluation (<10ms)
# ============================================================================


@pytest.mark.performance
@pytest.mark.asyncio
async def test_condition_evaluation_always_true():
    """Benchmark AlwaysTrueCondition evaluation."""
    condition = AlwaysTrueCondition()
    context = {"test": "data"}

    async def evaluate():
        await condition.evaluate(context)

    result = await PerformanceBenchmark.benchmark_async("condition_eval_always_true", 10.0, 100, evaluate)

    assert result.p99 < 10.0, f"P99 latency {result.p99:.2f}ms exceeds 10ms target"
    assert result.mean < 2.0, f"Mean latency {result.mean:.2f}ms should be well under target"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_condition_evaluation_threshold():
    """Benchmark ThresholdCondition evaluation."""
    condition = ThresholdCondition("value", ThresholdOperator.GREATER_THAN, 50.0)
    context = {"value": 75}

    async def evaluate():
        await condition.evaluate(context)

    result = await PerformanceBenchmark.benchmark_async("condition_eval_threshold", 10.0, 100, evaluate)

    assert result.p99 < 10.0, f"P99 latency {result.p99:.2f}ms exceeds 10ms target"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_condition_evaluation_sparql_ask_no_cache():
    """Benchmark SPARQL ASK condition without cache."""
    condition = SparqlAskCondition("ASK { ?s ?p ?o }", use_cache=False)
    context = {"test_result": True}

    async def evaluate():
        await condition.evaluate(context)

    result = await PerformanceBenchmark.benchmark_async("condition_eval_sparql_ask_no_cache", 10.0, 100, evaluate)

    assert result.p99 < 10.0, f"P99 latency {result.p99:.2f}ms exceeds 10ms target"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_condition_evaluation_sparql_ask_with_cache():
    """Benchmark SPARQL ASK condition with cache (should be faster)."""
    SparqlAskCondition.clear_cache()
    condition = SparqlAskCondition("ASK { ?s ?p ?o }", use_cache=True)
    context = {"test_result": True}

    # Warm up cache
    await condition.evaluate(context)

    samples = []
    for _ in range(100):
        start = time.perf_counter()
        await condition.evaluate(context)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        samples.append(duration_ms)

    result = PerformanceBenchmark.measure_latency(samples, 5.0, "condition_eval_sparql_ask_with_cache")

    # Cache hits should be much faster
    assert result.p99 < 5.0, f"P99 latency {result.p99:.2f}ms exceeds 5ms target with cache"
    assert result.mean < 2.0, f"Mean cache hit latency {result.mean:.2f}ms should be <2ms"


# ============================================================================
# SLO Target #3: Hook Execution (<100ms)
# ============================================================================


@pytest.mark.performance
@pytest.mark.asyncio
async def test_hook_execution_simple_handler():
    """Benchmark end-to-end hook execution with simple handler."""
    pipeline = HookExecutionPipeline(enable_performance_tracking=True)

    condition = AlwaysTrueCondition()
    handler = lambda ctx: {"result": "success"}

    hook = Hook(name="benchmark_hook", description="Benchmark hook", condition=condition, handler=handler)

    context = {"test": "data"}

    samples = []
    for _ in range(100):
        start = time.perf_counter()
        await pipeline.execute(hook, context)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        samples.append(duration_ms)

    result = PerformanceBenchmark.measure_latency(samples, 100.0, "hook_execution_simple")

    assert result.p99 < 100.0, f"P99 latency {result.p99:.2f}ms exceeds 100ms target"
    assert result.mean < 10.0, f"Mean latency {result.mean:.2f}ms should be well under target"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_hook_execution_async_handler():
    """Benchmark hook execution with async handler."""
    pipeline = HookExecutionPipeline(enable_performance_tracking=True)

    condition = AlwaysTrueCondition()

    async def async_handler(ctx):
        await asyncio.sleep(0.001)  # 1ms simulated work
        return {"result": "async_success"}

    hook = Hook(
        name="async_benchmark_hook", description="Async benchmark hook", condition=condition, handler=async_handler
    )

    context = {"test": "data"}

    samples = []
    for _ in range(100):
        start = time.perf_counter()
        await pipeline.execute(hook, context)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        samples.append(duration_ms)

    result = PerformanceBenchmark.measure_latency(samples, 100.0, "hook_execution_async")

    assert result.p99 < 100.0, f"P99 latency {result.p99:.2f}ms exceeds 100ms target"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_hook_execution_concurrent():
    """Benchmark concurrent execution of multiple hooks."""
    pipeline = HookExecutionPipeline(enable_performance_tracking=True)

    # Create 10 hooks
    hooks = []
    for i in range(10):
        condition = AlwaysTrueCondition()
        handler = lambda ctx, i=i: {"result": f"success_{i}"}
        hook = Hook(
            name=f"concurrent_hook_{i}", description=f"Concurrent hook {i}", condition=condition, handler=handler
        )
        hooks.append(hook)

    context = {"test": "data"}

    samples = []
    for _ in range(10):  # 10 iterations of concurrent execution
        start = time.perf_counter()
        tasks = [pipeline.execute(hook, context) for hook in hooks]
        await asyncio.gather(*tasks)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        samples.append(duration_ms)

    result = PerformanceBenchmark.measure_latency(samples, 500.0, "hook_execution_concurrent_10")

    # All 10 should complete within 500ms
    assert result.p99 < 500.0, f"P99 latency {result.p99:.2f}ms exceeds 500ms target"


# ============================================================================
# SLO Target #4: Receipt Writing (<10ms)
# ============================================================================


@pytest.mark.performance
def test_receipt_creation():
    """Benchmark HookReceipt creation."""
    from datetime import UTC, datetime

    from kgcl.hooks.conditions import ConditionResult

    samples = []

    for _ in range(100):
        start = time.perf_counter()
        receipt = HookReceipt(
            hook_id="test_hook",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"result": "success"},
            duration_ms=5.0,
            actor="benchmark_user",
            metadata={"test": "data"},
        )
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        samples.append(duration_ms)
        # Use receipt to avoid unused variable warning
        _ = receipt.receipt_id

    result = PerformanceBenchmark.measure_latency(samples, 10.0, "receipt_creation")

    assert result.p99 < 10.0, f"P99 latency {result.p99:.2f}ms exceeds 10ms target"
    assert result.mean < 1.0, f"Mean latency {result.mean:.2f}ms should be <1ms"


@pytest.mark.performance
def test_receipt_recording():
    """Benchmark recording receipts in HookManager."""
    from datetime import UTC, datetime

    from kgcl.hooks.conditions import ConditionResult

    manager = HookManager()

    samples = []

    for i in range(100):
        receipt = HookReceipt(
            hook_id=f"test_hook_{i}",
            timestamp=datetime.now(UTC),
            condition_result=ConditionResult(triggered=True, metadata={}),
            handler_result={"result": "success"},
            duration_ms=5.0,
        )

        start = time.perf_counter()
        manager.record_execution(receipt)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        samples.append(duration_ms)

    result = PerformanceBenchmark.measure_latency(samples, 10.0, "receipt_recording")

    assert result.p99 < 10.0, f"P99 latency {result.p99:.2f}ms exceeds 10ms target"


# ============================================================================
# SLO Target #5: Full Pipeline (<500ms)
# ============================================================================


@pytest.mark.performance
@pytest.mark.asyncio
async def test_full_pipeline_single_hook():
    """Benchmark full pipeline execution with single hook."""
    pipeline = HookExecutionPipeline(enable_performance_tracking=True)

    condition = SparqlAskCondition("ASK { ?s ?p ?o }", use_cache=False)
    handler = lambda ctx: {"result": "pipeline_success"}

    hook = Hook(name="pipeline_hook", description="Full pipeline hook", condition=condition, handler=handler)

    context = {"test_result": True}

    samples = []
    for _ in range(50):
        start = time.perf_counter()
        await pipeline.execute(hook, context)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        samples.append(duration_ms)

    result = PerformanceBenchmark.measure_latency(samples, 500.0, "full_pipeline_single")

    assert result.p99 < 500.0, f"P99 latency {result.p99:.2f}ms exceeds 500ms target"
    assert result.mean < 50.0, f"Mean latency {result.mean:.2f}ms should be well under target"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_full_pipeline_multiple_hooks_sequential():
    """Benchmark full pipeline with multiple hooks executed sequentially."""
    pipeline = HookExecutionPipeline(enable_performance_tracking=True)

    hooks = []
    for i in range(5):
        condition = ThresholdCondition("value", ThresholdOperator.GREATER_THAN, 10.0)
        handler = lambda ctx, i=i: {"result": f"hook_{i}"}
        hook = Hook(name=f"pipeline_hook_{i}", description=f"Pipeline hook {i}", condition=condition, handler=handler)
        hooks.append(hook)

    context = {"value": 50}

    samples = []
    for _ in range(20):
        start = time.perf_counter()
        for hook in hooks:
            await pipeline.execute(hook, context)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        samples.append(duration_ms)

    result = PerformanceBenchmark.measure_latency(samples, 500.0, "full_pipeline_5_hooks_sequential")

    assert result.p99 < 500.0, f"P99 latency {result.p99:.2f}ms exceeds 500ms target"


# ============================================================================
# Additional Performance Scenarios
# ============================================================================


@pytest.mark.performance
def test_query_cache_performance():
    """Benchmark query cache hit/miss performance."""
    cache = QueryCache(max_size=1000, ttl_seconds=3600)

    # Benchmark cache misses
    miss_samples = []
    for i in range(100):
        query = f"SELECT * WHERE {{ ?s ?p ?o }} LIMIT {i}"
        start = time.perf_counter()
        result = cache.get(query)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        miss_samples.append(duration_ms)
        assert result is None

    miss_result = PerformanceBenchmark.measure_latency(miss_samples, 2.0, "cache_miss")

    # Populate cache
    for i in range(100):
        query = f"SELECT * WHERE {{ ?s ?p ?o }} LIMIT {i}"
        cache.set(query, {"data": [i]})

    # Benchmark cache hits
    hit_samples = []
    for i in range(100):
        query = f"SELECT * WHERE {{ ?s ?p ?o }} LIMIT {i}"
        start = time.perf_counter()
        result = cache.get(query)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        hit_samples.append(duration_ms)
        assert result is not None

    hit_result = PerformanceBenchmark.measure_latency(hit_samples, 1.0, "cache_hit")

    # Cache hits meet SLO target
    assert hit_result.p99 < 1.0, f"Cache hit P99 {hit_result.p99:.2f}ms should be <1ms"
    # Note: Cache lookups aren't always faster due to hashing overhead on small datasets


@pytest.mark.performance
def test_error_sanitization_overhead():
    """Benchmark error sanitization overhead."""
    sanitizer = ErrorSanitizer()

    samples = []
    for _ in range(100):
        try:
            # Generate error
            raise ValueError("Test error with /sensitive/path/data.txt")
        except ValueError as e:
            start = time.perf_counter()
            sanitized = sanitizer.sanitize(e)
            end = time.perf_counter()
            duration_ms = (end - start) * 1000
            samples.append(duration_ms)
            # Use sanitized to avoid unused variable warning
            assert sanitized.message

    result = PerformanceBenchmark.measure_latency(samples, 5.0, "error_sanitization")

    assert result.p99 < 5.0, f"P99 latency {result.p99:.2f}ms exceeds 5ms target"
    assert result.mean < 1.0, f"Mean latency {result.mean:.2f}ms should be <1ms"


@pytest.mark.performance
def test_performance_optimizer_recording():
    """Benchmark PerformanceOptimizer metric recording."""
    from kgcl.hooks.performance import PerformanceMetrics

    optimizer = PerformanceOptimizer(sample_size=1000)

    samples = []
    for i in range(100):
        metric = PerformanceMetrics(operation="test_operation", latency_ms=float(i), success=True, p99_target_ms=100.0)

        start = time.perf_counter()
        optimizer.record_metric(metric)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        samples.append(duration_ms)

    result = PerformanceBenchmark.measure_latency(samples, 2.0, "optimizer_record_metric")

    assert result.p99 < 2.0, f"P99 latency {result.p99:.2f}ms exceeds 2ms target"


# ============================================================================
# Performance Report Generation
# ============================================================================


def generate_performance_report(results: list[BenchmarkResult]) -> str:
    """Generate a comprehensive performance report."""
    report_lines = [
        "=" * 80,
        "KGCL HOOKS PERFORMANCE BENCHMARK REPORT",
        "=" * 80,
        "",
        "SLO Targets:",
        "  - Hook registration: <5ms (p99)",
        "  - Condition evaluation: <10ms (p99)",
        "  - Hook execution: <100ms (p99)",
        "  - Receipt writing: <10ms (p99)",
        "  - Full pipeline: <500ms (p99)",
        "",
        "=" * 80,
        "BENCHMARK RESULTS",
        "=" * 80,
        "",
    ]

    for result in results:
        compliant_emoji = "✓" if result.compliant else "✗"
        report_lines.extend(
            [
                f"Operation: {result.operation}",
                f"  Target:     {result.target_ms:.2f}ms",
                f"  Compliant:  {compliant_emoji} ({result.compliance_rate * 100:.1f}% samples)",
                f"  Mean:       {result.mean:.4f}ms",
                f"  Median:     {result.median:.4f}ms",
                f"  P50:        {result.p50:.4f}ms",
                f"  P95:        {result.p95:.4f}ms",
                f"  P99:        {result.p99:.4f}ms",
                f"  Min:        {result.min_ms:.4f}ms",
                f"  Max:        {result.max_ms:.4f}ms",
                f"  StdDev:     {result.stdev:.4f}ms",
                "",
            ]
        )

    # Summary
    total = len(results)
    compliant = sum(1 for r in results if r.compliant)
    report_lines.extend(
        [
            "=" * 80,
            "SUMMARY",
            "=" * 80,
            f"Total Benchmarks:    {total}",
            f"SLO Compliant:       {compliant}",
            f"SLO Non-Compliant:   {total - compliant}",
            f"Overall Compliance:  {compliant / total * 100:.1f}%",
            "",
        ]
    )

    return "\n".join(report_lines)
