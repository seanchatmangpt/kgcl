# 80/20 Fill the Gaps – KGCL Capability Completion Order

## Purpose

Eliminate the highest-impact incomplete capabilities before they become regressions. Every pass through this command must tighten quality, consistency, and maintainability.

### Action Directive (DfLSS)

This is a Design for Lean Six Sigma order. When `/80-20-fill-gaps` runs, execute every step immediately and independently—no permission loops.

## Principles

- **Value is Quality × Consistency × Maintainability.**
- **80/20 targeting:** finish the top 20 % of gaps that unlock 80 % of the user value (SLOs, LinkML safety, UNRDF parity).
- **No partial work:** done means typed, tested (Chicago TDD), documented, validated.

## Flow

```
Scan quickly → Rank by impact/value → Execute fixes → Validate → Log next steps
```

## 1. Scan Quickly

Use lightweight sweeps to surface unfinished work:

```bash
rg -n "TODO|FIXME|pass|raise NotImplementedError" src/kgcl
rg -n "xfail|skip" tests
rg -n "pass$" src/kgcl/**/*.py
```

Targets to inspect:
- `src/kgcl/hooks/**` – lifecycle gaps, receipts, sandboxing
- `src/kgcl/unrdf_engine/**` – adapters, SPARQL, ingestion
- `tests/**` – integration holes, perf/security markers
- `docs/*.md` – implementation drift

Capture findings as you go:

```markdown
## Capability Inventory
- `hooks/policy_pack_manager.py::activate_pack` – missing idempotency guard
- `unrdf_engine/executor.py::execute_plan` – timeout data absent from receipts
- `tests/integration/test_unrdf_porting.py` – no lockchain regression coverage
```

## 2. Rank by Impact & Value

Categories:
- **Error handling** – sanitizer gaps, raw tracebacks
- **Type safety** – missing Literal enums, implicit `Any`
- **Validation** – LinkML not enforced, schema drift
- **Testing** – Chicago structure missing, no phase assertions
- **Performance** – no SLO metrics, cache not tracked

Apply the 80/20 matrix:

| Quadrant | Examples | Action |
| --- | --- | --- |
| High impact + high value | Receipt metrics missing, UNRDF cache invalid | Do now |
| High impact + medium value | Integration markers, observability gaps | Plan next |
| Low impact + high value | Doc sync for new CLI | Batch later |
| Low impact + low value | Cosmetic refactors | Ignore |

Keep a running stack ordered by SLO risk and user value.

## 3. Execute the Fix

1. Pick the top item; stop scanning.
2. Implement with frozen dataclasses, full type hints, absolute imports.
3. Add/expand Chicago tests first (real hooks/UNRDF, no mocks).

Example transformation:

```python
# BEFORE
def build_receipt(hook, duration_ms):
    pass

# AFTER
from kgcl.hooks.models import Hook, HookReceipt

def build_receipt(hook: Hook, duration_ms: float) -> HookReceipt:
    """Emit sanitized receipt with phase metrics."""
    return HookReceipt.from_execution(
        hook=hook,
        duration_ms=duration_ms,
        phase_metrics=hook.metrics.snapshot(),
    ).sanitize()
```

Completion checklist:
- [ ] Frozen dataclasses or typed functions
- [ ] ErrorSanitizer invoked at boundaries
- [ ] Performance metrics recorded (`duration_ms`, cache hits)
- [ ] Chicago tests cover pass/fail/receipt scenarios
- [ ] Docs updated if behavior changed

## 4. Validate Ruthlessly

```bash
uv sync --frozen
poe format
poe lint
poe type-check
poe test
poe unrdf-full        # required if the change touches UNRDF paths
poe pre-commit-run
```

Gates:
- Ruff clean (ALL rules except documented ignores)
- `poe type-check` passes with `strict = true`
- Pytest strict markers green, no new skips
- Performance stays within SLOs

Store evidence (command + exit code) in the PR or issue.

## 5. Log Next Moves

```markdown
## Next Steps
1. Instrument sandbox limits in `HookExecutionPipeline` (requires metrics schema)
2. Expand integration suite for `PolicyPackManager` error handling
3. Document the new LinkML validation guard in `docs/CLI_IMPLEMENTATION_SUMMARY.md`
```

If something can’t be finished, record owner/blocker and leave the codebase production-ready (feature flag off or guard clause).

## Cross-Checks

- Pair with **`/gemba-walk`** to observe behavior before declaring complete.
- Use **`/poka-yoke-design`** for invariants and **`/expert-testing-patterns`** for multi-layer tests.
- Close with **`/verify-tests`** to ensure suites remain green.

## Reminders

- Never reduce NumPy docstrings or type hints while filling gaps.
- Chicago TDD = real collaborators only.
- Structured logging/receipts only—`print` is banned.
- “Done” = `.githooks/pre-commit` + `poe verify` both pass.
- LinkML validation stays mandatory for CLI flows (including `kgct` commands).

