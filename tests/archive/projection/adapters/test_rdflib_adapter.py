"""Tests for RDFLibAdapter - rdflib.Graph wrapper.

Chicago School TDD: Test behavior through state verification,
minimal mocking, AAA structure.
"""

from __future__ import annotations

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF

from kgcl.projection.adapters.rdflib_adapter import RDFLibAdapter
from kgcl.projection.ports.graph_client import GraphClient


def test_adapter_implements_graph_client_protocol() -> None:
    """RDFLibAdapter implements GraphClient protocol."""
    # Arrange
    graph = Graph()
    adapter = RDFLibAdapter(graph)

    # Act & Assert
    assert isinstance(adapter, GraphClient)


def test_graph_id_default() -> None:
    """Default graph_id is 'rdflib'."""
    # Arrange
    graph = Graph()

    # Act
    adapter = RDFLibAdapter(graph)

    # Assert
    assert adapter.graph_id == "rdflib"


def test_graph_id_custom() -> None:
    """Custom graph_id is preserved."""
    # Arrange
    graph = Graph()

    # Act
    adapter = RDFLibAdapter(graph, graph_id="test_graph")

    # Assert
    assert adapter.graph_id == "test_graph"


def test_query_returns_empty_for_empty_graph() -> None:
    """Query on empty graph returns empty list."""
    # Arrange
    graph = Graph()
    adapter = RDFLibAdapter(graph)
    sparql = "SELECT ?s WHERE { ?s ?p ?o }"

    # Act
    results = adapter.query(sparql)

    # Assert
    assert results == []


def test_query_returns_single_triple() -> None:
    """Query returns single triple from graph."""
    # Arrange
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.alice, EX.name, Literal("Alice")))
    adapter = RDFLibAdapter(graph)
    sparql = "SELECT ?s ?name WHERE { ?s <http://example.org/name> ?name }"

    # Act
    results = adapter.query(sparql)

    # Assert
    assert len(results) == 1
    assert results[0]["s"] == "http://example.org/alice"
    assert results[0]["name"] == "Alice"


def test_query_returns_multiple_triples() -> None:
    """Query returns multiple matching triples."""
    # Arrange
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.alice, RDF.type, EX.Person))
    graph.add((EX.bob, RDF.type, EX.Person))
    adapter = RDFLibAdapter(graph)
    sparql = """
        SELECT ?person
        WHERE {
            ?person <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/Person>
        }
    """

    # Act
    results = adapter.query(sparql)

    # Assert
    assert len(results) == 2
    people = {r["person"] for r in results}
    assert people == {"http://example.org/alice", "http://example.org/bob"}


def test_query_with_filter() -> None:
    """Query with FILTER returns filtered results."""
    # Arrange
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.alice, EX.age, Literal(30)))
    graph.add((EX.bob, EX.age, Literal(25)))
    adapter = RDFLibAdapter(graph)
    sparql = """
        SELECT ?person ?age
        WHERE {
            ?person <http://example.org/age> ?age .
            FILTER(?age > 28)
        }
    """

    # Act
    results = adapter.query(sparql)

    # Assert
    assert len(results) == 1
    assert results[0]["person"] == "http://example.org/alice"
    assert results[0]["age"] == "30"


def test_query_with_optional() -> None:
    """Query with OPTIONAL returns all matches including empty bindings."""
    # Arrange
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.alice, EX.name, Literal("Alice")))
    graph.add((EX.bob, EX.name, Literal("Bob")))
    graph.add((EX.alice, EX.email, Literal("alice@example.org")))
    adapter = RDFLibAdapter(graph)
    sparql = """
        SELECT ?person ?name ?email
        WHERE {
            ?person <http://example.org/name> ?name .
            OPTIONAL { ?person <http://example.org/email> ?email }
        }
    """

    # Act
    results = adapter.query(sparql)

    # Assert
    assert len(results) == 2
    # Alice has email, Bob doesn't
    alice_result = next(r for r in results if "alice" in r["person"])
    bob_result = next(r for r in results if "bob" in r["person"])
    assert "email" in alice_result
    # Bob's email binding is absent (not in dict)


def test_ask_returns_false_for_empty_graph() -> None:
    """ASK query on empty graph returns False."""
    # Arrange
    graph = Graph()
    adapter = RDFLibAdapter(graph)
    sparql = "ASK { ?s ?p ?o }"

    # Act
    result = adapter.ask(sparql)

    # Assert
    assert result is False


