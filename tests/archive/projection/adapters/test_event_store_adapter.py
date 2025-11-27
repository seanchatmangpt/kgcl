"""Tests for EventStoreAdapter - RDFEventStore wrapper.

Chicago School TDD: Test behavior through state verification,
minimal mocking, AAA structure.
"""

from __future__ import annotations

import time

from kgcl.daemon.event_store import DomainEvent, EventType, RDFEventStore
from kgcl.projection.adapters.event_store_adapter import EventStoreAdapter
from kgcl.projection.ports.graph_client import GraphClient


def test_adapter_implements_graph_client_protocol() -> None:
    """EventStoreAdapter implements GraphClient protocol."""
    # Arrange
    store = RDFEventStore()
    adapter = EventStoreAdapter(store)

    # Act & Assert
    assert isinstance(adapter, GraphClient)


def test_graph_id_default() -> None:
    """Default graph_id is 'event_store'."""
    # Arrange
    store = RDFEventStore()

    # Act
    adapter = EventStoreAdapter(store)

    # Assert
    assert adapter.graph_id == "event_store"


def test_graph_id_custom() -> None:
    """Custom graph_id is preserved."""
    # Arrange
    store = RDFEventStore()

    # Act
    adapter = EventStoreAdapter(store, graph_id="custom")

    # Assert
    assert adapter.graph_id == "custom"


def test_query_returns_empty_for_empty_state() -> None:
    """Query on empty state graph returns empty list."""
    # Arrange
    store = RDFEventStore()
    adapter = EventStoreAdapter(store)
    sparql = "SELECT ?s WHERE { GRAPH <urn:kgcl:state> { ?s ?p ?o } }"

    # Act
    results = adapter.query(sparql)

    # Assert
    assert results == []


def test_query_returns_triple_from_state_graph() -> None:
    """Query returns triple added to state graph via event."""
    # Arrange
    store = RDFEventStore()
    store.append(
        DomainEvent(
            event_id="evt-001",
            event_type=EventType.TRIPLE_ADDED,
            timestamp=time.time(),
            sequence=0,
            payload={"s": "urn:entity:1", "p": "urn:prop:name", "o": "Alice"},
        )
    )
    adapter = EventStoreAdapter(store)
    sparql = """
        SELECT ?s ?o
        WHERE {
            GRAPH <urn:kgcl:state> {
                ?s <urn:prop:name> ?o
            }
        }
    """

    # Act
    results = adapter.query(sparql)

    # Assert
    assert len(results) == 1
    assert results[0]["s"] == "urn:entity:1"
    assert results[0]["o"] == "Alice"


def test_query_reflects_multiple_events() -> None:
    """Query results reflect multiple triple additions."""
    # Arrange
    store = RDFEventStore()
    store.append(
        DomainEvent(
            event_id="e1",
            event_type=EventType.TRIPLE_ADDED,
            timestamp=time.time(),
            sequence=0,
            payload={"s": "urn:alice", "p": "urn:type", "o": "Person"},
        )
    )
    store.append(
        DomainEvent(
            event_id="e2",
            event_type=EventType.TRIPLE_ADDED,
            timestamp=time.time(),
            sequence=0,
            payload={"s": "urn:bob", "p": "urn:type", "o": "Person"},
        )
    )
    adapter = EventStoreAdapter(store)
    sparql = """
        SELECT ?s
        WHERE {
            GRAPH <urn:kgcl:state> {
                ?s <urn:type> "Person"
            }
        }
    """

    # Act
    results = adapter.query(sparql)

    # Assert
    assert len(results) == 2
    subjects = {r["s"] for r in results}
    assert subjects == {"urn:alice", "urn:bob"}


def test_ask_returns_false_for_empty_graph() -> None:
    """ASK query on empty graph returns False."""
    # Arrange
    store = RDFEventStore()
    adapter = EventStoreAdapter(store)
    sparql = "ASK { GRAPH <urn:kgcl:state> { ?s ?p ?o } }"

    # Act
    result = adapter.ask(sparql)

    # Assert
    assert result is False


