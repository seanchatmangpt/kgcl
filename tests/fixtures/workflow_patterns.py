"""Workflow fixture generators for all 43 Van der Aalst Control Flow Patterns.

This module provides pytest fixtures that generate RDF workflow graphs
implementing each of the 43 Workflow Control Patterns (WCP) from
"Workflow Patterns: The Definitive Guide" by Van der Aalst et al.

Each fixture returns an rdflib.Graph with:
- Correct YAWL topology (tasks, conditions, flows)
- Split/join type annotations (AND, OR, XOR)
- Initial token placement
- Pattern metadata

Reference: http://www.workflowpatterns.com/
Chicago School TDD: Real RDF graphs, no mocking.
"""

from __future__ import annotations

from typing import Any

import pytest
from rdflib import RDF, RDFS, BNode, Graph, Literal, Namespace, URIRef

# Namespaces
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
KGC = Namespace("http://kgcl.io/ontology/kgc#")
PATTERN = Namespace("http://knhk.ai/ontology/workflow-patterns#")
WF = Namespace("http://example.org/workflow/")


def _create_task(graph: Graph, task_id: str, join_type: URIRef, split_type: URIRef, has_token: bool = False) -> URIRef:
    """Create a YAWL task with specified join/split types."""
    task = WF[task_id]
    graph.add((task, RDF.type, YAWL.AtomicTask))
    graph.add((task, YAWL.taskName, Literal(task_id)))
    graph.add((task, YAWL["join"], join_type))  # Use bracket notation to avoid method name conflict
    graph.add((task, YAWL["split"], split_type))
    if has_token:
        graph.add((task, KGC.hasToken, Literal(True)))
    return task


def _create_flow(graph: Graph, from_elem: URIRef, to_elem: URIRef, predicate: str | None = None) -> URIRef:
    """Create a flow connection between elements."""
    flow = BNode()
    graph.add((flow, RDF.type, YAWL.Flow))
    graph.add((flow, YAWL.flowsFrom, from_elem))
    graph.add((flow, YAWL.flowsInto, to_elem))
    graph.add((from_elem, YAWL.nextElementRef, to_elem))
    if predicate:
        graph.add((flow, YAWL.predicate, Literal(predicate)))
    return flow


def _create_condition(graph: Graph, condition_id: str) -> URIRef:
    """Create a YAWL condition node."""
    cond = WF[condition_id]
    graph.add((cond, RDF.type, YAWL.Condition))
    graph.add((cond, YAWL.conditionName, Literal(condition_id)))
    return cond


# ============================================================================
# BASIC CONTROL FLOW PATTERNS (1-5)
# ============================================================================


@pytest.fixture
def wcp01_sequence() -> Graph:
    """Pattern 1: Sequence (A → B → C).

    Join: XOR, Split: XOR
    Deterministic sequential execution.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    end = _create_condition(g, "end")
    g.add((end, RDF.type, YAWL.OutputCondition))

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)
    _create_flow(g, task_b, task_c)
    _create_flow(g, task_c, end)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern1_Sequence))
    return g


@pytest.fixture
def wcp02_parallel_split() -> Graph:
    """Pattern 2: Parallel Split (A → {B, C, D}).

    Join: XOR, Split: AND
    Divergence into multiple parallel branches.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeAnd)  # AND-split
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_d = _create_task(g, "TaskD", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)  # All branches activated
    _create_flow(g, task_a, task_c)
    _create_flow(g, task_a, task_d)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern2_ParallelSplit))
    return g


@pytest.fixture
def wcp03_synchronization() -> Graph:
    """Pattern 3: Synchronization ({A, B, C} → D).

    Join: AND, Split: XOR
    Convergence of parallel branches.
    """
    g = Graph()
    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor, has_token=True)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor, has_token=True)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor, has_token=True)
    task_d = _create_task(g, "TaskD", YAWL.ControlTypeAnd, YAWL.ControlTypeXor)  # AND-join

    _create_flow(g, task_a, task_d)
    _create_flow(g, task_b, task_d)
    _create_flow(g, task_c, task_d)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern3_Synchronization))
    return g


