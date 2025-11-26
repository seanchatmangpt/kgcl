"""
Consolidated Ingestion Tests.

80/20 consolidation: Essential ingestion behaviors.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from kgcl.ingestion.config import CollectorConfig, FeatureConfig, FilterConfig, IngestionConfig, RDFConfig
from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock, EventBatch
from kgcl.ingestion.service import IngestionService


class TestModels:
    """Event model validation."""

    def test_app_event_creation(self) -> None:
        """AppEvent creates with required fields."""
        event = AppEvent(event_id="app_001", timestamp=datetime.now(UTC), app_name="com.apple.Safari")
        assert event.event_id == "app_001"
        assert event.app_name == "com.apple.Safari"

    def test_browser_visit_creation(self) -> None:
        """BrowserVisit creates with URL and domain."""
        event = BrowserVisit(
            event_id="browser_001",
            timestamp=datetime.now(UTC),
            url="https://example.com/page",
            domain="example.com",
            browser_name="Safari",
        )
        assert event.domain == "example.com"

    def test_calendar_block_creation(self) -> None:
        """CalendarBlock creates with time range."""
        now = datetime.now(UTC)
        event = CalendarBlock(
            event_id="cal_001",
            timestamp=now,
            title="Meeting",
            start_time=now,
            end_time=now + timedelta(hours=1),
            calendar_name="Work",
        )
        assert event.title == "Meeting"

    def test_event_batch_aggregation(self) -> None:
        """EventBatch aggregates events with metadata."""
        now = datetime.now(UTC)
        events = [AppEvent(event_id=f"e_{i}", timestamp=now, app_name="App") for i in range(5)]
        batch = EventBatch(batch_id="batch_001", events=events)

        assert batch.event_count() == 5
        assert "AppEvent" in batch.events_by_type()


class TestConfig:
    """Configuration validation."""

    def test_default_config(self) -> None:
        """Default config has sensible values."""
        config = IngestionConfig.default()
        assert config.collector.batch_size > 0
        assert config.service.enable_hooks is True

    def test_config_yaml_roundtrip(self) -> None:
        """Config can be saved and loaded from YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig.default()
            path = Path(tmpdir) / "config.yaml"
            config.to_yaml(path)

            loaded = IngestionConfig.from_yaml(path)
            assert loaded.collector.batch_size == config.collector.batch_size


class TestService:
    """IngestionService behaviors."""

    def test_service_lifecycle(self) -> None:
        """Service starts and stops cleanly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir)))
            service = IngestionService(config)

            service.start()
            stats = service.get_stats()
            assert "total_events" in stats

            service.stop()

    def test_event_filtering(self) -> None:
        """Service filters events by configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir)),
                filter=FilterConfig(excluded_apps=["com.excluded.App"], min_duration_seconds=10),
            )
            service = IngestionService(config)
            service.start()

            # Excluded app
            result = service.ingest_event(
                AppEvent(event_id="excluded", timestamp=datetime.now(UTC), app_name="com.excluded.App")
            )
            assert result["status"] == "filtered"

            # Too short
            result = service.ingest_event(
                AppEvent(event_id="short", timestamp=datetime.now(UTC), app_name="com.ok.App", duration_seconds=5.0)
            )
            assert result["status"] == "filtered"

            service.stop()

    def test_hook_registration(self) -> None:
        """Service accepts pre and post hooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir)))
            service = IngestionService(config)

            pre_calls: list[int] = []
            post_calls: list[int] = []

            service.register_pre_hook("pre", lambda e: pre_calls.append(len(e)))
            service.register_post_hook("post", lambda e: post_calls.append(len(e)))
            service.start()

            service.ingest_event(AppEvent(event_id="hook_test", timestamp=datetime.now(UTC), app_name="com.test.App"))

            assert len(pre_calls) == 1
            assert len(post_calls) == 1

            service.stop()

    def test_flush_clears_buffer(self) -> None:
        """Flush writes buffered events and clears buffer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(
                    output_directory=Path(tmpdir),
                    batch_size=1000,  # Large batch to prevent auto-flush
                )
            )
            service = IngestionService(config)
            service.start()

            for i in range(10):
                service.ingest_event(AppEvent(event_id=f"e_{i}", timestamp=datetime.now(UTC), app_name="App"))

            result = service.flush()
            assert result["events_flushed"] == 10

            service.stop()


class TestRDFConversion:
    """RDF conversion behaviors."""

    def test_events_convert_to_triples(self) -> None:
        """Events convert to RDF triples."""
        config = IngestionConfig(rdf=RDFConfig(base_namespace="http://example.org/"))
        service = IngestionService(config)

        events = [AppEvent(event_id="rdf_test", timestamp=datetime.now(UTC), app_name="com.test.App")]

        graph = service.rdf_converter.convert_batch(events)
        assert len(graph) > 0


class TestMaterialization:
    """Feature materialization behaviors."""

    def test_materialize_app_usage(self) -> None:
        """Materializer computes app usage features."""
        config = IngestionConfig(feature=FeatureConfig(enabled_features=["app_usage_time"]))
        service = IngestionService(config)

        now = datetime.now(UTC).replace(tzinfo=None)
        window_start = now.replace(minute=0, second=0, microsecond=0)
        window_end = window_start + timedelta(hours=1)

        events = [
            AppEvent(
                event_id=f"mat_{i}",
                timestamp=window_start + timedelta(minutes=i * 5),
                app_name="com.test.App",
                duration_seconds=300.0,
            )
            for i in range(5)
        ]

        features = service.materializer.materialize(events, window_start, window_end)
        assert len(features) > 0
