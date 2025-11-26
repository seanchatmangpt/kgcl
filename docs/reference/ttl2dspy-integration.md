# TTL2DSPy Integration Guide

## Quick Reference

### Module Location
```
/Users/sac/dev/kgcl/src/kgcl/ttl2dspy/
```

### Import in Python
```python
from kgcl.ttl2dspy import (
    OntologyParser,
    DSPyGenerator,
    UltraOptimizer,
    ModuleWriter,
    CacheConfig,
)
```

### CLI Commands
```bash
# All commands under: python -m kgcl.ttl2dspy
python -m kgcl.ttl2dspy parse <ttl-file>
python -m kgcl.ttl2dspy generate <ttl-file> <output-dir>
python -m kgcl.ttl2dspy validate <ttl-file>
python -m kgcl.ttl2dspy list <ttl-file>
python -m kgcl.ttl2dspy cache-stats
python -m kgcl.ttl2dspy clear-cache
```

### UNRDF Hook
```bash
echo '{"action": "generate", "ttl_path": "ontology.ttl", "output_dir": "out/"}' | \
  python -m kgcl.ttl2dspy.hooks
```

## Integration Patterns

### 1. As a Library

```python
from kgcl.ttl2dspy import UltraOptimizer, ModuleWriter

# Simple usage
optimizer = UltraOptimizer()
shapes = optimizer.parse_with_cache("ontology.ttl")
code = optimizer.generate_with_cache(shapes)

writer = ModuleWriter()
result = writer.write_module(code, "output.py", shapes_count=len(shapes))
```

### 2. As a CLI Tool

```bash
# In Makefile or build script
generate-signatures:
    python -m kgcl.ttl2dspy generate \
        ontologies/features.ttl \
        src/generated/ \
        --module-name feature_signatures \
        --receipt

# In CI/CD pipeline
validate-ontologies:
    for ttl in ontologies/*.ttl; do \
        python -m kgcl.ttl2dspy validate $$ttl || exit 1; \
    done
```

### 3. As UNRDF Capability

```python
import json
import subprocess

def invoke_ttl2dspy(ttl_content: str, output_dir: str) -> dict:
    """Invoke TTL2DSPy as UNRDF capability."""
    request = {
        "action": "generate",
        "ttl_content": ttl_content,
        "output_dir": output_dir,
    }

    proc = subprocess.run(
        ["python", "-m", "kgcl.ttl2dspy.hooks"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
    )

    return json.loads(proc.stdout)
```

## Real-World Workflow

### Ontology-Driven Development

```python
# 1. Define ontology (features.ttl)
"""
@prefix kgcl: <http://kgcl.io/> .

kgcl:EntityExtractionShape a sh:NodeShape ;
    rdfs:comment "Extract named entities" ;
    sh:property [
        sh:path kgcl:text ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
    ] ;
    sh:property [
        sh:path kgcl:entities ;
        sh:datatype xsd:string ;
    ] .
"""

# 2. Generate signatures
from kgcl.ttl2dspy import UltraOptimizer, ModuleWriter

optimizer = UltraOptimizer()
shapes = optimizer.parse_with_cache("features.ttl")
code = optimizer.generate_with_cache(shapes)

writer = ModuleWriter()
writer.write_module(code, "src/signatures.py")

# 3. Use in application
from src.signatures import EntityExtractionSignature
import dspy

dspy.settings.configure(lm=dspy.OpenAI(model="gpt-4"))

extractor = dspy.Predict(EntityExtractionSignature)
result = extractor(text="Apple Inc. was founded by Steve Jobs.")
print(result.entities)  # ["Apple Inc.", "Steve Jobs"]
```

### Automated Pipeline

```bash
#!/bin/bash
# build-signatures.sh

set -e

ONTOLOGY_DIR="ontologies"
OUTPUT_DIR="src/generated"

echo "Building DSPy signatures from ontologies..."

# Validate all ontologies
for ttl in $ONTOLOGY_DIR/*.ttl; do
    echo "Validating $ttl..."
    python -m kgcl.ttl2dspy validate "$ttl"
done

# Generate signatures
for ttl in $ONTOLOGY_DIR/*.ttl; do
    base=$(basename "$ttl" .ttl)
    echo "Generating signatures from $ttl..."
    python -m kgcl.ttl2dspy generate \
        "$ttl" \
        "$OUTPUT_DIR" \
        --module-name "${base}_signatures" \
        --receipt
done

echo "✓ All signatures generated successfully"
```

## Advanced Configuration

### Custom Caching Strategy

```python
from kgcl.ttl2dspy import UltraOptimizer, CacheConfig
from pathlib import Path

# Development: fast iteration, no persistent cache
dev_config = CacheConfig(
    memory_cache_enabled=True,
    disk_cache_enabled=False,
    redis_enabled=False,
)

# Production: full caching with Redis
prod_config = CacheConfig(
    memory_cache_enabled=True,
    disk_cache_enabled=True,
    disk_cache_dir=Path("/var/cache/ttl2dspy"),
    max_disk_cache_age=86400,  # 24 hours
    redis_enabled=True,
    redis_url="redis://localhost:6379",
    redis_ttl=3600,  # 1 hour
)

optimizer = UltraOptimizer(prod_config)
```

### Batch Processing

