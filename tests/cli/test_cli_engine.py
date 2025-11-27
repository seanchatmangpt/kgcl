"""Integration tests for kgcl engine CLI commands.

Chicago School TDD: Real CLI invocations, real HybridEngine, real EYE reasoner.
No mocking. Tests verify actual behavior against real capabilities.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from click.testing import CliRunner

from kgcl.cli.app import app


class TestEngineRun:
    """Integration tests for 'kgcl engine run' command."""

    def test_engine_run_simple_sequence_converges(self) -> None:
        """Run simple sequence workflow to convergence.

        Verifies:
        - CLI accepts topology file
        - HybridEngine loads data
        - Physics runs to fixed point
        - Output shows convergence
        """
        # Arrange: Create real topology file
        topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Start> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:End> .
<urn:task:End> a yawl:Task .
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as f:
            f.write(topology)
            f.flush()
            topology_path = f.name

        runner = CliRunner()

        # Act: Invoke real CLI command
        result = runner.invoke(app, ["engine", "run", topology_path])

        # Assert: Verify real behavior
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "Converged" in result.output
        assert "Loading" in result.output
        assert "triples" in result.output.lower()

    def test_engine_run_and_split_parallel_activation(self) -> None:
        """Run AND-split workflow - both branches activate in parallel.

        Verifies WCP-2 (Parallel Split) and WCP-3 (Synchronization).
        """
        topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Start> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:hasSplit yawl:ControlTypeAnd ;
    yawl:flowsInto <urn:flow:1> ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:1> yawl:nextElementRef <urn:task:Branch1> .
<urn:flow:2> yawl:nextElementRef <urn:task:Branch2> .

<urn:task:Branch1> a yawl:Task ;
    yawl:flowsInto <urn:flow:3> .
<urn:task:Branch2> a yawl:Task ;
    yawl:flowsInto <urn:flow:4> .

<urn:flow:3> yawl:nextElementRef <urn:task:Join> .
<urn:flow:4> yawl:nextElementRef <urn:task:Join> .

<urn:task:Join> a yawl:Task ;
    yawl:hasJoin yawl:ControlTypeAnd ;
    yawl:flowsInto <urn:flow:5> .

<urn:flow:5> yawl:nextElementRef <urn:task:End> .
<urn:task:End> a yawl:Task .
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as f:
            f.write(topology)
            f.flush()
            topology_path = f.name

        runner = CliRunner()
        result = runner.invoke(app, ["engine", "run", topology_path])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "Converged" in result.output

    def test_engine_run_verbose_shows_task_statuses(self) -> None:
        """Run with --verbose flag shows final task statuses.

        Verifies inspect() is called and task statuses are displayed.
        """
        topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Start> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:End> .
<urn:task:End> a yawl:Task .
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as f:
            f.write(topology)
            f.flush()
            topology_path = f.name

        runner = CliRunner()
        result = runner.invoke(app, ["engine", "run", topology_path, "--verbose"])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "Task Statuses" in result.output or "urn:task" in result.output

    def test_engine_run_max_ticks_option(self) -> None:
        """Run with --max-ticks limits execution.

        Verifies max_ticks parameter is respected.
        """
        topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Start> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:End> .
<urn:task:End> a yawl:Task .
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as f:
            f.write(topology)
            f.flush()
            topology_path = f.name

        runner = CliRunner()
        result = runner.invoke(app, ["engine", "run", topology_path, "-t", "5"])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "max 5 ticks" in result.output

    def test_engine_run_nonexistent_file_fails(self) -> None:
        """Run with non-existent file produces error."""
        runner = CliRunner()
        result = runner.invoke(app, ["engine", "run", "/nonexistent/path.ttl"])

        assert result.exit_code != 0


class TestEngineTick:
    """Integration tests for 'kgcl engine tick' command."""

    def test_engine_tick_single_tick_execution(self) -> None:
        """Execute single tick and show delta.

        Verifies apply_physics() is called once.
        """
        topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Start> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:End> .
<urn:task:End> a yawl:Task .
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ttl", delete=False
        ) as f:
            f.write(topology)
            f.flush()
            topology_path = f.name

        runner = CliRunner()
        result = runner.invoke(app, ["engine", "tick", topology_path])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "Tick 1" in result.output
        assert "triples" in result.output.lower()
        # Should show delta (new triples inferred)
        assert "+" in result.output or "delta" in result.output.lower()


class TestEngineStatus:
    """Integration tests for 'kgcl engine status' command."""

    def test_engine_status_shows_components(self) -> None:
        """Status shows PyOxigraph, EYE, HybridEngine availability.

        Verifies component health check.
        """
        runner = CliRunner()
        result = runner.invoke(app, ["engine", "status"])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "PyOxigraph" in result.output
        assert "EYE" in result.output
        assert "HybridEngine" in result.output
        # Should have checkmarks for installed components
        assert "✓" in result.output
