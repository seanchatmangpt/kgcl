"""Tests for Innovation #8: Performance Optimizer with SLO Tracking.

Chicago School TDD: Real latency tracking, no mocking.
Tests percentile calculation, SLO enforcement, and optimization.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hooks.performance_optimizer import (
    OptimizationPath,
    PerformanceConfig,
    PerformanceMetrics,
    PerformanceOptimizer,
)


class TestPerformanceConfig:
    """Tests for performance configuration."""

    def test_default_config_values(self) -> None:
        """Default config has 2ms p99 target."""
        config = PerformanceConfig()

        assert config.p99_target_ms == 2.0
        assert config.enable_fast_path is True
        assert config.enable_caching is True
        assert config.max_concurrency == 10
        assert config.sample_size == 1000

    def test_custom_config(self) -> None:
        """Custom config values are stored."""
        config = PerformanceConfig(p99_target_ms=5.0, max_concurrency=20)

        assert config.p99_target_ms == 5.0
        assert config.max_concurrency == 20


class TestPerformanceMetrics:
    """Tests for performance metrics dataclass."""

    def test_metrics_creation(self) -> None:
        """Metrics stores all latency data."""
        metrics = PerformanceMetrics(
            p50_latency_ms=0.5, p95_latency_ms=1.2, p99_latency_ms=1.8, slo_met=True, sample_count=100
        )

        assert metrics.p50_latency_ms == 0.5
        assert metrics.p99_latency_ms == 1.8
        assert metrics.slo_met is True


class TestLatencyRecording:
    """Tests for latency recording and tracking."""

    def test_record_latency(self) -> None:
        """Latencies are recorded correctly."""
        optimizer = PerformanceOptimizer()

        optimizer.record_latency(1.5)
        optimizer.record_latency(2.5)

        assert len(optimizer._latencies) == 2

    def test_latency_rolling_window(self) -> None:
        """Latency window respects max size."""
        config = PerformanceConfig(sample_size=3)
        optimizer = PerformanceOptimizer(config=config)

        for i in range(5):
            optimizer.record_latency(float(i))

        # Only last 3 should be kept
        assert len(optimizer._latencies) == 3

    def test_fast_path_count_tracked(self) -> None:
        """Fast path executions are counted."""
        optimizer = PerformanceOptimizer()

        optimizer.record_latency(0.5, OptimizationPath.FAST)
        optimizer.record_latency(1.0, OptimizationPath.STANDARD)
        optimizer.record_latency(0.3, OptimizationPath.FAST)

        assert optimizer._fast_path_count == 2
        assert optimizer._total_count == 3


class TestPercentileCalculation:
    """Tests for percentile latency calculations."""

    def test_p50_calculation(self) -> None:
        """P50 (median) is calculated correctly."""
        optimizer = PerformanceOptimizer()
        for i in range(1, 11):  # 1-10
            optimizer.record_latency(float(i))

        p50 = optimizer.p50_latency

        # Median of 1-10 is ~5
        assert 4.0 <= p50 <= 6.0

    def test_p99_calculation(self) -> None:
        """P99 is calculated correctly."""
        optimizer = PerformanceOptimizer()
        for i in range(100):
            optimizer.record_latency(float(i))

        p99 = optimizer.p99_latency

        # 99th percentile of 0-99 should be ~98
        assert p99 >= 90.0

    def test_empty_percentile_is_zero(self) -> None:
        """Empty latency set returns zero percentile."""
        optimizer = PerformanceOptimizer()

        assert optimizer.p50_latency == 0.0
        assert optimizer.p99_latency == 0.0


class TestSLOEnforcement:
    """Tests for SLO target enforcement."""

    def test_slo_met_under_target(self) -> None:
        """SLO is met when p99 under target."""
        config = PerformanceConfig(p99_target_ms=10.0)
        optimizer = PerformanceOptimizer(config=config)
        optimizer.record_latency(5.0)

        assert optimizer.is_slo_met() is True

    def test_slo_not_met_over_target(self) -> None:
        """SLO is not met when p99 over target."""
        config = PerformanceConfig(p99_target_ms=1.0)
        optimizer = PerformanceOptimizer(config=config)
        optimizer.record_latency(5.0)

        assert optimizer.is_slo_met() is False


class TestThrottling:
    """Tests for execution throttling."""

    def test_no_throttle_with_low_latency(self) -> None:
        """No throttling when latency is low."""
        config = PerformanceConfig(p99_target_ms=10.0)
        optimizer = PerformanceOptimizer(config=config)
        for _ in range(20):
            optimizer.record_latency(1.0)

        assert optimizer.should_throttle() is False

    def test_throttle_with_high_latency(self) -> None:
        """Throttling recommended when p95 exceeds target."""
        config = PerformanceConfig(p99_target_ms=1.0)
        optimizer = PerformanceOptimizer(config=config)
        for _ in range(20):
            optimizer.record_latency(5.0)  # All above target

        assert optimizer.should_throttle() is True

    def test_insufficient_samples_no_throttle(self) -> None:
        """No throttling with insufficient samples."""
        optimizer = PerformanceOptimizer()
        optimizer.record_latency(100.0)  # High but only 1 sample

        assert optimizer.should_throttle() is False


class TestConditionClassification:
    """Tests for condition query classification."""

    def test_empty_condition_fast_path(self) -> None:
        """Empty condition uses fast path."""
        optimizer = PerformanceOptimizer()

        path = optimizer.classify_condition("")

        assert path == OptimizationPath.FAST

    def test_simple_pattern_fast_path(self) -> None:
        """Simple triple pattern uses fast path."""
        optimizer = PerformanceOptimizer()

        path = optimizer.classify_condition("ASK { ?s a :Person }")

        assert path == OptimizationPath.FAST

    def test_complex_query_standard_path(self) -> None:
        """Complex query with joins uses standard path."""
        optimizer = PerformanceOptimizer()

        path = optimizer.classify_condition("ASK { ?s ?p ?o . ?o ?q ?r . ?r ?x ?y . ?y ?z ?w }")

        assert path in (OptimizationPath.STANDARD, OptimizationPath.SLOW)

    def test_group_by_slow_path(self) -> None:
        """Query with GROUP BY uses slow path."""
        optimizer = PerformanceOptimizer()

        path = optimizer.classify_condition("SELECT (COUNT(?s) as ?c) WHERE { ?s ?p ?o } GROUP BY ?p")

        assert path == OptimizationPath.SLOW

    def test_service_slow_path(self) -> None:
        """Query with SERVICE uses slow path."""
        optimizer = PerformanceOptimizer()

        path = optimizer.classify_condition("SELECT ?s WHERE { SERVICE <http://example.org/sparql> { ?s ?p ?o } }")

        assert path == OptimizationPath.SLOW


class TestConcurrencyRecommendation:
    """Tests for recommended concurrency calculation."""

    def test_default_concurrency_when_healthy(self) -> None:
        """Default concurrency when SLO met."""
        config = PerformanceConfig(max_concurrency=10, p99_target_ms=10.0)
        optimizer = PerformanceOptimizer(config=config)
        optimizer.record_latency(1.0)

        recommended = optimizer.get_recommended_concurrency()

        assert recommended >= 10

    def test_reduced_concurrency_when_throttling(self) -> None:
        """Reduced concurrency when throttling."""
        config = PerformanceConfig(max_concurrency=10, p99_target_ms=1.0)
        optimizer = PerformanceOptimizer(config=config)
        for _ in range(20):
            optimizer.record_latency(10.0)  # High latency

        recommended = optimizer.get_recommended_concurrency()

        assert recommended < 10


class TestMetricsSnapshot:
    """Tests for metrics snapshot generation."""

    def test_get_metrics_empty(self) -> None:
        """Empty optimizer returns zero metrics."""
        optimizer = PerformanceOptimizer()

        metrics = optimizer.get_metrics()

        assert metrics.sample_count == 0
        assert metrics.slo_met is True

    def test_get_metrics_with_data(self) -> None:
        """Metrics snapshot with recorded data."""
        optimizer = PerformanceOptimizer()
        optimizer.record_latency(1.0, OptimizationPath.FAST)
        optimizer.record_latency(2.0, OptimizationPath.STANDARD)

        metrics = optimizer.get_metrics()

        assert metrics.sample_count == 2
        assert metrics.fast_path_ratio == 50.0


class TestReset:
    """Tests for optimizer reset."""

    def test_reset_clears_data(self) -> None:
        """Reset clears all tracking data."""
        optimizer = PerformanceOptimizer()
        optimizer.record_latency(1.0, OptimizationPath.FAST)

        optimizer.reset()

        assert len(optimizer._latencies) == 0
        assert optimizer._fast_path_count == 0
        assert optimizer._total_count == 0


class TestReportExport:
    """Tests for performance report export."""

    def test_report_structure(self) -> None:
        """Report has expected structure."""
        optimizer = PerformanceOptimizer()

        report = optimizer.export_report()

        assert "slo_target_ms" in report
        assert "slo_met" in report
        assert "latencies" in report
        assert "execution_stats" in report
        assert "recommendations" in report

    def test_report_with_data(self) -> None:
        """Report includes recorded data."""
        optimizer = PerformanceOptimizer()
        optimizer.record_latency(1.5)

        report = optimizer.export_report()

        assert report["execution_stats"]["total_executions"] == 1
        assert report["latencies"]["p99_ms"] == 1.5
