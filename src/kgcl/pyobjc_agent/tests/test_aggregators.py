"""
Unit tests for feature aggregators.
"""

import builtins
import contextlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from ..aggregators import (
    AggregatedFeature,
    BrowserHistoryAggregator,
    CalendarAggregator,
    FrontmostAppAggregator,
    TimeWindow,
    aggregate_jsonl_file,
)


class TestTimeWindow(unittest.TestCase):
    """Test cases for TimeWindow."""

    def test_creation(self):
        """Test time window creation."""
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 13, 0, 0)

        window = TimeWindow(start_time=start, end_time=end, window_type="hour")

        self.assertEqual(window.start_time, start)
        self.assertEqual(window.end_time, end)
        self.assertEqual(window.window_type, "hour")

    def test_duration_seconds(self):
        """Test duration calculation."""
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 13, 0, 0)

        window = TimeWindow(start_time=start, end_time=end)

        self.assertEqual(window.duration_seconds, 3600.0)

    def test_contains(self):
        """Test timestamp containment check."""
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 13, 0, 0)

        window = TimeWindow(start_time=start, end_time=end)

        # Within window
        self.assertTrue(window.contains(datetime(2024, 1, 1, 12, 30, 0)))

        # At boundaries
        self.assertTrue(window.contains(start))
        self.assertFalse(window.contains(end))

        # Outside window
        self.assertFalse(window.contains(datetime(2024, 1, 1, 11, 0, 0)))
        self.assertFalse(window.contains(datetime(2024, 1, 1, 14, 0, 0)))


class TestAggregatedFeature(unittest.TestCase):
    """Test cases for AggregatedFeature."""

    def test_creation(self):
        """Test feature creation."""
        window = TimeWindow(start_time=datetime(2024, 1, 1, 12, 0, 0), end_time=datetime(2024, 1, 1, 13, 0, 0))

        feature = AggregatedFeature(
            feature_name="test_feature", time_window=window, value=42, unit="count", metadata={"source": "test"}
        )

        self.assertEqual(feature.feature_name, "test_feature")
        self.assertEqual(feature.value, 42)
        self.assertEqual(feature.unit, "count")

    def test_to_dict(self):
        """Test conversion to dictionary."""
        window = TimeWindow(start_time=datetime(2024, 1, 1, 12, 0, 0), end_time=datetime(2024, 1, 1, 13, 0, 0))

        feature = AggregatedFeature(feature_name="test", time_window=window, value=100)

        result = feature.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["feature"], "test")
        self.assertEqual(result["value"], 100)
        self.assertIn("time_window", result)


class TestFrontmostAppAggregator(unittest.TestCase):
    """Test cases for FrontmostAppAggregator."""

    def setUp(self):
        """Set up test fixtures."""
        self.aggregator = FrontmostAppAggregator(window_size_hours=1.0)

    def test_aggregate_empty(self):
        """Test aggregation with no events."""
        features = self.aggregator.aggregate([])
        self.assertEqual(len(features), 0)

    def test_aggregate_single_window(self):
        """Test aggregation within single window."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)

        events = [
            {
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "data": {
                    "app_name": "Safari" if i % 2 == 0 else "Chrome",
                    "bundle_id": f"com.test.app{i % 2}",
                    "is_switch": i > 0,
                },
            }
            for i in range(10)
        ]

        features = self.aggregator.aggregate(events)

        # Should have multiple features
        self.assertGreater(len(features), 0)

        # Check for expected feature types
        feature_names = [f.feature_name for f in features]
        self.assertIn("app_usage_total_minutes", feature_names)
        self.assertIn("app_switch_count", feature_names)
        self.assertIn("unique_apps_used", feature_names)

    def test_calculate_app_times(self):
        """Test app time calculation."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)

        events = [
            {"timestamp": base_time.isoformat(), "data": {"app_name": "Safari"}},
            {"timestamp": (base_time + timedelta(minutes=5)).isoformat(), "data": {"app_name": "Chrome"}},
            {"timestamp": (base_time + timedelta(minutes=10)).isoformat(), "data": {"app_name": "Safari"}},
        ]

        app_times = self.aggregator._calculate_app_times(events)

        # Safari: 5 minutes first, then rest of time
        # Chrome: 5 minutes
        self.assertIn("Safari", app_times)
        self.assertIn("Chrome", app_times)


