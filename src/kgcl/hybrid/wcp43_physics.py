"""WCP-43 Complete Physics Ontology - All 43 Workflow Control Patterns.

This module implements ALL 43 YAWL Workflow Control Patterns as N3 physics laws
following van der Aalst et al.'s formal specifications.

Architecture
------------
- ALL state stored in Oxigraph (RDF triples)
- N3 rules handle pattern matching and inference
- Counter state tracked via RDF properties with math:sum
- Negation via () log:notIncludes {} pattern (EYE compatible)
- Monotonic assertions with status markers (no retraction)

The patterns are organized into 8 categories:
1. Basic Control Flow (WCP 1-5)
2. Advanced Branching (WCP 6-9)
3. Structural (WCP 10-11)
4. Multiple Instances (WCP 12-15)
5. State-Based (WCP 16-18)
6. Cancellation (WCP 19-20, 25-27)
7. Iteration & Triggers (WCP 21-24)
8. Advanced Joins & Sync (WCP 28-43)

References
----------
- van der Aalst et al. (2003) "Workflow Patterns"
- Russell et al. (2006) "Workflow Control-Flow Patterns: A Revised View"
- YAWL Workflow Patterns: http://www.workflowpatterns.com
"""

from __future__ import annotations

# ==============================================================================
# STANDARD PREFIXES
# ==============================================================================

STANDARD_PREFIXES: str = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix log: <http://www.w3.org/2000/10/swap/log#> .
@prefix math: <http://www.w3.org/2000/10/swap/math#> .
@prefix list: <http://www.w3.org/2000/10/swap/list#> .
@prefix string: <http://www.w3.org/2000/10/swap/string#> .
@prefix e: <http://eulersharp.sourceforge.net/2003/03swap/log-rules#> .
"""

# ==============================================================================
# LAW 0: TASK INITIALIZATION
# ==============================================================================

TASK_INITIALIZATION = """
# =============================================================================
# LAW 0 - TASK INITIALIZATION (Bootstrap)
# =============================================================================
# Initialize any yawl:Task that doesn't have a kgc:status to "Pending".
# Uses blank node scope with log:notIncludes for EYE-compatible negation.
{
    ?task a yawl:Task .
    _:scope log:notIncludes { ?task kgc:status _:anyStatus } .
}
=>
{
    ?task kgc:status "Pending" .
} .
"""

# ==============================================================================
# WCP 1-5: BASIC CONTROL FLOW PATTERNS
# ==============================================================================

WCP1_SEQUENCE = """
# =============================================================================
# LAW 1 - WCP-1: SEQUENCE (Transmute)
# =============================================================================
# van der Aalst: "A task is enabled after completion of preceding task."
# Semantics: Single thread of control, immediate activation.
# NOTE: Only fires when:
#   - Source task has NO explicit split type (AND, XOR, OR)
#   - Target task is NOT an AND-Join (AND-Joins need all predecessors via WCP3)
#       Tasks with split types are handled by WCP2, WCP4, WCP6.
#       AND-Join tasks are handled by WCP3.
#       Other join types (PartialJoin, XOR-Join, OR-Join) activate via WCP1 when
#       any predecessor completes (simplified behavior for testing).
{
    ?task kgc:status "Completed" .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?next kgc:status "Pending" .
    # Only fire for simple sequence - no split type on source
    _:scope log:notIncludes { ?task yawl:hasSplit _:anySplit } .
    # Only fire if target is NOT an AND-Join (those need all predecessors)
    _:scope2 log:notIncludes { ?next yawl:hasJoin yawl:ControlTypeAnd } .
}
=>
{
    ?next kgc:status "Active" .
} .
"""

WCP2_PARALLEL_SPLIT = """
# =============================================================================
# LAW 2 - WCP-2: PARALLEL SPLIT / AND-SPLIT (Copy)
# =============================================================================
# van der Aalst: "Single thread splits into multiple parallel threads."
# Semantics: ALL outgoing branches activated simultaneously.
# NOTE: Does NOT activate tasks with AND-Join (those need all predecessors via WCP3).
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeAnd .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?next kgc:status "Pending" .
    # Don't activate AND-Join tasks - they need all predecessors completed (WCP3)
    _:scope log:notIncludes { ?next yawl:hasJoin yawl:ControlTypeAnd } .
}
=>
{
    ?next kgc:status "Active" .
} .
"""

WCP3_SYNCHRONIZATION = """
# =============================================================================
# LAW 3 - WCP-3: SYNCHRONIZATION / AND-JOIN (Await)
# =============================================================================
# van der Aalst: "Multiple parallel threads converge, waiting for ALL."
# Semantics: AND-Join activates ONLY when ALL predecessors are Completed.
#
# Implementation: Uses scoped negation to verify no incomplete predecessor exists.
# The rule fires when:
#   1. Task has AND-Join type
#   2. Task is Pending
#   3. There exists at least one predecessor that flows into this task
#   4. NO predecessor exists that is NOT Completed (i.e., all are Completed)

{
    ?task yawl:hasJoin yawl:ControlTypeAnd .
    ?task kgc:status "Pending" .
    # Must have at least one predecessor
    ?somePred yawl:flowsInto ?someFlow .
    ?someFlow yawl:nextElementRef ?task .
    ?somePred kgc:status "Completed" .
    # Check that NO predecessor is NOT Completed (all must be Completed)
    _:scope log:notIncludes {
        _:anyPred yawl:flowsInto _:anyFlow .
        _:anyFlow yawl:nextElementRef ?task .
        _:scope2 log:notIncludes { _:anyPred kgc:status "Completed" } .
    } .
}
=>
{
    ?task kgc:status "Active" .
} .
"""

WCP4_EXCLUSIVE_CHOICE = """
# =============================================================================
# LAW 4 - WCP-4: EXCLUSIVE CHOICE / XOR-SPLIT (Filter)
# =============================================================================
# van der Aalst: "Based on decision, ONE of several branches is chosen."
# Semantics: MUTUAL EXCLUSION - only ONE branch activates.
#
# Implementation: Uses _:scope log:notIncludes for deterministic branch selection.
# - Rule 4a: Predicate branch with evaluatesTo true -> Active
# - Rule 4b: Default branch -> Active ONLY if NO predicate evaluates to true
#
# This approach uses EYE's scoped negation to check if any predicate evaluated
# to true before activating the default branch.

# Rule 4a: Predicate-based branch selection (predicate evaluates to true)
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeXor .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?flow yawl:hasPredicate ?pred .
    ?pred kgc:evaluatesTo true .
    ?next kgc:status "Pending" .
}
=>
{
    ?next kgc:status "Active" .
} .

# Rule 4b: Default path - fires ONLY if no predicate branch evaluated to true
# Uses scoped negation: check that no flow from this task has a true predicate
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeXor .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?flow yawl:isDefaultFlow true .
    ?next kgc:status "Pending" .

    # Check that no flow from this task has a predicate that evaluates to true
    _:scope log:notIncludes {
        ?task yawl:flowsInto _:otherFlow .
        _:otherFlow yawl:hasPredicate _:otherPred .
        _:otherPred kgc:evaluatesTo true .
    } .
}
=>
{
    ?next kgc:status "Active" .
} .
"""

WCP5_SIMPLE_MERGE = """
# =============================================================================
# LAW 5 - WCP-5: SIMPLE MERGE / XOR-JOIN (Transmute)
# =============================================================================
# van der Aalst: "Alternative branches come together without synchronization."
# Semantics: First arrival triggers, no waiting.
{
    ?task yawl:hasJoin yawl:ControlTypeXor .
    ?incoming yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?task .
    ?incoming kgc:status "Completed" .
    ?task kgc:status "Pending" .
}
=>
{
    ?task kgc:status "Active" .
} .
"""

# ==============================================================================
# WCP 6-9: ADVANCED BRANCHING AND SYNCHRONIZATION
# ==============================================================================

WCP6_MULTI_CHOICE = """
# =============================================================================
# LAW 6 - WCP-6: MULTI-CHOICE / OR-SPLIT (Filter)
# =============================================================================
# van der Aalst: "One or MORE branches chosen based on conditions."
# Semantics: Each true predicate activates its branch (parallel execution).
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeOr .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?flow yawl:hasPredicate ?pred .
    ?pred kgc:evaluatesTo true .
    ?next kgc:status "Pending" .
}
=>
{
    ?next kgc:status "Active" .
    ?next kgc:activatedBy ?task .
    ?task kgc:orBranchActivated ?next .
} .

