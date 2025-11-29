# Semantic Code Porting Tool

**Version**: 1.0  
**Status**: Implemented  
**Architecture**: Hybrid Engine (PyOxigraph + EYE + N3 Rules)

## Overview

The Semantic Code Porting Tool is a rule-based code analysis system that uses the hybrid engine architecture to detect deltas and suggest porting strategies between Java and Python codebases. Unlike traditional diff tools, this system uses:

- **PyOxigraph**: Store code structures as RDF triples (Matter)
- **EYE Reasoner**: Apply N3 rules for porting patterns (Physics)
- **Python/Typer**: Orchestration and CLI (Time)
- **MCP Server**: FastMCP pattern for IDE/agent integration

## Architecture

### Hybrid Engine Integration

The porting tool leverages the existing hybrid engine architecture:

```
┌─────────────────────────────────────────────────────────┐
│              Semantic Porting Engine                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ PyOxigraph   │  │ EYE Reasoner │  │ N3 Rules     │ │
│  │ (RDF Store)  │  │ (Inference)  │  │ (Logic)      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Components

1. **Ingestion Layer** (`src/kgcl/porting/ingestion/`)
   - `JavaIngester`: Parse Java → RDF
   - `PythonIngester`: Parse Python → RDF
   - `RDFCodebase`: PyOxigraph wrapper with codebase queries

2. **N3 Porting Rules** (`ontology/porting/`)
   - `structural-rules.n3`: Class/method matching
   - `semantic-rules.n3`: Behavioral equivalence
   - `type-mapping-rules.n3`: Type transformations
   - `exception-rules.n3`: Exception patterns
   - `dependency-rules.n3`: Dependency analysis

3. **Porting Engine** (`src/kgcl/porting/engine/`)
   - `PortingEngine`: Wraps HybridEngine for porting
   - `DeltaInference`: EYE-based delta detection
   - `PatternMatcher`: SPARQL-based pattern matching

4. **MCP Server** (`src/kgcl/porting/mcp/`)
   - `PortingMCPServer`: MCP server for IDE/agent integration
   - `tools.py`: MCP tool definitions
   - `resources.py`: MCP resource definitions

## Usage

### CLI Commands

#### Ingest Codebases

```bash
uv run kgc-porting ingest \
    --java-root vendors/yawl-v5.2/src \
    --python-root src/kgcl/yawl \
    --store porting_store
```

#### Detect Deltas (SPARQL-based)

```bash
uv run kgc-porting detect \
    --store porting_store \
    --output deltas.json \
    --format json
```

#### Detect Deltas (N3 Rules)

```bash
uv run kgc-porting detect \
    --store porting_store \
    --rules ontology/porting/structural-rules.n3 \
    --output deltas.json
```

#### Suggest Porting Strategy

```bash
uv run kgc-porting suggest YEngine --store porting_store
```

#### Start MCP Server

```bash
uv run kgc-porting serve \
    --java-root vendors/yawl-v5.2/src \
    --python-root src/kgcl/yawl \
    --port 8000
```

### Python API

```python
from kgcl.porting import PortingEngine, RDFCodebase

# Create engine
engine = PortingEngine(store_path="porting_store")

# Ingest codebases
java_count = engine.ingest_java(Path("vendors/yawl-v5.2/src"))
python_count = engine.ingest_python(Path("src/kgcl/yawl"))

# Detect deltas using N3 rules
from kgcl.porting.engine.delta_inference import DeltaInference
inference = DeltaInference(engine)
deltas = inference.infer_deltas(Path("ontology/porting/structural-rules.n3"))

# Or use SPARQL-based pattern matching
from kgcl.porting.engine.pattern_matcher import PatternMatcher
matcher = PatternMatcher(engine.codebase)
missing_classes = matcher.find_missing_classes()
```

## N3 Rules

### Structural Matching

```n3
# Match classes by exact name
{
    ?javaClass code:name ?className .
    ?pythonClass code:name ?className .
}
=>
{
    ?javaClass port:hasPort ?pythonClass .
} .
```

### Semantic Equivalence

```n3
# Match methods by fingerprint similarity
{
    ?javaMethod code:hasFingerprint ?javaFp .
    ?pythonMethod code:hasFingerprint ?pythonFp .
    port:similarity(?javaFp, ?pythonFp, ?score) .
    ?score >= 0.8 .
}
=>
{
    ?javaMethod port:semanticallyEquivalent ?pythonMethod .
} .
```

## MCP Integration

The porting tool can be exposed as an MCP server for IDE and agent integration:

### Tools

- `detect_deltas`: Detect deltas between codebases
- `suggest_port`: Suggest porting strategy for a class
- `validate_port`: Validate porting completeness

### Resources

- `porting://codebase/graph`: RDF graph of codebases
- `porting://rules/structural`: Structural porting rules
- `porting://rules/semantic`: Semantic porting rules

## Benefits

1. **Declarative Logic**: Porting patterns as N3 rules, not hardcoded Python
2. **Extensibility**: Add new patterns by writing N3 rules
3. **Reasoning**: EYE can infer complex relationships
4. **Language-Agnostic**: RDF schema works for any language
5. **IDE Integration**: MCP server enables Cursor/VS Code integration
6. **Agent-Friendly**: MCP tools can be used by AI agents

## Comparison with Delta Detector

| Feature | Delta Detector | Semantic Porting Tool |
|---------|---------------|----------------------|
| Architecture | Hardcoded Python analyzers | N3 rules + EYE reasoner |
| Storage | In-memory Python objects | PyOxigraph RDF store |
| Logic | Python if/else statements | Declarative N3 rules |
| Extensibility | Modify Python code | Add N3 rules |
| IDE Integration | CLI only | MCP server + CLI |
| Language Support | Java→Python specific | Language-agnostic schema |

## Future Enhancements

1. **FastMCP Integration**: Full MCP protocol implementation
2. **Multi-Language Support**: Extend beyond Java→Python
3. **Code Generation**: Generate Python code from Java using rules
4. **Incremental Analysis**: Track deltas over time
5. **Visualization**: Interactive delta exploration

## Related Documentation

- [Delta Detector PRD](../yawl_ontology/DELTA_DETECTOR_PRD.md) - Original delta detector design
- [Hybrid Engine Architecture](../../src/kgcl/hybrid/README.md) - Hybrid engine documentation
- [N3 Physics Rules](../../src/kgcl/hybrid/n3_physics.py) - Example N3 rules

