# KGCL Ingestion API Documentation

## Overview

The KGCL Ingestion System provides a complete event collection and processing pipeline for:

- Application usage tracking
- Browser visit monitoring
- Calendar event collection
- Feature materialization
- RDF conversion

## Quick Start

```python
from kgcl.ingestion import IngestionService, IngestionConfig, AppEvent
from datetime import datetime, timezone

# Create service with default configuration
service = IngestionService()
service.start()

# Ingest a single event
event = AppEvent(
    event_id="evt_001",
    timestamp=datetime.now(timezone.utc),
    app_name="com.apple.Safari",
    app_display_name="Safari",
    duration_seconds=120.5,
)

result = service.ingest_event(event)
print(result)  # {'status': 'success', 'event_id': 'evt_001', ...}

# Flush and stop
service.flush()
service.stop()
```

## Event Models

### AppEvent

Tracks application usage and focus events.

```python
from kgcl.ingestion.models import AppEvent

event = AppEvent(
    event_id="evt_app_001",
    timestamp=datetime.now(timezone.utc),
    app_name="com.apple.Safari",
    app_display_name="Safari",
    window_title="GitHub Repository",
    duration_seconds=120.5,
    process_id=1234,
)
```

**Fields:**
- `event_id` (str): Unique identifier
- `timestamp` (datetime): Event time (UTC)
- `app_name` (str): Application bundle name
- `app_display_name` (str, optional): Human-readable name
- `window_title` (str, optional): Active window title
- `duration_seconds` (float, optional): Time spent
- `process_id` (int, optional): Process ID

### BrowserVisit

Tracks webpage visits and navigation.

```python
from kgcl.ingestion.models import BrowserVisit

event = BrowserVisit(
    event_id="evt_browser_001",
    timestamp=datetime.now(timezone.utc),
    url="https://github.com/user/repo",
    domain="github.com",
    title="GitHub Repository",
    browser_name="Safari",
    duration_seconds=45.2,
    referrer="https://google.com/search",
)
```

**Fields:**
- `event_id` (str): Unique identifier
- `timestamp` (datetime): Visit time (UTC)
- `url` (str): Full URL
- `domain` (str): Extracted domain
- `title` (str, optional): Page title
- `browser_name` (str): Browser application
- `duration_seconds` (float, optional): Time on page
- `referrer` (str, optional): Referring URL

### CalendarBlock

Tracks calendar events and meetings.

```python
from kgcl.ingestion.models import CalendarBlock

event = CalendarBlock(
    event_id="evt_cal_001",
    timestamp=datetime(2024, 11, 24, 14, 0, 0),
    end_time=datetime(2024, 11, 24, 15, 0, 0),
    title="Team Meeting",
    description="Weekly sync",
    location="Zoom",
    attendees=["team@example.com"],
    organizer="manager@example.com",
)
```

**Fields:**
- `event_id` (str): Unique identifier
- `timestamp` (datetime): Event start (UTC)
- `end_time` (datetime): Event end (UTC)
- `title` (str): Event title
- `description` (str, optional): Description
- `location` (str, optional): Location
- `attendees` (list[str]): Attendee emails
- `organizer` (str, optional): Organizer email

## Configuration

### Creating Configuration

```python
from kgcl.ingestion.config import IngestionConfig, CollectorConfig, FeatureConfig
from pathlib import Path

config = IngestionConfig(
    collector=CollectorConfig(
        flush_interval_seconds=30,
        batch_size=50,
        output_directory=Path.home() / ".kgcl" / "events",
    ),
    feature=FeatureConfig(
        enabled_features=["app_usage_time", "browser_domain_visits"],
        aggregation_windows=["1h", "1d"],
    ),
)

service = IngestionService(config)
```

### Loading from YAML

```python
config = IngestionConfig.from_yaml("config.yaml")
service = IngestionService(config)
```

Example YAML configuration:

```yaml
collector:
  flush_interval_seconds: 60
  batch_size: 100
  output_format: jsonl
  enable_recovery: true

filter:
  excluded_apps:
    - com.apple.Spotlight
    - com.apple.loginwindow
  excluded_domains:
    - localhost
  min_duration_seconds: 1.0
  privacy_mode: false

feature:
  enabled_features:
    - app_usage_time
    - browser_domain_visits
    - meeting_count
    - context_switches
  aggregation_windows:
    - 1h
    - 1d
    - 1w
  incremental_updates: true

rdf:
  base_namespace: http://kgcl.example.org/
  normalize_timestamps: true
  property_cleanup: true
```

## Batch Ingestion

```python
from kgcl.ingestion.models import EventBatch

# Create batch
events = [
    AppEvent(...),
    BrowserVisit(...),
    CalendarBlock(...),
]

batch = EventBatch(
    batch_id="batch_001",
    events=events,
)

# Ingest batch
result = service.ingest_batch(batch)
print(result)
# {
#   'status': 'success',
#   'batch_id': 'batch_001',
#   'total_events': 3,
#   'processed_events': 3,
#   'transactions': 1
# }
```

## RDF Conversion

```python
from kgcl.ingestion.converters import RDFConverter
from kgcl.ingestion.config import RDFConfig

config = RDFConfig(
    base_namespace="http://myapp.example.org/",
    normalize_timestamps=True,
    property_cleanup=True,
)

converter = RDFConverter(config)

# Convert single event
event = AppEvent(...)
graph = converter.convert_event(event)

# Convert batch
events = [AppEvent(...), BrowserVisit(...)]
graph = converter.convert_batch(events)

# Serialize to Turtle
print(graph.serialize(format="turtle"))
```

