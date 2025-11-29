"""Jinja2 template rendering engine for code generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader


class TemplateNotFoundError(Exception):
    """Raised when a template file cannot be found."""

    pass


class TemplateRenderError(Exception):
    """Raised when template rendering fails."""

    pass


class TemplateEngine:
    """Template rendering engine using Jinja2."""

    def __init__(self, template_dir: Path) -> None:
        """Initialize template engine."""
        if not template_dir.exists():
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        self._register_filters()

    def _register_filters(self) -> None:
        """Register custom Jinja2 filters for code generation."""
        self.env.filters["snake_case"] = self._to_snake_case
        self.env.filters["camel_case"] = self._to_camel_case
        self.env.filters["indent"] = self._indent
        self.env.filters["python_default"] = self._python_default_value

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render template with context."""
        try:
            template = self.env.get_template(template_name)
        except Exception as e:
            raise TemplateNotFoundError(
                f"Template not found: {template_name}"
            ) from e

        try:
            return template.render(**context)
        except Exception as e:
            raise TemplateRenderError(f"Failed to render {template_name}: {e}") from e

    def render_string(self, template_str: str, context: dict[str, Any]) -> str:
        """Render template from string."""
        try:
            template = self.env.from_string(template_str)
            return template.render(**context)
        except Exception as e:
            raise TemplateRenderError(f"Failed to render template string: {e}") from e

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert CamelCase to snake_case."""
        import re

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    @staticmethod
    def _to_camel_case(name: str) -> str:
        """Convert snake_case to CamelCase."""
        return "".join(word.capitalize() for word in name.split("_"))

    @staticmethod
    def _indent(text: str, spaces: int = 4) -> str:
        """Indent text by specified number of spaces."""
        indent_str = " " * spaces
        lines = text.split("\n")
        return "\n".join(indent_str + line if line.strip() else "" for line in lines)

    @staticmethod
    def _python_default_value(python_type: str) -> str:
        """Get Python default value for a type."""
        defaults = {
            "int": "0",
            "float": "0.0",
            "bool": "False",
            "str": '""',
        }
        if python_type in defaults:
            return defaults[python_type]
        return "None"
