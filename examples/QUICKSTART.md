# Quick Start Guide

Get the KGC OS Graph Agent pipeline running in **< 1 minute**.

## Run the Demo

```bash
cd /Users/sac/dev/kgcl/examples

# Option 1: Use the quick runner
./run_demo.sh --verbose

# Option 2: Run Python directly
python full_pipeline_demo.py --verbose

# Option 3: Generate a full week
python full_pipeline_demo.py --days 7 --verbose
```

## What Happens

The pipeline executes in **< 5 seconds** and generates:

1. **25-50 synthetic events** (apps, browser, calendar)
2. **15-25 materialized features** (usage time, switches, domains)
3. **75+ RDF triples** in knowledge graph
4. **Daily brief** (AI-generated summary)
5. **Weekly retro** (AI-generated insights)
6. **Visualizations** (ASCII timelines and charts)

## Check the Results

```bash
# View the daily brief
cat sample_outputs/daily_brief.md

# View the weekly retrospective
cat sample_outputs/weekly_retro.md

# Examine feature values
cat sample_outputs/feature_values.json | jq

# Check graph statistics
cat sample_outputs/graph_stats.json | jq

# Inspect RDF knowledge graph
head -50 sample_outputs/knowledge_graph.ttl
```

## Run Tests

```bash
pytest test_full_example.py -v
```

All 15 tests should pass:
- Pipeline completion
- Output file generation
- Content validation
- JSON structure
- RDF format
- Performance benchmarks

## Expected Output

```
================================================================================
                        KGC OS Graph Agent Pipeline Demo
================================================================================

Step 1: Generating Synthetic Activity Data
-------------------------------------------
  ✓ Generated 25 events in 0.001s

Step 2: Ingesting into UNRDF Engine
-----------------------------------
  ✓ Ingested 25 events in 0.003s
    - RDF triples: 75

[... continues through 9 steps ...]

✅ Pipeline completed successfully in 1.23s

📊 Results:
   - Events processed: 25
   - Features computed: 18
   - RDF triples: 75
```

## Customization Examples

### Generate More Data

```bash
python full_pipeline_demo.py --days 7 --verbose
```

### Change Output Directory

```bash
python full_pipeline_demo.py --output-dir ./my_results
```

### Use Real Ollama (requires Ollama running)

```bash
ollama serve  # In another terminal
python full_pipeline_demo.py --use-ollama --verbose
```

## File Structure

After running, you'll have:

```
examples/
├── sample_outputs/
│   ├── daily_brief.md          # 1.3KB - AI brief
│   ├── weekly_retro.md         # 2.1KB - AI retro
│   ├── feature_values.json     # 4.0KB - All features
│   ├── graph_stats.json        # 613B - Metrics
│   └── knowledge_graph.ttl     # 3.7KB - Full RDF graph
├── full_pipeline_demo.py       # Main demo (800+ lines)
├── sample_data.py              # Data generator (400+ lines)
├── visualize.py                # Visualizations (300+ lines)
├── test_full_example.py        # Integration tests (300+ lines)
└── README.md                   # Full documentation
```

## Common Issues

### Import Error

```bash
# Install dependencies
pip install -e ..
```

### Missing pyshacl

```bash
pip install pyshacl rdflib
```

### Permission Error

```bash
chmod +x run_demo.sh
```

## Next Steps

1. **Read the full README.md** for detailed documentation
2. **Examine the output files** to understand the data
3. **Modify sample_data.py** to customize activity patterns
4. **Extend the pipeline** with custom features
5. **Integrate real data** from your OS

## Key Features Demonstrated

- **UNRDF Engine**: RDF triple store with transactions and provenance
- **Feature Materialization**: Aggregated metrics from raw events
- **SHACL Validation**: Schema generation for features
- **TTL2DSPy**: Automatic DSPy signature generation
- **DSPy Integration**: AI-powered brief and retro generation
- **OpenTelemetry**: Full distributed tracing
- **Multi-format Export**: Markdown, JSON, Turtle
- **ASCII Visualizations**: Timelines, charts, patterns

## Performance

- **Total time**: < 5 seconds
- **Data generation**: < 100ms
- **UNRDF ingestion**: < 10ms
- **Feature materialization**: < 5ms
- **Export**: < 50ms
- **Visualization**: < 10ms

## Documentation

- [README.md](./README.md) - Full documentation (300+ lines)
- [Test suite](./test_full_example.py) - 15 integration tests
- [Sample data](./sample_data.py) - Realistic activity generation
- [Visualizer](./visualize.py) - ASCII charts and timelines

---

**Ready to explore? Run `./run_demo.sh --verbose` now!**
