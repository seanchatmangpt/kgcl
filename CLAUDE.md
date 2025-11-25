# Claude Code Configuration - SPARC Development Environment

## 🚨 CRITICAL: CONCURRENT EXECUTION & FILE MANAGEMENT

**ABSOLUTE RULES**:
1. ALL operations MUST be concurrent/parallel in a single message
2. **NEVER save working files, text/mds and tests to the root folder**
3. ALWAYS organize files in appropriate subdirectories
4. **USE CLAUDE CODE'S TASK TOOL** for spawning agents concurrently, not just MCP

### ⚡ GOLDEN RULE: "1 MESSAGE = ALL RELATED OPERATIONS"

**MANDATORY PATTERNS:**
- **TodoWrite**: ALWAYS batch ALL todos in ONE call (5-10+ todos minimum)
- **Task tool (Claude Code)**: ALWAYS spawn ALL agents in ONE message with full instructions
- **File operations**: ALWAYS batch ALL reads/writes/edits in ONE message
- **Bash commands**: ALWAYS batch ALL terminal operations in ONE message
- **Memory operations**: ALWAYS batch ALL memory store/retrieve in ONE message

### 🎯 CRITICAL: Claude Code Task Tool for Agent Execution

**Claude Code's Task tool is the PRIMARY way to spawn agents:**
```javascript
// ✅ CORRECT: Use Claude Code's Task tool for parallel agent execution
[Single Message]:
  Task("Research agent", "Analyze requirements and patterns...", "researcher")
  Task("Coder agent", "Implement core features...", "coder")
  Task("Tester agent", "Create comprehensive tests...", "tester")
  Task("Reviewer agent", "Review code quality...", "reviewer")
  Task("Architect agent", "Design system architecture...", "system-architect")
```

**MCP tools are ONLY for coordination setup:**
- `mcp__claude-flow__swarm_init` - Initialize coordination topology
- `mcp__claude-flow__agent_spawn` - Define agent types for coordination
- `mcp__claude-flow__task_orchestrate` - Orchestrate high-level workflows

### 📁 File Organization Rules

**NEVER save to root folder. Use these directories:**
```
kgcl/
├── src/kgcl/              # Source code (all typed)
│   ├── hooks/             # Knowledge Hooks system
│   ├── unrdf_engine/      # UNRDF integration
│   ├── ontology/          # RDF/SHACL definitions
│   ├── cli/               # Command-line interface
│   └── ...
├── tests/                 # Test suite (Chicago School TDD)
│   ├── hooks/             # Hook behavior tests
│   ├── unrdf_engine/      # UNRDF tests
│   ├── integration/       # End-to-end UNRDF porting tests
│   └── ...
├── docs/                  # Documentation
├── config/                # Configuration files
├── scripts/               # Utility scripts
└── examples/              # Example code
```

## Project Overview

This project uses SPARC (Specification, Pseudocode, Architecture, Refinement, Completion) methodology with Claude-Flow orchestration for systematic **Chicago School Test-Driven Development** (tests drive implementation, no mocking domain objects).

### Core Principles (Adopted from .cursorrules)
1. **Chicago School TDD**: Tests drive all development. No mocking domain objects.
2. **Type Safety**: Full type hints everywhere. `poe type-check` must pass with `strict = true`.
3. **Production-Grade**: Code ready for immediate production use without refactoring.
4. **UNRDF Alignment**: Port UNRDF JavaScript patterns to Python idiomatically.
5. **No Tech Debt**: Clean code first time. No "TODO: refactor later".

## Build & Test Automation (using `poe` - Poetry)

All build/test/lint workflows run via `poe <task>` where tasks are defined in `pyproject.toml` → `[tool.poe.tasks]`.

