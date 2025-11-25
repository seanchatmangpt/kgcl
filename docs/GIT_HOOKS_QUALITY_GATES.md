# Git Hooks - Quality Gates & Standards

**Version**: 2.0
**Date**: 2025-11-24
**Status**: Enhanced with TODO-as-error and warnings-as-errors

---

## Overview

KGCL uses **strict pre-commit hooks** to enforce production-quality code standards. These are **hard stops** that prevent commits from being made if they violate quality policies.

### Implementation Layout

- `scripts/git_hooks/pre_commit.sh` — single source of truth for all 11 quality gates
- `.githooks/pre-commit` — lightweight wrapper installed via `git config core.hooksPath .githooks`
- `vendors/unrdf/scripts/hooks/pre-commit` — vendored wrapper that delegates to the same script

All environments call the same script, so the checks, messaging, and enforcement level stay consistent across the repository.

## Critical Quality Gates (Hard Stops)

### 🛑 Check 1: TODO/FIXME/WIP - HARD ERROR

**Rule**: No TODO, FIXME, WIP, HACK, or XXX markers allowed in committed code

```bash
# ❌ BLOCKED - This will fail pre-commit
def process_data(data):
    # TODO: Add error handling
    return data.strip()

# ✅ ALLOWED - Complete implementation
def process_data(data: str) -> str:
    """Process input data safely."""
    if not data:
        raise ValueError("Data cannot be empty")
    return data.strip()
```

**Why**: Code with TODO markers is incomplete and shouldn't be in the repository. All work must be finished before committing.

**How to Fix**:
1. Complete the implementation
2. If deferring work: Create a GitHub issue instead
3. Remove all TODO markers from code

---

### 🛑 Check 2: Type Safety - Mypy Warnings as Errors

**Rule**: All Mypy type warnings are treated as blocking errors

```bash
# ❌ BLOCKED - Type warning
def add_numbers(x, y):  # Missing type hints
    return x + y

# ✅ ALLOWED - Proper typing
def add_numbers(x: int, y: int) -> int:
    """Add two integers."""
    return x + y
```

**What We Check**:
- `--strict`: Strictest Mypy mode
- `--warn-return-any`: Flag functions returning Any
- `--warn-unused-configs`: Catch unused configurations
- All other warnings from strict mode

**How to Fix**:
```bash
# 1. Run mypy to see errors
uv run mypy src/ --strict

# 2. Add type hints to functions
def func(x: int) -> int:
    return x * 2

# 3. Add type annotations to variables
result: int = func(5)

# 4. Use Optional for nullable types
from typing import Optional
value: Optional[str] = None
```

---

### 🛑 Check 3: Linting - Ruff as Hard Error

**Rule**: All Ruff linting violations are treated as blocking errors

```bash
# ❌ BLOCKED - Linting violations
import os, sys  # Multiple imports on one line
from . import module  # Relative import

# ✅ ALLOWED - Proper style
import os
import sys
from kgcl import module
```

**What We Check**:
- All 400+ Ruff rules enabled
- Code formatting violations
- Import style (absolute only)
- Python best practices

**How to Fix**:
```bash
# 1. Auto-fix most issues
uv run ruff check --fix src/ tests/

# 2. Format code
uv run ruff format src/ tests/

# 3. Check for remaining issues
uv run ruff check src/ tests/
```

---

## All Pre-Commit Checks (11 Total)

### Check 1: Type Hints Coverage ⚠️ Warning
Functions must have type hints on parameters and return values

```python
# Required format
def func(x: int, y: str) -> bool:
    pass
```

### Check 2: No Hardcoded Secrets 🛑 Hard Error
No passwords, API keys, tokens, or credentials in code

```python
# ❌ BLOCKED
password = "secret123"

# ✅ ALLOWED
import os
password = os.getenv("DB_PASSWORD")
```

### Check 3: Test Coverage ⚠️ Warning
New source files should have corresponding tests

Rule: If multiple source files change, tests should exist

### Check 4: pyproject.toml Consistency ⚠️ Warning
New modules should register in pyproject.toml

### Check 5: No Debug Statements 🛑 Hard Error
No print(), pprint(), breakpoint() in production code

```python
# ❌ BLOCKED
print(f"Debug: {value}")

# ✅ ALLOWED
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Value: {value}")
```

### Check 6: Public API Docstrings ⚠️ Warning
Public classes and functions should have docstrings

```python
def public_function() -> None:
    """Brief description of what this does.

    Extended description if needed.
    """
    pass
```

### Check 7: Absolute Imports Only 🛑 Hard Error
No relative imports (from .. or from .)

```python
# ❌ BLOCKED
from ..core import module

# ✅ ALLOWED
from kgcl.core import module
```

### Check 8: Test Markers ⚠️ Warning
Integration tests should have pytest markers

```python
@pytest.mark.integration
def test_full_workflow():
    pass

@pytest.mark.unrdf
def test_unrdf_feature():
    pass
```

### Check 9: TODO/FIXME/WIP 🛑 HARD ERROR (NEW)
**No TODO, FIXME, WIP, HACK, or XXX markers allowed**

