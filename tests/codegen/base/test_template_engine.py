"""Tests for unified template engine."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from kgcl.codegen.base.template_engine import TemplateEngine, TemplateNotFoundError, TemplateRenderError


class TestTemplateEngine:
    """Test TemplateEngine functionality."""

    def test_init_with_valid_dir(self, tmp_path: Path) -> None:
        """Test initialization with valid template directory."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        engine = TemplateEngine(template_dir)

        assert engine.template_dir == template_dir
        assert engine.env is not None

    def test_init_with_invalid_dir(self, tmp_path: Path) -> None:
        """Test initialization with non-existent directory."""
        invalid_dir = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError):
            TemplateEngine(invalid_dir)

    def test_render_simple_template(self, tmp_path: Path) -> None:
        """Test rendering a simple template."""
        # Create template directory and file
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("Hello {{ name }}!")

        engine = TemplateEngine(template_dir)
        result = engine.render("test.j2", {"name": "World"})

        assert result == "Hello World!"

    def test_render_nonexistent_template(self, tmp_path: Path) -> None:
        """Test rendering non-existent template raises error."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        engine = TemplateEngine(template_dir)

        with pytest.raises(TemplateNotFoundError):
            engine.render("nonexistent.j2", {})

    def test_render_string(self, tmp_path: Path) -> None:
        """Test rendering template from string."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()

        engine = TemplateEngine(template_dir)
        result = engine.render_string("Hello {{ name }}!", {"name": "World"})

        assert result == "Hello World!"

    def test_snake_case_filter(self, tmp_path: Path) -> None:
        """Test snake_case filter."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("{{ name | snake_case }}")

        engine = TemplateEngine(template_dir)
        result = engine.render("test.j2", {"name": "MyClassName"})

        assert result == "my_class_name"

    def test_camel_case_filter(self, tmp_path: Path) -> None:
        """Test camel_case filter."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("{{ name | camel_case }}")

        engine = TemplateEngine(template_dir)
        result = engine.render("test.j2", {"name": "my_function_name"})

        assert result == "myFunctionName"

    def test_pascal_case_filter(self, tmp_path: Path) -> None:
        """Test pascal_case filter."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("{{ name | pascal_case }}")

        engine = TemplateEngine(template_dir)
        result = engine.render("test.j2", {"name": "my_class_name"})

        assert result == "MyClassName"

    def test_kebab_case_filter(self, tmp_path: Path) -> None:
        """Test kebab_case filter."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("{{ name | kebab_case }}")

        engine = TemplateEngine(template_dir)
        result = engine.render("test.j2", {"name": "MyClassName"})

        assert result == "my-class-name"

    def test_indent_filter(self, tmp_path: Path) -> None:
        """Test indent filter."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("{{ text | indent(2) }}")

        engine = TemplateEngine(template_dir)
        result = engine.render("test.j2", {"text": "line1\nline2"})

        assert result == "  line1\n  line2"

    def test_python_default_filter(self, tmp_path: Path) -> None:
        """Test python_default filter."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("{{ type_hint | python_default }}")

        engine = TemplateEngine(template_dir)

        # Test int
        result = engine.render("test.j2", {"type_hint": "int"})
        assert result == "0"

        # Test str
        result = engine.render("test.j2", {"type_hint": "str"})
        assert result == '""'

        # Test unknown
        result = engine.render("test.j2", {"type_hint": "CustomType"})
        assert result == "None"

    def test_quote_string_filter(self, tmp_path: Path) -> None:
        """Test quote_string filter."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("{{ value | quote_string }}")

        engine = TemplateEngine(template_dir)

        # Test string value
        result = engine.render("test.j2", {"value": "hello"})
        assert result == '"hello"'

        # Test None value
        result = engine.render("test.j2", {"value": None})
        assert result == "None"

    def test_docstring_filter(self, tmp_path: Path) -> None:
        """Test docstring filter."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("{{ text | docstring }}")

        engine = TemplateEngine(template_dir)

        # Single line
        result = engine.render("test.j2", {"text": "Short description."})
        assert result == '    """Short description."""'

        # Multi-line
        result = engine.render("test.j2", {"text": "Line 1.\nLine 2."})
        assert '"""' in result
        assert "Line 1." in result
        assert "Line 2." in result

    def test_whitespace_handling(self, tmp_path: Path) -> None:
        """Test trim_blocks and lstrip_blocks configuration."""
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.j2"
        template_file.write_text("{% if true %}\n  Hello\n{% endif %}")

        engine = TemplateEngine(template_dir)
        result = engine.render("test.j2", {})

        # Should trim whitespace properly
        assert result.strip() == "Hello"
