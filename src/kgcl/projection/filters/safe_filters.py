"""Safe Jinja filters for string and collection manipulation.

Whitelisted filters for template rendering without security risks.
All filters are pure functions with no side effects.
"""

import re
from collections.abc import Callable, Sequence
from typing import Any


def snake_case(value: str) -> str:
    """Convert string to snake_case.

    Parameters
    ----------
    value : str
        Input string in any case format

    Returns
    -------
    str
        snake_case formatted string

    Examples
    --------
    >>> snake_case("HelloWorld")
    'hello_world'
    >>> snake_case("someCamelCase")
    'some_camel_case'
    >>> snake_case("Already_Snake")
    'already_snake'
    """
    # Insert underscore before uppercase letters that follow lowercase
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    # Insert underscore before uppercase letters that follow multiple uppercase
    s2 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s1)
    # Replace spaces and hyphens with underscores
    s3 = re.sub(r"[-\s]+", "_", s2)
    return s3.lower()


def camel_case(value: str) -> str:
    """Convert string to camelCase.

    Parameters
    ----------
    value : str
        Input string in any case format

    Returns
    -------
    str
        camelCase formatted string

    Examples
    --------
    >>> camel_case("hello_world")
    'helloWorld'
    >>> camel_case("Hello World")
    'helloWorld'
    >>> camel_case("already-kebab")
    'alreadyKebab'
    """
    # Split on underscores, hyphens, and spaces
    words = re.split(r"[-_\s]+", value)
    if not words:
        return ""
    # First word lowercase, rest title case
    return words[0].lower() + "".join(w.capitalize() for w in words[1:])


def pascal_case(value: str) -> str:
    """Convert string to PascalCase.

    Parameters
    ----------
    value : str
        Input string in any case format

    Returns
    -------
    str
        PascalCase formatted string

    Examples
    --------
    >>> pascal_case("hello_world")
    'HelloWorld'
    >>> pascal_case("some-kebab-case")
    'SomeKebabCase'
    >>> pascal_case("already PascalCase")
    'AlreadyPascalcase'
    """
    # Split on underscores, hyphens, and spaces
    words = re.split(r"[-_\s]+", value)
    return "".join(w.capitalize() for w in words)


def kebab_case(value: str) -> str:
    """Convert string to kebab-case.

    Parameters
    ----------
    value : str
        Input string in any case format

    Returns
    -------
    str
        kebab-case formatted string

    Examples
    --------
    >>> kebab_case("HelloWorld")
    'hello-world'
    >>> kebab_case("some_snake_case")
    'some-snake-case'
    >>> kebab_case("Already Kebab")
    'already-kebab'
    """
    # Insert hyphen before uppercase letters that follow lowercase
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    # Insert hyphen before uppercase letters that follow multiple uppercase
    s2 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", s1)
    # Replace underscores and spaces with hyphens
    s3 = re.sub(r"[_\s]+", "-", s2)
    return s3.lower()


def slugify(value: str) -> str:
    """Convert string to URL-safe slug.

    Parameters
    ----------
    value : str
        Input string to slugify

    Returns
    -------
    str
        URL-safe slug (lowercase, hyphens, alphanumeric only)

    Examples
    --------
    >>> slugify("Hello World!")
    'hello-world'
    >>> slugify("Complex: String (with) Special#Chars")
    'complex-string-with-specialchars'
    >>> slugify("  Multiple   Spaces  ")
    'multiple-spaces'
    """
    # Convert to lowercase
    value = value.lower()
    # Remove non-alphanumeric characters (except spaces and hyphens)
    value = re.sub(r"[^a-z0-9\s-]", "", value)
    # Replace spaces and multiple hyphens with single hyphen
    value = re.sub(r"[-\s]+", "-", value)
    # Strip leading/trailing hyphens
    return value.strip("-")


def truncate(value: str, length: int, suffix: str = "...") -> str:
    """Truncate string to maximum length with suffix.

    Parameters
    ----------
    value : str
        String to truncate
    length : int
        Maximum length including suffix
    suffix : str, optional
        Suffix to append if truncated (default: "...")

    Returns
    -------
    str
        Truncated string with suffix if needed

    Examples
    --------
    >>> truncate("Hello World", 8)
    'Hello...'
    >>> truncate("Short", 10)
    'Short'
    >>> truncate("Truncate me", 8, "…")
    'Trunca…'
    """
    if len(value) <= length:
        return value
    # Account for suffix length
    truncate_at = max(0, length - len(suffix))
    return value[:truncate_at] + suffix


