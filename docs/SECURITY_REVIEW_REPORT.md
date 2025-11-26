# KGC YAWL Engine - Comprehensive Security Review Report

**Review Date**: 2025-11-25
**Reviewer**: Security Specialist (Claude Code)
**Scope**: Workflow orchestration, knowledge graph mutation engine (Atman), UNRDF engine, hooks system
**Severity Levels**: CRITICAL | HIGH | MEDIUM | LOW

---

## Executive Summary

This security review examined the KGC (Knowledge Graph Construction) workflow engine, Atman knowledge graph mutation engine, and UNRDF RDF triple store for production readiness. The system implements workflow orchestration with 5 steps (Discover, Align, Regenerate, Review, Remove) and provides RDF graph manipulation with SPARQL querying, transactions, and provenance tracking.

**Overall Security Posture**: **MODERATE** with several HIGH-severity findings requiring remediation before production deployment.

**Key Findings**:
- ✅ Strong transaction integrity with rollback support
- ✅ Comprehensive error sanitization system in place
- ✅ Good sandbox restrictions framework
- ⚠️ SPARQL injection vulnerabilities in trigger conditions (HIGH)
- ⚠️ Path traversal risks in workflow state persistence (MEDIUM)
- ⚠️ Missing authorization model for workflow execution (HIGH)
- ⚠️ Incomplete timeout enforcement in hook execution (MEDIUM)

---

## 1. INPUT VALIDATION

### 1.1 SPARQL/SQL Injection Vulnerabilities

#### Finding SEC-001: SPARQL Injection in Hook Trigger Conditions
**Severity**: **HIGH**
**File**: `/src/kgcl/unrdf_engine/hooks.py:141-169`
**CWE**: CWE-943 (Improper Neutralization of Special Elements in Data Query Logic)

**Description**:
The `TriggerCondition.matches()` method directly embeds user-supplied `pattern` into SPARQL queries without sanitization:

```python
def matches(self, context: HookContext) -> bool:
    target_graph = context.delta if self.check_delta else context.graph

    # VULNERABILITY: Direct string interpolation into SPARQL
    query = f"""
    SELECT (COUNT(*) as ?count) WHERE {{
        {self.pattern}  # ← User-controlled input!
    }}
    """

    results = list(target_graph.query(query))
```

**Attack Scenario**:
An attacker could craft a malicious hook with a trigger pattern:
```python
trigger = TriggerCondition(
    pattern="""
    ?s ?p ?o .
    } UNION {
        # Exfiltrate all data
        SELECT * WHERE { ?s ?p ?o }
    } {
    """
)
```

This would bypass the `COUNT(*)` aggregation and allow arbitrary SPARQL execution.

**Impact**:
- Information disclosure: Attacker can query ALL triples in the graph
- Denial of Service: Complex queries can exhaust resources
- Data exfiltration: Sensitive provenance or system data could be leaked

**Recommendation**:
1. **CRITICAL**: Use parameterized queries or SPARQL query builders:
   ```python
   from rdflib.plugins.sparql import prepareQuery

   def matches(self, context: HookContext) -> bool:
       # Whitelist allowed SPARQL patterns
       if not self._validate_pattern_syntax(self.pattern):
           raise ValueError("Invalid SPARQL pattern")

       # Use prepared query with validated pattern
       query_template = """
       SELECT (COUNT(*) as ?count) WHERE {
           %s
       }
       """
       prepared = prepareQuery(query_template % self.pattern)
       results = list(target_graph.query(prepared))
   ```

2. Implement pattern validation:
   ```python
   def _validate_pattern_syntax(self, pattern: str) -> bool:
       """Validate SPARQL pattern is safe."""
       # Deny patterns with nested queries, UNION, FILTER, etc.
       forbidden = ["UNION", "FILTER", "OPTIONAL", "SELECT", "CONSTRUCT"]
       pattern_upper = pattern.upper()
       return not any(keyword in pattern_upper for keyword in forbidden)
   ```

3. Add rate limiting for trigger evaluations to prevent DoS

**Status**: ❌ **UNRESOLVED** - Requires code changes

---

#### Finding SEC-002: Unvalidated SPARQL Query Limit Injection
**Severity**: **MEDIUM**
**File**: `/src/kgcl/cli/query.py:168-169`, `/src/kgcl/cli/services_impl.py:87`

**Description**:
The query limit parameter is concatenated into SPARQL without validation:

```python
# cli/query.py
if limit and "LIMIT" not in sparql_query.upper():
    sparql_query += f"\nLIMIT {limit}"  # ← No type/range validation

# cli/services_impl.py
sparql = (
    query_text
    if not limit or "LIMIT" in query_text.upper()
    else f"{query_text}\nLIMIT {limit}"  # ← Same issue
)
```

**Attack Scenario**:
While `limit` is typed as `int` in Click, this doesn't prevent:
- Negative limits: `--limit -1`
- Extremely large limits: `--limit 999999999` (DoS)
- Code execution if type validation fails

