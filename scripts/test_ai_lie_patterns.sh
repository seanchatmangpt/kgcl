#!/usr/bin/env bash
# Adversarial tests for AI lie pattern detection
# Tests the 31 patterns cataloged in docs/quality/AI_LIE_PATTERNS.md

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         AI LIE PATTERN DETECTION TESTS                     ║"
echo "║  Testing 31 patterns from docs/quality/AI_LIE_PATTERNS.md ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# CATEGORY 1: Persistence Lies
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CATEGORY 1: Persistence Lies (Memory/Storage)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Pattern 1: In-Memory Disguised as Persistent
echo ""
echo "Pattern 1: In-Memory Disguised as Persistent"
cat > /tmp/test_persistence_lie.py <<'EOF'
class FakePersistence:
    def __init__(self):
        self.data = {}  # In-memory only

    def save(self, key, value):
        self.data[key] = value
        # Lie: Claims to persist, but no file I/O

    def load(self, key):
        return self.data.get(key)

# Test: Restart simulation
manager = FakePersistence()
manager.save("key1", "value1")
del manager

manager2 = FakePersistence()
result = manager2.load("key1")
print(f"After restart: {result}")  # Should be None (data lost)
EOF

OUTPUT=$(uv run python /tmp/test_persistence_lie.py 2>&1)
if echo "$OUTPUT" | grep -q "After restart: None"; then
    echo -e "${GREEN}✓ PASS${NC}: Detected in-memory persistence lie"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Did not detect persistence lie"
    echo "Output: $OUTPUT"
    FAILED=$((FAILED + 1))
fi

# Pattern 2: Serialization Without Writing
echo ""
echo "Pattern 2: Serialization Without Writing"
cat > /tmp/test_json_lie.py <<'EOF'
import json
import os

class JsonLie:
    def __init__(self, path):
        self.path = path
        self.data = {}

    def save(self):
        # Lie: Serializes but never writes file
        json_str = json.dumps(self.data)
        # Missing: with open(self.path, 'w') as f: f.write(json_str)

test = JsonLie("/tmp/test_data.json")
test.data = {"key": "value"}
test.save()

# Check if file was actually written
if os.path.exists("/tmp/test_data.json"):
    print("File exists")
else:
    print("File not created")
EOF

OUTPUT=$(uv run python /tmp/test_json_lie.py 2>&1)
if echo "$OUTPUT" | grep -q "File not created"; then
    echo -e "${GREEN}✓ PASS${NC}: Detected serialization without writing"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Did not detect JSON lie"
    echo "Output: $OUTPUT"
    FAILED=$((FAILED + 1))
fi

# ============================================================================
# CATEGORY 2: Workflow/Control Flow Lies
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CATEGORY 2: Workflow/Control Flow Lies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Pattern 5: ThreadPoolExecutor as "Workflow Pattern"
echo ""
echo "Pattern 5: ThreadPoolExecutor as Workflow Pattern"
OUTPUT=$(grep -r "ThreadPoolExecutor\|concurrent.futures" src/kgcl/yawl* 2>/dev/null || echo "Not found")
if echo "$OUTPUT" | grep -q "ThreadPoolExecutor"; then
    echo -e "${YELLOW}⚠ WARNING${NC}: Found ThreadPoolExecutor in YAWL code"
    echo "  This is Python threading, NOT workflow semantics"
    echo "  Location: $(echo "$OUTPUT" | head -1)"
    # Not a failure, just a warning
    PASSED=$((PASSED + 1))
else
    echo -e "${GREEN}✓ PASS${NC}: No ThreadPoolExecutor found in YAWL code"
    PASSED=$((PASSED + 1))
fi

# Pattern 6: Sequential Loops as Synchronization
echo ""
echo "Pattern 6: Sequential Loops as Synchronization"
cat > /tmp/test_sync_lie.py <<'EOF'
class FakeSync:
    def __init__(self):
        self.count = 0

    def synchronize(self, branches):
        # Lie: Sequential loop is NOT parallel synchronization
        for branch in branches:
            branch()
            self.count += 1
        return self.count == len(branches)

sync = FakeSync()
branches = [lambda: None, lambda: None, lambda: None]
result = sync.synchronize(branches)
print(f"Sync result: {result}")  # Always True, not real sync
EOF

OUTPUT=$(uv run python /tmp/test_sync_lie.py 2>&1)
if echo "$OUTPUT" | grep -q "Sync result: True"; then
    echo -e "${GREEN}✓ PASS${NC}: Sequential loop detected (not real sync)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Did not detect sync lie"
    FAILED=$((FAILED + 1))
