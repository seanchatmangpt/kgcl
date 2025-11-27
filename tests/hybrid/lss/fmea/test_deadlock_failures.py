"""FMEA Tests: Deadlock and Cycle Failures.

This module tests failure modes related to workflow deadlocks and cycles:
- FM-004: Circular Dependency (Deadlock)
- FM-005: AND-Join Deadlock
- FM-006: XOR-Split No Valid Path

References
----------
AIAG FMEA Handbook (4th Edition), Section 4.3 (Control Flow Failures)
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine

from .ratings import Detection, Occurrence, Severity, calculate_rpn


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for FMEA testing.

    Returns
    -------
    HybridEngine
        Initialized engine instance
    """
    return HybridEngine()


class TestFM004CircularDependency:
    """FM-004: Circular task dependencies (deadlock).

    Failure Mode
    ------------
    Tasks form a cycle with mutual dependencies (A→B→A).

    Effect
    ------
    Infinite loop or deadlock, system hangs indefinitely.

    FMEA Ratings
    ------------
    - Severity: 9 (Critical - system hangs, requires restart)
    - Occurrence: 3 (Low - design review catches most cycles)
    - Detection: 5 (Moderate - not always obvious in complex workflows)
    - RPN: 135 (Critical risk - MUST prevent)

    Mitigation
    ----------
    Enforce max_ticks limit to prevent infinite execution.
    Cycle detection in topology validation.
    """

    rpn = calculate_rpn(Severity.CRITICAL, Occurrence.LOW, Detection.MODERATE)

    def test_two_task_cycle_terminates(self, engine: HybridEngine) -> None:
        """Two-task cycle should terminate via max_ticks.

        A→B→A cycle should be caught by max_ticks limit,
        not hang indefinitely.
        """
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
        # Should terminate within max_ticks, not hang
        result = engine.run_to_completion(max_ticks=10)
        assert result is not None, "Engine should return result, not hang"

    def test_self_referencing_task(self, engine: HybridEngine) -> None:
        """Self-referencing task should not cause infinite loop.

        A task with a flow to itself (A→A) should be handled gracefully.
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_a> .

        <urn:flow:a_to_a> yawl:nextElementRef <urn:task:A> .
        """
        engine.load_data(topology)
        result = engine.run_to_completion(max_ticks=5)
        assert result is not None


class TestFM005AndJoinDeadlock:
    """FM-005: AND-Join with unreachable predecessor.

    Failure Mode
    ------------
    AND-Join waits for task that can never complete.

    Effect
    ------
    Workflow permanently blocked, successor tasks never activate.

    FMEA Ratings
    ------------
    - Severity: 9 (Critical - workflow dead, no recovery)
    - Occurrence: 5 (Moderate - design error in complex workflows)
    - Detection: 7 (Low - hard to detect at design time)
    - RPN: 315 (Critical risk - MUST detect)

    Mitigation
    ----------
    AND-Join should only activate when ALL predecessors complete.
    Reachability analysis in topology validation.
    """

    rpn = calculate_rpn(Severity.CRITICAL, Occurrence.MODERATE, Detection.LOW)

    def test_and_join_with_one_path_blocked(self, engine: HybridEngine) -> None:
        """AND-Join should not activate if any predecessor is blocked.

        When one of two paths to AND-Join is Pending, the join should wait.
        """
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
        # Join should NOT activate - B is still Pending
        assert statuses.get("urn:task:Join") != "Active"

    def test_and_join_all_paths_complete(self, engine: HybridEngine) -> None:
        """AND-Join activates when all predecessors complete.

        When both paths to AND-Join are Completed, join should activate.
        """
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
        assert statuses.get("urn:task:Join") in ["Active", "Completed", "Archived"]


class TestFM006XorSplitNoValidPath:
    """FM-006: XOR-Split with no valid path.

    Failure Mode
    ------------
    XOR-Split has no matching predicate and no default fallback.

    Effect
    ------
    Workflow stalls at decision point, no successor activates.

    FMEA Ratings
    ------------
    - Severity: 7 (High - workflow blocked at decision)
    - Occurrence: 5 (Moderate - incomplete design/testing)
    - Detection: 5 (Moderate - requires runtime testing)
    - RPN: 175 (Critical risk)

    Mitigation
    ----------
    XOR-Split should always have a default fallback path.
    Validation should warn about splits without defaults.
    """

    rpn = calculate_rpn(Severity.HIGH, Occurrence.MODERATE, Detection.MODERATE)

    def test_xor_split_with_default_fallback(self, engine: HybridEngine) -> None:
        """XOR-Split should use default when no predicate matches.

        When the primary path's predicate is false, the default path
        should be taken.
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Decision> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeXor ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:A> ;
            yawl:hasPredicate <urn:pred:a> .
        <urn:pred:a> kgc:evaluatesTo false .

        <urn:flow:to_b> yawl:nextElementRef <urn:task:B> ;
            yawl:isDefaultFlow true .

        <urn:task:A> a yawl:Task .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()
        # B should activate as the default path
        assert statuses.get("urn:task:B") in ["Active", "Completed", "Archived"]
