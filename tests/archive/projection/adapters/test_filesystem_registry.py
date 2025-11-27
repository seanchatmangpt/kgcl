"""Tests for FilesystemTemplateRegistry - Template loading from filesystem.

Chicago School TDD: Test behavior through state verification,
minimal mocking, AAA structure.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from kgcl.projection.adapters.filesystem_registry import FilesystemTemplateRegistry
from kgcl.projection.domain.exceptions import ResourceLimitExceeded
from kgcl.projection.domain.descriptors import N3Role, QuerySource
from kgcl.projection.ports.template_registry import TemplateRegistry


def test_registry_implements_template_registry_protocol() -> None:
    """FilesystemTemplateRegistry implements TemplateRegistry protocol."""
    # Arrange & Act
    with TemporaryDirectory() as tmpdir:
        registry = FilesystemTemplateRegistry(Path(tmpdir))

        # Assert
        assert isinstance(registry, TemplateRegistry)


def test_list_templates_empty_directory() -> None:
    """list_templates returns empty list for empty directory."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        registry = FilesystemTemplateRegistry(Path(tmpdir))

        # Act
        templates = registry.list_templates()

        # Assert
        assert templates == []


def test_list_templates_finds_j2_files() -> None:
    """list_templates finds all .j2 files in directory."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        (template_dir / "api.j2").write_text("---\nid: test\n---\nBody")
        (template_dir / "model.j2").write_text("---\nid: test2\n---\nBody")
        (template_dir / "readme.md").write_text("Not a template")
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        templates = registry.list_templates()

        # Assert
        assert sorted(templates) == ["api.j2", "model.j2"]


def test_list_templates_recursive() -> None:
    """list_templates finds templates in subdirectories."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        (template_dir / "root.j2").write_text("---\nid: root\n---\nBody")
        subdir = template_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.j2").write_text("---\nid: nested\n---\nBody")
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        templates = registry.list_templates()

        # Assert
        assert sorted(templates) == ["root.j2", "subdir/nested.j2"]


def test_exists_returns_false_for_missing() -> None:
    """exists returns False for missing template."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        registry = FilesystemTemplateRegistry(Path(tmpdir))

        # Act
        result = registry.exists("missing.j2")

        # Assert
        assert result is False


def test_exists_returns_true_for_existing() -> None:
    """exists returns True for existing template."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        (template_dir / "test.j2").write_text("---\nid: test\n---\nBody")
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        result = registry.exists("test.j2")

        # Assert
        assert result is True


def test_exists_normalizes_name() -> None:
    """exists adds .j2 extension if missing."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        (template_dir / "test.j2").write_text("---\nid: test\n---\nBody")
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        result = registry.exists("test")

        # Assert
        assert result is True


def test_get_returns_none_for_missing() -> None:
    """get returns None for missing template."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        registry = FilesystemTemplateRegistry(Path(tmpdir))

        # Act
        result = registry.get("missing.j2")

        # Assert
        assert result is None


def test_get_parses_minimal_frontmatter() -> None:
    """get parses template with minimal frontmatter."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        content = """---
id: http://example.org/templates/minimal
engine: jinja2
language: python
framework: fastapi
version: 1.0.0
ontology: main
---
Template body here
"""
        (template_dir / "minimal.j2").write_text(content)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        descriptor = registry.get("minimal.j2")

        # Assert
        assert descriptor is not None
        assert descriptor.id == "http://example.org/templates/minimal"
        assert descriptor.engine == "jinja2"
        assert descriptor.language == "python"
        assert descriptor.framework == "fastapi"
        assert descriptor.version == "1.0.0"
        assert descriptor.ontology.graph_id == "main"
        assert descriptor.raw_content == "Template body here\n"


def test_get_parses_ontology_config_dict() -> None:
    """get parses ontology as dict with graph_id and base_iri."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        content = """---
id: test
ontology:
  graph_id: event_store
  base_iri: http://example.org/base/
---
Body
"""
        (template_dir / "test.j2").write_text(content)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        descriptor = registry.get("test.j2")

        # Assert
        assert descriptor is not None
        assert descriptor.ontology.graph_id == "event_store"
        assert descriptor.ontology.base_iri == "http://example.org/base/"


def test_get_parses_inline_query() -> None:
    """get parses inline SPARQL query."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        content = """---
