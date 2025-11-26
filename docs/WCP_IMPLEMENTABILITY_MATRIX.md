# WCP Pattern Implementability Matrix: N3-Pure vs Hybrid

**Project:** KGC Hybrid Engine - Compiled Physics Architecture
**Date:** 2025-11-26
**Scope:** All 43 YAWL Workflow Control Patterns

---

## Executive Summary

This document maps all 43 WCP patterns to their implementability in:
1. **Pure N3/EYE** - Monotonic reasoning only
2. **Hybrid N3+Python** - N3 for graph physics, Python for orchestration
3. **Python-Only** - Requires full Python implementation

**Key Finding:**
- 6 patterns (14%) are fully N3-pure
- 8 patterns (19%) are implementable with N3 + guards
- 12 patterns (28%) require hybrid N3+Python
- 17 patterns (39%) require Python-only (non-monotonic)

---

## Pattern Classification by Tier

### Tier I: Basic Control-Flow (N3-Pure) - 6 Patterns

| # | Pattern | N3 Implementation | Test Coverage | Status |
|---|---------|-------------------|---------------|--------|
| 43 | WCP-1: Sequence | LAW 1 | 5 tests | ✅ IMPLEMENTED |
| 42 | WCP-4: Exclusive Choice | LAW 4/4b | 4 tests | ✅ IMPLEMENTED |
| 41 | WCP-2: Parallel Split | LAW 2 | 4 tests | ✅ IMPLEMENTED |
| 40 | WCP-3: Synchronization | LAW 3 | 9 tests | ✅ IMPLEMENTED |
| 39 | WCP-5: Simple Merge | LAW 1 (implicit) | 3 tests | ✅ IMPLEMENTED |
| 37 | WCP-11: Implicit Term | LAW 6 | 3 tests | ✅ IMPLEMENTED |

**N3 Physics Rules:**
```n3
# LAW 1: SEQUENCE - Purely local token passing
{ ?task kgc:status "Completed" . ?task yawl:flowsInto ?flow .
  ?flow yawl:nextElementRef ?next .
  ?scope log:notIncludes { ?task yawl:hasSplit ?anySplit } .
  ?scope log:notIncludes { ?next yawl:hasJoin ?anyJoin } . }
=> { ?next kgc:status "Active" . } .

# LAW 2: AND-SPLIT - All branches activated
{ ?task kgc:status "Completed" . ?task yawl:hasSplit yawl:ControlTypeAnd .
  ?task yawl:flowsInto ?flow . ?flow yawl:nextElementRef ?next . }
=> { ?next kgc:status "Active" . } .

# LAW 3: AND-JOIN - Requires DISTINCT predecessor check
{ ?join yawl:hasJoin yawl:ControlTypeAnd .
  ?prev1 yawl:flowsInto ?flow1 . ?flow1 yawl:nextElementRef ?join .
  ?prev1 kgc:status "Completed" .
  ?prev2 yawl:flowsInto ?flow2 . ?flow2 yawl:nextElementRef ?join .
  ?prev2 kgc:status "Completed" .
  ?prev1 log:uri ?uri1 . ?prev2 log:uri ?uri2 .
  ?uri1 string:notEqualIgnoringCase ?uri2 . }
=> { ?join kgc:status "Active" . } .

# LAW 4: XOR-SPLIT - Predicate path
{ ?task kgc:status "Completed" . ?task yawl:hasSplit yawl:ControlTypeXor .
  ?task yawl:flowsInto ?flow . ?flow yawl:nextElementRef ?next .
  ?flow yawl:hasPredicate ?pred . ?pred kgc:evaluatesTo true . }
=> { ?next kgc:status "Active" . } .
```

---

### Tier II: Structured Joins/Cancellations (N3 + Guards) - 8 Patterns

| # | Pattern | N3 Implementation | Guard Required | Status |
|---|---------|-------------------|----------------|--------|
| 38 | WCP-43: Explicit Term | LAW 6 + cancel flag | Cancel status | 🔄 DESIGNABLE |
| 36 | WCP-20: Cancel Case | Status marker | Cancel propagation | 🔄 DESIGNABLE |
| 35 | WCP-19: Cancel Activity | Status marker | Single task cancel | 🔄 DESIGNABLE |
| 34 | WCP-6: Multi-Choice | LAW 8 (OR-split) | Multiple predicates | 📋 PLANNED |
| 33 | WCP-7: Struct Sync Merge | LAW 3 variant | Structured DAG | 🔄 DESIGNABLE |
| 32 | WCP-8: Multi-Merge | Simple merge + counter | Re-firing | 🔄 DESIGNABLE |
| 30 | WCP-9: Struct Discrim | First-completion flag | Block later | 🔄 DESIGNABLE |
| 29 | WCP-16: Deferred Choice | Environment predicate | Race resolution | 🔄 DESIGNABLE |

