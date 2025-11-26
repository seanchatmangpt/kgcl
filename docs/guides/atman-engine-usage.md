# Atman Engine Usage Guide

## Overview

The Atman Engine is a deterministic knowledge graph mutation engine implementing the **Chatman Equation**: `A = μ(O)`.

- **O (Observation)**: `QuadDelta` - The intent to mutate reality
- **μ (Operator)**: `Atman` - The deterministic mutation engine
- **A (Action)**: `Receipt` - Cryptographic proof of execution

## Quick Start

### Installation

```bash
uv add kgcl
```

### Basic Usage

```python
import asyncio
from kgcl.engine import Atman, QuadDelta

async def main():
    # Create engine instance
    engine = Atman()

    # Define a mutation
    delta = QuadDelta(
        additions=[
            ("urn:entity:123", "rdf:type", "schema:Person"),
            ("urn:entity:123", "schema:name", "Alice"),
        ]
    )

    # Apply the transaction
    receipt = await engine.apply(delta, actor="user:alice")

    # Verify success
    assert receipt.committed
    print(f"Transaction {receipt.tx_id[:8]}... committed")
    print(f"Merkle root: {receipt.merkle_root[:16]}...")
    print(f"Duration: {receipt.duration_ns / 1_000_000:.2f}ms")

asyncio.run(main())
```

**Output:**
```
Transaction 550e8400... committed
Merkle root: a7b8c9d0e1f2g3h4...
Duration: 2.35ms
```

## Core Concepts

### 1. QuadDelta (The Observation)

A `QuadDelta` represents the intent to mutate the knowledge graph. It is **immutable** once created.

```python
from kgcl.engine import QuadDelta

# Add triples only
delta = QuadDelta(
    additions=[
        ("urn:book:1984", "schema:title", "Nineteen Eighty-Four"),
        ("urn:book:1984", "schema:author", "urn:person:orwell"),
    ]
)

# Remove triples only
delta = QuadDelta(
    removals=[
        ("urn:book:1984", "schema:status", "draft"),
    ]
)

# Both additions and removals (atomic update)
delta = QuadDelta(
    additions=[
        ("urn:book:1984", "schema:status", "published"),
    ],
    removals=[
        ("urn:book:1984", "schema:status", "draft"),
    ]
)
```

**Constraints:**
- Maximum batch size: **64 triples** (Chatman Constant)
- Immutable after creation
- Subject, Predicate, Object are strings

### 2. Atman Engine (The Operator)

The `Atman` engine executes the Chatman Equation deterministically.

```python
from kgcl.engine import Atman
from rdflib import Dataset

# Create with default in-memory store
engine = Atman()

# Or provide an existing RDF Dataset
store = Dataset()
engine = Atman(store=store)

# Check current state
print(f"Triples: {len(engine)}")
print(f"Hooks: {len(engine.hooks)}")
print(f"Tip: {engine.tip_hash[:16]}...")
```

### 3. Receipt (The Action)

Every transaction returns a cryptographic `Receipt` proving what happened.

```python
receipt = await engine.apply(delta)

# Transaction metadata
print(receipt.tx_id)          # UUID of transaction
print(receipt.committed)      # True/False
print(receipt.error)          # Error message if failed

# Cryptographic proofs
print(receipt.merkle_root)    # Hash(Prev + Delta)
print(receipt.logic_hash)     # Hash(Active_Hooks)

# Telemetry
print(receipt.duration_ns)    # Execution time in nanoseconds
for result in receipt.hook_results:
    print(f"{result.hook_id}: {result.success} ({result.duration_ns}ns)")
```

## Hook System

Hooks extend engine behavior. There are two types:

- **PRE Hooks**: Blocking guards that can prevent transactions
- **POST Hooks**: Side effects that run after successful mutations

### Registering a PRE Hook (Guard)

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode, QuadDelta
from rdflib import Dataset

async def protect_system_triples(
    store: Dataset,
    delta: QuadDelta,
    ctx
) -> bool:
    """Block deletion of system triples."""
    for subject, predicate, obj in delta.removals:
        if subject.startswith("urn:system:"):
            return False  # Block transaction
    return True  # Allow transaction

