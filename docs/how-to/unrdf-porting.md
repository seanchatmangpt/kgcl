# UNRDF Porting Guide for KGCL Python Implementation

## Overview

This guide documents the key capabilities and patterns from the UNRDF JavaScript/Node.js implementation that should be ported to KGCL's Python Knowledge Hooks system.

**UNRDF Repository**: `/Users/sac/dev/kgcl/vendors/unrdf/`

---

## Part 1: Critical Patterns to Port

### 1. Hook Executor Architecture (`hook-executor.mjs`)

**Key Patterns:**
- Timeout management with `Promise.race(executionPromise, timeoutPromise)`
- Execution ID generation for tracking
- Error sanitization (prevents information disclosure)
- Lifecycle phases: PRE → EVALUATE → RUN → POST
- Duration tracking (`Date.now() - startTime`)
- Success/failure wrapping with metadata

**KGCL Equivalent:**
- Already implemented in `src/kgcl/hooks/lifecycle.py`
- Has execution context, timeout handling, and lifecycle phases
- Missing: execution ID generation, error sanitization

**Action Items:**
- ✅ Generate unique execution IDs for audit trails
- ✅ Add error sanitizer (from UNRDF security module)
- ✅ Add durationMs tracking to receipts

### 2. Condition Evaluator Patterns (`condition-evaluator.mjs`)

**Key Patterns:**
- Support for 7 condition types: SPARQL ASK, SPARQL SELECT, SHACL, Delta, Threshold, Count, Window
- File resolution with integrity checking (SHA256 refs)
- Environment variable injection
- Query optimization
- Deterministic execution mode

**KGCL Equivalent:**
- Implemented in `src/kgcl/hooks/conditions.py`
- Covers SPARQL, SHACL, Delta, Threshold, Window
- Missing: file resolution with SHA256 refs, deterministic mode flag

**Action Items:**
- ✅ Add `ref` support for loading conditions from files with SHA256 verification
- ✅ Add `deterministic` flag to condition evaluation
- ✅ Support environment variable injection in SPARQL/SHACL

### 3. Error Sanitizer (`security/error-sanitizer.mjs`)

**Purpose**: Prevent information disclosure in error messages

**Key Methods:**
- `sanitize(error)` - Remove sensitive stack traces, file paths, internal details
- Returns: `{ message: "generic message", code: "ERROR_CODE" }`
- Preserves error codes for debugging, hides implementation details

**KGCL Implementation:**
```python
# Port to: src/kgcl/hooks/security.py

from dataclasses import dataclass
from typing import Any

@dataclass
class SanitizedError:
    message: str
    code: str
    is_user_safe: bool = True

class ErrorSanitizer:
    """Sanitizes errors to prevent information disclosure."""

    SENSITIVE_PATTERNS = [
        r'/[a-z0-9_/-]+\.py',  # File paths
        r'File "[^"]+", line \d+',  # Stack traces
        r'in [a-z_]+',  # Function names
    ]

    def sanitize(self, error: Exception) -> SanitizedError:
        """Remove sensitive details from error."""
        msg = str(error)
        for pattern in self.SENSITIVE_PATTERNS:
            msg = re.sub(pattern, '[REDACTED]', msg)

        return SanitizedError(
            message=msg,
            code=getattr(error, 'error_code', 'INTERNAL_ERROR')
        )
```

### 4. Sandbox Restrictions (`security/sandbox-restrictions.mjs`)

**Purpose**: Define what code can and cannot do in isolated environments

**Key Restrictions:**
- No file system access beyond allowed paths
- No network calls
- No process spawning
- Memory limits
- Execution time limits

**KGCL Implementation:**
```python
# Port to: src/kgcl/hooks/sandbox.py

@dataclass
class SandboxRestrictions:
    allowed_paths: List[str] = field(default_factory=list)
    no_network: bool = True
    no_process_spawn: bool = True
    memory_limit_mb: int = 512
    timeout_ms: int = 30000
    read_only: bool = False

    def validate_path(self, path: str) -> bool:
        """Check if path is allowed."""
        return any(path.startswith(allowed) for allowed in self.allowed_paths)
```

