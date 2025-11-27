"""RDFLibAdapter - Wraps rdflib.Graph as GraphClient.

This adapter bridges rdflib.Graph to the GraphClient protocol,
enabling projection templates to work with in-memory RDF graphs
during testing or with external rdflib-based data sources.

Examples
--------
>>> from rdflib import Graph
>>> g = Graph()
>>> adapter = RDFLibAdapter(g, graph_id="test")
>>> adapter.graph_id
'test'
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rdflib import Graph


class RDFLibAdapter:
    """Adapter wrapping rdflib.Graph as GraphClient.

    This adapter exposes an rdflib Graph via the GraphClient protocol,
    allowing templates to execute SPARQL queries against in-memory
    RDF graphs. Useful for testing and working with external data.

    Parameters
    ----------
    graph : Graph
        The rdflib Graph instance to wrap.
    graph_id : str
        Unique identifier for this adapter (default: "rdflib").

    Attributes
    ----------
    graph_id : str
        Identifier used for graph client lookup in registry.

    Examples
    --------
    >>> from rdflib import Graph, Namespace
    >>> g = Graph()
    >>> EX = Namespace("http://example.org/")
    >>> g.add((EX.subject, EX.predicate, EX.object))
    >>> adapter = RDFLibAdapter(g, graph_id="example")
    >>> adapter.graph_id
    'example'
    """

    def __init__(self, graph: Graph, graph_id: str = "rdflib") -> None:
        """Initialize adapter with rdflib Graph.

        Parameters
        ----------
        graph : Graph
            rdflib Graph to wrap.
        graph_id : str
            Identifier for this adapter (default: "rdflib").
        """
        self._graph = graph
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
        >>> from rdflib import Graph
        >>> adapter = RDFLibAdapter(Graph())
        >>> adapter.graph_id
        'rdflib'
        """
        return self._graph_id

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Execute SPARQL SELECT query against rdflib graph.

        Parameters
        ----------
        sparql : str
            SPARQL SELECT query string.

        Returns
        -------
        list[dict[str, Any]]
            Query results as list of variable bindings.
            Values are converted to strings.

        Examples
        --------
        >>> from rdflib import Graph, Namespace, Literal
        >>> g = Graph()
        >>> EX = Namespace("http://example.org/")
        >>> g.add((EX.alice, EX.name, Literal("Alice")))
        >>> adapter = RDFLibAdapter(g)
        >>> results = adapter.query("SELECT ?s ?name WHERE { ?s <http://example.org/name> ?name }")
        >>> len(results)
        1
        >>> results[0]["name"]
        'Alice'
        """
        results: list[dict[str, Any]] = []
        query_results = self._graph.query(sparql)

        for row in query_results:
            binding: dict[str, Any] = {}
            # rdflib returns ResultRow objects with variable bindings
            for var in query_results.vars:
                var_name = str(var)  # Convert rdflib Variable to string
                value = row[var]
                if value is not None:
                    # Convert rdflib term to string
                    binding[var_name] = str(value)
            results.append(binding)

        return results

    def ask(self, sparql: str) -> bool:
        """Execute SPARQL ASK query against rdflib graph.

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
        >>> from rdflib import Graph, Namespace
        >>> g = Graph()
        >>> EX = Namespace("http://example.org/")
        >>> g.add((EX.subject, EX.predicate, EX.object))
        >>> adapter = RDFLibAdapter(g)
        >>> adapter.ask("ASK { ?s ?p ?o }")
        True
        >>> adapter.ask("ASK { ?s <urn:missing> ?o }")
        False
        """
        result = self._graph.query(sparql)
        # rdflib ASK returns a boolean result
        return bool(result)

    def construct(self, sparql: str) -> str:
        """Execute SPARQL CONSTRUCT query against rdflib graph.

        Constructs an RDF graph and serializes to Turtle format.

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
        >>> from rdflib import Graph, Namespace
        >>> g = Graph()
        >>> EX = Namespace("http://example.org/")
        >>> g.add((EX.alice, EX.knows, EX.bob))
        >>> adapter = RDFLibAdapter(g)
        >>> result = adapter.construct("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
        >>> "alice" in result
        True
        """
        query_result = self._graph.query(sparql)
        # CONSTRUCT returns a Graph object
        if hasattr(query_result, "serialize"):
            # rdflib Graph.serialize() returns bytes
            serialized = query_result.serialize(format="turtle")
            if isinstance(serialized, bytes):
                return serialized.decode("utf-8")
            return str(serialized)
        return ""