**Recommendation**:
```python
def _validate_limit(limit: int) -> int:
    """Validate SPARQL LIMIT parameter."""
    if limit < 1:
        raise ValueError("LIMIT must be positive")
    if limit > MAX_QUERY_LIMIT:  # e.g., 10000
        raise ValueError(f"LIMIT exceeds maximum {MAX_QUERY_LIMIT}")
    return limit

# Apply validation before use
if limit:
    limit = _validate_limit(limit)
    sparql_query += f"\nLIMIT {limit}"
```

**Status**: ❌ **UNRESOLVED** - Requires validation

---

### 1.2 Path Traversal Vulnerabilities

#### Finding SEC-003: Insufficient Path Validation in Workflow State Persistence
**Severity**: **MEDIUM**
**File**: `/src/kgcl/workflow/orchestrator.py:387-389`, `/src/kgcl/workflow/state.py:247-251`

**Description**:
Workflow state files are saved using user-controlled `workflow_id` without path sanitization:

```python
def _save_state(self, state: WorkflowState) -> None:
    """Persist workflow state to disk."""
    state_file = self.state_dir / f"{state.workflow_id}.json"  # ← No validation
    state.save(state_file)

# state.py
def save(self, path: Path) -> None:
    """Persist state to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)  # ← Creates arbitrary dirs
    with path.open("w") as f:
        json.dump(self.to_dict(), f, indent=2)
```

**Attack Scenario**:
An attacker could provide a malicious `workflow_id`:
```python
workflow_id = "../../../etc/passwd"
# Results in: state_dir / "../../../etc/passwd.json"
# Could overwrite system files!
```

Or:
```python
workflow_id = "../../.ssh/authorized_keys"
# Could write SSH keys to arbitrary locations
```

**Impact**:
- **File overwrite**: System files could be overwritten
- **Directory traversal**: Files written outside intended directory
- **Information disclosure**: State files in predictable locations

**Recommendation**:
```python
import re
from pathlib import Path

def _sanitize_workflow_id(workflow_id: str) -> str:
    """Sanitize workflow ID to prevent path traversal."""
    # Remove path separators
    sanitized = workflow_id.replace("/", "_").replace("\\", "_")

    # Remove parent directory references
    sanitized = sanitized.replace("..", "_")

    # Allow only alphanumeric, hyphens, underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', sanitized):
        raise ValueError(f"Invalid workflow_id: {workflow_id}")

    # Limit length
    if len(sanitized) > 255:
        raise ValueError("workflow_id too long")

    return sanitized

def _save_state(self, state: WorkflowState) -> None:
    """Persist workflow state to disk."""
    safe_id = _sanitize_workflow_id(state.workflow_id)
    state_file = self.state_dir / f"{safe_id}.json"

    # Verify final path is within state_dir
    if not state_file.resolve().is_relative_to(self.state_dir.resolve()):
        raise ValueError("Invalid state file path")

    state.save(state_file)
```

**Status**: ❌ **UNRESOLVED** - Requires sanitization

---

#### Finding SEC-004: Path Validation in Sandbox Restrictions
**Severity**: **LOW**
**File**: `/src/kgcl/hooks/sandbox.py:50-80`

**Description**:
The `SandboxRestrictions.validate_path()` method has good path normalization but minor issues:

```python
def validate_path(self, path: str) -> bool:
    try:
        # Good: Uses resolve() to handle symlinks
        normalized = str(Path(path).resolve())

        for allowed in self.allowed_paths:
            allowed_normalized = str(Path(allowed).resolve())
            if normalized.startswith(allowed_normalized):  # ← TOCTOU issue
                return True
    except Exception:
        return False  # Good: Deny on error
```

**Issues**:
1. **TOCTOU (Time-of-Check-Time-of-Use)**: Path could change between validation and use
2. **Symlink race**: Attacker could swap symlink target after validation
3. **Case sensitivity**: On Windows/macOS, paths are case-insensitive

**Recommendation**:
```python
def validate_path(self, path: str) -> bool:
    """Validate path with TOCTOU protection."""
    if not self.allowed_paths:
        return False

    try:
        normalized = Path(path).resolve(strict=True)  # strict=True raises if doesn't exist

        for allowed in self.allowed_paths:
            allowed_normalized = Path(allowed).resolve(strict=True)

            # Use is_relative_to() instead of startswith (Python 3.9+)
            try:
                normalized.relative_to(allowed_normalized)
                return True
            except ValueError:
                continue
    except (OSError, ValueError):
        return False

    return False
```

**Status**: ✅ **MINOR** - Enhancement recommended but not critical

---

### 1.3 URIRef Validation

#### Finding SEC-005: Malformed URI Handling
**Severity**: **LOW**
**File**: `/src/kgcl/engine/atman.py:445-466`

**Description**:
The `_convert_triple()` method uses heuristic URI detection:

