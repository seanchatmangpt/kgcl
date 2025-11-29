"""Tests for YCondition token operations matching Java YAWL.

Java reference: YCondition.java token management methods.
"""

from __future__ import annotations

import pytest

from kgcl.yawl.elements.y_condition import YCondition


class TestTokenManagement:
    """Test token add/remove/query operations."""

    def test_add_single_token(self) -> None:
        """Adding token makes it queryable."""
        cond = YCondition(id="c1")
        cond.add("case-001")

        assert cond.contains("case-001")
        assert cond.get_amount("case-001") == 1

    def test_add_multiple_tokens_same_identifier(self) -> None:
        """Adding multiple tokens increments count."""
        cond = YCondition(id="c1")
        cond.add("case-001", amount=3)

        assert cond.get_amount("case-001") == 3

    def test_add_tokens_different_identifiers(self) -> None:
        """Can track multiple case identifiers."""
        cond = YCondition(id="c1")
        cond.add("case-001")
        cond.add("case-002")

        assert cond.contains("case-001")
        assert cond.contains("case-002")
        assert len(cond.get_identifiers()) == 2

    def test_remove_token(self) -> None:
        """Removing token decrements count."""
        cond = YCondition(id="c1")
        cond.add("case-001", amount=2)
        cond.remove("case-001")

        assert cond.get_amount("case-001") == 1
        assert cond.contains("case-001")

    def test_remove_last_token_removes_identifier(self) -> None:
        """Removing last token removes identifier from tracking."""
        cond = YCondition(id="c1")
        cond.add("case-001")
        cond.remove("case-001")

        assert not cond.contains("case-001")
        assert cond.get_amount("case-001") == 0

    def test_remove_more_tokens_than_exist_raises(self) -> None:
        """Cannot remove more tokens than exist."""
        cond = YCondition(id="c1")
        cond.add("case-001", amount=2)

        with pytest.raises(ValueError, match="Cannot remove 3 tokens, only 2 exist"):
            cond.remove("case-001", amount=3)

    def test_contains_identifier_empty(self) -> None:
        """New condition contains no identifiers."""
        cond = YCondition(id="c1")
        assert not cond.contains_identifier()

    def test_contains_identifier_with_tokens(self) -> None:
        """Condition with tokens reports contains_identifier."""
        cond = YCondition(id="c1")
        cond.add("case-001")
        assert cond.contains_identifier()

    def test_get_identifiers_empty(self) -> None:
        """Empty condition returns empty list."""
        cond = YCondition(id="c1")
        assert cond.get_identifiers() == []

    def test_get_identifiers_multiple(self) -> None:
        """Returns all tracked identifiers."""
        cond = YCondition(id="c1")
        cond.add("case-001")
        cond.add("case-002")
        cond.add("case-003")

        identifiers = cond.get_identifiers()
        assert len(identifiers) == 3
        assert set(identifiers) == {"case-001", "case-002", "case-003"}

    def test_remove_all(self) -> None:
        """Remove all clears all tokens."""
        cond = YCondition(id="c1")
        cond.add("case-001")
        cond.add("case-002", amount=5)
        cond.add("case-003", amount=2)

        cond.remove_all()

        assert not cond.contains_identifier()
        assert cond.get_identifiers() == []
        assert cond.get_amount("case-001") == 0


class TestPetriNetSemantics:
    """Test Petri net token semantics."""

    def test_input_condition_initial_token(self) -> None:
        """Input condition can receive initial token."""
        from kgcl.yawl.elements.y_condition import ConditionType

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        start.add("case-001")

        assert start.contains("case-001")
        assert start.is_input_condition()

    def test_token_flow_through_conditions(self) -> None:
        """Tokens can be moved between conditions."""
        c1 = YCondition(id="c1")
        c2 = YCondition(id="c2")

        # Add token to c1
        c1.add("case-001")
        assert c1.contains("case-001")
        assert not c2.contains("case-001")

        # Move token c1 -> c2 (task execution)
        c1.remove("case-001")
        c2.add("case-001")

        assert not c1.contains("case-001")
        assert c2.contains("case-001")

    def test_multiple_tokens_same_condition(self) -> None:
        """Condition can hold multiple tokens (colored Petri net)."""
        cond = YCondition(id="c1")

        # Parallel execution - multiple case instances
        cond.add("case-001")
        cond.add("case-002")
        cond.add("case-003")

        assert cond.get_amount("case-001") == 1
        assert cond.get_amount("case-002") == 1
        assert cond.get_amount("case-003") == 1
        assert len(cond.get_identifiers()) == 3
