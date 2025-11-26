# KGCL Knowledge Hooks System

A comprehensive, production-ready hooks system for monitoring and reacting to knowledge graph changes with full provenance tracking and cryptographic receipts.

## Overview

The Knowledge Hooks system provides a powerful way to:
- Monitor knowledge graph changes in real-time
- React to graph events with custom handlers
- Track execution provenance with immutable receipts
- Validate graph state with SPARQL, SHACL, and custom conditions
- Chain hooks for complex workflows
- Generate cryptographic proofs of execution

## Architecture

The system follows **Chicago School TDD** principles with behavior-driven design:

```
├── core.py              # Hook, HookState, HookReceipt, HookRegistry, HookExecutor
├── conditions.py        # Condition system (SPARQL, SHACL, Delta, Threshold, Window, Composite)
├── lifecycle.py         # HookContext, HookExecutionPipeline, HookChain
└── receipts.py          # Receipt, ReceiptStore, MerkleAnchor, MerkleTree
```

## Core Components

### 1. Hook

A hook defines **what to monitor** (condition) and **what to do** (handler) when triggered.

```python
from kgcl.hooks import Hook, SparqlAskCondition

# Define condition
condition = SparqlAskCondition(
    query="""
    ASK {
        ?person a :Person ;
                :age ?age .
        FILTER(?age > 100)
    }
    """
)

# Define handler
def alert_handler(context):
    person = context.get("person")
    return {"alert": f"Person {person} is over 100 years old!"}

# Create hook
hook = Hook(
    name="centenarian_alert",
    description="Alert when person over 100",
    condition=condition,
    handler=alert_handler,
    priority=90  # High priority
)
```

### 2. Hook Lifecycle

Hooks transition through states: `PENDING → ACTIVE → EXECUTED → COMPLETED/FAILED`

```python
from kgcl.hooks import HookExecutor

executor = HookExecutor()
receipt = await executor.execute(hook, context={"person": "Alice"})

print(f"State: {hook.state}")           # COMPLETED
print(f"Duration: {receipt.duration_ms}ms")
print(f"Result: {receipt.handler_result}")
```

### 3. Condition System

Multiple condition types for flexible triggering:

#### SPARQL Conditions

```python
from kgcl.hooks import SparqlSelectCondition

condition = SparqlSelectCondition(
    query="""
    SELECT ?person WHERE {
        ?person a :Person ;
                :hasDisease :COVID19 .
    }
    """
)
```

#### SHACL Validation

```python
from kgcl.hooks import ShaclCondition

condition = ShaclCondition(
    shapes="""
    @prefix sh: <http://www.w3.org/ns/shacl#> .

    :PersonShape
        a sh:NodeShape ;
        sh:targetClass :Person ;
        sh:property [
            sh:path :name ;
            sh:minCount 1 ;
            sh:datatype xsd:string ;
        ] .
    """
)
```

#### Delta Detection

```python
from kgcl.hooks import DeltaCondition, DeltaType

condition = DeltaCondition(
    delta_type=DeltaType.INCREASE,
    query="SELECT (COUNT(*) as ?count) WHERE { ?s a :Person }"
)
```

#### Threshold Conditions

```python
from kgcl.hooks import ThresholdCondition, ThresholdOperator

condition = ThresholdCondition(
    variable="temperature",
    operator=ThresholdOperator.GREATER_THAN,
    value=100.0
)
```

#### Time Window Aggregation

```python
from kgcl.hooks import WindowCondition, WindowAggregation, ThresholdOperator

condition = WindowCondition(
    variable="requests",
    window_seconds=60,
    aggregation=WindowAggregation.SUM,
    threshold=1000,
    operator=ThresholdOperator.GREATER_THAN
)
```

#### Composite Conditions (AND, OR, NOT)

```python
from kgcl.hooks import CompositeCondition, CompositeOperator

condition = CompositeCondition(
    operator=CompositeOperator.AND,
    conditions=[
        ThresholdCondition("age", ThresholdOperator.GREATER_THAN, 65),
        ThresholdCondition("risk_score", ThresholdOperator.GREATER_THAN, 7)
    ]
)
```

