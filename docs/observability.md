# KGCL Observability Guide

Complete guide to OpenTelemetry instrumentation in KGCL.

## Overview

KGCL provides comprehensive observability through OpenTelemetry with:

- **Distributed Tracing**: Track operations across all subsystems
- **Metrics**: Monitor performance and resource usage
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Health Checks**: System diagnostics and connectivity monitoring

## Quick Start

### 1. Installation

Dependencies are automatically installed with KGCL:

```bash
uv pip install -e .
```

### 2. Basic Configuration

Configure via environment variables:

```bash
# Local development (console output)
export OTEL_SERVICE_NAME=kgcl
export KGCL_ENVIRONMENT=local
export OTEL_TRACES_EXPORTER=console
export OTEL_METRICS_EXPORTER=console

# Production (OTLP exporter)
export OTEL_SERVICE_NAME=kgcl
export KGCL_ENVIRONMENT=production
export OTEL_TRACES_EXPORTER=otlp_http
export OTEL_METRICS_EXPORTER=otlp_http
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

### 3. Health Check

```bash
# Check system health
kgc-health health

# Display configuration
kgc-health config

# Test tracing
kgc-health test-tracing --duration 30

# Test metrics
kgc-health test-metrics
```

## Configuration

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `OTEL_SERVICE_NAME` | Service name | `kgcl` | `kgcl-prod` |
| `KGCL_ENVIRONMENT` | Environment | `local` | `production` |
| `OTEL_TRACES_ENABLED` | Enable tracing | `true` | `true` |
| `OTEL_METRICS_ENABLED` | Enable metrics | `true` | `true` |
| `OTEL_LOGS_ENABLED` | Enable logging | `true` | `true` |
| `OTEL_TRACES_EXPORTER` | Trace exporter | `console` | `otlp_http` |
| `OTEL_METRICS_EXPORTER` | Metric exporter | `console` | `otlp_http` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP endpoint | `None` | `http://localhost:4318` |
| `OTEL_TRACES_SAMPLER` | Sampling strategy | `always_on` | `traceidratio` |
| `OTEL_TRACES_SAMPLER_ARG` | Sampling rate | `1.0` | `0.1` |
| `KGCL_LOG_LEVEL` | Log level | `INFO` | `DEBUG` |
| `KGCL_LOG_FORMAT` | Log format | `json` | `text` |

### Exporter Types

**Console Exporter** (Development):
```bash
export OTEL_TRACES_EXPORTER=console
export OTEL_METRICS_EXPORTER=console
```

**OTLP HTTP Exporter** (Production):
```bash
export OTEL_TRACES_EXPORTER=otlp_http
export OTEL_METRICS_EXPORTER=otlp_http
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

**OTLP gRPC Exporter**:
```bash
export OTEL_TRACES_EXPORTER=otlp_grpc
export OTEL_METRICS_EXPORTER=otlp_grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317
```

## Usage in Code

### Initialization

```python
from kgcl.observability import (
    configure_logging,
    configure_metrics,
    configure_tracing,
    ObservabilityConfig,
)

# Load from environment
config = ObservabilityConfig.from_env()

# Initialize all features
configure_logging(config)
configure_tracing(config)
configure_metrics(config)
```

### Distributed Tracing

```python
from kgcl.observability import get_tracer
from kgcl.observability.tracing import traced_operation

tracer = get_tracer(__name__)

# Automatic span creation with context manager
with traced_operation(
    tracer,
    "process_capability_event",
    attributes={"event_type": "window_focus", "app": "Chrome"}
) as span:
    # Your code here
    result = process_event(event)
    span.set_attribute("result_count", len(result))
```

### Manual Span Management

```python
from kgcl.observability import get_tracer

tracer = get_tracer(__name__)

with tracer.start_as_current_span("operation_name") as span:
    span.set_attribute("key", "value")
    # Your code here
    span.add_event("Processing started")
    # More code
    span.add_event("Processing completed")
```

### Metrics Recording

```python
from kgcl.observability.metrics import KGCLMetrics

metrics = KGCLMetrics()

# Record event ingestion
metrics.record_event_ingestion(
    event_type="capability_discovery",
    duration_ms=25.5,
    success=True
)

# Record LM call
metrics.record_lm_call(
    model="ollama/llama3.1",
    tokens=1024,
    duration_ms=150.0,
    success=True
)

# Record graph operation
metrics.record_graph_operation(
    operation="sparql_query",
    duration_ms=10.5,
    success=True
)

# Record cache access
metrics.record_cache_access(
    cache_name="template_cache",
    hit=True
)
```

### Structured Logging

```python
from kgcl.observability.logging import get_logger, set_correlation_id

logger = get_logger(__name__)

# Set correlation ID for request tracking
set_correlation_id("req-12345")

# Log with structured data
logger.info(
    "Processing capability event",
    extra={
        "event_type": "window_focus",
        "app_name": "Chrome",
        "duration_ms": 25.5,
    }
)

