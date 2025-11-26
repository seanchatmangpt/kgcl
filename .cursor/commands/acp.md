# Add → Commit → Push (ACP) for KGCL

## Purpose

Guarantee that every change merged into KGCL is production-grade. This ACP flow wires in all required quality gates (format, lint, types, tests, docs, git hooks) before staging, committing, and pushing.

### Action Directive (DfLSS)

This workflow is a Design for Lean Six Sigma command from the core team. When `/acp` runs, perform every step autonomously until the push succeeds—no additional confirmation or questions.

## High-Level Flow

```
Validate → Fix → Re-validate → Stage → Commit → Push
```

## Step 1: Pre-Validation

Run the full verification stack before touching git.

```bash
uv sync --frozen
poe verify             # format-check + lint-check + type-check + pytest
poe pre-commit-run     # mirrors CI gates
```

Success criteria:
- Ruff clean (ALL rules except documented ignores)
- `poe type-check` passes with `strict = true`
- Pytest exits 0 with strict markers
- Docs untouched or updated when behavior changes

If anything fails, stop and go to Step 2.

## Step 2: Fix Issues (loop until green)

1. **Type errors**
   ```bash
   poe mypy -- src/ tests/ --show-error-codes
   ```
   - Add/adjust type hints, frozen dataclasses, Literal enums.
   - No `Any`, no implicit Optional.

2. **Lint violations**
   ```bash
   poe lint
   ```
   - Resolve Ruff feedback (imports, docstrings, security, complexity).
   - Remove debug prints, commented-out code, dead paths.

3. **Formatting**
   ```bash
   poe format
   ```
   - Enforces 100-char lines, 2-space indents, docstring formatting.

4. **Tests**
   ```bash
   poe test
   ```
   - Use Chicago School TDD patterns (see `expert-testing-patterns.md`).
   - Never mock domain objects; use real hooks/unrdf components.

Document stubborn failures in TODOs/issues but do not move forward with red checks.

## Step 3: Re-Validation

Re-run the exact commands from Step 1. No warnings, no flaky tests, no skipped gates.

```bash
poe verify
poe pre-commit-run
```

Only continue once everything is green twice in a row.

## Step 4: Stage Changes

```bash
git status
git add -A
git status
```

Validate that only intentional files are staged. Guardrails:
- No compiled artifacts (`__pycache__`, `.pytest_cache`)
- No generated data outside `examples/sample_outputs`
- Lock files staged when dependencies changed

## Step 5: Write Commit Message

Use Conventional Commit format:

| Change | Example |
| --- | --- |
| Hook/engine feature | `feat: enforce sandbox receipt metrics` |
| Bug fix | `fix: sanitize UNRDF error payloads` |
| Refactor | `refactor: collapse policy pack loader` |
| Tests only | `test: harden lockchain writer integration` |
| Docs | `docs: update CLI quickstart for LinkML enforcement` |
| Build/config | `chore: tighten pre-commit gate` |

Rules:
- Present tense, imperative tone.
- Describe the highest-impact change.
- Never use “WIP” or “tmp”.

## Step 6: Commit

```bash
git commit -m "<message>"
```

If hooks block the commit:
- Fix root cause (missing docstring, TODO, debug code).
- Re-run `.githooks/pre-commit`.

## Step 7: Push

```bash
git push
```

If push fails due to divergence:
1. `git fetch origin`
2. `git merge origin/<branch>` (never rebase per repo policy)
3. Re-run full validation (Step 1) on the merged result
4. Commit merge, push again

## End-to-End Example

```bash
uv sync --frozen
poe verify                          # fails lint
poe lint && poe format
poe verify                          # green
poe pre-commit-run                   # green
git add -A
git status
git commit -m "feat: record hook phase metrics"
git push
```

## Troubleshooting

- **Persistent mypy errors**: Introduce typed helper functions instead of ignoring; never bypass with `# type: ignore`.
- **Ruff complexity warnings**: Break down functions >40 lines or split classes exceeding 7 methods.
- **Flaky tests**: Reproduce locally with `poe pytest -vv --maxfail=1`; stabilize immediately or isolate with marker + follow-up issue.
- **Docs drift**: Update `docs/*.md` when behavior or CLI contract changes; failing to do so will break readiness reviews.

## Best Practices

1. Always run validation before staging.
2. Keep commits surgical; multiple logical changes require multiple commits.
3. Reference supporting docs/tests in commit body when helpful.
4. Never bypass hooks with `--no-verify`.
5. Tag TODOs only when accompanied by opened issues and explicit owners (rare).

This ACP flow is the minimum bar for getting code into KGCL. Treat it like production deployment every time.

