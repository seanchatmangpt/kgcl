# KGCL Test Factories

Comprehensive factory_boy fixtures for KGCL test data generation following Chicago School TDD principles.

## Installation

```bash
# Add factory_boy to dev dependencies
uv add --dev factory_boy
```

## Overview

This module provides production-grade test data factories for:

- **Hooks**: Hook, HookReceipt with timing and provenance
- **Conditions**: ConditionResult, AlwaysTrueCondition
- **Receipts**: Receipt with cryptographic hashing and JSON-LD
- **Transactions**: Transaction with ACID properties
- **Provenance**: MerkleAnchor for graph state anchoring

## Quick Start

```python
from tests.factories import (
    HookFactory,
    HookReceiptFactory,
    ReceiptFactory,
    TransactionFactory,
)

# Create a hook
hook = HookFactory(name="delta-monitor", priority=90)

# Create a successful receipt
receipt = HookReceiptFactory(hook_id=hook.name, error=None)
assert receipt.duration_ms > 0

# Create a failed receipt
failed = HookReceiptFactory(
    error="Handler timeout",
    handler_result=None
)
assert failed.error is not None

# Create a transaction with changes
tx = TransactionWithChangesFactory()
assert len(tx.added_triples) > 0
```

## Available Factories

### Condition Factories

#### `ConditionResultFactory`
Creates realistic condition evaluation results.

```python
# Basic usage
result = ConditionResultFactory()
assert isinstance(result.triggered, bool)

# With metadata
result = ConditionResultFactory(
    triggered=True,
    metadata={"bindings": 42, "query": "..."}
)
```

#### `AlwaysTrueConditionFactory`
Creates conditions that always trigger (useful for testing execution flow).

```python
condition = AlwaysTrueConditionFactory()
result = await condition.evaluate({})
assert result.triggered is True
```

### Hook Factories

#### `HookFactory`
Creates realistic hooks with conditions and handlers.

```python
# Basic hook
hook = HookFactory()
assert 0 <= hook.priority <= 100
assert hook.enabled is True

# Custom hook
hook = HookFactory(
    name="custom-hook",
    priority=95,
    timeout=5.0,
    actor="alice@example.com"
)

# Handler is callable
context = {"event": "test"}
result = hook.handler(context)
assert result["status"] == "success"
```

#### `HighPriorityHookFactory`
Creates hooks with priority >= 80 and stricter timeouts.

```python
hook = HighPriorityHookFactory()
assert hook.priority >= 80
assert hook.timeout == 10.0
```

#### `LowPriorityHookFactory`
Creates hooks with priority <= 30 and relaxed timeouts.

```python
hook = LowPriorityHookFactory()
assert hook.priority <= 30
assert hook.timeout == 60.0
```

#### `DisabledHookFactory`
Creates disabled hooks.

```python
hook = DisabledHookFactory()
assert hook.enabled is False
```

### HookReceipt Factories

#### `HookReceiptFactory`
Creates realistic hook execution receipts.

```python
# Successful execution
receipt = HookReceiptFactory(error=None)
assert receipt.duration_ms > 0
assert receipt.handler_result is not None

# Failed execution
receipt = HookReceiptFactory(
    error="Timeout exceeded",
    handler_result=None,
    stack_trace="..."
)
```

#### `FailedHookReceiptFactory`
Creates receipts representing failed executions.

```python
receipt = FailedHookReceiptFactory()
assert receipt.error is not None
assert receipt.handler_result is None
assert receipt.stack_trace is not None
```

#### `LargeContextHookReceiptFactory`
Creates receipts with large data (tests truncation logic).

```python
receipt = LargeContextHookReceiptFactory(max_size_bytes=1024)
# handler_result contains 10KB+ data, triggering truncation
```

### Receipt & Provenance Factories

#### `MerkleAnchorFactory`
Creates Merkle anchors for cryptographic provenance.

```python
anchor = MerkleAnchorFactory(graph_version=42)
assert len(anchor.root_hash) == 64  # SHA256 hex
assert anchor.graph_version == 42
```

#### `ReceiptFactory`
Creates cryptographically verifiable receipts.

```python
receipt = ReceiptFactory(actor="alice@example.com")

# Compute hash
hash_val = receipt.compute_hash()
assert len(hash_val) == 64  # SHA256

# Serialize to JSON-LD
json_ld = receipt.to_json_ld()
assert json_ld["@type"] == "HookReceipt"

# Convert to RDF triples
triples = receipt.to_rdf_triples()
assert len(triples) > 0

# Generate proof
proof = receipt.generate_proof()
assert "hash" in proof
assert "merkle_anchor" in proof
```

### Transaction Factories

#### `TransactionFactory`
Creates ACID transactions.

