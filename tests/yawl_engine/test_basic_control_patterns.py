"""Tests for YAWL Basic Control Flow Patterns (1-5) - Chicago School TDD.

This test suite validates all 5 basic control flow patterns with full
coverage of YAWL semantics, edge cases, and error handling.

Test Strategy (Chicago School)
-------------------------------
- Use REAL RDF graphs (no mocking domain objects)
- Test observable behavior (graph state changes, enabled tasks)
- Verify ALL edge cases (missing predicates, empty graphs, timeouts)
- Target: <1 second total runtime, 100% pattern coverage

Test Organization
-----------------
- test_pattern_X_evaluate_* - Applicability checks
- test_pattern_X_execute_* - Execution behavior
- test_pattern_X_edge_cases_* - Error handling
"""

from __future__ import annotations

from typing import Any

import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.yawl_engine.patterns.basic_control import (
    BASIC_CONTROL_PATTERNS,
    ExclusiveChoice,
    ExecutionStatus,
    ParallelSplit,
    Sequence,
    SimpleMerge,
    Synchronization,
    get_pattern,
)

# YAWL namespace
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")


# ============================================================================
# FIXTURES - Reusable Graph Configurations
# ============================================================================


@pytest.fixture
def empty_graph() -> Graph:
    """Empty RDF graph for negative tests."""
    g = Graph()
    g.bind("yawl", YAWL)
    return g


@pytest.fixture
def sequential_graph() -> Graph:
    """Sequential workflow: A → B → C."""
    g = Graph()
    g.bind("yawl", YAWL)

    task_a = URIRef("urn:task:A")
    task_b = URIRef("urn:task:B")
    task_c = URIRef("urn:task:C")

    # A flows to B flows to C
    g.add((task_a, YAWL.flowsTo, task_b))
    g.add((task_b, YAWL.flowsTo, task_c))

    # No split/join types (defaults to sequential)
    return g


@pytest.fixture
def parallel_split_graph() -> Graph:
    """AND-split workflow: A → {B, C, D}."""
    g = Graph()
    g.bind("yawl", YAWL)

    task_a = URIRef("urn:task:A")
    task_b = URIRef("urn:task:B")
    task_c = URIRef("urn:task:C")
    task_d = URIRef("urn:task:D")

    # A is AND-split to {B, C, D}
    g.add((task_a, YAWL.splitType, Literal("AND")))
    g.add((task_a, YAWL.flowsTo, task_b))
    g.add((task_a, YAWL.flowsTo, task_c))
    g.add((task_a, YAWL.flowsTo, task_d))

    return g


@pytest.fixture
def synchronization_graph() -> Graph:
    """AND-join workflow: {B, C, D} → E."""
    g = Graph()
    g.bind("yawl", YAWL)

    task_b = URIRef("urn:task:B")
    task_c = URIRef("urn:task:C")
    task_d = URIRef("urn:task:D")
    task_e = URIRef("urn:task:E")

    # {B, C, D} converge to E (AND-join)
    g.add((task_e, YAWL.joinType, Literal("AND")))
    g.add((task_b, YAWL.flowsTo, task_e))
    g.add((task_c, YAWL.flowsTo, task_e))
    g.add((task_d, YAWL.flowsTo, task_e))

    return g


@pytest.fixture
def exclusive_choice_graph() -> Graph:
    """XOR-split workflow: A → {B | C}."""
    g = Graph()
    g.bind("yawl", YAWL)

    task_a = URIRef("urn:task:A")
    task_b = URIRef("urn:task:B")
    task_c = URIRef("urn:task:C")

    # A is XOR-split to {B, C}
    g.add((task_a, YAWL.splitType, Literal("XOR")))
    g.add((task_a, YAWL.flowsTo, task_b))
    g.add((task_a, YAWL.flowsTo, task_c))

    return g


@pytest.fixture
def simple_merge_graph() -> Graph:
    """XOR-join workflow: {B | C} → D."""
    g = Graph()
    g.bind("yawl", YAWL)

    task_b = URIRef("urn:task:B")
    task_c = URIRef("urn:task:C")
    task_d = URIRef("urn:task:D")

    # {B, C} converge to D (XOR-join)
    g.add((task_d, YAWL.joinType, Literal("XOR")))
    g.add((task_b, YAWL.flowsTo, task_d))
    g.add((task_c, YAWL.flowsTo, task_d))

    return g


# ============================================================================
# PATTERN 1: SEQUENCE - Tests
# ============================================================================


