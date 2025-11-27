"""RDFStore - Protocol for RDF triple store operations.

This module defines the abstract interface for RDF storage backends.
The hybrid engine depends on this protocol, not on concrete implementations.

Examples
--------
>>> class MockStore:
...     def load_turtle(self, data: str) -> int:
...         return 0
...
...     def load_n3(self, data: str) -> int:
...         return 0
...
...     def dump(self) -> str:
...         return ""
...
...     def triple_count(self) -> int:
...         return 0
...
...     def query(self, sparql: str) -> list[dict[str, object]]:
...         return []
...
...     def clear(self) -> None:
...         pass
>>> from typing import TYPE_CHECKING
>>> if TYPE_CHECKING:
...     store: RDFStore = MockStore()  # type: ignore[assignment]
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RDFStore(Protocol):
    """Protocol for RDF triple store operations.

    This protocol defines the minimal interface required by the hybrid engine
    for storing and querying RDF data. Implementations include OxigraphAdapter
    for production use and mock stores for testing.

    Methods
    -------
    load_turtle(data)
        Load Turtle-formatted RDF data into the store.
    load_n3(data)
        Load N3-formatted RDF data into the store.
    dump()
        Serialize store contents to Turtle/TriG format.
    triple_count()
        Count total triples in the store.
    query(sparql)
        Execute SPARQL SELECT query.
    clear()
        Remove all triples from the store.

    Examples
    --------
    Any class implementing this protocol can be used:

    >>> class InMemoryStore:
    ...     def __init__(self) -> None:
    ...         self._data: list[str] = []
    ...
    ...     def load_turtle(self, data: str) -> int:
    ...         self._data.append(data)
    ...         return 1
    ...
    ...     def load_n3(self, data: str) -> int:
    ...         self._data.append(data)
    ...         return 1
    ...
    ...     def dump(self) -> str:
    ...         return "\\n".join(self._data)
    ...
    ...     def triple_count(self) -> int:
    ...         return len(self._data)
    ...
    ...     def query(self, sparql: str) -> list[dict[str, object]]:
    ...         return []
    ...
    ...     def clear(self) -> None:
    ...         self._data.clear()
    """

    def load_turtle(self, data: str) -> int:
        """Load Turtle (TTL) format RDF data.

        Parameters
        ----------
        data : str
            Turtle format RDF data.

        Returns
        -------
        int
            Number of triples loaded.

        Raises
        ------
        Exception
            If loading fails due to parse error.
        """
        ...

    def load_n3(self, data: str) -> int:
        """Load N3 format RDF data.

        Parameters
        ----------
        data : str
            N3 format RDF data.

        Returns
        -------
        int
            Number of triples loaded.

        Raises
        ------
        Exception
            If loading fails due to parse error.
        """
        ...

    def dump(self) -> str:
        """Dump entire store as serialized RDF.

        Returns
        -------
        str
            All triples serialized (typically Turtle/TriG format).
        """
        ...

    def triple_count(self) -> int:
        """Count total triples in store.

        Returns
        -------
        int
            Number of triples.
        """
        ...

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Execute SPARQL SELECT query.

        Parameters
        ----------
        sparql : str
            SPARQL SELECT query.

        Returns
        -------
        list[dict[str, Any]]
            List of variable bindings from query results.
        """
        ...

    def clear(self) -> None:
        """Clear all triples from store."""
        ...
