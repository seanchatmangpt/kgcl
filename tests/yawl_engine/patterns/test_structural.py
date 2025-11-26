"""Tests for YAWL Structural Patterns (Patterns 10-11).

This test suite validates the Arbitrary Cycles and Implicit Termination patterns
using Chicago School TDD with real RDF graph operations (no mocking).

Test Coverage:
- Pattern 10: Arbitrary Cycles - Cycle detection, iteration tracking, max limits
- Pattern 11: Implicit Termination - Workflow termination detection
- Integration with RDF graphs and SPARQL queries
- Edge cases: Empty graphs, infinite loops, concurrent termination

Examples
--------
>>> pytest tests/yawl_engine/patterns/test_structural.py -v
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, URIRef

from kgcl.yawl_engine.patterns.structural import (
    KGC,
    YAWL,
    ArbitraryCycles,
    ExecutionResult,
    ImplicitTermination,
    PatternResult,
    PatternStatus,
)

# ============================================================================
# Fixtures - Real RDF Graphs (No Mocking)
# ============================================================================


@pytest.fixture
def empty_graph() -> Graph:
    """Create empty RDF graph."""
    graph = Graph()
    graph.bind("yawl", YAWL)
    graph.bind("kgc", KGC)
    return graph


@pytest.fixture
def cycle_graph() -> Graph:
    """Create graph with A → B → C → A cycle."""
    graph = Graph()
    graph.bind("yawl", YAWL)
    graph.bind("kgc", KGC)

    # Create cycle: TaskA → TaskB → TaskC → TaskA
    task_a = URIRef("urn:task:TaskA")
    task_b = URIRef("urn:task:TaskB")
    task_c = URIRef("urn:task:TaskC")

    graph.add((task_a, YAWL.flowsTo, task_b))
    graph.add((task_b, YAWL.flowsTo, task_c))
    graph.add((task_c, YAWL.flowsTo, task_a))

    return graph


@pytest.fixture
def linear_graph() -> Graph:
    """Create linear graph with no cycles: A → B → C."""
    graph = Graph()
    graph.bind("yawl", YAWL)
    graph.bind("kgc", KGC)

    task_a = URIRef("urn:task:TaskA")
    task_b = URIRef("urn:task:TaskB")
    task_c = URIRef("urn:task:TaskC")

    graph.add((task_a, YAWL.flowsTo, task_b))
    graph.add((task_b, YAWL.flowsTo, task_c))

    return graph


@pytest.fixture
def active_workflow_graph() -> Graph:
    """Create graph with active tasks (enabled/running)."""
    graph = Graph()
    graph.bind("yawl", YAWL)
    graph.bind("kgc", KGC)

    task_a = URIRef("urn:task:TaskA")
    task_b = URIRef("urn:task:TaskB")
    task_c = URIRef("urn:task:TaskC")

    graph.add((task_a, YAWL.status, Literal("completed")))
    graph.add((task_b, YAWL.status, Literal("enabled")))
    graph.add((task_c, YAWL.status, Literal("running")))

    return graph


@pytest.fixture
def completed_workflow_graph() -> Graph:
    """Create graph with all tasks completed."""
    graph = Graph()
    graph.bind("yawl", YAWL)
    graph.bind("kgc", KGC)

    task_a = URIRef("urn:task:TaskA")
    task_b = URIRef("urn:task:TaskB")
    task_c = URIRef("urn:task:TaskC")

    graph.add((task_a, YAWL.status, Literal("completed")))
    graph.add((task_b, YAWL.status, Literal("completed")))
    graph.add((task_c, YAWL.status, Literal("completed")))

    return graph


# ============================================================================
# Pattern 10: Arbitrary Cycles - Tests
# ============================================================================


def test_cycle_detection_finds_simple_cycle(cycle_graph: Graph) -> None:
    """Cycle detection identifies A → B → C → A cycle."""
    cycles = ArbitraryCycles()
    path = cycles.detect_cycle(cycle_graph, URIRef("urn:task:TaskA"))

    # Verify cycle path contains all nodes
    assert len(path) > 0
    assert URIRef("urn:task:TaskA") in path
    assert URIRef("urn:task:TaskB") in path
    assert URIRef("urn:task:TaskC") in path


def test_cycle_detection_returns_empty_for_linear_graph(linear_graph: Graph) -> None:
    """Cycle detection returns empty list for acyclic graph."""
    cycles = ArbitraryCycles()
    path = cycles.detect_cycle(linear_graph, URIRef("urn:task:TaskA"))

    assert len(path) == 0


def test_cycle_detection_handles_empty_graph(empty_graph: Graph) -> None:
    """Cycle detection handles empty graph without errors."""
    cycles = ArbitraryCycles()
    path = cycles.detect_cycle(empty_graph, URIRef("urn:task:NonExistent"))

    assert len(path) == 0


def test_cycle_evaluate_detects_cycle(cycle_graph: Graph) -> None:
    """Evaluate correctly detects cycle and returns success."""
    cycles = ArbitraryCycles()
    context = {"iteration_counts": {}}

    result = cycles.evaluate(cycle_graph, URIRef("urn:task:TaskA"), context)

    assert isinstance(result, PatternResult)
    assert result.success is True
    assert result.status == PatternStatus.CYCLE_DETECTED
    assert "cycle_path" in result.metadata
    assert result.metadata["cycle_length"] > 0


def test_cycle_evaluate_enforces_max_iterations(cycle_graph: Graph) -> None:
    """Evaluate enforces maximum iteration limit."""
    cycles = ArbitraryCycles(max_iterations=5)
    context = {"iteration_counts": {"urn:task:TaskA": 10}}

    result = cycles.evaluate(cycle_graph, URIRef("urn:task:TaskA"), context)

    assert result.success is False
    assert result.status == PatternStatus.MAX_ITERATIONS
    assert "exceeded max iterations" in result.message


def test_cycle_execute_increments_iteration_count(cycle_graph: Graph) -> None:
    """Execute increments iteration counter correctly."""
    cycles = ArbitraryCycles()
    context = {"iteration_counts": {"urn:task:TaskA": 2}}

    result = cycles.execute(cycle_graph, URIRef("urn:task:TaskA"), context)

    assert isinstance(result, ExecutionResult)
    assert result.committed is True
    assert result.data_updates["iteration_counts"]["urn:task:TaskA"] == 3


def test_cycle_execute_creates_rdf_updates(cycle_graph: Graph) -> None:
    """Execute creates correct RDF triple updates."""
    cycles = ArbitraryCycles()
    context = {"iteration_counts": {}}

    result = cycles.execute(cycle_graph, URIRef("urn:task:TaskA"), context)

    assert len(result.updates) == 3
    # Verify status, iteration count, and pattern ID triples
    statuses = [u for u in result.updates if YAWL.status in u[1]]
    assert len(statuses) == 1
    assert statuses[0][2] == "completed"


def test_cycle_execute_handles_first_iteration(cycle_graph: Graph) -> None:
    """Execute correctly handles first iteration (count 0 → 1)."""
    cycles = ArbitraryCycles()
    context = {"iteration_counts": {}}

    result = cycles.execute(cycle_graph, URIRef("urn:task:TaskA"), context)

    assert result.data_updates["iteration_counts"]["urn:task:TaskA"] == 1


def test_cycle_pattern_metadata() -> None:
    """Arbitrary cycles pattern has correct metadata."""
    cycles = ArbitraryCycles(max_iterations=100)

    assert cycles.pattern_id == 10
    assert cycles.name == "Arbitrary Cycles"
    assert cycles.max_iterations == 100


# ============================================================================
# Pattern 11: Implicit Termination - Tests
# ============================================================================


def test_implicit_termination_detects_active_tasks(active_workflow_graph: Graph) -> None:
    """Implicit termination returns False when tasks are active."""
    termination = ImplicitTermination()
    should_terminate = termination.check_termination(active_workflow_graph, URIRef("urn:workflow:W1"))

    assert should_terminate is False


def test_implicit_termination_detects_completion(completed_workflow_graph: Graph) -> None:
    """Implicit termination returns True when all tasks completed."""
    termination = ImplicitTermination()
    should_terminate = termination.check_termination(completed_workflow_graph, URIRef("urn:workflow:W1"))

    assert should_terminate is True


def test_implicit_termination_handles_empty_workflow(empty_graph: Graph) -> None:
    """Implicit termination handles empty workflow gracefully."""
    termination = ImplicitTermination()
    should_terminate = termination.check_termination(empty_graph, URIRef("urn:workflow:Empty"))

    # Empty workflow has no active tasks - should terminate
    assert should_terminate is True


def test_implicit_termination_evaluate_success(completed_workflow_graph: Graph) -> None:
    """Evaluate returns success when workflow should terminate."""
    termination = ImplicitTermination()
    result = termination.evaluate(completed_workflow_graph, URIRef("urn:workflow:W1"), {})

    assert isinstance(result, PatternResult)
    assert result.success is True
    assert result.status == PatternStatus.SUCCESS
    assert "terminated implicitly" in result.message
    assert result.metadata["completed_tasks"] > 0


def test_implicit_termination_evaluate_pending(active_workflow_graph: Graph) -> None:
    """Evaluate returns pending when workflow has active tasks."""
    termination = ImplicitTermination()
    result = termination.evaluate(active_workflow_graph, URIRef("urn:workflow:W1"), {})

    assert result.success is False
    assert result.status == PatternStatus.PENDING
    assert "active tasks" in result.message


def test_implicit_termination_execute_marks_workflow(completed_workflow_graph: Graph) -> None:
    """Execute marks workflow as completed with implicit termination."""
    termination = ImplicitTermination()
    result = termination.execute(completed_workflow_graph, URIRef("urn:workflow:W1"), {})

    assert isinstance(result, ExecutionResult)
    assert result.committed is True
    assert result.data_updates["workflow_terminated"] is True


def test_implicit_termination_execute_creates_rdf_updates(completed_workflow_graph: Graph) -> None:
    """Execute creates correct RDF triple updates."""
    termination = ImplicitTermination()
    result = termination.execute(completed_workflow_graph, URIRef("urn:workflow:W1"), {})

    assert len(result.updates) == 3
    # Verify status, termination type, and pattern ID
    status_updates = [u for u in result.updates if "status" in u[1]]
    assert len(status_updates) == 1
    assert status_updates[0][2] == "completed"


def test_implicit_termination_pattern_metadata() -> None:
    """Implicit termination pattern has correct metadata."""
    termination = ImplicitTermination()

    assert termination.pattern_id == 11
    assert termination.name == "Implicit Termination"


# ============================================================================
# Integration Tests - Patterns Working Together
# ============================================================================


def test_cycle_with_implicit_termination(cycle_graph: Graph) -> None:
    """Cycle pattern integrates with implicit termination detection."""
    cycles = ArbitraryCycles(max_iterations=3)
    termination = ImplicitTermination()

    # Execute 3 iterations
    context = {"iteration_counts": {}}
    for _ in range(3):
        result = cycles.execute(cycle_graph, URIRef("urn:task:TaskA"), context)
        context = {"iteration_counts": result.data_updates["iteration_counts"]}

    # Verify max iterations reached
    eval_result = cycles.evaluate(cycle_graph, URIRef("urn:task:TaskA"), context)
    assert eval_result.status == PatternStatus.MAX_ITERATIONS

    # Mark all tasks completed
    for task in ["urn:task:TaskA", "urn:task:TaskB", "urn:task:TaskC"]:
        cycle_graph.add((URIRef(task), YAWL.status, Literal("completed")))

    # Verify implicit termination triggers
    should_terminate = termination.check_termination(cycle_graph, URIRef("urn:workflow:W1"))
    assert should_terminate is True


def test_pattern_result_immutability() -> None:
    """PatternResult is immutable frozen dataclass."""
    result = PatternResult(success=True, status=PatternStatus.SUCCESS, message="Test", metadata={"key": "value"})

    # Verify cannot modify fields
    with pytest.raises(AttributeError):
        result.success = False  # type: ignore[misc]


def test_execution_result_immutability() -> None:
    """ExecutionResult is immutable frozen dataclass."""
    result = ExecutionResult(committed=True, task=URIRef("urn:task:Test"), updates=[], data_updates={})

    # Verify cannot modify fields
    with pytest.raises(AttributeError):
        result.committed = False  # type: ignore[misc]


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_cycle_detection_self_loop() -> None:
    """Cycle detection handles self-loop (A → A)."""
    graph = Graph()
    task_a = URIRef("urn:task:SelfLoop")
    graph.add((task_a, YAWL.flowsTo, task_a))

    cycles = ArbitraryCycles()
    path = cycles.detect_cycle(graph, task_a)

    assert len(path) > 0
    assert task_a in path


def test_implicit_termination_mixed_states() -> None:
    """Implicit termination handles mixed task states correctly."""
    graph = Graph()
    graph.add((URIRef("urn:task:A"), YAWL.status, Literal("completed")))
    graph.add((URIRef("urn:task:B"), YAWL.status, Literal("cancelled")))
    graph.add((URIRef("urn:task:C"), YAWL.status, Literal("failed")))

    termination = ImplicitTermination()
    # No tasks are enabled/running - should terminate
    should_terminate = termination.check_termination(graph, URIRef("urn:workflow:W1"))
    assert should_terminate is True


def test_cycle_execute_preserves_existing_counts() -> None:
    """Execute preserves iteration counts for other tasks."""
    cycles = ArbitraryCycles()
    context = {"iteration_counts": {"urn:task:Other": 5}}

    result = cycles.execute(Graph(), URIRef("urn:task:TaskA"), context)

    # Both tasks should be in updated counts
    assert result.data_updates["iteration_counts"]["urn:task:Other"] == 5
    assert result.data_updates["iteration_counts"]["urn:task:TaskA"] == 1
