"""WCP-43 Complete Physics Ontology - All 43 Workflow Control Patterns.

This module implements ALL 43 YAWL Workflow Control Patterns as N3 physics laws.
Each pattern is implemented using the 5 KGC verbs: Transmute, Copy, Filter, Await, Void.

The patterns are organized into 8 categories:
1. Basic Control Flow (WCP 1-5)
2. Advanced Branching (WCP 6-9)
3. Structural (WCP 10-11)
4. Multiple Instances (WCP 12-15)
5. State-Based (WCP 16-18)
6. Cancellation (WCP 19-20, 25-27)
7. Iteration & Triggers (WCP 21-24)
8. Advanced Joins & Sync (WCP 28-43)

Architecture
------------
- All patterns use tick-boundary state transitions (monotonic within tick)
- Non-monotonic operations (cancellation) use status markers not retraction
- State machines track complex patterns (discriminators, partial joins)
- Counter patterns handle M-of-N semantics

References
----------
- YAWL Workflow Patterns: http://www.workflowpatterns.com
- Russell et al. (2006) "Workflow Control-Flow Patterns: A Revised View"
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
"""

# ==============================================================================
# WCP 1-5: BASIC CONTROL FLOW PATTERNS
# ==============================================================================

WCP1_SEQUENCE = """
# =============================================================================
# WCP-1: SEQUENCE (Transmute)
# =============================================================================
# A task is enabled after completion of preceding task in same process.
{
    ?task kgc:status "Completed" .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?next kgc:status "Pending" .
}
=>
{
    ?next kgc:status "Active" .
} .
"""

WCP2_PARALLEL_SPLIT = """
# =============================================================================
# WCP-2: PARALLEL SPLIT / AND-SPLIT (Copy)
# =============================================================================
# Single thread splits into multiple parallel threads.
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeAnd .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?next kgc:status "Pending" .
}
=>
{
    ?next kgc:status "Active" .
} .
"""

WCP3_SYNCHRONIZATION = """
# =============================================================================
# WCP-3: SYNCHRONIZATION / AND-JOIN (Await)
# =============================================================================
# Multiple parallel threads converge, waiting for ALL to complete.
{
    ?task yawl:hasJoin yawl:ControlTypeAnd .
    ?task kgc:status "Pending" .
    ?task kgc:allPredecessorsComplete true .
}
=>
{
    ?task kgc:status "Active" .
} .

# Helper: Check if all predecessors complete
{
    ?task yawl:hasJoin yawl:ControlTypeAnd .
    ?incoming yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?task .
    ?incoming kgc:status "Completed" .
}
=>
{
    ?task kgc:predecessorComplete ?incoming .
} .
"""

WCP4_EXCLUSIVE_CHOICE = """
# =============================================================================
# WCP-4: EXCLUSIVE CHOICE / XOR-SPLIT (Filter)
# =============================================================================
# Based on decision, ONE of several branches is chosen.
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

# Default path when no predicate matches
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeXor .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?flow yawl:isDefault true .
    ?next kgc:status "Pending" .
}
=>
{
    ?next kgc:status "Active" .
} .
"""

WCP5_SIMPLE_MERGE = """
# =============================================================================
# WCP-5: SIMPLE MERGE / XOR-JOIN (Transmute)
# =============================================================================
# Alternative branches come together without synchronization.
# Each incoming branch independently triggers the merge.
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
# WCP-6: MULTI-CHOICE / OR-SPLIT (Filter)
# =============================================================================
# Based on decision, one or MORE branches are chosen.
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
} .

# Mark task as split-complete after evaluation
{
    ?task kgc:status "Completed" .
    ?task yawl:hasSplit yawl:ControlTypeOr .
}
=>
{
    ?task kgc:splitEvaluated true .
} .
"""