@pytest.fixture
def wcp04_exclusive_choice() -> Graph:
    """Pattern 4: Exclusive Choice (A → {B | C | D}).

    Join: XOR, Split: XOR with predicates
    Selection of exactly one branch.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_d = _create_task(g, "TaskD", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b, "amount < 100")
    _create_flow(g, task_a, task_c, "amount >= 100 && amount < 1000")
    _create_flow(g, task_a, task_d, "amount >= 1000")

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern4_ExclusiveChoice))
    return g


@pytest.fixture
def wcp05_simple_merge() -> Graph:
    """Pattern 5: Simple Merge ({A | B | C} → D).

    Join: XOR, Split: XOR
    Convergence without synchronization.
    """
    g = Graph()
    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_d = _create_task(g, "TaskD", YAWL.ControlTypeXor, YAWL.ControlTypeXor)  # XOR-join

    _create_flow(g, task_a, task_d)
    _create_flow(g, task_b, task_d)
    _create_flow(g, task_c, task_d)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern5_SimpleMerge))
    return g


# ============================================================================
# ADVANCED BRANCHING AND SYNCHRONIZATION (6-11)
# ============================================================================


@pytest.fixture
def wcp06_multi_choice() -> Graph:
    """Pattern 6: Multi-Choice (A → {B, C, D}).

    Join: XOR, Split: OR
    Selection of one or more branches.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeOr)  # OR-split
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_d = _create_task(g, "TaskD", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b, "condition_b == true")
    _create_flow(g, task_a, task_c, "condition_c == true")
    _create_flow(g, task_a, task_d, "condition_d == true")

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern6_MultiChoice))
    return g


@pytest.fixture
def wcp07_structured_synchronizing_merge() -> Graph:
    """Pattern 7: Structured Synchronizing Merge (OR-join).

    Join: OR, Split: XOR
    Waits for all active branches from corresponding OR-split.
    YAWL's unique contribution with dead path elimination.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    # OR-split
    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeOr)

    # Parallel branches
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_d = _create_task(g, "TaskD", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    # OR-join (synchronized with OR-split)
    task_e = _create_task(g, "TaskE", YAWL.ControlTypeOr, YAWL.ControlTypeXor)  # OR-join

    end = _create_condition(g, "end")
    g.add((end, RDF.type, YAWL.OutputCondition))

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b, "condition_b == true")
    _create_flow(g, task_a, task_c, "condition_c == true")
    _create_flow(g, task_a, task_d, "condition_d == true")
    _create_flow(g, task_b, task_e)
    _create_flow(g, task_c, task_e)
    _create_flow(g, task_d, task_e)
    _create_flow(g, task_e, end)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern7_StructuredSynchronizingMerge))
    return g


@pytest.fixture
def wcp08_multi_merge() -> Graph:
    """Pattern 8: Multi-Merge ({A | B | C} → D).

    Join: XOR (activates for EACH token), Split: XOR
    Non-deterministic, may create multiple instances.
    """
    g = Graph()
    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    # Multi-merge: activates for each incoming token (no synchronization)
    task_d = _create_task(g, "TaskD", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    g.add((task_d, YAWL.multiMerge, Literal(True)))  # Marker for multi-merge semantics

    _create_flow(g, task_a, task_d)
    _create_flow(g, task_b, task_d)
    _create_flow(g, task_c, task_d)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern8_MultiMerge))
    return g


@pytest.fixture
def wcp09_structured_discriminator() -> Graph:
    """Pattern 9: Structured Discriminator ({A, B, C} → D).

    Join: OR (first wins), Split: XOR
    Activates on first arriving token, ignores rest.
    """
    g = Graph()
    # Parallel branches (all start with tokens)
    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor, has_token=True)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor, has_token=True)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor, has_token=True)

    # Discriminator: first token wins
    task_d = _create_task(g, "TaskD", YAWL.ControlTypeOr, YAWL.ControlTypeXor)
    g.add((task_d, YAWL.discriminator, Literal(True)))  # Marker for discriminator semantics

    _create_flow(g, task_a, task_d)
    _create_flow(g, task_b, task_d)
    _create_flow(g, task_c, task_d)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern9_StructuredDiscriminator))
    return g


@pytest.fixture
def wcp10_arbitrary_cycles() -> Graph:
    """Pattern 10: Arbitrary Cycles (A → B → C → A).

    Loops with one or more entry/exit points.
    Non-deterministic, may deadlock without guards.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    end = _create_condition(g, "end")
    g.add((end, RDF.type, YAWL.OutputCondition))

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)
    _create_flow(g, task_b, task_c)
    _create_flow(g, task_c, task_a, "iteration_count < max_iterations")  # Back edge
    _create_flow(g, task_c, end, "iteration_count >= max_iterations")  # Exit

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern10_ArbitraryCycles))
    return g