# JSON output:
# {
#   "timestamp": "2025-11-24 10:30:45",
#   "level": "INFO",
#   "logger": "kgcl.agent",
#   "message": "Processing capability event",
#   "correlation_id": "req-12345",
#   "event_type": "window_focus",
#   "app_name": "Chrome",
#   "duration_ms": 25.5
# }
```

## Subsystem Instrumentation

### PyObjC Agent

```python
from kgcl.observability.instruments.pyobjc_agent import (
    traced_capability_crawler,
    traced_collector,
)
from kgcl.observability.metrics import KGCLMetrics

class CapabilityCrawler:
    def __init__(self):
        self.metrics = KGCLMetrics()

    @traced_capability_crawler
    def crawl_applications(self):
        # Automatically instrumented
        apps = discover_running_apps()
        return apps

    @traced_collector("accessibility")
    def collect_accessibility_tree(self, app_name):
        # Automatically instrumented
        tree = get_ax_tree(app_name)
        return tree
```

### UnRDF Engine

```python
from kgcl.observability.instruments.unrdf_engine import (
    traced_ingestion,
    traced_graph_operation,
    traced_hook,
)

class UnRDFEngine:
    def __init__(self):
        self.metrics = KGCLMetrics()

    @traced_ingestion("capability_event")
    def ingest_event(self, event):
        # Automatically instrumented with metrics
        self.graph.add_triples(event.to_triples())

    @traced_graph_operation("query")
    def query(self, sparql):
        # Automatically instrumented
        return self.graph.query(sparql)

    @traced_hook("pre_ingestion")
    def validate_event(self, event):
        # Automatically instrumented
        return validate(event)
```

### TTL2DSpy

```python
from kgcl.observability.instruments.ttl2dspy import (
    traced_parser,
    traced_generator,
    traced_cache_operation,
)

class TTL2DSpy:
    def __init__(self):
        self.metrics = KGCLMetrics()
        self.cache = {}

    @traced_parser("turtle")
    def parse_turtle(self, content):
        # Automatically instrumented with parse metrics
        return parse(content)

    @traced_generator("dspy_signature")
    def generate_signature(self, schema):
        # Automatically instrumented with generation metrics
        return generate_code(schema)

    @traced_cache_operation("template")
    def get_cached(self, key):
        # Automatically instrumented with cache hit/miss metrics
        return self.cache.get(key)
```

### DSPy Runtime

```python
from kgcl.observability.instruments.dspy_runtime import (
    traced_lm_call,
    traced_prediction,
)

class LLMWrapper:
    def __init__(self, model="ollama/llama3.1"):
        self.model = model
        self.metrics = KGCLMetrics()

    @traced_lm_call("ollama/llama3.1")
    def call(self, prompt):
        # Automatically instrumented with token usage
        response = self.model.generate(prompt)
        return response

    @traced_prediction("capability_classifier")
    def predict(self, input_data):
        # Automatically instrumented
        return self.model.predict(input_data)
```

## Health Checks

### Built-in Checks

KGCL includes health checks for:

1. **Ollama Connectivity**: Verifies connection to Ollama service
2. **Graph Integrity**: Checks RDF graph health
3. **Observability Configuration**: Validates OTEL setup

### Custom Health Checks

```python
from kgcl.observability.health import register_health_check

def check_custom_service():
    """Check custom service health.

    Returns:
        tuple: (is_healthy, message, details)
    """
    try:
        # Your health check logic
        return (True, "Service healthy", {"status": "ok"})
    except Exception as e:
        return (False, f"Service unhealthy: {e}", {"error": str(e)})

# Register the check
register_health_check("custom_service", check_custom_service)
```

### CLI Health Check

```bash
# Run all health checks
kgc-health health

# Output:
# 🏥 KGCL System Health Check
# ==================================================
# Overall Status: HEALTHY
# Timestamp: 1732456789.123
#
# ✅ ollama
#    Status: healthy
#    Message: Connected to Ollama (3 models available)
#    Check Duration: 45.23ms
#    Details:
#       models: ['llama3.1', 'mistral', 'codellama']
#
# ✅ graph
#    Status: healthy
#    Message: Graph integrity check passed
#    Check Duration: 12.45ms
#
# ✅ observability
#    Status: healthy
#    Message: Observability configured
#    Check Duration: 1.23ms
```

## OpenTelemetry Collector Setup

### Docker Compose

```yaml
version: '3'
services:
  # OTEL Collector
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
    volumes:
      - ./otel-config.yaml:/etc/otel/config.yaml
    command: ["--config=/etc/otel/config.yaml"]

  # Jaeger for trace visualization
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "14250:14250"  # Jaeger gRPC

  # Prometheus for metrics
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

### OTEL Collector Config

