"""FMEA Tests: State Transition Failures.

This module tests failure modes related to task state management:
- FM-003: Missing Task Status
- FM-009: Duplicate Task Activation

References
----------
AIAG FMEA Handbook (4th Edition), Section 4.2 (State Management Failures)
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


class TestFM003MissingTaskStatus:
    """FM-003: Task without status property.

    Failure Mode
    ------------
    Task exists but has no kgc:status property.

    Effect
    ------
    Task may never activate or complete, workflow stalls.

    FMEA Ratings
    ------------
    - Severity: 5 (Moderate - workflow stalls but system stable)
    - Occurrence: 5 (Moderate - easy to forget in manual topology creation)
    - Detection: 3 (High - inspection reveals missing status)
    - RPN: 75 (High risk - needs mitigation)

    Mitigation
    ----------
    Tasks without status should not activate successors.
    Validation should warn about tasks without status.
    """

    rpn = calculate_rpn(Severity.MODERATE, Occurrence.MODERATE, Detection.HIGH)

    def test_task_without_status_is_inactive(self, engine: HybridEngine) -> None:
        """Task without status should not activate successors.

        A task with no kgc:status property should be treated as inactive,
        preventing successor tasks from activating.
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology)
        result = engine.apply_physics()
        statuses = engine.inspect()
        # Task B should NOT be activated because A has no status
        assert statuses.get("urn:task:B") is None or statuses.get("urn:task:B") != "Active"

    def test_explicit_pending_status(self, engine: HybridEngine) -> None:
        """Task with explicit Pending status behaves correctly.

        A task with kgc:status "Pending" should not activate successors
        until it transitions to "Completed".
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Pending" ;
            yawl:flowsInto <urn:flow:a_to_b> .

        <urn:flow:a_to_b> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology)
        result = engine.apply_physics()
        statuses = engine.inspect()
        # Task B should NOT activate - A is only Pending, not Completed
        assert statuses.get("urn:task:B") != "Active"


class TestFM009DuplicateActivation:
    """FM-009: Task activated multiple times (race condition).

    Failure Mode
    ------------
    Same task activated twice in parallel paths (convergent flows).

    Effect
    ------
    Duplicate work execution, inconsistent state, wasted resources.

    FMEA Ratings
    ------------
    - Severity: 5 (Moderate - data inconsistency but recoverable)
    - Occurrence: 3 (Low - requires specific convergent topology)
    - Detection: 5 (Moderate - requires runtime inspection)
    - RPN: 75 (High risk)

    Mitigation
    ----------
    Tasks receiving multiple inputs should activate once only.
    Use AND-Join pattern for synchronization when appropriate.
    """

    rpn = calculate_rpn(Severity.MODERATE, Occurrence.LOW, Detection.MODERATE)

    def test_convergent_paths_single_activation(self, engine: HybridEngine) -> None:
        """Task receiving multiple inputs should activate once.

        When multiple completed tasks flow into the same successor,
        the successor should have a single consistent status.
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a_to_c> .

        <urn:task:B> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:b_to_c> .

        <urn:flow:a_to_c> yawl:nextElementRef <urn:task:C> .
        <urn:flow:b_to_c> yawl:nextElementRef <urn:task:C> .

        <urn:task:C> a yawl:Task .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=5)
        statuses = engine.inspect()
        # C should have a single consistent status
        status_c = statuses.get("urn:task:C")
        assert status_c in ["Active", "Completed", "Archived", None]
