"""Advanced usage examples for KGCL Ingestion System."""

import asyncio
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from kgcl.ingestion import AppEvent, BrowserVisit, IngestionService
from kgcl.ingestion.config import (
    CollectorConfig,
    FeatureConfig,
    FilterConfig,
    IngestionConfig,
    RDFConfig,
)


def example_1_custom_configuration():
    """Example 1: Custom configuration from YAML."""
    print("Example 1: Custom Configuration")
    print("-" * 50)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create custom config
        config = IngestionConfig(
            collector=CollectorConfig(
                output_directory=Path(tmpdir), batch_size=50, flush_interval_seconds=30
            ),
            filter=FilterConfig(
                excluded_apps=["com.apple.Spotlight", "com.test.app"],
                min_duration_seconds=2.0,
                privacy_mode=True,
            ),
            feature=FeatureConfig(
                enabled_features=["app_usage_time", "context_switches"],
                aggregation_windows=["1h", "1d"],
            ),
        )

        # Save to YAML
        config_path = Path(tmpdir) / "config.yaml"
        config.to_yaml(config_path)

        # Load from YAML
        loaded_config = IngestionConfig.from_yaml(config_path)

        print(f"Batch size: {loaded_config.collector.batch_size}")
        print(f"Privacy mode: {loaded_config.filter.privacy_mode}")
        print(f"Enabled features: {loaded_config.feature.enabled_features}")

        # Use loaded config
        service = IngestionService(loaded_config)
        print(f"Service initialized with batch_size={service.collector.batch_size}")
        print()


def example_2_async_ingestion():
    """Example 2: Async event ingestion."""
    print("Example 2: Async Ingestion")
    print("-" * 50)

    async def async_main():
        service = IngestionService()
        service.start()

        # Create events
        now = datetime.now(UTC)
        events = [
            AppEvent(
                event_id=f"evt_{i:03d}",
                timestamp=now + timedelta(seconds=i),
                app_name="com.apple.Safari",
            )
            for i in range(10)
        ]

        # Async ingestion
        tasks = [service.ingest_event_async(event) for event in events]
        results = await asyncio.gather(*tasks)

        print(f"Ingested {len(results)} events asynchronously")
        print(f"Success count: {sum(1 for r in results if r['status'] == 'success')}")

        service.flush()
        service.stop()

    asyncio.run(async_main())
    print()


