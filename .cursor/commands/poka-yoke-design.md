# Poka-Yoke Design (Error Prevention) for KGCL

## Purpose

Poka-yoke means “mistake-proofing.” In KGCL we use Python’s type system, dataclasses, and strict mypy configuration to eliminate whole classes of bugs before runtime. This guide shows how to design APIs that cannot be misused.

### Action Directive (DfLSS)

This guide is issued through the core team’s Design for Lean Six Sigma program. Once `/poka-yoke-design` is called, implement the safeguards immediately without seeking additional approval.

## Workflow

```
Identify error modes → Encode invariants in types → Enforce via helpers/decorators → Verify with mypy + tests → Document guarantees
```

## 1. Identify Error Modes

Create an inventory per module:

```markdown
### Invalid State
- HookReceipt missing sanitized error payload
- PolicyPackManager activates same pack twice

### Invalid Input
- CLI accepts empty ontology path
- UnrdfEngine executes query without schema validation

### Invalid Operation
- Hook executed after sandbox timeout
- Cache mutated after expiration
```

Focus on scenarios that repeatedly cause bugs or regressions.

## 2. Encode Invariants in Types

### 2.1 Value Objects (Frozen Dataclasses)

```python
@dataclass(frozen=True)
class SanitizedError:
    code: str
    message: str

    @staticmethod
    def from_exception(exc: Exception) -> SanitizedError:
        return SanitizedError(
            code="UNEXPECTED_ERROR",
            message=ErrorSanitizer.strip_sensitive_data(str(exc)),
        )
```

By freezing the dataclass, no caller can mutate the sanitized message later.

### 2.2 Typed Constructors

```python
class HookName(str):
    """Valid hook names."""

    @classmethod
    def new(cls, raw: str) -> HookName:
        if not raw or raw.strip() != raw:
            raise ValueError("Hook names must be non-empty and trimmed")
        return cls(raw)
```

Use these wrappers across registries (`Dict[HookName, Hook]`) to prevent duplicates and whitespace issues.

### 2.3 Enum / Literal States

```python
class HookPhase(str, Enum):
    PRE = "PRE"
    EVALUATE = "EVALUATE"
    RUN = "RUN"
    POST = "POST"
```

All receipts/metrics must reference `HookPhase` instead of raw strings, eliminating typos and enabling mypy exhaustiveness checks.

### 2.4 Protocols for Capability Contracts

```python
class Cache(Protocol):
    def get(self, key: str) -> CacheEntry | None: ...
    def set(self, key: str, entry: CacheEntry, ttl_seconds: int) -> None: ...
```

Consumers depend on the protocol, so any cache implementation must satisfy the contract or mypy fails.

## 3. Enforce with Helpers and Decorators

### 3.1 Guarded Factories

```python
def build_receipt(
    hook: Hook,
    result: HookResult,
    *,
    phase: HookPhase,
) -> HookReceipt:
    if result.duration_ms > hook.timeout_ms:
        raise HookTimeoutError(hook.name)
    return HookReceipt(...)
```

Callers must go through the factory, guaranteeing timeouts are enforced consistently.

### 3.2 Validation Wrappers

```python
def require_linkml(func: Callable[P, T]) -> Callable[P, T]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        schema = kwargs.get("linkml_path")
        if not schema:
            raise LinkMLValidationError("LinkML schema required")
        return func(*args, **kwargs)
    return wrapper
```

Apply to every CLI entrypoint so validation can’t be skipped.

### 3.3 Typed Context Managers

```python
@contextmanager
def sandboxed_execution(hook: Hook) -> Iterator[SandboxContext]:
    ctx = SandboxContext.start(hook)
    try:
        yield ctx
    finally:
        ctx.finish()
```

Enforces cleanup even if the hook fails, preventing leaked resources.

## 4. Verify with Tooling

1. `poe type-check` – mypy rejects any misuse.
2. `poe test` – Chicago School tests exercise real objects.
3. Add regression tests around new invariants; e.g., `pytest.raises(ValueError)` for invalid HookName.

When invariants span modules, add integration tests (e.g., `tests/integration/test_unrdf_porting.py`) to prove end-to-end enforcement.

## 5. Document Invariants

Include NumPy-style docstrings that state guarantees explicitly:

```python
def execute_hook(hook: Hook, event: HookEvent) -> HookReceipt:
    """Run a hook through the full lifecycle.

    Guarantees
    ----------
    - LinkML validation succeeded before execution.
    - Returned receipt contains sanitized error information.
    - Duration metrics include all phases in chronological order.
    """
```

Also update relevant docs (`docs/HOOKS_IMPLEMENTATION_SUMMARY.md`, `docs/UNRDF_PORTING_GUIDE.md`) so future contributors know the invariants.

## Anti-Patterns

- Relying on runtime checks when a typed constructor or enum would prevent the issue.
- Allowing mutable dictionaries or bare strings to represent critical IDs.
- Using `Optional` without enforcing non-`None` paths downstream.
- Accepting `dict[str, Any]` instead of typed `TypedDict` / dataclass objects.

## References

- [Expert Testing Patterns](./expert-testing-patterns.md) – validate the invariants
- [Eliminate Mura](./eliminate-mura.md) – keep patterns consistent
- [Strict Build Verification](./strict-build-verification.md) – enforce mypy + lint gates

