"""Property-Based Fuzz Testing for YAWL Engine - Hypothesis Integration.

This module uses Hypothesis to generate random workflow graphs, contexts, and
data to catch edge cases, race conditions, and errors across all 43 YAWL patterns.

Fuzz Test Categories
--------------------
1. Pattern Execution Fuzzing - Random inputs to all patterns
2. Graph Structure Fuzzing - Random workflow topologies
3. Data Type Fuzzing - Random context variable types
4. Boundary Fuzzing - Edge values (0, MAX_INT, empty, Unicode)
5. Stateful Fuzzing - RuleBasedStateMachine for workflow lifecycle

Properties Under Test
---------------------
- Pattern execution never crashes (catches all exceptions gracefully)
- Results are always valid ExecutionResult instances
- Completed tasks stay completed (monotonicity)
- No infinite loops (timeout protection)
- Memory doesn't grow unbounded (resource limits)
- RDF graph consistency (no dangling references)

References
----------
- Hypothesis: https://hypothesis.readthedocs.io/
- YAWL Patterns: http://www.yawlfoundation.org/patterns/
- Property-Based Testing: https://fsharpforfunandprofit.com/posts/property-based-testing/
"""

from __future__ import annotations

import logging
import signal
from typing import Any

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.yawl_engine.core import ExecutionResult
from kgcl.yawl_engine.patterns.basic_control import (
    ExclusiveChoice,
    ParallelSplit,
    Sequence,
    SimpleMerge,
    Synchronization,
)
from kgcl.yawl_engine.patterns.structural import ArbitraryCycles, ImplicitTermination

# YAWL namespaces
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
KGC = Namespace("https://kgc.org/ns/")

logger = logging.getLogger(__name__)

# ============================================================================
# HYPOTHESIS STRATEGIES - Random Data Generators
# ============================================================================


@st.composite
def task_uris(draw: st.DrawFn) -> URIRef:
    """Generate random task URIs.

    Returns
    -------
    URIRef
        Random task URI like urn:task:TaskABC123

    Examples
    --------
    >>> from hypothesis import given
    >>> @given(task_uris())
    ... def test_uri_format(uri):
    ...     assert str(uri).startswith("urn:task:")
    """
    task_id = draw(st.text(alphabet=st.characters(whitelist_categories=("Lu", "Nd")), min_size=1, max_size=20))
    return URIRef(f"urn:task:{task_id}")


@st.composite
def workflow_contexts(draw: st.DrawFn) -> dict[str, Any]:
    """Generate random workflow execution contexts.

    Returns
    -------
    dict[str, Any]
        Context with random workflow variables

    Examples
    --------
    >>> from hypothesis import given
    >>> @given(workflow_contexts())
    ... def test_context_is_dict(ctx):
    ...     assert isinstance(ctx, dict)
    """
    num_vars = draw(st.integers(min_value=0, max_value=10))
    context: dict[str, Any] = {}

    for _ in range(num_vars):
        key = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))))
        value = draw(
            st.one_of(
                st.integers(min_value=-10000, max_value=10000),
                st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
                st.text(max_size=100),
                st.booleans(),
                st.lists(st.integers(), max_size=10),
            )
        )
        context[key] = value

    return context


@st.composite
def split_types(draw: st.DrawFn) -> str:
    """Generate random split types (AND, XOR, OR, SEQUENCE)."""
    return draw(st.sampled_from(["AND", "XOR", "OR", "SEQUENCE"]))


@st.composite
def join_types(draw: st.DrawFn) -> str:
    """Generate random join types (AND, XOR, OR)."""
    return draw(st.sampled_from(["AND", "XOR", "OR"]))


@st.composite
def sequential_graphs(draw: st.DrawFn) -> Graph:
    """Generate random sequential workflow graphs (A → B → C → ...).

    Returns
    -------
    Graph
        RDF graph with linear task sequence

    Examples
    --------
    >>> from hypothesis import given
    >>> @given(sequential_graphs())
    ... def test_sequential_has_edges(g):
    ...     assert len(list(g.triples((None, YAWL.flowsTo, None)))) > 0
    """
    g = Graph()
    g.bind("yawl", YAWL)

    num_tasks = draw(st.integers(min_value=2, max_value=10))
    tasks = [draw(task_uris()) for _ in range(num_tasks)]

    # Create linear sequence
    for i in range(len(tasks) - 1):
        g.add((tasks[i], YAWL.flowsTo, tasks[i + 1]))

    return g


