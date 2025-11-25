# KGC OS Graph Agent Pipeline - Complete Example

This directory contains a **complete, runnable demonstration** of the KGC OS Graph Agent pipeline, showcasing every major component working together end-to-end.

## What This Example Demonstrates

The pipeline executes these steps sequentially:

1. **Generate Synthetic Data** - Realistic 24-hour activity patterns
2. **Ingest into UNRDF** - Store events in RDF knowledge graph with provenance
3. **Materialize Features** - Compute aggregated features (app time, switches, domains, meetings)
4. **Generate SHACL Shapes** - Create validation schemas for features
5. **Generate DSPy Signatures** - Convert shapes to typed DSPy interfaces
6. **Generate Daily Brief** - AI-generated summary of daily activity
7. **Generate Weekly Retro** - AI-generated retrospective analysis
8. **Export Results** - Output in multiple formats (Markdown, JSON, Turtle)
9. **Visualize** - ASCII charts and timelines

### Full Observability

Every step is instrumented with **OpenTelemetry** spans, providing:
- Detailed timing metrics
- Attribute tracking
- Distributed tracing support
- Performance profiling

## Quick Start

### Run the Complete Example

```bash
# From the examples directory
cd /Users/sac/dev/kgcl/examples

# Run with default settings (1 day, mock LLM)
python full_pipeline_demo.py

# Run with verbose output
python full_pipeline_demo.py --verbose

# Generate a full week of data
python full_pipeline_demo.py --days 7 --verbose

# Try using real Ollama (requires Ollama running locally)
python full_pipeline_demo.py --use-ollama --verbose

# Custom output directory
python full_pipeline_demo.py --output-dir ./my_results --verbose
```

### Expected Output

The pipeline completes in **< 5 seconds** and produces:

```
================================================================================
           KGC OS Graph Agent Pipeline Demo
================================================================================

Step 1: Generating Synthetic Activity Data
-------------------------------------------
  ✓ Generated 47 events in 0.023s
    - AppEvents: 32
    - BrowserVisits: 13
    - CalendarBlocks: 2

Step 2: Ingesting into UNRDF Engine
------------------------------------
  ✓ Ingested 47 events in 0.156s
    - RDF triples: 141
    - Provenance records: 141

Step 3: Materializing Features
-------------------------------
  ✓ Materialized 23 features in 0.042s
    - app: 8
    - browser: 7
    - context: 1
    - meeting: 2

[... continues through all 9 steps ...]

Pipeline Summary
================================================================================

Total Execution Time: 1.234s

Step Breakdown:
  Data Generation                      0.023s  (  1.9%)
  Unrdf Ingestion                      0.156s  ( 12.6%)
  Feature Materialization              0.042s  (  3.4%)
  Shacl Generation                     0.008s  (  0.6%)
  Dspy Signature Generation            0.003s  (  0.2%)
  Daily Brief Generation               0.089s  (  7.2%)
  Weekly Retro Generation              0.067s  (  5.4%)
  Export                               0.234s  ( 19.0%)
  Visualization                        0.012s  (  1.0%)

================================================================================

✅ Pipeline completed successfully in 1.23s

📊 Results:
   - Events processed: 47
   - Features computed: 23
   - RDF triples: 141

📁 Output directory: /Users/sac/dev/kgcl/examples/sample_outputs
```

### Output Files

The pipeline generates these files in `sample_outputs/`:

```
sample_outputs/
├── daily_brief.md          # AI-generated daily summary
├── weekly_retro.md         # AI-generated weekly retrospective
├── feature_values.json     # All computed features
├── graph_stats.json        # Graph statistics and metrics
└── knowledge_graph.ttl     # Complete RDF knowledge graph
```

## Understanding the Components

### 1. Sample Data Generator (`sample_data.py`)

Generates realistic activity patterns:

**Morning (8-11am)**: Deep work sessions
- Extended focus in code editors (2-3 hours)
- Minimal context switches
- Occasional documentation lookups

**Late Morning (11am-12pm)**: Research phase
- Frequent browser navigation
- Multiple short sessions (1-5 minutes each)
- Documentation and Stack Overflow
- Quick Slack/email checks

**Midday (12-2pm)**: Meetings
- Daily standup (15 minutes)
- Project sync meetings (30-60 minutes)
- Video conferencing apps

**Afternoon (2-5pm)**: Mixed work
- Alternating coding and collaboration
- 30-60 minute coding blocks
- 5-15 minute communication breaks

**Evening (5-6pm)**: Wrap-up
- Email inbox review
- Documentation updates
- Planning for tomorrow

**Weekend**: Light activity
- Occasional email checks
- Brief planning sessions

