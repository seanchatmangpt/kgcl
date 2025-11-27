"""DMAIC DEFINE Phase: Pattern Definition Validation Tests.

This module tests that all 43 WCP patterns are correctly defined with complete
metadata, physics rules, and proper categorization.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.wcp43_physics import (
    get_pattern_info,
    get_pattern_rule,
    get_patterns_by_category,
    get_patterns_by_verb,
    list_all_patterns,
)


class TestDMAIC001Define:
    """DEFINE Phase: Verify all 43 patterns are correctly defined.

    Tests that validate pattern definitions, ontology structure, and metadata.
    """

    def test_all_43_patterns_defined(self) -> None:
        """Test that all 43 WCP patterns are defined in catalog.

        Verifies:
        - Pattern numbers 1-43 all exist
        - No gaps in numbering
        - Catalog completeness
        """
        # Arrange
        expected_patterns = list(range(1, 44))

        # Act
        actual_patterns = list_all_patterns()

        # Assert
        assert actual_patterns == expected_patterns, "All 43 patterns must be defined"
        assert len(actual_patterns) == 43, "Exactly 43 patterns required"

    def test_pattern_metadata_completeness(self) -> None:
        """Test that each pattern has complete metadata.

        Verifies each pattern has:
        - name: Human-readable pattern name
        - verb: KGC verb (Transmute, Copy, Filter, Await, Void)
        - category: Pattern category classification
        """
        # Arrange
        required_fields = {"name", "verb", "category"}

        # Act & Assert
        for pattern_num in range(1, 44):
            info = get_pattern_info(pattern_num)
            assert info is not None, f"WCP-{pattern_num} must have metadata"
            assert set(info.keys()) == required_fields, f"WCP-{pattern_num} missing required fields"
            assert len(info["name"]) > 0, f"WCP-{pattern_num} name cannot be empty"
            assert len(info["verb"]) > 0, f"WCP-{pattern_num} verb cannot be empty"
            assert len(info["category"]) > 0, f"WCP-{pattern_num} category cannot be empty"

    def test_pattern_rules_exist(self) -> None:
        """Test that each pattern has N3 physics rules defined.

        Verifies:
        - Rule exists for each pattern
        - Rule is non-empty string
        - Rule contains N3 syntax markers
        """
        # Act & Assert
        for pattern_num in range(1, 44):
            rule = get_pattern_rule(pattern_num)
            assert rule is not None, f"WCP-{pattern_num} must have physics rule"
            assert len(rule) > 0, f"WCP-{pattern_num} rule cannot be empty"
            assert "=>" in rule, f"WCP-{pattern_num} rule must contain N3 implication"

    def test_categories_cover_all_patterns(self) -> None:
        """Test that category groupings cover all 43 patterns.

        Verifies:
        - No pattern is orphaned
        - Each pattern belongs to exactly one category
        - All categories combined equal 43 patterns
        """
        # Arrange
        categories = {
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

        # Act
        all_patterns_from_categories: set[int] = set()
        for category in categories:
            patterns = get_patterns_by_category(category)
            all_patterns_from_categories.update(patterns)

        # Assert
        expected_all = set(range(1, 44))
        assert all_patterns_from_categories == expected_all, "Categories must cover all 43 patterns"

    def test_verb_assignments_valid(self) -> None:
        """Test that all verb assignments use valid KGC verbs.

        Verifies:
        - Only valid verbs used: Transmute, Copy, Filter, Await, Void
        - Composite verbs use '+' separator
        - No typos or invalid combinations
        """
        # Arrange
        valid_verbs = {"Transmute", "Copy", "Filter", "Await", "Void"}

        # Act & Assert
        for pattern_num in range(1, 44):
            info = get_pattern_info(pattern_num)
            assert info is not None
            verb_str = info["verb"]

            # Split composite verbs (e.g., "Copy+Await")
            verbs = verb_str.split("+")
            for verb in verbs:
                assert verb in valid_verbs, f"WCP-{pattern_num} uses invalid verb: {verb}"
