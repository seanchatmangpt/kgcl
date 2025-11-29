"""Main code generator orchestrator.

This module coordinates Java parsing, type mapping, and template rendering
to generate Python client code from Java services.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codegen.java_parser import JavaClass, JavaParser
from codegen.template_engine import TemplateEngine
from codegen.type_mapper import TypeMapper


@dataclass(frozen=True)
class PythonMethod:
    """Represents a Python method generated from Java.

    Parameters
    ----------
    name : str
        Method name (snake_case)
    return_type : str
        Python return type hint
    parameters : list[tuple[str, str]]
        List of (param_name, param_type) tuples
    docstring : str | None
        Method docstring
    is_async : bool
        Whether method should be async
    """

    name: str
    return_type: str
    parameters: list[tuple[str, str]]
    docstring: str | None
    is_async: bool = False


@dataclass(frozen=True)
class PythonClass:
    """Represents a Python class generated from Java.

    Parameters
    ----------
    name : str
        Class name
    module_path : str
        Python module path (e.g., "kgcl.yawl_ui.clients")
    methods : list[PythonMethod]
        Class methods
    imports : list[str]
        Required imports
    docstring : str | None
        Class docstring
    base_class : str | None
        Base class name if present
    """

    name: str
    module_path: str
    methods: list[PythonMethod]
    imports: list[str]
    docstring: str | None
    base_class: str | None = None


class CodeGenerator:
    """Generate Python client code from Java services.

    Orchestrates the full code generation pipeline:
    1. Parse Java source files
    2. Map Java types to Python types
    3. Generate Python code from templates
    4. Generate corresponding test files
    """

    def __init__(self, template_dir: Path, output_dir: Path) -> None:
        """Initialize code generator.

        Parameters
        ----------
        template_dir : Path
            Directory containing Jinja2 templates
        output_dir : Path
            Root directory for generated Python code

        Raises
        ------
        FileNotFoundError
            If template directory doesn't exist
        """
        self.parser = JavaParser()
        self.mapper = TypeMapper()
        self.templates = TemplateEngine(template_dir)
        self.output_dir = output_dir

        # Ensure output directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_python_client(self, java_file: Path) -> Path:
        """Generate Python client from Java service.

        Parameters
        ----------
        java_file : Path
            Path to Java source file

        Returns
        -------
        Path
            Path to generated Python file

        Raises
        ------
        FileNotFoundError
            If Java file doesn't exist
        """
        # 1. Parse Java
        java_class = self.parser.parse_file(java_file)

        # 2. Map to Python class
        python_class = self._map_class(java_class)

        # 3. Render template
        code = self.templates.render(
            "python_client.py.jinja2",
            {
                "class_name": python_class.name,
                "module_path": python_class.module_path,
                "methods": python_class.methods,
                "imports": python_class.imports,
                "docstring": python_class.docstring,
                "base_class": python_class.base_class,
            },
        )

        # 4. Write file
        output_path = self._get_output_path(python_class)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(code)

        # 5. Generate tests
        test_path = self._generate_test_file(python_class, java_class)

        return output_path

    def _map_class(self, java_class: JavaClass) -> PythonClass:
        """Map Java class to Python class.

        Parameters
        ----------
        java_class : JavaClass
            Parsed Java class

        Returns
        -------
        PythonClass
            Mapped Python class
        """
        # Map methods
        methods = []
        for java_method in java_class.methods:
            # Convert method name to snake_case
            python_name = self._to_snake_case(java_method.name)

            # Map return type
            python_return = self.mapper.map_type(java_method.return_type)

            # Map parameters
            python_params = [
                (self._to_snake_case(name), self.mapper.map_type(param_type))
                for name, param_type in java_method.parameters
            ]

            # Generate docstring from Javadoc
            docstring = self._generate_docstring(java_method, python_params)

            methods.append(
                PythonMethod(
                    name=python_name,
                    return_type=python_return,
                    parameters=python_params,
                    docstring=docstring,
                )
            )

        # Determine module path from Java package
        module_path = self._package_to_module(java_class.package)

        # Generate class docstring
        class_docstring = self._generate_class_docstring(java_class)

        # Collect imports
        imports = self._collect_imports(java_class, methods)

        return PythonClass(
            name=java_class.name,
            module_path=module_path,
            methods=methods,
            imports=imports,
            docstring=class_docstring,
        )

    def _generate_test_file(self, python_class: PythonClass, java_class: JavaClass) -> Path:
        """Generate pytest test file for Python class.

        Parameters
        ----------
        python_class : PythonClass
            Generated Python class
        java_class : JavaClass
            Original Java class

        Returns
        -------
        Path
            Path to generated test file
        """
        test_code = self.templates.render(
            "pytest_test.py.jinja2",
            {
                "class_name": python_class.name,
                "module_path": python_class.module_path,
                "methods": python_class.methods,
            },
        )

        test_path = self._get_test_path(python_class)
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(test_code)

        return test_path

    def _get_output_path(self, python_class: PythonClass) -> Path:
        """Get output file path for Python class.

        Parameters
        ----------
        python_class : PythonClass
            Python class metadata

        Returns
        -------
        Path
            Output file path
        """
        # Convert module path to file path
        module_parts = python_class.module_path.split(".")
        file_name = f"{self._to_snake_case(python_class.name)}.py"

        return self.output_dir / Path(*module_parts) / file_name

    def _get_test_path(self, python_class: PythonClass) -> Path:
        """Get test file path for Python class.

        Parameters
        ----------
        python_class : PythonClass
            Python class metadata

        Returns
        -------
        Path
            Test file path
        """
        # Map src/ to tests/
        module_parts = python_class.module_path.split(".")
        if module_parts[0] == "src":
            module_parts[0] = "tests"

        file_name = f"test_{self._to_snake_case(python_class.name)}.py"

        return self.output_dir / Path(*module_parts) / file_name

    def _package_to_module(self, java_package: str) -> str:
        """Convert Java package to Python module path.

        Parameters
        ----------
        java_package : str
            Java package (e.g., "org.yawlfoundation.yawl.ui.dynform")

        Returns
        -------
        str
            Python module path (e.g., "kgcl.yawl_ui.dynform")
        """
        if not java_package:
            return "kgcl.yawl_ui"

        # Map org.yawlfoundation.yawl.ui.* to kgcl.yawl_ui.*
        if java_package.startswith("org.yawlfoundation.yawl.ui."):
            suffix = java_package.replace("org.yawlfoundation.yawl.ui.", "")
            return f"kgcl.yawl_ui.{suffix}"

        return "kgcl.yawl_ui"

    def _collect_imports(
        self, java_class: JavaClass, methods: list[PythonMethod]
    ) -> list[str]:
        """Collect required Python imports.

        Parameters
        ----------
        java_class : JavaClass
            Original Java class
        methods : list[PythonMethod]
            Generated Python methods

        Returns
        -------
        list[str]
            List of import statements
        """
        imports = set()

        # Standard library imports
        imports.add("from __future__ import annotations")

        # Check if Any is needed
        for method in methods:
            if "Any" in method.return_type:
                imports.add("from typing import Any")
                break
            for _, param_type in method.parameters:
                if "Any" in param_type:
                    imports.add("from typing import Any")
                    break

        return sorted(imports)

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert CamelCase to snake_case."""
        import re

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    def _generate_docstring(
        self, java_method: Any, python_params: list[tuple[str, str]]
    ) -> str:
        """Generate NumPy-style docstring from Java method.

        Parameters
        ----------
        java_method : Any
            Java method metadata
        python_params : list[tuple[str, str]]
            Python parameters

        Returns
        -------
        str
            NumPy-style docstring
        """
        lines = []

        # Add summary from Javadoc or generate from name
        if java_method.javadoc:
            # Extract first sentence from Javadoc
            summary = java_method.javadoc.split(".")[0].strip()
            lines.append(summary + ".")
        else:
            # Generate generic summary
            lines.append(f"Execute {java_method.name} operation.")

        # Add parameters section
        if python_params:
            lines.append("")
            lines.append("Parameters")
            lines.append("----------")
            for param_name, param_type in python_params:
                lines.append(f"{param_name} : {param_type}")
                lines.append(f"    {param_name.replace('_', ' ').capitalize()}")

        # Add returns section
        if java_method.return_type != "void":
            lines.append("")
            lines.append("Returns")
            lines.append("-------")
            lines.append(self.mapper.map_type(java_method.return_type))
            lines.append("    Operation result")

        return "\n".join(lines)

    def _generate_class_docstring(self, java_class: JavaClass) -> str:
        """Generate class docstring from Java class.

        Parameters
        ----------
        java_class : JavaClass
            Java class metadata

        Returns
        -------
        str
            Class docstring
        """
        if java_class.javadoc:
            return str(java_class.javadoc)

        return f"Python client for {java_class.name} Java service."
