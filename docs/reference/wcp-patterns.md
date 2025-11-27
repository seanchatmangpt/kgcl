# WCP-43 Workflow Control Patterns

Complete reference for all 43 YAWL Workflow Control Patterns implemented in N3 rules.

## Pattern Categories

| Category | Patterns | Description |
|----------|----------|-------------|
| Basic Control Flow | 1-5 | Sequence, splits, joins, choices |
| Advanced Branching | 6-9 | Multi-choice, sync, merge, discriminator |
| Structural | 10-11 | Cycles, implicit termination |
| Multiple Instances | 12-15 | MI without/with sync, runtime knowledge |
| State-Based | 16-18 | Deferred choice, interleaved, milestone |
| Cancellation | 19-20, 25-27 | Cancel task/case/region/MI |
| Iteration | 21-22 | Structured loop, recursion |
| Triggers | 23-24 | Transient, persistent triggers |
| Advanced Sync | 28-36 | Discriminators, partial joins |
| Termination | 37-43 | Sync merge, critical section, explicit termination |

## KGC Verbs

| Verb | Action | Patterns |
|------|--------|----------|
| **Transmute** | Change status | WCP 1, 11, 21-22 |
| **Copy** | Parallel activation | WCP 2, 12-15 |
| **Filter** | Conditional routing | WCP 4-6, 9 |
| **Await** | Synchronization | WCP 3, 7-8, 28-36 |
| **Void** | Cancellation | WCP 19-20, 25-27, 43 |

---

## Basic Control Flow (WCP 1-5)

### WCP-1: Sequence

**Verb**: Transmute

When a task completes, the next task in sequence activates.

```turtle
# Topology
<urn:task:A> kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .
<urn:flow:1> yawl:nextElementRef <urn:task:B> .
<urn:task:B> kgc:status "Pending" .

# Result: B becomes Active
```

### WCP-2: Parallel Split (AND-Split)

**Verb**: Copy

When a task with AND-split completes, ALL outgoing branches activate.

```turtle
# Topology
<urn:task:Split> kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .
<urn:flow:1> yawl:nextElementRef <urn:task:B1> .
<urn:flow:2> yawl:nextElementRef <urn:task:B2> .

# Result: Both B1 and B2 become Active
```

### WCP-3: Synchronization (AND-Join)

**Verb**: Await

Task with AND-join activates only when ALL incoming tasks complete.

```turtle
# Topology
<urn:task:B1> kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .
<urn:task:B2> kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:2> .
<urn:flow:1> yawl:nextElementRef <urn:task:Join> .
<urn:flow:2> yawl:nextElementRef <urn:task:Join> .
<urn:task:Join> yawl:hasJoin yawl:ControlTypeAnd .

# Result: Join becomes Active (after both B1 AND B2 complete)
```

### WCP-4: Exclusive Choice (XOR-Split)

**Verb**: Filter

When a task with XOR-split completes, ONE branch activates based on condition.

```turtle
# Topology
<urn:task:Decision> kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .
<urn:flow:1> yawl:nextElementRef <urn:task:Yes> ;
    yawl:predicate "condition=true" .
<urn:flow:2> yawl:nextElementRef <urn:task:No> ;
    yawl:isDefaultFlow true .

# Result: One of Yes or No becomes Active
```

### WCP-5: Simple Merge (XOR-Join)

**Verb**: Transmute

Task with XOR-join activates when ANY incoming task completes.

```turtle
# Topology
<urn:task:B1> kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .
<urn:flow:1> yawl:nextElementRef <urn:task:Merge> .
<urn:task:Merge> yawl:hasJoin yawl:ControlTypeXor .

# Result: Merge becomes Active (when B1 OR B2 completes)
```

---

## Advanced Branching (WCP 6-9)

### WCP-6: Multi-Choice (OR-Split)

**Verb**: Filter

Multiple branches can activate based on conditions.

### WCP-7: Structured Synchronizing Merge

**Verb**: Await

Merge that waits for all activated branches.

### WCP-8: Multi-Merge

**Verb**: Await

Each incoming completion triggers downstream activation.

