"""Hook Waste Analysis Tests (Kaizen for Knowledge Hooks).

Tests the 3M waste framework applied to Knowledge Hooks:
- MUDA: The 7 wastes in hook operations
- MURA: Unevenness in hook performance
- MURI: Overburden in hook execution

CRITICAL: Tests the metrics dataclasses and analysis without requiring reasoner.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.knowledge_hooks import HookAction, HookPhase, HookRegistry, KnowledgeHook
from tests.hybrid.lss.hooks.kaizen.metrics import (
    HookMudaMetrics,
    HookMudaType,
    HookMuraMetrics,
    HookMuriMetrics,
    HookWasteAnalysis,
)


@pytest.fixture
def hook_registry() -> HookRegistry:
    """Create fresh HookRegistry."""
    return HookRegistry()


class TestHookMudaWaste:
    """Test detection and measurement of 7 wastes in hook execution."""

    def test_overprocessing_waste_metrics(self) -> None:
        """Test overprocessing waste metrics (unnecessary condition evaluations)."""
        # Create metrics for unnecessary condition evaluations
        metrics = HookMudaMetrics(
            waste_type=HookMudaType.OVERPROCESSING,
            count=5,
            total_duration_ms=25.0,
            percentage_of_total=15.0,
        )

        assert metrics.waste_type == HookMudaType.OVERPROCESSING
        assert metrics.count == 5
        assert metrics.total_duration_ms == 25.0
        assert metrics.percentage_of_total == 15.0

    def test_waiting_waste_metrics(self) -> None:
        """Test waiting waste metrics (hooks blocked by priority)."""
        metrics = HookMudaMetrics(
            waste_type=HookMudaType.WAITING,
            count=3,
            total_duration_ms=45.0,
            percentage_of_total=20.0,
        )

        assert metrics.waste_type == HookMudaType.WAITING
        assert metrics.count == 3
        assert metrics.total_duration_ms == 45.0

    def test_motion_waste_metrics(self) -> None:
        """Test motion waste metrics (excessive phase transitions)."""
        metrics = HookMudaMetrics(
            waste_type=HookMudaType.MOTION,
            count=2,
            total_duration_ms=10.0,
            percentage_of_total=5.0,
        )

        assert metrics.waste_type == HookMudaType.MOTION
        assert metrics.count == 2

    def test_inventory_waste_metrics(self, hook_registry: HookRegistry) -> None:
        """Test inventory waste metrics (too many pending hooks)."""
        # Register many hooks but don't execute them
        for i in range(20):
            hook = KnowledgeHook(
                hook_id=f"pending-hook-{i}",
                name=f"Pending Hook {i}",
                phase=HookPhase.PRE_TICK,
                priority=100 - i,
                enabled=True,
                condition_query="",
                action=HookAction.NOTIFY,
            )
            hook_registry.register(hook)

        # Count pending hooks as inventory waste
        all_hooks = hook_registry.get_all()
        pending_count = len([h for h in all_hooks if h.enabled])

        metrics = HookMudaMetrics(
            waste_type=HookMudaType.INVENTORY,
            count=pending_count,
            total_duration_ms=0.0,
            percentage_of_total=0.0,
        )

        assert metrics.waste_type == HookMudaType.INVENTORY
        assert metrics.count == 20

    def test_defects_waste_metrics(self) -> None:
        """Test defect waste metrics (failed hook executions)."""
        metrics = HookMudaMetrics(
            waste_type=HookMudaType.DEFECTS,
            count=2,
            total_duration_ms=80.0,
            percentage_of_total=25.0,
        )

        assert metrics.waste_type == HookMudaType.DEFECTS
        assert metrics.count == 2
        assert metrics.total_duration_ms == 80.0

    def test_overproduction_waste_metrics(self) -> None:
        """Test overproduction waste metrics (redundant assertions)."""
        metrics = HookMudaMetrics(
            waste_type=HookMudaType.OVERPRODUCTION,
            count=4,
            total_duration_ms=60.0,
            percentage_of_total=18.0,
        )

        assert metrics.waste_type == HookMudaType.OVERPRODUCTION
        assert metrics.count == 4

    def test_transport_waste_metrics(self) -> None:
        """Test transport waste metrics (cross-phase data movement)."""
        metrics = HookMudaMetrics(
            waste_type=HookMudaType.TRANSPORT,
            count=1,
            total_duration_ms=15.0,
            percentage_of_total=8.0,
        )

        assert metrics.waste_type == HookMudaType.TRANSPORT
        assert metrics.count == 1
        assert metrics.total_duration_ms == 15.0

    def test_zero_waste(self) -> None:
        """Test zero waste case."""
        metrics = HookMudaMetrics(
            waste_type=HookMudaType.WAITING,
            count=0,
            total_duration_ms=0.0,
            percentage_of_total=0.0,
        )

        assert metrics.count == 0
        assert metrics.total_duration_ms == 0.0
        assert metrics.percentage_of_total == 0.0


class TestHookMuraUnevenness:
    """Test detection and measurement of unevenness in hook execution."""

    def test_low_variability(self) -> None:
        """Test metrics for consistent (low variability) hook execution."""
        metrics = HookMuraMetrics(
            coefficient_of_variation=0.3,
            max_duration_ms=25.0,
            min_duration_ms=15.0,
        )

        assert metrics.coefficient_of_variation == 0.3
        assert metrics.coefficient_of_variation < 0.5, "Should be low variability"
        assert metrics.max_duration_ms == 25.0
        assert metrics.min_duration_ms == 15.0

    def test_high_variability(self) -> None:
        """Test metrics for uneven (high variability) hook execution."""
        metrics = HookMuraMetrics(
            coefficient_of_variation=1.2,
            max_duration_ms=200.0,
            min_duration_ms=10.0,
        )

        assert metrics.coefficient_of_variation == 1.2
        assert metrics.coefficient_of_variation >= 1.0, "Should be high variability"
        assert metrics.max_duration_ms == 200.0
        assert metrics.min_duration_ms == 10.0

    def test_perfect_consistency(self) -> None:
        """Test metrics for perfectly consistent execution."""
        metrics = HookMuraMetrics(
            coefficient_of_variation=0.0,
            max_duration_ms=20.0,
            min_duration_ms=20.0,
        )

        assert metrics.coefficient_of_variation == 0.0
        assert metrics.max_duration_ms == metrics.min_duration_ms

    def test_moderate_variability(self) -> None:
        """Test metrics for moderate variability."""
        metrics = HookMuraMetrics(
            coefficient_of_variation=0.7,
            max_duration_ms=80.0,
            min_duration_ms=40.0,
        )

        assert 0.5 <= metrics.coefficient_of_variation < 1.0
        assert metrics.max_duration_ms > metrics.min_duration_ms


class TestHookMuriOverburden:
    """Test detection and measurement of overburden in hook execution."""

    def test_normal_load(self) -> None:
        """Test metrics for normal (non-overloaded) system."""
        metrics = HookMuriMetrics(
            hooks_per_tick=5.0,
            max_concurrent=3,
            overload_threshold=10,
            is_overloaded=False,
        )

        assert metrics.hooks_per_tick == 5.0
        assert metrics.max_concurrent == 3
        assert metrics.overload_threshold == 10
        assert not metrics.is_overloaded
        assert metrics.hooks_per_tick < metrics.overload_threshold

    def test_overloaded_system(self) -> None:
        """Test metrics for overloaded system."""
        metrics = HookMuriMetrics(
            hooks_per_tick=15.0,
            max_concurrent=12,
            overload_threshold=10,
            is_overloaded=True,
        )

        assert metrics.hooks_per_tick == 15.0
        assert metrics.max_concurrent == 12
        assert metrics.is_overloaded
        assert metrics.hooks_per_tick > metrics.overload_threshold

    def test_approaching_capacity(self) -> None:
        """Test metrics for system approaching capacity."""
        metrics = HookMuriMetrics(
            hooks_per_tick=9.5,
            max_concurrent=8,
            overload_threshold=10,
            is_overloaded=False,
        )

        utilization = metrics.hooks_per_tick / metrics.overload_threshold
        assert utilization > 0.9, "Should be approaching capacity"
        assert not metrics.is_overloaded, "Not yet overloaded"

    def test_zero_load(self) -> None:
        """Test metrics for idle system."""
        metrics = HookMuriMetrics(
            hooks_per_tick=0.0,
            max_concurrent=0,
            overload_threshold=10,
            is_overloaded=False,
        )

        assert metrics.hooks_per_tick == 0.0
        assert metrics.max_concurrent == 0
        assert not metrics.is_overloaded

    def test_high_concurrency(self) -> None:
        """Test metrics for high concurrent execution."""
        metrics = HookMuriMetrics(
            hooks_per_tick=12.0,
            max_concurrent=12,
            overload_threshold=10,
            is_overloaded=True,
        )

        assert metrics.max_concurrent == 12
        assert metrics.max_concurrent > metrics.overload_threshold


class TestHookWasteAnalysisIntegration:
    """Test comprehensive waste analysis combining all three types."""

    def test_complete_waste_analysis(self) -> None:
        """Test complete waste analysis with all three waste types."""
        # Create comprehensive waste metrics
        muda_metrics = [
            HookMudaMetrics(HookMudaType.OVERPROCESSING, 3, 45.0, 15.0),
            HookMudaMetrics(HookMudaType.WAITING, 2, 30.0, 10.0),
            HookMudaMetrics(HookMudaType.DEFECTS, 1, 20.0, 5.0),
        ]

        mura_metrics = HookMuraMetrics(
            coefficient_of_variation=0.5,
            max_duration_ms=80.0,
            min_duration_ms=20.0,
        )

        muri_metrics = HookMuriMetrics(
            hooks_per_tick=8.0,
            max_concurrent=5,
            overload_threshold=10,
            is_overloaded=False,
        )

        analysis = HookWasteAnalysis(
            cycle_id="test-cycle-001",
            muda_metrics=muda_metrics,
            mura_metrics=mura_metrics,
            muri_metrics=muri_metrics,
            total_hooks_executed=10,
            total_duration_ms=300.0,
        )

        assert analysis.cycle_id == "test-cycle-001"
        assert len(analysis.muda_metrics) == 3
        assert analysis.total_hooks_executed == 10
        assert analysis.total_duration_ms == 300.0
        assert analysis.total_waste_percentage == 30.0

    def test_waste_analysis_total_percentage(self) -> None:
        """Test calculation of total waste percentage."""
        muda = [
            HookMudaMetrics(HookMudaType.OVERPROCESSING, 1, 10.0, 10.0),
            HookMudaMetrics(HookMudaType.WAITING, 1, 15.0, 15.0),
        ]
        mura = HookMuraMetrics(0.5, 50.0, 10.0)
        muri = HookMuriMetrics(5.0, 3, 10, False)

        analysis = HookWasteAnalysis("c1", muda, mura, muri, 5, 100.0)

        assert analysis.total_waste_percentage == 25.0

    def test_unevenness_detection(self) -> None:
        """Test detection of unevenness problems."""
        muda: list[HookMudaMetrics] = []
        mura_uneven = HookMuraMetrics(1.2, 100.0, 10.0)
        muri = HookMuriMetrics(5.0, 3, 10, False)

        analysis = HookWasteAnalysis("c1", muda, mura_uneven, muri, 5, 100.0)

        assert analysis.has_unevenness_problem

        # Test without unevenness
        mura_even = HookMuraMetrics(0.3, 50.0, 40.0)
        good_analysis = HookWasteAnalysis("c2", muda, mura_even, muri, 5, 100.0)

        assert not good_analysis.has_unevenness_problem

    def test_overload_detection(self) -> None:
        """Test detection of overload problems."""
        muda: list[HookMudaMetrics] = []
        mura = HookMuraMetrics(0.5, 50.0, 10.0)

        # Test overloaded system
        muri_bad = HookMuriMetrics(15.0, 12, 10, True)
        overloaded = HookWasteAnalysis("c1", muda, mura, muri_bad, 15, 500.0)

        assert overloaded.has_overload_problem

        # Test normal system
        muri_ok = HookMuriMetrics(5.0, 3, 10, False)
        normal = HookWasteAnalysis("c2", muda, mura, muri_ok, 5, 100.0)

        assert not normal.has_overload_problem

    def test_zero_waste_baseline(self) -> None:
        """Test waste analysis with zero waste baseline."""
        muda: list[HookMudaMetrics] = []
        mura = HookMuraMetrics(0.1, 20.0, 18.0)
        muri = HookMuriMetrics(3.0, 2, 10, False)

        analysis = HookWasteAnalysis(
            cycle_id="baseline",
            muda_metrics=muda,
            mura_metrics=mura,
            muri_metrics=muri,
            total_hooks_executed=3,
            total_duration_ms=60.0,
        )

        assert analysis.total_waste_percentage == 0.0
        assert not analysis.has_unevenness_problem
        assert not analysis.has_overload_problem

    def test_high_waste_scenario(self) -> None:
        """Test waste analysis with high waste levels."""
        muda = [
            HookMudaMetrics(HookMudaType.OVERPROCESSING, 10, 150.0, 30.0),
            HookMudaMetrics(HookMudaType.WAITING, 5, 100.0, 20.0),
            HookMudaMetrics(HookMudaType.DEFECTS, 3, 75.0, 15.0),
        ]
        mura = HookMuraMetrics(1.8, 300.0, 10.0)
        muri = HookMuriMetrics(25.0, 20, 10, True)

        analysis = HookWasteAnalysis("high-waste", muda, mura, muri, 25, 500.0)

        assert analysis.total_waste_percentage == 65.0
        assert analysis.has_unevenness_problem
        assert analysis.has_overload_problem

    def test_single_waste_type(self) -> None:
        """Test analysis with only one waste type."""
        muda = [HookMudaMetrics(HookMudaType.OVERPROCESSING, 5, 50.0, 25.0)]
        mura = HookMuraMetrics(0.3, 30.0, 20.0)
        muri = HookMuriMetrics(5.0, 3, 10, False)

        analysis = HookWasteAnalysis("single", muda, mura, muri, 5, 200.0)

        assert len(analysis.muda_metrics) == 1
        assert analysis.total_waste_percentage == 25.0

    def test_multiple_hooks_executed(self) -> None:
        """Test analysis with varying hook execution counts."""
        muda = [HookMudaMetrics(HookMudaType.OVERPROCESSING, 2, 20.0, 10.0)]
        mura = HookMuraMetrics(0.4, 40.0, 30.0)
        muri = HookMuriMetrics(20.0, 15, 10, True)

        analysis = HookWasteAnalysis("multi", muda, mura, muri, 20, 200.0)

        assert analysis.total_hooks_executed == 20
        assert analysis.muri_metrics.hooks_per_tick == 20.0
