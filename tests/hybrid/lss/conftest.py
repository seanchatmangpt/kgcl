"""Shared fixtures and utilities for LSS YAWL engine tests.

This module provides:
- pytest fixtures for engine setup and workflow execution
- Topology generation utilities with comprehensive doctests
- Statistical analysis functions for performance validation
- Shared dataclasses for metrics tracking

All functions include doctests to validate correctness at development time.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

# ============================================================================
# Dataclasses with Doctest Examples
# ============================================================================


@dataclass(frozen=True)
class StatisticsResult:
    """Statistical metrics for performance analysis.

    Attributes
    ----------
    mean : float
        Arithmetic mean of values
    std_dev : float
        Standard deviation (population)
    min_value : float
        Minimum value
    max_value : float
        Maximum value
    cv_percent : float
        Coefficient of variation as percentage (std_dev/mean * 100)

    Examples
    --------
    >>> result = StatisticsResult(mean=50.0, std_dev=5.0, min_value=40.0, max_value=60.0, cv_percent=10.0)
    >>> result.mean
    50.0
    >>> result.cv_percent
    10.0

    >>> # Zero standard deviation case
    >>> perfect = StatisticsResult(mean=100.0, std_dev=0.0, min_value=100.0, max_value=100.0, cv_percent=0.0)
    >>> perfect.std_dev
    0.0
    >>> perfect.cv_percent
    0.0
    """

    mean: float
    std_dev: float
    min_value: float
    max_value: float
    cv_percent: float


# ============================================================================
# Statistical Analysis Functions
# ============================================================================


def calculate_statistics(values: list[float]) -> StatisticsResult:
    """Calculate statistical metrics for a list of values.

    Parameters
    ----------
    values : list[float]
        List of numeric values to analyze

    Returns
    -------
    StatisticsResult
        Statistical metrics including mean, std_dev, min, max, cv_percent

    Raises
    ------
    ValueError
        If values list is empty

    Examples
    --------
    >>> # Basic statistics
    >>> stats = calculate_statistics([10.0, 20.0, 30.0, 40.0, 50.0])
    >>> stats.mean
    30.0
    >>> stats.min_value
    10.0
    >>> stats.max_value
    50.0
    >>> abs(stats.std_dev - 14.142) < 0.01  # ~sqrt(200)
    True

    >>> # Single value (zero variance)
    >>> stats = calculate_statistics([42.0])
    >>> stats.mean
    42.0
    >>> stats.std_dev
    0.0
    >>> stats.cv_percent
    0.0

    >>> # Two values
    >>> stats = calculate_statistics([10.0, 20.0])
    >>> stats.mean
    15.0
    >>> stats.std_dev
    5.0
    >>> abs(stats.cv_percent - 33.333) < 0.01
    True

    >>> # Empty list raises
    >>> calculate_statistics([])
    Traceback (most recent call last):
        ...
    ValueError: Cannot calculate statistics on empty list
    """
    if not values:
        raise ValueError("Cannot calculate statistics on empty list")

    n = len(values)
    mean_val = sum(values) / n
    min_val = min(values)
    max_val = max(values)

    # Population standard deviation
    if n == 1:
        std_dev = 0.0
    else:
        variance = sum((x - mean_val) ** 2 for x in values) / n
        std_dev = math.sqrt(variance)

    # Coefficient of variation
    cv_percent = (std_dev / mean_val * 100.0) if mean_val != 0.0 else 0.0

    return StatisticsResult(mean=mean_val, std_dev=std_dev, min_value=min_val, max_value=max_val, cv_percent=cv_percent)


def calculate_percentile(values: list[float], percentile: float) -> float:
    """Calculate the specified percentile of a list of values.

    Uses linear interpolation between closest ranks.

    Parameters
    ----------
    values : list[float]
        List of numeric values
    percentile : float
        Percentile to calculate (0-100)

    Returns
    -------
    float
        The percentile value

    Raises
    ------
    ValueError
        If values is empty or percentile is out of range

    Examples
    --------
    >>> # Basic percentile
    >>> values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    >>> calculate_percentile(values, 50.0)  # Median
    5.5
    >>> calculate_percentile(values, 90.0)
    9.1
    >>> calculate_percentile(values, 99.0)
    9.91

    >>> # Edge cases
    >>> calculate_percentile([42.0], 50.0)
    42.0
    >>> calculate_percentile([1.0, 2.0], 0.0)
    1.0
    >>> calculate_percentile([1.0, 2.0], 100.0)
    2.0

    >>> # Invalid percentile
    >>> calculate_percentile([1.0, 2.0], 101.0)
    Traceback (most recent call last):
        ...
    ValueError: Percentile must be between 0 and 100
    """
    if not values:
        raise ValueError("Cannot calculate percentile on empty list")
    if not 0.0 <= percentile <= 100.0:
        raise ValueError("Percentile must be between 0 and 100")

    sorted_values = sorted(values)
    n = len(sorted_values)

    if n == 1:
        return sorted_values[0]

    # Linear interpolation
    k = (n - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)

    if f == c:
        return sorted_values[int(k)]

    d0 = sorted_values[int(f)] * (c - k)
    d1 = sorted_values[int(c)] * (k - f)
    return d0 + d1


# ============================================================================
# Topology Generation Functions
# ============================================================================


def create_sequence_topology(n_tasks: int) -> str:
    """Create a sequential workflow topology with N tasks.

    Generates a YAWL workflow where tasks execute in strict sequence:
    task_1 -> task_2 -> ... -> task_N

    Parameters
    ----------
    n_tasks : int
        Number of sequential tasks (must be >= 1)

    Returns
    -------
    str
        JSON string representing the workflow topology

    Raises
    ------
    ValueError
        If n_tasks < 1

    Examples
    --------
    >>> # Single task
    >>> topology = create_sequence_topology(1)
    >>> data = json.loads(topology)
    >>> data["workflow"]["id"]
    'sequence_1'
    >>> len(data["tasks"])
    1
    >>> data["tasks"][0]["id"]
    'task_1'

    >>> # Three tasks in sequence
    >>> topology = create_sequence_topology(3)
    >>> data = json.loads(topology)
    >>> data["workflow"]["id"]
    'sequence_3'
    >>> len(data["tasks"])
    3
    >>> data["tasks"][0]["id"]
    'task_1'
    >>> data["tasks"][1]["id"]
    'task_2'
    >>> data["tasks"][2]["id"]
    'task_3'
    >>> # Check sequencing
    >>> data["tasks"][0]["successors"]
    ['task_2']
    >>> data["tasks"][1]["successors"]
    ['task_3']
    >>> data["tasks"][2]["successors"]
    []

    >>> # Invalid input
    >>> create_sequence_topology(0)
    Traceback (most recent call last):
        ...
    ValueError: n_tasks must be >= 1
    """
    if n_tasks < 1:
        raise ValueError("n_tasks must be >= 1")

    tasks = []
    for i in range(1, n_tasks + 1):
        task_id = f"task_{i}"
        successors = [f"task_{i + 1}"] if i < n_tasks else []
        tasks.append({"id": task_id, "type": "atomic", "successors": successors})

    topology = {
        "workflow": {"id": f"sequence_{n_tasks}", "name": f"Sequential Workflow ({n_tasks} tasks)"},
        "tasks": tasks,
    }

    return json.dumps(topology, indent=2)


def create_parallel_split_topology(n_branches: int) -> str:
    """Create an AND-split workflow topology with N parallel branches.

    Generates a YAWL workflow with one split task that launches N parallel tasks:
    split_task -> (branch_1, branch_2, ..., branch_N)

    Parameters
    ----------
    n_branches : int
        Number of parallel branches (must be >= 2)

    Returns
    -------
    str
        JSON string representing the workflow topology

    Raises
    ------
    ValueError
        If n_branches < 2

    Examples
    --------
    >>> # Two parallel branches
    >>> topology = create_parallel_split_topology(2)
    >>> data = json.loads(topology)
    >>> data["workflow"]["id"]
    'parallel_split_2'
    >>> len(data["tasks"])
    3
    >>> data["tasks"][0]["id"]
    'split_task'
    >>> data["tasks"][0]["split_type"]
    'AND'
    >>> set(data["tasks"][0]["successors"]) == {"branch_1", "branch_2"}
    True

    >>> # Five parallel branches
    >>> topology = create_parallel_split_topology(5)
    >>> data = json.loads(topology)
    >>> len(data["tasks"])
    6
    >>> data["tasks"][0]["successors"]
    ['branch_1', 'branch_2', 'branch_3', 'branch_4', 'branch_5']
    >>> # All branches are atomic
    >>> all(t["type"] == "atomic" for t in data["tasks"][1:])
    True

    >>> # Invalid input
    >>> create_parallel_split_topology(1)
    Traceback (most recent call last):
        ...
    ValueError: n_branches must be >= 2 for parallel split
    """
    if n_branches < 2:
        raise ValueError("n_branches must be >= 2 for parallel split")

    branch_ids = [f"branch_{i}" for i in range(1, n_branches + 1)]

    tasks = [{"id": "split_task", "type": "composite", "split_type": "AND", "successors": branch_ids}]

    for branch_id in branch_ids:
        tasks.append({"id": branch_id, "type": "atomic", "successors": []})

    topology = {
        "workflow": {"id": f"parallel_split_{n_branches}", "name": f"Parallel Split Workflow ({n_branches} branches)"},
        "tasks": tasks,
    }

    return json.dumps(topology, indent=2)


def create_and_join_topology(n_predecessors: int) -> str:
    """Create an AND-join workflow topology with N predecessors.

    Generates a YAWL workflow where N parallel tasks converge to one join task:
    (pred_1, pred_2, ..., pred_N) -> join_task

    Parameters
    ----------
    n_predecessors : int
        Number of predecessor tasks (must be >= 2)

    Returns
    -------
    str
        JSON string representing the workflow topology

    Raises
    ------
    ValueError
        If n_predecessors < 2

    Examples
    --------
    >>> # Two predecessors join
    >>> topology = create_and_join_topology(2)
    >>> data = json.loads(topology)
    >>> data["workflow"]["id"]
    'and_join_2'
    >>> len(data["tasks"])
    3
    >>> data["tasks"][2]["id"]
    'join_task'
    >>> data["tasks"][2]["join_type"]
    'AND'
    >>> # Check predecessors point to join
    >>> data["tasks"][0]["successors"]
    ['join_task']
    >>> data["tasks"][1]["successors"]
    ['join_task']

    >>> # Four predecessors join
    >>> topology = create_and_join_topology(4)
    >>> data = json.loads(topology)
    >>> len(data["tasks"])
    5
    >>> # All predecessors point to join
    >>> all(t["successors"] == ["join_task"] for t in data["tasks"][:4])
    True
    >>> data["tasks"][4]["join_type"]
    'AND'

    >>> # Invalid input
    >>> create_and_join_topology(1)
    Traceback (most recent call last):
        ...
    ValueError: n_predecessors must be >= 2 for AND-join
    """
    if n_predecessors < 2:
        raise ValueError("n_predecessors must be >= 2 for AND-join")

    tasks = []
    for i in range(1, n_predecessors + 1):
        tasks.append({"id": f"pred_{i}", "type": "atomic", "successors": ["join_task"]})

    tasks.append({"id": "join_task", "type": "composite", "join_type": "AND", "successors": []})

    topology = {
        "workflow": {"id": f"and_join_{n_predecessors}", "name": f"AND-Join Workflow ({n_predecessors} predecessors)"},
        "tasks": tasks,
    }

    return json.dumps(topology, indent=2)


def create_diamond_topology(n_parallel_tasks: int) -> str:
    """Create a diamond workflow: split -> N parallel -> join.

    Generates a YAWL workflow with AND-split, N parallel branches, and AND-join:
    split_task -> (task_1, task_2, ..., task_N) -> join_task

    Parameters
    ----------
    n_parallel_tasks : int
        Number of parallel tasks in the middle (must be >= 2)

    Returns
    -------
    str
        JSON string representing the workflow topology

    Raises
    ------
    ValueError
        If n_parallel_tasks < 2

    Examples
    --------
    >>> # Simple diamond (2 parallel)
    >>> topology = create_diamond_topology(2)
    >>> data = json.loads(topology)
    >>> data["workflow"]["id"]
    'diamond_2'
    >>> len(data["tasks"])
    4
    >>> data["tasks"][0]["id"]
    'split_task'
    >>> data["tasks"][0]["split_type"]
    'AND'
    >>> data["tasks"][3]["id"]
    'join_task'
    >>> data["tasks"][3]["join_type"]
    'AND'

    >>> # Complex diamond (5 parallel)
    >>> topology = create_diamond_topology(5)
    >>> data = json.loads(topology)
    >>> len(data["tasks"])
    7
    >>> # Split fans out to all parallel tasks
    >>> set(data["tasks"][0]["successors"]) == {"parallel_1", "parallel_2", "parallel_3", "parallel_4", "parallel_5"}
    True
    >>> # All parallel tasks point to join
    >>> all(t["successors"] == ["join_task"] for t in data["tasks"][1:6])
    True

    >>> # Invalid input
    >>> create_diamond_topology(1)
    Traceback (most recent call last):
        ...
    ValueError: n_parallel_tasks must be >= 2 for diamond pattern
    """
    if n_parallel_tasks < 2:
        raise ValueError("n_parallel_tasks must be >= 2 for diamond pattern")

    parallel_ids = [f"parallel_{i}" for i in range(1, n_parallel_tasks + 1)]

    tasks = [{"id": "split_task", "type": "composite", "split_type": "AND", "successors": parallel_ids}]

    for parallel_id in parallel_ids:
        tasks.append({"id": parallel_id, "type": "atomic", "successors": ["join_task"]})

    tasks.append({"id": "join_task", "type": "composite", "join_type": "AND", "successors": []})

    topology = {
        "workflow": {
            "id": f"diamond_{n_parallel_tasks}",
            "name": f"Diamond Workflow ({n_parallel_tasks} parallel tasks)",
        },
        "tasks": tasks,
    }

    return json.dumps(topology, indent=2)


# ============================================================================
# Pytest Fixtures
# ============================================================================


@pytest.fixture
def engine() -> Any:
    """Provide a YAWL execution engine instance.

    Returns
    -------
    Any
        YAWL engine instance (mocked for now, real implementation TBD)

    Notes
    -----
    This fixture will be updated to return the actual YAWL engine
    once the implementation is complete.
    """

    # TODO: Return actual YAWL engine instance
    # For now, return a mock object
    class MockEngine:
        def load_topology(self, topology_json: str) -> None:
            """Load workflow topology."""
            self.topology = json.loads(topology_json)

        def execute(self, workflow_id: str) -> dict[str, Any]:
            """Execute workflow and return results."""
            return {"workflow_id": workflow_id, "status": "completed", "execution_time_ms": 42.0}

    return MockEngine()


@pytest.fixture
def load_and_run(engine: Any) -> Any:
    """Fixture that loads topology and executes workflow.

    Parameters
    ----------
    engine : Any
        YAWL engine instance from engine fixture

    Returns
    -------
    callable
        Function that takes topology JSON and returns execution results

    Examples
    --------
    This fixture is used in tests like:

    >>> # In a test function
    >>> def test_sequence_execution(load_and_run):
    ...     topology = create_sequence_topology(3)
    ...     result = load_and_run(topology)
    ...     assert result["status"] == "completed"
    """

    def _load_and_run(topology_json: str) -> dict[str, Any]:
        engine.load_topology(topology_json)
        topology_data = json.loads(topology_json)
        workflow_id = topology_data["workflow"]["id"]
        return engine.execute(workflow_id)

    return _load_and_run


# ============================================================================
# Doctest Runner
# ============================================================================


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
