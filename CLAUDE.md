# Claude Code Configuration - KGCL Research Library

## YAWL Engine Status: BROKEN

**The `src/kgcl/yawl_engine/` is non-functional.** Claims "RDF-only" architecture but uses Python if/else for all logic. See `docs/explanation/yawl-failure-report.md` for details. **Recommendation:** Delete and rewrite, or rename to acknowledge it's conventional code.

---

## Project Context

**Research library, not production system.** SHACL validates at ingress; internal code trusts data.

| Do | Don't |
|---|---|
| Clean algorithm implementations | Input validation beyond SHACL |
| Type hints for documentation | Defensive null checks |
| Tests verifying correctness | Enterprise patterns (retries, circuit breakers) |
| RDF/SPARQL patterns | Auth, rate limiting, security theater |

---

## Quick Reference

### Commands (always use `uv run poe`)
```bash
poe format      # Ruff format
poe lint        # Ruff lint + fix
poe type-check  # Mypy strict
poe test        # Pytest
poe verify      # All checks
poe detect-lies # Find TODO/FIXME/stubs
```

### Python Execution: NEVER use `python` directly
```bash
# ✅ CORRECT - Always use uv
uv python script.py           # Run script with uv-managed Python
uv run python script.py       # Alternative (runs in venv)
uv run pytest                 # Run tools through uv

# ❌ WRONG - Never call python directly
python script.py              # NO - uses system Python
python3 script.py             # NO - bypasses uv
python -m pytest              # NO - use uv run pytest
```
**Why:** `uv python` ensures correct Python version (3.13+) and project dependencies.

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

### Instead: Single-File POCs
When exploring, create complete working files in `examples/`:
- Self-contained (all types, implementation, tests)
- Runnable: `uv python examples/poc_x.py`
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

## Quality Gates (Mandatory)

Before "done":
- [ ] ALL tests passing
- [ ] 80%+ coverage
- [ ] 100% type hints
- [ ] Docstrings on public APIs
- [ ] Ruff clean
- [ ] No TODO/FIXME/stubs

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
