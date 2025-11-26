# Explanation

Explanation documentation is **understanding-oriented** and helps you understand the concepts, architecture, and design decisions behind KGCL.

---

## Architecture

### [Architecture Overview](architecture/index.md)
High-level system architecture and design principles.

### [Compiled Physics Architecture](architecture/compiled-physics.md)
The PyOxigraph + EYE reasoner architecture for workflow execution.

### [True Hybrid Engine](architecture/hybrid-engine.md)
How the hybrid engine combines RDF storage with N3 reasoning.

### [RDF Purity Matrix](architecture/rdf-purity-matrix.md)
Levels of RDF purity in the implementation.

### [L5 Python Boundaries](architecture/l5-python-boundaries.md)
Where Python is required and why.

---

## Design Analysis

### [WCP 43-Pattern FMEA Analysis](wcp-fmea-analysis.md)
Complete Failure Mode and Effects Analysis of all 43 workflow patterns.

### [Lean Six Sigma WCP Analysis](lean-six-sigma-analysis.md)
DFSS quality analysis of workflow patterns.

### [YAWL Pattern Mapping](yawl-pattern-mapping.md)
How YAWL patterns map to KGCL implementation.

---

## Validation Reports

### [TRIZ Validation Summary](triz-validation.md)
TRIZ Principle 15 (Dynamics) validation.

### [TRIZ Principle 35 Report](triz-principle-35.md)
Parameter changes validation.

### [Poka-Yoke Chronology](poka-yoke-chronology.md)
Time-based safety barrier validation.

---

## Implementation Analysis

### [Parameter Evolution Analysis](parameter-evolution.md)
How parameters evolved from values to execution logic.

### [Ontology Evolution](ontology-evolution.md)
COMPLETENESS Law and ontology changes.

### [Before/After Comparison](before-after-comparison.md)
Visual comparison of architectural evolution.

---

## Historical & Context

### [YAWL Implementation Failure Report](yawl-failure-report.md)
Analysis of the original YAWL engine failure and lessons learned.

### [Security Review Report](security-review.md)
Comprehensive security analysis of the system.

### [KGCL v3 Implementation Plan](v3-implementation-plan.md)
Original implementation roadmap.

---

## Conceptual Index

| Concept | Explanation |
|---------|-------------|
| Why N3 over SPARQL? | [Compiled Physics](architecture/compiled-physics.md) |
| Why monotonic reasoning? | [Hybrid Engine](architecture/hybrid-engine.md) |
| Pattern risk assessment | [WCP FMEA Analysis](wcp-fmea-analysis.md) |
| What went wrong before? | [YAWL Failure Report](yawl-failure-report.md) |
| Design principles | [TRIZ Validation](triz-validation.md) |

---

## See Also

- [Tutorials](../tutorials/index.md) for learning by doing
- [How-To Guides](../how-to/index.md) for solving problems
- [Reference](../reference/index.md) for API details