### Core Poe Commands (via `uv run poe` with Timeouts)
```bash
# Development (with timeouts to prevent hanging)
timeout 5s uv run poe format            # Format code (Ruff) - 5s max
timeout 8s uv run poe lint              # Lint & fix (Ruff) - 8s max
timeout 15s uv run poe type-check       # Type check (Mypy, strict mode) - 15s max
timeout 30s uv run poe test             # Run tests (Pytest) - 30s max

# Verification
timeout 60s uv run poe verify           # All checks + tests - 60s max
timeout 60s uv run poe ci               # CI pipeline - 60s max

# Release
timeout 30s uv run poe release-check    # All checks (no fixes) - 30s max
timeout 60s uv run poe prod-build       # Strict production build - 60s max

# UNRDF-Specific
timeout 30s uv run poe unrdf-validate   # Type-check + UNRDF tests - 30s max
timeout 60s uv run poe unrdf-full       # All UNRDF porting tests - 60s max

# Git Hooks
timeout 3s uv run poe pre-commit-setup  # Install hooks - 3s max
timeout 15s uv run poe pre-commit-run   # Run pre-commit checks - 15s max
```

**NEVER run ad-hoc shell commands when an equivalent `poe <task>` exists.**

## Code Style & Best Practices - Lean Six Sigma Standards

**ZERO TOLERANCE QUALITY REQUIREMENTS:**
- **Modular Design**: Files under 500 lines - STRICTLY ENFORCED
- **Environment Safety**: NEVER hardcode secrets - Bandit scanning mandatory
- **Test-First**: MANDATORY Chicago School TDD - tests drive all behavior
- **Type Coverage**: 100% type hints on ALL functions - NO EXCEPTIONS
- **Test Coverage**: 80%+ minimum coverage - NON-NEGOTIABLE
- **Clean Architecture**: Separate concerns - NO MIXING ALLOWED
- **Documentation**: ALWAYS keep updated with NumPy-style docstrings on ALL public APIs
- **Code Quality**: ALL Ruff rules enforced - NO SUPPRESSION except with justification

## Type Hints - Mandatory

Every function MUST have complete type hints:

```python
# ✅ CORRECT
def process_hook(hook: Hook, context: HookContext) -> Receipt:
    """Process a hook with full context.

    Parameters
    ----------
    hook : Hook
        The hook to process
    context : HookContext
        Execution context with metadata

    Returns
    -------
    Receipt
        Immutable execution receipt
    """
    ...

# ❌ WRONG
def process_hook(hook, context):  # Missing types!
    ...
```

### Type Annotations Rules
- All function parameters: `param: Type`
- All return types: `-> ReturnType`
- All class attributes: `attribute: Type`
- Generics: `List[T]`, `Dict[K, V]`, `Optional[X]`
- Union types: `Union[A, B]` or `A | B` (Python 3.10+)
- Callbacks: `Callable[[Arg], ReturnType]`

### Dataclass Immutability
Use frozen dataclasses for value objects:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Receipt:
    """Immutable hook execution receipt."""
    execution_id: str
    hook_id: str
    result: bool
```

### Mypy Configuration (Strictest)
From `pyproject.toml`:
```toml
[tool.mypy]
strict = true                      # All strictest checks enabled
disallow_any_unimported = true     # No `Any` imports
disallow_incomplete_defs = true    # All types complete
disallow_untyped_defs = true       # All functions typed
disallow_untyped_calls = true      # All calls typed
check_untyped_defs = true          # Check untyped functions
no_implicit_optional = true        # No implicit Optional
```

## Testing - Chicago School TDD

### Test-First Development
1. Write tests FIRST (before implementation)
2. Tests specify behavior, not implementation
3. No mocking of domain objects (Hook, Receipt, Condition, etc.)
4. Real I/O, real SPARQL evaluation, real metrics

### Test Markers
```python
@pytest.mark.integration      # Integration tests
@pytest.mark.security         # Security tests
@pytest.mark.performance      # Performance tests
@pytest.mark.slow            # Long-running tests (deselect with -m "not slow")
```

### Test Organization
```
tests/
├── hooks/
│   ├── test_core.py          # Hook, HookReceipt, HookRegistry
│   ├── test_conditions.py    # All condition types
│   ├── test_lifecycle.py     # HookExecutionPipeline
│   ├── test_security.py      # ErrorSanitizer, SandboxRestrictions
│   ├── test_performance.py   # PerformanceOptimizer, QueryCache
│   ├── test_policy_packs.py  # PolicyPackManager
│   ├── test_file_resolver.py # FileResolver
│   └── test_unrdf_integration.py  # Hook-UNRDF interaction
├── integration/
│   └── test_unrdf_porting.py # All 8 UNRDF patterns validated
└── ...
```

### Test Naming
```python
# ✅ CORRECT - Describes behavior
def test_hook_execution_with_error_sanitization():
    """Errors are sanitized before storage in receipt."""

