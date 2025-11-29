# Claude Code Configuration - KGCL Research Library

## Project Context

**Research library for YAWL workflow engine and RDF/N3 reasoning.** Production-ready YAWL implementation with 95% parity to Java YAWL v5.2.

## Quick Reference

### Commands (MUST use `uv run poe`)
```bash
uv run poe format      # Ruff format
uv run poe lint        # Ruff lint + fix
uv run poe type-check  # Mypy strict
uv run poe test        # Pytest
uv run poe verify      # All checks
uv run poe detect-lies # Find TODO/FIXME/stubs
```

**CRITICAL**: NEVER use `poe` directly - ALWAYS prefix with `uv run`

### Performance SLAs (Targets)

| Operation | Target | Context |
|-----------|--------|---------|
| `uv run poe format` | <5s | Quick validation |
| `uv run poe lint` | <10s | Full ruff check |
| `uv run poe type-check` | <15s | Mypy strict |
| `uv run poe test` | <1s per test | Individual timeout |
| `uv run poe verify` | <30s | Complete validation |
| `uv run poe detect-lies` | <5s | Pattern search |

### Python Execution: NEVER use `python` directly

**🔴 CRITICAL ENFORCEMENT: ALL Python execution MUST use `uv`**

```bash
# ✅ CORRECT - MANDATORY patterns
uv run python script.py       # Run script (REQUIRED)
uv run pytest                 # Run pytest (REQUIRED)
uv run poe test               # Run poe tasks (REQUIRED)

# ❌ FORBIDDEN - Inconsistent execution
python script.py              # 🔴 SIGNAL - uses system Python
python3 script.py             # 🔴 SIGNAL - bypasses uv
pytest                        # 🔴 SIGNAL - might use wrong Python
python -m pytest              # 🔴 SIGNAL - bypasses dependency management
./script.py                   # 🔴 SIGNAL - uses shebang, not uv
```

**Why Strict Enforcement:**
- `uv` guarantees Python 3.13+ (project requirement)
- `uv` ensures project dependencies are available
- Inconsistent usage causes "works on my machine" failures
- System Python may be 3.12 or older (incompatible)

**Pre-commit hook BLOCKS direct `python` usage** - Andon signal for inconsistent execution.

### Dependency Rules: Python 3.13+ Required

**All dependencies MUST support Python 3.13.** The project uses `requires-python = ">=3.13,<4.0"`.

When adding dependencies:
1. Check PyPI for Python version support (classifiers or `requires-python`)
2. If a library doesn't list Python 3.13, check its GitHub for recent releases
3. **DO NOT add libraries that only support Python ≤3.12**

**Known incompatible libraries (DO NOT USE):**
- `toxiproxy-python` - only supports Python ≤3.12

**Verification:**
```bash
# uv will fail if any dependency doesn't support Python 3.13
uv lock  # Must succeed without resolution errors
```

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

## 🚨 CRITICAL: Andon Signals (Stop the Line)

**Andon Principle** (from Toyota Production System): When problems appear, STOP immediately. Don't hide signals, don't ignore them, don't proceed with them present.

### Signal Types

| Signal | Severity | Triggers | Action |
|--------|----------|----------|--------|
| **🔴 CRITICAL** | Must stop | Test failures, import errors, type errors | STOP - fix before proceeding |
| **🟡 HIGH** | Should stop | Ruff warnings, missing docstrings, <80% coverage | Investigate immediately |
| **🟢 CLEAR** | Continue | All checks pass | Proceed with work |

### Signal Verification Commands

```bash
# Check all signals before marking work complete
uv run poe verify          # Runs all checks: lint, type-check, test
uv run poe detect-lies     # Check for TODO/FIXME/stubs/placeholders

# Individual signal checks
uv run poe test            # 🔴 CRITICAL - All tests must pass
uv run poe type-check      # 🔴 CRITICAL - No mypy errors
uv run poe lint            # 🟡 HIGH - No ruff errors
```

### Signal Workflow (MANDATORY)

1. **Monitor**: Run `uv run poe verify` before claiming completion
2. **Stop**: When signal appears (red/yellow), immediately STOP
3. **Fix**: Address root cause - no workarounds, no suppression comments
4. **Verify**: Re-run checks - signal MUST clear before continuing
5. **Document**: If suppression needed, add justification in commit message

