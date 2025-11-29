# Unified Code Generation System - Complete Guide

## Overview

The KGCL codegen module provides a comprehensive, extensible framework for generating multiple output formats from RDF ontologies. Built on a solid foundation of caching, indexing, and performance optimization, it supports:

- **DSPy Signatures** - Generate type-safe DSPy prompt interfaces from SHACL constraints
- **YAWL Specifications** - Generate workflow XML from RDF workflow patterns
- **Python Modules** - Generate dataclasses, Pydantic models, or plain classes from OWL

## Architecture

### Core Components

```
kgcl.codegen/
├── base/
│   ├── generator.py          # BaseGenerator abstract class (Template Method pattern)
│   ├── template_engine.py    # Jinja2 rendering with filters
│   └── validator.py          # Code validation framework
├── generators/
│   ├── dspy_generator.py     # DSPy signature generator
│   ├── yawl_generator.py     # YAWL specification generator
│   ├── python_generator.py   # Python module generator
│   ├── cli_generator.py      # CLI generator (existing)
│   └── java_generator.py     # Java client generator (existing)
├── orchestrator.py            # Unified generation orchestrator
├── registry.py                # Generator discovery and registration
├── transpiler.py              # Ultra-optimized RDF/SHACL transpiler
├── cache.py                   # Multi-tier graph caching
├── indexing.py                # SHACL pattern indexing (O(1) lookups)
├── string_pool.py             # Cached string transformations
├── metrics.py                 # Performance metrics tracking
└── cli.py                     # Unified CLI interface
```

### Design Patterns

1. **Template Method Pattern** - `BaseGenerator` provides standard workflow
2. **Registry Pattern** - Dynamic generator discovery and instantiation
3. **Factory Pattern** - Generator factories with configuration
4. **Strategy Pattern** - Different output formats as strategies
5. **Orchestrator Pattern** - Unified interface coordinating generators

## Quick Start

### Installation

```bash
# Install KGCL with codegen dependencies
uv sync

# Configure DSPy (optional, auto-configured with defaults)
export DSPY_MODEL="ollama/granite4"
export DSPY_API_BASE="http://localhost:11434"
```

### Basic Usage

```python
from pathlib import Path
from kgcl.codegen import CodeGenOrchestrator, GenerationConfig, OutputFormat

# Create orchestrator
orchestrator = CodeGenOrchestrator()

# Generate DSPy signatures
config = GenerationConfig(
    format=OutputFormat.DSPY,
    output_dir=Path("generated/dspy")
)
result = orchestrator.generate(Path("ontology.ttl"), config)

# Generate YAWL specification
config = GenerationConfig(
    format=OutputFormat.YAWL,
    output_dir=Path("generated/yawl"),
    template_dir=Path("templates/yawl")
)
result = orchestrator.generate(Path("workflow.ttl"), config)

# Generate Python dataclasses
config = GenerationConfig(
    format=OutputFormat.PYTHON_DATACLASS,
    output_dir=Path("generated/python")
)
result = orchestrator.generate(Path("ontology.ttl"), config)
```

### CLI Usage

```bash
# List supported formats
python -m kgcl.codegen.cli --list-formats

# Generate DSPy signatures (default)
python -m kgcl.codegen.cli ontology.ttl output.py

# Generate YAWL specification
python -m kgcl.codegen.cli workflow.ttl workflow.yawl --format yawl

# Generate Python dataclasses
python -m kgcl.codegen.cli ontology.ttl models.py --format python-dataclass

# Generate Pydantic models
python -m kgcl.codegen.cli ontology.ttl models.py --format python-pydantic

# Batch processing with verbose output
python -m kgcl.codegen.cli ontologies/ generated/ --format dspy --verbose

# Dry run (validate without writing)
python -m kgcl.codegen.cli ontology.ttl --format yawl --dry-run
```

## Supported Formats

### 1. DSPy Signatures

**Format**: `dspy`

**Description**: Generates DSPy signature classes from RDF ontologies with SHACL constraints.

**Features**:
- Ultra-optimized transpilation (80/20 performance improvements)
- Multi-tier caching (memory/disk/Redis)
- SHACL pattern indexing for O(1) lookups
- Parallel processing with configurable workers
- OpenTelemetry instrumentation
- Automatic type inference from XSD datatypes

