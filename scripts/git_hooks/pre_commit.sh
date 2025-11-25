#!/usr/bin/env bash

# KGCL Unified Pre-Commit Hook
# ----------------------------
# This script implements the single source of truth for all git
# pre-commit checks defined by the core team quality gates.
# Usage:
#   scripts/git_hooks/pre_commit.sh

set -euo pipefail

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

echo "Running KGCL pre-commit checks..."

echo -n "Checking type hints... "
PY_FILES="$(git diff --cached --name-only | grep -E 'src/.*\.py$' || true)"
if [ -n "$PY_FILES" ]; then
  if echo "$PY_FILES" | xargs grep -E '^\s*def\s+\w+\([^)]*\)\s*:(?!\s*->' 2>/dev/null | grep -v '@property\|@dataclass\|@staticmethod' >/dev/null; then
    echo -e "${RED}✗${NC}"
    echo "   Functions must have type hints. Use: def func(x: int) -> int:"
    FAILED=1
  else
    echo -e "${GREEN}✓${NC}"
  fi
else
  echo -e "${BLUE}⊘${NC} (no Python source files)"
fi

echo -n "Checking for hardcoded secrets... "
if git diff --cached --unified=0 | grep -E 'password|secret|api_key|token|credential' -i | grep -v '.md' >/dev/null 2>&1; then
  echo -e "${RED}✗${NC}"
  echo "   Found potential secrets in code. Use environment variables instead."
  FAILED=1
else
  echo -e "${GREEN}✓${NC}"
fi

echo -n "Checking test coverage... "
TEST_FILES="$(git diff --cached --name-only | grep -E 'tests/.*\.py$' || true)"
SRC_FILES="$(git diff --cached --name-only | grep -E 'src/.*\.py$' | grep -v '__pycache__' || true)"
if [ -n "$SRC_FILES" ] && [ -z "$TEST_FILES" ]; then
  FILE_COUNT="$(echo "$SRC_FILES" | wc -l | tr -d ' ')"
  if [ "$FILE_COUNT" -gt 2 ]; then
    echo -e "${YELLOW}⚠${NC}"
    echo "   Source files changed but no corresponding tests. Add tests in tests/ directory."
  else
    echo -e "${GREEN}✓${NC}"
  fi
else
  echo -e "${GREEN}✓${NC}"
fi

echo -n "Checking pyproject.toml consistency... "
if git diff --cached --name-only | grep -q 'src/'; then
  if ! git diff --cached --name-only | grep -q 'pyproject.toml'; then
    MODIFIED_MODULES="$(git diff --cached --name-only | grep -E 'src/kgcl/[^/]+/__init__.py$' || true)"
    if [ -n "$MODIFIED_MODULES" ]; then
      echo -e "${YELLOW}⚠${NC}"
      echo "   New modules added. Verify pyproject.toml is updated if needed."
    else
      echo -e "${GREEN}✓${NC}"
    fi
  else
    echo -e "${GREEN}✓${NC}"
  fi
else
  echo -e "${BLUE}⊘${NC} (no source changes)"
fi

echo -n "Checking for debug statements... "
if git diff --cached --no-ext-diff | grep -E '^\+.*\b(print|pprint|breakpoint)\s*\(' 2>/dev/null | grep -v 'test_' >/dev/null; then
  echo -e "${RED}✗${NC}"
  echo "   Found print/debug statements. Use logging instead."
  FAILED=1
else
  echo -e "${GREEN}✓${NC}"
fi

echo -n "Checking docstrings... "
PY_SRC="$(git diff --cached -- 'src/**/*.py' 2>/dev/null | grep '^+' | grep -E '^\+\s*(class|def)\s+[A-Z_]' || true)"
if [ -n "$PY_SRC" ]; then
  if echo "$PY_SRC" | grep -v '"""' >/dev/null; then
    echo -e "${YELLOW}⚠${NC}"
    echo "   Public APIs should have docstrings. Use NumPy style (\"\"\"docstring\"\"\")."
  else
    echo -e "${GREEN}✓${NC}"
  fi
else
  echo -e "${GREEN}✓${NC}"
fi

echo -n "Checking import style... "
if git diff --cached | grep '^+' | grep -E 'from\s+\.\.' 2>/dev/null >/dev/null; then
  echo -e "${RED}✗${NC}"
  echo "   Relative imports not allowed. Use absolute imports: from kgcl.module import X"
  FAILED=1
