"""Tests for query CLI command."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import TYPE_CHECKING
from urllib.parse import parse_qs

import pytest
from click.testing import CliRunner

from kgcl.cli.query import TEMPLATE_QUERIES, Verbosity, _execute_query, query

if TYPE_CHECKING:
    from pathlib import Path

SAMPLE_TTL = """
@prefix kgcl: <http://kgcl.io/ontology#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

kgcl:FeatureAlpha a kgcl:Feature ;
    kgcl:type "template" ;
    kgcl:category "testing" ;
    kgcl:dependsOn kgcl:FeatureBeta .

kgcl:FeatureBeta a kgcl:Feature ;
    kgcl:type "template" ;
    kgcl:category "quality" .

kgcl:Instance1 a kgcl:FeatureInstance ;
    kgcl:template kgcl:FeatureAlpha ;
    kgcl:value "0.9"^^xsd:decimal .
"""


@pytest.fixture
def sample_dataset(tmp_path: Path) -> Path:
    """Create a temporary RDF dataset for CLI tests."""
    dataset = tmp_path / "graph.ttl"
    dataset.write_text(SAMPLE_TTL, encoding="utf-8")
    return dataset


def test_query_help() -> None:
    """Test query help output."""
    runner = CliRunner()
    result = runner.invoke(query, ["--help"])
    assert result.exit_code == 0
    assert "Execute SPARQL queries" in result.output
    assert "--query" in result.output
    assert "--template" in result.output


def test_query_show_templates() -> None:
    """Test showing query templates."""
    runner = CliRunner()
    result = runner.invoke(query, ["--show-templates"])
    assert result.exit_code == 0
    assert "Available Query Templates" in result.output
    assert "all_features" in result.output


def test_query_with_template(sample_dataset: Path) -> None:
    """Test query using a template."""
    runner = CliRunner()
    result = runner.invoke(query, ["--template", "all_features", "--endpoint", str(sample_dataset)])
    assert result.exit_code == 0
    assert "Query executed successfully" in result.output


def test_query_with_custom_query(sample_dataset: Path) -> None:
    """Test query with custom SPARQL."""
    runner = CliRunner()
    result = runner.invoke(
        query, ["--query", "SELECT * WHERE { ?s ?p ?o } LIMIT 10", "--endpoint", str(sample_dataset)]
    )
    assert result.exit_code == 0


def test_query_with_limit(sample_dataset: Path) -> None:
    """Test query with result limit."""
    runner = CliRunner()
    result = runner.invoke(query, ["--template", "all_features", "--limit", "5", "--endpoint", str(sample_dataset)])
    assert result.exit_code == 0


def test_query_output_formats(sample_dataset: Path) -> None:
    """Test different output formats."""
    runner = CliRunner()

    # Test table format
    result = runner.invoke(
        query, ["--template", "all_features", "--format", "table", "--endpoint", str(sample_dataset)]
    )
    assert result.exit_code == 0

    # Test JSON format
    result = runner.invoke(query, ["--template", "all_features", "--format", "json", "--endpoint", str(sample_dataset)])
    assert result.exit_code == 0


def test_query_with_output_file(sample_dataset: Path, tmp_path: Path) -> None:
    """Test query with output file."""
    runner = CliRunner()
    output_path = tmp_path / "results.json"
    result = runner.invoke(
        query,
        [
            "--template",
            "all_features",
            "--format",
            "json",
            "--output",
            str(output_path),
            "--endpoint",
            str(sample_dataset),
        ],
    )
    assert result.exit_code == 0
    assert output_path.exists()
    exported = json.loads(output_path.read_text(encoding="utf-8"))
    assert exported


def test_query_verbose(sample_dataset: Path) -> None:
    """Test query with verbose output."""
    runner = CliRunner()
    result = runner.invoke(query, ["--template", "all_features", "--verbose", "--endpoint", str(sample_dataset)])
    assert result.exit_code == 0
    assert "Executing query" in result.output


def test_query_no_params() -> None:
    """Test query without parameters shows error."""
    runner = CliRunner()
    result = runner.invoke(query, [])
    assert result.exit_code == 1
    assert "No query specified" in result.output


def test_template_queries_valid() -> None:
    """Test that all template queries are valid strings."""
    assert len(TEMPLATE_QUERIES) > 0
    for name, query_str in TEMPLATE_QUERIES.items():
        assert isinstance(name, str)
        assert isinstance(query_str, str)
        assert len(query_str.strip()) > 0


def test_execute_query_with_local_dataset(sample_dataset: Path) -> None:
    """_execute_query should return RDF bindings for local dataset endpoints."""
    results = _execute_query(TEMPLATE_QUERIES["all_features"], str(sample_dataset), Verbosity.QUIET)
    assert any(binding["feature"].endswith("FeatureAlpha") for binding in results)
    assert any(binding["feature"].endswith("FeatureBeta") for binding in results)


class _StaticSparqlHandler(BaseHTTPRequestHandler):
    """Serve static SPARQL JSON responses for HTTP execution tests."""

    last_query: str = ""

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        type(self).last_query = body.decode("utf-8")
        payload = {
            "head": {"vars": ["feature", "category"]},
            "results": {
                "bindings": [{"feature": {"type": "literal", "value": "alpha"}, "category": {"value": "testing"}}]
            },
        }
        response_data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/sparql-results+json")
        self.send_header("Content-Length", str(len(response_data)))
        self.end_headers()
        self.wfile.write(response_data)

    def log_message(self, _message_format: str, *_args: object) -> None:
        """Suppress default stdout logging for cleaner test output."""
        return


def test_execute_query_over_http() -> None:
    """_execute_query should parse HTTP SPARQL JSON responses."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StaticSparqlHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]
        endpoint = f"http://127.0.0.1:{port}/sparql"
        results = _execute_query("SELECT ?feature ?category WHERE { ?s ?p ?o }", endpoint, Verbosity.QUIET)

        assert results == [{"feature": "alpha", "category": "testing"}]
        parsed = parse_qs(_StaticSparqlHandler.last_query)
        assert "query" in parsed
        assert parsed["query"][0].startswith("SELECT ?feature ?category")
    finally:
        server.shutdown()
        server.server_close()  # Close the socket to prevent ResourceWarning
        thread.join()
