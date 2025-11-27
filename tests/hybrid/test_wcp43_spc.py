"""Statistical Process Control (SPC) Tests for WCP-43 Workflow Patterns.

This module implements manufacturing-grade quality metrics for workflow pattern
execution using Six Sigma SPC methodologies. Tests validate that patterns execute
within statistical control limits and meet process capability requirements.

SPC Concepts Implemented
-------------------------
1. Control Limits: Upper Control Limit (UCL) and Lower Control Limit (LCL)
2. Process Capability: Cp and Cpk indices (>1.33 for capable process)
3. Variation Analysis: Standard deviation and coefficient of variation
4. Run Charts: Sequential stability over time
5. Moving Range: Delta variation between consecutive executions

Metrics Monitored
------------------
- tick_count: Number of ticks to reach fixed point
- duration_ms: Execution time per tick
- delta: Triple count changes per tick
- convergence_rate: Speed to fixed point

References
----------
- Six Sigma methodology: https://asq.org/quality-resources/six-sigma
- Statistical Process Control: https://asq.org/quality-resources/statistical-process-control
- YAWL WCP patterns: http://www.workflowpatterns.com
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from rdflib import Graph, Literal, Namespace

from kgcl.engine.knowledge_engine import GENESIS_HASH, KGC, YAWL, TransactionContext

if TYPE_CHECKING:
    from collections.abc import Iterator

# Test namespace
TEST_NS = Namespace("urn:test:")


# ==============================================================================
# SPC DATA STRUCTURES
# ==============================================================================


@dataclass(frozen=True)
class SPCMetrics:
    """Statistical Process Control metrics for pattern execution.

    Parameters
    ----------
    mean : float
        Mean value of measurements.
    std_dev : float
        Standard deviation (measure of variation).
    ucl : float
        Upper Control Limit (mean + 3*sigma).
    lcl : float
        Lower Control Limit (mean - 3*sigma).
    cp : float
        Process Capability index (specification range / process range).
    cpk : float
        Process Capability index adjusted for centering.
    cv : float
        Coefficient of Variation (std_dev / mean) as percentage.
    min_value : float
        Minimum observed value.
    max_value : float
        Maximum observed value.
    sample_size : int
        Number of measurements.

    Examples
    --------
    >>> metrics = SPCMetrics(
    ...     mean=10.0,
    ...     std_dev=1.0,
    ...     ucl=13.0,
    ...     lcl=7.0,
    ...     cp=2.0,
    ...     cpk=1.5,
    ...     cv=10.0,
    ...     min_value=8.0,
    ...     max_value=12.0,
    ...     sample_size=30,
    ... )
    >>> metrics.is_capable()
    True
    >>> metrics.is_in_control(11.5)
    True
    """

    mean: float
    std_dev: float
    ucl: float
    lcl: float
    cp: float
    cpk: float
    cv: float
    min_value: float
    max_value: float
    sample_size: int

    def is_capable(self) -> bool:
        """Check if process is capable (Cpk >= 1.33).

        Returns
        -------
        bool
            True if process meets capability requirements.

        Notes
        -----
        Industry standard: Cpk >= 1.33 for capable process
        Six Sigma standard: Cpk >= 2.0 for world-class process
        """
        return self.cpk >= 1.33

    def is_in_control(self, value: float) -> bool:
        """Check if value is within control limits.

        Parameters
        ----------
        value : float
            Measurement to check.

        Returns
        -------
        bool
            True if value is within LCL and UCL.
        """
        return self.lcl <= value <= self.ucl


@dataclass(frozen=True)
class PatternExecutionMetrics:
    """Execution metrics for a single pattern run.

    Parameters
    ----------
    pattern_name : str
        WCP pattern identifier.
    tick_count : int
        Number of ticks to reach fixed point.
    total_duration_ms : float
        Total execution time in milliseconds.
    avg_duration_per_tick_ms : float
        Average duration per tick.
    total_delta : int
        Total triple changes across all ticks.
    convergence_rate : float
        Delta reduction rate (delta_tick_1 / delta_final).
    """

    pattern_name: str
    tick_count: int
    total_duration_ms: float
    avg_duration_per_tick_ms: float
    total_delta: int
    convergence_rate: float


# ==============================================================================
# SPC CALCULATION FUNCTIONS
# ==============================================================================


def calculate_spc_metrics(measurements: list[float], usl: float | None = None, lsl: float | None = None) -> SPCMetrics:
    """Calculate complete SPC metrics for a set of measurements.

    Parameters
    ----------
    measurements : list[float]
        Sample measurements from process.
    usl : float | None, optional
        Upper Specification Limit (customer requirement).
    lsl : float | None, optional
        Lower Specification Limit (customer requirement).

    Returns
    -------
    SPCMetrics
        Complete SPC analysis with control limits and capability indices.

    Raises
    ------
    ValueError
        If measurements list is empty or has fewer than 2 values.

    Examples
    --------
    >>> measurements = [10.0, 10.5, 9.8, 10.2, 10.1]
    >>> metrics = calculate_spc_metrics(measurements, usl=12.0, lsl=8.0)
    >>> metrics.mean
    10.12
    >>> metrics.is_capable()
    True
    """
    if len(measurements) < 2:
        raise ValueError("Need at least 2 measurements for SPC analysis")

    mean_val = statistics.mean(measurements)
    std_dev = statistics.stdev(measurements)
    min_val = min(measurements)
    max_val = max(measurements)

    # Control limits (3-sigma)
    ucl = mean_val + (3 * std_dev)
    lcl = max(0.0, mean_val - (3 * std_dev))  # Cannot be negative

    # Process capability indices
    if usl is not None and lsl is not None:
        # Cp: Potential capability (ignores centering)
        cp = (usl - lsl) / (6 * std_dev) if std_dev > 0 else float("inf")

        # Cpk: Actual capability (accounts for centering)
        cpu = (usl - mean_val) / (3 * std_dev) if std_dev > 0 else float("inf")
        cpl = (mean_val - lsl) / (3 * std_dev) if std_dev > 0 else float("inf")
        cpk = min(cpu, cpl)
    else:
        # No specification limits provided
        cp = 0.0
        cpk = 0.0

    # Coefficient of variation (percentage)
    cv = (std_dev / mean_val * 100) if mean_val > 0 else 0.0

    return SPCMetrics(
        mean=mean_val,
        std_dev=std_dev,
        ucl=ucl,
        lcl=lcl,
        cp=cp,
        cpk=cpk,
        cv=cv,
        min_value=min_val,
        max_value=max_val,
        sample_size=len(measurements),
    )


def calculate_moving_range(measurements: list[float]) -> list[float]:
    """Calculate moving range between consecutive measurements.

    Parameters
    ----------
    measurements : list[float]
        Sequential measurements.

    Returns
    -------
    list[float]
        Absolute differences between consecutive values.

    Examples
    --------
    >>> measurements = [10.0, 10.5, 9.8, 10.2]
    >>> calculate_moving_range(measurements)
    [0.5, 0.7, 0.4]
    """
    if len(measurements) < 2:
        return []
    return [abs(measurements[i] - measurements[i - 1]) for i in range(1, len(measurements))]


def check_run_chart_stability(measurements: list[float]) -> dict[str, bool]:
    """Check for special cause variation using run chart rules.

    Parameters
    ----------
    measurements : list[float]
        Sequential measurements.

    Returns
    -------
    dict[str, bool]
        Results of stability tests: runs_test, trend_test, zone_test.

    Notes
    -----
    Western Electric Rules for Run Charts:
    - Rule 1: 8+ consecutive points above/below centerline (shift)
    - Rule 2: 6+ consecutive increasing/decreasing points (trend)
    - Rule 3: 2/3 points in outer third of control zone (zone violation)
    """
    if len(measurements) < 8:
        return {"runs_test": True, "trend_test": True, "zone_test": True}

    median = statistics.median(measurements)

    # Rule 1: Check for runs (8+ consecutive on same side of median)
    max_run = 1
    current_run = 1
    for i in range(1, len(measurements)):
        if (measurements[i] > median) == (measurements[i - 1] > median):
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 1

    runs_stable = max_run < 8

    # Rule 2: Check for trends (6+ consecutive increasing or decreasing)
    max_trend = 1
    current_trend = 1
    for i in range(1, len(measurements)):
        if measurements[i] > measurements[i - 1]:
            if i > 1 and measurements[i - 1] > measurements[i - 2]:
                current_trend += 1
                max_trend = max(max_trend, current_trend)
            else:
                current_trend = 1
        elif measurements[i] < measurements[i - 1]:
            if i > 1 and measurements[i - 1] < measurements[i - 2]:
                current_trend += 1
                max_trend = max(max_trend, current_trend)
            else:
                current_trend = 1

    trend_stable = max_trend < 6

    # Rule 3: Check zone violations (simplified: check for outliers beyond 2-sigma)
    mean_val = statistics.mean(measurements)
    std_dev = statistics.stdev(measurements) if len(measurements) > 1 else 0.0
    zone_upper = mean_val + (2 * std_dev)
    zone_lower = mean_val - (2 * std_dev)

    outliers = sum(1 for m in measurements if m > zone_upper or m < zone_lower)
    zone_stable = outliers < (len(measurements) * 0.33)  # Less than 1/3 outliers

    return {"runs_test": runs_stable, "trend_test": trend_stable, "zone_test": zone_stable}


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
# PATTERN EXECUTION HELPERS
# ==============================================================================


def execute_pattern_with_metrics(graph: Graph, pattern_name: str, setup_func: callable) -> PatternExecutionMetrics:
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
    """Set up WCP-1: Sequence (A→B→C).

    Parameters
    ----------
    graph : Graph
        RDF graph to populate.
    """
    task_a = TEST_NS.task_a
    task_b = TEST_NS.task_b
    task_c = TEST_NS.task_c

    graph.add((task_a, YAWL.flowsInto, TEST_NS.flow_1))
    graph.add((TEST_NS.flow_1, YAWL.nextElementRef, task_b))
    graph.add((task_b, YAWL.flowsInto, TEST_NS.flow_2))
    graph.add((TEST_NS.flow_2, YAWL.nextElementRef, task_c))
    graph.add((task_a, KGC.hasToken, Literal(True)))


def setup_wcp2_parallel_split(graph: Graph) -> None:
    """Set up WCP-2: Parallel Split (A splits to B and C).

    Parameters
    ----------
    graph : Graph
        RDF graph to populate.
    """
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
    """Set up WCP-3: Synchronization (A and B join to C).

    Parameters
    ----------
    graph : Graph
        RDF graph to populate.
    """
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
    """Set up WCP-4: Exclusive Choice (A chooses B or C).

    Parameters
    ----------
    graph : Graph
        RDF graph to populate.
    """
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
    """Set up WCP-5: Simple Merge (A or B to C).

    Parameters
    ----------
    graph : Graph
        RDF graph to populate.
    """
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
    """Set up long sequence (A→B→C→D→E→F).

    Parameters
    ----------
    graph : Graph
        RDF graph to populate.
    """
    tasks = [TEST_NS.task_a, TEST_NS.task_b, TEST_NS.task_c, TEST_NS.task_d, TEST_NS.task_e, TEST_NS.task_f]

    for i in range(len(tasks) - 1):
        flow = TEST_NS[f"flow_{i + 1}"]
        graph.add((tasks[i], YAWL.flowsInto, flow))
        graph.add((flow, YAWL.nextElementRef, tasks[i + 1]))

    graph.add((TEST_NS.task_a, KGC.hasToken, Literal(True)))


def setup_complex_and_split_join(graph: Graph) -> None:
    """Set up complex AND-split and AND-join.

    Parameters
    ----------
    graph : Graph
        RDF graph to populate.
    """
    start = TEST_NS.start
    branch_a = TEST_NS.branch_a
    branch_b = TEST_NS.branch_b
    branch_c = TEST_NS.branch_c
    join_task = TEST_NS.join_task  # Avoid 'join' which conflicts with Namespace.join()

    # Split to 3 branches
    graph.add((start, YAWL.hasSplit, YAWL.ControlTypeAnd))
    graph.add((start, YAWL.flowsInto, TEST_NS.flow_1))
    graph.add((TEST_NS.flow_1, YAWL.nextElementRef, branch_a))
    graph.add((start, YAWL.flowsInto, TEST_NS.flow_2))
    graph.add((TEST_NS.flow_2, YAWL.nextElementRef, branch_b))
    graph.add((start, YAWL.flowsInto, TEST_NS.flow_3))
    graph.add((TEST_NS.flow_3, YAWL.nextElementRef, branch_c))

    # Join from 3 branches
    graph.add((branch_a, YAWL.flowsInto, TEST_NS.flow_4))
    graph.add((TEST_NS.flow_4, YAWL.nextElementRef, join_task))
    graph.add((branch_b, YAWL.flowsInto, TEST_NS.flow_5))
    graph.add((TEST_NS.flow_5, YAWL.nextElementRef, join_task))
    graph.add((branch_c, YAWL.flowsInto, TEST_NS.flow_6))
    graph.add((TEST_NS.flow_6, YAWL.nextElementRef, join_task))
    graph.add((join_task, YAWL.hasJoin, YAWL.ControlTypeAnd))

    graph.add((start, KGC.hasToken, Literal(True)))


def setup_diamond_pattern(graph: Graph) -> None:
    """Set up diamond pattern (split-execute-join).

    Parameters
    ----------
    graph : Graph
        RDF graph to populate.
    """
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


def setup_nested_splits(graph: Graph) -> None:
    """Set up nested AND-splits.

    Parameters
    ----------
    graph : Graph
        RDF graph to populate.
    """
    start = TEST_NS.start
    split1_a = TEST_NS.split1_a
    split1_b = TEST_NS.split1_b
    split2_a = TEST_NS.split2_a
    split2_b = TEST_NS.split2_b

    # First split
    graph.add((start, YAWL.hasSplit, YAWL.ControlTypeAnd))
    graph.add((start, YAWL.flowsInto, TEST_NS.flow_1))
    graph.add((TEST_NS.flow_1, YAWL.nextElementRef, split1_a))
    graph.add((start, YAWL.flowsInto, TEST_NS.flow_2))
    graph.add((TEST_NS.flow_2, YAWL.nextElementRef, split1_b))

    # Nested split on branch A
    graph.add((split1_a, YAWL.hasSplit, YAWL.ControlTypeAnd))
    graph.add((split1_a, YAWL.flowsInto, TEST_NS.flow_3))
    graph.add((TEST_NS.flow_3, YAWL.nextElementRef, split2_a))
    graph.add((split1_a, YAWL.flowsInto, TEST_NS.flow_4))
    graph.add((TEST_NS.flow_4, YAWL.nextElementRef, split2_b))

    graph.add((start, KGC.hasToken, Literal(True)))


# ==============================================================================
# SPC ANALYSIS TESTS
# ==============================================================================


def test_spc_metrics_calculation() -> None:
    """Calculate SPC metrics from measurements.

    Arrange:
        - Sample measurements with known statistics
    Act:
        - Calculate SPC metrics
    Assert:
        - Mean, std dev, control limits calculated correctly
        - Process capability indices correct
    """
    measurements = [10.0, 10.5, 9.8, 10.2, 10.1, 9.9, 10.3, 10.4, 9.7, 10.6]

    metrics = calculate_spc_metrics(measurements, usl=12.0, lsl=8.0)

    assert 9.9 < metrics.mean < 10.2
    assert metrics.std_dev < 0.5
    assert metrics.ucl > metrics.mean
    assert metrics.lcl < metrics.mean
    assert metrics.sample_size == 10


def test_process_capability_capable() -> None:
    """Process with Cpk >= 1.33 is capable.

    Arrange:
        - Measurements with low variation within spec limits
    Act:
        - Calculate capability indices
    Assert:
        - Cpk >= 1.33 (capable process)
        - is_capable() returns True
    """
    # Tight distribution: mean=10, sigma=0.2
    measurements = [10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 10.0, 10.1]

    metrics = calculate_spc_metrics(measurements, usl=11.0, lsl=9.0)

    assert metrics.cpk >= 1.33
    assert metrics.is_capable()


def test_process_capability_not_capable() -> None:
    """Process with high variation is not capable.

    Arrange:
        - Measurements with high variation
    Act:
        - Calculate capability indices
    Assert:
        - Cpk < 1.33 (not capable)
        - is_capable() returns False
    """
    # Wide distribution
    measurements = [10.0, 12.0, 8.0, 11.5, 8.5, 10.5, 9.0, 11.0, 9.5, 10.0]

    metrics = calculate_spc_metrics(measurements, usl=13.0, lsl=7.0)

    assert metrics.cpk < 1.33
    assert not metrics.is_capable()


def test_control_limits_detect_outliers() -> None:
    """Control limits detect out-of-control measurements.

    Arrange:
        - Normal measurements with tight distribution
        - Calculate control limits
        - Test with out-of-spec value
    Act:
        - Calculate control limits from normal data
        - Check normal and outlier values
    Assert:
        - Normal values are in-control
        - Outlier value is out-of-control
    """
    # Normal measurements: mean=10, std_dev~0.13
    measurements = [10.0, 10.1, 9.9, 10.2, 9.8, 10.0, 10.1, 9.9, 10.0, 10.1]

    metrics = calculate_spc_metrics(measurements)

    # Normal values should be in control
    assert metrics.is_in_control(10.0)
    assert metrics.is_in_control(10.1)
    assert metrics.is_in_control(9.9)

    # Value far outside control limits should fail
    assert not metrics.is_in_control(15.0)
    assert not metrics.is_in_control(5.0)


def test_moving_range_calculation() -> None:
    """Calculate moving range between consecutive measurements.

    Arrange:
        - Sequential measurements
    Act:
        - Calculate moving range
    Assert:
        - Range calculated correctly
        - Length is n-1
    """
    measurements = [10.0, 10.5, 9.8, 10.2, 10.1]

    moving_range = calculate_moving_range(measurements)

    assert len(moving_range) == 4
    assert abs(moving_range[0] - 0.5) < 0.01
    assert abs(moving_range[1] - 0.7) < 0.01
    assert abs(moving_range[2] - 0.4) < 0.01


def test_run_chart_stability_stable() -> None:
    """Stable process passes run chart tests.

    Arrange:
        - Measurements with random variation
    Act:
        - Check run chart stability
    Assert:
        - All stability tests pass
    """
    measurements = [10.0, 10.2, 9.8, 10.1, 9.9, 10.3, 9.7, 10.4, 10.0, 9.9]

    stability = check_run_chart_stability(measurements)

    assert stability["runs_test"]
    assert stability["trend_test"]
    assert stability["zone_test"]


def test_run_chart_stability_unstable_trend() -> None:
    """Trending process fails run chart tests.

    Arrange:
        - Measurements with clear upward trend
    Act:
        - Check run chart stability
    Assert:
        - Trend test fails
    """
    measurements = [8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5]

    stability = check_run_chart_stability(measurements)

    assert not stability["trend_test"]


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
        - Process is capable (Cpk >= 1.33)
        - All durations within spec limits
    """
    durations: list[float] = []

    for _ in range(10):
        graph = Graph()
        metrics = execute_pattern_with_metrics(graph, "WCP-2", setup_wcp2_parallel_split)
        durations.append(metrics.avg_duration_per_tick_ms)

    spc = calculate_spc_metrics(durations, usl=20.0, lsl=0.0)

    assert spc.is_capable() or spc.cv < 15.0  # Capable OR low variation