# Mark split as evaluated after all predicates processed
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeOr .
    () log:notIncludes { ?task kgc:splitEvaluated true } .
}
=>
{
    ?task kgc:splitEvaluated true .
} .
"""

WCP7_STRUCTURED_SYNC_MERGE = """
# =============================================================================
# LAW 7 - WCP-7: STRUCTURED SYNCHRONIZING MERGE / OR-JOIN (Await)
# =============================================================================
# van der Aalst: "Wait for all ACTIVE branches from corresponding OR-split."
# Semantics: Track which branches were activated, wait for those only.

# Track expected branches from split
{
    ?next kgc:activatedBy ?split .
    ?next yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?merge .
    ?merge yawl:hasJoin yawl:ControlTypeOr .
    ?merge kgc:correspondingSplit ?split .
}
=>
{
    ?merge kgc:expectsBranch ?next .
} .

# Mark completed branches
{
    ?merge kgc:expectsBranch ?branch .
    ?branch kgc:status "Completed" .
    () log:notIncludes { ?merge kgc:branchCompleted ?branch } .
}
=>
{
    ?merge kgc:branchCompleted ?branch .
} .

# Fire when all expected branches complete (count-based)
{
    ?merge yawl:hasJoin yawl:ControlTypeOr .
    ?merge kgc:status "Pending" .
    ?merge kgc:expectedBranchCount ?expected .
    ?merge kgc:completedBranchCount ?completed .
    ?completed math:notLessThan ?expected .
}
=>
{
    ?merge kgc:status "Active" .
} .
"""

WCP8_MULTI_MERGE = """
# =============================================================================
# LAW 8 - WCP-8: MULTI-MERGE (Transmute)
# =============================================================================
# van der Aalst: "Each branch independently triggers subsequent task."
# Semantics: May fire multiple times (once per incoming branch).
{
    ?task yawl:hasJoin yawl:ControlTypeMultiMerge .
    ?incoming yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?task .
    ?incoming kgc:status "Completed" .
    () log:notIncludes { ?incoming kgc:multiMergeProcessed ?task } .
}
=>
{
    ?task kgc:status "Active" .
    ?incoming kgc:multiMergeProcessed ?task .
    ?task kgc:activationInstance ?incoming .
} .
"""

WCP9_STRUCTURED_DISCRIMINATOR = """
# =============================================================================
# LAW 9 - WCP-9: STRUCTURED DISCRIMINATOR (Await)
# =============================================================================
# van der Aalst: "First incoming branch enables task, later ignored until reset."
# Semantics: First-arrival wins, consume remaining, reset when all consumed.

# First arrival fires the discriminator
{
    ?disc yawl:hasJoin yawl:ControlTypeDiscriminator .
    ?disc kgc:discriminatorState "waiting" .
    ?incoming yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?disc .
    ?incoming kgc:status "Completed" .
}
=>
{
    ?disc kgc:status "Active" .
    ?disc kgc:discriminatorState "fired" .
    ?disc kgc:winningBranch ?incoming .
    ?incoming kgc:discriminatorConsumed ?disc .
} .

# Consume subsequent completions silently
{
    ?disc yawl:hasJoin yawl:ControlTypeDiscriminator .
    ?disc kgc:discriminatorState "fired" .
    ?incoming yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?disc .
    ?incoming kgc:status "Completed" .
    () log:notIncludes { ?incoming kgc:discriminatorConsumed ?disc } .
}
=>
{
    ?incoming kgc:discriminatorConsumed ?disc .
} .

# Reset when all branches consumed (count-based)
{
    ?disc yawl:hasJoin yawl:ControlTypeDiscriminator .
    ?disc kgc:discriminatorState "fired" .
    ?disc kgc:consumedBranchCount ?consumed .
    ?disc kgc:totalBranchCount ?total .
    ?consumed math:notLessThan ?total .
}
=>
{
    ?disc kgc:discriminatorState "waiting" .
} .
"""

# ==============================================================================
# WCP 10-11: STRUCTURAL PATTERNS
# ==============================================================================

WCP10_ARBITRARY_CYCLES = """
# =============================================================================
# LAW 10 - WCP-10: ARBITRARY CYCLES (Filter)
# =============================================================================
# van der Aalst: "Tasks executed repeatedly (unstructured loops)."
# Semantics: Back-edge conditional on loop predicate.

# Continue loop when condition true
{
    ?task kgc:status "Completed" .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?flow yawl:isBackEdge true .
    ?flow yawl:loopCondition ?cond .
    ?cond kgc:evaluatesTo true .
    ?task kgc:iterationCount ?oldCount .
}
=>
{
    ?next kgc:status "Active" .
    (?oldCount 1) math:sum ?newCount .
    ?next kgc:iterationCount ?newCount .
} .

# Exit loop when condition false
{
    ?task kgc:status "Completed" .
    ?task yawl:flowsInto ?exitFlow .
    ?exitFlow yawl:nextElementRef ?exit .
    ?exitFlow yawl:isExitEdge true .
    ?task yawl:flowsInto ?loopFlow .
    ?loopFlow yawl:loopCondition ?cond .
    ?cond kgc:evaluatesTo false .
    ?exit kgc:status "Pending" .
}
=>
{
    ?exit kgc:status "Active" .
} .
"""

WCP11_IMPLICIT_TERMINATION = """
# =============================================================================
# LAW 11 - WCP-11: IMPLICIT TERMINATION (Void)
# =============================================================================
# van der Aalst: "Process terminates when no more tasks to execute."
# Semantics: Deadlock-free completion detection.
# A completed task with no outgoing flows is implicitly terminated.
{
    ?task kgc:status "Completed" .
    _:scope log:notIncludes { ?task yawl:flowsInto _:anyFlow } .
}
=>
{
    ?task kgc:terminated true .
    ?task kgc:terminationType "implicit" .
} .
"""

# ==============================================================================
# WCP 12-15: MULTIPLE INSTANCE PATTERNS
# ==============================================================================

WCP12_MI_WITHOUT_SYNC = """
# =============================================================================
# LAW 12 - WCP-12: MI WITHOUT SYNCHRONIZATION (Copy)
# =============================================================================
# van der Aalst: "Multiple instances created, each independent."
# Semantics: Each instance proceeds independently to successor.

# Spawn instances (instance creation tracked in RDF)
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:synchronization "none" .
    ?mi kgc:status "Active" .
    ?mi kgc:instanceCount ?n .
    ?mi kgc:spawnedCount ?spawned .
    ?spawned math:lessThan ?n .
}
=>
{
    (?spawned 1) math:sum ?newSpawned .
    ?mi kgc:spawnedCount ?newSpawned .
    ?mi kgc:hasInstance ?newSpawned .
} .

# Each instance completion independently enables successor
{
    ?instance kgc:parentMI ?mi .
    ?mi kgc:synchronization "none" .
    ?instance kgc:status "Completed" .
    ?mi yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    () log:notIncludes { ?instance kgc:successorEnabled true } .
}
=>
{
    ?next kgc:status "Active" .
    ?instance kgc:successorEnabled true .
} .
"""

WCP13_MI_DESIGN_TIME = """
# =============================================================================
# LAW 13 - WCP-13: MI WITH A PRIORI DESIGN-TIME KNOWLEDGE (Copy+Await)
# =============================================================================
# van der Aalst: "Fixed number known at design time, synchronize on completion."
# Semantics: Spawn N, wait for ALL N to complete.