def indent(value: str, width: int = 4, first: bool = False) -> str:
    """Indent each line of text.

    Parameters
    ----------
    value : str
        Text to indent
    width : int, optional
        Number of spaces to indent (default: 4)
    first : bool, optional
        Whether to indent first line (default: False)

    Returns
    -------
    str
        Indented text

    Examples
    --------
    >>> indent("line1\\nline2", 2)
    'line1\\n  line2'
    >>> indent("line1\\nline2", 2, first=True)
    '  line1\\n  line2'
    """
    lines = value.splitlines(keepends=True)
    if not lines:
        return value

    indent_str = " " * width
    if first:
        return "".join(indent_str + line for line in lines)
    # Don't indent first line
    return lines[0] + "".join(indent_str + line for line in lines[1:])


def sort_by[T](items: Sequence[T], key: str) -> list[T]:
    """Sort sequence of dictionaries by specified key.

    Parameters
    ----------
    items : Sequence[T]
        Sequence of dict-like objects to sort
    key : str
        Dictionary key to sort by

    Returns
    -------
    list[T]
        Sorted list

    Examples
    --------
    >>> items = [{"name": "Bob", "age": 30}, {"name": "Alice", "age": 25}]
    >>> sort_by(items, "name")
    [{'name': 'Alice', 'age': 25}, {'name': 'Bob', 'age': 30}]
    >>> sort_by(items, "age")
    [{'name': 'Alice', 'age': 25}, {'name': 'Bob', 'age': 30}]
    """
    # Type narrowing: assume items are dict-like with __getitem__
    return sorted(items, key=lambda x: x[key])


def unique[T](items: Sequence[T]) -> list[T]:
    """Remove duplicates while preserving order.

    Parameters
    ----------
    items : Sequence[T]
        Sequence with potential duplicates

    Returns
    -------
    list[T]
        List with duplicates removed, order preserved

    Examples
    --------
    >>> unique([1, 2, 2, 3, 1])
    [1, 2, 3]
    >>> unique(["a", "b", "a", "c"])
    ['a', 'b', 'c']
    """
    seen: set[T] = set()
    result: list[T] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def group_by(items: Sequence[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    """Group dictionaries by key value.

    Parameters
    ----------
    items : Sequence[dict[str, Any]]
        Sequence of dictionaries to group
    key : str
        Dictionary key to group by

    Returns
    -------
    dict[str, list[dict[str, Any]]]
        Dictionary mapping key values to lists of items

    Examples
    --------
    >>> items = [{"type": "A", "value": 1}, {"type": "B", "value": 2}, {"type": "A", "value": 3}]
    >>> result = group_by(items, "type")
    >>> result["A"]
    [{'type': 'A', 'value': 1}, {'type': 'A', 'value': 3}]
    >>> result["B"]
    [{'type': 'B', 'value': 2}]
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        group_key = str(item.get(key, ""))
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(item)
    return groups


def pluck(items: Sequence[dict[str, Any]], key: str) -> list[Any]:
    """Extract values for a key from sequence of dictionaries.

    Parameters
    ----------
    items : Sequence[dict[str, Any]]
        Sequence of dictionaries
    key : str
        Dictionary key to extract

    Returns
    -------
    list[Any]
        List of values for the specified key

    Examples
    --------
    >>> items = [{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]
    >>> pluck(items, "name")
    ['Alice', 'Bob']
    >>> pluck(items, "age")
    [25, 30]
    """
    return [item.get(key) for item in items]


# Export dictionary for Jinja environment
SAFE_FILTERS: dict[str, Callable[..., Any]] = {
    "snake_case": snake_case,
    "camel_case": camel_case,
    "pascal_case": pascal_case,
    "kebab_case": kebab_case,
    "slugify": slugify,
    "truncate": truncate,
    "indent": indent,
    "sort_by": sort_by,
    "unique": unique,
    "group_by": group_by,
    "pluck": pluck,
}