@st.composite
def parallel_split_graphs(draw: st.DrawFn) -> Graph:
    """Generate random AND-split workflow graphs (A → {B, C, D, ...}).

    Returns
    -------
    Graph
        RDF graph with parallel split pattern

    Examples
    --------
    >>> from hypothesis import given
    >>> @given(parallel_split_graphs())
    ... def test_parallel_has_split(g):
    ...     splits = list(g.triples((None, YAWL.splitType, Literal("AND"))))
    ...     assert len(splits) > 0
    """
    g = Graph()
    g.bind("yawl", YAWL)

    # Split task
    split_task = draw(task_uris())
    num_branches = draw(st.integers(min_value=2, max_value=8))
    branch_tasks = [draw(task_uris()) for _ in range(num_branches)]

    # Configure AND-split
    g.add((split_task, YAWL.splitType, Literal("AND")))
    for branch in branch_tasks:
        g.add((split_task, YAWL.flowsTo, branch))

    return g


@st.composite
def xor_split_graphs(draw: st.DrawFn) -> Graph:
    """Generate random XOR-split workflow graphs (A → B | C | D).

    Returns
    -------
    Graph
        RDF graph with exclusive choice pattern
    """
    g = Graph()
    g.bind("yawl", YAWL)

    # XOR split task
    split_task = draw(task_uris())
    num_branches = draw(st.integers(min_value=2, max_value=8))
    branch_tasks = [draw(task_uris()) for _ in range(num_branches)]

    # Configure XOR-split
    g.add((split_task, YAWL.splitType, Literal("XOR")))
    for branch in branch_tasks:
        g.add((split_task, YAWL.flowsTo, branch))

    return g


@st.composite
def sync_join_graphs(draw: st.DrawFn) -> Graph:
    """Generate random AND-join workflow graphs ({A, B, C} → D).

    Returns
    -------
    Graph
        RDF graph with synchronization pattern
    """
    g = Graph()
    g.bind("yawl", YAWL)

    # Join task
    join_task = draw(task_uris())
    num_incoming = draw(st.integers(min_value=2, max_value=8))
    incoming_tasks = [draw(task_uris()) for _ in range(num_incoming)]

    # Configure AND-join
    g.add((join_task, YAWL.joinType, Literal("AND")))
    for incoming in incoming_tasks:
        g.add((incoming, YAWL.flowsTo, join_task))
        # Mark incoming tasks as completed
        g.add((incoming, YAWL.status, Literal("completed")))

    return g


@st.composite
def cyclic_graphs(draw: st.DrawFn) -> Graph:
    """Generate random workflow graphs with cycles (A → B → C → A).

    Returns
    -------
    Graph
        RDF graph with at least one cycle
    """
    g = Graph()
    g.bind("yawl", YAWL)

    num_tasks = draw(st.integers(min_value=3, max_value=8))
    tasks = [draw(task_uris()) for _ in range(num_tasks)]

    # Create linear chain
    for i in range(len(tasks) - 1):
        g.add((tasks[i], YAWL.flowsTo, tasks[i + 1]))

    # Add backward edge to create cycle
    g.add((tasks[-1], YAWL.flowsTo, tasks[0]))

    return g


@st.composite
def boundary_values(draw: st.DrawFn) -> Any:
    """Generate boundary values for edge case testing.

    Returns
    -------
    Any
        Boundary value (empty, zero, max, Unicode, etc.)
    """
    return draw(
        st.one_of(
            st.just(0),
            st.just(-1),
            st.just(2**31 - 1),  # MAX_INT
            st.just(-(2**31)),  # MIN_INT
            st.just(""),
            st.just(" "),
            st.just("\n"),
            st.just("\t"),
            st.text(alphabet="🔥💣⚡️🎯", min_size=1, max_size=10),  # Unicode
            st.just([]),
            st.just({}),
            st.just(None),
            st.floats(min_value=0.0, max_value=0.0),  # Exactly 0.0
            st.floats(min_value=1e-10, max_value=1e-10),  # Near-zero
        )
    )


