"""Tests for ingestion service."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from kgcl.ingestion.config import CollectorConfig, IngestionConfig
from kgcl.ingestion.models import AppEvent, EventBatch
from kgcl.ingestion.service import IngestionHook, IngestionService


class TestIngestionHook:
    """Tests for IngestionHook."""

    @pytest.mark.asyncio
    async def test_sync_hook_execution(self):
        """Test executing synchronous hook."""
        executed = False

        def handler(events):
            nonlocal executed
            executed = True

        hook = IngestionHook("test_hook", handler)
        await hook.execute([])

        assert executed is True

    @pytest.mark.asyncio
    async def test_async_hook_execution(self):
        """Test executing asynchronous hook."""
        executed = False

        async def handler(events):
            nonlocal executed
            executed = True

        hook = IngestionHook("test_hook", handler)
        await hook.execute([])

        assert executed is True


class TestIngestionService:
    """Tests for IngestionService."""

    def test_initialization(self):
        """Test service initialization."""
        service = IngestionService()

        assert service.config is not None
        assert service.collector is not None
        assert service.rdf_converter is not None
        assert service.materializer is not None

    def test_initialization_with_config(self):
        """Test service initialization with custom config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir), batch_size=50)
            )
            service = IngestionService(config)

            assert service.collector.batch_size == 50

    def test_ingest_single_event(self):
        """Test ingesting single event."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir))
            )
            service = IngestionService(config)
            service.start()

            event = AppEvent(
                event_id="test_001",
                timestamp=datetime.now(UTC),
                app_name="com.apple.Safari",
            )

            result = service.ingest_event(event)

            assert result["status"] == "success"
            assert result["event_id"] == "test_001"
            assert service._stats["total_events"] == 1

    @pytest.mark.asyncio
    async def test_ingest_event_async(self):
        """Test async event ingestion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir))
            )
            service = IngestionService(config)
            service.start()

            event = AppEvent(
                event_id="test_001",
                timestamp=datetime.now(UTC),
                app_name="com.apple.Safari",
            )

            result = await service.ingest_event_async(event)

            assert result["status"] == "success"

    def test_ingest_batch(self):
        """Test batch ingestion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir))
            )
            service = IngestionService(config)
            service.start()

            events = [
                AppEvent(
                    event_id=f"test_{i:03d}",
                    timestamp=datetime.now(UTC),
                    app_name="com.apple.Safari",
                )
                for i in range(5)
            ]

            batch = EventBatch(batch_id="batch_001", events=events)
            result = service.ingest_batch(batch)

            assert result["status"] == "success"
            assert result["total_events"] == 5
            assert service._stats["total_batches"] == 1

    def test_event_filtering(self):
        """Test event filtering."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir))
            )
            service = IngestionService(config)
            service.start()

            # Event that should be filtered
            event = AppEvent(
                event_id="test_001",
                timestamp=datetime.now(UTC),
                app_name="com.apple.Spotlight",  # In excluded_apps
            )

            result = service.ingest_event(event)

            assert result["status"] == "filtered"

    def test_duration_filtering(self):
        """Test filtering by minimum duration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir))
            )
            service = IngestionService(config)
            service.start()

            # Event with duration below threshold
            event = AppEvent(
                event_id="test_001",
                timestamp=datetime.now(UTC),
                app_name="com.apple.Safari",
                duration_seconds=0.5,  # Below min_duration_seconds (1.0)
            )

            result = service.ingest_event(event)

            assert result["status"] == "filtered"

    def test_register_pre_hook(self):
        """Test registering pre-ingestion hook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir))
            )
            service = IngestionService(config)

            hook_executed = False

            def pre_hook(events):
                nonlocal hook_executed
                hook_executed = True

            service.register_pre_hook("test_pre", pre_hook)
            service.start()

            event = AppEvent(
                event_id="test_001",
                timestamp=datetime.now(UTC),
                app_name="com.apple.Safari",
            )

            service.ingest_event(event)

            assert hook_executed is True

    def test_register_post_hook(self):
        """Test registering post-ingestion hook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir))
            )
            service = IngestionService(config)

            hook_executed = False

            def post_hook(events):
                nonlocal hook_executed
                hook_executed = True

            service.register_post_hook("test_post", post_hook)
            service.start()

            event = AppEvent(
                event_id="test_001",
                timestamp=datetime.now(UTC),
                app_name="com.apple.Safari",
            )

            service.ingest_event(event)

            assert hook_executed is True

    def test_flush(self):
        """Test manual flush."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir), batch_size=100)
            )
            service = IngestionService(config)
            service.start()

            # Add some events
            for i in range(5):
                event = AppEvent(
                    event_id=f"test_{i:03d}",
                    timestamp=datetime.now(UTC),
                    app_name="com.apple.Safari",
                )
                service.ingest_event(event)

            # Flush
            result = service.flush()

            assert result["events_flushed"] == 5
            assert "collector_stats" in result

    def test_get_stats(self):
        """Test getting service statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir))
            )
            service = IngestionService(config)

            stats = service.get_stats()

            assert "total_events" in stats
            assert "total_batches" in stats
            assert "collector" in stats
            assert "materializer" in stats

    def test_start_stop(self):
        """Test service lifecycle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir))
            )
            service = IngestionService(config)

            service.start()
            # Add event
            event = AppEvent(
                event_id="test_001",
                timestamp=datetime.now(UTC),
                app_name="com.apple.Safari",
            )
            service.ingest_event(event)

            service.stop()
            # Events should be flushed on stop

    def test_export_config(self):
        """Test exporting configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(batch_size=75))
            service = IngestionService(config)

            config_path = Path(tmpdir) / "exported_config.yaml"
            service.export_config(config_path)

            assert config_path.exists()

    def test_from_config_file(self):
        """Test creating service from config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(batch_size=75))
            config_path = Path(tmpdir) / "config.yaml"
            config.to_yaml(config_path)

            service = IngestionService.from_config_file(config_path)

            assert service.config.collector.batch_size == 75

    @pytest.mark.asyncio
    async def test_http_handler_ingest_event(self):
        """Test HTTP handler for single event ingestion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir))
            )
            service = IngestionService(config)
            service.start()

            handler = service.to_http_handler()

            request = {
                "endpoint": "/ingest/event",
                "payload": {
                    "event_type": "AppEvent",
                    "data": {
                        "event_id": "test_001",
                        "timestamp": "2024-11-24T10:00:00",
                        "app_name": "com.apple.Safari",
                        "schema_version": "1.0.0",
                    },
                },
            }

            result = await handler(request)

            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_http_handler_ingest_batch(self):
        """Test HTTP handler for batch ingestion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir))
            )
            service = IngestionService(config)
            service.start()

            handler = service.to_http_handler()

            request = {
                "endpoint": "/ingest/batch",
                "payload": {
                    "events": [
                        {
                            "event_type": "AppEvent",
                            "data": {
                                "event_id": "test_001",
                                "timestamp": "2024-11-24T10:00:00",
                                "app_name": "com.apple.Safari",
                                "schema_version": "1.0.0",
                            },
                        },
                        {
                            "event_type": "BrowserVisit",
                            "data": {
                                "event_id": "test_002",
                                "timestamp": "2024-11-24T10:05:00",
                                "url": "https://example.com",
                                "domain": "example.com",
                                "browser_name": "Safari",
                                "schema_version": "1.0.0",
                            },
                        },
                    ]
                },
            }

            result = await handler(request)

            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_http_handler_stats(self):
        """Test HTTP handler for stats endpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir))
            )
            service = IngestionService(config)

            handler = service.to_http_handler()

            request = {"endpoint": "/stats", "payload": {}}

            result = await handler(request)

            assert result["status"] == "success"
            assert "stats" in result

    @pytest.mark.asyncio
    async def test_http_handler_flush(self):
        """Test HTTP handler for flush endpoint."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir))
            )
            service = IngestionService(config)

            handler = service.to_http_handler()

            request = {"endpoint": "/flush", "payload": {}}

            result = await handler(request)

            assert result["status"] == "success"
