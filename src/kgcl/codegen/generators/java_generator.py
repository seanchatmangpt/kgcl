"""Java to Python code generator using unified framework.

Generates Python client code from Java service classes, including:
- Type mapping from Java to Python
- Method transformation
- Test generation
- Documentation generation
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import javalang

from kgcl.codegen.base.generator import BaseGenerator


@dataclass(frozen=True)
class JavaField:
    """Java class field metadata.

    Parameters
    ----------
    name : str
        Field name
    type : str
        Field type (Java type string)
    modifiers : list[str]
        Access modifiers
    annotations : list[str]
        Field annotations
    javadoc : str | None
        Javadoc comment
    """

    name: str
    type: str
    modifiers: list[str]
    annotations: list[str]
    javadoc: str | None


@dataclass(frozen=True)
class JavaMethod:
    """Java method metadata.

    Parameters
    ----------
    name : str
        Method name
    return_type : str
        Return type
    parameters : list[tuple[str, str]]
        (parameter_name, parameter_type) tuples
    modifiers : list[str]
        Access modifiers
    annotations : list[str]
        Method annotations
    javadoc : str | None
        Javadoc comment
    body : str
        Method body source
    """

    name: str
    return_type: str
    parameters: list[tuple[str, str]]
    modifiers: list[str]
    annotations: list[str]
    javadoc: str | None
    body: str


@dataclass(frozen=True)
class JavaClass:
    """Java class metadata.

    Parameters
    ----------
    name : str
        Class name
    package : str
        Package declaration
    extends : str | None
        Parent class
    implements : list[str]
        Implemented interfaces
    fields : list[JavaField]
        Class fields
    methods : list[JavaMethod]
        Class methods
    modifiers : list[str]
        Class modifiers
    annotations : list[str]
        Class annotations
    javadoc : str | None
        Javadoc comment
    imports : list[str]
        Import statements
    """

    name: str
    package: str
    extends: str | None
    implements: list[str]
    fields: list[JavaField]
    methods: list[JavaMethod]
    modifiers: list[str]
    annotations: list[str]
    javadoc: str | None
    imports: list[str]


@dataclass(frozen=True)
class PythonMethod:
    """Python method generated from Java.

    Parameters
    ----------
    name : str
        Method name (snake_case)
    return_type : str
        Python return type hint
    parameters : list[tuple[str, str]]
        (param_name, param_type) tuples
    docstring : str | None
        Method docstring
    is_async : bool
        Whether method is async
    """

    name: str
    return_type: str
    parameters: list[tuple[str, str]]
    docstring: str | None
    is_async: bool = False


@dataclass(frozen=True)
class PythonClass:
    """Python class generated from Java.

    Parameters
    ----------
    name : str
        Class name
    module_path : str
        Python module path
    methods : list[PythonMethod]
        Class methods
    imports : list[str]
        Required imports
    docstring : str | None
        Class docstring
    base_class : str | None
        Base class name
    """

    name: str
    module_path: str
    methods: list[PythonMethod]
    imports: list[str]
    docstring: str | None
    base_class: str | None = None


class JavaParseError(Exception):
    """Raised when Java parsing fails."""

    pass


class JavaParser:
    """Parse Java source files using javalang."""

    def parse(self, input_path: Path) -> JavaClass:
        """Parse Java file and extract metadata.

        Parameters
        ----------
        input_path : Path
            Path to Java source file

        Returns
        -------
        JavaClass
            Parsed Java class metadata

        Raises
        ------
        FileNotFoundError
            If Java file doesn't exist
        JavaParseError
            If parsing fails
        """
        if not input_path.exists():
            msg = f"Java file not found: {input_path}"
            raise FileNotFoundError(msg)

        try:
            content = input_path.read_text(encoding="utf-8")
            tree = javalang.parse.parse(content)
        except javalang.parser.JavaSyntaxError as e:
            msg = f"Failed to parse {input_path}: {e}"
            raise JavaParseError(msg) from e

        package = tree.package.name if tree.package else ""
        imports = [imp.path for imp in tree.imports] if tree.imports else []

        # Support both classes and enums
        classes = [
            node
            for _, node in tree.filter(javalang.tree.ClassDeclaration)
            if isinstance(node, javalang.tree.ClassDeclaration)
        ]

        # Also check for enums
        enums = [
            node
            for _, node in tree.filter(javalang.tree.EnumDeclaration)
            if isinstance(node, javalang.tree.EnumDeclaration)
        ]

        if not classes and not enums:
            msg = f"No class or enum declaration found in {input_path}"
            raise JavaParseError(msg)

        # Prefer classes over enums, but support both
        all_declarations = classes + enums

        # Find primary declaration (public class/enum or first)
        if len(all_declarations) > 1:
            public_declarations = [d for d in all_declarations if "public" in (d.modifiers or [])]
            primary_decl = public_declarations[0] if public_declarations else all_declarations[0]
        else:
            primary_decl = all_declarations[0]

        # For enums, handle differently (no extends/implements)
        extends_name = None
        implements_list = []
        if hasattr(primary_decl, "extends") and primary_decl.extends:
            extends_name = primary_decl.extends.name
        if hasattr(primary_decl, "implements") and primary_decl.implements:
            implements_list = [impl.name for impl in primary_decl.implements]

        return JavaClass(
            name=primary_decl.name,
            package=package,
            extends=extends_name,
            implements=implements_list,
            fields=self._extract_fields(primary_decl),
            methods=self._extract_methods(primary_decl),
            modifiers=list(primary_decl.modifiers) if primary_decl.modifiers else [],
            annotations=self._extract_annotations(primary_decl),
            javadoc=self._extract_javadoc(primary_decl),
            imports=imports,
        )

    def _extract_fields(self, class_node: Any) -> list[JavaField]:
        """Extract field declarations."""
        fields = []
        for field_decl in class_node.fields:
            field_type = self._format_type(field_decl.type)
            modifiers = list(field_decl.modifiers) if field_decl.modifiers else []
            annotations = self._extract_annotations(field_decl)

            for declarator in field_decl.declarators:
                fields.append(
                    JavaField(
                        name=declarator.name,
                        type=field_type,
                        modifiers=modifiers,
                        annotations=annotations,
                        javadoc=self._extract_javadoc(field_decl),
                    )
                )
        return fields

    def _extract_methods(self, class_node: Any) -> list[JavaMethod]:
        """Extract method declarations."""
        methods = []
        for method in class_node.methods:
            return_type = self._format_type(method.return_type) if method.return_type else "void"
            modifiers = list(method.modifiers) if method.modifiers else []
            annotations = self._extract_annotations(method)

            parameters = []
            if method.parameters:
                for param in method.parameters:
                    param_type = self._format_type(param.type)
                    parameters.append((param.name, param_type))

            methods.append(
                JavaMethod(
                    name=method.name,
                    return_type=return_type,
                    parameters=parameters,
                    modifiers=modifiers,
                    annotations=annotations,
                    javadoc=self._extract_javadoc(method),
                    body="# Method body from Java source",
                )
            )
        return methods

    @staticmethod
    def _extract_annotations(node: Any) -> list[str]:
        """Extract annotations from node."""
        if not hasattr(node, "annotations") or not node.annotations:
            return []
        return [ann.name for ann in node.annotations]

    @staticmethod
    def _extract_javadoc(node: Any) -> str | None:
        """Extract Javadoc comment."""
        if hasattr(node, "documentation") and node.documentation:
            return str(node.documentation)
        return None

    def _format_type(self, type_node: Any) -> str:
        """Format type node as string."""
        if isinstance(type_node, javalang.tree.ReferenceType):
            name = str(type_node.name)

            if type_node.arguments:
                args = ", ".join(self._format_type(arg.type) for arg in type_node.arguments)
                return f"{name}<{args}>"

            if type_node.dimensions:
                return f"{name}[]" * len(type_node.dimensions)

            return name
        if isinstance(type_node, javalang.tree.BasicType):
            return str(type_node.name)
        return str(type_node)


class TypeMapper:
    """Map Java types to Python type hints."""

    # Comprehensive Java to Python type mapping
    JAVA_TO_PYTHON: dict[str, str] = {
        # Primitives
        "byte": "int",
        "short": "int",
        "int": "int",
        "long": "int",
        "float": "float",
        "double": "float",
        "boolean": "bool",
        "char": "str",
        "void": "None",
        # Boxed primitives
        "Byte": "int",
        "Short": "int",
        "Integer": "int",
        "Long": "int",
        "Float": "float",
        "Double": "float",
        "Boolean": "bool",
        "Character": "str",
        # Common types
        "String": "str",
        "Object": "Any",
        "Date": "datetime",
        "Timestamp": "datetime",
        "BigDecimal": "Decimal",
        "BigInteger": "int",
        "UUID": "str",
        # Collections
        "List": "list[Any]",
        "Set": "set[Any]",
        "Map": "dict[str, Any]",
        "Collection": "list[Any]",
        "ArrayList": "list[Any]",
        "HashSet": "set[Any]",
        "HashMap": "dict[str, Any]",
        "LinkedList": "list[Any]",
        "TreeSet": "set[Any]",
        "TreeMap": "dict[str, Any]",
        # YAWL-specific
        "YSpecificationID": "str",
        "YTask": "dict[str, Any]",
        "YNet": "dict[str, Any]",
        "YCondition": "dict[str, Any]",
        "Element": "Any",
        "Document": "Any",
    }

    def __init__(self) -> None:
        """Initialize type mapper."""
        self.type_map = self.JAVA_TO_PYTHON.copy()

    def map_type(self, java_type: str) -> str:
        """Convert Java type to Python type hint.

        Parameters
        ----------
        java_type : str
            Java type string

        Returns
        -------
        str
            Python type hint
        """
        # Handle arrays
        if "[]" in java_type:
            base_type = java_type.replace("[]", "")
            mapped_base = self._map_simple_type(base_type)
            return f"list[{mapped_base}]"

        # Handle generics
        if "<" in java_type and ">" in java_type:
            return self._map_generic_type(java_type)

        return self._map_simple_type(java_type)

    def _map_simple_type(self, java_type: str) -> str:
        """Map simple (non-generic) Java type."""
        java_type = java_type.strip()

        if java_type in self.type_map:
            return self.type_map[java_type]

        # Handle fully qualified names
        if "." in java_type:
            simple_name = java_type.split(".")[-1]
            if simple_name in self.type_map:
                return self.type_map[simple_name]

        return "Any"

    def _map_generic_type(self, java_type: str) -> str:
        """Map generic Java type."""
        match = re.match(r"(\w+)<(.+)>", java_type.strip())
        if not match:
            return self._map_simple_type(java_type)

        base_type = match.group(1)
        type_args = match.group(2)

        python_base = self._get_generic_base(base_type)
        python_args = self._parse_type_arguments(type_args)

        return f"{python_base}[{', '.join(python_args)}]"

    @staticmethod
    def _get_generic_base(base_type: str) -> str:
        """Get Python base type for generic."""
        mapping = {
            "List": "list",
            "ArrayList": "list",
            "LinkedList": "list",
            "Set": "set",
            "HashSet": "set",
            "TreeSet": "set",
            "Map": "dict",
            "HashMap": "dict",
            "TreeMap": "dict",
            "Collection": "list",
            "Optional": "Optional",
        }
        return mapping.get(base_type, "Any")

    def _parse_type_arguments(self, type_args: str) -> list[str]:
        """Parse and map generic type arguments."""
        args = []
        current = ""
        depth = 0

        for char in type_args:
            if char == "<":
                depth += 1
                current += char
            elif char == ">":
                depth -= 1
                current += char
            elif char == "," and depth == 0:
                args.append(current.strip())
                current = ""
            else:
                current += char

        if current.strip():
            args.append(current.strip())

        return [self.map_type(arg) for arg in args]

    def add_custom_mapping(self, java_type: str, python_type: str) -> None:
        """Add custom type mapping.

        Parameters
        ----------
        java_type : str
            Java type name
        python_type : str
            Python type hint
        """
        self.type_map[java_type] = python_type


class JavaGenerator(BaseGenerator[JavaClass]):  # noqa: UP046
    """Generate Python client code from Java services.

    This generator parses Java source files and generates equivalent
    Python client code with type hints, docstrings, and tests.

    Examples
    --------
    >>> from pathlib import Path
    >>> generator = JavaGenerator(template_dir=Path("templates/python"), output_dir=Path("src/kgcl/yawl_ui"))
    >>> result = generator.generate(Path("java/DynFormService.java"))
    """

    def __init__(
        self, template_dir: Path, output_dir: Path, dry_run: bool = False, generate_tests: bool = True
    ) -> None:
        """Initialize Java generator.

        Parameters
        ----------
        template_dir : Path
            Directory containing templates
        output_dir : Path
            Output directory for generated code
        dry_run : bool
            If True, don't write files
        generate_tests : bool
            If True, generate test files
        """
        super().__init__(template_dir, output_dir, dry_run)
        self.generate_tests = generate_tests
        self._parser = JavaParser()
        self.mapper = TypeMapper()

    @property
    def parser(self) -> JavaParser:
        """Return Java parser instance."""
        return self._parser

    def _transform(self, metadata: JavaClass, **kwargs: Any) -> dict[str, Any]:
        """Transform Java class to Python class context.

        Parameters
        ----------
        metadata : JavaClass
            Parsed Java class
        **kwargs : Any
            Additional options

        Returns
        -------
        dict[str, Any]
            Template context
        """
        python_class = self._map_class(metadata)

        return {
            "class_name": python_class.name,
            "module_path": python_class.module_path,
            "methods": python_class.methods,
            "imports": python_class.imports,
            "docstring": python_class.docstring,
            "base_class": python_class.base_class,
        }

    def _map_class(self, java_class: JavaClass) -> PythonClass:
        """Map Java class to Python class."""
        methods = []
        for java_method in java_class.methods:
            python_name = self._to_snake_case(java_method.name)
            python_return = self.mapper.map_type(java_method.return_type)
            python_params = [
                (self._to_snake_case(name), self.mapper.map_type(param_type))
                for name, param_type in java_method.parameters
            ]
            docstring = self._generate_docstring(java_method, python_params)

            methods.append(
                PythonMethod(name=python_name, return_type=python_return, parameters=python_params, docstring=docstring)
            )

        module_path = self._package_to_module(java_class.package)
        class_docstring = self._generate_class_docstring(java_class)
        imports = self._collect_imports(java_class, methods)

        return PythonClass(
            name=java_class.name, module_path=module_path, methods=methods, imports=imports, docstring=class_docstring
        )

    def _get_template_name(self, metadata: JavaClass, **kwargs: Any) -> str:
        """Get template file name."""
        return "python_client.py.j2"

    def _get_output_path(self, metadata: JavaClass, **kwargs: Any) -> Path:
        """Get output file path."""
        python_class = self._map_class(metadata)
        module_parts = python_class.module_path.split(".")
        file_name = f"{self._to_snake_case(python_class.name)}.py"
        return self.output_dir / Path(*module_parts) / file_name

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert CamelCase to snake_case."""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
        return s2.lower()

    @staticmethod
    def _package_to_module(java_package: str) -> str:
        """Convert Java package to Python module path."""
        if not java_package:
            return "kgcl.yawl_ui"

        if java_package.startswith("org.yawlfoundation.yawl.ui."):
            suffix = java_package.replace("org.yawlfoundation.yawl.ui.", "")
            return f"kgcl.yawl_ui.{suffix}"

        return "kgcl.yawl_ui"

    def _collect_imports(self, java_class: JavaClass, methods: list[PythonMethod]) -> list[str]:
        """Collect required Python imports."""
        imports = {"from __future__ import annotations"}

        for method in methods:
            if "Any" in method.return_type:
                imports.add("from typing import Any")
                break
            for _, param_type in method.parameters:
                if "Any" in param_type:
                    imports.add("from typing import Any")
                    break

        return sorted(imports)

    def _generate_docstring(self, java_method: JavaMethod, python_params: list[tuple[str, str]]) -> str:
        """Generate NumPy-style docstring."""
        lines = []

        if java_method.javadoc:
            summary = java_method.javadoc.split(".")[0].strip()
            lines.append(summary + ".")
        else:
            lines.append(f"Execute {java_method.name} operation.")

        if python_params:
            lines.append("")
            lines.append("Parameters")
            lines.append("----------")
            for param_name, param_type in python_params:
                lines.append(f"{param_name} : {param_type}")
                lines.append(f"    {param_name.replace('_', ' ').capitalize()}")

        if java_method.return_type != "void":
            lines.append("")
            lines.append("Returns")
            lines.append("-------")
            lines.append(self.mapper.map_type(java_method.return_type))
            lines.append("    Operation result")

        return "\n".join(lines)

    @staticmethod
    def _generate_class_docstring(java_class: JavaClass) -> str:
        """Generate class docstring."""
        if java_class.javadoc:
            return str(java_class.javadoc)
        return f"Python client for {java_class.name} Java service."


__all__ = [
    "JavaClass",
    "JavaMethod",
    "JavaField",
    "PythonClass",
    "PythonMethod",
    "JavaGenerator",
    "JavaParser",
    "TypeMapper",
]
