"""Tests for WCP43RulesAdapter.

Tests verify RulesProvider protocol implementation wrapping wcp43_physics.
"""

from __future__ import annotations

from kgcl.hybrid.adapters.wcp43_rules_adapter import WCP43RulesAdapter


class TestWCP43RulesAdapterGetRules:
    """Tests for getting complete rules."""

    def test_get_rules_returns_string(self) -> None:
        """get_rules returns non-empty string."""
        adapter = WCP43RulesAdapter()
        rules = adapter.get_rules()

        assert isinstance(rules, str)
        assert len(rules) > 1000  # Complete rules are large

    def test_get_rules_contains_wcp1(self) -> None:
        """Complete rules contain WCP-1 (Sequence)."""
        adapter = WCP43RulesAdapter()
        rules = adapter.get_rules()

        assert "WCP-1" in rules
        assert "SEQUENCE" in rules

    def test_get_rules_contains_wcp43(self) -> None:
        """Complete rules contain WCP-43 (Explicit Termination)."""
        adapter = WCP43RulesAdapter()
        rules = adapter.get_rules()

        assert "WCP-43" in rules

    def test_get_rules_contains_prefixes(self) -> None:
        """Complete rules include standard prefixes."""
        adapter = WCP43RulesAdapter()
        rules = adapter.get_rules()

        assert "@prefix kgc:" in rules
        assert "@prefix yawl:" in rules


class TestWCP43RulesAdapterGetRuleSubset:
    """Tests for getting rule subsets."""

    def test_subset_basic_patterns(self) -> None:
        """Subset returns rules for specified patterns."""
        adapter = WCP43RulesAdapter()
        subset = adapter.get_rule_subset([1, 2, 3])

        assert "WCP-1" in subset
        assert "WCP-2" in subset
        assert "WCP-3" in subset

    def test_subset_excludes_other_patterns(self) -> None:
        """Subset excludes non-specified patterns."""
        adapter = WCP43RulesAdapter()
        subset = adapter.get_rule_subset([1])

        assert "WCP-1" in subset
        # WCP-43 should not be in the subset
        assert "WCP-43: EXPLICIT TERMINATION" not in subset

    def test_empty_subset_returns_prefixes(self) -> None:
        """Empty pattern list returns just prefixes."""
        adapter = WCP43RulesAdapter()
        subset = adapter.get_rule_subset([])

        assert "@prefix" in subset
        # Should be much smaller than full rules (prefixes only ~600 chars)
        assert len(subset) < 700


class TestWCP43RulesAdapterConvenienceMethods:
    """Tests for convenience methods."""

    def test_get_basic_patterns(self) -> None:
        """get_basic_patterns returns WCP 1-5."""
        adapter = WCP43RulesAdapter()
        basic = adapter.get_basic_patterns()

        assert "SEQUENCE" in basic
        assert "PARALLEL SPLIT" in basic

    def test_get_join_patterns(self) -> None:
        """get_join_patterns returns join-related patterns."""
        adapter = WCP43RulesAdapter()
        joins = adapter.get_join_patterns()

        # Should contain synchronization patterns
        assert "WCP-3" in joins or "SYNCHRONIZATION" in joins

    def test_get_cancellation_patterns(self) -> None:
        """get_cancellation_patterns returns cancellation patterns."""
        adapter = WCP43RulesAdapter()
        cancel = adapter.get_cancellation_patterns()

        assert "CANCEL" in cancel
