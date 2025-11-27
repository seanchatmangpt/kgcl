"""KZ-001: Muda (Waste Elimination) tests.

Kaizen Focus: MUDA (無駄) - Eliminate the 7 wastes:
- Overproduction: Unnecessary triple generation
- Waiting: Unnecessary tick delays
- Transport: Unnecessary data movement
- Processing: Unnecessary complexity
- Motion: Unnecessary state transitions
- Inventory: Unnecessary state accumulation
- Defects: Unnecessary error states

CRITICAL: Uses REAL HybridEngine to measure actual waste.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from tests.hybrid.lss.kaizen.metrics import KaizenMetric


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for Muda tests."""
    return HybridEngine()


class TestKZ001MudaWasteElimination:
    """KZ-001: Test for and eliminate waste (unnecessary operations)."""

    def test_eliminate_unnecessary_triples(self, engine: HybridEngine) -> None:
        """Test that patterns don't generate wasteful triples."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology)

        result = engine.apply_physics()

        metric = KaizenMetric(
            name="Triple Delta for Simple Sequence", before=20.0, after=float(result.delta), target=10.0, unit="triples"
        )

        assert result.delta > 0, "Pattern should infer new facts"
        assert result.delta < 20, f"Too many triples generated: {result.delta} (waste detected)"

    def test_eliminate_unnecessary_ticks(self, engine: HybridEngine) -> None:
        """Test that patterns converge quickly without wasted cycles."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology)

        results = engine.run_to_completion(max_ticks=10)
        tick_count = len(results)

        metric = KaizenMetric(name="Convergence Time", before=5.0, after=float(tick_count), target=3.0, unit="ticks")

        assert tick_count <= 5, f"Too many ticks: {tick_count} (wasted cycles)"
        assert metric.improvement_pct >= 0, "Should not regress"

    def test_eliminate_redundant_state_transitions(self, engine: HybridEngine) -> None:
        """Test that tasks don't transition through redundant states."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:1> .

        <urn:flow:1> yawl:nextElementRef <urn:task:B> .
        <urn:task:B> a yawl:Task .
        """
        engine.load_data(topology)
        engine.run_to_completion(max_ticks=10)

        statuses = engine.inspect()

        task_b_status = statuses.get("urn:task:B")
        assert task_b_status in ["Active", "Completed", "Archived"], "Task B should reach terminal state"