### Forbidden Signal Violations

```python
# ❌ FORBIDDEN - Hiding signals
# type: ignore   # Blanket suppression
# noqa          # Blanket suppression
@pytest.mark.skip("broken")  # Hiding test failures

# ❌ FORBIDDEN - Bypassing signals
git commit --no-verify       # Skipping pre-commit hooks
# TODO: fix this later       # Deferring obvious errors

# ✅ REQUIRED - Clear signals properly
def typed_function(x: int) -> str:  # Full type hints
    """Documented function."""       # Required docstring
    result = str(x)
    assert len(result) > 0           # Meaningful assertion
    return result
```

**ZERO TOLERANCE**: Cannot mark work complete while signals are present. Cannot bypass hooks. Cannot suppress without justification.

---

## Code Standards

### Types: 100% Coverage Required
```python
# Every function: typed params + return type
def process(data: dict[str, Any]) -> list[str]: ...

# Use | None, not Optional
def fetch(path: str, default: str | None = None) -> str: ...

# Inner functions need types too
def outer(items: list[str]) -> int:
    def inner(x: str) -> bool: return len(x) > 0
    return sum(1 for i in items if inner(i))

# Frozen dataclasses for value objects
@dataclass(frozen=True)
class Receipt:
    execution_id: str
    hook_id: str
    result: bool
```

### Testing: Chicago School TDD
- Write tests FIRST
- No mocking domain objects
- AAA structure (Arrange/Act/Assert)
- 80%+ coverage, <1s total runtime
- Verify behavior, not `assert result` / `assert True`

### Testing: Prove the Engine, Not the Script
1. **A test that passes without the engine running is worthless.** If you can delete the workflow engine and tests still pass, you tested Python, not the system.
2. **The test must fail when the pattern is violated.** If WCP-3 sync test passes when only 2 of 3 branches complete, it's not testing synchronization.
3. **Assert on engine state, not script variables.** Check RDF token positions, not Python counters you incremented yourself.
4. **External services must influence control flow.** If RabbitMQ messages don't change which code path executes, the test proves nothing about event-driven behavior.
5. **If you wrote the behavior in the test, you're testing your test.** The engine must produce the behavior; the test must only observe and assert.

### Lint: Ruff (120 char lines)
Real errors enforced; style preferences (E501, PLR complexity) caught by tests. See `pyproject.toml` for full config.

### Docstrings: NumPy Style
```python
def execute(hook: Hook, event: dict[str, Any]) -> Receipt:
    """Execute hook against event.

    Parameters
    ----------
    hook : Hook
        Hook definition
    event : dict[str, Any]
        Triggering event

    Returns
    -------
    Receipt
        Execution result
    """
```

### Imports: Absolute Only
```python
from kgcl.hooks.core import Hook  # Correct
from ..hooks.core import Hook     # WRONG
```

---

## Forbidden Patterns

### Theater Code: Tests That Prove Nothing

**DO NOT write tests that claim to validate behavior but only prove connectivity.**

1. **ThreadPoolExecutor is not WCP-2.** Parallel Python threads are not workflow parallel splits—there are no tokens, no control flow constructs, no workflow semantics.
2. **Sequential loops are not WCP-3.** Iterating through approvals and counting is not synchronization—real sync blocks until concurrent branches converge.
3. **Logging "cancelled" is not cancellation.** Adding a supplier to a cancelled list after their work completed is not WCP-35—real cancellation aborts running tasks.
4. **Hash-based branching is not deferred choice.** `if hash(x) % 3 == 0` is deterministic—WCP-16 requires external events racing to trigger branches.
5. **Publishing without consuming is not coordination.** Fire-and-forget to RabbitMQ proves nothing—real event-driven systems have consumers that influence execution.
6. **In-memory chains are not lockchains.** SHA-256 hashes in a Python list are not audit trails—real lockchains persist to PostgreSQL with hash columns.
7. **Domain data in RDF is not workflow.** Storing supplier metadata is not workflow execution—real YAWL execution has tokens, task states, and control flow in RDF.
8. **Pattern IDs in audit logs do not prove patterns.** Writing `pattern_id=35` to PostgreSQL while using Python if/else is a lie—the pattern must be enforced by the engine.
9. **If the workflow is Python code, it's not RDF-driven.** The thesis claims RDF-only execution; tests must prove RDF rules fire, not that Python scripts run.
10. **Name tests honestly.** `TestContainerConnectivity` not `TestWCPPatterns`. `test_services_respond` not `test_complete_supply_chain_lifecycle`.

