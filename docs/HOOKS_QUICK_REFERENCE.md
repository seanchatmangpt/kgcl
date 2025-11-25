# Knowledge Hooks Quick Reference

## Basic Setup

```python
from pathlib import Path
from kgcl.unrdf_engine import (
    UnrdfEngine,
    PersistentHookRegistry,
    IngestionPipeline,
    HookExecutor,
    KnowledgeHook,
    HookPhase,
    HookContext,
    TriggerCondition,
)

# 1. Create hook registry
registry = PersistentHookRegistry(
    storage_path=Path("hooks.json"),
    auto_save=True
)

# 2. Create engine with hook support
engine = UnrdfEngine(
    file_path=Path("graph.ttl"),
    hook_registry=registry
)

# 3. Create pipeline with hooks
hook_executor = HookExecutor(registry)
pipeline = IngestionPipeline(engine, hook_executor=hook_executor)
```

## Hook Lifecycle Phases

| Phase | When | Use Case |
|-------|------|----------|
| `PRE_INGESTION` | Before data enters graph | Input validation, preprocessing |
| `ON_CHANGE` | When graph changes detected | Change tracking, notifications |
| `PRE_VALIDATION` | Before SHACL validation | Custom validation rules |
| `POST_VALIDATION` | After SHACL validation | Rollback on validation failure |
| `PRE_TRANSACTION` | Before transaction commit | Final checks, authorization |
| `POST_COMMIT` | After transaction commits | Feature materialization, indexing |
| `POST_TRANSACTION` | After transaction completed | Cleanup, notifications |
| `ON_ERROR` | On error | Error handling, rollback |
| `PRE_QUERY` | Before SPARQL query | Query modification, authorization |
| `POST_QUERY` | After SPARQL query | Result transformation, caching |

## Creating Hooks

### Simple Hook
```python
class MyHook(KnowledgeHook):
    def __init__(self):
        super().__init__(
            name="my_hook",
            phases=[HookPhase.POST_COMMIT]
        )

    def execute(self, context: HookContext):
        # Your logic here
        pass

registry.register(MyHook(), description="My custom hook")
```

### Hook with Trigger Condition
```python
class ConditionalHook(KnowledgeHook):
    def __init__(self):
        super().__init__(
            name="conditional_hook",
            phases=[HookPhase.POST_COMMIT],
            trigger=TriggerCondition(
                pattern="?person a foaf:Person",
                check_delta=True,
                min_matches=1
            )
        )

    def execute(self, context: HookContext):
        # Only executes when Person entities are in delta
        pass
```

### Hook with Priority
```python
class HighPriorityHook(KnowledgeHook):
    def __init__(self):
        super().__init__(
            name="high_priority_hook",
            phases=[HookPhase.POST_COMMIT],
            priority=100  # Higher number = higher priority
        )

    def execute(self, context: HookContext):
        pass
```

## Common Patterns

### 1. Validation Hook (Reject Invalid Data)
```python
class ValidationHook(KnowledgeHook):
    def __init__(self):
        super().__init__(
            name="validator",
            phases=[HookPhase.POST_VALIDATION]
        )

    def execute(self, context: HookContext):
        # Check delta for invalid data
        for s, p, o in context.delta:
            if self.is_invalid(s, p, o):
                context.metadata["should_rollback"] = True
                context.metadata["rollback_reason"] = "Invalid data detected"
```

### 2. Feature Materialization Hook
```python
class FeatureMaterializer(KnowledgeHook):
    def __init__(self):
        super().__init__(
            name="feature_materializer",
            phases=[HookPhase.POST_COMMIT],
            trigger=TriggerCondition(
                pattern="?entity a unrdf:Entity",
                check_delta=True
            )
        )

    def execute(self, context: HookContext):
        # Compute and add features to entities
        for s, p, o in context.delta:
            if str(p) == str(RDF.type):
                feature_value = self.compute_feature(s)
                context.graph.add((s, UNRDF.feature, Literal(feature_value)))
```

### 3. Cross-Hook Communication
```python
class Hook1(KnowledgeHook):
    def __init__(self):
        super().__init__(name="hook1", phases=[HookPhase.ON_CHANGE], priority=100)

    def execute(self, context: HookContext):
        # Share data with next hook
        context.metadata["processed_by_hook1"] = True
        context.metadata["entities"] = [...]

class Hook2(KnowledgeHook):
    def __init__(self):
        super().__init__(name="hook2", phases=[HookPhase.ON_CHANGE], priority=50)

    def execute(self, context: HookContext):
        # Access data from Hook1
        if context.metadata.get("processed_by_hook1"):
            entities = context.metadata.get("entities", [])
            # Process entities...
```

### 4. Query Modification Hook
```python
class QueryModifier(KnowledgeHook):
    def __init__(self):
        super().__init__(name="query_modifier", phases=[HookPhase.PRE_QUERY])

    def execute(self, context: HookContext):
        # Modify query before execution
        original_query = context.metadata.get("query")
        modified_query = self.add_security_filter(original_query)
        context.metadata["query"] = modified_query
```

### 5. Audit Trail Hook
```python
class AuditHook(KnowledgeHook):
    def __init__(self):
        super().__init__(
            name="auditor",
            phases=[HookPhase.POST_TRANSACTION]
        )

    def execute(self, context: HookContext):
        # Log transaction details
        audit_record = {
            "transaction_id": context.transaction_id,
            "timestamp": datetime.now(timezone.utc),
            "triples_added": len(context.delta),
            "agent": context.metadata.get("agent")
        }
        self.audit_log.append(audit_record)
```

