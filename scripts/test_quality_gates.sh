#!/usr/bin/env bash
#
# Adversarial Quality Gate Testing
# ==================================
# Tests that git hooks and quality gates actually block defects.
#
# Tests:
# 1. Pre-commit blocks TODO on main branch
# 2. Pre-commit allows TODO on feature branch
# 3. Pre-commit blocks format violations
# 4. Pre-commit blocks lint violations
# 5. Pre-push blocks test failures
# 6. Pre-push blocks type errors
# 7. Branch-aware validation works correctly
#
# Usage:
#   bash scripts/test_quality_gates.sh
#
# Exit codes:
#   0 - All tests passed
#   1 - One or more tests failed

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up test artifacts..."

    # Remove test files
    rm -f src/kgcl/_test_adversarial_*.py
    rm -f tests/_test_adversarial_*.py

    # Unstage any staged files
    git reset HEAD -- src/kgcl/_test_adversarial_*.py 2>/dev/null || true
    git reset HEAD -- tests/_test_adversarial_*.py 2>/dev/null || true

    # Switch back to original branch if we created a test branch
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$CURRENT_BRANCH" = "test-quality-gates-temp" ]; then
        git checkout master 2>/dev/null || git checkout main 2>/dev/null || true
        git branch -D test-quality-gates-temp 2>/dev/null || true
    fi
}

trap cleanup EXIT

# Test runner
run_test() {
    local test_name="$1"
    local test_func="$2"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "TEST: $test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if $test_func; then
        echo -e "${GREEN}✓ PASSED${NC}: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAILED${NC}: $test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("$test_name")
    fi
}

# ============================================================================
# Test 1: Pre-commit blocks TODO on main branch
# ============================================================================
test_precommit_blocks_todo_on_main() {
    # Ensure we're on main/master
    git checkout master 2>/dev/null || git checkout main 2>/dev/null || return 1

    # Create file with TODO
    cat > src/kgcl/_test_adversarial_todo.py <<'EOF'
def test_function():
    # TODO: implement this later
    pass
EOF

    # Stage file
    git add src/kgcl/_test_adversarial_todo.py

    # Run pre-commit hook - should FAIL
    if bash scripts/git_hooks/pre-commit 2>&1 | grep -q "ANDON CORD PULLED"; then
        echo "  → Correctly blocked TODO on main branch"
        return 0
    else
        echo "  → ERROR: Failed to block TODO on main branch"
        return 1
    fi
}

# ============================================================================
# Test 2: Pre-commit allows TODO on feature branch
# ============================================================================
test_precommit_allows_todo_on_feature() {
    # Create feature branch
    git checkout -b test-quality-gates-temp 2>/dev/null || return 1

    # Create file with TODO
    cat > src/kgcl/_test_adversarial_todo_feature.py <<'EOF'
def test_function():
    # TODO: work in progress on feature branch
    pass
EOF

    # Stage file
    git add src/kgcl/_test_adversarial_todo_feature.py

    # Run detect-lies directly with branch awareness
    if uv run python scripts/detect_implementation_lies.py --staged 2>&1 | grep -q "RELAXED (feature branch)"; then
        echo "  → Correctly allowed TODO on feature branch"

        # Switch back to main
        git checkout master 2>/dev/null || git checkout main 2>/dev/null
        return 0
    else
        echo "  → ERROR: Branch-aware validation not working"
        git checkout master 2>/dev/null || git checkout main 2>/dev/null
        return 1
    fi
}

# ============================================================================
# Test 3: Pre-commit blocks format violations
# ============================================================================
test_precommit_blocks_format_violations() {
    # Ensure we're on main
    git checkout master 2>/dev/null || git checkout main 2>/dev/null || return 1

    # Create file with format violations
    cat > src/kgcl/_test_adversarial_format.py <<'EOF'
def badly_formatted(  x,y,   z  ):
    return x+y+z
EOF

    # Stage file
    git add src/kgcl/_test_adversarial_format.py

    # Run format check
    if ! uv run poe format-check 2>&1 | grep -q "would be reformatted"; then
        echo "  → ERROR: Format check didn't detect violations"
        return 1
    fi

    echo "  → Correctly detected format violations"
    return 0
}

# ============================================================================
# Test 4: Pre-commit blocks lint violations
# ============================================================================
test_precommit_blocks_lint_violations() {
    # Create file with lint violations
    cat > src/kgcl/_test_adversarial_lint.py <<'EOF'
def test_function():
    unused_variable = 42  # F841 violation
    return None
EOF

    # Stage file
    git add src/kgcl/_test_adversarial_lint.py

    # Run lint check
    if uv run poe lint-check 2>&1 | grep -q "F841"; then
        echo "  → Correctly detected lint violations"
        return 0
    else
        echo "  → ERROR: Lint check didn't detect F841 violation"
        return 1
    fi
}

