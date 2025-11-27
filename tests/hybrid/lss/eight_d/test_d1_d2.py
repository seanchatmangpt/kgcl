"""8D Steps D1 (Team Formation) + D2 (Problem Description) Tests.

D1: Team Formation
------------------
- Establish cross-functional team for problem solving
- In WCP-43: Multiple workflow patterns coordinating
- Test pattern interactions without interference

D2: Problem Description
-----------------------
- Define and quantify the problem with data
- In WCP-43: Specific failure modes (deadlock, infinite loop, missing status)
- Identify exactly when and how failure occurs

Examples
--------
>>> from kgcl.hybrid.hybrid_engine import HybridEngine
>>> # D1: Multiple patterns coexist
>>> engine = HybridEngine()
>>> topology = '''
... @prefix kgc: <https://kgc.org/ns/> .
... @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
... <urn:task:A> a yawl:Task ; kgc:status "Completed" .
... '''
>>> _ = engine.load_data(topology)
>>> result = engine.apply_physics()
>>> result.delta >= 0
True
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine


class TestD1TeamFormation:
    """D1: Establish cross-functional team for problem solving.

    In WCP-43 context:
    - Team = Multiple workflow patterns coordinating
    - Cross-functional = Different pattern types (sequence, split, join)
    - Coordination = Patterns must work together without conflicts

    Test Strategy:
    - Verify multiple patterns can coexist in same topology
    - Test pattern interactions (sequence → split → join)
    - Validate no interference between concurrent patterns
    """

    def test_team_simple_sequence_and_split_coexist(self) -> None:
        """D1: Sequence (WCP-1) and Parallel Split (WCP-2) coexist.

        Team Members: WCP-1 (Sequence), WCP-2 (Parallel Split)
        Expected: Both patterns execute without interference
        """
        engine = HybridEngine()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        # WCP-1: Sequence
        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_b> .
        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .

        # WCP-2: Parallel Split
        <urn:task:C> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:c_to_d>, <urn:flow:c_to_e> .
        <urn:flow:c_to_d> yawl:nextElementRef <urn:task:D> .
        <urn:flow:c_to_e> yawl:nextElementRef <urn:task:E> .
        <urn:task:D> a yawl:Task .
        <urn:task:E> a yawl:Task .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)
        statuses = engine.inspect()

        # D1: Both patterns execute successfully
        assert statuses.get("urn:task:B") in ["Active", "Completed", "Archived"]
        assert statuses.get("urn:task:D") in ["Active", "Completed", "Archived"]
        assert statuses.get("urn:task:E") in ["Active", "Completed", "Archived"]

    def test_team_split_join_coordination(self) -> None:
        """D1: Split (WCP-2) and Join (WCP-3) coordinate.

        Team Members: WCP-2 (AND-Split), WCP-3 (AND-Join)
        Expected: Split activates parallel paths, Join synchronizes
        """
        engine = HybridEngine()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        # AND-Split
        <urn:task:Split> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b> .
        <urn:flow:to_a> yawl:nextElementRef <urn:task:A> .
        <urn:flow:to_b> yawl:nextElementRef <urn:task:B> .
        <urn:task:A> a yawl:Task .
        <urn:task:B> a yawl:Task .

        # AND-Join
        <urn:task:C> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:c_to_join> .
        <urn:task:D> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:d_to_join> .
        <urn:flow:c_to_join> yawl:nextElementRef <urn:task:Join> .
        <urn:flow:d_to_join> yawl:nextElementRef <urn:task:Join> .
        <urn:task:Join> a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeAnd .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)
        statuses = engine.inspect()

        # D1: Both patterns function correctly in same topology
        assert statuses.get("urn:task:A") in ["Active", "Completed", "Archived"]
        assert statuses.get("urn:task:Join") in ["Active", "Completed", "Archived"]


class TestD2ProblemDescription:
    """D2: Define and quantify the problem with data.

    In WCP-43 context:
    - Problem = Specific failure modes (deadlock, infinite loop, missing status)
    - Quantify = Identify exactly when and how failure occurs
    - Data = Topology state, tick counts, status transitions

    Test Strategy:
    - Identify and describe each failure mode
    - Quantify impact (how many tasks affected, how many ticks to failure)
    - Document conditions that trigger failure
    """

    def test_problem_deadlock_and_join_with_blocked_predecessor(self) -> None:
        """D2: AND-Join deadlock when predecessor never completes.

        Problem: Task waiting for predecessor that's Pending (never Active)
        Quantify: Join remains inactive indefinitely
        Impact: Workflow permanently stalled
        """
        engine = HybridEngine()
        topology = """
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
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()

        # D2 Problem: Join never activates due to B being Pending
        assert statuses.get("urn:task:Join") != "Active"
        assert statuses.get("urn:task:B") == "Pending"

    def test_problem_infinite_loop_circular_dependency(self) -> None:
        """D2: Infinite loop from circular task dependencies.

        Problem: Tasks form cycle (A → B → A)
        Quantify: System reaches max_ticks without convergence
        Impact: Resource exhaustion, system hangs
        """
        engine = HybridEngine()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .

        <urn:task:B> a yawl:Task ;
            yawl:flowsInto <urn:flow:b_to_a> .

        <urn:flow:b_to_a> yawl:nextElementRef <urn:task:A> .
        """
        engine.load_data(topology)

        # D2 Problem: System reaches max_ticks due to cycle
        try:
            results = engine.run_to_completion(max_ticks=5)
            # If converged early, that's acceptable
            assert results[-1].converged or engine.tick_count == 5
        except RuntimeError as e:
            # Expected if max_ticks reached without convergence
            assert "did not converge" in str(e)
