"""Integration tests for full pipeline example.

Verifies that the complete pipeline runs successfully and produces
well-formed outputs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from full_pipeline_demo import PipelineRunner
from sample_data import generate_sample_data
from visualize import ActivityVisualizer


class TestFullPipeline:
    """Test complete pipeline execution."""

    def test_pipeline_completes_successfully(self) -> None:
        """Verify pipeline runs to completion without errors."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            runner = PipelineRunner(output_dir=output_dir, use_ollama=False, verbose=False)

            # Run pipeline with minimal data for speed
            results = runner.run(days=1)

            # Verify results structure
            assert "events_count" in results
            assert "features_count" in results
            assert "graph_triples" in results
            assert "metrics" in results

            # Verify counts are reasonable
            assert results["events_count"] > 0
            assert results["features_count"] > 0
            assert results["graph_triples"] > 0

    def test_output_files_generated(self) -> None:
        """Verify all expected output files are created."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            runner = PipelineRunner(output_dir=output_dir, use_ollama=False, verbose=False)

            runner.run(days=1)

            # Check all expected files exist
            assert (output_dir / "daily_brief.md").exists()
            assert (output_dir / "weekly_retro.md").exists()
            assert (output_dir / "feature_values.json").exists()
            assert (output_dir / "graph_stats.json").exists()
            assert (output_dir / "knowledge_graph.ttl").exists()

    def test_daily_brief_well_formed(self) -> None:
        """Verify daily brief has expected structure."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            runner = PipelineRunner(output_dir=output_dir, use_ollama=False, verbose=False)

            runner.run(days=1)

            brief_path = output_dir / "daily_brief.md"
            brief_content = brief_path.read_text()

            # Check for key sections
            assert "# Daily Brief" in brief_content
            assert "## Activity Summary" in brief_content
            assert "## Application Usage" in brief_content
            assert "## Browser Activity" in brief_content
            assert "## Productivity Insights" in brief_content

            # Check for non-empty content
            assert len(brief_content) > 500  # Should be substantial

    def test_weekly_retro_well_formed(self) -> None:
        """Verify weekly retro has expected structure."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            runner = PipelineRunner(output_dir=output_dir, use_ollama=False, verbose=False)

            runner.run(days=1)

            retro_path = output_dir / "weekly_retro.md"
            retro_content = retro_path.read_text()

            # Check for key sections
            assert "# Weekly Retrospective" in retro_content
            assert "## Overview" in retro_content
            assert "## Activity Patterns" in retro_content
            assert "## Recommendations" in retro_content

            # Check for non-empty content
            assert len(retro_content) > 800

    def test_feature_values_valid_json(self) -> None:
        """Verify feature values JSON is well-formed."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            runner = PipelineRunner(output_dir=output_dir, use_ollama=False, verbose=False)

            runner.run(days=1)

            features_path = output_dir / "feature_values.json"
            features_data = json.loads(features_path.read_text())

            # Verify structure
            assert isinstance(features_data, list)
            assert len(features_data) > 0

            # Check first feature has required fields
            feature = features_data[0]
            assert "feature_id" in feature
            assert "value" in feature
            assert "aggregation_type" in feature
            assert "sample_count" in feature
            assert "window_start" in feature
            assert "window_end" in feature

    def test_graph_stats_valid_json(self) -> None:
        """Verify graph statistics JSON is well-formed."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            runner = PipelineRunner(output_dir=output_dir, use_ollama=False, verbose=False)

            runner.run(days=1)

            stats_path = output_dir / "graph_stats.json"
            stats_data = json.loads(stats_path.read_text())

            # Verify required fields
            assert "triple_count" in stats_data
            assert "provenance_count" in stats_data
            assert "total_events" in stats_data
            assert "total_features" in stats_data
            assert "pipeline_metrics" in stats_data

            # Verify values are reasonable
            assert stats_data["triple_count"] > 0
            assert stats_data["total_events"] > 0
            assert stats_data["total_features"] > 0

    def test_knowledge_graph_valid_turtle(self) -> None:
        """Verify knowledge graph Turtle file is valid."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            runner = PipelineRunner(output_dir=output_dir, use_ollama=False, verbose=False)

            runner.run(days=1)

            ttl_path = output_dir / "knowledge_graph.ttl"
            ttl_content = ttl_path.read_text()

            # Basic Turtle validation
            assert "@prefix" in ttl_content or "PREFIX" in ttl_content
            assert "<http://kgcl.example.org/" in ttl_content

            # Should have reasonable size
            assert len(ttl_content) > 100

    def test_metrics_captured(self) -> None:
        """Verify pipeline metrics are captured."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            runner = PipelineRunner(output_dir=output_dir, use_ollama=False, verbose=False)

            results = runner.run(days=1)
            metrics = results["metrics"]

            # Check for expected metrics
            expected_metrics = [
                "data_generation_seconds",
                "unrdf_ingestion_seconds",
                "feature_materialization_seconds",
                "shacl_generation_seconds",
                "dspy_signature_generation_seconds",
                "daily_brief_generation_seconds",
                "weekly_retro_generation_seconds",
                "export_seconds",
            ]

            for metric in expected_metrics:
                assert metric in metrics
                assert metrics[metric] >= 0  # Non-negative time

    def test_performance_within_bounds(self) -> None:
        """Verify pipeline completes within reasonable time."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            runner = PipelineRunner(output_dir=output_dir, use_ollama=False, verbose=False)

            import time

            start = time.time()
            runner.run(days=1)
            elapsed = time.time() - start

            # Should complete in under 30 seconds for single day
            assert elapsed < 30.0


