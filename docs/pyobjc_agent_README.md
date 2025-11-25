# PyObjC Agent - macOS Capability Discovery and Monitoring

A comprehensive system for discovering and continuously monitoring macOS capabilities through PyObjC frameworks.

## Features

### Framework Discovery
- Dynamic PyObjC framework loading
- API enumeration (classes, protocols, selectors)
- Capability metadata generation
- JSON-LD export for knowledge graph integration

### Plugin System
- **AppKit Plugin**: Frontmost app, running apps, window enumeration, workspace monitoring
- **Browser Plugin**: Safari/Chrome history access with read-only DB queries
- **Calendar Plugin**: EventKit integration for calendar events and availability

### Event Collectors
- Continuous sampling at configurable intervals
- Event batching for efficient I/O
- JSONL output for streaming ingestion
- Backpressure handling and buffering

### Feature Aggregation
- Time-windowed aggregation (hourly, daily, custom)
- Pre-computed features for UNRDF ingestion
- Application usage analytics
- Browser activity patterns
- Calendar-based context detection

### Production Features
- Daemonizable main loop
- OpenTelemetry instrumentation
- Graceful shutdown handling
- Comprehensive error handling
- Type hints throughout
- Full test coverage

## Installation

### Prerequisites
```bash
# Install PyObjC frameworks
pip install pyobjc-core
pip install pyobjc-framework-Cocoa
pip install pyobjc-framework-EventKit
pip install pyobjc-framework-Quartz

# Install OpenTelemetry
pip install opentelemetry-api
pip install opentelemetry-sdk
pip install opentelemetry-exporter-otlp-proto-grpc

# Install other dependencies
pip install pyyaml
```

### Optional: Install all PyObjC frameworks
```bash
pip install pyobjc
```

## Usage

### CLI Commands

#### Run Agent Daemon
```bash
# Run with default configuration
python -m kgcl.pyobjc_agent run

# Run with custom config
python -m kgcl.pyobjc_agent run --config config/pyobjc_agent.yaml

# Run with custom data directory
python -m kgcl.pyobjc_agent run --data-dir /path/to/data
```

#### Discover Capabilities
```bash
# Discover all frameworks
python -m kgcl.pyobjc_agent discover

# Discover specific framework
python -m kgcl.pyobjc_agent discover --framework AppKit

# Custom output path
python -m kgcl.pyobjc_agent discover --output capabilities.jsonld
```

#### Aggregate Collected Data
```bash
# Aggregate frontmost app data
python -m kgcl.pyobjc_agent aggregate data/frontmost_app.jsonl

# Custom window size and output
python -m kgcl.pyobjc_agent aggregate data/browser_history.jsonl \
  --window-hours 24 \
  --output aggregated_features.json
```

#### Check Status
```bash
python -m kgcl.pyobjc_agent status
```

#### Manage Configuration
```bash
# Generate default configuration
python -m kgcl.pyobjc_agent config --generate

# Validate configuration
python -m kgcl.pyobjc_agent config --validate config/pyobjc_agent.yaml
```

### Programmatic Usage

#### Initialize and Run Agent
```python
from kgcl.pyobjc_agent import create_default_agent

# Create agent with default config
agent = create_default_agent(data_dir="/path/to/data")

# Run daemon (blocks until interrupted)
agent.run()
```

#### Use Specific Collectors
```python
from kgcl.pyobjc_agent import (
    create_frontmost_app_collector,
    create_browser_history_collector,
    create_calendar_collector
)

# Create frontmost app collector
collector = create_frontmost_app_collector(
    interval_seconds=1.0,
    output_path="data/frontmost_app.jsonl"
)

# Start collecting
collector.start()

# ... do other work ...

# Stop collecting
collector.stop()
```

#### Discover Capabilities
```python
from kgcl.pyobjc_agent import PyObjCFrameworkCrawler, FrameworkName

# Create crawler
crawler = PyObjCFrameworkCrawler(safe_mode=True)

# Crawl specific framework
capabilities = crawler.crawl_framework(FrameworkName.APPKIT)

# Export as JSON-LD
crawler.export_capabilities(
    {"AppKit": capabilities},
    "appkit_capabilities.jsonld",
    format="jsonld"
)
```

#### Aggregate Features
```python
from kgcl.pyobjc_agent import (
    FrontmostAppAggregator,
    aggregate_jsonl_file
)

# Create aggregator
aggregator = FrontmostAppAggregator(window_size_hours=1.0)

# Aggregate from file
features = aggregate_jsonl_file(
    "data/frontmost_app.jsonl",
    aggregator,
    output_path="features.json"
)

# Access features
for feature in features:
    print(f"{feature.feature_name}: {feature.value} {feature.unit}")
```

## Configuration

### YAML Configuration File
```yaml
data_dir: /Users/sac/dev/kgcl/data
enable_otel: true
otlp_endpoint: http://localhost:4317
environment: development

collectors:
  frontmost_app:
    enabled: true
    interval: 1.0
    batch_size: 50
    batch_timeout_seconds: 60.0

  browser_history:
    enabled: true
    interval: 300.0
    batch_size: 10

  calendar:
    enabled: true
    interval: 300.0
```

### Environment Variables
Override configuration with environment variables:
- `PYOBJC_DATA_DIR`: Data output directory
- `PYOBJC_OTLP_ENDPOINT`: OpenTelemetry endpoint
- `PYOBJC_ENVIRONMENT`: Deployment environment

