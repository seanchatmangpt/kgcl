# KGCL Observability

Production-ready OpenTelemetry instrumentation for KGCL (Knowledge Geometry Calculus for Life).

## Features

- **Distributed Tracing**: Track operations across all subsystems with OpenTelemetry
- **Metrics**: Monitor performance with counters, histograms, and gauges
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Health Checks**: Built-in diagnostics for Ollama, graph integrity, and observability
- **Subsystem Instrumentation**: Pre-built decorators for PyObjC agent, UnRDF engine, TTL2DSpy, and DSPy runtime

## Quick Start

### 1. Install Dependencies

```bash
cd /Users/sac/dev/kgcl
uv pip install -e .
```

### 2. Configure Observability

```bash
# Console output (development)
export OTEL_TRACES_EXPORTER=console
export OTEL_METRICS_EXPORTER=console

# OTLP exporter (production)
export OTEL_TRACES_EXPORTER=otlp_http
export OTEL_METRICS_EXPORTER=otlp_http
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

### 3. Check Health

```bash
kgc-health health
kgc-health config
```

## Package Structure

```
observability/
├── __init__.py           # Public API
├── config.py             # Configuration management
├── tracing.py            # Distributed tracing
├── metrics.py            # Metrics collection
├── logging.py            # Structured logging
├── health.py             # Health checks
├── cli.py                # CLI commands
└── instruments/          # Subsystem instrumentation
    ├── __init__.py
    ├── pyobjc_agent.py   # PyObjC capability crawler
    ├── unrdf_engine.py   # RDF graph operations
    ├── ttl2dspy.py       # TTL to DSPy conversion
    └── dspy_runtime.py   # DSPy/LM calls
```

## Usage Examples

### Initialize Observability

```python
from kgcl.observability import (
    configure_logging,
    configure_metrics,
    configure_tracing,
    ObservabilityConfig,
)

config = ObservabilityConfig.from_env()
configure_logging(config)
configure_tracing(config)
configure_metrics(config)
```

### Distributed Tracing

```python
from kgcl.observability import get_tracer
from kgcl.observability.tracing import traced_operation

tracer = get_tracer(__name__)

with traced_operation(
    tracer,
    "process_event",
    attributes={"event_type": "window_focus", "app": "Chrome"}
):
    process_capability_event()
```

### Metrics Recording

```python
from kgcl.observability.metrics import KGCLMetrics

metrics = KGCLMetrics()

# Record event ingestion
metrics.record_event_ingestion("capability_discovery", duration_ms=25.5, success=True)

# Record LM call
metrics.record_lm_call("ollama/llama3.1", tokens=512, duration_ms=150.0, success=True)

# Record graph operation
metrics.record_graph_operation("sparql_query", duration_ms=10.5, success=True)
```

### Structured Logging

```python
from kgcl.observability.logging import get_logger, set_correlation_id

logger = get_logger(__name__)
set_correlation_id("req-12345")

logger.info("Processing event", extra={"event_type": "window_focus", "app": "Chrome"})
```

### Subsystem Instrumentation

```python
from kgcl.observability.instruments.pyobjc_agent import traced_capability_crawler

class CapabilityCrawler:
    @traced_capability_crawler
    def crawl_applications(self):
        # Automatically instrumented with tracing and metrics
        return discover_apps()
```

## CLI Commands

```bash
# Check system health
kgc-health health

# Display configuration
kgc-health config

# Test tracing (generate sample traces)
kgc-health test-tracing --duration 30

# Test metrics (generate sample metrics)
kgc-health test-metrics
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OTEL_SERVICE_NAME` | Service name | `kgcl` |
| `KGCL_ENVIRONMENT` | Environment (local, production) | `local` |
| `OTEL_TRACES_ENABLED` | Enable tracing | `true` |
| `OTEL_METRICS_ENABLED` | Enable metrics | `true` |
| `OTEL_TRACES_EXPORTER` | Trace exporter type | `console` |
| `OTEL_METRICS_EXPORTER` | Metric exporter type | `console` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint | `None` |
| `OTEL_TRACES_SAMPLER_ARG` | Sampling rate | `1.0` |
| `KGCL_LOG_LEVEL` | Log level | `INFO` |
| `KGCL_LOG_FORMAT` | Log format (json, text) | `json` |

## Metrics Reference

### Counters
- `kgcl.events.ingested` - Events ingested by type
- `kgcl.lm.calls` - Language model calls
- `kgcl.lm.tokens` - Tokens used
- `kgcl.graph.operations` - Graph operations
- `kgcl.cache.hits` / `kgcl.cache.misses` - Cache performance

### Histograms
- `kgcl.ingestion.duration` - Ingestion latency
- `kgcl.lm.call.duration` - LM call latency
- `kgcl.graph.query.duration` - Query latency
- `kgcl.parse.duration` - Parse latency

## Documentation

Full documentation: `/Users/sac/dev/kgcl/docs/observability.md`

Examples: `/Users/sac/dev/kgcl/docs/examples/observability_example.py`

## Architecture

### Tracing
- Uses OpenTelemetry SDK
- Supports console, OTLP (HTTP/gRPC), Jaeger, Zipkin exporters
- Parent-based sampling with configurable rate
- Automatic span creation with context managers

### Metrics
- Counter, histogram, and gauge metrics
- Pre-configured metrics for all subsystems
- 60-second export interval
- Supports console, OTLP, Prometheus exporters

### Logging
- Structured JSON logging
- Correlation IDs for request tracking
- Configurable log levels per module
- Integration with OpenTelemetry traces

### Health Checks
- Ollama connectivity check
- Graph integrity check
- Observability configuration check
- Extensible custom health checks

## OpenTelemetry Collector

Run with Docker Compose:

```bash
cd /Users/sac/dev/kgcl/docs/examples
docker-compose -f docker-compose.observability.yml up -d
```

Access:
- Jaeger UI: http://localhost:16686
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## Best Practices

1. **Use Context Managers**: Always use `traced_operation()` for automatic cleanup
2. **Add Meaningful Attributes**: Include context in span attributes
3. **Record Metrics Consistently**: Always record duration and success status
4. **Use Correlation IDs**: Set correlation IDs at request boundaries
5. **Sample in Production**: Use `traceidratio` sampler to reduce overhead

## Troubleshooting

### Traces Not Appearing
1. Verify OTLP endpoint: `curl http://localhost:4318/v1/traces`
2. Check configuration: `kgc-health config`
3. Test with console: `export OTEL_TRACES_EXPORTER=console`

### High Overhead
1. Reduce sampling: `export OTEL_TRACES_SAMPLER_ARG=0.1`
2. Disable console export: `export OTEL_CONSOLE_EXPORT=false`

### Missing Metrics
1. Check metric interval (default 60s)
2. Test metrics: `kgc-health test-metrics`
3. Verify endpoint: `curl http://localhost:4318/v1/metrics`

## Development

### Running Tests

```bash
cd /Users/sac/dev/kgcl
pytest tests/observability/
```

### Code Quality

```bash
# Linting
ruff check src/kgcl/observability/

# Type checking
mypy src/kgcl/observability/

# Formatting
ruff format src/kgcl/observability/
```

## License

See project LICENSE file.