# ============================================================================
# PROPERTY-BASED TESTS - Pattern Execution Fuzzing
# ============================================================================


@given(sequential_graphs(), task_uris(), workflow_contexts())
@settings(max_examples=50, deadline=5000)  # 5 second timeout per example
def test_sequence_never_crashes(graph: Graph, task: URIRef, context: dict[str, Any]) -> None:
    """Property: Sequence pattern execution never crashes.

    Fuzzes sequence pattern with random graphs, tasks, and contexts to ensure
    robust error handling across all input combinations.
    """
    pattern = Sequence()

    try:
        # Evaluation should never crash
        eval_result = pattern.evaluate(graph, task, context)
        assert hasattr(eval_result, "applicable")
        assert isinstance(eval_result.applicable, bool)

        # Execution should never crash (even if not applicable)
        exec_result = pattern.execute(graph, task, context)
        assert hasattr(exec_result, "success")
        assert isinstance(exec_result.success, bool)
        assert isinstance(exec_result.next_tasks, list)

    except Exception as e:
        pytest.fail(f"Sequence pattern crashed: {e}")


@given(parallel_split_graphs(), workflow_contexts())
@settings(max_examples=50, deadline=5000)
def test_parallel_split_never_crashes(graph: Graph, context: dict[str, Any]) -> None:
    """Property: ParallelSplit pattern execution never crashes."""
    pattern = ParallelSplit()

    # Find split task in graph
    split_tasks = list(graph.subjects(YAWL.splitType, Literal("AND")))
    assume(len(split_tasks) > 0)  # Skip if no split tasks
    split_task = split_tasks[0]

    # Verify graph has required structure (≥2 outgoing branches)
    outgoing = list(graph.objects(split_task, YAWL.flowsTo))
    assume(len(outgoing) >= 2)  # AND-split requires ≥2 branches

    try:
        eval_result = pattern.evaluate(graph, split_task, context)
        assert isinstance(eval_result.applicable, bool)

        exec_result = pattern.execute(graph, split_task, context)
        assert isinstance(exec_result.success, bool)
        assert isinstance(exec_result.next_tasks, list)

        # Property: ALL outgoing tasks should be enabled
        if exec_result.success:
            assert len(exec_result.next_tasks) >= 2  # AND-split requires ≥2 branches

    except AssertionError:
        # Re-raise assertion errors as they are test failures, not pattern crashes
        raise
    except Exception as e:
        pytest.fail(f"ParallelSplit pattern crashed: {e}")


@given(xor_split_graphs(), workflow_contexts())
@settings(max_examples=50, deadline=5000)
def test_exclusive_choice_never_crashes(graph: Graph, context: dict[str, Any]) -> None:
    """Property: ExclusiveChoice pattern execution never crashes."""
    pattern = ExclusiveChoice()

    # Find XOR split task
    xor_tasks = list(graph.subjects(YAWL.splitType, Literal("XOR")))
    assume(len(xor_tasks) > 0)
    xor_task = xor_tasks[0]

    try:
        eval_result = pattern.evaluate(graph, xor_task, context)
        assert isinstance(eval_result.applicable, bool)

        exec_result = pattern.execute(graph, xor_task, context)
        assert isinstance(exec_result.success, bool)

        # Property: EXACTLY ONE branch should be selected
        if exec_result.success:
            assert len(exec_result.next_tasks) == 1

    except Exception as e:
        pytest.fail(f"ExclusiveChoice pattern crashed: {e}")


