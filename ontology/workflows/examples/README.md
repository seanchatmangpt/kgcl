# Example Workflows

Simple, educational workflows demonstrating basic YAWL patterns.

## Files

- **simple-sequence.ttl**
  - Basic sequence pattern (WCP 1)
  - Demonstrates linear task execution

- **parallel-processing.ttl**
  - Parallel execution example
  - Demonstrates AND-split and AND-join

- **autonomic-self-healing-workflow.ttl**
  - MAPE-K autonomic computing example
  - Self-healing workflow pattern

- **autonomous-work-definition.ttl**
  - Autonomous workflow definition
  - Demonstrates autonomous task execution

## Purpose

These workflows serve as:
- Learning examples for YAWL patterns
- Test cases for workflow execution
- Documentation of basic patterns

## Usage

```python
from rdflib import Graph

# Load an example
g = Graph()
g.parse("ontology/workflows/examples/simple-sequence.ttl", format="turtle")
```

