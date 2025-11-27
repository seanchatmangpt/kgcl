"""8D Steps D5 (Corrective Actions) + D6 (Verification) Tests.

D5: Corrective Actions
----------------------
- Choose and verify permanent corrective actions
- In WCP-43: Topology fixes (add status, fix flows, break cycles)
- Ensure no side effects from corrections

D6: Verification
----------------
- Verify that corrective actions work as expected
- In WCP-43: Test that fixes resolve the problem
- Test edge cases to ensure robustness

Examples
--------
>>> from kgcl.hybrid.hybrid_engine import HybridEngine
>>> # D5: Corrective action - add missing status
>>> engine = HybridEngine()
>>> topology = '''
... @prefix kgc: <https://kgc.org/ns/> .
... @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
... <urn:task:A> a yawl:Task ; kgc:status "Completed" ;
...     yawl:flowsInto <urn:flow:a_to_b> .
... <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
... <urn:task:B> a yawl:Task .
... '''
>>> _ = engine.load_data(topology)
>>> _ = engine.run_to_completion(max_ticks=5)
>>> statuses = engine.inspect()
>>> statuses.get("urn:task:B") in ["Active", "Completed", "Archived"]
True
"""

from __future__ import annotations

from kgcl.hybrid.hybrid_engine import HybridEngine


class TestD5CorrectiveActions:
    """D5: Choose and verify permanent corrective actions.

    In WCP-43 context:
    - Corrective Actions = Topology fixes (add status, fix flows, break cycles)
    - Permanent = Changes that prevent recurrence
    - Verify = Test that corrections work

    Test Strategy:
    - Implement fixes for identified root causes
    - Verify fixes resolve the problem
    - Ensure no side effects from corrections
    """

    def test_corrective_action_add_missing_status(self) -> None:
        """D5: Add kgc:status to resolve non-activation.

        Corrective Action: Add "kgc:status Completed" to task
        Expected: Successor activates correctly
        Verification: Workflow progresses to completion
        """
        engine = HybridEngine()
        topology_corrected = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology_corrected)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()

        # D5: Verify corrective action works
        assert statuses.get("urn:task:B") in ["Active", "Completed", "Archived"]

    def test_corrective_action_break_circular_dependency(self) -> None:
        """D5: Break circular dependency by removing back-edge.

        Corrective Action: Remove flow that creates cycle
        Expected: Workflow converges
        Verification: System reaches fixed point
        """
        engine = HybridEngine()
        topology_corrected = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .

        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology_corrected)
        result = engine.run_to_completion(max_ticks=5)

        # D5: Verify correction - system converges
        assert result[-1].converged, "System should converge after breaking cycle"


class TestD6Verification:
    """D6: Verify that corrective actions work as expected.

    In WCP-43 context:
    - Verification = Test that fixes resolve the problem
    - Work = System behaves correctly after correction
    - Expected = Matches desired workflow behavior

    Test Strategy:
    - Re-run problem scenarios with corrections
    - Verify problem no longer occurs
    - Test edge cases to ensure robustness
    """

    def test_verification_and_join_with_all_complete(self) -> None:
        """D6: Verify AND-Join activates when all predecessors complete.

        Verification: After correcting missing status, join works
        Expected: Join activates when both paths complete
        """
        engine = HybridEngine()
        topology = """
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
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()

        # D6: Verification - Join activates correctly
        assert statuses.get("urn:task:Join") in ["Active", "Completed", "Archived"]

    def test_verification_no_infinite_loop_after_correction(self) -> None:
        """D6: Verify no infinite loop after breaking cycle.

        Verification: System converges after removing back-edge
        Expected: Reaches fixed point within max_ticks
        """
        engine = HybridEngine()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology)
        result = engine.run_to_completion(max_ticks=5)

        # D6: Verification - System converges
        assert result[-1].converged