Complete all work before committing

### Check 10: Mypy Type Validation 🛑 HARD ERROR (NEW)
**All type warnings treated as errors**

Run: `uv run mypy src/ --strict`

### Check 11: Ruff Linting 🛑 HARD ERROR (NEW)
**All linting violations treated as errors**

Run: `uv run ruff check src/ tests/`

---

## Pre-Commit Workflow

### Before Committing

```bash
# 1. Stage your changes
git add src/modified_file.py tests/test_new_feature.py

# 2. Let pre-commit hooks run
git commit -m "Add new feature"

# 3. If hooks fail, fix issues:
uv run ruff format src/ tests/
uv run ruff check --fix src/ tests/
uv run mypy src/ --strict

# 4. Commit again
git add .
git commit -m "Add new feature"
```

### Hook Failure Example

```
$ git commit -m "Add feature"
Running KGCL pre-commit checks...
✓ Type hints: Checking type hints... ✓
✓ Secrets: Checking for hardcoded secrets... ✓
✗ TODO check: Checking for TODO/FIXME/WIP markers... ✗
   ERROR: Found TODO markers in code. All code must be complete.
   Markers found:
        # TODO: Add error handling

ERROR: Commit rejected by quality gates
Fix the issues above and try again
```

---

## Color Legend

| Color | Meaning | Impact |
|-------|---------|--------|
| 🟢 ✓ | Passed | Continues normally |
| 🔴 ✗ | Failed (Hard Error) | **Blocks commit** |
| 🟡 ⚠ | Warning | Advisory (not blocking) |
| 🔵 ⊘ | N/A | Check doesn't apply |

---

## Ignoring Hooks (Not Recommended)

**DO NOT use `--no-verify`** to bypass these hooks

```bash
# ❌ DON'T DO THIS
git commit -m "message" --no-verify

# This bypasses quality gates and will fail in CI/CD anyway
```

Why:
- These gates are designed for production safety
- Same checks run in CI/CD pipelines
- Will fail at merge time if not fixed
- Better to fix now than during review

---

## Manual Hook Verification

Run hook checks manually before commit:

```bash
# Check type safety
uv run mypy src/kgcl/hooks/ --strict

# Check linting
uv run ruff check src/kgcl/hooks/

# Check for TODO markers
grep -r "TODO\|FIXME\|WIP\|HACK\|XXX" src/kgcl/ || echo "No markers found"

# Quick format check
uv run ruff format --check src/kgcl/
```

---

## CI/CD Integration

Same checks run in GitHub Actions during merge:

```yaml
# .github/workflows/quality.yml
jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: uv run mypy src/ --strict
      - run: uv run ruff check src/ tests/
      - run: grep -r "TODO\|FIXME" src/ && exit 1 || true
```

---

## Standards by Severity

### 🛑 HARD ERRORS (Blocks Commit)
1. TODO/FIXME/WIP/HACK/XXX markers
2. Hardcoded secrets
3. Type errors/warnings (Mypy strict)
4. Linting violations (Ruff)
5. Debug statements (print/breakpoint)
6. Relative imports

### ⚠️ WARNINGS (Advisory)
1. Type hints coverage
2. Test coverage for new features
3. Docstrings for public APIs
4. Test markers for integration tests
5. Module registration in config

---

## Quick Fix Guide

### "Found TODO markers"
```bash
# Find them
grep -n "TODO\|FIXME" src/kgcl/hooks/file.py

# Fix or complete the code
# Remove the TODO comment
```

### "Mypy found type errors"
```bash
# See detailed errors
uv run mypy src/kgcl/hooks/ --strict

# Add type hints
def func(x: int) -> int:  # ← Add types

# Or use type narrowing
if isinstance(value, str):
    process_string(value)
```

### "Ruff found linting issues"
```bash
# Auto-fix most issues
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/

# See remaining issues
uv run ruff check src/ tests/
```

---

## Frequently Asked Questions

**Q: Can I work around the hook with `--no-verify`?**
A: Technically yes, but don't. These same checks run in CI/CD and will fail during merge. Better to fix now.

**Q: What if my code legitimately needs a TODO?**
A: Create a GitHub issue instead. Reference it in comments without the TODO keyword:
```python
# See issue #123 for implementation details
# This will be fixed in the next phase
```

**Q: Can I temporarily disable the hooks?**
A: Not recommended. Hooks are designed for team quality. If you need to change them, update `.githooks/pre-commit` with consensus.

**Q: How often do the hooks run?**
A: Every time you attempt to commit. Manually verify with `uv run mypy` and `uv run ruff` first.

---

## Summary

KGCL uses **11 pre-commit checks** with **3 critical hard stops**:

1. **No TODO markers** - All code must be complete
2. **Type safety** - All Mypy warnings are errors
3. **Lint clean** - All Ruff violations are errors

These ensure that every commit to the repository is:
✅ Complete
✅ Type-safe
✅ Production-quality
✅ Ready for deployment

---

**Document Version**: 2.0
**Last Updated**: 2025-11-24
**Status**: Active
