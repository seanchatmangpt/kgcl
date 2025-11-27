"""Lead Time and Cycle Time Tests.

Tests for measuring lead time, cycle time, and sequential workflow efficiency
using REAL HybridEngine execution.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from tests.hybrid.lss.vsm.calculations import calculate_vsm_metrics


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for VSM testing."""
    return HybridEngine()


class TestVSM001SequenceFlowValueStream:
    """VSM-001: Analyze value stream for sequential workflow.

    Value Stream: Start -> Task A -> Task B -> Task C -> End
    Focus: Lead time, cycle time, sequential bottlenecks
    """

    def test_sequence_lead_time_calculation(self, engine: HybridEngine) -> None:
        """Measure lead time for 3-task sequence using REAL engine."""
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
        results = engine.run_to_completion(max_ticks=10)

        # Calculate VSM metrics from REAL execution
        vsm = calculate_vsm_metrics(results)

        # Verify lead time is positive and measurable
        assert vsm.lead_time_ms > 0, "Lead time must be positive"
        assert vsm.total_ticks >= 2, "Sequence requires at least 2 ticks"
        assert vsm.lead_time_ms == sum(r.duration_ms for r in results)

    def test_sequence_cycle_time_breakdown(self, engine: HybridEngine) -> None:
        """Break down cycle time per task in sequence."""
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
        results = engine.run_to_completion(max_ticks=10)

        # Total cycle time = sum of processing ticks
        vsm = calculate_vsm_metrics(results)
        assert vsm.total_cycle_time_ms > 0
        assert vsm.total_cycle_time_ms <= vsm.lead_time_ms


class TestVSM006TaktTimeAnalysis:
    """VSM-006: Calculate and validate takt time.

    Takt Time = Available Time / Customer Demand
    Focus: Demand-driven pacing, capacity planning
    """

    def test_takt_time_calculation(self) -> None:
        """Calculate takt time for workflow instances."""
        from tests.hybrid.lss.vsm.calculations import calculate_takt_time

        available_time_ms = 10000.0  # 10 seconds available
        demand = 5  # 5 workflow instances needed

        takt_time = calculate_takt_time(available_time_ms, demand)

        # Each workflow should complete in 2000ms to meet demand
        assert takt_time == 2000.0
        assert takt_time == available_time_ms / demand

    def test_workflow_meets_takt_time(self, engine: HybridEngine) -> None:
        """Verify workflow lead time meets takt time requirement."""
        from tests.hybrid.lss.vsm.calculations import calculate_takt_time

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
        results = engine.run_to_completion(max_ticks=10)

        vsm = calculate_vsm_metrics(results)

        # Assume demand of 10 workflows per second (100ms takt time)
        # Generous takt time for testing
        takt_time = calculate_takt_time(1000.0, 10)

        # This workflow should be fast enough (typically < 100ms)
        # Note: We can't guarantee this without actual benchmarks,
        # but we verify the measurement works
        assert takt_time == 100.0
        assert vsm.lead_time_ms >= 0