```python
from kgcl.ttl2dspy import UltraOptimizer, ModuleWriter
from pathlib import Path

def process_ontologies(ontology_dir: Path, output_dir: Path):
    """Process all TTL files in a directory."""
    optimizer = UltraOptimizer()
    writer = ModuleWriter()

    ttl_files = list(ontology_dir.glob("*.ttl"))

    # Parse all files (cached)
    all_shapes = optimizer.batch_parse(ttl_files)

    # Generate modules
    for ttl_file, shapes in all_shapes.items():
        if not shapes:
            continue

        module_name = Path(ttl_file).stem + "_signatures"
        code = optimizer.generate_with_cache(shapes)

        result = writer.write_module(
            code=code,
            output_path=output_dir / f"{module_name}.py",
            shapes_count=len(shapes),
            ttl_source=ttl_file,
        )

        print(f"✓ {ttl_file}: {result.signatures_count} signatures")

    # Export metrics
    writer.export_metrics(output_dir / "metrics.json")
```

### Custom Post-Processing

```python
from kgcl.ttl2dspy import DSPyGenerator, SignatureDefinition

def customize_signature(sig: SignatureDefinition) -> SignatureDefinition:
    """Add custom base classes or fields."""
    sig.base_classes.append("CustomValidationMixin")
    return sig

generator = DSPyGenerator()
shapes = optimizer.parse_with_cache("ontology.ttl")

for shape in shapes:
    sig = generator.generate_signature(shape)
    sig = customize_signature(sig)
    code = sig.generate_code()
    # ... write code
```

## Testing Generated Signatures

```python
import pytest
from src.generated.signatures import TextSummarizationSignature

def test_signature_structure():
    """Test that signature has expected fields."""
    # Check input fields
    assert hasattr(TextSummarizationSignature, "text")
    assert hasattr(TextSummarizationSignature, "max_length")

    # Check output fields
    assert hasattr(TextSummarizationSignature, "summary")

def test_signature_with_dspy(mocker):
    """Test signature with mocked DSPy."""
    import dspy

    # Mock the LM
    mocker.patch.object(dspy, "OpenAI")

    predictor = dspy.Predict(TextSummarizationSignature)
    # ... test with mock responses
```

## Monitoring and Metrics

### Track Generation Performance

```python
from kgcl.ttl2dspy import UltraOptimizer
import time

optimizer = UltraOptimizer()

start = time.time()
shapes = optimizer.parse_with_cache("large_ontology.ttl")
parse_time = time.time() - start

start = time.time()
code = optimizer.generate_with_cache(shapes)
gen_time = time.time() - start

stats = optimizer.get_detailed_stats()

print(f"Parse: {parse_time:.3f}s")
print(f"Generate: {gen_time:.3f}s")
print(f"Cache hit rate: {stats['cache']['memory_hit_rate']:.2%}")
```

### Integrate with OpenTelemetry

```python
from opentelemetry import trace
from kgcl.ttl2dspy import UltraOptimizer

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("generate_signatures"):
    optimizer = UltraOptimizer()

    with tracer.start_as_current_span("parse_ontology"):
        shapes = optimizer.parse_with_cache("ontology.ttl")

    with tracer.start_as_current_span("generate_code"):
        code = optimizer.generate_with_cache(shapes)

    with tracer.start_as_current_span("write_module"):
        writer.write_module(code, "output.py")
```

## Troubleshooting

### Issue: Generated signatures have wrong types

**Cause**: SHACL shape missing datatype or minCount
**Solution**: Add explicit sh:datatype and sh:minCount to properties

```turtle
# Before (ambiguous)
sh:property [
    sh:path kgcl:value ;
] .

# After (explicit)
sh:property [
    sh:path kgcl:value ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
    rdfs:comment "The value to process" ;
] .
```

### Issue: Properties categorized incorrectly

**Cause**: Heuristic categorization fails for your ontology
**Solution**: Use sh:minCount or sh:defaultValue to mark inputs

```turtle
# Mark as input with minCount
sh:property [
    sh:path kgcl:input_field ;
    sh:minCount 1 ;  # This marks it as input
] .

# Mark as input with defaultValue
sh:property [
    sh:path kgcl:optional_param ;
    sh:defaultValue "default" ;  # This also marks it as input
] .
```

### Issue: Cache not working

**Cause**: File modified or cache disabled
**Solution**: Check cache config and file mtimes

```python
optimizer = UltraOptimizer()
stats = optimizer.get_detailed_stats()
print(stats)  # Check cache hit rates

# Clear cache if stale
optimizer.clear_all_caches()
```

## Best Practices

1. **Version Control**: Track generated files in git for visibility
2. **CI/CD Validation**: Always validate ontologies in CI
3. **Caching**: Use disk cache in production for faster builds
4. **Documentation**: Keep SHACL comments up-to-date (they become docstrings)
5. **Testing**: Test generated signatures with unit tests
6. **Monitoring**: Track generation metrics over time

## Examples

See `/Users/sac/dev/kgcl/examples/ttl2dspy/` for:
- `example_ontology.ttl`: Complete SHACL ontology
- `usage_example.py`: Full working example
- `README.md`: Comprehensive guide
- `generated/`: Sample generated signatures

## Support

For issues or questions:
1. Check the examples directory
2. Review the test suite for usage patterns
3. Consult the main documentation at `docs/ttl2dspy-summary.md`
