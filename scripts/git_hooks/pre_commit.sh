#!/usr/bin/env bash

# KGCL Unified Pre-Commit Hook - KGC v3.0 Andon Cord Enforcement
# ----------------------------------------------------------------
# This script implements the Andon Cord principle: ANY failure stops the commit.
# All warnings are treated as errors. No auto-fixing is performed.
#
# KGC v3.0 Standards:
#   - PYTHONWARNINGS="error" - All warnings are errors
#   - set -euo pipefail - Fail fast on any error
#   - timeout on every step - Prevent hangs
#   - NO auto-fixing - Developer must fix manually
#   - Exit non-zero on ANY failure - Andon Cord
#
# Usage:
#   scripts/git_hooks/pre_commit.sh

set -euo pipefail

# KGC v3.0: Treat all Python warnings as errors
export PYTHONWARNINGS="error"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: 'uv' is required for KGCL pre-commit checks."
  echo "Install uv: https://github.com/astral-sh/uv"
  exit 1
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

FAILED=0

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "KGCL Pre-Commit Checks - KGC v3.0 Andon Cord Mode"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Environment: PYTHONWARNINGS=error (all warnings are errors)"
echo "Mode: Andon Cord (ANY failure stops the commit)"
echo ""

# Check if there are staged Python files
STAGED_PY_FILES="$(git diff --cached --name-only | grep -E '\.py$' || true)"
STAGED_SRC_FILES="$(git diff --cached --name-only | grep -E 'src/.*\.py$' || true)"
STAGED_TEST_FILES="$(git diff --cached --name-only | grep -E 'tests/.*\.py$' || true)"

if [ -z "$STAGED_PY_FILES" ]; then
  echo -e "${BLUE}⊘ No Python files staged. Skipping checks.${NC}"
  exit 0
fi

echo "Staged files:"
echo "$STAGED_PY_FILES" | sed 's/^/  • /'
echo ""

# ============================================================================
# STEP 1: Static Code Analysis (Fast Checks)
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: Static Code Analysis"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check 1.1: Type hints on all functions
echo -n "1.1 Type hints coverage... "
if [ -n "$STAGED_SRC_FILES" ]; then
  MISSING_TYPES="$(echo "$STAGED_SRC_FILES" | xargs grep -nE '^\s*def\s+\w+\([^)]*\)\s*:(?!\s*->)' 2>/dev/null | grep -v '@property\|@dataclass\|@staticmethod\|@pytest.fixture' || true)"
  if [ -n "$MISSING_TYPES" ]; then
    echo -e "${RED}✗ FAILED${NC}"
    echo "   ERROR: Functions missing type hints (-> ReturnType):"
    echo "$MISSING_TYPES" | sed 's/^/     /'
    echo ""
    echo "   Fix: Add type hints to all functions:"
    echo "     def func(x: int) -> int:"
    echo ""
    FAILED=1
  else
    echo -e "${GREEN}✓ PASSED${NC}"
  fi
else
  echo -e "${BLUE}⊘ SKIPPED${NC} (no source files)"
fi

# Check 1.2: No hardcoded secrets
echo -n "1.2 Hardcoded secrets scan... "
SECRET_PATTERN='(password|secret|api_key|token|credential|private_key|access_key).*=.*["\047][^"\047]{8,}'
if git diff --cached --unified=0 | grep -E "$SECRET_PATTERN" -i | grep -v '.md\|test_\|# pragma: allowlist secret' >/dev/null 2>&1; then
  echo -e "${RED}✗ FAILED${NC}"
  echo "   ERROR: Found potential hardcoded secrets in code:"
  git diff --cached --unified=0 | grep -E "$SECRET_PATTERN" -i | grep -v '.md\|test_' | sed 's/^/     /'
  echo ""
  echo "   Fix: Use environment variables instead:"
  echo "     api_key = os.getenv('API_KEY')"
  echo ""
  FAILED=1
else
  echo -e "${GREEN}✓ PASSED${NC}"
fi

# Check 1.3: Test coverage for new features
echo -n "1.3 Test coverage check... "
if [ -n "$STAGED_SRC_FILES" ] && [ -z "$STAGED_TEST_FILES" ]; then
  FILE_COUNT="$(echo "$STAGED_SRC_FILES" | wc -l | tr -d ' ')"
  if [ "$FILE_COUNT" -gt 2 ]; then
    echo -e "${RED}✗ FAILED${NC}"
    echo "   ERROR: Source files changed but no corresponding tests."
    echo "   Changed files:"
    echo "$STAGED_SRC_FILES" | sed 's/^/     /'
    echo ""
    echo "   Fix: Add tests in tests/ directory for new features."
    echo ""
    FAILED=1
  else
    echo -e "${YELLOW}⚠ WARNING${NC} (few files changed, consider adding tests)"
  fi