### 2. Feature Materialization

The pipeline computes these features:

**App Usage Time**:
- Total time per application
- Aggregated by time window (1h, 1d, 1w)
- Tracks: VSCode, PyCharm, Slack, Safari, etc.

**Browser Domain Visits**:
- Visit counts per domain
- Unique URL tracking
- Tracks: github.com, stackoverflow.com, docs.python.org, etc.

**Meeting Count**:
- Total meetings per window
- Aggregate duration
- Average meeting length

**Context Switches**:
- Application transition count
- Switch frequency
- Focus time indicators

### 3. UNRDF Knowledge Graph

Events are stored as RDF triples with:

- **Full provenance**: Who, when, why, source for each triple
- **Transactions**: Atomic batch ingestion with rollback capability
- **SPARQL queries**: Full querying support
- **Schema validation**: SHACL-based validation
- **Persistence**: Turtle format serialization

Example triples:

```turtle
<http://kgcl.example.org/event/evt_000001>
    a <http://kgcl.example.org/AppEvent> ;
    kgcl:appName "com.microsoft.VSCode" ;
    kgcl:timestamp "2024-11-24T08:00:00" ;
    kgcl:duration 7200.5 .
```

### 4. DSPy Integration

The pipeline generates DSPy signatures like:

```python
class DailyBriefSignature(dspy.Signature):
    """Generate a daily brief from activity features."""

    # Input fields
    app_usage: str = dspy.InputField(desc="Application usage summary")
    browser_activity: str = dspy.InputField(desc="Browser activity summary")
    meetings: str = dspy.InputField(desc="Meeting summary")
    context_switches: int = dspy.InputField(desc="Number of context switches")

    # Output fields
    activity_summary: str = dspy.OutputField(desc="Summary of daily activity")
    top_apps: str = dspy.OutputField(desc="Most used applications")
    key_insights: str = dspy.OutputField(desc="Key insights from the day")
```

### 5. Visualization

ASCII-based visualizations include:

**Timeline**: Hour-by-hour activity density
```
Hour:  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23
       .  .  .  .  .  .  .  .  █  █  █  ▄  ▂  ▄  ▄  ▂  ▄  .  .  .  .  .  .  .
```

**Feature Charts**: Top features by value
```
app_usage_time_VSCode         ████████████████████████ 10.5h
app_usage_time_Slack          ████████████ 5.2h
browser_domain_visits_github  ████████ 42
```

**Pattern Highlights**: Key insights
- Most used applications
- Most visited domains
- Context switch frequency
- Meeting load analysis

## Customization

### Generate Custom Activity Patterns

```python
from sample_data import ActivityGenerator

generator = ActivityGenerator()

# Generate specific day patterns
weekday_events = generator.generate_day(day_offset=0)
weekend_events = generator.generate_day(day_offset=6, include_weekend_pattern=True)

# Generate custom week
week_events = generator.generate_week(start_offset=0)
```

### Modify Feature Configuration

```python
from kgcl.ingestion.config import FeatureConfig

config = FeatureConfig(
    enabled_features=[
        "app_usage_time",
        "browser_domain_visits",
        "meeting_count",
        "context_switches",
        # Add custom features here
    ],
    aggregation_windows=["1h", "4h", "1d", "1w"],  # Custom windows
    incremental_updates=True,
)
```

### Use Real Ollama

If you have Ollama running locally:

```bash
# Start Ollama (if not running)
ollama serve

# Pull a model
ollama pull llama3.2

# Run pipeline with Ollama
python full_pipeline_demo.py --use-ollama --verbose
```

The pipeline will automatically:
1. Detect Ollama availability
2. Initialize DSPy with OllamaLM
3. Generate real LLM-powered briefs and retros
4. Fall back to mock generation if Ollama unavailable

### Extend with Custom Features

Add new feature types in `materializer.py`:

```python
def _compute_custom_feature(
    self,
    events: list[Event],
    window_start: datetime,
    window_end: datetime,
) -> list[MaterializedFeature]:
    """Compute custom feature logic."""
    # Your feature computation here
    return features
```

Register in `FeatureConfig`:

```python
enabled_features=[
    # ... existing features ...
    "custom_feature",
]
```

## Running Tests

```bash
# Run the integration test
cd /Users/sac/dev/kgcl
pytest examples/test_full_example.py -v

# Run with coverage
pytest examples/test_full_example.py --cov=examples --cov-report=term
```

## Performance Notes

The example is optimized for demonstration speed:

- **< 5 seconds** total execution time
- **< 100ms** per pipeline step (most steps)
- **Efficient batching**: Transaction-based ingestion
- **Lazy evaluation**: Features computed on-demand
- **Minimal I/O**: All processing in-memory except final export