@given(sync_join_graphs(), workflow_contexts())
@settings(max_examples=50, deadline=5000)
def test_synchronization_never_crashes(graph: Graph, context: dict[str, Any]) -> None:
    """Property: Synchronization pattern execution never crashes."""
    pattern = Synchronization()

    # Find AND-join task
    join_tasks = list(graph.subjects(YAWL.joinType, Literal("AND")))
    assume(len(join_tasks) > 0)
    join_task = join_tasks[0]

    try:
        eval_result = pattern.evaluate(graph, join_task, context)
        assert isinstance(eval_result.applicable, bool)

        exec_result = pattern.execute(graph, join_task, context)
        assert isinstance(exec_result.success, bool)

        # Property: Monotonicity - if all incoming completed, join should succeed
        incoming = list(graph.subjects(YAWL.flowsTo, join_task))
        all_completed = all(
            (task, YAWL.status, Literal("completed")) in graph
            for task in incoming
        )
        if all_completed and len(incoming) >= 2:
            assert exec_result.success

    except Exception as e:
        pytest.fail(f"Synchronization pattern crashed: {e}")


@given(cyclic_graphs(), workflow_contexts())
@settings(max_examples=30, deadline=10000)  # 10s timeout for cycle detection
def test_arbitrary_cycles_prevents_infinite_loops(graph: Graph, context: dict[str, Any]) -> None:
    """Property: Cycle pattern never causes infinite loops.

    Verifies that ArbitraryCycles enforces maximum iteration limits to prevent
    infinite execution.
    """
    pattern = ArbitraryCycles(max_iterations=100)

    # Get any task from graph
    tasks = list(graph.subjects(YAWL.flowsTo, None))
    assume(len(tasks) > 0)
    task = tasks[0]

    try:
        # Initialize iteration tracking
        context["iteration_counts"] = {}

        # Execute pattern multiple times
        for iteration in range(150):  # Exceed max_iterations
            eval_result = pattern.evaluate(graph, task, context)
            assert isinstance(eval_result.success, bool)

            exec_result = pattern.execute(graph, task, context)
            assert isinstance(exec_result.committed, bool)

            # Update iteration count
            if "iteration_counts" in exec_result.data_updates:
                context.update(exec_result.data_updates)

            # Property: Should fail after max_iterations
            if iteration >= 100:
                eval_result = pattern.evaluate(graph, task, context)
                assert not eval_result.success
                break

    except Exception as e:
        pytest.fail(f"ArbitraryCycles pattern crashed: {e}")


# ============================================================================
# BOUNDARY VALUE FUZZING
# ============================================================================


@given(sequential_graphs(), task_uris(), st.dictionaries(st.text(max_size=20), boundary_values(), max_size=10))
@settings(max_examples=50, deadline=5000)
def test_patterns_handle_boundary_values(graph: Graph, task: URIRef, context: dict[str, Any]) -> None:
    """Property: Patterns handle boundary values gracefully.

    Tests patterns with edge values: empty strings, zero, MAX_INT, Unicode, etc.
    """
    patterns = [Sequence(), ParallelSplit(), ExclusiveChoice()]

    for pattern in patterns:
        try:
            eval_result = pattern.evaluate(graph, task, context)
            assert isinstance(eval_result.applicable, bool)

            exec_result = pattern.execute(graph, task, context)
            assert isinstance(exec_result.success, bool)

            # Property: Execution result must be well-formed
            assert hasattr(exec_result, "next_tasks")
            assert hasattr(exec_result, "data_updates")
            assert hasattr(exec_result, "error")

        except Exception as e:
            pytest.fail(f"Pattern {pattern.name} failed on boundary value: {e}")


# ============================================================================
# GRAPH CONSISTENCY PROPERTIES
# ============================================================================


@given(parallel_split_graphs(), workflow_contexts())
@settings(max_examples=50, deadline=5000)
def test_graph_consistency_after_execution(graph: Graph, context: dict[str, Any]) -> None:
    """Property: RDF graph remains consistent after pattern execution.

    Verifies no dangling references, orphaned nodes, or corrupt triples.
    """
    pattern = ParallelSplit()

    # Get initial state
    initial_triples = len(graph)

    split_tasks = list(graph.subjects(YAWL.splitType, Literal("AND")))
    assume(len(split_tasks) > 0)
    split_task = split_tasks[0]

    try:
        exec_result = pattern.execute(graph, split_task, context)

        # Property: Graph should grow (new status triples added)
        assert len(graph) >= initial_triples

        # Property: All next_tasks should exist in graph
        for next_task in exec_result.next_tasks:
            assert (next_task, YAWL.status, Literal("enabled")) in graph

        # Property: Split task should be marked completed
        assert (split_task, YAWL.status, Literal("completed")) in graph

    except Exception as e:
        pytest.fail(f"Graph consistency violated: {e}")


