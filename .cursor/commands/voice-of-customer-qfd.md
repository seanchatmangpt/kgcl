# Voice of Customer (QFD) for KGCL

## Purpose

Translate stakeholder needs (operators, data scientists, compliance, platform teams) into concrete KGCL technical requirements using a lightweight House of Quality.

### Action Directive (DfLSS)

This is a Design for Lean Six Sigma command. When `/voice-of-customer-qfd` runs, gather input, build the matrix, and derive prioritized requirements immediately—no extra approvals.

## Workflow

```
Gather VOC → Translate to CTQs → Build House of Quality → Analyze → Feed downstream
```

## 1. Gather VOC

- Interview or survey stakeholders (CLI users, hook authors, UNRDF integrators).
- Pull recent bug reports or feature requests.
- Capture needs verbatim and cluster similar statements.

## 2. Translate to Critical-to-Quality (CTQ) Requirements

- Convert each VOC statement into measurable requirements (e.g., “CLI must fail fast when LinkML schema missing”, “Hook execution p99 < 80ms”).
- Note owner (hooks, CLI, UNRDF, docs).

## 3. Build House of Quality

Create a table in `reports/qfd/<initiative>.md`:

| VOC Need | Weight | Requirement A (LinkML enforcement) | Requirement B (Observability) | Requirement C (UNRDF cache) |
| --- | --- | --- | --- | --- |
| Schema safety | 5 | 9 | 1 | 1 |
| Fast CLI feedback | 3 | 3 | 3 | 1 |
| Traceability | 4 | 1 | 9 | 3 |

- Use standard QFD scoring (9 = strong, 3 = medium, 1 = weak).
- Sum weighted scores per requirement to get priorities.

## 4. Analyze

- Highlight top-scoring technical requirements.
- Identify conflicts (e.g., safety vs. speed) and feed them into `/triz-problem-solving`.
- Assign owners and timelines.

## 5. Feed Downstream

- Pass requirements to `/concept-selection`, `/robust-design`, or `/dmaic-problem-solving`.
- Update docs/roadmaps so everyone sees the prioritized needs.

## Related Commands

- `/concept-selection` for deciding between solution options.
- `/dmaic-problem-solving` when VOC uncovers chronic quality issues.




