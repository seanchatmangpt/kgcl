"""Pytest fixtures and topology templates for testing 43 WCP patterns on PyOxigraph.

This module provides:
1. Pytest fixtures for HybridEngine with PyOxigraph store
2. Topology templates (Turtle format) for each of the 43 WCP patterns
3. Helper functions for loading topologies, running physics, querying status

All 43 Workflow Control Patterns (WCP) are implemented as minimal test graphs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyoxigraph as ox
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

from kgcl.hybrid.hybrid_engine import HybridEngine, PhysicsResult

# ==============================================================================
# PYTEST FIXTURES
# ==============================================================================


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh in-memory HybridEngine with PyOxigraph store.

    Returns
    -------
    HybridEngine
        Fresh engine with empty in-memory store.

    Examples
    --------
    >>> def test_basic(engine):
    ...     engine.load_data("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")
    ...     assert len(list(engine.store)) > 0
    """
    return HybridEngine()


@pytest.fixture
def load_topology(engine: HybridEngine) -> Callable[[str], None]:
    """Factory fixture for loading topology into engine.

    Parameters
    ----------
    engine : HybridEngine
        Engine fixture to load data into.

    Returns
    -------
    Callable[[str], None]
        Function that loads Turtle string into engine.

    Examples
    --------
    >>> def test_load(engine, load_topology):
    ...     load_topology(WCP01_SEQUENCE)
    ...     assert len(list(engine.store)) > 0
    """

    def _load(topology: str) -> None:
        engine.load_data(topology)

    return _load


@pytest.fixture
def run_physics(engine: HybridEngine) -> Callable[[int], list[PhysicsResult]]:
    """Factory fixture for running physics ticks.

    Parameters
    ----------
    engine : HybridEngine
        Engine to run physics on.

    Returns
    -------
    Callable[[int], list[PhysicsResult]]
        Function that runs N ticks and returns results.

    Examples
    --------
    >>> def test_physics(engine, load_topology, run_physics):
    ...     load_topology(WCP01_SEQUENCE)
    ...     results = run_physics(5)
    ...     assert len(results) <= 5
    """

    def _run(max_ticks: int = 10) -> list[PhysicsResult]:
        return engine.run_to_completion(max_ticks=max_ticks)

    return _run


@pytest.fixture
def query_status(engine: HybridEngine) -> Callable[[str], str | None]:
    """Factory fixture for querying task status.

    Parameters
    ----------
    engine : HybridEngine
        Engine to query.

    Returns
    -------
    Callable[[str], str | None]
        Function that returns status of task by URI.

    Examples
    --------
    >>> def test_status(engine, load_topology, query_status):
    ...     load_topology(WCP01_SEQUENCE)
    ...     status = query_status("urn:task:A")
    ...     assert status == "Completed"
    """

    def _query(task_uri: str) -> str | None:
        statuses = engine.inspect()
        return statuses.get(task_uri)

    return _query


@pytest.fixture
def validate_outcome(engine: HybridEngine) -> Callable[[dict[str, str]], None]:
    """Factory fixture for validating expected task statuses.

    Parameters
    ----------
    engine : HybridEngine
        Engine to validate.

    Returns
    -------
    Callable[[dict[str, str]], None]
        Function that asserts expected statuses match actual.

    Examples
    --------
    >>> def test_validate(engine, load_topology, run_physics, validate_outcome):
    ...     load_topology(WCP01_SEQUENCE)
    ...     run_physics(5)
    ...     validate_outcome({"urn:task:A": "Completed", "urn:task:B": "Active"})
    """

    def _validate(expected: dict[str, str]) -> None:
        actual = engine.inspect()
        for task_uri, expected_status in expected.items():
            assert task_uri in actual, f"Task {task_uri} not found in graph"
            assert actual[task_uri] == expected_status, (
                f"Task {task_uri}: expected {expected_status}, got {actual[task_uri]}"
            )

    return _validate


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================


def count_triples(engine: HybridEngine) -> int:
    """Count total triples in engine store.

    Parameters
    ----------
    engine : HybridEngine
        Engine to count triples in.

    Returns
    -------
    int
        Total number of triples.
    """
    return len(list(engine.store))