```python
def _convert_triple(self, t: Triple) -> tuple[URIRef | Literal, URIRef, URIRef | Literal]:
    s, p, o = t
    # Heuristic: If it looks like a URI, it is. Else Literal.
    s_term: URIRef | Literal = URIRef(s) if "://" in s or ":" in s else Literal(s)
    p_term = URIRef(p)
    o_term: URIRef | Literal = URIRef(o) if "://" in o or ":" in o else Literal(o)
    return (s_term, p_term, o_term)
```

**Issues**:
1. **Permissive URI detection**: `":"` is too broad (matches `"C:\path"`, `"time:12:30"`)
2. **No URI validation**: Malformed URIs like `http://[::1]://broken` accepted
3. **Colon prefix mismatch**: Could incorrectly treat email addresses as URIs

**Attack Scenario**:
```python
delta = QuadDelta(additions=[
    ("javascript:alert(1)", "urn:p", "data:text/html,<script>alert(1)</script>")
])
```

This creates URIs with executable content that could be exploited if rendered.

**Recommendation**:
```python
import re
from urllib.parse import urlparse

URI_PATTERN = re.compile(r'^[a-z][a-z0-9+.-]*:', re.IGNORECASE)

def _is_valid_uri(value: str) -> bool:
    """Validate URI format."""
    if not URI_PATTERN.match(value):
        return False

    try:
        parsed = urlparse(value)
        # Require scheme and netloc for absolute URIs
        if "://" in value:
            return bool(parsed.scheme and parsed.netloc)
        # Allow prefix-style URIs like "rdf:type"
        return bool(parsed.scheme)
    except Exception:
        return False

def _convert_triple(self, t: Triple) -> tuple:
    s, p, o = t

    # Predicate MUST be a URI
    if not _is_valid_uri(p):
        raise ValueError(f"Invalid predicate URI: {p}")

    s_term = URIRef(s) if _is_valid_uri(s) else Literal(s)
    p_term = URIRef(p)
    o_term = URIRef(o) if _is_valid_uri(o) else Literal(o)

    return (s_term, p_term, o_term)
```

**Status**: ✅ **MINOR** - Low risk in current usage

---

## 2. AUTHORIZATION MODEL

### Finding SEC-006: Missing Access Control for Workflow Execution
**Severity**: **HIGH**
**File**: `/src/kgcl/workflow/orchestrator.py`, `/src/kgcl/workflow/scheduler.py`

**Description**:
The `StandardWorkLoop` and `WorkflowScheduler` have **NO authorization checks**:

```python
def execute(self, workflow_id: str | None = None) -> WorkflowState:
    """Execute complete 5-step workflow."""
    # NO actor validation
    # NO permission checks
    # NO role verification
    workflow_id = workflow_id or str(uuid.uuid4())
    state = WorkflowState(workflow_id=workflow_id, ...)
```

**Attack Scenarios**:
1. **Unauthorized execution**: Any code can execute workflows
2. **Workflow hijacking**: Attacker could resume/modify others' workflows
3. **Resource exhaustion**: Spawn unlimited workflows
4. **Data exfiltration**: Execute workflows that leak sensitive data

**Impact**:
- **CRITICAL** for production deployment
- No audit trail of WHO executed workflows
- Cannot enforce principle of least privilege

**Recommendation**:

```python
from dataclasses import dataclass
from enum import Enum

class WorkflowRole(Enum):
    """Workflow execution roles."""
    ADMIN = "admin"          # Can execute any workflow
    OPERATOR = "operator"    # Can execute/resume workflows
    VIEWER = "viewer"        # Can only view workflow state
    SCHEDULER = "scheduler"  # Automated scheduler role

@dataclass
class WorkflowActor:
    """Actor performing workflow operations."""
    identity: str  # User ID, service account, etc.
    roles: list[WorkflowRole]
    attributes: dict[str, str] = field(default_factory=dict)

    def has_role(self, role: WorkflowRole) -> bool:
        return role in self.roles

    def can_execute(self) -> bool:
        return self.has_role(WorkflowRole.ADMIN) or self.has_role(WorkflowRole.OPERATOR)

    def can_view(self) -> bool:
        return any(self.has_role(r) for r in WorkflowRole)

class WorkflowAuthz:
    """Authorization policy for workflows."""

    def __init__(self):
        self._policies: dict[str, callable] = {}

    def check_execute(self, actor: WorkflowActor, workflow_id: str) -> bool:
        """Check if actor can execute workflow."""
        if not actor.can_execute():
            raise PermissionError(f"Actor {actor.identity} cannot execute workflows")

        # Check workflow-specific policy if registered
        if workflow_id in self._policies:
            if not self._policies[workflow_id](actor):
                raise PermissionError(f"Actor {actor.identity} denied for workflow {workflow_id}")

        return True

    def register_policy(self, workflow_id: str, policy: callable):
        """Register custom authorization policy for workflow."""
        self._policies[workflow_id] = policy

# Integrate into StandardWorkLoop
class StandardWorkLoop:
    def __init__(self, ..., authz: WorkflowAuthz | None = None):
        ...
        self.authz = authz or WorkflowAuthz()

    def execute(self, workflow_id: str | None = None, actor: WorkflowActor | None = None) -> WorkflowState:
        """Execute workflow with authorization check."""
        if not actor:
            raise ValueError("Actor required for workflow execution")

        workflow_id = workflow_id or str(uuid.uuid4())

        # AUTHORIZATION CHECK
        self.authz.check_execute(actor, workflow_id)

        state = WorkflowState(
            workflow_id=workflow_id,
            actor=actor.identity,  # Track who executed
            ...
        )
        ...
```