def test_cache_hit_reduces_latency():
    """Query cache hit should reduce latency."""

# ❌ WRONG - Too vague
def test_hook():
def test_error():
```

### Test Verification (Chicago School AAA)
- Apply Chicago School AAA structure (Arrange → Act → Assert) with real collaborators
- No mocking of domain objects—use real Hook, Receipt, Condition instances
- Tests MUST verify observable behavior/state, not merely `assert result.is_ok()`
- Keep total test suite runtime under **1 second**; optimize or parallelize if needed

### Pytest Configuration (Strictest)
From `pyproject.toml`:
```toml
[tool.pytest.ini_options]
addopts = "--color=yes --doctest-modules --exitfirst --failed-first --verbosity=2 --strict-markers"
xfail_strict = true         # xfail must actually fail
asyncio_mode = "auto"       # Async test support
```

## Code Style - NumPy Docstrings

Every public class/function needs NumPy-style docstrings:

```python
def execute_hook(hook: Hook, event: Dict[str, Any]) -> Receipt:
    """Execute a single hook against an event.

    Parameters
    ----------
    hook : Hook
        Hook definition with condition and handler
    event : Dict[str, Any]
        Event triggering hook execution

    Returns
    -------
    Receipt
        Immutable record of execution with result and metadata

    Raises
    ------
    ValueError
        If hook definition is invalid
    TimeoutError
        If execution exceeds timeout limit

    Examples
    --------
    >>> hook = Hook(name="test", condition=ThresholdCondition(5), handler=lambda e: True)
    >>> result = execute_hook(hook, {"count": 10})
    >>> assert result.success
    """
```

## Imports - Absolute Only

```python
# ✅ CORRECT
from kgcl.hooks.core import Hook, HookReceipt
from kgcl.hooks.conditions import SparqlAskCondition
from kgcl.unrdf_engine.engine import UnrdfEngine

# ❌ WRONG - Relative imports banned
from ..hooks.core import Hook
from . import utils
from .conditions import SparqlAskCondition
```

## Logging, Not Print

```python
import logging

logger = logging.getLogger(__name__)

# ✅ CORRECT
logger.info("Hook executed", extra={"hook_id": hook.name, "duration_ms": duration})
logger.error("Failed to load file", exc_info=True)

# ❌ WRONG
print("Hook executed")
print(f"Duration: {duration}ms")
```

## Secrets Management

```python
# ✅ CORRECT
import os
api_key = os.getenv("API_KEY")  # From environment
config = {"key": api_key}  # Set in CI/deployment

# ❌ WRONG
config = {"key": "sk-abc123xyz"}  # Hardcoded!
password = "admin123"  # Secret in code!
```

## Linting & Formatting - Strictest

### Run Before Commit (with Timeouts)
```bash
timeout 5s uv run poe format         # Format code (5s max)
timeout 8s uv run poe lint           # Fix linting issues (8s max)
timeout 15s uv run poe type-check    # Type check (15s max)
timeout 30s uv run poe test          # Run all tests (30s max)
```

Or via `git hooks` (automatic on commit):
```bash
.githooks/pre-commit     # Blocks commits violating standards
```

### Ruff Configuration
From `pyproject.toml`:
```toml
[tool.ruff.lint]
select = ["ALL"]  # Enable ALL rules
ignore = ["CPY", "FIX", "T20", "ARG001", "COM812", "D203", "D213", "E501", "PD008", "PD009", "PGH003", "RET504", "S101", "TD003"]
```

## UNRDF Porting Rules

### 8 Critical Patterns to Port
1. **Hook Executor** - Timeout, execution ID, error sanitization, phases
2. **Condition Evaluator** - 8 condition types, file resolution
3. **Error Sanitizer** - Remove sensitive info from errors
4. **Sandbox Restrictions** - Resource/access limits
5. **Performance Optimizer** - Latency tracking, SLO monitoring
6. **Query Cache** - SPARQL result caching with TTL/LRU
7. **Policy Pack Manager** - Bundle, version, activate hooks
8. **Lockchain Writer** - Cryptographic provenance, chain anchoring

### Pattern Requirements
- Port JavaScript → Python idiomatically (not mechanical translation)
- Use Python dataclasses instead of TypeScript interfaces
- Use `frozen=True` for immutable value objects
- Full type hints (Python 3.12+)
- Chicago School TDD (test-first, real objects)
- SLO targets: p99 < 100ms for all operations

### Integration Points
Each pattern must integrate with:
- Hook lifecycle (phases: PRE, EVALUATE, RUN, POST)
- Error handling (sanitization at boundaries)
- Performance tracking (metrics in receipts)
- RDF/SPARQL engine (UnrdfEngine)

## Performance Targets (from UNRDF)
| Operation | p50 | p99 | Target |
|-----------|-----|-----|--------|
| Hook registration | 0.1ms | 1.0ms | <5ms |
| Condition eval | 0.2ms | 2.0ms | <10ms |
| Hook execution | 1.0ms | 10.0ms | <100ms |
| Receipt write | 5.0ms | 5.0ms | <10ms |
| Full pipeline | 2.0ms | 50.0ms | <500ms |

## Error Handling

```python
# ✅ CORRECT - Sanitized error
from kgcl.hooks.security import ErrorSanitizer

