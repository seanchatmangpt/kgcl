"""Integration tests for kgcl task CLI commands.

Chicago School TDD: Real CLI invocations, real HybridEngine.
No mocking. Tests verify actual task inspection.
"""

from __future__ import annotations

import tempfile

from click.testing import CliRunner

from kgcl.cli.app import app


class TestTaskList:
    """Integration tests for 'kgcl task list' command."""

    def test_task_list_shows_all_tasks(self) -> None:
        """List all tasks from topology.

        Verifies:
        - CLI accepts topology file
        - inspect() returns task statuses
        - Output displays task URIs and statuses
        """
        topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

<urn:task:Start> a yawl:Task ;
    kgc:status "Completed" ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:Process> .

<urn:task:Process> a yawl:Task ;
    kgc:status "Active" ;
    yawl:flowsInto <urn:flow:2> .

<urn:flow:2> yawl:nextElementRef <urn:task:End> .

<urn:task:End> a yawl:Task .
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            f.write(topology)
            f.flush()
            topology_path = f.name

        runner = CliRunner()
        result = runner.invoke(app, ["task", "list", topology_path])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # Should show task URIs
        assert "Start" in result.output or "urn:task" in result.output
        # Should show statuses
        assert "Completed" in result.output or "Active" in result.output

    def test_task_list_no_tasks(self) -> None:
        """List tasks when topology has no kgc:status triples.

        Verifies empty result handling.
        """
        topology = """
@prefix ex: <http://example.org/> .
ex:SomeResource ex:property "value" .
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            f.write(topology)
            f.flush()
            topology_path = f.name

        runner = CliRunner()
        result = runner.invoke(app, ["task", "list", topology_path])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert "No tasks" in result.output


class TestTaskInspect:
    """Integration tests for 'kgcl task inspect' command."""

    def test_task_inspect_shows_details(self) -> None:
        """Inspect specific task shows all properties.

        Verifies SPARQL query for task details.
        """
        topology = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<urn:task:Process> a yawl:Task ;
    rdfs:label "Process Task" ;
    kgc:status "Active" ;
    kgc:priority "high" ;
    yawl:flowsInto <urn:flow:1> .

<urn:flow:1> yawl:nextElementRef <urn:task:End> .
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            f.write(topology)
            f.flush()
            topology_path = f.name

        runner = CliRunner()
        result = runner.invoke(app, ["task", "inspect", topology_path, "urn:task:Process"])

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        # Should show task URI in header
        assert "Process" in result.output
        # Should show properties
        assert "status" in result.output.lower() or "Active" in result.output

    def test_task_inspect_nonexistent_task(self) -> None:
        """Inspect non-existent task shows not found.

        Verifies error handling.
        """
        topology = """
@prefix kgc: <https://kgc.org/ns/> .
<urn:task:Exists> kgc:status "Active" .
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ttl", delete=False) as f:
            f.write(topology)
            f.flush()
            topology_path = f.name

        runner = CliRunner()
        result = runner.invoke(app, ["task", "inspect", topology_path, "urn:task:NotFound"])

        assert result.exit_code == 0  # Command succeeds, just no results
        assert "not found" in result.output.lower()