WCP7_STRUCTURED_SYNC_MERGE = """
# =============================================================================
# WCP-7: STRUCTURED SYNCHRONIZING MERGE / OR-JOIN (Await)
# =============================================================================
# Convergence of branches from earlier OR-split, waiting for all ACTIVE branches.
{
    ?task yawl:hasJoin yawl:ControlTypeOr .
    ?task kgc:status "Pending" .
    ?task kgc:correspondingSplit ?split .
    ?split kgc:splitEvaluated true .
    ?task kgc:allActiveBranchesComplete true .
}
=>
{
    ?task kgc:status "Active" .
} .

# Track which branches were activated
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

# Check if expected branch is complete
{
    ?merge kgc:expectsBranch ?branch .
    ?branch kgc:status "Completed" .
}
=>
{
    ?merge kgc:branchComplete ?branch .
} .
"""

WCP8_MULTI_MERGE = """
# =============================================================================
# WCP-8: MULTI-MERGE (Transmute)
# =============================================================================
# Branches reconverge without synchronization. Each branch independently
# triggers the subsequent task (may fire multiple times).
{
    ?task yawl:hasJoin yawl:ControlTypeMultiMerge .
    ?incoming yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?task .
    ?incoming kgc:status "Completed" .
    ?incoming kgc:mergeProcessed false .
}
=>
{
    ?task kgc:status "Active" .
    ?task kgc:activationCount ?newCount .
    ?incoming kgc:mergeProcessed true .
} .
"""

WCP9_STRUCTURED_DISCRIMINATOR = """
# =============================================================================
# WCP-9: STRUCTURED DISCRIMINATOR (Await)
# =============================================================================
# First incoming branch to complete enables subsequent task.
# Later completions are ignored until all complete and reset.
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
} .

# Consume later completions without firing
{
    ?disc yawl:hasJoin yawl:ControlTypeDiscriminator .
    ?disc kgc:discriminatorState "fired" .
    ?incoming yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?disc .
    ?incoming kgc:status "Completed" .
}
=>
{
    ?incoming kgc:discriminatorConsumed true .
} .

# Reset when all branches consumed
{
    ?disc yawl:hasJoin yawl:ControlTypeDiscriminator .
    ?disc kgc:discriminatorState "fired" .
    ?disc kgc:allBranchesConsumed true .
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
# WCP-10: ARBITRARY CYCLES (Filter)
# =============================================================================
# One or more tasks can be executed repeatedly (unstructured loops).
{
    ?task kgc:status "Completed" .
    ?task yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
    ?flow yawl:isBackEdge true .
    ?flow yawl:loopCondition ?cond .
    ?cond kgc:evaluatesTo true .
}
=>
{
    ?next kgc:status "Active" .
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
}
=>
{
    ?exit kgc:status "Active" .
} .
"""

WCP11_IMPLICIT_TERMINATION = """
# =============================================================================
# WCP-11: IMPLICIT TERMINATION (Void)
# =============================================================================
# Process terminates when no more tasks to execute (deadlock-free completion).
{
    ?task kgc:status "Completed" .
    ?task yawl:flowsInto ?none .
    FILTER NOT EXISTS { ?task yawl:flowsInto ?any }
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
# WCP-12: MULTIPLE INSTANCES WITHOUT SYNCHRONIZATION (Copy)
# =============================================================================
# Multiple instances created, each independent, no waiting for siblings.
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:synchronization "none" .
    ?mi kgc:status "Active" .
    ?mi kgc:instanceCount ?n .
}
=>
{
    ?mi kgc:createInstances ?n .
    ?mi kgc:status "Spawning" .
} .

# Each instance completes independently
{
    ?instance kgc:parentMI ?mi .
    ?mi kgc:synchronization "none" .
    ?instance kgc:status "Completed" .
    ?mi yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?next .
}
=>
{
    ?next kgc:status "Active" .
} .
"""

