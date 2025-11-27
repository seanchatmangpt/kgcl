"""Tests for BundleRenderer - Multi-file projection.

Chicago School TDD: No mocking domain objects, verify actual behavior.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from kgcl.projection.domain.bundle import BundleDescriptor, BundleTemplateEntry, ConflictMode, IterationSpec
from kgcl.projection.domain.exceptions import ResourceLimitExceeded
from kgcl.projection.domain.descriptors import (
    OntologyConfig,
    QueryDescriptor,
    QuerySource,
    TemplateDescriptor,
    TemplateMetadata,
)
from kgcl.projection.engine.bundle_renderer import BundleRenderer
from kgcl.projection.engine.projection_engine import ProjectionEngine
from kgcl.projection.ports.template_registry import InMemoryTemplateRegistry


class MockGraphClient:
    """Mock graph client for testing."""

    def __init__(self, gid: str, query_results: dict[str, list[dict[str, Any]]]) -> None:
        """Initialize mock client."""
        self._id = gid
        self._query_results = query_results

    @property
    def graph_id(self) -> str:
        """Get graph ID."""
        return self._id

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Execute query."""
        return self._query_results.get(sparql, [])

    def ask(self, sparql: str) -> bool:
        """Execute ASK."""
        return False

    def construct(self, sparql: str) -> str:
        """Execute CONSTRUCT."""
        return ""


def test_bundle_renderer_single_file() -> None:
    """BundleRenderer renders single-file bundle."""
    # Arrange
    desc = TemplateDescriptor(
        id="test",
        engine="jinja2",
        language="python",
        framework="",
        version="1.0",
        ontology=OntologyConfig("main"),
        queries=(),
        n3_rules=(),
        metadata=TemplateMetadata(),
        template_path="test.j2",
        raw_content="# {{ params.title }}",
    )

    registry = InMemoryTemplateRegistry()
    registry.add(desc)

    graphs = {"main": MockGraphClient("main", {})}
    engine = ProjectionEngine(registry, graphs)
    renderer = BundleRenderer(engine)

    entry = BundleTemplateEntry("test.j2", "output.py")
    bundle = BundleDescriptor("test-bundle", (entry,))

    # Act
    result = renderer.render_bundle(bundle, {"title": "Test"}, dry_run=True)

    # Assert
    assert result.file_count == 1
    assert result.bundle_id == "test-bundle"
    assert result.dry_run is True
    assert result.files[0].output_path == "output.py"
    assert "# Test" in result.files[0].result.content


def test_bundle_renderer_multiple_files() -> None:
    """BundleRenderer renders multiple files."""
    # Arrange
    desc1 = TemplateDescriptor(
        id="t1",
        engine="jinja2",
        language="python",
        framework="",
        version="1.0",
        ontology=OntologyConfig("main"),
        queries=(),
        n3_rules=(),
        metadata=TemplateMetadata(),
        template_path="t1.j2",
        raw_content="# File 1",
    )
    desc2 = TemplateDescriptor(
        id="t2",
        engine="jinja2",
        language="python",
        framework="",
        version="1.0",
        ontology=OntologyConfig("main"),
        queries=(),
        n3_rules=(),
        metadata=TemplateMetadata(),
        template_path="t2.j2",
        raw_content="# File 2",
    )

    registry = InMemoryTemplateRegistry()
    registry.add(desc1)
    registry.add(desc2)

    graphs = {"main": MockGraphClient("main", {})}
    engine = ProjectionEngine(registry, graphs)
    renderer = BundleRenderer(engine)

    entry1 = BundleTemplateEntry("t1.j2", "a.py")
    entry2 = BundleTemplateEntry("t2.j2", "b.py")
    bundle = BundleDescriptor("multi", (entry1, entry2))

    # Act
    result = renderer.render_bundle(bundle, dry_run=True)

    # Assert
    assert result.file_count == 2
    assert result.output_paths == ("a.py", "b.py")


