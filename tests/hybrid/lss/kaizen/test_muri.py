"""KZ-002: Muri (Overburden) tests.

Kaizen Focus: MURI (無理) - Eliminate overburden:
- Pattern complexity (rule count)
- Reasoning overhead (inference time)
- Memory pressure (triple count growth)
- Cognitive load (topology clarity)

CRITICAL: Uses REAL HybridEngine to measure burden.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from kgcl.hybrid.wcp43_physics import WCP_PATTERN_CATALOG
from tests.hybrid.lss.kaizen.metrics import KaizenMetric


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for Muri tests."""
    return HybridEngine()


class TestKZ002MuriOverburden:
    """KZ-002: Test for excessive complexity that burdens the system."""

    def test_pattern_complexity_burden(self, engine: HybridEngine) -> None:
        """Test that patterns don't impose excessive complexity."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:a> .

        <urn:task:B> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:b> .

        <urn:task:C> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:flowsInto <urn:flow:c> .

        <urn:flow:a> yawl:nextElementRef <urn:task:Join> .
        <urn:flow:b> yawl:nextElementRef <urn:task:Join> .
        <urn:flow:c> yawl:nextElementRef <urn:task:Join> .

        <urn:task:Join> a yawl:Task ;
            yawl:hasJoin yawl:ControlTypeAnd .
        """
        engine.load_data(topology)

        result = engine.apply_physics()

        metric = KaizenMetric(
            name="Reasoning Time for AND-join", before=50.0, after=result.duration_ms, target=30.0, unit="ms"
        )

        assert result.duration_ms < 100, f"Excessive reasoning time: {result.duration_ms}ms (overburden)"

    def test_memory_pressure_burden(self, engine: HybridEngine) -> None:
        """Test that patterns don't cause excessive memory growth."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:Split> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:a>, <urn:flow:b>, <urn:flow:c>, <urn:flow:d> .

        <urn:flow:a> yawl:nextElementRef <urn:task:A> .
        <urn:flow:b> yawl:nextElementRef <urn:task:B> .
        <urn:flow:c> yawl:nextElementRef <urn:task:C> .
        <urn:flow:d> yawl:nextElementRef <urn:task:D> .

        <urn:task:A> a yawl:Task .
        <urn:task:B> a yawl:Task .
        <urn:task:C> a yawl:Task .
        <urn:task:D> a yawl:Task .
        """
        engine.load_data(topology)

        results = engine.run_to_completion(max_ticks=10)
        total_delta = sum(r.delta for r in results)

        metric = KaizenMetric(
            name="Memory Growth for 4-way Split", before=50.0, after=float(total_delta), target=30.0, unit="triples"
        )

        assert total_delta < 100, f"Excessive memory growth: {total_delta} triples (overburden)"

    def test_cognitive_load_burden(self) -> None:
        """Test that pattern catalog is maintainable (not overburdened)."""
        assert len(WCP_PATTERN_CATALOG) == 43, "Should have exactly 43 patterns"

        for pattern_num, info in WCP_PATTERN_CATALOG.items():
            assert "name" in info, f"Pattern {pattern_num} missing name"
            assert "verb" in info, f"Pattern {pattern_num} missing verb"
            assert "category" in info, f"Pattern {pattern_num} missing category"

        categories = [info["category"] for info in WCP_PATTERN_CATALOG.values()]
        category_counts = {cat: categories.count(cat) for cat in set(categories)}

        max_category_size = max(category_counts.values())
        assert max_category_size <= 15, f"Category overburden: {max_category_size} patterns in one category"