**Example Input** (RDF/SHACL):
```turtle
@prefix ex: <http://example.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:PersonShape
    a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:property ex:nameShape, ex:ageShape .

ex:nameShape
    sh:path ex:name ;
    sh:datatype xsd:string ;
    sh:minCount 1 .

ex:ageShape
    sh:path ex:age ;
    sh:datatype xsd:integer .
```

**Example Output** (DSPy):
```python
import dspy

class PersonSignature(dspy.Signature):
    \"\"\"Person processing signature.\"\"\"

    name: str = dspy.InputField(desc="Name input")
    age: int = dspy.InputField(desc="Age input")
    result: str = dspy.OutputField(desc="Processing result")
```

**Configuration**:
```python
config = GenerationConfig(
    format=OutputFormat.DSPY,
    output_dir=Path("generated/dspy"),
    cache_size=200,          # Graph cache size
    max_workers=8,           # Parallel workers
    dspy_model="ollama/granite4",
    dspy_api_base="http://localhost:11434"
)
```

### 2. YAWL Specifications

**Format**: `yawl`

**Description**: Generates YAWL workflow XML specifications from RDF workflow patterns.

**Features**:
- Workflow pattern extraction from RDF
- YAWL 4.3 compliant XML generation
- Task, condition, and flow mapping
- Layout generation for visual representation
- XML validation

**Example Input** (RDF):
```turtle
@prefix wf: <http://kgcl.io/workflow#> .

wf:SupplyChain
    a wf:Workflow ;
    rdfs:label "Supply Chain Workflow" .

wf:PlaceOrder
    a wf:Task ;
    rdfs:label "Place Order" ;
    wf:decomposition "order_decomposition" .

wf:ApproveOrder
    a wf:Task ;
    rdfs:label "Approve Order" .

wf:Flow1
    a wf:Flow ;
    wf:source wf:PlaceOrder ;
    wf:target wf:ApproveOrder .
```

**Example Output** (YAWL XML):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<specificationSet xmlns="http://www.yawlfoundation.org/yawlschema" version="4.3">
  <specification uri="http://kgcl.io/workflow/SupplyChain">
    <metaData>
      <title>SupplyChain</title>
      <creator>KGCL Code Generator</creator>
    </metaData>
    <decomposition id="SupplyChain" isRootNet="true" xsi:type="NetFactsType">
      <processControlElements>
        <task id="task_0">
          <name>Place Order</name>
          <decomposesTo id="order_decomposition" />
          <flowsInto>
            <nextElementRef id="task_1" />
          </flowsInto>
        </task>
        <task id="task_1">
          <name>Approve Order</name>
        </task>
      </processControlElements>
    </decomposition>
  </specification>
</specificationSet>
```

**Configuration**:
```python
config = GenerationConfig(
    format=OutputFormat.YAWL,
    output_dir=Path("generated/yawl"),
    template_dir=Path("templates/yawl")
)
```

### 3. Python Modules

**Formats**: `python-dataclass`, `python-pydantic`, `python-plain`

**Description**: Generates Python classes from OWL class definitions with properties.

**Features**:
- Three style options: dataclass, Pydantic, plain classes
- Automatic type mapping from XSD to Python
- Property extraction from OWL/RDFS
- Docstring generation from rdfs:comment
- Parent class inheritance support
- Import management

**Example Input** (OWL):
```turtle
@prefix ex: <http://example.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:Person
    a owl:Class ;
    rdfs:label "Person" ;
    rdfs:comment "Represents a person entity" .

ex:name
    a owl:DatatypeProperty ;
    rdfs:domain ex:Person ;
    rdfs:range xsd:string ;
    rdfs:label "name" ;
    rdfs:comment "Person's full name" .

ex:age
    a owl:DatatypeProperty ;
    rdfs:domain ex:Person ;
    rdfs:range xsd:integer ;
    rdfs:label "age" .
```

**Example Output** (dataclass):
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Person:
    \"\"\"Represents a person entity.

    RDF URI: http://example.org/Person
    \"\"\"

    name: str | None = None
    \"\"\"Person's full name\"\"\"

    age: int | None = None
    \"\"\"age property\"\"\"
```