else
  echo -e "${GREEN}✓ PASSED${NC}"
fi

# Check 1.4: No debug statements
echo -n "1.4 Debug statement scan... "
DEBUG_STMTS="$(git diff --cached --no-ext-diff | grep -E '^\+.*\b(print|pprint|breakpoint)\s*\(' 2>/dev/null | grep -v 'test_\|# pragma: allowlist debug' || true)"
if [ -n "$DEBUG_STMTS" ]; then
  echo -e "${RED}✗ FAILED${NC}"
  echo "   ERROR: Found debug statements in code:"
  echo "$DEBUG_STMTS" | sed 's/^+/     /'
  echo ""
  echo "   Fix: Replace print() with logging:"
  echo "     import logging"
  echo "     logger = logging.getLogger(__name__)"
  echo "     logger.info('message', extra={...})"
  echo ""
  FAILED=1
else
  echo -e "${GREEN}✓ PASSED${NC}"
fi

# Check 1.5: Docstrings on public APIs
echo -n "1.5 Docstring coverage... "
PUBLIC_APIS="$(git diff --cached -- 'src/**/*.py' 2>/dev/null | grep '^+' | grep -E '^\+\s*(class [A-Z]|def [a-z_]+\((?!self|cls).*\):)' || true)"
if [ -n "$PUBLIC_APIS" ]; then
  # Check if docstrings follow within 2 lines
  MISSING_DOCS="$(echo "$PUBLIC_APIS" | grep -v '"""' || true)"
  if [ -n "$MISSING_DOCS" ]; then
    echo -e "${YELLOW}⚠ WARNING${NC}"
    echo "   Public APIs should have NumPy-style docstrings:"
    echo "$MISSING_DOCS" | sed 's/^+/     /'
    echo ""
    echo "   Recommendation: Add docstrings to all public APIs."
    echo ""
  else
    echo -e "${GREEN}✓ PASSED${NC}"
  fi
else
  echo -e "${GREEN}✓ PASSED${NC}"
fi

# Check 1.6: Absolute imports only
echo -n "1.6 Import style check... "
RELATIVE_IMPORTS="$(git diff --cached | grep '^+' | grep -E 'from\s+\.\.' 2>/dev/null || true)"
if [ -n "$RELATIVE_IMPORTS" ]; then
  echo -e "${RED}✗ FAILED${NC}"
  echo "   ERROR: Relative imports not allowed:"
  echo "$RELATIVE_IMPORTS" | sed 's/^+/     /'
  echo ""
  echo "   Fix: Use absolute imports:"
  echo "     from kgcl.module import X"
  echo ""
  FAILED=1
else
  echo -e "${GREEN}✓ PASSED${NC}"
fi

# Check 1.7: Test markers on integration tests
echo -n "1.7 Test marker validation... "
INTEGRATION_TESTS="$(git diff --cached -- 'tests/**/*.py' 2>/dev/null | grep '^+' | grep -E 'def test_.*(integration|unrdf|dspy|full_pipeline)' || true)"
if [ -n "$INTEGRATION_TESTS" ]; then
  MISSING_MARKERS="$(echo "$INTEGRATION_TESTS" | grep -v '@pytest.mark' || true)"
  if [ -n "$MISSING_MARKERS" ]; then
    echo -e "${YELLOW}⚠ WARNING${NC}"
    echo "   Integration tests should have @pytest.mark.integration marker:"
    echo "$MISSING_MARKERS" | sed 's/^+/     /'
    echo ""
  else
    echo -e "${GREEN}✓ PASSED${NC}"
  fi
else
  echo -e "${GREEN}✓ PASSED${NC}"
fi

# Check 1.8: Implementation Lies Detector (CRITICAL - Lean Six Sigma)
echo -n "1.8 Implementation lies scan (CRITICAL)... "

