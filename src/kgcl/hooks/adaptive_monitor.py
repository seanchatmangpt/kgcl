"""Adaptive Monitor - Dynamically adjust monitoring thresholds.

Automatically learns baseline behavior and adapts thresholds based on
observed metrics using statistical analysis.
"""

import logging
import statistics
from dataclasses import dataclass


@dataclass
class MetricThreshold:
    """Adaptive threshold for metric."""

    metric_name: str
    baseline: float
    variance: float
    current_threshold: float
    sample_count: int = 0


class AdaptiveMonitor:
    """Dynamically adjust monitoring thresholds based on observed behavior.

    Uses statistical analysis to establish baselines and detect anomalies:
    - Tracks rolling window of metric observations
    - Calculates mean and standard deviation
    - Sets threshold at mean + N * stddev
    - Adapts as system behavior changes
    """

    def __init__(self, window_size: int = 100, stddev_multiplier: float = 2.0, min_samples: int = 10):
        """Initialize adaptive monitor.

        Args:
            window_size: Number of samples to keep in rolling window
            stddev_multiplier: Number of standard deviations for threshold
            min_samples: Minimum samples before calculating thresholds
        """
        self.metrics: dict[str, list[float]] = {}
        self.thresholds: dict[str, MetricThreshold] = {}
        self.window_size = window_size
        self.stddev_multiplier = stddev_multiplier
        self.min_samples = min_samples
        self._logger = logging.getLogger(__name__)

    def observe_metric(self, name: str, value: float) -> None:
        """Observe metric value and update statistics.

        Args:
            name: Metric name
            value: Metric value
        """
        if not isinstance(value, (int, float)):
            raise ValueError(f"Metric value must be numeric, got {type(value)}")

        # Initialize metric if needed
        if name not in self.metrics:
            self.metrics[name] = []

        # Add value to rolling window
        self.metrics[name].append(value)

        # Trim to window size
        if len(self.metrics[name]) > self.window_size:
            self.metrics[name] = self.metrics[name][-self.window_size :]

        # Recalculate threshold
        self._recalculate_threshold(name)

    def _recalculate_threshold(self, name: str) -> None:
        """Recalculate adaptive threshold for metric.

        Args:
            name: Metric name
        """
        if name not in self.metrics:
            return

        values = self.metrics[name]

        # Need minimum samples for statistical significance
        if len(values) < self.min_samples:
            return

        # Calculate statistics
        mean = statistics.mean(values)

        # Calculate standard deviation (need at least 2 samples)
        stdev = statistics.stdev(values) if len(values) > 1 else 0

        # Threshold = mean + N * stddev
        # For very low variance, use percentage-based threshold
        if stdev > 0:
            threshold = mean + (self.stddev_multiplier * stdev)
        else:
            threshold = mean * 1.5  # 50% above mean if no variance

        # Update threshold
        self.thresholds[name] = MetricThreshold(
            metric_name=name, baseline=mean, variance=stdev, current_threshold=threshold, sample_count=len(values)
        )

        self._logger.debug(
            f"Updated threshold for {name}: baseline={mean:.2f}, stdev={stdev:.2f}, threshold={threshold:.2f}"
        )

    def is_anomaly(self, name: str, value: float) -> bool:
        """Check if value is anomalous based on adaptive threshold.

        Args:
            name: Metric name
            value: Value to check

        Returns
        -------
            True if value exceeds threshold
        """
        if name not in self.thresholds:
            # No threshold yet, not anomalous
            return False

        return value > self.thresholds[name].current_threshold

    def get_threshold(self, name: str) -> MetricThreshold | None:
        """Get current threshold for metric.

        Args:
            name: Metric name

        Returns
        -------
            MetricThreshold if available, None otherwise
        """
        return self.thresholds.get(name)

    def get_all_thresholds(self) -> dict[str, MetricThreshold]:
        """Get all current thresholds.

        Returns
        -------
            Dictionary mapping metric names to thresholds
        """
        return self.thresholds.copy()

    def get_metric_stats(self, name: str) -> dict | None:
        """Get statistics for a metric.

        Args:
            name: Metric name

        Returns
        -------
            Dictionary with statistics or None if metric not found
        """
        if name not in self.metrics or name not in self.thresholds:
            return None

        values = self.metrics[name]
        threshold = self.thresholds[name]

        return {
            "name": name,
            "sample_count": len(values),
            "baseline": threshold.baseline,
            "variance": threshold.variance,
            "threshold": threshold.current_threshold,
            "current_value": values[-1] if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }

    def reset_metric(self, name: str) -> bool:
        """Reset a metric's history and threshold.

        Args:
            name: Metric name

        Returns
        -------
            True if metric was found and reset
        """
        if name in self.metrics:
            del self.metrics[name]
        if name in self.thresholds:
            del self.thresholds[name]
        return name in self.metrics or name in self.thresholds

    def reset_all(self) -> None:
        """Reset all metrics and thresholds."""
        self.metrics.clear()
        self.thresholds.clear()

    def check_and_observe(self, name: str, value: float) -> bool:
        """Check if value is anomalous, then observe it.

        Convenience method that combines is_anomaly() and observe_metric().

        Args:
            name: Metric name
            value: Metric value

        Returns
        -------
            True if value was anomalous
        """
        is_anom = self.is_anomaly(name, value)
        self.observe_metric(name, value)
        return is_anom
