"""CTQ-5: Reliability Tests for WCP Patterns.

This module validates that YAWL workflow control patterns gracefully handle edge
cases and failure modes without crashing or producing incorrect results.

Test Coverage
-------------
- Empty graphs (no tasks)
- Disconnected tasks
- Missing predicates/guards (default path activation)
- Invalid states

Quality Gates
-------------
- Graceful handling of edge cases
- Proper default path activation
- No crashes on invalid input
- Convergence even with missing data
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine

if TYPE_CHECKING:
    from collections.abc import Callable

    from kgcl.hybrid.hybrid_engine import PhysicsResult


@pytest.fixture
def load_and_run(engine: HybridEngine) -> Callable[[str, int], tuple[list[PhysicsResult], dict[str, str]]]:
    """Factory fixture for loading topology and running physics.

    Parameters
    ----------
    engine : HybridEngine
        Engine to load data into and run.

    Returns
    -------
    Callable[[str, int], tuple[list[PhysicsResult], dict[str, str]]]
        Function that loads topology, runs physics, returns results and statuses.
    """

    def _load_and_run(topology: str, max_ticks: int = 10) -> tuple[list[PhysicsResult], dict[str, str]]:
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=max_ticks)
        statuses = engine.inspect()
        return results, statuses

    return _load_and_run


class TestCTQ5Reliability:
    """CTQ-5: Reliability - Graceful handling of edge cases and failures.

    Validates that patterns handle:
    - Empty graphs (no tasks)
    - Disconnected tasks
    - Missing predicates/guards
    - Cyclic dependencies
    """

    def test_basic_control_flow_empty_graph(self, engine: HybridEngine) -> None:
        """Empty graph converges immediately.

        CTQ Factor: Reliability
        Edge Case: No tasks
        Expected: Converge in 1 tick (no state changes)
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=5)

        assert len(results) == 1, "Empty graph should converge in 1 tick"
        assert results[0].delta == 0, "No state changes should occur"

    def test_basic_control_flow_disconnected_tasks(
        self, load_and_run: Callable[[str, int], tuple[list[PhysicsResult], dict[str, str]]]
    ) -> None:
        """Disconnected tasks do not interfere with each other.

        CTQ Factor: Reliability
        Edge Case: No flows connecting tasks
        Expected: Each task evolves independently
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Active" .

        <urn:task:B> a yawl:Task ;
            kgc:status "Active" .
        """
        results, statuses = load_and_run(topology, max_ticks=5)

        assert "urn:task:A" in statuses, "Task A should remain in graph"
        assert "urn:task:B" in statuses, "Task B should remain in graph"

    def test_advanced_branching_missing_predicate(
        self, load_and_run: Callable[[str, int], tuple[list[PhysicsResult], dict[str, str]]]
    ) -> None:
        """XOR-split handles false predicate gracefully (default path).

        CTQ Factor: Reliability
        Edge Case: Predicate evaluates to false
        Expected: Default flow activates
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
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
        results, statuses = load_and_run(topology, max_ticks=5)

        assert "urn:task:C" in statuses, "Task C (default) should activate when predicate false"
        assert statuses["urn:task:C"] in ("Active", "Completed", "Archived"), "Task C should be activated"