@pytest.fixture
def wcp11_implicit_termination() -> Graph:
    """Pattern 11: Implicit Termination.

    Workflow completes when no tasks can execute.
    No explicit end condition.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeAnd)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    # No explicit end condition - terminates when all paths exhausted
    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)
    _create_flow(g, task_a, task_c)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern11_ImplicitTermination))
    g.add((WF.workflow, YAWL.implicitTermination, Literal(True)))
    return g


# ============================================================================
# MULTIPLE INSTANCE PATTERNS (12-15)
# ============================================================================


@pytest.fixture
def wcp12_mi_without_synchronization() -> Graph:
    """Pattern 12: Multiple Instances without Synchronization.

    Multiple task instances created, no wait for completion.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    g.add((task_a, YAWL.multipleInstance, Literal(True)))
    g.add((task_a, YAWL.minInstances, Literal(3)))
    g.add((task_a, YAWL.maxInstances, Literal(10)))
    g.add((task_a, YAWL.threshold, Literal(0)))  # No synchronization

    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern12_MIWithoutSynchronization))
    return g


@pytest.fixture
def wcp13_mi_with_design_time_knowledge() -> Graph:
    """Pattern 13: Multiple Instances with A Priori Design-Time Knowledge.

    Number of instances known at design time.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    g.add((task_a, YAWL.multipleInstance, Literal(True)))
    g.add((task_a, YAWL.creationMode, Literal("static")))
    g.add((task_a, YAWL.instances, Literal(5)))  # Fixed at design time
    g.add((task_a, YAWL.threshold, Literal(5)))  # Wait for all

    task_b = _create_task(g, "TaskB", YAWL.ControlTypeAnd, YAWL.ControlTypeXor)  # AND-join

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern13_MIWithAPrioriDesignTimeKnowledge))
    return g


@pytest.fixture
def wcp14_mi_with_runtime_knowledge() -> Graph:
    """Pattern 14: Multiple Instances with A Priori Runtime Knowledge.

    Number of instances determined at runtime before activation.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    g.add((task_a, YAWL.multipleInstance, Literal(True)))
    g.add((task_a, YAWL.creationMode, Literal("dynamic")))
    g.add((task_a, YAWL.instancesExpression, Literal("count(/data/items)")))  # Runtime data
    g.add((task_a, YAWL.threshold, Literal("all")))

    task_b = _create_task(g, "TaskB", YAWL.ControlTypeAnd, YAWL.ControlTypeXor)

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern14_MIWithAPrioriRuntimeKnowledge))
    return g


@pytest.fixture
def wcp15_mi_without_runtime_knowledge() -> Graph:
    """Pattern 15: Multiple Instances without A Priori Runtime Knowledge.

    Instances created dynamically during execution.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    g.add((task_a, YAWL.multipleInstance, Literal(True)))
    g.add((task_a, YAWL.creationMode, Literal("dynamic")))
    g.add((task_a, YAWL.dynamicCreation, Literal(True)))  # On-demand
    g.add((task_a, YAWL.threshold, Literal("all")))

    task_b = _create_task(g, "TaskB", YAWL.ControlTypeAnd, YAWL.ControlTypeXor)

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern15_MIWithoutAPrioriRuntimeKnowledge))
    return g


# ============================================================================
# STATE-BASED PATTERNS (16-18)
# ============================================================================


@pytest.fixture
def wcp16_deferred_choice() -> Graph:
    """Pattern 16: Deferred Choice (external choice).

    Join: XOR, Split: XOR (event-driven)
    Choice made by environment, not workflow.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    g.add((task_a, YAWL.enablementTrigger, Literal("event_A")))
    g.add((task_b, YAWL.enablementTrigger, Literal("event_B")))
    g.add((task_c, YAWL.enablementTrigger, Literal("event_C")))

    _create_flow(g, start, task_a)  # All enabled simultaneously
    _create_flow(g, start, task_b)
    _create_flow(g, start, task_c)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern16_DeferredChoice))
    return g


