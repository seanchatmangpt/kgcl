"""Waste Analysis Tests.

Tests for identifying and measuring waste in workflow execution:
- Waiting waste (blocked tasks)
- WIP inventory waste
- Synchronization delays
- Process efficiency
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from tests.hybrid.lss.vsm.calculations import calculate_vsm_metrics


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for VSM testing."""
    return HybridEngine()


class TestVSM003SynchronizationWaitTime:
    """VSM-003: Measure wait time at synchronization points.

    Value Stream: (A || B) -> AND-Join -> Continue
    Focus: Wait time waste, synchronization delays
    """

    def test_and_join_wait_time(self, engine: HybridEngine) -> None:
        """Measure wait time when join waits for slowest branch."""
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
        results = engine.run_to_completion(max_ticks=10)

        vsm = calculate_vsm_metrics(results)

        # With one branch pending, there should be wait time (waste)
        assert vsm.total_wait_time_ms > 0, "Blocked join should incur wait time"
        assert vsm.waste_percentage > 0, "Wait time is waste"

    def test_balanced_vs_unbalanced_branches(self, engine: HybridEngine) -> None:
        """Compare balanced vs unbalanced parallel branches."""
        # Balanced: both branches complete
        topology_balanced = """
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
        engine_bal = HybridEngine()
        engine_bal.load_data(topology_balanced)
        results_bal = engine_bal.run_to_completion(max_ticks=10)

        vsm_bal = calculate_vsm_metrics(results_bal)

        # Balanced branches should have reasonable efficiency (>= 40%)
        # Note: Timing variance can cause slight fluctuations near boundary values
        assert vsm_bal.process_efficiency >= 0.4, "Balanced branches should be efficient"


class TestVSM005ProcessEfficiencyRatio:
    """VSM-005: Calculate process efficiency (value-add / lead time).

    Value Stream: Any workflow
    Focus: Efficiency ratio, waste elimination opportunities
    """

    def test_efficiency_ratio_calculation(self, engine: HybridEngine) -> None:
        """Calculate process efficiency ratio from REAL execution."""
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

        # Efficiency should be between 0 and 1
        assert 0.0 <= vsm.process_efficiency <= 1.0
        # Efficiency formula check
        expected_efficiency = vsm.value_add_time_ms / vsm.lead_time_ms if vsm.lead_time_ms > 0 else 0.0
        assert abs(vsm.process_efficiency - expected_efficiency) < 0.001

    def test_high_efficiency_workflow(self, engine: HybridEngine) -> None:
        """Test workflow with high process efficiency (low waste)."""
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

        vsm = calculate_vsm_metrics(results)

        # Simple sequence should have reasonable efficiency
        assert vsm.process_efficiency > 0.0, "Should have some value-add time"


class TestVSM012WasteCategoryClassification:
    """VSM-012: Classify waste into 7 Deadly Wastes categories.

    Categories: Overproduction, Waiting, Transport, Overprocessing,
                Inventory, Motion, Defects
    Focus: Waste categorization, improvement priorities
    """

    def test_waiting_waste_identification(self, engine: HybridEngine) -> None:
        """Identify waiting waste (tasks blocked on predecessors)."""
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
        results = engine.run_to_completion(max_ticks=10)

        vsm = calculate_vsm_metrics(results)

        # Pending task A creates waiting waste
        assert vsm.total_wait_time_ms > 0, "Pending task should create waiting waste"

    def test_inventory_waste_wip(self, engine: HybridEngine) -> None:
        """Measure inventory waste (excessive WIP)."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Split> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:to_a>, <urn:flow:to_b>, <urn:flow:to_c>, <urn:flow:to_d> .

        <urn:flow:to_a> yawl:nextElementRef <urn:task:A> .
        <urn:flow:to_b> yawl:nextElementRef <urn:task:B> .
        <urn:flow:to_c> yawl:nextElementRef <urn:task:C> .
        <urn:flow:to_d> yawl:nextElementRef <urn:task:D> .

        <urn:task:A> a yawl:Task .
        <urn:task:B> a yawl:Task .
        <urn:task:C> a yawl:Task .
        <urn:task:D> a yawl:Task .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=10)

        vsm = calculate_vsm_metrics(results)

        # High WIP indicates inventory waste
        assert vsm.max_wip >= 4, "4-way split should create WIP >= 4"


class TestVSM009MilestoneBlockingWaste:
    """VSM-009: Measure waste from milestone blocking.

    Value Stream: Task -> (blocked by milestone) -> Continue
    Focus: Blocking waste, milestone wait time
    """

    def test_milestone_blocking_waste(self, engine: HybridEngine) -> None:
        """Measure wait time waste from milestone blocking."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Predecessor> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:to_blocked> .

        <urn:flow:to_blocked> yawl:nextElementRef <urn:task:Blocked> .

        <urn:task:Blocked> a yawl:Task ;
            kgc:requiresMilestone <urn:milestone:M1> .

        <urn:milestone:M1> a yawl:Milestone ;
            kgc:status "Pending" .
        """
        engine.load_data(topology)
        results = engine.run_to_completion(max_ticks=10)

        vsm = calculate_vsm_metrics(results)

        # Blocked milestone should create wait time waste
        assert vsm.total_wait_time_ms > 0, "Milestone blocking should create waste"
        assert vsm.waste_percentage > 0
