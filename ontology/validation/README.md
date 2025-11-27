# Validation Shapes

This directory contains SHACL validation shapes for ensuring data quality and workflow correctness.

## Files

### Core Invariants

- **invariants.shacl.ttl** (16K, last modified Nov 25)
  - Enforces the Three Laws:
    1. **TYPING**: All entities must have explicit types
    2. **HERMETICITY**: No external dependencies in pure RDF execution
    3. **CHRONOLOGY**: Temporal ordering must be preserved
  - Used by `BBBIngress` for topology validation
  - Path: `src/kgcl/ingress/bbb.py` references this file

### Quality Invariants

- **q-invariants.ttl**
  - Quality invariants for workflow validation
  - Ensures workflow properties and constraints

### Soundness Validation

- **soundness.ttl**
  - General soundness validation rules
  - Structural correctness checks

- **workflow-soundness.ttl**
  - Workflow-specific soundness validation
  - Ensures workflows are well-formed and executable

### Guard Conditions

- **workflow-guards.ttl**
  - Guard condition validation
  - Precondition and postcondition checks

## Usage

### In Code

```python
from kgcl.ingress import validate_topology

# Automatically uses ontology/validation/invariants.shacl.ttl
is_valid, report, message = validate_topology(data_graph)
```

### Command Line

```bash
# Validate against invariants
uv run pyshacl --shapes ontology/validation/invariants.shacl.ttl \
               --data your_data.ttl
```

## Integration

- **BBB Ingress**: Uses `invariants.shacl.ttl` for topology validation
- **Personal KGCL**: Uses validation shapes for data quality
- **Workflow Engine**: Uses soundness validation for workflow correctness

## References

- `src/kgcl/ingress/bbb.py` - BBB Ingress implementation
- `src/personal_kgcl/ingest/validation.py` - Personal KGCL validation
- `docs/explanation/poka-yoke-chronology.md` - Validation history