try:
    result = evaluate_condition(condition)
except Exception as e:
    sanitizer = ErrorSanitizer()
    sanitized = sanitizer.sanitize(e)
    logger.error(sanitized.message, extra={"code": sanitized.code})
    raise

# ❌ WRONG - Raw error leaks details
except Exception as e:
    logger.error(str(e))  # Exposes stack trace, file paths!
    raise
```

## Git Hooks Setup

```bash
# Install hooks (one-time setup)
poe pre-commit-setup

# Manually run pre-commit checks
poe pre-commit-run

# Push to remote (hooks verify code quality)
git push
```

### Pre-Commit Hook (.githooks/pre-commit)
Blocks commits if:
- Missing type hints on functions
- Hardcoded secrets detected
- No tests for new features
- Debug print statements found
- Public APIs lack docstrings
- Relative imports used
- Integration tests lack markers

## File Organization & Complexity Limits
- Max file size: 500 lines (unless justified for cohesion)
- Max function size: 40 lines
- Max class complexity: 7 methods per class
- Separate concerns: hooks, ontology, observability, CLI
- Related tests in parallel directories

## Documentation
- README.md - Project overview
- docs/UNRDF_PORTING_GUIDE.md - All 8 patterns
- docs/UNRDF_PORTING_VALIDATION.md - Test results
- pyproject.toml docstrings - Tool configuration
- NumPy docstrings - All public APIs
- Comments - Only for "why", not "what"

## Version Management
- Semantic versioning: MAJOR.MINOR.PATCH
- Commit: `bump: v$current_version → v$new_version`
- Tags: `v$version`
- Changelog: Updated on every bump (via commitizen)

## Critical Non-Negotiables (Adopted from clap-noun-verb)
- **Never trust text, only test results.** Every claim must be backed by a passing test run.
- **Build System Enforcement.** Always use the Poe tasks via `poe <task>` defined in `pyproject.toml` (`poe format`, `poe lint`, `poe verify`, etc.) for format, lint, type, and test workflows. Ad-hoc scripts are banned.
- **Git Hooks.** Never bypass hooks (`--no-verify` prohibited). Fix issues instead of skipping the gate.
- **Timeout SLAs.** All CLI/test invocations must be wrapped with sane timeouts (e.g., quick checks 5s, compilation 10s, unit tests 1s, integration 30s, long ops 60s). Timeouts expose hung workflows early.

## Behavior Verification Reinforcement
- Tests MUST verify observable behavior/state, not merely `assert result.is_ok()`.
- Apply Chicago School AAA structure (Arrange → Act → Assert) with real collaborators—no mocking of domain objects.
- Keep total test suite runtime under **1 second**; optimize or parallelize if needed.

## Prohibited Patterns (Extended)
- No placeholders, TODOs, stubs, or speculative scaffolding.
- No `print`/`logging` trickery to "fake" behavior; rely on structured errors and receipts.
- No `.unwrap()`, `.expect()`, or silent exception swallowing anywhere.
- No runtime checks when invariants can be enforced via types/dataclasses.
- Never rebase shared branches; prefer merge or fast-forward.

## Work Completion Protocol - Lean Six Sigma Quality

### The Golden Rule: ZERO DEFECTS BEFORE DELIVERY

**DO NOT STOP or compromise on quality.** Complete the full scope with zero defects before responding.
- **NO partial deliveries** - Everything must be complete and working
- **NO shortcuts** - Cannot skip tests, reduce coverage, or lower standards
- **NO exceptions** - All quality gates must pass

### MANDATORY QUALITY GATES (Zero Tolerance)

These are NOT optional - they are mandatory on EVERY delivery:
- ✓ 100% type coverage (NO untyped code)
- ✓ 80%+ test coverage (MINIMUM, not maximum)
- ✓ ALL tests passing (0 failures, 0 flakes)
- ✓ Comprehensive docstrings (ALL public APIs)
- ✓ Security scanning passed (Bandit clean)
- ✓ Code quality passed (ALL Ruff rules)
- ✓ No suppression comments (except with justification tracked in commits)

### Completion Workflow (Mandatory)
1. **Run tests immediately:** `timeout 30s uv run poe test` before claiming progress. If failures occur, stop and analyze.
2. **Create rich TODOs:** For each failure capture test name, error, file, hypothesized root cause, fix plan, and status. Batch at least 10 related TODO entries per failure set.
3. **Systematic fix cycle:** Investigate → implement fix → run targeted test → update TODO status.
4. **Re-run full suite:** `timeout 30s uv run poe test` again to confirm everything passes.
5. **Verify gates:** Ensure `timeout 8s uv run poe lint`, `timeout 15s uv run poe type-check`, docs, and hooks all pass before concluding work.

### Completion Checklist (MANDATORY)

Before responding "done", verify ALL items:
- [x] ALL parts of the request completed (not partial)
- [x] Production-ready code/tests delivered
- [x] ALL tests passing (0 failures)
- [x] Test coverage >= 80% (verified)
- [x] 100% type hints (verified)
- [x] All docstrings present (verified)
- [x] Security scan passed (Bandit clean)
- [x] Code quality passed (Ruff clean)
- [x] Can run immediately (NO "TODO" blockers)
- [x] Ready for production deployment

## TODO Discipline
- TODO lists contain **≥10 items**; partial lists are forbidden.
- All TODO items must be fully resolved before moving to subsequent tasks.
- Update TODO tracking immediately after each fix; no stale entries.

## Workflow Guardrails
- Always surface the build/verify button in planning updates so others can rerun checks quickly.
- Document second- and third-idea options (80/20 thinking) when proposing solutions; default to the sweet-spot "second idea" unless higher leverage is justified.
- Treat performance budgets (p99 targets above) as blocking requirements—profiling data must accompany any exception request.

## 🚀 Available Agents (54 Total)

### Core Development
`coder`, `reviewer`, `tester`, `planner`, `researcher`

### Swarm Coordination
`hierarchical-coordinator`, `mesh-coordinator`, `adaptive-coordinator`, `collective-intelligence-coordinator`, `swarm-memory-manager`

### Consensus & Distributed
`byzantine-coordinator`, `raft-manager`, `gossip-coordinator`, `consensus-builder`, `crdt-synchronizer`, `quorum-manager`, `security-manager`

### Performance & Optimization
`perf-analyzer`, `performance-benchmarker`, `task-orchestrator`, `memory-coordinator`, `smart-agent`

### GitHub & Repository
`github-modes`, `pr-manager`, `code-review-swarm`, `issue-tracker`, `release-manager`, `workflow-automation`, `project-board-sync`, `repo-architect`, `multi-repo-swarm`

### SPARC Methodology
`sparc-coord`, `sparc-coder`, `specification`, `pseudocode`, `architecture`, `refinement`

### Specialized Development
`backend-dev`, `mobile-dev`, `ml-developer`, `cicd-engineer`, `api-docs`, `system-architect`, `code-analyzer`, `base-template-generator`

### Testing & Validation
`tdd-london-swarm`, `production-validator`

### Migration & Planning
`migration-planner`, `swarm-init`

## 🎯 Claude Code vs MCP Tools

### Claude Code Handles ALL EXECUTION:
- **Task tool**: Spawn and run agents concurrently for actual work
- File operations (Read, Write, Edit, MultiEdit, Glob, Grep)
- Code generation and programming
- Bash commands and system operations
- Implementation work
- Project navigation and analysis
- TodoWrite and task management
- Git operations
- Package management
- Testing and debugging

### MCP Tools ONLY COORDINATE:
- Swarm initialization (topology setup)
- Agent type definitions (coordination patterns)
- Task orchestration (high-level planning)
- Memory management
- Neural features
- Performance tracking
- GitHub integration

**KEY**: MCP coordinates the strategy, Claude Code's Task tool executes with real agents.

## 🚀 Quick Setup

```bash
# Add MCP servers (Claude Flow required, others optional)
claude mcp add claude-flow npx claude-flow@alpha mcp start
claude mcp add ruv-swarm npx ruv-swarm mcp start  # Optional: Enhanced coordination
claude mcp add flow-nexus npx flow-nexus@latest mcp start  # Optional: Cloud features
```

## MCP Tool Categories

### Coordination
`swarm_init`, `agent_spawn`, `task_orchestrate`

### Monitoring
`swarm_status`, `agent_list`, `agent_metrics`, `task_status`, `task_results`

### Memory & Neural
`memory_usage`, `neural_status`, `neural_train`, `neural_patterns`

### GitHub Integration
`github_swarm`, `repo_analyze`, `pr_enhance`, `issue_triage`, `code_review`

### System
`benchmark_run`, `features_detect`, `swarm_monitor`

### Flow-Nexus MCP Tools (Optional Advanced Features)
Flow-Nexus extends MCP capabilities with 70+ cloud-based orchestration tools:

**Key MCP Tool Categories:**
- **Swarm & Agents**: `swarm_init`, `swarm_scale`, `agent_spawn`, `task_orchestrate`
- **Sandboxes**: `sandbox_create`, `sandbox_execute`, `sandbox_upload` (cloud execution)
- **Templates**: `template_list`, `template_deploy` (pre-built project templates)
- **Neural AI**: `neural_train`, `neural_patterns`, `seraphina_chat` (AI assistant)
- **GitHub**: `github_repo_analyze`, `github_pr_manage` (repository management)
- **Real-time**: `execution_stream_subscribe`, `realtime_subscribe` (live monitoring)
- **Storage**: `storage_upload`, `storage_list` (cloud file management)

**Authentication Required:**
- Register: `mcp__flow-nexus__user_register` or `npx flow-nexus@latest register`
- Login: `mcp__flow-nexus__user_login` or `npx flow-nexus@latest login`
- Access 70+ specialized MCP tools for advanced orchestration

## 🚀 Agent Execution Flow with Claude Code

### The Correct Pattern:

1. **Optional**: Use MCP tools to set up coordination topology
2. **REQUIRED**: Use Claude Code's Task tool to spawn agents that do actual work
3. **REQUIRED**: Each agent runs hooks for coordination
4. **REQUIRED**: Batch all operations in single messages

### Example Full-Stack Development:

```javascript
// Single message with all agent spawning via Claude Code's Task tool
[Parallel Agent Execution]:
  Task("Backend Developer", "Build REST API with Express. Use hooks for coordination.", "backend-dev")
  Task("Frontend Developer", "Create React UI. Coordinate with backend via memory.", "coder")
  Task("Database Architect", "Design PostgreSQL schema. Store schema in memory.", "code-analyzer")
  Task("Test Engineer", "Write Jest tests. Check memory for API contracts.", "tester")
  Task("DevOps Engineer", "Setup Docker and CI/CD. Document in memory.", "cicd-engineer")
  Task("Security Auditor", "Review authentication. Report findings via hooks.", "reviewer")
  
  // All todos batched together
  TodoWrite { todos: [...8-10 todos...] }
  
  // All file operations together
  Write "backend/server.js"
  Write "frontend/App.jsx"
  Write "database/schema.sql"
