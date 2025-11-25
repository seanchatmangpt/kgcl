# Eliminate Mura (Unevenness) in KGCL

## Purpose

Mura = inconsistency. In KGCL it shows up as divergent hook lifecycles, inconsistent LinkML handling, type hints that vary across modules, or docs that disagree with implementation. This workflow enforces one way of doing things everywhere.

### Action Directive (DfLSS)

Issued by the core team’s Design for Lean Six Sigma initiative: when `/eliminate-mura` is triggered, carry out the standardization steps immediately and independently, with no additional approval.

## Workflow

```
Identify → Measure → Standardize → Apply → Control
```

## Step 1: Identify Unevenness

Scan for the following categories:

1. **Style**  
   - Files missing Ruff-formatted 2-space indentation, trailing commas, or NumPy docstrings.
   - Mixed import styles (some relative, some absolute).

2. **Pattern**  
   - Hook phases implemented differently per module.  
   - Some CLI commands enforce LinkML, others skip.

3. **Quality**  
   - Tests for hooks but not for CLI surfaces.  
   - Some dataclasses frozen, others mutable.

4. **Complexity**  
   - Two similar pipelines, one simple, one layered with factories.  
   - Duplicate RDF parsing logic with diverging code paths.

5. **Documentation**  
   - Docstrings missing sections.  
   - Guides referencing removed behaviors.

Create a structured inventory:

```markdown
## Mura Inventory
- Style: src/kgcl/hooks/executor.py uses relative imports
- Pattern: CLI ingest path runs LinkML validation; export path skips it
- Quality: tests/hooks/test_policy_packs.py has coverage, tests/cli/test_cli.py missing cases
- Documentation: docs/CLI_QUICKSTART.md lacks new sandbox switches
```

## Step 2: Measure Variability

Use tooling to quantify gap size:

```bash
poe format-check           # style drift
poe lint-check             # Ruff pattern violations
poe test -- --maxfail=1    # look for modules lacking coverage
poe type-check             # strict typing differences
```

Collect metrics:
- Count of Ruff violations per module
- mypy error counts by package
- Coverage deltas (pytest + `coverage xml`)
- Docstring completeness (D* rules in Ruff)

## Step 3: Standardize

Select the canonical approach for each inconsistency:

```markdown
### Hook Error Handling
Standard: funnel all errors through kgcl.hooks.security.ErrorSanitizer before logging or receipts.
Migration: touch every HookExecutionPipeline variant.

### CLI Validation
Standard: LinkML validation on by default with no flags to disable.
Migration: update CLI entry + tests + docs.
```

Rules of thumb:
- Favor the pattern already documented in `docs/HOOKS_IMPLEMENTATION_SUMMARY.md`.
- If two patterns exist, choose the one with tighter type hints/tests.
- Document the decision in docs + commit messages.

## Step 4: Apply Consistently

Execution steps:
1. Update code to follow the chosen pattern.
2. Add/adjust tests demonstrating the standard.
3. Update docs (CLI quickstart, UNRDF guides, etc.).
4. Re-run validation.

Example:

```python
# BEFORE
from .errors import HookError

def execute(hook, event):
    ...

# AFTER
from kgcl.hooks.errors import HookError

def execute(hook: Hook, event: HookEvent) -> HookReceipt:
    """Execute hook with sanitized receipts."""
    ...
```

Validation:

```bash
cargo-make format
cargo-make lint
cargo-make type-check
cargo-make test
```

## Step 5: Control

Embed guardrails so variance cannot creep back:
- Ruff `B` rules for security, `I` rules for import style.
- mypy strict configuration (already enforced) plus targeted `py.typed` exports.
- Pre-commit hook requiring docstrings on all public APIs.
- Code review checklist item: “Matches documented hook pattern?”
- Reference this playbook + decisions in `kaizen-improvement.md`.

## Example Outcome

```markdown
### Unevenness Removed
- Hook receipts now all instantiate HookReceipt via HookExecutionPipeline builder.
- All CLI commands enforce LinkML validation and test coverage increased from 70% → 96%.
- Docs updated to describe sandbox phases uniformly.

### Controls
- Added Ruff rule S608 guard to block unsafe subprocess patterns.
- Added regression tests to tests/integration/test_unrdf_porting.py.
```

## References

- [Eliminate Muda](./eliminate-muda.md) for removing waste after standardization
- [Kaizen Improvement](./kaizen-improvement.md) to record the new standard
- [Strict Build Verification](./strict-build-verification.md) for validation commands

