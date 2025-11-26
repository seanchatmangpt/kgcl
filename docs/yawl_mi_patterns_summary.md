# YAWL Multiple Instance Patterns Implementation

## Overview

Complete implementation of YAWL workflow patterns 12-15 (Multiple Instance patterns) with full type safety, comprehensive tests, and production-ready code.

## Implemented Patterns

### Pattern 12: Multiple Instance without Synchronization

**Fire-and-forget pattern** - spawns multiple instances without waiting for completion.

```python
pattern = MIWithoutSync()
instances = pattern.spawn_instances(graph, task, count=5)
# Spawns 5 instances, no synchronization barrier
```

**Use Cases:**
- Sending notifications to multiple recipients
- Broadcasting events without waiting for acknowledgment
- Parallel processing where completion doesn't matter

**Key Features:**
- No parent synchronization
- Immediate return after spawning
- Each instance runs independently

### Pattern 13: Multiple Instance with Design-Time Knowledge

**Fixed instance count** - number of instances known at design time (compile time).

```python
pattern = MIDesignTime(instance_count=3)  # Exactly 3 instances
result = pattern.execute(graph, task, context={})
# Spawns 3 instances with synchronization barrier
```

**Use Cases:**
- Fixed number of reviewers (e.g., 3 reviewers)
- Predefined set of approval steps
- Static parallel processing requirements

**Key Features:**
- Fixed instance count at design time
- Synchronization barrier created
- Workflow waits for all instances to complete

### Pattern 14: Multiple Instance with Runtime Knowledge

**Runtime-determined count** - number of instances known when workflow starts.

```python
pattern = MIRunTimeKnown(instance_count_variable="order_count")
result = pattern.execute(
    graph,
    task,
    context={"order_count": 7}  # Count from workflow data
)
# Spawns 7 instances based on runtime variable
```

**Use Cases:**
- One instance per order in a batch
- Processing variable-length lists
- Dynamic parallelism based on input data

**Key Features:**
- Instance count from runtime variable
- Validation of count value (must be positive integer)
- Synchronization barrier with runtime count

### Pattern 15: Multiple Instance without Runtime Knowledge

**Dynamic spawning** - instances created dynamically based on events/conditions.

```python
pattern = MIDynamic(
    spawn_condition="new_order_received",
    termination_condition="queue_empty"
)
result = pattern.execute(
    graph,
    task,
    context={"events": ["order1", "order2", "order3"]}
)
# Spawns instances dynamically as events arrive
```

**Use Cases:**
- Event-driven processing (orders arriving in real-time)
- Queue-based workflows
- Dynamic resource allocation

**Key Features:**
- Dynamic instance spawning based on events
- Optional termination condition
- No pre-determined synchronization count

## Implementation Details

### Type Safety

All patterns implemented with **100% type coverage** using Python 3.12+ syntax:

```python
@dataclass(frozen=True)
class ExecutionResult:
    success: bool
    instance_ids: list[str]
    state: MIState
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
```

### Completion Tracking

Utility functions for MI coordination:

```python
# Check if all instances completed
completed = check_completion(graph, parent_id)

# Mark instance as complete
mark_instance_complete(graph, instance_id)
# Automatically increments parent counter
```

### RDF Graph Structure

Each MI pattern stores metadata in RDF graph:

```python
# Instance metadata
(instance_uri, YAWL.instanceOf, task)
(instance_uri, YAWL.instanceNumber, Literal(i))
(instance_uri, YAWL.parentMI, parent_uri)
(instance_uri, YAWL.state, Literal(MIState.RUNNING.value))

# Parent synchronization (patterns 13, 14)
(parent_uri, YAWL.requiredInstances, Literal(count))
(parent_uri, YAWL.completedInstances, Literal(0))

# Dynamic spawning metadata (pattern 15)
(parent_uri, YAWL.spawnedInstances, Literal(count))
(parent_uri, YAWL.dynamicSpawning, Literal(True))
(parent_uri, YAWL.spawnCondition, Literal(condition))
```

## Test Coverage

Comprehensive test suite with **40 tests**, all passing in <0.1s:

### Test Categories

1. **Basic Functionality** (7 tests)
   - Spawning instances
   - State management
   - Sequential numbering
   - Input validation

2. **Synchronization** (6 tests)
   - Barrier creation
   - Parent-child relationships
   - Completion tracking

3. **Error Handling** (8 tests)
   - Missing variables
   - Invalid input types
   - Zero/negative counts
   - Missing parent references

4. **Dynamic Patterns** (7 tests)
   - Event-driven spawning
   - Termination conditions
   - Dynamic flags

5. **Integration Scenarios** (3 tests)
   - Full lifecycle workflows
   - Multi-phase execution
   - Event streaming

6. **Validation** (4 tests)
   - ExecutionResult invariants
   - Error message requirements