**Proposed LAW 8: OR-SPLIT:**
```n3
# Multiple predicates can be true, activate all matching branches
{ ?task kgc:status "Completed" . ?task yawl:hasSplit yawl:ControlTypeOr .
  ?task yawl:flowsInto ?flow . ?flow yawl:nextElementRef ?next .
  ?flow yawl:hasPredicate ?pred . ?pred kgc:evaluatesTo true . }
=> { ?next kgc:status "Active" . } .
```

---

### Tier III: Multi-Instance + Milestones (Hybrid N3+Python) - 12 Patterns

| # | Pattern | N3 Component | Python Component | Status |
|---|---------|--------------|------------------|--------|
| 28 | WCP-12: MI w/o Sync | Instance spawning | Instance counting | 📋 PLANNED |
| 27 | WCP-13: MI Design-Time | Instance spawning | Fixed count | 📋 PLANNED |
| 26 | WCP-14: MI Runtime | Instance spawning | Dynamic count | 📋 PLANNED |
| 25 | WCP-15: MI Unknown | Instance spawning | Runtime discovery | 📋 PLANNED |
| 24 | WCP-18: Milestone | Status marker | Milestone tracking | 🔄 DESIGNABLE |
| 12 | WCP-17: Interleaved | Status marker | Serialization | 🧪 TESTED |
| 11 | WCP-29: Cancel Discrim | Completion events | First-wins logic | 🧪 TESTED |
| 10 | WCP-28: Block Discrim | Completion events | Block flag | 🧪 TESTED |
| 9 | WCP-30: Struct Partial | Completion events | k-of-n count | 🧪 TESTED |
| 8 | WCP-31: Block Partial | Completion events | Threshold + block | 🧪 TESTED |
| 7 | WCP-32: Cancel Partial | Completion events | Threshold + cancel | 🧪 TESTED |
| 6 | WCP-34: Static Partial MI | Completion events | Fixed threshold | 🧪 TESTED |

**Hybrid Pattern: Blocking Discriminator (WCP-28)**
```n3
# N3: Generate completion event
{ ?task kgc:status "Completed" . ?task yawl:flowsInto ?flow .
  ?flow yawl:nextElementRef ?discrim .
  ?discrim nato:hasDiscriminator nato:Blocking . }
=> { ?discrim kgc:completionEvent ?task . } .
```

```python
# Python: First-wins logic
def evaluate_discriminator(engine: HybridEngine, discrim_id: str) -> str | None:
    events = engine.query_completion_events(discrim_id)
    if not events:
        return None
    events.sort(key=lambda e: (e.tick, e.task_id))  # Deterministic
    return events[0].task_id
```

---

### Tier IV: Dynamic + Cancellation (Hybrid N3+Python) - 8 Patterns

| # | Pattern | N3 Component | Python Component | Status |
|---|---------|--------------|------------------|--------|
| 24 | WCP-21: Struct Loop | Loop entry/exit | Iteration count | 🔄 DESIGNABLE |
| 23 | WCP-22: Recursion | Call/return | Stack management | 🔄 DESIGNABLE |
| 22 | WCP-24: Persist Trigger | Event marker | Event queue | 📋 PLANNED |
| 21 | WCP-23: Trans Trigger | Event marker | Time window | 📋 PLANNED |
| 5 | WCP-35: Cancel Part MI | Threshold events | Cancel remaining | 🧪 TESTED |
| 4 | WCP-36: Dynamic Part MI | Threshold events | Runtime k | 🧪 TESTED |
| 13 | WCP-39: Critical Section | Lock marker | Mutex | 🔄 DESIGNABLE |
| 14 | WCP-40: Interleaved Route | Sequence marker | Order tracking | 🔄 DESIGNABLE |

---

### Tier V: Global Non-Local (Hybrid N3+Python) - 4 Patterns

