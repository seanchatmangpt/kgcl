"""Internal condition for multi-instance task state tracking (mirrors Java YInternalCondition).

YInternalCondition tracks identifiers in internal states of multi-instance tasks:
- mi_active: Instances that are active
- mi_entered: Instances that have entered
- mi_executing: Instances currently executing
- mi_complete: Instances that have completed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from kgcl.yawl.elements.y_identifier import YIdentifier

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_task import YTask


@dataclass
class YInternalCondition:
    """Internal condition for multi-instance task state tracking.

    Mirrors Java YInternalCondition. Tracks identifiers in internal states
    of multi-instance tasks using a bag-based approach (identifier -> count).

    Parameters
    ----------
    id : str
        Condition identifier (e.g., "mi_active", "mi_entered")
    my_task : YTask
        The task this condition belongs to
    _bag : dict[YIdentifier, int]
        Bag mapping identifier to count

    Examples
    --------
    >>> from kgcl.yawl.elements.y_task import YTask
    >>> task = YTask(id="task1")
    >>> cond = YInternalCondition(id="mi_active", my_task=task)
    >>> identifier = YIdentifier(id="case-1-0")
    >>> cond.add(None, identifier)
    >>> cond.contains_identifier()
    True
    """

    id: str
    my_task: Any  # YTask (circular import)
    _bag: dict[YIdentifier, int] = field(default_factory=dict, repr=False)

    # Constants for condition types
    MI_ACTIVE: str = "mi_active"
    MI_ENTERED: str = "mi_entered"
    MI_EXECUTING: str = "mi_executing"
    MI_COMPLETE: str = "mi_complete"

    def add(self, pmgr: Any | None, identifier: YIdentifier) -> None:
        """Add an identifier to the collection.

        Java signature: void add(YPersistenceManager pmgr, YIdentifier identifier)

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager (optional, for future use)
        identifier : YIdentifier
            Identifier to add

        Notes
        -----
        Mirrors Java YAWL YInternalCondition.add()
        """
        amount = self.get_amount(identifier)
        self._bag[identifier] = amount + 1
        if hasattr(identifier, "add_location"):
            identifier.add_location(pmgr, self)

    def contains(self, identifier: YIdentifier) -> bool:
        """Check if this contains the specified identifier.

        Java signature: boolean contains(YIdentifier identifier)

        Parameters
        ----------
        identifier : YIdentifier
            Identifier to check

        Returns
        -------
        bool
            True if this contains identifier

        Notes
        -----
        Mirrors Java YAWL YInternalCondition.contains()
        """
        return identifier in self._bag

    def contains_identifier(self) -> bool:
        """Check if this contains one or more identifier.

        Java signature: boolean containsIdentifier()

        Returns
        -------
        bool
            True if this contains at least one identifier

        Notes
        -----
        Mirrors Java YAWL YInternalCondition.containsIdentifier()
        """
        return len(self._bag) > 0

    def get_amount(self, identifier: YIdentifier) -> int:
        """Get the number of identifiers matching the specified identifier.

        Java signature: int getAmount(YIdentifier identifier)

        Parameters
        ----------
        identifier : YIdentifier
            Identifier to count

        Returns
        -------
        int
            Number of equal identifiers in this condition

        Notes
        -----
        Mirrors Java YAWL YInternalCondition.getAmount()
        """
        return self._bag.get(identifier, 0)

    def get_identifiers(self) -> list[YIdentifier]:
        """Get all identifiers in the condition.

        Java signature: List<YIdentifier> getIdentifiers()

        Returns
        -------
        list[YIdentifier]
            List of identifiers (with duplicates based on count)

        Notes
        -----
        Mirrors Java YAWL YInternalCondition.getIdentifiers()
        Returns a list where each identifier appears as many times as its count
        """
        id_list: list[YIdentifier] = []
        for identifier, amount in self._bag.items():
            for _ in range(amount):
                id_list.append(identifier)
        return id_list

    def remove_one(self, pmgr: Any | None, identifier: YIdentifier | None = None) -> YIdentifier | None:
        """Remove one identifier from the condition.

        Java signature: YIdentifier removeOne(YPersistenceManager pmgr)
        Java signature: void removeOne(YPersistenceManager pmgr, YIdentifier identifier)

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager (optional)
        identifier : YIdentifier | None
            If provided, remove one matching this identifier.
            If None, remove any one identifier.

        Returns
        -------
        YIdentifier | None
            The identifier that was removed, or None if none removed

        Notes
        -----
        Mirrors Java YAWL YInternalCondition.removeOne()
        """
        if identifier is not None:
            if identifier in self._bag:
                amount = self._bag[identifier]
                if amount > 1:
                    self._bag[identifier] = amount - 1
                else:
                    del self._bag[identifier]
                if hasattr(identifier, "remove_location"):
                    identifier.remove_location(pmgr, self)
                return identifier
            return None
        else:
            if not self._bag:
                return None
            first_identifier = next(iter(self._bag))
            return self.remove_one(pmgr, first_identifier)

    def remove(self, pmgr: Any | None, identifier: YIdentifier, amount: int) -> None:
        """Remove specified amount of identifiers matching the identifier.

        Java signature: void remove(YPersistenceManager pmgr, YIdentifier identifier, int amount)

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager (optional)
        identifier : YIdentifier
            Identifier to remove
        amount : int
            Number of matching identifiers to remove

        Raises
        ------
        ValueError
            If amount is greater than the number of identifiers held

        Notes
        -----
        Mirrors Java YAWL YInternalCondition.remove()
        """
        current_amount = self.get_amount(identifier)
        if amount > current_amount:
            raise ValueError(f"Attempted to remove {amount} identifiers but only {current_amount} available")
        if amount == current_amount:
            del self._bag[identifier]
        else:
            self._bag[identifier] = current_amount - amount
        if hasattr(identifier, "remove_location"):
            identifier.remove_location(pmgr, self)

    def remove_all(self, pmgr: Any | None, identifier: YIdentifier | None = None) -> None:
        """Remove all identifiers (optionally matching the specified identifier).

        Java signature: void removeAll(YPersistenceManager pmgr, YIdentifier identifier)
        Java signature: void removeAll(YPersistenceManager pmgr)

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager (optional)
        identifier : YIdentifier | None
            If provided, remove all matching this identifier.
            If None, remove all identifiers.

        Notes
        -----
        Mirrors Java YAWL YInternalCondition.removeAll()
        """
        if identifier is not None:
            amount = self.get_amount(identifier)
            if amount > 0:
                self.remove(pmgr, identifier, amount)
        else:
            for ident in list(self._bag.keys()):
                self.remove_all(pmgr, ident)

    def __str__(self) -> str:
        """String representation.

        Returns
        -------
        str
            String representation in format "id[task]"

        Notes
        -----
        Mirrors Java YAWL YInternalCondition.toString()
        """
        task_str = str(self.my_task) if self.my_task else "None"
        return f"{self.id}[{task_str}]"

    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"YInternalCondition(id={self.id!r}, task={self.my_task.id if self.my_task else None})"