### WCP-9: Structured Discriminator

**Verb**: Filter

Activates on first completion, ignores subsequent.

---

## Structural (WCP 10-11)

### WCP-10: Arbitrary Cycles

Allows loops in workflow structure.

### WCP-11: Implicit Termination

**Verb**: Transmute

Workflow ends when no tasks remain active.

---

## Multiple Instances (WCP 12-15)

### WCP-12: MI without Synchronization

**Verb**: Copy

Spawn multiple instances, no waiting.

### WCP-13: MI with Design-Time Knowledge

**Verb**: Copy + Await

Fixed number of instances, synchronize on completion.

### WCP-14: MI with Runtime Knowledge

**Verb**: Copy + Await

Instance count determined at runtime.

### WCP-15: MI without A-Priori Runtime Knowledge

**Verb**: Copy + Await

Instance count unknown until execution.

---

## State-Based (WCP 16-18)

### WCP-16: Deferred Choice

Choice made by environment, not workflow.

### WCP-17: Interleaved Parallel Routing

Tasks execute in any order, but not concurrently.

### WCP-18: Milestone

Task only executes if milestone is reached.

---

## Cancellation (WCP 19-20, 25-27)

### WCP-19: Cancel Task

**Verb**: Void

Cancel a specific task.

```turtle
# Cancel task B
<urn:task:B> kgc:status "Cancelled" .
```

### WCP-20: Cancel Case

**Verb**: Void

Cancel entire workflow instance.

### WCP-25: Cancel Region

**Verb**: Void

Cancel a specific region of tasks.

### WCP-26: Cancel MI Task

**Verb**: Void

Cancel one instance in multi-instance.

### WCP-27: Complete MI Task

**Verb**: Void

Complete multi-instance when threshold met.

---

## Iteration (WCP 21-22)

### WCP-21: Structured Loop

**Verb**: Transmute

Repeat tasks until condition met.

### WCP-22: Recursion

**Verb**: Transmute

Self-referential workflow invocation.

---

## Triggers (WCP 23-24)

### WCP-23: Transient Trigger

External signal that must be caught immediately.

### WCP-24: Persistent Trigger

External signal that persists until processed.

---

## Advanced Synchronization (WCP 28-36)

### WCP-28: Blocking Discriminator

First completion proceeds, others wait.

### WCP-29: Cancelling Discriminator

First completion proceeds, others cancelled.

### WCP-30: Structured Partial Join

N-of-M synchronization.

### WCP-31-36: Variations

Additional partial join and discriminator patterns.

---

## Termination (WCP 37-43)

### WCP-37: Local Synchronizing Merge

Merge at local scope.

### WCP-38: General Synchronizing Merge

Merge at any scope.

### WCP-39: Critical Section

Exclusive access region.

### WCP-40: Interleaved Routing

Non-concurrent parallel.

### WCP-41: Thread Merge

Merge parallel threads.

### WCP-42: Thread Split

Split into parallel threads.

### WCP-43: Explicit Termination

**Verb**: Void

Explicitly terminate workflow.

```turtle
<urn:workflow:1> kgc:status "Terminated" .
```

---

## Using Patterns

### Get Pattern Info

```python
from kgcl.hybrid import get_pattern_info

info = get_pattern_info(1)
# {'name': 'Sequence', 'verb': 'Transmute', 'category': 'Basic Control Flow'}
```

### Get N3 Rule

```python
from kgcl.hybrid import get_pattern_rule

rule = get_pattern_rule(2)
# Returns N3 rule for WCP-2 (Parallel Split)
```

### Filter Patterns

```python
from kgcl.hybrid import get_patterns_by_category, get_patterns_by_verb

# By category
basic = get_patterns_by_category("Basic Control Flow")
# [1, 2, 3, 4, 5]

# By verb
cancel = get_patterns_by_verb("Void")
# [19, 20, 25, 26, 27, 43]
```

### Use Subset of Rules

```python
from kgcl.hybrid import WCP43RulesAdapter

adapter = WCP43RulesAdapter()
# Only use sequence and parallel split
rules = adapter.get_rule_subset([1, 2])
```