## Accessing Hook Context

```python
def execute(self, context: HookContext):
    # Access full graph
    for s, p, o in context.graph:
        pass

    # Access changes (delta)
    for s, p, o in context.delta:
        pass

    # Query the graph
    query = "SELECT ?s WHERE { ?s a foaf:Person }"
    results = context.graph.query(query)

    # Access transaction ID
    txn_id = context.transaction_id

    # Share data between hooks
    context.metadata["my_data"] = "value"

    # Access previous hook receipts
    for receipt in context.receipts:
        print(f"{receipt.hook_id}: {receipt.duration_ms}ms")
```

## Hook Registry Operations

```python
# Register hook
hook_id = registry.register(MyHook(), description="My hook", version=1)

# Get hook
hook = registry.get("my_hook")

# Get hook metadata
metadata = registry.get_metadata("my_hook")

# Enable/disable hook
registry.enable_hook("my_hook")
registry.disable_hook("my_hook")

# List all hooks
all_hooks = registry.list_all()

# Get hooks for specific phase
post_commit_hooks = registry.get_for_phase(HookPhase.POST_COMMIT)

# Save to file
registry.save()

# Load from file
registry.load()

# Hot reload
registry.reload()

# Export to RDF
rdf_graph = registry.export_to_rdf(Path("hooks.ttl"))

# Get statistics
stats = registry.get_statistics()
print(f"Total hooks: {stats['total_hooks']}")
print(f"Enabled: {stats['enabled_hooks']}")
```

## Engine Hook Operations

```python
# Register hook directly on engine
engine.register_hook(MyHook(), description="My hook")

# Trigger hooks manually
delta = Graph()
delta.add((subject, predicate, object))
receipts = engine.trigger_hooks(delta, "post_commit")

# Query with hooks
results = engine.query_with_hooks("SELECT ?s WHERE { ?s a Person }")

# Get hook statistics
stats = engine.get_hook_statistics()
```

## Working with Receipts

```python
# In a hook
def execute(self, context: HookContext):
    # Previous receipts available
    for receipt in context.receipts:
        print(f"Hook: {receipt.hook_id}")
        print(f"Success: {receipt.success}")
        print(f"Duration: {receipt.duration_ms}ms")
        print(f"Error: {receipt.error}")
        print(f"Result: {receipt.result}")

# After transaction
txn = engine.transaction("user", "reason")
engine.add_triple(s, p, o, txn)
engine.commit(txn)

for receipt in txn.hook_receipts:
    print(receipt.to_dict())
```

## Performance Monitoring

```python
# Access execution history
hook_executor = HookExecutor(registry)
history = hook_executor.get_execution_history()

for execution in history:
    print(f"Hook: {execution['hook']}")
    print(f"Phase: {execution['phase']}")
    print(f"Duration: {execution['duration_ms']}ms")
    print(f"Success: {execution['success']}")

# Clear history
hook_executor.clear_history()
```

## Best Practices

1. **Keep hooks focused**: Each hook should do one thing well
2. **Use appropriate phases**: Choose the right lifecycle phase for your logic
3. **Handle errors gracefully**: Wrap hook logic in try/except
4. **Set priorities carefully**: Higher priority hooks run first (100 > 50 > 10)
5. **Use trigger conditions**: Avoid unnecessary hook executions
6. **Document hooks**: Use clear names and descriptions
7. **Test hooks independently**: Unit test each hook in isolation
8. **Monitor performance**: Track hook duration and optimize slow hooks
9. **Version hooks**: Increment version when changing hook logic
10. **Use receipts**: Leverage receipts for audit trails and debugging

## Common Pitfalls

1. **Modifying graph in PRE_* hooks**: Only read in PRE_ phases, modify in POST_
2. **Infinite loops**: Avoid hooks that trigger themselves
3. **Long-running hooks**: Keep execution under 10ms
4. **Missing hook_executor**: Pipeline needs HookExecutor to run hooks
5. **Wrong phase**: Using POST_COMMIT when you need PRE_TRANSACTION
6. **Not checking context.metadata**: Missing rollback signals from previous hooks
7. **Mutating context.graph directly**: Use transactions when possible
8. **Forgetting to register**: Hooks must be registered before they execute

## Debugging Hooks

```python
# Enable verbose logging
import logging
logging.getLogger("kgcl.unrdf_engine.hooks").setLevel(logging.DEBUG)

# Add debug prints in hooks
def execute(self, context: HookContext):
    print(f"Hook {self.name} executing")
    print(f"Delta size: {len(context.delta)}")
    print(f"Metadata: {context.metadata}")

# Check if hook should execute
hook = registry.get("my_hook")
context = HookContext(...)
if hook.should_execute(context):
    print("Hook will execute")
else:
    print("Hook will be skipped")

# Examine receipts for failures
for receipt in context.receipts:
    if not receipt.success:
        print(f"Failed: {receipt.hook_id}")
        print(f"Error: {receipt.error}")
```

## Examples Directory

See `/Users/sac/dev/kgcl/tests/integration/` for complete examples:
- `test_hooks_unrdf_integration.py` - Hook integration patterns
- `test_feature_materialization_hooks.py` - Feature materialization examples