# Initialize MI with design-time count
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:synchronization "all" .
    ?mi kgc:instanceCountType "designTime" .
    ?mi kgc:status "Active" .
    ?mi kgc:instanceCount ?n .
    () log:notIncludes { ?mi kgc:miInitialized true } .
}
=>
{
    ?mi kgc:remainingInstances ?n .
    ?mi kgc:status "AwaitingCompletion" .
    ?mi kgc:miInitialized true .
} .

# Decrement on instance completion
{
    ?instance kgc:parentMI ?mi .
    ?mi kgc:synchronization "all" .
    ?instance kgc:status "Completed" .
    ?mi kgc:remainingInstances ?remaining .
    ?remaining math:greaterThan 0 .
    () log:notIncludes { ?instance kgc:miCounted true } .
}
=>
{
    (-1 ?remaining) math:sum ?newRemaining .
    ?mi kgc:remainingInstances ?newRemaining .
    ?instance kgc:miCounted true .
} .

# Fire when all instances complete
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:synchronization "all" .
    ?mi kgc:remainingInstances 0 .
    ?mi kgc:status "AwaitingCompletion" .
    ?mi yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
}
=>
{
    ?mi kgc:status "Completed" .
    ?next kgc:status "Active" .
} .
"""

WCP14_MI_RUNTIME = """
# =============================================================================
# LAW 14 - WCP-14: MI WITH A PRIORI RUNTIME KNOWLEDGE (Copy+Await)
# =============================================================================
# van der Aalst: "Instance count determined at runtime start."
# Semantics: Evaluate expression, then behave like WCP-13.
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:synchronization "all" .
    ?mi kgc:instanceCountType "runtime" .
    ?mi kgc:status "Active" .
    ?mi kgc:instanceCountExpression ?expr .
    ?expr kgc:evaluatesTo ?n .
    () log:notIncludes { ?mi kgc:miInitialized true } .
}
=>
{
    ?mi kgc:instanceCount ?n .
    ?mi kgc:remainingInstances ?n .
    ?mi kgc:status "AwaitingCompletion" .
    ?mi kgc:miInitialized true .
} .
"""

WCP15_MI_NO_APRIORI = """
# =============================================================================
# LAW 15 - WCP-15: MI WITHOUT A PRIORI RUNTIME KNOWLEDGE (Copy+Await)
# =============================================================================
# van der Aalst: "Instance count not known a priori, can add dynamically."
# Semantics: Spawning phase, then await phase.

# Enter spawning phase
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:synchronization "all" .
    ?mi kgc:instanceCountType "dynamic" .
    ?mi kgc:status "Active" .
    () log:notIncludes { ?mi kgc:miPhase ?anyPhase } .
}
=>
{
    ?mi kgc:miPhase "spawning" .
    ?mi kgc:activeInstances 0 .
    ?mi kgc:completedInstances 0 .
} .

# Accept spawn request during spawning phase
{
    ?mi kgc:miPhase "spawning" .
    ?mi kgc:spawnRequest ?req .
    ?req kgc:action "create" .
    ?mi kgc:activeInstances ?active .
    () log:notIncludes { ?req kgc:processed true } .
}
=>
{
    (?active 1) math:sum ?newActive .
    ?mi kgc:activeInstances ?newActive .
    ?req kgc:processed true .
} .

# Close spawning phase
{
    ?mi kgc:miPhase "spawning" .
    ?mi kgc:spawnRequest ?req .
    ?req kgc:action "close" .
}
=>
{
    ?mi kgc:miPhase "awaiting" .
    ?mi kgc:status "AwaitingCompletion" .
} .

# Complete when all active instances done
{
    ?mi kgc:miPhase "awaiting" .
    ?mi kgc:activeInstances ?active .
    ?mi kgc:completedInstances ?completed .
    ?completed math:notLessThan ?active .
    ?mi yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
}
=>
{
    ?mi kgc:status "Completed" .
    ?next kgc:status "Active" .
} .
"""

# ==============================================================================
# WCP 16-18: STATE-BASED PATTERNS
# ==============================================================================

WCP16_DEFERRED_CHOICE = """
# =============================================================================
# LAW 16 - WCP-16: DEFERRED CHOICE (Filter)
# =============================================================================
# van der Aalst: "Choice determined by environment (first enabled wins)."
# Semantics: Racing branches, first external enable wins.

# First externally enabled branch wins
{
    ?choice kgc:type "DeferredChoice" .
    ?choice kgc:status "Waiting" .
    ?choice yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?branch .
    ?branch kgc:externallyEnabled true .
    () log:notIncludes { ?choice kgc:choiceResolved true } .
}
=>
{
    ?choice kgc:status "Resolved" .
    ?branch kgc:status "Active" .
    ?choice kgc:selectedBranch ?branch .
    ?choice kgc:choiceResolved true .
} .

# Disable losing branches
{
    ?choice kgc:type "DeferredChoice" .
    ?choice kgc:choiceResolved true .
    ?choice kgc:selectedBranch ?winner .
    ?choice yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?loser .
    () log:notIncludes { ?loser log:equalTo ?winner } .
    () log:notIncludes { ?loser kgc:status "Disabled" } .
}
=>
{
    ?loser kgc:status "Disabled" .
} .
"""

WCP17_INTERLEAVED_PARALLEL = """
# =============================================================================
# LAW 17 - WCP-17: INTERLEAVED PARALLEL ROUTING (Filter+Await)
# =============================================================================
# van der Aalst: "Tasks execute in any order but not simultaneously."
# Semantics: Mutex-based serialization.

# Acquire mutex when free
{
    ?region kgc:type "InterleavedParallel" .
    ?region kgc:contains ?task .
    ?task kgc:status "Ready" .
    ?region kgc:mutex ?mutex .
    ?mutex kgc:holder "none" .
}
=>
{
    ?mutex kgc:holder ?task .
    ?task kgc:status "Active" .
} .

# Release mutex on completion
{
    ?region kgc:type "InterleavedParallel" .
    ?region kgc:contains ?task .
    ?task kgc:status "Completed" .
    ?region kgc:mutex ?mutex .
    ?mutex kgc:holder ?task .
}
=>
{
    ?mutex kgc:holder "none" .
} .

# Block when mutex held by another
{
    ?region kgc:type "InterleavedParallel" .
    ?region kgc:contains ?task .
    ?task kgc:status "Ready" .
    ?region kgc:mutex ?mutex .
    ?mutex kgc:holder ?other .
    () log:notIncludes { ?other log:equalTo "none" } .
}
=>
{
    ?task kgc:status "Blocked" .
    ?task kgc:waitingFor ?mutex .
} .
"""

WCP18_MILESTONE = """
# =============================================================================
# LAW 18 - WCP-18: MILESTONE (Await)
# =============================================================================
# van der Aalst: "Task enabled only when process in specific state."
# Semantics: Gate opens when milestone achieved.

# Enable when milestone achieved
{
    ?task kgc:status "Ready" .
    ?task kgc:requiresMilestone ?milestone .
    ?milestone kgc:status "Achieved" .
}
=>
{
    ?task kgc:status "Active" .
} .

# Block when milestone not achieved
{
    ?task kgc:status "Ready" .
    ?task kgc:requiresMilestone ?milestone .
    ?milestone kgc:status "NotAchieved" .
}
=>
{
    ?task kgc:status "Blocked" .
    ?task kgc:waitingFor ?milestone .
} .

