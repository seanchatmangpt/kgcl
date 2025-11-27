"""Tests for GraphClient protocol and registry - Chicago School TDD.

Tests verify the protocol compliance and registry behavior.
"""

from __future__ import annotations

from typing import Any

import pytest

from kgcl.projection.ports.graph_client import GraphClient, GraphRegistry

# =============================================================================
# Mock Client for Testing
# =============================================================================


class MockGraphClient:
    """Mock graph client for testing."""

    def __init__(self, gid: str, data: list[dict[str, Any]] | None = None) -> None:
        """Initialize mock client."""
        self._id = gid
        self._data = data or []

    @property
    def graph_id(self) -> str:
        """Return graph identifier."""
        return self._id

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Execute mock query."""
        return self._data

    def ask(self, sparql: str) -> bool:
        """Execute mock ASK query."""
        return len(self._data) > 0

    def construct(self, sparql: str) -> str:
        """Execute mock CONSTRUCT query."""
        return ""


# =============================================================================
# GraphClient Protocol Tests
# =============================================================================


class TestGraphClientProtocol:
    """Tests for GraphClient protocol."""

    def test_mock_is_graph_client(self) -> None:
        """MockGraphClient satisfies GraphClient protocol."""
        client = MockGraphClient("main")
        assert isinstance(client, GraphClient)

    def test_graph_id_property(self) -> None:
        """Protocol requires graph_id property."""
        client = MockGraphClient("test-graph")
        assert client.graph_id == "test-graph"

    def test_query_method(self) -> None:
        """Protocol requires query method returning list of dicts."""
        data = [{"name": "Alice"}, {"name": "Bob"}]
        client = MockGraphClient("main", data)
        result = client.query("SELECT ?name WHERE { ?s rdfs:label ?name }")
        assert result == data

    def test_ask_method(self) -> None:
        """Protocol requires ask method returning bool."""
        client_with_data = MockGraphClient("main", [{"x": 1}])
        client_empty = MockGraphClient("main", [])

        assert client_with_data.ask("ASK { ?s ?p ?o }") is True
        assert client_empty.ask("ASK { ?s ?p ?o }") is False

    def test_construct_method(self) -> None:
        """Protocol requires construct method returning string."""
        client = MockGraphClient("main")
        result = client.construct("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
        assert isinstance(result, str)


# =============================================================================
# GraphRegistry Tests
# =============================================================================


class TestGraphRegistry:
    """Tests for GraphRegistry."""

    def test_create_empty_registry(self) -> None:
        """Can create empty registry."""
        registry = GraphRegistry()
        assert registry.list_ids() == ()

    def test_create_with_initial_clients(self) -> None:
        """Can create registry with initial clients."""
        c1 = MockGraphClient("main")
        c2 = MockGraphClient("secondary")
        registry = GraphRegistry({"main": c1, "secondary": c2})
        assert set(registry.list_ids()) == {"main", "secondary"}

    def test_register_client(self) -> None:
        """Can register a client."""
        registry = GraphRegistry()
        client = MockGraphClient("test")
        registry.register(client)
        assert "test" in registry.list_ids()

    def test_get_existing_client(self) -> None:
        """get returns registered client."""
        registry = GraphRegistry()
        client = MockGraphClient("main")
        registry.register(client)

        retrieved = registry.get("main")
        assert retrieved is client

    def test_get_missing_client(self) -> None:
        """get returns None for missing client."""
        registry = GraphRegistry()
        assert registry.get("missing") is None

    def test_require_existing_client(self) -> None:
        """require returns registered client."""
        registry = GraphRegistry()
        client = MockGraphClient("main")
        registry.register(client)

        retrieved = registry.require("main")
        assert retrieved is client

    def test_require_missing_client_raises(self) -> None:
        """require raises KeyError for missing client."""
        registry = GraphRegistry()
        with pytest.raises(KeyError, match="Graph not found: missing"):
            registry.require("missing")

    def test_contains_registered(self) -> None:
        """__contains__ returns True for registered clients."""
        registry = GraphRegistry()
        client = MockGraphClient("main")
        registry.register(client)
        assert "main" in registry

    def test_contains_missing(self) -> None:
        """__contains__ returns False for missing clients."""
        registry = GraphRegistry()
        assert "missing" not in registry

    def test_list_ids_returns_tuple(self) -> None:
        """list_ids returns tuple of identifiers."""
        registry = GraphRegistry()
        registry.register(MockGraphClient("a"))
        registry.register(MockGraphClient("b"))
        ids = registry.list_ids()
        assert isinstance(ids, tuple)
        assert set(ids) == {"a", "b"}

    def test_register_overwrites_existing(self) -> None:
        """Registering same graph_id overwrites previous."""
        registry = GraphRegistry()
        client1 = MockGraphClient("main", [{"x": 1}])
        client2 = MockGraphClient("main", [{"y": 2}])

        registry.register(client1)
        registry.register(client2)

        retrieved = registry.get("main")
        assert retrieved is client2