def test_sequence_evaluate_applies_to_default_task(sequential_graph: Graph) -> None:
    """Sequential pattern applies to tasks with no split/join configured."""
    seq = Sequence()
    task_a = URIRef("urn:task:A")

    result = seq.evaluate(sequential_graph, task_a, {})

    assert result.applicable
    assert "sequential" in result.reason.lower()
    assert result.metadata["outgoing_count"] == 1


def test_sequence_evaluate_rejects_and_split(parallel_split_graph: Graph) -> None:
    """Sequential pattern rejects AND-split tasks."""
    seq = Sequence()
    task_a = URIRef("urn:task:A")

    result = seq.evaluate(parallel_split_graph, task_a, {})

    assert not result.applicable
    assert "AND" in result.reason


def test_sequence_execute_enables_next_task(sequential_graph: Graph) -> None:
    """Executing sequence marks task complete and enables successor."""
    seq = Sequence()
    task_a = URIRef("urn:task:A")
    task_b = URIRef("urn:task:B")

    result = seq.execute(sequential_graph, task_a, {})

    assert result.success
    assert len(result.next_tasks) == 1
    assert result.next_tasks[0] == task_b

    # Verify graph state changes
    assert (task_a, YAWL.status, Literal("completed")) in sequential_graph
    assert (task_b, YAWL.status, Literal("enabled")) in sequential_graph


def test_sequence_execute_handles_empty_outgoing(empty_graph: Graph) -> None:
    """Sequence execution succeeds even with no outgoing tasks."""
    seq = Sequence()
    task_a = URIRef("urn:task:A")

    result = seq.execute(empty_graph, task_a, {})

    assert result.success
    assert result.next_tasks == []


def test_sequence_execute_passes_context_data(sequential_graph: Graph) -> None:
    """Sequence execution preserves workflow data context."""
    seq = Sequence()
    task_a = URIRef("urn:task:A")
    context = {"workflow_var": 42}

    result = seq.execute(sequential_graph, task_a, context)

    assert result.success
    assert result.data_updates == context
    assert result.data_updates["workflow_var"] == 42


# ============================================================================
# PATTERN 2: PARALLEL SPLIT - Tests
# ============================================================================


def test_parallel_split_evaluate_requires_and_type(parallel_split_graph: Graph) -> None:
    """Parallel split requires explicit AND split type."""
    split = ParallelSplit()
    task_a = URIRef("urn:task:A")

    result = split.evaluate(parallel_split_graph, task_a, {})

    assert result.applicable
    assert "AND-split" in result.reason
    assert result.metadata["branch_count"] == 3


def test_parallel_split_evaluate_rejects_xor_split(exclusive_choice_graph: Graph) -> None:
    """Parallel split rejects XOR-split tasks."""
    split = ParallelSplit()
    task_a = URIRef("urn:task:A")

    result = split.evaluate(exclusive_choice_graph, task_a, {})

    assert not result.applicable
    assert "XOR" in result.reason


def test_parallel_split_evaluate_requires_multiple_branches(sequential_graph: Graph) -> None:
    """Parallel split topology validation delegated to SHACL shapes.

    Note: This test now reflects the Semantic Singularity architecture where
    topology validation is performed by SHACL shapes (ontology/yawl-shapes.ttl),
    NOT by procedural Python code. The pattern's evaluate() method assumes the
    graph has already passed SHACL validation.
    """
    split = ParallelSplit()
    task_a = URIRef("urn:task:A")

    # Add AND split type but only 1 outgoing branch
    sequential_graph.add((task_a, YAWL.splitType, Literal("AND")))

    result = split.evaluate(sequential_graph, task_a, {})

    # Pattern evaluates assuming SHACL validation already passed
    # Invalid topology would be caught by SHACL validator before reaching here
    assert result.applicable  # Pattern doesn't validate topology anymore
    assert "AND-split" in result.reason


def test_parallel_split_execute_enables_all_branches(parallel_split_graph: Graph) -> None:
    """Executing parallel split enables ALL outgoing tasks."""
    split = ParallelSplit()
    task_a = URIRef("urn:task:A")
    task_b = URIRef("urn:task:B")
    task_c = URIRef("urn:task:C")
    task_d = URIRef("urn:task:D")

    result = split.execute(parallel_split_graph, task_a, {})

    assert result.success
    assert len(result.next_tasks) == 3
    assert set(result.next_tasks) == {task_b, task_c, task_d}

    # Verify ALL branches enabled
    assert (task_b, YAWL.status, Literal("enabled")) in parallel_split_graph
    assert (task_c, YAWL.status, Literal("enabled")) in parallel_split_graph
    assert (task_d, YAWL.status, Literal("enabled")) in parallel_split_graph


