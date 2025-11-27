"""GraphClient Protocol - Abstract interface for SPARQL-capable stores.

This module defines the protocol that all graph backends must implement
for use with the projection engine. Adapters wrap concrete stores
like RDFEventStore, rdflib.Graph, or PyOxigraph Store.

Examples
--------
>>> class MockClient:
...     @property
...     def graph_id(self) -> str:
...         return "mock"
...
...     def query(self, sparql: str) -> list[dict[str, object]]:
...         return []
...
...     def ask(self, sparql: str) -> bool:
...         return False
...
...     def construct(self, sparql: str) -> str:
...         return ""
>>> client = MockClient()
>>> isinstance(client, GraphClient)
True
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GraphClient(Protocol):
    """Protocol for SPARQL-capable RDF graph clients.

    This protocol defines the minimal interface required by the projection
    engine for executing SPARQL queries against an RDF store. Implementations
    include EventStoreAdapter for KGCLDaemon integration, RDFLibAdapter for
    testing with rdflib, and OxigraphAdapter for direct PyOxigraph use.

    Properties
    ----------
    graph_id : str
        Unique identifier for this graph client instance.

    Methods
    -------
    query(sparql)
        Execute SPARQL SELECT query and return bindings.
    ask(sparql)
        Execute SPARQL ASK query and return boolean.
    construct(sparql)
        Execute SPARQL CONSTRUCT and return serialized graph.

    Examples
    --------
    Any class implementing the required methods works:

    >>> class InMemoryClient:
    ...     def __init__(self, gid: str) -> None:
    ...         self._id = gid
    ...         self._data: list[tuple[str, str, str]] = []
    ...
    ...     @property
    ...     def graph_id(self) -> str:
    ...         return self._id
    ...
    ...     def query(self, sparql: str) -> list[dict[str, Any]]:
    ...         return [{"s": s, "p": p, "o": o} for s, p, o in self._data]
    ...
    ...     def ask(self, sparql: str) -> bool:
    ...         return len(self._data) > 0
    ...
    ...     def construct(self, sparql: str) -> str:
    ...         return ""
    """

    @property
    def graph_id(self) -> str:
        """Unique identifier for this graph client.

        Returns
        -------
        str
            Graph identifier used for client lookup.

        Examples
        --------
        >>> class C:
        ...     @property
        ...     def graph_id(self) -> str:
        ...         return "main"
        ...
        ...     def query(self, s: str) -> list[dict[str, Any]]:
        ...         return []
        ...
        ...     def ask(self, s: str) -> bool:
        ...         return False
        ...
        ...     def construct(self, s: str) -> str:
        ...         return ""
        >>> C().graph_id
        'main'
        """
        ...

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Execute SPARQL SELECT query.

        Parameters
        ----------
        sparql : str
            SPARQL SELECT query string.

        Returns
        -------
        list[dict[str, Any]]
            List of binding dictionaries, one per result row.
            Keys are variable names, values are bound terms.

        Raises
        ------
        Exception
            If query execution fails (parse error, store error, etc.).

        Examples
        --------
        >>> class C:
        ...     @property
        ...     def graph_id(self) -> str:
        ...         return "x"
        ...
        ...     def query(self, s: str) -> list[dict[str, Any]]:
        ...         return [{"name": "Alice"}, {"name": "Bob"}]
        ...
        ...     def ask(self, s: str) -> bool:
        ...         return True
        ...
        ...     def construct(self, s: str) -> str:
        ...         return ""
        >>> c = C()
        >>> c.query("SELECT ?name WHERE { ?s rdfs:label ?name }")
        [{'name': 'Alice'}, {'name': 'Bob'}]
        """
        ...

    def ask(self, sparql: str) -> bool:
        """Execute SPARQL ASK query.

        Parameters
        ----------
        sparql : str
            SPARQL ASK query string.

        Returns
        -------
        bool
            True if the pattern exists, False otherwise.

        Raises
        ------
        Exception
            If query execution fails.

        Examples
        --------
        >>> class C:
        ...     @property
        ...     def graph_id(self) -> str:
        ...         return "x"
        ...
        ...     def query(self, s: str) -> list[dict[str, Any]]:
        ...         return []
        ...
        ...     def ask(self, s: str) -> bool:
        ...         return True
        ...
        ...     def construct(self, s: str) -> str:
        ...         return ""
        >>> c = C()
        >>> c.ask("ASK { ?s a ex:Entity }")
        True
        """
        ...

    def construct(self, sparql: str) -> str:
        """Execute SPARQL CONSTRUCT query.

        Parameters
        ----------
        sparql : str
            SPARQL CONSTRUCT query string.

        Returns
        -------
        str
            Serialized RDF graph (typically Turtle format).

        Raises
        ------
        Exception
            If query execution fails.

        Examples
        --------
        >>> class C:
        ...     @property
        ...     def graph_id(self) -> str:
        ...         return "x"
        ...
        ...     def query(self, s: str) -> list[dict[str, Any]]:
        ...         return []
        ...
        ...     def ask(self, s: str) -> bool:
        ...         return False
        ...
        ...     def construct(self, s: str) -> str:
        ...         return "<urn:s> <urn:p> <urn:o> ."
        >>> c = C()
        >>> c.construct("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
        '<urn:s> <urn:p> <urn:o> .'
        """
        ...


