"""Pattern Catalog Validation Tests.

This module validates the WCP-43 pattern catalog completeness and correctness.
Tests ensure all 43 patterns are present with valid metadata.
"""

from __future__ import annotations

from kgcl.hybrid.wcp43_physics import WCP_PATTERN_CATALOG, list_all_patterns


class TestWCPPatternCatalog:
    """Verify the WCP-43 pattern catalog is complete and correct."""

    def test_catalog_has_43_patterns(self) -> None:
        """Verify catalog contains exactly 43 patterns."""
        patterns = list_all_patterns()
        assert len(patterns) == 43, f"Expected 43 patterns, got {len(patterns)}"
        assert patterns == list(range(1, 44)), "Patterns should be 1-43"

    def test_all_patterns_have_metadata(self) -> None:
        """Verify each pattern has name, verb, and category."""
        for wcp_num in range(1, 44):
            info = WCP_PATTERN_CATALOG.get(wcp_num)
            assert info is not None, f"WCP-{wcp_num} missing from catalog"
            assert "name" in info, f"WCP-{wcp_num} missing name"
            assert "verb" in info, f"WCP-{wcp_num} missing verb"
            assert "category" in info, f"WCP-{wcp_num} missing category"

    def test_verbs_are_valid(self) -> None:
        """Verify all verbs are from the 5 KGC verbs."""
        valid_verbs = {"Transmute", "Copy", "Filter", "Await", "Void"}
        for wcp_num in range(1, 44):
            info = WCP_PATTERN_CATALOG[wcp_num]
            verb_parts = info["verb"].replace("+", ",").split(",")
            for part in verb_parts:
                part = part.strip()
                assert part in valid_verbs, f"WCP-{wcp_num} has invalid verb '{part}'. Valid verbs: {valid_verbs}"
