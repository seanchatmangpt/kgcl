# Robust Design (Taguchi) for KGCL

## Purpose

Design KGCL features that remain stable under noise: variable input schemas, inconsistent hook payloads, fluctuating resource limits, or noisy networks. Robust design ensures performance and correctness stay within SLOs even when conditions drift.

### Action Directive (DfLSS)

Issued under the Design for Lean Six Sigma initiative: when `/robust-design` is invoked, run the following steps immediately and implement the selected controls without waiting for approval.

## Workflow

```
Define response → Identify control/noise factors → Plan experiments → Optimize → Lock in controls
```

## 1. Define the Response

- Choose the critical metric (e.g., hook execution p95 latency, LinkML validation success rate, receipt completeness).
- Set the target and acceptable variance.
- Document in `reports/robust/<feature>/define.md`.

## 2. Identify Factors

| Type | Examples |
| --- | --- |
| Control factors | Cache TTL, LinkML pre-validation, async concurrency, retry counts |
| Noise factors | Input size, schema complexity, network jitter, file system latency |

List each factor and expected ranges.

## 3. Design Experiments

- Use orthogonal arrays or a simple factorial matrix to cover combinations.
- Automate scenarios via pytest parametrization or dedicated scripts.
- Capture metrics with `src/kgcl/workflow/metrics.py` or custom logging.

## 4. Run & Analyze

```bash
poe pytest tests/hooks/test_performance.py -vv --maxfail=1
poe pytest tests/integration -vv -m performance
```

- Calculate mean/variance for each configuration.
- Identify settings that minimize variance while meeting the target.

## 5. Optimize & Implement

- Update code/configs (e.g., adjust cache TTL, introduce staged validation).
- Add automated guards (pytest assertions, LinkML rules, receipts).
- Run `poe verify-strict` to ensure stability.

## 6. Control

- Document chosen settings in `docs/HOOKS_IMPLEMENTATION_SUMMARY.md` or relevant design notes.
- Add monitoring dashboards/alerts if performance drifts.
- Schedule periodic robustness tests (e.g., monthly stress suite).

## Related Commands

- `/poka-yoke-design` to encode invariants discovered here.
- `/verify-tests` to formalize robustness tests.

