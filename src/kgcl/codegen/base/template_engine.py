"""Unified Jinja2 template rendering engine.

This module merges the template engines from both CLI and YAWL generators,
providing a comprehensive set of filters and utilities for code generation.
"""

from __future__ import annotations

import re
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
    """Template rendering engine using Jinja2.

    Features:
    - Custom filters for code generation (snake_case, camel_case, etc.)
    - Proper whitespace handling (trim_blocks, lstrip_blocks)
    - Error handling with detailed messages
    - Support for both file-based and string templates

    Examples
    --------
    >>> engine = TemplateEngine(Path("templates"))
    >>> context = {"class_name": "MyClass", "methods": ["foo", "bar"]}
    >>> code = engine.render("python_class.py.j2", context)
    """

    def __init__(self, template_dir: Path) -> None:
        """Initialize template engine.

        Parameters
        ----------
        template_dir : Path
            Directory containing Jinja2 templates

        Raises
        ------
        FileNotFoundError
            If template directory doesn't exist
        """
        if not template_dir.exists():
            msg = f"Template directory not found: {template_dir}"
            raise FileNotFoundError(msg)

        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            autoescape=False,  # Code generation doesn't need HTML escaping
        )
        self._register_filters()

    def _register_filters(self) -> None:
        """Register custom Jinja2 filters for code generation."""
        self.env.filters["snake_case"] = self._to_snake_case
        self.env.filters["camel_case"] = self._to_camel_case
        self.env.filters["pascal_case"] = self._to_pascal_case
        self.env.filters["kebab_case"] = self._to_kebab_case
        self.env.filters["indent"] = self._indent
        self.env.filters["python_default"] = self._python_default_value
        self.env.filters["quote_string"] = self._quote_string
        self.env.filters["docstring"] = self._format_docstring

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render template file with context.

        Parameters
        ----------
        template_name : str
            Template file name (relative to template_dir)
        context : dict[str, Any]
            Template context variables

        Returns
        -------
        str
            Rendered template

        Raises
        ------
        TemplateNotFoundError
            If template file doesn't exist
        TemplateRenderError
            If rendering fails
        """
        try:
            template = self.env.get_template(template_name)
        except Exception as e:
            msg = f"Template not found: {template_name}"
            raise TemplateNotFoundError(msg) from e

        try:
            return template.render(**context)
        except Exception as e:
            msg = f"Failed to render {template_name}: {e}"
            raise TemplateRenderError(msg) from e

    def render_string(self, template_str: str, context: dict[str, Any]) -> str:
        """Render template from string.

        Parameters
        ----------
        template_str : str
            Template string with Jinja2 syntax
        context : dict[str, Any]
            Template context variables

        Returns
        -------
        str
            Rendered template

        Raises
        ------
        TemplateRenderError
            If rendering fails
        """
        try:
            template = self.env.from_string(template_str)
            return template.render(**context)
        except Exception as e:
            msg = f"Failed to render template string: {e}"
            raise TemplateRenderError(msg) from e

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert CamelCase to snake_case.

        Parameters
        ----------
        name : str
            Name in any case format

        Returns
        -------
        str
            snake_case name

        Examples
        --------
        >>> TemplateEngine._to_snake_case("MyClassName")
        'my_class_name'
        >>> TemplateEngine._to_snake_case("HTTPSConnection")
        'https_connection'
        """
        # Handle acronyms (e.g., HTTPSConnection -> https_connection)
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    @staticmethod
    def _to_camel_case(name: str) -> str:
        """Convert snake_case to camelCase.

        Parameters
        ----------
        name : str
            Name in snake_case

        Returns
        -------
        str
            camelCase name

        Examples
        --------
        >>> TemplateEngine._to_camel_case("my_function_name")
        'myFunctionName'
        """
        parts = name.split("_")
        if not parts:
            return name
        return parts[0].lower() + "".join(word.capitalize() for word in parts[1:])

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        """Convert snake_case to PascalCase.

        Parameters
        ----------
        name : str
            Name in snake_case

        Returns
        -------
        str
            PascalCase name

        Examples
        --------
        >>> TemplateEngine._to_pascal_case("my_class_name")
        'MyClassName'
        """
        return "".join(word.capitalize() for word in name.split("_"))

    @staticmethod
    def _to_kebab_case(name: str) -> str:
        """Convert to kebab-case.

        Parameters
        ----------
        name : str
            Name in any case format

        Returns
        -------
        str
            kebab-case name

        Examples
        --------
        >>> TemplateEngine._to_kebab_case("MyClassName")
        'my-class-name'
        """
        snake = TemplateEngine._to_snake_case(name)
        return snake.replace("_", "-")

    @staticmethod
    def _indent(text: str, spaces: int = 4, skip_first: bool = False) -> str:
        """Indent text by specified number of spaces.

        Parameters
        ----------
        text : str
            Text to indent
        spaces : int
            Number of spaces to indent (default: 4)
        skip_first : bool
            If True, don't indent first line (default: False)

        Returns
        -------
        str
            Indented text

        Examples
        --------
        >>> TemplateEngine._indent("line1\\nline2", spaces=2)
        '  line1\\n  line2'
        """
        indent_str = " " * spaces
        lines = text.split("\n")

        result_lines = []
        for i, line in enumerate(lines):
            if skip_first and i == 0:
                result_lines.append(line)
            elif line.strip():  # Only indent non-empty lines
                result_lines.append(indent_str + line)
            else:
                result_lines.append("")  # Preserve empty lines

        return "\n".join(result_lines)

    @staticmethod
    def _python_default_value(python_type: str) -> str:
        """Get Python default value for a type.

        Parameters
        ----------
        python_type : str
            Python type hint string

        Returns
        -------
        str
            Default value as string

        Examples
        --------
        >>> TemplateEngine._python_default_value("int")
        '0'
        >>> TemplateEngine._python_default_value("str")
        '""'
        >>> TemplateEngine._python_default_value("MyClass")
        'None'
        """
        defaults: dict[str, str] = {
            "int": "0",
            "float": "0.0",
            "bool": "False",
            "str": '""',
            "list": "[]",
            "dict": "{}",
            "set": "set()",
            "tuple": "()",
        }

        # Handle generic types (e.g., list[str] -> [])
        if "[" in python_type:
            base_type = python_type.split("[")[0]
            if base_type in defaults:
                return defaults[base_type]

        return defaults.get(python_type, "None")

    @staticmethod
    def _quote_string(value: str | None) -> str:
        """Quote string value for Python code.

        Parameters
        ----------
        value : str | None
            String value to quote

        Returns
        -------
        str
            Quoted string or "None"

        Examples
        --------
        >>> TemplateEngine._quote_string("hello")
        '"hello"'
        >>> TemplateEngine._quote_string(None)
        'None'
        """
        if value is None:
            return "None"
        # Escape quotes in the string
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'

    @staticmethod
    def _format_docstring(text: str, indent_level: int = 1) -> str:
        """Format text as Python docstring.

        Parameters
        ----------
        text : str
            Docstring content
        indent_level : int
            Indentation level (number of 4-space indents)

        Returns
        -------
        str
            Formatted docstring with triple quotes

        Examples
        --------
        >>> TemplateEngine._format_docstring("This is a docstring.")
        '    \"\"\"This is a docstring.\"\"\"'
        """
        if not text.strip():
            return ""

        indent = " " * (indent_level * 4)
        lines = text.strip().split("\n")

        if len(lines) == 1:
            # Single-line docstring
            return f'{indent}"""{lines[0]}"""'

        # Multi-line docstring
        result = [f'{indent}"""']
        for line in lines:
            result.append(f"{indent}{line}")
        result.append(f'{indent}"""')

        return "\n".join(result)
