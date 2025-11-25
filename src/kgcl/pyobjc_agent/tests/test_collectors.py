"""
Unit tests for collectors.
"""

import json
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

from ..collectors.base import BaseCollector, CollectedEvent, CollectorConfig, CollectorStatus


class MockCollector(BaseCollector):
    """Mock collector for testing."""

    def __init__(self, config: CollectorConfig):
        super().__init__(config)
        self.collect_count = 0

    def collect_event(self):
        """Collect a test event."""
        self.collect_count += 1
        return {"test": "data", "count": self.collect_count}

    def validate_configuration(self):
        """Validate configuration."""
        return True


class TestBaseCollector(unittest.TestCase):
    """Test cases for BaseCollector."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl")
        self.temp_path = self.temp_file.name
        self.temp_file.close()

        self.config = CollectorConfig(
            name="test_collector",
            interval_seconds=0.1,
            batch_size=5,
            batch_timeout_seconds=1.0,
            output_path=self.temp_path,
        )

        self.collector = MockCollector(self.config)

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            Path(self.temp_path).unlink()
        except:
            pass

    def test_initialization(self):
        """Test collector initialization."""
        self.assertEqual(self.collector.config.name, "test_collector")
        self.assertEqual(self.collector.status, CollectorStatus.STOPPED)
        self.assertEqual(len(self.collector._event_buffer), 0)

    def test_validate_configuration(self):
        """Test configuration validation."""
        result = self.collector.validate_configuration()
        self.assertTrue(result)

    def test_start_stop(self):
        """Test starting and stopping collector."""
        self.collector.start()
        self.assertEqual(self.collector.status, CollectorStatus.RUNNING)

        time.sleep(0.5)  # Let it collect some events

        self.collector.stop()
        self.assertEqual(self.collector.status, CollectorStatus.STOPPED)
        self.assertGreater(self.collector.collect_count, 0)

    def test_pause_resume(self):
        """Test pausing and resuming collector."""
        self.collector.start()
        initial_count = self.collector.collect_count

        self.collector.pause()
        self.assertEqual(self.collector.status, CollectorStatus.PAUSED)

        time.sleep(0.3)
        paused_count = self.collector.collect_count

        # Should not collect while paused
        self.assertEqual(paused_count, initial_count)

        self.collector.resume()
        self.assertEqual(self.collector.status, CollectorStatus.RUNNING)

        time.sleep(0.3)
        resumed_count = self.collector.collect_count

        # Should collect after resume
        self.assertGreater(resumed_count, paused_count)

        self.collector.stop()

    def test_event_buffering(self):
        """Test event buffering."""
        event1 = CollectedEvent(
            collector_name="test",
            timestamp=datetime.utcnow().isoformat(),
            data={"test": 1},
            sequence_number=1,
        )

        event2 = CollectedEvent(
            collector_name="test",
            timestamp=datetime.utcnow().isoformat(),
            data={"test": 2},
            sequence_number=2,
        )

        self.collector._add_to_buffer(event1)
        self.collector._add_to_buffer(event2)

        self.assertEqual(len(self.collector._event_buffer), 2)

    def test_flush_buffer(self):
        """Test buffer flushing."""
        self.collector._open_output_file()

        # Add events to buffer
        for i in range(5):
            event = CollectedEvent(
                collector_name="test",
                timestamp=datetime.utcnow().isoformat(),
                data={"value": i},
                sequence_number=i,
            )
            self.collector._event_buffer.append(event)

        # Flush
        self.collector._flush_buffer(force=True)

        # Verify buffer cleared
        self.assertEqual(len(self.collector._event_buffer), 0)

        # Verify events written
        self.collector._close_output_file()

        with open(self.temp_path) as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 5)

        # Verify JSONL format
        for line in lines:
            data = json.loads(line)
            self.assertIn("collector_name", data)
            self.assertIn("data", data)

    def test_get_stats(self):
        """Test getting collector statistics."""
        stats = self.collector.get_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn("status", stats)
        self.assertIn("events_collected", stats)
        self.assertIn("buffer_size", stats)

    def test_collected_event_to_jsonl(self):
        """Test CollectedEvent to JSONL conversion."""
        event = CollectedEvent(
            collector_name="test",
            timestamp="2024-01-01T00:00:00",
            data={"key": "value"},
            metadata={"source": "test"},
            sequence_number=1,
        )

        jsonl = event.to_jsonl()

        # Verify it's valid JSON
        parsed = json.loads(jsonl)
        self.assertEqual(parsed["collector_name"], "test")
        self.assertEqual(parsed["data"]["key"], "value")


class TestCollectorConfig(unittest.TestCase):
    """Test cases for CollectorConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CollectorConfig(name="test")

        self.assertEqual(config.interval_seconds, 60.0)
        self.assertEqual(config.batch_size, 100)
        self.assertEqual(config.batch_timeout_seconds, 300.0)
        self.assertIsNone(config.output_path)
        self.assertEqual(config.buffer_size, 10000)
        self.assertFalse(config.enable_compression)
        self.assertTrue(config.retry_on_error)
        self.assertEqual(config.max_retries, 3)

    def test_custom_values(self):
        """Test custom configuration values."""
        config = CollectorConfig(
            name="test",
            interval_seconds=30.0,
            batch_size=50,
            output_path="/tmp/test.jsonl",
            retry_on_error=False,
        )

        self.assertEqual(config.interval_seconds, 30.0)
        self.assertEqual(config.batch_size, 50)
        self.assertEqual(config.output_path, "/tmp/test.jsonl")
        self.assertFalse(config.retry_on_error)


class TestCollectorIntegration(unittest.TestCase):
    """Integration tests for collectors."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl")
        self.temp_path = self.temp_file.name
        self.temp_file.close()

    def tearDown(self):
        """Clean up test fixtures."""
        try:
            Path(self.temp_path).unlink()
        except:
            pass

    def test_full_collection_cycle(self):
        """Test full collection, buffering, and writing cycle."""
        config = CollectorConfig(
            name="integration_test",
            interval_seconds=0.1,
            batch_size=3,
            batch_timeout_seconds=0.5,
            output_path=self.temp_path,
        )

        collector = MockCollector(config)

        # Start collector
        collector.start()

        # Let it run and collect events
        time.sleep(1.0)

        # Stop collector
        collector.stop()

        # Verify events were written
        with open(self.temp_path) as f:
            lines = f.readlines()

        # Should have collected multiple events
        self.assertGreater(len(lines), 0)

        # Verify all lines are valid JSON
        for line in lines:
            data = json.loads(line)
            self.assertIn("collector_name", data)
            self.assertEqual(data["collector_name"], "integration_test")

    def test_error_handling(self):
        """Test error handling in collection."""

        class FailingCollector(BaseCollector):
            def __init__(self, config):
                super().__init__(config)
                self.attempts = 0

            def collect_event(self):
                self.attempts += 1
                if self.attempts < 3:
                    raise RuntimeError("Test error")
                return {"recovered": True}

            def validate_configuration(self):
                return True

        config = CollectorConfig(
            name="failing_test",
            interval_seconds=0.1,
            batch_size=10,
            output_path=self.temp_path,
            retry_on_error=True,
            max_retries=5,
        )

        collector = FailingCollector(config)
        collector.start()

        time.sleep(1.0)

        collector.stop()

        # Should have retried and eventually recovered
        self.assertGreater(collector.attempts, 1)
        self.assertNotEqual(collector.status, CollectorStatus.ERROR)


if __name__ == "__main__":
    unittest.main()