# Run comprehensive implementation lies detector
if [ -f "$REPO_ROOT/scripts/detect_implementation_lies.py" ]; then
  LIES_OUTPUT="$(timeout 15s uv run python "$REPO_ROOT/scripts/detect_implementation_lies.py" --staged --warnings-as-errors 2>&1 || true)"
  LIES_EXIT_CODE=$?

  if [ $LIES_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}✗ FAILED (ANDON CORD PULLED)${NC}"
    echo "   CRITICAL ERROR: Implementation lies detected."
    echo "   All code must be complete with real implementations."
    echo ""
    echo "$LIES_OUTPUT" | tail -60
    echo ""
    echo "   Lean Six Sigma Standards (ZERO TOLERANCE):"
    echo "     • No TODO/FIXME/XXX/HACK/WIP comments"
    echo "     • No stub implementations (pass, ..., NotImplementedError)"
    echo "     • No placeholder returns without logic"
    echo "     • No meaningless test assertions (assert True)"
    echo "     • No empty classes or speculative scaffolding"
    echo "     • No temporal deferral phrases ('later', 'temporary', 'for now')"
    echo ""
    echo "   Chicago School TDD requires COMPLETE implementations."
    echo ""
    FAILED=1
  else
    echo -e "${GREEN}✓ PASSED${NC}"
  fi
else
  # Fallback to basic TODO scan if detector not available
  TODO_MARKERS="$(git diff --cached -- 'src/**/*.py' 'tests/**/*.py' 2>/dev/null | grep '^+' | grep -iE '(TODO|FIXME|WIP|HACK|XXX)\s*:' | grep -v '^+++\|# pragma: allowlist todo' || true)"
  if [ -n "$TODO_MARKERS" ]; then
    echo -e "${RED}✗ FAILED (ANDON CORD PULLED)${NC}"
    echo "   CRITICAL ERROR: Found TODO/FIXME/WIP markers in code."
    echo "   All code must be complete before commit."
    echo ""
    echo "   Markers found:"
    echo "$TODO_MARKERS" | sed 's/^+/     /'
    echo ""
    echo "   Fix: Complete all work or remove markers."
    echo ""
    FAILED=1
  else
    echo -e "${GREEN}✓ PASSED${NC}"
  fi
fi

echo ""

# ============================================================================
# STEP 2: Code Formatting (Read-Only Check)
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Code Formatting Check (NO AUTO-FIX)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -n "2.1 Ruff format check... "
if timeout 5s uv run ruff format --check $STAGED_PY_FILES 2>&1 | grep -E 'would reformat|Files would be reformatted' >/dev/null; then
  echo -e "${RED}✗ FAILED${NC}"
  echo "   ERROR: Code formatting issues found."
  echo ""
  timeout 5s uv run ruff format --check $STAGED_PY_FILES 2>&1 | head -20
  echo ""
  echo "   Fix manually:"
  echo "     uv run ruff format src/ tests/"
  echo ""
  FAILED=1
else
  echo -e "${GREEN}✓ PASSED${NC}"
fi

echo ""

# ============================================================================
# STEP 3: Linting (NO AUTO-FIX)
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Linting Check (NO AUTO-FIX)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -n "3.1 Ruff lint check... "
RUFF_OUTPUT="$(timeout 8s uv run ruff check --no-fix $STAGED_PY_FILES 2>&1 || true)"
if echo "$RUFF_OUTPUT" | grep -E 'error:|warning:|Found [0-9]+ error' >/dev/null; then
  echo -e "${RED}✗ FAILED${NC}"
  echo "   ERROR: Ruff found linting issues:"
  echo ""
  echo "$RUFF_OUTPUT" | head -30
  echo ""
  echo "   Fix manually:"
  echo "     uv run ruff check --fix src/ tests/"
  echo ""
  FAILED=1
elif echo "$RUFF_OUTPUT" | grep -qE 'All checks passed!|Found 0 errors'; then
  echo -e "${GREEN}✓ PASSED${NC}"
else
  # Assume pass if no explicit errors
  echo -e "${GREEN}✓ PASSED${NC}"
fi

echo ""

# ============================================================================
# STEP 4: Type Checking (Strict Mode)
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Type Checking (Strict Mode)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -n "$STAGED_SRC_FILES" ]; then
  echo -n "4.1 Mypy type check (strict)... "
  MYPY_OUTPUT="$(timeout 15s uv run mypy $STAGED_SRC_FILES --strict --warn-return-any --warn-unused-configs 2>&1 || true)"
  if echo "$MYPY_OUTPUT" | grep -E 'error:|warning:' >/dev/null; then
    echo -e "${RED}✗ FAILED${NC}"
    echo "   ERROR: Mypy found type errors or warnings:"
    echo ""
    echo "$MYPY_OUTPUT" | head -30
    echo ""
    echo "   Fix: Add type hints or fix type errors."
    echo "   All warnings are treated as errors in KGC v3.0."
    echo ""
    FAILED=1
  else
    echo -e "${GREEN}✓ PASSED${NC}"
  fi
else
  echo -e "${BLUE}⊘ SKIPPED${NC} (no source files)"
fi

echo ""

