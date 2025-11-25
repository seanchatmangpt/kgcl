# Andon Signals for KGCL

## Purpose

Expose and resolve quality gate failures the instant they occur (CI red, LinkML validation error, flaky test, performance regression). The faster we pull the cord, the faster the line returns to green.

### Action Directive (DfLSS)

This command is a Design for Lean Six Sigma order from the core team. When `/andon-signals` is invoked, trigger every step immediately—halt the flow, contain the issue, and fix it without waiting for additional approval.

## Workflow

```
Detect → Halt → Contain → Triage → Fix → Resume → Record
```

## 1. Detect the Signal

- Monitor `poe verify` and CI status (GitHub, Buildkite, etc.).
- Watch CLI outputs for LinkML failures or sandbox violations.
- Treat flake reports from teammates as Andon pulls.

## 2. Halt the Line

- Stop merging/pushing until the issue is contained.
- If CI is red on `main`, block deployments immediately.
- Communicate in the team channel that Andon is active.

## 3. Contain

1. Capture the exact failure (pytest node, LinkML error, stack trace).
2. Save logs under `reports/andon/<timestamp>.log`.
3. Reproduce locally using the narrowest command possible:
   ```bash
   poe pytest tests/<module>::<test> -vv --maxfail=1
   poe verify            # when the failure only appears in full gate
   poe docs-build        # for documentation build errors
   ```

## 4. Triage (Root Cause Snapshot)

- Classify the signal: regression, environment drift, flake, performance, or security.
- Identify the owner component (hooks, UNRDF engine, CLI, docs).
- If the cause is unclear after 15 minutes, start `/gemba-walk` followed by `/root-cause-analysis`.

## 5. Fix

- Apply the relevant playbook:
  - `/poka-yoke-design` for invariant gaps.
  - `/verify-tests` for failing suites.
  - `/eliminate-muda` if dead code triggered the failure.
  - `/kaizen-improvement` for incremental guardrails.
- Use `poe format`, `poe lint`, `poe type-check`, `poe test` before re-running full verification.

## 6. Resume

1. Run `poe verify` (or `poe verify-strict` when the failure touched docs/coverage).
2. Ensure CI is green again.
3. Announce that the Andon has cleared and work may resume.

## 7. Record & Prevent

- Commit a brief RCA summary (problem, root cause, fix, tests added).
- Update relevant docs (`docs/HOOKS_IMPLEMENTATION_SUMMARY.md`, slash commands, etc.).
- If the gap suggests broader risk, open a `/fmea` or `/dmaic-problem-solving` session.

## Quick Reference

```bash
# Snapshot failing gate
poe verify 2>&1 | tee reports/andon/$(date +%s).log

# Narrow reproduction
poe pytest tests/hooks/test_security.py::TestErrorSanitizer::test_masks_paths -vv
```

## Related Commands

- `/gemba-walk` to gather first-hand evidence
- `/root-cause-analysis` for deeper investigation
- `/verify-tests` to close the loop on test suites