WCP13_MI_DESIGN_TIME = """
# =============================================================================
# WCP-13: MI WITH A PRIORI DESIGN-TIME KNOWLEDGE (Copy+Await)
# =============================================================================
# Fixed number of instances known at design time, synchronize on completion.
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:synchronization "all" .
    ?mi kgc:instanceCountType "designTime" .
    ?mi kgc:status "Active" .
    ?mi kgc:instanceCount ?n .
}
=>
{
    ?mi kgc:createInstances ?n .
    ?mi kgc:remainingInstances ?n .
    ?mi kgc:status "AwaitingCompletion" .
} .

# Decrement on instance completion
{
    ?instance kgc:parentMI ?mi .
    ?mi kgc:synchronization "all" .
    ?instance kgc:status "Completed" .
    ?mi kgc:remainingInstances ?remaining .
    ?remaining > 0 .
}
=>
{
    ?mi kgc:remainingInstances ?newRemaining .
    ?instance kgc:counted true .
} .

# Fire when all complete
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:synchronization "all" .
    ?mi kgc:remainingInstances 0 .
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
# WCP-14: MI WITH A PRIORI RUNTIME KNOWLEDGE (Copy+Await)
# =============================================================================
# Instance count determined at runtime start, synchronize on completion.
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:synchronization "all" .
    ?mi kgc:instanceCountType "runtime" .
    ?mi kgc:status "Active" .
    ?mi kgc:instanceCountExpression ?expr .
    ?expr kgc:evaluatesTo ?n .
}
=>
{
    ?mi kgc:createInstances ?n .
    ?mi kgc:remainingInstances ?n .
    ?mi kgc:status "AwaitingCompletion" .
} .
"""

WCP15_MI_NO_APRIORI = """
# =============================================================================
# WCP-15: MI WITHOUT A PRIORI RUNTIME KNOWLEDGE (Copy+Await)
# =============================================================================
# Instance count not known a priori, can add dynamically during execution.
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:synchronization "all" .
    ?mi kgc:instanceCountType "dynamic" .
    ?mi kgc:status "Active" .
}
=>
{
    ?mi kgc:status "Spawning" .
    ?mi kgc:activeInstances 0 .
    ?mi kgc:completedInstances 0 .
} .

# Accept spawn request
{
    ?mi kgc:status "Spawning" .
    ?mi kgc:spawnRequest ?req .
    ?req kgc:action "create" .
}
=>
{
    ?mi kgc:createInstance ?newInstance .
    ?mi kgc:activeInstances ?newActive .
} .

# Close spawning phase
{
    ?mi kgc:status "Spawning" .
    ?mi kgc:spawnRequest ?req .
    ?req kgc:action "close" .
}
=>
{
    ?mi kgc:status "AwaitingCompletion" .
} .

# Complete when all active instances done
{
    ?mi kgc:status "AwaitingCompletion" .
    ?mi kgc:activeInstances 0 .
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
# WCP-16: DEFERRED CHOICE (Filter)
# =============================================================================
# Choice determined by environment (first enabled path wins).
{
    ?choice kgc:type "DeferredChoice" .
    ?choice kgc:status "Waiting" .
    ?choice yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?branch .
    ?branch kgc:externallyEnabled true .
}
=>
{
    ?choice kgc:status "Resolved" .
    ?branch kgc:status "Active" .
    ?choice kgc:selectedBranch ?branch .
} .

# Disable other branches
{
    ?choice kgc:type "DeferredChoice" .
    ?choice kgc:status "Resolved" .
    ?choice kgc:selectedBranch ?winner .
    ?choice yawl:flowsInto ?flow .
    ?flow yawl:nextElementRef ?loser .
    ?loser != ?winner .
}
=>
{
    ?loser kgc:status "Disabled" .
} .
"""

WCP17_INTERLEAVED_PARALLEL = """
# =============================================================================
# WCP-17: INTERLEAVED PARALLEL ROUTING (Filter+Await)
# =============================================================================
# Tasks execute in any order but not simultaneously (mutual exclusion).
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

# Block if mutex held
{
    ?region kgc:type "InterleavedParallel" .
    ?region kgc:contains ?task .
    ?task kgc:status "Ready" .
    ?region kgc:mutex ?mutex .
    ?mutex kgc:holder ?other .
    ?other != "none" .
}
=>
{
    ?task kgc:status "Blocked" .
    ?task kgc:waitingFor ?mutex .
} .
"""