```yaml
# otel-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s

exporters:
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true

  prometheus:
    endpoint: 0.0.0.0:8889

  logging:
    loglevel: debug

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger, logging]

    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus, logging]
```

### KGCL Configuration

```bash
export OTEL_TRACES_EXPORTER=otlp_http
export OTEL_METRICS_EXPORTER=otlp_http
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_EXPORTER_OTLP_INSECURE=true
```

## Metrics Reference

### Counter Metrics

| Metric | Description | Labels |
|--------|-------------|--------|
| `kgcl.events.ingested` | Events ingested | `event_type`, `success` |
| `kgcl.ingestion.errors` | Ingestion errors | `event_type` |
| `kgcl.graph.operations` | Graph operations | `operation`, `success` |
| `kgcl.lm.calls` | LM calls | `model`, `success` |
| `kgcl.lm.tokens` | Tokens used | `model`, `success` |
| `kgcl.lm.errors` | LM errors | `model` |
| `kgcl.parse.operations` | Parse operations | `parser`, `success` |
| `kgcl.parse.errors` | Parse errors | `parser` |
| `kgcl.cache.hits` | Cache hits | `cache` |
| `kgcl.cache.misses` | Cache misses | `cache` |
| `kgcl.features.generated` | Features generated | `generator` |
| `kgcl.capabilities.discovered` | Capabilities discovered | `type` |

### Histogram Metrics

| Metric | Description | Labels | Unit |
|--------|-------------|--------|------|
| `kgcl.ingestion.duration` | Ingestion duration | `event_type`, `success` | ms |
| `kgcl.graph.operation.duration` | Graph operation duration | `operation`, `success` | ms |
| `kgcl.graph.query.duration` | Graph query duration | `query_type` | ms |
| `kgcl.lm.call.duration` | LM call duration | `model`, `success` | ms |
| `kgcl.parse.duration` | Parse duration | `parser`, `success` | ms |
| `kgcl.features.generation.duration` | Feature generation duration | `generator` | ms |
| `kgcl.crawler.duration` | Crawler duration | `type` | ms |

## Best Practices

### 1. Always Use Context Managers

```python
# ✅ Good: Automatic cleanup and error handling
with traced_operation(tracer, "operation", attributes={"key": "value"}):
    do_work()

# ❌ Bad: Manual span management is error-prone
span = tracer.start_span("operation")
do_work()
span.end()
```

### 2. Add Meaningful Attributes

```python
# ✅ Good: Rich context
with traced_operation(
    tracer,
    "ingest_capability_event",
    attributes={
        "event_type": "window_focus",
        "app_name": "Chrome",
        "window_title": "GitHub - KGCL",
        "user_id": "user123",
    }
):
    process_event()

# ❌ Bad: Minimal context
with traced_operation(tracer, "process"):
    process_event()
```

### 3. Record Metrics Consistently

```python
# ✅ Good: Always record duration and success
start = time.perf_counter()
try:
    result = process()
    duration_ms = (time.perf_counter() - start) * 1000
    metrics.record_event_ingestion("event", duration_ms, success=True)
except Exception as e:
    duration_ms = (time.perf_counter() - start) * 1000
    metrics.record_event_ingestion("event", duration_ms, success=False)
    raise
```

### 4. Use Correlation IDs

```python
from kgcl.observability.logging import set_correlation_id

# Set at request boundary
correlation_id = str(uuid.uuid4())
set_correlation_id(correlation_id)

# All logs will include this correlation_id
logger.info("Processing started")
process()
logger.info("Processing completed")
```

### 5. Sampling in Production

```bash
# Use sampling to reduce overhead
export OTEL_TRACES_SAMPLER=traceidratio
export OTEL_TRACES_SAMPLER_ARG=0.1  # 10% sampling
```

## Troubleshooting

### Traces Not Appearing

1. Check OTLP endpoint connectivity:
   ```bash
   curl http://localhost:4318/v1/traces
   ```

2. Verify configuration:
   ```bash
   kgc-health config
   ```

3. Test with console exporter:
   ```bash
   export OTEL_TRACES_EXPORTER=console
   kgc-health test-tracing --duration 10
   ```

### High Overhead

1. Reduce sampling rate:
   ```bash
   export OTEL_TRACES_SAMPLER_ARG=0.01  # 1% sampling
   ```

2. Use batch processor (default)

3. Disable console export in production:
   ```bash
   export OTEL_CONSOLE_EXPORT=false
   ```

### Missing Metrics

1. Check metric reader interval (default: 60s)

2. Verify exporter configuration:
   ```bash
   kgc-health test-metrics
   ```

3. Check OTLP endpoint:
   ```bash
   curl http://localhost:4318/v1/metrics
   ```

## Examples

See `/Users/sac/dev/kgcl/docs/examples/observability_example.py` for complete examples.

## Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/)
- [OpenTelemetry Python SDK](https://opentelemetry-python.readthedocs.io/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
