"""Tests for hook loader - parsing hooks.ttl into Hook domain objects.

Chicago TDD Pattern - London School:
    - Test parsing RDF hook definitions
    - Test extracting triggers and effects
    - Test error handling for malformed hooks
    - Mock RDF graph interactions
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS

from kgcl.hooks.loader import HookLoader, HookDefinition, HookEffect


# Define namespaces (same as loader)
KGC = Namespace("urn:kgc:")
APPLE = Namespace("urn:kgc:apple:")


class TestHookLoader:
    """Test suite for HookLoader class."""

    @pytest.fixture
    def sample_hooks_ttl(self, tmp_path: Path) -> Path:
        """Create a sample hooks.ttl file for testing."""
        hooks_file = tmp_path / "hooks.ttl"

        hooks_content = """
@prefix kgc: <urn:kgc:> .
@prefix apple: <urn:kgc:apple:> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

apple:IngestHook a kgc:Hook ;
    rdfs:label "Apple Data Ingest Hook" ;
    rdfs:comment "Regenerate projections when data ingested" ;
    kgc:triggeredBy apple:DataIngested ;
    kgc:effect [
        rdfs:label "Regenerate Daily Agenda" ;
        rdfs:comment "Update docs/agenda.md" ;
        kgc:command "kgct generate-agenda --day today" ;
        kgc:target "docs/agenda.md"
    ] ;
    kgc:wasteRemoved "Manual copy/paste" .

apple:DataIngested a kgc:HookEvent ;
    rdfs:label "Data Ingested" ;
    rdfs:comment "Apple data imported" .
"""
        hooks_file.write_text(hooks_content)
        return hooks_file

    @pytest.fixture
    def loader(self, sample_hooks_ttl: Path) -> HookLoader:
        """Create HookLoader instance with sample hooks."""
        return HookLoader(sample_hooks_ttl)

    def test_loader_initialization(self, sample_hooks_ttl: Path) -> None:
        """Test loader initializes and parses RDF graph."""
        loader = HookLoader(sample_hooks_ttl)

        assert loader.hooks_file == sample_hooks_ttl
        assert isinstance(loader.graph, Graph)
        assert len(loader.graph) > 0  # Should have triples

    def test_loader_missing_file_raises_error(self) -> None:
        """Test loader raises error for missing hooks file."""
        with pytest.raises(FileNotFoundError, match="Hooks file not found"):
            HookLoader(Path("/nonexistent/hooks.ttl"))

    def test_load_hooks_returns_hook_definitions(self, loader: HookLoader) -> None:
        """Test load_hooks returns parsed HookDefinition objects."""
        hooks = loader.load_hooks()

        assert len(hooks) > 0
        assert all(isinstance(h, HookDefinition) for h in hooks)

    def test_parse_hook_extracts_metadata(self, loader: HookLoader) -> None:
        """Test hook parsing extracts name, label, description."""
        hooks = loader.load_hooks()
        ingest_hook = next(h for h in hooks if h.name == "IngestHook")

        assert ingest_hook.label == "Apple Data Ingest Hook"
        assert "projections" in ingest_hook.description
        assert ingest_hook.waste_removed == "Manual copy/paste"

    def test_parse_hook_extracts_trigger_event(self, loader: HookLoader) -> None:
        """Test hook parsing extracts trigger event URI."""
        hooks = loader.load_hooks()
        ingest_hook = next(h for h in hooks if h.name == "IngestHook")

        assert ingest_hook.trigger_event is not None
        assert str(ingest_hook.trigger_event) == "urn:kgc:apple:DataIngested"
        assert ingest_hook.trigger_label == "Data Ingested"

    def test_parse_hook_extracts_effects(self, loader: HookLoader) -> None:
        """Test hook parsing extracts all effects."""
        hooks = loader.load_hooks()
        ingest_hook = next(h for h in hooks if h.name == "IngestHook")

        assert len(ingest_hook.effects) > 0

        effect = ingest_hook.effects[0]
        assert effect.label == "Regenerate Daily Agenda"
        assert effect.command == "kgct generate-agenda --day today"
        assert effect.target == "docs/agenda.md"

    def test_map_command_to_generator(self, loader: HookLoader) -> None:
        """Test command mapping to generator class."""
        hooks = loader.load_hooks()
        ingest_hook = next(h for h in hooks if h.name == "IngestHook")

        effect = ingest_hook.effects[0]
        assert effect.generator == "AgendaGenerator"

    def test_get_hook_by_name(self, loader: HookLoader) -> None:
        """Test retrieving hook by name."""
        hook = loader.get_hook_by_name("IngestHook")

        assert hook is not None
        assert hook.name == "IngestHook"

    def test_get_hook_by_name_returns_none_for_missing(
        self,
        loader: HookLoader
    ) -> None:
        """Test get_hook_by_name returns None for missing hooks."""
        hook = loader.get_hook_by_name("NonexistentHook")

        assert hook is None

    def test_get_hooks_by_trigger(self, loader: HookLoader) -> None:
        """Test retrieving hooks by trigger event."""
        hooks = loader.get_hooks_by_trigger("urn:kgc:apple:DataIngested")

        assert len(hooks) > 0
        assert all(str(h.trigger_event) == "urn:kgc:apple:DataIngested" for h in hooks)

    def test_empty_graph_returns_no_hooks(self, tmp_path: Path) -> None:
        """Test loading from empty RDF file returns no hooks."""
        empty_file = tmp_path / "empty.ttl"
        empty_file.write_text("@prefix kgc: <urn:kgc:> .")

        loader = HookLoader(empty_file)
        hooks = loader.load_hooks()

        assert hooks == []

    def test_hook_validation_requires_trigger(self, tmp_path: Path) -> None:
        """Test hook validation enforces trigger requirement.

        Loader gracefully handles invalid hooks by logging error and continuing.
        Invalid hooks are not returned in the list.
        """
        invalid_file = tmp_path / "invalid.ttl"
        invalid_content = """
