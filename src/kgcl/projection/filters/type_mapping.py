"""Type mapping filters for converting XSD types to language types.

Filters for mapping between XSD datatypes and Python, TypeScript, OpenAPI types.
Includes cardinality and naming convention conversions.
All filters are pure functions with no side effects.
"""

from collections.abc import Callable
from typing import Any

# XSD to Python type mappings
_XSD_TO_PYTHON: dict[str, str] = {
    "xsd:string": "str",
    "xsd:boolean": "bool",
    "xsd:integer": "int",
    "xsd:int": "int",
    "xsd:long": "int",
    "xsd:short": "int",
    "xsd:byte": "int",
    "xsd:decimal": "float",
    "xsd:float": "float",
    "xsd:double": "float",
    "xsd:dateTime": "datetime",
    "xsd:date": "date",
    "xsd:time": "time",
    "xsd:duration": "timedelta",
    "xsd:anyURI": "str",
    "xsd:base64Binary": "bytes",
    "xsd:hexBinary": "bytes",
}

# XSD to TypeScript type mappings
_XSD_TO_TYPESCRIPT: dict[str, str] = {
    "xsd:string": "string",
    "xsd:boolean": "boolean",
    "xsd:integer": "number",
    "xsd:int": "number",
    "xsd:long": "number",
    "xsd:short": "number",
    "xsd:byte": "number",
    "xsd:decimal": "number",
    "xsd:float": "number",
    "xsd:double": "number",
    "xsd:dateTime": "Date",
    "xsd:date": "Date",
    "xsd:time": "string",
    "xsd:duration": "string",
    "xsd:anyURI": "string",
    "xsd:base64Binary": "string",
    "xsd:hexBinary": "string",
}

# XSD to OpenAPI type mappings
_XSD_TO_OPENAPI: dict[str, dict[str, str]] = {
    "xsd:string": {"type": "string"},
    "xsd:boolean": {"type": "boolean"},
    "xsd:integer": {"type": "integer"},
    "xsd:int": {"type": "integer", "format": "int32"},
    "xsd:long": {"type": "integer", "format": "int64"},
    "xsd:short": {"type": "integer"},
    "xsd:byte": {"type": "integer"},
    "xsd:decimal": {"type": "number"},
    "xsd:float": {"type": "number", "format": "float"},
    "xsd:double": {"type": "number", "format": "double"},
    "xsd:dateTime": {"type": "string", "format": "date-time"},
    "xsd:date": {"type": "string", "format": "date"},
    "xsd:time": {"type": "string", "format": "time"},
    "xsd:duration": {"type": "string"},
    "xsd:anyURI": {"type": "string", "format": "uri"},
    "xsd:base64Binary": {"type": "string", "format": "byte"},
    "xsd:hexBinary": {"type": "string"},
}


def xsd_to_python(xsd_type: str) -> str:
    """Convert XSD datatype to Python type.

    Parameters
    ----------
    xsd_type : str
        XSD datatype (e.g., "xsd:string", "xsd:integer")

    Returns
    -------
    str
        Python type name (e.g., "str", "int")

    Examples
    --------
    >>> xsd_to_python("xsd:string")
    'str'
    >>> xsd_to_python("xsd:integer")
    'int'
    >>> xsd_to_python("xsd:dateTime")
    'datetime'
    >>> xsd_to_python("xsd:unknown")
    'Any'
    """
    return _XSD_TO_PYTHON.get(xsd_type, "Any")


def xsd_to_typescript(xsd_type: str) -> str:
    """Convert XSD datatype to TypeScript type.

    Parameters
    ----------
    xsd_type : str
        XSD datatype (e.g., "xsd:string", "xsd:integer")

    Returns
    -------
    str
        TypeScript type name (e.g., "string", "number")

    Examples
    --------
    >>> xsd_to_typescript("xsd:string")
    'string'
    >>> xsd_to_typescript("xsd:integer")
    'number'
    >>> xsd_to_typescript("xsd:boolean")
    'boolean'
    >>> xsd_to_typescript("xsd:unknown")
    'any'
    """
    return _XSD_TO_TYPESCRIPT.get(xsd_type, "any")


