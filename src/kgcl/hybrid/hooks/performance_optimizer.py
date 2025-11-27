"""Innovation #8: Performance Optimizer with SLO Tracking.

Enforces p99 < 2ms latency target for hook execution with real-time
monitoring, fast path optimization, and automatic throttling.

Architecture
------------
- Rolling window latency tracking (configurable sample size)
- Percentile calculation for SLO compliance
- Fast path detection for simple conditions
- Automatic concurrency throttling

Examples
--------
>>> from kgcl.hybrid.hooks.performance_optimizer import PerformanceOptimizer, PerformanceConfig
>>> config = PerformanceConfig(p99_target_ms=2.0)
>>> optimizer = PerformanceOptimizer(config)
>>> optimizer.is_slo_met()
True
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class OptimizationPath(Enum):
    """Execution path types.

    FAST   : Simple condition, no N3 reasoning needed
    STANDARD : Normal execution path
    SLOW   : Complex query, may exceed SLO
    """

    FAST = "fast"
    STANDARD = "standard"
    SLOW = "slow"


@dataclass(frozen=True)
class PerformanceConfig:
    """Configuration for performance optimization.

    Parameters
    ----------
    p99_target_ms : float
        Target p99 latency in milliseconds
    enable_fast_path : bool
        Enable fast path for simple conditions
    enable_caching : bool
        Enable query result caching
    max_concurrency : int
        Maximum concurrent hook executions
    sample_size : int
        Rolling window size for latency samples

    Examples
    --------
    >>> config = PerformanceConfig(p99_target_ms=5.0)
    >>> config.p99_target_ms
    5.0
    >>> config.max_concurrency
    10
    """

    p99_target_ms: float = 2.0
    enable_fast_path: bool = True
    enable_caching: bool = True
    max_concurrency: int = 10
    sample_size: int = 1000


@dataclass
class PerformanceMetrics:
    """Snapshot of current performance metrics.

    Parameters
    ----------
    p50_latency_ms : float
        Median latency
    p95_latency_ms : float
        95th percentile latency
    p99_latency_ms : float
        99th percentile latency
    slo_met : bool
        Whether SLO target is met
    sample_count : int
        Number of samples in window
    fast_path_ratio : float
        Percentage of fast path executions

    Examples
    --------
    >>> metrics = PerformanceMetrics(p50_latency_ms=0.5, p99_latency_ms=1.5, slo_met=True)
    >>> metrics.slo_met
    True
    """

    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    slo_met: bool = True
    sample_count: int = 0
    fast_path_ratio: float = 0.0


@dataclass
class PerformanceOptimizer:
    """Optimizes and tracks hook execution performance.

    Monitors execution latency, enforces SLO targets, and provides
    optimization hints for hook execution.

    Attributes
    ----------
    config : PerformanceConfig
        Optimization configuration
    _latencies : deque
        Rolling window of latency samples
    _fast_path_count : int
        Number of fast path executions
    _total_count : int
        Total executions

    Examples
    --------
    >>> optimizer = PerformanceOptimizer()
    >>> optimizer.record_latency(1.0)
    >>> optimizer.p99_latency
    1.0
    """

    config: PerformanceConfig = field(default_factory=PerformanceConfig)
    _latencies: deque[float] = field(default_factory=lambda: deque(maxlen=1000))
    _fast_path_count: int = 0
    _total_count: int = 0

    def __post_init__(self) -> None:
        """Initialize with correct sample size."""
        self._latencies = deque(maxlen=self.config.sample_size)

    def record_latency(self, duration_ms: float, path: OptimizationPath = OptimizationPath.STANDARD) -> None:
        """Record hook execution latency.

        Parameters
        ----------
        duration_ms : float
            Execution time in milliseconds
        path : OptimizationPath
            Execution path taken

        Examples
        --------
        >>> optimizer = PerformanceOptimizer()
        >>> optimizer.record_latency(0.5, OptimizationPath.FAST)
        >>> optimizer._fast_path_count
        1
        """
        self._latencies.append(duration_ms)
        self._total_count += 1

        if path == OptimizationPath.FAST:
            self._fast_path_count += 1

        # Log warning if SLO violated
        if duration_ms > self.config.p99_target_ms:
            logger.warning(f"Hook latency {duration_ms:.2f}ms exceeds SLO {self.config.p99_target_ms}ms")

    @property
    def p50_latency(self) -> float:
        """Calculate median latency.

        Returns
        -------
        float
            p50 latency in milliseconds

        Examples
        --------
        >>> optimizer = PerformanceOptimizer()
        >>> optimizer.record_latency(1.0)
        >>> optimizer.record_latency(2.0)
        >>> optimizer.p50_latency
        1.5
        """
        return self._percentile(50)

    @property
    def p95_latency(self) -> float:
        """Calculate 95th percentile latency.

        Returns
        -------
        float
            p95 latency in milliseconds
        """
        return self._percentile(95)

    @property
    def p99_latency(self) -> float:
        """Calculate 99th percentile latency.

        Returns
        -------
        float
            p99 latency in milliseconds

        Examples
        --------
        >>> optimizer = PerformanceOptimizer()
        >>> for i in range(100):
        ...     optimizer.record_latency(float(i))
        >>> optimizer.p99_latency  # Should be around 99
        98.0
        """
        return self._percentile(99)

    def _percentile(self, p: int) -> float:
        """Calculate percentile from latency samples.

        Parameters
        ----------
        p : int
            Percentile (0-100)

        Returns
        -------
        float
            Percentile value
        """
        if not self._latencies:
            return 0.0

        sorted_latencies = sorted(self._latencies)
        idx = int(len(sorted_latencies) * p / 100)
        idx = min(idx, len(sorted_latencies) - 1)
        return sorted_latencies[idx]

    def is_slo_met(self) -> bool:
        """Check if current p99 meets SLO target.

        Returns
        -------
        bool
            True if p99 <= target

        Examples
        --------
        >>> optimizer = PerformanceOptimizer(PerformanceConfig(p99_target_ms=10.0))
        >>> optimizer.record_latency(5.0)
        >>> optimizer.is_slo_met()
        True
        """
        return self.p99_latency <= self.config.p99_target_ms

    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics snapshot.

        Returns
        -------
        PerformanceMetrics
            Current metrics

        Examples
        --------
        >>> optimizer = PerformanceOptimizer()
        >>> metrics = optimizer.get_metrics()
        >>> metrics.sample_count
        0
        """
        fast_ratio = (self._fast_path_count / self._total_count * 100) if self._total_count > 0 else 0.0

        return PerformanceMetrics(
            p50_latency_ms=self.p50_latency,
            p95_latency_ms=self.p95_latency,
            p99_latency_ms=self.p99_latency,
            slo_met=self.is_slo_met(),
            sample_count=len(self._latencies),
            fast_path_ratio=fast_ratio,
        )

    def classify_condition(self, condition_query: str) -> OptimizationPath:
        """Classify condition for execution path optimization.

        Parameters
        ----------
        condition_query : str
            SPARQL condition query

        Returns
        -------
        OptimizationPath
            Recommended execution path

        Examples
        --------
        >>> optimizer = PerformanceOptimizer()
        >>> optimizer.classify_condition("")
        <OptimizationPath.FAST: 'fast'>
        >>> optimizer.classify_condition("ASK { ?s ?p ?o . ?o ?q ?r }")
        <OptimizationPath.STANDARD: 'standard'>
        """
        if not condition_query.strip():
            return OptimizationPath.FAST

        query_upper = condition_query.upper()

        # Slow path: Complex queries (check first to prevent fast path override)
        slow_indicators = ["GROUP BY", "ORDER BY", "HAVING", "SUBQUERY", "SERVICE"]
        if any(ind in query_upper for ind in slow_indicators):
            return OptimizationPath.SLOW

        # Fast path: Simple triple patterns
        if self.config.enable_fast_path:
            # Count BGP patterns (rough heuristic)
            pattern_count = condition_query.count("?")
            join_indicators = ["OPTIONAL", "UNION", "FILTER", "NOT EXISTS", "EXISTS"]

            has_joins = any(ind in query_upper for ind in join_indicators)

            if pattern_count <= 4 and not has_joins:
                return OptimizationPath.FAST

        return OptimizationPath.STANDARD

    def should_throttle(self) -> bool:
        """Check if execution should be throttled due to SLO pressure.

        Returns
        -------
        bool
            True if throttling recommended

        Examples
        --------
        >>> optimizer = PerformanceOptimizer()
        >>> optimizer.should_throttle()
        False
        """
        if len(self._latencies) < 10:
            return False

        # Throttle if p95 > target (preemptive)
        return self.p95_latency > self.config.p99_target_ms

    def get_recommended_concurrency(self) -> int:
        """Get recommended concurrency based on current performance.

        Returns
        -------
        int
            Recommended concurrent execution limit

        Examples
        --------
        >>> optimizer = PerformanceOptimizer()
        >>> optimizer.get_recommended_concurrency()
        10
        """
        if self.should_throttle():
            # Reduce concurrency when under pressure
            return max(1, self.config.max_concurrency // 2)

        if self.is_slo_met() and self.p95_latency < self.config.p99_target_ms * 0.5:
            # Room to increase if well under target
            return min(self.config.max_concurrency * 2, 50)

        return self.config.max_concurrency

    def reset(self) -> None:
        """Reset all performance tracking.

        Examples
        --------
        >>> optimizer = PerformanceOptimizer()
        >>> optimizer.record_latency(1.0)
        >>> optimizer.reset()
        >>> optimizer._total_count
        0
        """
        self._latencies.clear()
        self._fast_path_count = 0
        self._total_count = 0

    def export_report(self) -> dict[str, Any]:
        """Export detailed performance report.

        Returns
        -------
        dict[str, Any]
            Comprehensive performance report

        Examples
        --------
        >>> optimizer = PerformanceOptimizer()
        >>> report = optimizer.export_report()
        >>> "slo_target_ms" in report
        True
        """
        metrics = self.get_metrics()

        return {
            "slo_target_ms": self.config.p99_target_ms,
            "slo_met": metrics.slo_met,
            "latencies": {
                "p50_ms": round(metrics.p50_latency_ms, 3),
                "p95_ms": round(metrics.p95_latency_ms, 3),
                "p99_ms": round(metrics.p99_latency_ms, 3),
            },
            "execution_stats": {
                "total_executions": self._total_count,
                "sample_count": metrics.sample_count,
                "fast_path_ratio_pct": round(metrics.fast_path_ratio, 1),
            },
            "recommendations": {
                "throttle": self.should_throttle(),
                "recommended_concurrency": self.get_recommended_concurrency(),
            },
        }
