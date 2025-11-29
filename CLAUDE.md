# Claude Code Configuration - KGCL Research Library

## 🚨 CRITICAL RULES - READ FIRST

### ABSOLUTE PROHIBITIONS (ZERO TOLERANCE)

**NEVER do these - they destroy work:**

1. **NEVER use `git reset --hard`** - It's destructive and loses work
2. **NEVER move code to "planned/" or similar directories** - If asked to implement, IMPLEMENT the code
3. **NEVER delete stub files** - Implement them instead
4. **NEVER trust agent recommendations blindly** - Ask user before major changes
5. **NEVER make architectural decisions without user approval** - Moving 82 files is NOT "cleanup"

### What "Implement Stubs" Means

**"Implement implementation stubs" = WRITE THE ACTUAL CODE**

```python
# ❌ WRONG - Moving files away
git mv src/feature.py planned/feature.py  # This is NOT implementing!

# ❌ WRONG - Deleting code
rm src/feature.py  # This is NOT implementing!

# ✅ CORRECT - Writing the implementation
def calculate(x: int) -> int:
    """Calculate result."""
    return x * 2  # Actual implementation code
```

**If quality gates detect stubs, the solution is:**
- ✅ Write the implementation code
- ✅ Replace `pass` with real logic
- ✅ Implement the function/class properly
- ❌ NOT moving files
- ❌ NOT deleting code
- ❌ NOT creating "planned/" directories

### Git Safety

**FORBIDDEN git commands:**
- ❌ `git reset --hard` - Loses uncommitted work
- ❌ `git clean -fd` - Deletes untracked files
- ❌ `git checkout -- .` - Discards changes

**SAFE git commands:**
- ✅ `git status` - Check state
- ✅ `git diff` - See changes
- ✅ `git add` - Stage files
- ✅ `git commit` - Save work
- ✅ `git stash` - Temporarily save work (recoverable)

## Project Context

**Research library for YAWL workflow engine and RDF/N3 reasoning.** Production-ready YAWL implementation with 95% parity to Java YAWL v5.2.

## Quick Reference

### Execution Rules (CRITICAL)

**ALL Python execution MUST use `uv run`** - Pre-commit hook blocks direct `python` usage.

```bash
# ✅ CORRECT - MANDATORY
uv run poe format      # Ruff format (<5s)
uv run poe lint        # Ruff lint + fix (<10s)
uv run poe type-check  # Mypy strict (<15s)
uv run poe test        # Pytest (<1s per test)
uv run poe verify      # All checks (<30s)
uv run poe detect-lies # Find TODO/FIXME/stubs (<5s)
uv run python script.py # Run scripts
uv run pytest          # Run pytest

# ❌ FORBIDDEN
python script.py       # Uses system Python (may be 3.12)
pytest                 # Bypasses uv dependency management
```

**Dependencies:** Python 3.13+ required. Check PyPI for version support. Known incompatible: `toxiproxy-python` (≤3.12 only). Verify with `uv lock`.

### File Organization
```
src/kgcl/    # Source (typed)
tests/       # Chicago School TDD
docs/        # Documentation
examples/    # POCs (single-file, runnable)
scripts/     # Utilities
```
**Never save to root folder.**

---

## 🚨 Andon Signals & Definition of Done

**Andon Principle:** When problems appear, STOP immediately. Don't hide, ignore, or proceed with signals present.

**Signal Types:** 🔴 CRITICAL (test/type/import failures - STOP), 🟡 HIGH (lint warnings, missing docs, <80% coverage - investigate), 🟢 CLEAR (all pass - proceed).

**Verification:** `uv run poe verify` (all checks), `uv run poe test` (🔴), `uv run poe type-check` (🔴), `uv run poe lint` (🟡), `uv run poe detect-lies` (🔴).

**Workflow:** Monitor → Stop on signal → Fix root cause (no workarounds) → Verify cleared → Document exceptions.

**Forbidden:** Blanket `# type: ignore`/`# noqa`, `@pytest.mark.skip`, `git commit --no-verify`, `TODO: fix later`.

**Definition of Done Checklist:**
- [ ] 🔴 Tests: `uv run poe test` - all passing
- [ ] 🔴 Types: `uv run poe type-check` - 0 errors
- [ ] 🔴 Lint: `uv run poe lint` - 0 errors
- [ ] 🔴 Lies: `uv run poe detect-lies` - 0 TODO/FIXME/stubs
- [ ] 🟡 Coverage: 80%+ maintained
- [ ] 🟡 Docs: Public APIs have NumPy docstrings
- [ ] 🟡 Proof: Claims verified with tests/scripts

