#!/usr/bin/env bash
# Simplified adversarial quality gate tests

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

PASSED=0
FAILED=0

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ADVERSARIAL QUALITY GATE TESTS (Simplified)            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Test 1: detect-lies finds TODO on main branch
echo "Test 1: detect-lies blocks TODO on main branch"
cat > /tmp/test_todo.py <<'EOF'
def test():
    # TODO: implement
    pass
EOF

OUTPUT=$(uv run python scripts/detect_implementation_lies.py /tmp/test_todo.py 2>&1 || true)
if echo "$OUTPUT" | grep -q "TODO comment"; then
    echo -e "${GREEN}✓ PASS${NC}: Detected TODO marker"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Did not detect TODO"
    echo "Output: $OUTPUT" | head -10
    FAILED=$((FAILED + 1))
fi

# Test 2: detect-lies runs in STRICT mode on main
echo ""
echo "Test 2: detect-lies runs in STRICT mode on main branch"
OUTPUT=$(uv run python scripts/detect_implementation_lies.py /tmp/test_todo.py 2>&1 || true)
if echo "$OUTPUT" | grep -q "STRICT (main/master)"; then
    echo -e "${GREEN}✓ PASS${NC}: Running in STRICT mode on main"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Not running in STRICT mode"
    echo "Output: $OUTPUT" | head -5
    FAILED=$((FAILED + 1))
fi

# Test 3: detect-lies finds stub patterns
echo ""
echo "Test 3: detect-lies finds stub implementations"
cat > /tmp/test_stub.py <<'EOF'
def incomplete():
    pass
EOF

OUTPUT=$(uv run python scripts/detect_implementation_lies.py /tmp/test_stub.py 2>&1 || true)
if echo "$OUTPUT" | grep -q "stub"; then
    echo -e "${GREEN}✓ PASS${NC}: Detected stub pattern"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Did not detect stub"
    FAILED=$((FAILED + 1))
fi

# Test 4: detect-lies finds NotImplementedError (stub pattern)
echo ""
echo "Test 4: detect-lies finds NotImplementedError"
cat > /tmp/test_notimpl.py <<'EOF'
def incomplete():
    raise NotImplementedError()
EOF

OUTPUT=$(uv run python scripts/detect_implementation_lies.py /tmp/test_notimpl.py 2>&1 || true)
# NotImplementedError is detected as stub_pattern
if echo "$OUTPUT" | grep -qi "NotImplementedError"; then
    echo -e "${GREEN}✓ PASS${NC}: Detected NotImplementedError pattern"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Did not detect NotImplementedError"
    echo "Output:"
    echo "$OUTPUT"
    FAILED=$((FAILED + 1))
fi

# Test 5: detect-lies finds meaningless assertions
echo ""
echo "Test 5: detect-lies finds meaningless assertions"
cat > /tmp/test_assert.py <<'EOF'
def test_bad():
    assert True
EOF

OUTPUT=$(uv run python scripts/detect_implementation_lies.py /tmp/test_assert.py 2>&1 || true)
if echo "$OUTPUT" | grep -q "assert True"; then
    echo -e "${GREEN}✓ PASS${NC}: Detected meaningless assertion"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Did not detect meaningless assertion"
    FAILED=$((FAILED + 1))
fi

# Test 6: poe tasks are defined
echo ""
echo "Test 6: Required poe tasks exist"
TASKS_OK=true
for task in "pre-commit-fast" "pre-push-heavy" "detect-lies" "detect-lies-staged"; do
    if ! uv run poe --help 2>&1 | grep -q "$task"; then
        echo -e "${RED}✗ FAIL${NC}: Task $task not found"
        TASKS_OK=false
        FAILED=$((FAILED + 1))
        break
    fi
done

if $TASKS_OK; then
    echo -e "${GREEN}✓ PASS${NC}: All required poe tasks exist"
    PASSED=$((PASSED + 1))
fi

# Test 7: format-check detects violations
echo ""
echo "Test 7: format-check detects violations"
cat > /tmp/test_format.py <<'EOF'
def bad(  x,y  ):
    return x+y
EOF

OUTPUT=$(uv run ruff format --check /tmp/test_format.py 2>&1 || true)
if echo "$OUTPUT" | grep -q "Would reformat"; then
    echo -e "${GREEN}✓ PASS${NC}: Format check works"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Format check didn't detect violations"
    echo "Output: $OUTPUT"
    FAILED=$((FAILED + 1))
fi

# Test 8: lint-check detects violations
echo ""
echo "Test 8: lint-check detects F841 (unused variable)"
cat > /tmp/test_lint.py <<'EOF'
def test():
    unused = 42
EOF

# Use --select F841 --no-fix to specifically test for unused variable
OUTPUT=$(uv run ruff check --select F841 --no-fix /tmp/test_lint.py 2>&1 || true)
if echo "$OUTPUT" | grep -q "F841"; then
    echo -e "${GREEN}✓ PASS${NC}: Lint check works"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Lint check didn't detect F841"
    echo "Output: $OUTPUT"
    FAILED=$((FAILED + 1))
fi

# Results
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "RESULTS: $PASSED passed, $FAILED failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ ALL QUALITY GATES WORKING                               ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ✗ SOME TESTS FAILED                                       ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