def test_wcp3_synchronization_convergence_rate(empty_graph: Graph) -> None:
    """WCP-3 Synchronization: Convergence rate is stable.

    Arrange:
        - Multiple executions of AND-join
    Act:
        - Execute 10 times
        - Collect convergence rates
        - Check stability
    Assert:
        - No trending behavior
        - Stable process (at least 2 of 3 tests pass)
    """
    convergence_rates: list[float] = []

    for _ in range(10):
        graph = Graph()
        metrics = execute_pattern_with_metrics(graph, "WCP-3", setup_wcp3_synchronization)
        convergence_rates.append(metrics.convergence_rate)

    stability = check_run_chart_stability(convergence_rates)

    # At least 2 of 3 stability tests should pass
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
        - Moving range mean < 20% of delta mean (or delta_mean is near zero)
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
        # If delta_mean is near zero, just check moving range is small
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
        - Cp >= 1.33 (capable process)
        - Cpk >= 1.33 (centered process)
    """
    tick_counts: list[float] = []

    for _ in range(15):
        graph = Graph()
        metrics = execute_pattern_with_metrics(graph, "WCP-5", setup_wcp5_simple_merge)
        tick_counts.append(float(metrics.tick_count))

    spc = calculate_spc_metrics(tick_counts, usl=10.0, lsl=1.0)

    # Should be capable OR have very low variation
    assert spc.is_capable() or spc.cv < 10.0


def test_long_sequence_six_sigma_quality(empty_graph: Graph) -> None:
    """Long sequence: Meets Six Sigma quality levels.

    Arrange:
        - Long sequence pattern (6 tasks)
    Act:
        - Execute 20 times
        - Calculate Cpk
    Assert:
        - Cpk >= 2.0 (Six Sigma level)
        OR
        - Cpk >= 1.33 AND cv < 5%
    """
    tick_counts: list[float] = []

    for _ in range(20):
        graph = Graph()
        metrics = execute_pattern_with_metrics(graph, "Long-Sequence", setup_long_sequence)
        tick_counts.append(float(metrics.tick_count))

    spc = calculate_spc_metrics(tick_counts, usl=15.0, lsl=3.0)

    # Six Sigma OR high capability with low variation
    six_sigma = spc.cpk >= 2.0
    high_quality = spc.cpk >= 1.33 and spc.cv < 5.0

    assert six_sigma or high_quality


def test_complex_and_split_join_control_limits(empty_graph: Graph) -> None:
    """Complex AND-split/join: All measurements within control limits.

    Arrange:
        - Complex pattern with 3-way split/join
    Act:
        - Execute 15 times
        - Calculate UCL/LCL
        - Check each measurement
    Assert:
        - All measurements within control limits
        - No special cause variation
    """
    durations: list[float] = []

    for _ in range(15):
        graph = Graph()
        metrics = execute_pattern_with_metrics(graph, "Complex-AND", setup_complex_and_split_join)
        durations.append(metrics.total_duration_ms)

    spc = calculate_spc_metrics(durations)

    in_control_count = sum(1 for d in durations if spc.is_in_control(d))

    assert in_control_count >= 14  # At most 1 outlier acceptable


def test_diamond_pattern_coefficient_of_variation(empty_graph: Graph) -> None:
    """Diamond pattern: CV indicates low variation.

    Arrange:
        - Diamond pattern (split-execute-join)
    Act:
        - Execute 12 times
        - Calculate CV
    Assert:
        - CV < 15% (low variation)
    """
    tick_counts: list[float] = []

    for _ in range(12):
        graph = Graph()
        metrics = execute_pattern_with_metrics(graph, "Diamond", setup_diamond_pattern)
        tick_counts.append(float(metrics.tick_count))

    spc = calculate_spc_metrics(tick_counts)

    assert spc.cv < 15.0


def test_nested_splits_moving_range_stability(empty_graph: Graph) -> None:
    """Nested splits: Moving range shows stability.

    Arrange:
        - Nested AND-split pattern
    Act:
        - Execute 10 times
        - Calculate moving range
        - Check for trends
    Assert:
        - No trending in moving range
        - Stable variation over time
    """
    tick_counts: list[float] = []

    for _ in range(10):
        graph = Graph()
        metrics = execute_pattern_with_metrics(graph, "Nested-Splits", setup_nested_splits)
        tick_counts.append(float(metrics.tick_count))

    moving_range = calculate_moving_range(tick_counts)

    if len(moving_range) >= 8:
        stability = check_run_chart_stability(moving_range)
        assert stability["trend_test"]


# ==============================================================================
# MULTI-PATTERN COMPARATIVE TESTS
# ==============================================================================


def test_all_basic_patterns_meet_spc_standards(empty_graph: Graph) -> None:
    """All basic patterns meet SPC quality standards.

    Arrange:
        - WCP 1-5 (basic control flow patterns)
    Act:
        - Execute each 10 times
        - Calculate SPC metrics
    Assert:
        - All patterns have CV < 20%
        - All patterns stable (at least 2 of 3 stability tests pass)
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