WCP18_MILESTONE = """
# =============================================================================
# WCP-18: MILESTONE (Await)
# =============================================================================
# Task enabled only when process in specific state (milestone achieved).
{
    ?task kgc:status "Ready" .
    ?task kgc:requiresMilestone ?milestone .
    ?milestone kgc:status "Achieved" .
}
=>
{
    ?task kgc:status "Active" .
} .

# Block if milestone not achieved
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

# Withdraw if milestone lost while executing
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
# WCP-19: CANCEL TASK (Void)
# =============================================================================
# Individual task is cancelled (withdrawn from execution).
{
    ?task kgc:cancelRequested true .
    ?task kgc:status ?oldStatus .
    FILTER(?oldStatus != "Completed" && ?oldStatus != "Cancelled")
}
=>
{
    ?task kgc:status "Cancelled" .
    ?task kgc:previousStatus ?oldStatus .
    ?task kgc:cancelledAt ?now .
} .
"""

WCP20_CANCEL_CASE = """
# =============================================================================
# WCP-20: CANCEL CASE (Void)
# =============================================================================
# Entire process instance is cancelled.
{
    ?case kgc:cancelRequested true .
    ?case kgc:hasTask ?task .
    ?task kgc:status ?status .
    FILTER(?status != "Completed" && ?status != "Cancelled")
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
# WCP-25: CANCEL REGION (Void)
# =============================================================================
# Specific region (subset) of process is cancelled.
{
    ?region kgc:cancelRequested true .
    ?region kgc:contains ?task .
    ?task kgc:status ?status .
    FILTER(?status != "Completed" && ?status != "Cancelled")
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
# WCP-26: CANCEL MULTIPLE INSTANCE ACTIVITY (Void)
# =============================================================================
# All instances of a multiple instance task are cancelled.
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:cancelRequested true .
    ?instance kgc:parentMI ?mi .
    ?instance kgc:status ?status .
    FILTER(?status != "Completed" && ?status != "Cancelled")
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
# WCP-27: COMPLETE MULTIPLE INSTANCE ACTIVITY (Void+Await)
# =============================================================================
# Force early completion of MI activity (remaining instances cancelled).
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

# Cancel remaining
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:forceCompleteRequested true .
    ?instance kgc:parentMI ?mi .
    ?instance kgc:status ?status .
    FILTER(?status != "Completed" && ?status != "Cancelled")
}
=>
{
    ?instance kgc:status "ForcedCancelled" .
} .

# Complete MI
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:forceCompleteRequested true .
    ?mi kgc:hasCompletedInstance ?inst .
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
# WCP 21-24: ITERATION AND TRIGGER PATTERNS
# ==============================================================================

WCP21_STRUCTURED_LOOP = """
# =============================================================================
# WCP-21: STRUCTURED LOOP (Filter)
# =============================================================================
# Task executed repeatedly using structured loop constructs.
{
    ?loop kgc:type "StructuredLoop" .
    ?loop kgc:status "Evaluating" .
    ?loop kgc:loopCondition ?cond .
    ?cond kgc:evaluatesTo true .
    ?loop kgc:iterationCount ?count .
    ?loop kgc:maxIterations ?max .
    ?count < ?max .
}
=>
{
    ?loop kgc:status "Iterating" .
    ?loop kgc:iterationCount ?newCount .
    ?loop kgc:body kgc:status "Active" .
} .

# Exit loop
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
# WCP-22: RECURSION (Copy)
# =============================================================================
# Task can invoke itself recursively.
{
    ?task kgc:isRecursive true .
    ?task kgc:status "Active" .
    ?task kgc:recursionCondition ?cond .
    ?cond kgc:evaluatesTo true .
    ?task kgc:depth ?depth .
    ?task kgc:maxDepth ?maxDepth .
    ?depth < ?maxDepth .
}
=>
{
    ?newTask kgc:copyOf ?task .
    ?newTask kgc:status "Active" .
    ?newTask kgc:depth ?newDepth .
    ?newTask kgc:parent ?task .
    ?task kgc:status "AwaitingRecursion" .
} .

# Base case - no recursion
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

# Unwind recursion
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
# WCP-23: TRANSIENT TRIGGER (Await)
# =============================================================================
# Signal from environment - lost if task not ready.
{
    ?trigger kgc:type "Transient" .
    ?trigger kgc:firedAt ?time .
    ?trigger kgc:targets ?task .
    ?task kgc:status "Ready" .
}
=>
{
    ?task kgc:status "Triggered" .
    ?task kgc:triggeredBy ?trigger .
    ?trigger kgc:status "Consumed" .
} .

