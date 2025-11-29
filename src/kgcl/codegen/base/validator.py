"""Validation layer for generated code.

This module provides validation utilities to ensure generated code
meets quality standards before being written to disk.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any


class ValidationError(Exception):
    """Raised when generated code fails validation."""

    pass


class Validator:
    """Validate generated code for correctness and quality.

    Provides various validation checks:
    - Python syntax validation
    - Type hint presence
    - Docstring presence
    - Import organization
    - Line length limits
    """

    def __init__(
        self, max_line_length: int = 120, require_type_hints: bool = True, require_docstrings: bool = True
    ) -> None:
        """Initialize validator with configuration.

        Parameters
        ----------
        max_line_length : int
            Maximum allowed line length (default: 120)
        require_type_hints : bool
            Whether to require type hints (default: True)
        require_docstrings : bool
            Whether to require docstrings (default: True)
        """
        self.max_line_length = max_line_length
        self.require_type_hints = require_type_hints
        self.require_docstrings = require_docstrings

    def validate_python(self, source: str) -> None:
        """Validate Python source code.

        Parameters
        ----------
        source : str
            Python source code to validate

        Raises
        ------
        ValidationError
            If validation fails
        """
        # 1. Check syntax
        self._check_syntax(source)

        # 2. Parse AST
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            msg = f"Syntax error: {e}"
            raise ValidationError(msg) from e

        # 3. Check type hints (if required)
        if self.require_type_hints:
            self._check_type_hints(tree)

        # 4. Check docstrings (if required)
        if self.require_docstrings:
            self._check_docstrings(tree)

        # 5. Check line length
        self._check_line_length(source)

        # 6. Check imports
        self._check_imports(tree)

    def _check_syntax(self, source: str) -> None:
        """Check Python syntax.

        Parameters
        ----------
        source : str
            Python source code

        Raises
        ------
        ValidationError
            If syntax is invalid
        """
        try:
            compile(source, "<generated>", "exec")
        except SyntaxError as e:
            msg = f"Invalid Python syntax at line {e.lineno}: {e.msg}"
            raise ValidationError(msg) from e

    def _check_type_hints(self, tree: ast.Module) -> None:
        """Check that functions have type hints.

        Parameters
        ----------
        tree : ast.Module
            Parsed AST

        Raises
        ------
        ValidationError
            If public functions lack type hints
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip private methods (starting with _)
                if node.name.startswith("_"):
                    continue

                # Check return type hint
                if node.returns is None:
                    msg = f"Function {node.name} missing return type hint"
                    raise ValidationError(msg)

                # Check parameter type hints
                for arg in node.args.args:
                    if arg.annotation is None and arg.arg != "self":
                        msg = f"Parameter {arg.arg} in {node.name} missing type hint"
                        raise ValidationError(msg)

    def _check_docstrings(self, tree: ast.Module) -> None:
        """Check that public classes and functions have docstrings.

        Parameters
        ----------
        tree : ast.Module
            Parsed AST

        Raises
        ------
        ValidationError
            If public definitions lack docstrings
        """
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                # Skip private items
                if node.name.startswith("_"):
                    continue

                # Check for docstring
                docstring = ast.get_docstring(node)
                if not docstring:
                    kind = "Class" if isinstance(node, ast.ClassDef) else "Function"
                    msg = f"{kind} {node.name} missing docstring"
                    raise ValidationError(msg)

    def _check_line_length(self, source: str) -> None:
        """Check that lines don't exceed maximum length.

        Parameters
        ----------
        source : str
            Python source code

        Raises
        ------
        ValidationError
            If any line exceeds max_line_length
        """
        for i, line in enumerate(source.split("\n"), start=1):
            # Remove trailing whitespace for check
            clean_line = line.rstrip()
            if len(clean_line) > self.max_line_length:
                msg = f"Line {i} exceeds {self.max_line_length} characters ({len(clean_line)} chars)"
                raise ValidationError(msg)

    def _check_imports(self, tree: ast.Module) -> None:
        """Check import organization.

        Parameters
        ----------
        tree : ast.Module
            Parsed AST

        Raises
        ------
        ValidationError
            If imports are poorly organized
        """
        # Collect imports
        imports: list[tuple[int, str]] = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                line_no = node.lineno
                if isinstance(node, ast.Import):
                    import_type = "absolute"
                else:
                    # Check for relative imports
                    if node.level and node.level > 0:
                        msg = f"Relative import at line {line_no} (use absolute imports)"
                        raise ValidationError(msg)
                    import_type = "absolute"

                imports.append((line_no, import_type))

        # Verify imports are at the top (after docstring and __future__)
        if imports:
            first_import_line = imports[0][0]
            # Allow module docstring and __future__ before imports
            allowed_before = ["Expr", "ImportFrom"]  # Docstring or __future__

            for _i, node in enumerate(tree.body):
                if node.lineno >= first_import_line:
                    break
                if type(node).__name__ not in allowed_before:
                    msg = f"Non-import statement before imports at line {node.lineno}"
                    raise ValidationError(msg)

    def validate_file(self, file_path: Path) -> None:
        """Validate a generated file.

        Parameters
        ----------
        file_path : Path
            Path to generated file

        Raises
        ------
        ValidationError
            If file fails validation
        FileNotFoundError
            If file doesn't exist
        """
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        source = file_path.read_text(encoding="utf-8")

        # Determine language from extension
        suffix = file_path.suffix.lower()
        if suffix == ".py":
            self.validate_python(source)
        else:
            # For non-Python files, just check line length
            self._check_line_length(source)