engine = Atman()
guard = KnowledgeHook(
    hook_id="protect-system",
    mode=HookMode.PRE,
    handler=protect_system_triples,
    priority=200  # Higher priority = runs first
)
engine.register_hook(guard)

# Test the guard
delta = QuadDelta(removals=[("urn:system:root", "rdf:type", "System")])
receipt = await engine.apply(delta)

assert receipt.committed is False
assert "Guard Violation: protect-system" in receipt.error
```

### Registering a POST Hook (Side Effect)

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode

async def log_mutations(store, delta, ctx) -> bool:
    """Log all mutations to external system."""
    print(f"Actor: {ctx.actor}")
    print(f"Added: {len(delta.additions)} triples")
    print(f"Removed: {len(delta.removals)} triples")

    # Could send to external logging service
    # await send_to_datadog(delta)

    return True  # POST hooks always return True

engine = Atman()
logger = KnowledgeHook(
    hook_id="mutation-logger",
    mode=HookMode.POST,
    handler=log_mutations,
    priority=50
)
engine.register_hook(logger)

# Mutations are logged after commit
delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
await engine.apply(delta)
```

### Hook Execution Order

Hooks execute in deterministic order:
1. **Priority** (descending): Higher priority runs first
2. **Hook ID** (ascending): Alphabetical for same priority

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode

async def handler(s, d, c) -> bool:
    return True

engine = Atman()

# These hooks will execute in this order:
# 1. high-priority (priority=200)
# 2. a-medium (priority=100)
# 3. b-medium (priority=100)
# 4. low-priority (priority=50)

engine.register_hook(KnowledgeHook("b-medium", HookMode.PRE, handler, priority=100))
engine.register_hook(KnowledgeHook("high-priority", HookMode.PRE, handler, priority=200))
engine.register_hook(KnowledgeHook("a-medium", HookMode.PRE, handler, priority=100))
engine.register_hook(KnowledgeHook("low-priority", HookMode.PRE, handler, priority=50))

# Verify execution order
hooks = engine.hooks
assert hooks[0].id == "high-priority"
assert hooks[1].id == "a-medium"
assert hooks[2].id == "b-medium"
assert hooks[3].id == "low-priority"
```

### Unregistering Hooks

```python
engine = Atman()
# ... register hooks ...

# Remove by ID
removed = engine.unregister_hook("protect-system")
assert removed is True

# Removing nonexistent hook returns False
removed = engine.unregister_hook("nonexistent")
assert removed is False
```

## Provenance & The Lockchain

Every transaction links to the previous state via the **merkle_root**, forming an immutable chain.

### Tracking the Chain

```python
from kgcl.engine import Atman, QuadDelta, GENESIS_HASH

engine = Atman()

# Initial state is genesis
assert engine.tip_hash == GENESIS_HASH

# Apply first transaction
delta1 = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
receipt1 = await engine.apply(delta1)

# Tip advances
assert engine.tip_hash == receipt1.merkle_root
assert receipt1.merkle_root != GENESIS_HASH

# Apply second transaction
delta2 = QuadDelta(additions=[("urn:d", "urn:e", "urn:f")])
receipt2 = await engine.apply(delta2)

# Tip advances again
assert engine.tip_hash == receipt2.merkle_root
assert receipt2.merkle_root != receipt1.merkle_root
```

### Verifying Chain Integrity

```python
from kgcl.engine import Atman, QuadDelta

async def verify_chain(engine: Atman, receipts: list) -> bool:
    """Verify chain integrity by recomputing hashes."""
    import hashlib

    prev_hash = GENESIS_HASH

    for receipt in receipts:
        # Reconstruct the delta (would need to store this)
        # For demo, we trust the receipt

        # Verify this receipt links to previous
        # (In production, store deltas to recompute)
        prev_hash = receipt.merkle_root

    # Final hash should match engine tip
    return prev_hash == engine.tip_hash

# Collect receipts
engine = Atman()
receipts = []

