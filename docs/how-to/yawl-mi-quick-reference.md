# YAWL Multiple Instance Patterns - Quick Reference

## Pattern Selection Guide

| Pattern | When to Use | Instance Count Known |
|---------|-------------|---------------------|
| **12: MI without Sync** | Fire-and-forget, no waiting | Design time |
| **13: MI Design-Time** | Fixed count, wait for all | Design time |
| **14: MI Runtime** | Variable count, wait for all | Runtime start |
| **15: MI Dynamic** | Event-driven, unknown count | Runtime (ongoing) |

## Quick Start Examples

### Pattern 12: Fire-and-Forget

```python
from kgcl.yawl_engine.patterns.multiple_instance import MIWithoutSync

# Send 100 notifications, don't wait
pattern = MIWithoutSync()
result = pattern.execute(graph, send_notification, context={"count": 100})
# Continues immediately
```

### Pattern 13: Fixed Count

```python
from kgcl.yawl_engine.patterns.multiple_instance import MIDesignTime

# Exactly 3 reviewers required
pattern = MIDesignTime(instance_count=3)
result = pattern.execute(graph, review_task, context={})
# Waits for all 3 to complete
```

### Pattern 14: Runtime Variable

```python
from kgcl.yawl_engine.patterns.multiple_instance import MIRunTimeKnown

# One instance per order in batch
pattern = MIRunTimeKnown(instance_count_variable="order_count")
result = pattern.execute(
    graph,
    process_order,
    context={"order_count": len(orders)}
)
# Waits for all orders to complete
```

### Pattern 15: Dynamic Events

```python
from kgcl.yawl_engine.patterns.multiple_instance import MIDynamic

# Process events as they arrive
pattern = MIDynamic(
    spawn_condition="order_received",
    termination_condition="queue_empty"
)
result = pattern.execute(
    graph,
    handle_order,
    context={"events": event_queue}
)
# Spawns instances dynamically
```

## Completion Tracking

```python
from kgcl.yawl_engine.patterns.multiple_instance import (
    check_completion,
    mark_instance_complete,
)

# After instance finishes
mark_instance_complete(graph, instance_id)

# Check if all done
if check_completion(graph, parent_id):
    # All instances completed
    continue_workflow()
```

## ExecutionResult Structure

```python
@dataclass(frozen=True)
class ExecutionResult:
    success: bool                    # True if spawning succeeded
    instance_ids: list[str]          # List of spawned instance IDs
    state: MIState                   # Current state (RUNNING, COMPLETED, FAILED)
    metadata: dict[str, Any]         # Pattern-specific metadata
    error: str | None                # Error message if failed

# Access results
if result.success:
    for instance_id in result.instance_ids:
        # Process instance
        pass
    parent_id = result.metadata["parent_id"]  # Patterns 13-14
```

## Common Metadata Keys

| Key | Patterns | Type | Description |
|-----|----------|------|-------------|
| `pattern` | All | int | Pattern ID (12-15) |
| `sync` | 12 | bool | False for fire-and-forget |
| `requires_sync` | 13-15 | bool | True if synchronization needed |
| `parent_id` | 13-15 | str | Parent MI identifier |
| `instance_count` | 13-14 | int | Total instances spawned |
| `count_variable` | 14 | str | Variable name used for count |
| `initial_instance_count` | 15 | int | Initial event count |
| `spawn_condition` | 15 | str | Event trigger condition |
| `termination_condition` | 15 | str\|None | Stop condition |

## Error Handling

### Pattern 14: Missing Variable

```python
pattern = MIRunTimeKnown(instance_count_variable="items")
result = pattern.execute(graph, task, context={})

if not result.success:
    print(result.error)
    # "Instance count variable 'items' not found in context"
```

### Pattern 14: Invalid Count

```python
result = pattern.execute(graph, task, context={"items": "five"})

if not result.success:
    print(result.error)
    # "Instance count must be positive integer, got 'five'"
```

### Pattern 13: Zero Count

```python
try:
    pattern = MIDesignTime(instance_count=0)
except ValueError as e:
    print(e)
    # "Instance count must be positive, got 0"
```

