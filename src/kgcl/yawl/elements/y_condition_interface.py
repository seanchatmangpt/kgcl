"""Condition interface for token management (mirrors Java YConditionInterface).

This protocol defines the interface for classes that can hold tokens
(identifiers) in a YAWL workflow net.
"""

from __future__ import annotations

from typing import Protocol

from kgcl.yawl.elements.y_identifier import YIdentifier


class YConditionInterface(Protocol):
    """Protocol for classes that hold tokens (identifiers).

    This interface expresses the ability to hold tokens (Identifiers),
    nothing more. Used by conditions and other net elements that manage
    workflow state.

    Examples
    --------
    >>> class MyCondition:
    ...     def contains(self, identifier: YIdentifier) -> bool:
    ...         return identifier.id in self._tokens
    >>> condition = MyCondition()
    >>> identifier = YIdentifier("case-001")
    >>> condition.contains(identifier)
    """

    def contains(self, identifier: YIdentifier) -> bool:
        """Check if condition contains the specified identifier.

        Parameters
        ----------
        identifier : YIdentifier
            The identifier in question

        Returns
        -------
        bool
            True if this contains identifier
        """
        ...

    def contains_identifier(self) -> bool:
        """Check if condition has at least one identifier.

        Returns
        -------
        bool
            True if this contains one or more identifier
        """
        ...

    def get_amount(self, identifier: YIdentifier) -> int:
        """Get the number of identifiers matching the specified identifier.

        Parameters
        ----------
        identifier : YIdentifier
            The identifier in question

        Returns
        -------
        int
            The number of equal identifiers in the condition
        """
        ...

    def get_identifiers(self) -> list[YIdentifier]:
        """Get all the identifiers in the condition.

        Returns
        -------
        list[YIdentifier]
            List of the identifiers in the condition
        """
        ...

    def remove_one(self, identifier: YIdentifier | None = None) -> YIdentifier | None:
        """Remove one identifier from the condition.

        Parameters
        ----------
        identifier : YIdentifier | None
            If provided, remove one matching this identifier.
            If None, remove any one identifier.

        Returns
        -------
        YIdentifier | None
            The identifier that has been removed, or None if none removed
        """
        ...

    def remove(self, identifier: YIdentifier, amount: int) -> None:
        """Remove a specified number of identifiers matching the identifier.

        Parameters
        ----------
        identifier : YIdentifier
            An identifier matching the ones to be removed
        amount : int
            The number of matching identifiers to remove

        Raises
        ------
        ValueError
            If the amount specified is greater than the number of identifiers
            held inside the condition
        """
        ...

    def remove_all(self, identifier: YIdentifier | None = None) -> None:
        """Remove all identifiers (optionally matching the specified identifier).

        Parameters
        ----------
        identifier : YIdentifier | None
            If provided, remove all matching this identifier.
            If None, remove all identifiers.
        """
        ...

    def add(self, identifier: YIdentifier) -> None:
        """Add an identifier to the condition.

        Parameters
        ----------
        identifier : YIdentifier
            The identifier to add
        """
        ...
