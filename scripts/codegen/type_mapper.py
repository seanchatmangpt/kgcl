"""Map Java types to Python types.

This module handles conversion of Java type declarations to their Python equivalents,
including generics, collections, and primitives.
"""

from __future__ import annotations

import re
from typing import Any

# Comprehensive Java to Python type mapping
JAVA_TO_PYTHON_TYPES: dict[str, str] = {
    # Primitives
    "byte": "int",
    "short": "int",
    "int": "int",
    "long": "int",
    "float": "float",
    "double": "float",
    "boolean": "bool",
    "char": "str",
    "void": "None",
    # Boxed primitives
    "Byte": "int",
    "Short": "int",
    "Integer": "int",
    "Long": "int",
    "Float": "float",
    "Double": "float",
    "Boolean": "bool",
    "Character": "str",
    # Common types
    "String": "str",
    "Object": "Any",
    "Date": "datetime",
    "Timestamp": "datetime",
    "BigDecimal": "Decimal",
    "BigInteger": "int",
    "UUID": "str",
    # Collections (non-generic forms)
    "List": "list[Any]",
    "Set": "set[Any]",
    "Map": "dict[str, Any]",
    "Collection": "list[Any]",
    "ArrayList": "list[Any]",
    "HashSet": "set[Any]",
    "HashMap": "dict[str, Any]",
    "LinkedList": "list[Any]",
    "TreeSet": "set[Any]",
    "TreeMap": "dict[str, Any]",
    # YAWL-specific types
    "YSpecificationID": "str",
    "YTask": "dict[str, Any]",
    "YNet": "dict[str, Any]",
    "YCondition": "dict[str, Any]",
    "Element": "Any",  # XML Element
    "Document": "Any",  # XML Document
}


class TypeMapper:
    """Map Java types to Python type hints.

    Handles primitive types, generics, collections, arrays, and complex nested types.
    """

    def __init__(self) -> None:
        """Initialize type mapper with default mappings."""
        self.type_map = JAVA_TO_PYTHON_TYPES.copy()

    def map_type(self, java_type: str) -> str:
        """Convert Java type to Python type hint.

        Parameters
        ----------
        java_type : str
            Java type string (e.g., "List<String>", "Map<String, Object>")

        Returns
        -------
        str
            Python type hint (e.g., "list[str]", "dict[str, Any]")

        Examples
        --------
        >>> mapper = TypeMapper()
        >>> mapper.map_type("String")
        'str'
        >>> mapper.map_type("List<String>")
        'list[str]'
        >>> mapper.map_type("Map<String, List<Integer>>")
        'dict[str, list[int]]'
        >>> mapper.map_type("String[]")
        'list[str]'
        """
        # Handle arrays first
        if "[]" in java_type:
            base_type = java_type.replace("[]", "")
            mapped_base = self._map_simple_type(base_type)
            return f"list[{mapped_base}]"

        # Handle generics
        if "<" in java_type and ">" in java_type:
            return self._map_generic_type(java_type)

        # Handle simple types
        return self._map_simple_type(java_type)

    def _map_simple_type(self, java_type: str) -> str:
        """Map a simple (non-generic) Java type.

        Parameters
        ----------
        java_type : str
            Simple Java type (no generics)

        Returns
        -------
        str
            Python type hint
        """
        # Remove whitespace
        java_type = java_type.strip()

        # Check direct mapping
        if java_type in self.type_map:
            return self.type_map[java_type]

        # Handle fully qualified names (e.g., java.util.List -> list[Any])
        if "." in java_type:
            simple_name = java_type.split(".")[-1]
            if simple_name in self.type_map:
                return self.type_map[simple_name]

        # Default to Any for unknown types
        return "Any"

    def _map_generic_type(self, java_type: str) -> str:
        """Map a generic Java type to Python type hint.

        Parameters
        ----------
        java_type : str
            Generic Java type (e.g., "List<String>", "Map<K, V>")

        Returns
        -------
        str
            Python type hint with generics
        """
        # Parse generic structure
        match = re.match(r"(\w+)<(.+)>", java_type.strip())
        if not match:
            return self._map_simple_type(java_type)

        base_type = match.group(1)
        type_args = match.group(2)

        # Map base type
        python_base = self._get_generic_base(base_type)

        # Parse and map type arguments
        python_args = self._parse_type_arguments(type_args)

        # Construct Python generic
        return f"{python_base}[{', '.join(python_args)}]"

    def _get_generic_base(self, base_type: str) -> str:
        """Get Python base type for a generic.

        Parameters
        ----------
        base_type : str
            Java generic base (e.g., "List", "Map", "Set")

        Returns
        -------
        str
            Python generic base (e.g., "list", "dict", "set")
        """
        mapping = {
            "List": "list",
            "ArrayList": "list",
            "LinkedList": "list",
            "Set": "set",
            "HashSet": "set",
            "TreeSet": "set",
            "Map": "dict",
            "HashMap": "dict",
            "TreeMap": "dict",
            "Collection": "list",
            "Optional": "Optional",
        }
        return mapping.get(base_type, "Any")

    def _parse_type_arguments(self, type_args: str) -> list[str]:
        """Parse and map generic type arguments.

        Parameters
        ----------
        type_args : str
            Comma-separated type arguments (may include nested generics)

        Returns
        -------
        list[str]
            List of mapped Python type arguments

        Examples
        --------
        >>> mapper = TypeMapper()
        >>> mapper._parse_type_arguments("String, Integer")
        ['str', 'int']
        >>> mapper._parse_type_arguments("String, List<Integer>")
        ['str', 'list[int]']
        """
        # Handle nested generics by tracking bracket depth
        args = []
        current = ""
        depth = 0

        for char in type_args:
            if char == "<":
                depth += 1
                current += char
            elif char == ">":
                depth -= 1
                current += char
            elif char == "," and depth == 0:
                args.append(current.strip())
                current = ""
            else:
                current += char

        # Add final argument
        if current.strip():
            args.append(current.strip())

        # Map each argument
        return [self.map_type(arg) for arg in args]

    def add_custom_mapping(self, java_type: str, python_type: str) -> None:
        """Add a custom type mapping.

        Parameters
        ----------
        java_type : str
            Java type name
        python_type : str
            Python type hint

        Examples
        --------
        >>> mapper = TypeMapper()
        >>> mapper.add_custom_mapping("CustomType", "CustomPythonType")
        >>> mapper.map_type("CustomType")
        'CustomPythonType'
        """
        self.type_map[java_type] = python_type
