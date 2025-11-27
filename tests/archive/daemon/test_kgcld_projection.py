"""Tests for KGCL Daemon projection integration - Chicago School TDD.

Tests verify behavior of daemon projection rendering:
- render_projection() delegates to ProjectionEngine
- Template registry resolves from .kgc/projections
- Projections reflect current graph state
- Parameters are merged into template context
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kgcl.daemon.kgcld import DaemonConfig, KGCLDaemon
from kgcl.projection.domain.descriptors import OntologyConfig, TemplateDescriptor, TemplateMetadata
from kgcl.projection.domain.result import ProjectionResult
from kgcl.projection.ports.template_registry import InMemoryTemplateRegistry

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def running_daemon(tmp_path: Path) -> KGCLDaemon:
    """Create and start a daemon with some test data."""
    config = DaemonConfig(tick_interval=0.1, snapshot_interval=10)
    daemon = KGCLDaemon(config=config)
    await daemon.start()

    # Add some test data
    await daemon.add("urn:entity:User", "urn:rdfs:label", "User")
    await daemon.add("urn:entity:User", "urn:type", "Entity")
    await daemon.add("urn:entity:Product", "urn:rdfs:label", "Product")
    await daemon.add("urn:entity:Product", "urn:type", "Entity")

    yield daemon
    await daemon.stop()


@pytest.fixture
def simple_template() -> TemplateDescriptor:
    """Create a simple template descriptor for testing."""
    return TemplateDescriptor(
        id="simple",
        engine="jinja2",
        language="txt",
        framework="",
        version="1.0.0",
        ontology=OntologyConfig(graph_id="main"),
        queries=(),
        n3_rules=(),
        metadata=TemplateMetadata(author="Test", description="Simple test template", tags=("test",)),
        template_path="simple.j2",
        raw_content="Hello {% if params.name %}{{ params.name }}{% else %}World{% endif %}!",
    )


# =============================================================================
# Daemon Projection Tests
# =============================================================================


class TestDaemonProjection:
    """Tests for daemon projection integration."""

    @pytest.mark.asyncio
    async def test_render_projection_basic(
        self, running_daemon: KGCLDaemon, simple_template: TemplateDescriptor
    ) -> None:
        """Can render basic projection template."""
        # Override registry with test template
        registry = InMemoryTemplateRegistry()
        registry.add(simple_template)
        running_daemon._projection_registry = registry

        result = await running_daemon.render_projection("simple.j2")

        assert isinstance(result, ProjectionResult)
        assert result.template_id == "simple"
        assert result.content == "Hello World!"

    @pytest.mark.asyncio
    async def test_render_projection_with_params(
        self, running_daemon: KGCLDaemon, simple_template: TemplateDescriptor
    ) -> None:
        """Can render projection with parameters."""
        registry = InMemoryTemplateRegistry()
        registry.add(simple_template)
        running_daemon._projection_registry = registry

        result = await running_daemon.render_projection("simple.j2", {"name": "KGCL"})

        assert result.content == "Hello KGCL!"

    @pytest.mark.asyncio
    async def test_render_projection_uses_current_state(self, running_daemon: KGCLDaemon) -> None:
        """Projection reflects current graph state."""
        from kgcl.projection.domain.descriptors import QueryDescriptor, QuerySource

        # Create template that queries current state
        template = TemplateDescriptor(
            id="state_query",
            engine="jinja2",
            language="txt",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(
                QueryDescriptor(
                    name="entities",
                    purpose="Get entity labels",
                    source=QuerySource.INLINE,
                    content="""
                    SELECT ?label WHERE {
                        GRAPH <urn:kgcl:state> {
                            ?e <urn:rdfs:label> ?label
                        }
                    }
                    """,
                ),
            ),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="state_query.j2",
            raw_content="Entities: {% for e in sparql.entities %}{{ e.label }}{% if not loop.last %}, {% endif %}{% endfor %}",
        )

        registry = InMemoryTemplateRegistry()
        registry.add(template)
        running_daemon._projection_registry = registry

        result = await running_daemon.render_projection("state_query.j2")

        # Should include both User and Product from fixture
        assert "User" in result.content
        assert "Product" in result.content

    @pytest.mark.asyncio
    async def test_render_projection_result_has_metadata(
        self, running_daemon: KGCLDaemon, simple_template: TemplateDescriptor
    ) -> None:
        """Projection result includes timing and query metadata."""
        registry = InMemoryTemplateRegistry()
        registry.add(simple_template)
        running_daemon._projection_registry = registry

        result = await running_daemon.render_projection("simple.j2")

        assert result.version == "1.0.0"
        # txt is not in the media type mapping, so it's None
        assert result.media_type is None
        assert result.render_time_ms >= 0
        assert result.query_count == 0  # No queries in simple template

    @pytest.mark.asyncio
    async def test_render_projection_with_query_increments_count(self, running_daemon: KGCLDaemon) -> None:
        """Projection with SPARQL queries reports query_count."""
        from kgcl.projection.domain.descriptors import QueryDescriptor, QuerySource

        template = TemplateDescriptor(
            id="query_template",
            engine="jinja2",
            language="txt",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(
                QueryDescriptor(
                    name="test_query",
                    purpose="Get all triples",
                    source=QuerySource.INLINE,
                    content="SELECT ?s WHERE { GRAPH <urn:kgcl:state> { ?s ?p ?o } }",
                ),
            ),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="query.j2",
            raw_content="Results: {{ sparql.test_query | length }}",
        )

        registry = InMemoryTemplateRegistry()
        registry.add(template)
        running_daemon._projection_registry = registry

        result = await running_daemon.render_projection("query.j2")

        assert result.query_count == 1

    @pytest.mark.asyncio
    async def test_render_projection_not_running_raises(self) -> None:
        """Cannot render projection when daemon not running."""
        daemon = KGCLDaemon(DaemonConfig())

        with pytest.raises(RuntimeError, match="Cannot render in state"):
            await daemon.render_projection("test.j2")

    @pytest.mark.asyncio
    async def test_get_projection_registry_filesystem(self, tmp_path: Path) -> None:
        """_get_projection_registry creates FilesystemTemplateRegistry if .kgc/projections exists."""
        # Create .kgc/projections directory
        projections_dir = tmp_path / ".kgc" / "projections"
        projections_dir.mkdir(parents=True)

        # Change to tmp_path so daemon finds .kgc/projections
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            daemon = KGCLDaemon(DaemonConfig())
            registry = daemon._get_projection_registry()

            # Should be FilesystemTemplateRegistry
            from kgcl.projection.adapters.filesystem_registry import FilesystemTemplateRegistry

            assert isinstance(registry, FilesystemTemplateRegistry)
        finally:
            os.chdir(old_cwd)

    @pytest.mark.asyncio
    async def test_get_projection_registry_in_memory_fallback(self, tmp_path: Path) -> None:
        """_get_projection_registry creates InMemoryTemplateRegistry if .kgc/projections missing."""
        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)  # Directory without .kgc/projections

            daemon = KGCLDaemon(DaemonConfig())
            registry = daemon._get_projection_registry()

            # Should be InMemoryTemplateRegistry
            from kgcl.projection.ports.template_registry import InMemoryTemplateRegistry

            assert isinstance(registry, InMemoryTemplateRegistry)
        finally:
            os.chdir(old_cwd)

    @pytest.mark.asyncio
    async def test_render_projection_caches_engine(
        self, running_daemon: KGCLDaemon, simple_template: TemplateDescriptor
    ) -> None:
        """Projection engine is created once and reused."""
        registry = InMemoryTemplateRegistry()
        registry.add(simple_template)
        running_daemon._projection_registry = registry

        # First render
        await running_daemon.render_projection("simple.j2")
        engine1 = running_daemon._projection_engine

        # Second render
        await running_daemon.render_projection("simple.j2")
        engine2 = running_daemon._projection_engine

        # Should be same instance
        assert engine1 is engine2

    @pytest.mark.asyncio
    async def test_render_projection_state_changes_reflected(self, running_daemon: KGCLDaemon) -> None:
        """Projection reflects graph state changes."""
        from kgcl.projection.domain.descriptors import QueryDescriptor, QuerySource

        template = TemplateDescriptor(
            id="count_template",
            engine="jinja2",
            language="txt",
            framework="",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(
                QueryDescriptor(
                    name="count",
                    purpose="Count triples",
                    source=QuerySource.INLINE,
                    content="SELECT (COUNT(?s) AS ?count) WHERE { GRAPH <urn:kgcl:state> { ?s ?p ?o } }",
                ),
            ),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="count.j2",
            raw_content="Triple count: {{ sparql.count[0].count }}",
        )

        registry = InMemoryTemplateRegistry()
        registry.add(template)
        running_daemon._projection_registry = registry

        # Render before adding more triples
        result1 = await running_daemon.render_projection("count.j2")
        count1 = int(result1.content.split(": ")[1])

        # Add more triples
        await running_daemon.add("urn:new:entity", "urn:new:prop", "value")

        # Render again
        result2 = await running_daemon.render_projection("count.j2")
        count2 = int(result2.content.split(": ")[1])

        # Count should have increased
        assert count2 > count1
