# KGCL Complete Test Plan

## Project Goals

Prove that the HybridEngine implements all 43 YAWL Workflow Control Patterns using pure N3/RDF semantics where:
- **State** is stored in PyOxigraph (RDF triples)
- **Logic** is enforced by N3 rules executed via EYE Reasoner
- **Python** only orchestrates ticks—NO workflow logic in Python

## Current Test Status

### What Exists (REAL tests)
| Test File | Patterns | Approach |
|-----------|----------|----------|
| `test_wcp_basic_control.py` | WCP 1-5 | SemanticDriver + Kernel |
| `test_wcp_advanced_branching.py` | WCP 6-9 | SemanticDriver + Kernel |
| `test_wcp_structural.py` | WCP 10-11 | Kernel verbs |
| `test_wcp_multiple_instance.py` | WCP 12-15 | Kernel verbs |
| `test_wcp_state_based.py` | WCP 16-18 | Kernel verbs |
| `test_wcp_cancellation_*.py` | WCP 19-27 | Kernel verbs |
| `test_wcp_iteration.py` | WCP 21-22 | Kernel verbs |
| `test_wcp_triggers.py` | WCP 23-24 | Kernel verbs |
| `test_wcp_mi_joins.py` | WCP 34-36 | Kernel verbs |
| `test_all_43_patterns_validated.py` | All 41 mappings | Ontology SPARQL validation |

### What These Tests Actually Prove
1. **Ontology correctness**: Pattern mappings exist with correct verbs/params
2. **Kernel behavior**: The 5 verbs (transmute, copy, filter, await, void) produce correct QuadDeltas
3. **SemanticDriver resolution**: Correct verb+params resolved from RDF topology

### What Is NOT Proven Yet
1. **N3 rules actually fire**: No tests invoke EYE reasoner with workflow state
2. **Multi-tick convergence**: `run_to_completion()` not tested for complex patterns
3. **HybridEngine integration**: Full facade not tested end-to-end
4. **State transitions persist**: RDF state changes not verified across ticks

---

## Test Plan: Three Levels of Verification

### Level 1: Ontology Validation (EXISTS ✓)
**Purpose**: Verify the physics ontology correctly maps all 41 patterns to verbs.

**File**: `tests/engine/test_all_43_patterns_validated.py`

**Coverage**: Complete for all 41 pattern mappings.

---

### Level 2: Kernel Behavior Tests (EXISTS ✓)
**Purpose**: Verify each parameterized verb produces correct QuadDeltas.

**Files**: `tests/engine/test_wcp_*.py`

**Coverage**:
- WCP 1-5: Complete
- WCP 6-9: Complete
- WCP 10-11: Complete
- WCP 12-15: Partial (cardinality tests)
- WCP 16-18: Partial (deferred choice, milestone)
- WCP 19-27: Partial (cancellation scopes)
- WCP 34-36: Partial (MI joins)

**Gaps to Fill**:
1. WCP-16 deferred choice: Test external event racing
2. WCP-17 interleaved parallel: Test mutex execution
3. WCP-18 milestone: Test milestone waiting and reset
4. WCP-28 to WCP-33: Advanced sync patterns not tested
5. WCP-37 to WCP-43: Termination patterns incomplete

---

### Level 3: HybridEngine Integration (TO BE CREATED)
**Purpose**: Verify the full engine executes workflows via N3 rules.

#### Test Architecture

```
                    Test Harness
                         │
                         ▼
    ┌─────────────────────────────────────────┐
    │            HybridEngine                  │
    │  load_data() │ apply_physics() │ run_to │
    ├─────────────────────────────────────────┤
    │  TickExecutor invokes:                   │
    │    1. Query PyOxigraph for tokens        │
    │    2. Call EYE subprocess with N3 rules  │◄── MUST BE TESTED
    │    3. Parse EYE output as triples        │
    │    4. Apply delta to PyOxigraph          │
    └─────────────────────────────────────────┘
```

#### Required Test File: `tests/engine/test_hybrid_engine_integration.py`

