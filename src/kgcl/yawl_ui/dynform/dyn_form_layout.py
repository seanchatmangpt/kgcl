"""Form layout container for YAWL dynamic forms."""

from __future__ import annotations

from typing import Any


class DynFormLayout:
    """Container for form components.

    This class holds the assembled form components in a hierarchical structure.

    Attributes
    ----------
    _name : str
        Form name (root element name)
    _children : list[Any]
        Child components
    """

    def __init__(self, name: str) -> None:
        """Initialize form layout.

        Parameters
        ----------
        name : str
            Form name (root element)
        """
        self._name = name
        self._children: list[Any] = []

    def add(self, components: list[Any] | Any) -> None:
        """Add components to layout.

        Parameters
        ----------
        components : list[Any] | Any
            Component or list of components to add
        """
        if isinstance(components, list):
            self._children.extend(components)
        else:
            self._children.append(components)

    def get_children(self) -> list[Any]:
        """Get child components.

        Returns
        -------
        list[Any]
            List of child components
        """
        return self._children

    def get_name(self) -> str:
        """Get form name.

        Returns
        -------
        str
            Form name
        """
        return self._name