**The test for a workflow pattern must show the ENGINE enforcing the pattern, not Python code simulating it.**

### Implementation Lies (pre-commit blocks these)
```python
# TODO/FIXME/HACK/WIP/STUB
# noqa / type: ignore (blanket)
pass  # in function body
...   # ellipsis stub
raise NotImplementedError
assert True  # meaningless test
```

### Test Skipping is Laziness
```python
# FORBIDDEN - These are excuses, not solutions:
@pytest.mark.xfail(reason="...")  # NEVER - implement properly
@pytest.mark.skipif(...)          # NEVER - make it work

# If a test requires a dependency (EYE reasoner, etc.), ensure:
# 1. The dependency IS installed in the dev environment
# 2. The test RUNS and PASSES
# 3. CI/CD has the dependency available

# The only acceptable skip: platform-specific tests on wrong platform
# e.g., skipif(sys.platform != "darwin") for macOS-only features
```

**Philosophy:** If you write a test, make it pass. If you can't make it pass, you haven't finished implementing.

### Poe Task Standardization (Lean Six Sigma Quality)

**NEVER run Python scripts directly - ALWAYS create poe tasks for standardization.**

```toml
# pyproject.toml - Add new poe tasks
[tool.poe.tasks]
proof-persistence = "python examples/proof_persistence.py"
proof-wcp = "python examples/proof_wcp_03_sync.py"
benchmark = "python scripts/benchmark.py"
```

**Why standardize through poe:**
- ✅ Consistent execution environment
- ✅ Centralized task management
- ✅ Easy to add quality gates (pre/post hooks)
- ✅ Self-documenting workflow
- ✅ Lean Six Sigma traceability

### Common Mistakes → Correct Patterns

| ❌ Wrong Pattern | ✅ Correct Alternative | Why |
|-----------------|----------------------|-----|
| `python script.py` | `uv run poe <task>` | Create poe task for standardization |
| `uv run python script.py` | `uv run poe <task>` | Create poe task for standardization |
| `pytest tests/` | `uv run poe test` | Missing coverage/flags |
| `mypy src/` | `uv run poe type-check` | Missing strict flags |
| `from ..module import` | `from kgcl.module import` | Relative import |
| `assert True` | `assert condition` | Meaningless test |
| Reading code | Running proof script | No verification |
| `--no-verify` | Fix issues, commit properly | Bypasses hooks |
| `TODO: fix later` | Complete implementation | Deferred defects |

### Claims Require Proof (Gemba Walk)

**DO NOT make claims about functionality without executable proof.**

#### The Persistence Lie Example

```python
# ❌ WRONG - Claiming without verification
"The persistence layer handles saving to disk"
# Reality: Only examined code, didn't RUN it to see what actually persists

# ✅ CORRECT - Gemba walk with proof script
# Created examples/test_persistence_reality.py that PROVES:
# - In-memory repos: VOLATILE (lost on exit)
# - Checkpoints: VOLATILE (in-memory dict only)
# - XML parser: DURABLE (actually writes files)
# - Database: NOT CONNECTED
```

#### Mandatory Proof Protocol

**BEFORE claiming that X works:**

1. **Write proof script** in `examples/` that demonstrates X
2. **Run the script** with `uv run python examples/proof_x.py`
3. **Show actual output** - don't describe, don't summarize, SHOW
4. **Test failure case** - prove it fails when X is broken

```bash
# Example: Proving YAWL persistence actually works
uv run python examples/test_persistence_reality.py

# Output MUST show:
# ✓ Written to disk: /tmp/test.yawl
# ✓ File exists: True
# ✓ Read back: spec-001
```

#### Forbidden Claims Without Proof