def test_bundle_renderer_dynamic_output_path() -> None:
    """BundleRenderer resolves dynamic output paths."""
    # Arrange
    desc = TemplateDescriptor(
        id="test",
        engine="jinja2",
        language="python",
        framework="",
        version="1.0",
        ontology=OntologyConfig("main"),
        queries=(),
        n3_rules=(),
        metadata=TemplateMetadata(),
        template_path="test.j2",
        raw_content="content",
    )

    registry = InMemoryTemplateRegistry()
    registry.add(desc)

    graphs = {"main": MockGraphClient("main", {})}
    engine = ProjectionEngine(registry, graphs)
    renderer = BundleRenderer(engine)

    entry = BundleTemplateEntry("test.j2", "{{ params.module }}/{{ params.name }}.py")
    bundle = BundleDescriptor("dynamic", (entry,))

    # Act
    result = renderer.render_bundle(bundle, {"module": "services", "name": "user"}, dry_run=True)

    # Assert
    assert result.files[0].output_path == "services/user.py"


def test_bundle_renderer_iteration() -> None:
    """BundleRenderer iterates over query results."""
    # Arrange
    query = QueryDescriptor(
        name="entities",
        purpose="",
        source=QuerySource.INLINE,
        content="SELECT ?slug ?name WHERE { ?s ex:slug ?slug ; ex:name ?name }",
    )
    desc = TemplateDescriptor(
        id="test",
        engine="jinja2",
        language="python",
        framework="",
        version="1.0",
        ontology=OntologyConfig("main"),
        queries=(query,),
        n3_rules=(),
        metadata=TemplateMetadata(),
        template_path="test.j2",
        raw_content="# {{ params.entity.name }}",
    )

    registry = InMemoryTemplateRegistry()
    registry.add(desc)

    query_results = {
        "SELECT ?slug ?name WHERE { ?s ex:slug ?slug ; ex:name ?name }": [
            {"slug": "user", "name": "User"},
            {"slug": "post", "name": "Post"},
        ]
    }
    graphs = {"main": MockGraphClient("main", query_results)}
    engine = ProjectionEngine(registry, graphs)
    renderer = BundleRenderer(engine)

    iter_spec = IterationSpec(query="SELECT ?slug ?name WHERE { ?s ex:slug ?slug ; ex:name ?name }", as_var="entity")
    entry = BundleTemplateEntry("test.j2", "{{ params.entity.slug }}_service.py", iterate=iter_spec)
    bundle = BundleDescriptor("iterated", (entry,))

    # Act
    result = renderer.render_bundle(bundle, dry_run=True)

    # Assert
    assert result.file_count == 2
    assert "user_service.py" in result.output_paths
    assert "post_service.py" in result.output_paths

    # Check content
    user_file = result.get_file("user_service.py")
    assert user_file is not None
    assert "# User" in user_file.result.content

    post_file = result.get_file("post_service.py")
    assert post_file is not None
    assert "# Post" in post_file.result.content


def test_bundle_renderer_conflict_error() -> None:
    """BundleRenderer detects output path conflicts."""
    # Arrange
    desc = TemplateDescriptor(
        id="test",
        engine="jinja2",
        language="python",
        framework="",
        version="1.0",
        ontology=OntologyConfig("main"),
        queries=(),
        n3_rules=(),
        metadata=TemplateMetadata(),
        template_path="test.j2",
        raw_content="content",
    )

    registry = InMemoryTemplateRegistry()
    registry.add(desc)

    graphs = {"main": MockGraphClient("main", {})}
    engine = ProjectionEngine(registry, graphs)
    renderer = BundleRenderer(engine)

    # Both entries write to same path
    entry1 = BundleTemplateEntry("test.j2", "same.py")
    entry2 = BundleTemplateEntry("test.j2", "same.py")
    bundle = BundleDescriptor("conflict", (entry1, entry2))

    # Act & Assert
    with pytest.raises(ValueError, match="Output path conflict"):
        renderer.render_bundle(bundle, dry_run=True, conflict_mode=ConflictMode.ERROR)