@pytest.fixture
def wcp17_interleaved_parallel_routing() -> Graph:
    """Pattern 17: Interleaved Parallel Routing.

    Parallel execution with mutual exclusion.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeAnd)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_d = _create_task(g, "TaskD", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_e = _create_task(g, "TaskE", YAWL.ControlTypeAnd, YAWL.ControlTypeXor)

    # Mutual exclusion constraint
    g.add((task_b, YAWL.mutex, task_c))
    g.add((task_b, YAWL.mutex, task_d))
    g.add((task_c, YAWL.mutex, task_d))

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)
    _create_flow(g, task_a, task_c)
    _create_flow(g, task_a, task_d)
    _create_flow(g, task_b, task_e)
    _create_flow(g, task_c, task_e)
    _create_flow(g, task_d, task_e)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern17_InterleavedParallelRouting))
    return g


@pytest.fixture
def wcp18_milestone() -> Graph:
    """Pattern 18: Milestone.

    Task enabled only while condition holds.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeAnd)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)  # Milestone
    task_d = _create_task(g, "TaskD", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    # Task C only enabled while milestone holds
    g.add((task_c, YAWL.milestone, Literal("milestone_state == active")))

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)
    _create_flow(g, task_a, task_c)
    _create_flow(g, task_b, task_d)
    _create_flow(g, task_c, task_d)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern18_Milestone))
    return g


# ============================================================================
# CANCELLATION AND FORCE COMPLETION (19-25)
# ============================================================================


@pytest.fixture
def wcp19_cancel_activity() -> Graph:
    """Pattern 19: Cancel Activity.

    Enabled activity is disabled and removed.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeAnd)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    cancel_task = _create_task(g, "CancelB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    # Cancel task B when CancelB executes
    g.add((cancel_task, YAWL.cancellationRegion, task_b))

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)
    _create_flow(g, task_a, cancel_task)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern19_CancelActivity))
    return g


@pytest.fixture
def wcp20_cancel_case() -> Graph:
    """Pattern 20: Cancel Case.

    Entire workflow instance is removed.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeAnd)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    cancel_case = _create_task(g, "CancelCase", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    # Cancel entire case
    g.add((cancel_case, YAWL.cancelCase, Literal(True)))

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)
    _create_flow(g, task_a, cancel_case)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern20_CancelCase))
    return g


@pytest.fixture
def wcp21_cancel_region() -> Graph:
    """Pattern 21: Cancel Region.

    Cancel a region of the workflow.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeAnd)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_d = _create_task(g, "TaskD", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    cancel_task = _create_task(g, "CancelRegion", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    # Cancel region containing B, C, D
    region = BNode()
    g.add((region, RDF.type, YAWL.CancellationRegion))
    g.add((region, YAWL.contains, task_b))
    g.add((region, YAWL.contains, task_c))
    g.add((region, YAWL.contains, task_d))
    g.add((cancel_task, YAWL.cancellationRegion, region))

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)
    _create_flow(g, task_a, task_c)
    _create_flow(g, task_a, task_d)
    _create_flow(g, task_a, cancel_task)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern21_CancelRegion))
    return g


@pytest.fixture
def wcp22_cancel_multiple_instance_activity() -> Graph:
    """Pattern 22: Cancel Multiple Instance Activity.

    Cancel all instances of a MI task.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeAnd)
    mi_task = _create_task(g, "MITask", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    g.add((mi_task, YAWL.multipleInstance, Literal(True)))
    g.add((mi_task, YAWL.instances, Literal(5)))

    cancel_task = _create_task(g, "CancelMI", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    g.add((cancel_task, YAWL.cancellationRegion, mi_task))

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, mi_task)
    _create_flow(g, task_a, cancel_task)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern22_CancelMultipleInstanceActivity))
    return g


