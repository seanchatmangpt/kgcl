# Core Ontologies

This directory contains the fundamental ontology definitions for KGCL.

## Files

### Physics Ontology

- **kgc_physics.ttl** (36K, last modified Nov 26)
  - Main physics ontology implementing all 43 YAWL Workflow Control Patterns
  - Defines PhysicsRule, Verb, Pattern classes
  - Contains N3 logic for workflow execution
  - Used by `SemanticDriver` in `knowledge_engine.py`

- **kgc_physics_execution_templates.ttl** (33K, last modified Nov 26)
  - SPARQL execution templates for L5 Pure RDF Kernel
  - Part of the L5 boundary implementation

- **sparql_templates_wcp16_27.ttl** (31K, last modified Nov 26)
  - SPARQL templates for WCP patterns 16-27
  - Execution templates for state-based patterns

### YAWL Ontologies

- **yawl.ttl** (45K)
  - Complete YAWL 4.0 vocabulary
  - Task, Condition, Flow definitions
  - Control types (AND, OR, XOR)

- **yawl-extended.ttl** (23K)
  - Extended YAWL definitions
  - Additional workflow constructs

- **yawl-shapes.ttl** (21K)
  - SHACL shapes for YAWL topology validation
  - Well-designed but currently unused in code

### KNHK Ontologies

- **knhk.owl.ttl** (35K)
  - KNHK operational ontology
  - Pipeline stages (Ingest, Transform, Load, Reflex, Emit)
  - Enterprise workflow definitions

- **osys.ttl** (2.8K)
  - OS system ontology
  - System-level definitions

- **mape-k-autonomic.ttl** (28K)
  - MAPE-K autonomic computing patterns
  - Monitor, Analyze, Plan, Execute, Knowledge loop

## Usage

```python
from rdflib import Graph

# Load main physics ontology
g = Graph()
g.parse("ontology/core/kgc_physics.ttl", format="turtle")

# Load YAWL vocabulary
g.parse("ontology/core/yawl.ttl", format="turtle")
```

## References

- Used by: `src/kgcl/engine/knowledge_engine.py`
- Tested in: `tests/engine/test_*.py`
- Documented in: `docs/explanation/` and `docs/reference/`