```

## 📋 Agent Coordination Protocol

### Every Agent Spawned via Task Tool MUST:

**1️⃣ BEFORE Work:**
```bash
npx claude-flow@alpha hooks pre-task --description "[task]"
npx claude-flow@alpha hooks session-restore --session-id "swarm-[id]"
```

**2️⃣ DURING Work:**
```bash
npx claude-flow@alpha hooks post-edit --file "[file]" --memory-key "swarm/[agent]/[step]"
npx claude-flow@alpha hooks notify --message "[what was done]"
```

**3️⃣ AFTER Work:**
```bash
npx claude-flow@alpha hooks post-task --task-id "[task]"
npx claude-flow@alpha hooks session-end --export-metrics true
```

## 🎯 Concurrent Execution Examples

### ✅ CORRECT WORKFLOW: MCP Coordinates, Claude Code Executes

```javascript
// Step 1: MCP tools set up coordination (optional, for complex tasks)
[Single Message - Coordination Setup]:
  mcp__claude-flow__swarm_init { topology: "mesh", maxAgents: 6 }
  mcp__claude-flow__agent_spawn { type: "researcher" }
  mcp__claude-flow__agent_spawn { type: "coder" }
  mcp__claude-flow__agent_spawn { type: "tester" }

// Step 2: Claude Code Task tool spawns ACTUAL agents that do the work
[Single Message - Parallel Agent Execution]:
  // Claude Code's Task tool spawns real agents concurrently
  Task("Research agent", "Analyze API requirements and best practices. Check memory for prior decisions.", "researcher")
  Task("Coder agent", "Implement REST endpoints with authentication. Coordinate via hooks.", "coder")
  Task("Database agent", "Design and implement database schema. Store decisions in memory.", "code-analyzer")
  Task("Tester agent", "Create comprehensive test suite with 90% coverage.", "tester")
  Task("Reviewer agent", "Review code quality and security. Document findings.", "reviewer")
  
  // Batch ALL todos in ONE call
  TodoWrite { todos: [
    {id: "1", content: "Research API patterns", status: "in_progress", priority: "high"},
    {id: "2", content: "Design database schema", status: "in_progress", priority: "high"},
    {id: "3", content: "Implement authentication", status: "pending", priority: "high"},
    {id: "4", content: "Build REST endpoints", status: "pending", priority: "high"},
    {id: "5", content: "Write unit tests", status: "pending", priority: "medium"},
    {id: "6", content: "Integration tests", status: "pending", priority: "medium"},
    {id: "7", content: "API documentation", status: "pending", priority: "low"},
    {id: "8", content: "Performance optimization", status: "pending", priority: "low"}
  ]}
  
  // Parallel file operations
  Bash "mkdir -p app/{src,tests,docs,config}"
  Write "app/package.json"
  Write "app/src/server.js"
  Write "app/tests/server.test.js"
  Write "app/docs/API.md"