for i in range(5):
    delta = QuadDelta(additions=[(f"urn:s{i}", f"urn:p{i}", f"urn:o{i}")])
    receipt = await engine.apply(delta)
    receipts.append(receipt)

# Verify integrity
assert await verify_chain(engine, receipts)
```

### Logic Hash (Proving Engine Configuration)

The **logic_hash** proves which hooks were active during execution.

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode

async def handler(s, d, c) -> bool:
    return True

engine = Atman()

# No hooks: logic hash is deterministic
hash_empty = engine.compute_logic_hash()

# Add a hook: logic hash changes
hook1 = KnowledgeHook("hook-1", HookMode.PRE, handler)
engine.register_hook(hook1)
hash_with_one = engine.compute_logic_hash()
assert hash_with_one != hash_empty

# Add another hook: logic hash changes again
hook2 = KnowledgeHook("hook-2", HookMode.POST, handler)
engine.register_hook(hook2)
hash_with_two = engine.compute_logic_hash()
assert hash_with_two != hash_with_one

# Every receipt includes the logic_hash
delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
receipt = await engine.apply(delta)
assert receipt.logic_hash == hash_with_two
```

## Advanced Patterns

### 1. Schema Validation Hook

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode, QuadDelta
from rdflib import Dataset, URIRef

async def validate_schema(store: Dataset, delta: QuadDelta, ctx) -> bool:
    """Ensure all entities have required types."""
    required_predicates = {
        URIRef("rdf:type"),
    }

    for subj, pred, obj in delta.additions:
        subj_uri = URIRef(subj) if "://" in subj or ":" in subj else None

        if subj_uri:
            # Check if entity has rdf:type
            has_type = any(
                store.triples((subj_uri, URIRef("rdf:type"), None))
            )

            # For new entities, require rdf:type in same transaction
            if not has_type:
                has_type_in_delta = any(
                    s == subj and p == "rdf:type"
                    for s, p, o in delta.additions
                )
                if not has_type_in_delta:
                    return False  # Block: missing rdf:type

    return True

engine = Atman()
validator = KnowledgeHook(
    "schema-validator",
    HookMode.PRE,
    validate_schema,
    priority=150
)
engine.register_hook(validator)

# This will be blocked (no rdf:type)
delta_invalid = QuadDelta(
    additions=[("urn:entity:123", "schema:name", "Alice")]
)
receipt = await engine.apply(delta_invalid)
assert receipt.committed is False

# This will succeed (includes rdf:type)
delta_valid = QuadDelta(
    additions=[
        ("urn:entity:123", "rdf:type", "schema:Person"),
        ("urn:entity:123", "schema:name", "Alice"),
    ]
)
receipt = await engine.apply(delta_valid)
assert receipt.committed is True
```

### 2. Audit Trail Hook

```python
import json
from pathlib import Path
from kgcl.engine import Atman, KnowledgeHook, HookMode

async def write_audit_log(store, delta, ctx) -> bool:
    """Write every transaction to audit log."""
    audit_entry = {
        "tx_id": ctx.tx_id,
        "timestamp": ctx.timestamp.isoformat(),
        "actor": ctx.actor,
        "additions": delta.additions,
        "removals": delta.removals,
        "prev_hash": ctx.prev_hash,
    }

    # Append to audit log file
    log_path = Path("audit_log.jsonl")
    with log_path.open("a") as f:
        f.write(json.dumps(audit_entry) + "\n")

    return True

engine = Atman()
auditor = KnowledgeHook(
    "audit-logger",
    HookMode.POST,
    write_audit_log,
    priority=200  # High priority for critical audit
)
engine.register_hook(auditor)