def test_bundle_renderer_write_files() -> None:
    """BundleRenderer writes files to disk."""
    # Arrange
    desc = TemplateDescriptor(
        id="test",
        engine="jinja2",
        language="python",
        framework="",
        version="1.0",
        ontology=OntologyConfig("main"),
        queries=(),
        n3_rules=(),
        metadata=TemplateMetadata(),
        template_path="test.j2",
        raw_content="# Generated",
    )

    registry = InMemoryTemplateRegistry()
    registry.add(desc)

    graphs = {"main": MockGraphClient("main", {})}
    engine = ProjectionEngine(registry, graphs)
    renderer = BundleRenderer(engine)

    entry = BundleTemplateEntry("test.j2", "output.py")
    bundle = BundleDescriptor("write-test", (entry,))

    # Act
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        result = renderer.render_bundle(bundle, output_dir=output_dir, dry_run=False)

        # Assert
        assert result.dry_run is False
        output_file = output_dir / "output.py"
        assert output_file.exists()
        assert "# Generated" in output_file.read_text()


def test_bundle_renderer_conflict_overwrite() -> None:
    """BundleRenderer overwrites existing files."""
    # Arrange
    desc = TemplateDescriptor(
        id="test",
        engine="jinja2",
        language="python",
        framework="",
        version="1.0",
        ontology=OntologyConfig("main"),
        queries=(),
        n3_rules=(),
        metadata=TemplateMetadata(),
        template_path="test.j2",
        raw_content="# New content",
    )

    registry = InMemoryTemplateRegistry()
    registry.add(desc)

    graphs = {"main": MockGraphClient("main", {})}
    engine = ProjectionEngine(registry, graphs)
    renderer = BundleRenderer(engine)

    entry = BundleTemplateEntry("test.j2", "output.py")
    bundle = BundleDescriptor("overwrite-test", (entry,))

    # Act
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        output_file = output_dir / "output.py"

        # Write initial content
        output_file.write_text("# Old content")

        # Render with overwrite
        renderer.render_bundle(bundle, output_dir=output_dir, conflict_mode=ConflictMode.OVERWRITE, dry_run=False)

        # Assert
        assert "# New content" in output_file.read_text()


def test_bundle_renderer_conflict_skip() -> None:
    """BundleRenderer skips existing files."""
    # Arrange
    desc = TemplateDescriptor(
        id="test",
        engine="jinja2",
        language="python",
        framework="",
        version="1.0",
        ontology=OntologyConfig("main"),
        queries=(),
        n3_rules=(),
        metadata=TemplateMetadata(),
        template_path="test.j2",
        raw_content="# New content",
    )

    registry = InMemoryTemplateRegistry()
    registry.add(desc)

    graphs = {"main": MockGraphClient("main", {})}
    engine = ProjectionEngine(registry, graphs)
    renderer = BundleRenderer(engine)

    entry = BundleTemplateEntry("test.j2", "output.py")
    bundle = BundleDescriptor("skip-test", (entry,))

    # Act
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        output_file = output_dir / "output.py"

        # Write initial content
        output_file.write_text("# Old content")

        # Render with skip
        renderer.render_bundle(bundle, output_dir=output_dir, conflict_mode=ConflictMode.SKIP, dry_run=False)

        # Assert - file unchanged
        assert "# Old content" in output_file.read_text()
        assert "# New" not in output_file.read_text()


# =============================================================================
# Resource Limit Tests
# =============================================================================


