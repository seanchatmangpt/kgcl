"""Dynamic value utility for runtime property evaluation.

Represents a value that is evaluated each time toString is called.
"""

from __future__ import annotations

import inspect


class DynamicValue:
    """Represents a value evaluated dynamically from an object property.

    The value is evaluated each time __str__ is called by invoking the
    appropriate getter method on the target object.

    Parameters
    ----------
    property : str
        Property name (data member name of the object)
    target : object
        Object containing the data member
    """

    def __init__(self, property: str, target: object) -> None:
        """Initialize dynamic value.

        Parameters
        ----------
        property : str
            Property name
        target : object
            Target object
        """
        self._property: str = ""
        self._target: object | None = None
        self.set_property(property)
        self.set_target(target)

    def get_property(self) -> str:
        """Get property name.

        Returns
        -------
        str
            Property name
        """
        return self._property

    def set_property(self, property: str) -> None:
        """Set property name.

        Parameters
        ----------
        property : str
            Property name (may be wrapped in dynamic{...})
        """
        if property and property.startswith("dynamic{"):
            end_idx = property.rfind("}")
            if end_idx != -1:
                property = property[8:end_idx]

        self._property = property

    def get_target(self) -> object | None:
        """Get target object.

        Returns
        -------
        object | None
            Target object
        """
        return self._target

    def set_target(self, target: object | None) -> None:
        """Set target object.

        Parameters
        ----------
        target : object | None
            Target object
        """
        self._target = target

    def __str__(self) -> str:
        """Get string representation by invoking getter method.

        Returns
        -------
        str
            String representation of property value
        """
        if self._target is None or not self._property:
            return ""

        # Find appropriate accessor method
        property_lower = self._property.lower()
        getter_name = f"get{property_lower}"
        is_getter_name = f"is{property_lower}"

        # Get all methods from the target object
        for name, method in inspect.getmembers(self._target, predicate=inspect.ismethod):
            if not inspect.signature(method).parameters:
                name_lower = name.lower()
                if name_lower == getter_name or name_lower == is_getter_name:
                    try:
                        result = method()
                        return str(result) if result is not None else ""
                    except Exception:
                        # Fall through to empty string
                        pass

        return ""