### 4. Hook Registry

Manage multiple hooks with automatic priority ordering:

```python
from kgcl.hooks import HookRegistry

registry = HookRegistry()

registry.register(hook1)
registry.register(hook2)
registry.register(hook3)

# Get hooks sorted by priority (high to low)
sorted_hooks = registry.get_all_sorted()
```

### 5. Execution Pipeline

Execute multiple hooks with error handling:

```python
from kgcl.hooks import HookExecutionPipeline

pipeline = HookExecutionPipeline(stop_on_error=False)

receipts = await pipeline.execute_batch(
    hooks=[hook1, hook2, hook3],
    context={"graph": my_graph}
)

for receipt in receipts:
    print(f"{receipt.hook_id}: {receipt.error or 'SUCCESS'}")
```

### 6. Hook Chaining

Chain hooks for sequential processing:

```python
from kgcl.hooks import HookChain

chain = HookChain(hooks=[
    validation_hook,
    enrichment_hook,
    notification_hook
])

receipts = await chain.execute(context={"data": input_data})
```

### 7. Receipts & Provenance

Every hook execution produces an immutable cryptographic receipt:

```python
# Receipt contains complete execution record
receipt = await executor.execute(hook, context)

print(receipt.hook_id)              # Hook identifier
print(receipt.timestamp)            # Execution time
print(receipt.actor)                # Who triggered it
print(receipt.condition_result)     # Condition evaluation
print(receipt.handler_result)       # Handler output
print(receipt.duration_ms)          # Execution time
print(receipt.error)                # Any errors
print(receipt.compute_hash())       # SHA256 hash

# Generate cryptographic proof
proof = receipt.generate_proof()
print(proof["hash"])
print(proof["merkle_anchor"])

# Export to JSON-LD
json_ld = receipt.to_json_ld()

# Export to RDF triples
triples = receipt.to_rdf_triples()
```

### 8. Receipt Storage & Querying

Store and query receipts:

```python
from kgcl.hooks import ReceiptStore

store = ReceiptStore()

# Save receipt
await store.save(receipt)

# Query by hook ID
receipts = await store.query(hook_id="centenarian_alert")

# Query by actor
receipts = await store.query(actor="alice")

# Query by time range
receipts = await store.query(
    timestamp_from=datetime(2025, 1, 1),
    timestamp_to=datetime(2025, 12, 31)
)
```

## Integration with UNRDF

Hooks integrate seamlessly with UNRDF graph stores:

```python
from kgcl.hooks import Hook, SparqlSelectCondition

def graph_update_handler(context):
    graph = context.get("graph")

    # Modify graph
    graph.add_triple(
        "http://example.org/event/123",
        "http://purl.org/dc/terms/created",
        datetime.utcnow().isoformat()
    )

    return {"triples_added": 1}

hook = Hook(
    name="record_graph_change",
    description="Record graph changes",
    condition=SparqlSelectCondition(query="..."),
    handler=graph_update_handler
)

# Execute with graph context
receipt = await executor.execute(hook, context={"graph": unrdf_store})
```

## Performance

- **Condition evaluation**: < 10ms
- **Hook execution**: < 100ms (excluding handler)
- **Receipt storage**: < 5ms
- **Supports batching**: Execute multiple hooks efficiently

## Observability

Built-in OpenTelemetry support:

```python
# Hooks automatically emit OTEL spans
# Track:
# - hook_executions_total
# - hook_duration_ms
# - hook_errors_total
```

## Testing

100% test coverage with 84 comprehensive tests:

```bash
# Run all tests
pytest tests/hooks/ -v

# Run with coverage
pytest tests/hooks/ --cov=kgcl.hooks --cov-report=html

# Type checking
mypy src/kgcl/hooks/ --strict
```

## Examples

### Example 1: Data Quality Hook