```python
# ❌ FORBIDDEN
"The system handles errors gracefully"       # Show error handling WORKING
"Persistence is implemented"                 # Show data PERSISTING to disk
"All WCP patterns are supported"             # Show each pattern EXECUTING
"The engine uses RDF for control flow"       # Show RDF triples DRIVING execution
"Integration with RabbitMQ works"            # Show messages CHANGING behavior

# ✅ REQUIRED - Proof for each claim
examples/proof_error_handling.py  # Triggers error, shows recovery
examples/proof_persistence.py     # Writes, exits, restarts, reads back
examples/proof_wcp_03_sync.py     # Shows engine blocking until all branches complete
examples/proof_rdf_control.py     # Shows SPARQL query results changing execution path
examples/proof_rabbitmq_event.py  # Shows message arrival triggering different code path
```

#### Gemba Walk Checklist

**For ANY claim about system behavior:**

- [ ] Proof script exists in `examples/`
- [ ] Script is runnable: `uv run python examples/proof_x.py`
- [ ] Script shows ACTUAL behavior, not mocked/simulated
- [ ] Script output is observable and verifiable
- [ ] Script fails when feature is broken (negative test)

**Philosophy**: "Don't tell me the code exists, SHOW me it works. Don't read the code, RUN it."

---

## 🔍 Anti-Lie Planning Protocol

**BEFORE implementing any feature, list all the ways you might lie about it. THEN create proof against each lie.**

### Planning Phase: Identify Potential Lies

