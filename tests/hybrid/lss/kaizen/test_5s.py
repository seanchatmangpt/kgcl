"""KZ-004: 5S Methodology tests.

Kaizen Focus: 5S - Workplace organization:
1. Seiri (Sort): Remove unnecessary patterns
2. Seiton (Set): Organize patterns logically
3. Seiso (Shine): Clean up pattern definitions
4. Seiketsu (Standardize): Consistent pattern structure
5. Shitsuke (Sustain): Maintain improvements

CRITICAL: Uses pattern catalog and engine for verification.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from kgcl.hybrid.wcp43_physics import WCP_PATTERN_CATALOG


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for 5S tests."""
    return HybridEngine()


class TestKZ004FiveSMethodology:
    """KZ-004: Test 5S methodology (Sort, Set, Shine, Standardize, Sustain)."""

    def test_5s_sort_remove_unnecessary(self) -> None:
        """5S-1: SEIRI (Sort) - Verify no unnecessary patterns."""
        assert len(WCP_PATTERN_CATALOG) == 43, "Should have exactly 43 patterns (no extras)"

        pattern_names = [info["name"] for info in WCP_PATTERN_CATALOG.values()]
        assert len(pattern_names) == len(set(pattern_names)), "Duplicate patterns detected"

    def test_5s_set_organize_logically(self) -> None:
        """5S-2: SEITON (Set) - Verify patterns are organized by category."""
        categories = {info["category"] for info in WCP_PATTERN_CATALOG.values()}

        expected_categories = {
            "Basic Control Flow",
            "Advanced Branching",
            "Structural",
            "Multiple Instances",
            "State-Based",
            "Cancellation",
            "Iteration",
            "Trigger",
            "Discriminator",
            "Partial Join",
            "MI Partial Join",
            "Advanced Sync",
            "Termination",
        }

        assert categories == expected_categories, f"Category mismatch: {categories - expected_categories}"

    def test_5s_shine_clean_definitions(self) -> None:
        """5S-3: SEISO (Shine) - Verify pattern definitions are clean."""
        for info in WCP_PATTERN_CATALOG.values():
            name = info["name"]
            assert len(name) < 50, f"Pattern name too long: {name}"
            assert name[0].isupper() or name.startswith("MI"), f"Pattern name should be capitalized: {name}"

    def test_5s_standardize_structure(self) -> None:
        """5S-4: SEIKETSU (Standardize) - Verify consistent structure."""
        required_fields = {"name", "verb", "category"}

        for pattern_num, info in WCP_PATTERN_CATALOG.items():
            actual_fields = set(info.keys())
            assert actual_fields == required_fields, f"Pattern {pattern_num} field mismatch: {actual_fields}"

    def test_5s_sustain_improvements(self, engine: HybridEngine) -> None:
        """5S-5: SHITSUKE (Sustain) - Verify improvements are sustained."""
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

        assert result1.delta == result2.delta, "Results not sustained (regression detected)"