id: test
queries:
  - name: all_entities
    purpose: Fetch all entities
    inline: |
      SELECT ?s WHERE {
        ?s a ex:Entity
      }
---
Body
"""
        (template_dir / "test.j2").write_text(content)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        descriptor = registry.get("test.j2")

        # Assert
        assert descriptor is not None
        assert len(descriptor.queries) == 1
        query = descriptor.queries[0]
        assert query.name == "all_entities"
        assert query.purpose == "Fetch all entities"
        assert query.source == QuerySource.INLINE
        assert "SELECT ?s WHERE" in query.content


def test_get_parses_file_query() -> None:
    """get parses query from external file."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        query_dir = template_dir / "queries"
        query_dir.mkdir()

        # Write query file
        (query_dir / "entities.sparql").write_text("SELECT ?s WHERE { ?s a ex:Entity }")

        content = """---
id: test
queries:
  - name: entities
    purpose: Fetch entities
    file: entities.sparql
---
Body
"""
        (template_dir / "test.j2").write_text(content)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        descriptor = registry.get("test.j2")

        # Assert
        assert descriptor is not None
        assert len(descriptor.queries) == 1
        query = descriptor.queries[0]
        assert query.name == "entities"
        assert query.source == QuerySource.INLINE  # Converted to inline after loading
        assert "SELECT ?s WHERE" in query.content


def test_get_parses_multiple_queries() -> None:
    """get parses multiple queries in frontmatter."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        content = """---
id: test
queries:
  - name: q1
    purpose: First query
    inline: SELECT ?x WHERE { ?x a ex:A }
  - name: q2
    purpose: Second query
    inline: SELECT ?y WHERE { ?y a ex:B }
---
Body
"""
        (template_dir / "test.j2").write_text(content)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        descriptor = registry.get("test.j2")

        # Assert
        assert descriptor is not None
        assert len(descriptor.queries) == 2
        assert descriptor.queries[0].name == "q1"
        assert descriptor.queries[1].name == "q2"


def test_get_parses_n3_rules() -> None:
    """get parses N3 rules from frontmatter."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        content = """---
id: test
n3_rules:
  - name: validation
    file: rules/validate.n3
    role: precondition
  - name: inference
    file: rules/infer.n3
    role: inference
---
Body
"""
        (template_dir / "test.j2").write_text(content)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        descriptor = registry.get("test.j2")

        # Assert
        assert descriptor is not None
        assert len(descriptor.n3_rules) == 2
        assert descriptor.n3_rules[0].name == "validation"
        assert descriptor.n3_rules[0].file_path == "rules/validate.n3"
        assert descriptor.n3_rules[0].role == N3Role.PRECONDITION
        assert descriptor.n3_rules[1].name == "inference"
        assert descriptor.n3_rules[1].role == N3Role.INFERENCE


def test_get_parses_metadata() -> None:
    """get parses optional metadata section."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        content = """---
id: test
metadata:
  author: Team KGCL
  description: API template for FastAPI
  tags:
    - api
    - rest
    - fastapi
---
Body
"""
        (template_dir / "test.j2").write_text(content)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        descriptor = registry.get("test.j2")

        # Assert
        assert descriptor is not None
        assert descriptor.metadata.author == "Team KGCL"
        assert descriptor.metadata.description == "API template for FastAPI"
        assert descriptor.metadata.tags == ("api", "rest", "fastapi")


def test_get_caches_parsed_template() -> None:
    """get caches parsed template for repeated access."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        content = "---\nid: test\n---\nBody"
        (template_dir / "test.j2").write_text(content)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        descriptor1 = registry.get("test.j2")
        descriptor2 = registry.get("test.j2")

        # Assert
        assert descriptor1 is descriptor2  # Same object (cached)


def test_get_normalizes_template_name() -> None:
    """get adds .j2 extension if missing."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        content = "---\nid: test\n---\nBody"
        (template_dir / "test.j2").write_text(content)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        descriptor = registry.get("test")

        # Assert
        assert descriptor is not None
        assert descriptor.id == "test"


def test_get_preserves_template_path() -> None:
    """get sets template_path to absolute file path."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        content = "---\nid: test\n---\nBody"
        (template_dir / "test.j2").write_text(content)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        descriptor = registry.get("test.j2")

        # Assert
        assert descriptor is not None
        assert Path(descriptor.template_path).name == "test.j2"


