# Poka-Yoke Error Proofing for Knowledge Hooks

This module implements Lean Six Sigma Poka-Yoke (error-proofing) patterns specifically for Knowledge Hooks validation and execution safety.

## Overview

Following Shigeo Shingo's "Zero Quality Control" methodology, this module defines 10 pre-defined poka-yokes organized by severity:

### Severity Levels

1. **SHUTDOWN** (Highest Severity - Safety-Critical)
   - Prevents catastrophic errors
   - Stops process immediately
   - Examples: Empty condition queries, recursive triggers

2. **CONTROL** (Medium Severity - Gating)
   - Gates process until corrected
   - Requires manual intervention
   - Examples: Priority conflicts, invalid action types

3. **VALIDATION** (Pre-Execution Checks)
   - Validates before execution
   - Ensures operational requirements
   - Examples: Invalid phase, missing handler data

4. **WARNING** (Informational - Non-Blocking)
   - Alerts without stopping
   - Monitoring and observability
   - Examples: Circular chains, orphan hooks

## Pre-Defined Poka-Yokes

### SHUTDOWN (3 poka-yokes)

- **PY-HOOK-001**: Empty Condition Query
  - Prevents hooks without conditions (would fire on every tick)

- **PY-HOOK-005**: Disabled Hook with Chaining
  - Prevents dead code paths from disabled hooks

- **PY-HOOK-010**: Recursive Hook Trigger
  - Prevents infinite loops from recursive milestone triggers

### CONTROL (2 poka-yokes)

- **PY-HOOK-003**: Priority Conflict
  - Ensures deterministic execution order via unique priorities

- **PY-HOOK-007**: Invalid Action Type
  - Restricts actions to: Assert, Reject, Notify, Transform

### VALIDATION (2 poka-yokes)

- **PY-HOOK-004**: Invalid Phase Assignment
  - Validates phase is one of 5 valid values

- **PY-HOOK-008**: Missing Handler Data
  - Ensures REJECT/NOTIFY actions have required data

### WARNING (3 poka-yokes)

- **PY-HOOK-002**: Circular Chain Detection
  - Detects potential infinite loops in hook chains

- **PY-HOOK-006**: Orphan Chained Hook
  - Warns when hook chains to non-existent child

- **PY-HOOK-009**: Overly Broad Condition
  - Alerts on performance-impacting broad queries

## Files

```
tests/hybrid/lss/hooks/poka_yoke/
├── __init__.py          # Module exports
├── types.py             # Poka-yoke definitions (10 pre-defined)
├── test_hook_errors.py  # Comprehensive test suite (20 tests)
└── README.md            # This file
```

## Usage

```python
from tests.hybrid.lss.hooks.poka_yoke.types import (
    HookPokaYokeType,
    HookPokaYoke,
    ALL_HOOK_POKA_YOKES,
    get_poka_yoke_by_id,
    get_poka_yokes_by_type,
)

# Get all SHUTDOWN poka-yokes
shutdown_checks = get_poka_yokes_by_type(HookPokaYokeType.SHUTDOWN)

# Get specific poka-yoke
py_001 = get_poka_yoke_by_id("PY-HOOK-001")

# Access all 10 poka-yokes
for py in ALL_HOOK_POKA_YOKES:
    print(f"{py.id}: {py.description} ({py.type.value})")
```

## Testing

All 10 poka-yokes have comprehensive test coverage:

```bash
# Run tests
uv run pytest tests/hybrid/lss/hooks/poka_yoke/ -v

# Run with coverage
uv run pytest tests/hybrid/lss/hooks/poka_yoke/ --cov=tests/hybrid/lss/hooks/poka_yoke --cov-report=term-missing

# Run doctests
uv run python -c "import sys; sys.path.insert(0, 'tests'); from hybrid.lss.hooks.poka_yoke.types import *; import doctest; doctest.testmod(sys.modules['hybrid.lss.hooks.poka_yoke.types'])"
```

## Quality Metrics

- **Test Coverage**: 95.5% (20 tests, all passing)
- **Type Coverage**: 100% (mypy --strict)
- **Lint Status**: Clean (Ruff all rules)
- **Doctests**: 18/18 passing
- **Test Runtime**: <1 second

## Safety Principles

Following Toyota Production System and IEC 61508 standards:

1. **Fail-Fast**: Detect and stop immediately (SHUTDOWN)
2. **Bounded Execution**: Prevent runaway processes (max_ticks)
3. **State Protection**: Prevent corruption (validation gates)
4. **Resource Protection**: Prevent exhaustion (tick limits)
5. **Visual Management**: Clear alerts and monitoring (WARNING)
6. **Jidoka**: Built-in quality (stop on defects)

## References

- Shigeo Shingo: "Zero Quality Control" - Poka-Yoke methodology
- Toyota Production System: Andon cord (line-stop on errors)
- IEC 61508: Functional Safety of Safety-Related Systems
- KGCL Knowledge Hooks: src/kgcl/hybrid/knowledge_hooks.py
- Lean Six Sigma: 99.99966% defect-free (6σ quality)

## Integration

These poka-yokes integrate with the Knowledge Hooks system:

```python
from kgcl.hybrid.knowledge_hooks import KnowledgeHook, HookRegistry
from tests.hybrid.lss.hooks.poka_yoke.types import PY_HOOK_001

registry = HookRegistry()

# Before registering a hook, apply poka-yokes
hook = KnowledgeHook(...)

# Apply PY-HOOK-001: Empty Condition Query
if eval(PY_HOOK_001.condition, {"hook": hook, "len": len}):
    raise ValidationError(PY_HOOK_001.action)

# Register if validation passes
registry.register(hook)
```

## Contributing

When adding new poka-yokes:

1. Follow the naming convention: `PY-HOOK-XXX`
2. Choose appropriate severity level
3. Write both positive and negative tests
4. Document safety rationale
5. Add to `ALL_HOOK_POKA_YOKES` list
6. Update this README

## License

Part of the KGCL (Knowledge Graph Change Language) project.