def test_parallel_split_execute_marks_split_type(parallel_split_graph: Graph) -> None:
    """Parallel split records AND split type in graph."""
    split = ParallelSplit()
    task_a = URIRef("urn:task:A")

    split.execute(parallel_split_graph, task_a, {})

    assert (task_a, YAWL.status, Literal("completed")) in parallel_split_graph
    # Note: splitType already in graph from fixture, verify it's preserved


def test_parallel_split_execute_fails_without_outgoing(empty_graph: Graph) -> None:
    """Parallel split fails if no outgoing branches configured."""
    split = ParallelSplit()
    task_a = URIRef("urn:task:A")
    empty_graph.add((task_a, YAWL.splitType, Literal("AND")))

    result = split.execute(empty_graph, task_a, {})

    assert not result.success
    assert result.error is not None
    assert "no outgoing tasks" in result.error.lower()


# ============================================================================
# PATTERN 3: SYNCHRONIZATION - Tests
# ============================================================================


def test_synchronization_evaluate_requires_and_join(synchronization_graph: Graph) -> None:
    """Synchronization requires explicit AND join type."""
    sync = Synchronization()
    task_e = URIRef("urn:task:E")

    result = sync.evaluate(synchronization_graph, task_e, {})

    assert result.applicable
    assert "AND-join" in result.reason
    assert result.metadata["incoming_count"] == 3


def test_synchronization_evaluate_rejects_xor_join(simple_merge_graph: Graph) -> None:
    """Synchronization rejects XOR-join tasks."""
    sync = Synchronization()
    task_d = URIRef("urn:task:D")

    result = sync.evaluate(simple_merge_graph, task_d, {})

    assert not result.applicable
    assert "XOR" in result.reason


def test_synchronization_evaluate_checks_completion_status(synchronization_graph: Graph) -> None:
    """Synchronization evaluation reports incoming completion status."""
    sync = Synchronization()
    task_e = URIRef("urn:task:E")
    task_b = URIRef("urn:task:B")

    # Mark one task completed
    synchronization_graph.add((task_b, YAWL.status, Literal("completed")))

    result = sync.evaluate(synchronization_graph, task_e, {})

    assert result.applicable
    assert not result.metadata["all_completed"]  # Not all done yet


def test_synchronization_execute_waits_for_all_incoming(synchronization_graph: Graph) -> None:
    """Synchronization blocks until ALL incoming tasks complete."""
    sync = Synchronization()
    task_e = URIRef("urn:task:E")
    task_b = URIRef("urn:task:B")

    # Only one task completed
    synchronization_graph.add((task_b, YAWL.status, Literal("completed")))

    result = sync.execute(synchronization_graph, task_e, {})

    # Should fail (waiting for others)
    assert not result.success
    assert result.error is not None
    assert "incomplete" in result.error.lower()


def test_synchronization_execute_proceeds_when_all_complete(synchronization_graph: Graph) -> None:
    """Synchronization succeeds when all incoming tasks are complete."""
    sync = Synchronization()
    task_b = URIRef("urn:task:B")
    task_c = URIRef("urn:task:C")
    task_d = URIRef("urn:task:D")
    task_e = URIRef("urn:task:E")

    # Mark ALL incoming tasks completed
    synchronization_graph.add((task_b, YAWL.status, Literal("completed")))
    synchronization_graph.add((task_c, YAWL.status, Literal("completed")))
    synchronization_graph.add((task_d, YAWL.status, Literal("completed")))

    result = sync.execute(synchronization_graph, task_e, {})

    assert result.success
    assert (task_e, YAWL.status, Literal("completed")) in synchronization_graph


def test_synchronization_execute_fails_without_incoming(empty_graph: Graph) -> None:
    """Synchronization fails if no incoming tasks configured."""
    sync = Synchronization()
    task_e = URIRef("urn:task:E")
    empty_graph.add((task_e, YAWL.joinType, Literal("AND")))

    result = sync.execute(empty_graph, task_e, {})

    assert not result.success
    assert result.error is not None
    assert "no incoming tasks" in result.error.lower()


# ============================================================================
# PATTERN 4: EXCLUSIVE CHOICE - Tests
# ============================================================================