def example_3_incremental_features():
    """Example 3: Incremental feature updates."""
    print("Example 3: Incremental Feature Updates")
    print("-" * 50)

    config = IngestionConfig(
        feature=FeatureConfig(enabled_features=["app_usage_time"], incremental_updates=True)
    )

    service = IngestionService(config)

    now = datetime.now(UTC).replace(tzinfo=None)
    window_start = now.replace(minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(hours=1)

    # Initial events
    initial_events = [
        AppEvent(
            event_id=f"app_{i:03d}",
            timestamp=window_start + timedelta(minutes=i * 5),
            app_name="com.apple.Safari",
            duration_seconds=float(i * 60),
        )
        for i in range(5)
    ]

    # Materialize initial features
    initial_features = service.materializer.materialize(initial_events, window_start, window_end)

    print(f"Initial features: {len(initial_features)}")
    for feature in initial_features:
        print(f"  {feature.feature_id}: {feature.value}")

    # New events arrive
    new_events = [
        AppEvent(
            event_id=f"app_new_{i:03d}",
            timestamp=window_start + timedelta(minutes=30 + i * 5),
            app_name="com.apple.Safari",
            duration_seconds=float(i * 30),
        )
        for i in range(3)
    ]

    # Incremental update
    updated_features = service.materializer.materialize_incremental(new_events, initial_features)

    print(f"\nUpdated features: {len(updated_features)}")
    for feature in updated_features:
        print(f"  {feature.feature_id}: {feature.value}")

    print()


def example_4_error_recovery():
    """Example 4: Error recovery from corrupted files."""
    print("Example 4: Error Recovery")
    print("-" * 50)

    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        config = IngestionConfig(
            collector=CollectorConfig(output_directory=Path(tmpdir), enable_recovery=True)
        )

        service = IngestionService(config)

        # Create a corrupted JSONL file
        corrupted_file = Path(tmpdir) / "corrupted.jsonl"
        with corrupted_file.open("w") as f:
            # Valid event
            f.write(
                json.dumps(
                    {
                        "type": "event",
                        "batch_id": "batch_001",
                        "event_type": "AppEvent",
                        "data": {
                            "event_id": "evt_001",
                            "timestamp": "2024-11-24T10:00:00",
                            "app_name": "com.apple.Safari",
                            "schema_version": "1.0.0",
                        },
                    }
                )
                + "\n"
            )

            # Corrupted line
            f.write("{ invalid json\n")

            # Another valid event
            f.write(
                json.dumps(
                    {
                        "type": "event",
                        "batch_id": "batch_001",
                        "event_type": "AppEvent",
                        "data": {
                            "event_id": "evt_002",
                            "timestamp": "2024-11-24T10:05:00",
                            "app_name": "com.apple.Mail",
                            "schema_version": "1.0.0",
                        },
                    }
                )
                + "\n"
            )

        # Attempt recovery
        recovered, corrupted = service.collector.recover_from_file(corrupted_file)

        print(f"Recovered {recovered} events")
        print(f"Found {corrupted} corrupted lines")
        print(f"Recovery success rate: {recovered / (recovered + corrupted) * 100:.1f}%")

        print()


def example_5_advanced_filtering():
    """Example 5: Advanced event filtering."""
    print("Example 5: Advanced Event Filtering")
    print("-" * 50)

    config = IngestionConfig(
        filter=FilterConfig(
            excluded_apps=["com.apple.Spotlight", "com.apple.systemuiserver"],
            excluded_domains=["localhost", "127.0.0.1"],
            min_duration_seconds=5.0,
            privacy_mode=True,
        )
    )

    service = IngestionService(config)
    service.start()

    now = datetime.now(UTC)
    test_events = [
        # Should be filtered (excluded app)
        AppEvent(
            event_id="filtered_1",
            timestamp=now,
            app_name="com.apple.Spotlight",
            duration_seconds=10.0,
        ),
        # Should be filtered (too short)
        AppEvent(
            event_id="filtered_2", timestamp=now, app_name="com.apple.Safari", duration_seconds=2.0
        ),
        # Should pass
        AppEvent(
            event_id="pass_1", timestamp=now, app_name="com.apple.Safari", duration_seconds=10.0
        ),
        # Should be filtered (excluded domain)
        BrowserVisit(
            event_id="filtered_3",
            timestamp=now,
            url="http://localhost:8000",
            domain="localhost",
            browser_name="Safari",
        ),
        # Should pass
        BrowserVisit(
            event_id="pass_2",
            timestamp=now,
            url="https://github.com",
            domain="github.com",
            browser_name="Safari",
            duration_seconds=10.0,
        ),
    ]

    results = []
    for event in test_events:
        result = service.ingest_event(event)
        results.append((event.event_id, result["status"]))

    print("Filtering results:")
    for event_id, status in results:
        print(f"  {event_id}: {status}")

    stats = service.get_stats()
    print(f"\nTotal processed: {stats['total_events']} events")

    service.flush()
    service.stop()
    print()


def example_6_custom_features():
    """Example 6: Custom feature computation."""
    print("Example 6: Custom Features")
    print("-" * 50)

    from kgcl.ingestion.materializer import FeatureMaterializer
    from kgcl.ingestion.models import MaterializedFeature

    config = FeatureConfig()
    materializer = FeatureMaterializer(config)

    # Extend materializer with custom feature
    def compute_custom_feature(events, window_start, window_end):
        """Compute custom feature: unique apps per hour."""
        app_events = [e for e in events if isinstance(e, AppEvent)]
        unique_apps = len(set(e.app_name for e in app_events))

        return MaterializedFeature(
            feature_id="unique_apps_hourly",
            window_start=window_start,
            window_end=window_end,
            aggregation_type="distinct",
            value=unique_apps,
            sample_count=len(app_events),
            metadata={"apps": list(set(e.app_name for e in app_events))},
        )

    # Generate test events
    now = datetime.now(UTC).replace(tzinfo=None)
    window_start = now.replace(minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(hours=1)

    events = [
        AppEvent(
            event_id=f"app_{i:03d}",
            timestamp=window_start + timedelta(minutes=i * 5),
            app_name=f"com.app.App{i % 3}",  # 3 unique apps
            duration_seconds=float(i * 10),
        )
        for i in range(10)
    ]

    # Compute custom feature
    custom_feature = compute_custom_feature(events, window_start, window_end)

    print(f"Custom feature: {custom_feature.feature_id}")
    print(f"Value: {custom_feature.value} unique apps")
    print(f"Apps: {custom_feature.metadata['apps']}")

    print()


def example_7_rdf_export():
    """Example 7: RDF export to multiple formats."""
    print("Example 7: RDF Export")
    print("-" * 50)

    config = IngestionConfig(
        rdf=RDFConfig(
            base_namespace="http://kgcl.example.org/",
            normalize_timestamps=True,
            property_cleanup=True,
        )
    )

    service = IngestionService(config)

    # Create events
    now = datetime.now(UTC)
    events = [
        AppEvent(
            event_id="evt_001", timestamp=now, app_name="com.apple.Safari", duration_seconds=120.0
        ),
        BrowserVisit(
            event_id="evt_002",
            timestamp=now + timedelta(minutes=5),
            url="https://github.com/user/repo",
            domain="github.com",
            browser_name="Safari",
        ),
    ]

    # Convert to RDF
    graph = service.rdf_converter.convert_batch(events)

    print(f"Generated {len(graph)} triples\n")

    # Export to different formats
    formats = ["turtle", "xml", "nt", "json-ld"]

    for fmt in formats:
        serialized = graph.serialize(format=fmt)
        print(f"{fmt.upper()}:")
        print(serialized[:200] + "...\n")

    print()


if __name__ == "__main__":
    example_1_custom_configuration()
    example_2_async_ingestion()
    example_3_incremental_features()
    example_4_error_recovery()
    example_5_advanced_filtering()
    example_6_custom_features()
    example_7_rdf_export()
