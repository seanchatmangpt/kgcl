# TTL2DSPy Examples

This directory contains examples of using TTL2DSPy to generate DSPy signatures from SHACL ontologies.

## Example Ontology

`example_ontology.ttl` contains SHACL shapes for common LLM tasks:

- **TextSummarization**: Generate concise summaries
- **QuestionAnswering**: Answer questions from context
- **SentimentAnalysis**: Analyze text sentiment
- **TextTranslation**: Translate between languages
- **CodeGeneration**: Generate code from descriptions

## Quick Start

### 1. Parse and Validate

```bash
python -m kgcl.ttl2dspy parse examples/ttl2dspy/example_ontology.ttl
```

### 2. Generate DSPy Signatures

```bash
python -m kgcl.ttl2dspy generate \
    examples/ttl2dspy/example_ontology.ttl \
    examples/ttl2dspy/generated \
    --module-name llm_signatures \
    --receipt
```

### 3. List Available Shapes

```bash
python -m kgcl.ttl2dspy list examples/ttl2dspy/example_ontology.ttl --verbose
```

### 4. Validate SHACL Shapes

```bash
python -m kgcl.ttl2dspy validate examples/ttl2dspy/example_ontology.ttl
```

## Using Generated Signatures

After generation, you can use the signatures in your DSPy programs:

```python
import dspy
from examples.ttl2dspy.generated.llm_signatures import (
    TextSummarizationSignature,
    QuestionAnsweringSignature,
    SentimentAnalysisSignature,
)

# Configure DSPy
lm = dspy.OpenAI(model="gpt-4")
dspy.settings.configure(lm=lm)

# Use signatures
summarizer = dspy.Predict(TextSummarizationSignature)
result = summarizer(
    text="Long text to summarize...",
    max_length=50
)
print(result.summary)

qa = dspy.ChainOfThought(QuestionAnsweringSignature)
answer = qa(
    question="What is the capital of France?",
    context="France is a country in Europe. Its capital is Paris."
)
print(answer.answer)
```

## Python API Usage

```python
from kgcl.ttl2dspy import UltraOptimizer, ModuleWriter

# Create optimizer
optimizer = UltraOptimizer()

# Parse ontology
shapes = optimizer.parse_with_cache("example_ontology.ttl")

# Generate code
code = optimizer.generate_with_cache(shapes)

# Write module
writer = ModuleWriter()
result = writer.write_module(
    code=code,
    output_path="generated/signatures.py",
    shapes_count=len(shapes),
)

print(f"Generated {result.signatures_count} signatures")
```

## UNRDF Hooks Integration

Use as an external capability via stdin/stdout:

```python
import json
import subprocess

request = {
    "action": "generate",
    "ttl_path": "example_ontology.ttl",
    "output_dir": "generated",
    "module_name": "signatures",
}

proc = subprocess.run(
    ["python", "-m", "kgcl.ttl2dspy.hooks"],
    input=json.dumps(request),
    capture_output=True,
    text=True,
)

receipt = json.loads(proc.stdout)
print(f"Success: {receipt['success']}")
print(f"Output: {receipt['output_path']}")
```

## Advanced Features

### Caching

TTL2DSPy uses multi-level caching for performance:

```python
from kgcl.ttl2dspy import UltraOptimizer, CacheConfig

config = CacheConfig(
    memory_cache_enabled=True,
    disk_cache_enabled=True,
    disk_cache_dir="/tmp/ttl2dspy_cache",
    redis_enabled=False,  # Optional Redis caching
)

optimizer = UltraOptimizer(config)

# First parse (cache miss)
shapes = optimizer.parse_with_cache("example_ontology.ttl")

# Second parse (cache hit)
shapes = optimizer.parse_with_cache("example_ontology.ttl")

# View stats
stats = optimizer.get_detailed_stats()
print(f"Cache hit rate: {stats['cache']['memory_hit_rate']:.2%}")
```

### Batch Processing

Process multiple ontologies:

```python
from pathlib import Path
from kgcl.ttl2dspy import UltraOptimizer

optimizer = UltraOptimizer()

ttl_files = list(Path("ontologies").glob("*.ttl"))
results = optimizer.batch_parse(ttl_files)

for path, shapes in results.items():
    print(f"{path}: {len(shapes)} shapes")
```

### Custom Output

```python
from kgcl.ttl2dspy import DSPyGenerator

generator = DSPyGenerator()

for shape in shapes:
    sig = generator.generate_signature(shape)

    # Customize signature
    sig.base_classes.append("CustomBase")

    # Generate custom code
    code = sig.generate_code()
    print(code)
```

## Cache Management

View cache statistics:

```bash
python -m kgcl.ttl2dspy cache-stats
python -m kgcl.ttl2dspy cache-stats --json
```

Clear all caches:

```bash
python -m kgcl.ttl2dspy clear-cache
```

## Tips

1. **Use descriptive comments**: SHACL `rdfs:comment` becomes Python docstrings
2. **Mark required fields**: Use `sh:minCount 1` for required inputs
3. **Set defaults**: Use `sh:defaultValue` for optional parameters
4. **Validate first**: Always validate before generating
5. **Enable caching**: Significantly speeds up repeated operations

## SHACL Best Practices

### Input/Output Categorization

TTL2DSPy categorizes properties as inputs or outputs using these heuristics:

- **Inputs**: Properties with `sh:minCount > 0` or `sh:defaultValue`
- **Outputs**: Properties without the above

You can also organize shapes to follow this pattern naturally:
- List input properties first
- List output properties last

### Type Mapping

SHACL datatypes map to Python types:

| SHACL Type | Python Type |
|------------|-------------|
| `xsd:string` | `str` |
| `xsd:integer` | `int` |
| `xsd:float` | `float` |
| `xsd:boolean` | `bool` |
| `xsd:dateTime` | `str` (ISO format) |

### Optional vs Required

```turtle
# Required input
sh:property [
    sh:path kgcl:required_field ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;  # Makes it required
] ;

# Optional input
sh:property [
    sh:path kgcl:optional_field ;
    sh:datatype xsd:string ;
    # No minCount = optional
] ;
```

### Lists

```turtle
# List field (multiple values)
sh:property [
    sh:path kgcl:tags ;
    sh:datatype xsd:string ;
    sh:maxCount 10 ;  # Or omit for unlimited
] ;
```

This generates: `tags: Optional[List[str]]`

## Troubleshooting

### Import Errors

Ensure the generated directory is in your Python path:

```python
import sys
sys.path.append("examples/ttl2dspy/generated")
```

### Validation Failures

Check for:
- Missing property descriptions
- Empty shapes (no properties)
- Invalid SHACL syntax

### Cache Issues

Clear caches if you see stale data:

```bash
python -m kgcl.ttl2dspy clear-cache
```

Or disable caching:

```bash
python -m kgcl.ttl2dspy generate ... --no-cache
```
