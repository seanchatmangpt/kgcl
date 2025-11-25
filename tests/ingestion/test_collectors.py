"""Tests for event collectors."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from kgcl.ingestion.collectors.base import BaseCollector, CollectorState
from kgcl.ingestion.collectors.batch import BatchCollector
from kgcl.ingestion.config import CollectorConfig
from kgcl.ingestion.models import AppEvent, BrowserVisit


class TestCollectorState:
    """Tests for CollectorState enum."""

    def test_state_values(self):
        """Test collector state values."""
        assert CollectorState.INITIALIZED.value == "initialized"
        assert CollectorState.RUNNING.value == "running"
        assert CollectorState.STOPPED.value == "stopped"


class TestBatchCollector:
    """Tests for BatchCollector."""

    def test_initialization(self):
        """Test collector initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CollectorConfig(output_directory=Path(tmpdir))
            collector = BatchCollector(config)

            assert collector.state == CollectorState.INITIALIZED
            assert collector.batch_size == 100
            assert len(collector._buffer) == 0

    def test_add_single_event(self):
        """Test adding single event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CollectorConfig(
                output_directory=Path(tmpdir),
                batch_size=10,
            )
            collector = BatchCollector(config)

            event = AppEvent(
                event_id="test_001",
                timestamp=datetime.now(timezone.utc),
                app_name="com.apple.Safari",
            )

            collector.add_event(event)

            assert len(collector._buffer) == 1
            assert collector._event_count == 1

    def test_add_multiple_events(self):
        """Test adding multiple events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CollectorConfig(
                output_directory=Path(tmpdir),
                batch_size=10,
            )
            collector = BatchCollector(config)

            events = [
                AppEvent(
                    event_id=f"test_{i:03d}",
                    timestamp=datetime.now(timezone.utc),
                    app_name="com.apple.Safari",
                )
                for i in range(5)
            ]

            collector.add_events(events)

            assert len(collector._buffer) == 5
            assert collector._event_count == 5

    def test_auto_flush_on_batch_size(self):
        """Test automatic flush when batch size reached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CollectorConfig(
                output_directory=Path(tmpdir),
                batch_size=3,
            )
            collector = BatchCollector(config)
            collector.start()

            # Add events up to batch size
            for i in range(3):
                event = AppEvent(
                    event_id=f"test_{i:03d}",
                    timestamp=datetime.now(timezone.utc),
                    app_name="com.apple.Safari",
                )
                collector.add_event(event)

            # Buffer should be empty after auto-flush
            assert len(collector._buffer) == 0

    def test_manual_flush(self):
        """Test manual flush."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CollectorConfig(
                output_directory=Path(tmpdir),
                batch_size=100,
            )
            collector = BatchCollector(config)
            collector.start()

            # Add some events
            events = [
                AppEvent(
                    event_id=f"test_{i:03d}",
                    timestamp=datetime.now(timezone.utc),
                    app_name="com.apple.Safari",
                )
                for i in range(5)
            ]
            collector.add_events(events)

            # Flush manually
            flushed = collector.flush()

            assert flushed == 5
            assert len(collector._buffer) == 0

    def test_flush_writes_jsonl(self):
        """Test that flush writes JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CollectorConfig(
                output_directory=Path(tmpdir),
                batch_size=100,
            )
            collector = BatchCollector(config)
            collector.start()

            event = AppEvent(
                event_id="test_001",
                timestamp=datetime.now(timezone.utc),
                app_name="com.apple.Safari",
            )
            collector.add_event(event)
            collector.flush()

            # Check JSONL file exists
            output_files = list(Path(tmpdir).glob("*.jsonl"))
            assert len(output_files) == 1

            # Verify content
            with output_files[0].open() as f:
                lines = f.readlines()
                assert len(lines) >= 2  # Batch metadata + event

    def test_recovery_from_corrupted_file(self):
        """Test recovery from corrupted JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CollectorConfig(
                output_directory=Path(tmpdir),
                enable_recovery=True,
            )
            collector = BatchCollector(config)

            # Create corrupted JSONL file
            corrupt_file = Path(tmpdir) / "corrupted.jsonl"
            with corrupt_file.open("w") as f:
                # Valid line
                valid_event = {
                    "type": "event",
                    "batch_id": "batch_001",
                    "event_type": "AppEvent",
                    "data": {
                        "event_id": "test_001",
                        "timestamp": "2024-11-24T10:00:00",
                        "app_name": "com.apple.Safari",
                        "schema_version": "1.0.0",
                    },
                }
                f.write(json.dumps(valid_event) + "\n")

                # Corrupted line
                f.write("{ invalid json }\n")

                # Another valid line
                valid_event2 = {
                    "type": "event",
                    "batch_id": "batch_001",
                    "event_type": "BrowserVisit",
                    "data": {
                        "event_id": "test_002",
                        "timestamp": "2024-11-24T10:00:00",
                        "url": "https://example.com",
                        "domain": "example.com",
                        "browser_name": "Safari",
                        "schema_version": "1.0.0",
                    },
                }
                f.write(json.dumps(valid_event2) + "\n")

            # Attempt recovery
            recovered, corrupted = collector.recover_from_file(corrupt_file)

            assert recovered == 2
            assert corrupted == 1
            assert len(collector._buffer) == 2

    def test_start_stop_lifecycle(self):
        """Test collector lifecycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CollectorConfig(output_directory=Path(tmpdir))
            collector = BatchCollector(config)

            # Start
            collector.start()
            assert collector.state == CollectorState.RUNNING

            # Add event
            event = AppEvent(
                event_id="test_001",
                timestamp=datetime.now(timezone.utc),
                app_name="com.apple.Safari",
            )
            collector.add_event(event)

            # Stop
            collector.stop()
            assert collector.state == CollectorState.STOPPED
            assert len(collector._buffer) == 0  # Flushed on stop

    def test_get_stats(self):
        """Test getting collector statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CollectorConfig(output_directory=Path(tmpdir))
            collector = BatchCollector(config)

            stats = collector.get_stats()

            assert "state" in stats
            assert "event_count" in stats
            assert "buffer_size" in stats
            assert stats["batch_size"] == 100

    def test_error_handling(self):
        """Test error handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CollectorConfig(output_directory=Path(tmpdir))
            collector = BatchCollector(config)

            error_count = 0

            def error_handler(error, context):
                nonlocal error_count
                error_count += 1

            collector.register_error_handler(error_handler)

            # Trigger error with invalid source function
            collector.source_fn = lambda: 1 / 0  # noqa: RUF015

            result = collector.collect()

            assert result == []
            assert error_count == 1
            assert collector.state == CollectorState.ERROR