### 5. Performance Optimizer (`performance-optimizer.mjs`)

**Key Patterns:**
- Query plan analysis
- Caching decisions
- Batch size optimization
- Memory profiling
- Latency tracking per operation

**KGCL Implementation:**
```python
# Port to: src/kgcl/hooks/performance.py

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PerformanceMetrics:
    operation: str
    latency_ms: float
    memory_delta_bytes: int
    success: bool
    p99_target_ms: float = 10

    @property
    def meets_slo(self) -> bool:
        return self.latency_ms <= self.p99_target_ms

class PerformanceOptimizer:
    """Optimize performance of hook conditions and execution."""

    def __init__(self, sample_size: int = 100):
        self.samples: Dict[str, List[float]] = {}
        self.sample_size = sample_size

    def record_latency(self, operation: str, latency_ms: float) -> None:
        """Record operation latency for trend analysis."""
        if operation not in self.samples:
            self.samples[operation] = []
        self.samples[operation].append(latency_ms)
        if len(self.samples[operation]) > self.sample_size:
            self.samples[operation].pop(0)

    def get_percentile(self, operation: str, percentile: float = 0.99) -> Optional[float]:
        """Get p99 latency for operation."""
        if operation not in self.samples or not self.samples[operation]:
            return None
        sorted_samples = sorted(self.samples[operation])
        idx = int(len(sorted_samples) * percentile) - 1
        return sorted_samples[max(0, idx)]
```

### 6. Lockchain Writer (`lockchain-writer.mjs`)

**Purpose**: Create cryptographic proofs of hook executions

**Key Methods:**
- Merkle tree construction from triples
- SHA256 hashing
- Receipt anchoring to blockchain-like chain
- Content addressing

**KGCL Equivalent:**
- Already implemented in `src/kgcl/hooks/receipts.py`
- Has MerkleTree, MerkleAnchor, receipt hashing
- Should use SHA256 consistently

**Action Items:**
- ✅ Verify SHA256 hashing is production-grade
- ✅ Add content addressability (content hash as ID)
- ✅ Add chain anchoring (link receipts to previous receipt)

### 7. Policy Pack System (`policy-pack.mjs`)

**Purpose**: Bundle, version, and activate hook collections

**Key Concepts:**
- Manifest file defines hooks, dependencies, SLOs
- Versioning for compatibility
- Hot loading without restart
- Activation/deactivation without deletion

**KGCL Implementation:**
```python
# Port to: src/kgcl/hooks/policy_pack.py

@dataclass
class PolicyPackManifest:
    name: str
    version: str
    description: str
    hooks: List[str]  # Hook IDs
    dependencies: Dict[str, str]  # name -> version
    slos: Dict[str, float]  # metric -> target value

    def validate(self) -> bool:
        """Verify manifest is valid."""
        if not self.name or not self.version:
            return False
        return all(self.version.count('.') == 2 for _ in [self.version])  # semver

class PolicyPackManager:
    """Manage policy packs and their activation."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.active_packs: Dict[str, PolicyPack] = {}

    def load_pack(self, pack_path: Path) -> PolicyPack:
        """Load and activate a policy pack."""
        manifest = self._load_manifest(pack_path / 'manifest.json')
        hooks = self._load_hooks(pack_path / 'hooks')
        return PolicyPack(manifest, hooks)
```

### 8. Query Cache (`query-cache.mjs`)

**Purpose**: Cache expensive SPARQL query results

**Key Methods:**
- Cache hit/miss tracking
- TTL-based invalidation
- LRU eviction
- Cache statistics

**KGCL Implementation:**
```python
# Port to: src/kgcl/hooks/query_cache.py

from functools import lru_cache
from datetime import datetime, timedelta

class QueryCache:
    """Cache SPARQL query results."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.hits = 0
        self.misses = 0

    def get(self, query_hash: str) -> Optional[Any]:
        """Get cached result if fresh."""
        if query_hash not in self.cache:
            self.misses += 1
            return None

        result, timestamp = self.cache[query_hash]
        if datetime.now().timestamp() - timestamp > self.ttl:
            del self.cache[query_hash]
            self.misses += 1
            return None

        self.hits += 1
        return result

    @property
    def hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
```

