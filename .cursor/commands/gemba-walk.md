# Gemba Walk - KGCL Edition

## Purpose

“Gemba” = the actual place where work happens. For KGCL that means running real hooks, inspecting SPARQL plans, reading Python modules, and verifying CLI behavior. Never trust a doc or summary until you’ve seen the source and the output.

### Action Directive (DfLSS)

This workflow is mandated by the core team’s Design for Lean Six Sigma initiative. When `/gemba-walk` is invoked, immediately go to the source and execute every step without pausing for confirmation.

## Workflow

```
Go to source → Observe behavior → Verify claims → Capture discrepancies → Fix at source
```

## 1. Go to the Source

Focus areas:
- `src/kgcl/hooks/**` – hook lifecycle, receipts, sandbox limits
- `src/kgcl/unrdf_engine/**` – SPARQL execution, caching, lockchain writer
- `tests/**` – how the system is actually exercised
- `docs/**` – to cross-check statements against reality

Commands:

```bash
rg -n "" src/kgcl/hooks/executor.py         # open the actual file in Cursor
rg -n "" tests/integration/test_unrdf_porting.py
```

Avoid assumptions, PowerPoint summaries, or outdated READMEs. Read the code, not the myth.

## 2. Observe Real Behavior

Run the system the way users do:

```bash
poe test
poe unrdf-full
poe pytest tests/cli/test_cli.py::test_cli_enforces_linkml -vv
```

Capture artifacts:

```bash
poe test 2>&1 | tee reports/gemba-test.log
```

Inspect receipts, metrics, and RDF outputs saved in `examples/sample_outputs` or test fixtures. If necessary, run the installed KGCL CLI commands (e.g., `kgc-query`, `kgc-config`) using real data.

## 3. Verify Claims vs Reality

Collect claims from:
- Docstrings and module headers
- Docs (e.g., `docs/CLI_QUICKSTART.md`, `docs/UNRDF_PORTING_GUIDE.md`)
- Test names like `test_lockchain_writer_persists_anchor`
- Commit messages or TODOs

For each claim, answer:
1. Does the implementation actually do that?
2. Do tests enforce it?
3. Does the CLI/docs say something else?

Document findings:

```markdown
## Claim Verification
- Claim: "CLI always validates LinkML schema" (docs/CLI_QUICKSTART.md)
  - Code: `kgcl.cli.app` calls `validate_linkml()` unconditionally ✅
  - Tests: `tests/cli/test_cli.py::test_cli_requires_linkml` ensures failure when schema missing ✅
  - Status: Accurate
- Claim: "Hook receipts include cache hit ratio" (docs/HOOKS_QUICK_REFERENCE.md)
  - Code: `HookReceipt` lacks `cache_hit_ratio` ❌
  - Tests: none ❌
  - Action: add metric or update docs
```

## 4. Capture Discrepancies

Produce a todo inventory (10+ if possible) with severity and owner hints:

```markdown
### High
- hooks/executor.py: docstring says sanitization happens before metrics; code does reverse.
- docs/UNRDF_PORTING_VALIDATION.md claims 8 patterns validated but missing lockchain writer proof.

### Medium
- tests/hooks/test_security.py names mention “async” but fixture is sync.
- CLI README references `--no-validate` flag that no longer exists.
```

## 5. Fix at the Source

1. Update code/doc/tests exactly where the discrepancy lives.
2. Maintain NumPy docstrings and strict typing.
3. Add/adjust Chicago School tests (no mocks of domain objects).
4. Re-run full gates:

```bash
poe format
poe lint
poe type-check
poe test
poe pre-commit-run
```

When the fix requires broader architectural work, open an explicit issue or backlog item referencing the Gemba notes.

## Anti-Patterns to Avoid

- Believing README statements without re-running tests.
- Copying logs from previous runs; always re-run in the current branch.
- Relying on print statements (banned) instead of receipts/tests.
- Editing docs without inspecting the code path they describe.

## References

- [80/20 Fill Gaps](./80-20-fill-gaps.md) – finish high-value capabilities found during the walk
- [Verify Tests](./verify-tests.md) – triage test failures discovered in Gemba
- [Root Cause Analysis](./root-cause-analysis.md) – when discrepancies expose deeper issues

