"""
Observability for hook system monitoring.

This module provides health checking, metrics collection, and system
monitoring for the hook execution framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging
import statistics


@dataclass
class HealthCheck:
    """
    System health status.

    Parameters
    ----------
    is_healthy : bool
        Overall system health status
    metrics : Dict[str, float]
        Current metric values
    warnings : List[str]
        Warning messages
    errors : List[str]
        Error messages
    timestamp : datetime
        Time of health check
    """

    is_healthy: bool
    metrics: Dict[str, float]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class Observability:
    """
    Monitor hook system health and performance.

    Collects metrics, detects anomalies, and provides health status reporting.
    """

    def __init__(self, max_history: int = 1000) -> None:
        """
        Initialize observability system.

        Parameters
        ----------
        max_history : int
            Maximum number of metric values to retain
        """
        self.logger = logging.getLogger("kgcl.hooks")
        self.metrics: Dict[str, List[float]] = {}
        self.max_history = max_history
        self.thresholds: Dict[str, Dict[str, float]] = {}
        self._health_checks: List[HealthCheck] = []

    def record_metric(self, name: str, value: float) -> None:
        """
        Record metric value.

        Parameters
        ----------
        name : str
            Metric name
        value : float
            Metric value
        """
        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append(value)

        # Keep only last max_history values
        if len(self.metrics[name]) > self.max_history:
            self.metrics[name].pop(0)

        self.logger.debug(f"Recorded metric {name}={value}")

    def set_threshold(
        self, name: str, warning: Optional[float] = None, error: Optional[float] = None
    ) -> None:
        """
        Set thresholds for metric.

        Parameters
        ----------
        name : str
            Metric name
        warning : Optional[float]
            Warning threshold
        error : Optional[float]
            Error threshold
        """
        self.thresholds[name] = {}
        if warning is not None:
            self.thresholds[name]["warning"] = warning
        if error is not None:
            self.thresholds[name]["error"] = error

    def get_health_status(self) -> HealthCheck:
        """
        Get current system health.

        Returns
        -------
        HealthCheck
            Current health status with metrics and issues
        """
        warnings = []
        errors = []

        # Check metrics against thresholds
        for name, values in self.metrics.items():
            if not values:
                continue

            current = values[-1]

            # Check thresholds
            if name in self.thresholds:
                thresholds = self.thresholds[name]
                if "error" in thresholds and current > thresholds["error"]:
                    errors.append(
                        f"{name} is {current:.2f} (threshold: {thresholds['error']:.2f})"
                    )
                elif "warning" in thresholds and current > thresholds["warning"]:
                    warnings.append(
                        f"{name} is {current:.2f} (threshold: {thresholds['warning']:.2f})"
                    )

            # Check for anomalies (2x average)
            if len(values) >= 10:
                avg = statistics.mean(values)
                if current > avg * 2:
                    warnings.append(f"{name} is {current:.2f}, avg {avg:.2f}")

        health = HealthCheck(
            is_healthy=len(errors) == 0,
            metrics=self._compute_stats(),
            warnings=warnings,
            errors=errors,
            timestamp=datetime.utcnow(),
        )

        self._health_checks.append(health)
        if len(self._health_checks) > 100:
            self._health_checks.pop(0)

        return health

    def get_metric_stats(self, name: str) -> Optional[Dict[str, float]]:
        """
        Get statistics for a specific metric.

        Parameters
        ----------
        name : str
            Metric name

        Returns
        -------
        Optional[Dict[str, float]]
            Metric statistics or None if not found
        """
        if name not in self.metrics or not self.metrics[name]:
            return None

        values = self.metrics[name]
        return {
            "current": values[-1],
            "avg": statistics.mean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
            "stddev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "count": len(values),
        }

    def get_all_metrics(self) -> Dict[str, List[float]]:
        """
        Get all recorded metrics.

        Returns
        -------
        Dict[str, List[float]]
            Dictionary of metric names to value lists
        """
        return {name: values.copy() for name, values in self.metrics.items()}

    def clear_metrics(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()
        self._health_checks.clear()

    def get_health_history(self) -> List[HealthCheck]:
        """
        Get historical health checks.

        Returns
        -------
        List[HealthCheck]
            List of recent health checks
        """
        return self._health_checks.copy()

    def _compute_stats(self) -> Dict[str, float]:
        """
        Compute current statistics for all metrics.

        Returns
        -------
        Dict[str, float]
            Flattened statistics dictionary
        """
        stats = {}
        for name, values in self.metrics.items():
            if values:
                stats[f"{name}_current"] = values[-1]
                stats[f"{name}_avg"] = statistics.mean(values)
                stats[f"{name}_max"] = max(values)
                stats[f"{name}_min"] = min(values)
                if len(values) > 1:
                    stats[f"{name}_stddev"] = statistics.stdev(values)
        return stats

    def detect_anomalies(self, window: int = 10, threshold: float = 2.0) -> List[str]:
        """
        Detect anomalies in recent metrics.

        Parameters
        ----------
        window : int
            Number of recent values to analyze
        threshold : float
            Multiplier for standard deviation threshold

        Returns
        -------
        List[str]
            List of detected anomalies
        """
        anomalies = []

        for name, values in self.metrics.items():
            if len(values) < window:
                continue

            recent = values[-window:]
            if len(recent) < 2:
                continue

            mean = statistics.mean(recent[:-1])
            stddev = statistics.stdev(recent[:-1])
            current = recent[-1]

            # Check if current value is threshold * stddev away from mean
            if abs(current - mean) > threshold * stddev:
                anomalies.append(
                    f"{name}: {current:.2f} (mean: {mean:.2f}, stddev: {stddev:.2f})"
                )

        return anomalies

    def record_hook_execution(
        self, hook_id: str, duration_ms: float, success: bool
    ) -> None:
        """
        Record hook execution metrics.

        Parameters
        ----------
        hook_id : str
            Hook identifier
        duration_ms : float
            Execution duration in milliseconds
        success : bool
            Whether execution succeeded
        """
        self.record_metric(f"hook.{hook_id}.duration_ms", duration_ms)
        self.record_metric(f"hook.{hook_id}.success", 1.0 if success else 0.0)
        self.record_metric("hooks.total_executions", 1.0)
        if success:
            self.record_metric("hooks.total_successes", 1.0)
        else:
            self.record_metric("hooks.total_failures", 1.0)

    def get_hook_stats(self, hook_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific hook.

        Parameters
        ----------
        hook_id : str
            Hook identifier

        Returns
        -------
        Dict[str, Any]
            Hook statistics including execution count, success rate, avg duration
        """
        duration_key = f"hook.{hook_id}.duration_ms"
        success_key = f"hook.{hook_id}.success"

        stats = {}

        if duration_key in self.metrics and self.metrics[duration_key]:
            durations = self.metrics[duration_key]
            stats["executions"] = len(durations)
            stats["avg_duration_ms"] = statistics.mean(durations)
            stats["min_duration_ms"] = min(durations)
            stats["max_duration_ms"] = max(durations)

        if success_key in self.metrics and self.metrics[success_key]:
            successes = self.metrics[success_key]
            stats["success_rate"] = statistics.mean(successes)
            stats["total_successes"] = sum(successes)
            stats["total_failures"] = len(successes) - sum(successes)

        return stats