---

## Part 2: UNRDF File Organization to Port

### High-Priority Files (80% value)

1. **`src/knowledge-engine/hook-executor.mjs`**
   - Lifecycle management
   - Timeout handling
   - Error sanitization
   - → Port pattern to `lifecycle.py` (already done, refine error handling)

2. **`src/knowledge-engine/condition-evaluator.mjs`**
   - SPARQL evaluation patterns
   - SHACL validation integration
   - File resolution with SHA256
   - → Enhance `conditions.py` with file resolution

3. **`src/knowledge-engine/security/error-sanitizer.mjs`**
   - Error message sanitization
   - → Create `security.py` with ErrorSanitizer

4. **`src/knowledge-engine/security/sandbox-restrictions.mjs`**
   - Sandbox configuration
   - → Create `sandbox.py` with SandboxRestrictions

5. **`src/knowledge-engine/effect-sandbox.mjs`**
   - Isolated code execution
   - → Enhanced `execution_sandbox.py` (if needed)

6. **`src/knowledge-engine/performance-optimizer.mjs`**
   - Latency tracking
   - Performance metrics
   - → Add to `performance.py`

7. **`src/knowledge-engine/lockchain-writer.mjs`**
   - Cryptographic provenance
   - → Enhance `receipts.py`

8. **`src/knowledge-engine/policy-pack.mjs`**
   - Hook bundling and versioning
   - → Add to `hook_registry.py`

### Medium-Priority Files (15% value)

- `query-optimizer.mjs` → Optimize SPARQL parsing
- `query-cache.mjs` → Cache condition results
- `validate.mjs` → SHACL validation wrapper
- `transaction.mjs` → Transaction lifecycle patterns

### Low-Priority Files (5% value)

- `dark-matter/` - Advanced optimization (future)
- `federation/` - Multi-node support (future)
- `streaming/` - Real-time processing (future)

---

## Part 3: Implementation Checklist

### Phase 1: Security & Error Handling (Immediate)

- [ ] Create `src/kgcl/hooks/security.py` with ErrorSanitizer
- [ ] Create `src/kgcl/hooks/sandbox.py` with SandboxRestrictions
- [ ] Update `lifecycle.py` to use error sanitization
- [ ] Add execution IDs to HookContext
- [ ] Tests: `tests/hooks/test_security.py`

### Phase 2: Performance & Monitoring (Week 1)

- [ ] Enhance `conditions.py` with performance tracking
- [ ] Create `src/kgcl/hooks/performance.py` with PerformanceOptimizer
- [ ] Add query caching to condition evaluation
- [ ] Add latency tracking to receipts
- [ ] Tests: `tests/hooks/test_performance.py`

### Phase 3: Advanced Capabilities (Week 2)

- [ ] Enhance `hook_registry.py` with PolicyPackManager
- [ ] Add file resolution with SHA256 to condition loader
- [ ] Implement deterministic evaluation mode
- [ ] Add lockchain features to receipt storage
- [ ] Tests: `tests/hooks/test_advanced.py`

### Phase 4: Integration & Documentation (Week 3)

- [ ] Update all imports in UNRDF engine
- [ ] Complete integration tests with all new features
- [ ] Document all ported patterns
- [ ] Performance benchmarking
- [ ] Tests: `tests/integration/test_unrdf_ports.py`

---

## Part 4: Specific Code Mappings

### Hook Executor Lifecycle

**UNRDF**: `hook-executor.mjs:_executeHookLifecycle()`
```javascript
// UNRDF phases:
// 1. Pre-evaluation hook lifecycle.beforeEvaluate
// 2. Condition evaluation (SPARQL, SHACL, etc.)
// 3. Hook execution in sandbox
// 4. Post-execution lifecycle.afterExecute
// 5. Error handling + sanitization
```

**KGCL Port**: `lifecycle.py:HookExecutionPipeline`
```python
# Already has phases, need to add:
# - error_sanitizer integration
# - execution_id generation
# - deterministic mode
```

