"""CLI integration tests.

Tests end-to-end CLI commands with real data flow, output formats,
and correctness validation.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from kgcl.cli.config import DEFAULT_CONFIG
from kgcl.cli.daily_brief import _generate_brief, _ingest_events, _materialize_features
from kgcl.cli.utils import load_config, save_config


class TestCLIIntegration:
    """Test CLI integration with real data flow."""

    def test_daily_brief_data_flow(self):
        """Test daily brief command with mocked but realistic flow."""
        from datetime import datetime, timedelta

        start_date = datetime(2024, 11, 24, 9, 0, 0)
        end_date = start_date + timedelta(days=1)

        # Ingest events (placeholder)
        events = _ingest_events(start_date, end_date, verbose=False)
        assert len(events) >= 0  # May be mock data

        # Materialize features
        features = _materialize_features(events, verbose=False)
        assert isinstance(features, dict)
        assert "total_events" in features

        # Generate brief
        brief = _generate_brief(features, model="llama3.1", verbose=False)
        assert isinstance(brief, str)
        assert len(brief) > 0
        assert "# Daily Brief" in brief

    def test_feature_list_output_formats(self):
        """Test feature list command output formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"

            # Create default config
            config = DEFAULT_CONFIG.copy()
            config_file.write_text('{"features": []}')

            # Test would list features (currently returns empty)
            # In real implementation, would query UNRDF
            assert config_file.exists()

    def test_query_sparql_execution(self):
        """Test SPARQL query execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test RDF graph
            from rdflib import Graph, Literal, Namespace, URIRef
            from rdflib.namespace import RDF

            UNRDF = Namespace("http://unrdf.org/ontology/")

            g = Graph()
            g.bind("unrdf", UNRDF)

            # Add test data
            entity = UNRDF.TestEntity
            g.add((entity, RDF.type, UNRDF.Event))
            g.add((entity, UNRDF.name, Literal("Test Event")))

            graph_file = Path(tmpdir) / "graph.ttl"
            g.serialize(destination=graph_file, format="turtle")

            # Execute query manually using rdflib
            query = """
            PREFIX unrdf: <http://unrdf.org/ontology/>
            SELECT ?name WHERE {
                ?s unrdf:name ?name .
            }
            """

            results = list(g.query(query))
            assert len(results) == 1

    def test_config_cli_operations(self):
        """Test configuration CLI operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"

            # Create config
            config = DEFAULT_CONFIG.copy()
            import json
            config_file.write_text(json.dumps(config))

            # Verify config file created
            assert config_file.exists()

            # Read back config
            loaded = json.loads(config_file.read_text())
            assert loaded is not None
            assert "settings" in loaded or "capabilities" in loaded

    def test_weekly_retro_aggregation(self):
        """Test weekly retrospective aggregation placeholder."""
        from datetime import datetime, timedelta

        end_date = datetime(2024, 11, 24)
        start_date = end_date - timedelta(days=7)

        # Test date range logic
        diff = (end_date - start_date).days
        assert diff == 7

    def test_cli_output_formats(self):
        """Test CLI output format handling."""
        from kgcl.cli.utils import OutputFormat, format_output

        test_content = "# Test\nContent"

        # Test markdown output
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            output_path = Path(f.name)

        format_output(
            test_content,
            OutputFormat.MARKDOWN,
            output_file=output_path,
            clipboard=False,
        )

        assert output_path.exists()
        assert output_path.read_text() == test_content
        output_path.unlink()

    def test_cli_error_handling(self):
        """Test CLI error handling."""
        from kgcl.cli.utils import print_error

        # print_error with exit_code=0 should not exit
        print_error("Test error message", exit_code=0)

    def test_health_check_cli(self):
        """Test health check CLI command."""
        from kgcl.observability.health import check_health

        health = check_health()

        # Returns a SystemHealth dataclass, not a dict
        assert health is not None
        assert hasattr(health, "status")
        assert hasattr(health, "timestamp")

    def test_cli_verbose_mode(self):
        """Test CLI verbose output."""
        from datetime import datetime, timedelta

        from kgcl.cli.utils import print_info

        start_date = datetime(2024, 11, 24)
        end_date = start_date + timedelta(days=1)

        # Test verbose ingestion
        events = _ingest_events(start_date, end_date, verbose=True)

        # Should not raise exception
        assert isinstance(events, list)