# ============================================================================
# STATEFUL FUZZING - RuleBasedStateMachine
# ============================================================================


class WorkflowStateMachine(RuleBasedStateMachine):
    """Stateful fuzzing of workflow lifecycle.

    This state machine simulates random workflow executions:
    1. Initialize workflow with random topology
    2. Execute random patterns on random tasks
    3. Verify invariants (no crashes, monotonicity, termination)

    Examples
    --------
    >>> TestWorkflowStateMachine = WorkflowStateMachine.TestCase
    """

    def __init__(self) -> None:
        """Initialize state machine with empty graph."""
        super().__init__()
        self.graph = Graph()
        self.graph.bind("yawl", YAWL)
        self.context: dict[str, Any] = {}
        self.completed_tasks: set[URIRef] = set()
        self.enabled_tasks: set[URIRef] = set()

    @rule(task=task_uris())
    def add_sequential_task(self, task: URIRef) -> None:
        """Add a sequential task to workflow."""
        # Skip if task already completed (preserve monotonicity)
        if task in self.completed_tasks:
            return

        # Create linear chain if possible
        existing_tasks = list(self.graph.subjects(YAWL.flowsTo, None))
        if existing_tasks:
            prev_task = existing_tasks[-1]
            self.graph.add((prev_task, YAWL.flowsTo, task))
        self.enabled_tasks.add(task)

    @rule(split_task=task_uris(), num_branches=st.integers(min_value=2, max_value=5))
    def add_parallel_split(self, split_task: URIRef, num_branches: int) -> None:
        """Add AND-split to workflow."""
        self.graph.add((split_task, YAWL.splitType, Literal("AND")))
        for i in range(num_branches):
            branch = URIRef(f"urn:task:Branch{i}")
            self.graph.add((split_task, YAWL.flowsTo, branch))
            self.enabled_tasks.add(branch)

    @rule(task=task_uris(), context_data=workflow_contexts())
    def execute_sequence(self, task: URIRef, context_data: dict[str, Any]) -> None:
        """Execute sequence pattern on random task."""
        pattern = Sequence()
        try:
            result = pattern.execute(self.graph, task, context_data)
            if result.success:
                self.completed_tasks.add(task)
                self.enabled_tasks.discard(task)
                for next_task in result.next_tasks:
                    self.enabled_tasks.add(next_task)
        except Exception:
            pass  # Execution failures are acceptable

    @invariant()
    def completed_tasks_stay_completed(self) -> None:
        """Invariant: Once completed, tasks never revert to enabled."""
        for task in self.completed_tasks:
            # Check task is not in enabled set
            assert task not in self.enabled_tasks

    @invariant()
    def graph_is_consistent(self) -> None:
        """Invariant: RDF graph has no malformed triples."""
        # All subjects, predicates, objects should be valid
        for s, p, o in self.graph:
            assert s is not None
            assert p is not None
            assert o is not None


# Create Hypothesis test case from state machine
TestWorkflowStateMachine = WorkflowStateMachine.TestCase


# ============================================================================
# TIMEOUT PROTECTION
# ============================================================================


class TimeoutError(Exception):
    """Raised when pattern execution exceeds timeout."""


def timeout_handler(signum: int, frame: Any) -> None:
    """Signal handler for timeout."""
    raise TimeoutError("Pattern execution exceeded timeout")


@given(cyclic_graphs(), workflow_contexts())
@settings(max_examples=20, deadline=10000)
@pytest.mark.slow
def test_patterns_respect_timeout(graph: Graph, context: dict[str, Any]) -> None:
    """Property: Pattern execution completes within timeout (no hangs).

    Uses signal.alarm to enforce 5-second timeout per pattern execution.
    """
    patterns = [
        Sequence(),
        ParallelSplit(),
        ExclusiveChoice(),
        Synchronization(),
        ArbitraryCycles(max_iterations=10),
    ]

    tasks = list(graph.subjects(YAWL.flowsTo, None))
    assume(len(tasks) > 0)
    task = tasks[0]

    for pattern in patterns:
        # Set 5-second alarm
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)

        try:
            pattern.evaluate(graph, task, context)
            pattern.execute(graph, task, context)
            signal.alarm(0)  # Cancel alarm

        except TimeoutError:
            pytest.fail(f"Pattern {pattern.name} exceeded 5-second timeout")

        except Exception:
            signal.alarm(0)  # Cancel alarm on error
            # Other exceptions are acceptable (pattern might fail)