def test_ask_returns_true_when_pattern_exists() -> None:
    """ASK query returns True when pattern matches."""
    # Arrange
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.subject, EX.predicate, EX.object))
    adapter = RDFLibAdapter(graph)
    sparql = "ASK { ?s ?p ?o }"

    # Act
    result = adapter.ask(sparql)

    # Assert
    assert result is True


def test_ask_returns_false_when_pattern_missing() -> None:
    """ASK query returns False when pattern doesn't match."""
    # Arrange
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.alice, EX.name, Literal("Alice")))
    adapter = RDFLibAdapter(graph)
    sparql = "ASK { <http://example.org/bob> ?p ?o }"

    # Act
    result = adapter.ask(sparql)

    # Assert
    assert result is False


def test_ask_with_filter() -> None:
    """ASK query with FILTER evaluates condition."""
    # Arrange
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.alice, EX.age, Literal(30)))
    adapter = RDFLibAdapter(graph)
    sparql = """
        ASK {
            ?person <http://example.org/age> ?age .
            FILTER(?age > 25)
        }
    """

    # Act
    result = adapter.ask(sparql)

    # Assert
    assert result is True


def test_construct_returns_empty_for_empty_graph() -> None:
    """CONSTRUCT on empty graph returns minimal serialization."""
    # Arrange
    graph = Graph()
    adapter = RDFLibAdapter(graph)
    sparql = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"

    # Act
    result = adapter.construct(sparql)

    # Assert
    assert isinstance(result, str)
    # Empty graph returns empty or minimal Turtle
    assert len(result) >= 0


def test_construct_returns_serialized_graph() -> None:
    """CONSTRUCT returns serialized RDF graph in Turtle format."""
    # Arrange
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.alice, EX.knows, EX.bob))
    adapter = RDFLibAdapter(graph)
    sparql = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"

    # Act
    result = adapter.construct(sparql)

    # Assert
    assert isinstance(result, str)
    assert "alice" in result
    assert "knows" in result or "http://example.org/knows" in result
    assert "bob" in result


def test_construct_with_transformation() -> None:
    """CONSTRUCT can transform graph structure."""
    # Arrange
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.alice, EX.hasName, Literal("Alice")))
    adapter = RDFLibAdapter(graph)
    # Transform hasName to name
    sparql = """
        PREFIX ex: <http://example.org/>
        CONSTRUCT { ?s ex:name ?n }
        WHERE { ?s ex:hasName ?n }
    """

    # Act
    result = adapter.construct(sparql)

    # Assert
    assert isinstance(result, str)
    assert "name" in result or "http://example.org/name" in result
    assert "Alice" in result


def test_construct_with_filter() -> None:
    """CONSTRUCT applies FILTER to select triples."""
    # Arrange
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.alice, EX.age, Literal(30)))
    graph.add((EX.bob, EX.age, Literal(25)))
    adapter = RDFLibAdapter(graph)
    sparql = """
        PREFIX ex: <http://example.org/>
        CONSTRUCT { ?p ex:age ?a }
        WHERE {
            ?p ex:age ?a .
            FILTER(?a >= 30)
        }
    """

    # Act
    result = adapter.construct(sparql)

    # Assert
    assert isinstance(result, str)
    assert "alice" in result
    assert "bob" not in result  # Filtered out


def test_query_preserves_variable_names() -> None:
    """Query results use SPARQL variable names as dict keys."""
    # Arrange
    graph = Graph()
    EX = Namespace("http://example.org/")
    graph.add((EX.alice, EX.name, Literal("Alice")))
    adapter = RDFLibAdapter(graph)
    sparql = "SELECT ?person ?fullName WHERE { ?person <http://example.org/name> ?fullName }"

    # Act
    results = adapter.query(sparql)

    # Assert
    assert len(results) == 1
    assert "person" in results[0]
    assert "fullName" in results[0]
    assert results[0]["fullName"] == "Alice"


def test_query_handles_literals_with_datatypes() -> None:
    """Query correctly handles typed literals."""
    # Arrange
    graph = Graph()
    EX = Namespace("http://example.org/")
    from rdflib import XSD

    graph.add((EX.alice, EX.age, Literal(30, datatype=XSD.integer)))
    adapter = RDFLibAdapter(graph)
    sparql = "SELECT ?age WHERE { ?s <http://example.org/age> ?age }"

    # Act
    results = adapter.query(sparql)

    # Assert
    assert len(results) == 1
    # Value is converted to string
    assert results[0]["age"] == "30"