class TestBrowserHistoryAggregator(unittest.TestCase):
    """Test cases for BrowserHistoryAggregator."""

    def setUp(self):
        """Set up test fixtures."""
        self.aggregator = BrowserHistoryAggregator(window_size_hours=1.0)

    def test_aggregate_browser_data(self):
        """Test browser history aggregation."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)

        events = [
            {
                "timestamp": base_time.isoformat(),
                "data": {
                    "total_visits": 10,
                    "new_visits_count": 5,
                    "browsers": {"safari": 6, "chrome": 4},
                    "top_domains": [{"domain": "google.com", "count": 5}, {"domain": "github.com", "count": 3}],
                },
            }
        ]

        features = self.aggregator.aggregate(events)

        self.assertGreater(len(features), 0)

        feature_names = [f.feature_name for f in features]
        self.assertIn("browser_total_visits", feature_names)
        self.assertIn("browser_new_visits", feature_names)
        self.assertIn("browser_unique_domains", feature_names)


class TestCalendarAggregator(unittest.TestCase):
    """Test cases for CalendarAggregator."""

    def setUp(self):
        """Set up test fixtures."""
        self.aggregator = CalendarAggregator(window_size_hours=1.0)

    def test_aggregate_calendar_data(self):
        """Test calendar event aggregation."""
        base_time = datetime(2024, 1, 1, 12, 0, 0)

        events = [
            {
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "data": {"upcoming_count": 3, "events_today": 5, "is_busy": i % 2 == 0, "new_event_started": i == 5},
            }
            for i in range(10)
        ]

        features = self.aggregator.aggregate(events)

        self.assertGreater(len(features), 0)

        feature_names = [f.feature_name for f in features]
        self.assertIn("calendar_busy_samples", feature_names)
        self.assertIn("calendar_avg_upcoming_events", feature_names)
        self.assertIn("calendar_new_events_started", feature_names)


class TestAggregateJsonlFile(unittest.TestCase):
    """Test cases for JSONL file aggregation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl")
        self.temp_path = self.temp_file.name

        # Write test data
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        for i in range(5):
            event = {
                "collector_name": "frontmost_app",
                "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
                "data": {"app_name": "TestApp", "bundle_id": "com.test.app", "is_switch": i > 0},
                "sequence_number": i,
            }
            self.temp_file.write(json.dumps(event) + "\n")

        self.temp_file.close()

    def tearDown(self):
        """Clean up test fixtures."""
        with contextlib.suppress(builtins.BaseException):
            Path(self.temp_path).unlink()

    def test_aggregate_file(self):
        """Test aggregating from JSONL file."""
        aggregator = FrontmostAppAggregator()

        features = aggregate_jsonl_file(self.temp_path, aggregator)

        self.assertGreater(len(features), 0)

    def test_aggregate_file_with_output(self):
        """Test aggregating with output file."""
        output_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        output_path = output_file.name
        output_file.close()

        try:
            aggregator = FrontmostAppAggregator()

            features = aggregate_jsonl_file(self.temp_path, aggregator, output_path=output_path)

            # Verify output file created
            self.assertTrue(Path(output_path).exists())

            # Verify content
            with open(output_path) as f:
                data = json.load(f)

            self.assertIn("features", data)
            self.assertIn("event_count", data)

        finally:
            with contextlib.suppress(builtins.BaseException):
                Path(output_path).unlink()


if __name__ == "__main__":
    unittest.main()
