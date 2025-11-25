## 80/20 Capability Inventory — 2025-11-25

### High-Signal Findings
- `src/kgcl/cli/query.py::_execute_query` – placeholder returns mock data, no real SPARQL execution or timeout enforcement.
- `src/kgcl/cli/daily_brief.py` – ingestion/materialization/DSPy stages marked TODO, so CLI cannot surface real operational data.
- `src/kgcl/cli/weekly_retro.py` – metric computation and DSPy integration are stubs, preventing production retrospectives.
- `src/kgcl/cli/feature_list.py` – SPARQL-backed feature discovery is unimplemented, limiting CLI usefulness.
- `src/kgcl/observability/tracing.py` – service metadata hard-coded; no version introspection for receipts/traces.
- `tests/apple_ingest/*` – broad swaths marked TODO, leaving ingest behavior largely unverified.
- `tests/integration/test_dspy_integration.py` and related DSPy suites heavily skipped when DSPy unavailable, masking regressions.
- `src/kgcl/hooks/orchestrator.py::_check_for_chaining` – simplistic trigger detection, no idempotency or phase metrics.
- `src/kgcl/ttl2dspy/generator.py` – template generator inserts literal `pass`, producing unusable code.

### Completed Remediations (2025-11-25)
- `src/kgcl/observability/health.py::check_graph_integrity` now performs rdflib-backed validation, namespace inspection, and SHA256 auditing instead of returning a static “passed” message.

### Categorization
- **Error Handling / Resilience**: `hooks/orchestrator.py`, `observability/health.py`.
- **Type Safety & Execution Fidelity**: CLI modules returning synthetic data (`daily_brief`, `weekly_retro`, `feature_list`, `query`).
- **Testing Coverage**: Apple ingest and DSPy suites marked TODO/skip.
- **Performance / Observability**: `observability/tracing.py`, missing metrics in CLI outputs.

### 80/20 Prioritization Matrix
| Capability | Impact | Effort | Notes |
| --- | --- | --- | --- |
| Real SPARQL execution in `kgc-query` | High | Medium | Unlocks truthful CLI + regression tests |
| Daily brief DSPy integration | High | High | Requires ingestion + DSPy orchestration |
| Weekly retrospective metrics | High | High | Same dependencies as daily brief |
| Feature list SPARQL backend | Medium | Medium | Shares primitives with `kgc-query` |
| Observability graph integrity checks | Medium | Low | Implement SHACL/rdflib validation |
| Tracing service metadata | Medium | Low | Derive version from package metadata |
| Hook chaining idempotency | High | Medium | Needs receipts + policy manager coordination |
| Apple ingest end-to-end tests | High | High | Substantial domain modeling effort |
| DSPy integration skips | Medium | Medium | Need hermetic DSPy harness |
| TTL2DSPy generator placeholders | Medium | Medium | Blocks auto-codegen SLO guarantees |

### Selected Focus (Current Pass)
Implement truthful SPARQL execution for `kgc-query` (CLI + tests). This unblocks multiple CLI surfaces (`kgc-query`, `kgc-feature-list`) and establishes the shared querying substrate needed before higher-effort DSPy automation.