**Additional Requirements**:
1. Add `actor` field to `WorkflowState` for audit trail
2. Implement role-based access control (RBAC)
3. Add workflow ownership model
4. Log all authorization decisions
5. Implement resource gates (max workflows per actor)

**Status**: ❌ **CRITICAL** - Production blocker

---

### Finding SEC-007: Missing Resource Limits on Hook Registration
**Severity**: **MEDIUM**
**File**: `/src/kgcl/unrdf_engine/hooks.py:273-297`

**Description**:
No limits on number of hooks that can be registered:

```python
def register(self, hook: KnowledgeHook) -> None:
    """Register a hook."""
    if hook.name in self._hooks:
        raise ValueError(f"Hook {hook.name} already registered")

    self._hooks[hook.name] = hook
    # No limit check! Can register unlimited hooks
```

**Attack Scenario**:
```python
# DoS: Register millions of hooks
for i in range(1000000):
    registry.register(KnowledgeHook(f"hook_{i}", [HookPhase.PRE_QUERY], ...))
```

**Recommendation**:
```python
MAX_HOOKS_PER_PHASE = 100
MAX_TOTAL_HOOKS = 500

def register(self, hook: KnowledgeHook) -> None:
    """Register a hook with limits."""
    # Check total limit
    if len(self._hooks) >= MAX_TOTAL_HOOKS:
        raise ValueError(f"Maximum hooks limit ({MAX_TOTAL_HOOKS}) reached")

    # Check per-phase limit
    for phase in hook.phases:
        if len(self._hooks_by_phase[phase]) >= MAX_HOOKS_PER_PHASE:
            raise ValueError(f"Maximum hooks for phase {phase} ({MAX_HOOKS_PER_PHASE}) reached")

    # Existing registration logic...
```

**Status**: ❌ **UNRESOLVED** - Needs resource limits

---

## 3. DATA PROTECTION

### Finding SEC-008: Provenance Data Exposure
**Severity**: **MEDIUM**
**File**: `/src/kgcl/unrdf_engine/engine.py:438-459`

**Description**:
Provenance records store potentially sensitive metadata without access control:

```python
@dataclass
class ProvenanceRecord:
    agent: str  # Who added the triple
    timestamp: datetime
    reason: str | None = None  # Why it was added (could contain sensitive info)
    source: str | None = None  # Source system/file (could expose internal paths)
    activity: str | None = None  # Activity (could leak business logic)
```

**Issues**:
1. No redaction of sensitive data in `reason` or `source`
2. Provenance accessible via `get_all_provenance()` without authorization
3. Could leak internal system paths, user IDs, business processes

**Recommendation**:
```python
def get_provenance(self, subject: URIRef, predicate: URIRef, obj: URIRef | Literal,
                   actor: WorkflowActor | None = None) -> ProvenanceRecord | None:
    """Get provenance with access control."""
    record = self._provenance.get((subject, predicate, obj))

    if not record:
        return None

    # Check authorization
    if actor and not actor.has_role(WorkflowRole.ADMIN):
        # Redact sensitive fields for non-admin users
        return ProvenanceRecord(
            agent="[REDACTED]",
            timestamp=record.timestamp,
            reason=None,
            source=None,
            activity=None
        )

    return record
```

**Status**: ✅ **ACCEPTABLE** - Low risk, but should add authorization

---

### Finding SEC-009: Error Sanitization Coverage
**Severity**: **LOW**
**File**: `/src/kgcl/hooks/security.py:37-98`

**Description**:
The `ErrorSanitizer` is well-implemented but has gaps:

**Strengths**:
✅ Removes file paths, stack traces, function names
✅ Returns sanitized error codes
✅ Marks errors as user-safe

**Gaps**:
1. Not automatically applied to all error paths
2. Some regex patterns may miss edge cases:
   ```python
   r"/[a-z0-9_\-./]+"  # Misses uppercase paths like /Users/Alice
   ```
3. No sanitization of environment variables in errors

**Recommendation**:
```python
# Improve regex patterns
SENSITIVE_PATTERNS = [
    r'File "[^"]+", line \d+',
    r"[A-Z]:[\\\/][\w\-\\\/. ]+",  # Windows: C:\Users\Alice\file.txt
    r"/[\w\-./]+",  # Unix: /home/alice/file.py
    r"\b[A-Z_]+=[^\s]+",  # Environment variables: API_KEY=secret
    r"at line \d+",
    r"in [a-z_][a-z0-9_]*",
]

# Auto-apply to all exceptions
class SecureException(Exception):
    """Exception with automatic sanitization."""
    def __str__(self) -> str:
        return ErrorSanitizer().sanitize(super().__str__()).message
```