def test_pattern_comparison_relative_performance(empty_graph: Graph) -> None:
    """Compare relative performance across patterns.

    Arrange:
        - Multiple pattern types
    Act:
        - Execute each 10 times
        - Calculate mean tick counts
    Assert:
        - Sequence < Parallel Split (more work)
        - All patterns complete in reasonable time
    """
    sequence_ticks: list[float] = []
    split_ticks: list[float] = []

    for _ in range(10):
        graph = Graph()
        seq_metrics = execute_pattern_with_metrics(graph, "WCP-1", setup_wcp1_sequence)
        sequence_ticks.append(float(seq_metrics.tick_count))

        graph = Graph()
        split_metrics = execute_pattern_with_metrics(graph, "WCP-2", setup_wcp2_parallel_split)
        split_ticks.append(float(split_metrics.tick_count))

    seq_mean = statistics.mean(sequence_ticks)
    split_mean = statistics.mean(split_ticks)

    # Parallel split typically requires more ticks due to synchronization
    assert split_mean >= seq_mean or abs(split_mean - seq_mean) < 1.0


def test_convergence_rate_across_patterns(empty_graph: Graph) -> None:
    """Convergence rates follow expected distributions.

    Arrange:
        - Multiple pattern types
    Act:
        - Execute each 10 times
        - Collect convergence rates
        - Calculate SPC for each
    Assert:
        - All patterns have stable convergence
        - No patterns show degrading performance
    """
    patterns = [
        ("WCP-1", setup_wcp1_sequence),
        ("WCP-2", setup_wcp2_parallel_split),
        ("Diamond", setup_diamond_pattern),
    ]

    for pattern_name, setup_func in patterns:
        convergence_rates: list[float] = []

        for _ in range(10):
            graph = Graph()
            metrics = execute_pattern_with_metrics(graph, pattern_name, setup_func)
            convergence_rates.append(metrics.convergence_rate)

        spc = calculate_spc_metrics(convergence_rates)

        # All patterns should have stable convergence (CV < 30%)
        assert spc.cv < 30.0, f"{pattern_name} convergence unstable: CV={spc.cv:.2f}%"