For production use:
- Enable persistent storage
- Use real Ollama for generation
- Enable OTLP export for traces
- Scale with batch processing

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Pipeline Orchestrator                        │
└───────────┬─────────────────────────────────────────────────────┘
            │
            ├──> 1. Sample Data Generator
            │        │
            │        └──> Realistic activity events
            │
            ├──> 2. UNRDF Engine
            │        │
            │        ├──> RDF triple store
            │        ├──> Transaction management
            │        └──> Provenance tracking
            │
            ├──> 3. Feature Materializer
            │        │
            │        ├──> App usage time
            │        ├──> Browser visits
            │        ├──> Meeting counts
            │        └──> Context switches
            │
            ├──> 4. SHACL Shape Generator
            │        │
            │        └──> Feature validation schemas
            │
            ├──> 5. TTL2DSPy
            │        │
            │        └──> DSPy Signature classes
            │
            ├──> 6. DSPy Runtime
            │        │
            │        ├──> OllamaLM configuration
            │        ├──> Signature invocation
            │        └──> Receipt generation
            │
            ├──> 7. Export Engine
            │        │
            │        ├──> Markdown (daily brief, weekly retro)
            │        ├──> JSON (features, stats)
            │        └──> Turtle (knowledge graph)
            │
            └──> 8. Visualizer
                     │
                     ├──> ASCII timelines
                     ├──> Feature charts
                     └──> Pattern highlights
```

## Observability Integration

The example demonstrates full OpenTelemetry instrumentation:

### Tracing

Every pipeline step creates spans:

```python
with traced_operation(tracer, "pipeline.generate_data", {"days": days}):
    events = generate_sample_data(days=days)
```

### Attributes

Spans include rich metadata:

- Event counts
- Feature types
- Processing times
- Success indicators
- Error details

### Export Options

Configure trace export:

```python
from kgcl.observability.config import ObservabilityConfig

config = ObservabilityConfig(
    enable_tracing=True,
    trace_exporter="otlp_http",  # or "console", "jaeger", "zipkin"
    otlp_endpoint="http://localhost:4318",
)
```

### Metrics

The pipeline tracks:

- **Latency**: Per-step execution time
- **Throughput**: Events/features processed
- **Resource usage**: Memory, CPU
- **Success rates**: Step completion rates

## Troubleshooting

### Import Errors

If you see import errors:

```bash
# Ensure you're in the examples directory
cd /Users/sac/dev/kgcl/examples

# Run with Python path set
PYTHONPATH=/Users/sac/dev/kgcl/src python full_pipeline_demo.py
```

### Ollama Connection Issues

If Ollama connection fails:

```bash
# Check Ollama is running
curl http://localhost:11434/api/version

# Pull required model
ollama pull llama3.2

# Run pipeline without Ollama (uses mock)
python full_pipeline_demo.py  # Don't use --use-ollama flag
```

### Memory Issues

For large datasets:

```python
# Use smaller time windows
config = FeatureConfig(
    aggregation_windows=["1h", "1d"],  # Remove "1w"
)

# Process in smaller batches
for day in range(7):
    events = generate_sample_data(days=1, start_date=base_date + timedelta(days=day))
    # Process each day separately
```

## Next Steps

After running this example:

1. **Explore the outputs**: Read the generated briefs and examine the JSON data
2. **Customize patterns**: Modify `sample_data.py` to match your workflow
3. **Add features**: Extend `materializer.py` with domain-specific features
4. **Integrate real data**: Replace synthetic data with actual OS events
5. **Deploy observability**: Export traces to Jaeger/Grafana for monitoring
6. **Scale up**: Process weeks/months of historical data

## Related Documentation

- [UNRDF Engine](../src/kgcl/unrdf_engine/README.md) - RDF triple store details
- [Feature Materialization](../src/kgcl/ingestion/README.md) - Feature computation
- [TTL2DSPy](../src/kgcl/ttl2dspy/README.md) - Signature generation
- [DSPy Runtime](../src/kgcl/dspy_runtime/README.md) - LLM integration
- [Observability](../src/kgcl/observability/README.md) - Tracing and metrics

## Support

For issues or questions:

1. Check existing [GitHub issues](https://github.com/user/kgcl/issues)
2. Review [documentation](https://user.github.io/kgcl)
3. Open a new issue with:
   - Error message
   - Command used
   - Python version
   - OS details

## License

Same as parent project - see [LICENSE](../LICENSE)

---

**Happy exploring the KGC OS Graph Agent pipeline!**