**Status**: ✅ **GOOD** - Minor improvements recommended

---

### Finding SEC-010: No Secret Detection in Graph Data
**Severity**: **MEDIUM**
**File**: `/src/kgcl/unrdf_engine/engine.py`, `/src/kgcl/engine/atman.py`

**Description**:
Neither engine validates that RDF data doesn't contain secrets:

```python
def add_triple(self, subject: URIRef, predicate: URIRef, obj: URIRef | Literal, transaction: Transaction):
    # No check if 'obj' contains:
    # - API keys (sk-...)
    # - Passwords
    # - Private keys (-----BEGIN RSA PRIVATE KEY-----)
    # - AWS credentials
```

**Attack Scenario**:
```python
# Accidentally commit secrets to knowledge graph
engine.add_triple(
    URIRef("urn:config"),
    URIRef("urn:apiKey"),
    Literal("sk-1234567890abcdef"),  # ← LEAKED!
    txn
)
```

**Recommendation**:
```python
import re

SECRET_PATTERNS = {
    "api_key": r"(sk|pk|api)[_-]?[a-zA-Z0-9]{20,}",
    "private_key": r"-----BEGIN (RSA )?PRIVATE KEY-----",
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "password": r"password\s*[:=]\s*['\"]?[a-zA-Z0-9!@#$%^&*]{8,}",
}

class SecretDetector:
    """Detect secrets in RDF literals."""

    def scan_literal(self, value: str) -> list[str]:
        """Scan literal for potential secrets."""
        findings = []
        for secret_type, pattern in SECRET_PATTERNS.items():
            if re.search(pattern, value, re.IGNORECASE):
                findings.append(secret_type)
        return findings

    def validate_triple(self, triple: tuple) -> None:
        """Validate triple doesn't contain secrets."""
        s, p, o = triple

        # Check object literal
        if isinstance(o, Literal):
            findings = self.scan_literal(str(o))
            if findings:
                raise ValueError(f"Potential secrets detected: {findings}")

# Integrate into add_triple()
detector = SecretDetector()
detector.validate_triple((subject, predicate, obj))
```

**Status**: ❌ **UNRESOLVED** - Should add secret scanning

---

## 4. ERROR HANDLING

### Finding SEC-011: Information Disclosure in Hook Execution Errors
**Severity**: **LOW**
**File**: `/src/kgcl/engine/atman.py:545-548`

**Description**:
Hook execution errors log raw exception messages:

```python
except Exception as e:
    logger.exception("TX Failed: %s", ctx.tx_id)  # ← Logs full exception
    error_msg = str(e)  # ← Raw error in receipt
```

**Impact**:
- Stack traces in logs could expose internal paths
- Error messages in receipts could leak implementation details

**Recommendation**:
```python
from kgcl.hooks.security import ErrorSanitizer

sanitizer = ErrorSanitizer()

except Exception as e:
    # Sanitize before logging
    sanitized = sanitizer.sanitize(e)
    logger.error("TX Failed: %s - %s", ctx.tx_id, sanitized.code)
    error_msg = sanitized.message  # User-safe message
```

**Status**: ✅ **MINOR** - Easy fix, low impact

---

### Finding SEC-012: Transaction Rollback Integrity
**Severity**: **LOW**
**File**: `/src/kgcl/unrdf_engine/engine.py:346-364`

**Description**:
Transaction rollback correctly prevents modification but doesn't validate final state:

```python
def rollback(self, transaction: Transaction) -> None:
    """Rollback a transaction, discarding all changes."""
    if not transaction.can_modify():
        raise ValueError(f"Transaction {transaction.transaction_id} already finalized")

    transaction.rolled_back = True
    # Good: Sets flag, doesn't modify graph
```

**Observations**:
✅ Graph remains unchanged on rollback
✅ Transaction state prevents double-rollback
✅ Span tracking for observability

**Enhancement**:
```python
def rollback(self, transaction: Transaction) -> None:
    """Rollback with integrity verification."""
    if not transaction.can_modify():
        raise ValueError(...)

    # Verify graph hasn't been modified yet (defensive check)
    for triple in transaction.added_triples:
        if triple in self.graph:
            logger.warning(f"Triple already in graph during rollback: {triple}")

    transaction.rolled_back = True
```

**Status**: ✅ **GOOD** - Rollback integrity is sound

---

## 5. TIMEOUT & RESOURCE LIMITS

### Finding SEC-013: Missing Timeout Enforcement in Hook Execution
**Severity**: **MEDIUM**
**File**: `/src/kgcl/unrdf_engine/hooks.py`, `/src/kgcl/engine/atman.py`

**Description**:
`SandboxRestrictions` defines `timeout_ms = 30000` but it's **not enforced**:

```python
@dataclass
class SandboxRestrictions:
    timeout_ms: int = 30000  # ← Defined but never used!
```

