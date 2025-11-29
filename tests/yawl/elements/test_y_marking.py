"""Tests for YMarking (token state)."""

from __future__ import annotations

from kgcl.yawl.state.y_marking import YMarking


class TestYMarking:
    """Tests for token marking operations."""

    def test_empty_marking(self) -> None:
        """Empty marking has no tokens."""
        marking = YMarking()
        assert marking.is_empty()
        assert marking.total_token_count() == 0
        assert not marking.has_tokens("c1")

    def test_add_token(self) -> None:
        """Add token to condition."""
        marking = YMarking()
        marking.add_token("c1", "t1")

        assert marking.has_tokens("c1")
        assert marking.token_count("c1") == 1
        assert "t1" in marking.get_tokens("c1")

    def test_add_multiple_tokens(self) -> None:
        """Add multiple tokens to same condition."""
        marking = YMarking()
        marking.add_token("c1", "t1")
        marking.add_token("c1", "t2")
        marking.add_token("c1", "t3")

        assert marking.token_count("c1") == 3
        assert marking.get_tokens("c1") == {"t1", "t2", "t3"}

    def test_remove_token(self) -> None:
        """Remove specific token."""
        marking = YMarking()
        marking.add_token("c1", "t1")
        marking.add_token("c1", "t2")

        result = marking.remove_token("c1", "t1")

        assert result is True
        assert marking.token_count("c1") == 1
        assert "t1" not in marking.get_tokens("c1")
        assert "t2" in marking.get_tokens("c1")

    def test_remove_nonexistent_token(self) -> None:
        """Remove token that doesn't exist."""
        marking = YMarking()
        marking.add_token("c1", "t1")

        result = marking.remove_token("c1", "t999")
        assert result is False

        result = marking.remove_token("c999", "t1")
        assert result is False

    def test_remove_one_token(self) -> None:
        """Remove arbitrary token from condition."""
        marking = YMarking()
        marking.add_token("c1", "t1")
        marking.add_token("c1", "t2")

        token_id = marking.remove_one_token("c1")

        assert token_id in {"t1", "t2"}
        assert marking.token_count("c1") == 1

    def test_remove_one_token_empty(self) -> None:
        """Remove from empty condition returns None."""
        marking = YMarking()

        token_id = marking.remove_one_token("c1")
        assert token_id is None

    def test_get_marked_conditions(self) -> None:
        """Get all conditions with tokens."""
        marking = YMarking()
        marking.add_token("c1", "t1")
        marking.add_token("c2", "t2")
        marking.add_token("c3", "t3")

        marked = set(marking.get_marked_conditions())
        assert marked == {"c1", "c2", "c3"}

    def test_total_token_count(self) -> None:
        """Count all tokens across conditions."""
        marking = YMarking()
        marking.add_token("c1", "t1")
        marking.add_token("c1", "t2")
        marking.add_token("c2", "t3")

        assert marking.total_token_count() == 3

    def test_clear(self) -> None:
        """Clear all tokens."""
        marking = YMarking()
        marking.add_token("c1", "t1")
        marking.add_token("c2", "t2")

        marking.clear()

        assert marking.is_empty()
        assert marking.total_token_count() == 0

    def test_copy(self) -> None:
        """Copy marking creates independent copy."""
        marking = YMarking()
        marking.add_token("c1", "t1")

        copy = marking.copy()

        # Modify original
        marking.add_token("c1", "t2")

        # Copy unchanged
        assert copy.token_count("c1") == 1
        assert marking.token_count("c1") == 2

    def test_repr(self) -> None:
        """String representation shows marked conditions."""
        marking = YMarking()
        marking.add_token("c1", "t1")

        repr_str = repr(marking)
        assert "c1" in repr_str
        assert "t1" in repr_str