### Error Sanitization Pattern

**UNRDF**:
```javascript
const errorSanitizer = createErrorSanitizer();
const sanitizedError = errorSanitizer.sanitize(error);
// Returns: { message: "safe message", code: "ERROR_CODE" }
```

**KGCL Port**:
```python
from kgcl.hooks.security import ErrorSanitizer

sanitizer = ErrorSanitizer()
result = sanitizer.sanitize(error)
# Returns: SanitizedError(message="safe message", code="ERROR_CODE")
```

### Performance Tracking Pattern

**UNRDF**:
```javascript
const startTime = Date.now();
// ... do work ...
const durationMs = Date.now() - startTime;
```

**KGCL Port**:
```python
import time

start_time = time.perf_counter()
# ... do work ...
duration_ms = (time.perf_counter() - start_time) * 1000
```

### Condition File Resolution

**UNRDF**:
```javascript
const { ref, query } = condition;
if (ref && ref.uri && ref.sha256) {
    const loaded = await resolver.loadSparql(ref.uri, ref.sha256);
}
```

**KGCL Port**:
```python
from hashlib import sha256

if condition.get('ref'):
    ref = condition['ref']
    content = load_file(ref['uri'])
    calculated_hash = sha256(content.encode()).hexdigest()
    if calculated_hash != ref['sha256']:
        raise ValueError("Integrity check failed")
```

---

## Part 5: Performance SLOs

UNRDF targets:

| Operation | p50 | p99 | Target |
|-----------|-----|-----|--------|
| Hook registration | 0.1ms | 1.0ms | <5ms ✓ |
| Condition eval (SPARQL) | 0.2ms | 2.0ms | <10ms ✓ |
| Hook execution | 1.0ms | 10.0ms | <100ms ✓ |
| Receipt write | 5.0ms | 5.0ms | <10ms ✓ |
| Full pipeline | 2.0ms | 50.0ms | <500ms ✓ |

**KGCL Targets**: Match or exceed UNRDF SLOs

---

## Part 6: Testing Strategy

### Unit Tests from UNRDF

Check `/Users/sac/dev/kgcl/vendors/unrdf/test/knowledge-engine/`:
- Hook executor tests
- Condition evaluator tests
- Security tests
- Performance tests

### Port Test Patterns

```python
# Port from UNRDF test patterns
def test_hook_execution_with_timeout():
    """Execution should timeout at limit."""
    hook = {..., "timeout": 100}  # 100ms
    # execution should fail after 100ms

def test_error_sanitization():
    """Sensitive info should be removed."""
    error = Exception("Failed at /path/to/file.py line 42")
    sanitized = sanitizer.sanitize(error)
    assert "/path" not in sanitized.message
    assert "line 42" not in sanitized.message

def test_condition_with_sha256_verification():
    """File integrity should be verified."""
    condition = {
        "kind": "sparql-ask",
        "ref": {
            "uri": "file:///path/to/query.sparql",
            "sha256": "abc123..."
        }
    }
    # Should verify sha256 matches file contents
```

---

## Summary: What to Port

| Component | Priority | Effort | Value |
|-----------|----------|--------|-------|
| Error Sanitizer | HIGH | 1h | P1 - Security |
| Sandbox Restrictions | HIGH | 2h | P1 - Safety |
| Performance Optimizer | HIGH | 3h | P1 - Observability |
| Policy Pack Manager | MEDIUM | 4h | P2 - Manageability |
| Query Cache | MEDIUM | 2h | P2 - Perf |
| File Resolution (SHA256) | MEDIUM | 2h | P2 - Integrity |
| Lockchain Advanced | LOW | 8h | P3 - Future |
| Dark Matter Optimization | LOW | 16h | P3 - Future |

**Total Estimated Work**: ~38 hours for P1+P2 items

---

## Next Steps

1. **This Week**: Implement security module (error sanitizer, sandbox)
2. **Next Week**: Add performance tracking and query caching
3. **Week 3**: Integrate policy packs and advanced features
4. **Week 4**: Full integration testing and documentation

