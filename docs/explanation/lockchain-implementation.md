# Lockchain Anchor Implementation

## Overview

The Lockchain Anchor provides an immutable, git-backed audit trail for KGC Hybrid Engine tick receipts. Each tick execution is cryptographically hashed and stored in a verifiable chain.

## Components

### 1. TickReceipt (Frozen Dataclass)

Immutable record of a single tick execution:

```python
@dataclass(frozen=True)
class TickReceipt:
    tick_number: int
    state_hash_before: str  # SHA-256 of graph state
    state_hash_after: str
    rules_fired: tuple[str, ...]  # Rule URIs that fired
    triples_added: int
    triples_removed: int
    timestamp: datetime
    converged: bool
```

**Features:**
- Frozen dataclass ensures immutability
- Rules fired stored as tuple (immutable sequence)
- YAML serialization/deserialization
- ISO 8601 timestamp format

### 2. LockchainWriter

Git-backed receipt chain writer:

```python
writer = LockchainWriter(repo_path, branch="lockchain")
```

**Methods:**
- `compute_state_hash(store)` - SHA-256 hash of canonical N-Quads dump
- `write_receipt(receipt)` - Write receipt to git, return commit SHA
- `get_receipt_chain(limit=100)` - Read receipt history
- `verify_chain()` - Verify hash chain integrity

**Storage:**
- Receipts stored in `.kgc/lockchain/tick_NNNNNN.yaml`
- Each receipt committed to git with hash in commit message
- Commit message includes state hashes and receipt hash for tamper detection

### 3. LockchainHook

TickHook implementation for automatic receipt writing:

```python
hook = LockchainHook(writer, store)
controller.register_hook(hook)
```

**Behavior:**
- `on_pre_tick`: Captures state hash before tick execution
- `on_rule_fired`: Records rule URIs that fire
- `on_post_tick`: Writes complete receipt to lockchain

### 4. RDFStore Protocol

Protocol-based interface for RDF stores:

```python
class RDFStore(Protocol):
    def dump(self) -> str: ...
```

**Benefits:**
- No dependency on buggy OxigraphStore import
- Works with any store implementing `dump()` method
- Type-safe with mypy strict mode

## Receipt File Format

```yaml
tick: 1
timestamp: '2025-01-15T10:30:00+00:00'
state:
  before: sha256:abc123...
  after: sha256:def456...
mutations:
  rules_fired:
  - kgc:WCP1_Sequence
  - kgc:WCP2_ParallelSplit
  triples_added: 5
  triples_removed: 2
converged: false
```

## Chain Verification

The lockchain ensures integrity through:

1. **Hash Chain**: Each receipt's `state_hash_before` must match previous receipt's `state_hash_after`
2. **Git Commits**: Receipt hash included in commit message for tamper detection
3. **Immutability**: Frozen dataclasses prevent modification
4. **Canonical Hashing**: Sorted N-Quads ensure deterministic hashes

## Example Usage

```python
from pathlib import Path
from kgcl.hybrid.lockchain import LockchainWriter, LockchainHook
from kgcl.hybrid.tick_controller import TickController

# Initialize writer
writer = LockchainWriter(Path.cwd())

# Create hook
hook = LockchainHook(writer, store)

# Register with controller
controller = TickController(engine)
controller.register_hook(hook)

# Execute ticks (receipts written automatically)
while not result.converged:
    result = controller.execute_tick()

# Verify chain integrity
assert writer.verify_chain()

# Read receipt history
receipts = writer.get_receipt_chain()
for receipt in receipts:
    print(f"Tick {receipt.tick_number}: {receipt.state_hash_after}")
```

See `examples/lockchain_demo.py` for full demonstration.

## Testing

Comprehensive test suite with 22 tests:

```bash
uv run pytest tests/hybrid/test_lockchain.py -v
```

**Test Coverage:**
- TickReceipt immutability and serialization
- LockchainWriter git operations and hashing
- Chain verification and tampering detection
- LockchainHook integration with TickController
- Full end-to-end integration test

## Quality Gates

All quality gates pass:

```bash
uv run poe format      # Ruff format: PASSED
uv run poe lint        # Ruff lint: PASSED
uv run poe type-check  # Mypy strict: PASSED (100% type coverage)
uv run poe test        # Pytest: 22/22 PASSED
```

## Implementation Notes

### Design Decisions

1. **Protocol over Concrete Type**: Used `RDFStore` protocol instead of importing `OxigraphStore` to avoid broken import (QueryResults → QuerySolutions bug)

2. **Frozen Dataclasses**: All data classes are frozen for immutability - critical for audit trail integrity

3. **Tuple for Rules**: Rules fired stored as tuple (not list) to enforce immutability

4. **Git Subprocess**: Used subprocess instead of GitPython to minimize dependencies

5. **Canonical Hashing**: Sorted N-Quads before hashing ensures deterministic state hashes

### Performance Considerations

- Hash computation: O(n log n) due to sorting
- Receipt storage: O(1) file write + git commit
- Chain verification: O(n) where n = number of receipts
- Git operations: Subprocess overhead ~10-50ms per commit

### Security Properties

- **Tamper-evident**: Hash chain detects modification of receipts
- **Non-repudiation**: Git commits provide timestamp and hash verification
- **Immutability**: Frozen dataclasses prevent in-memory modification
- **Cryptographic strength**: SHA-256 provides 2^256 security

## Future Enhancements

Potential improvements (not implemented):

1. **Git signing**: GPG signatures on commits for non-repudiation
2. **Merkle tree**: More efficient verification for large chains
3. **Compression**: YAML compression for large receipt files
4. **Remote sync**: Push receipts to remote git repositories
5. **Pruning**: Archive old receipts beyond retention period
6. **Parallel writes**: Async git operations for high-frequency ticks