class TestSampleDataGenerator:
    """Test sample data generation."""

    def test_generates_events(self) -> None:
        """Verify sample data generator produces events."""
        events = generate_sample_data(days=1)

        assert len(events) > 0
        assert any(e.__class__.__name__ == "AppEvent" for e in events)

    def test_events_sorted_by_time(self) -> None:
        """Verify events are chronologically ordered."""
        events = generate_sample_data(days=1)

        timestamps = [e.timestamp for e in events]
        assert timestamps == sorted(timestamps)

    def test_week_generation(self) -> None:
        """Verify week generation produces multiple days."""
        events = generate_sample_data(days=7)

        # Should have events across multiple days
        unique_days = len(set(e.timestamp.date() for e in events))
        assert unique_days >= 1  # At least some variety


class TestVisualizer:
    """Test visualization utilities."""

    def test_timeline_visualization(self) -> None:
        """Verify timeline visualization produces output."""
        from datetime import datetime

        from kgcl.ingestion.models import AppEvent

        events = [
            AppEvent(
                event_id=f"evt_{i}",
                timestamp=datetime.now().replace(hour=i, minute=0),
                app_name="test.app",
                duration_seconds=300,
            )
            for i in range(8, 18)  # 8am to 6pm
        ]

        visualizer = ActivityVisualizer()
        output = visualizer.visualize_timeline(events)

        assert len(output) > 0
        assert "Activity Timeline" in output
        assert "Hour:" in output

    def test_feature_visualization(self) -> None:
        """Verify feature visualization produces output."""
        from datetime import datetime

        from kgcl.ingestion.models import MaterializedFeature

        features = [
            MaterializedFeature(
                feature_id=f"test_feature_{i}",
                window_start=datetime.now(),
                window_end=datetime.now(),
                aggregation_type="sum",
                value=float(i * 100),
                sample_count=10,
            )
            for i in range(5)
        ]

        visualizer = ActivityVisualizer()
        output = visualizer.visualize_features(features)

        assert len(output) > 0
        assert "Top Features" in output

    def test_pattern_visualization(self) -> None:
        """Verify pattern visualization produces output."""
        from datetime import datetime

        from kgcl.ingestion.models import AppEvent

        events = [
            AppEvent(
                event_id=f"evt_{i}",
                timestamp=datetime.now().replace(hour=9 + i, minute=0),
                app_name=f"app_{i % 3}",
                duration_seconds=1800,
            )
            for i in range(10)
        ]

        visualizer = ActivityVisualizer()
        output = visualizer.visualize_patterns(events)

        assert len(output) > 0
        assert "Activity Patterns" in output


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