**ZERO TOLERANCE:** Cannot mark complete with signals present. Cannot bypass hooks. Cannot claim without proof.

---

## Code Standards

**Types:** 100% coverage - all params and returns typed. Use `| None` not `Optional`. Frozen dataclasses for value objects.

**Testing:** Chicago School TDD - tests FIRST, no mocking domain objects, AAA structure, 80%+ coverage, <1s runtime. **Prove the engine, not the script** - tests must fail when engine is broken, assert on engine state (RDF tokens, not Python counters), external services must influence control flow.

**Lint:** Ruff (120 char lines). See `pyproject.toml` for config.

**Docstrings:** NumPy style for all public APIs.

**Imports:** Absolute only - `from kgcl.module import X`, never `from ..module import X`.

---

## Forbidden Patterns

**Theater Code:** Tests must prove ENGINE behavior, not Python simulation. ThreadPoolExecutor ≠ WCP-2, loops ≠ WCP-3, logging ≠ cancellation, hash branching ≠ deferred choice, fire-and-forget ≠ coordination, in-memory ≠ persistence, domain data ≠ workflow, pattern IDs ≠ pattern enforcement. Name tests honestly.

**Implementation Lies:** `TODO/FIXME/HACK/WIP/STUB`, blanket `# noqa`/`# type: ignore`, `pass`/`...`/`raise NotImplementedError`, `assert True`. Pre-commit blocks these.

**Test Skipping:** `@pytest.mark.xfail`/`skipif` forbidden. If test needs dependency, install it. Only acceptable: platform-specific skips.

**Poe Tasks:** Never run scripts directly - create `poe` tasks in `pyproject.toml` for standardization, consistency, and traceability.

**Common Mistakes:** Use `uv run poe <task>` not direct commands, absolute imports not relative, proof scripts not code reading, fix issues not `--no-verify`, complete implementation not TODOs.

## 🔍 Proof Protocol (Gemba Walk + Anti-Lie Planning)