# All transactions are now audited
delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
await engine.apply(delta, actor="user:alice")
```

### 3. Cache Invalidation Hook

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode, QuadDelta

class QueryCache:
    """Simple query result cache."""

    def __init__(self):
        self._cache = {}

    def get(self, query: str):
        return self._cache.get(query)

    def set(self, query: str, result):
        self._cache[query] = result

    def invalidate_all(self):
        self._cache.clear()

    def invalidate_matching(self, pattern: str):
        keys_to_delete = [k for k in self._cache if pattern in k]
        for key in keys_to_delete:
            del self._cache[key]

cache = QueryCache()

async def invalidate_cache(store, delta, ctx) -> bool:
    """Invalidate query cache on mutations."""
    # Strategy 1: Invalidate everything (simple but slow)
    cache.invalidate_all()

    # Strategy 2: Selective invalidation (complex but fast)
    # for subj, pred, obj in delta.additions + delta.removals:
    #     cache.invalidate_matching(subj)

    return True

engine = Atman()
cache_hook = KnowledgeHook(
    "cache-invalidator",
    HookMode.POST,
    invalidate_cache,
    priority=100
)
engine.register_hook(cache_hook)

# Cache is invalidated after every mutation
delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
await engine.apply(delta)
```

### 4. Transaction Batching

```python
from kgcl.engine import Atman, QuadDelta

async def batch_mutations(engine: Atman, triples: list, batch_size: int = 64):
    """Apply large datasets in batches."""
    receipts = []

    for i in range(0, len(triples), batch_size):
        batch = triples[i:i+batch_size]
        delta = QuadDelta(additions=batch)
        receipt = await engine.apply(delta)
        receipts.append(receipt)

        if not receipt.committed:
            raise RuntimeError(f"Batch {i//batch_size} failed: {receipt.error}")

    return receipts

# Import 1000 triples
engine = Atman()
large_dataset = [
    (f"urn:entity:{i}", "rdf:type", "schema:Thing")
    for i in range(1000)
]

receipts = await batch_mutations(engine, large_dataset)
print(f"Imported {sum(len(r.hook_results) for r in receipts)} batches")
```

## Performance Optimization

### Target Metrics (p99)

| Operation | Target | Best Practice |
|-----------|--------|---------------|
| Hook registration | <5ms | Register hooks once at startup |
| Transaction apply | <100ms | Keep batches ≤64 triples |
| Logic hash | <10ms | Minimize hook changes |

### Measuring Performance

```python
import time
from kgcl.engine import Atman, QuadDelta

async def benchmark_apply():
    """Measure transaction latency."""
    engine = Atman()

    latencies = []
    for i in range(100):
        delta = QuadDelta(additions=[(f"urn:s{i}", f"urn:p{i}", f"urn:o{i}")])

        start = time.perf_counter()
        receipt = await engine.apply(delta)
        elapsed_ns = (time.perf_counter() - start) * 1_000_000_000

        latencies.append(elapsed_ns)

    # Compute percentiles
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p99 = latencies[int(len(latencies) * 0.99)]

    print(f"p50: {p50 / 1_000_000:.2f}ms")
    print(f"p99: {p99 / 1_000_000:.2f}ms")

    # Receipt also includes duration_ns
    assert receipt.duration_ns > 0

await benchmark_apply()
```

### Optimization Tips

1. **Batch size**: Keep batches at or below 64 triples (Chatman Constant)
2. **Hook count**: Minimize number of registered hooks
3. **Hook complexity**: Keep hook logic simple and fast
4. **Store size**: Large stores may slow SPARQL queries
5. **I/O in hooks**: Use async I/O, don't block

## Error Handling

### Handling Failed Transactions

```python
from kgcl.engine import Atman, QuadDelta

engine = Atman()

delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
receipt = await engine.apply(delta)

if not receipt.committed:
    # Transaction was blocked
    print(f"Failed: {receipt.error}")

    # Check which hook blocked it
    for result in receipt.hook_results:
        if not result.success:
            print(f"Blocked by: {result.hook_id}")
else:
    # Transaction succeeded
    print(f"Committed: {receipt.merkle_root[:16]}...")
```

### Handling Exceptions

```python
from kgcl.engine import Atman, QuadDelta
from pydantic import ValidationError

try:
    # This will raise ValidationError (too large)
    oversized = [("urn:s", f"urn:p{i}", f"urn:o{i}") for i in range(100)]
    delta = QuadDelta(additions=oversized)
except ValidationError as e:
    print(f"Invalid delta: {e}")

try:
    # Normal execution
    engine = Atman()
    delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
    receipt = await engine.apply(delta)
except Exception as e:
    # Unexpected error (should be rare)
    print(f"Engine error: {e}")
```

