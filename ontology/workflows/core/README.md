# Core Pattern Definitions

This directory contains the complete YAWL workflow pattern permutation matrix.

## Files

- **yawl-pattern-permutations.ttl** (464 lines)
  - Complete specification of all 43 Van der Aalst workflow patterns
  - Pattern annotations with category, control flow semantics, execution characteristics
  - MAPE-K annotations for autonomic behavior
  - Reference: http://www.workflowpatterns.com/

## Pattern Coverage

This file defines all 43 patterns from "Workflow Patterns: The Definitive Guide":

- **Basic Control Flow** (1-5): Sequence, Parallel Split, Synchronization, Exclusive Choice, Simple Merge
- **Advanced Branching** (6-11): Multi-Choice, OR-Join, Multi-Merge, Discriminator, Cycles, Termination
- **Multiple Instance** (12-15): MI patterns with various synchronization modes
- **State-Based** (16-18): Deferred Choice, Interleaved Parallel, Milestone
- **Cancellation** (19-25): Cancel Activity, Case, Region, MI Activity, Loop, Recursion, Trigger
- **Iteration** (36-43): Structured Loop, Recursion, Transient/Persistent Triggers, Termination

## Usage

```python
from rdflib import Graph

# Load pattern definitions
g = Graph()
g.parse("ontology/workflows/core/yawl-pattern-permutations.ttl", format="turtle")
```

## References

- `tests/fixtures/README.md` - References this file for pattern definitions
- `tests/fixtures/workflow_patterns.py` - Uses patterns for test fixtures