## Feature Materialization

```python
from kgcl.ingestion.materializer import FeatureMaterializer
from kgcl.ingestion.config import FeatureConfig
from datetime import datetime, timedelta

config = FeatureConfig(
    enabled_features=["app_usage_time", "context_switches"],
)

materializer = FeatureMaterializer(config)

# Materialize features for time window
window_start = datetime.now().replace(minute=0, second=0)
window_end = window_start + timedelta(hours=1)

features = materializer.materialize(events, window_start, window_end)

for feature in features:
    print(f"{feature.feature_id}: {feature.value}")
```

### Available Features

- `app_usage_time`: Total time per application
- `browser_domain_visits`: Visit counts per domain
- `meeting_count`: Number of meetings
- `context_switches`: Application switch count

## Hooks

### Pre-ingestion Hook

```python
def validate_events(events):
    """Validate events before ingestion."""
    for event in events:
        # Custom validation logic
        pass

service.register_pre_hook("validator", validate_events)
```

### Post-ingestion Hook

```python
def log_events(events):
    """Log events after ingestion."""
    print(f"Ingested {len(events)} events")

service.register_post_hook("logger", log_events)
```

### Async Hooks

```python
async def async_hook(events):
    """Async event processing."""
    # Async operations
    pass

service.register_post_hook("async_processor", async_hook)
```

## HTTP API

```python
# Get HTTP handler
handler = service.to_http_handler()

# Ingest single event
request = {
    "endpoint": "/ingest/event",
    "payload": {
        "event_type": "AppEvent",
        "data": {
            "event_id": "evt_001",
            "timestamp": "2024-11-24T10:00:00Z",
            "app_name": "com.apple.Safari",
            "schema_version": "1.0.0",
        },
    },
}

result = await handler(request)

# Get statistics
request = {"endpoint": "/stats", "payload": {}}
stats = await handler(request)

# Flush collector
request = {"endpoint": "/flush", "payload": {}}
result = await handler(request)
```

## Statistics

```python
# Get service statistics
stats = service.get_stats()

print(stats)
# {
#   'total_events': 1000,
#   'total_batches': 10,
#   'failed_events': 0,
#   'last_ingestion': '2024-11-24T10:30:00',
#   'collector': {...},
#   'materializer': {...}
# }

# Get collector statistics
collector_stats = service.collector.get_stats()

# Get cache statistics
cache_stats = service.materializer.get_cache_stats()
```

## Error Handling

```python
# Register error handler
def error_handler(error, context):
    print(f"Error: {error}")
    print(f"Context: {context}")

service.collector.register_error_handler(error_handler)

# Handle ingestion errors
result = service.ingest_event(event)
if result["status"] == "error":
    print(f"Ingestion failed: {result['error']}")
```

## Recovery

```python
from pathlib import Path

# Recover from corrupted JSONL file
corrupted_file = Path("events_20241124.jsonl")
recovered, corrupted = service.collector.recover_from_file(corrupted_file)

print(f"Recovered: {recovered} events")
print(f"Corrupted: {corrupted} lines")
```

## Best Practices

### 1. Use Batch Ingestion for Performance

```python
# Bad: Individual ingestion
for event in events:
    service.ingest_event(event)

# Good: Batch ingestion
service.ingest_batch(events)
```

### 2. Configure Appropriate Batch Sizes

```python
# For high-frequency events
config = IngestionConfig(
    collector=CollectorConfig(
        batch_size=1000,
        flush_interval_seconds=30,
    )
)

# For low-frequency events
config = IngestionConfig(
    collector=CollectorConfig(
        batch_size=10,
        flush_interval_seconds=300,
    )
)
```

### 3. Use Event Filtering

```python
config = IngestionConfig(
    filter=FilterConfig(
        excluded_apps=["com.apple.Spotlight"],
        min_duration_seconds=2.0,
        privacy_mode=True,
    )
)
```

### 4. Enable Incremental Updates

```python
config = IngestionConfig(
    feature=FeatureConfig(
        incremental_updates=True,
        cache_size=1000,
    )
)
```

### 5. Properly Manage Service Lifecycle

```python
try:
    service = IngestionService(config)
    service.start()

    # Process events
    service.ingest_batch(events)

finally:
    # Always flush and stop
    service.flush()
    service.stop()
```

## Performance Tuning

### Batch Size Optimization

- **Small batches (10-50)**: Low latency, higher overhead
- **Medium batches (100-500)**: Balanced performance
- **Large batches (1000+)**: Maximum throughput

### Flush Interval Tuning

- **Short intervals (10-30s)**: Near real-time processing
- **Medium intervals (60-300s)**: Balanced resource usage
- **Long intervals (600s+)**: Maximum efficiency

### Feature Configuration

```python
# Minimal features for better performance
config = FeatureConfig(
    enabled_features=["app_usage_time"],  # Only essential features
    cache_size=5000,  # Larger cache
)

# Comprehensive features
config = FeatureConfig(
    enabled_features=[
        "app_usage_time",
        "browser_domain_visits",
        "meeting_count",
        "context_switches",
    ],
    aggregation_windows=["1h", "1d", "1w"],
)
```

## API Reference

See individual module documentation:

- [Models API](./api/models.md)
- [Configuration API](./api/config.md)
- [Collectors API](./api/collectors.md)
- [Converters API](./api/converters.md)
- [Materializer API](./api/materializer.md)
- [Service API](./api/service.md)
