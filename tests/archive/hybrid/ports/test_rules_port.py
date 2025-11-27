"""Tests for RulesProvider protocol.

Coverage tests for rules_port.py protocol definition.
"""

from __future__ import annotations

from kgcl.hybrid.ports.rules_port import RulesProvider


class MockRulesProvider:
    """Mock implementation of RulesProvider protocol."""

    def __init__(self, rules: str = "{ ?x a :Task } => { ?x :processed true } .") -> None:
        """Initialize mock rules provider."""
        self._rules = rules

    def get_rules(self) -> str:
        """Get complete rules."""
        return self._rules

    def get_rule_subset(self, pattern_ids: list[int]) -> str:
        """Get rules subset."""
        # Simple impl: return all rules regardless of pattern_ids
        return self._rules


class TestRulesProviderProtocol:
    """Test RulesProvider protocol compliance."""

    def test_protocol_detects_compliant_implementation(self) -> None:
        """Test isinstance check for compliant implementation."""
        provider = MockRulesProvider()
        assert isinstance(provider, RulesProvider)

    def test_protocol_requires_get_rules(self) -> None:
        """Test protocol requires get_rules method."""

        class IncompleteProvider:
            def get_rule_subset(self, pattern_ids: list[int]) -> str:
                return ""

        provider = IncompleteProvider()
        assert not isinstance(provider, RulesProvider)

    def test_protocol_requires_get_rule_subset(self) -> None:
        """Test protocol requires get_rule_subset method."""

        class IncompleteProvider:
            def get_rules(self) -> str:
                return ""

        provider = IncompleteProvider()
        assert not isinstance(provider, RulesProvider)


class TestMockRulesProviderImplementation:
    """Test MockRulesProvider implementation behavior."""

    def test_get_rules_returns_string(self) -> None:
        """Test get_rules returns N3 rules string."""
        provider = MockRulesProvider()
        rules = provider.get_rules()
        assert isinstance(rules, str)
        assert len(rules) > 0

    def test_get_rule_subset_returns_string(self) -> None:
        """Test get_rule_subset returns N3 rules string."""
        provider = MockRulesProvider()
        subset = provider.get_rule_subset([1, 2, 3])
        assert isinstance(subset, str)
        assert len(subset) > 0

    def test_custom_rules_preserved(self) -> None:
        """Test custom rules are stored correctly."""
        custom_rules = "@prefix wcp: <http://example.org/wcp#> . { ?t wcp:ready true } => { ?t wcp:execute true } ."
        provider = MockRulesProvider(custom_rules)
        assert provider.get_rules() == custom_rules