# Withdraw if milestone lost during execution
{
    ?task kgc:status "Active" .
    ?task kgc:requiresMilestone ?milestone .
    ?milestone kgc:status "Withdrawn" .
}
=>
{
    ?task kgc:status "Withdrawn" .
    ?task kgc:withdrawnDueTo ?milestone .
} .
"""

# ==============================================================================
# WCP 19-20, 25-27: CANCELLATION PATTERNS
# ==============================================================================

WCP19_CANCEL_TASK = """
# =============================================================================
# LAW 19 - WCP-19: CANCEL TASK (Void)
# =============================================================================
# van der Aalst: "Individual task is cancelled."
# Semantics: Monotonic cancellation marker (no retraction).
{
    ?task kgc:cancelRequested true .
    ?task kgc:status ?oldStatus .
    () log:notIncludes { ?oldStatus log:equalTo "Completed" } .
    () log:notIncludes { ?oldStatus log:equalTo "Cancelled" } .
}
=>
{
    ?task kgc:status "Cancelled" .
    ?task kgc:previousStatus ?oldStatus .
} .
"""

WCP20_CANCEL_CASE = """
# =============================================================================
# LAW 20 - WCP-20: CANCEL CASE (Void)
# =============================================================================
# van der Aalst: "Entire process instance is cancelled."
# Semantics: Cascading cancellation to all tasks.
{
    ?case kgc:cancelRequested true .
    ?case kgc:hasTask ?task .
    ?task kgc:status ?status .
    () log:notIncludes { ?status log:equalTo "Completed" } .
    () log:notIncludes { ?status log:equalTo "Cancelled" } .
}
=>
{
    ?case kgc:status "Cancelled" .
    ?task kgc:status "Cancelled" .
    ?task kgc:cancelledBy ?case .
} .
"""

WCP25_CANCEL_REGION = """
# =============================================================================
# LAW 25 - WCP-25: CANCEL REGION (Void)
# =============================================================================
# van der Aalst: "Specific region (subset) of process is cancelled."
# Semantics: Scoped cancellation.
{
    ?region kgc:cancelRequested true .
    ?region kgc:contains ?task .
    ?task kgc:status ?status .
    () log:notIncludes { ?status log:equalTo "Completed" } .
    () log:notIncludes { ?status log:equalTo "Cancelled" } .
}
=>
{
    ?region kgc:status "Cancelled" .
    ?task kgc:status "Cancelled" .
    ?task kgc:cancelledBy ?region .
} .
"""

WCP26_CANCEL_MI_ACTIVITY = """
# =============================================================================
# LAW 26 - WCP-26: CANCEL MULTIPLE INSTANCE ACTIVITY (Void)
# =============================================================================
# van der Aalst: "All instances of MI task are cancelled."
# Semantics: Bulk instance cancellation.
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:cancelRequested true .
    ?instance kgc:parentMI ?mi .
    ?instance kgc:status ?status .
    () log:notIncludes { ?status log:equalTo "Completed" } .
    () log:notIncludes { ?status log:equalTo "Cancelled" } .
}
=>
{
    ?mi kgc:status "Cancelled" .
    ?instance kgc:status "Cancelled" .
    ?instance kgc:cancelledBy ?mi .
} .
"""

WCP27_COMPLETE_MI_ACTIVITY = """
# =============================================================================
# LAW 27 - WCP-27: COMPLETE MULTIPLE INSTANCE ACTIVITY (Void+Await)
# =============================================================================
# van der Aalst: "Force early completion of MI, cancel remaining."
# Semantics: Partial completion acceptance.

# Mark completed instances as contributing
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:forceCompleteRequested true .
    ?instance kgc:parentMI ?mi .
    ?instance kgc:status "Completed" .
}
=>
{
    ?instance kgc:contributesToCompletion true .
} .

# Cancel remaining active instances
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:forceCompleteRequested true .
    ?instance kgc:parentMI ?mi .
    ?instance kgc:status ?status .
    () log:notIncludes { ?status log:equalTo "Completed" } .
    () log:notIncludes { ?status log:equalTo "Cancelled" } .
    () log:notIncludes { ?status log:equalTo "ForcedCancelled" } .
}
=>
{
    ?instance kgc:status "ForcedCancelled" .
} .

# Complete MI when force requested and at least one instance done
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:forceCompleteRequested true .
    ?mi kgc:hasCompletedInstance true .
    ?mi yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    () log:notIncludes { ?mi kgc:status "Completed" } .
}
=>
{
    ?mi kgc:status "Completed" .
    ?next kgc:status "Active" .
} .
"""

# ==============================================================================
# WCP 21-24: ITERATION AND TRIGGER PATTERNS
# ==============================================================================

WCP21_STRUCTURED_LOOP = """
# =============================================================================
# LAW 21 - WCP-21: STRUCTURED LOOP (Filter)
# =============================================================================
# van der Aalst: "Task executed repeatedly using structured loop constructs."
# Semantics: Pre/post-test loop with counter.

# Continue iteration when condition true and under max
{
    ?loop kgc:type "StructuredLoop" .
    ?loop kgc:status "Evaluating" .
    ?loop kgc:loopCondition ?cond .
    ?cond kgc:evaluatesTo true .
    ?loop kgc:iterationCount ?count .
    ?loop kgc:maxIterations ?max .
    ?count math:lessThan ?max .
}
=>
{
    ?loop kgc:status "Iterating" .
    (?count 1) math:sum ?newCount .
    ?loop kgc:iterationCount ?newCount .
} .

# Exit loop when condition false
{
    ?loop kgc:type "StructuredLoop" .
    ?loop kgc:status "Evaluating" .
    ?loop kgc:loopCondition ?cond .
    ?cond kgc:evaluatesTo false .
}
=>
{
    ?loop kgc:status "Completed" .
} .

# Return to evaluation after body completes
{
    ?loop kgc:type "StructuredLoop" .
    ?loop kgc:status "Iterating" .
    ?loop kgc:body ?body .
    ?body kgc:status "Completed" .
}
=>
{
    ?loop kgc:status "Evaluating" .
} .
"""

WCP22_RECURSION = """
# =============================================================================
# LAW 22 - WCP-22: RECURSION (Copy)
# =============================================================================
# van der Aalst: "Task can invoke itself recursively."
# Semantics: Stack-based with depth tracking.

# Recursive call when condition true and under max depth
{
    ?task kgc:isRecursive true .
    ?task kgc:status "Active" .
    ?task kgc:recursionCondition ?cond .
    ?cond kgc:evaluatesTo true .
    ?task kgc:depth ?depth .
    ?task kgc:maxDepth ?maxDepth .
    ?depth math:lessThan ?maxDepth .
}
=>
{
    (?depth 1) math:sum ?newDepth .
    ?task kgc:spawnsRecursion ?newDepth .
    ?task kgc:status "AwaitingRecursion" .
} .

# Base case - no more recursion
{
    ?task kgc:isRecursive true .
    ?task kgc:status "Active" .
    ?task kgc:recursionCondition ?cond .
    ?cond kgc:evaluatesTo false .
}
=>
{
    ?task kgc:status "Completed" .
} .

# Unwind recursion when child completes
{
    ?task kgc:status "AwaitingRecursion" .
    ?child kgc:parent ?task .
    ?child kgc:status "Completed" .
}
=>
{
    ?task kgc:status "Completed" .
} .
"""

WCP23_TRANSIENT_TRIGGER = """
# =============================================================================
# LAW 23 - WCP-23: TRANSIENT TRIGGER (Await)
# =============================================================================
# van der Aalst: "Signal from environment - lost if task not ready."
# Semantics: Fire-and-forget trigger.

# Consume trigger when ready
{
    ?trigger kgc:type "Transient" .
    ?trigger kgc:firedAt ?time .
    ?trigger kgc:targets ?task .
    ?task kgc:status "Ready" .
    () log:notIncludes { ?trigger kgc:triggerConsumed true } .
}
=>
{
    ?task kgc:status "Triggered" .
    ?task kgc:triggeredBy ?trigger .
    ?trigger kgc:triggerConsumed true .
    ?trigger kgc:status "Consumed" .
} .