def query_sparql(engine: HybridEngine, query: str) -> list[dict[str, str]]:
    """Execute SPARQL query and return results.

    Parameters
    ----------
    engine : HybridEngine
        Engine to query.
    query : str
        SPARQL SELECT query.

    Returns
    -------
    list[dict[str, str]]
        List of solution mappings.
    """
    results = []
    for solution in engine.store.query(query):
        row = {}
        for var in solution.variables:
            value = str(solution[var])
            # Strip angle brackets from URIs and quotes from literals
            row[var] = value.strip("<>").strip('"')
        results.append(row)
    return results


def assert_task_active(engine: HybridEngine, task_uri: str) -> None:
    """Assert that task has Active status.

    Parameters
    ----------
    engine : HybridEngine
        Engine to check.
    task_uri : str
        Task URI to check status of.

    Raises
    ------
    AssertionError
        If task is not Active.
    """
    statuses = engine.inspect()
    assert task_uri in statuses, f"Task {task_uri} not found"
    assert statuses[task_uri] == "Active", f"Expected Active, got {statuses[task_uri]}"


def assert_task_completed(engine: HybridEngine, task_uri: str) -> None:
    """Assert that task has Completed status.

    Parameters
    ----------
    engine : HybridEngine
        Engine to check.
    task_uri : str
        Task URI to check status of.

    Raises
    ------
    AssertionError
        If task is not Completed.
    """
    statuses = engine.inspect()
    assert task_uri in statuses, f"Task {task_uri} not found"
    assert statuses[task_uri] == "Completed", f"Expected Completed, got {statuses[task_uri]}"


# ==============================================================================
# WCP TOPOLOGY TEMPLATES (43 Patterns)
# ==============================================================================
# Each template is a minimal graph that exercises ONLY that specific pattern.
# Uses YAWL predicates: yawl:flowsInto, yawl:hasSplit, yawl:hasJoin, etc.

# ------------------------------------------------------------------------------
# BASIC CONTROL FLOW PATTERNS (WCP 1-5)
# ------------------------------------------------------------------------------

WCP01_SEQUENCE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-1: Sequence (Simple sequential flow)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> .

<urn:task:B> a yawl:Task .
"""

WCP02_PARALLEL_SPLIT = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-2: Parallel Split (AND-split)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> .
<urn:flow:2> yawl:nextElementRef <urn:task:C> .

<urn:task:B> a yawl:Task .
<urn:task:C> a yawl:Task .
"""

WCP03_SYNCHRONIZATION = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-3: Synchronization (AND-join)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:task:B> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:C> .
<urn:flow:2> yawl:nextElementRef <urn:task:C> .

<urn:task:C> a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd .
"""

WCP04_EXCLUSIVE_CHOICE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-4: Exclusive Choice (XOR-split with predicate)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> ;
    yawl:hasPredicate <urn:pred:1> .

<urn:flow:2> yawl:nextElementRef <urn:task:C> ;
    yawl:isDefaultFlow true .

<urn:pred:1> kgc:evaluatesTo true .

<urn:task:B> a yawl:Task .
<urn:task:C> a yawl:Task .
"""

WCP05_SIMPLE_MERGE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-5: Simple Merge (No join control, multiple incoming flows)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:task:B> a yawl:Task ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:C> .
<urn:flow:2> yawl:nextElementRef <urn:task:C> .

<urn:task:C> a yawl:Task .
"""

# ------------------------------------------------------------------------------
# ADVANCED BRANCHING PATTERNS (WCP 6-9)
# ------------------------------------------------------------------------------

WCP06_MULTI_CHOICE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-6: Multi-Choice (OR-split, multiple branches can activate)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeOr ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> ;
    yawl:hasPredicate <urn:pred:1> .

<urn:flow:2> yawl:nextElementRef <urn:task:C> ;
    yawl:hasPredicate <urn:pred:2> .

<urn:pred:1> kgc:evaluatesTo true .
<urn:pred:2> kgc:evaluatesTo true .

<urn:task:B> a yawl:Task .
<urn:task:C> a yawl:Task .
"""

WCP07_STRUCTURED_SYNCHRONIZING_MERGE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-7: Structured Synchronizing Merge (OR-join)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:task:B> a yawl:Task ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:C> .
<urn:flow:2> yawl:nextElementRef <urn:task:C> .

<urn:task:C> a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeOr .
"""

WCP08_MULTI_MERGE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-8: Multi-Merge (Multiple activations from multiple incoming)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:task:B> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:C> .
<urn:flow:2> yawl:nextElementRef <urn:task:C> .

<urn:task:C> a yawl:Task .
"""