## Architecture

### Components

```
pyobjc_agent/
├── crawler.py           # Framework discovery
├── plugins/
│   ├── base.py         # Plugin interface
│   ├── appkit_plugin.py
│   ├── browser_plugin.py
│   └── calendar_plugin.py
├── collectors/
│   ├── base.py         # Collector interface
│   ├── frontmost_app_collector.py
│   ├── browser_history_collector.py
│   └── calendar_collector.py
├── aggregators.py      # Feature aggregation
├── agent.py           # Main daemon
└── __main__.py        # CLI entry point
```

### Data Flow

1. **Discovery Phase**:
   - Framework Crawler → PyObjC APIs → Capability Metadata → JSON-LD

2. **Collection Phase**:
   - Plugin → Capability Data → Collector → JSONL Events → Disk

3. **Aggregation Phase**:
   - JSONL Events → Aggregator → Time Windows → Features → JSON

4. **Integration Phase**:
   - JSON Features → UNRDF Ingestion → Knowledge Graph

## Entitlements and Permissions

### Required Permissions
- **AppKit (Basic)**: No special permissions
- **Browser History**: Full Disk Access
- **Calendar**: Calendar access permission
- **Accessibility**: Screen Recording/Accessibility (for window enumeration)

### Granting Permissions
1. System Preferences → Security & Privacy → Privacy
2. Add your Python application to:
   - Full Disk Access (for browser history)
   - Calendar (for calendar events)
   - Accessibility (for window enumeration)

## Output Formats

### JSONL Event Format
```json
{
  "collector_name": "frontmost_app",
  "timestamp": "2024-01-01T12:00:00.000000",
  "data": {
    "bundle_id": "com.apple.Safari",
    "app_name": "Safari",
    "process_id": 1234,
    "is_active": true,
    "is_switch": true
  },
  "metadata": {"plugin": "appkit"},
  "sequence_number": 42
}
```

### Aggregated Feature Format
```json
{
  "aggregated_at": "2024-01-01T13:00:00.000000",
  "event_count": 3600,
  "features": [
    {
      "feature": "app_usage_total_minutes",
      "value": 45.5,
      "unit": "minutes",
      "time_window": {
        "start": "2024-01-01T12:00:00",
        "end": "2024-01-01T13:00:00",
        "type": "hour"
      }
    }
  ]
}
```

### Capability JSON-LD Format
```json
{
  "@context": "https://kgcl.dev/ontology/macos",
  "@type": "framework",
  "name": "AppKit",
  "discoveredAt": "2024-01-01T12:00:00.000000",
  "capabilities": [
    {
      "@type": "capability",
      "className": "NSWorkspace",
      "selector": "frontmostApplication",
      "isObservable": true
    }
  ]
}
```

## Testing

### Run Unit Tests
```bash
# Run all tests
python -m pytest src/kgcl/pyobjc_agent/tests/

# Run specific test file
python -m pytest src/kgcl/pyobjc_agent/tests/test_crawler.py

# Run with coverage
python -m pytest --cov=kgcl.pyobjc_agent src/kgcl/pyobjc_agent/tests/
```

### Test Coverage
- Framework crawler: Unit and integration tests
- Plugin system: Mock plugins, registry tests
- Collectors: Event batching, JSONL output, error handling
- Aggregators: Time windowing, feature computation

## Monitoring

### OpenTelemetry Integration
The agent exports traces to an OTLP endpoint for observability:
- Agent lifecycle spans
- Collection operation spans
- Plugin initialization spans
- Error tracking

### Metrics
Access collector statistics:
```python
stats = collector.get_stats()
# {
#   "events_collected": 1000,
#   "events_written": 1000,
#   "batches_flushed": 10,
#   "buffer_size": 50,
#   "status": "running"
# }
```

## Troubleshooting

### Framework Not Loading
```
Error: Failed to load framework AppKit
Solution: pip install pyobjc-framework-Cocoa
```

### Permission Denied (Browser History)
```
Error: Failed to read Safari history
Solution: Grant Full Disk Access in System Preferences
```

### Calendar Access Denied
```
Error: Calendar access not authorized
Solution: Grant Calendar permission in System Preferences
```

### OTLP Connection Error
```
Error: Failed to connect to OTLP endpoint
Solution: Start OTEL collector or disable telemetry (enable_otel: false)
```

## Performance

### Resource Usage
- **CPU**: ~1-2% with default intervals
- **Memory**: ~50-100MB typical
- **Disk**: ~10-50MB per day (depending on activity)

### Optimization Tips
- Increase collection intervals for less active monitoring
- Adjust batch sizes for I/O efficiency
- Use appropriate buffer sizes for your workload
- Enable compression for long-term storage

## Roadmap

### Planned Features
- [ ] Additional plugins (Photos, Messages, Spotlight)
- [ ] Real-time streaming to knowledge graph
- [ ] Machine learning feature extraction
- [ ] Privacy-preserving aggregation modes
- [ ] Multi-user support
- [ ] Cloud storage integration

## License

Part of the KGCL project.

## Contributing

Contributions welcome! Please ensure:
- Type hints on all functions
- Comprehensive docstrings
- Unit tests for new features
- Error handling with safe defaults
- Read-only access to user data
