# Eliminate Muda (Waste) in KGCL

## Purpose

Muda = any line of code, dependency, or workflow in KGCL that consumes resources without delivering production value (quality, consistency, maintainability). This playbook removes it surgically while keeping the pipeline green.

### Action Directive (DfLSS)

This command is issued under the core team’s Design for Lean Six Sigma program. When `/eliminate-muda` is invoked, act immediately—identify waste, remove it, and validate without pausing to ask for permission.

## Workflow

```
Identify → Measure → Remove → Verify → Control
```

## Step 1: Identify Muda

Scan with intent. Focus on the seven wastes translated for this Python/UNRDF stack:

1. **Over-processing**
   - Multiple abstractions hiding the same hook behavior
   - Dataclasses that wrap identical payloads
   - Manual JSON parsing when LinkML schema already validates

2. **Waiting**
   - Blocking file IO inside hook evaluation
   - Sequential SPARQL calls that could be cached
   - CLI operations waiting on unnecessary network hops

3. **Transportation**
   - Passing large dicts through three layers just to pull 1 key
   - Serializing/deserializing RDF repeatedly

4. **Inventory**
   - Dead modules under `src/kgcl/legacy/**`
   - Unused dependencies in `pyproject.toml`
   - Commented-out code, feature toggles left on forever

5. **Motion**
   - Copy/paste hook lifecycle logic per policy pack
   - Tests recreating identical fixtures instead of using shared factories

6. **Defects**
   - Silent `except Exception` blocks
   - Missing sanitizer coverage
   - Partial type hints that hide bugs

7. **Over-production**
   - Features built without real CLI access
   - Config flags with no tests or docs

Create an explicit inventory:

```markdown
## Muda Inventory
- src/kgcl/hooks/policy_pack_manager.py::activate_pack – duplicate validation branch (Over-processing)
- src/kgcl/unrdf_engine/cache.py – unused TTL parameter (Inventory)
- tests/hooks/test_security.py – repeated sanitizer fixtures (Motion)
- docs/README.md – outdated workflow description causing confusion (Defect)
```

## Step 2: Measure Impact

Decide what to remove first by quantifying:

- Lines of dead/duplicate code
- Cyclomatic complexity (Ruff C901 hints)
- Runtime cost (SPARQL latency, hook duration)
- Maintenance burden (number of call sites affected)

Prioritize:
1. High impact / low effort (delete unused module, remove duplicate code)
2. High impact / higher effort (refactor shared hook lifecycle)
3. Low impact / low effort (clean small utils)
4. Low impact / high effort (defer)

## Step 3: Remove Waste

Tactics by waste:
- **Dead code**: delete files + tests, update docs.
- **Unused deps**: remove from `pyproject.toml`, run `uv sync`.
- **Duplication**: extract typed helper or strategy.
- **Blocking IO**: introduce async pipeline or caching layer.
- **Error-prone code**: replace with sanitizer + typed exceptions.

Example:

```python
# BEFORE: duplicate sanitizer fixture in every test module
def test_receipt_sanitizes_errors():
    sanitizer = ErrorSanitizer()
    ...

# AFTER: shared fixture in tests/conftest.py
@pytest.fixture
def sanitizer() -> ErrorSanitizer:
    return ErrorSanitizer()
```

Always keep LinkML validation, sandbox limits, and UNRDF parity intact.

## Step 4: Verify Value Stream

```bash
cargo-make format
cargo-make lint
cargo-make type-check
cargo-make test
cargo-make unrdf-full        # if touching UNRDF paths
.githooks/pre-commit
```

Ensure:
- No regressions in hooks/UNRDF integration tests
- Coverage of deleted code replaced with better tests if needed
- SLO metrics still tracked (duration, cache hit ratios)

## Step 5: Control (keep waste from returning)

- Update `docs/HOOKS_QUICK_REFERENCE.md` or relevant guides with new simplified flow.
- Add Ruff or pytest rules to catch the waste earlier (e.g., forbid `pass`).
- Strengthen Chicago TDD fixtures or LinkML schemas to make the waste impossible.
- Note learnings in `kaizen-improvement.md`.

## Sample Outcome Log

```markdown
### Waste removed
1. Deleted src/kgcl/legacy/cache_adapter.py (unused module)
2. Replaced duplicate sanitizer fixtures with shared pytest fixture
3. Removed redundant RDF serialization roundtrip

### Impact
- 350 lines deleted
- Hook execution p95 dropped from 42ms → 29ms
- Simplified docs section to match real workflow

### Controls
- Added Ruff rule (F841) enforcement to block unused vars
- Added test ensuring receipts never serialize twice
```

## References

- [Eliminate Mura](./eliminate-mura.md) for standardization controls
- [Kaizen Improvement](./kaizen-improvement.md) for continuous tracking
- [Strict Build Verification](./strict-build-verification.md) for validation commands