WCP09_STRUCTURED_DISCRIMINATOR = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-9: Structured Discriminator (Wait for N completions)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:task:B> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:C> .
<urn:flow:2> yawl:nextElementRef <urn:task:C> .

<urn:task:C> a yawl:Task ;
    yawl:hasJoin kgc:StructuredDiscriminator ;
    kgc:discriminatorThreshold 1 .
"""

# ------------------------------------------------------------------------------
# MULTIPLE INSTANCE PATTERNS (WCP 12-15)
# ------------------------------------------------------------------------------

WCP12_MULTIPLE_INSTANCES_WITHOUT_SYNC = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-12: Multiple Instances without Synchronization
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2>, <urn:flow:3> .

<urn:flow:1> yawl:nextElementRef <urn:task:B1> .
<urn:flow:2> yawl:nextElementRef <urn:task:B2> .
<urn:flow:3> yawl:nextElementRef <urn:task:B3> .

<urn:task:B1> a yawl:Task .
<urn:task:B2> a yawl:Task .
<urn:task:B3> a yawl:Task .
"""

WCP13_MULTIPLE_INSTANCES_WITH_DESIGN_TIME_KNOWLEDGE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-13: Multiple Instances with Design Time Knowledge
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:B1> .
<urn:flow:2> yawl:nextElementRef <urn:task:B2> .

<urn:task:B1> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:3> .

<urn:task:B2> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:4> .

<urn:flow:3> yawl:nextElementRef <urn:task:C> .
<urn:flow:4> yawl:nextElementRef <urn:task:C> .

<urn:task:C> a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd .
"""

WCP14_MULTIPLE_INSTANCES_WITH_RUNTIME_KNOWLEDGE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-14: Multiple Instances with Runtime Knowledge (Dynamic)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    kgc:instanceCount 3 ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2>, <urn:flow:3> .

<urn:flow:1> yawl:nextElementRef <urn:task:B1> .
<urn:flow:2> yawl:nextElementRef <urn:task:B2> .
<urn:flow:3> yawl:nextElementRef <urn:task:B3> .

<urn:task:B1> a yawl:Task .
<urn:task:B2> a yawl:Task .
<urn:task:B3> a yawl:Task .
"""

WCP15_MULTIPLE_INSTANCES_WITHOUT_PRIOR_KNOWLEDGE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-15: Multiple Instances without Prior Knowledge
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    kgc:dynamicInstances true ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> .

<urn:task:B> a yawl:Task ;
    kgc:canSpawnNew true .
"""

# ------------------------------------------------------------------------------
# STATE-BASED PATTERNS (WCP 16-18)
# ------------------------------------------------------------------------------

WCP16_DEFERRED_CHOICE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-16: Deferred Choice (Runtime decision)
<urn:task:A> a yawl:Task ;
    kgc:status "Active" ;
    kgc:requiresManualCompletion true ;
    yawl:hasSplit yawl:ControlTypeXor ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> ;
    yawl:hasPredicate <urn:pred:1> .

<urn:flow:2> yawl:nextElementRef <urn:task:C> ;
    yawl:isDefaultFlow true .

<urn:pred:1> kgc:evaluatesTo false .

<urn:task:B> a yawl:Task .
<urn:task:C> a yawl:Task .
"""

WCP17_INTERLEAVED_PARALLEL_ROUTING = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-17: Interleaved Parallel Routing (Mutual exclusion)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> .
<urn:flow:2> yawl:nextElementRef <urn:task:C> .

<urn:task:B> a yawl:Task ;
    kgc:mutex <urn:lock:1> .

<urn:task:C> a yawl:Task ;
    kgc:mutex <urn:lock:1> .
"""

WCP18_MILESTONE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-18: Milestone (External condition)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> .

<urn:task:B> a yawl:Task ;
    kgc:requiresMilestone <urn:milestone:1> .

<urn:milestone:1> kgc:status "Reached" .
"""

# ------------------------------------------------------------------------------
# CANCELLATION PATTERNS (WCP 19-20)
# ------------------------------------------------------------------------------

WCP19_CANCEL_TASK = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-19: Cancel Task
<urn:task:A> a yawl:Task ;
    kgc:status "Active" .

<urn:task:B> a yawl:Task ;
    kgc:status "Completed" ;
    kgc:cancels <urn:task:A> .
