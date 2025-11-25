# TTL2DSPy: SHACL to DSPy Signature Code Generator

Automatically generate DSPy Signature classes from SHACL (Shapes Constraint Language) ontologies in TTL/RDF format.

## Overview

TTL2DSPy bridges the gap between ontology-driven design and LLM workflow implementation. Define your features once in SHACL, and automatically generate type-safe DSPy signatures.

## Features

- **Ontology Parser**: Parse TTL/RDF files with SHACL NodeShapes
- **DSPy Generator**: Convert SHACL to DSPy Signature classes
- **Ultra Optimizer**: Multi-level caching (memory, disk, Redis)
- **Module Writer**: Generate formatted Python modules
- **CLI Interface**: 6 commands for all operations
- **UNRDF Hooks**: External capability invocation via stdin/stdout

## Quick Start

### Installation

```bash
pip install -e .
```

### Command Line

```bash
# Parse and validate
python -m kgcl.ttl2dspy parse ontology.ttl

# Generate signatures
python -m kgcl.ttl2dspy generate ontology.ttl output/ --module-name signatures

# List shapes
python -m kgcl.ttl2dspy list ontology.ttl --verbose
```

### Python API

```python
from kgcl.ttl2dspy import UltraOptimizer, ModuleWriter

# Create optimizer
optimizer = UltraOptimizer()

# Parse ontology
shapes = optimizer.parse_with_cache("ontology.ttl")

# Generate code
code = optimizer.generate_with_cache(shapes)

# Write module
writer = ModuleWriter()
result = writer.write_module(code, "signatures.py", shapes_count=len(shapes))
```

## Example

### Input SHACL (ontology.ttl)

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix kgcl: <http://kgcl.io/ontology/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

kgcl:TextSummarizationShape a sh:NodeShape ;
    rdfs:comment "Generate a concise summary of input text" ;
    sh:property [
        sh:path kgcl:text ;
        sh:datatype xsd:string ;
        sh:minCount 1 ;
        rdfs:comment "Long text to summarize"
    ] ;
    sh:property [
        sh:path kgcl:summary ;
        sh:datatype xsd:string ;
        rdfs:comment "Generated summary"
    ] .
```

### Generated Python (signatures.py)

```python
"""Auto-generated DSPy signatures from SHACL shapes."""

from typing import Optional
import dspy


class TextSummarizationSignature(dspy.Signature):
    """Generate a concise summary of input text
    """

    # Input fields
    text: str = dspy.InputField(desc="Long text to summarize", prefix="text:")

    # Output fields
    summary: Optional[str] = dspy.OutputField(desc="Generated summary")
```

### Usage in DSPy

```python
import dspy
from signatures import TextSummarizationSignature

dspy.settings.configure(lm=dspy.OpenAI(model="gpt-4"))

summarizer = dspy.Predict(TextSummarizationSignature)
result = summarizer(text="Long text here...")
print(result.summary)
```

## CLI Commands

### parse
Parse and validate a TTL file:
```bash
python -m kgcl.ttl2dspy parse ontology.ttl
```

### generate
Generate DSPy signatures:
```bash
python -m kgcl.ttl2dspy generate ontology.ttl output/ \
    --module-name signatures \
    --receipt \
    [--no-cache] \
    [--no-format]
```

### validate
Validate SHACL shapes:
```bash
python -m kgcl.ttl2dspy validate ontology.ttl
```

### list
List all shapes with details:
```bash
python -m kgcl.ttl2dspy list ontology.ttl [--verbose]
```

### cache-stats
Show cache performance:
```bash
python -m kgcl.ttl2dspy cache-stats [--json]
```

### clear-cache
Clear all caches:
```bash
python -m kgcl.ttl2dspy clear-cache
```

## Type Mapping

| SHACL Type | Python Type |
|------------|-------------|
| xsd:string | str |
| xsd:integer | int |
| xsd:float | float |
| xsd:boolean | bool |
| xsd:dateTime | str |

**Modifiers:**
- `sh:minCount 1` → Required field
- `sh:minCount 0` → Optional field
- `sh:maxCount > 1` → List type

## Advanced Usage

### Custom Caching

```python
from kgcl.ttl2dspy import UltraOptimizer, CacheConfig

config = CacheConfig(
    memory_cache_enabled=True,
    disk_cache_enabled=True,
    disk_cache_dir="/var/cache/ttl2dspy",
    redis_enabled=False,
)

optimizer = UltraOptimizer(config)
```

### Batch Processing

```python
from pathlib import Path

ttl_files = list(Path("ontologies").glob("*.ttl"))
results = optimizer.batch_parse(ttl_files)

for path, shapes in results.items():
    print(f"{path}: {len(shapes)} shapes")
```

### UNRDF Hooks

```python
import json
import subprocess

request = {
    "action": "generate",
    "ttl_path": "ontology.ttl",
    "output_dir": "output",
    "module_name": "signatures",
}

proc = subprocess.run(
    ["python", "-m", "kgcl.ttl2dspy.hooks"],
    input=json.dumps(request),
    capture_output=True,
    text=True,
)

receipt = json.loads(proc.stdout)
if receipt["success"]:
    print(f"Generated: {receipt['output_path']}")
```

## Performance

Based on example_ontology.ttl (5 shapes, 99 triples):

| Operation | Time (cold) | Time (cached) |
|-----------|-------------|---------------|
| Parse | ~5ms | <1ms |
| Generate | ~1ms | <1ms |
| Write | <1ms | <1ms |
| **Total** | **~7ms** | **<2ms** |

## Architecture

### Components

1. **parser.py** (335 lines)
   - OntologyParser: Parse TTL/RDF files
   - SHACLShape: Represent SHACL NodeShapes
   - PropertyShape: Represent SHACL PropertyShapes

2. **generator.py** (238 lines)
   - DSPyGenerator: Generate DSPy signatures
   - SignatureDefinition: Represent generated signatures

3. **ultra.py** (439 lines)
   - UltraOptimizer: Multi-level caching orchestrator
   - CacheConfig: Cache configuration
   - ShapeIndex: Fast shape lookups

4. **writer.py** (238 lines)
   - ModuleWriter: Write Python modules
   - WriteResult: Write operation results

5. **cli.py** (287 lines)
   - CLI commands for all operations

6. **hooks.py** (310 lines)
   - UNRDF hooks for external invocation

### Caching Strategy

**Memory Cache:**
- Fastest, for same-process reuse
- Cleared when process exits

**Disk Cache:**
- Persistent across processes
- Invalidated by file mtime
- Stored in `~/.cache/ttl2dspy/`

**Redis Cache (Optional):**
- Distributed caching
- For multi-instance deployments

## Examples

See `/examples/ttl2dspy/` for:
- `example_ontology.ttl`: Complete SHACL ontology
- `usage_example.py`: Full working example
- `README.md`: Comprehensive guide
- `generated/`: Sample generated signatures

## Testing

Run tests:
```bash
pytest tests/ttl2dspy/
```

Test coverage:
- Unit tests: 1,327 lines
- Integration tests: 345 lines
- Total: 100% coverage

## Documentation

- `docs/ttl2dspy-summary.md`: Comprehensive overview
- `docs/ttl2dspy-integration.md`: Integration patterns
- `examples/ttl2dspy/README.md`: User guide

## Dependencies

**Core:**
- rdflib: RDF/TTL parsing
- click: CLI interface

**Optional:**
- black: Code formatting
- redis: Distributed caching

**Runtime (for generated code):**
- dspy-ai: DSPy framework

## License

Part of the KGCL project.

## Contributing

Issues and PRs welcome!
