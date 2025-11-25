# 80/20 Fill the Gaps - KGCL Capability Completion Playbook

## Purpose

Use this command when the codebase needs an aggressive, autonomous sweep for partially implemented KGCL capabilities. The agent applies 80/20 thinking to finish the highest-value work, validates everything with Chicago School TDD rigor, and ships production-grade Python without asking for confirmation.

### Action Directive (DfLSS)

This playbook is an order from the core team’s Design for Lean Six Sigma initiative. When `/80-20-fill-gaps` is invoked, execute every step immediately and independently—do not pause to ask for additional approval.

## Core Principle

- **Value = Quality + Consistency + Maintainability**. Shipping partial work is negative value.
- **80/20 targeting**: the top 20% of unfinished capabilities deliver 80% of the real value (SLO compliance, type safety, UNRDF readiness).
- **No tech debt allowed**: work is complete only when typed, documented, tested, and validated end-to-end.

## Workflow

```
Scan → Identify → Finish → Validate → Plan Next Moves
```

## Step 1: 80/20 Scan

### 1.1 High-Signal Sweep

```bash
# Critical directories
rg -n "TODO|FIXME|pass|raise NotImplementedError" src/kgcl
rg -n "TODO|xfail|skip" tests
rg -n "pass$" src/kgcl/**/*.py
```

Targets:
- `src/kgcl/hooks/**`: lifecycle gaps, missing receipts, sandbox violations
- `src/kgcl/unrdf_engine/**`: UNRDF adapters, RDF parsers, SPARQL evaluators
- `tests/**`: missing integration hooks, absent perf/security markers
- `docs/*.md`: implementation references that lag reality

### 1.2 Pattern Recognition

Incomplete capability signals:
1. `pass` blocks guarding production paths
2. Missing NumPy docstrings or partial parameter docs
3. Functions without return type annotations (`mypy` will fail)
4. Integration tests not covering new hook phases
5. Partial UNRDF porting (JS pseudo-code left in comments)

Document findings immediately:

```markdown
## Capability Inventory
- hooks/policy_pack_manager.py::PolicyPackManager.activate_pack – missing idempotency guard
- unrdf_engine/executor.py::execute_plan – lacks timeout receipt data
- tests/integration/test_unrdf_porting.py – no coverage for lockchain writer regression
```

## Step 2: Identify + Prioritize

### 2.1 Categorize

- **Error Handling**: sanitizer gaps, unsanitized tracebacks, raised raw exceptions
- **Type Safety**: missing Literal-based phase enums, Optional misuse, implicit `Any`
- **Validation**: CLI commands without LinkML validation, missing schema hooks
- **Testing**: Chicago TDD violations, no pre/post-phase assertions
- **Performance**: missing metrics for p99 SLO, absent caching paths

### 2.2 80/20 Matrix (Quality-First)

| Quadrant | Examples | Action |
| --- | --- | --- |
| High Impact + High Value | Hook receipts missing sandbox metrics; UNRDF cache invalidation incomplete | Finish now |
| High Impact + Medium Value | Additional integration markers | Plan after high-value |
| Low Impact + High Value | Doc sync for new CLI command | Batch after core |
| Low Impact + Low Value | Cosmetic refactors | Skip |

Keep a running prioritized stack ranked by value to SLO, safety, and UNRDF parity.

## Step 3: Finish Capabilities

### 3.1 Implementation Flow

1. Stop scanning; laser-focus on the highest-value capability.
2. Flesh out the implementation using idiomatic Python + dataclasses.
3. Enforce absolute imports and full type hints.
4. Add/adjust Chicago-style tests first when feasible.

Example transformation:

```python
# BEFORE
def build_receipt(hook, duration_ms):
    pass

# AFTER
from kgcl.hooks.models import Hook, HookReceipt

def build_receipt(hook: Hook, duration_ms: float) -> HookReceipt:
    """Create immutable receipt with sanitized metadata."""
    receipt = HookReceipt.from_execution(
        hook=hook,
        duration_ms=duration_ms,
        phase_metrics=hook.metrics.snapshot(),
    )
    return receipt.sanitize()
```

### 3.2 Completion Checklist

- [ ] Implementation uses frozen dataclasses or typed functions
- [ ] Error handling routes through `ErrorSanitizer`
- [ ] Performance metrics recorded (`duration_ms`, cache hits)
- [ ] Chicago tests cover happy path + failure path + receipt assertions
- [ ] Documentation references updated if behavior changed

### 3.3 Batch Wisely

Batch only tightly related fixes (e.g., all hook receipt metrics). Avoid mixing CLI edits with UNRDF internals in a single pass to keep verification sharp.

## Step 4: Validate Ruthlessly

```bash
uv sync --frozen
cargo-make format
cargo-make lint
cargo-make type-check
cargo-make test
cargo-make unrdf-full      # when capability touches UNRDF porting
```

Validation gates:
- Ruff clean (ALL rules minus allowed ignores)
- `poe type-check` passes with `strict = true`
- Pytest green with strict markers, no unexpected skips
- Performance-focused tests stay within documented SLO thresholds

Capture evidence (command + exit code) if reporting back.

## Step 5: Plan Next Moves

Create a crisp follow-up plan:

```markdown
## Next Steps
1. Instrument hook sandbox limits in `HookExecutionPipeline` (blocked on metrics schema)
2. Expand integration test matrix for `PolicyPackManager` activation errors
3. Document new LinkML validation flow in `docs/CLI_IMPLEMENTATION_SUMMARY.md`
```

If a capability cannot be finished immediately, log blockers, open TODO with owner, and ensure the codebase remains production-ready (feature flag off, guard clause, or revert partial change).

## Integration with Other Commands

- Pair with **[Gemba Walk](./gemba-walk.md)** to see real behavior before declaring complete.
- Use **[Poka-Yoke Design](./poka-yoke-design.md)** for type-safety and sandbox guards.
- Run **[Expert Testing Patterns](./expert-testing-patterns.md)** once a capability spans multiple layers.
- Finish by **[Verify Tests](./verify-tests.md)** to ensure Chicago coverage.

## Expert Reminders

- Never degrade NumPy docstrings or type hints while filling gaps.
- Chicago School TDD means real objects, real IO, no mocks for core domain.
- `print` statements are banned—capture diagnostics via structured receipts/tests instead.
- Capability is “done” only when it can pass `.githooks/pre-commit` and `cargo-make verify`.
- Always keep LinkML validation enabled for CLI flows—no escape hatches.