```

### ❌ WRONG (Multiple Messages):
```javascript
Message 1: mcp__claude-flow__swarm_init
Message 2: Task("agent 1")
Message 3: TodoWrite { todos: [single todo] }
Message 4: Write "file.js"
// This breaks parallel coordination!
```

## Performance Benefits

- **84.8% SWE-Bench solve rate**
- **32.3% token reduction**
- **2.8-4.4x speed improvement**
- **27+ neural models**

## Hooks Integration

### Pre-Operation
- Auto-assign agents by file type
- Validate commands for safety
- Prepare resources automatically
- Optimize topology by complexity
- Cache searches

### Post-Operation
- Auto-format code
- Train neural patterns
- Update memory
- Analyze performance
- Track token usage

### Session Management
- Generate summaries
- Persist state
- Track metrics
- Restore context
- Export workflows

## Advanced Features (v2.0.0)

- 🚀 Automatic Topology Selection
- ⚡ Parallel Execution (2.8-4.4x speed)
- 🧠 Neural Training
- 📊 Bottleneck Analysis
- 🤖 Smart Auto-Spawning
- 🛡️ Self-Healing Workflows
- 💾 Cross-Session Memory
- 🔗 GitHub Integration

## Integration Tips

1. Start with basic swarm init
2. Scale agents gradually
3. Use memory for context
4. Monitor progress regularly
5. Train patterns from success
6. Enable hooks automation
7. Use GitHub tools first

## Support

- Documentation: https://github.com/ruvnet/claude-flow
- Issues: https://github.com/ruvnet/claude-flow/issues
- Flow-Nexus Platform: https://flow-nexus.ruv.io (registration required for cloud features)

---

Remember: **Claude Flow coordinates, Claude Code creates!**

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
Never save working files, text/mds and tests to the root folder.
