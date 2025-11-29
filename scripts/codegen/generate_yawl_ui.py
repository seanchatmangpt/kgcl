#!/usr/bin/env python3
"""Generate YAWL UI Python/React code from Java sources.

Systematic code generator for converting Java YAWL UI code to Python/React.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from scripts.codegen.java_parser import JavaParser
from scripts.codegen.template_engine import TemplateEngine


class YAWLUICodeGenerator:
    """YAWL UI code generator.

    Converts Java YAWL UI code to Python clients, models, FastAPI endpoints,
    React components, and tests.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize code generator.

        Parameters
        ----------
        project_root : Path | None
            Project root directory (defaults to cwd)
        """
        if project_root is None:
            project_root = Path.cwd()

        self.project_root = project_root
        self.parser = JavaParser()
        self.engine = TemplateEngine()

        # Output directories
        self.output_dirs = {
            "client": project_root / "src" / "kgcl" / "yawl_ui" / "clients",
            "model": project_root / "src" / "kgcl" / "yawl_ui" / "models",
            "endpoint": project_root / "src" / "kgcl" / "yawl_ui" / "api",
            "component": project_root / "frontend" / "src" / "components",
            "test": project_root / "tests" / "yawl_ui",
        }

        # Create output directories
        for output_dir in self.output_dirs.values():
            output_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_java(
        self, java_file: Path, output_type: str, custom_metadata: dict[str, Any] | None = None
    ) -> Path:
        """Generate code from Java source file.

        Parameters
        ----------
        java_file : Path
            Path to Java source file
        output_type : str
            Output type: "client", "model", "endpoint", "component", "test"
        custom_metadata : dict[str, Any] | None
            Custom metadata to override/extend parser output

        Returns
        -------
        Path
            Path to generated output file

        Raises
        ------
        ValueError
            If output_type is invalid or generation fails
        FileNotFoundError
            If java_file does not exist
        """
        if output_type not in self.output_dirs:
            raise ValueError(
                f"Invalid output_type: {output_type}. "
                f"Must be one of: {list(self.output_dirs.keys())}"
            )

        # Parse Java source
        metadata = self.parser.parse(java_file)
        metadata_dict = self.parser.to_dict(metadata)

        # Merge custom metadata if provided
        if custom_metadata:
            metadata_dict.update(custom_metadata)

        # Select template and output location
        template_name, output_path = self._get_template_and_output(
            output_type, metadata_dict
        )

        # Render template
        self.engine.render_to_file(template_name, metadata_dict, output_path)

        # Auto-generate tests for non-test outputs
        if output_type != "test":
            self._generate_test(metadata_dict, output_type)

        return output_path

    def _get_template_and_output(
        self, output_type: str, metadata: dict[str, Any]
    ) -> tuple[str, Path]:
        """Determine template name and output path.

        Parameters
        ----------
        output_type : str
            Output type
        metadata : dict[str, Any]
            Metadata dictionary

        Returns
        -------
        tuple[str, Path]
            Template name and output file path
        """
        class_name = metadata["class_name"]
        output_dir = self.output_dirs[output_type]

        if output_type == "client":
            template = "python_client.py.jinja2"
            filename = f"{self._to_snake_case(class_name)}.py"
        elif output_type == "model":
            template = "pydantic_model.py.jinja2"
            filename = f"{self._to_snake_case(class_name)}.py"
        elif output_type == "endpoint":
            template = "fastapi_endpoint.py.jinja2"
            filename = f"{self._to_snake_case(class_name)}_endpoints.py"
        elif output_type == "component":
            template = "react_component.tsx.jinja2"
            filename = f"{class_name}.tsx"
        elif output_type == "test":
            template = "pytest_test.py.jinja2"
            filename = f"test_{self._to_snake_case(class_name)}.py"
        else:
            raise ValueError(f"Unknown output_type: {output_type}")

        output_path = output_dir / filename
        return template, output_path

    def _generate_test(self, metadata: dict[str, Any], source_type: str) -> Path:
        """Auto-generate test file for generated code.

        Parameters
        ----------
        metadata : dict[str, Any]
            Metadata for test generation
        source_type : str
            Source output type that was generated

        Returns
        -------
        Path
            Path to generated test file
        """
        class_name = metadata["class_name"]
        test_metadata = {
            "class_name": class_name,
            "module_path": f"kgcl.yawl_ui.{source_type}s.{self._to_snake_case(class_name)}",
            "test_methods": [
                {
                    "name": f"{method['name']}_basic",
                    "description": f"Test {method['name']} basic functionality",
                    "implementation": f"# TODO: Implement test for {method['name']}()\n        pass",
                }
                for method in metadata.get("methods", [])
            ],
        }

        template = "pytest_test.py.jinja2"
        output_path = (
            self.output_dirs["test"]
            / f"test_{self._to_snake_case(class_name)}.py"
        )

        self.engine.render_to_file(template, test_metadata, output_path)
        return output_path

    @staticmethod
    def _to_snake_case(camel: str) -> str:
        """Convert CamelCase to snake_case.

        Parameters
        ----------
        camel : str
            CamelCase string

        Returns
        -------
        str
            snake_case string
        """
        import re

        return re.sub(r"(?<!^)(?=[A-Z])", "_", camel).lower()


def main() -> None:
    """CLI entry point for YAWL UI code generator."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate YAWL UI Python/React code from Java sources"
    )
    parser.add_argument("java_file", type=Path, help="Java source file to convert")
    parser.add_argument(
        "output_type",
        choices=["client", "model", "endpoint", "component", "test"],
        help="Type of code to generate",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )

    args = parser.parse_args()

    try:
        generator = YAWLUICodeGenerator(project_root=args.project_root)
        output_path = generator.generate_from_java(args.java_file, args.output_type)
        print(f"✓ Generated: {output_path}")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