Hook execution has no timeout:
```python
async def execute(self, store: Dataset, delta: QuadDelta, ctx: TransactionContext) -> bool:
    return await self._handler(store, delta, ctx)  # ← No timeout wrapper!
```

**Attack Scenario**:
```python
async def malicious_hook(store, delta, ctx):
    # Infinite loop - hangs entire transaction
    while True:
        await asyncio.sleep(0.1)
```

**Recommendation**:
```python
import asyncio

async def execute(self, store: Dataset, delta: QuadDelta, ctx: TransactionContext,
                  timeout_ms: int = 30000) -> bool:
    """Execute hook with timeout."""
    try:
        return await asyncio.wait_for(
            self._handler(store, delta, ctx),
            timeout=timeout_ms / 1000.0
        )
    except asyncio.TimeoutError:
        logger.error(f"Hook {self.id} timed out after {timeout_ms}ms")
        return False  # Timeout = failure for PRE hooks
```

**Apply to Atman engine**:
```python
# atman.py
for hook in pre_hooks:
    h_start = time.perf_counter_ns()

    # Add timeout wrapper
    try:
        success = await asyncio.wait_for(
            hook.execute(self.store, delta, ctx),
            timeout=30.0  # 30 seconds max
        )
    except asyncio.TimeoutError:
        logger.error(f"Hook {hook.id} timed out")
        success = False
```

**Status**: ❌ **UNRESOLVED** - Critical for production

---

### Finding SEC-014: Unbounded Memory Usage in Graph Operations
**Severity**: **MEDIUM**
**File**: `/src/kgcl/unrdf_engine/engine.py`, `/src/kgcl/engine/atman.py`

**Description**:
No limits on:
1. Number of triples in a transaction
2. Size of provenance metadata
3. Number of concurrent transactions
4. Graph size

```python
def add_triple(self, subject, predicate, obj, transaction):
    # No check on transaction size!
    triple = (subject, predicate, obj)
    transaction.added_triples.append(triple)  # ← Unbounded list
```

Atman has `CHATMAN_CONSTANT = 64` limit per batch, but transactions can be unlimited.

**Recommendation**:
```python
MAX_TRANSACTION_TRIPLES = 10000
MAX_GRAPH_TRIPLES = 10_000_000
MAX_CONCURRENT_TRANSACTIONS = 100

def add_triple(self, subject, predicate, obj, transaction):
    # Enforce transaction size limit
    if len(transaction.added_triples) >= MAX_TRANSACTION_TRIPLES:
        raise ValueError(f"Transaction exceeds maximum {MAX_TRANSACTION_TRIPLES} triples")

    # Enforce graph size limit
    if len(self.graph) >= MAX_GRAPH_TRIPLES:
        raise ValueError(f"Graph exceeds maximum {MAX_GRAPH_TRIPLES} triples")

    transaction.added_triples.append((subject, predicate, obj))
```

**Status**: ❌ **UNRESOLVED** - Needs resource limits

---

### Finding SEC-015: Atman Chatman Constant Validation
**Severity**: **LOW**
**File**: `/src/kgcl/engine/atman.py:108-137`

**Description**:
The Chatman Constant (64 triples/batch) is well-enforced:

```python
@field_validator("additions", "removals")
@classmethod
def enforce_chatman_constant(cls, v: list[Triple]) -> list[Triple]:
    if len(v) > CHATMAN_CONSTANT:
        raise ValueError(f"Topology Violation: Batch size {len(v)} exceeds Hot Path limit ({CHATMAN_CONSTANT}).")
    return v
```

**Observations**:
✅ Enforced at `QuadDelta` creation (immutable)
✅ Clear error message
✅ Prevents batch size DoS

**Status**: ✅ **EXCELLENT** - No changes needed

---

## 6. EXTERNAL SERVICE INTERACTION

### Finding SEC-016: Unvalidated Webhook URLs
**Severity**: **HIGH**
**File**: Not currently implemented, but webhook support is implied by architecture

**Description**:
If webhooks are added for workflow events or hook notifications, URL validation is critical.

**Preventive Recommendation**:
```python
import ipaddress
from urllib.parse import urlparse

BLOCKED_SCHEMES = {"file", "ftp", "gopher", "data"}
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),     # Localhost
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("10.0.0.0/8"),      # Private
    ipaddress.ip_network("172.16.0.0/12"),   # Private
    ipaddress.ip_network("192.168.0.0/16"),  # Private
]

def validate_webhook_url(url: str) -> bool:
    """Validate webhook URL to prevent SSRF."""
    parsed = urlparse(url)

    # Block non-HTTP schemes
    if parsed.scheme.lower() in BLOCKED_SCHEMES:
        raise ValueError(f"Blocked scheme: {parsed.scheme}")

    # Require HTTPS in production
    if os.getenv("ENV") == "production" and parsed.scheme != "https":
        raise ValueError("HTTPS required in production")

    # Block private/internal IPs
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        for network in BLOCKED_NETWORKS:
            if ip in network:
                raise ValueError(f"Private IP address not allowed: {ip}")
    except ValueError:
        # Hostname is not an IP, allow (will be resolved)
        pass

    return True
```