# Lost if not ready
{
    ?trigger kgc:type "Transient" .
    ?trigger kgc:firedAt ?time .
    ?trigger kgc:targets ?task .
    ?task kgc:status ?status .
    FILTER(?status != "Ready")
}
=>
{
    ?trigger kgc:status "Lost" .
} .
"""

WCP24_PERSISTENT_TRIGGER = """
# =============================================================================
# WCP-24: PERSISTENT TRIGGER (Await)
# =============================================================================
# Signal from environment - queued until task ready.
{
    ?trigger kgc:type "Persistent" .
    ?trigger kgc:firedAt ?time .
    ?trigger kgc:targets ?task .
}
=>
{
    ?task kgc:hasPendingTrigger ?trigger .
    ?trigger kgc:status "Queued" .
} .

# Consume when ready
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
# WCP-28: BLOCKING DISCRIMINATOR (Await)
# =============================================================================
# First completion wins, blocks subsequent until all complete and reset.
{
    ?disc kgc:type "BlockingDiscriminator" .
    ?disc kgc:status "Waiting" .
    ?disc kgc:waitingFor ?branch .
    ?branch kgc:status "Completed" .
}
=>
{
    ?disc kgc:status "Fired" .
    ?disc kgc:winningBranch ?branch .
} .

# Block subsequent completions
{
    ?disc kgc:type "BlockingDiscriminator" .
    ?disc kgc:status "Fired" .
    ?disc kgc:waitingFor ?branch .
    ?branch kgc:status "Completed" .
    ?branch != ?disc kgc:winningBranch .
}
=>
{
    ?branch kgc:blocked true .
    ?branch kgc:blockedBy ?disc .
} .

# Reset when all complete
{
    ?disc kgc:type "BlockingDiscriminator" .
    ?disc kgc:status "Fired" .
    ?disc kgc:allBranchesComplete true .
}
=>
{
    ?disc kgc:status "Waiting" .
} .
"""

WCP29_CANCELLING_DISCRIMINATOR = """
# =============================================================================
# WCP-29: CANCELLING DISCRIMINATOR (Await+Void)
# =============================================================================
# First completion wins, remaining branches cancelled.
{
    ?disc kgc:type "CancellingDiscriminator" .
    ?disc kgc:status "Waiting" .
    ?disc kgc:waitingFor ?branch .
    ?branch kgc:status "Completed" .
}
=>
{
    ?disc kgc:status "Fired" .
    ?disc kgc:winningBranch ?branch .
} .

# Cancel losers
{
    ?disc kgc:type "CancellingDiscriminator" .
    ?disc kgc:status "Fired" .
    ?disc kgc:winningBranch ?winner .
    ?disc kgc:waitingFor ?loser .
    ?loser != ?winner .
    ?loser kgc:status ?status .
    FILTER(?status != "Completed" && ?status != "Cancelled")
}
=>
{
    ?loser kgc:status "Cancelled" .
    ?loser kgc:cancelledBy ?disc .
} .
"""

WCP30_STRUCTURED_PARTIAL_JOIN = """
# =============================================================================
# WCP-30: STRUCTURED PARTIAL JOIN (Await)
# =============================================================================
# N out of M branches must complete before firing.
{
    ?join kgc:type "PartialJoin" .
    ?join kgc:threshold ?n .
    ?join kgc:completionCount ?count .
    ?count >= ?n .
    ?join kgc:status "Waiting" .
}
=>
{
    ?join kgc:status "Active" .
} .

# Count completions
{
    ?join kgc:type "PartialJoin" .
    ?join kgc:waitingFor ?branch .
    ?branch kgc:status "Completed" .
    ?branch kgc:countedFor ?join .
}
=>
{
    ?join kgc:incrementCompletionCount true .
} .
"""

WCP31_BLOCKING_PARTIAL_JOIN = """
# =============================================================================
# WCP-31: BLOCKING PARTIAL JOIN (Await)
# =============================================================================
# N of M complete, blocks until reset.
{
    ?join kgc:type "BlockingPartialJoin" .
    ?join kgc:threshold ?n .
    ?join kgc:completionCount ?count .
    ?count >= ?n .
    ?join kgc:status "Waiting" .
    ?join kgc:blocked false .
}
=>
{
    ?join kgc:status "Active" .
    ?join kgc:blocked true .
} .

