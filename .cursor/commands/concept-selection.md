# Concept Selection (Pugh Matrix) for KGCL

## Purpose

When multiple design options compete (e.g., new hook orchestration flow, LinkML enforcement strategy, observability pipeline), use this command to evaluate them objectively and pick the best fit for KGCL.

### Action Directive (DfLSS)

This is a Design for Lean Six Sigma execution order. Once `/concept-selection` is invoked, complete the evaluation autonomously and move forward with the chosen concept.

## Workflow

```
Define criteria → Choose baseline → Score concepts → Analyze sensitivities → Select & proceed
```

## 1. Define Criteria

- Derive requirements from VOC, SLOs, UNRDF parity, security needs.
- Example criteria: LinkML safety, execution latency, implementation effort, test coverage impact, observability support.
- Weight criteria if necessary (sum to 1.0).

## 2. Choose Baseline

- Pick the current approach or simplest viable concept as the baseline (“0” scores).
- Each alternative is scored relative to this baseline.

## 3. Score

Create a table in `reports/concept-selection/<decision>.md`:

| Concept | LinkML Safety | Latency | Effort | Testability | Observability | Total |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline | 0 | 0 | 0 | 0 | 0 | 0 |
| Option A | +1 | -1 | +2 | +1 | 0 | +3 |
| Option B | +2 | +1 | -2 | +2 | +1 | +4 |

- Use +1 (better), 0 (same), -1 (worse) or a weighted numeric scheme.
- Multiply by weights if applicable.

## 4. Analyze

- Identify dominant options and trade-offs.
- Run sensitivity checks by adjusting weights or removing low-value criteria.
- Validate assumptions through quick spikes/tests when uncertain.

## 5. Select & Proceed

- Document the winning concept and rationale.
- Kick off `/poka-yoke-design`, `/verify-tests`, or `/robust-design` to implement.
- Update docs and stakeholders with the decision summary.

## Related Commands

- `/voice-of-customer-qfd` to gather criteria from stakeholders.
- `/triz-problem-solving` when contradictions remain.