**Status**: ✅ **PREVENTIVE** - No current vulnerability, implement when adding webhooks

---

## 7. CRYPTOGRAPHIC OPERATIONS

### Finding SEC-017: Hash Algorithm Selection
**Severity**: **LOW**
**File**: `/src/kgcl/engine/atman.py:48, 441-443, 552-553`

**Description**:
SHA256 is used correctly throughout:

```python
GENESIS_HASH: str = "4d7c606c9002d3043ee3979533922e25752bd2755709057060b553593605bd62"  # ✅

def compute_logic_hash(self) -> str:
    signatures = [h.signature() for h in self._hooks]
    payload = "|".join(signatures)
    return hashlib.sha256(payload.encode()).hexdigest()  # ✅

merkle_payload = f"{ctx.prev_hash}|{delta.model_dump_json(exclude_none=True)}"
new_hash = hashlib.sha256(merkle_payload.encode()).hexdigest()  # ✅
```

**Observations**:
✅ SHA256 (256-bit) is cryptographically secure
✅ No weak algorithms (MD5, SHA1)
✅ Deterministic serialization for Merkle chains
✅ Collision resistance for provenance

**Status**: ✅ **EXCELLENT** - Crypto is sound

---

### Finding SEC-018: Merkle Chain Integrity
**Severity**: **LOW**
**File**: `/src/kgcl/engine/atman.py:551-558`

**Description**:
Merkle chain is correctly maintained:

```python
merkle_payload = f"{ctx.prev_hash}|{delta.model_dump_json(exclude_none=True)}"
new_hash = hashlib.sha256(merkle_payload.encode()).hexdigest()

# Update Tip *only if committed* (Atomic State)
if committed:
    self._tip_hash = new_hash  # ✅ Only update on success
```

**Observations**:
✅ Links to previous hash (chain integrity)
✅ Includes delta (content integrity)
✅ Updates only on commit (atomicity)
✅ Genesis hash prevents empty chain attacks

**Enhancement**:
```python
def verify_chain(self) -> bool:
    """Verify Merkle chain integrity from genesis."""
    # Walk backwards through transaction history
    # Recompute hashes and verify chain
    # (Requires transaction history storage)
```

**Status**: ✅ **EXCELLENT** - Merkle chain is well-designed

---

## COMPLIANCE CHECKLIST

| Check | Status | Details |
|-------|--------|---------|
| ✅ No SQL injection | ⚠️ **FAIL** | SEC-001: SPARQL injection in trigger conditions |
| ✅ No path traversal | ⚠️ **FAIL** | SEC-003: workflow_id path traversal |
| ✅ No unsafe deserialization | ✅ **PASS** | JSON only, no pickle/eval |
| ✅ URIRef validation | ⚠️ **PARTIAL** | SEC-005: Heuristic validation needs improvement |
| ✅ RBAC implementation | ❌ **FAIL** | SEC-006: No authorization model |
| ✅ Resource gate enforcement | ⚠️ **FAIL** | SEC-007: No hook registration limits |
| ✅ No privilege escalation | ⚠️ **PARTIAL** | SEC-009: Hook execution needs isolation |
| ✅ No hardcoded secrets | ✅ **PASS** | No secrets found in code |
| ✅ Sensitive data not logged | ✅ **PASS** | Error sanitization in place (SEC-009) |
| ✅ Data transformations safe | ✅ **PASS** | RDF transformations don't leak data |
| ✅ Exceptions sanitized | ✅ **PASS** | ErrorSanitizer comprehensive |
| ✅ Stack traces hidden | ✅ **PASS** | Sanitized before user display |
| ✅ Failed txn rollback | ✅ **PASS** | SEC-012: Rollback integrity verified |
| ✅ Error messages safe | ✅ **PASS** | SEC-011: Minor improvement recommended |
| ✅ Timeout enforcement | ❌ **FAIL** | SEC-013: No hook timeout enforcement |
| ✅ Memory limits | ⚠️ **FAIL** | SEC-014: No graph/transaction limits |
| ✅ No unbounded recursion | ✅ **PASS** | No recursive verb dispatch found |
| ✅ Cancellation works | ⚠️ **PARTIAL** | Transaction rollback works, hook cancellation needed |
| ✅ Webhook URL validation | ⚠️ **N/A** | SEC-016: Not implemented yet (preventive) |
| ✅ No SSRF | ⚠️ **N/A** | No external calls currently |
| ✅ Response handling safe | ⚠️ **N/A** | No HTTP responses processed |
| ✅ External call timeout | ⚠️ **N/A** | No external calls |
| ✅ Strong hashing (SHA256) | ✅ **PASS** | SEC-017: Crypto is excellent |
| ✅ No weak algorithms | ✅ **PASS** | No MD5/SHA1 usage |
| ✅ Merkle deterministic | ✅ **PASS** | SEC-018: Chain integrity verified |
| ✅ Hash collision resistance | ✅ **PASS** | SHA256 provides 2^128 security |

---