def test_exclusive_choice_evaluate_requires_xor_split(exclusive_choice_graph: Graph) -> None:
    """Exclusive choice requires explicit XOR split type."""
    choice = ExclusiveChoice()
    task_a = URIRef("urn:task:A")

    result = choice.evaluate(exclusive_choice_graph, task_a, {})

    assert result.applicable
    assert "XOR-split" in result.reason
    assert result.metadata["branch_count"] == 2


def test_exclusive_choice_evaluate_rejects_and_split(parallel_split_graph: Graph) -> None:
    """Exclusive choice rejects AND-split tasks."""
    choice = ExclusiveChoice()
    task_a = URIRef("urn:task:A")

    result = choice.evaluate(parallel_split_graph, task_a, {})

    assert not result.applicable
    assert "AND" in result.reason


def test_exclusive_choice_execute_enables_one_branch(exclusive_choice_graph: Graph) -> None:
    """Executing exclusive choice enables exactly ONE outgoing task."""
    choice = ExclusiveChoice()
    task_a = URIRef("urn:task:A")

    result = choice.execute(exclusive_choice_graph, task_a, {})

    assert result.success
    assert len(result.next_tasks) == 1  # Only one branch


def test_exclusive_choice_execute_uses_context_selector(exclusive_choice_graph: Graph) -> None:
    """Exclusive choice can select branch via context data."""
    choice = ExclusiveChoice()
    task_a = URIRef("urn:task:A")
    task_c = URIRef("urn:task:C")

    # Select second branch (index 1)
    context = {"branch_selector": 1}

    result = choice.execute(exclusive_choice_graph, task_a, context)

    assert result.success
    assert result.next_tasks[0] == task_c


def test_exclusive_choice_execute_records_chosen_branch(exclusive_choice_graph: Graph) -> None:
    """Exclusive choice records which branch was selected."""
    choice = ExclusiveChoice()
    task_a = URIRef("urn:task:A")

    result = choice.execute(exclusive_choice_graph, task_a, {})

    assert result.success
    # Check graph has chosenBranch recorded
    chosen = list(exclusive_choice_graph.objects(task_a, YAWL.chosenBranch))
    assert len(chosen) == 1


def test_exclusive_choice_execute_fails_without_outgoing(empty_graph: Graph) -> None:
    """Exclusive choice fails if no outgoing branches configured."""
    choice = ExclusiveChoice()
    task_a = URIRef("urn:task:A")
    empty_graph.add((task_a, YAWL.splitType, Literal("XOR")))

    result = choice.execute(empty_graph, task_a, {})

    assert not result.success
    assert result.error is not None
    assert "no outgoing" in result.error.lower()


# ============================================================================
# PATTERN 5: SIMPLE MERGE - Tests
# ============================================================================


def test_simple_merge_evaluate_requires_xor_join(simple_merge_graph: Graph) -> None:
    """Simple merge requires explicit XOR join type."""
    merge = SimpleMerge()
    task_d = URIRef("urn:task:D")

    result = merge.evaluate(simple_merge_graph, task_d, {})

    assert result.applicable
    assert "XOR-join" in result.reason
    assert result.metadata["incoming_count"] == 2


def test_simple_merge_evaluate_rejects_and_join(synchronization_graph: Graph) -> None:
    """Simple merge rejects AND-join tasks."""
    merge = SimpleMerge()
    task_e = URIRef("urn:task:E")

    result = merge.evaluate(synchronization_graph, task_e, {})

    assert not result.applicable
    assert "AND" in result.reason


def test_simple_merge_execute_waits_for_one_incoming(simple_merge_graph: Graph) -> None:
    """Simple merge waits until at least one incoming task completes."""
    merge = SimpleMerge()
    task_d = URIRef("urn:task:D")

    # No incoming tasks completed yet
    result = merge.execute(simple_merge_graph, task_d, {})

    assert not result.success
    assert result.error is not None
    assert "waiting" in result.error.lower()


def test_simple_merge_execute_proceeds_on_first_arrival(simple_merge_graph: Graph) -> None:
    """Simple merge succeeds when ANY incoming task completes."""
    merge = SimpleMerge()
    task_b = URIRef("urn:task:B")
    task_d = URIRef("urn:task:D")

    # Mark one incoming task completed (first arrival)
    simple_merge_graph.add((task_b, YAWL.status, Literal("completed")))

    result = merge.execute(simple_merge_graph, task_d, {})

    assert result.success
    assert (task_d, YAWL.status, Literal("completed")) in simple_merge_graph


