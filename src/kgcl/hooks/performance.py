"""
Performance Optimization for Hook Conditions & Execution.

Tracks latencies, memory usage, percentile analysis, and SLO compliance.
Ported from UNRDF performance-optimizer.mjs.
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PerformanceMetrics:
    """Metrics for a single operation execution."""

    operation: str
    latency_ms: float
    memory_delta_bytes: int = 0
    success: bool = True
    timestamp: datetime = field(default_factory=datetime.utcnow)
    p99_target_ms: float = 100.0

    @property
    def meets_slo(self) -> bool:
        """Check if operation meets SLO target."""
        return self.latency_ms <= self.p99_target_ms

    @property
    def slo_violation_ratio(self) -> float:
        """How much operation exceeds SLO (0.0 = meets, >1.0 = severe violation)."""
        if self.latency_ms <= self.p99_target_ms:
            return 0.0
        return self.latency_ms / self.p99_target_ms


class PerformanceOptimizer:
    """Optimize performance of hook conditions and execution.

    Tracks:
    - Operation latencies (per-operation basis)
    - Memory usage deltas
    - Percentile analysis (p50, p99, p999)
    - SLO compliance
    - Success rates
    """

    def __init__(self, sample_size: int = 100):
        """Initialize optimizer.

        Parameters
        ----------
        sample_size : int
            Number of samples to keep for trend analysis
        """
        self.samples: dict[str, list[float]] = {}
        self.sample_size = sample_size
        self.metrics: dict[str, list[PerformanceMetrics]] = {}

    def record_metric(self, metric: PerformanceMetrics) -> None:
        """Record a performance metric.

        Parameters
        ----------
        metric : PerformanceMetrics
            PerformanceMetrics to record
        """
        # Record latency sample
        if metric.operation not in self.samples:
            self.samples[metric.operation] = []
        self.samples[metric.operation].append(metric.latency_ms)

        # Keep only last N samples
        if len(self.samples[metric.operation]) > self.sample_size:
            self.samples[metric.operation].pop(0)

        # Record full metrics for detailed analysis
        if metric.operation not in self.metrics:
            self.metrics[metric.operation] = []
        self.metrics[metric.operation].append(metric)
        if len(self.metrics[metric.operation]) > self.sample_size:
            self.metrics[metric.operation].pop(0)

    def record_latency(self, operation: str, latency_ms: float) -> None:
        """Record operation latency (convenience method).

        Parameters
        ----------
        operation : str
            Operation name
        latency_ms : float
            Latency in milliseconds
        """
        metric = PerformanceMetrics(operation=operation, latency_ms=latency_ms)
        self.record_metric(metric)

    def get_percentile(self, operation: str, percentile: float = 0.99) -> float | None:
        """Get percentile latency for operation.

        Parameters
        ----------
        operation : str
            Operation name
        percentile : float
            Percentile (0.0-1.0)

        Returns
        -------
        Optional[float]
            Latency at percentile or None if insufficient data
        """
        if operation not in self.samples or not self.samples[operation]:
            return None

        sorted_samples = sorted(self.samples[operation])
        # Use proper percentile calculation (round up)
        idx = int(len(sorted_samples) * percentile)
        # Clamp to valid range
        idx = min(max(0, idx), len(sorted_samples) - 1)
        return sorted_samples[idx]

    def get_stats(self, operation: str) -> dict | None:
        """Get comprehensive statistics for operation.

        Parameters
        ----------
        operation : str
            Operation name

        Returns
        -------
        Optional[Dict]
            Dict with p50, p99, p999, mean, min, max, or None
        """
        if operation not in self.samples or not self.samples[operation]:
            return None

        samples = self.samples[operation]
        return {
            "operation": operation,
            "count": len(samples),
            "min": min(samples),
            "max": max(samples),
            "mean": statistics.mean(samples),
            "median": statistics.median(samples),
            "p50": self.get_percentile(operation, 0.50),
            "p99": self.get_percentile(operation, 0.99),
            "p999": self.get_percentile(operation, 0.999),
            "stdev": statistics.stdev(samples) if len(samples) > 1 else 0.0,
        }

    def get_slo_status(self, operation: str, target_ms: float) -> dict | None:
        """Get SLO compliance status.

        Parameters
        ----------
        operation : str
            Operation name
        target_ms : float
            SLO target in milliseconds

        Returns
        -------
        Optional[Dict]
            Dict with compliance info or None
        """
        if operation not in self.metrics or not self.metrics[operation]:
            return None

        metrics = self.metrics[operation]
        compliant = sum(1 for m in metrics if m.latency_ms <= target_ms)
        total = len(metrics)

        return {
            "operation": operation,
            "target_ms": target_ms,
            "compliant_count": compliant,
            "total_count": total,
            "compliance_rate": compliant / total if total > 0 else 0.0,
            "success_rate": sum(1 for m in metrics if m.success) / total if total > 0 else 0.0,
        }

    def get_all_operations(self) -> list[str]:
        """Get all tracked operations."""
        return list(set(self.samples.keys()) | set(self.metrics.keys()))