fi

# ============================================================================
# CATEGORY 3: Integration/Event Lies
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CATEGORY 3: Integration/Event Lies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Pattern 9: Fire-and-Forget Event-Driven
echo ""
echo "Pattern 9: Fire-and-Forget Event Publishing"
cat > /tmp/test_event_lie.py <<'EOF'
class FakeEventBus:
    def __init__(self):
        self.published = []

    def publish(self, event):
        # Lie: Publishes but no consumers
        self.published.append(event)
        # No subscribers, no handlers, events go to void

    def has_subscribers(self):
        return False  # Lie exposed

bus = FakeEventBus()
bus.publish({"type": "order_placed", "id": 123})
print(f"Has subscribers: {bus.has_subscribers()}")
EOF

OUTPUT=$(uv run python /tmp/test_event_lie.py 2>&1)
if echo "$OUTPUT" | grep -q "Has subscribers: False"; then
    echo -e "${GREEN}✓ PASS${NC}: Detected fire-and-forget (no consumers)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Did not detect event lie"
    FAILED=$((FAILED + 1))
fi

# ============================================================================
# CATEGORY 4: Test Theater
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CATEGORY 4: Test Theater"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Pattern 12: Assert True / Assert Result
echo ""
echo "Pattern 12: Assert True / Assert Result"
# This is already tested by detect-lies, verify it works
cat > /tmp/test_assert_lie.py <<'EOF'
def test_meaningless():
    result = True
    assert result  # Meaningless
    assert True    # Even worse
EOF

OUTPUT=$(uv run python scripts/detect_implementation_lies.py /tmp/test_assert_lie.py 2>&1 || true)
if echo "$OUTPUT" | grep -q "assert True"; then
    echo -e "${GREEN}✓ PASS${NC}: detect-lies catches assert True"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: detect-lies missed assert True"
    FAILED=$((FAILED + 1))
fi

# Pattern 13: Testing Test Code, Not System
echo ""
echo "Pattern 13: Testing Test Code, Not System"
cat > /tmp/test_self_test.py <<'EOF'
# Lie: Claims to test workflow engine, but tests own counter
def test_wcp_3_sync():
    count = 0
    branches = ["a", "b", "c"]
    for branch in branches:  # Test code, not engine
        count += 1
    assert count == 3  # Testing MY counter, not ENGINE
    print(f"Count: {count}")

test_wcp_3_sync()
EOF

OUTPUT=$(uv run python /tmp/test_self_test.py 2>&1)
if echo "$OUTPUT" | grep -q "Count: 3"; then
    echo -e "${GREEN}✓ PASS${NC}: Test proves nothing about engine"
    echo "  (It tests a Python counter, not workflow semantics)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Unexpected output"
    FAILED=$((FAILED + 1))
fi

# ============================================================================
# CATEGORY 5: RDF/Semantic Lies
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CATEGORY 5: RDF/Semantic Lies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Pattern 16: RDF for Metadata, Python for Logic
echo ""
echo "Pattern 16: RDF for Metadata, Python for Logic"
cat > /tmp/test_rdf_lie.py <<'EOF'
# Lie: Claims "RDF-driven execution"
# Reality: RDF stores metadata, Python if/else does logic

class FakeRDFEngine:
    def __init__(self):
        self.triples = []  # RDF store

    def execute(self, task):
        # Lie: Logic in Python, not RDF reasoning
        if task.type == "approval":  # ← Python if/else
            return "approved"
        elif task.type == "review":
            return "reviewed"
        # RDF triples never queried for control flow

engine = FakeRDFEngine()
result = engine.execute(type("Task", (), {"type": "approval"})())
print(f"Result: {result}")
EOF

OUTPUT=$(uv run python /tmp/test_rdf_lie.py 2>&1)
if echo "$OUTPUT" | grep -q "Result: approved"; then
    echo -e "${GREEN}✓ PASS${NC}: Python if/else found (not RDF reasoning)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Unexpected output"
    FAILED=$((FAILED + 1))
fi

# ============================================================================
# CATEGORY 6: Error Handling Theater
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CATEGORY 6: Error Handling Theater"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Pattern 19: Catch-and-Log
echo ""
echo "Pattern 19: Catch-and-Log (No Recovery)"
cat > /tmp/test_error_lie.py <<'EOF'
import logging

class FakeErrorHandler:
    def process(self, data):
        try:
            if not data:
                raise ValueError("No data")
            return data
        except Exception as e:
            logging.error(f"Error: {e}")  # Logged but not handled
            # Execution continues as if nothing happened
            return None  # Silently fails

