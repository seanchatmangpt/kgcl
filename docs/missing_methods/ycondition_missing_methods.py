"""Missing methods for YCondition class.

Copy these methods to src/kgcl/yawl/elements/y_condition.py

NOTE: This file wraps methods in a class for syntax validation.
When copying to the actual class, copy only the method definitions.
"""

from __future__ import annotations

from typing import Any


class YConditionStubs:
    """Generated stubs for missing YCondition methods."""

    def add(self, identifier: YIdentifier) -> None:
        """TODO: Implement add.

        Java signature: void add(YIdentifier identifier)
        """
        pass

    def add(self, pmgr: YPersistenceManager, identifier: YIdentifier) -> None:
        """TODO: Implement add.

        Java signature: void add(YPersistenceManager pmgr, YIdentifier identifier)
        """
        pass

    def clone(self) -> object:
        """TODO: Implement clone.

        Java signature: Object clone()
        """
        raise NotImplementedError

    def contains(self, identifier: YIdentifier) -> bool:
        """TODO: Implement contains.

        Java signature: boolean contains(YIdentifier identifier)
        """
        return False

    def containsIdentifier(self) -> bool:
        """TODO: Implement containsIdentifier.

        Java signature: boolean containsIdentifier()
        """
        return False

    def getAmount(self, identifier: YIdentifier) -> int:
        """TODO: Implement getAmount.

        Java signature: int getAmount(YIdentifier identifier)
        """
        return 0

    def getIdentifiers(self) -> list:
        """TODO: Implement getIdentifiers.

        Java signature: List getIdentifiers()
        """
        return []

    def isAnonymous(self) -> bool:
        """TODO: Implement isAnonymous.

        Java signature: boolean isAnonymous()
        """
        return False

    def remove(self, identifier: YIdentifier, amount: int) -> None:
        """TODO: Implement remove.

        Java signature: void remove(YIdentifier identifier, int amount)
        """
        pass

    def remove(self, pmgr: YPersistenceManager, identifier: YIdentifier, amount: int) -> None:
        """TODO: Implement remove.

        Java signature: void remove(YPersistenceManager pmgr, YIdentifier identifier, int amount)
        """
        pass

    def removeAll(self) -> None:
        """TODO: Implement removeAll.

        Java signature: void removeAll()
        """
        pass

    def removeAll(self, pmgr: YPersistenceManager) -> None:
        """TODO: Implement removeAll.

        Java signature: void removeAll(YPersistenceManager pmgr)
        """
        pass

    def removeAll(self, identifier: YIdentifier) -> None:
        """TODO: Implement removeAll.

        Java signature: void removeAll(YIdentifier identifier)
        """
        pass

    def removeAll(self, pmgr: YPersistenceManager, identifier: YIdentifier) -> None:
        """TODO: Implement removeAll.

        Java signature: void removeAll(YPersistenceManager pmgr, YIdentifier identifier)
        """
        pass

    def removeOne(self, identifier: YIdentifier) -> None:
        """TODO: Implement removeOne.

        Java signature: void removeOne(YIdentifier identifier)
        """
        pass

    def removeOne(self, pmgr: YPersistenceManager, identifier: YIdentifier) -> None:
        """TODO: Implement removeOne.

        Java signature: void removeOne(YPersistenceManager pmgr, YIdentifier identifier)
        """
        pass

    def removeOne(self) -> YIdentifier:
        """TODO: Implement removeOne.

        Java signature: YIdentifier removeOne()
        """
        raise NotImplementedError

    def removeOne(self, pmgr: YPersistenceManager) -> YIdentifier:
        """TODO: Implement removeOne.

        Java signature: YIdentifier removeOne(YPersistenceManager pmgr)
        """
        raise NotImplementedError

    def setImplicit(self, isImplicit: bool) -> None:
        """TODO: Implement setImplicit.

        Java signature: void setImplicit(boolean isImplicit)
        """
        pass

    def toXML(self) -> str:
        """TODO: Implement toXML.

        Java signature: String toXML()
        """
        return ""

    def verify(self, handler: YVerificationHandler) -> None:
        """TODO: Implement verify.

        Java signature: void verify(YVerificationHandler handler)
        """
        pass
