# KGCL Slash Commands

These commands encode the workflows we run inside Cursor for the KGCL repository. Each one assumes:

- Chicago School TDD (real hooks/engines, no mocked domain objects)
- `uv` + `poe` build tooling
- Strict Ruff + mypy settings from `pyproject.toml`
- LinkML validation always enabled for the CLI

### DfLSS Action Mandate

Every slash command is an execution order from the core team’s Design for Lean Six Sigma initiative. When a command is invoked, carry out all listed steps immediately—no confirmation, no “may I?” questions.

## Available Commands

| Command | Summary |
| --- | --- |
| `/80-20-fill-gaps` | Scan the repo, find the top 20% of unfinished capabilities, finish + validate them. |
| `/andon-signals` | Pull the cord on failing quality gates and resolve immediately. |
| `/acp` | Add → Commit → Push with full pre-flight (format, lint, types, tests, hooks). |
| `/concept-selection` | Use a Pugh matrix to compare design options objectively. |
| `/dmaic-problem-solving` | Run the full Define–Measure–Analyze–Improve–Control cycle. |
| `/eliminate-muda` | Remove waste: dead code, duplicate logic, unused deps, redundant IO. |
| `/eliminate-mura` | Standardize patterns (imports, hook lifecycles, docstrings, LinkML enforcement). |
| `/expert-testing-patterns` | Apply KGCL testing heuristics (error paths, boundary phases, receipts). |
| `/fix-lint-errors` | Systematic flow for clearing Ruff + mypy violations. |
| `/gemba-walk` | “Go see” actual code/tests/CLI behavior before making decisions. |
| `/kaizen-improvement` | PDCA loop for tiny, low-risk improvements that compound. |
| `/poka-yoke-design` | Mistake-proof APIs via frozen dataclasses, enums, typed factories. |
| `/release-preparation` | Final release checklist before tagging/publishing. |
| `/root-cause-analysis` | 5-Whys + containment to stop regressions. |
| `/robust-design` | Taguchi-style resilience against noise factors. |
| `/strict-build-verification` | Full build/type/test/docs gate before merge. |
| `/triz-problem-solving` | Resolve design contradictions with TRIZ heuristics. |
| `/verify-tests` | Diagnose + stabilize failing Chicago tests. |
| `/verify-unrdf-porting` | Reconfirm all eight UNRDF patterns stay green. |
| `/voice-of-customer-qfd` | Convert stakeholder needs into technical requirements. |
| `/fmea` | Proactively rank failure modes and mitigations. |

## Command Families

- **Improvement**: `/80-20-fill-gaps`, `/kaizen-improvement`, `/eliminate-muda`, `/eliminate-mura`
- **Quality Gates**: `/strict-build-verification`, `/acp`, `/fix-lint-errors`, `/release-preparation`
- **Reliability & Safety**: `/poka-yoke-design`, `/verify-tests`, `/verify-unrdf-porting`, `/fmea`, `/robust-design`
- **Problem Solving**: `/gemba-walk`, `/root-cause-analysis`, `/andon-signals`, `/dmaic-problem-solving`, `/triz-problem-solving`
- **Discovery & Design**: `/voice-of-customer-qfd`, `/concept-selection`
- **Testing Craft**: `/expert-testing-patterns`

## Usage Patterns

- **Bug investigation**: `/gemba-walk` → `/root-cause-analysis` → `/poka-yoke-design` → `/verify-tests`
- **Capability completion**: `/80-20-fill-gaps` → `/kaizen-improvement` → `/strict-build-verification`
- **Release readiness**: `/fix-lint-errors` + `/strict-build-verification` + `/verify-unrdf-porting` before `/acp`
- **Code health**: `/eliminate-muda` + `/eliminate-mura` keep modules consistent with docs/tests

## Build & Test Expectations

- Always run `poe format`, `poe lint`, `poe type-check`, `poe test`
- Use `poe unrdf-full` when UNRDF code is touched
- `poe type-check` must pass with `strict = true`
- Pytest runs with `--strict-markers` and doctests enabled
- CLI changes must keep LinkML validation mandatory

## Contributing New Commands

1. Follow the structure (Purpose → Workflow → Steps → Examples → Best practices).
2. Reference KGCL paths and tooling (e.g., `src/kgcl/hooks/**`, `poe` tasks).
3. Tie into Chicago TDD + UNRDF rules where relevant.
4. Update this README with a concise description once the command is added.