**BEFORE claiming X works or implementing a feature:**
1. List potential lies (theater code that looks real but isn't)
2. Write proof script in `examples/proof_x.py` demonstrating REAL behavior
3. Run script: `uv run python examples/proof_x.py` - show actual output
4. Test failure case - prove it fails when X is broken

**Lie Categories:** Persistence (in-memory ≠ disk), workflow control (loops ≠ sync), RDF/SPARQL (metadata ≠ control flow), event-driven (publish ≠ coordination), cancellation (logging ≠ abort), parallel (threads ≠ tokens), choice (deterministic ≠ external events), audit (lists ≠ PostgreSQL).

**Forbidden Claims Without Proof:** "Error handling works", "Persistence implemented", "WCP patterns supported", "RDF-driven", "RabbitMQ integration works" - all require executable proof scripts.

**Checklist:** Proof script exists, runnable, shows actual behavior (not mocked), observable output, fails when broken.

**Planning Template:**
```markdown
## Feature: [Name]
### Potential Lies
1. **Lie**: [Claim] → **Theater**: [Fake implementation] → **Proof**: [Test that fails if theater]
### Implementation Checklist
- [ ] Proof script: `examples/proof_[feature].py` (runnable, shows real behavior, fails when broken)
- [ ] Tests assert on ENGINE state, not script variables
```

## Git Hooks

```bash
git config core.hooksPath scripts/git_hooks
```

| Hook       | Speed   | Checks                            |
| ---------- | ------- | --------------------------------- |
| pre-commit | <10s    | Secrets, lies, format, basic lint |
| pre-push   | 30-120s | Full lint, mypy strict, all tests |

**Never bypass with `--no-verify`.**

**POCs:** When exploring, create complete working files in `examples/` - self-contained, runnable, no TODOs/stubs.

---

## UNRDF Porting

8 patterns to port from JavaScript:
1. Hook Executor (timeout, phases, error sanitization)
2. Condition Evaluator (8 types, file resolution)
3. Error Sanitizer
4. Sandbox Restrictions
5. Performance Optimizer (latency, SLO)
6. Query Cache (TTL/LRU)
7. Policy Pack Manager
8. Lockchain Writer

**Targets:** p99 <100ms for all operations. Use frozen dataclasses, full types, Chicago School TDD.

---

## 🍖 Dogfooding Policy

**ALWAYS test KGCL using its own installed version, NOT development artifacts.**

```bash
# ❌ WRONG - Don't use for validation
uv run python -m kgcl.cli test
python src/kgcl/cli.py

# ✅ CORRECT - Use installed package
pip install -e .
kgcl test  # Or whatever the CLI command is
```

**Rationale**: Validates production installation path, not development shortcuts.

**Verification workflow:**
1. Install package: `pip install -e .` or `uv pip install -e .`
2. Test installed CLI/package (NOT source files directly)
3. Verify imports work from installed package location
4. Ensure entry points and console scripts work


## 🤖 AI Assistant Guidelines

**DO:** Run `uv run poe verify` before commits, use `uv run poe <task>` for execution, Chicago School TDD (tests first), proof scripts for claims, frozen dataclasses, NumPy docstrings, batch operations, assert on engine state.

**DON'T:** Skip tests, claim without proof, run Python directly, create root files, mark complete with signals, write theater code, use relative imports, skip verification, claim by reading code, blanket suppressions.

---

## Agents & Orchestration

### Available Agents (54 Total)

**Core:** `coder`, `reviewer`, `tester`, `planner`, `researcher`

**Swarm:** `hierarchical-coordinator`, `mesh-coordinator`, `adaptive-coordinator`, `collective-intelligence-coordinator`, `swarm-memory-manager`

**Consensus:** `byzantine-coordinator`, `raft-manager`, `gossip-coordinator`, `consensus-builder`, `crdt-synchronizer`, `quorum-manager`, `security-manager`

**Performance:** `perf-analyzer`, `performance-benchmarker`, `task-orchestrator`, `memory-coordinator`, `smart-agent`

**GitHub:** `github-modes`, `pr-manager`, `code-review-swarm`, `issue-tracker`, `release-manager`, `workflow-automation`, `project-board-sync`, `repo-architect`, `multi-repo-swarm`

**SPARC:** `sparc-coord`, `sparc-coder`, `specification`, `pseudocode`, `architecture`, `refinement`

**Specialized:** `backend-dev`, `mobile-dev`, `ml-developer`, `cicd-engineer`, `api-docs`, `system-architect`, `code-analyzer`, `base-template-generator`

**Testing:** `tdd-london-swarm`, `production-validator`

**Migration:** `migration-planner`, `swarm-init`

### Claude Code vs MCP Tools

| Claude Code (EXECUTION) | MCP Tools (COORDINATION) |
| ----------------------- | ------------------------ |
| Task tool spawns agents | swarm_init, agent_spawn  |
| File operations         | task_orchestrate         |
| Bash commands           | memory_usage             |
| Code generation         | neural_train             |
| Git operations          | GitHub integration       |

**KEY:** MCP coordinates strategy, Claude Code's Task tool executes with real agents.

### MCP Setup
```bash
claude mcp add claude-flow npx claude-flow@alpha mcp start
```

### Agent Execution Pattern

**GOLDEN RULE:** 1 message = ALL related operations

```javascript
// Single message - parallel agent execution
[Single Message]:
  Task("Research", "Analyze requirements...", "researcher")
  Task("Coder", "Implement features...", "coder")
  Task("Tester", "Create tests...", "tester")

  TodoWrite { todos: [...10 todos...] }

  Write "src/feature.py"
  Write "tests/test_feature.py"
```

### Agent Coordination Protocol

**BEFORE:** `npx claude-flow@alpha hooks pre-task --description "[task]"`
**DURING:** `npx claude-flow@alpha hooks post-edit --file "[file]"`
**AFTER:** `npx claude-flow@alpha hooks post-task --task-id "[task]"`

### Hooks Integration

| Pre-Operation      | Post-Operation | Session            |
| ------------------ | -------------- | ------------------ |
| Auto-assign agents | Auto-format    | Generate summaries |
| Validate commands  | Train patterns | Persist state      |
| Prepare resources  | Update memory  | Track metrics      |

---

## Reminders

- Do what was asked; nothing more, nothing less
- Never create files unless necessary
- Prefer editing existing files
- Never save to root folder
- Never create docs unless requested


DO NOT CHANGE DEPENDENCIES UNLESS DIRECTLY ASKED TO DO SO.