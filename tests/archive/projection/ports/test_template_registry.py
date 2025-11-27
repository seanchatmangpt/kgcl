"""Tests for TemplateRegistry protocol and implementations - Chicago School TDD.

Tests verify the protocol compliance and InMemoryTemplateRegistry behavior.
"""

from __future__ import annotations

import pytest

from kgcl.projection.domain.descriptors import OntologyConfig, TemplateDescriptor, TemplateMetadata
from kgcl.projection.ports.template_registry import InMemoryTemplateRegistry, TemplateRegistry

# =============================================================================
# TemplateRegistry Protocol Tests
# =============================================================================


class TestTemplateRegistryProtocol:
    """Tests for TemplateRegistry protocol."""

    def test_in_memory_is_template_registry(self) -> None:
        """InMemoryTemplateRegistry satisfies TemplateRegistry protocol."""
        registry = InMemoryTemplateRegistry()
        assert isinstance(registry, TemplateRegistry)


# =============================================================================
# InMemoryTemplateRegistry Tests
# =============================================================================


class TestInMemoryTemplateRegistry:
    """Tests for InMemoryTemplateRegistry."""

    @pytest.fixture
    def sample_descriptor(self) -> TemplateDescriptor:
        """Sample template descriptor for tests."""
        return TemplateDescriptor(
            id="http://example.org/templates/api",
            engine="jinja2",
            language="python",
            framework="fastapi",
            version="1.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="api.j2",
            raw_content="{% for e in entities %}...{% endfor %}",
        )

    def test_create_empty_registry(self) -> None:
        """Can create empty registry."""
        registry = InMemoryTemplateRegistry()
        assert registry.list_templates() == []

    def test_add_template(self, sample_descriptor: TemplateDescriptor) -> None:
        """Can add template to registry."""
        registry = InMemoryTemplateRegistry()
        registry.add(sample_descriptor)
        assert registry.exists("api.j2")

    def test_get_existing_template(self, sample_descriptor: TemplateDescriptor) -> None:
        """get returns registered template."""
        registry = InMemoryTemplateRegistry()
        registry.add(sample_descriptor)

        retrieved = registry.get("api.j2")
        assert retrieved is not None
        assert retrieved.id == sample_descriptor.id

    def test_get_missing_template(self) -> None:
        """get returns None for missing template."""
        registry = InMemoryTemplateRegistry()
        assert registry.get("missing.j2") is None

    def test_list_templates(self, sample_descriptor: TemplateDescriptor) -> None:
        """list_templates returns all template names."""
        registry = InMemoryTemplateRegistry()
        registry.add(sample_descriptor)

        # Add another
        other = TemplateDescriptor(
            id="other",
            engine="jinja2",
            language="ts",
            framework="",
            version="1.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="other.j2",
            raw_content="",
        )
        registry.add(other)

        templates = registry.list_templates()
        assert set(templates) == {"api.j2", "other.j2"}

    def test_exists_true(self, sample_descriptor: TemplateDescriptor) -> None:
        """exists returns True for registered template."""
        registry = InMemoryTemplateRegistry()
        registry.add(sample_descriptor)
        assert registry.exists("api.j2") is True

    def test_exists_false(self) -> None:
        """exists returns False for missing template."""
        registry = InMemoryTemplateRegistry()
        assert registry.exists("missing.j2") is False

    def test_add_overwrites_existing(self, sample_descriptor: TemplateDescriptor) -> None:
        """Adding template with same path overwrites previous."""
        registry = InMemoryTemplateRegistry()
        registry.add(sample_descriptor)

        # Create different descriptor with same path
        updated = TemplateDescriptor(
            id="updated-id",
            engine="jinja2",
            language="typescript",
            framework="nextjs",
            version="2.0.0",
            ontology=OntologyConfig(graph_id="main"),
            queries=(),
            n3_rules=(),
            metadata=TemplateMetadata(),
            template_path="api.j2",  # Same path
            raw_content="new content",
        )
        registry.add(updated)

        retrieved = registry.get("api.j2")
        assert retrieved is not None
        assert retrieved.id == "updated-id"
        assert retrieved.version == "2.0.0"
