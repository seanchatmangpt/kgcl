"""RDF-specific Jinja filters for URI and literal manipulation.

Filters for extracting components from URIs, CURIEs, and RDF literals.
All filters are pure functions with no side effects.
"""

import re
from collections.abc import Callable
from typing import Any


def uri_local_name(uri: str) -> str:
    """Extract local name from URI.

    Parameters
    ----------
    uri : str
        Full URI (e.g., "http://example.org/schema#Person")

    Returns
    -------
    str
        Local name part after # or final /

    Examples
    --------
    >>> uri_local_name("http://example.org/schema#Person")
    'Person'
    >>> uri_local_name("http://example.org/schema/Person")
    'Person'
    >>> uri_local_name("http://example.org/")
    ''
    """
    # Try splitting on # first
    if "#" in uri:
        return uri.split("#")[-1]
    # Otherwise split on / and take last non-empty part
    parts = uri.rstrip("/").split("/")
    return parts[-1] if parts else ""


def uri_namespace(uri: str) -> str:
    """Extract namespace from URI.

    Parameters
    ----------
    uri : str
        Full URI (e.g., "http://example.org/schema#Person")

    Returns
    -------
    str
        Namespace part before # or final /

    Examples
    --------
    >>> uri_namespace("http://example.org/schema#Person")
    'http://example.org/schema#'
    >>> uri_namespace("http://example.org/schema/Person")
    'http://example.org/schema/'
    >>> uri_namespace("http://example.org/")
    'http://example.org/'
    """
    # Split on # if present
    if "#" in uri:
        return uri.rsplit("#", 1)[0] + "#"
    # If ends with /, return as-is
    if uri.endswith("/"):
        return uri
    # Otherwise split on / and keep everything except last part
    parts = uri.rsplit("/", 1)
    return parts[0] + "/" if len(parts) > 1 else uri


def uri_to_curie(uri: str, prefixes: dict[str, str]) -> str:
    """Convert URI to CURIE using prefix mappings.

    Parameters
    ----------
    uri : str
        Full URI to convert
    prefixes : dict[str, str]
        Mapping of namespace URIs to prefixes

    Returns
    -------
    str
        CURIE (e.g., "schema:Person") or original URI if no match

    Examples
    --------
    >>> prefixes = {"http://example.org/schema#": "ex"}
    >>> uri_to_curie("http://example.org/schema#Person", prefixes)
    'ex:Person'
    >>> uri_to_curie("http://other.org/Thing", prefixes)
    'http://other.org/Thing'
    """
    namespace = uri_namespace(uri)
    local_name = uri_local_name(uri)

    # Look for matching prefix
    prefix = prefixes.get(namespace)
    if prefix:
        return f"{prefix}:{local_name}"

    # No match, return original URI
    return uri


def literal_value(literal: str) -> str:
    """Extract value from typed literal.

    Parameters
    ----------
    literal : str
        RDF literal (e.g., '"42"^^xsd:integer' or '"hello"@en')

    Returns
    -------
    str
        Value without quotes, type, or language tag

    Examples
    --------
    >>> literal_value('"42"^^xsd:integer')
    '42'
    >>> literal_value('"hello"@en')
    'hello'
    >>> literal_value('"plain"')
    'plain'
    >>> literal_value("unquoted")
    'unquoted'
    """
    # Match quoted string
    match = re.match(r'^"(.*?)"', literal)
    if match:
        return match.group(1)
    # No quotes, return as-is
    return literal


def literal_lang(literal: str) -> str | None:
    """Extract language tag from literal.

    Parameters
    ----------
    literal : str
        RDF literal (e.g., '"hello"@en')

    Returns
    -------
    str | None
        Language tag (e.g., "en") or None if not present

    Examples
    --------
    >>> literal_lang('"hello"@en')
    'en'
    >>> literal_lang('"bonjour"@fr-CA')
    'fr-CA'
    >>> literal_lang('"42"^^xsd:integer')
    >>> literal_lang('"plain"')
    """
    # Match language tag after @
    match = re.search(r"@([a-zA-Z]{2}(?:-[a-zA-Z]{2})?)\s*$", literal)
    return match.group(1) if match else None


def literal_datatype(literal: str) -> str | None:
    """Extract datatype URI from typed literal.

    Parameters
    ----------
    literal : str
        RDF literal (e.g., '"42"^^xsd:integer')

    Returns
    -------
    str | None
        Datatype URI or None if not present

    Examples
    --------
    >>> literal_datatype('"42"^^xsd:integer')
    'xsd:integer'
    >>> literal_datatype('"true"^^http://www.w3.org/2001/XMLSchema#boolean')
    'http://www.w3.org/2001/XMLSchema#boolean'
    >>> literal_datatype('"hello"@en')
    >>> literal_datatype('"plain"')
    """
    # Match datatype after ^^
    match = re.search(r"\^\^(.+?)\s*$", literal)
    return match.group(1) if match else None


# Export dictionary for Jinja environment
RDF_FILTERS: dict[str, Callable[..., Any]] = {
    "uri_local_name": uri_local_name,
    "uri_namespace": uri_namespace,
    "uri_to_curie": uri_to_curie,
    "literal_value": literal_value,
    "literal_lang": literal_lang,
    "literal_datatype": literal_datatype,
}
