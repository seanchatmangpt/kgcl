"""Tests for OxigraphAdapter.

Tests verify RDFStore protocol implementation using PyOxigraph.
"""

from __future__ import annotations

import pyoxigraph as ox
import pytest

from kgcl.hybrid.adapters.oxigraph_adapter import OxigraphAdapter


class TestOxigraphAdapterCreation:
    """Tests for adapter initialization."""

    def test_create_in_memory(self) -> None:
        """In-memory adapter starts with zero triples."""
        adapter = OxigraphAdapter()
        assert adapter.triple_count() == 0

    def test_raw_store_returns_pyoxigraph_store(self) -> None:
        """raw_store property returns pyoxigraph Store."""
        adapter = OxigraphAdapter()
        assert isinstance(adapter.raw_store, ox.Store)


class TestOxigraphAdapterLoadTurtle:
    """Tests for loading Turtle data."""

    def test_load_single_triple(self) -> None:
        """Load single triple returns 1."""
        adapter = OxigraphAdapter()
        count = adapter.load_turtle("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")

        assert count == 1
        assert adapter.triple_count() == 1

    def test_load_multiple_triples(self) -> None:
        """Load multiple triples returns correct count."""
        adapter = OxigraphAdapter()
        data = """
            @prefix ex: <http://example.org/> .
            ex:a ex:b ex:c .
            ex:d ex:e ex:f .
            ex:g ex:h ex:i .
        """
        count = adapter.load_turtle(data)

        assert count == 3
        assert adapter.triple_count() == 3

    def test_load_with_prefixes(self) -> None:
        """Load Turtle with standard prefixes."""
        adapter = OxigraphAdapter()
        data = """
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
            <urn:task:A> kgc:status "Active" .
            <urn:task:A> a yawl:Task .
        """
        count = adapter.load_turtle(data)

        assert count == 2


class TestOxigraphAdapterQuery:
    """Tests for SPARQL query execution."""

    def test_query_returns_bindings(self) -> None:
        """Query returns list of bindings."""
        adapter = OxigraphAdapter()
        adapter.load_turtle("""
            @prefix ex: <http://example.org/> .
            ex:task1 ex:status "Active" .
        """)

        results = adapter.query("SELECT ?s ?o WHERE { ?s <http://example.org/status> ?o }")

        assert len(results) == 1
        assert "s" in results[0]
        assert "o" in results[0]

    def test_query_empty_store(self) -> None:
        """Query on empty store returns empty list."""
        adapter = OxigraphAdapter()
        results = adapter.query("SELECT ?s WHERE { ?s ?p ?o }")

        assert results == []


class TestOxigraphAdapterDump:
    """Tests for dumping store contents."""

    def test_dump_empty_store(self) -> None:
        """Dump empty store returns empty or minimal string."""
        adapter = OxigraphAdapter()
        output = adapter.dump()

        # Empty store may return empty string or just newline
        assert output == "" or output == "\n"

    def test_dump_contains_data(self) -> None:
        """Dump includes loaded triples."""
        adapter = OxigraphAdapter()
        adapter.load_turtle("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")

        output = adapter.dump()

        # Output should contain the triple (format may vary)
        assert "example.org" in output or "ex:" in output


class TestOxigraphAdapterClear:
    """Tests for clearing store."""

    def test_clear_removes_all_triples(self) -> None:
        """Clear removes all triples."""
        adapter = OxigraphAdapter()
        adapter.load_turtle("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")
        assert adapter.triple_count() == 1

        adapter.clear()

        assert adapter.triple_count() == 0

    def test_clear_empty_store(self) -> None:
        """Clear on empty store is safe."""
        adapter = OxigraphAdapter()
        adapter.clear()  # Should not raise
        assert adapter.triple_count() == 0


class TestOxigraphAdapterTripleCount:
    """Tests for triple counting."""

    def test_count_increases_with_load(self) -> None:
        """Triple count increases as data is loaded."""
        adapter = OxigraphAdapter()

        assert adapter.triple_count() == 0

        adapter.load_turtle("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")
        assert adapter.triple_count() == 1

        adapter.load_turtle("@prefix ex: <http://example.org/> . ex:d ex:e ex:f .")
        assert adapter.triple_count() == 2