**Example Output** (Pydantic):
```python
from pydantic import BaseModel

class Person(BaseModel):
    \"\"\"Represents a person entity.

    RDF URI: http://example.org/Person
    \"\"\"

    name: str | None = None
    \"\"\"Person's full name\"\"\"

    age: int | None = None
    \"\"\"age property\"\"\"
```

**Configuration**:
```python
# Dataclass style
config = GenerationConfig(
    format=OutputFormat.PYTHON_DATACLASS,
    output_dir=Path("generated/python")
)

# Pydantic style
config = GenerationConfig(
    format=OutputFormat.PYTHON_PYDANTIC,
    output_dir=Path("generated/python")
)

# Plain class style
config = GenerationConfig(
    format=OutputFormat.PYTHON_PLAIN,
    output_dir=Path("generated/python")
)
```

## Advanced Features

### Multi-File Batch Processing

```python
from pathlib import Path

# Process multiple ontology files
input_files = [
    Path("ontologies/core.ttl"),
    Path("ontologies/domain.ttl"),
    Path("ontologies/application.ttl")
]

results = orchestrator.generate_multiple(input_files, config)

for result in results:
    print(f"Generated: {result.output_path}")
    print(f"  Signatures: {result.metadata.get('signatures_generated', 'N/A')}")
    print(f"  Time: {result.metadata.get('processing_time_ms', 0):.1f}ms")
```

### Custom Templates

```python
# Use custom Jinja2 templates
config = GenerationConfig(
    format=OutputFormat.YAWL,
    output_dir=Path("generated"),
    template_dir=Path("custom/templates/yawl")
)
```

### Performance Tuning

```python
# Optimize for large ontologies
config = GenerationConfig(
    format=OutputFormat.DSPY,
    output_dir=Path("generated"),
    cache_size=500,      # Larger cache
    max_workers=16,      # More parallelism
)
```

### Dry Run Validation

```python
# Validate without writing files
config = GenerationConfig(
    format=OutputFormat.PYTHON_DATACLASS,
    output_dir=Path("generated"),
    dry_run=True  # Don't write output
)

result = orchestrator.generate(Path("ontology.ttl"), config)
print(f"Would generate: {result.output_path}")
print(f"Source preview:\n{result.source[:500]}")
```

## Extending the System

### Creating Custom Generators

```python
from pathlib import Path
from typing import Any
from dataclasses import dataclass

from kgcl.codegen.base.generator import BaseGenerator, Parser

@dataclass(frozen=True)
class CustomMetadata:
    # Your metadata structure
    data: dict[str, Any]

class CustomParser(Parser[CustomMetadata]):
    def parse(self, input_path: Path) -> CustomMetadata:
        # Your parsing logic
        return CustomMetadata(data={})

class CustomGenerator(BaseGenerator[CustomMetadata]):
    @property
    def parser(self) -> Parser[CustomMetadata]:
        return CustomParser()

    def _transform(self, metadata: CustomMetadata, **kwargs: Any) -> dict[str, Any]:
        # Transform to template context
        return {"data": metadata.data}

    def _get_template_name(self, metadata: CustomMetadata, **kwargs: Any) -> str:
        return "custom.j2"

    def _get_output_path(self, metadata: CustomMetadata, **kwargs: Any) -> Path:
        return self.output_dir / "output.txt"
```

### Registering Custom Generators

```python
from kgcl.codegen import get_registry

# Get global registry
registry = get_registry()

# Register your generator
registry.register(
    "custom",
    lambda **kwargs: CustomGenerator(**kwargs),
    description="My custom generator",
    file_types=[".ttl"],
    category="custom"
)

# Now use it
from kgcl.codegen import CodeGenOrchestrator

orchestrator = CodeGenOrchestrator(registry=registry)
# ... use as normal
```

## Performance Metrics

The codegen system includes comprehensive performance tracking:

