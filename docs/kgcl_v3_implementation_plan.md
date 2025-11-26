# KGCL v3.0 Implementation Plan

## Executive Summary

This document analyzes the PRD v3.0 "Semantic Driver" specification and provides a concrete implementation roadmap for the KGCL Reference Engine. The core principle is **The Chatman Equation: A = μ(O)** where Action equals Operator applied to Observation.

## Critical Constraints (Anti-Hallucination Directives)

The PRD explicitly FORBIDS:

1. **NO Pattern Classes**: No `Sequence`, `XorSplit`, `ParallelJoin` Python classes
2. **NO Control Flow Logic**: No `if split_type == 'XOR': ...` statements
3. **NO Hardcoded IDs**: No `pattern_id = 1` literals
4. **Validation IS Execution**: pyshacl at ingress; conformance = execution
5. **Single File Mandate**: Core engine in one `knowledge_engine.py`

## Architecture: The 5 Stratums

### Stratum 1: Dark Matter (Ontology)

**Location**: `ontology/`

**Files to create**:
- `kgc_physics.ttl` - Defines 5 Verbs and YAWL→KGC mappings
- `invariants.shacl.ttl` - Constitution (Typing, Hermeticity, Chronology)

**Verb Definitions**:
| Verb | Semantics | YAWL Mapping |
|------|-----------|--------------|
| `kgc:Transmute` | A→B (Arrow of Time) | Sequence, Data Mappings |
| `kgc:Copy` | A→{B,C} (Divergence) | AND-split, Service calls |
| `kgc:Filter` | A→{Subset} (Selection) | XOR-split, OR-split, Resource checks |
| `kgc:Await` | {A,B}→C (Convergence) | AND-join, OR-join, Discriminator |
| `kgc:Void` | A→∅ (Termination) | Timeout, Cancel, Exception |

### Stratum 2: Blood-Brain Barrier (Ingress)

**Location**: `src/kgcl/ingress/bbb.py`

**Responsibilities**:
1. **Lift**: Convert JSON payload → N-Triples (QuadDelta)
2. **Screen**: Run `pyshacl.validate()` against `invariants.shacl.ttl`
3. **Reject**: If invalid, raise `TopologyViolationError`
4. **Pass**: Send validated QuadDelta to Atman

### Stratum 3: The Kernel (5 Verbs)

**Location**: Inside `knowledge_engine.py`

**Pure functions operating on graph nodes**:

```python
class Kernel:
    @staticmethod
    def transmute(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
        """A→B: Find yawl:nextElementRef and move token."""

    @staticmethod
    def copy(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
        """A→{B,C}: Clone token state to multiple next elements."""

    @staticmethod
    def filter(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
        """A→{Subset}: Evaluate yawl:hasPredicate to select paths."""

    @staticmethod
    def await_(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
        """Wait for all incoming flows to complete."""

    @staticmethod
    def void(graph: Graph, subject: URIRef, ctx: TransactionContext) -> QuadDelta:
        """A→∅: Remove token without successor."""
```

### Stratum 4: The Atman (Semantic Driver)

**Location**: Inside `knowledge_engine.py`

**Responsibilities**:
1. Load `kgc_physics.ttl` into memory (PHYSICS_ONTOLOGY)
2. Resolve verb from ontology: `?mapping kgc:pattern ?pattern ; kgc:verb ?verbURI`
3. Dispatch to Kernel function
4. Apply QuadDelta to store
5. Update Merkle hash

**Critical**: The Atman contains ZERO business logic. It only:
- Queries the ontology to find which verb to execute
- Invokes the corresponding Kernel function
- Records provenance

### Stratum 5: The Lockchain (Provenance)

**Algorithm**:
```python
prev_hash = ctx.prev_hash  # From context
current_hash = SHA3_256(prev_hash + delta.serialize())
```

## File Structure

