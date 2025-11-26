"""Tests for adaptive_monitor module."""

import pytest

from kgcl.hooks.adaptive_monitor import AdaptiveMonitor, MetricThreshold


class TestMetricThreshold:
    """Test MetricThreshold dataclass."""

    def test_create_threshold(self):
        """Test creating MetricThreshold."""
        threshold = MetricThreshold(
            metric_name="response_time", baseline=100.0, variance=10.0, current_threshold=120.0, sample_count=50
        )
        assert threshold.metric_name == "response_time"
        assert threshold.baseline == 100.0
        assert threshold.variance == 10.0
        assert threshold.current_threshold == 120.0
        assert threshold.sample_count == 50


class TestAdaptiveMonitor:
    """Test AdaptiveMonitor class."""

    def test_initialization(self):
        """Test monitor initialization."""
        monitor = AdaptiveMonitor()
        assert monitor.window_size == 100
        assert monitor.stddev_multiplier == 2.0
        assert monitor.min_samples == 10
        assert len(monitor.metrics) == 0
        assert len(monitor.thresholds) == 0

    def test_custom_initialization(self):
        """Test custom initialization."""
        monitor = AdaptiveMonitor(window_size=50, stddev_multiplier=3.0, min_samples=5)
        assert monitor.window_size == 50
        assert monitor.stddev_multiplier == 3.0
        assert monitor.min_samples == 5

    def test_observe_metric(self):
        """Test observing a metric."""
        monitor = AdaptiveMonitor()
        monitor.observe_metric("response_time", 100.0)
        assert "response_time" in monitor.metrics
        assert len(monitor.metrics["response_time"]) == 1
        assert monitor.metrics["response_time"][0] == 100.0

    def test_observe_multiple_values(self):
        """Test observing multiple values."""
        monitor = AdaptiveMonitor(min_samples=3)
        values = [100.0, 105.0, 95.0, 110.0, 90.0]

        for value in values:
            monitor.observe_metric("test_metric", value)

        assert len(monitor.metrics["test_metric"]) == 5
        assert monitor.metrics["test_metric"] == values

    def test_rolling_window(self):
        """Test that metrics respect window size."""
        monitor = AdaptiveMonitor(window_size=5)

        for i in range(10):
            monitor.observe_metric("test", float(i))

        # Should only keep last 5 values
        assert len(monitor.metrics["test"]) == 5
        assert monitor.metrics["test"] == [5.0, 6.0, 7.0, 8.0, 9.0]

    def test_threshold_calculation(self):
        """Test threshold calculation."""
        monitor = AdaptiveMonitor(min_samples=5, stddev_multiplier=2.0)

        # Add values with known statistics
        values = [100.0, 100.0, 100.0, 100.0, 100.0]
        for value in values:
            monitor.observe_metric("test", value)

        threshold = monitor.get_threshold("test")
        assert threshold is not None
        assert threshold.baseline == 100.0
        assert threshold.variance == 0.0
        # With zero variance, threshold = mean * 1.5
        assert threshold.current_threshold == 150.0

    def test_threshold_with_variance(self):
        """Test threshold calculation with variance."""
        monitor = AdaptiveMonitor(min_samples=5, stddev_multiplier=2.0)

        # Values: [90, 95, 100, 105, 110]
        # Mean = 100, StdDev ≈ 7.91
        # Threshold = 100 + 2*7.91 ≈ 115.82
        values = [90.0, 95.0, 100.0, 105.0, 110.0]
        for value in values:
            monitor.observe_metric("test", value)

        threshold = monitor.get_threshold("test")
        assert threshold is not None
        assert abs(threshold.baseline - 100.0) < 0.1
        assert threshold.variance > 0
        assert abs(threshold.current_threshold - 115.82) < 1.0

    def test_is_anomaly_no_threshold(self):
        """Test that is_anomaly returns False when no threshold exists."""
        monitor = AdaptiveMonitor()
        assert monitor.is_anomaly("unknown_metric", 1000.0) is False

    def test_is_anomaly_insufficient_samples(self):
        """Test that is_anomaly returns False with insufficient samples."""
        monitor = AdaptiveMonitor(min_samples=10)

        # Add only 5 samples
        for i in range(5):
            monitor.observe_metric("test", 100.0)

        # No threshold calculated yet
        assert monitor.is_anomaly("test", 200.0) is False

    def test_is_anomaly_normal_value(self):
        """Test normal value is not anomalous."""
        monitor = AdaptiveMonitor(min_samples=5)

        # Establish baseline around 100
        for _ in range(10):
            monitor.observe_metric("test", 100.0)

        # Value within threshold
        assert monitor.is_anomaly("test", 105.0) is False

    def test_is_anomaly_anomalous_value(self):
        """Test anomalous value detection."""
        monitor = AdaptiveMonitor(min_samples=5)

        # Establish baseline around 100
        for _ in range(10):
            monitor.observe_metric("test", 100.0)

        # Value way above threshold
        assert monitor.is_anomaly("test", 1000.0) is True

    def test_get_threshold_nonexistent(self):
        """Test getting threshold for nonexistent metric."""
        monitor = AdaptiveMonitor()
        assert monitor.get_threshold("nonexistent") is None

    def test_get_all_thresholds(self):
        """Test getting all thresholds."""
        monitor = AdaptiveMonitor(min_samples=3)

        # Create thresholds for multiple metrics
        for metric in ["metric1", "metric2", "metric3"]:
            for i in range(5):
                monitor.observe_metric(metric, 100.0 + i)

        thresholds = monitor.get_all_thresholds()
        assert len(thresholds) == 3
        assert "metric1" in thresholds
        assert "metric2" in thresholds
        assert "metric3" in thresholds

    def test_get_metric_stats(self):
        """Test getting metric statistics."""
        monitor = AdaptiveMonitor(min_samples=3)

        values = [90.0, 95.0, 100.0, 105.0, 110.0]
        for value in values:
            monitor.observe_metric("test", value)

        stats = monitor.get_metric_stats("test")
        assert stats is not None
        assert stats["name"] == "test"
        assert stats["sample_count"] == 5
        assert abs(stats["baseline"] - 100.0) < 0.1
        assert stats["current_value"] == 110.0
        assert stats["min"] == 90.0
        assert stats["max"] == 110.0

    def test_get_metric_stats_nonexistent(self):
        """Test getting stats for nonexistent metric."""
        monitor = AdaptiveMonitor()
        assert monitor.get_metric_stats("nonexistent") is None

    def test_reset_metric(self):
        """Test resetting a metric."""
        monitor = AdaptiveMonitor(min_samples=3)

        for i in range(5):
            monitor.observe_metric("test", 100.0 + i)

        assert "test" in monitor.metrics
        assert "test" in monitor.thresholds

        monitor.reset_metric("test")

        assert "test" not in monitor.metrics
        assert "test" not in monitor.thresholds

    def test_reset_all(self):
        """Test resetting all metrics."""
        monitor = AdaptiveMonitor(min_samples=3)

        for metric in ["metric1", "metric2", "metric3"]:
            for i in range(5):
                monitor.observe_metric(metric, 100.0 + i)

        assert len(monitor.metrics) == 3
        assert len(monitor.thresholds) == 3

        monitor.reset_all()

        assert len(monitor.metrics) == 0
        assert len(monitor.thresholds) == 0

    def test_check_and_observe(self):
        """Test combined check and observe."""
        monitor = AdaptiveMonitor(min_samples=3)

        # Establish baseline
        for _ in range(5):
            is_anom = monitor.check_and_observe("test", 100.0)
            assert is_anom is False

        # Add anomalous value
        is_anom = monitor.check_and_observe("test", 1000.0)
        assert is_anom is True

        # Value should be observed
        assert monitor.metrics["test"][-1] == 1000.0

    def test_invalid_metric_value(self):
        """Test that invalid metric value raises error."""
        monitor = AdaptiveMonitor()

        with pytest.raises(ValueError, match="must be numeric"):
            monitor.observe_metric("test", "invalid")  # type: ignore

    def test_adaptive_threshold_updates(self):
        """Test that thresholds adapt to changing behavior."""
        monitor = AdaptiveMonitor(min_samples=5)

        # Establish baseline around 100
        for _ in range(10):
            monitor.observe_metric("test", 100.0)

        threshold1 = monitor.get_threshold("test").current_threshold

        # Shift to higher values
        for _ in range(20):
            monitor.observe_metric("test", 200.0)

        threshold2 = monitor.get_threshold("test").current_threshold

        # Threshold should adapt upward
        assert threshold2 > threshold1
