"""Backwards compatibility wrapper for Java generator.

This module maintains the original API while delegating to the unified
framework implementation.

DEPRECATED: Use kgcl.codegen.generators.java_generator instead.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

from kgcl.codegen.generators.java_generator import (
    JavaClass,
    JavaGenerator,
    JavaMethod,
    PythonClass,
    PythonMethod,
)


class CodeGenerator:
    """DEPRECATED: Use JavaGenerator from kgcl.codegen.generators.java_generator."""

    def __init__(self, template_dir: Path, output_dir: Path) -> None:
        """Initialize code generator.

        DEPRECATED: Use JavaGenerator instead.
        """
        warnings.warn(
            "CodeGenerator is deprecated. Use JavaGenerator instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        self.generator = JavaGenerator(
            template_dir=template_dir,
            output_dir=output_dir,
        )
        self.output_dir = output_dir

    def generate_python_client(self, java_file: Path) -> Path:
        """Generate Python client from Java service.

        DEPRECATED: Use JavaGenerator.generate instead.

        Parameters
        ----------
        java_file : Path
            Path to Java source file

        Returns
        -------
        Path
            Path to generated Python file
        """
        result = self.generator.generate(java_file)
        return result.output_path


__all__ = [
    "CodeGenerator",
    "JavaClass",
    "JavaMethod",
    "PythonClass",
    "PythonMethod",
]
