"""Integration tests for kgcl store CLI commands.

Chicago School TDD: Real CLI invocations, real PyOxigraph store.
No mocking. Tests verify actual SPARQL query execution.
"""

from __future__ import annotations

import tempfile

from click.testing import CliRunner

from kgcl.cli.app import app


class TestStoreQuery:
    """Integration tests for 'kgcl store query' command."""

    def test_store_query_simple_select_all(self) -> None:
        """Execute SPARQL SELECT * query.

        Verifies:
        - CLI accepts SPARQL string
        - Query executes against real store
        - Results displayed in table format
        """
        # Arrange: Create RDF data file
        data = """
@prefix ex: <http://example.org/> .

ex:Alice ex:name "Alice" .
ex:Bob ex:name "Bob" .
ex:Alice ex:knows ex:Bob .
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as f:
            f.write(data)
            f.flush()
            data_path = f.name

        runner = CliRunner()

        # Act: Query with file loaded
        result = runner.invoke(
            app,
            [
                "store",
                "query",
                "SELECT ?s ?p ?o WHERE { ?s ?p ?o }",
                "-f",
                data_path,
            ],
        )

        # Assert
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "results" in result.output.lower()
        assert "Alice" in result.output or "ex:Alice" in result.output

    def test_store_query_filtered_select(self) -> None:
        """Execute SPARQL query with filter.

        Verifies complex query execution.
        """
        data = """
@prefix ex: <http://example.org/> .

ex:Alice ex:age 30 .
ex:Bob ex:age 25 .
ex:Carol ex:age 35 .
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as f:
            f.write(data)
            f.flush()
            data_path = f.name

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "store",
                "query",
                'SELECT ?person WHERE { ?person <http://example.org/age> ?age . FILTER(?age > 28) }',
                "-f",
                data_path,
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # Should find Alice (30) and Carol (35), not Bob (25)
        assert "results" in result.output.lower()

    def test_store_query_json_format(self) -> None:
        """Query with JSON output format.

        Verifies --format json option.
        """
        data = """
@prefix ex: <http://example.org/> .
ex:Alice ex:name "Alice" .
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as f:
            f.write(data)
            f.flush()
            data_path = f.name

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "store",
                "query",
                "SELECT ?s ?o WHERE { ?s <http://example.org/name> ?o }",
                "-f",
                data_path,
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # JSON output should have brackets
        assert "[" in result.output and "]" in result.output

    def test_store_query_csv_format(self) -> None:
        """Query with CSV output format.

        Verifies --format csv option.
        """
        data = """
@prefix ex: <http://example.org/> .
ex:Alice ex:name "Alice" .
ex:Bob ex:name "Bob" .
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as f:
            f.write(data)
            f.flush()
            data_path = f.name

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "store",
                "query",
                "SELECT ?s ?o WHERE { ?s <http://example.org/name> ?o }",
                "-f",
                data_path,
                "--format",
                "csv",
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # CSV has commas
        assert "," in result.output

    def test_store_query_no_results(self) -> None:
        """Query that returns no results.

        Verifies empty result handling.
        """
        data = """
@prefix ex: <http://example.org/> .
ex:Alice ex:name "Alice" .
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as f:
            f.write(data)
            f.flush()
            data_path = f.name

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "store",
                "query",
                "SELECT ?x WHERE { ?x <http://example.org/nonexistent> ?y }",
                "-f",
                data_path,
            ],
        )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "No results" in result.output

    def test_store_query_invalid_sparql_fails(self) -> None:
        """Invalid SPARQL produces error.

        Verifies error handling.
        """
        data = """
@prefix ex: <http://example.org/> .
ex:Alice ex:name "Alice" .
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as f:
            f.write(data)
            f.flush()
            data_path = f.name

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "store",
                "query",
                "NOT VALID SPARQL",
                "-f",
                data_path,
            ],
        )

        assert result.exit_code != 0


class TestStoreLoad:
    """Integration tests for 'kgcl store load' command."""

    def test_store_load_turtle_file(self) -> None:
        """Load Turtle file into store.

        Verifies data loading and triple count.
        """
        data = """
@prefix ex: <http://example.org/> .

ex:Alice ex:name "Alice" .
ex:Bob ex:name "Bob" .
ex:Alice ex:knows ex:Bob .
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as f:
            f.write(data)
            f.flush()
            data_path = f.name

        runner = CliRunner()
        result = runner.invoke(app, ["store", "load", data_path])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "Loaded" in result.output
        assert "triples" in result.output.lower()
        # Should have loaded 3 triples
        assert "3" in result.output


class TestStoreDump:
    """Integration tests for 'kgcl store dump' command."""

    def test_store_dump_outputs_triples(self) -> None:
        """Dump store contents after loading.

        Verifies serialization.
        """
        data = """
@prefix ex: <http://example.org/> .

ex:Alice ex:name "Alice" .
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as f:
            f.write(data)
            f.flush()
            data_path = f.name

        runner = CliRunner()
        result = runner.invoke(app, ["store", "dump", data_path])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # Should output N-Triples format with subject predicate object
        assert "Alice" in result.output or "example.org" in result.output
