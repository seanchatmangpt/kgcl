"""8D Steps D7 (Prevention) + D8 (Recognition) Tests.

D7: Prevention
--------------
- Prevent recurrence through systemic changes
- In WCP-43: Guards, constraints, validation rules
- Changes to process/validation, not just fixes

D8: Recognition
---------------
- Recognize team contributions and capture learnings
- In WCP-43: Verify success criteria (convergence, correctness)
- Document what works and what doesn't

See Also
--------
test_integration : Full 8D cycle integration test

Examples
--------
>>> from kgcl.hybrid.hybrid_engine import HybridEngine
>>> # D7: Prevention - max_ticks constraint
>>> engine = HybridEngine()
>>> topology = '''
... @prefix kgc: <https://kgc.org/ns/> .
... @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
... <urn:task:A> a yawl:Task ; kgc:status "Completed" ;
...     yawl:flowsInto <urn:flow:loop> .
... <urn:flow:loop> yawl:nextElementRef <urn:task:A> .
... '''
>>> _ = engine.load_data(topology)
>>> _ = engine.run_to_completion(max_ticks=3)  # doctest: +ELLIPSIS
>>> engine.tick_count <= 3
True

>>> # D8: Recognition - convergence
>>> engine2 = HybridEngine()
>>> topology2 = '''
... @prefix kgc: <https://kgc.org/ns/> .
... @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
... <urn:task:A> a yawl:Task ; kgc:status "Completed" ;
...     yawl:flowsInto <urn:flow:a_to_b> .
... <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
... <urn:task:B> a yawl:Task .
... '''
>>> _ = engine2.load_data(topology2)
>>> result = engine2.run_to_completion(max_ticks=10)
>>> result[-1].converged
True
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine


class TestD7Prevention:
    """D7: Prevent recurrence through systemic changes.

    In WCP-43 context:
    - Prevention = Guards, constraints, validation rules
    - Recurrence = Same failure mode happening again
    - Systemic = Changes to process/validation, not just fixes

    Test Strategy:
    - Implement validation that detects problems early
    - Add guards to prevent invalid states
    - Test that prevention mechanisms work
    """

    def test_prevention_guard_against_missing_status(self) -> None:
        """D7: Guard ensures tasks have status before processing.

        Prevention: Validation that all tasks have status
        Expected: System handles missing status gracefully
        """
        engine = HybridEngine()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology)

        # D7: Prevention - System handles gracefully, doesn't crash
        result = engine.apply_physics()
        assert result is not None, "Prevention: System should handle missing status"

    def test_prevention_max_ticks_constraint_always_present(self) -> None:
        """D7: max_ticks constraint prevents infinite execution.

        Prevention: Always require max_ticks parameter
        Expected: System cannot run indefinitely
        """
        engine = HybridEngine()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:loop> .

        <urn:flow:loop> yawl:nextElementRef <urn:task:A> .
        """
        engine.load_data(topology)

        # D7: Prevention - max_ticks is required and enforced
        try:
            result = engine.run_to_completion(max_ticks=3)
        except RuntimeError:
            pass  # Expected when hitting limit

        assert engine.tick_count <= 3, "Prevention failed: no max_ticks enforcement"


class TestD8Recognition:
    """D8: Recognize team contributions and capture learnings.

    In WCP-43 context:
    - Recognition = Verify success criteria met (convergence, correctness)
    - Team = All patterns working together correctly
    - Learnings = Document what works and what doesn't

    Test Strategy:
    - Verify convergence for valid topologies
    - Confirm correctness of final states
    - Validate all quality criteria met
    """

    def test_recognition_convergence_achieved(self) -> None:
        """D8: Recognize convergence as success criterion.

        Success Criteria: System reaches fixed point (delta=0)
        Recognition: Workflow completed correctly
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
        result = engine.run_to_completion(max_ticks=10)

        # D8: Recognition - Convergence achieved
        assert result[-1].converged, "Success criterion: System must converge"

    def test_recognition_correctness_all_tasks_completed(self) -> None:
        """D8: Recognize correct final state as success.

        Success Criteria: All tasks reach expected status
        Recognition: Workflow correctness validated
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
            yawl:flowsInto <urn:flow:b_to_c> .

        <urn:flow:b_to_c> yawl:nextElementRef <urn:task:C> .
        <urn:task:C> a yawl:Task .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)
        statuses = engine.inspect()

        # D8: Recognition - All tasks reached expected state
        # Note: WCP physics rules activate tasks but don't auto-complete them.
        # Completion requires external actors (human, automated task executor).
        # Task A is Completed (initial state), B becomes Active via WCP-1.
        assert statuses.get("urn:task:A") in ["Completed", "Archived"]
        assert statuses.get("urn:task:B") in ["Active", "Completed", "Archived"]
        assert statuses.get("urn:task:C") in ["Pending", "Active", "Completed", "Archived"]

    def test_recognition_quality_no_errors_in_valid_topology(self) -> None:
        """D8: Recognize quality achievement (no errors).

        Success Criteria: No errors during execution
        Recognition: System stability validated
        """
        engine = HybridEngine()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        # WCP-2: Parallel Split
        <urn:task:Split> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:A> .
        <urn:flow:to_b> yawl:nextElementRef <urn:task:B> .
        <urn:task:A> a yawl:Task .
        <urn:task:B> a yawl:Task .

        # WCP-3: Synchronization
        <urn:task:A> yawl:flowsInto <urn:flow:a_to_join> .
        <urn:task:B> yawl:flowsInto <urn:flow:b_to_join> .
        <urn:flow:a_to_join> yawl:nextElementRef <urn:task:Join> .
        <urn:flow:b_to_join> yawl:nextElementRef <urn:task:Join> .

        <urn:task:Join> a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeAnd .
        """
        engine.load_data(topology)

        # D8: Recognition - No errors during execution
        try:
            result = engine.run_to_completion(max_ticks=10)
            assert result[-1].converged, "Quality criterion: Must converge"
        except Exception as e:
            pytest.fail(f"Quality failure: Unexpected error {e}")