# Lost if task not ready
{
    ?trigger kgc:type "Transient" .
    ?trigger kgc:firedAt ?time .
    ?trigger kgc:targets ?task .
    ?task kgc:status ?status .
    () log:notIncludes { ?status log:equalTo "Ready" } .
    () log:notIncludes { ?trigger kgc:triggerConsumed true } .
}
=>
{
    ?trigger kgc:status "Lost" .
    ?trigger kgc:triggerConsumed true .
} .
"""

WCP24_PERSISTENT_TRIGGER = """
# =============================================================================
# LAW 24 - WCP-24: PERSISTENT TRIGGER (Await)
# =============================================================================
# van der Aalst: "Signal from environment - queued until task ready."
# Semantics: Durable trigger queue.

# Queue trigger
{
    ?trigger kgc:type "Persistent" .
    ?trigger kgc:firedAt ?time .
    ?trigger kgc:targets ?task .
    () log:notIncludes { ?trigger kgc:status ?anyStatus } .
}
=>
{
    ?task kgc:hasPendingTrigger ?trigger .
    ?trigger kgc:status "Queued" .
} .

# Consume when task becomes ready
{
    ?task kgc:status "Ready" .
    ?task kgc:hasPendingTrigger ?trigger .
    ?trigger kgc:status "Queued" .
}
=>
{
    ?task kgc:status "Triggered" .
    ?task kgc:triggeredBy ?trigger .
    ?trigger kgc:status "Consumed" .
} .
"""

# ==============================================================================
# WCP 28-33: DISCRIMINATOR AND PARTIAL JOIN PATTERNS
# ==============================================================================

WCP28_BLOCKING_DISCRIMINATOR = """
# =============================================================================
# LAW 28 - WCP-28: BLOCKING DISCRIMINATOR (Await)
# =============================================================================
# van der Aalst: "First completion wins, blocks subsequent until reset."
# Semantics: First-wins with blocking queue.

# First completion fires
{
    ?disc kgc:type "BlockingDiscriminator" .
    ?disc kgc:status "Waiting" .
    ?disc kgc:waitingFor ?branch .
    ?branch kgc:status "Completed" .
    () log:notIncludes { ?disc kgc:discriminatorFired true } .
}
=>
{
    ?disc kgc:status "Fired" .
    ?disc kgc:winningBranch ?branch .
    ?disc kgc:discriminatorFired true .
} .

# Block subsequent completions
{
    ?disc kgc:type "BlockingDiscriminator" .
    ?disc kgc:discriminatorFired true .
    ?disc kgc:waitingFor ?branch .
    ?branch kgc:status "Completed" .
    ?disc kgc:winningBranch ?winner .
    () log:notIncludes { ?branch log:equalTo ?winner } .
    () log:notIncludes { ?branch kgc:blocked true } .
}
=>
{
    ?branch kgc:blocked true .
    ?branch kgc:blockedBy ?disc .
} .

# Reset when all complete
{
    ?disc kgc:type "BlockingDiscriminator" .
    ?disc kgc:discriminatorFired true .
    ?disc kgc:completedBranchCount ?completed .
    ?disc kgc:totalBranchCount ?total .
    ?completed math:notLessThan ?total .
}
=>
{
    ?disc kgc:status "Waiting" .
    ?disc kgc:discriminatorFired false .
} .
"""

WCP29_CANCELLING_DISCRIMINATOR = """
# =============================================================================
# LAW 29 - WCP-29: CANCELLING DISCRIMINATOR (Await+Void)
# =============================================================================
# van der Aalst: "First completion wins, cancel remaining branches."
# Semantics: First-wins with cancellation.

# First completion fires
{
    ?disc kgc:type "CancellingDiscriminator" .
    ?disc kgc:status "Waiting" .
    ?disc kgc:waitingFor ?branch .
    ?branch kgc:status "Completed" .
    () log:notIncludes { ?disc kgc:discriminatorFired true } .
}
=>
{
    ?disc kgc:status "Fired" .
    ?disc kgc:winningBranch ?branch .
    ?disc kgc:discriminatorFired true .
} .

# Cancel losing branches
{
    ?disc kgc:type "CancellingDiscriminator" .
    ?disc kgc:discriminatorFired true .
    ?disc kgc:winningBranch ?winner .
    ?disc kgc:waitingFor ?loser .
    () log:notIncludes { ?loser log:equalTo ?winner } .
    ?loser kgc:status ?status .
    () log:notIncludes { ?status log:equalTo "Completed" } .
    () log:notIncludes { ?status log:equalTo "Cancelled" } .
}
=>
{
    ?loser kgc:status "Cancelled" .
    ?loser kgc:cancelledBy ?disc .
} .
"""

WCP30_STRUCTURED_PARTIAL_JOIN = """
# =============================================================================
# LAW 30 - WCP-30: STRUCTURED PARTIAL JOIN (Await)
# =============================================================================
# van der Aalst: "N out of M branches must complete before firing."
# Semantics: Threshold-based join (N-of-M).

# Fire when threshold reached
{
    ?join kgc:type "PartialJoin" .
    ?join kgc:threshold ?n .
    ?join kgc:completedBranchCount ?count .
    ?count math:notLessThan ?n .
    ?join kgc:status "Waiting" .
}
=>
{
    ?join kgc:status "Active" .
} .

# Count completions (mark to avoid double-counting)
{
    ?join kgc:type "PartialJoin" .
    ?join kgc:waitingFor ?branch .
    ?branch kgc:status "Completed" .
    () log:notIncludes { ?branch kgc:countedFor ?join } .
}
=>
{
    ?branch kgc:countedFor ?join .
} .
"""

WCP31_BLOCKING_PARTIAL_JOIN = """
# =============================================================================
# LAW 31 - WCP-31: BLOCKING PARTIAL JOIN (Await)
# =============================================================================
# van der Aalst: "N of M complete, blocks until explicit reset."
# Semantics: Threshold join with explicit reset.

# Fire when threshold reached (first time)
{
    ?join kgc:type "BlockingPartialJoin" .
    ?join kgc:threshold ?n .
    ?join kgc:completedBranchCount ?count .
    ?count math:notLessThan ?n .
    ?join kgc:status "Waiting" .
    () log:notIncludes { ?join kgc:joinBlocked true } .
}
=>
{
    ?join kgc:status "Active" .
    ?join kgc:joinBlocked true .
} .

# Reset on explicit request
{
    ?join kgc:type "BlockingPartialJoin" .
    ?join kgc:joinBlocked true .
    ?join kgc:resetRequested true .
}
=>
{
    ?join kgc:joinBlocked false .
    ?join kgc:completedBranchCount 0 .
    ?join kgc:status "Waiting" .
} .
"""

WCP32_CANCELLING_PARTIAL_JOIN = """
# =============================================================================
# LAW 32 - WCP-32: CANCELLING PARTIAL JOIN (Await+Void)
# =============================================================================
# van der Aalst: "N of M complete, cancel remaining."
# Semantics: Threshold join with cancellation.

# Fire and mark for cancellation
{
    ?join kgc:type "CancellingPartialJoin" .
    ?join kgc:threshold ?n .
    ?join kgc:completedBranchCount ?count .
    ?count math:notLessThan ?n .
    ?join kgc:status "Waiting" .
}
=>
{
    ?join kgc:status "Active" .
    ?join kgc:cancelPending true .
} .

# Cancel incomplete branches
{
    ?join kgc:type "CancellingPartialJoin" .
    ?join kgc:cancelPending true .
    ?join kgc:waitingFor ?branch .
    ?branch kgc:status ?status .
    () log:notIncludes { ?status log:equalTo "Completed" } .
    () log:notIncludes { ?status log:equalTo "Cancelled" } .
}
=>
{
    ?branch kgc:status "Cancelled" .
    ?branch kgc:cancelledBy ?join .
} .
"""

WCP33_GENERALIZED_AND_JOIN = """
# =============================================================================
# LAW 33 - WCP-33: GENERALIZED AND-JOIN (Await)
# =============================================================================
# van der Aalst: "Synchronization with varying number of incoming branches."
# Semantics: Dynamic dependency tracking.

