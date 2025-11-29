"""Tests for YIdentifier (token identity)."""

from __future__ import annotations

from kgcl.yawl.elements.y_identifier import YIdentifier


class TestYIdentifier:
    """Tests for token identity and lineage."""

    def test_create_identifier(self) -> None:
        """Create basic identifier."""
        token = YIdentifier(id="token-1")
        assert token.id == "token-1"
        assert token.parent is None
        assert token.children == []
        assert token.location is None
        assert token.data == {}

    def test_create_child(self) -> None:
        """Create child token."""
        parent = YIdentifier(id="parent")
        child = parent.create_child("child")

        assert child.parent is parent
        assert child in parent.children
        assert child.id == "child"

    def test_get_root(self) -> None:
        """Get root of lineage chain."""
        root = YIdentifier(id="root")
        child = root.create_child("child")
        grandchild = child.create_child("grandchild")

        assert root.get_root() is root
        assert child.get_root() is root
        assert grandchild.get_root() is root

    def test_is_ancestor_of(self) -> None:
        """Check ancestor relationships."""
        root = YIdentifier(id="root")
        child = root.create_child("child")
        grandchild = child.create_child("grandchild")

        assert root.is_ancestor_of(child)
        assert root.is_ancestor_of(grandchild)
        assert child.is_ancestor_of(grandchild)

        assert not child.is_ancestor_of(root)
        assert not grandchild.is_ancestor_of(root)

    def test_get_depth(self) -> None:
        """Get depth in lineage tree."""
        root = YIdentifier(id="root")
        child = root.create_child("child")
        grandchild = child.create_child("grandchild")

        assert root.get_depth() == 0
        assert child.get_depth() == 1
        assert grandchild.get_depth() == 2

    def test_get_ancestors(self) -> None:
        """Get all ancestors."""
        root = YIdentifier(id="root")
        child = root.create_child("child")
        grandchild = child.create_child("grandchild")

        ancestors = grandchild.get_ancestors()
        assert len(ancestors) == 2
        assert ancestors[0] is child
        assert ancestors[1] is root

    def test_merge_data(self) -> None:
        """Merge data into token."""
        token = YIdentifier(id="t1", data={"a": 1, "b": 2})
        token.merge_data({"b": 3, "c": 4})

        assert token.data == {"a": 1, "b": 3, "c": 4}

    def test_hash_and_equality(self) -> None:
        """Token identity based on ID."""
        t1 = YIdentifier(id="same")
        t2 = YIdentifier(id="same")
        t3 = YIdentifier(id="different")

        assert t1 == t2
        assert t1 != t3
        assert hash(t1) == hash(t2)

        # Can use in set
        token_set = {t1, t2, t3}
        assert len(token_set) == 2

    def test_location_tracking(self) -> None:
        """Track token location."""
        token = YIdentifier(id="t1")
        token.location = "condition-1"
        assert token.location == "condition-1"

        token.location = "condition-2"
        assert token.location == "condition-2"
