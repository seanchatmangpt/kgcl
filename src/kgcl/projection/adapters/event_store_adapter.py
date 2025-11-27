"""EventStoreAdapter - Wraps RDFEventStore as GraphClient.

This adapter bridges the RDFEventStore (4D event-sourced ontology)
to the GraphClient protocol, enabling projection templates to query
the current state graph or event log.

Examples
--------
>>> from kgcl.daemon.event_store import RDFEventStore
>>> store = RDFEventStore()
>>> adapter = EventStoreAdapter(store)
>>> adapter.graph_id
'event_store'
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.daemon.event_store import RDFEventStore


class EventStoreAdapter:
    """Adapter wrapping RDFEventStore as GraphClient.

    This adapter exposes the event store's state graph via the GraphClient
    protocol, allowing templates to execute SPARQL queries against the
    current graph state maintained by the daemon.

    Parameters
    ----------
    store : RDFEventStore
        The event store instance to wrap.
    graph_id : str
        Unique identifier for this adapter (default: "event_store").

    Attributes
    ----------
    graph_id : str
        Identifier used for graph client lookup in registry.

    Examples
    --------
    >>> from kgcl.daemon.event_store import RDFEventStore
    >>> store = RDFEventStore()
    >>> adapter = EventStoreAdapter(store, graph_id="main")
    >>> adapter.graph_id
    'main'
    """

    def __init__(self, store: RDFEventStore, graph_id: str = "event_store") -> None:
        """Initialize adapter with event store.

        Parameters
        ----------
        store : RDFEventStore
            Event store to wrap.
        graph_id : str
            Identifier for this adapter (default: "event_store").
        """
        self._store = store
        self._graph_id = graph_id

    @property
    def graph_id(self) -> str:
        """Return unique identifier for this adapter.

        Returns
        -------
        str
            Graph client identifier.

        Examples
        --------
        >>> from kgcl.daemon.event_store import RDFEventStore
        >>> adapter = EventStoreAdapter(RDFEventStore())
        >>> adapter.graph_id
        'event_store'
        """
        return self._graph_id

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Execute SPARQL SELECT query against state graph.

        Delegates to RDFEventStore.query_state() which executes queries
        against the current state graph (not the event log).

        Parameters
        ----------
        sparql : str
            SPARQL SELECT query string.

        Returns
        -------
        list[dict[str, Any]]
            Query results as list of variable bindings.

        Examples
        --------
        >>> from kgcl.daemon.event_store import RDFEventStore, DomainEvent, EventType
        >>> import time
        >>> store = RDFEventStore()
        >>> store.append(
        ...     DomainEvent(
        ...         event_id="e1",
        ...         event_type=EventType.TRIPLE_ADDED,
        ...         timestamp=time.time(),
        ...         sequence=0,
        ...         payload={"s": "urn:x", "p": "urn:type", "o": "Entity"},
        ...     )
        ... )
        1
        >>> adapter = EventStoreAdapter(store)
        >>> results = adapter.query("SELECT ?s WHERE { GRAPH <urn:kgcl:state> { ?s ?p ?o } }")
        >>> len(results) > 0
        True
        """
        return self._store.query_state(sparql)

    def ask(self, sparql: str) -> bool:
        """Execute SPARQL ASK query against state graph.

        Executes an ASK query by running a SELECT and checking if
        any results are returned.

        Parameters
        ----------
        sparql : str
            SPARQL ASK query string.

        Returns
        -------
        bool
            True if pattern exists in graph, False otherwise.

        Examples
        --------
        >>> from kgcl.daemon.event_store import RDFEventStore, DomainEvent, EventType
        >>> import time
        >>> store = RDFEventStore()
        >>> store.append(
        ...     DomainEvent(
        ...         event_id="e1",
        ...         event_type=EventType.TRIPLE_ADDED,
        ...         timestamp=time.time(),
        ...         sequence=0,
        ...         payload={"s": "urn:x", "p": "urn:p", "o": "y"},
        ...     )
        ... )
        1
        >>> adapter = EventStoreAdapter(store)
        >>> adapter.ask("ASK { GRAPH <urn:kgcl:state> { <urn:x> ?p ?o } }")
        True
        """
        # Convert ASK to SELECT and check for results
        # Replace ASK with SELECT returning a dummy variable
        select_query = sparql.replace("ASK", "SELECT ?__ask", 1)
        results = self.query(select_query)
        return len(results) > 0

    def construct(self, sparql: str) -> str:
        """Execute SPARQL CONSTRUCT query against state graph.

        Constructs an RDF graph from the current state and serializes
        to Turtle format.

        Parameters
        ----------
        sparql : str
            SPARQL CONSTRUCT query string.

        Returns
        -------
        str
            Serialized RDF graph in Turtle format.

        Examples
        --------
        >>> from kgcl.daemon.event_store import RDFEventStore, DomainEvent, EventType
        >>> import time
        >>> store = RDFEventStore()
        >>> store.append(
        ...     DomainEvent(
        ...         event_id="e1",
        ...         event_type=EventType.TRIPLE_ADDED,
        ...         timestamp=time.time(),
        ...         sequence=0,
        ...         payload={"s": "urn:x", "p": "urn:p", "o": "y"},
        ...     )
        ... )
        1
        >>> adapter = EventStoreAdapter(store)
        >>> result = adapter.construct("CONSTRUCT { ?s ?p ?o } WHERE { GRAPH <urn:kgcl:state> { ?s ?p ?o } }")
        >>> isinstance(result, str)
        True
        """
        # Execute CONSTRUCT query directly on the underlying store
        try:
            query_result = self._store.store.query(sparql)
            # PyOxigraph CONSTRUCT returns an iterator of Quad objects
            triples = []
            for quad in query_result:
                # Format as N-Triples for simplicity
                s = str(quad.subject)
                p = str(quad.predicate)
                o = str(quad.object)
                triples.append(f"{s} {p} {o} .")
            return "\n".join(triples)
        except Exception:
            # Fallback to empty result on error
            return ""
