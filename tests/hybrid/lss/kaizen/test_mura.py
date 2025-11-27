"""KZ-003: Mura (Unevenness) tests.

Kaizen Focus: MURA (斑) - Eliminate unevenness:
- Consistent timing across patterns
- Consistent triple generation
- Consistent state transitions
- Consistent naming conventions

CRITICAL: Uses REAL HybridEngine to measure consistency.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from kgcl.hybrid.wcp43_physics import WCP_PATTERN_CATALOG


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for Mura tests."""
    return HybridEngine()


class TestKZ003MuraUnevenness:
    """KZ-003: Test for inconsistent behavior that creates unevenness."""

    def test_timing_consistency(self, engine: HybridEngine) -> None:
        """Test that similar patterns have consistent timing."""
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

        result1 = engine.apply_physics()

        engine2 = HybridEngine()
        engine2.load_data(topology)
        result2 = engine2.apply_physics()

        timing_variance = abs(result1.duration_ms - result2.duration_ms) / result1.duration_ms * 100

        assert timing_variance < 50, f"Timing unevenness: {timing_variance}% variance"

    def test_delta_consistency(self, engine: HybridEngine) -> None:
        """Test that same patterns generate consistent deltas."""
        topology = """
        @prefix kgc: <https://kgc.org/ns/> .
        @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

        <urn:task:A> a yawl:Task ;
            kgc:status "Completed" ;
            yawl:hasSplit yawl:ControlTypeAnd ;
            yawl:flowsInto <urn:flow:a>, <urn:flow:b> .

        <urn:flow:a> yawl:nextElementRef <urn:task:A1> .
        <urn:flow:b> yawl:nextElementRef <urn:task:A2> .

        <urn:task:A1> a yawl:Task .
        <urn:task:A2> a yawl:Task .
        """
        engine.load_data(topology)
        result1 = engine.apply_physics()

        engine2 = HybridEngine()
        engine2.load_data(topology)
        result2 = engine2.apply_physics()

        assert result1.delta == result2.delta, f"Delta unevenness: {result1.delta} vs {result2.delta}"

    def test_naming_consistency(self) -> None:
        """Test that pattern naming is consistent."""
        verbs = {info["verb"] for info in WCP_PATTERN_CATALOG.values()}
        base_verbs = {"Transmute", "Copy", "Filter", "Await", "Void"}

        for verb in verbs:
            verb_parts = verb.split("+")
            for part in verb_parts:
                assert part in base_verbs, f"Inconsistent verb: {part}"
