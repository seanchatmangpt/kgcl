"""Tests for template engine."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.codegen.template_engine import TemplateEngine, TemplateNotFoundError


class TestTemplateEngine:
    """Test Jinja2 template rendering."""

    @pytest.fixture
    def template_dir(self, tmp_path: Path) -> Path:
        """Create temporary template directory."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        return template_dir

    @pytest.fixture
    def engine(self, template_dir: Path) -> TemplateEngine:
        """Create template engine instance."""
        return TemplateEngine(template_dir)

    def test_init_success(self, template_dir: Path) -> None:
        """Test successful engine initialization."""
        engine = TemplateEngine(template_dir)

        assert engine.template_dir == template_dir
        assert engine.env is not None

    def test_init_directory_not_found(self) -> None:
        """Test initialization with non-existent directory."""
        non_existent = Path("/tmp/does_not_exist")

        with pytest.raises(FileNotFoundError):
            TemplateEngine(non_existent)

    def test_render_simple_template(self, engine: TemplateEngine, template_dir: Path) -> None:
        """Test rendering simple template."""
        template_file = template_dir / "simple.txt"
        template_file.write_text("Hello {{ name }}!")

        result = engine.render("simple.txt", {"name": "World"})

        assert result == "Hello World!"

    def test_render_template_not_found(self, engine: TemplateEngine) -> None:
        """Test rendering non-existent template."""
        with pytest.raises(TemplateNotFoundError):
            engine.render("does_not_exist.txt", {})

    def test_snake_case_filter(self, engine: TemplateEngine) -> None:
        """Test snake_case filter."""
        template_str = "{{ name | snake_case }}"

        result = engine.render_string(template_str, {"name": "MyClassName"})

        assert result == "my_class_name"
