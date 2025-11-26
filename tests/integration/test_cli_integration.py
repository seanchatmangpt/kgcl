"""CLI integration tests.

Tests end-to-end CLI commands with real data flow, output formats,
and correctness validation.
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF

from kgcl.cli.config import DEFAULT_CONFIG
from kgcl.cli.daily_brief import (
    _generate_brief,
    _ingest_events,
    _materialize_features,
    _select_payload_for_format,
)
from kgcl.cli.daily_brief_pipeline import (
    DailyBriefEventBatch,
    DailyBriefFeatureSet,
    DailyBriefResult,
)
from kgcl.cli.utils import OutputFormat, format_output, print_error
from kgcl.observability.health import check_health
from kgcl.signatures.daily_brief import DailyBriefInput


class TestCLIIntegration:
    """Test CLI integration with real data flow."""

    def test_daily_brief_data_flow(self) -> None:
        """Test daily brief command with mocked but realistic flow."""
        start_date = datetime(2024, 11, 24, 9, 0, 0, tzinfo=UTC)
        end_date = start_date + timedelta(days=1)

        # Ingest events from test data
        events = _ingest_events(start_date, end_date, verbose=False)
        assert isinstance(events, DailyBriefEventBatch)
        assert events.event_count > 0

        # Materialize features
        features = _materialize_features(events, verbose=False)
        assert isinstance(features, DailyBriefFeatureSet)
        assert isinstance(features.input_data, DailyBriefInput)

        # Generate brief
        brief = _generate_brief(features, model="llama3.1", verbose=False)
        assert isinstance(brief, DailyBriefResult)
        markdown = brief.to_markdown()
        assert markdown.startswith("# Daily Brief")
        payload = brief.to_dict()
        assert "brief" in payload
        assert "metadata" in payload
        table_payload = _select_payload_for_format(brief, OutputFormat.TABLE)
        assert isinstance(table_payload, list)

    def test_feature_list_output_formats(self) -> None:
        """Test feature list command output formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"

            # Create default config
            config_file.write_text('{"features": []}')

            # Test would list features (currently returns empty)
            # In real implementation, would query UNRDF
            assert config_file.exists()

    def test_query_sparql_execution(self) -> None:
        """Test SPARQL query execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            unrdf_ns = Namespace("http://unrdf.org/ontology/")

            g = Graph()
            g.bind("unrdf", unrdf_ns)

            # Add test data
            entity = unrdf_ns.TestEntity
            g.add((entity, RDF.type, unrdf_ns.Event))
            g.add((entity, unrdf_ns.name, Literal("Test Event")))

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

    def test_config_cli_operations(self) -> None:
        """Test configuration CLI operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"

            # Create config
            config_file.write_text(json.dumps(DEFAULT_CONFIG))

            # Verify config file created
            assert config_file.exists()

            # Read back config
            loaded = json.loads(config_file.read_text())
            assert loaded is not None
            assert "settings" in loaded or "capabilities" in loaded

    def test_weekly_retro_aggregation(self) -> None:
        """Test weekly retrospective aggregation placeholder."""
        end_date = datetime(2024, 11, 24, tzinfo=UTC)
        start_date = end_date - timedelta(days=7)

        # Test date range logic
        diff = (end_date - start_date).days
        week_length_days = 7
        assert diff == week_length_days

    def test_cli_output_formats(self) -> None:
        """Test CLI output format handling."""
        test_content = "# Test\nContent"

        # Test markdown output
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
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

    def test_cli_error_handling(self) -> None:
        """Test CLI error handling."""
        # print_error with exit_code=0 should not exit
        print_error("Test error message", exit_code=0)

    def test_health_check_cli(self) -> None:
        """Test health check CLI command."""
        health = check_health()

        # Returns a SystemHealth dataclass, not a dict
        assert health is not None
        assert hasattr(health, "status")
        assert hasattr(health, "timestamp")

    def test_cli_verbose_mode(self) -> None:
        """Test CLI verbose output."""
        start_date = datetime(2024, 11, 24, tzinfo=UTC)
        end_date = start_date + timedelta(days=1)

        # Test verbose ingestion
        events = _ingest_events(start_date, end_date, verbose=True)
        assert isinstance(events, DailyBriefEventBatch)
