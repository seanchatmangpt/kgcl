# TRIZ Problem Solving for KGCL

## Purpose

Apply TRIZ (Theory of Inventive Problem Solving) when KGCL faces a contradiction—e.g., enforcing LinkML validation without hurting CLI speed, strengthening sandbox limits without blocking observability, or preserving UNRDF accuracy while cutting resource usage.

### Action Directive (DfLSS)

This command is a standing Design for Lean Six Sigma order. When `/triz-problem-solving` is invoked, follow the steps end-to-end immediately and independently.

## Workflow

```
Frame contradiction → Map to TRIZ principles → Generate options → Evaluate → Implement & test
```

## 1. Frame the Contradiction

- Describe the desired improvement (e.g., “faster hook activation”).
- Describe what worsens when you attempt it (e.g., “loss of LinkML safety”).
- Identify who/what is affected (hooks, CLI, UNRDF pipeline).

Document in `reports/triz/<issue>/problem.md`.

## 2. Map to TRIZ Principles

- Use the classic contradiction matrix or team heuristics to pick 2–3 relevant principles (e.g., Separation in Time, Nested Doll, Prior Action).
- Note why each principle applies to KGCL’s context.

## 3. Generate Options

For each principle, brainstorm concrete design ideas:

- Pre-validate LinkML schemas during install (Prior Action).
- Cache sanitized receipts while reusing immutable dataclasses (Nested Doll).
- Run heavy SPARQL checks asynchronously after returning provisional CLI output (Separation in Time).

Capture options and quick effort/impact estimates.

## 4. Evaluate

- Prototype or spike key ideas.
- Use `/verify-tests` and `poe verify` to measure correctness/impact.
- If multiple options remain viable, run `/concept-selection` (Pugh matrix) to pick the best one.

## 5. Implement & Test

- Convert the winning concept into production code (full type hints, docstrings, Chicago tests).
- Run `poe format`, `poe lint`, `poe type-check`, `poe test`, and `poe verify-strict`.
- Update docs and slash commands if the pattern becomes standard.

## Artefacts

Store TRIZ notes in `reports/triz/<issue>/`:

- `problem.md`
- `principles.md`
- `options.md`
- `decision.md`

## Related Commands

- `/concept-selection` to compare options
- `/poka-yoke-design` for implementing the chosen idea safely
- `/dmaic-problem-solving` when the contradiction is part of a broader quality effort

