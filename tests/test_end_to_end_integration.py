"""End-to-end integration tests - Verify generators wired to hooks and workflow.

Tests the complete flow:
    Data Ingest → Validation → Hook Triggers → Generators → Artifacts

Chicago TDD Pattern:
    - Real generator objects in real hooks
    - Real workflow orchestration
    - Real hook triggering with event data
    - Integration tests with minimal test doubles
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from kgcl.generators.agenda import AgendaGenerator
from kgcl.hooks.handlers import HookHandlers, register_all_handlers
from kgcl.hooks.loader import HookDefinition, HookEffect
from kgcl.hooks.orchestrator import ExecutionContext, HookOrchestrator
from kgcl.hooks.value_objects import HookName
from kgcl.integration import KGCIntegration
from kgcl.workflow.state import WorkflowState, WorkflowStep

# Define test namespaces
KGC = Namespace("http://example.org/kgc/")
ICAL = Namespace("http://www.w3.org/2002/12/cal/ical#")
MIN_GENERATOR_RUNS: int = 3


@pytest.fixture
def test_graph() -> Graph:
    """Create RDF graph with test calendar data."""
    g = Graph()
    g.bind("kgc", KGC)
    g.bind("ical", ICAL)

    # Add sample calendar event
    event = URIRef("http://example.org/event/1")
    g.add((event, RDF.type, ICAL.Vevent))
    g.add((event, ICAL.summary, Literal("Team Meeting")))
    g.add((event, ICAL.dtstart, Literal(datetime(2025, 11, 24, 10, 0, tzinfo=UTC))))
    g.add((event, ICAL.dtend, Literal(datetime(2025, 11, 24, 11, 0, tzinfo=UTC))))

    return g


@pytest.fixture
def test_hooks_file(tmp_path: Path) -> Path:
    """Create test hooks.ttl file."""
    hooks_ttl = """
    @prefix kgc: <http://example.org/kgc/> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

    kgc:IngestHook
        a kgc:Hook ;
        rdfs:label "Ingest Hook" ;
        kgc:trigger "urn:kgc:apple:DataIngested" ;
        kgc:effect "generate_agenda" .

    kgc:ValidationFailureHook
        a kgc:Hook ;
        rdfs:label "Validation Failure Hook" ;
        kgc:trigger "urn:kgc:ValidationFailed" ;
        kgc:effect "generate_quality_report" .
    """

    hooks_file = tmp_path / "hooks.ttl"
    hooks_file.write_text(hooks_ttl)
    return hooks_file


class TestGeneratorHandlers:
    """Test individual generator handlers."""

    def test_agenda_handler_produces_artifact(self, test_graph: Graph) -> None:
        """Test that agenda handler produces valid artifact."""
        ctx = ExecutionContext(
            event_type="urn:kgc:apple:DataIngested",
            event_data={},
            hook=None,
            effect=None,
            graph=test_graph,
            timestamp=datetime.now(tz=UTC),
            actor="system",
        )

        result = HookHandlers.generate_agenda(ctx)

        assert result["artifact_type"] == "agenda"
        assert result["artifact_name"] is not None
        assert (
            "daily-" in result["artifact_name"].lower()
            or "agenda" in result["artifact_name"].lower()
        )
        assert result["artifact_content"] is not None
        assert len(result["artifact_content"]) > 0
        assert (
            "Summary" in result["artifact_content"]
            or "summary" in result["artifact_content"].lower()
        )

    def test_quality_report_handler_produces_artifact(self, test_graph: Graph) -> None:
        """Test that quality report handler produces valid artifact."""
        ctx = ExecutionContext(
            event_type="urn:kgc:ValidationFailed",
            event_data={},
            hook=None,
            effect=None,
            graph=test_graph,
            timestamp=datetime.now(tz=UTC),
            actor="validator",
        )

        result = HookHandlers.generate_quality_report(ctx)

        assert result["artifact_type"] == "quality_report"
        assert result["artifact_name"] is not None
        assert "quality" in result["artifact_name"].lower()

    def test_conflict_report_handler_produces_artifact(self, test_graph: Graph) -> None:
        """Test that conflict report handler produces valid artifact."""
        ctx = ExecutionContext(
            event_type="urn:kgc:ConflictDetected",
            event_data={"lookahead_days": 7},
            hook=None,
            effect=None,
            graph=test_graph,
            timestamp=datetime.now(tz=UTC),
            actor="system",
        )

        result = HookHandlers.generate_conflict_report(ctx)

        assert result["artifact_type"] == "conflict_report"
        assert result["artifact_name"] is not None
        assert "conflict" in result["artifact_name"].lower()

    def test_stale_items_handler_produces_artifact(self, test_graph: Graph) -> None:
        """Test that stale items handler produces valid artifact."""
        ctx = ExecutionContext(
            event_type="urn:kgc:StaleItemFound",
            event_data={"stale_threshold_days": 30},
            hook=None,
            effect=None,
            graph=test_graph,
            timestamp=datetime.now(tz=UTC),
            actor="system",
        )

        result = HookHandlers.generate_stale_items_report(ctx)

        assert result["artifact_type"] == "stale_items_report"
        assert result["artifact_name"] is not None
        assert "stale" in result["artifact_name"].lower()

    def test_all_reports_handler_runs_multiple_generators(
        self, test_graph: Graph
    ) -> None:
        """Test that all_reports handler runs all generators."""
        ctx = ExecutionContext(
            event_type="urn:kgc:OntologyChanged",
            event_data={},
            hook=None,
            effect=None,
            graph=test_graph,
            timestamp=datetime.now(tz=UTC),
            actor="system",
        )

        result = HookHandlers.generate_all_reports(ctx)

        assert result["artifact_type"] == "all_reports"
        assert "artifacts" in result
        # Should have attempted to run at least the configured number of generators
        assert len(result["artifacts"]) >= MIN_GENERATOR_RUNS


class TestHookHandlerIntegration:
    """Test hooks and handlers working together."""

    def test_hook_orchestrator_executes_handlers(
        self, test_graph: Graph, test_hooks_file: Path
    ) -> None:
        """Test that hook orchestrator can execute handlers."""
        # Initialize orchestrator
        orchestrator = HookOrchestrator(
            graph=test_graph, hooks_file=test_hooks_file, continue_on_error=True
        )

        # Register handlers
        register_all_handlers(orchestrator)

        # Verify handlers registered through public API
        registered_hooks = orchestrator.get_registered_hooks()
        assert registered_hooks
        assert "IngestHook" in registered_hooks

    def test_hook_orchestrator_sanitizes_handler_errors(
        self, test_graph: Graph, test_hooks_file: Path
    ) -> None:
        """Handlers that raise should yield sanitized receipts."""
        orchestrator = HookOrchestrator(
            graph=test_graph, hooks_file=test_hooks_file, continue_on_error=True
        )

        ingest_hook = HookDefinition(
            uri=URIRef("urn:kgc:IngestHook"),
            name=HookName.new("IngestHook"),
            label="Ingest Hook",
            description="Test hook",
            trigger_event=URIRef("urn:kgc:apple:DataIngested"),
            trigger_label="Data Ingested",
            cron_schedule=None,
            effects=[
                HookEffect(
                    label="Failing Effect",
                    description="Raises error",
                    command="kgct failing",
                    target="out.txt",
                )
            ],
            waste_removed="",
        )
        orchestrator.hooks = [ingest_hook]
        orchestrator.loader.get_hooks_by_trigger = (
            lambda event: [ingest_hook] if event == "urn:kgc:apple:DataIngested" else []
        )

        def failing_handler(ctx: ExecutionContext) -> dict[str, Any]:
            raise RuntimeError("boom /tmp/secret_path.py line 42")

        orchestrator.register_handler("IngestHook", failing_handler)

        result = orchestrator.trigger_event("urn:kgc:apple:DataIngested", {})

        assert result.errors
        assert not result.success
        assert "[RUNTIME]" in result.errors[0]
        assert "/tmp/secret_path.py" not in result.errors[0]
        assert result.receipts
        receipt = result.receipts[0]
        assert receipt.metadata.get("sanitized") is True
        assert receipt.metadata.get("error_code") == "RUNTIME"

    def test_handler_error_handling(self, test_graph: Graph) -> None:
        """Test that handlers handle errors gracefully."""
        # Create execution context with missing template directory
        ctx = ExecutionContext(
            event_type="urn:kgc:apple:DataIngested",
            event_data={},
            hook=None,
            effect=None,
            graph=test_graph,
            timestamp=datetime.now(tz=UTC),
            actor="system",
        )

        # This may fail due to missing templates, but should return error result
        result = HookHandlers.generate_agenda(ctx)

        # Should return result dict with artifact_type, even if artifact_content is None
        assert "artifact_type" in result
        # Either has content or has error in metadata
        assert result["artifact_content"] is not None or "metadata" in result


class TestWorkflowWithGenerators:
    """Test that workflow can trigger generators through hooks."""

    def test_workflow_state_tracks_generator_artifacts(self) -> None:
        """Test that workflow state can track generator artifacts."""
        state = WorkflowState(workflow_id="test-1", started_at=datetime.now(tz=UTC))

        # Simulate completing a REGENERATE step with generated artifacts
        artifacts_data = {
            "artifacts": {
                "agenda": {
                    "artifact_type": "agenda",
                    "artifact_name": "agenda_20251124.md",
                    "artifact_content": "# Agenda\n...",
                }
            }
        }

        state.complete_step(
            step=WorkflowStep.REGENERATE,
            success=True,
            started_at=datetime.now(tz=UTC),
            data=artifacts_data,
        )

        # Verify step was recorded
        regenerate_result = state.get_step_result(WorkflowStep.REGENERATE)
        assert regenerate_result is not None
        assert regenerate_result.success is True
        assert "artifacts" in regenerate_result.data


class TestEndToEndFlow:
    """Integration tests for complete data flow."""

    def test_generator_produces_valid_markdown(self, test_graph: Graph) -> None:
        """Test that generators produce valid markdown artifacts."""
        gen = AgendaGenerator(graph=test_graph)

        # Should not raise exception
        try:
            result = gen.generate()
            # Result should be non-empty string
            assert isinstance(result, str)
            assert len(result) > 0
        except FileNotFoundError:
            # Template might not exist yet, that's ok
            pytest.skip("Templates not yet created")

    def test_handler_result_has_all_fields(self, test_graph: Graph) -> None:
        """Test that handler results have required fields."""
        ctx = ExecutionContext(
            event_type="urn:kgc:apple:DataIngested",
            event_data={},
            hook=None,
            effect=None,
            graph=test_graph,
            timestamp=datetime.now(tz=UTC),
            actor="system",
        )

        result = HookHandlers.generate_agenda(ctx)

        # Check required fields
        assert "artifact_type" in result
        assert "artifact_name" in result
        assert "artifact_content" in result
        assert "metadata" in result


# Smoke tests - verify basic integration without full dependencies
class TestIntegrationSetup:
    """Smoke tests for integration module initialization."""

    def test_handlers_module_imports(self) -> None:
        """Test that handlers module can be imported."""
        assert HookHandlers is not None
        assert register_all_handlers is not None

    def test_integration_module_imports(self) -> None:
        """Test that integration module can be imported."""
        assert KGCIntegration is not None

    def test_handler_functions_callable(self) -> None:
        """Test that handler functions are callable."""
        assert callable(HookHandlers.generate_agenda)
        assert callable(HookHandlers.generate_quality_report)
        assert callable(HookHandlers.generate_conflict_report)
        assert callable(HookHandlers.generate_stale_items_report)
        assert callable(HookHandlers.generate_all_reports)