else
  echo -e "${GREEN}✓${NC}"
fi

echo -n "Checking test markers... "
TEST_CHANGES="$(git diff --cached -- 'tests/**/*.py' 2>/dev/null | grep '^+' | grep 'def test_' || true)"
if [ -n "$TEST_CHANGES" ]; then
  if echo "$TEST_CHANGES" | grep -E 'test_.*integration|test_.*unrdf|test_.*dspy' | grep -v '@pytest.mark' >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC}"
    echo "   Integration tests should have @pytest.mark.integration marker."
  else
    echo -e "${GREEN}✓${NC}"
  fi
else
  echo -e "${GREEN}✓${NC}"
fi

echo -n "Checking for TODO/FIXME/WIP markers... "
TODO_FOUND="$(git diff --cached -- 'src/**/*.py' 'tests/**/*.py' 2>/dev/null | grep '^+' | grep -iE '(TODO|FIXME|WIP|HACK|XXX)\s*:' | grep -v '^+++' || true)"
if [ -n "$TODO_FOUND" ]; then
  echo -e "${RED}✗${NC}"
  echo "   ERROR: Found TODO/FIXME/WIP markers in code. All code must be complete."
  echo "   Markers found:"
  echo "$TODO_FOUND" | sed 's/^+/     /'
  FAILED=1
else
  echo -e "${GREEN}✓${NC}"
fi

echo -n "Running Mypy with strict mode... "
if git diff --cached --name-only | grep -E 'src/.*\.py$' >/dev/null; then
  CHANGED_FILES="$(git diff --cached --name-only | grep -E 'src/.*\.py$' || true)"
  if uv run mypy $CHANGED_FILES --strict --warn-return-any --warn-unused-configs 2>&1 | grep -E 'error:|warning:' >/dev/null; then
    echo -e "${RED}✗${NC}"
    echo "   Mypy found type errors or warnings. Fix all issues:"
    uv run mypy $CHANGED_FILES --strict --warn-return-any --warn-unused-configs 2>&1 | head -20
    FAILED=1
  else
    echo -e "${GREEN}✓${NC}"
  fi
else
  echo -e "${BLUE}⊘${NC} (no Python source files)"
fi

echo -n "Running Ruff linting... "
if git diff --cached --name-only | grep -E '\.py$' >/dev/null; then
  CHANGED_PY_FILES="$(git diff --cached --name-only | grep -E '\.py$' || true)"
  RUFF_OUTPUT="$(uv run ruff check $CHANGED_PY_FILES 2>&1 || true)"
  if [ -n "$RUFF_OUTPUT" ] && echo "$RUFF_OUTPUT" | grep -v 'All checks passed' >/dev/null; then
    echo -e "${RED}✗${NC}"
    echo "   Ruff found linting issues:"
    echo "$RUFF_OUTPUT" | head -20
    FAILED=1
  else
    echo -e "${GREEN}✓${NC}"
  fi
else
  echo -e "${BLUE}⊘${NC} (no Python files)"
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
  echo -e "${GREEN}✓ All KGCL code quality checks passed${NC}"
  echo ""
  echo "Ready to commit. Next steps:"
  echo "  1. Format code: uv run ruff format src/ tests/"
  echo "  2. Check types: uv run mypy src/ tests/"
  echo "  3. Run tests: uv run pytest tests/"
  exit 0
else
  echo -e "${RED}✗ Some checks failed${NC}"
  echo ""
  echo "KGCL Code Quality Standards (CRITICAL):"
  echo "  • NO TODO/FIXME/WIP/HACK/XXX in code (HARD ERROR)"
  echo "  • All functions must have type hints"
  echo "  • No hardcoded secrets (use env vars)"
  echo "  • All Mypy warnings treated as errors"
  echo "  • All Ruff linting issues treated as errors"
  echo "  • New features must have tests"
  echo "  • No debug print statements (use logging)"
  echo "  • Public APIs require docstrings (NumPy style)"
  echo "  • Use absolute imports only"
  echo "  • Integration tests need @pytest.mark.integration"
  echo ""
  echo "To fix automatically:"
  echo "  uv run ruff format src/ tests/"
  echo "  uv run ruff check --fix src/ tests/"
  echo "  uv run mypy src/ --strict"
  echo ""
  exit 1
fi


