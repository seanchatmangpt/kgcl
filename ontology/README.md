# KGCL Ontology Directory

This directory contains all RDF/Turtle ontology files used by the KGCL system.

## Directory Structure

```
ontology/
├── codebase/                # Java codebase structure (code-centric)
│   ├── yawl-java-schema.ttl # Meta-model definitions (JavaClass, JavaMethod, etc.)
│   └── org/
│       └── yawlfoundation/
│           └── yawl/
│               └── ...      # Individual class files organized by package
├── core/                    # Core ontology definitions (domain-centric)
│   ├── kgc_physics.ttl      # Main physics ontology (WCP patterns)
│   ├── kgc_physics_execution_templates.ttl
│   ├── sparql_templates_wcp16_27.ttl
│   ├── yawl.ttl             # YAWL 4.0 vocabulary
│   ├── yawl-extended.ttl    # Extended YAWL definitions
│   ├── yawl-shapes.ttl      # YAWL SHACL shapes
│   ├── knhk.owl.ttl         # KNHK operational ontology
│   ├── osys.ttl             # OS system ontology
│   └── mape-k-autonomic.ttl # MAPE-K autonomic patterns
├── validation/              # SHACL validation shapes
│   ├── invariants.shacl.ttl # Three Laws (TYPING, HERMETICITY, CHRONOLOGY)
│   ├── q-invariants.ttl    # Quality invariants
│   ├── soundness.ttl        # Workflow soundness validation
│   ├── workflow-guards.ttl  # Workflow guard conditions
│   └── workflow-soundness.ttl # Workflow soundness checks
└── workflows/               # Workflow examples and patterns
    ├── core/                # Core pattern definitions
    ├── examples/            # Example workflows
    ├── financial/           # Financial domain workflows
    └── reference/           # Reference implementations
```

## Codebase Ontology

The `codebase/` directory contains the Java codebase structure extracted from the YAWL Java implementation:

- **yawl-java-schema.ttl**: Meta-model definitions (yawl:Package, yawl:Class, yawl:Method, yawl:Field, etc.)
- **org/yawlfoundation/yawl/...**: Individual class files organized by Java package structure
- Contains 863 Java classes across 133 packages

This is code-centric knowledge (mirroring the Java source structure), separate from the domain-centric ontologies in `core/`.

See `codebase/README.md` for detailed documentation.

## Core Ontologies

The `core/` directory contains the fundamental ontology definitions:

- **kgc_physics.ttl**: Main physics ontology implementing all 43 YAWL Workflow Control Patterns
- **yawl*.ttl**: YAWL vocabulary and extensions for workflow modeling
- **knhk.owl.ttl**: KNHK operational ontology for enterprise workflows
- **mape-k-autonomic.ttl**: MAPE-K patterns for autonomic computing

## Validation Shapes

The `validation/` directory contains SHACL shapes for data quality:

- **invariants.shacl.ttl**: Enforces the Three Laws (TYPING, HERMETICITY, CHRONOLOGY)
- **q-invariants.ttl**: Quality invariants for workflow validation
- **workflow-*.ttl**: Workflow-specific validation rules

## Workflows

The `workflows/` directory contains example and reference workflows:

- **core/**: Pattern permutation definitions
- **examples/**: Simple example workflows
- **financial/**: Financial domain workflows
- **reference/**: Canonical YAWL workflow implementations

## Usage

### Loading Core Ontology

```python
from rdflib import Graph

ontology = Graph()
ontology.parse("ontology/core/kgc_physics.ttl", format="turtle")
```

### Validation

```python
from kgcl.ingress import validate_topology

# Uses ontology/validation/invariants.shacl.ttl
is_valid = validate_topology(data_graph)
```

## See Also

- `src/kgcl/ontology/` - Package ontology (separate from this directory)
- `docs/explanation/ontology-evolution.md` - Ontology evolution history
- `docs/reference/sparql-template-reference.md` - SPARQL template documentation