# ============================================================================
# Test 5: detect-lies finds implementation lies
# ============================================================================
test_detect_lies_finds_stubs() {
    # Create file with stub patterns
    cat > src/kgcl/_test_adversarial_stub.py <<'EOF'
def incomplete_function():
    """This is incomplete."""
    pass

def another_stub():
    raise NotImplementedError
EOF

    # Stage file
    git add src/kgcl/_test_adversarial_stub.py

    # Ensure we're on main for strict mode
    git checkout master 2>/dev/null || git checkout main 2>/dev/null || return 1

    # Run detect-lies
    if uv run poe detect-lies 2>&1 | grep -q "stub"; then
        echo "  → Correctly detected stub implementations"
        return 0
    else
        echo "  → ERROR: Didn't detect stub patterns"
        return 1
    fi
}

# ============================================================================
# Test 6: Poe tasks execute correctly
# ============================================================================
test_poe_tasks_execute() {
    # Test that poe tasks are properly defined
    if ! uv run poe --help 2>&1 | grep -q "pre-commit-fast"; then
        echo "  → ERROR: pre-commit-fast task not found"
        return 1
    fi

    if ! uv run poe --help 2>&1 | grep -q "pre-push-heavy"; then
        echo "  → ERROR: pre-push-heavy task not found"
        return 1
    fi

    if ! uv run poe --help 2>&1 | grep -q "detect-lies"; then
        echo "  → ERROR: detect-lies task not found"
        return 1
    fi

    echo "  → All poe tasks properly defined"
    return 0
}

# ============================================================================
# Test 7: Branch detection works correctly
# ============================================================================
test_branch_detection() {
    # Test main branch detection
    git checkout master 2>/dev/null || git checkout main 2>/dev/null || return 1
    CURRENT=$(git rev-parse --abbrev-ref HEAD)

    # Create test file to check mode
    cat > src/kgcl/_test_adversarial_branch.py <<'EOF'
def test(): pass
EOF

    # Run detect-lies and check mode
    OUTPUT=$(uv run python scripts/detect_implementation_lies.py src/kgcl/_test_adversarial_branch.py 2>&1)

    if echo "$OUTPUT" | grep -q "STRICT (main/master)"; then
        echo "  → Correctly detected main/master branch (STRICT mode)"
    else
        echo "  → ERROR: Should be STRICT mode on main/master"
        return 1
    fi

    # Create feature branch
    git checkout -b test-quality-gates-temp 2>/dev/null || return 1

    # Run detect-lies and check mode
    OUTPUT=$(uv run python scripts/detect_implementation_lies.py src/kgcl/_test_adversarial_branch.py 2>&1)

    if echo "$OUTPUT" | grep -q "RELAXED (feature branch)"; then
        echo "  → Correctly detected feature branch (RELAXED mode)"
        git checkout master 2>/dev/null || git checkout main 2>/dev/null
        return 0
    else
        echo "  → ERROR: Should be RELAXED mode on feature branch"
        git checkout master 2>/dev/null || git checkout main 2>/dev/null
        return 1
    fi
}

# ============================================================================
# Test 8: Test meaningful assertion detection
# ============================================================================
test_detect_meaningless_assertions() {
    cat > tests/_test_adversarial_assertions.py <<'EOF'
def test_meaningless():
    """Bad test with meaningless assertion."""
    result = do_something()
    assert True  # Meaningless!

def test_another_bad():
    """Another bad test."""
    assert result  # Just checking truthy
EOF

    # Run detect-lies on tests
    if uv run python scripts/detect_implementation_lies.py tests/_test_adversarial_assertions.py 2>&1 | grep -q "assert True"; then
        echo "  → Correctly detected meaningless assertions"
        return 0
    else
        echo "  → ERROR: Didn't detect meaningless assertions"
        return 1
    fi
}

# ============================================================================
# Main Test Execution
# ============================================================================

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║       ADVERSARIAL QUALITY GATE TESTING                     ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Testing that quality gates actually block defects..."

# Run all tests
run_test "Pre-commit blocks TODO on main branch" test_precommit_blocks_todo_on_main
run_test "Pre-commit allows TODO on feature branch" test_precommit_allows_todo_on_feature
run_test "Pre-commit blocks format violations" test_precommit_blocks_format_violations
run_test "Pre-commit blocks lint violations" test_precommit_blocks_lint_violations
run_test "detect-lies finds stub implementations" test_detect_lies_finds_stubs
run_test "Poe tasks are properly defined" test_poe_tasks_execute
run_test "Branch detection works correctly" test_branch_detection
run_test "Detect meaningless test assertions" test_detect_meaningless_assertions

# Results
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Total tests: $((TESTS_PASSED + TESTS_FAILED))"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}FAILED TESTS:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo "  - $test"
    done
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ✗ QUALITY GATES NOT WORKING CORRECTLY                     ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 1
else
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ ALL QUALITY GATES WORKING CORRECTLY                     ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 0
fi
