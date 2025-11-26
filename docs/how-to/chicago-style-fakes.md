# Chicago-Style TDD with Verified Fakes

## Overview

The `tests/fakes/` module provides in-memory test fakes for Chicago School Test-Driven Development. These fakes implement the same interfaces as production code but store data in memory for fast, predictable testing.

## Key Principles

1. **Real Interfaces**: Fakes implement the same protocols as production code
2. **In-Memory Storage**: All data stored in simple dict/list structures
3. **Observable State**: Fakes expose helper methods to inspect internal state
4. **No Mocking**: Real object interactions, no mock frameworks
5. **Full Type Safety**: Complete type hints matching production types

## Available Fakes

### FakeReceiptStore

Stores hook execution receipts in memory.

```python
from tests.fakes import FakeReceiptStore
from kgcl.unrdf_engine.hooks import Receipt, HookPhase

store = FakeReceiptStore()
receipt = Receipt(
    hook_id="test_hook",
    phase=HookPhase.PRE_TRANSACTION,
    timestamp=datetime.now(UTC),
    success=True,
    duration_ms=5.0
)
store.save(receipt)

# Inspection methods
assert store.count() == 1
assert store.successful_count() == 1
assert len(store.for_phase(HookPhase.PRE_TRANSACTION)) == 1
```

### FakeRdfStore

In-memory RDF triple store using rdflib.Graph.

```python
from tests.fakes import FakeRdfStore
from rdflib import URIRef, Literal

store = FakeRdfStore()
subject = URIRef("http://example.org/person1")
predicate = URIRef("http://xmlns.com/foaf/0.1/name")
obj = Literal("Alice")

store.add_triple(subject, predicate, obj)

# Inspection methods
assert store.count_triples() == 1
assert list(store.all_triples())[0] == (subject, predicate, obj)

# Query support
results = store.query("SELECT ?name WHERE { ?s foaf:name ?name }")
```

### FakeHookRegistry

In-memory hook registry for testing.

```python
from tests.fakes import FakeHookRegistry
from kgcl.unrdf_engine.hooks import KnowledgeHook, HookPhase

registry = FakeHookRegistry()
hook = MyValidationHook(name="validator", phases=[HookPhase.PRE_TRANSACTION])
registry.register(hook)

# Inspection methods
assert registry.count() == 1
assert registry.get("validator") == hook
hooks = registry.get_for_phase(HookPhase.PRE_TRANSACTION)
assert hook in hooks
```

### FakeHookExecutor

Executes hooks and records execution history.

```python
from tests.fakes import FakeHookExecutor, FakeHookRegistry
from kgcl.unrdf_engine.hooks import HookContext, HookPhase

registry = FakeHookRegistry()
executor = FakeHookExecutor(registry=registry)

# Register hooks
registry.register(my_hook)

# Execute
context = HookContext(
    phase=HookPhase.PRE_TRANSACTION,
    graph=Graph(),
    delta=Graph(),
    transaction_id="txn-001"
)
results = executor.execute_phase(HookPhase.PRE_TRANSACTION, context)

# Inspect history
history = executor.get_execution_history()
assert len(history) == 1
assert history[0]["success"] is True
```

### FakeTransactionStore

Stores transactions for testing.

```python
from tests.fakes import FakeTransactionStore
from kgcl.unrdf_engine.engine import Transaction, ProvenanceRecord

store = FakeTransactionStore()
txn = Transaction(
    transaction_id="txn-001",
    provenance=ProvenanceRecord(
        agent="test_user",
        timestamp=datetime.now(UTC),
        reason="test data"
    )
)
store.save(txn)

# Inspection methods
assert store.count() == 1
assert store.get("txn-001") == txn
assert len(store.committed()) == 0  # Not committed yet
```

### FakeIngestionPipeline

Simplified ingestion pipeline for testing.

```python
from tests.fakes import FakeIngestionPipeline

pipeline = FakeIngestionPipeline()
result = pipeline.ingest_json(
    data={"type": "Person", "name": "Alice"},
    agent="test_service"
)

# Verify results
assert result["success"] is True
assert result["triples_added"] > 0

# Inspect RDF store
assert pipeline.rdf_store.count_triples() == 2

# Inspect history
history = pipeline.get_history()
assert len(history) == 1
```

## Chicago-Style Test Example

```python
def test_hook_execution_with_real_collaborators():
    """Hook execution with real objects and fake storage.

    This demonstrates Chicago School TDD:
    - Real KnowledgeHook instances
    - Real HookExecutor logic
    - Real Graph from rdflib
    - Fake storage for verification
    - Assertions on observable state (not mocks)
    """
    # Arrange - real collaborators with fake storage
    registry = FakeHookRegistry()
    rdf_store = FakeRdfStore()

    hook = ValidationHook(name="validator", phases=[HookPhase.PRE_TRANSACTION])
    registry.register(hook)

    executor = FakeHookExecutor(registry=registry)

    # Act - real execution
    context = HookContext(
        phase=HookPhase.PRE_TRANSACTION,
        graph=rdf_store.graph,
        delta=Graph(),
        transaction_id="txn-001"
    )
    results = executor.execute_phase(HookPhase.PRE_TRANSACTION, context)

    # Assert - verify observable state
    assert len(results) == 1
    assert results[0]["success"] is True
    assert hook.executed_count == 1

    # Verify receipt was created
    assert len(context.receipts) == 1
    receipt = context.receipts[0]
    assert receipt.hook_id == "validator"
    assert receipt.success is True
    assert receipt.duration_ms > 0
```

## Why Fakes Instead of Mocks?

### Chicago School TDD Philosophy

1. **Real Interactions**: Tests verify actual object interactions
2. **Observable State**: Tests assert on visible state changes
3. **No Mock Frameworks**: Simpler tests, fewer dependencies
4. **Maintainability**: Tests survive refactoring better
5. **Confidence**: Tests exercise real code paths

### Comparison

**With Mocks (London School)**:
```python
# ❌ Fragile - tests implementation details
mock_registry = Mock()
mock_registry.get_for_phase.return_value = [mock_hook]
executor.execute_phase(HookPhase.PRE_TRANSACTION, context)
mock_hook.execute.assert_called_once()
```

**With Fakes (Chicago School)**:
```python
# ✅ Robust - tests observable behavior
registry = FakeHookRegistry()
registry.register(real_hook)
executor = FakeHookExecutor(registry=registry)
results = executor.execute_phase(HookPhase.PRE_TRANSACTION, context)
assert len(results) == 1
assert results[0]["success"] is True
```

## Best Practices

1. **Use Real Objects**: Only use fakes for storage/persistence
2. **Test Behavior**: Assert on observable state, not internal calls
3. **Keep Fakes Simple**: No complex logic in fakes
4. **Verify State**: Use fake helper methods to inspect state
5. **Integration Tests**: Combine multiple real objects with fakes

## Performance

All fakes are designed for **<1 second** test suite execution:

- In-memory storage (no I/O)
- Simple data structures
- No external dependencies
- Minimal overhead

## References

- [Growing Object-Oriented Software, Guided by Tests](http://www.growing-object-oriented-software.com/) - Freeman & Pryce
- [Test Double Patterns](https://martinfowler.com/bliki/TestDouble.html) - Martin Fowler
- [London vs Chicago TDD](https://github.com/testdouble/contributing-tests/wiki/London-school-TDD) - Test Double
