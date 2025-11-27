"""FMEA Tests: Resource and Integration Failures.

This module tests failure modes related to system resources and integration:
- FM-007: Resource Exhaustion
- FM-008: EYE Reasoner Failure

References
----------
AIAG FMEA Handbook (4th Edition), Section 4.4 (Resource Failures)
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine, PhysicsResult

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


class TestFM007ResourceExhaustion:
    """FM-007: Memory/time resource exhaustion.

    Failure Mode
    ------------
    Large topology exhausts memory or exceeds timeout limits.

    Effect
    ------
    System crash, unresponsive, or degraded performance.

    FMEA Ratings
    ------------
    - Severity: 9 (Critical - system down or unresponsive)
    - Occurrence: 3 (Low - edge case with very large workflows)
    - Detection: 3 (High - monitoring detects resource spikes)
    - RPN: 81 (High risk)

    Mitigation
    ----------
    Enforce max_ticks to prevent runaway execution.
    Memory limits and streaming for large topologies.
    """

    rpn = calculate_rpn(Severity.CRITICAL, Occurrence.LOW, Detection.HIGH)

    def test_max_ticks_prevents_runaway(self, engine: HybridEngine) -> None:
        """max_ticks parameter prevents infinite execution.

        A workflow should terminate within max_ticks iterations.
        """
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Active" .
        """
        engine.load_data(topology)
        # Should complete within max_ticks
        result = engine.run_to_completion(max_ticks=3)
        assert engine.tick_count <= 3

    def test_moderate_topology_size(self, engine: HybridEngine) -> None:
        """System handles moderate topology (100 tasks).

        Engine should process 100 tasks without errors.
        """
        tasks = []
        for i in range(100):
            tasks.append(f'<urn:task:T{i}> a yawl:Task ; kgc:status "Pending" .')

        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
        """ + "\n".join(tasks)

        engine.load_data(topology)
        result = engine.apply_physics()
        # Should complete without error
        assert isinstance(result, PhysicsResult)


class TestFM008EyeReasonerFailure:
    """FM-008: EYE reasoner subprocess failure.

    Failure Mode
    ------------
    EYE reasoner crashes, times out, or returns invalid output.

    Effect
    ------
    Physics rules cannot be applied, workflow execution halts.

    FMEA Ratings
    ------------
    - Severity: 9 (Critical - core function lost)
    - Occurrence: 1 (Remote - EYE is stable and well-tested)
    - Detection: 1 (Certain - subprocess error is caught immediately)
    - RPN: 9 (Low risk due to EYE stability)

    Mitigation
    ----------
    Subprocess error handling with clear error messages.
    Retry logic for transient failures.
    """

    rpn = calculate_rpn(Severity.CRITICAL, Occurrence.REMOTE, Detection.CERTAIN)

    def test_valid_topology_processes_successfully(self, engine: HybridEngine) -> None:
        """Valid topology processes through EYE without error.

        A well-formed topology should execute successfully.
        """
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
        result = engine.apply_physics()
        assert isinstance(result, PhysicsResult)
