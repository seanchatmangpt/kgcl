# Release Preparation for KGCL

## Purpose

Ensure every KGCL release candidate is production-ready: code, docs, tests, observability, and compliance artifacts must all pass before tagging.

### Action Directive (DfLSS)

This command comes directly from the Design for Lean Six Sigma initiative. When `/release-preparation` is invoked, execute the checklist immediately and autonomously—no exceptions.

## Workflow

```
Stabilize branch → Run quality gates → Verify docs & artifacts → Final checks → Tag & communicate
```

## 1. Stabilize Branch

- Ensure PR queue is empty or explicitly deferred.
- Merge `main` into the release branch (no rebases on shared branches).
- Confirm clean working tree: `git status -sb`.

## 2. Quality Gates

```bash
poe format-check
poe lint-check
poe type-check
poe test
poe verify-strict          # includes coverage + docs
poe unrdf-full             # mandatory for UNRDF patterns
```

All commands must pass with documented output (store logs in `reports/release/<version>/`).

## 3. Docs & Observability

- `poe docs-build` (and `poe docs-serve` for spot checks).
- Confirm changelog, README, and `docs/UNRDF_PORTING_VALIDATION.md` reflect the release.
- Verify observability dashboards and alert configs reference the new version.

## 4. Compliance & Operational Checks

- LinkML validation defaults intact (no hidden flags).
- Sandbox restrictions and receipts audited (`tests/hooks/test_security.py`).
- Security scans: `poe audit`.
- Ensure `.githooks/pre-commit` installed and passing.

## 5. Final Steps

1. Bump version via commitizen or manual edit + `poe format`.
2. `poe release-check`.
3. Tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`.
4. Push: `git push && git push --tags`.
5. Publish release notes (use `poe release-notes` as a template).

## Checklist

- [ ] Branch stable and merged with `main`
- [ ] All uv scripts above passed
- [ ] Docs built and verified
- [ ] Observability updated
- [ ] Security checks cleared
- [ ] Version bumped and tagged
- [ ] Release notes published

## Related Commands

- `/strict-build-verification` (embedded in the quality gates)
- `/verify-unrdf-porting` for the pattern checklist

