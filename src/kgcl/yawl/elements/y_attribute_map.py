"""Extended attribute map with dynamic values (mirrors Java YAttributeMap).

YAttributeMap extends a standard map to support:
- Dynamic values that are evaluated on access
- XML serialization (attributes and elements)
- Boolean value conversion
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class DynamicValue:
    """Dynamic value evaluated on access (mirrors Java DynamicValue).

    Parameters
    ----------
    property_name : str
        Property name to access on target
    target : Any
        Object containing the property
    """

    property_name: str
    target: Any

    def __str__(self) -> str:
        """Evaluate and return property value.

        Returns
        -------
        str
            String representation of property value
        """
        if self.target is None:
            return ""

        # Try to get property via getter method
        prop_lower = self.property_name.lower()
        for attr_name in dir(self.target):
            if attr_name.lower() == f"get{prop_lower}" or attr_name.lower() == f"is{prop_lower}":
                try:
                    method = getattr(self.target, attr_name)
                    if callable(method):
                        result = method()
                        return str(result) if result is not None else ""
                except Exception:
                    pass

        # Try direct attribute access
        try:
            value = getattr(self.target, self.property_name, None)
            if value is not None:
                return str(value)
        except Exception:
            pass

        return ""


class YAttributeMap(dict[str, str]):
    """Extended map of key=attribute pairs (mirrors Java YAttributeMap).

    Supports both static string values and dynamic values that are
    evaluated each time they are accessed.

    Parameters
    ----------
    attributes : dict[str, str] | None
        Initial attributes to populate

    Examples
    --------
    >>> attrs = YAttributeMap({"key1": "value1", "key2": "value2"})
    >>> attrs.get("key1")
    'value1'
    >>> attrs.get_boolean("enabled")
    False
    """

    def __init__(self, attributes: dict[str, str] | None = None) -> None:
        """Initialize attribute map."""
        super().__init__()
        self._dynamics: dict[str, DynamicValue] = {}
        if attributes:
            self.update(attributes)

    def set(self, attributes: dict[str, str]) -> None:
        """Replace stored attributes with new ones.

        Parameters
        ----------
        attributes : dict[str, str]
            New attribute key-value pairs
        """
        self.clear()
        self._dynamics.clear()
        self.update(attributes)

    def get_boolean(self, key: str) -> bool:
        """Get boolean value for key.

        Parameters
        ----------
        key : str
            Attribute key

        Returns
        -------
        bool
            True if value is "true" (case-insensitive), False otherwise
        """
        value = self.get_value(key)
        return value is not None and value.lower() == "true"

    def put_dynamic(self, key: str, value: DynamicValue) -> DynamicValue:
        """Add dynamic value.

        Parameters
        ----------
        key : str
            Key for dynamic value
        value : DynamicValue
            Dynamic value to store

        Returns
        -------
        DynamicValue
            The added dynamic value
        """
        old = self._dynamics.get(key)
        self._dynamics[key] = value
        return old if old else value

    def get(self, key: str) -> str | None:  # type: ignore[override]
        """Get stored value (evaluates dynamic values).

        Parameters
        ----------
        key : str
            Key to retrieve

        Returns
        -------
        str | None
            String value, or None if not found
        """
        return self.get_value(key)

    def remove(self, key: str) -> None:
        """Remove value (static or dynamic).

        Parameters
        ----------
        key : str
            Key to remove
        """
        if key in self:
            super().__delitem__(key)
        elif key in self._dynamics:
            del self._dynamics[key]

    def transform_dynamic_values(self, owner: Any) -> None:
        """Transform dynamic{...} strings to DynamicValue objects.

        Parameters
        ----------
        owner : Any
            Object to use as target for dynamic values
        """
        keys_to_remove: list[str] = []
        for key, value in self.items():
            if isinstance(value, str) and value.startswith("dynamic{"):
                # Extract property name from dynamic{property}
                end_pos = value.rindex("}")
                if end_pos > 8:
                    prop_name = value[8:end_pos]
                    self._dynamics[key] = DynamicValue(prop_name, owner)
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            super().__delitem__(key)

    def to_xml(self, key: str | None = None) -> str:
        """Write attributes in XML format.

        Parameters
        ----------
        key : str | None
            Single key to write, or None for all

        Returns
        -------
        str
            XML attribute string(s)
        """
        if key is not None:
            value = self.get_value(key)
            if value is None:
                return ""
            # Escape XML special characters
            escaped = value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
            return f'{key}="{escaped}"'

        # All attributes
        xml_parts: list[str] = []
        for k in self.keys():
            attr_xml = self.to_xml(k)
            if attr_xml:
                xml_parts.append(attr_xml)
        return " " + " ".join(xml_parts) if xml_parts else ""

    def to_xml_elements(self) -> str:
        """Write attributes as XML elements.

        Returns
        -------
        str
            XML element string
        """
        xml_parts: list[str] = []
        for key in self.keys():
            value = self.get_value(key)
            if value is not None:
                escaped = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                xml_parts.append(f"<{key}>{escaped}</{key}>")
        return " " + " ".join(xml_parts) if xml_parts else ""

    def from_xml_elements(self, xml: str) -> None:
        """Parse XML elements into attributes.

        Parameters
        ----------
        xml : str
            XML string containing element tags
        """
        # Simple XML parsing - for full implementation would use xml.etree
        # This is a simplified version
        import re

        self.clear()
        pattern = r"<(\w+)>(.*?)</\1>"
        for match in re.finditer(pattern, xml, re.DOTALL):
            key = match.group(1)
            value = match.group(2)
            # Unescape
            value = value.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
            self[key] = value

    def get_value(self, key: str) -> str | None:
        """Get stored value (tries static first, then dynamic).

        Parameters
        ----------
        key : str
            Key to retrieve

        Returns
        -------
        str | None
            String value, or None if not found
        """
        # Try static map first
        if key in self:
            return super().__getitem__(key)

        # Try dynamic map
        dynamic = self._dynamics.get(key)
        if dynamic is not None:
            return str(dynamic)

        return None
