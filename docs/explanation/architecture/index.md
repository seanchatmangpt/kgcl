# Architecture

High-level system architecture and design principles for KGCL.

---

## Overview

KGCL implements a **Hard Separation** architecture where:

- **State (Matter)**: PyOxigraph stores inert RDF triples
- **Logic (Physics)**: N3 rules executed by EYE reasoner
- **Time**: Python tick controller orchestrates execution

```
┌─────────────────────────────────────────────────────────────────┐
│                   Python (Time Layer - L5)                       │
│              Manual Tick Controller + Observability              │
├─────────────────────────────────────────────────────────────────┤
│                  N3 Rules (Physics Layer - L4)                   │
│         17 Laws implementing 43 YAWL Workflow Patterns           │
├─────────────────────────────────────────────────────────────────┤
│                 PyOxigraph (State Layer - L3)                    │
│              Rust-based RDF Triple Store (Inert)                 │
├─────────────────────────────────────────────────────────────────┤
│                 EYE Reasoner (Inference - L2)                    │
│              Forward-chaining N3 Rule Execution                  │
├─────────────────────────────────────────────────────────────────┤
│                  SHACL (Validation - L1)                         │
│                 Data validated at ingress only                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Architecture Documents

### [Compiled Physics](compiled-physics.md)

The N3 rule-based workflow execution architecture. Explains:

- Why N3 over SPARQL for workflow logic
- Forward-chaining inference model
- EYE reasoner integration
- Rule composition patterns

### [True Hybrid Engine](hybrid-engine.md)

How PyOxigraph and EYE work together:

- State/Logic separation
- Tick-based execution model
- Transaction boundaries
- Query patterns

### [RDF Purity Matrix](rdf-purity-matrix.md)

Levels of RDF purity in the implementation:

- L1: SHACL validation
- L2: EYE inference
- L3: PyOxigraph storage
- L4: N3 physics
- L5: Python boundaries

### [L5 Python Boundaries](l5-python-boundaries.md)

Where Python is required and why:

- External system integration
- Non-monotonic operations
- Time/scheduling
- File I/O

---

## Design Principles

### 1. Hard Separation

State and logic never mix. Oxigraph stores data. N3 rules transform data. Python orchestrates.

### 2. Monotonic Reasoning

All N3 rules are monotonic - they only add facts, never remove. State changes happen through tick boundaries.

### 3. Tick-Based Execution

The world advances through discrete ticks:

```python
controller = TickController(store)
result = controller.tick()  # Apply all applicable rules once
```

### 4. SHACL at Ingress

Data is validated once at system boundary. Internal code trusts validated data.

### 5. Provenance by Default

Every tick produces a receipt stored in the Lockchain for audit trail.

---

## Component Map

| Component | Layer | Purpose |
|-----------|-------|---------|
| `TickController` | L5 | Orchestrates tick execution |
| `HybridEngine` | L4/L5 | Main engine interface |
| `WCP43_COMPLETE_PHYSICS` | L4 | ALL 43 WCP patterns implemented |
| `OxigraphStore` | L3 | RDF storage wrapper |
| `EYEReasoner` | L2 | N3 rule execution |
| `SHACL` | L1 | Ingress validation |

---

## See Also

- [WCP FMEA Analysis](../wcp-fmea-analysis.md) - Pattern risk assessment
- [YAWL Pattern Mapping](../yawl-pattern-mapping.md) - Pattern implementation details
- [System Architecture](../system-architecture.md) - Full system documentation
