"""Performance tests for ingestion system."""

import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from kgcl.ingestion.config import CollectorConfig, FeatureConfig, IngestionConfig
from kgcl.ingestion.models import AppEvent, BrowserVisit
from kgcl.ingestion.service import IngestionService


class TestPerformance:
    """Performance tests for ingestion pipeline."""

    @pytest.mark.slow
    def test_batch_ingestion_throughput(self):
        """Test batch ingestion throughput."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir), batch_size=1000))

            service = IngestionService(config)
            service.start()

            # Generate large batch
            now = datetime.now(UTC)
            events = [
                AppEvent(
                    event_id=f"app_{i:06d}",
                    timestamp=now + timedelta(seconds=i),
                    app_name=f"com.app.App{i % 100}",
                    duration_seconds=float(i % 300),
                )
                for i in range(10000)
            ]

            # Measure ingestion time
            start_time = time.perf_counter()
            result = service.ingest_batch(events)
            end_time = time.perf_counter()

            elapsed = end_time - start_time
            throughput = len(events) / elapsed

            assert result["status"] == "success"
            assert throughput > 1000  # At least 1000 events/sec
            print(f"Throughput: {throughput:.2f} events/sec")

            service.stop()

    @pytest.mark.slow
    def test_materialization_performance(self):
        """Test feature materialization performance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir)),
                feature=FeatureConfig(enabled_features=["app_usage_time", "browser_domain_visits", "context_switches"]),
            )

            service = IngestionService(config)

            # Generate large event set
            now = datetime.now(UTC).replace(tzinfo=None)
            window_start = now.replace(minute=0, second=0, microsecond=0)
            window_end = window_start + timedelta(hours=1)

            events = []
            for i in range(5000):
                if i % 2 == 0:
                    events.append(
                        AppEvent(
                            event_id=f"app_{i:06d}",
                            timestamp=window_start + timedelta(seconds=i),
                            app_name=f"com.app.App{i % 50}",
                            duration_seconds=float(i % 300),
                        )
                    )
                else:
                    events.append(
                        BrowserVisit(
                            event_id=f"browser_{i:06d}",
                            timestamp=window_start + timedelta(seconds=i),
                            url=f"https://domain{i % 20}.com/page",
                            domain=f"domain{i % 20}.com",
                            browser_name="Safari",
                        )
                    )

            # Measure materialization time
            start_time = time.perf_counter()
            features = service.materializer.materialize(events, window_start, window_end)
            end_time = time.perf_counter()

            elapsed = end_time - start_time
            throughput = len(events) / elapsed

            assert len(features) > 0
            assert elapsed < 5.0  # Should complete in under 5 seconds
            print(f"Materialization: {throughput:.2f} events/sec, {len(features)} features")

    def test_flush_latency(self):
        """Test flush operation latency."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir), batch_size=100))

            service = IngestionService(config)
            service.start()

            # Add events
            now = datetime.now(UTC)
            for i in range(50):
                event = AppEvent(
                    event_id=f"app_{i:03d}", timestamp=now + timedelta(seconds=i), app_name="com.apple.Safari"
                )
                service.ingest_event(event)

            # Measure flush time
            start_time = time.perf_counter()
            result = service.flush()
            end_time = time.perf_counter()

            elapsed = end_time - start_time

            assert result["events_flushed"] == 50
            assert elapsed < 1.0  # Should flush in under 1 second
            print(f"Flush latency: {elapsed * 1000:.2f}ms for {result['events_flushed']} events")

            service.stop()

    def test_rdf_conversion_performance(self):
        """Test RDF conversion performance."""
        config = IngestionConfig()
        service = IngestionService(config)

        # Generate events
        now = datetime.now(UTC)
        events = [
            AppEvent(
                event_id=f"app_{i:05d}",
                timestamp=now + timedelta(seconds=i),
                app_name=f"com.app.App{i % 10}",
                duration_seconds=float(i % 300),
            )
            for i in range(1000)
        ]

        # Measure conversion time
        start_time = time.perf_counter()
        graph = service.rdf_converter.convert_batch(events)
        end_time = time.perf_counter()

        elapsed = end_time - start_time
        throughput = len(events) / elapsed

        assert len(graph) > 0
        assert elapsed < 2.0  # Should complete in under 2 seconds
        print(f"RDF conversion: {throughput:.2f} events/sec, {len(graph)} triples")

    def test_incremental_update_performance(self):
        """Test incremental feature update performance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(
                collector=CollectorConfig(output_directory=Path(tmpdir)),
                feature=FeatureConfig(enabled_features=["app_usage_time"], incremental_updates=True),
            )

            service = IngestionService(config)

            now = datetime.now(UTC).replace(tzinfo=None)
            window_start = now.replace(minute=0, second=0, microsecond=0)
            window_end = window_start + timedelta(hours=1)

            # Initial batch
            initial_events = [
                AppEvent(
                    event_id=f"app_{i:05d}",
                    timestamp=window_start + timedelta(seconds=i),
                    app_name=f"com.app.App{i % 10}",
                    duration_seconds=float(i),
                )
                for i in range(1000)
            ]

            initial_features = service.materializer.materialize(initial_events, window_start, window_end)

            # New events
            new_events = [
                AppEvent(
                    event_id=f"app_new_{i:05d}",
                    timestamp=window_start + timedelta(seconds=1000 + i),
                    app_name=f"com.app.App{i % 10}",
                    duration_seconds=float(i),
                )
                for i in range(100)
            ]

            # Measure incremental update time
            start_time = time.perf_counter()
            updated_features = service.materializer.materialize_incremental(new_events, initial_features)
            end_time = time.perf_counter()

            elapsed = end_time - start_time

            assert len(updated_features) > 0
            assert elapsed < 1.0  # Incremental update should be fast
            print(f"Incremental update: {elapsed * 1000:.2f}ms for 100 new events")

    def test_concurrent_ingestion(self):
        """Test concurrent event ingestion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir), batch_size=100))

            service = IngestionService(config)
            service.start()

            # Simulate concurrent ingestion
            now = datetime.now(UTC)
            batches = [
                [
                    AppEvent(
                        event_id=f"app_b{batch}_e{i:03d}",
                        timestamp=now + timedelta(seconds=batch * 100 + i),
                        app_name=f"com.app.App{i % 10}",
                    )
                    for i in range(50)
                ]
                for batch in range(10)
            ]

            start_time = time.perf_counter()
            for batch in batches:
                result = service.ingest_batch(batch)
                assert result["status"] == "success"
            end_time = time.perf_counter()

            elapsed = end_time - start_time
            total_events = sum(len(b) for b in batches)
            throughput = total_events / elapsed

            assert service._stats["total_events"] == total_events
            print(f"Concurrent ingestion: {throughput:.2f} events/sec")

            service.stop()

    def test_memory_efficiency(self):
        """Test memory efficiency with large batches."""
        import sys

        with tempfile.TemporaryDirectory() as tmpdir:
            config = IngestionConfig(collector=CollectorConfig(output_directory=Path(tmpdir), batch_size=1000))

            service = IngestionService(config)
            service.start()

            # Generate large batch
            now = datetime.now(UTC)
            events = [
                AppEvent(
                    event_id=f"app_{i:06d}",
                    timestamp=now + timedelta(seconds=i),
                    app_name=f"com.app.App{i % 100}",
                    duration_seconds=float(i % 300),
                )
                for i in range(5000)
            ]

            # Check memory usage
            event_size = sys.getsizeof(events)
            events_mb = event_size / (1024 * 1024)

            result = service.ingest_batch(events)
            assert result["status"] == "success"

            print(f"Batch size: {events_mb:.2f} MB for {len(events)} events")

            service.stop()