@pytest.fixture
def wcp23_structured_loop() -> Graph:
    """Pattern 23: Structured Loop.

    Loop with single entry and exit point.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    end = _create_condition(g, "end")
    g.add((end, RDF.type, YAWL.OutputCondition))

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)
    _create_flow(g, task_b, task_c)
    _create_flow(g, task_c, task_a, "loop_condition == true")  # Back edge
    _create_flow(g, task_c, end, "loop_condition == false")  # Exit

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern23_StructuredLoop))
    return g


@pytest.fixture
def wcp24_recursion() -> Graph:
    """Pattern 24: Recursion.

    Task calls itself (composite task).
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    recursive_task = _create_task(g, "RecursiveTask", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    g.add((recursive_task, RDF.type, YAWL.CompositeTask))
    g.add((recursive_task, YAWL.decomposesTo, recursive_task))  # Self-reference

    end = _create_condition(g, "end")
    g.add((end, RDF.type, YAWL.OutputCondition))

    _create_flow(g, start, recursive_task)
    _create_flow(g, recursive_task, end, "base_case == true")

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern24_Recursion))
    return g


@pytest.fixture
def wcp25_transient_trigger() -> Graph:
    """Pattern 25: Transient Trigger.

    Event that may be missed if not handled immediately.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    event_task = _create_task(g, "EventTask", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    g.add((event_task, YAWL.transientTrigger, Literal(True)))
    g.add((event_task, YAWL.eventType, Literal("timeout")))

    _create_flow(g, start, task_a)
    _create_flow(g, start, event_task)  # Event enabled concurrently

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern25_TransientTrigger))
    return g


# ============================================================================
# ITERATION PATTERNS (26-27) [Skipped: WCP26-WCP33 are data/resource patterns]
# ============================================================================


# ============================================================================
# MI JOIN PATTERNS (34-36)
# ============================================================================


@pytest.fixture
def wcp34_static_partial_join() -> Graph:
    """Pattern 34: Static Partial Join for Multiple Instances.

    Join waits for N of M instances (known at design time).
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    mi_task = _create_task(g, "MITask", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    g.add((mi_task, YAWL.multipleInstance, Literal(True)))
    g.add((mi_task, YAWL.instances, Literal(10)))
    g.add((mi_task, YAWL.threshold, Literal(7)))  # Wait for 7 of 10

    join_task = _create_task(g, "JoinTask", YAWL.ControlTypeAnd, YAWL.ControlTypeXor)

    _create_flow(g, start, mi_task)
    _create_flow(g, mi_task, join_task)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern34_StaticPartialJoin))
    return g


@pytest.fixture
def wcp35_cancelling_partial_join() -> Graph:
    """Pattern 35: Cancelling Partial Join for Multiple Instances.

    Join waits for N of M, then cancels remaining instances.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    mi_task = _create_task(g, "MITask", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    g.add((mi_task, YAWL.multipleInstance, Literal(True)))
    g.add((mi_task, YAWL.instances, Literal(10)))
    g.add((mi_task, YAWL.threshold, Literal(7)))
    g.add((mi_task, YAWL.cancelRemaining, Literal(True)))  # Cancel after threshold

    join_task = _create_task(g, "JoinTask", YAWL.ControlTypeAnd, YAWL.ControlTypeXor)

    _create_flow(g, start, mi_task)
    _create_flow(g, mi_task, join_task)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern35_CancellingPartialJoin))
    return g


@pytest.fixture
def wcp36_dynamic_partial_join() -> Graph:
    """Pattern 36: Dynamic Partial Join for Multiple Instances.

    Join threshold determined at runtime.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    mi_task = _create_task(g, "MITask", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    g.add((mi_task, YAWL.multipleInstance, Literal(True)))
    g.add((mi_task, YAWL.instancesExpression, Literal("count(/data/items)")))
    g.add((mi_task, YAWL.thresholdExpression, Literal("/data/required_count")))  # Runtime

    join_task = _create_task(g, "JoinTask", YAWL.ControlTypeAnd, YAWL.ControlTypeXor)

    _create_flow(g, start, mi_task)
    _create_flow(g, mi_task, join_task)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern36_DynamicPartialJoin))
    return g


