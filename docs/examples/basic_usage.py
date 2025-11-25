"""Basic usage examples for KGCL Ingestion System."""

from datetime import datetime, timedelta, timezone

from kgcl.ingestion import AppEvent, BrowserVisit, CalendarBlock, IngestionService


def example_1_simple_ingestion():
    """Example 1: Simple event ingestion."""
    print("Example 1: Simple Event Ingestion")
    print("-" * 50)

    # Create service with defaults
    service = IngestionService()
    service.start()

    # Create and ingest an app event
    event = AppEvent(
        event_id="evt_001",
        timestamp=datetime.now(timezone.utc),
        app_name="com.apple.Safari",
        app_display_name="Safari",
        duration_seconds=120.5,
    )

    result = service.ingest_event(event)
    print(f"Ingestion result: {result}")

    # Flush and stop
    flush_result = service.flush()
    print(f"Flushed {flush_result['events_flushed']} events")

    service.stop()
    print()


def example_2_batch_ingestion():
    """Example 2: Batch event ingestion."""
    print("Example 2: Batch Event Ingestion")
    print("-" * 50)

    service = IngestionService()
    service.start()

    # Create multiple events
    now = datetime.now(timezone.utc)
    events = []

    # App events
    for i in range(5):
        events.append(
            AppEvent(
                event_id=f"app_{i:03d}",
                timestamp=now + timedelta(minutes=i * 10),
                app_name=f"com.example.App{i}",
                duration_seconds=float(i * 60),
            )
        )

    # Browser events
    for i in range(3):
        events.append(
            BrowserVisit(
                event_id=f"browser_{i:03d}",
                timestamp=now + timedelta(minutes=i * 15),
                url=f"https://example{i}.com",
                domain=f"example{i}.com",
                browser_name="Safari",
            )
        )

    # Ingest batch
    result = service.ingest_batch(events)
    print(f"Batch result: {result}")
    print(f"Processed {result['processed_events']} events")

    service.flush()
    service.stop()
    print()


def example_3_calendar_events():
    """Example 3: Calendar event ingestion."""
    print("Example 3: Calendar Event Ingestion")
    print("-" * 50)

    service = IngestionService()
    service.start()

    # Create calendar events
    now = datetime.now(timezone.utc)
    events = [
        CalendarBlock(
            event_id="cal_001",
            timestamp=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            title="Team Standup",
            description="Daily sync meeting",
            attendees=["team@example.com"],
            organizer="manager@example.com",
        ),
        CalendarBlock(
            event_id="cal_002",
            timestamp=now + timedelta(hours=3),
            end_time=now + timedelta(hours=4),
            title="Project Review",
            location="Conference Room A",
            attendees=["dev1@example.com", "dev2@example.com"],
        ),
    ]

    for event in events:
        result = service.ingest_event(event)
        print(f"Ingested: {event.title} - {result['status']}")

    service.flush()
    service.stop()
    print()


def example_4_with_hooks():
    """Example 4: Using pre/post hooks."""
    print("Example 4: Event Hooks")
    print("-" * 50)

    service = IngestionService()

    # Register hooks
    def pre_hook(events):
        print(f"PRE-HOOK: About to ingest {len(events)} events")

    def post_hook(events):
        print(f"POST-HOOK: Finished ingesting {len(events)} events")

    service.register_pre_hook("logger_pre", pre_hook)
    service.register_post_hook("logger_post", post_hook)

    service.start()

    # Ingest events
    event = AppEvent(
        event_id="evt_001",
        timestamp=datetime.now(timezone.utc),
        app_name="com.apple.Safari",
    )

    service.ingest_event(event)

    service.flush()
    service.stop()
    print()


def example_5_statistics():
    """Example 5: Getting statistics."""
    print("Example 5: Service Statistics")
    print("-" * 50)

    service = IngestionService()
    service.start()

    # Ingest some events
    now = datetime.now(timezone.utc)
    events = [
        AppEvent(
            event_id=f"evt_{i:03d}",
            timestamp=now + timedelta(seconds=i),
            app_name="com.apple.Safari",
        )
        for i in range(10)
    ]

    service.ingest_batch(events)

    # Get statistics
    stats = service.get_stats()
    print(f"Total events: {stats['total_events']}")
    print(f"Total batches: {stats['total_batches']}")
    print(f"Failed events: {stats['failed_events']}")
    print(f"Last ingestion: {stats['last_ingestion']}")

    # Collector stats
    collector_stats = service.collector.get_stats()
    print(f"\nCollector state: {collector_stats['state']}")
    print(f"Buffer size: {collector_stats['buffer_size']}")

    service.flush()
    service.stop()
    print()


def example_6_feature_materialization():
    """Example 6: Feature materialization."""
    print("Example 6: Feature Materialization")
    print("-" * 50)

    from kgcl.ingestion.config import FeatureConfig, IngestionConfig

    # Configure features
    config = IngestionConfig(
        feature=FeatureConfig(
            enabled_features=[
                "app_usage_time",
                "browser_domain_visits",
                "context_switches",
            ]
        )
    )

    service = IngestionService(config)
    service.start()

    # Create diverse events
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_start = now.replace(minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(hours=1)

    events = [
        AppEvent(
            event_id="app_001",
            timestamp=window_start + timedelta(minutes=10),
            app_name="com.apple.Safari",
            duration_seconds=300.0,
        ),
        AppEvent(
            event_id="app_002",
            timestamp=window_start + timedelta(minutes=20),
            app_name="com.apple.Mail",
            duration_seconds=200.0,
        ),
        BrowserVisit(
            event_id="browser_001",
            timestamp=window_start + timedelta(minutes=15),
            url="https://github.com/user/repo",
            domain="github.com",
            browser_name="Safari",
        ),
    ]

    service.ingest_batch(events)

    # Materialize features
    features = service.materializer.materialize(events, window_start, window_end)

    print(f"Materialized {len(features)} features:")
    for feature in features:
        print(f"  {feature.feature_id}: {feature.value}")

    service.flush()
    service.stop()
    print()


def example_7_rdf_conversion():
    """Example 7: RDF conversion."""
    print("Example 7: RDF Conversion")
    print("-" * 50)

    from kgcl.ingestion.config import IngestionConfig, RDFConfig

    # Configure RDF
    config = IngestionConfig(
        rdf=RDFConfig(
            base_namespace="http://myapp.example.org/",
            normalize_timestamps=True,
        )
    )

    service = IngestionService(config)

    # Create event
    event = AppEvent(
        event_id="evt_001",
        timestamp=datetime.now(timezone.utc),
        app_name="com.apple.Safari",
        app_display_name="Safari",
        duration_seconds=120.5,
    )

    # Convert to RDF
    graph = service.rdf_converter.convert_event(event)

    print(f"Generated {len(graph)} RDF triples")
    print("\nTurtle format:")
    print(graph.serialize(format="turtle"))


if __name__ == "__main__":
    example_1_simple_ingestion()
    example_2_batch_ingestion()
    example_3_calendar_events()
    example_4_with_hooks()
    example_5_statistics()
    example_6_feature_materialization()
    example_7_rdf_conversion()