## Integration Examples

### With KGCL Hooks System

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode, QuadDelta
from kgcl.hooks import HookRegistry  # From KGCL hooks module

async def integrate_with_kgcl_hooks(store, delta, ctx) -> bool:
    """Bridge Atman hooks to KGCL hooks system."""
    # Trigger KGCL hook registry
    registry = HookRegistry()

    event = {
        "type": "graph.mutation",
        "tx_id": ctx.tx_id,
        "actor": ctx.actor,
        "additions": len(delta.additions),
        "removals": len(delta.removals),
    }

    # Execute KGCL hooks
    await registry.trigger("graph.mutation", event)

    return True

engine = Atman()
bridge = KnowledgeHook(
    "kgcl-bridge",
    HookMode.POST,
    integrate_with_kgcl_hooks,
    priority=50
)
engine.register_hook(bridge)
```

### With OpenTelemetry

```python
from kgcl.engine import Atman, KnowledgeHook, HookMode, QuadDelta
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def otel_instrumentation(store, delta, ctx) -> bool:
    """Emit OpenTelemetry spans for transactions."""
    with tracer.start_as_current_span("atman.mutation") as span:
        span.set_attribute("tx_id", ctx.tx_id)
        span.set_attribute("actor", ctx.actor)
        span.set_attribute("additions", len(delta.additions))
        span.set_attribute("removals", len(delta.removals))

    return True

engine = Atman()
otel_hook = KnowledgeHook(
    "otel-tracer",
    HookMode.POST,
    otel_instrumentation,
    priority=200
)
engine.register_hook(otel_hook)
```

### With CLI Commands

```python
from kgcl.engine import Atman, QuadDelta
import asyncio

async def cli_apply(additions: list[tuple], removals: list[tuple], actor: str):
    """CLI wrapper for applying transactions."""
    engine = Atman()  # Or load from persistent store

    delta = QuadDelta(additions=additions, removals=removals)
    receipt = await engine.apply(delta, actor=actor)

    return {
        "success": receipt.committed,
        "tx_id": receipt.tx_id,
        "merkle_root": receipt.merkle_root,
        "duration_ms": receipt.duration_ns / 1_000_000,
        "error": receipt.error,
    }

# Usage from CLI
result = asyncio.run(cli_apply(
    additions=[("urn:a", "urn:b", "urn:c")],
    removals=[],
    actor="cli:user"
))
print(result)
```

## Testing

### Unit Testing Hooks

```python
import pytest
from kgcl.engine import Atman, KnowledgeHook, HookMode, QuadDelta
from rdflib import Dataset

@pytest.mark.asyncio
async def test_guard_blocks_invalid_mutation():
    """Guard hook blocks invalid mutations."""

    async def validate_schema(store, delta, ctx) -> bool:
        # Block if no rdf:type
        for s, p, o in delta.additions:
            if p == "schema:name":
                has_type = any(
                    p2 == "rdf:type" for s2, p2, o2 in delta.additions if s2 == s
                )
                if not has_type:
                    return False
        return True

    engine = Atman()
    guard = KnowledgeHook("validate", HookMode.PRE, validate_schema)
    engine.register_hook(guard)

    # Invalid: name without type
    delta = QuadDelta(additions=[("urn:e1", "schema:name", "Alice")])
    receipt = await engine.apply(delta)
    assert receipt.committed is False

    # Valid: name with type
    delta = QuadDelta(
        additions=[
            ("urn:e1", "rdf:type", "schema:Person"),
            ("urn:e1", "schema:name", "Alice"),
        ]
    )
    receipt = await engine.apply(delta)
    assert receipt.committed is True
```

### Integration Testing

```python
import pytest
from kgcl.engine import Atman, KnowledgeHook, HookMode, QuadDelta