When planning a feature, explicitly enumerate every way the implementation could be **theater code** (looks like it works but doesn't):

#### Lie Categories (From Real KGCL Examples)

**1. Persistence Lies**
- ❌ Claim: "Data persists to disk"
- 🎭 Theater: In-memory dict/list that's lost on process exit
- ✅ Proof: Write to file, exit process, restart, read back same data

**2. Workflow Control Flow Lies**
- ❌ Claim: "Implements WCP-3 synchronization"
- 🎭 Theater: Python loop iterating branches, counting completions
- ✅ Proof: Engine blocks until ALL branches complete, test fails if only 2 of 3 finish

**3. RDF/SPARQL Lies**
- ❌ Claim: "RDF-driven execution"
- 🎭 Theater: RDF stores metadata, Python if/else does control flow
- ✅ Proof: SPARQL query results change which code path executes

**4. Event-Driven Lies**
- ❌ Claim: "Event-driven coordination via RabbitMQ"
- 🎭 Theater: Fire-and-forget publish, no consumers, no behavior change
- ✅ Proof: Message arrival triggers different code path, test fails without message

**5. Cancellation Lies**
- ❌ Claim: "Implements WCP-35 cancellation"
- 🎭 Theater: Logging "cancelled" after task already completed
- ✅ Proof: Task execution aborts mid-run, resources released

**6. Parallel Execution Lies**
- ❌ Claim: "WCP-2 parallel split"
- 🎭 Theater: ThreadPoolExecutor with Python threads
- ✅ Proof: Workflow engine creates tokens in parallel branches, each advances independently

**7. Choice Pattern Lies**
- ❌ Claim: "WCP-16 deferred choice"
- 🎭 Theater: Deterministic `if hash(x) % 3 == 0` branching
- ✅ Proof: External events race, first to arrive triggers branch

**8. Audit Trail Lies**
- ❌ Claim: "Immutable lockchain audit trail"
- 🎭 Theater: SHA-256 hashes in Python list
- ✅ Proof: PostgreSQL with hash columns, tamper detection works

### Implementation Phase: Prove Against Each Lie

**For EVERY lie identified in planning, create explicit proof:**

```python
# Example: Planning identified "persistence lie"
# Implementation MUST include:

# examples/proof_persistence_real.py
"""Prove persistence actually works (not in-memory only)."""

def test_persistence_survives_restart():
    # Write data
    manager = PersistenceManager(db_path="/tmp/test.db")
    manager.save("key1", {"value": 123})
    manager.close()

    # Simulate process restart
    del manager

    # Read back - MUST succeed if persistence is real
    manager2 = PersistenceManager(db_path="/tmp/test.db")
    data = manager2.load("key1")
    assert data == {"value": 123}  # FAILS if in-memory only

    # Negative test: Prove it fails when broken
    manager3 = PersistenceManager(db_path=":memory:")
    manager3.save("key2", {"value": 456})
    del manager3

    manager4 = PersistenceManager(db_path=":memory:")
    data = manager4.load("key2")  # MUST be None (in-memory lost)
    assert data is None
```

### Anti-Lie Planning Template

**Use this template when planning ANY feature:**

```markdown
## Feature: [Name]

### Potential Lies (Planning Phase)
1. **Lie**: [What I might falsely claim]
   - **Theater**: [How I could fake it]
   - **Proof**: [Test that fails if theater]

2. **Lie**: [What I might falsely claim]
   - **Theater**: [How I could fake it]
   - **Proof**: [Test that fails if theater]

[...continue for all lies...]

### Implementation Checklist
- [ ] Proof script created: `examples/proof_[feature].py`
- [ ] Proof script RUNS successfully
- [ ] Proof script shows REAL behavior (not mocked)
- [ ] Negative tests prove detection (fails when broken)
- [ ] Tests assert on ENGINE state, not script variables
```

### Real Example: YAWL Persistence Feature

**Planning Phase (Before Writing Code):**

```markdown
## Feature: YAWL Case Persistence

### Potential Lies
1. **Lie**: "CheckpointManager persists case state to disk"
   - **Theater**: Store in `self.checkpoints` dict (in-memory only)
   - **Proof**: Create checkpoint, exit process, restart, restore checkpoint

2. **Lie**: "to_json() means it's persisted"
   - **Theater**: Serialize to JSON string but never write file
   - **Proof**: Check filesystem for actual .json file

3. **Lie**: "DatabaseRepository persists to PostgreSQL"
   - **Theater**: Repository class exists, methods defined, but no DB connection
   - **Proof**: INSERT row, query from separate connection, row exists

4. **Lie**: "XMLWriter persists specifications"
   - **Theater**: Generate XML string, never write file
   - **Proof**: Write spec, check file exists, parse with XMLParser
```

**Implementation Phase (Proof Against Lies):**

```python
# examples/test_persistence_reality.py (ACTUALLY CREATED in KGCL)
# This file PROVES which persistence claims are lies:

def test_checkpoint_manager():
    """Prove: CheckpointManager stores in memory, NOT on disk."""
    manager = CheckpointManager()
    checkpoint = manager.create_case_checkpoint(case)

    print(f"✓ Stored in manager.checkpoints dict: {checkpoint.id in manager.checkpoints}")
    print(f"✗ Written to disk: False (in-memory dict only)")
    # PROOF: This exposes the lie - no file written
```

### Enforcement

**Pre-commit hook checks:**
- [ ] Every feature plan has "Potential Lies" section
- [ ] Every lie has corresponding proof script
- [ ] Proof scripts in `examples/proof_*.py` are executable
- [ ] Proof scripts contain negative tests

**Definition of Done:**
- [ ] ALL identified lies have been proven false (or admitted as limitations)
- [ ] Proof scripts demonstrate REAL behavior
- [ ] No claims without proof scripts

---

## ⚠️ Common Pitfalls

1. **`python` instead of `uv run`** → Environment mismatches → Always `uv run python`
2. **Direct pytest/mypy/ruff** → Missing flags → Always `poe` tasks
3. **Claims without proof** → Gemba walk failure → Create `examples/proof_*.py`
4. **Theater code** → False positives → Test engine state, not script variables
5. **Skipping verification** → Signals ignored → Run `poe verify` before "done"
6. **TODO in production** → Pre-commit blocks → Complete or remove
7. **Relative imports** → Import errors → Use absolute imports
8. **Marking complete with signals** → Quality regressions → Clear signals first
9. **Root folder files** → Organization chaos → Use subdirectories
10. **Blanket suppressions** → Hidden defects → Fix root cause, justify exceptions

---

### Instead: Single-File POCs
When exploring, create complete working files in `examples/`:
- Self-contained (all types, implementation, tests)
- Runnable: `uv run python examples/poc_x.py`
- No TODOs, stubs, placeholders

---

## Git Hooks

```bash
git config core.hooksPath scripts/git_hooks
```

| Hook | Speed | Checks |
|------|-------|--------|
| pre-commit | <10s | Secrets, lies, format, basic lint |
| pre-push | 30-120s | Full lint, mypy strict, all tests |

**Never bypass with `--no-verify`.**

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

---

## 🚨 Definition of Done (Andon Signals Enforced)

**MANDATORY VALIDATION BEFORE MARKING ANY TASK COMPLETE:**

### Critical Signals (RED - MUST be clear)

```bash
# 1. All tests pass - NO FAILURES, NO SKIPS
uv run poe test
# Expected: ✓ All tests passed

# 2. No type errors - 100% type coverage
uv run poe type-check
# Expected: ✓ Success: no issues found

# 3. No lint errors - ALL 400+ Ruff rules pass
uv run poe lint
# Expected: ✓ All checks passed

# 4. No implementation lies
uv run poe detect-lies
# Expected: ✓ No TODO/FIXME/stubs/placeholders found
```

### Verification Checklist

**BEFORE claiming "done", verify ALL items:**

- [ ] **🔴 Tests**: `uv run poe test` - all passing, 0 failures
- [ ] **🔴 Types**: `uv run poe type-check` - 0 mypy errors, 100% coverage
- [ ] **🔴 Lint**: `uv run poe lint` - 0 ruff errors
- [ ] **🔴 Lies**: `uv run poe detect-lies` - 0 TODO/FIXME/stubs
- [ ] **🟡 Coverage**: 80%+ maintained (check pytest output)
- [ ] **🟡 Docs**: Public APIs have NumPy-style docstrings
- [ ] **🟡 Proof**: Claims verified with tests or proof scripts

### Completion Protocol

**Step 1: Run Full Verification**
```bash
uv run poe verify  # Runs ALL checks in sequence
```

**Step 2: Check Signals**
- If ANY red signal (🔴): STOP - fix before proceeding
- If ANY yellow signal (🟡): Investigate and document

**Step 3: Only Mark Complete When**
- ✅ ALL critical signals clear (green)
- ✅ ALL verification checklist items checked
- ✅ Claims backed by executable proof (tests or scripts)

### Forbidden Completion Shortcuts

```python
# ❌ NEVER mark complete with:
"Done (except tests)"           # Tests are MANDATORY
"Implemented (needs types)"     # Types are MANDATORY
"Working (has TODOs)"           # TODOs are FORBIDDEN
"Verified by inspection"        # Proof scripts REQUIRED for claims
```

**ZERO TOLERANCE**: Cannot mark complete while signals present. Cannot skip verification. Cannot claim without proof.

---

## 🤖 AI Assistant Guidelines

### DO

1. Run `uv run poe verify` before suggesting commits
2. Use `uv run poe <task>` for ALL execution (create tasks as needed)
3. Follow Chicago School TDD (tests first, behavior-focused)
4. Add proof scripts in `examples/` for claimed functionality
5. Create frozen dataclasses for value objects
6. Follow gemba walk protocol for verification
7. Use NumPy-style docstrings for public APIs
8. Batch ALL operations in single messages (parallel execution)
9. Mark todos as in_progress BEFORE starting work
10. Assert on engine state, not script variables

### DON'T

1. Skip tests when adding features
2. Make claims without executable proof scripts
3. Run Python directly (ALWAYS create poe tasks)
4. Create files in root folder (use subdirectories)
5. Mark tasks complete while Andon signals present
6. Write theater code (tests that don't prove engine behavior)
7. Use relative imports (always absolute)
8. Skip `uv run poe verify` before commits
9. Claim features work by reading code (must RUN proof)
10. Use blanket type: ignore or noqa without justification

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
|------------------------|-------------------------|
| Task tool spawns agents | swarm_init, agent_spawn |
| File operations | task_orchestrate |
| Bash commands | memory_usage |
| Code generation | neural_train |
| Git operations | GitHub integration |

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

| Pre-Operation | Post-Operation | Session |
|--------------|----------------|---------|
| Auto-assign agents | Auto-format | Generate summaries |
| Validate commands | Train patterns | Persist state |
| Prepare resources | Update memory | Track metrics |

---

## Reminders

- Do what was asked; nothing more, nothing less
- Never create files unless necessary
- Prefer editing existing files
- Never save to root folder
- Never create docs unless requested