@prefix kgc: <urn:kgc:> .
@prefix apple: <urn:kgc:apple:> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

apple:BadHook a kgc:Hook ;
    rdfs:label "Bad Hook" ;
    rdfs:comment "No trigger" ;
    kgc:effect [
        rdfs:label "Some Effect" ;
        kgc:command "kgct something" ;
        kgc:target "output.txt"
    ] .
"""
        invalid_file.write_text(invalid_content)

        loader = HookLoader(invalid_file)
        hooks = loader.load_hooks()

        # Loader continues on error, returns empty list
        assert hooks == []

    def test_get_timed_hooks(self, tmp_path: Path) -> None:
        """Test retrieving hooks with cron schedules."""
        timed_file = tmp_path / "timed.ttl"
        timed_content = """
@prefix kgc: <urn:kgc:> .
@prefix apple: <urn:kgc:apple:> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

apple:DailyHook a kgc:Hook ;
    rdfs:label "Daily Hook" ;
    rdfs:comment "Runs daily" ;
    kgc:triggeredBy [
        rdfs:label "Morning Trigger" ;
        rdfs:comment "6:00 AM local time" ;
        kgc:cronSchedule "0 6 * * *"
    ] ;
    kgc:effect [
        rdfs:label "Daily Effect" ;
        rdfs:comment "Generate daily report" ;
        kgc:command "kgct daily-task" ;
        kgc:target "output.txt"
    ] .
"""
        timed_file.write_text(timed_content)

        loader = HookLoader(timed_file)
        timed_hooks = loader.get_timed_hooks()

        assert len(timed_hooks) > 0
        daily_hook = timed_hooks[0]
        assert daily_hook.cron_schedule == "0 6 * * *"
        assert daily_hook.trigger_event is None  # Timed hooks don't have event triggers


class TestHookDefinition:
    """Test suite for HookDefinition dataclass."""

    def test_hook_definition_requires_trigger_or_cron(self) -> None:
        """Test HookDefinition validates trigger/cron requirement."""
        with pytest.raises(ValueError, match="trigger_event or cron_schedule"):
            HookDefinition(
                uri=URIRef("urn:test:hook"),
                name="TestHook",
                label="Test",
                description="Test hook",
                trigger_event=None,
                trigger_label=None,
                cron_schedule=None,
                effects=[]
            )

    def test_hook_definition_requires_effects(self) -> None:
        """Test HookDefinition validates effects requirement."""
        with pytest.raises(ValueError, match="at least one effect"):
            HookDefinition(
                uri=URIRef("urn:test:hook"),
                name="TestHook",
                label="Test",
                description="Test hook",
                trigger_event=URIRef("urn:test:event"),
                trigger_label="Event",
                cron_schedule=None,
                effects=[]  # No effects
            )

    def test_hook_definition_valid_with_event_trigger(self) -> None:
        """Test HookDefinition accepts event trigger."""
        effect = HookEffect(
            label="Test Effect",
            description="Test",
            command="test-cmd",
            target="output.txt"
        )

        hook = HookDefinition(
            uri=URIRef("urn:test:hook"),
            name="TestHook",
            label="Test",
            description="Test hook",
            trigger_event=URIRef("urn:test:event"),
            trigger_label="Event",
            cron_schedule=None,
            effects=[effect]
        )

        assert hook.trigger_event is not None
        assert hook.cron_schedule is None

    def test_hook_definition_valid_with_cron_trigger(self) -> None:
        """Test HookDefinition accepts cron trigger."""
        effect = HookEffect(
            label="Test Effect",
            description="Test",
            command="test-cmd",
            target="output.txt"
        )

        hook = HookDefinition(
            uri=URIRef("urn:test:hook"),
            name="TestHook",
            label="Test",
            description="Test hook",
            trigger_event=None,
            trigger_label=None,
            cron_schedule="0 6 * * *",
            effects=[effect]
        )

        assert hook.trigger_event is None
        assert hook.cron_schedule == "0 6 * * *"


class TestHookEffect:
    """Test suite for HookEffect dataclass."""

    def test_hook_effect_creation(self) -> None:
        """Test creating HookEffect instance."""
        effect = HookEffect(
            label="Test Effect",
            description="Test description",
            command="kgct test",
            target="output.txt",
            generator="TestGenerator"
        )

        assert effect.label == "Test Effect"
        assert effect.command == "kgct test"
        assert effect.generator == "TestGenerator"
