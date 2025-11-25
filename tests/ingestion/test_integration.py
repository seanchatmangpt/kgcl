"""Integration tests for complete ingestion pipeline."""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from kgcl.ingestion.config import (
    CollectorConfig,
    FeatureConfig,
    FilterConfig,
    IngestionConfig,
    RDFConfig,
)
from kgcl.ingestion.models import AppEvent, BrowserVisit, CalendarBlock
from kgcl.ingestion.service import IngestionService


class TestEndToEndPipeline:
    """End-to-end integration tests."""

    def test_complete_ingestion_flow(self):
        """Test complete flow from ingestion to materialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir), batch_size=10),
                feature=FeatureConfig(enabled_features=["app_usage_time", "browser_domain_visits"]),
            )

            service = IngestionService(config)
            service.start()

            # Create diverse events
            now = datetime.now(UTC)
            events = [
                AppEvent(
                    event_id="app_001",
                    timestamp=now,
                    app_name="com.apple.Safari",
                    duration_seconds=120.0,
                ),
                AppEvent(
                    event_id="app_002",
                    timestamp=now + timedelta(minutes=5),
                    app_name="com.apple.Mail",
                    duration_seconds=60.0,
                ),
                BrowserVisit(
                    event_id="browser_001",
                    timestamp=now + timedelta(minutes=10),
                    url="https://github.com/user/repo",
                    domain="github.com",
                    browser_name="Safari",
                ),
                CalendarBlock(
                    event_id="cal_001",
                    timestamp=now + timedelta(hours=1),
                    end_time=now + timedelta(hours=2),
                    title="Team Meeting",
                ),
            ]

            # Ingest all events
            for event in events:
                result = service.ingest_event(event)
                assert result["status"] == "success"

            # Flush and get stats
            flush_result = service.flush()
            assert flush_result["events_flushed"] >= 4

            stats = service.get_stats()
            assert stats["total_events"] >= 4

            # Verify files created
            output_files = list(Path(tmpdir).glob("*.jsonl"))
            assert len(output_files) > 0

            service.stop()

    def test_batch_processing_with_rdf_conversion(self):
        """Test batch processing with RDF conversion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir)),
                rdf=RDFConfig(base_namespace="http://test.example.org/"),
                filter=FilterConfig(min_duration_seconds=0.0),  # Don't filter any events
            )

            service = IngestionService(config)
            service.start()

            now = datetime.now(UTC)
            events = [
                AppEvent(
                    event_id=f"app_{i:03d}",
                    timestamp=now + timedelta(minutes=i),
                    app_name="com.apple.Safari",
                    duration_seconds=float(i * 10),
                )
                for i in range(20)
            ]

            # Ingest batch
            result = service.ingest_batch(events)

            assert result["status"] == "success"
            assert result["processed_events"] == 20

            service.stop()

    def test_feature_materialization_pipeline(self):
        """Test feature materialization in pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir)),
                feature=FeatureConfig(
                    enabled_features=[
                        "app_usage_time",
                        "browser_domain_visits",
                        "meeting_count",
                        "context_switches",
                    ]
                ),
            )

            service = IngestionService(config)
            service.start()

            now = datetime.now(UTC).replace(tzinfo=None)
            window_start = now.replace(minute=0, second=0, microsecond=0)

            # Create comprehensive event set
            events = [
                # App events for context switches
                AppEvent(
                    event_id="app_001",
                    timestamp=window_start + timedelta(minutes=0),
                    app_name="com.apple.Safari",
                    duration_seconds=300.0,
                ),
                AppEvent(
                    event_id="app_002",
                    timestamp=window_start + timedelta(minutes=10),
                    app_name="com.apple.Mail",
                    duration_seconds=200.0,
                ),
                AppEvent(
                    event_id="app_003",
                    timestamp=window_start + timedelta(minutes=20),
                    app_name="com.apple.Safari",
                    duration_seconds=150.0,
                ),
                # Browser visits
                BrowserVisit(
                    event_id="browser_001",
                    timestamp=window_start + timedelta(minutes=5),
                    url="https://github.com/user/repo1",
                    domain="github.com",
                    browser_name="Safari",
                ),
                BrowserVisit(
                    event_id="browser_002",
                    timestamp=window_start + timedelta(minutes=15),
                    url="https://github.com/user/repo2",
                    domain="github.com",
                    browser_name="Safari",
                ),
                # Calendar events
                CalendarBlock(
                    event_id="cal_001",
                    timestamp=window_start + timedelta(hours=1),
                    end_time=window_start + timedelta(hours=2),
                    title="Meeting 1",
                ),
            ]

            # Ingest
            result = service.ingest_batch(events)
            assert result["status"] == "success"

            # Materialize features
            window_end = window_start + timedelta(hours=3)
            features = service.materializer.materialize(events, window_start, window_end)

            # Verify features computed
            assert len(features) > 0

            # Check for specific features
            feature_ids = {f.feature_id for f in features}
            assert any("Safari" in fid for fid in feature_ids)
            assert any("github.com" in fid for fid in feature_ids)
            assert "meeting_count" in feature_ids
            assert "context_switches" in feature_ids

            service.stop()

    def test_hooks_execution_in_pipeline(self):
        """Test pre/post hooks in complete pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir)))

            service = IngestionService(config)

            pre_hook_events = []
            post_hook_events = []

            def pre_hook(events):
                pre_hook_events.extend(events)

            def post_hook(events):
                post_hook_events.extend(events)

            service.register_pre_hook("test_pre", pre_hook)
            service.register_post_hook("test_post", post_hook)

            service.start()

            event = AppEvent(
                event_id="test_001", timestamp=datetime.now(UTC), app_name="com.apple.Safari"
            )

            service.ingest_event(event)

            assert len(pre_hook_events) == 1
            assert len(post_hook_events) == 1

            service.stop()

    def test_config_persistence_and_reload(self):
        """Test configuration persistence and reload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create service with custom config
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir), batch_size=75),
                feature=FeatureConfig(enabled_features=["app_usage_time"]),
            )

            service1 = IngestionService(config)

            # Export config
            config_path = Path(tmpdir) / "config.yaml"
            service1.export_config(config_path)

            # Create new service from exported config
            service2 = IngestionService.from_config_file(config_path)

            assert service2.config.collector.batch_size == 75
            assert "app_usage_time" in service2.config.feature.enabled_features

    def test_high_volume_ingestion(self):
        """Test ingestion with high event volume."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir), batch_size=100),
                filter=FilterConfig(min_duration_seconds=0.0),  # Don't filter any events
            )

            service = IngestionService(config)
            service.start()

            # Generate 500 events
            now = datetime.now(UTC)
            events = [
                AppEvent(
                    event_id=f"app_{i:05d}",
                    timestamp=now + timedelta(seconds=i),
                    app_name=f"com.app.App{i % 10}",
                    duration_seconds=float(i % 60),
                )
                for i in range(500)
            ]

            # Ingest in batches
            batch_size = 50
            for i in range(0, len(events), batch_size):
                batch = events[i : i + batch_size]
                result = service.ingest_batch(batch)
                assert result["status"] == "success"

            stats = service.get_stats()
            assert stats["total_events"] == 500

            service.stop()

    def test_mixed_event_types(self):
        """Test handling mixed event types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir)))

            service = IngestionService(config)
            service.start()

            now = datetime.now(UTC)

            # Create one of each event type
            app_event = AppEvent(event_id="app_001", timestamp=now, app_name="com.apple.Safari")

            browser_event = BrowserVisit(
                event_id="browser_001",
                timestamp=now + timedelta(minutes=1),
                url="https://example.com",
                domain="example.com",
                browser_name="Safari",
            )

            calendar_event = CalendarBlock(
                event_id="cal_001",
                timestamp=now + timedelta(hours=1),
                end_time=now + timedelta(hours=2),
                title="Meeting",
            )

            # Ingest all types
            for event in [app_event, browser_event, calendar_event]:
                result = service.ingest_event(event)
                assert result["status"] == "success"

            stats = service.get_stats()
            assert stats["total_events"] == 3

            service.stop()

    def test_error_recovery(self):
        """Test error recovery in pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir), enable_recovery=True)
            )

            service = IngestionService(config)
            service.start()

            # Ingest valid events
            valid_events = [
                AppEvent(
                    event_id=f"app_{i:03d}",
                    timestamp=datetime.now(UTC),
                    app_name="com.apple.Safari",
                )
                for i in range(5)
            ]

            for event in valid_events:
                result = service.ingest_event(event)
                assert result["status"] == "success"

            # Service should continue working after errors
            stats = service.get_stats()
            assert stats["total_events"] == 5

            service.stop()