7. **Completion Tracking** (5 tests)
   - Counter increments
   - State updates
   - Missing data handling

### Example Integration Test

```python
def test_runtime_variable_workflow(empty_graph, sample_task):
    """Runtime variable determines instance count."""
    # Simulate batch of 5 orders
    context = {"order_count": 5, "batch_id": "B-123"}

    pattern = MIRunTimeKnown(instance_count_variable="order_count")
    result = pattern.execute(empty_graph, sample_task, context)

    assert result.success
    assert len(result.instance_ids) == 5

    # Complete first 3
    for iid in result.instance_ids[:3]:
        mark_instance_complete(empty_graph, iid)

    parent_id = result.metadata["parent_id"]
    assert not check_completion(empty_graph, parent_id)

    # Complete remaining 2
    for iid in result.instance_ids[3:]:
        mark_instance_complete(empty_graph, iid)

    assert check_completion(empty_graph, parent_id)
```

## Quality Metrics

### Code Quality

- ✅ **Type Coverage**: 100% (strict mypy)
- ✅ **Test Coverage**: 40 tests, all passing
- ✅ **Linting**: All Ruff rules passing
- ✅ **Code Style**: Auto-formatted with Ruff
- ✅ **Performance**: <0.1s test suite runtime

### Standards Compliance

- ✅ **YAWL Specification**: Patterns 12-15 fully implemented
- ✅ **Chicago School TDD**: Tests drive implementation
- ✅ **Immutability**: Frozen dataclasses for value objects
- ✅ **NumPy Docstrings**: Complete API documentation
- ✅ **Absolute Imports**: No relative imports

## Usage Examples

### Example 1: Email Notification (Pattern 12)

```python
# Send emails without waiting for delivery confirmation
pattern = MIWithoutSync()
result = pattern.execute(
    graph,
    send_email_task,
    context={"count": 100}  # Send to 100 recipients
)
# Continues immediately, doesn't wait for email delivery
```

### Example 2: Document Review (Pattern 13)

```python
# Exactly 3 reviewers required
pattern = MIDesignTime(instance_count=3)
result = pattern.execute(graph, review_task, context={})
# Workflow waits for all 3 reviewers to complete
```

### Example 3: Batch Order Processing (Pattern 14)

```python
# Process each order in the batch
pattern = MIRunTimeKnown(instance_count_variable="order_count")
result = pattern.execute(
    graph,
    process_order_task,
    context={"order_count": len(orders)}
)
# Spawns one instance per order
```

### Example 4: Real-time Event Processing (Pattern 15)

```python
# Process events as they arrive
pattern = MIDynamic(
    spawn_condition="order_received",
    termination_condition="queue_empty"
)

# Initial events
result = pattern.execute(
    graph,
    handle_order_task,
    context={"events": initial_orders}
)

# More events can spawn additional instances dynamically
```

## Files

### Implementation
- `src/kgcl/yawl_engine/patterns/multiple_instance.py` (667 lines)
  - 4 pattern classes
  - 2 utility functions
  - Full type hints
  - Comprehensive docstrings

### Tests
- `tests/yawl_engine/test_multiple_instance.py` (580 lines)
  - 40 comprehensive tests
  - 7 test classes
  - Integration scenarios
  - Edge case coverage

## Integration with YAWL Engine

The MI patterns integrate with the broader YAWL engine:

```python
from kgcl.yawl_engine.patterns.multiple_instance import (
    MIDesignTime,
    MIDynamic,
    MIRunTimeKnown,
    MIWithoutSync,
    check_completion,
    mark_instance_complete,
)

# Use in workflow execution
pattern = MIRunTimeKnown(instance_count_variable="items")
result = pattern.execute(graph, task, workflow_context)

# Track completion
for instance_id in result.instance_ids:
    # Process instance...
    mark_instance_complete(graph, instance_id)

if check_completion(graph, result.metadata["parent_id"]):
    # All instances completed, continue workflow
    pass
```

## References

- **YAWL Specification**: van der Aalst & ter Hofstede (2005)
- **Workflow Patterns**: http://www.workflowpatterns.com/
- **Pattern Catalog**: Multiple Instance patterns 12-15

## Future Enhancements

Potential extensions for MI patterns:

1. **Cancellation Policies**
   - Cancel all instances if one fails
   - Cancel remaining instances after N completions

2. **Advanced Synchronization**
   - Partial synchronization (e.g., wait for 2 out of 3)
   - Threshold-based completion (e.g., majority vote)

3. **Resource Management**
   - Instance pooling
   - Resource limits per instance
   - Load balancing across instances

4. **Monitoring**
   - Real-time instance status
   - Progress tracking
   - Performance metrics per instance

5. **Recovery**
   - Automatic retry on instance failure
   - Checkpoint/resume support
   - State persistence across restarts
