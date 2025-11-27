"""Integration tests for RemoteStoreAdapter against Oxigraph container.

Tests verify the RemoteStoreAdapter can correctly:
- Connect to a real SPARQL endpoint
- Load Turtle/N3 data via SPARQL UPDATE
- Execute SPARQL SELECT queries
- Execute SPARQL ASK queries
- Clear the store
- Handle errors gracefully

Examples
--------
>>> uv run pytest tests/integration/test_remote_store_adapter.py -v
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

if TYPE_CHECKING:
    pass


@pytest.mark.container
class TestRemoteStoreAdapterOxigraph:
    """Integration tests for RemoteStoreAdapter with Oxigraph container."""

    def test_connection_and_empty_store(
        self, oxigraph_container: dict[str, str]
    ) -> None:
        """Verify adapter connects and reports empty store."""
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container["query"],
            update_endpoint=oxigraph_container["update"],
            store_endpoint=oxigraph_container["store"],
        )

        # Fresh store should be empty
        count = adapter.triple_count()
        assert count == 0, f"Expected empty store, got {count} triples"

    def test_load_turtle_and_query(
        self, oxigraph_container: dict[str, str]
    ) -> None:
        """Load Turtle data and verify via SPARQL query."""
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container["query"],
            update_endpoint=oxigraph_container["update"],
            store_endpoint=oxigraph_container["store"],
        )

        # Clear any existing data
        adapter.clear()

        # Load test data
        turtle_data = """
            @prefix ex: <http://example.org/> .
            @prefix kgc: <https://kgc.org/ns/> .

            ex:task1 a ex:Task ;
                kgc:status "Active" ;
                ex:name "Receive Order" .

            ex:task2 a ex:Task ;
                kgc:status "Pending" ;
                ex:name "Process Payment" .
        """

        count = adapter.load_turtle(turtle_data)
        assert count >= 2, f"Expected at least 2 triples loaded, got {count}"

        # Verify data via query
        results = adapter.query("""
            PREFIX ex: <http://example.org/>
            PREFIX kgc: <https://kgc.org/ns/>

            SELECT ?task ?status WHERE {
                ?task a ex:Task ;
                    kgc:status ?status .
            }
            ORDER BY ?task
        """)

        assert len(results) == 2, f"Expected 2 tasks, got {len(results)}"

        # Check task statuses
        statuses = {r["status"] for r in results}
        assert "Active" in statuses
        assert "Pending" in statuses

        # Cleanup
        adapter.clear()

    def test_ask_query(self, oxigraph_container: dict[str, str]) -> None:
        """Test ASK query returns correct boolean."""
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container["query"],
            update_endpoint=oxigraph_container["update"],
            store_endpoint=oxigraph_container["store"],
        )

        adapter.clear()

        # Load a single triple
        adapter.load_turtle("""
            @prefix ex: <http://example.org/> .
            ex:task1 ex:status "Active" .
        """)

        # ASK for existing pattern - should be True
        exists = adapter.ask("""
            PREFIX ex: <http://example.org/>
            ASK { ex:task1 ex:status "Active" }
        """)
        assert exists is True

        # ASK for non-existing pattern - should be False
        not_exists = adapter.ask("""
            PREFIX ex: <http://example.org/>
            ASK { ex:task1 ex:status "Completed" }
        """)
        assert not_exists is False

        adapter.clear()

    def test_triple_count(self, oxigraph_container: dict[str, str]) -> None:
        """Verify triple count is accurate."""
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container["query"],
            update_endpoint=oxigraph_container["update"],
            store_endpoint=oxigraph_container["store"],
        )

        adapter.clear()
        assert adapter.triple_count() == 0

        # Load exactly 3 triples
        adapter.load_turtle("""
            @prefix ex: <http://example.org/> .
            ex:s1 ex:p1 ex:o1 .
            ex:s2 ex:p2 ex:o2 .
            ex:s3 ex:p3 ex:o3 .
        """)

        count = adapter.triple_count()
        assert count == 3, f"Expected 3 triples, got {count}"

        adapter.clear()
        assert adapter.triple_count() == 0

    def test_dump_returns_turtle(self, oxigraph_container: dict[str, str]) -> None:
        """Verify dump() returns valid Turtle serialization."""
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container["query"],
            update_endpoint=oxigraph_container["update"],
            store_endpoint=oxigraph_container["store"],
        )

        adapter.clear()

        # Load data
        adapter.load_turtle("""
            @prefix ex: <http://example.org/> .
            ex:subject ex:predicate "object" .
        """)

        # Dump should return Turtle
        output = adapter.dump()
        assert isinstance(output, str)
        assert len(output) > 0

        # Should contain the triple components
        assert "subject" in output or "ex:subject" in output
        assert "predicate" in output or "ex:predicate" in output
        assert "object" in output

        adapter.clear()

    def test_update_sparql(self, oxigraph_container: dict[str, str]) -> None:
        """Test direct SPARQL UPDATE execution."""
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container["query"],
            update_endpoint=oxigraph_container["update"],
            store_endpoint=oxigraph_container["store"],
        )

        adapter.clear()

        # Insert via SPARQL UPDATE
        adapter.update("""
            PREFIX ex: <http://example.org/>
            INSERT DATA {
                ex:task1 ex:status "Active" .
            }
        """)

        assert adapter.triple_count() == 1

        # Delete via SPARQL UPDATE
        adapter.update("""
            PREFIX ex: <http://example.org/>
            DELETE DATA {
                ex:task1 ex:status "Active" .
            }
        """)

        assert adapter.triple_count() == 0

    def test_load_n3_as_turtle(self, oxigraph_container: dict[str, str]) -> None:
        """Test that load_n3 works for Turtle-compatible N3."""
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container["query"],
            update_endpoint=oxigraph_container["update"],
            store_endpoint=oxigraph_container["store"],
        )

        adapter.clear()

        # N3 that's Turtle-compatible
        n3_data = """
            @prefix ex: <http://example.org/> .
            ex:task1 ex:status "Active" .
        """

        count = adapter.load_n3(n3_data)
        assert count >= 1

        adapter.clear()

    def test_workflow_pattern_data(
        self, oxigraph_container: dict[str, str]
    ) -> None:
        """Test loading and querying WCP workflow pattern data."""
        adapter = RemoteStoreAdapter(
            query_endpoint=oxigraph_container["query"],
            update_endpoint=oxigraph_container["update"],
            store_endpoint=oxigraph_container["store"],
        )

        adapter.clear()

        # Load WCP-1 Sequence pattern data
        adapter.load_turtle("""
            @prefix kgc: <https://kgc.org/ns/> .
            @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

            <urn:task:A> a yawl:Task ;
                kgc:status "Completed" ;
                yawl:flowsInto [ yawl:nextElementRef <urn:task:B> ] .

            <urn:task:B> a yawl:Task ;
                kgc:status "Pending" .
        """)

        # Query for pending tasks that should be activated
        results = adapter.query("""
            PREFIX kgc: <https://kgc.org/ns/>
            PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>

            SELECT ?next WHERE {
                ?task kgc:status "Completed" ;
                    yawl:flowsInto ?flow .
                ?flow yawl:nextElementRef ?next .
                ?next kgc:status "Pending" .
            }
        """)

        assert len(results) == 1
        assert results[0]["next"] == "urn:task:B"

        adapter.clear()