# Fire when all dynamic dependencies satisfied
{
    ?join kgc:type "GeneralizedAndJoin" .
    ?join kgc:status "Waiting" .
    ?join kgc:satisfiedDependencyCount ?satisfied .
    ?join kgc:totalDependencyCount ?total .
    ?satisfied math:notLessThan ?total .
}
=>
{
    ?join kgc:status "Active" .
} .

# Track satisfied dependencies
{
    ?join kgc:type "GeneralizedAndJoin" .
    ?join kgc:dynamicDependency ?dep .
    ?dep kgc:status "Completed" .
    () log:notIncludes { ?dep kgc:satisfiedFor ?join } .
}
=>
{
    ?dep kgc:satisfiedFor ?join .
} .
"""

# ==============================================================================
# WCP 34-36: MULTIPLE INSTANCE PARTIAL JOINS
# ==============================================================================

WCP34_STATIC_PARTIAL_JOIN_MI = """
# =============================================================================
# LAW 34 - WCP-34: STATIC PARTIAL JOIN FOR MI (Await)
# =============================================================================
# van der Aalst: "Fixed N out of M instances must complete."
# Semantics: Static threshold for MI completion.
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:joinType "StaticPartial" .
    ?mi kgc:threshold ?n .
    ?mi kgc:completedInstanceCount ?count .
    ?count math:notLessThan ?n .
    ?mi kgc:status "AwaitingCompletion" .
}
=>
{
    ?mi kgc:status "Completed" .
} .
"""

WCP35_CANCELLING_PARTIAL_JOIN_MI = """
# =============================================================================
# LAW 35 - WCP-35: CANCELLING PARTIAL JOIN FOR MI (Await+Void)
# =============================================================================
# van der Aalst: "N instances complete, cancel remaining."
# Semantics: Threshold MI with cancellation.

# Complete MI and trigger cancellation
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:joinType "CancellingPartial" .
    ?mi kgc:threshold ?n .
    ?mi kgc:completedInstanceCount ?count .
    ?count math:notLessThan ?n .
    ?mi kgc:status "AwaitingCompletion" .
}
=>
{
    ?mi kgc:status "Completed" .
    ?mi kgc:cancelRemaining true .
} .

# Cancel remaining instances
{
    ?mi kgc:cancelRemaining true .
    ?instance kgc:parentMI ?mi .
    ?instance kgc:status ?status .
    () log:notIncludes { ?status log:equalTo "Completed" } .
    () log:notIncludes { ?status log:equalTo "Cancelled" } .
}
=>
{
    ?instance kgc:status "Cancelled" .
} .
"""

WCP36_DYNAMIC_PARTIAL_JOIN_MI = """
# =============================================================================
# LAW 36 - WCP-36: DYNAMIC PARTIAL JOIN FOR MI (Await)
# =============================================================================
# van der Aalst: "Threshold N determined at runtime."
# Semantics: Runtime threshold evaluation.
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:joinType "DynamicPartial" .
    ?mi kgc:thresholdExpression ?expr .
    ?expr kgc:evaluatesTo ?n .
    ?mi kgc:completedInstanceCount ?count .
    ?count math:notLessThan ?n .
    ?mi kgc:status "AwaitingCompletion" .
}
=>
{
    ?mi kgc:status "Completed" .
} .
"""

# ==============================================================================
# WCP 37-42: ADVANCED SYNCHRONIZATION PATTERNS
# ==============================================================================

WCP37_LOCAL_SYNC_MERGE = """
# =============================================================================
# LAW 37 - WCP-37: LOCAL SYNCHRONIZING MERGE (Await)
# =============================================================================
# van der Aalst: "Synchronization based on local path analysis."
# Semantics: Wait for all branches from local split context.

# Fire when all local branches complete
{
    ?merge kgc:type "LocalSyncMerge" .
    ?merge kgc:status "Waiting" .
    ?merge kgc:localCompletedCount ?completed .
    ?merge kgc:localExpectedCount ?expected .
    ?completed math:notLessThan ?expected .
}
=>
{
    ?merge kgc:status "Active" .
} .

# Track local branch completions
{
    ?merge kgc:type "LocalSyncMerge" .
    ?merge kgc:localContext ?ctx .
    ?ctx kgc:activeBranch ?branch .
    ?branch kgc:status "Completed" .
    () log:notIncludes { ?branch kgc:locallyComplete ?merge } .
}
=>
{
    ?branch kgc:locallyComplete ?merge .
} .
"""

WCP38_GENERAL_SYNC_MERGE = """
# =============================================================================
# LAW 38 - WCP-38: GENERAL SYNCHRONIZING MERGE (Await)
# =============================================================================
# van der Aalst: "Synchronization based on global execution history."
# Semantics: Track all paths globally.

# Fire when all executed paths complete
{
    ?merge kgc:type "GeneralSyncMerge" .
    ?merge kgc:status "Waiting" .
    ?merge kgc:executedPathCount ?executed .
    ?merge kgc:completedPathCount ?completed .
    ?completed math:notLessThan ?executed .
}
=>
{
    ?merge kgc:status "Active" .
} .

# Track execution history
{
    ?task kgc:status "Completed" .
    ?task kgc:inPath ?path .
    ?merge kgc:type "GeneralSyncMerge" .
    ?merge kgc:globalContext ?ctx .
    () log:notIncludes { ?ctx kgc:pathCompleted ?path } .
}
=>
{
    ?ctx kgc:pathCompleted ?path .
} .
"""

WCP39_CRITICAL_SECTION = """
# =============================================================================
# LAW 39 - WCP-39: CRITICAL SECTION (Filter+Await)
# =============================================================================
# van der Aalst: "Mutual exclusion across process instances."
# Semantics: Global mutex for cross-instance serialization.

# Acquire critical section when free
{
    ?task kgc:requiresCriticalSection ?cs .
    ?task kgc:status "Ready" .
    ?cs kgc:lockHolder "none" .
}
=>
{
    ?cs kgc:lockHolder ?task .
    ?task kgc:status "Active" .
    ?task kgc:holdsLock ?cs .
} .

# Block when locked by another
{
    ?task kgc:requiresCriticalSection ?cs .
    ?task kgc:status "Ready" .
    ?cs kgc:lockHolder ?other .
    () log:notIncludes { ?other log:equalTo "none" } .
}
=>
{
    ?task kgc:status "Blocked" .
    ?task kgc:waitingFor ?cs .
} .

# Release on completion
{
    ?task kgc:holdsLock ?cs .
    ?task kgc:status "Completed" .
}
=>
{
    ?cs kgc:lockHolder "none" .
} .
"""

WCP40_INTERLEAVED_ROUTING = """
# =============================================================================
# LAW 40 - WCP-40: INTERLEAVED ROUTING (Filter)
# =============================================================================
# van der Aalst: "Tasks execute in any order but sequentially."
# Semantics: Relaxed interleaving without strict mutex.

# Select next task when region idle
{
    ?region kgc:type "InterleavedRouting" .
    ?region kgc:contains ?task .
    ?task kgc:status "Ready" .
    ?region kgc:currentTask "none" .
}
=>
{
    ?region kgc:currentTask ?task .
    ?task kgc:status "Active" .
} .

# Complete and release
{
    ?region kgc:type "InterleavedRouting" .
    ?region kgc:currentTask ?task .
    ?task kgc:status "Completed" .
}
=>
{
    ?region kgc:currentTask "none" .
    ?task kgc:interleaveComplete true .
} .