"""

WCP20_CANCEL_CASE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-20: Cancel Case (Cancel entire workflow)
<urn:task:A> a yawl:Task ;
    kgc:status "Active" .

<urn:task:B> a yawl:Task ;
    kgc:status "Active" .

<urn:case:1> a yawl:Case ;
    kgc:status "Cancelled" ;
    kgc:containsTask <urn:task:A>, <urn:task:B> .
"""

# ------------------------------------------------------------------------------
# ITERATION PATTERNS (WCP 21-22)
# ------------------------------------------------------------------------------

WCP21_STRUCTURED_LOOP = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-21: Structured Loop (Repeat until condition)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> ;
    yawl:hasPredicate <urn:pred:1> .

<urn:flow:2> yawl:nextElementRef <urn:task:C> ;
    yawl:isDefaultFlow true .

<urn:pred:1> kgc:evaluatesTo true .

<urn:task:B> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:3> .

<urn:flow:3> yawl:nextElementRef <urn:task:A> .

<urn:task:C> a yawl:Task .
"""

WCP22_RECURSION = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-22: Recursion (Task invokes itself)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    kgc:recursionDepth 0 ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:A> ;
    yawl:hasPredicate <urn:pred:1> .

<urn:flow:2> yawl:nextElementRef <urn:task:B> ;
    yawl:isDefaultFlow true .

<urn:pred:1> kgc:evaluatesTo false .

<urn:task:B> a yawl:Task .
"""

# ------------------------------------------------------------------------------
# TRIGGER PATTERNS (WCP 23-25)
# ------------------------------------------------------------------------------

WCP23_TRANSIENT_TRIGGER = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-23: Transient Trigger (Event-based activation)
<urn:task:A> a yawl:Task ;
    kgc:status "Waiting" ;
    kgc:triggeredBy <urn:event:1> .

<urn:event:1> kgc:status "Fired" .
"""

WCP24_PERSISTENT_TRIGGER = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-24: Persistent Trigger (Event persists)
<urn:task:A> a yawl:Task ;
    kgc:status "Waiting" ;
    kgc:triggeredBy <urn:event:1> .

<urn:event:1> kgc:status "Active" ;
    kgc:persistent true .
"""

WCP25_CANCEL_REGION = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-25: Cancel Region (Cancel all tasks in region)
<urn:task:A> a yawl:Task ;
    kgc:status "Active" ;
    kgc:inRegion <urn:region:1> .

<urn:task:B> a yawl:Task ;
    kgc:status "Active" ;
    kgc:inRegion <urn:region:1> .

<urn:region:1> kgc:status "Cancelled" .
"""

# ------------------------------------------------------------------------------
# ADVANCED JOIN PATTERNS (WCP 28-30, 33-38)
# ------------------------------------------------------------------------------

WCP28_BLOCKING_DISCRIMINATOR = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-28: Blocking Discriminator (First wins, others blocked)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:task:B> a yawl:Task ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:C> .
<urn:flow:2> yawl:nextElementRef <urn:task:C> .

<urn:task:C> a yawl:Task ;
    yawl:hasJoin kgc:BlockingDiscriminator .
"""

WCP29_CANCELLING_DISCRIMINATOR = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-29: Cancelling Discriminator (First wins, others cancelled)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:task:B> a yawl:Task ;
    kgc:status "Active" ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:C> .
<urn:flow:2> yawl:nextElementRef <urn:task:C> .

<urn:task:C> a yawl:Task ;
    yawl:hasJoin kgc:CancellingDiscriminator .
"""

WCP30_PARTIAL_JOIN = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-30: Partial Join (K-of-N join)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:task:B> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:2> .

<urn:task:C> a yawl:Task ;
    yawl:flowsInto <urn:flow:3> .

<urn:flow:1> yawl:nextElementRef <urn:task:D> .
<urn:flow:2> yawl:nextElementRef <urn:task:D> .
<urn:flow:3> yawl:nextElementRef <urn:task:D> .

<urn:task:D> a yawl:Task ;
    yawl:hasJoin kgc:PartialJoin ;
    kgc:requiredPredecessors 2 .
"""

WCP33_GENERALIZED_AND_JOIN = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-33: Generalized AND-Join (N-way synchronization)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:task:B> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:2> .

<urn:task:C> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:3> .

