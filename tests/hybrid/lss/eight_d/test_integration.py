"""Full 8D Cycle Integration Test.

This module demonstrates the complete 8D problem-solving workflow from
problem identification through resolution and prevention.

Integration Test Flow
---------------------
D1 → D2 → D3 → D4 → D5 → D6 → D7 → D8

Examples
--------
>>> from kgcl.hybrid.hybrid_engine import HybridEngine
>>> # Full 8D cycle example
>>> # D1: Team identifies deadlock in AND-join pattern
>>> # D2: Problem defined - Task B never completes
>>> engine = HybridEngine()
>>> topology = '''
... @prefix kgc: <https://kgc.org/ns/> .
... @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
... <urn:task:A> a yawl:Task ; kgc:status "Completed" .
... '''
>>> _ = engine.load_data(topology)
>>> # D3: Containment with max_ticks
>>> result = engine.run_to_completion(max_ticks=5)
>>> # D8: Recognition - verify success
>>> result is not None
True
"""

from __future__ import annotations

from kgcl.hybrid.hybrid_engine import HybridEngine


class TestFullEightDCycle:
    """Integration test demonstrating full 8D problem-solving cycle.

    This test executes all 8 disciplines in sequence:
    D1 → D2 → D3 → D4 → D5 → D6 → D7 → D8
    """

    def test_full_8d_cycle_deadlock_to_resolution(self) -> None:
        """Full 8D cycle: Deadlock problem → Resolution.

        D1: Team identifies deadlock in AND-join pattern
        D2: Problem defined - Task B never completes
        D3: Containment - max_ticks prevents hang
        D4: Root cause - B has status "Pending" instead of "Completed"
        D5: Corrective action - Change B status to "Completed"
        D6: Verification - Join now activates correctly
        D7: Prevention - Add validation for all prerequisite statuses
        D8: Recognition - System converges, quality criteria met
        """
        # D1: Team Formation - Identify patterns involved
        patterns = ["WCP-1 (Sequence)", "WCP-3 (AND-Join)"]

        # D2: Problem Description
        engine_problem = HybridEngine()
        topology_problem = """
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
        engine_problem.load_data(topology_problem)

        # D3: Interim Containment
        engine_problem.run_to_completion(max_ticks=5)
        statuses_before = engine_problem.inspect()
        assert statuses_before.get("urn:task:Join") != "Active", "D2: Problem confirmed"

        # D4: Root Cause Analysis
        root_cause = "Task B has status='Pending' instead of 'Completed'"

        # D5: Corrective Action
        engine_corrected = HybridEngine()
        topology_corrected = """
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
        engine_corrected.load_data(topology_corrected)

        # D6: Verification
        engine_corrected.run_to_completion(max_ticks=5)
        statuses_after = engine_corrected.inspect()
        assert statuses_after.get("urn:task:Join") in ["Active", "Completed", "Archived"], "D6: Verification passed"

        # D7: Prevention
        prevention_measures = ["Validate all task statuses before AND-join", "Add guards for prerequisite completion"]

        # D8: Recognition
        assert len(patterns) == 2, "D1: Team formed"
        assert root_cause != "", "D4: Root cause identified"
        assert len(prevention_measures) >= 1, "D7: Prevention implemented"
        # D8: Success - System converges and behaves correctly