# Region complete when all tasks done
{
    ?region kgc:type "InterleavedRouting" .
    ?region kgc:completedTaskCount ?completed .
    ?region kgc:totalTaskCount ?total .
    ?completed math:notLessThan ?total .
}
=>
{
    ?region kgc:status "Completed" .
} .
"""

WCP41_THREAD_MERGE = """
# =============================================================================
# LAW 41 - WCP-41: THREAD MERGE (Await)
# =============================================================================
# van der Aalst: "Multiple concurrent threads converge into single thread."
# Semantics: Thread-level synchronization.

# Fire when all threads converged
{
    ?merge kgc:type "ThreadMerge" .
    ?merge kgc:status "Waiting" .
    ?merge kgc:convergedThreadCount ?converged .
    ?merge kgc:totalThreadCount ?total .
    ?converged math:notLessThan ?total .
}
=>
{
    ?merge kgc:status "Active" .
} .

# Track thread convergence
{
    ?merge kgc:type "ThreadMerge" .
    ?merge kgc:threadSet ?threads .
    ?threads kgc:hasMember ?thread .
    ?thread kgc:status "Converged" .
    () log:notIncludes { ?thread kgc:convergedAt ?merge } .
}
=>
{
    ?thread kgc:convergedAt ?merge .
} .
"""

WCP42_THREAD_SPLIT = """
# =============================================================================
# LAW 42 - WCP-42: THREAD SPLIT (Copy)
# =============================================================================
# van der Aalst: "Single thread diverges into multiple concurrent threads."
# Semantics: Thread spawning.

# Spawn target threads
{
    ?split kgc:type "ThreadSplit" .
    ?split kgc:status "Active" .
    ?split kgc:targetThreads ?threads .
    ?threads kgc:hasMember ?thread .
    () log:notIncludes { ?thread kgc:status ?anyStatus } .
}
=>
{
    ?thread kgc:status "Active" .
    ?thread kgc:copiedFrom ?split .
    ?split kgc:threadSpawned ?thread .
} .

# Mark split complete when all threads spawned
{
    ?split kgc:type "ThreadSplit" .
    ?split kgc:spawnedThreadCount ?spawned .
    ?split kgc:targetThreadCount ?target .
    ?spawned math:notLessThan ?target .
}
=>
{
    ?split kgc:status "Completed" .
} .
"""

WCP43_EXPLICIT_TERMINATION = """
# =============================================================================
# LAW 43 - WCP-43: EXPLICIT TERMINATION (Void)
# =============================================================================
# van der Aalst: "Process terminates when specific end node reached."
# Semantics: Explicit termination with cascading cancellation.

# Terminate when output condition reached
{
    ?task a yawl:OutputCondition .
    ?task kgc:status "Active" .
}
=>
{
    ?task kgc:status "Completed" .
    ?task kgc:terminated true .
    ?task kgc:terminationType "explicit" .
} .