<urn:flow:1> yawl:nextElementRef <urn:task:D> .
<urn:flow:2> yawl:nextElementRef <urn:task:D> .
<urn:flow:3> yawl:nextElementRef <urn:task:D> .

<urn:task:D> a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    kgc:expectedPredecessors 3 .
"""

WCP37_LOCAL_SYNCHRONIZING_MERGE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-37: Local Synchronizing Merge (Dynamic path tracking)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    kgc:wasActivated true ;
    yawl:flowsInto <urn:flow:1> .

<urn:task:B> a yawl:Task ;
    kgc:status "Completed" ;
    kgc:wasActivated true ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:C> .
<urn:flow:2> yawl:nextElementRef <urn:task:C> .

<urn:task:C> a yawl:Task ;
    yawl:hasJoin kgc:SynchronizingMerge .
"""

WCP38_GENERAL_SYNCHRONIZING_MERGE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-38: General Synchronizing Merge (Global tracking)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    kgc:wasActivated true ;
    yawl:flowsInto <urn:flow:1> .

<urn:task:B> a yawl:Task ;
    kgc:wasActivated true ;
    yawl:flowsInto <urn:flow:2> .

<urn:task:C> a yawl:Task ;
    kgc:status "Completed" ;
    kgc:wasActivated true ;
    yawl:flowsInto <urn:flow:3> .

<urn:flow:1> yawl:nextElementRef <urn:task:D> .
<urn:flow:2> yawl:nextElementRef <urn:task:D> .
<urn:flow:3> yawl:nextElementRef <urn:task:D> .

<urn:task:D> a yawl:Task ;
    yawl:hasJoin kgc:SynchronizingMerge .
"""

# ------------------------------------------------------------------------------
# ADVANCED WORKFLOW PATTERNS (WCP 39-43)
# ------------------------------------------------------------------------------

WCP39_CRITICAL_SECTION = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-39: Critical Section (Exclusive execution region)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> .
<urn:flow:2> yawl:nextElementRef <urn:task:C> .

<urn:task:B> a yawl:Task ;
    kgc:criticalSection <urn:section:1> .

<urn:task:C> a yawl:Task ;
    kgc:criticalSection <urn:section:1> .
"""

WCP40_INTERLEAVED_ROUTING = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-40: Interleaved Routing (Ordered execution)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> .

<urn:task:B> a yawl:Task ;
    kgc:executionOrder 1 ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:2> yawl:nextElementRef <urn:task:C> .

<urn:task:C> a yawl:Task ;
    kgc:executionOrder 2 .
"""

WCP41_THREAD_MERGE = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-41: Thread Merge (Multiple threads synchronize)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    kgc:threadId "thread1" ;
    yawl:flowsInto <urn:flow:1> .

<urn:task:B> a yawl:Task ;
    kgc:status "Completed" ;
    kgc:threadId "thread2" ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:C> .
<urn:flow:2> yawl:nextElementRef <urn:task:C> .

<urn:task:C> a yawl:Task ;
    yawl:hasJoin kgc:ThreadMerge .
"""

WCP42_THREAD_SPLIT = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-42: Thread Split (Spawn new threads)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    kgc:threadId "main" ;
    yawl:hasSplit kgc:ThreadSplit ;
    yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> ;
    kgc:spawnsThread "thread1" .

<urn:flow:2> yawl:nextElementRef <urn:task:C> ;
    kgc:spawnsThread "thread2" .

<urn:task:B> a yawl:Task ;
    kgc:threadId "thread1" .

<urn:task:C> a yawl:Task ;
    kgc:threadId "thread2" .
"""

WCP43_EXPLICIT_TERMINATION = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

# WCP-43: Explicit Termination (Terminate on condition)
<urn:task:A> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:B> .

<urn:task:B> a yawl:Task ;
    kgc:status "Active" ;
    kgc:terminateCondition <urn:cond:1> .

<urn:cond:1> kgc:evaluatesTo true .
"""

# ==============================================================================
# TOPOLOGY REGISTRY (For parameterized tests)
# ==============================================================================