## SEVERITY SUMMARY

| Severity | Count | Findings |
|----------|-------|----------|
| **CRITICAL** | 1 | SEC-006 (Authorization) |
| **HIGH** | 2 | SEC-001 (SPARQL injection), SEC-016 (Webhooks) |
| **MEDIUM** | 6 | SEC-002, SEC-003, SEC-007, SEC-008, SEC-013, SEC-014 |
| **LOW** | 9 | SEC-004, SEC-005, SEC-009, SEC-010, SEC-011, SEC-012, SEC-015, SEC-017, SEC-018 |

---

## REMEDIATION ROADMAP

### Phase 1: Critical Blockers (Production)
**Timeline**: 1-2 weeks

1. **SEC-006**: Implement RBAC authorization model
   - Add `WorkflowActor` with role-based permissions
   - Enforce authorization on all workflow operations
   - Add audit logging

2. **SEC-001**: Fix SPARQL injection in trigger conditions
   - Validate/sanitize SPARQL patterns
   - Use parameterized queries
   - Add pattern whitelist

### Phase 2: High-Severity Issues
**Timeline**: 2-3 weeks

3. **SEC-003**: Sanitize workflow_id path traversal
   - Validate workflow IDs
   - Prevent directory traversal
   - Verify final paths

4. **SEC-013**: Enforce hook execution timeouts
   - Wrap all hook calls with `asyncio.wait_for()`
   - Set 30s default timeout
   - Log timeout violations

### Phase 3: Medium-Severity Hardening
**Timeline**: 3-4 weeks

5. **SEC-007**: Add resource limits (hooks, transactions, graphs)
6. **SEC-002**: Validate SPARQL LIMIT parameter
7. **SEC-014**: Implement graph size/transaction limits
8. **SEC-010**: Add secret detection for RDF literals

### Phase 4: Low-Severity Improvements
**Timeline**: Ongoing

9. SEC-004, SEC-005, SEC-009, SEC-011 (minor enhancements)
10. SEC-016: Implement webhook validation (when feature added)

---

## PRODUCTION READINESS ASSESSMENT

**Current Status**: ⚠️ **NOT PRODUCTION READY**

**Blocking Issues**:
1. ❌ No authorization model (SEC-006) - **CRITICAL**
2. ❌ SPARQL injection vulnerability (SEC-001) - **HIGH**
3. ❌ No hook timeout enforcement (SEC-013) - **MEDIUM**

**Recommended Actions**:
1. **DO NOT deploy** to production without fixing SEC-006 and SEC-001
2. Implement authorization and SPARQL sanitization (Phase 1)
3. Add comprehensive security testing:
   - Penetration testing for SPARQL injection
   - Fuzzing for path traversal
   - Load testing for resource limits
4. Security audit of all hook implementations
5. Threat modeling for workflow execution paths

**Estimated Remediation Time**: 4-6 weeks for production-ready state

---

## ADDITIONAL SECURITY RECOMMENDATIONS

### 1. Security Testing
- **SAST**: Integrate Bandit, Semgrep for automated scanning
- **DAST**: Penetration testing of SPARQL endpoints
- **Fuzzing**: Use hypothesis for property-based testing
- **Dependency scanning**: Monitor PyPI packages for vulnerabilities

### 2. Monitoring & Alerting
- **Failed authorization attempts** → Alert security team
- **SPARQL injection attempts** → Block IP, alert
- **Resource limit violations** → Rate limit, alert
- **Hook timeouts** → Log, investigate

### 3. Secure Deployment
- **Principle of least privilege**: Run with minimal permissions
- **Network isolation**: Firewall SPARQL endpoints
- **Secrets management**: Use Vault/AWS Secrets Manager
- **Audit logging**: Log all security events to SIEM

### 4. Code Review Process
- **Security review** for all PRs touching:
  - Hook system
  - SPARQL query construction
  - File I/O operations
  - Authorization logic
- **Two-person rule** for security-sensitive changes

---

## CONCLUSION

The KGC YAWL Engine demonstrates **good architectural patterns** (transactions, provenance, error sanitization) but has **critical security gaps** that must be addressed before production deployment.

**Strengths**:
✅ Strong transaction integrity with rollback
✅ Comprehensive error sanitization
✅ Excellent cryptographic design (SHA256, Merkle chains)
✅ Good observability (OpenTelemetry)

**Critical Weaknesses**:
❌ No authorization model (SEC-006)
❌ SPARQL injection vulnerabilities (SEC-001)
❌ Missing timeout enforcement (SEC-013)
❌ Inadequate resource limits (SEC-007, SEC-014)

**Recommendation**: **Delay production deployment** until Phase 1 and Phase 2 remediation is complete. The system shows promise but requires security hardening to meet production standards for a "Nuclear Launch Protocol" scenario.

---

**Report Prepared By**: Security Specialist (Claude Code)
**Date**: 2025-11-25
**Review Scope**: Workflow orchestration, Atman engine, UNRDF engine, hooks system
**Next Review**: After Phase 1 remediation (2 weeks)