```
ontology/
├── kgc_physics.ttl          # 5 Verbs + Mappings (NEW)
├── invariants.shacl.ttl     # Constitution (NEW)
├── yawl.ttl                 # YAWL 4.0 Vocabulary (EXISTS)
└── yawl-shapes.ttl          # Topology constraints (EXISTS)

src/kgcl/
├── ingress/
│   └── bbb.py               # Blood-Brain Barrier (NEW)
└── engine/
    └── knowledge_engine.py  # Single-file engine (NEW)
```

## Implementation Order

### Phase 1: Dark Matter (Ontology)

1. Create `kgc_physics.ttl`:
   - Define `kgc:` namespace
   - Define 5 verb classes
   - Define mappings from YAWL patterns to KGC verbs

2. Create `invariants.shacl.ttl`:
   - Typing constraints (all nodes must have rdf:type)
   - Hermeticity constraints (closed-world assumption)
   - Chronology constraints (timestamps must be valid)

### Phase 2: Ingress

3. Implement `bbb.py`:
   - JSON → RDF conversion
   - pyshacl validation
   - Error handling with meaningful messages

### Phase 3: Engine

4. Implement `knowledge_engine.py`:
   - `QuadDelta` (Pydantic, 64-op limit)
   - `TransactionContext` (tx_id, actor, prev_hash, data)
   - `Receipt` (merkle_root, verb_executed)
   - `Kernel` (5 static verb methods)
   - `Atman` (semantic driver with ontology lookup)

### Phase 4: Validation

5. Create test: Nuclear Launch Simulation
   - Complex workflow with Generals, Codes, Timeouts
   - Must execute using only ontology-driven verb dispatch

6. Verify zero `if type ==` statements
   - grep for forbidden patterns
   - all logic must be `verb = lookup_verb(type)`

## Success Criteria

1. **Nuclear Launch Simulation Runs**: Complex workflow executes correctly
2. **Zero Logic If-Statements**: No `if type == XOR`, only `verb = lookup_verb(type)`
3. **Cryptographic Integrity**: Deterministic Receipt hashes
4. **Clean Lint**: `ruff` and `mypy` pass with zero warnings
5. **80%+ Coverage**: Chicago School TDD

## YAWL 4.0 Feature Parity

| Perspective | YAWL Feature | KGC Implementation |
|-------------|--------------|-------------------|
| Control Flow | XOR Split | `Filter` verb with `yawl:hasPredicate` |
| Control Flow | AND Join | `Await` verb checking completion history |
| Data | Mappings | `Transmute` verb with `yawl:startingMappings` |
| Resource | Allocation | `Filter` verb with `yawl:hasResourcing` |
| Service | Webhooks | `Copy` verb to `yawl:hasExternalInteraction` |
| Exception | Timeout | `Void` verb when `CurrentTime > StartTime + duration` |

## Existing Code Analysis

### What to Keep

- `ontology/yawl.ttl` - Complete YAWL 4.0 vocabulary (1558 lines)
- `ontology/yawl-shapes.ttl` - Well-designed SHACL shapes (593 lines)
- `src/kgcl/engine/atman.py` - Good foundation but needs refactoring

### What to Delete

- `src/kgcl/yawl_engine/` - Entire directory (as per failure report)
- All hardcoded pattern classes
- All procedural dispatch logic

### What to Create

1. `ontology/kgc_physics.ttl` - New physics ontology
2. `ontology/invariants.shacl.ttl` - Constitution shapes
3. `src/kgcl/ingress/bbb.py` - Blood-Brain Barrier
4. `src/kgcl/engine/knowledge_engine.py` - Single-file Semantic Driver

## Risk Mitigation

### Risk: Ontology Query Performance
**Mitigation**: Cache SPARQL query results for verb resolution

### Risk: SHACL Validation Overhead
**Mitigation**: Use existing shapes cache pattern from `yawl_engine`

### Risk: Expression Evaluation (XQuery/Predicates)
**Mitigation**: Use safe Python evaluation with restricted globals

## Next Steps

1. Review this plan with stakeholder
2. Begin Phase 1: Create ontology files
3. TDD approach: Write tests first for each stratum
4. Integrate with existing Atman engine base

---

*Document generated: 2025-11-25*
*PRD Version: 3.0 "Semantic Driver"*