## RDF Graph Queries

### Get All Instances of Task

```python
from rdflib import Namespace

YAWL = Namespace("http://www.yawlsystem.com/yawl/elements/")

instances = list(graph.subjects(YAWL.instanceOf, task))
```

### Get Instance State

```python
instance_uri = URIRef(instance_id)
states = list(graph.objects(instance_uri, YAWL.state))
state = str(states[0])  # "running", "completed", etc.
```

### Get Parent ID

```python
parents = list(graph.objects(instance_uri, YAWL.parentMI))
parent_id = str(parents[0]) if parents else None
```

### Get Completion Status

```python
parent_uri = URIRef(parent_id)
required = int(list(graph.objects(parent_uri, YAWL.requiredInstances))[0])
completed = int(list(graph.objects(parent_uri, YAWL.completedInstances))[0])
progress = f"{completed}/{required}"
```

## Best Practices

### ✅ DO

- Use Pattern 12 for notifications/logging where completion doesn't matter
- Use Pattern 13 when instance count is truly fixed (e.g., 3 reviewers)
- Use Pattern 14 when count varies but known at start (e.g., batch size)
- Use Pattern 15 for event-driven workflows
- Always check `result.success` before using `result.instance_ids`
- Use `check_completion()` before continuing workflow
- Validate runtime variables exist before Pattern 14

### ❌ DON'T

- Don't use Pattern 12 if you need to wait for completion
- Don't use Pattern 13 for variable counts
- Don't assume Pattern 14 variables exist without validation
- Don't skip error handling on `ExecutionResult`
- Don't modify instance state directly (use `mark_instance_complete()`)
- Don't forget to track `parent_id` for synchronization

## Performance Tips

1. **Pattern 12**: Fastest - no synchronization overhead
2. **Pattern 13/14**: Use when synchronization required
3. **Pattern 15**: Highest flexibility, slight overhead for dynamic tracking
4. Batch `mark_instance_complete()` calls when possible
5. Use `check_completion()` sparingly (RDF query)

## Testing

### Unit Test Template

```python
def test_my_mi_pattern(empty_graph: Graph, sample_task: URIRef) -> None:
    """Test MI pattern behavior."""
    pattern = MIDesignTime(instance_count=3)
    result = pattern.execute(empty_graph, sample_task, context={})

    # Assert success
    assert result.success
    assert len(result.instance_ids) == 3
    assert result.state == MIState.RUNNING

    # Verify RDF graph
    instances = list(empty_graph.subjects(YAWL.instanceOf, sample_task))
    assert len(instances) == 3

    # Complete instances
    for iid in result.instance_ids:
        mark_instance_complete(empty_graph, iid)

    # Check completion
    assert check_completion(empty_graph, result.metadata["parent_id"])
```

## Troubleshooting

### Problem: Instances not spawning

**Check:**
1. Pattern type matches use case
2. Context contains required variables (Pattern 14)
3. `result.success` is True
4. No ValueError exceptions

### Problem: Completion not tracking

**Check:**
1. Using patterns 13-14 (pattern 12 has no tracking)
2. Calling `mark_instance_complete()` for each instance
3. Correct `parent_id` from result metadata
4. RDF graph persistence

### Problem: Type errors

**Check:**
1. Using `cast(Literal, obj).value` for RDF values
2. Type narrowing for `result.error` (check `is not None` first)
3. All function signatures have type hints

## Import Paths

```python
# Patterns
from kgcl.yawl_engine.patterns.multiple_instance import (
    MIWithoutSync,      # Pattern 12
    MIDesignTime,       # Pattern 13
    MIRunTimeKnown,     # Pattern 14
    MIDynamic,          # Pattern 15
)

# Utilities
from kgcl.yawl_engine.patterns.multiple_instance import (
    check_completion,
    mark_instance_complete,
    ExecutionResult,
    MIState,
)

# RDF
from rdflib import Graph, URIRef, Literal, Namespace
```

## Next Steps

- See `docs/yawl_mi_patterns_summary.md` for full documentation
- Check `tests/yawl_engine/test_multiple_instance.py` for examples
- Review YAWL specification for pattern details