```python
tx = TransactionFactory(isolation_level="SERIALIZABLE")
assert tx.state == TransactionState.PENDING

# Transaction lifecycle
tx.begin()
tx.add_triple("urn:s1", "urn:p1", "urn:o1")
tx.commit()
assert tx.state == TransactionState.COMMITTED
```

#### `TransactionWithChangesFactory`
Creates transactions with pre-populated changes.

```python
tx = TransactionWithChangesFactory()
assert len(tx.added_triples) > 0
assert len(tx.removed_triples) >= 0
```

#### `CommittedTransactionFactory`
Creates already-committed transactions.

```python
tx = CommittedTransactionFactory()
assert tx.state == TransactionState.COMMITTED
assert tx.completed_at is not None
```

#### `RolledBackTransactionFactory`
Creates rolled-back transactions.

```python
tx = RolledBackTransactionFactory()
assert tx.state == TransactionState.ROLLED_BACK
assert len(tx.added_triples) == 0  # Cleared
```

## Common Patterns

### Testing Hook Execution

```python
from tests.factories import HookFactory, HookReceiptFactory

def test_hook_execution():
    # Create hook
    hook = HookFactory(name="test-hook", priority=50)

    # Simulate execution
    context = {"event": "change", "count": 42}
    result = hook.handler(context)

    # Create receipt
    receipt = HookReceiptFactory(
        hook_id=hook.name,
        input_context=context,
        handler_result=result
    )

    assert receipt.error is None
    assert receipt.duration_ms > 0
```

### Testing Transaction Lifecycle

```python
from tests.factories import TransactionFactory

def test_transaction_commit():
    tx = TransactionFactory()

    tx.begin()
    tx.add_triple("urn:s1", "urn:p1", "urn:o1")
    tx.remove_triple("urn:s2", "urn:p2", "urn:o2")

    changes = tx.get_changes()
    assert len(changes["added"]) == 1
    assert len(changes["removed"]) == 1

    tx.commit()
    assert tx.state == TransactionState.COMMITTED
```

### Testing Cryptographic Provenance

```python
from tests.factories import MerkleAnchorFactory, ReceiptFactory

def test_receipt_with_merkle_anchor():
    # Create anchor
    anchor = MerkleAnchorFactory(graph_version=999)

    # Create receipt with anchor
    receipt = ReceiptFactory(merkle_anchor=anchor)

    # Generate proof
    proof = receipt.generate_proof()
    assert proof["merkle_anchor"]["graph_version"] == 999
    assert proof["merkle_anchor"]["root_hash"] == anchor.root_hash
```

### Batch Test Data Creation

```python
from tests.factories import HookFactory, HookReceiptFactory

def test_batch_creation():
    # Create multiple hooks
    hooks = [HookFactory() for _ in range(10)]

    # Create receipts for each hook
    receipts = [
        HookReceiptFactory(hook_id=hook.name)
        for hook in hooks
    ]

    assert len(receipts) == 10
    assert all(r.error is None for r in receipts)
```

### Testing Error Scenarios

```python
from tests.factories import FailedHookReceiptFactory

def test_error_handling():
    # Create failed receipt
    receipt = FailedHookReceiptFactory()

    assert receipt.error is not None
    assert receipt.handler_result is None
    assert receipt.stack_trace is not None

    # Verify error sanitization (if implemented)
    assert "internal" not in receipt.error.lower()
```

## Design Principles

1. **Chicago School TDD**: Factories create real objects, not mocks
2. **Realistic Data**: Uses Faker for production-like test data
3. **Composable**: Factories work together (SubFactory pattern)
4. **Immutability**: Respects frozen dataclasses
5. **Type Safety**: Full type hints throughout

## Performance

Factories are optimized for test performance:

- Lazy evaluation with `LazyAttribute` and `LazyFunction`
- Minimal object graph construction
- Efficient batch creation
- No database/network dependencies

## Integration with Existing Tests

Replace manual test data construction:

```python
# ❌ BEFORE: Manual construction
hook = Hook(
    name=HookName.new("test-hook"),
    description="Test hook",
    condition=AlwaysTrueCondition(),
    handler=lambda ctx: {"status": "ok"},
    priority=50,
    timeout=30.0,
    enabled=True,
    actor="test",
    metadata={}
)

# ✅ AFTER: Factory
hook = HookFactory(name="test-hook", priority=50)
```

## Contributing

When adding new factories:

1. Add to `tests/factories/__init__.py`
2. Follow naming convention: `{Model}Factory`
3. Use `LazyAttribute` for complex defaults
4. Add docstring with examples
5. Create tests in `test_factories.py`
6. Export in `__all__`

## See Also

- [factory_boy documentation](https://factoryboy.readthedocs.io/)
- [Chicago School TDD](https://martinfowler.com/articles/mocksArentStubs.html)
- `tests/factories/test_factories.py` - Comprehensive test examples
