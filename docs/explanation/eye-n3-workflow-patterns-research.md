# EYE Reasoner N3 Builtins for Workflow Pattern Implementation

**Project:** KGCL Hybrid Engine - Workflow Control Patterns
**Date:** 2025-11-26
**Purpose:** Research findings on N3/EYE capabilities for implementing complex YAWL workflow patterns

---

## Executive Summary

This document catalogs EYE reasoner N3 builtins that can be used to implement complex workflow patterns, particularly focusing on counting, aggregation, negation, and graph operations needed for YAWL patterns.

**Key Finding:** N3 provides rich builtins for many workflow operations, but has fundamental limitations for non-monotonic patterns (cancellation, discriminators, n-of-m joins).

---

## 1. Counting and Aggregation Builtins

### 1.1 log:collectAllIn - Collecting All Matches

**Capability:** Collects all values matching a pattern into a list (similar to Prolog's findall).

**Signature:**
```n3
(?Variable ?WhereClause ?ResultList) log:collectAllIn ?Scope .
```

**N3 Syntax:**
```n3
@prefix log: <http://www.w3.org/2000/10/swap/log#> .
@prefix list: <http://www.w3.org/2000/10/swap/list#> .
@prefix yawl: <http://example.org/yawl#> .

# Collect all completed predecessors of a task
{
  ?join yawl:hasJoin yawl:ControlTypeAnd .
  (?pred {
    ?pred yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?join .
    ?pred kgc:status "Completed" .
  } ?completedPreds) log:collectAllIn ?scope .
} => {
  ?join yawl:completedPredecessors ?completedPreds .
} .
```

**Use Case:** Counting how many predecessors have completed for n-way AND-join.

**Limitation:** Cannot count within the rule - need to combine with `list:length`.

---

### 1.2 list:length - Getting Count of Items

**Capability:** Gets the length of a list.

**Signature:**
```n3
?List list:length ?Count .
```

**N3 Syntax:**
```n3
@prefix list: <http://www.w3.org/2000/10/swap/list#> .
@prefix math: <http://www.w3.org/2000/10/swap/math#> .

# Count completed predecessors for AND-join
{
  ?join yawl:hasJoin yawl:ControlTypeAnd .
  ?join yawl:completedPredecessors ?predList .
  ?predList list:length ?completedCount .
  ?join yawl:expectedPredecessors ?expectedCount .
  ?completedCount math:equalTo ?expectedCount .
} => {
  ?join kgc:status "Active" .
} .
```

**Use Case:** Implementing n-way AND-join by counting completed predecessors.

**Pattern:** Combine `log:collectAllIn` + `list:length` + `math:equalTo` for exact counting.

---

### 1.3 math:sum - Arithmetic on Collections

**Capability:** Sum numeric values from a list.

**Signature:**
```n3
?List math:sum ?Total .
```

**N3 Syntax:**
```n3
@prefix math: <http://www.w3.org/2000/10/swap/math#> .

# Calculate total latency across sequential workflow steps
{
  ?workflow yawl:steps ?stepList .
  ?stepList math:sum ?totalLatency .
} => {
  ?workflow yawl:predictedLatency ?totalLatency .
} .
```

**Use Case:** Performance prediction for sequential workflows.

**Note:** `math:product` also available for multiplication.

---

### 1.4 e:findall - Prolog-Style Findall

**Capability:** EYE-specific builtin for collecting matching patterns (more powerful than `log:collectAllIn`).

**Signature:**
```n3
(?Template ?Pattern ?ResultList) e:findall true .
```

**N3 Syntax:**
```n3
@prefix e: <http://eulersharp.sourceforge.net/2003/03swap/log-rules#> .

# Find all active tasks in workflow
{
  (?task {?task kgc:status "Active"} ?activeTasks) e:findall true .
  ?activeTasks list:length ?count .
} => {
  :workflow :activeTaskCount ?count .
} .
```

**Use Case:** Dynamic counting of active tasks for termination detection.

**Power:** Can bypass monotonicity for counting (but not for retraction).

---

## 2. List Operations

### 2.1 list:member - Membership Testing

**Capability:** Check if item is in list or iterate over list members.

**Signature:**
```n3
?List list:member ?Item .
```

**N3 Syntax:**
```n3
@prefix list: <http://www.w3.org/2000/10/swap/list#> .

# Check if task is a valid terminal state
{
  ?protocol yawl:terminalStates ?terminalList .
  ?terminalList list:member ?task .
  ?task kgc:status "Completed" .
} => {
  ?protocol :terminalReached true .
} .
```

**Use Case:** Validating that a task is in the expected set of terminal states.

**Bidirectional:** Can use for checking membership or for iterating over members.

---

### 2.2 list:append - List Concatenation

**Capability:** Append two lists together.

**Signature:**
```n3
(?List1 ?List2) list:append ?CombinedList .
```

**N3 Syntax:**
```n3
# Combine two branches of completed tasks
{
  ?branch1 yawl:completedTasks ?list1 .
  ?branch2 yawl:completedTasks ?list2 .
  (?list1 ?list2) list:append ?allCompleted .
} => {
  :workflow yawl:allCompletedTasks ?allCompleted .
} .
```

**Use Case:** Merging task lists from parallel branches.

---

### 2.3 list:first / list:rest - List Traversal

**Capability:** Get first element and remaining list (cons/car/cdr pattern).

**Signature:**
```n3
?List list:first ?FirstElement .
?List list:rest ?RemainingList .
```

**N3 Syntax:**
```n3
# Process first task in queue
{
  ?workflow yawl:taskQueue ?queue .
  ?queue list:first ?nextTask .
} => {
  ?nextTask kgc:status "Active" .
} .
```

**Use Case:** Queue-based task processing.

---

### 2.4 rdf:first / rdf:rest - RDF List Traversal

**Capability:** Traverse RDF lists (first/rest ladders).

**Signature:**
```n3
?RDFList rdf:first ?FirstElement .
?RDFList rdf:rest ?RemainingList .
```

**N3 Syntax:**
```n3
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

# Iterate over RDF list of tasks
{
  ?workflow yawl:taskSequence ?seq .
  ?seq rdf:first ?task .
  ?task kgc:status "Completed" .
  ?seq rdf:rest ?remaining .
  ?remaining rdf:first ?nextTask .
} => {
  ?nextTask kgc:status "Active" .
} .
```

**Use Case:** Sequential task activation from RDF lists.

**Note:** N3 lists (`()` syntax) are different from RDF lists - can convert between them with rules.

---

## 3. Comparison and Ordering

### 3.1 math:lessThan / math:greaterThan

**Capability:** Numeric comparison.

**Signature:**
```n3
?Number1 math:lessThan ?Number2 .
?Number1 math:greaterThan ?Number2 .
```

**N3 Syntax:**
```n3
@prefix math: <http://www.w3.org/2000/10/swap/math#> .

# Threshold-based partial join (k-of-n)
{
  ?join yawl:hasJoin yawl:ControlTypePartial .
  ?join yawl:threshold ?k .
  ?join yawl:completedPredecessors ?predList .
  ?predList list:length ?completedCount .
  ?completedCount math:greaterThan ?k .  # OR math:equalTo for exactly k
} => {
  ?join kgc:status "Active" .
} .
```

**Use Case:** WCP-30 (Structured Partial Join) - activate when k-of-n branches complete.

**Also Available:** `math:equalTo`, `math:notEqualTo`, `math:notLessThan`, `math:notGreaterThan`

---

### 3.2 string:lessThan - Lexicographic Ordering

**Capability:** String comparison (alphabetical order).

**Signature:**
```n3
?String1 string:lessThan ?String2 .
```

**N3 Syntax:**
```n3
@prefix string: <http://www.w3.org/2000/10/swap/string#> .

# Order tasks alphabetically
{
  ?task1 rdfs:label ?label1 .
  ?task2 rdfs:label ?label2 .
  ?label1 string:lessThan ?label2 .
} => {
  ?task1 yawl:orderBefore ?task2 .
} .
```

**Use Case:** Deterministic ordering of tasks for discriminator patterns.

---

### 3.3 log:equalTo / log:notEqualTo

**Capability:** Generic equality/inequality (works with URIs, literals, etc).

**Signature:**
```n3
?Value1 log:equalTo ?Value2 .
?Value1 log:notEqualTo ?Value2 .
```

**N3 Syntax:**
```n3
@prefix log: <http://www.w3.org/2000/10/swap/log#> .

# Ensure XOR exclusivity - only one predicate is true
{
  ?task yawl:hasSplit yawl:ControlTypeXor .
  ?task yawl:flowsInto ?flow1 .
  ?flow1 yawl:hasPredicate ?pred1 .
  ?pred1 kgc:evaluatesTo true .
  ?task yawl:flowsInto ?flow2 .
  ?flow1 log:notEqualTo ?flow2 .
  ?flow2 yawl:hasPredicate ?pred2 .
  ?pred2 kgc:evaluatesTo true .
} => {
  :error :xorViolation ?task .
} .
```

**Use Case:** Detecting XOR violations (both branches activated).

---

## 4. Scoped Negation

### 4.1 log:notIncludes - Scoped Negation as Failure

**Capability:** Check that a scope DOES NOT include certain triples.

**Signature:**
```n3
?Scope log:notIncludes { ?Pattern } .
```

**N3 Syntax:**
```n3
@prefix log: <http://www.w3.org/2000/10/swap/log#> .

# Simple sequence rule: activate next task ONLY if no split/join
{
  ?task kgc:status "Completed" .
  ?task yawl:flowsInto ?flow .
  ?flow yawl:nextElementRef ?next .
  ?scope log:notIncludes { ?task yawl:hasSplit ?anySplit } .
  ?scope log:notIncludes { ?next yawl:hasJoin ?anyJoin } .
} => {
  ?next kgc:status "Active" .
} .
```

**Use Case:** Guard against simple sequence rule firing for split/join tasks.

**Scope:** `?scope` is typically the current N3 document or reasoning scope.

---

### 4.2 log:includes - Pattern Matching in Scope

**Capability:** Check that a scope DOES include certain triples.

**Signature:**
```n3
?Scope log:includes { ?Pattern } .
```

**N3 Syntax:**
```n3
# Check that all required predecessors exist
{
  ?join yawl:hasJoin yawl:ControlTypeAnd .
  ?scope log:includes {
    ?pred1 yawl:flowsInto ?flow1 .
    ?flow1 yawl:nextElementRef ?join .
    ?pred2 yawl:flowsInto ?flow2 .
    ?flow2 yawl:nextElementRef ?join .
    ?pred1 log:notEqualTo ?pred2 .
  } .
} => {
  ?join yawl:hasRequiredPredecessors true .
} .
```

**Use Case:** Validating that AND-join has multiple distinct predecessors.

---

### 4.3 Implementing "No X Such That..."

**Pattern:** Combine `log:collectAllIn` + `list:length` + `math:equalTo` for checking emptiness.

**N3 Syntax:**
```n3
# Detect no active tasks remaining (termination)
{
  (?task {?task kgc:status "Active"} ?activeTasks) log:collectAllIn ?scope .
  ?activeTasks list:length ?count .
  ?count math:equalTo 0 .
} => {
  :workflow :terminated true .
} .
```

**Alternative with e:findall:**
```n3
{
  (?task {?task kgc:status "Active"} ?activeTasks) e:findall true .
  ?activeTasks log:equalTo () .  # Empty list
} => {
  :workflow :terminated true .
} .
```

**Use Case:** WCP-11 (Implicit Termination) - detect when no tasks are active.

---

## 5. Graph Operations

### 5.1 log:semantics - Loading External Graphs

**Capability:** Load and reason over external N3/RDF documents.

**Signature:**
```n3
?URI log:semantics ?Graph .
```

**N3 Syntax:**
```n3
# Load workflow definition from external file
{
  <file:///path/to/workflow.n3> log:semantics ?workflowGraph .
  ?workflowGraph log:includes {
    ?task a yawl:AtomicTask .
  } .
} => {
  ?task :loadedFromExternal true .
} .
```

**Use Case:** Modular workflow definitions loaded from separate files.

---

### 5.2 log:conjunction - Combining Patterns

**Capability:** Combine multiple graph patterns.

**Signature:**
```n3
(?Graph1 ?Graph2) log:conjunction ?CombinedGraph .
```

**N3 Syntax:**
```n3
# Combine workflow state and rules
{
  ?stateGraph a :WorkflowState .
  ?rulesGraph a :WorkflowRules .
  (?stateGraph ?rulesGraph) log:conjunction ?fullWorkflow .
} => {
  ?fullWorkflow :readyForReasoning true .
} .
```

**Use Case:** Merging workflow state with workflow rules for reasoning.

---

### 5.3 e:graphDifference / e:graphIntersection

**Capability:** Set operations on graphs (EYE-specific).

**Signature:**
```n3
(?Graph1 ?Graph2) e:graphDifference ?DiffGraph .
(?Graph1 ?Graph2) e:graphIntersection ?CommonGraph .
```

**Use Case:** Analyzing workflow changes between versions.

---

## 6. Workflow Pattern Implementations

### 6.1 N-Way AND-Join (Full Implementation)

**Pattern:** WCP-3 Synchronization - all branches must complete.

**N3 Implementation:**
```n3
@prefix log: <http://www.w3.org/2000/10/swap/log#> .
@prefix list: <http://www.w3.org/2000/10/swap/list#> .
@prefix math: <http://www.w3.org/2000/10/swap/math#> .

# Step 1: Collect all completed predecessors
{
  ?join yawl:hasJoin yawl:ControlTypeAnd .
  (?pred {
    ?pred yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?join .
    ?pred kgc:status "Completed" .
  } ?completedPreds) log:collectAllIn ?scope .
} => {
  ?join yawl:completedPredecessors ?completedPreds .
} .

# Step 2: Count completed vs expected
{
  ?join yawl:completedPredecessors ?predList .
  ?predList list:length ?completedCount .
  ?join yawl:expectedPredecessorCount ?expectedCount .
  ?completedCount math:equalTo ?expectedCount .
} => {
  ?join kgc:status "Active" .
} .
```

**Limitation:** Requires manually setting `yawl:expectedPredecessorCount` - cannot dynamically count all predecessors in pure N3.

**Workaround:** Pre-compute expected count during workflow compilation/validation.

---

### 6.2 K-of-N Partial Join (Threshold Logic)

**Pattern:** WCP-30 Structured Partial Join - activate when k-of-n branches complete.

**N3 Implementation:**
```n3
# Collect completed predecessors and check threshold
{
  ?join yawl:hasJoin yawl:ControlTypePartial .
  ?join yawl:threshold ?k .
  (?pred {
    ?pred yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?join .
    ?pred kgc:status "Completed" .
  } ?completedPreds) log:collectAllIn ?scope .
  ?completedPreds list:length ?count .
  ?count math:greaterThan ?k .  # OR math:equalTo for exactly k
} => {
  ?join kgc:status "Active" .
} .
```

**Use Case:** P5 UN Security Council veto system - 9-of-15 votes required.

**Works in N3:** ✅ Yes - counting + comparison is monotonic.

---

### 6.3 Discriminator (First Completion Wins)

**Pattern:** WCP-9 Structured Discriminator - first branch to complete wins.

**N3 Implementation (Partial):**
```n3
# Detect first completion via timestamp
{
  ?discrim yawl:hasJoin yawl:ControlTypeDiscriminator .
  (?pred {
    ?pred yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?discrim .
    ?pred kgc:status "Completed" .
    ?pred kgc:completionTime ?time .
  } ?completedPreds) log:collectAllIn ?scope .
  ?completedPreds list:first ?firstCompleted .
} => {
  ?discrim yawl:winningBranch ?firstCompleted .
} .
```

**Limitation:** ❌ Cannot determine "first" without external ordering mechanism (timestamps, tick counters).

**N3 Issue:** No built-in temporal ordering - `list:first` gives arbitrary first element from unordered collection.

**Solution:** Requires Python/hybrid layer to sort by completion time before feeding to N3.

---

### 6.4 Synchronizing Merge (All Activated Paths Complete)

**Pattern:** WCP-38 General Synchronizing Merge - wait for all activated paths.

**N3 Implementation (Partial):**
```n3
# Collect all predecessors
{
  ?merge yawl:hasJoin yawl:ControlTypeSyncMerge .
  (?pred {
    ?pred yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?merge .
  } ?allPreds) log:collectAllIn ?scope .
} => {
  ?merge yawl:allPredecessors ?allPreds .
} .

# Check if all activated predecessors are complete
{
  ?merge yawl:allPredecessors ?allPreds .
  (?pred {
    ?pred list:member ?allPreds .
    ?pred kgc:status "Active" .
  } ?activePreds) log:collectAllIn ?scope .
  ?activePreds list:length 0 .  # No active predecessors remain
} => {
  ?merge kgc:status "Active" .
} .
```

**Limitation:** ❌ Cannot determine which paths were "activated" vs "exist but never activated" in pure N3.

**N3 Issue:** Requires global reachability analysis to know which paths are active.

**Solution:** Requires Python/hybrid layer for BFS/DFS reachability analysis.

---

## 7. Fundamental N3 Limitations for Workflows

### 7.1 No Token Counting

**Problem:** Cannot count arbitrary patterns without pre-declaring what to count.

**Example:**
```n3
# ❌ Cannot do: Count all predecessors dynamically
{
  ?join yawl:hasJoin yawl:ControlTypeAnd .
  # No way to count all ?pred that flow into ?join without log:collectAllIn
} => {
  ?join yawl:predecessorCount ?count .  # IMPOSSIBLE
} .
```

**Workaround:** Use `log:collectAllIn` + `list:length`, but requires knowing the pattern in advance.

---

### 7.2 No Retraction (Monotonicity)

**Problem:** Cannot remove or modify existing triples.

**Example:**
```n3
# ❌ Cannot do: Cancel a task by removing its status
{
  ?task kgc:status "Active" .
  :cancelSignal :received true .
} => {
  # Cannot REMOVE (?task kgc:status "Active")
  # Can only ADD new triples
} .
```

**Workaround:** Status markers instead of retraction:
```n3
{
  ?task kgc:status "Active" .
  :cancelSignal :received true .
} => {
  ?task kgc:status "Cancelled" .  # Add new status, don't remove old
} .
```

**Issue:** Multiple status values can coexist - need `inspect()` to pick highest-priority.

---

### 7.3 No Global Reachability

**Problem:** Cannot perform BFS/DFS graph traversal in pure N3.

**Example:**
```n3
# ❌ Cannot do: Check if task is reachable from initial state
{
  ?task a yawl:AtomicTask .
  # No way to express "is reachable via any path from :initialTask"
} => {
  ?task yawl:reachable true .  # IMPOSSIBLE without explicit path rules
} .
```

**Workaround:** Explicitly enumerate paths (doesn't scale):
```n3
# Initial task is reachable
{ ?workflow yawl:initialTask ?task } => { ?task yawl:reachable true } .

# Reachability is transitive
{
  ?task1 yawl:reachable true .
  ?task1 yawl:flowsInto ?flow .
  ?flow yawl:nextElementRef ?task2 .
} => {
  ?task2 yawl:reachable true .
} .
```

**Issue:** Requires explicit transitive closure - doesn't work for dynamic workflows.

**Solution:** Python/hybrid layer for graph analysis algorithms.

---

### 7.4 No Temporal Ordering Within Tick

**Problem:** Cannot determine which task completed "first" within same reasoning step.

**Example:**
```n3
# ❌ Cannot do: Determine first completion for discriminator
{
  ?task1 kgc:status "Completed" .
  ?task2 kgc:status "Completed" .
  # No way to know which completed first without external timestamps
} => {
  ?winner :isFirstCompletion true .  # IMPOSSIBLE
} .
```

**Workaround:** External tick counter + timestamps:
```n3
{
  ?task1 kgc:status "Completed" .
  ?task1 kgc:tick ?tick1 .
  ?task2 kgc:status "Completed" .
  ?task2 kgc:tick ?tick2 .
  ?tick1 math:lessThan ?tick2 .
} => {
  ?task1 :completedBefore ?task2 .
} .
```

**Issue:** Requires Python orchestration layer to assign tick numbers.

---

### 7.5 No Arbitrary Unbounded Iteration

**Problem:** Cannot express "repeat until condition" in pure N3.

**Example:**
```n3
# ❌ Cannot do: Loop until no active tasks
{
  (?task {?task kgc:status "Active"} ?activeTasks) log:collectAllIn ?scope .
  ?activeTasks list:length ?count .
  ?count math:greaterThan 0 .
  # Cannot express "keep running rules until count = 0"
} => {
  :workflow :step :oneMoreTick .  # IMPOSSIBLE - would cause infinite loop
} .
```

**Workaround:** Fixed-point reasoning - EYE runs rules until no new triples are derived.

**Issue:** Doesn't work for workflows that require external input or timed events.

---

## 8. Implementability Matrix

| Workflow Pattern | N3 Pure | N3 + Guards | Hybrid N3+Python | Python Only |
|------------------|---------|-------------|------------------|-------------|
| **WCP-1: Sequence** | ✅ | - | - | - |
| **WCP-2: AND-Split** | ✅ | - | - | - |
| **WCP-3: n-way AND-Join** | ❌ | ✅ (pre-count) | ✅ (dynamic count) | - |
| **WCP-4: XOR-Split** | ✅ | - | - | - |
| **WCP-5: Simple Merge** | ✅ | - | - | - |
| **WCP-6: OR-Split** | ✅ | - | - | - |
| **WCP-9: Discriminator** | ❌ | ❌ | ✅ (tick sort) | ✅ (timestamp sort) |
| **WCP-30: k-of-n Partial** | ❌ | ✅ (pre-count) | ✅ (dynamic count) | - |
| **WCP-38: Sync Merge** | ❌ | ❌ | ✅ (reachability) | ✅ (BFS/DFS) |
| **WCP-19/20: Cancellation** | ❌ | ❌ | ❌ | ✅ (retraction) |

**Legend:**
- ✅ Fully implementable
- ✅ (note) Implementable with constraints
- ❌ Not implementable
- `-` Not applicable

---

## 9. Recommended Hybrid Architecture

Based on research findings, the optimal architecture is:

### 9.1 N3/EYE Handles (Pure Monotonic)

1. **Local token passing** - Sequence, AND-split
2. **Fixed guards** - XOR-split with predicates
3. **Status markers** - Instead of retraction
4. **Validation rules** - Protocol well-formedness

### 9.2 Python Handles (Non-Monotonic)

1. **Counting** - Aggregate `log:collectAllIn` results
2. **Ordering** - Sort by tick/timestamp for discriminator
3. **Reachability** - BFS/DFS for sync merge
4. **Cancellation** - Status propagation and blocking
5. **Orchestration** - Tick-based execution loop

### 9.3 Interaction Pattern

```python
# Python orchestration loop
while not workflow.terminated():
    # 1. Materialize current state to N3
    state_n3 = workflow.to_n3()

    # 2. Run EYE reasoner
    result = eye_reasoner.reason(state_n3, "workflow_rules.n3")

    # 3. Parse inferred triples
    new_triples = parse_n3(result.output)

    # 4. Python decides on non-monotonic actions
    for triple in new_triples:
        if triple.predicate == "yawl:completedPredecessors":
            # Python counts and decides
            if len(triple.object) >= workflow.expected_count:
                workflow.activate(triple.subject)

        elif triple.predicate == "yawl:discriminatorComplete":
            # Python sorts by tick and picks winner
            winner = min(triple.object, key=lambda t: t.tick)
            workflow.activate_from_discriminator(winner)

    # 5. Increment tick
    workflow.tick += 1
```

---

## 10. References

### Primary Sources

- [W3C N3 Builtins Specification](https://w3c.github.io/N3/reports/20230703/builtins.html)
- [EYE Builtins Reference](https://eulersharp.sourceforge.net/2003/03swap/eye-builtins.html)
- [N3 Language Specification](https://w3c.github.io/N3/spec/)
- [EYE Reasoner GitHub](https://github.com/eyereasoner/eye)

### N3 Negation and Scoping

- [Custom built-in for negation-as-failure (N3 Issue #18)](https://github.com/w3c/N3/issues/18)
- [Closing the world (N3 Issue #9)](https://github.com/w3c/N3/issues/9)
- [EYE log-rules.n3](https://github.com/josd/eye/blob/master/log-rules.n3)

### List and Math Operations

- [N3 List Functions](https://w3c.github.io/N3/ns/list.html)
- [N3 String Processing Ontology](https://w3c.github.io/N3/ns/string.html)
- [RDF-N3 Ruby Implementation](https://github.com/ruby-rdf/rdf-n3)

### Workflow Patterns

- [YAWL: Yet Another Workflow Language (PDF)](https://www.vdaalst.com/publications/p174.pdf)
- [YAWL Foundation Patterns](http://www.yawlfoundation.org/pages/resources/patterns.html)
- [Drawing Conclusions from Linked Data: The EYE Reasoner](https://dl.acm.org/doi/abs/10.1109/MS.2015.63)

---

## Conclusion

N3/EYE provides powerful builtins for:
- ✅ **Counting** - `log:collectAllIn` + `list:length`
- ✅ **Aggregation** - `math:sum`, `math:product`
- ✅ **Comparison** - `math:greaterThan`, `string:lessThan`
- ✅ **Scoped negation** - `log:notIncludes`
- ✅ **List operations** - `list:member`, `list:append`

But has fundamental limitations:
- ❌ **No retraction** (monotonic only)
- ❌ **No global reachability** (requires BFS/DFS)
- ❌ **No temporal ordering** (within same tick)
- ❌ **No unbounded iteration** (fixed-point only)

**Recommended approach:** Hybrid N3+Python architecture with clear separation of concerns.
