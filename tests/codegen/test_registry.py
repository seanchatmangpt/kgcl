"""Tests for generator registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from kgcl.codegen.base.generator import BaseGenerator, GenerationResult
from kgcl.codegen.registry import GeneratorNotFoundError, GeneratorRegistry, register_generator


class DummyGenerator(BaseGenerator):
    """Dummy generator for testing."""

    def __init__(self, template_dir: Path, output_dir: Path, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(template_dir, output_dir)
        self.test_value = kwargs.get("test_value", "default")

    @property
    def parser(self):  # type: ignore[no-untyped-def]
        """Return dummy parser."""
        return None

    def _transform(self, metadata, **kwargs):  # type: ignore[no-untyped-def]
        """Transform metadata."""
        return {"data": metadata}

    def _get_template_name(self, metadata, **kwargs):  # type: ignore[no-untyped-def]
        """Get template name."""
        return "test.j2"

    def _get_output_path(self, metadata, **kwargs):  # type: ignore[no-untyped-def]
        """Get output path."""
        return self.output_dir / "test.py"


class TestGeneratorRegistry:
    """Test GeneratorRegistry functionality."""

    def test_init(self) -> None:
        """Test registry initialization."""
        registry = GeneratorRegistry()

        assert len(registry.list_generators()) == 0

    def test_register_generator(self) -> None:
        """Test registering a generator."""
        registry = GeneratorRegistry()

        def dummy_factory(**kwargs):  # type: ignore[no-untyped-def]
            return DummyGenerator(**kwargs)

        registry.register("dummy", dummy_factory, description="Dummy generator")

        assert "dummy" in registry.list_generators()

    def test_create_generator(self, tmp_path: Path) -> None:
        """Test creating generator instance."""
        registry = GeneratorRegistry()

        def dummy_factory(**kwargs):  # type: ignore[no-untyped-def]
            return DummyGenerator(**kwargs)

        registry.register("dummy", dummy_factory)

        # Create template directory
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        generator = registry.create(
            "dummy", template_dir=template_dir, output_dir=tmp_path / "output", test_value="custom"
        )

        assert isinstance(generator, DummyGenerator)
        assert generator.test_value == "custom"

    def test_create_unregistered_generator(self, tmp_path: Path) -> None:
        """Test creating unregistered generator raises error."""
        registry = GeneratorRegistry()

        with pytest.raises(GeneratorNotFoundError):
            registry.create("nonexistent", template_dir=tmp_path / "templates", output_dir=tmp_path / "output")

    def test_unregister_generator(self) -> None:
        """Test unregistering a generator."""
        registry = GeneratorRegistry()

        def dummy_factory(**kwargs):  # type: ignore[no-untyped-def]
            return DummyGenerator(**kwargs)

        registry.register("dummy", dummy_factory)
        assert "dummy" in registry.list_generators()

        registry.unregister("dummy")
        assert "dummy" not in registry.list_generators()

    def test_unregister_nonexistent(self) -> None:
        """Test unregistering non-existent generator raises error."""
        registry = GeneratorRegistry()

        with pytest.raises(GeneratorNotFoundError):
            registry.unregister("nonexistent")

    def test_get_metadata(self) -> None:
        """Test retrieving generator metadata."""
        registry = GeneratorRegistry()

        def dummy_factory(**kwargs):  # type: ignore[no-untyped-def]
            return DummyGenerator(**kwargs)

        registry.register(
            "dummy", dummy_factory, description="Test generator", file_types=[".test"], category="testing"
        )

        metadata = registry.get_metadata("dummy")

        assert metadata["description"] == "Test generator"
        assert metadata["file_types"] == [".test"]
        assert metadata["category"] == "testing"

    def test_get_metadata_nonexistent(self) -> None:
        """Test getting metadata for non-existent generator."""
        registry = GeneratorRegistry()

        with pytest.raises(GeneratorNotFoundError):
            registry.get_metadata("nonexistent")

    def test_list_generators(self) -> None:
        """Test listing all generators."""
        registry = GeneratorRegistry()

        def dummy_factory(**kwargs):  # type: ignore[no-untyped-def]
            return DummyGenerator(**kwargs)

        registry.register("gen1", dummy_factory)
        registry.register("gen2", dummy_factory)
        registry.register("gen3", dummy_factory)

        generators = registry.list_generators()

        assert len(generators) == 3
        assert "gen1" in generators
        assert "gen2" in generators
        assert "gen3" in generators
        # Should be sorted
        assert generators == sorted(generators)

    def test_discover_generators(self) -> None:
        """Test automatic generator discovery."""
        registry = GeneratorRegistry()

        registry.discover_generators()

        # Should register built-in generators
        generators = registry.list_generators()
        assert len(generators) > 0

    def test_register_generator_decorator(self, tmp_path: Path) -> None:
        """Test @register_generator decorator."""
        from kgcl.codegen.registry import get_registry

        @register_generator("test_decorator", description="Test")
        def create_test_generator(**kwargs):  # type: ignore[no-untyped-def]
            return DummyGenerator(**kwargs)

        registry = get_registry()

        # Generator should be registered
        assert "test_decorator" in registry.list_generators()

        # Create template directory
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        # Should be able to create instance
        generator = registry.create("test_decorator", template_dir=template_dir, output_dir=tmp_path / "output")

        assert isinstance(generator, DummyGenerator)

        # Clean up
        registry.unregister("test_decorator")
