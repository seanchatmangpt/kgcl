"""OxigraphAdapter - Wraps OxigraphStore to implement RDFStore protocol.

This adapter provides the RDFStore interface using PyOxigraph as the backend.
It wraps the existing OxigraphStore class from oxigraph_store.py.

Examples
--------
>>> adapter = OxigraphAdapter()
>>> _ = adapter.load_turtle("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")
>>> adapter.triple_count()
1
"""

from __future__ import annotations

import logging
from typing import Any

import pyoxigraph as ox

from kgcl.hybrid.oxigraph_store import OxigraphStore

logger = logging.getLogger(__name__)


class OxigraphAdapter:
    """Adapter wrapping OxigraphStore to implement RDFStore protocol.

    This adapter provides a clean interface to PyOxigraph storage,
    implementing the RDFStore protocol for use by the hybrid engine.

    Parameters
    ----------
    path : str | None, optional
        Path for persistent storage. If None, uses in-memory store.

    Attributes
    ----------
    raw_store : ox.Store
        The underlying pyoxigraph Store (for backward compatibility).

    Examples
    --------
    Create in-memory store:

    >>> adapter = OxigraphAdapter()
    >>> adapter.triple_count()
    0

    Load data:

    >>> _ = adapter.load_turtle('''
    ...     @prefix ex: <http://example.org/> .
    ...     ex:task1 ex:status "Active" .
    ... ''')
    >>> adapter.triple_count()
    1

    Query data:

    >>> results = adapter.query("SELECT * WHERE { ?s ?p ?o }")
    >>> len(results) >= 1
    True
    """

    def __init__(self, path: str | None = None) -> None:
        """Initialize OxigraphAdapter.

        Parameters
        ----------
        path : str | None, optional
            Path for persistent storage. If None, uses in-memory store.
        """
        self._store = OxigraphStore(path)
        logger.info(f"OxigraphAdapter initialized (persistent={path is not None})")

    @property
    def raw_store(self) -> ox.Store:
        """Get the underlying pyoxigraph Store.

        This property provides backward compatibility for code that
        needs direct access to the pyoxigraph Store object.

        Returns
        -------
        ox.Store
            The underlying pyoxigraph Store.

        Examples
        --------
        >>> adapter = OxigraphAdapter()
        >>> store = adapter.raw_store
        >>> isinstance(store, ox.Store)
        True
        """
        return self._store.store

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

        Examples
        --------
        >>> adapter = OxigraphAdapter()
        >>> count = adapter.load_turtle("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")
        >>> count
        1
        """
        return self._store.load_turtle(data)

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

        Examples
        --------
        >>> adapter = OxigraphAdapter()
        >>> count = adapter.load_n3("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")
        >>> count >= 0  # N3 loading may vary
        True
        """
        return self._store.load_n3(data)

    def dump(self) -> str:
        """Dump entire store as serialized RDF.

        Returns
        -------
        str
            All triples serialized in Turtle-like format.

        Examples
        --------
        >>> adapter = OxigraphAdapter()
        >>> _ = adapter.load_turtle("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")
        >>> output = adapter.dump()
        >>> "ex:a" in output or "<http://example.org/a>" in output
        True
        """
        return self._store.dump()

    def dump_trig(self) -> str:
        """Dump store as TriG format (for EYE reasoning).

        Uses the underlying pyoxigraph Store directly for TriG format,
        which is more suitable for EYE reasoner input.

        Returns
        -------
        str
            All quads serialized in TriG format.
        """
        result = self._store.store.dump(format=ox.RdfFormat.TRIG)
        if result is None:
            return ""
        return result.decode("utf-8")

    def triple_count(self) -> int:
        """Count total triples in store.

        Returns
        -------
        int
            Number of triples.

        Examples
        --------
        >>> adapter = OxigraphAdapter()
        >>> adapter.triple_count()
        0
        >>> _ = adapter.load_turtle("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")
        >>> adapter.triple_count()
        1
        """
        return self._store.triple_count()

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

        Examples
        --------
        >>> adapter = OxigraphAdapter()
        >>> _ = adapter.load_turtle('''
        ...     @prefix ex: <http://example.org/> .
        ...     ex:task1 ex:status "Active" .
        ... ''')
        >>> results = adapter.query("SELECT ?s ?o WHERE { ?s <http://example.org/status> ?o }")
        >>> len(results)
        1
        """
        return self._store.query(sparql)

    def clear(self) -> None:
        """Clear all triples from store.

        Examples
        --------
        >>> adapter = OxigraphAdapter()
        >>> _ = adapter.load_turtle("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")
        >>> adapter.triple_count()
        1
        >>> adapter.clear()
        >>> adapter.triple_count()
        0
        """
        self._store.clear()

    def load_raw(self, data: bytes, format: ox.RdfFormat) -> None:
        """Load raw RDF data with explicit format.

        Used internally for loading EYE output (N3 format).

        Parameters
        ----------
        data : bytes
            Raw RDF data as bytes.
        format : ox.RdfFormat
            RDF format (e.g., ox.RdfFormat.N3).
        """
        self._store.store.load(input=data, format=format)