# Reset
{
    ?join kgc:type "BlockingPartialJoin" .
    ?join kgc:blocked true .
    ?join kgc:resetRequested true .
}
=>
{
    ?join kgc:blocked false .
    ?join kgc:completionCount 0 .
    ?join kgc:status "Waiting" .
} .
"""

WCP32_CANCELLING_PARTIAL_JOIN = """
# =============================================================================
# WCP-32: CANCELLING PARTIAL JOIN (Await+Void)
# =============================================================================
# N of M complete, cancel remaining.
{
    ?join kgc:type "CancellingPartialJoin" .
    ?join kgc:threshold ?n .
    ?join kgc:completionCount ?count .
    ?count >= ?n .
    ?join kgc:status "Waiting" .
}
=>
{
    ?join kgc:status "Active" .
    ?join kgc:cancelPending true .
} .

# Cancel pending branches
{
    ?join kgc:type "CancellingPartialJoin" .
    ?join kgc:cancelPending true .
    ?join kgc:waitingFor ?branch .
    ?branch kgc:status ?status .
    FILTER(?status != "Completed" && ?status != "Cancelled")
}
=>
{
    ?branch kgc:status "Cancelled" .
    ?branch kgc:cancelledBy ?join .
} .
"""

WCP33_GENERALIZED_AND_JOIN = """
# =============================================================================
# WCP-33: GENERALIZED AND-JOIN (Await)
# =============================================================================
# Synchronization with varying number of incoming branches per instance.
{
    ?join kgc:type "GeneralizedAndJoin" .
    ?join kgc:dynamicDependencies ?deps .
    ?deps kgc:allComplete true .
    ?join kgc:status "Waiting" .
}
=>
{
    ?join kgc:status "Active" .
} .