def xsd_to_openapi(xsd_type: str) -> dict[str, str]:
    """Convert XSD datatype to OpenAPI schema type.

    Parameters
    ----------
    xsd_type : str
        XSD datatype (e.g., "xsd:string", "xsd:integer")

    Returns
    -------
    dict[str, str]
        OpenAPI type schema (e.g., {"type": "integer", "format": "int32"})

    Examples
    --------
    >>> xsd_to_openapi("xsd:string")
    {'type': 'string'}
    >>> xsd_to_openapi("xsd:integer")
    {'type': 'integer'}
    >>> xsd_to_openapi("xsd:int")
    {'type': 'integer', 'format': 'int32'}
    >>> xsd_to_openapi("xsd:unknown")
    {'type': 'string'}
    """
    return _XSD_TO_OPENAPI.get(xsd_type, {"type": "string"})


def to_python_class(name: str) -> str:
    """Convert name to Python class name (PascalCase).

    Parameters
    ----------
    name : str
        Input name (e.g., "entity", "user_profile")

    Returns
    -------
    str
        Python class name in PascalCase

    Examples
    --------
    >>> to_python_class("entity")
    'Entity'
    >>> to_python_class("user_profile")
    'UserProfile'
    >>> to_python_class("http-client")
    'HttpClient'
    """
    # Split on underscores, hyphens, and spaces
    import re

    words = re.split(r"[-_\s]+", name)
    return "".join(w.capitalize() for w in words if w)


def to_typescript_interface(name: str) -> str:
    """Convert name to TypeScript interface name (IEntity convention).

    Parameters
    ----------
    name : str
        Input name (e.g., "entity", "user_profile")

    Returns
    -------
    str
        TypeScript interface name with I prefix

    Examples
    --------
    >>> to_typescript_interface("entity")
    'IEntity'
    >>> to_typescript_interface("user_profile")
    'IUserProfile'
    >>> to_typescript_interface("http-client")
    'IHttpClient'
    """
    class_name = to_python_class(name)
    return f"I{class_name}"


def cardinality_to_python(min_card: int, max_card: int | None) -> str:
    """Convert cardinality to Python type annotation.

    Parameters
    ----------
    min_card : int
        Minimum cardinality (0 or 1)
    max_card : int | None
        Maximum cardinality (None for unbounded)

    Returns
    -------
    str
        Python type annotation (e.g., "Optional[X]", "list[X]")

    Examples
    --------
    >>> cardinality_to_python(0, 1)
    'Optional[X]'
    >>> cardinality_to_python(1, 1)
    'X'
    >>> cardinality_to_python(0, None)
    'list[X]'
    >>> cardinality_to_python(1, None)
    'list[X]'
    >>> cardinality_to_python(0, 5)
    'list[X]'
    """
    # Unbounded or max > 1: list
    if max_card is None or max_card > 1:
        return "list[X]"

    # max_card == 1
    if min_card == 0:
        return "Optional[X]"

    # min_card == 1, max_card == 1
    return "X"


def cardinality_to_typescript(min_card: int, max_card: int | None) -> str:
    """Convert cardinality to TypeScript type annotation.

    Parameters
    ----------
    min_card : int
        Minimum cardinality (0 or 1)
    max_card : int | None
        Maximum cardinality (None for unbounded)

    Returns
    -------
    str
        TypeScript type annotation (e.g., "X | null", "X[]")

    Examples
    --------
    >>> cardinality_to_typescript(0, 1)
    'X | null'
    >>> cardinality_to_typescript(1, 1)
    'X'
    >>> cardinality_to_typescript(0, None)
    'X[]'
    >>> cardinality_to_typescript(1, None)
    'X[]'
    """
    # Unbounded or max > 1: array
    if max_card is None or max_card > 1:
        return "X[]"

    # max_card == 1
    if min_card == 0:
        return "X | null"

    # min_card == 1, max_card == 1
    return "X"


# Export dictionary for Jinja environment
TYPE_MAPPING_FILTERS: dict[str, Callable[..., Any]] = {
    "xsd_to_python": xsd_to_python,
    "xsd_to_typescript": xsd_to_typescript,
    "xsd_to_openapi": xsd_to_openapi,
    "to_python_class": to_python_class,
    "to_typescript_interface": to_typescript_interface,
    "cardinality_to_python": cardinality_to_python,
    "cardinality_to_typescript": cardinality_to_typescript,
}
