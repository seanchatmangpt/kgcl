# Expert Testing Patterns for KGCL

## Purpose

Chicago School TDD requires real systems exercising real dependencies. These patterns catch the failures that actually break KGCL (hooks, UNRDF engine, CLI, LinkML validation) without bloated suites.

### Action Directive (DfLSS)

This command represents an active Design for Lean Six Sigma directive. When `/expert-testing-patterns` is used, implement the patterns immediately—no waiting for further confirmation.

## Workflow

```
Identify test type → Apply pattern → Assert behavior → Validate coverage → Enforce quality gates
```

## Core 80/20 Areas

- Error paths & sanitizer coverage
- Hook lifecycle boundaries (PRE/EVALUATE/RUN/POST)
- Data integrity (RDF/SPARQL round-trips, LinkML validation)
- Performance envelopes (cache hits, timeout receipts)
- Real collaborators (no mocking domain objects)

---

### Pattern 1: Error Path & Sanitizer Testing

1. Enumerate every exception that should be sanitized (invalid SPARQL, sandbox violation, timeout, policy pack missing).
2. Use pytest parametrization to cover them.

```python
@pytest.mark.parametrize(
    ("event", "expected_code"),
    [
        ({"hook": "unknown"}, "HOOK_NOT_FOUND"),
        ({"hook": "slow"}, "TIMEOUT"),
    ],
)
def test_pipeline_sanitizes_errors(event: dict[str, Any], expected_code: str) -> None:
    pipeline = HookExecutionPipeline(...)
    receipt = pipeline.execute(event)
    assert receipt.error is not None
    assert receipt.error.code == expected_code
    assert "Traceback" not in receipt.error.message
```

Checklist:
- [ ] Every error variant triggered
- [ ] Receipt captures sanitized payload
- [ ] Pipeline remains reusable after failure

---

### Pattern 2: Boundary & Phase Testing

Treat each hook lifecycle phase as a boundary. Validate min/max payloads.

```python
def test_hook_phases_run_in_order(sample_hook: Hook, sample_event: HookEvent) -> None:
    pipeline = HookExecutionPipeline(metrics=InMemoryMetrics())
    receipt = pipeline.execute(sample_hook, sample_event)
    assert receipt.phase_metrics == ["PRE", "EVALUATE", "RUN", "POST"]
    assert receipt.duration_ms < 100.0
```

Additional boundaries:
- Empty RDF graph vs. max-size example
- CLI input with minimum arguments vs. full set
- Query cache TTL = 0 vs. default vs. extreme

---

### Pattern 3: Behavior-Focused Integration Tests

Focus on observable outcomes:

```python
@pytest.mark.integration
def test_policy_pack_activation_updates_registry(tmp_path: Path) -> None:
    manager = PolicyPackManager(registry=HookRegistry())
    manager.activate_pack(path=tmp_path / "pack.yml")
    active_hooks = manager.registry.list_active()
    assert {"sandbox_enforcer", "lockchain_writer"} <= {h.name for h in active_hooks}
```

Rules:
- Use actual registries, engines, and LinkML schemas.
- Assert on receipts, metrics, or persisted files, not just return values.

---

### Pattern 4: AAA + Fixtures

Structure every test explicitly:

```python
def test_error_sanitizer_masks_paths(error_sanitizer: ErrorSanitizer) -> None:
    # Arrange
    raw_error = RuntimeError("Failed at /tmp/secrets")

    # Act
    sanitized = error_sanitizer.sanitize(raw_error)

    # Assert
    assert "/tmp" not in sanitized.message
    assert sanitized.code == "UNEXPECTED_ERROR"
```

Fixtures live in `tests/conftest.py` or module-level `conftest.py` organized by domain (hooks, unrdf_engine, cli).

---

### Pattern 5: Real Collaborators

Never mock Hook, Receipt, or UnrdfEngine. Use lightweight in-memory implementations or actual files under `tests/fixtures`.

```python
def test_unrdf_cache_hits(tmp_path: Path, rdf_fixture: str) -> None:
    engine = UnrdfEngine(cache=QueryCache(ttl_seconds=30))
    first = engine.execute(rdf_fixture, tmp_path / "query.sparql")
    second = engine.execute(rdf_fixture, tmp_path / "query.sparql")
    assert second.metadata["cache_hit"] is True
```

Use mocks only for true side effects (network calls to external services) and prefer adapters with contract tests.

---

## Coverage Validation

```bash
poe test
poe test-coverage
poe pytest tests/hooks/test_security.py::TestErrorSanitizer -vv
```

Targets:
- Hooks + UNRDF modules ≥95%
- Overall ≥90%
- New code 100% branch coverage

## Anti-Patterns to Avoid

- `assert hook is not None` (meaningless).
- Tests that only check type of exception without ensuring sanitizer behavior.
- Mocking LinkML validation or SPARQL responses.
- omitting NumPy docstrings in test helpers.
- Sleeping to “test” timeouts instead of using deterministic controls.

## Quick Reference

```python
# Error path
def test_pipeline_handles_timeout(...): ...

# Boundary
def test_cli_requires_linkml_schema(...): ...

# Behavior
@pytest.mark.integration
def test_lockchain_writer_records_anchor(...): ...
```

## Supporting Commands

- [Verify Tests](./verify-tests.md) for failure triage
- [80/20 Fill Gaps](./80-20-fill-gaps.md) to find missing coverage
- [Strict Build Verification](./strict-build-verification.md) for gating