```python
"""Integration tests for HybridEngine proving N3 rules execute.

These tests verify:
1. EYE reasoner is actually invoked (not mocked)
2. N3 rules produce state changes
3. Multi-tick convergence works
4. Full WCP patterns work end-to-end
"""
```

---

## Level 3 Test Specifications

### Test 3.1: Single Tick Execution

**File**: `tests/engine/test_hybrid_engine_integration.py`

```python
def test_single_tick_invokes_eye_reasoner():
    """Verify apply_physics() actually calls EYE subprocess."""
    # Arrange
    engine = HybridEngine()
    engine.load_data(WCP1_SEQUENCE_WORKFLOW)

    # Act
    result = engine.apply_physics()

    # Assert
    assert result.physics_applied > 0, "N3 rules must fire"
    assert result.triples_added > 0, "State must change"
    # Verify task B now has token (from N3 rule firing)
    assert engine.inspect()["urn:task:B"] == "Active"
```

### Test 3.2: WCP-1 Sequence End-to-End

```python
def test_wcp1_sequence_runs_to_completion():
    """WCP-1: A → B → C runs to completion via N3 rules."""
    engine = HybridEngine()
    engine.load_data("""
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ; kgc:status "Completed" ;
            yawl:flowsInto [ yawl:nextElementRef <urn:task:B> ] .
        <urn:task:B> a yawl:Task ; kgc:status "Pending" ;
            yawl:flowsInto [ yawl:nextElementRef <urn:task:C> ] .
        <urn:task:C> a yawl:Task ; kgc:status "Pending" .
    """)

    # Act
    results = engine.run_to_completion(max_ticks=10)

    # Assert
    assert len(results) == 2, "Should take 2 ticks: A→B, B→C"
    assert engine.inspect()["urn:task:C"] == "Active"
```

### Test 3.3: WCP-2 Parallel Split

```python
def test_wcp2_parallel_split_creates_multiple_tokens():
    """WCP-2: AND-split creates tokens on all branches via N3."""
    engine = HybridEngine()
    engine.load_data("""
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto [ yawl:nextElementRef <urn:task:B> ] ;
            yawl:flowsInto [ yawl:nextElementRef <urn:task:C> ] .
        <urn:task:B> a yawl:Task ; kgc:status "Pending" .
        <urn:task:C> a yawl:Task ; kgc:status "Pending" .
    """)

    results = engine.run_to_completion(max_ticks=5)

    # Both branches activated
    status = engine.inspect()
    assert status["urn:task:B"] == "Active"
    assert status["urn:task:C"] == "Active"
```

### Test 3.4: WCP-3 Synchronization (AND-join)

```python
def test_wcp3_synchronization_waits_for_all():
    """WCP-3: AND-join waits until all predecessors complete."""
    engine = HybridEngine()
    engine.load_data("""
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ; kgc:status "Completed" ;
            yawl:flowsInto [ yawl:nextElementRef <urn:task:C> ] .
        <urn:task:B> a yawl:Task ; kgc:status "Pending" ;  # NOT completed
            yawl:flowsInto [ yawl:nextElementRef <urn:task:C> ] .
        <urn:task:C> a yawl:Task ; kgc:status "Pending" ;
            yawl:hasJoin yawl:ControlTypeAnd .
    """)

    results = engine.run_to_completion(max_ticks=5)

    # C should NOT be active (waiting for B)
    assert engine.inspect()["urn:task:C"] == "Pending"

    # Now complete B
    engine.load_data('<urn:task:B> kgc:status "Completed" .')
    results = engine.run_to_completion(max_ticks=5)

    # C should now be active
    assert engine.inspect()["urn:task:C"] == "Active"
```

### Test 3.5: Negative Test - Pattern Must Fail When Violated

