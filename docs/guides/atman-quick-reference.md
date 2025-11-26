# Atman Engine Quick Reference

## The Chatman Equation

```
A = μ(O)

Where:
  O = QuadDelta (Observation - intent to mutate)
  μ = Atman (Operator - deterministic engine)
  A = Receipt (Action - cryptographic proof)
```

## Installation

```bash
uv add kgcl
```

## Basic Usage

### 1. Create Engine

```python
from kgcl.engine import Atman

engine = Atman()
```

### 2. Define Mutation

```python
from kgcl.engine import QuadDelta

delta = QuadDelta(
    additions=[("urn:entity:123", "rdf:type", "schema:Person")],
    removals=[("urn:entity:123", "schema:status", "pending")]
)
```

### 3. Apply Transaction

```python
receipt = await engine.apply(delta, actor="user:alice")

if receipt.committed:
    print(f"Success: {receipt.merkle_root[:16]}...")
else:
    print(f"Failed: {receipt.error}")
```

## Core Types

### QuadDelta (Immutable)

```python
QuadDelta(
    additions: list[Triple] = [],  # Max 64
    removals: list[Triple] = [],   # Max 64
)
```

### Triple

```python
Triple = tuple[str, str, str]  # (subject, predicate, object)

# Examples
("urn:entity:123", "rdf:type", "schema:Person")
("urn:book:1984", "schema:author", "urn:person:orwell")
```

### Receipt

```python
Receipt(
    tx_id: str,              # UUID of transaction
    committed: bool,         # True if successful
    merkle_root: str,        # Hash(Prev + Delta)
    logic_hash: str,         # Hash(Active_Hooks)
    hook_results: list[HookResult],
    duration_ns: int,        # Execution time
    error: str | None,       # Error if failed
)
```

## Hook System

### PRE Hook (Guard - Can Block)

```python
from kgcl.engine import KnowledgeHook, HookMode

async def guard(store, delta, ctx) -> bool:
    # Return False to block transaction
    if some_invalid_condition:
        return False
    return True

hook = KnowledgeHook(
    hook_id="my-guard",
    mode=HookMode.PRE,
    handler=guard,
    priority=200,  # Higher = runs first
)
engine.register_hook(hook)
```

### POST Hook (Side Effect - Cannot Block)

```python
async def side_effect(store, delta, ctx) -> bool:
    # Always returns True
    await send_notification(delta)
    return True

hook = KnowledgeHook(
    hook_id="notify",
    mode=HookMode.POST,
    handler=side_effect,
    priority=100,
)
engine.register_hook(hook)
```

### Hook Handler Signature

```python
from rdflib import Dataset
from kgcl.engine import QuadDelta, TransactionContext

async def handler(
    store: Dataset,           # RDF store
    delta: QuadDelta,         # Proposed mutations
    ctx: TransactionContext,  # Transaction metadata
) -> bool:
    # Return True to allow, False to block (PRE only)
    return True
```

## Common Patterns

### 1. Batch Mutations

```python
triples = [...]  # Large list

for i in range(0, len(triples), 64):
    batch = triples[i:i+64]
    delta = QuadDelta(additions=batch)
    receipt = await engine.apply(delta)
    assert receipt.committed
```

### 2. Schema Validation

```python
async def validate_type(store, delta, ctx) -> bool:
    for s, p, o in delta.additions:
        if p == "schema:name":
            # Ensure entity has rdf:type
            has_type = any(
                s2 == s and p2 == "rdf:type"
                for s2, p2, o2 in delta.additions
            )
            if not has_type:
                return False
    return True

engine.register_hook(
    KnowledgeHook("schema-validator", HookMode.PRE, validate_type)
)
```

### 3. Audit Logging

```python
async def audit_log(store, delta, ctx) -> bool:
    log.info(
        f"TX {ctx.tx_id}: {ctx.actor} "
        f"+{len(delta.additions)} -{len(delta.removals)}"
    )
    return True

engine.register_hook(
    KnowledgeHook("audit", HookMode.POST, audit_log)
)
```

### 4. Cache Invalidation

```python
cache = {}

async def invalidate_cache(store, delta, ctx) -> bool:
    cache.clear()
    return True

engine.register_hook(
    KnowledgeHook("cache-invalidate", HookMode.POST, invalidate_cache)
)
```

## Provenance

### Chain Tip

```python
# Current hash
tip = engine.tip_hash

# Genesis hash (before any transactions)
from kgcl.engine import GENESIS_HASH
assert tip == GENESIS_HASH  # If no transactions yet
```

### Logic Hash

```python
# Hash of engine configuration
logic_hash = engine.compute_logic_hash()

# Changes when hooks are added/removed
engine.register_hook(hook)
new_hash = engine.compute_logic_hash()
assert new_hash != logic_hash
```

### Verify Chain

```python
receipts = []

for delta in deltas:
    receipt = await engine.apply(delta)
    receipts.append(receipt)

# Final tip should match last receipt
assert engine.tip_hash == receipts[-1].merkle_root
```

