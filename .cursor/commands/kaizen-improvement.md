# Kaizen (Continuous Improvement) for KGCL

## Purpose

Kaizen = relentless, low-risk improvements that compound. Instead of rewriting whole subsystems, keep KGCL moving forward through tiny, verifiable upgrades that align with Chicago TDD, UNRDF parity, and strict lint gates.

### Action Directive (DfLSS)

This command is part of the Design for Lean Six Sigma toolkit. When `/kaizen-improvement` runs, implement the improvements immediately—no waiting for further authorization.

## Workflow

```
Identify → Plan → Do → Check → Standardize
```

## 1. Identify Improvement Opportunities

Criteria:
- Small enough for a single focused PR or commit.
- Improves clarity, safety, performance, or consistency.
- Can be validated by existing test suites.

Example categories:
- **Clarity**: Rename ambiguous variables, split 60-line functions, replace magic literals with typed constants.
- **Safety**: Add missing `ErrorSanitizer` coverage, enforce LinkML validation, freeze dataclasses.
- **Performance**: Cache repeated SPARQL queries, avoid redundant JSON serialization.
- **Consistency**: Align docstrings, import order, or hook lifecycle patterns.

Capture them:

```markdown
## Kaizen Backlog
- [ ] hooks/executor.py – extract repeated duration formatting helper
- [ ] docs/CLI_IMPLEMENTATION_SUMMARY.md – update to mention LinkML enforcement
- [ ] tests/hooks/conftest.py – share policy pack fixtures
```

## 2. Plan the Change

Fill a micro-plan:

```markdown
### Improvement Plan
- What: Replace repeated `"hook_execution"` literal with Enum HookPhase
- Why: Removes typo risk, improves type hints, matches UNRDF spec
- How: Introduce HookPhase(Enum), update pipeline + receipts + tests
- Risk: Low; ensure mypy + pytest cover all call sites
```

Stick to the smallest viable slice. If you uncover something bigger, log a new backlog item rather than expanding scope mid-stream.

## 3. Do (Implement)

Steps:
1. Write/adjust tests first when possible (Chicago TDD).
2. Implement the minimal change in source.
3. Keep docstrings and type hints in sync.

Example:

```python
# BEFORE
if phase == "RUN":
    metrics.append(("hook_execution", duration_ms))

# AFTER
class HookPhase(str, Enum):
    RUN = "RUN"
    POST = "POST"

if phase is HookPhase.RUN:
    metrics.append((HookPhase.RUN.value, duration_ms))
```

## 4. Check (Verify)

Run the full gate relevant to the change:

```bash
poe format
poe lint
poe type-check
poe test
```

Add specialized suites if touched:
- `poe unrdf-full` for UNRDF components
- `poe pytest tests/cli -vv` for CLI updates

Ensure the improvement actually provides value (readability, perf numbers, etc.). If there’s no measurable improvement, iterate or revert.

## 5. Act (Standardize + Share)

- Apply the same pattern wherever else it belongs (batch responsibly).
- Update docs/README/checklists so future contributors follow the upgraded standard.
- If tooling can enforce it (Ruff rule, pre-commit), add it.
- Mention the Kaizen change in the next retrospective or documentation log.

## Best Practices

1. **One improvement at a time** – keep diffs audit-friendly.
2. **Document intent** – short commit body describing the Kaizen rationale.
3. **Verify immediately** – never leave the codebase partially improved.
4. **Avoid speculative work** – improve what we actually use.
5. **Update references** – docs/tests/examples must reflect the new standard.

## Anti-Patterns

- Massive refactors justified as “cleanup.”
- Introducing TODOs instead of finishing the improvement.
- Skipping docs/tests because the change “is small.”
- Ignoring LinkML validation or sandbox constraints in the name of speed.

## References

- [Poka-Yoke Design](./poka-yoke-design.md) for type-safety guardrails
- [Eliminate Muda](./eliminate-muda.md) for waste removal ideas
- [Strict Build Verification](./strict-build-verification.md) for required checks