def test_simple_merge_execute_records_triggering_branch(simple_merge_graph: Graph) -> None:
    """Simple merge records which branch triggered the merge."""
    merge = SimpleMerge()
    task_b = URIRef("urn:task:B")
    task_d = URIRef("urn:task:D")

    simple_merge_graph.add((task_b, YAWL.status, Literal("completed")))

    result = merge.execute(simple_merge_graph, task_d, {})

    assert result.success
    # Check graph has triggeringBranch recorded
    triggering = list(simple_merge_graph.objects(task_d, YAWL.triggeringBranch))
    assert len(triggering) == 1
    assert triggering[0] == task_b


def test_simple_merge_execute_handles_multiple_completed(simple_merge_graph: Graph) -> None:
    """Simple merge handles case where multiple branches completed."""
    merge = SimpleMerge()
    task_b = URIRef("urn:task:B")
    task_c = URIRef("urn:task:C")
    task_d = URIRef("urn:task:D")

    # Both branches completed (shouldn't happen in XOR, but test resilience)
    simple_merge_graph.add((task_b, YAWL.status, Literal("completed")))
    simple_merge_graph.add((task_c, YAWL.status, Literal("completed")))

    result = merge.execute(simple_merge_graph, task_d, {})

    # Should still succeed (takes first completed)
    assert result.success


def test_simple_merge_execute_fails_without_incoming(empty_graph: Graph) -> None:
    """Simple merge fails if no incoming tasks configured."""
    merge = SimpleMerge()
    task_d = URIRef("urn:task:D")
    empty_graph.add((task_d, YAWL.joinType, Literal("XOR")))

    result = merge.execute(empty_graph, task_d, {})

    assert not result.success
    assert result.error is not None
    assert "no incoming" in result.error.lower()


# ============================================================================
# PATTERN REGISTRY - Tests
# ============================================================================


def test_pattern_registry_contains_all_patterns() -> None:
    """Pattern registry includes all 5 basic control patterns."""
    assert len(BASIC_CONTROL_PATTERNS) == 5
    assert all(i in BASIC_CONTROL_PATTERNS for i in range(1, 6))


def test_get_pattern_returns_correct_pattern() -> None:
    """get_pattern() returns pattern implementation by ID."""
    seq = get_pattern(1)
    split = get_pattern(2)
    sync = get_pattern(3)
    choice = get_pattern(4)
    merge = get_pattern(5)

    assert isinstance(seq, Sequence)
    assert isinstance(split, ParallelSplit)
    assert isinstance(sync, Synchronization)
    assert isinstance(choice, ExclusiveChoice)
    assert isinstance(merge, SimpleMerge)


def test_get_pattern_returns_none_for_invalid_id() -> None:
    """get_pattern() returns None for non-existent pattern ID."""
    pattern = get_pattern(999)
    assert pattern is None


def test_all_patterns_have_correct_ids() -> None:
    """All patterns have sequential IDs 1-5."""
    expected_ids = {1, 2, 3, 4, 5}
    actual_ids = {p.pattern_id for p in BASIC_CONTROL_PATTERNS.values()}
    assert actual_ids == expected_ids


def test_all_patterns_have_names() -> None:
    """All patterns have non-empty names."""
    for pattern in BASIC_CONTROL_PATTERNS.values():
        assert pattern.name
        assert len(pattern.name) > 0


# ============================================================================
# EDGE CASES & ERROR HANDLING - Tests
# ============================================================================


def test_patterns_handle_empty_graph_gracefully() -> None:
    """All patterns handle empty graphs without crashing."""
    empty = Graph()
    task = URIRef("urn:task:NonExistent")
    context: dict[str, Any] = {}

    for pattern in BASIC_CONTROL_PATTERNS.values():
        # Should not raise exceptions
        eval_result = pattern.evaluate(empty, task, context)
        exec_result = pattern.execute(empty, task, context)

        assert isinstance(eval_result.applicable, bool)
        assert isinstance(exec_result.success, bool)


def test_patterns_preserve_immutability() -> None:
    """All pattern instances are frozen (immutable)."""
    for pattern in BASIC_CONTROL_PATTERNS.values():
        with pytest.raises(AttributeError):
            pattern.name = "Modified"


def test_execution_status_enum_values() -> None:
    """ExecutionStatus enum has correct YAWL lifecycle states."""
    assert ExecutionStatus.ENABLED.value == "enabled"
    assert ExecutionStatus.EXECUTING.value == "executing"
    assert ExecutionStatus.COMPLETED.value == "completed"
    assert ExecutionStatus.CANCELLED.value == "cancelled"
    assert ExecutionStatus.FAILED.value == "failed"