## Querying

### SPARQL

```python
results = engine.store.query("""
    SELECT ?s ?p ?o
    WHERE { ?s ?p ?o }
    LIMIT 10
""")

for row in results:
    print(row.s, row.p, row.o)
```

### Count Triples

```python
count = len(engine)
print(f"Triples: {count}")
```

### List Hooks

```python
for hook in engine.hooks:
    print(f"{hook.id}: {hook.mode.value} (priority={hook.priority})")
```

## Error Handling

### Transaction Failed

```python
receipt = await engine.apply(delta)

if not receipt.committed:
    print(f"Error: {receipt.error}")

    # Find which hook blocked it
    for result in receipt.hook_results:
        if not result.success:
            print(f"Blocked by: {result.hook_id}")
```

### Batch Too Large

```python
from pydantic import ValidationError

try:
    huge = [("urn:s", f"urn:p{i}", f"urn:o{i}") for i in range(100)]
    delta = QuadDelta(additions=huge)
except ValidationError as e:
    print("Batch too large! Max 64 triples.")
```

## Performance

### Targets (p99)

| Operation | Target |
|-----------|--------|
| Hook registration | <5ms |
| Transaction apply | <100ms |
| Logic hash | <10ms |

### Measure Latency

```python
import time

start = time.perf_counter()
receipt = await engine.apply(delta)
elapsed_ms = (time.perf_counter() - start) * 1000

print(f"Latency: {elapsed_ms:.2f}ms")

# Also available in receipt
duration_ms = receipt.duration_ns / 1_000_000
print(f"Receipt duration: {duration_ms:.2f}ms")
```

### Hook Telemetry

```python
receipt = await engine.apply(delta)

for result in receipt.hook_results:
    duration_ms = result.duration_ns / 1_000_000
    print(f"{result.hook_id}: {duration_ms:.2f}ms")
```

## Constants

```python
from kgcl.engine import CHATMAN_CONSTANT, GENESIS_HASH

CHATMAN_CONSTANT  # 64 (max batch size)
GENESIS_HASH      # "4d7c606c9002d3043ee3979533922e25..."
```

## Common Imports

```python
# Core
from kgcl.engine import (
    Atman,
    QuadDelta,
    Receipt,
    KnowledgeHook,
    HookMode,
    TransactionContext,
)

# Constants
from kgcl.engine import CHATMAN_CONSTANT, GENESIS_HASH

# RDF (for hook handlers)
from rdflib import Dataset, URIRef, Literal
```

## CLI Usage

```bash
# Apply mutations
kgcl mutate \
  -a "urn:entity:123,rdf:type,schema:Person" \
  -a "urn:entity:123,schema:name,Alice" \
  --actor user:alice

# Query
kgcl query "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"

# Status
kgcl status
```

## Testing

### Unit Test

```python
import pytest

@pytest.mark.asyncio
async def test_mutation():
    engine = Atman()
    delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
    receipt = await engine.apply(delta)

    assert receipt.committed is True
    assert len(engine) == 1
```

### Hook Test

```python
@pytest.mark.asyncio
async def test_guard_blocks():
    async def deny_all(store, delta, ctx) -> bool:
        return False

    engine = Atman()
    engine.register_hook(
        KnowledgeHook("deny", HookMode.PRE, deny_all)
    )

    delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
    receipt = await engine.apply(delta)

    assert receipt.committed is False
    assert "Guard Violation: deny" in receipt.error
```

## Troubleshooting

### "Topology Violation: Batch size exceeds Hot Path limit"

**Solution:** Split into batches of 64 or less.

```python
# ❌ WRONG
delta = QuadDelta(additions=[...100 triples...])

# ✅ RIGHT
for i in range(0, len(triples), 64):
    delta = QuadDelta(additions=triples[i:i+64])
    await engine.apply(delta)
```

### "Guard Violation: <hook-id>"

**Solution:** Check hook logic and data.

```python
receipt = await engine.apply(delta)

if not receipt.committed:
    for result in receipt.hook_results:
        if not result.success:
            print(f"Failed hook: {result.hook_id}")
```

### Slow Performance

**Solution:** Profile hooks, reduce batch size.

```python
receipt = await engine.apply(delta)

for result in receipt.hook_results:
    ms = result.duration_ns / 1_000_000
    if ms > 50:
        print(f"Slow hook: {result.hook_id} ({ms:.2f}ms)")
```

## Resources

- [Full Usage Guide](./atman-engine-usage.md)
- [Integration Guide](./atman-integration.md)
- [OpenAPI Spec](../api/atman-engine-openapi.yaml)
- [Source Code](/src/kgcl/engine/atman.py)
- [Tests](/tests/engine/test_atman.py)

## Support

- GitHub Issues: https://github.com/kgcl/kgcl/issues
- Discussions: https://github.com/kgcl/kgcl/discussions
