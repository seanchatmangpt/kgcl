"""GW-002/GW-003: Parallel split and synchronization walk tests.

Gemba Walk Focus: THROUGHPUT and HANDOFF observation
Walk Paths:
- Start -> AND-Split -> (A || B || C) -> AND-Join -> End
- Multiple branches -> AND-Join -> Continue

Observations: All branches activate simultaneously, join waits for all

CRITICAL: Uses REAL HybridEngine execution.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from tests.hybrid.lss.gemba.observations import gemba_observe


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for Gemba Walk observations.

    Returns
    -------
    HybridEngine
        New engine instance
    """
    return HybridEngine()


class TestGW002ParallelSplitWalk:
    """GW-002: Walk through parallel split to verify concurrent activation."""

    def test_walk_and_split_simultaneous_activation(self, engine: HybridEngine) -> None:
        """Walk AND-split, verify all branches start together with REAL engine.

        Parameters
        ----------
        engine : HybridEngine
            Fresh engine instance
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Split> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b>, <urn:flow:to_c> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:A> .
        <urn:flow:to_b> yawl:nextElementRef <urn:task:B> .
        <urn:flow:to_c> yawl:nextElementRef <urn:task:C> .

        <urn:task:A> a yawl:Task .
        <urn:task:B> a yawl:Task .
        <urn:task:C> a yawl:Task .
        """
        observations = []

        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)

        # REAL Gemba observation: Check actual states from engine
        statuses = engine.inspect()
        active_branches = sum(
            1
            for task in ["urn:task:A", "urn:task:B", "urn:task:C"]
            if statuses.get(task) in ["Active", "Completed", "Archived"]
        )

        observations.append(
            gemba_observe("After AND-split - all 3 branches activated (from engine)", 3, active_branches)
        )

        failed = [o for o in observations if not o.passed]
        assert len(failed) == 0, f"Failed observations: {failed}"

    def test_walk_branch_independence(self, engine: HybridEngine) -> None:
        """Walk verifies branches execute independently using REAL engine.

        Parameters
        ----------
        engine : HybridEngine
            Fresh engine instance
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Split> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:A> .
        <urn:flow:to_b> yawl:nextElementRef <urn:task:B> .

        <urn:task:A> a yawl:Task .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()

        # Both branches should be activated independently
        observation = gemba_observe(
            "Both branches activated independently (from engine)",
            True,
            statuses.get("urn:task:A") is not None and statuses.get("urn:task:B") is not None,
        )
        assert observation.passed


class TestGW003SynchronizationWalk:
    """GW-003: Walk through synchronization point to verify waiting behavior."""

    def test_walk_and_join_waits_for_all(self, engine: HybridEngine) -> None:
        """Walk AND-join, verify it waits for all branches with REAL engine.

        Parameters
        ----------
        engine : HybridEngine
            Fresh engine instance
        """
        # First test: Only one predecessor complete - join should NOT fire
        topology_partial = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_join> .

        <urn:task:B> a yawl:Task ;
            kgc:status "Pending" ;
            yawl:flowsInto <urn:flow:b_to_join> .

        <urn:flow:a_to_join> yawl:nextElementRef <urn:task:Join> .
        <urn:flow:b_to_join> yawl:nextElementRef <urn:task:Join> .

        <urn:task:Join> a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeAnd .
        """
        engine.load_data(topology_partial)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()

        observation = gemba_observe(
            "Join NOT ready with partial completion (from engine)",
            True,
            statuses.get("urn:task:Join") not in ["Active", "Completed", "Archived"],
        )
        assert observation.passed, f"Join fired prematurely: {statuses}"

    def test_walk_and_join_fires_when_all_complete(self, engine: HybridEngine) -> None:
        """Walk AND-join, verify it fires when ALL predecessors complete.

        Parameters
        ----------
        engine : HybridEngine
            Fresh engine instance
        """
        topology_complete = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_join> .

        <urn:task:B> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:b_to_join> .

        <urn:flow:a_to_join> yawl:nextElementRef <urn:task:Join> .
        <urn:flow:b_to_join> yawl:nextElementRef <urn:task:Join> .

        <urn:task:Join> a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeAnd .
        """
        engine2 = HybridEngine()
        engine2.load_data(topology_complete)
        engine2.run_to_completion(max_ticks=5)
        statuses2 = engine2.inspect()

        observation = gemba_observe(
            "Join ready when all complete (from engine)",
            True,
            statuses2.get("urn:task:Join") in ["Active", "Completed", "Archived"],
        )
        assert observation.passed, f"Join did not fire: {statuses2}"
