"""Token identifier in YAWL net (mirrors Java YIdentifier).

Each token has a unique ID and optional parent for tracking lineage.
Tokens carry data payload through the workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class YIdentifier:
    """Token identifier in YAWL net (mirrors Java YIdentifier).

    Each token has a unique ID and optional parent for tracking lineage
    through splits and joins. Tokens carry a data payload through the
    workflow execution.

    Parameters
    ----------
    id : str
        Unique identifier for this token
    parent : YIdentifier | None
        Parent token (for lineage tracking after splits)
    children : list[YIdentifier]
        Child tokens created from this token
    location : str | None
        Current condition or task ID where token resides
    data : dict[str, Any]
        Data payload carried by this token

    Examples
    --------
    >>> token = YIdentifier(id="case-1-0")
    >>> child = token.create_child("case-1-1")
    >>> child.parent is token
    True
    >>> token.is_ancestor_of(child)
    True
    """

    id: str
    parent: YIdentifier | None = None
    children: list[YIdentifier] = field(default_factory=list)
    location: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def create_child(self, child_id: str) -> YIdentifier:
        """Create child token (for AND-split).

        Parameters
        ----------
        child_id : str
            Unique ID for the child token

        Returns
        -------
        YIdentifier
            New child token with this token as parent

        Examples
        --------
        >>> parent = YIdentifier(id="case-1-0")
        >>> child = parent.create_child("case-1-1")
        >>> child.parent.id
        'case-1-0'
        """
        child = YIdentifier(id=child_id, parent=self)
        self.children.append(child)
        return child

    def get_root(self) -> YIdentifier:
        """Get root ancestor token.

        Returns
        -------
        YIdentifier
            The root token in the lineage chain

        Examples
        --------
        >>> root = YIdentifier(id="root")
        >>> child = root.create_child("child")
        >>> grandchild = child.create_child("grandchild")
        >>> grandchild.get_root().id
        'root'
        """
        current = self
        while current.parent is not None:
            current = current.parent
        return current

    def is_ancestor_of(self, other: YIdentifier) -> bool:
        """Check if this token is an ancestor of other.

        Parameters
        ----------
        other : YIdentifier
            Token to check ancestry for

        Returns
        -------
        bool
            True if this token is an ancestor of other

        Examples
        --------
        >>> root = YIdentifier(id="root")
        >>> child = root.create_child("child")
        >>> root.is_ancestor_of(child)
        True
        >>> child.is_ancestor_of(root)
        False
        """
        current = other.parent
        while current is not None:
            if current.id == self.id:
                return True
            current = current.parent
        return False

    def get_depth(self) -> int:
        """Get depth in lineage tree (root = 0).

        Returns
        -------
        int
            Depth from root token

        Examples
        --------
        >>> root = YIdentifier(id="root")
        >>> child = root.create_child("child")
        >>> root.get_depth()
        0
        >>> child.get_depth()
        1
        """
        depth = 0
        current = self.parent
        while current is not None:
            depth += 1
            current = current.parent
        return depth

    def get_ancestors(self) -> list[YIdentifier]:
        """Get all ancestor tokens (nearest first).

        Returns
        -------
        list[YIdentifier]
            List of ancestors from parent to root

        Examples
        --------
        >>> root = YIdentifier(id="root")
        >>> child = root.create_child("child")
        >>> grandchild = child.create_child("grandchild")
        >>> [a.id for a in grandchild.get_ancestors()]
        ['child', 'root']
        """
        ancestors = []
        current = self.parent
        while current is not None:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def merge_data(self, other_data: dict[str, Any]) -> None:
        """Merge data from another source into this token.

        Parameters
        ----------
        other_data : dict[str, Any]
            Data to merge (overwrites existing keys)

        Examples
        --------
        >>> token = YIdentifier(id="t1", data={"a": 1})
        >>> token.merge_data({"b": 2})
        >>> token.data
        {'a': 1, 'b': 2}
        """
        self.data.update(other_data)

    def __hash__(self) -> int:
        """Hash by ID for use in sets/dicts."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality by ID."""
        if not isinstance(other, YIdentifier):
            return NotImplemented
        return self.id == other.id
