# Worklet Integration Testing - Visual Guide

This directory contains PlantUML diagrams illustrating the 80/20 principle applied to worklet JTBD integration testing: the 20% of concepts that explain 80% of the functionality.

## Diagrams

### 1. Integration Test Overview
**File:** `integration-test-overview.puml`

Shows the complete exception handling flow from workflow engine through worklet execution. This is the **core flow** that 80% of tests exercise.

**Key Components (20%):**
- WorkletExecutor: Orchestrates exception handling
- RDREngine: Selects appropriate worklets
- WorkletRepository: Stores worklets and cases
- RDR Trees: Decision trees for worklet selection

**Main Flow (80%):**
1. Exception occurs in workflow
2. Executor handles exception
3. RDR engine finds matching worklet
4. Worklet case created and executed
5. Result returned to engine

### 2. RDR Tree Traversal Logic
**File:** `rdr-tree-traversal.puml`

Illustrates the decision tree traversal algorithm - the **20% of logic** that powers **80% of worklet selection**.

**Key Features:**
- Condition evaluation (numeric, string, boolean)
- True/false branch navigation
- Refinement through nested rules
- Fallback mechanism (4-level hierarchy)

**Example Conditions:**
- `priority == high` (string equality)
- `load > 80` (numeric threshold)
- `environment == production` (environment routing)

### 3. Test Coverage Map
**File:** `test-coverage-map.puml`

Maps the 18 integration tests to their JTBD categories, showing which tests provide **80% of value** (critical path) vs 20% (edge cases).

**Critical Path (80% value):**
- Case exception handling (3 tests)
- RDR tree traversal (3 tests)
- Worklet execution (2 tests)
- Lifecycle management (3 tests)

**Edge Cases (20% value):**
- Fallback chains (3 tests)
- Error handling (2 tests)
- Repository operations (2 tests)

### 4. Worklet Lifecycle States
**File:** `worklet-lifecycle.puml`

State diagram showing the **5 possible states** and their transitions - the **20% of states** that **80% of tests verify**.

**States:**
- PENDING → RUNNING → COMPLETED (happy path)
- RUNNING → FAILED (error path)
- PENDING/RUNNING → CANCELLED (cancellation path)

**Integration Tests Verify:**
- State transitions occur correctly
- Timestamps are recorded
- Data persists in repository
- Engine callbacks fire

### 5. Key Test Scenarios
**File:** `key-test-scenarios.puml`

Sequence diagrams for the **top 3 test scenarios** that demonstrate **80% of worklet functionality**.

**Scenario 1: Priority-Based Selection**
- Tests RDR condition evaluation
- Verifies context data access
- Proves correct worklet routing

**Scenario 2: Numeric Threshold Routing**
- Tests numeric comparisons
- Verifies threshold logic
- Proves branch navigation

**Scenario 3: Complete Lifecycle**
- Tests state transitions
- Verifies persistence
- Proves end-to-end flow

## Viewing Diagrams

### Online
Use [PlantUML Online Server](https://www.plantuml.com/plantuml/uml/):
```bash
cat integration-test-overview.puml | pbcopy  # Copy to clipboard
# Paste into online editor
```

### VSCode
Install PlantUML extension:
```bash
code --install-extension jebbs.plantuml
```

### Command Line
```bash
# Generate PNGs
plantuml *.puml

# Generate SVGs
plantuml -tsvg *.puml
```

## 80/20 Principles Applied

### The 20% of Concepts:
1. **RDR Tree Traversal** - How worklets are selected
2. **Worklet Lifecycle** - State management
3. **Exception Handling Flow** - Core orchestration

### That Explain 80% of Functionality:
1. Case and item exception handling
2. Condition evaluation (numeric, string, boolean)
3. Worklet execution and result handling
4. State persistence and callbacks

## Test Philosophy

All integration tests follow **Chicago School TDD**:
- ✅ Assert on **ENGINE state** (worklet cases, RDR trees)
- ✅ Verify **REAL behavior** (no mocks)
- ✅ Test **complete workflows** (end-to-end)
- ❌ NO mocking domain objects
- ❌ NO testing Python simulation
- ❌ NO theater code

## Related Files

- **Tests:** `tests/yawl/worklets/test_worklet_integration.py` (922 lines, 18 tests)
- **Source:** `src/kgcl/yawl/worklets/`
- **Docs:** `docs/worklets/` (this directory)
