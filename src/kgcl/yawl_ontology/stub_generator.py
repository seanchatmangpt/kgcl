"""Generate Python implementation stubs from YAWL ontology analysis.

Uses ontology to create type-safe Python stubs that match Java API surface,
enabling systematic porting with guaranteed API parity.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from kgcl.yawl_ontology.explorer import MethodSignature, YawlOntologyExplorer


@dataclass
class PythonStub:
    """Generated Python stub for a Java class."""

    class_name: str
    module_path: str
    imports: list[str]
    methods: list[str]
    docstring: str


class StubGenerator:
    """Generate Python stubs from YAWL ontology."""

    # Java -> Python type mapping
    TYPE_MAP = {
        "void": "None",
        "String": "str",
        "int": "int",
        "long": "int",
        "boolean": "bool",
        "double": "float",
        "List": "list",
        "Set": "set",
        "Map": "dict",
        "Collection": "list",
        "Object": "object",
    }

    def __init__(self, explorer: YawlOntologyExplorer) -> None:
        """Initialize stub generator.

        Parameters
        ----------
        explorer : YawlOntologyExplorer
            Ontology explorer instance
        """
        self.explorer = explorer

    def _map_type(self, java_type: str) -> str:
        """Map Java type to Python type hint."""
        # Handle generics (List<String> -> list[str])
        if "<" in java_type:
            base = java_type.split("<")[0]
            inner = java_type.split("<")[1].split(">")[0]
            base_py = self.TYPE_MAP.get(base, base)
            inner_py = self.TYPE_MAP.get(inner, inner)
            return f"{base_py}[{inner_py}]"

        return self.TYPE_MAP.get(java_type, java_type)

    def _extract_parameters_from_signature(self, full_signature: str) -> str:
        """Extract parameter portion from full Java signature.

        The ontology provides full Java signatures like:
        - "void addRunner(YNetRunner runner, YSpecification spec)"
        - "String getValue()"
        - "boolean check(String id, int count)"

        This method extracts just the parameter portion.

        Parameters
        ----------
        full_signature : str
            Full Java method signature

        Returns
        -------
        str
            Parameter portion (e.g., "YNetRunner runner, YSpecification spec")
            Empty string if no parameters

        Examples
        --------
        >>> self._extract_parameters_from_signature("void addRunner(YNetRunner runner)")
        "YNetRunner runner"
        >>> self._extract_parameters_from_signature("String getValue()")
        ""
        """
        # Match content inside parentheses
        match = re.search(r"\(([^)]*)\)", full_signature)
        return match.group(1).strip() if match else ""

    def _parse_parameters(self, params_str: str) -> list[tuple[str, str]]:
        """Parse Java parameter string into (type, name) tuples."""
        if not params_str.strip():
            return []

        params = []
        for param in params_str.split(","):
            param = param.strip()
            if not param:
                continue

            parts = param.rsplit(" ", 1)
            if len(parts) == 2:
                param_type, param_name = parts
                py_type = self._map_type(param_type.strip())
                params.append((py_type, param_name.strip()))

        return params

    def generate_method_stub(self, method: MethodSignature) -> str:
        """Generate Python method stub from Java method signature.

        Parameters
        ----------
        method : MethodSignature
            Java method signature

        Returns
        -------
        str
            Python method definition
        """
        # Extract parameters from full signature if it looks like a full signature
        # (contains return type and parentheses)
        params_str = method.parameters
        if "(" in params_str and ")" in params_str:
            params_str = self._extract_parameters_from_signature(params_str)

        params = self._parse_parameters(params_str)
        return_type = self._map_type(method.return_type)

        # Build parameter list
        param_list = ["self"]
        for py_type, name in params:
            param_list.append(f"{name}: {py_type}")

        params_str = ", ".join(param_list)

        # Generate method body
        java_sig = method.parameters if method.parameters else f"{method.return_type} {method.name}(...)"
        lines = [
            f"    def {method.name}({params_str}) -> {return_type}:",
            f'        """TODO: Implement {method.name}.',
            "",
            f"        Java signature: {java_sig}",
            '        """',
        ]

        if return_type == "None":
            lines.append("        pass")
        elif return_type == "bool":
            lines.append("        return False")
        elif return_type in ("int", "float"):
            lines.append("        return 0")
        elif return_type == "str":
            lines.append('        return ""')
        elif return_type.startswith("list"):
            lines.append("        return []")
        elif return_type.startswith("dict"):
            lines.append("        return {}")
        else:
            lines.append("        raise NotImplementedError")

        return "\n".join(lines)

    def generate_class_stub(self, class_name: str, package: str = "kgcl.yawl") -> PythonStub:
        """Generate complete Python class stub.

        Parameters
        ----------
        class_name : str
            Java class name
        package : str
            Python package name

        Returns
        -------
        PythonStub
            Complete Python stub
        """
        methods = self.explorer.get_class_methods(class_name)

        # Generate module path
        module_path = f"{package}.{class_name.lower()}"

        # Generate imports
        imports = ["from __future__ import annotations", "", "from typing import Any"]

        # Generate method stubs
        method_stubs = []
        for method in methods:
            stub = self.generate_method_stub(method)
            method_stubs.append(stub)

        # Generate class docstring
        docstring = f'''"""Python implementation of YAWL {class_name}.

Ported from Java YAWL v5.2 using ontology analysis.
Total methods: {len(methods)}
"""'''

        return PythonStub(
            class_name=class_name, module_path=module_path, imports=imports, methods=method_stubs, docstring=docstring
        )

    def write_stub_file(self, stub: PythonStub, output_dir: Path) -> Path:
        """Write Python stub to file.

        Parameters
        ----------
        stub : PythonStub
            Generated stub
        output_dir : Path
            Output directory

        Returns
        -------
        Path
            Path to written file
        """
        output_file = output_dir / f"{stub.class_name.lower()}.py"
        output_dir.mkdir(parents=True, exist_ok=True)

        lines = []
        lines.extend(stub.imports)
        lines.append("")
        lines.append("")
        lines.append(f"class {stub.class_name}:")
        lines.append(f"    {stub.docstring}")
        lines.append("")

        for method in stub.methods:
            lines.append(method)
            lines.append("")

        content = "\n".join(lines)
        output_file.write_text(content)

        return output_file

    def generate_core_engine_stubs(self, output_dir: Path) -> list[Path]:
        """Generate stubs for core YAWL engine classes.

        Parameters
        ----------
        output_dir : Path
            Output directory for stubs

        Returns
        -------
        list[Path]
            List of generated stub files
        """
        core_classes = ["YEngine", "YWorkItem", "YSpecification", "YNet", "YTask", "YDecomposition", "YCondition"]

        generated = []
        for cls in core_classes:
            try:
                stub = self.generate_class_stub(cls)
                output_file = self.write_stub_file(stub, output_dir)
                generated.append(output_file)
                print(f"✓ Generated {cls}: {output_file}")
            except Exception as e:
                print(f"✗ Failed to generate {cls}: {e}")

        return generated