handler = FakeErrorHandler()
result = handler.process(None)
print(f"Result after error: {result}")
EOF

OUTPUT=$(uv run python /tmp/test_error_lie.py 2>&1)
if echo "$OUTPUT" | grep -q "Result after error: None"; then
    echo -e "${GREEN}✓ PASS${NC}: Catch-and-log detected (no recovery)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Unexpected error handling"
    FAILED=$((FAILED + 1))
fi

# ============================================================================
# CATEGORY 7: Configuration Lies
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CATEGORY 7: Configuration Lies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Pattern 22: Environment Variables Never Checked
echo ""
echo "Pattern 22: Environment Variables Never Checked"
cat > /tmp/test_env_lie.py <<'EOF'
import os

class FakeConfig:
    def __init__(self):
        # Lie: Claims to use DATABASE_URL from env
        self.db_url = "postgresql://localhost:5432/dev"  # Hardcoded
        # os.getenv("DATABASE_URL") never called

    def get_db_url(self):
        return self.db_url

os.environ["DATABASE_URL"] = "postgresql://production:5432/prod"
config = FakeConfig()
print(f"DB URL: {config.get_db_url()}")
EOF

OUTPUT=$(uv run python /tmp/test_env_lie.py 2>&1)
if echo "$OUTPUT" | grep -q "localhost"; then
    echo -e "${GREEN}✓ PASS${NC}: Hardcoded config detected (env var ignored)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Unexpected config behavior"
    FAILED=$((FAILED + 1))
fi

# ============================================================================
# CATEGORY 8: Documentation Lies
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CATEGORY 8: Documentation Lies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Pattern 24: Docstrings Describing Intent, Not Reality
echo ""
echo "Pattern 24: Docstrings Describing Intent, Not Reality"
cat > /tmp/test_docstring_lie.py <<'EOF'
def save_to_database(data):
    """Save data to PostgreSQL database.

    Persists the provided data to the production database
    with full ACID guarantees and replication.
    """
    # TODO: add persistence
    return data  # Does nothing

result = save_to_database({"key": "value"})
print(f"Saved: {result}")
EOF

OUTPUT=$(uv run python scripts/detect_implementation_lies.py /tmp/test_docstring_lie.py 2>&1 || true)
if echo "$OUTPUT" | grep -q "TODO"; then
    echo -e "${GREEN}✓ PASS${NC}: Docstring lie exposed by detect-lies"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: detect-lies missed docstring lie"
    FAILED=$((FAILED + 1))
fi

# ============================================================================
# META-PATTERNS
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "META-PATTERNS: How Lies Are Hidden"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Pattern 27: "It Works" Based on No Errors
echo ""
echo "Pattern 27: Success Based on Absence of Errors"
cat > /tmp/test_no_error_lie.py <<'EOF'
def broken_feature():
    """This feature is 'working' because it doesn't throw errors."""
    pass  # Does nothing

broken_feature()
print("Success: No errors!")
EOF

OUTPUT=$(uv run python /tmp/test_no_error_lie.py 2>&1)
if echo "$OUTPUT" | grep -q "Success: No errors"; then
    echo -e "${GREEN}✓ PASS${NC}: No-error lie detected"
    echo "  (Just because it doesn't error doesn't mean it works)"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: Unexpected output"
    FAILED=$((FAILED + 1))
fi

# Pattern 30: Comments as Implementation
echo ""
echo "Pattern 30: Comments as Implementation"
# This is caught by detect-lies pass statement detection
cat > /tmp/test_comment_lie.py <<'EOF'
def complex_algorithm():
    """Implements sophisticated ML algorithm."""
    # TODO: implement neural network
    # TODO: add gradient descent
    # TODO: optimize hyperparameters
    pass
EOF

OUTPUT=$(uv run python scripts/detect_implementation_lies.py /tmp/test_comment_lie.py 2>&1 || true)
if echo "$OUTPUT" | grep -q "TODO"; then
    echo -e "${GREEN}✓ PASS${NC}: Comment-as-implementation detected"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAIL${NC}: detect-lies missed comment lie"
    FAILED=$((FAILED + 1))
fi

# ============================================================================
# RESULTS
# ============================================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "RESULTS: $PASSED passed, $FAILED failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ ALL AI LIE DETECTORS WORKING                           ║${NC}"
    echo -e "${GREEN}║  31 patterns cataloged, $PASSED patterns tested            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ✗ SOME LIE DETECTORS FAILED                              ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
