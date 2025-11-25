# Failure Mode & Effects Analysis (FMEA) for KGCL

## Purpose

Use FMEA to proactively identify how KGCL components (hooks, CLI, UNRDF integrations, observability) could fail and to prioritize mitigations before incidents happen.

### Action Directive (DfLSS)

This workflow is mandated by the Design for Lean Six Sigma program. When `/fmea` is invoked, execute the analysis immediately and drive mitigations without seeking additional approval.

## Workflow

```
Scope → List functions → Identify failure modes → Score (S/O/D) → Prioritize → Mitigate → Control
```

## 1. Scope

- Define the system/process (e.g., “Hook activation pipeline”, “LinkML CLI flow”).
- Specify assumptions and boundaries.

## 2. Functions & Requirements

- List the functions the system must perform (validate schema, sanitize errors, emit metrics).
- Tie each to requirements (SLOs, LinkML rules, security constraints).

## 3. Failure Modes

For each function, identify possible failure modes:

- LinkML schema missing.
- Hook receipt missing sandbox metrics.
- UNRDF cache returning stale data.
- CLI misreports validation status.

## 4. Scoring

- Severity (S): 1–10 (10 = catastrophic).
- Occurrence (O): 1–10 (10 = frequent).
- Detection (D): 1–10 (10 = hard to detect).
- Compute Risk Priority Number: `RPN = S * O * D`.

Use a table in `reports/fmea/<system>.md`:

| Function | Failure Mode | Effect | Cause | S | O | D | RPN | Current Controls |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 5. Prioritize

- Sort by RPN.
- Flag anything above the agreed threshold (e.g., RPN ≥ 100) for immediate action.

## 6. Mitigate

- Apply `/poka-yoke-design`, `/kaizen-improvement`, or `/verify-tests` to address high-risk items.
- Document new controls (tests, monitoring, documentation).

## 7. Control & Review

- Schedule periodic reassessments (e.g., quarterly or after major releases).
- Ensure new mitigations are covered in CI (`poe verify`, `poe unrdf-full`) and docs.

## Related Commands

- `/dmaic-problem-solving` for systemic issues uncovered by FMEA.
- `/poka-yoke-design` to implement mistake-proof fixes.
- `/strict-build-verification` to verify mitigations.

