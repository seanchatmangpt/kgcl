# Fix Ruff Lint Errors - KGCL Workflow

## Purpose

KGCL enables Ruff's `select = ["ALL"]`, mypy strict mode, and aggressive git hooks. This playbook removes every lint violation quickly while prioritizing correctness and security (no `print`, no relative imports, no mutable dataclasses).

### Action Directive (DfLSS)

This is a Design for Lean Six Sigma execution order. Once `/fix-lint-errors` is invoked, clear the violations immediately without seeking additional approval.

## Workflow

```
Analyze → Auto-fix → Batch Critical → Batch Style → Verify
```

## Step 1: Analyze Violations

```bash
poe lint-check 2>&1 | tee /tmp/ruff.log
rg -n "error" /tmp/ruff.log | head -50
```

Key signals:
- `F401/F841` (unused import/variable) – common after refactors
- `D` rules – missing/invalid NumPy docstrings
- `ANN` rules – missing type hints
- `N` naming errors (CamelCase vs snake_case)
- `S/B` security issues (dangerous subprocess, exec)

Document the count per code area to plan batching.

## Step 2: Auto-Fix What Ruff Can

```bash
poe lint        # runs ruff --fix
```

Auto-fix handles:
- Import sorting/removal
- Simple formatting (but still run `poe format`)
- Some docstring spacing

Re-run `poe lint-check` afterwards to view remaining violations.

## Step 3: Fix Critical Issues First

### 3.1 Safety / Correctness (`S`, `B`, `ERA`)

- Replace `print()` with logging or receipt metrics (but repo prefers structured logging already; usually remove prints).
- Ensure subprocess usage goes through allowed wrappers.
- Remove commented-out code flagged by `ERA*`.

### 3.2 Type-System Issues (`ANN`, `ARG`, `FBT`)

- Add explicit type hints to every function, including tests.
- For callbacks, use `Callable[[...], ReturnType]`.
- Replace mutable dataclasses with `@dataclass(frozen=True)` unless the class is clearly mutable (rare).

### 3.3 Import Rules

- Convert relative imports to absolute: `from kgcl.hooks.core import Hook`.
- Keep `__all__` updated when exports change.

### 3.4 Prohibited Patterns

- `pass` placeholders → raise typed exceptions or implement functionality.
- `raise NotImplementedError` in production paths → complete implementation or guard with feature flag.
- `Optional[...]` without explicit `None` handling → restructure logic.

## Step 4: Batch Style/Readability Issues

### 4.1 Docstrings (`D*`)

- All public functions/classes require NumPy-style docstrings with Parameters/Returns/Raises.
- Keep docstrings aligned with actual behavior; update examples if signatures changed.

### 4.2 Complexity (`C901`, `PLR0915`)

- Split functions >40 lines or with too many branches.
- Extract helper functions under the same module; ensure they are fully typed and documented.

### 4.3 Test Cleanups

- Pytest fixtures must live in `conftest.py` or be explicitly imported.
- Use descriptive test names (`test_hook_pipeline_sanitizes_timeout`).
- Replace `assert 1 == 1` placeholders with meaningful assertions.

### 4.4 Dead Code (`F401`, `F841`, `ERA001`)

- Remove unused imports/variables rather than prefixing with `_` unless intentionally unused (i.e., `*_args` in fixtures).
- Delete commented-out blocks; they violate ERA rules and clutter diffs.

## Step 5: Verify

```bash
poe format
poe lint
poe type-check
poe test
.githooks/pre-commit
```

All commands must exit 0. Lint phase should output “0 violations”.

## Batch Strategies

1. **File-by-file**: Ideal when a module has multiple violations; keeps context local.
2. **Rule-by-rule**: Useful for repetitive fixes (e.g., missing docstrings). Use `ruff --select D1 --exit-zero` to focus on docstrings.
3. **Domain-first**: Start with `src/kgcl/hooks/**`, then `src/kgcl/unrdf_engine/**`, then CLI/tests.

## Common Fix Patterns

| Violation | Fix |
| --- | --- |
| `ANN201 Missing return type` | Add explicit return `-> Receipt` etc. |
| `D417 Missing argument description` | Add Parameters section in docstring. |
| `F401` | Delete import, or move usage from test helper to module. |
| `S101/S607` | Replace assert/exec with safe alternative; ensure sandboxed contexts. |
| `T20` (print) | Remove or convert to structured logging (if absolutely necessary). |
| `ERA001` | Delete commented code, document history in git instead. |

## Example Mini-Workflow

```bash
poe lint-check                          # F401, D102 flagged
# Remove unused import in src/kgcl/hooks/core.py
# Add docstring to HookRegistry.register
poe lint-check                          # clean
poe format
poe type-check
poe test
```

## Tips

- Keep `pyproject.toml` consistent; never loosen lint ignore lists.
- If a rule truly requires suppression, use targeted `# noqa: <code>` with justification, but expect scrutiny.
- When adding docstrings, ensure examples run under doctest (`pytest --doctest-modules` is on).
- Update docs if lint changes behavior (e.g., replacing `print` with sanitized message).

## Related Commands

- [ACP](./acp.md) for staging/pushing once lint is clean.
- [Root Cause Analysis](./root-cause-analysis.md) if lint reveals deeper architectural problems.
- [Strict Build Verification](./strict-build-verification.md) for the full gate suite.



