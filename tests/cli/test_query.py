"""Tests for query CLI command."""

from click.testing import CliRunner

from kgcl.cli.query import TEMPLATE_QUERIES, query


def test_query_help():
    """Test query help output."""
    runner = CliRunner()
    result = runner.invoke(query, ["--help"])
    assert result.exit_code == 0
    assert "Execute SPARQL queries" in result.output
    assert "--query" in result.output
    assert "--template" in result.output


def test_query_show_templates():
    """Test showing query templates."""
    runner = CliRunner()
    result = runner.invoke(query, ["--show-templates"])
    assert result.exit_code == 0
    assert "Available Query Templates" in result.output
    assert "all_features" in result.output


def test_query_with_template():
    """Test query using a template."""
    runner = CliRunner()
    result = runner.invoke(query, ["--template", "all_features"])
    assert result.exit_code == 0
    assert "Query executed successfully" in result.output


def test_query_with_custom_query():
    """Test query with custom SPARQL."""
    runner = CliRunner()
    result = runner.invoke(query, ["--query", "SELECT * WHERE { ?s ?p ?o } LIMIT 10"])
    assert result.exit_code == 0


def test_query_with_limit():
    """Test query with result limit."""
    runner = CliRunner()
    result = runner.invoke(query, ["--template", "all_features", "--limit", "5"])
    assert result.exit_code == 0


def test_query_output_formats():
    """Test different output formats."""
    runner = CliRunner()

    # Test table format
    result = runner.invoke(query, ["--template", "all_features", "--format", "table"])
    assert result.exit_code == 0

    # Test JSON format
    result = runner.invoke(query, ["--template", "all_features", "--format", "json"])
    assert result.exit_code == 0


def test_query_with_output_file():
    """Test query with output file."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            query, ["--template", "all_features", "--format", "json", "--output", "results.json"]
        )
        assert result.exit_code == 0


def test_query_verbose():
    """Test query with verbose output."""
    runner = CliRunner()
    result = runner.invoke(query, ["--template", "all_features", "--verbose"])
    assert result.exit_code == 0
    assert "Executing query" in result.output


def test_query_no_params():
    """Test query without parameters shows error."""
    runner = CliRunner()
    result = runner.invoke(query, [])
    assert result.exit_code == 1
    assert "No query specified" in result.output


def test_template_queries_valid():
    """Test that all template queries are valid strings."""
    assert len(TEMPLATE_QUERIES) > 0
    for name, query_str in TEMPLATE_QUERIES.items():
        assert isinstance(name, str)
        assert isinstance(query_str, str)
        assert len(query_str.strip()) > 0