```python
result = orchestrator.generate(Path("ontology.ttl"), config)

# Access metrics
metadata = result.metadata
print(f"Signatures generated: {metadata.get('signatures_generated', 0)}")
print(f"Processing time: {metadata.get('processing_time_ms', 0)}ms")
print(f"Cache efficiency: {metadata.get('cache_efficiency', 0):.1%}")
print(f"Graph size: {metadata.get('graph_size', 0)} triples")
```

### Optimization Results

From ultra-optimized transpiler:
- **80/20 performance improvements** - Focus on high-impact optimizations
- **Multi-tier caching** - Memory → Disk → Redis with LRU eviction
- **O(1) SHACL lookups** - Pre-computed indexes for property shapes
- **String pooling** - Cached transformations reduce allocations
- **Parallel processing** - ThreadPoolExecutor for concurrent files
- **32.3% token reduction** - Efficient prompt generation
- **2.8-4.4x speed improvement** - vs. non-optimized transpiler

## Integration Examples

### Integration with YAWL Engine

```python
# Generate YAWL specification
config = GenerationConfig(
    format=OutputFormat.YAWL,
    output_dir=Path("specs")
)
result = orchestrator.generate(Path("workflow.ttl"), config)

# Load into YAWL engine
from kgcl.yawl.persistence.xml_parser import YAWLParser

parser = YAWLParser()
specification = parser.parse(result.output_path)

# Execute with YAWL engine
from kgcl.yawl.engine.y_engine import YEngine

engine = YEngine()
case_id = engine.launch_case(specification)
```

### Integration with DSPy

```python
# Generate DSPy signatures
config = GenerationConfig(
    format=OutputFormat.DSPY,
    output_dir=Path("signatures")
)
result = orchestrator.generate(Path("ontology.ttl"), config)

# Import and use generated signatures
import sys
sys.path.insert(0, str(result.output_path.parent))

from ontology_signatures import PersonSignature, get_signature

# Use in DSPy programs
signature = get_signature("PersonSignature")
# ... use with dspy.ChainOfThought, etc.
```

### Integration with FastAPI

```python
# Generate Pydantic models
config = GenerationConfig(
    format=OutputFormat.PYTHON_PYDANTIC,
    output_dir=Path("api/models")
)
result = orchestrator.generate(Path("api_schema.ttl"), config)

# Use in FastAPI
from fastapi import FastAPI
from api.models.api_schema import Person

app = FastAPI()

@app.post("/persons/")
async def create_person(person: Person):
    return person
```

## Best Practices

1. **Use appropriate formats** - DSPy for LLM prompts, YAWL for workflows, Python for data models
2. **Leverage caching** - Configure cache_size based on ontology size and available memory
3. **Batch processing** - Process multiple files together for better performance
4. **Custom templates** - Create domain-specific templates for consistent output
5. **Validate ontologies** - Ensure RDF/SHACL/OWL files are well-formed before generation
6. **Version control** - Track generated code to detect unintended changes
7. **Test generated code** - Add integration tests for generated artifacts

## Troubleshooting

### Issue: Import errors for generated modules
```python
# Solution: Add output directory to Python path
import sys
from pathlib import Path
sys.path.insert(0, str(Path("generated").absolute()))
```

### Issue: Template not found
```python
# Solution: Specify full template directory path
config = GenerationConfig(
    format=OutputFormat.YAWL,
    template_dir=Path(__file__).parent / "templates" / "yawl"
)
```

### Issue: SHACL validation errors
```bash
# Solution: Validate SHACL before generation
uv run python -c "
from rdflib import Graph
g = Graph()
g.parse('ontology.ttl')
# Check for SHACL shapes
from rdflib.namespace import SH
print(f'SHACL shapes: {len(list(g.subjects(rdflib.RDF.type, SH.NodeShape)))}')
"
```

## Future Extensions

Planned enhancements:
- GraphQL schema generation
- OpenAPI/Swagger spec generation
- TypeScript interface generation
- SQL schema generation
- Protobuf message generation
- JSON Schema generation

## Support

- **Documentation**: `/docs/codegen/`
- **Examples**: `/examples/codegen_demo.py`
- **Tests**: `/tests/codegen/`
- **Issues**: https://github.com/yourorg/kgcl/issues

---

Generated by KGCL Unified Code Generation System v1.0.0
