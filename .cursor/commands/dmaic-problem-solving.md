# DMAIC Problem Solving for KGCL

## Purpose

Use Define–Measure–Analyze–Improve–Control to drive systemic fixes when a KGCL capability drifts (e.g., hook latency exceeds SLO, UNRDF sync regresses, CLI validation gaps). DMAIC keeps the response data-driven and auditable.

### Action Directive (DfLSS)

This is a core Design for Lean Six Sigma command. When `/dmaic-problem-solving` is triggered, run every phase immediately and autonomously—no waiting for extra confirmation.

## Workflow

```
Define → Measure → Analyze → Improve → Control
```

## 1. Define

- State the exact issue (What/Where/When/Impact).
- Identify stakeholders (hook owners, CLI maintainers, integrations).
- Set a target (e.g., “Reduce hook timeout failures from 8% to <0.5%”).

## 2. Measure

Collect current-state data:

- Test/CI logs (`reports/pytest.log`, `reports/mypy.xml`).
- Performance metrics (`src/kgcl/workflow/metrics.py`, receipts).
- LinkML validation reports.
- Use `poe verify` or targeted suites to reproduce and log baseline numbers.

Document measurements in `reports/dmaic/<issue>/measure.md`.

## 3. Analyze

- Perform `/root-cause-analysis` or `/andon-signals` triage.
- Identify patterns: failing pytest nodes, specific policies, schema versions.
- Map causes to contributing processes (e.g., missing Poka-Yoke, absent tests, docs drift).

## 4. Improve

- Design countermeasures:
  - Poka-yoke guardrails (typed helpers, LinkML enforcement).
  - Performance optimizations (cache tuning, async improvements).
  - Documentation clarifications or CLI UX tweaks.
- Implement with `poe format/lint/type-check/test`.
- Validate improvements via `/verify-tests` and `/strict-build-verification`.

## 5. Control

- Add monitors (metrics, logging, docs) to detect relapse.
- Update playbooks/slash commands with the new standard.
- Schedule follow-up checks (e.g., weekly `poe verify-strict`, new CI job).

## Artifacts

Create a `reports/dmaic/<issue>/` folder containing:

- `define.md`
- `measure.md`
- `analyze.md`
- `improve.md`
- `control.md`

Each file should capture data, decisions, and links to PRs/tests.

## Related Commands

- `/gemba-walk` for firsthand observation
- `/root-cause-analysis` for the Analyze phase
- `/poka-yoke-design` to harden the Improve phase