```python
def test_wcp3_fails_when_threshold_not_met():
    """WCP-3 MUST fail if AND-join receives only 2 of 3 required tokens."""
    engine = HybridEngine()
    engine.load_data("""
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        # 3 predecessors: A, B, C → D (AND-join)
        <urn:task:A> a yawl:Task ; kgc:status "Completed" ;
            yawl:flowsInto [ yawl:nextElementRef <urn:task:D> ] .
        <urn:task:B> a yawl:Task ; kgc:status "Completed" ;
            yawl:flowsInto [ yawl:nextElementRef <urn:task:D> ] .
        <urn:task:C> a yawl:Task ; kgc:status "Pending" ;  # NOT completed
            yawl:flowsInto [ yawl:nextElementRef <urn:task:D> ] .
        <urn:task:D> a yawl:Task ; kgc:status "Pending" ;
            yawl:hasJoin yawl:ControlTypeAnd .
    """)

    results = engine.run_to_completion(max_ticks=10)

    # D MUST NOT activate - this is the critical assertion
    assert engine.inspect()["urn:task:D"] != "Active", (
        "AND-join fired with only 2/3 predecessors - pattern violated!"
    )
```

### Test 3.6: WCP-19 Cancel Task

```python
def test_wcp19_cancel_task_voids_single_task():
    """WCP-19: Cancel Task voids only the specified task."""
    engine = HybridEngine()
    engine.load_data("""
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ; kgc:status "Active" .
        <urn:task:B> a yawl:Task ; kgc:status "Active" .
        <urn:task:Cancel> a yawl:Task ;
            yawl:cancels <urn:task:A> ;
            kgc:status "Active" .
    """)

    results = engine.run_to_completion(max_ticks=5)

    # A should be voided, B should still be active
    assert engine.inspect()["urn:task:A"] == "Voided"
    assert engine.inspect()["urn:task:B"] == "Active"
```

### Test 3.7: Convergence Detection

```python
def test_run_to_completion_detects_convergence():
    """Engine must detect when no more rules can fire."""
    engine = HybridEngine()
    engine.load_data("""
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ; kgc:status "Completed" ;
            yawl:flowsInto [ yawl:nextElementRef <urn:task:B> ] .
        <urn:task:B> a yawl:Task ; kgc:status "Pending" .
    """)

    results = engine.run_to_completion(max_ticks=100)

    # Should converge in 1 tick, not 100
    assert len(results) == 1
    assert results[0].physics_applied == 1
```

### Test 3.8: Divergence Detection

```python
def test_run_to_completion_raises_on_divergence():
    """Engine must raise ConvergenceError if max_ticks exceeded."""
    engine = HybridEngine()
    # Infinite loop workflow
    engine.load_data("""
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ; kgc:status "Completed" ;
            yawl:flowsInto [ yawl:nextElementRef <urn:task:B> ] .
        <urn:task:B> a yawl:Task ; kgc:status "Pending" ;
            yawl:flowsInto [ yawl:nextElementRef <urn:task:A> ] .  # Loop back
    """)

    with pytest.raises(ConvergenceError) as exc:
        engine.run_to_completion(max_ticks=5)

    assert exc.value.max_ticks == 5
```

---

## Test Matrix: All 43 Patterns

