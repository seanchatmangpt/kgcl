# KGCL Observability Quick Reference

Fast reference for OpenTelemetry instrumentation in KGCL.

## Installation

```bash
cd /Users/sac/dev/kgcl
uv pip install -e .
```

## Environment Configuration

### Local Development
```bash
export OTEL_TRACES_EXPORTER=console
export OTEL_METRICS_EXPORTER=console
export KGCL_LOG_FORMAT=text
```

### Production
```bash
export OTEL_SERVICE_NAME=kgcl-prod
export KGCL_ENVIRONMENT=production
export OTEL_TRACES_EXPORTER=otlp_http
export OTEL_METRICS_EXPORTER=otlp_http
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_TRACES_SAMPLER_ARG=0.1
export KGCL_LOG_LEVEL=WARNING
```

## CLI Commands

```bash
kgc-health health                  # Check system health
kgc-health config                  # Show configuration
kgc-health test-tracing            # Test tracing
kgc-health test-metrics            # Test metrics
```

## Quick Start Code

### Initialize Everything
```python
from kgcl.observability import (
    ObservabilityConfig,
    configure_logging,
    configure_metrics,
    configure_tracing,
)

config = ObservabilityConfig.from_env()
configure_logging(config)
configure_tracing(config)
configure_metrics(config)
```

### Tracing
```python
from kgcl.observability import get_tracer
from kgcl.observability.tracing import traced_operation

tracer = get_tracer(__name__)

with traced_operation(
    tracer,
    "operation_name",
    attributes={"key": "value"}
):
    # Your code here
    pass
```

### Metrics
```python
from kgcl.observability.metrics import KGCLMetrics

metrics = KGCLMetrics()
metrics.record_event_ingestion("event_type", 25.5, success=True)
metrics.record_lm_call("ollama/llama3.1", 512, 150.0, success=True)
metrics.record_graph_operation("query", 10.5, success=True)
metrics.record_cache_access("cache_name", hit=True)
```

### Logging
```python
from kgcl.observability.logging import get_logger, set_correlation_id

logger = get_logger(__name__)
set_correlation_id("req-12345")
logger.info("Message", extra={"key": "value"})
```

## Instrumentation Decorators

### PyObjC Agent
```python
from kgcl.observability.instruments.pyobjc_agent import (
    traced_capability_crawler,
    traced_collector,
)

@traced_capability_crawler
def crawl_apps(self):
    return discover()

@traced_collector("accessibility")
def collect_tree(self):
    return get_tree()
```

### UnRDF Engine
```python
from kgcl.observability.instruments.unrdf_engine import (
    traced_ingestion,
    traced_graph_operation,
)

@traced_ingestion("capability_event")
def ingest(self, event):
    self.graph.add(event)

@traced_graph_operation("query")
def query(self, sparql):
    return self.graph.query(sparql)
```

### TTL2DSpy
```python
from kgcl.observability.instruments.ttl2dspy import (
    traced_parser,
    traced_generator,
)

@traced_parser("turtle")
def parse(self, content):
    return parse_ttl(content)

@traced_generator("dspy_signature")
def generate(self, schema):
    return gen_code(schema)
```

### DSPy Runtime
```python
from kgcl.observability.instruments.dspy_runtime import (
    traced_lm_call,
    traced_prediction,
)

@traced_lm_call("ollama/llama3.1")
def call(self, prompt):
    return self.model.generate(prompt)

@traced_prediction("classifier")
def predict(self, data):
    return self.model.predict(data)
```

## Key Metrics

### Counters
- `kgcl.events.ingested` - Events by type
- `kgcl.lm.calls` - LM calls by model
- `kgcl.lm.tokens` - Tokens used
- `kgcl.graph.operations` - Graph ops
- `kgcl.cache.hits` - Cache hits
- `kgcl.cache.misses` - Cache misses

### Histograms
- `kgcl.ingestion.duration` - Ingestion latency
- `kgcl.lm.call.duration` - LM latency
- `kgcl.graph.query.duration` - Query latency
- `kgcl.parse.duration` - Parse latency

## Docker Stack

```bash
cd /Users/sac/dev/kgcl/docs/examples
docker-compose -f docker-compose.observability.yml up -d
```

Access:
- Jaeger: http://localhost:16686
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## Common Patterns

### Complete Operation with Metrics
```python
start = time.perf_counter()
try:
    with traced_operation(tracer, "op", {"type": "batch"}):
        result = process()
        metrics.record_event_ingestion("event", duration_ms, success=True)
except Exception as e:
    duration_ms = (time.perf_counter() - start) * 1000
    metrics.record_event_ingestion("event", duration_ms, success=False)
    raise
```

### Nested Operations
```python
with traced_operation(tracer, "parent"):
    for item in items:
        with traced_operation(tracer, "child", {"item": item}):
            process(item)
```

### Error Handling
```python
with traced_operation(tracer, "op") as span:
    try:
        result = dangerous_operation()
        span.set_attribute("success", True)
    except Exception as e:
        span.set_attribute("success", False)
        span.record_exception(e)
        raise
```

## Environment Variables

| Variable | Default | Production |
|----------|---------|------------|
| `OTEL_SERVICE_NAME` | `kgcl` | `kgcl-prod` |
| `KGCL_ENVIRONMENT` | `local` | `production` |
| `OTEL_TRACES_EXPORTER` | `console` | `otlp_http` |
| `OTEL_METRICS_EXPORTER` | `console` | `otlp_http` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `None` | `http://collector:4318` |
| `OTEL_TRACES_SAMPLER_ARG` | `1.0` | `0.1` |
| `KGCL_LOG_LEVEL` | `INFO` | `WARNING` |
| `KGCL_LOG_FORMAT` | `json` | `json` |

## Troubleshooting

### No traces in Jaeger
```bash
# Test endpoint
curl http://localhost:4318/v1/traces

# Check config
kgc-health config

# Use console output
export OTEL_TRACES_EXPORTER=console
```

### High overhead
```bash
# Reduce sampling
export OTEL_TRACES_SAMPLER_ARG=0.01

# Disable console
export OTEL_CONSOLE_EXPORT=false
```

### Missing metrics
```bash
# Wait 60s for export
sleep 60

# Test metrics
kgc-health test-metrics

# Check endpoint
curl http://localhost:4318/v1/metrics
```

## Files

### Core Package
- `/Users/sac/dev/kgcl/src/kgcl/observability/`

### Documentation
- `/Users/sac/dev/kgcl/docs/observability.md` - Complete guide
- `/Users/sac/dev/kgcl/OBSERVABILITY_IMPLEMENTATION.md` - Implementation details
- `/Users/sac/dev/kgcl/src/kgcl/observability/README.md` - Package README

### Examples
- `/Users/sac/dev/kgcl/docs/examples/observability_example.py` - Code examples
- `/Users/sac/dev/kgcl/docs/examples/docker-compose.observability.yml` - Docker stack
- `/Users/sac/dev/kgcl/docs/examples/.env.observability` - Config template
