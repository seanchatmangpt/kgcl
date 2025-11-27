# Workflow Examples and Patterns

This directory contains example workflows, reference implementations, and pattern definitions.

## Directory Structure

```
workflows/
├── core/                    # Core pattern definitions
├── examples/                # Simple example workflows
├── financial/               # Financial domain workflows
└── reference/               # Canonical YAWL implementations
```

## Core Patterns

The `core/` directory contains the complete YAWL pattern permutation matrix:

- **yawl-pattern-permutations.ttl**: Complete specification of all 43 Van der Aalst workflow patterns with MAPE-K annotations

## Examples

The `examples/` directory contains simple, educational workflows:

- **simple-sequence.ttl**: Basic sequence pattern (WCP 1)
- **parallel-processing.ttl**: Parallel execution example
- **autonomic-self-healing-workflow.ttl**: MAPE-K autonomic example
- **autonomous-work-definition.ttl**: Autonomous workflow definition

## Financial Workflows

The `financial/` directory contains domain-specific workflows:

- **atm_transaction.ttl**: ATM transaction processing
- **payroll.ttl**: Payroll processing workflow
- **swift_payment.ttl**: SWIFT payment processing

## Reference Workflows

The `reference/` directory contains canonical YAWL workflow implementations that serve as the source of truth for YAWL execution. See `reference/README.md` for details.

These 5 workflows cover 15+ critical patterns:
- Order Processing (Patterns 1-5)
- Multi-Instance Approval (Patterns 12-15)
- Cancellation Pattern (Patterns 19, 25)
- OR-Join (Pattern 7) - YAWL's unique contribution
- Timer Escalation (Patterns 40-43)

## Usage

```python
from rdflib import Graph

# Load a reference workflow
g = Graph()
g.parse("ontology/workflows/reference/order_processing.ttl", format="turtle")
```

## References

- `tests/fixtures/README.md` - Workflow pattern fixtures
- `ontology/workflows/reference/README.md` - Reference workflow documentation

