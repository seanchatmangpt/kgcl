"""Semantic Java parser using javalang.

This module extracts semantic metadata from Java source files, including classes,
methods, fields, annotations, and type information.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import javalang


@dataclass(frozen=True)
class JavaField:
    """Represents a Java class field.

    Parameters
    ----------
    name : str
        Field name
    type : str
        Field type (Java type string)
    modifiers : list[str]
        Access modifiers (public, private, static, final, etc.)
    annotations : list[str]
        Field annotations
    javadoc : str | None
        Javadoc comment if present
    """

    name: str
    type: str
    modifiers: list[str]
    annotations: list[str]
    javadoc: str | None


@dataclass(frozen=True)
class JavaMethod:
    """Represents a Java method.

    Parameters
    ----------
    name : str
        Method name
    return_type : str
        Return type (Java type string)
    parameters : list[tuple[str, str]]
        List of (parameter_name, parameter_type) tuples
    modifiers : list[str]
        Access modifiers (public, private, static, etc.)
    annotations : list[str]
        Method annotations
    javadoc : str | None
        Javadoc comment if present
    body : str
        Method body source code
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
    """Represents a Java class with full semantic metadata.

    Parameters
    ----------
    name : str
        Class name
    package : str
        Package declaration
    extends : str | None
        Parent class if present
    implements : list[str]
        Implemented interfaces
    fields : list[JavaField]
        Class fields
    methods : list[JavaMethod]
        Class methods
    modifiers : list[str]
        Class modifiers (public, abstract, final, etc.)
    annotations : list[str]
        Class annotations
    javadoc : str | None
        Javadoc comment if present
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


class JavaParseError(Exception):
    """Raised when Java parsing fails."""

    pass


class JavaParser:
    """Parse Java source files and extract semantic metadata."""

    def parse_file(self, java_file: Path) -> JavaClass:
        """Parse Java file and extract semantic metadata."""
        if not java_file.exists():
            raise FileNotFoundError(f"Java file not found: {java_file}")

        try:
            content = java_file.read_text(encoding="utf-8")
            tree = javalang.parse.parse(content)
        except javalang.parser.JavaSyntaxError as e:
            raise JavaParseError(f"Failed to parse {java_file}: {e}") from e

        package = tree.package.name if tree.package else ""
        imports = [imp.path for imp in tree.imports] if tree.imports else []

        classes = [
            node
            for path, node in tree.filter(javalang.tree.ClassDeclaration)
            if isinstance(node, javalang.tree.ClassDeclaration)
        ]

        if not classes:
            raise JavaParseError(f"No class declaration found in {java_file}")

        if len(classes) > 1:
            public_classes = [c for c in classes if "public" in (c.modifiers or [])]
            primary_class = public_classes[0] if public_classes else classes[0]
        else:
            primary_class = classes[0]

        class_name = primary_class.name
        modifiers = list(primary_class.modifiers) if primary_class.modifiers else []
        extends = primary_class.extends.name if primary_class.extends else None
        implements = (
            [impl.name for impl in primary_class.implements]
            if primary_class.implements
            else []
        )
        annotations = self._extract_annotations(primary_class)
        javadoc = self._extract_javadoc(primary_class)
        fields = self._extract_fields(primary_class)
        methods = self._extract_methods(primary_class, content)

        return JavaClass(
            name=class_name,
            package=package,
            extends=extends,
            implements=implements,
            fields=fields,
            methods=methods,
            modifiers=modifiers,
            annotations=annotations,
            javadoc=javadoc,
            imports=imports,
        )

    def _extract_fields(self, class_node: Any) -> list[JavaField]:
        """Extract field declarations from class."""
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

    def _extract_methods(self, class_node: Any, source: str) -> list[JavaMethod]:
        """Extract method declarations from class."""
        methods = []
        for method in class_node.methods:
            return_type = (
                self._format_type(method.return_type) if method.return_type else "void"
            )
            modifiers = list(method.modifiers) if method.modifiers else []
            annotations = self._extract_annotations(method)

            parameters = []
            if method.parameters:
                for param in method.parameters:
                    param_type = self._format_type(param.type)
                    parameters.append((param.name, param_type))

            body = "# Method body from Java source"

            methods.append(
                JavaMethod(
                    name=method.name,
                    return_type=return_type,
                    parameters=parameters,
                    modifiers=modifiers,
                    annotations=annotations,
                    javadoc=self._extract_javadoc(method),
                    body=body,
                )
            )
        return methods

    def _extract_annotations(self, node: Any) -> list[str]:
        """Extract annotations from a node."""
        if not hasattr(node, "annotations") or not node.annotations:
            return []
        return [ann.name for ann in node.annotations]

    def _extract_javadoc(self, node: Any) -> str | None:
        """Extract Javadoc comment from a node."""
        if hasattr(node, "documentation") and node.documentation:
            return str(node.documentation)
        return None

    def _format_type(self, type_node: Any) -> str:
        """Format a type node as a string."""
        if isinstance(type_node, javalang.tree.ReferenceType):
            name = str(type_node.name)

            if type_node.arguments:
                args = ", ".join(
                    self._format_type(arg.type) for arg in type_node.arguments
                )
                return f"{name}<{args}>"

            if type_node.dimensions:
                return f"{name}[]" * len(type_node.dimensions)

            return name
        elif isinstance(type_node, javalang.tree.BasicType):
            return str(type_node.name)
        else:
            return str(type_node)