def test_bundle_renderer_iteration_limit_exceeded() -> None:
    """BundleRenderer raises ResourceLimitExceeded when iteration exceeds max."""
    # Arrange
    query = QueryDescriptor(
        name="entities",
        purpose="",
        source=QuerySource.INLINE,
        content="SELECT ?slug WHERE { ?s ex:slug ?slug }",
    )
    desc = TemplateDescriptor(
        id="test",
        engine="jinja2",
        language="python",
        framework="",
        version="1.0",
        ontology=OntologyConfig("main"),
        queries=(query,),
        n3_rules=(),
        metadata=TemplateMetadata(),
        template_path="test.j2",
        raw_content="# {{ params.entity.slug }}",
    )

    registry = InMemoryTemplateRegistry()
    registry.add(desc)

    # Return 100 results
    query_results = {
        "SELECT ?slug WHERE { ?s ex:slug ?slug }": [{"slug": f"entity_{i}"} for i in range(100)]
    }
    graphs = {"main": MockGraphClient("main", query_results)}
    engine = ProjectionEngine(registry, graphs)
    renderer = BundleRenderer(engine, max_iteration=10)  # Limit to 10

    iter_spec = IterationSpec(query="SELECT ?slug WHERE { ?s ex:slug ?slug }", as_var="entity")
    entry = BundleTemplateEntry("test.j2", "{{ params.entity.slug }}.py", iterate=iter_spec)
    bundle = BundleDescriptor("iterated", (entry,))

    # Act & Assert
    with pytest.raises(ResourceLimitExceeded) as exc:
        renderer.render_bundle(bundle, dry_run=True)

    assert exc.value.limit == 10
    assert exc.value.actual == 100
    assert "iterations" in exc.value.resource


def test_bundle_renderer_iteration_limit_allows_under() -> None:
    """BundleRenderer allows iterations under the limit."""
    # Arrange
    query = QueryDescriptor(
        name="entities",
        purpose="",
        source=QuerySource.INLINE,
        content="SELECT ?slug WHERE { ?s ex:slug ?slug }",
    )
    desc = TemplateDescriptor(
        id="test",
        engine="jinja2",
        language="python",
        framework="",
        version="1.0",
        ontology=OntologyConfig("main"),
        queries=(query,),
        n3_rules=(),
        metadata=TemplateMetadata(),
        template_path="test.j2",
        raw_content="# {{ params.entity.slug }}",
    )

    registry = InMemoryTemplateRegistry()
    registry.add(desc)

    # Return 5 results (under limit of 10)
    query_results = {
        "SELECT ?slug WHERE { ?s ex:slug ?slug }": [{"slug": f"entity_{i}"} for i in range(5)]
    }
    graphs = {"main": MockGraphClient("main", query_results)}
    engine = ProjectionEngine(registry, graphs)
    renderer = BundleRenderer(engine, max_iteration=10)

    iter_spec = IterationSpec(query="SELECT ?slug WHERE { ?s ex:slug ?slug }", as_var="entity")
    entry = BundleTemplateEntry("test.j2", "{{ params.entity.slug }}.py", iterate=iter_spec)
    bundle = BundleDescriptor("iterated", (entry,))

    # Act
    result = renderer.render_bundle(bundle, dry_run=True)

    # Assert
    assert result.file_count == 5


def test_bundle_renderer_no_iteration_limit_when_none() -> None:
    """BundleRenderer has no iteration limit when max_iteration is None."""
    # Arrange
    query = QueryDescriptor(
        name="entities",
        purpose="",
        source=QuerySource.INLINE,
        content="SELECT ?slug WHERE { ?s ex:slug ?slug }",
    )
    desc = TemplateDescriptor(
        id="test",
        engine="jinja2",
        language="python",
        framework="",
        version="1.0",
        ontology=OntologyConfig("main"),
        queries=(query,),
        n3_rules=(),
        metadata=TemplateMetadata(),
        template_path="test.j2",
        raw_content="# {{ params.entity.slug }}",
    )

    registry = InMemoryTemplateRegistry()
    registry.add(desc)

    # Return many results
    query_results = {
        "SELECT ?slug WHERE { ?s ex:slug ?slug }": [{"slug": f"entity_{i}"} for i in range(500)]
    }
    graphs = {"main": MockGraphClient("main", query_results)}
    engine = ProjectionEngine(registry, graphs)
    renderer = BundleRenderer(engine, max_iteration=None)

    iter_spec = IterationSpec(query="SELECT ?slug WHERE { ?s ex:slug ?slug }", as_var="entity")
    entry = BundleTemplateEntry("test.j2", "{{ params.entity.slug }}.py", iterate=iter_spec)
    bundle = BundleDescriptor("iterated", (entry,))

    # Act
    result = renderer.render_bundle(bundle, dry_run=True)

    # Assert
    assert result.file_count == 500