| # | Pattern | N3 Component | Python Component | Status |
|---|---------|--------------|------------------|--------|
| 3 | WCP-33: Gen AND-Join | Token events | Multi-token count | 🧪 TESTED |
| 2 | WCP-37: Acyclic Sync | Path completion | DAG reachability | 🧪 TESTED |
| 1 | WCP-38: Gen Sync Merge | Path completion | Global reachability | 🧪 TESTED |
| 16 | WCP-41: Thread Merge | Thread markers | Thread tracking | 🔄 DESIGNABLE |

**Hybrid Pattern: General Synchronizing Merge (WCP-38)**
```python
# Python: Reachability analysis for sync merge
def is_path_exhausted(engine: HybridEngine, merge_id: str) -> bool:
    topology = engine.get_topology()
    merge_predecessors = topology.get_predecessors(merge_id)

    for pred in merge_predecessors:
        status = engine.get_status(pred)
        if status == "Completed":
            continue
        if is_reachable_from_active(topology, pred):
            return False  # Path still live
    return True  # All paths exhausted
```

---

### Not Implementable (Non-Monotonic) - 5 Patterns

| # | Pattern | Reason | Alternative |
|---|---------|--------|-------------|
| 17 | WCP-25: Cancel Region | Requires retraction | Status-based cancel |
| 18 | WCP-26: Cancel MI Activity | Requires retraction | Status-based cancel |
| 19 | WCP-27: Complete MI Activity | Requires force-complete | Status override |
| 15 | WCP-42: Thread Split | Covered by WCP-2 | Use AND-split |
| 20 | WCP-10: Arbitrary Cycles | Unbounded behavior | Bounded loops |

---

## Implementation Status Summary

| Category | Count | Percentage |
|----------|-------|------------|
| ✅ IMPLEMENTED (N3-pure) | 6 | 14% |
| 🧪 TESTED (Hybrid) | 12 | 28% |
| 🔄 DESIGNABLE | 14 | 33% |
| 📋 PLANNED | 6 | 14% |
| ❌ NOT FEASIBLE | 5 | 11% |
| **TOTAL** | **43** | **100%** |

---

## N3 Physics Limitations

### 1. Two-Predecessor AND-Join
Current LAW 3 only checks for 2 distinct predecessors. True n-way AND-join requires enumeration or Python counting.

### 2. No Token Counting
N3 cannot count tokens. Multi-instance patterns require Python aggregation.

### 3. No Retraction
Monotonic reasoning cannot remove triples. Cancellation uses status markers instead.

### 4. No Global Reachability
Sync merge patterns require BFS/DFS which N3 cannot express natively.

### 5. No Time/Ordering
Within a single tick, all completions are simultaneous. Discriminators need Python serialization.

---

## NATO Governance Mapping

| NATO Scenario | Primary WCP | Tier | Status |
|---------------|-------------|------|--------|
| Robert's Rules Sequence | WCP-1 | I | ✅ |
| Committee Formation | WCP-2 | I | ✅ |
| Committee Sync | WCP-3 | I | ✅ |
| Motion Decision | WCP-4 | I | ✅ |
| P5 Veto System | WCP-34 | III | 🧪 |
| Nuclear Triad | WCP-28 | III | 🧪 |
| Diplomatic Exhaustion | WCP-38 | V | 🧪 |
| Interleaved Debate | WCP-17 | III | 🧪 |
| Dual-Key Auth | WCP-3 | I | ✅ |
| Abort Override | WCP-4 | I | ✅ |

---

## Test Coverage Matrix

| Test File | Patterns Tested | Tests | Status |
|-----------|-----------------|-------|--------|
| test_nuclear_launch.py | WCP 1-5, 11 | 39 | ✅ |
| test_nato_symposium.py | WCP 1-5, 11 | 25 | ✅ |
| test_nato_maximum_stress.py | WCP 17, 28-38 | 19 | ✅ |
| test_wcp_dfss_patterns.py | WCP 1-5, 11 | 22 | ✅ |
| test_true_hybrid_engine.py | Engine core | 20 | ✅ |
| **TOTAL** | | **125** | ✅ |

---

## References

1. Russell, N., ter Hofstede, A.H.M., et al. (2006). "Workflow Control-Flow Patterns: A Revised View"
2. van der Aalst, W.M.P., ter Hofstede, A.H.M. (2005). "YAWL: yet another workflow language"
3. Berners-Lee, T., et al. (2008). "N3Logic: A logical framework for the World Wide Web"
4. De Roo, J. (2023). "EYE reasoner documentation"