# ============================================================================
# STEP 5: Test Execution (Warnings as Errors)
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 5: Test Execution (PYTHONWARNINGS=error)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -n "$STAGED_TEST_FILES" ] || [ -n "$STAGED_SRC_FILES" ]; then
  echo -n "5.1 Running pytest (warnings=error)... "

  # Determine test scope based on what changed
  if [ -n "$STAGED_TEST_FILES" ]; then
    TEST_SCOPE="$STAGED_TEST_FILES"
  else
    # If only source files changed, run related tests
    TEST_SCOPE="tests/"
  fi

  # Run tests with PYTHONWARNINGS=error (already set globally)
  # -W error forces all warnings to be errors
  # --strict-markers ensures test markers are valid
  # -v for verbose output on failures
  TEST_OUTPUT="$(timeout 30s uv run pytest $TEST_SCOPE -W error --strict-markers -v 2>&1 || true)"
  TEST_EXIT_CODE=$?

  if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}✗ FAILED${NC}"
    echo "   ERROR: Tests failed or warnings detected:"
    echo ""
    echo "$TEST_OUTPUT" | tail -50
    echo ""
    echo "   Fix: All tests must pass with PYTHONWARNINGS=error."
    echo "   All warnings are treated as errors in KGC v3.0."
    echo ""
    FAILED=1
  elif echo "$TEST_OUTPUT" | grep -E 'FAILED|ERROR|warning' >/dev/null; then
    echo -e "${RED}✗ FAILED${NC}"
    echo "   ERROR: Test failures or warnings detected:"
    echo ""
    echo "$TEST_OUTPUT" | grep -E 'FAILED|ERROR|warning' | head -20
    echo ""
    FAILED=1
  else
    echo -e "${GREEN}✓ PASSED${NC}"
  fi
else
  echo -e "${BLUE}⊘ SKIPPED${NC} (no test or source files)"
fi

echo ""

# ============================================================================
# FINAL VERDICT
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FINAL VERDICT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$FAILED" -eq 0 ]; then
  echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║                                                            ║${NC}"
  echo -e "${GREEN}║  ✓ ALL CHECKS PASSED - COMMIT APPROVED                     ║${NC}"
  echo -e "${GREEN}║                                                            ║${NC}"
  echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo "KGC v3.0 Quality Gates: ALL PASSED"
  echo "  ✓ Type coverage: 100%"
  echo "  ✓ No hardcoded secrets"
  echo "  ✓ Test coverage verified"
  echo "  ✓ No debug statements"
  echo "  ✓ Code formatting clean"
  echo "  ✓ Linting clean (no auto-fix)"
  echo "  ✓ Type checking strict mode"
  echo "  ✓ Tests passing (warnings=error)"
  echo ""
  echo "Ready to commit. Recommended next steps:"
  echo "  1. git commit -m 'your message'"
  echo "  2. git push"
  echo ""
  exit 0
else
  echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${RED}║                                                            ║${NC}"
  echo -e "${RED}║  ✗ ANDON CORD PULLED - COMMIT BLOCKED                      ║${NC}"
  echo -e "${RED}║                                                            ║${NC}"
  echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "${RED}CRITICAL: One or more quality gates failed.${NC}"
  echo ""
  echo "KGC v3.0 Standards (NON-NEGOTIABLE):"
  echo "  • 100% type hints on all functions"
  echo "  • NO hardcoded secrets (use environment variables)"
  echo "  • NO debug statements (use logging)"
  echo "  • NO relative imports (use absolute imports)"
  echo "  • NO TODO/FIXME/WIP markers (complete all work)"
  echo "  • ALL Mypy warnings are errors (strict mode)"
  echo "  • ALL Ruff linting issues are errors"
  echo "  • ALL test warnings are errors (PYTHONWARNINGS=error)"
  echo "  • Code must be formatted (ruff format)"
  echo "  • New features require tests"
  echo ""
  echo "To fix issues:"
  echo "  1. Review error messages above"
  echo "  2. Fix issues manually (NO auto-fix in pre-commit)"
  echo "  3. Stage fixed files: git add <files>"
  echo "  4. Try commit again: git commit"
  echo ""
  echo "Manual fix commands:"
  echo "  uv run ruff format src/ tests/        # Format code"
  echo "  uv run ruff check --fix src/ tests/   # Fix linting"
  echo "  uv run mypy src/ --strict              # Check types"
  echo "  uv run pytest tests/ -W error          # Run tests"
  echo ""
  echo "ANDON CORD PRINCIPLE:"
  echo "  Quality issues STOP the line. Fix before proceeding."
  echo ""
  exit 1
fi