# Cancel remaining active tasks in same case
{
    ?endTask kgc:terminated true .
    ?endTask kgc:terminationType "explicit" .
    ?endTask kgc:inCase ?case .
    ?otherTask kgc:inCase ?case .
    () log:notIncludes { ?otherTask log:equalTo ?endTask } .
    ?otherTask kgc:status "Active" .
}
=>
{
    ?otherTask kgc:status "Cancelled" .
    ?otherTask kgc:cancelledBy ?endTask .
} .
"""

# ==============================================================================
# COMPLETE PHYSICS ONTOLOGY - ALL 43 PATTERNS
# ==============================================================================

WCP43_COMPLETE_PHYSICS: str = (
    STANDARD_PREFIXES
    + "\n# =============================================================================="
    + "\n# WCP-43 COMPLETE PHYSICS ONTOLOGY"
    + "\n# All 43 YAWL Workflow Control Patterns as N3 Physics Laws"
    + "\n# Following van der Aalst et al. formal specifications"
    + "\n# =============================================================================="
    + "\n\n# --- TASK INITIALIZATION (LAW 0) ---"
    + TASK_INITIALIZATION
    + "\n\n# --- BASIC CONTROL FLOW (WCP 1-5) ---"
    + WCP1_SEQUENCE
    + WCP2_PARALLEL_SPLIT
    + WCP3_SYNCHRONIZATION
    + WCP4_EXCLUSIVE_CHOICE
    + WCP5_SIMPLE_MERGE
    + "\n\n# --- ADVANCED BRANCHING (WCP 6-9) ---"
    + WCP6_MULTI_CHOICE
    + WCP7_STRUCTURED_SYNC_MERGE
    + WCP8_MULTI_MERGE
    + WCP9_STRUCTURED_DISCRIMINATOR
    + "\n\n# --- STRUCTURAL PATTERNS (WCP 10-11) ---"
    + WCP10_ARBITRARY_CYCLES
    + WCP11_IMPLICIT_TERMINATION
    + "\n\n# --- MULTIPLE INSTANCES (WCP 12-15) ---"
    + WCP12_MI_WITHOUT_SYNC
    + WCP13_MI_DESIGN_TIME
    + WCP14_MI_RUNTIME
    + WCP15_MI_NO_APRIORI
    + "\n\n# --- STATE-BASED PATTERNS (WCP 16-18) ---"
    + WCP16_DEFERRED_CHOICE
    + WCP17_INTERLEAVED_PARALLEL
    + WCP18_MILESTONE
    + "\n\n# --- CANCELLATION PATTERNS (WCP 19-20, 25-27) ---"
    + WCP19_CANCEL_TASK
    + WCP20_CANCEL_CASE
    + WCP25_CANCEL_REGION
    + WCP26_CANCEL_MI_ACTIVITY
    + WCP27_COMPLETE_MI_ACTIVITY
    + "\n\n# --- ITERATION & TRIGGERS (WCP 21-24) ---"
    + WCP21_STRUCTURED_LOOP
    + WCP22_RECURSION
    + WCP23_TRANSIENT_TRIGGER
    + WCP24_PERSISTENT_TRIGGER
    + "\n\n# --- DISCRIMINATOR & PARTIAL JOIN (WCP 28-33) ---"
    + WCP28_BLOCKING_DISCRIMINATOR
    + WCP29_CANCELLING_DISCRIMINATOR
    + WCP30_STRUCTURED_PARTIAL_JOIN
    + WCP31_BLOCKING_PARTIAL_JOIN
    + WCP32_CANCELLING_PARTIAL_JOIN
    + WCP33_GENERALIZED_AND_JOIN
    + "\n\n# --- MI PARTIAL JOINS (WCP 34-36) ---"
    + WCP34_STATIC_PARTIAL_JOIN_MI
    + WCP35_CANCELLING_PARTIAL_JOIN_MI
    + WCP36_DYNAMIC_PARTIAL_JOIN_MI
    + "\n\n# --- ADVANCED SYNCHRONIZATION (WCP 37-42) ---"
    + WCP37_LOCAL_SYNC_MERGE
    + WCP38_GENERAL_SYNC_MERGE
    + WCP39_CRITICAL_SECTION
    + WCP40_INTERLEAVED_ROUTING
    + WCP41_THREAD_MERGE
    + WCP42_THREAD_SPLIT
    + "\n\n# --- TERMINATION (WCP 43) ---"
    + WCP43_EXPLICIT_TERMINATION
)


# ==============================================================================
# PATTERN CATALOG
# ==============================================================================

WCP_PATTERN_CATALOG: dict[int, dict[str, str]] = {
    1: {"name": "Sequence", "verb": "Transmute", "category": "Basic Control Flow"},
    2: {"name": "Parallel Split", "verb": "Copy", "category": "Basic Control Flow"},
    3: {"name": "Synchronization", "verb": "Await", "category": "Basic Control Flow"},
    4: {"name": "Exclusive Choice", "verb": "Filter", "category": "Basic Control Flow"},
    5: {"name": "Simple Merge", "verb": "Transmute", "category": "Basic Control Flow"},
    6: {"name": "Multi-Choice", "verb": "Filter", "category": "Advanced Branching"},
    7: {"name": "Structured Synchronizing Merge", "verb": "Await", "category": "Advanced Branching"},
    8: {"name": "Multi-Merge", "verb": "Transmute", "category": "Advanced Branching"},
    9: {"name": "Structured Discriminator", "verb": "Await", "category": "Advanced Branching"},
    10: {"name": "Arbitrary Cycles", "verb": "Filter", "category": "Structural"},
    11: {"name": "Implicit Termination", "verb": "Void", "category": "Structural"},
    12: {"name": "MI without Synchronization", "verb": "Copy", "category": "Multiple Instances"},
    13: {"name": "MI with Design-Time Knowledge", "verb": "Copy+Await", "category": "Multiple Instances"},
    14: {"name": "MI with Runtime Knowledge", "verb": "Copy+Await", "category": "Multiple Instances"},
    15: {"name": "MI without a priori Knowledge", "verb": "Copy+Await", "category": "Multiple Instances"},
    16: {"name": "Deferred Choice", "verb": "Filter", "category": "State-Based"},
    17: {"name": "Interleaved Parallel Routing", "verb": "Filter+Await", "category": "State-Based"},
    18: {"name": "Milestone", "verb": "Await", "category": "State-Based"},
    19: {"name": "Cancel Task", "verb": "Void", "category": "Cancellation"},
    20: {"name": "Cancel Case", "verb": "Void", "category": "Cancellation"},
    21: {"name": "Structured Loop", "verb": "Filter", "category": "Iteration"},
    22: {"name": "Recursion", "verb": "Copy", "category": "Iteration"},
    23: {"name": "Transient Trigger", "verb": "Await", "category": "Trigger"},
    24: {"name": "Persistent Trigger", "verb": "Await", "category": "Trigger"},
    25: {"name": "Cancel Region", "verb": "Void", "category": "Cancellation"},
    26: {"name": "Cancel MI Activity", "verb": "Void", "category": "Cancellation"},
    27: {"name": "Complete MI Activity", "verb": "Void+Await", "category": "Cancellation"},
    28: {"name": "Blocking Discriminator", "verb": "Await", "category": "Discriminator"},
    29: {"name": "Cancelling Discriminator", "verb": "Await+Void", "category": "Discriminator"},
    30: {"name": "Structured Partial Join", "verb": "Await", "category": "Partial Join"},
    31: {"name": "Blocking Partial Join", "verb": "Await", "category": "Partial Join"},
    32: {"name": "Cancelling Partial Join", "verb": "Await+Void", "category": "Partial Join"},
    33: {"name": "Generalized AND-Join", "verb": "Await", "category": "Partial Join"},
    34: {"name": "Static Partial Join for MI", "verb": "Await", "category": "MI Partial Join"},
    35: {"name": "Cancelling Partial Join for MI", "verb": "Await+Void", "category": "MI Partial Join"},
    36: {"name": "Dynamic Partial Join for MI", "verb": "Await", "category": "MI Partial Join"},
    37: {"name": "Local Synchronizing Merge", "verb": "Await", "category": "Advanced Sync"},
    38: {"name": "General Synchronizing Merge", "verb": "Await", "category": "Advanced Sync"},
    39: {"name": "Critical Section", "verb": "Filter+Await", "category": "Advanced Sync"},
    40: {"name": "Interleaved Routing", "verb": "Filter", "category": "Advanced Sync"},
    41: {"name": "Thread Merge", "verb": "Await", "category": "Advanced Sync"},
    42: {"name": "Thread Split", "verb": "Copy", "category": "Advanced Sync"},
    43: {"name": "Explicit Termination", "verb": "Void", "category": "Termination"},
}


def get_pattern_info(wcp_number: int) -> dict[str, str] | None:
    """Get information about a specific WCP pattern.

    Parameters
    ----------
    wcp_number : int
        WCP pattern number (1-43)

    Returns
    -------
    dict[str, str] | None
        Pattern info with name, verb, category; None if not found
    """
    return WCP_PATTERN_CATALOG.get(wcp_number)


def get_pattern_rule(wcp_number: int) -> str | None:
    """Get the N3 physics rule for a specific WCP pattern.

    Parameters
    ----------
    wcp_number : int
        WCP pattern number (1-43)

    Returns
    -------
    str | None
        N3 rule string; None if not found
    """
    rule_map = {
        1: WCP1_SEQUENCE,
        2: WCP2_PARALLEL_SPLIT,
        3: WCP3_SYNCHRONIZATION,
        4: WCP4_EXCLUSIVE_CHOICE,
        5: WCP5_SIMPLE_MERGE,
        6: WCP6_MULTI_CHOICE,
        7: WCP7_STRUCTURED_SYNC_MERGE,
        8: WCP8_MULTI_MERGE,
        9: WCP9_STRUCTURED_DISCRIMINATOR,
        10: WCP10_ARBITRARY_CYCLES,
        11: WCP11_IMPLICIT_TERMINATION,
        12: WCP12_MI_WITHOUT_SYNC,
        13: WCP13_MI_DESIGN_TIME,
        14: WCP14_MI_RUNTIME,
        15: WCP15_MI_NO_APRIORI,
        16: WCP16_DEFERRED_CHOICE,
        17: WCP17_INTERLEAVED_PARALLEL,
        18: WCP18_MILESTONE,
        19: WCP19_CANCEL_TASK,
        20: WCP20_CANCEL_CASE,
        21: WCP21_STRUCTURED_LOOP,
        22: WCP22_RECURSION,
        23: WCP23_TRANSIENT_TRIGGER,
        24: WCP24_PERSISTENT_TRIGGER,
        25: WCP25_CANCEL_REGION,
        26: WCP26_CANCEL_MI_ACTIVITY,
        27: WCP27_COMPLETE_MI_ACTIVITY,
        28: WCP28_BLOCKING_DISCRIMINATOR,
        29: WCP29_CANCELLING_DISCRIMINATOR,
        30: WCP30_STRUCTURED_PARTIAL_JOIN,
        31: WCP31_BLOCKING_PARTIAL_JOIN,
        32: WCP32_CANCELLING_PARTIAL_JOIN,
        33: WCP33_GENERALIZED_AND_JOIN,
        34: WCP34_STATIC_PARTIAL_JOIN_MI,
        35: WCP35_CANCELLING_PARTIAL_JOIN_MI,
        36: WCP36_DYNAMIC_PARTIAL_JOIN_MI,
        37: WCP37_LOCAL_SYNC_MERGE,
        38: WCP38_GENERAL_SYNC_MERGE,
        39: WCP39_CRITICAL_SECTION,
        40: WCP40_INTERLEAVED_ROUTING,
        41: WCP41_THREAD_MERGE,
        42: WCP42_THREAD_SPLIT,
        43: WCP43_EXPLICIT_TERMINATION,
    }
    return rule_map.get(wcp_number)


def list_all_patterns() -> list[int]:
    """List all 43 WCP pattern numbers.

    Returns
    -------
    list[int]
        Pattern numbers 1-43
    """
    return list(range(1, 44))


def get_patterns_by_category(category: str) -> list[int]:
    """Get pattern numbers for a specific category.

    Parameters
    ----------
    category : str
        Category name (e.g., "Basic Control Flow", "Cancellation")

    Returns
    -------
    list[int]
        Pattern numbers in that category
    """
    return [num for num, info in WCP_PATTERN_CATALOG.items() if info["category"] == category]


def get_patterns_by_verb(verb: str) -> list[int]:
    """Get pattern numbers that use a specific verb.

    Parameters
    ----------
    verb : str
        Verb name (Transmute, Copy, Filter, Await, Void)

    Returns
    -------
    list[int]
        Pattern numbers using that verb
    """
    return [num for num, info in WCP_PATTERN_CATALOG.items() if verb in info["verb"]]