| WCP | Pattern | Verb | Level 1 | Level 2 | Level 3 |
|-----|---------|------|---------|---------|---------|
| 1 | Sequence | transmute | ✓ | ✓ | TODO |
| 2 | Parallel Split | copy | ✓ | ✓ | TODO |
| 3 | Synchronization | await | ✓ | ✓ | TODO |
| 4 | Exclusive Choice | filter | ✓ | ✓ | TODO |
| 5 | Simple Merge | transmute | ✓ | ✓ | TODO |
| 6 | Multi-Choice | filter | ✓ | ✓ | TODO |
| 7 | Structured Sync Merge | await | ✓ | ✓ | TODO |
| 8 | Multi-Merge | transmute | ✓ | ✓ | TODO |
| 9 | Structured Discriminator | await | ✓ | ✓ | TODO |
| 10 | Arbitrary Cycles | filter | ✓ | ✓ | TODO |
| 11 | Implicit Termination | void | ✓ | ✓ | TODO |
| 12 | MI No Sync | copy | ✓ | Partial | TODO |
| 13 | MI Design Time | copy | ✓ | Partial | TODO |
| 14 | MI Runtime | copy | ✓ | Partial | TODO |
| 15 | MI No Prior | copy | ✓ | Partial | TODO |
| 16 | Deferred Choice | filter | ✓ | Partial | TODO |
| 17 | Interleaved Parallel | filter | ✓ | Partial | TODO |
| 18 | Milestone | await | ✓ | Partial | TODO |
| 19 | Cancel Task | void | ✓ | ✓ | TODO |
| 20 | Cancel Case | void | ✓ | ✓ | TODO |
| 21 | Cancel Region | void | ✓ | ✓ | TODO |
| 22 | Cancel MI | void | ✓ | Partial | TODO |
| 23 | Complete MI | await | ✓ | Partial | TODO |
| 24 | Exception Handling | void | ✓ | Partial | TODO |
| 25 | Timeout | void | ✓ | Partial | TODO |
| 26 | Structured Loop | filter | ✓ | ✓ | TODO |
| 27 | Recursion | copy | ✓ | Partial | TODO |
| 28-33 | Advanced Sync | await | ✓ | TODO | TODO |
| 34 | MI Static Partial Join | await | ✓ | ✓ | TODO |
| 35 | MI Cancelling Join | await | ✓ | ✓ | TODO |
| 36 | MI Dynamic Join | await | ✓ | ✓ | TODO |
| 37-42 | Advanced Termination | void | ✓ | TODO | TODO |
| 43 | Explicit Termination | void | ✓ | ✓ | TODO |

---

## Implementation Priority

### Phase 1: Core Patterns (Week 1)
1. Create `test_hybrid_engine_integration.py`
2. Implement Tests 3.1-3.5 (WCP 1-5 via HybridEngine)
3. Verify EYE reasoner is actually invoked

### Phase 2: Cancellation (Week 2)
1. Tests 3.6+ for WCP 19-27
2. Verify void verb works with N3 rules
3. Test region-scoped cancellation

### Phase 3: Multiple Instances (Week 3)
1. WCP 12-15 full integration
2. Dynamic cardinality tests
3. MI join patterns (34-36)

### Phase 4: State-Based (Week 4)
1. WCP 16: Deferred choice with external events
2. WCP 17: Mutex interleaved parallel
3. WCP 18: Milestone waiting

### Phase 5: Advanced Sync & Termination (Week 5)
1. WCP 28-33: Blocking/non-blocking joins
2. WCP 37-42: Termination variants
3. Full convergence/divergence testing

---

## Test Quality Criteria

### Every Test MUST:
1. **Invoke the real engine** - No mocking HybridEngine internals
2. **Load RDF workflow data** - Turtle format into PyOxigraph
3. **Assert on RDF state** - Use `engine.inspect()` or SPARQL queries
4. **Include negative case** - Test what happens when pattern is violated
5. **Document pattern being tested** - Clear WCP-N reference in docstring

### A Test FAILS if:
1. It passes without EYE reasoner installed
2. It passes when N3 rules are deleted
3. It uses Python `if/else` to simulate patterns
4. It asserts on script variables instead of RDF state
5. It doesn't verify the specific pattern semantics

---

## Validation Commands

```bash
# Run Level 1 (ontology validation)
uv run pytest tests/engine/test_all_43_patterns_validated.py -v

# Run Level 2 (kernel behavior)
uv run pytest tests/engine/test_wcp_*.py -v

# Run Level 3 (integration)
uv run pytest tests/engine/test_hybrid_engine_integration.py -v

# Full test suite
uv run poe test

# Coverage report
uv run pytest --cov=src/kgcl --cov-report=html
```

---

## Success Criteria

1. **All 43 patterns have Level 3 tests** - No pattern untested
2. **Tests fail without EYE** - `which eye` must succeed for tests to pass
3. **80%+ code coverage** - On `src/kgcl/hybrid/` module
4. **Tests run in <30s** - Performance requirement
5. **Zero flaky tests** - Deterministic results
