"""WCP workflow pattern SPC validation tests.

This module tests Statistical Process Control metrics for YAWL Workflow
Control Patterns (WCP) to ensure manufacturing-grade quality:
- WCP-1: Sequence
- WCP-2: Parallel Split
- WCP-3: Synchronization
- WCP-4: Exclusive Choice
- WCP-5: Simple Merge

All patterns must meet SPC standards: Cpk >= 1.33, CV < 20%, stable run charts.
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

import pytest
from rdflib import Graph, Literal, Namespace

from kgcl.engine.knowledge_engine import KGC, YAWL
from tests.hybrid.lss.spc.metrics import (
    PatternExecutionMetrics,
    calculate_moving_range,
    calculate_spc_metrics,
    check_run_chart_stability,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# Test namespace
TEST_NS = Namespace("urn:test:")


# ==============================================================================
# TEST FIXTURES
# ==============================================================================


@pytest.fixture
def empty_graph() -> Graph:
    """Create empty RDF graph.

    Returns
    -------
    Graph
        Empty RDF graph for testing.
    """
    return Graph()


# ==============================================================================
# PATTERN EXECUTION HELPER
# ==============================================================================


def execute_pattern_with_metrics(
    graph: Graph, pattern_name: str, setup_func: Callable[[Graph], None]
) -> PatternExecutionMetrics:
    """Execute a workflow pattern and collect metrics.

    Parameters
    ----------
    graph : Graph
        RDF graph for workflow execution.
    pattern_name : str
        Pattern identifier for reporting.
    setup_func : callable
        Function to set up pattern topology and initial state.

    Returns
    -------
    PatternExecutionMetrics
        Execution metrics including timing and convergence data.
    """
    # Import here to avoid circular dependency
    from kgcl.hybrid.hybrid_engine import HybridEngine

    # Setup pattern
    setup_func(graph)

    # Create engine (HybridEngine only takes store_path, not graph + ontology)
    # Use in-memory store
    engine = HybridEngine(store_path=None)

    # Load graph data as Turtle
    turtle_data = graph.serialize(format="turtle")
    engine.load_data(turtle_data)

    # Execute until fixed point
    results = engine.run_to_completion(max_ticks=100)

    tick_count = len(results)
    total_delta = sum(r.delta for r in results)
    total_duration_ms = sum(r.duration_ms for r in results)

    # Calculate metrics
    avg_duration = total_duration_ms / tick_count if tick_count > 0 else 0.0
    convergence = float(total_delta) / tick_count if tick_count > 0 else 0.0

    return PatternExecutionMetrics(
        pattern_name=pattern_name,
        tick_count=tick_count,
        total_duration_ms=total_duration_ms,
        avg_duration_per_tick_ms=avg_duration,
        total_delta=total_delta,
        convergence_rate=convergence,
    )


# ==============================================================================
# PATTERN SETUP FUNCTIONS
# ==============================================================================


def setup_wcp1_sequence(graph: Graph) -> None:
    """Set up WCP-1: Sequence (A→B→C)."""
    task_a = TEST_NS.task_a
    task_b = TEST_NS.task_b
    task_c = TEST_NS.task_c

    graph.add((task_a, YAWL.flowsInto, TEST_NS.flow_1))
    graph.add((TEST_NS.flow_1, YAWL.nextElementRef, task_b))
    graph.add((task_b, YAWL.flowsInto, TEST_NS.flow_2))
    graph.add((TEST_NS.flow_2, YAWL.nextElementRef, task_c))
    graph.add((task_a, KGC.hasToken, Literal(True)))


def setup_wcp2_parallel_split(graph: Graph) -> None:
    """Set up WCP-2: Parallel Split (A splits to B and C)."""
    task_a = TEST_NS.task_a
    task_b = TEST_NS.task_b
    task_c = TEST_NS.task_c

    graph.add((task_a, YAWL.hasSplit, YAWL.ControlTypeAnd))
    graph.add((task_a, YAWL.flowsInto, TEST_NS.flow_1))
    graph.add((TEST_NS.flow_1, YAWL.nextElementRef, task_b))
    graph.add((task_a, YAWL.flowsInto, TEST_NS.flow_2))
    graph.add((TEST_NS.flow_2, YAWL.nextElementRef, task_c))
    graph.add((task_a, KGC.hasToken, Literal(True)))


def setup_wcp3_synchronization(graph: Graph) -> None:
    """Set up WCP-3: Synchronization (A and B join to C)."""
    task_a = TEST_NS.task_a
    task_b = TEST_NS.task_b
    task_c = TEST_NS.task_c

    graph.add((task_a, YAWL.flowsInto, TEST_NS.flow_1))
    graph.add((TEST_NS.flow_1, YAWL.nextElementRef, task_c))
    graph.add((task_b, YAWL.flowsInto, TEST_NS.flow_2))
    graph.add((TEST_NS.flow_2, YAWL.nextElementRef, task_c))
    graph.add((task_c, YAWL.hasJoin, YAWL.ControlTypeAnd))
    graph.add((task_a, KGC.hasToken, Literal(True)))
    graph.add((task_b, KGC.hasToken, Literal(True)))


def setup_wcp4_exclusive_choice(graph: Graph) -> None:
    """Set up WCP-4: Exclusive Choice (A chooses B or C)."""
    task_a = TEST_NS.task_a
    task_b = TEST_NS.task_b
    task_c = TEST_NS.task_c

    graph.add((task_a, YAWL.hasSplit, YAWL.ControlTypeXor))
    flow_b = TEST_NS.flow_b
    pred_b = TEST_NS.pred_b
    graph.add((task_a, YAWL.flowsInto, flow_b))
    graph.add((flow_b, YAWL.nextElementRef, task_b))
    graph.add((flow_b, YAWL.hasPredicate, pred_b))
    graph.add((pred_b, YAWL.query, Literal("data['x'] > 5")))

    flow_c = TEST_NS.flow_c
    graph.add((task_a, YAWL.flowsInto, flow_c))
    graph.add((flow_c, YAWL.nextElementRef, task_c))
    graph.add((flow_c, YAWL.isDefaultFlow, Literal(True)))
    graph.add((task_a, KGC.hasToken, Literal(True)))


def setup_wcp5_simple_merge(graph: Graph) -> None:
    """Set up WCP-5: Simple Merge (A or B to C)."""
    task_a = TEST_NS.task_a
    task_b = TEST_NS.task_b
    task_c = TEST_NS.task_c

    graph.add((task_c, YAWL.hasJoin, YAWL.ControlTypeXor))
    graph.add((task_a, YAWL.flowsInto, TEST_NS.flow_1))
    graph.add((TEST_NS.flow_1, YAWL.nextElementRef, task_c))
    graph.add((task_b, YAWL.flowsInto, TEST_NS.flow_2))
    graph.add((TEST_NS.flow_2, YAWL.nextElementRef, task_c))
    graph.add((task_a, KGC.hasToken, Literal(True)))


def setup_long_sequence(graph: Graph) -> None:
    """Set up long sequence (A→B→C→D→E→F)."""
    tasks = [TEST_NS.task_a, TEST_NS.task_b, TEST_NS.task_c, TEST_NS.task_d, TEST_NS.task_e, TEST_NS.task_f]

    for i in range(len(tasks) - 1):
        flow = TEST_NS[f"flow_{i + 1}"]
        graph.add((tasks[i], YAWL.flowsInto, flow))
        graph.add((flow, YAWL.nextElementRef, tasks[i + 1]))

    graph.add((TEST_NS.task_a, KGC.hasToken, Literal(True)))


def setup_diamond_pattern(graph: Graph) -> None:
    """Set up diamond pattern (split-execute-join)."""
    start = TEST_NS.start
    left = TEST_NS.left
    right = TEST_NS.right
    end = TEST_NS.end

    graph.add((start, YAWL.hasSplit, YAWL.ControlTypeAnd))
    graph.add((start, YAWL.flowsInto, TEST_NS.flow_1))
    graph.add((TEST_NS.flow_1, YAWL.nextElementRef, left))
    graph.add((start, YAWL.flowsInto, TEST_NS.flow_2))
    graph.add((TEST_NS.flow_2, YAWL.nextElementRef, right))

    graph.add((left, YAWL.flowsInto, TEST_NS.flow_3))
    graph.add((TEST_NS.flow_3, YAWL.nextElementRef, end))
    graph.add((right, YAWL.flowsInto, TEST_NS.flow_4))
    graph.add((TEST_NS.flow_4, YAWL.nextElementRef, end))
    graph.add((end, YAWL.hasJoin, YAWL.ControlTypeAnd))

    graph.add((start, KGC.hasToken, Literal(True)))


# ==============================================================================
# WCP PATTERN SPC TESTS
# ==============================================================================


def test_wcp1_sequence_tick_count_variation(empty_graph: Graph) -> None:
    """WCP-1 Sequence: Tick count has low variation across runs.

    Arrange:
        - Multiple executions of sequence pattern
    Act:
        - Execute pattern 10 times
        - Collect tick counts
        - Calculate SPC metrics
    Assert:
        - Coefficient of variation < 10%
        - All runs within control limits
    """
    tick_counts: list[float] = []

    for _ in range(10):
        graph = Graph()
        metrics = execute_pattern_with_metrics(graph, "WCP-1", setup_wcp1_sequence)
        tick_counts.append(float(metrics.tick_count))

    spc = calculate_spc_metrics(tick_counts)

    assert spc.cv < 10.0  # Less than 10% variation
    assert all(spc.is_in_control(tc) for tc in tick_counts)


def test_wcp2_parallel_split_consistency(empty_graph: Graph) -> None:
    """WCP-2 Parallel Split: Execution time is consistent.

    Arrange:
        - Multiple executions of parallel split
    Act:
        - Execute 10 times
        - Collect duration metrics
        - Calculate SPC
    Assert:
        - Process is capable (Cpk >= 1.33) OR low variation
    """
    durations: list[float] = []

    for _ in range(10):
        graph = Graph()
        metrics = execute_pattern_with_metrics(graph, "WCP-2", setup_wcp2_parallel_split)
        durations.append(metrics.avg_duration_per_tick_ms)

    spc = calculate_spc_metrics(durations, usl=20.0, lsl=0.0)

    assert spc.is_capable() or spc.cv < 15.0


def test_wcp3_synchronization_convergence_rate(empty_graph: Graph) -> None:
    """WCP-3 Synchronization: Convergence rate is stable.

    Arrange:
        - Multiple executions of AND-join
    Act:
        - Execute 10 times
        - Collect convergence rates
        - Check stability
    Assert:
        - At least 2 of 3 stability tests pass
    """
    convergence_rates: list[float] = []

    for _ in range(10):
        graph = Graph()
        metrics = execute_pattern_with_metrics(graph, "WCP-3", setup_wcp3_synchronization)
        convergence_rates.append(metrics.convergence_rate)

    stability = check_run_chart_stability(convergence_rates)

    passes = sum(stability.values())
    assert passes >= 2, f"Only {passes}/3 stability tests passed: {stability}"


def test_wcp4_exclusive_choice_delta_variation(empty_graph: Graph) -> None:
    """WCP-4 Exclusive Choice: Delta has acceptable variation.

    Arrange:
        - Multiple XOR-split executions
    Act:
        - Execute 10 times
        - Collect total delta
        - Calculate moving range
    Assert:
        - Moving range mean < 20% of delta mean
    """
    deltas: list[float] = []

    for _ in range(10):
        graph = Graph()
        metrics = execute_pattern_with_metrics(graph, "WCP-4", setup_wcp4_exclusive_choice)
        deltas.append(float(metrics.total_delta))

    moving_range = calculate_moving_range(deltas)

    if len(moving_range) > 0:
        mr_mean = statistics.mean(moving_range)
        delta_mean = statistics.mean(deltas)
        if delta_mean < 0.1:
            assert mr_mean < 1.0
        else:
            assert mr_mean < (delta_mean * 0.2)


def test_wcp5_simple_merge_process_capability(empty_graph: Graph) -> None:
    """WCP-5 Simple Merge: Process meets capability requirements.

    Arrange:
        - Multiple simple merge executions
    Act:
        - Execute 15 times
        - Calculate Cp and Cpk
    Assert:
        - Process is capable OR has very low variation
    """
    tick_counts: list[float] = []

    for _ in range(15):
        graph = Graph()
        metrics = execute_pattern_with_metrics(graph, "WCP-5", setup_wcp5_simple_merge)
        tick_counts.append(float(metrics.tick_count))

    spc = calculate_spc_metrics(tick_counts, usl=10.0, lsl=1.0)

    assert spc.is_capable() or spc.cv < 10.0


def test_all_basic_patterns_meet_spc_standards(empty_graph: Graph) -> None:
    """All basic patterns meet SPC quality standards.

    Arrange:
        - WCP 1-5 (basic control flow patterns)
    Act:
        - Execute each 10 times
        - Calculate SPC metrics
    Assert:
        - All patterns have CV < 20%
        - All patterns stable (at least 2 of 3 tests pass)
    """
    patterns = [
        ("WCP-1", setup_wcp1_sequence),
        ("WCP-2", setup_wcp2_parallel_split),
        ("WCP-3", setup_wcp3_synchronization),
        ("WCP-4", setup_wcp4_exclusive_choice),
        ("WCP-5", setup_wcp5_simple_merge),
    ]

    for pattern_name, setup_func in patterns:
        tick_counts: list[float] = []

        for _ in range(10):
            graph = Graph()
            metrics = execute_pattern_with_metrics(graph, pattern_name, setup_func)
            tick_counts.append(float(metrics.tick_count))

        spc = calculate_spc_metrics(tick_counts)

        assert spc.cv < 20.0, f"{pattern_name} has CV={spc.cv:.2f}% (>20%)"

        stability = check_run_chart_stability(tick_counts)
        passes = sum(stability.values())
        assert passes >= 2, f"{pattern_name} only passed {passes}/3 stability tests: {stability}"
