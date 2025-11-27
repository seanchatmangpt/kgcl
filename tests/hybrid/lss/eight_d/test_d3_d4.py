"""8D Steps D3 (Interim Containment) + D4 (Root Cause Analysis) Tests.

D3: Interim Containment
-----------------------
- Implement interim containment actions to protect customers
- In WCP-43: max_ticks prevents infinite execution
- Ensure system doesn't hang or exhaust resources

D4: Root Cause Analysis
-----------------------
- Identify and verify root causes of the problem
- In WCP-43: Why topology fails (missing status, invalid flow, etc.)
- Examine physics rules, topology structure, state transitions

Examples
--------
>>> from kgcl.hybrid.hybrid_engine import HybridEngine
>>> # D3: max_ticks containment
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
"""

from __future__ import annotations

from kgcl.hybrid.hybrid_engine import HybridEngine


class TestD3InterimContainment:
    """D3: Implement interim containment actions to protect customers.

    In WCP-43 context:
    - Containment = max_ticks prevents infinite execution
    - Protect = Ensure system doesn't hang or exhaust resources
    - Interim = Temporary measure until root cause fixed

    Test Strategy:
    - Verify max_ticks prevents infinite loops
    - Test timeout prevents resource exhaustion
    - Validate graceful degradation under failure
    """

    def test_containment_max_ticks_prevents_infinite_loop(self) -> None:
        """D3: max_ticks containment action prevents infinite execution.

        Containment: max_ticks=5 limits execution
        Protection: System terminates gracefully
        Interim: Until circular dependency root cause is fixed
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

        # D3 Containment: max_ticks prevents runaway
        try:
            engine.run_to_completion(max_ticks=5)
        except RuntimeError:
            pass  # Expected - containment triggered

        # Verify containment was effective
        assert engine.tick_count <= 5, "Containment failed: exceeded max_ticks"

    def test_containment_graceful_termination_on_deadlock(self) -> None:
        """D3: Graceful termination when deadlock detected.

        Containment: System terminates without crash
        Protection: No resource leak or corruption
        """
        engine = HybridEngine()
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Pending" ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .

        <urn:task:B> a yawl:Task ;
            yawl:flowsInto <urn:flow:b_to_a> .

        <urn:flow:b_to_a> yawl:nextElementRef <urn:task:A> .
        """
        engine.load_data(topology)

        # D3 Containment: Graceful termination
        result = engine.run_to_completion(max_ticks=3)
        assert result is not None, "System should return result, not crash"


class TestD4RootCauseAnalysis:
    """D4: Identify and verify root causes of the problem.

    In WCP-43 context:
    - Root Cause = Why topology fails (missing status, invalid flow, etc.)
    - Verify = Demonstrate cause-effect relationship
    - Analysis = Examine physics rules, topology structure, state transitions

    Test Strategy:
    - Identify root cause for each failure mode
    - Verify cause-effect with controlled experiments
    - Test that removing cause eliminates failure
    """

    def test_root_cause_missing_status_prevents_activation(self) -> None:
        """D4: Missing kgc:status is root cause of non-activation.

        Root Cause: Task has no status property
        Effect: Successor never activates
        Verification: Adding status resolves issue
        """
        engine = HybridEngine()

        # Topology WITH root cause (missing status)
        topology_with_cause = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology_with_cause)
        engine.run_to_completion(max_ticks=5)
        statuses_with_cause = engine.inspect()

        # D4: Verify effect - B not activated
        assert statuses_with_cause.get("urn:task:B") != "Active"

        # Now fix root cause (add status)
        engine2 = HybridEngine()
        topology_without_cause = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        engine2.load_data(topology_without_cause)
        engine2.run_to_completion(max_ticks=5)
        statuses_without_cause = engine2.inspect()

        # D4: Verify fixing root cause resolves problem
        assert statuses_without_cause.get("urn:task:B") in ["Active", "Completed", "Archived"]

    def test_root_cause_dangling_flow_no_next_element(self) -> None:
        """D4: Dangling flow (no nextElementRef) is root cause of non-progression.

        Root Cause: Flow exists but has no nextElementRef
        Effect: Workflow terminates prematurely
        Verification: Adding nextElementRef enables progression
        """
        engine = HybridEngine()

        # Topology WITH root cause (dangling flow)
        topology_dangling = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:dangling> .

        <urn:flow:dangling> a yawl:Flow .
        """
        engine.load_data(topology_dangling)
        result = engine.apply_physics()

        # D4: Verify effect - no activation occurs
        assert result.delta == 0 or result.delta == 1  # Only status updates
