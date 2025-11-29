"""Identifier bag utility for managing YIdentifier collections.

Manages collections of YIdentifier objects with quantity tracking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kgcl.yawl.elements.state.y_identifier import YIdentifier
    from kgcl.yawl.elements.y_net_element import YNetElement
    from kgcl.yawl.engine.y_persistence_manager import YPersistenceManager
    from kgcl.yawl.exceptions.y_persistence_exception import YPersistenceException


class YIdentifierBag:
    """Bag for managing YIdentifier objects with quantity tracking.

    Tracks identifiers and their quantities, managing locations through
    the persistence manager.

    Parameters
    ----------
    condition : YNetElement
        Net element condition associated with this bag
    """

    def __init__(self, condition: YNetElement) -> None:
        """Initialize identifier bag.

        Parameters
        ----------
        condition : YNetElement
            Net element condition
        """
        self._id_to_qty_map: dict[YIdentifier, int] = {}
        self._condition: YNetElement = condition

    def add_identifier(self, pmgr: YPersistenceManager, identifier: YIdentifier) -> None:
        """Add an identifier to the bag.

        Parameters
        ----------
        pmgr : YPersistenceManager
            Persistence manager
        identifier : YIdentifier
            Identifier to add

        Raises
        ------
        YPersistenceException
            If persistence operation fails
        """
        amount = self.get_amount(identifier)
        self._id_to_qty_map[identifier] = amount + 1
        identifier.add_location(pmgr, self._condition)

    def get_amount(self, identifier: YIdentifier) -> int:
        """Get quantity of identifier in bag.

        Parameters
        ----------
        identifier : YIdentifier
            Identifier to check

        Returns
        -------
        int
            Quantity of identifier (0 if not present)
        """
        return self._id_to_qty_map.get(identifier, 0)

    def contains(self, identifier: YIdentifier) -> bool:
        """Check if bag contains identifier.

        Parameters
        ----------
        identifier : YIdentifier
            Identifier to check

        Returns
        -------
        bool
            True if identifier is in bag
        """
        return identifier in self._id_to_qty_map

    def get_identifiers(self) -> list[YIdentifier]:
        """Get all identifiers in bag (with duplicates for quantity).

        Returns
        -------
        list[YIdentifier]
            List of identifiers, with each identifier repeated according
            to its quantity
        """
        id_list: list[YIdentifier] = []
        for identifier, amount in self._id_to_qty_map.items():
            for _ in range(amount):
                id_list.append(identifier)
        return id_list

    def remove(self, pmgr: YPersistenceManager, identifier: YIdentifier, amount_to_remove: int) -> None:
        """Remove identifiers from bag.

        Parameters
        ----------
        pmgr : YPersistenceManager
            Persistence manager
        identifier : YIdentifier
            Identifier to remove
        amount_to_remove : int
            Number of identifiers to remove

        Raises
        ------
        RuntimeError
            If amount_to_remove is invalid or identifier not in bag
        YPersistenceException
            If persistence operation fails
        """
        if identifier not in self._id_to_qty_map:
            raise RuntimeError(
                f"Cannot remove {amount_to_remove} tokens from YIdentifierBag:"
                f" {self._condition} - this bag contains no identifiers of type"
                f" {identifier}. It does have {self.get_identifiers()}"
                f" (locations of {identifier}: {identifier.get_locations()})"
            )

        amount_existing = self._id_to_qty_map[identifier]

        if amount_to_remove <= 0:
            raise RuntimeError(f"Cannot remove {amount_to_remove} from YIdentifierBag: {self._condition} {identifier}")

        if amount_to_remove > amount_existing:
            raise RuntimeError(
                f"Cannot remove {amount_to_remove} tokens from YIdentifierBag:"
                f" {self._condition} - this bag only contains {amount_existing}"
                f" identifiers of type {identifier}"
            )

        amount_left = amount_existing - amount_to_remove
        if amount_left > 0:
            self._id_to_qty_map[identifier] = amount_left
        else:
            del self._id_to_qty_map[identifier]

        identifier.remove_location(pmgr, self._condition)

    def remove_all(self, pmgr: YPersistenceManager) -> None:
        """Remove all identifiers from bag.

        Parameters
        ----------
        pmgr : YPersistenceManager
            Persistence manager

        Raises
        ------
        YPersistenceException
            If persistence operation fails
        """
        identifiers = set(self._id_to_qty_map.keys())
        for identifier in identifiers:
            while self._condition in identifier.get_locations():
                identifier.clear_location(pmgr, self._condition)
            del self._id_to_qty_map[identifier]