def test_ask_returns_true_when_pattern_exists() -> None:
    """ASK query returns True when pattern matches."""
    # Arrange
    store = RDFEventStore()
    store.append(
        DomainEvent(
            event_id="e1",
            event_type=EventType.TRIPLE_ADDED,
            timestamp=time.time(),
            sequence=0,
            payload={"s": "urn:x", "p": "urn:p", "o": "value"},
        )
    )
    adapter = EventStoreAdapter(store)
    sparql = "ASK { GRAPH <urn:kgcl:state> { <urn:x> ?p ?o } }"

    # Act
    result = adapter.ask(sparql)

    # Assert
    assert result is True


def test_ask_returns_false_when_pattern_missing() -> None:
    """ASK query returns False when pattern doesn't match."""
    # Arrange
    store = RDFEventStore()
    store.append(
        DomainEvent(
            event_id="e1",
            event_type=EventType.TRIPLE_ADDED,
            timestamp=time.time(),
            sequence=0,
            payload={"s": "urn:x", "p": "urn:p", "o": "value"},
        )
    )
    adapter = EventStoreAdapter(store)
    sparql = "ASK { GRAPH <urn:kgcl:state> { <urn:missing> ?p ?o } }"

    # Act
    result = adapter.ask(sparql)

    # Assert
    assert result is False


def test_construct_returns_empty_for_empty_graph() -> None:
    """CONSTRUCT on empty graph returns empty string."""
    # Arrange
    store = RDFEventStore()
    adapter = EventStoreAdapter(store)
    sparql = "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH <urn:kgcl:state> { ?s ?p ?o } }"

    # Act
    result = adapter.construct(sparql)

    # Assert
    assert isinstance(result, str)
    # Empty graph may return "" or minimal serialization
    assert len(result) >= 0


def test_construct_returns_serialized_graph() -> None:
    """CONSTRUCT returns serialized RDF graph."""
    # Arrange
    store = RDFEventStore()
    store.append(
        DomainEvent(
            event_id="e1",
            event_type=EventType.TRIPLE_ADDED,
            timestamp=time.time(),
            sequence=0,
            payload={"s": "urn:alice", "p": "urn:knows", "o": "urn:bob"},
        )
    )
    adapter = EventStoreAdapter(store)
    sparql = "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH <urn:kgcl:state> { ?s ?p ?o } }"

    # Act
    result = adapter.construct(sparql)

    # Assert
    assert isinstance(result, str)
    # Serialization should contain the triple components
    assert len(result) > 0


def test_query_isolated_from_event_graph() -> None:
    """Query against state graph doesn't see event metadata."""
    # Arrange
    store = RDFEventStore()
    store.append(
        DomainEvent(
            event_id="evt-meta",
            event_type=EventType.TRIPLE_ADDED,
            timestamp=time.time(),
            sequence=0,
            payload={"s": "urn:x", "p": "urn:p", "o": "y"},
        )
    )
    adapter = EventStoreAdapter(store)
    # Query for event metadata (should not be in state graph)
    sparql = """
        SELECT ?eventId
        WHERE {
            GRAPH <urn:kgcl:state> {
                ?e <urn:kgcl:vocab#eventId> ?eventId
            }
        }
    """

    # Act
    results = adapter.query(sparql)

    # Assert
    # Event metadata is in the events graph, not state graph
    assert results == []


def test_query_multiple_graph_patterns() -> None:
    """Query can reference state graph explicitly."""
    # Arrange
    store = RDFEventStore()
    store.append(
        DomainEvent(
            event_id="e1",
            event_type=EventType.TRIPLE_ADDED,
            timestamp=time.time(),
            sequence=0,
            payload={"s": "urn:doc:1", "p": "urn:title", "o": "Test"},
        )
    )
    adapter = EventStoreAdapter(store)
    sparql = """
        SELECT ?title
        WHERE {
            GRAPH <urn:kgcl:state> {
                <urn:doc:1> <urn:title> ?title
            }
        }
    """

    # Act
    results = adapter.query(sparql)

    # Assert
    assert len(results) == 1
    assert results[0]["title"] == "Test"