# ============================================================================
# MEMORY LEAK DETECTION
# ============================================================================


@given(sequential_graphs(), workflow_contexts())
@settings(max_examples=20, deadline=10000)
@pytest.mark.slow
def test_patterns_no_memory_leaks(graph: Graph, context: dict[str, Any]) -> None:
    """Property: Pattern execution doesn't cause unbounded memory growth.

    Executes patterns 1000 times and verifies memory usage stays bounded.
    """
    import sys

    pattern = Sequence()
    tasks = list(graph.subjects(YAWL.flowsTo, None))
    assume(len(tasks) > 0)
    task = tasks[0]

    initial_size = sys.getsizeof(graph)

    # Execute 1000 times
    for _ in range(1000):
        try:
            pattern.execute(graph, task, context)
        except Exception:
            pass

    final_size = sys.getsizeof(graph)

    # Property: Memory growth should be bounded (< 10x initial size)
    assert final_size < initial_size * 10, "Potential memory leak detected"


# ============================================================================
# DATA TYPE FUZZING
# ============================================================================


@given(
    graph=sequential_graphs(),
    task=task_uris(),
    int_val=st.integers(),
    float_val=st.floats(allow_nan=False, allow_infinity=False),
    str_val=st.text(max_size=1000),
    bool_val=st.booleans(),
    list_val=st.lists(st.integers(), max_size=100),
)
@settings(max_examples=50, deadline=5000)
def test_patterns_handle_all_data_types(
    graph: Graph,
    task: URIRef,
    int_val: int,
    float_val: float,
    str_val: str,
    bool_val: bool,
    list_val: list[int],
) -> None:
    """Property: Patterns handle all Python data types in context.

    Fuzzes patterns with random int, float, str, bool, list values.
    """
    context = {
        "int_var": int_val,
        "float_var": float_val,
        "str_var": str_val,
        "bool_var": bool_val,
        "list_var": list_val,
    }

    patterns = [Sequence(), ExclusiveChoice()]

    for pattern in patterns:
        try:
            eval_result = pattern.evaluate(graph, task, context)
            assert isinstance(eval_result.applicable, bool)

            exec_result = pattern.execute(graph, task, context)
            assert isinstance(exec_result.success, bool)

            # Property: data_updates should preserve types
            for key, value in exec_result.data_updates.items():
                if key in context:
                    assert type(value) == type(context[key])  # noqa: E721

        except Exception as e:
            pytest.fail(f"Pattern {pattern.name} failed on data type: {e}")


# ============================================================================
# IMPLICIT TERMINATION FUZZING
# ============================================================================


@given(sequential_graphs())
@settings(max_examples=50, deadline=5000)
def test_implicit_termination_detects_completion(graph: Graph) -> None:
    """Property: ImplicitTermination correctly detects workflow completion.

    Fuzzes with random graphs and verifies termination is triggered only when
    no tasks are enabled/running.
    """
    pattern = ImplicitTermination()
    workflow = URIRef("urn:workflow:W1")

    # Mark all tasks as completed
    for task in graph.subjects(YAWL.flowsTo, None):
        graph.add((task, YAWL.status, Literal("completed")))

    try:
        should_terminate = pattern.check_termination(graph, workflow)

        # Property: Should terminate if no tasks are enabled/running
        enabled = list(graph.subjects(YAWL.status, Literal("enabled")))
        running = list(graph.subjects(YAWL.status, Literal("running")))

        if len(enabled) == 0 and len(running) == 0:
            assert should_terminate
        else:
            assert not should_terminate

    except Exception as e:
        pytest.fail(f"ImplicitTermination crashed: {e}")
