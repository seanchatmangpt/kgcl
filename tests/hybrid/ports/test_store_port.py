"""Tests for RDFStore protocol.

Coverage tests for store_port.py protocol definition.
"""

from __future__ import annotations

from typing import Any

import pytest

from kgcl.hybrid.ports.store_port import RDFStore


class MockRDFStore:
    """Mock implementation of RDFStore protocol."""

    def __init__(self) -> None:
        """Initialize mock store."""
        self._triples: list[str] = []

    def load_turtle(self, data: str) -> int:
        """Load Turtle data."""
        self._triples.append(data)
        return 1

    def load_n3(self, data: str) -> int:
        """Load N3 data."""
        self._triples.append(data)
        return 1

    def dump(self) -> str:
        """Dump store contents."""
        return "\n".join(self._triples)

    def triple_count(self) -> int:
        """Count triples."""
        return len(self._triples)

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Execute SPARQL query."""
        return []

    def clear(self) -> None:
        """Clear all triples."""
        self._triples.clear()


class TestRDFStoreProtocol:
    """Test RDFStore protocol compliance."""

    def test_protocol_detects_compliant_implementation(self) -> None:
        """Test isinstance check for compliant implementation."""
        store = MockRDFStore()
        assert isinstance(store, RDFStore)

    def test_protocol_requires_load_turtle(self) -> None:
        """Test protocol requires load_turtle method."""

        class IncompleteStore:
            def load_n3(self, data: str) -> int:
                return 0

            def dump(self) -> str:
                return ""

            def triple_count(self) -> int:
                return 0

            def query(self, sparql: str) -> list[dict[str, Any]]:
                return []

            def clear(self) -> None:
                pass

        store = IncompleteStore()
        assert not isinstance(store, RDFStore)

    def test_protocol_requires_load_n3(self) -> None:
        """Test protocol requires load_n3 method."""

        class IncompleteStore:
            def load_turtle(self, data: str) -> int:
                return 0

            def dump(self) -> str:
                return ""

            def triple_count(self) -> int:
                return 0

            def query(self, sparql: str) -> list[dict[str, Any]]:
                return []

            def clear(self) -> None:
                pass

        store = IncompleteStore()
        assert not isinstance(store, RDFStore)

    def test_protocol_requires_dump(self) -> None:
        """Test protocol requires dump method."""

        class IncompleteStore:
            def load_turtle(self, data: str) -> int:
                return 0

            def load_n3(self, data: str) -> int:
                return 0

            def triple_count(self) -> int:
                return 0

            def query(self, sparql: str) -> list[dict[str, Any]]:
                return []

            def clear(self) -> None:
                pass

        store = IncompleteStore()
        assert not isinstance(store, RDFStore)

    def test_protocol_requires_triple_count(self) -> None:
        """Test protocol requires triple_count method."""

        class IncompleteStore:
            def load_turtle(self, data: str) -> int:
                return 0

            def load_n3(self, data: str) -> int:
                return 0

            def dump(self) -> str:
                return ""

            def query(self, sparql: str) -> list[dict[str, Any]]:
                return []

            def clear(self) -> None:
                pass

        store = IncompleteStore()
        assert not isinstance(store, RDFStore)

    def test_protocol_requires_query(self) -> None:
        """Test protocol requires query method."""

        class IncompleteStore:
            def load_turtle(self, data: str) -> int:
                return 0

            def load_n3(self, data: str) -> int:
                return 0

            def dump(self) -> str:
                return ""

            def triple_count(self) -> int:
                return 0

            def clear(self) -> None:
                pass

        store = IncompleteStore()
        assert not isinstance(store, RDFStore)

    def test_protocol_requires_clear(self) -> None:
        """Test protocol requires clear method."""

        class IncompleteStore:
            def load_turtle(self, data: str) -> int:
                return 0

            def load_n3(self, data: str) -> int:
                return 0

            def dump(self) -> str:
                return ""

            def triple_count(self) -> int:
                return 0

            def query(self, sparql: str) -> list[dict[str, Any]]:
                return []

        store = IncompleteStore()
        assert not isinstance(store, RDFStore)


class TestMockRDFStoreImplementation:
    """Test MockRDFStore implementation behavior."""

    def test_load_turtle_increases_count(self) -> None:
        """Test loading Turtle increases triple count."""
        store = MockRDFStore()
        initial = store.triple_count()
        store.load_turtle("<urn:s> <urn:p> <urn:o> .")
        assert store.triple_count() == initial + 1

    def test_clear_resets_count(self) -> None:
        """Test clear removes all triples."""
        store = MockRDFStore()
        store.load_turtle("<urn:s> <urn:p> <urn:o> .")
        store.clear()
        assert store.triple_count() == 0

    def test_dump_returns_string(self) -> None:
        """Test dump returns string representation."""
        store = MockRDFStore()
        store.load_turtle("<urn:s> <urn:p> <urn:o> .")
        output = store.dump()
        assert isinstance(output, str)
        assert "<urn:s> <urn:p> <urn:o> ." in output
