# Workflow Pattern Fixtures - KGCL v3

RDF graph fixtures for all 43 Van der Aalst Workflow Control Flow Patterns (WCP).

## Overview

This package provides pytest fixtures that generate valid YAWL workflow graphs implementing each of the 43 control flow patterns from "Workflow Patterns: The Definitive Guide" by Van der Aalst et al.

**Reference:** http://www.workflowpatterns.com/

## Usage

### As Pytest Fixtures

```python
from rdflib import Graph

def test_sequence_execution(wcp01_sequence: Graph) -> None:
    """Test using sequence pattern fixture."""
    graph = wcp01_sequence
    # Verify topology
    tasks = list(graph.subjects(predicate=YAWL.taskName))
    assert len(tasks) == 3
```

### Using the Factory

```python
from tests.fixtures import create_workflow_pattern

def test_dynamic_pattern() -> None:
    """Test using factory function."""
    graph = create_workflow_pattern(pattern_id=7)  # OR-join pattern
    assert len(graph) > 0
```

## Pattern Categories

### Basic Control Flow (1-5)
- **WCP 1:** Sequence (A → B → C)
- **WCP 2:** Parallel Split (AND-split)
- **WCP 3:** Synchronization (AND-join)
- **WCP 4:** Exclusive Choice (XOR-split)
- **WCP 5:** Simple Merge (XOR-join)

### Advanced Branching (6-11)
- **WCP 6:** Multi-Choice (OR-split)
- **WCP 7:** Structured Synchronizing Merge (OR-join) ⭐
- **WCP 8:** Multi-Merge
- **WCP 9:** Structured Discriminator
- **WCP 10:** Arbitrary Cycles
- **WCP 11:** Implicit Termination

⭐ *YAWL's unique contribution with dead path elimination*

### Multiple Instance (12-15)
- **WCP 12:** MI without Synchronization
- **WCP 13:** MI with Design-Time Knowledge
- **WCP 14:** MI with Runtime Knowledge
- **WCP 15:** MI without A Priori Knowledge

### State-Based (16-18)
- **WCP 16:** Deferred Choice
- **WCP 17:** Interleaved Parallel Routing
- **WCP 18:** Milestone

### Cancellation (19-25)
- **WCP 19:** Cancel Activity
- **WCP 20:** Cancel Case
- **WCP 21:** Cancel Region
- **WCP 22:** Cancel Multiple Instance Activity
- **WCP 23:** Structured Loop
- **WCP 24:** Recursion
- **WCP 25:** Transient Trigger

### MI Join (34-36)
- **WCP 34:** Static Partial Join
- **WCP 35:** Cancelling Partial Join
- **WCP 36:** Dynamic Partial Join

### Termination (43)
- **WCP 43:** Explicit Termination

## Graph Structure

Each fixture generates an RDF graph with:

1. **YAWL Topology:**
   - Tasks (atomic/composite)
   - Conditions (input/output)
   - Flows (connections)

2. **Join/Split Annotations:**
   - `yawl:join` (AND, OR, XOR)
   - `yawl:split` (AND, OR, XOR)

3. **Token Placement:**
   - `kgc:hasToken` marks initial state

4. **Pattern Metadata:**
   - `pattern:implementsPattern` links to pattern definition

## Example Graph Structure

```turtle
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix kgc: <http://kgcl.io/ontology/kgc#> .

<http://example.org/workflow/start> a yawl:InputCondition ;
    kgc:hasToken true .

<http://example.org/workflow/TaskA> a yawl:AtomicTask ;
    yawl:taskName "TaskA" ;
    yawl:join yawl:ControlTypeXor ;
    yawl:split yawl:ControlTypeXor ;
    yawl:nextElementRef <http://example.org/workflow/TaskB> .
```

## Available Fixtures

### Basic Control Flow
- `wcp01_sequence`
- `wcp02_parallel_split`
- `wcp03_synchronization`
- `wcp04_exclusive_choice`
- `wcp05_simple_merge`

### Advanced Branching
- `wcp06_multi_choice`
- `wcp07_structured_synchronizing_merge`
- `wcp08_multi_merge`
- `wcp09_structured_discriminator`
- `wcp10_arbitrary_cycles`
- `wcp11_implicit_termination`

### Multiple Instance
- `wcp12_mi_without_synchronization`
- `wcp13_mi_with_design_time_knowledge`
- `wcp14_mi_with_runtime_knowledge`
- `wcp15_mi_without_runtime_knowledge`

### State-Based
- `wcp16_deferred_choice`
- `wcp17_interleaved_parallel_routing`
- `wcp18_milestone`

### Cancellation
- `wcp19_cancel_activity`
- `wcp20_cancel_case`
- `wcp21_cancel_region`
- `wcp22_cancel_multiple_instance_activity`
- `wcp23_structured_loop`
- `wcp24_recursion`
- `wcp25_transient_trigger`

### MI Join
- `wcp34_static_partial_join`
- `wcp35_cancelling_partial_join`
- `wcp36_dynamic_partial_join`

### Termination
- `wcp43_explicit_termination`

### Factory
- `workflow_pattern_factory` (fixture)
- `create_workflow_pattern()` (function)

## Namespaces

```python
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
KGC = Namespace("http://kgcl.io/ontology/kgc#")
PATTERN = Namespace("http://knhk.ai/ontology/workflow-patterns#")
WF = Namespace("http://example.org/workflow/")
```

## Testing Standards

All fixtures follow **Chicago School TDD**:
- Real RDF graphs, no mocking
- Correct YAWL topology
- Valid namespace usage
- Reusable and parametrizable

## Implementation Details

### Control Type URIs

- **AND:** `yawl:ControlTypeAnd`
- **OR:** `yawl:ControlTypeOr`
- **XOR:** `yawl:ControlTypeXor`

### Critical: Namespace Method Collision

RDFLib `Namespace` objects have a `.join()` method. Use bracket notation to avoid conflicts:

```python
# ❌ WRONG: Calls join() method
graph.add((task, YAWL.join, YAWL.ControlTypeXor))

# ✅ CORRECT: Access join URI
graph.add((task, YAWL["join"], YAWL.ControlTypeXor))
```

Same applies to `YAWL["split"]`.

## Pattern Coverage

- **Implemented:** 29 patterns (control flow only)
- **Not Implemented:** WCP 26-33, 37-42 (data/resource patterns)

Data and resource patterns are outside the scope of the KGCL v3 engine, which focuses on control flow semantics.

## File Organization

```
tests/fixtures/
├── __init__.py                  # Package exports
├── conftest.py                  # Pytest configuration
├── workflow_patterns.py         # All 43 pattern fixtures
└── README.md                    # This file
```

## See Also

- `/Users/sac/dev/kgcl/ontology/workflows/core/yawl-pattern-permutations.ttl` - Pattern definitions
- `/Users/sac/dev/kgcl/tests/engine/test_workflow_pattern_fixtures.py` - Usage examples
- Van der Aalst et al., "Workflow Patterns: The Definitive Guide"