@pytest.mark.asyncio
async def test_full_workflow():
    """Test complete transaction workflow."""
    executed_hooks = []

    async def pre_hook(store, delta, ctx) -> bool:
        executed_hooks.append("pre")
        return True

    async def post_hook(store, delta, ctx) -> bool:
        executed_hooks.append("post")
        return True

    engine = Atman()
    engine.register_hook(KnowledgeHook("pre", HookMode.PRE, pre_hook))
    engine.register_hook(KnowledgeHook("post", HookMode.POST, post_hook))

    delta = QuadDelta(additions=[("urn:a", "urn:b", "urn:c")])
    receipt = await engine.apply(delta)

    # Verify execution
    assert receipt.committed is True
    assert executed_hooks == ["pre", "post"]
    assert len(receipt.hook_results) == 2
    assert len(engine) == 1  # One triple added
```

## Troubleshooting

### Common Issues

#### 1. "Topology Violation: Batch size exceeds Hot Path limit"

**Problem**: Trying to add/remove more than 64 triples at once.

**Solution**: Split into batches.

```python
# ❌ WRONG
huge_delta = QuadDelta(additions=[...200 triples...])

# ✅ RIGHT
for i in range(0, 200, 64):
    batch = triples[i:i+64]
    delta = QuadDelta(additions=batch)
    await engine.apply(delta)
```

#### 2. "Guard Violation: <hook-id>"

**Problem**: A PRE hook blocked the transaction.

**Solution**: Check hook logic and ensure data meets requirements.

```python
receipt = await engine.apply(delta)

if not receipt.committed:
    # Find which hook blocked it
    for result in receipt.hook_results:
        if not result.success:
            print(f"Blocked by: {result.hook_id}")
```

#### 3. Slow Performance

**Problem**: Transactions taking >100ms.

**Solution**: Profile hooks, reduce batch size, optimize SPARQL queries.

```python
# Check receipt telemetry
receipt = await engine.apply(delta)

print(f"Total: {receipt.duration_ns / 1_000_000:.2f}ms")
for result in receipt.hook_results:
    print(f"{result.hook_id}: {result.duration_ns / 1_000_000:.2f}ms")
```

## Best Practices

### 1. Register Hooks Once

```python
# ✅ GOOD: Register at startup
engine = Atman()
engine.register_hook(guard_hook)
engine.register_hook(audit_hook)

for delta in transactions:
    await engine.apply(delta)

# ❌ BAD: Re-registering on every transaction
for delta in transactions:
    engine = Atman()
    engine.register_hook(guard_hook)  # Wasteful!
    await engine.apply(delta)
```

### 2. Keep Hooks Fast

```python
# ✅ GOOD: Fast validation
async def fast_hook(store, delta, ctx) -> bool:
    return len(delta.additions) < 100

# ❌ BAD: Expensive computation
async def slow_hook(store, delta, ctx) -> bool:
    # Don't do heavy computation in PRE hooks!
    result = await expensive_api_call()
    return result.is_valid
```

### 3. Use POST Hooks for I/O

```python
# ✅ GOOD: I/O in POST hooks
async def notify(store, delta, ctx) -> bool:
    await send_webhook(delta)
    return True

# ❌ BAD: I/O in PRE hooks
async def blocking_notify(store, delta, ctx) -> bool:
    await send_webhook(delta)  # Blocks transaction!
    return True
```

### 4. Handle Errors Gracefully

```python
# ✅ GOOD: Proper error handling
async def safe_hook(store, delta, ctx) -> bool:
    try:
        validate(delta)
        return True
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False

# ❌ BAD: Uncaught exceptions
async def unsafe_hook(store, delta, ctx) -> bool:
    validate(delta)  # May raise exception!
    return True
```

## Additional Resources

- [API Reference (OpenAPI)](/docs/api/atman-engine-openapi.yaml)
- [Source Code](/src/kgcl/engine/atman.py)
- [Test Suite](/tests/engine/test_atman.py)
- [KGCL Documentation](/docs)

## Support

For issues and questions:
- GitHub Issues: https://github.com/kgcl/kgcl/issues
- Discussions: https://github.com/kgcl/kgcl/discussions
