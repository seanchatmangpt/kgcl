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

**ALL Python execution MUST use `uv run python`** - Pre-commit hook blocks direct `python` usage. Never run `python` directly; always use `uv run python` or `uv run poe <task>`.

```bash
# ✅ CORRECT - MANDATORY
uv run poe format      # Ruff format (<5s)
uv run poe lint        # Ruff lint + fix (<10s)
uv run poe type-check  # Mypy strict (<15s)
uv run poe test        # Pytest (<1s per test)
uv run poe verify      # All checks (<30s)
uv run poe detect-lies # Find TODO/FIXME/stubs (<5s)
uv run python script.py # Run scripts - MANDATORY
uv run pytest          # Run pytest

# ❌ FORBIDDEN - NEVER USE DIRECT PYTHON
python script.py       # Uses system Python (may be 3.12) - BLOCKED
python3 script.py      # Bypasses uv dependency management - BLOCKED
pytest                 # Bypasses uv dependency management - BLOCKED
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

## 🚨 Implementation Lies Detection - Prevent Writing Lies

**CRITICAL:** The lies detector runs automatically on every commit, push, and pytest run. It **BLOCKS** commits/pushes/tests if any lies are detected. Write complete code from the start.

### What Are Implementation Lies?

Implementation lies are patterns that make code **appear complete** while actually **deferring work** or using **fake implementations**. They violate Chicago School TDD and Lean Six Sigma zero-defect standards.

### 8 Categories of Lies (ALL BLOCKED)

#### 1. DEFERRED_WORK - Deferred Work Comments
**❌ FORBIDDEN:**
```python
# TODO: implement later
# FIXME: known bug
# XXX: hack/workaround
# HACK: technical debt
# WIP: incomplete work
# STUB: placeholder
# noqa  # Blanket suppression
# type: ignore  # Blanket type suppression
```

**✅ CORRECT:** Complete the work immediately. If you need to document future work, use proper issue tracking, not code comments.

#### 2. STUB_PATTERNS - Stub Implementations
**❌ FORBIDDEN:**
```python
def calculate(x: int) -> int:
    pass  # Stub

def process(data: dict) -> dict:
    ...  # Ellipsis stub

def validate(value: str) -> bool:
    raise NotImplementedError("Not implemented yet")
```

**✅ CORRECT:** Write the actual implementation:
```python
def calculate(x: int) -> int:
    """Calculate result."""
    return x * 2

def process(data: dict) -> dict:
    """Process data."""
    return {k: v * 2 for k, v in data.items()}

def validate(value: str) -> bool:
    """Validate value."""
    return len(value) > 0 and value.isalnum()
```

#### 3. PLACEHOLDER_RETURNS - Empty Returns Without Logic
**❌ FORBIDDEN:**
```python
def get_config() -> dict:
    return {}  # No logic, just empty dict

def find_user(id: str) -> User | None:
    return None  # No lookup logic

def process_items(items: list) -> list:
    return []  # No processing
```

**✅ CORRECT:** Implement the actual logic:
```python
def get_config() -> dict:
    """Load configuration."""
    config_path = Path("config.yaml")
    if config_path.exists():
        return yaml.safe_load(config_path.read_text())
    return {"default": True}

def find_user(id: str) -> User | None:
    """Find user by ID."""
    return db.session.query(User).filter(User.id == id).first()
```

#### 4. MOCK_ASSERTIONS - Meaningless Test Assertions
**❌ FORBIDDEN:**
```python
def test_something():
    result = do_work()
    assert True  # Meaningless
    assert result  # Too vague
```

**✅ CORRECT:** Assert on specific behavior:
```python
def test_calculate_doubles_value():
    """Calculate doubles the input value."""
    result = calculate(5)
    assert result == 10
    assert isinstance(result, int)
```

#### 5. INCOMPLETE_TESTS - Tests Without Assertions
**❌ FORBIDDEN:**
```python
def test_process_data():
    data = {"key": "value"}
    process(data)  # No assertions!

def test_validate():
    validate("test")  # No check of result
```

**✅ CORRECT:** Every test must verify behavior:
```python
def test_process_data_doubles_values():
    """Process doubles all values."""
    data = {"a": 1, "b": 2}
    result = process(data)
    assert result == {"a": 2, "b": 4}