def test_get_raises_on_missing_frontmatter() -> None:
    """get raises ValueError for template without frontmatter."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        (template_dir / "bad.j2").write_text("Just body, no frontmatter")
        registry = FilesystemTemplateRegistry(template_dir)

        # Act & Assert
        try:
            registry.get("bad.j2")
            raise AssertionError("Expected ValueError")
        except ValueError as e:
            assert "missing frontmatter" in str(e)


def test_get_raises_on_invalid_yaml() -> None:
    """get raises ValueError for invalid YAML frontmatter."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        content = """---
id: test
invalid: [unclosed
---
Body
"""
        (template_dir / "bad.j2").write_text(content)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act & Assert
        try:
            registry.get("bad.j2")
            raise AssertionError("Expected ValueError")
        except ValueError as e:
            assert "Invalid YAML" in str(e)


def test_get_raises_on_missing_id() -> None:
    """get raises ValueError for template without id field."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        content = """---
engine: jinja2
---
Body
"""
        (template_dir / "bad.j2").write_text(content)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act & Assert
        try:
            registry.get("bad.j2")
            raise AssertionError("Expected ValueError")
        except ValueError as e:
            assert "missing required 'id'" in str(e)


def test_template_dir_property() -> None:
    """template_dir property returns configured directory."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        result = registry.template_dir

        # Assert
        assert result == template_dir


def test_query_dir_property_default() -> None:
    """query_dir defaults to template_dir/queries."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        registry = FilesystemTemplateRegistry(template_dir)

        # Act
        result = registry.query_dir

        # Assert
        assert result == template_dir / "queries"


def test_query_dir_property_custom() -> None:
    """query_dir can be set to custom directory."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        query_dir = Path(tmpdir) / "custom_queries"
        registry = FilesystemTemplateRegistry(template_dir, query_dir=query_dir)

        # Act
        result = registry.query_dir

        # Assert
        assert result == query_dir


# =============================================================================
# Resource Limit Tests
# =============================================================================


def test_max_template_size_exceeded() -> None:
    """get raises ResourceLimitExceeded when template exceeds size limit."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        # Create a template that is 1000 bytes
        content = "---\nid: test\n---\n" + ("x" * 1000)
        (template_dir / "big.j2").write_text(content)

        # Limit to 500 bytes
        registry = FilesystemTemplateRegistry(template_dir, max_template_size=500)

        # Act & Assert
        with pytest.raises(ResourceLimitExceeded) as exc:
            registry.get("big.j2")

        assert exc.value.limit == 500
        assert exc.value.actual > 500
        assert "template_size" in exc.value.resource


def test_max_template_size_allows_under() -> None:
    """get allows templates under size limit."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        content = "---\nid: test\n---\nSmall body"
        (template_dir / "small.j2").write_text(content)

        # Limit to 1000 bytes
        registry = FilesystemTemplateRegistry(template_dir, max_template_size=1000)

        # Act
        descriptor = registry.get("small.j2")

        # Assert
        assert descriptor is not None
        assert descriptor.id == "test"


def test_max_template_size_allows_exact() -> None:
    """get allows templates at exactly the limit."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        content = "---\nid: test\n---\n" + ("x" * 100)
        (template_dir / "exact.j2").write_text(content)
        file_size = (template_dir / "exact.j2").stat().st_size

        # Set limit to exact file size
        registry = FilesystemTemplateRegistry(template_dir, max_template_size=file_size)

        # Act
        descriptor = registry.get("exact.j2")

        # Assert
        assert descriptor is not None


def test_no_size_limit_when_none() -> None:
    """get allows any size when max_template_size is None."""
    # Arrange
    with TemporaryDirectory() as tmpdir:
        template_dir = Path(tmpdir)
        # Create a large template (10KB)
        content = "---\nid: test\n---\n" + ("x" * 10000)
        (template_dir / "large.j2").write_text(content)

        registry = FilesystemTemplateRegistry(template_dir, max_template_size=None)

        # Act
        descriptor = registry.get("large.j2")

        # Assert
        assert descriptor is not None
        assert descriptor.id == "test"