```python
from kgcl.hooks import Hook, ShaclCondition

# Validate data quality on every update
quality_hook = Hook(
    name="data_quality_check",
    description="Validate data against SHACL shapes",
    condition=ShaclCondition(shapes=load_shacl_shapes()),
    handler=lambda ctx: {"valid": True} if ctx else {"valid": False},
    priority=100  # Run first
)
```

### Example 2: Performance Monitoring

```python
from kgcl.hooks import Hook, WindowCondition, WindowAggregation, ThresholdOperator

# Alert on high query load
performance_hook = Hook(
    name="query_load_alert",
    description="Alert when query rate exceeds threshold",
    condition=WindowCondition(
        variable="queries_per_second",
        window_seconds=60,
        aggregation=WindowAggregation.AVG,
        threshold=100,
        operator=ThresholdOperator.GREATER_THAN
    ),
    handler=lambda ctx: send_alert("High query load detected!"),
    priority=50
)
```

### Example 3: Automated Enrichment

```python
from kgcl.hooks import Hook, SparqlSelectCondition, HookChain

# Multi-stage enrichment pipeline
detect_hook = Hook(
    name="detect_new_entities",
    description="Detect new entities needing enrichment",
    condition=SparqlSelectCondition(query="SELECT ?entity WHERE { ?entity :needsEnrichment true }"),
    handler=lambda ctx: {"entities": ctx.get("entities", [])}
)

enrich_hook = Hook(
    name="enrich_entities",
    description="Fetch external data for entities",
    condition=AlwaysTrueCondition(),
    handler=lambda ctx: enrich_from_external_api(ctx["entities"])
)

validate_hook = Hook(
    name="validate_enrichment",
    description="Validate enriched data",
    condition=ShaclCondition(shapes=enrichment_shapes),
    handler=lambda ctx: {"validated": True}
)

# Chain hooks
chain = HookChain([detect_hook, enrich_hook, validate_hook])
receipts = await chain.execute(context={"graph": graph})
```

## Security

- Immutable receipts prevent tampering
- Cryptographic hashing (SHA256)
- Merkle tree anchoring to graph state
- Full audit trail
- Actor tracking

## Best Practices

1. **Priority Management**: Use priority to control execution order (0-100, higher = earlier)
2. **Error Handling**: Use `stop_on_error=False` for resilient pipelines
3. **Timeouts**: Set appropriate timeouts to prevent runaway execution
4. **Caching**: Use condition caching for expensive queries
5. **Monitoring**: Track receipts for debugging and compliance
6. **Testing**: Write behavior tests before implementation (Chicago School TDD)

## API Reference

### Core Classes

- `Hook`: Main hook definition
- `HookState`: Lifecycle states enum
- `HookReceipt`: Immutable execution receipt
- `HookRegistry`: Hook management
- `HookExecutor`: Hook execution engine

### Condition Classes

- `Condition`: Abstract base
- `SparqlAskCondition`: SPARQL ASK queries
- `SparqlSelectCondition`: SPARQL SELECT queries
- `ShaclCondition`: SHACL validation
- `DeltaCondition`: Graph change detection
- `ThresholdCondition`: Numeric thresholds
- `WindowCondition`: Time window aggregation
- `CompositeCondition`: Logical combinations

### Lifecycle Classes

- `HookContext`: Execution context
- `HookExecutionPipeline`: Batch execution
- `HookChain`: Sequential chaining
- `HookLifecycleEvent`: Event system

### Receipt Classes

- `Receipt`: Cryptographic receipt
- `ReceiptStore`: Receipt persistence
- `MerkleAnchor`: Graph state anchor
- `MerkleTree`: Merkle tree implementation

## Type Safety

100% type hints with mypy strict mode compliance:

```bash
mypy src/kgcl/hooks/ --strict
# Success: no issues found in 5 source files
```

## License

Part of the KGCL (Knowledge Graph Change Language) project.

## Contributing

This system was built using **Chicago School TDD**:
- Write behavior tests FIRST
- Implementation follows tests
- No mocking of domain objects
- Real object collaboration

See `tests/hooks/` for comprehensive test examples.

## Support

For issues and questions, please refer to the KGCL documentation and test suite.
