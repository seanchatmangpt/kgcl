"""XNodeIO Protocol for objects that can serialize to/from XNode.

Pythonic equivalent to XNodeIO.java interface using Protocol.
"""

from __future__ import annotations

from typing import Protocol

from kgcl.yawl.util.xml.xnode import XNode


class XNodeIO(Protocol):
    """Protocol for objects that can serialize to/from XNode.

    Objects implementing this protocol can convert themselves to XNode
    and create new instances from XNode.
    """

    def from_xnode(self, node: XNode) -> None:
        """Populate this object from an XNode.

        Parameters
        ----------
        node : XNode
            XNode to read from
        """
        ...

    def to_xnode(self) -> XNode:
        """Convert this object to an XNode.

        Returns
        -------
        XNode
            XNode representation of this object
        """
        ...

    def new_instance(self, node: XNode) -> XNodeIO:
        """Create a new instance of this type from an XNode.

        Parameters
        ----------
        node : XNode
            XNode to create instance from

        Returns
        -------
        XNodeIO
            New instance populated from XNode
        """
        ...