def test_validate_rejects_empty():
    """Validate rejects empty strings."""
    assert validate("") is False
    assert validate("abc123") is True
```

#### 6. SPECULATIVE_SCAFFOLDING - Empty Classes/Unused Code
**❌ FORBIDDEN:**
```python
class UserService:
    pass  # Empty class

class DataProcessor:
    """Will implement later."""
    pass

import json  # Unused import
from typing import List, Dict  # Dict unused
```

**✅ CORRECT:** Only create classes when you implement them:
```python
class UserService:
    """Service for user operations."""
    
    def __init__(self, db: Database) -> None:
        self.db = db
    
    def get_user(self, id: str) -> User | None:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == id).first()
```

#### 7. TEMPORAL_DEFERRAL - "Later", "For Now", "Temporary"
**❌ FORBIDDEN:**
```python
# Do later
# Fix later
# Implement later
# For now, just return None
# Quick fix - needs proper solution
# Temporary workaround
# Skip for now
# Needs more work
# To be done
# Incomplete implementation
# Need to refactor
# Should refactor
```

**✅ CORRECT:** Complete the work immediately. If it's truly temporary, use proper issue tracking and document the migration path.

#### 8. MOCKING_VIOLATION - Mocking Domain Objects (Chicago TDD Violation)
**❌ FORBIDDEN:**
```python
from unittest.mock import MagicMock, Mock, patch

def test_hook_execution():
    hook = MagicMock()  # Mocking domain object!
    hook.name = "test"
    # ...

@patch("kgcl.hooks.core.Hook")
def test_with_patch(mock_hook):
    # Mocking domain object!

class MockHook:  # Custom mock class
    def __init__(self):
        self.name = "test"
```

**✅ CORRECT:** Use factory_boy factories for real domain objects:
```python
from tests.factories.hooks import HookFactory, HookReceiptFactory

def test_hook_execution():
    """Hook execution creates receipt with correct metadata."""
    hook = HookFactory()  # Real domain object
    context = HookContextFactory()
    
    receipt = execute_hook(hook, context)
    
    assert receipt.hook_id == hook.hook_id
    assert receipt.status == HookStatus.SUCCESS
    assert receipt.duration_ms > 0
```

**Factory_boy Factories Available:**
- `HookFactory`, `HookReceiptFactory` (from `tests.factories.hooks`)
- `ConditionFactory`, `ConditionResultFactory` (from `tests.factories.conditions`)
- `YCaseFactory`, `YWorkItemFactory`, `YTaskFactory`, `YSpecificationFactory` (from `tests.factories.yawl`)
- `ReceiptFactory`, `ChainAnchorFactory` (from `tests.factories.receipts`)

See `docs/how-to/migrate-from-mocks-to-factories.md` for migration guide.

### Enforcement Mechanism

**Automatic Detection:**
- **Pre-commit hook:** Fast scan (<10s) - blocks commits with lies
- **Pre-push hook:** Full scan (30-120s) - blocks pushes with lies
- **Pytest integration:** Mandatory scan before tests run - blocks test execution if lies detected

**No Bypass Available:** Detection is mandatory. Fix all lies before committing/pushing/running tests.

**Manual Check:**
```bash
uv run python scripts/detect_implementation_lies.py tests/ src/
uv run python scripts/detect_implementation_lies.py --staged  # Check staged files
```

### How to Avoid Writing Lies

1. **Write complete implementations immediately** - Don't defer work
2. **Use factory_boy for test data** - Never mock domain objects
3. **Every test must assert behavior** - No empty tests
4. **Remove unused imports/code** - No speculative scaffolding
5. **Complete functions fully** - No `pass`, `...`, or `NotImplementedError`
6. **Use proper issue tracking** - Not code comments for future work

**Remember:** The detector runs automatically. Write it right the first time.

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
python src/kgcl/cli.py  # FORBIDDEN: Direct python usage

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

**DO:** Run `uv run poe verify` before commits, use `uv run poe <task>` for execution, use `uv run python script.py` for all Python scripts, Chicago School TDD (tests first), proof scripts for claims, frozen dataclasses, NumPy docstrings, batch operations, assert on engine state.

**DON'T:** Skip tests, claim without proof, run `python` or `python3` directly (ALWAYS use `uv run python`), create root files, mark complete with signals, write theater code, use relative imports, skip verification, claim by reading code, blanket suppressions.

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