class GraphRegistry:
    """Registry for managing multiple GraphClient instances.

    The registry provides a central lookup mechanism for graph clients
    by their identifiers, enabling templates to reference multiple
    data sources.

    Parameters
    ----------
    clients : dict[str, GraphClient] | None
        Initial mapping of graph_id to client instances.

    Examples
    --------
    >>> class MockClient:
    ...     def __init__(self, gid: str) -> None:
    ...         self._id = gid
    ...
    ...     @property
    ...     def graph_id(self) -> str:
    ...         return self._id
    ...
    ...     def query(self, s: str) -> list[dict[str, Any]]:
    ...         return []
    ...
    ...     def ask(self, s: str) -> bool:
    ...         return False
    ...
    ...     def construct(self, s: str) -> str:
    ...         return ""
    >>> registry = GraphRegistry()
    >>> registry.register(MockClient("main"))
    >>> registry.get("main") is not None
    True
    """

    def __init__(self, clients: dict[str, GraphClient] | None = None) -> None:
        """Initialize registry with optional clients."""
        self._clients: dict[str, GraphClient] = dict(clients) if clients else {}

    def register(self, client: GraphClient) -> None:
        """Register a graph client.

        Parameters
        ----------
        client : GraphClient
            Client to register (uses client.graph_id as key).

        Examples
        --------
        >>> class C:
        ...     @property
        ...     def graph_id(self) -> str:
        ...         return "test"
        ...
        ...     def query(self, s: str) -> list[dict[str, Any]]:
        ...         return []
        ...
        ...     def ask(self, s: str) -> bool:
        ...         return False
        ...
        ...     def construct(self, s: str) -> str:
        ...         return ""
        >>> r = GraphRegistry()
        >>> r.register(C())
        >>> "test" in r.list_ids()
        True
        """
        self._clients[client.graph_id] = client

    def get(self, graph_id: str) -> GraphClient | None:
        """Get client by graph_id.

        Parameters
        ----------
        graph_id : str
            Identifier to look up.

        Returns
        -------
        GraphClient | None
            The client or None if not found.

        Examples
        --------
        >>> r = GraphRegistry()
        >>> r.get("missing") is None
        True
        """
        return self._clients.get(graph_id)

    def require(self, graph_id: str) -> GraphClient:
        """Get client by graph_id or raise.

        Parameters
        ----------
        graph_id : str
            Identifier to look up.

        Returns
        -------
        GraphClient
            The client.

        Raises
        ------
        KeyError
            If graph_id not found.

        Examples
        --------
        >>> r = GraphRegistry()
        >>> r.require("missing")
        Traceback (most recent call last):
            ...
        KeyError: "Graph not found: missing"
        """
        client = self._clients.get(graph_id)
        if client is None:
            msg = f"Graph not found: {graph_id}"
            raise KeyError(msg)
        return client

    def list_ids(self) -> tuple[str, ...]:
        """List all registered graph_ids.

        Returns
        -------
        tuple[str, ...]
            Registered identifiers.

        Examples
        --------
        >>> r = GraphRegistry()
        >>> r.list_ids()
        ()
        """
        return tuple(self._clients.keys())

    def __contains__(self, graph_id: str) -> bool:
        """Check if graph_id is registered.

        Parameters
        ----------
        graph_id : str
            Identifier to check.

        Returns
        -------
        bool
            True if registered.

        Examples
        --------
        >>> r = GraphRegistry()
        >>> "main" in r
        False
        """
        return graph_id in self._clients