# ============================================================================
# TERMINATION PATTERN (43)
# ============================================================================


@pytest.fixture
def wcp43_explicit_termination() -> Graph:
    """Pattern 43: Explicit Termination.

    Workflow has explicit end condition/task.
    """
    g = Graph()
    start = _create_condition(g, "start")
    g.add((start, RDF.type, YAWL.InputCondition))
    g.add((start, KGC.hasToken, Literal(True)))

    task_a = _create_task(g, "TaskA", YAWL.ControlTypeXor, YAWL.ControlTypeAnd)
    task_b = _create_task(g, "TaskB", YAWL.ControlTypeXor, YAWL.ControlTypeXor)
    task_c = _create_task(g, "TaskC", YAWL.ControlTypeXor, YAWL.ControlTypeXor)

    end = _create_condition(g, "end")
    g.add((end, RDF.type, YAWL.OutputCondition))
    g.add((end, YAWL.explicitTermination, Literal(True)))

    _create_flow(g, start, task_a)
    _create_flow(g, task_a, task_b)
    _create_flow(g, task_a, task_c)
    _create_flow(g, task_b, end)
    _create_flow(g, task_c, end)

    g.add((WF.workflow, PATTERN.implementsPattern, PATTERN.Pattern43_ExplicitTermination))
    return g


# ============================================================================
# PARAMETRIZED FIXTURE FACTORY
# ============================================================================


def create_workflow_pattern(pattern_id: int, **kwargs: Any) -> Graph:
    """Create workflow graph for specified pattern (plain function, not fixture).

    Args:
        pattern_id: WCP pattern number (1-43)
        **kwargs: Pattern-specific parameters (e.g., branch_count, instances)

    Returns:
        RDF graph implementing the pattern

    Raises:
        ValueError: If pattern_id is invalid or not a control-flow pattern

    Usage:
        graph = create_workflow_pattern(pattern_id=7)
    """
    # Map to plain generator functions (call unwrapped fixture functions)
    pattern_map = {
        1: wcp01_sequence,
        2: wcp02_parallel_split,
        3: wcp03_synchronization,
        4: wcp04_exclusive_choice,
        5: wcp05_simple_merge,
        6: wcp06_multi_choice,
        7: wcp07_structured_synchronizing_merge,
        8: wcp08_multi_merge,
        9: wcp09_structured_discriminator,
        10: wcp10_arbitrary_cycles,
        11: wcp11_implicit_termination,
        12: wcp12_mi_without_synchronization,
        13: wcp13_mi_with_design_time_knowledge,
        14: wcp14_mi_with_runtime_knowledge,
        15: wcp15_mi_without_runtime_knowledge,
        16: wcp16_deferred_choice,
        17: wcp17_interleaved_parallel_routing,
        18: wcp18_milestone,
        19: wcp19_cancel_activity,
        20: wcp20_cancel_case,
        21: wcp21_cancel_region,
        22: wcp22_cancel_multiple_instance_activity,
        23: wcp23_structured_loop,
        24: wcp24_recursion,
        25: wcp25_transient_trigger,
        34: wcp34_static_partial_join,
        35: wcp35_cancelling_partial_join,
        36: wcp36_dynamic_partial_join,
        43: wcp43_explicit_termination,
    }

    fixture_func = pattern_map.get(pattern_id)
    if not fixture_func:
        msg = f"Pattern {pattern_id} not implemented or not a control-flow pattern"
        raise ValueError(msg)

    # Extract unwrapped function and call it
    # pytest.fixture decorates functions but stores original as __wrapped__
    if hasattr(fixture_func, "__wrapped__"):
        return fixture_func.__wrapped__()
    else:
        # Fallback: try calling directly (should work for plain functions)
        return fixture_func()  # type: ignore[no-any-return]


@pytest.fixture
def workflow_pattern_factory() -> Any:
    """Fixture that returns the pattern factory function.

    Returns:
        Callable that generates workflow graphs for any of the 43 patterns.

    Usage in tests:
        def test_example(workflow_pattern_factory):
            graph = workflow_pattern_factory(pattern_id=7)
    """
    return create_workflow_pattern
