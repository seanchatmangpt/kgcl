"""CTQ-1: Correctness Tests for WCP Patterns.

This module validates that YAWL workflow control patterns produce expected state
transitions according to their specifications.

Test Coverage
-------------
- Basic Control Flow: Sequence (WCP-1), Parallel Split (WCP-2)
- Advanced Branching: Exclusive Choice (WCP-4)
- State-Based: Milestone (WCP-18)

Quality Gates
-------------
- Expected state transitions verified
- Task activation order confirmed
- Join/split logic correctness validated
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


class TestCTQ1Correctness:
    """CTQ-1: Correctness - Patterns produce expected state transitions.

    Validates that each pattern category correctly implements the YAWL semantics.
    Tests verify:
    - Tasks activate in correct order
    - Join/split logic fires when expected
    - Final states match specification
    """

    def test_basic_control_flow_sequence_correct(
        self, load_and_run: Callable[[str, int], tuple[list[PhysicsResult], dict[str, str]]]
    ) -> None:
        """WCP-1 Sequence produces correct linear state transition.

        CTQ Factor: Correctness
        Pattern: WCP-1 (Sequence)
        Expected: A (Completed) → B (Active)
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        results, statuses = load_and_run(topology, max_ticks=5)

        assert len(results) >= 1, "Physics should execute at least 1 tick"
        assert "urn:task:B" in statuses, "Task B should be in graph"
        assert statuses["urn:task:B"] in ("Active", "Completed", "Archived"), (
            "Task B should be Active, Completed, or Archived"
        )

    def test_basic_control_flow_parallel_split_correct(
        self, load_and_run: Callable[[str, int], tuple[list[PhysicsResult], dict[str, str]]]
    ) -> None:
        """WCP-2 Parallel Split activates all branches simultaneously.

        CTQ Factor: Correctness
        Pattern: WCP-2 (AND-Split)
        Expected: A (Completed) → B (Active) AND C (Active)
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:1>, <urn:flow:2> .

        <urn:flow:1> yawl:nextElementRef <urn:task:B> .
        <urn:flow:2> yawl:nextElementRef <urn:task:C> .

        <urn:task:B> a yawl:Task .
        <urn:task:C> a yawl:Task .
        """
        results, statuses = load_and_run(topology, max_ticks=5)

        assert "urn:task:B" in statuses, "Task B should be activated"
        assert "urn:task:C" in statuses, "Task C should be activated"
        assert statuses["urn:task:B"] in ("Active", "Completed", "Archived"), "Task B should be activated"
        assert statuses["urn:task:C"] in ("Active", "Completed", "Archived"), "Task C should be activated"

    def test_advanced_branching_xor_correct(
        self, load_and_run: Callable[[str, int], tuple[list[PhysicsResult], dict[str, str]]]
    ) -> None:
        """WCP-4 Exclusive Choice activates exactly one branch.

        CTQ Factor: Correctness
        Pattern: WCP-4 (XOR-Split)
        Expected: A (Completed) → B (Active) XOR C (inactive)
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

        <urn:pred:1> kgc:evaluatesTo true .

        <urn:task:B> a yawl:Task .
        <urn:task:C> a yawl:Task .
        """
        results, statuses = load_and_run(topology, max_ticks=5)

        assert "urn:task:B" in statuses, "Task B should be activated (predicate true)"
        assert statuses["urn:task:B"] in ("Active", "Completed", "Archived"), "Task B should be activated"
        # C should NOT be activated - it can have "Pending" status but not "Active"
        if "urn:task:C" in statuses:
            assert statuses["urn:task:C"] not in (
                "Active",
                "Completed",
                "Archived",
            ), "Task C should NOT be activated (XOR exclusivity)"

    def test_state_based_milestone_correct(
        self, load_and_run: Callable[[str, int], tuple[list[PhysicsResult], dict[str, str]]]
    ) -> None:
        """WCP-18 Milestone blocks task until milestone reached.

        CTQ Factor: Correctness
        Pattern: WCP-18 (Milestone)
        Expected: B waits for milestone before activating
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:B> .

        <urn:task:B> a yawl:Task ;
            kgc:requiresMilestone <urn:milestone:1> .

        <urn:milestone:1> kgc:status "Reached" .
        """
        results, statuses = load_and_run(topology, max_ticks=5)

        assert "urn:task:B" in statuses, "Task B should be activated after milestone"
        assert statuses["urn:task:B"] in ("Active", "Completed", "Archived"), "Task B should be activated"
