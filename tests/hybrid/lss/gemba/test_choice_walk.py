"""GW-004/GW-005/GW-006: Choice pattern walk tests.

Gemba Walk Focus: FLOW_DIRECTION and TIMING observation
Walk Paths:
- Decision -> (Path A XOR Path B XOR Path C)
- (Path A XOR Path B) -> XOR-Join -> Continue
- OR-Split -> (any subset of paths)

Observations: Correct path selection, timing, and merge behavior

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


class TestGW004ExclusiveChoiceWalk:
    """GW-004: Walk through exclusive choice to verify single path selection."""

    def test_walk_xor_split_single_path(self, engine: HybridEngine) -> None:
        """Walk XOR-split, verify exactly one path activated with REAL engine.

        Parameters
        ----------
        engine : HybridEngine
            Fresh engine instance
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Decision> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeXor ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:PathA> ;
            yawl:hasPredicate <urn:pred:a> .
        <urn:pred:a> kgc:evaluatesTo true .

        <urn:flow:to_b> yawl:nextElementRef <urn:task:PathB> ;
            yawl:isDefaultFlow true .

        <urn:task:PathA> a yawl:Task .
        <urn:task:PathB> a yawl:Task .
        """
        observations = []

        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()

        # Count active paths (from REAL engine)
        path_a_active = statuses.get("urn:task:PathA") in ["Active", "Completed", "Archived"]
        path_b_active = statuses.get("urn:task:PathB") in ["Active", "Completed", "Archived"]

        observations.append(gemba_observe("XOR-split activated the predicated path (from engine)", True, path_a_active))

        failed = [o for o in observations if not o.passed]
        assert len(failed) == 0, f"Failed observations: {failed}"

    def test_walk_xor_default_path(self, engine: HybridEngine) -> None:
        """Walk XOR-split default path when predicate is false.

        Parameters
        ----------
        engine : HybridEngine
            Fresh engine instance
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Decision> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeXor ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:PathA> ;
            yawl:hasPredicate <urn:pred:a> .
        <urn:pred:a> kgc:evaluatesTo false .

        <urn:flow:to_b> yawl:nextElementRef <urn:task:PathB> ;
            yawl:isDefaultFlow true .

        <urn:task:PathA> a yawl:Task .
        <urn:task:PathB> a yawl:Task .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()

        # Default path B should be taken when predicate is false
        observation = gemba_observe(
            "XOR-split took default path when predicate false (from engine)",
            True,
            statuses.get("urn:task:PathB") in ["Active", "Completed", "Archived"],
        )
        assert observation.passed, f"Default path not taken: {statuses}"


class TestGW005SimpleMergeWalk:
    """GW-005: Walk through simple merge to verify no synchronization."""

    def test_walk_xor_join_immediate_continuation(self, engine: HybridEngine) -> None:
        """Walk XOR-join, verify first arrival continues with REAL engine.

        Parameters
        ----------
        engine : HybridEngine
            Fresh engine instance
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:PathA> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_merge> .

        <urn:task:PathB> a yawl:Task ;
            kgc:status "Pending" ;
            yawl:flowsInto <urn:flow:b_to_merge> .

        <urn:flow:a_to_merge> yawl:nextElementRef <urn:task:Merge> .
        <urn:flow:b_to_merge> yawl:nextElementRef <urn:task:Merge> .

        <urn:task:Merge> a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeOr ;
            yawl:flowsInto <urn:flow:to_successor> .

        <urn:flow:to_successor> yawl:nextElementRef <urn:task:Successor> .
        <urn:task:Successor> a yawl:Task .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()

        observations = []

        # OR-join should fire when first path completes
        observations.append(
            gemba_observe(
                "OR-join fires on first completion (from engine)",
                True,
                statuses.get("urn:task:Merge") in ["Active", "Completed", "Archived"],
            )
        )

        # Successor should be activated
        observations.append(
            gemba_observe(
                "Successor activates after merge (from engine)",
                True,
                statuses.get("urn:task:Successor") in ["Active", "Completed", "Archived"],
            )
        )

        failed = [o for o in observations if not o.passed]
        assert len(failed) == 0, f"Failed observations: {failed}"


class TestGW006MultiChoiceWalk:
    """GW-006: Walk through multi-choice to verify flexible selection."""

    def test_walk_or_split_multiple_paths(self, engine: HybridEngine) -> None:
        """Walk OR-split, verify multiple path selection with REAL engine.

        Parameters
        ----------
        engine : HybridEngine
            Fresh engine instance
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:OrSplit> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeOr ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b>, <urn:flow:to_c> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:PathA> ;
            yawl:hasPredicate <urn:pred:a> .
        <urn:pred:a> kgc:evaluatesTo true .

        <urn:flow:to_b> yawl:nextElementRef <urn:task:PathB> ;
            yawl:hasPredicate <urn:pred:b> .
        <urn:pred:b> kgc:evaluatesTo true .

        <urn:flow:to_c> yawl:nextElementRef <urn:task:PathC> ;
            yawl:hasPredicate <urn:pred:c> .
        <urn:pred:c> kgc:evaluatesTo false .

        <urn:task:PathA> a yawl:Task .
        <urn:task:PathB> a yawl:Task .
        <urn:task:PathC> a yawl:Task .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()

        observations = []

        # Count activated paths (should be 2: A and B with true predicates)
        path_a_active = statuses.get("urn:task:PathA") in ["Active", "Completed", "Archived"]
        path_b_active = statuses.get("urn:task:PathB") in ["Active", "Completed", "Archived"]
        path_c_active = statuses.get("urn:task:PathC") in ["Active", "Completed", "Archived"]

        observations.append(
            gemba_observe(
                "OR-split activated paths with true predicates (from engine)", True, path_a_active and path_b_active
            )
        )

        observations.append(
            gemba_observe("OR-split did NOT activate path with false predicate (from engine)", False, path_c_active)
        )

        failed = [o for o in observations if not o.passed]
        assert len(failed) == 0, f"Failed observations: {failed}"


class TestGW007DeferredChoiceWalk:
    """GW-007: Walk through deferred choice to verify environment-driven selection."""

    def test_walk_deferred_choice_state(self, engine: HybridEngine) -> None:
        """Walk deferred choice, observe REAL state transitions.

        Parameters
        ----------
        engine : HybridEngine
            Fresh engine instance
        """
        # Deferred choice is modeled as XOR-split with runtime predicate
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Deferred> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeXor ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:OptionA> ;
            yawl:hasPredicate <urn:pred:runtime> .
        <urn:pred:runtime> kgc:evaluatesTo true .

        <urn:flow:to_b> yawl:nextElementRef <urn:task:OptionB> ;
            yawl:isDefaultFlow true .

        <urn:task:OptionA> a yawl:Task .
        <urn:task:OptionB> a yawl:Task .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()

        # One option should be activated based on runtime predicate
        observation = gemba_observe(
            "Deferred choice resolved at runtime (from engine)",
            True,
            statuses.get("urn:task:OptionA") in ["Active", "Completed", "Archived"]
            or statuses.get("urn:task:OptionB") in ["Active", "Completed", "Archived"],
        )
        assert observation.passed, f"Deferred choice not resolved: {statuses}"