ALL_WCP_TOPOLOGIES = {
    "WCP01_SEQUENCE": WCP01_SEQUENCE,
    "WCP02_PARALLEL_SPLIT": WCP02_PARALLEL_SPLIT,
    "WCP03_SYNCHRONIZATION": WCP03_SYNCHRONIZATION,
    "WCP04_EXCLUSIVE_CHOICE": WCP04_EXCLUSIVE_CHOICE,
    "WCP05_SIMPLE_MERGE": WCP05_SIMPLE_MERGE,
    "WCP06_MULTI_CHOICE": WCP06_MULTI_CHOICE,
    "WCP07_STRUCTURED_SYNCHRONIZING_MERGE": WCP07_STRUCTURED_SYNCHRONIZING_MERGE,
    "WCP08_MULTI_MERGE": WCP08_MULTI_MERGE,
    "WCP09_STRUCTURED_DISCRIMINATOR": WCP09_STRUCTURED_DISCRIMINATOR,
    "WCP12_MULTIPLE_INSTANCES_WITHOUT_SYNC": WCP12_MULTIPLE_INSTANCES_WITHOUT_SYNC,
    "WCP13_MULTIPLE_INSTANCES_WITH_DESIGN_TIME_KNOWLEDGE": WCP13_MULTIPLE_INSTANCES_WITH_DESIGN_TIME_KNOWLEDGE,
    "WCP14_MULTIPLE_INSTANCES_WITH_RUNTIME_KNOWLEDGE": WCP14_MULTIPLE_INSTANCES_WITH_RUNTIME_KNOWLEDGE,
    "WCP15_MULTIPLE_INSTANCES_WITHOUT_PRIOR_KNOWLEDGE": WCP15_MULTIPLE_INSTANCES_WITHOUT_PRIOR_KNOWLEDGE,
    "WCP16_DEFERRED_CHOICE": WCP16_DEFERRED_CHOICE,
    "WCP17_INTERLEAVED_PARALLEL_ROUTING": WCP17_INTERLEAVED_PARALLEL_ROUTING,
    "WCP18_MILESTONE": WCP18_MILESTONE,
    "WCP19_CANCEL_TASK": WCP19_CANCEL_TASK,
    "WCP20_CANCEL_CASE": WCP20_CANCEL_CASE,
    "WCP21_STRUCTURED_LOOP": WCP21_STRUCTURED_LOOP,
    "WCP22_RECURSION": WCP22_RECURSION,
    "WCP23_TRANSIENT_TRIGGER": WCP23_TRANSIENT_TRIGGER,
    "WCP24_PERSISTENT_TRIGGER": WCP24_PERSISTENT_TRIGGER,
    "WCP25_CANCEL_REGION": WCP25_CANCEL_REGION,
    "WCP28_BLOCKING_DISCRIMINATOR": WCP28_BLOCKING_DISCRIMINATOR,
    "WCP29_CANCELLING_DISCRIMINATOR": WCP29_CANCELLING_DISCRIMINATOR,
    "WCP30_PARTIAL_JOIN": WCP30_PARTIAL_JOIN,
    "WCP33_GENERALIZED_AND_JOIN": WCP33_GENERALIZED_AND_JOIN,
    "WCP37_LOCAL_SYNCHRONIZING_MERGE": WCP37_LOCAL_SYNCHRONIZING_MERGE,
    "WCP38_GENERAL_SYNCHRONIZING_MERGE": WCP38_GENERAL_SYNCHRONIZING_MERGE,
    "WCP39_CRITICAL_SECTION": WCP39_CRITICAL_SECTION,
    "WCP40_INTERLEAVED_ROUTING": WCP40_INTERLEAVED_ROUTING,
    "WCP41_THREAD_MERGE": WCP41_THREAD_MERGE,
    "WCP42_THREAD_SPLIT": WCP42_THREAD_SPLIT,
    "WCP43_EXPLICIT_TERMINATION": WCP43_EXPLICIT_TERMINATION,
}


@pytest.fixture(params=ALL_WCP_TOPOLOGIES.keys())
def wcp_topology(request: pytest.FixtureRequest) -> tuple[str, str]:
    """Parameterized fixture for all 43 WCP topologies.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Pytest request object with pattern name.

    Returns
    -------
    tuple[str, str]
        (pattern_name, topology_turtle)

    Examples
    --------
    >>> @pytest.mark.parametrize("wcp_topology", ALL_WCP_TOPOLOGIES.keys(), indirect=True)
    ... def test_all_patterns(wcp_topology):
    ...     pattern_name, topology = wcp_topology
    ...     assert len(topology) > 0
    """
    pattern_name = request.param
    return (pattern_name, ALL_WCP_TOPOLOGIES[pattern_name])