# Check dynamic dependencies
{
    ?join kgc:type "GeneralizedAndJoin" .
    ?join kgc:dynamicDependencies ?deps .
    ?deps kgc:hasMember ?dep .
    ?dep kgc:status "Completed" .
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
# WCP-34: STATIC PARTIAL JOIN FOR MI (Await)
# =============================================================================
# Fixed N out of M instances must complete.
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:joinType "StaticPartial" .
    ?mi kgc:threshold ?n .
    ?mi kgc:completedInstances ?count .
    ?count >= ?n .
    ?mi kgc:status "AwaitingCompletion" .
}
=>
{
    ?mi kgc:status "Completed" .
} .
"""

WCP35_CANCELLING_PARTIAL_JOIN_MI = """
# =============================================================================
# WCP-35: CANCELLING PARTIAL JOIN FOR MI (Await+Void)
# =============================================================================
# N instances complete, cancel remaining.
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:joinType "CancellingPartial" .
    ?mi kgc:threshold ?n .
    ?mi kgc:completedInstances ?count .
    ?count >= ?n .
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
    FILTER(?status != "Completed" && ?status != "Cancelled")
}
=>
{
    ?instance kgc:status "Cancelled" .
} .
"""

WCP36_DYNAMIC_PARTIAL_JOIN_MI = """
# =============================================================================
# WCP-36: DYNAMIC PARTIAL JOIN FOR MI (Await)
# =============================================================================
# N determined at runtime.
{
    ?mi kgc:type "MultiInstance" .
    ?mi kgc:joinType "DynamicPartial" .
    ?mi kgc:thresholdExpression ?expr .
    ?expr kgc:evaluatesTo ?n .
    ?mi kgc:completedInstances ?count .
    ?count >= ?n .
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
# WCP-37: LOCAL SYNCHRONIZING MERGE (Await)
# =============================================================================
# Synchronization based on local path analysis from preceding split.
{
    ?merge kgc:type "LocalSyncMerge" .
    ?merge kgc:localContext ?ctx .
    ?ctx kgc:activeBranches ?branches .
    ?branches kgc:allComplete true .
    ?merge kgc:status "Waiting" .
}
=>
{
    ?merge kgc:status "Active" .
} .

# Track local branches
{
    ?merge kgc:type "LocalSyncMerge" .
    ?merge kgc:localContext ?ctx .
    ?ctx kgc:activeBranches ?branches .
    ?branches kgc:hasMember ?branch .
    ?branch kgc:status "Completed" .
}
=>
{
    ?branch kgc:locallyComplete true .
} .
"""

WCP38_GENERAL_SYNC_MERGE = """
# =============================================================================
# WCP-38: GENERAL SYNCHRONIZING MERGE (Await)
# =============================================================================
# Synchronization based on global execution history analysis.
{
    ?merge kgc:type "GeneralSyncMerge" .
    ?merge kgc:globalContext ?ctx .
    ?ctx kgc:executionHistory ?history .
    ?history kgc:allPathsExecuted true .
    ?merge kgc:status "Waiting" .
}
=>
{
    ?merge kgc:status "Active" .
} .

# Track execution history
{
    ?task kgc:status "Completed" .
    ?task kgc:inPath ?path .
    ?merge kgc:globalContext ?ctx .
    ?ctx kgc:executionHistory ?history .
}
=>
{
    ?history kgc:pathExecuted ?path .
} .
"""

WCP39_CRITICAL_SECTION = """
# =============================================================================
# WCP-39: CRITICAL SECTION (Filter+Await)
# =============================================================================
# Mutual exclusion across process instances.
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

# Block if locked
{
    ?task kgc:requiresCriticalSection ?cs .
    ?task kgc:status "Ready" .
    ?cs kgc:lockHolder ?other .
    ?other != "none" .
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
# WCP-40: INTERLEAVED ROUTING (Filter)
# =============================================================================
# Tasks execute in any order but sequentially (relaxed WCP-17).
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
    ?region kgc:allTasksComplete true .
}
=>
{
    ?region kgc:status "Completed" .
} .
"""

WCP41_THREAD_MERGE = """
# =============================================================================
# WCP-41: THREAD MERGE (Await)
# =============================================================================
# Multiple concurrent threads converge into single thread.
{
    ?merge kgc:type "ThreadMerge" .
    ?merge kgc:threadSet ?threads .
    ?threads kgc:allConverged true .
    ?merge kgc:status "Waiting" .
}
=>
{
    ?merge kgc:status "Active" .
    ?merge kgc:mergedThread ?newThread .
} .

# Track thread convergence
{
    ?merge kgc:type "ThreadMerge" .
    ?merge kgc:threadSet ?threads .
    ?threads kgc:hasMember ?thread .
    ?thread kgc:status "Converged" .
}
=>
{
    ?thread kgc:convergedAt ?merge .
} .
"""

WCP42_THREAD_SPLIT = """
# =============================================================================
# WCP-42: THREAD SPLIT (Copy)
# =============================================================================
# Single thread diverges into multiple concurrent threads.
{
    ?split kgc:type "ThreadSplit" .
    ?split kgc:status "Active" .
    ?split kgc:targetThreads ?threads .
    ?threads kgc:hasMember ?thread .
}
=>
{
    ?thread kgc:status "Active" .
    ?thread kgc:copiedFrom ?split .
    ?split kgc:threadSpawned ?thread .
} .

# Mark split complete after spawning
{
    ?split kgc:type "ThreadSplit" .
    ?split kgc:allThreadsSpawned true .
}
=>
{
    ?split kgc:status "Completed" .
} .
"""

WCP43_EXPLICIT_TERMINATION = """
# =============================================================================
# WCP-43: EXPLICIT TERMINATION (Void)
# =============================================================================
# Process terminates when specific end node reached, cancelling remaining tasks.
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
    ?otherTask != ?endTask .
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
    + "\n# =============================================================================="
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
    return [
        num
        for num, info in WCP_PATTERN_CATALOG.items()
        if info["category"] == category
    ]


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
    return [
        num
        for num, info in WCP_PATTERN_CATALOG.items()
        if verb in info["verb"]
    ]
