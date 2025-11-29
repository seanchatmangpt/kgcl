"""Java source code parser using javalang.

Extracts structural information from Java files: packages, classes,
methods, fields, and javadoc comments.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import javalang


@dataclass(frozen=True)
class MethodInfo:
    """Method metadata extracted from Java source."""

    name: str
    return_type: str
    parameters: list[str] = field(default_factory=list)
    modifiers: set[str] = field(default_factory=set)
    javadoc: str = ""

    @property
    def signature(self) -> str:
        """Generate method signature string."""
        params = ", ".join(self.parameters)
        return f"{self.return_type} {self.name}({params})"

    @property
    def clean_name(self) -> str:
        """URI-safe method name."""
        return self.name.replace("<", "_").replace(">", "_").replace(",", "_")


@dataclass(frozen=True)
class ClassInfo:
    """Class metadata extracted from Java source."""

    name: str
    package: str
    file_path: str
    modifiers: set[str] = field(default_factory=set)
    javadoc: str = ""
    methods: list[MethodInfo] = field(default_factory=list)
    fields: list[str] = field(default_factory=list)
    extends: str | None = None
    implements: list[str] = field(default_factory=list)

    @property
    def clean_name(self) -> str:
        """URI-safe class name."""
        return self.name.replace("<", "_").replace(">", "_").replace(",", "_")

    @property
    def fully_qualified_name(self) -> str:
        """Full class name including package."""
        return f"{self.package}.{self.name}"


class JavaParser:
    """Parse Java source files and extract structural metadata."""

    def parse_file(self, file_path: Path) -> list[ClassInfo]:
        """Parse a Java file and extract class information.

        Parameters
        ----------
        file_path : Path
            Path to Java source file

        Returns
        -------
        list[ClassInfo]
            List of classes found in the file
        """
        source_code = file_path.read_text(encoding="utf-8")
        try:
            tree = javalang.parse.parse(source_code)
        except javalang.parser.JavaSyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return []

        package_name = tree.package.name if tree.package else "default"
        classes = []

        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            class_info = self._extract_class_info(node, package_name, str(file_path))
            classes.append(class_info)

        return classes

    def _extract_class_info(self, node: javalang.tree.ClassDeclaration, package: str, file_path: str) -> ClassInfo:
        """Extract class information from AST node."""
        methods = []
        fields = []

        for member in node.body:
            if isinstance(member, javalang.tree.MethodDeclaration):
                methods.append(self._extract_method_info(member))
            elif isinstance(member, javalang.tree.FieldDeclaration):
                fields.extend(self._extract_field_names(member))

        javadoc = self._clean_javadoc(node.documentation) if node.documentation else ""

        return ClassInfo(
            name=node.name,
            package=package,
            file_path=file_path,
            modifiers=set(node.modifiers) if node.modifiers else set(),
            javadoc=javadoc,
            methods=methods,
            fields=fields,
            extends=node.extends.name if node.extends else None,
            implements=[impl.name for impl in node.implements] if node.implements else [],
        )

    def _extract_method_info(self, node: javalang.tree.MethodDeclaration) -> MethodInfo:
        """Extract method information from AST node."""
        return_type = node.return_type.name if node.return_type else "void"
        parameters = []

        if node.parameters:
            for param in node.parameters:
                param_type = param.type.name if hasattr(param.type, "name") else str(param.type)
                parameters.append(f"{param_type} {param.name}")

        javadoc = self._clean_javadoc(node.documentation) if node.documentation else ""

        return MethodInfo(
            name=node.name,
            return_type=return_type,
            parameters=parameters,
            modifiers=set(node.modifiers) if node.modifiers else set(),
            javadoc=javadoc,
        )

    def _extract_field_names(self, node: javalang.tree.FieldDeclaration) -> list[str]:
        """Extract field names from field declaration."""
        return [declarator.name for declarator in node.declarators]

    def _clean_javadoc(self, doc: str) -> str:
        """Clean and normalize javadoc comments."""
        if not doc:
            return ""
        cleaned = re.sub(r"/\*\*|\*/|\*", "", doc)
        cleaned = re.sub(r"\n\s+", " ", cleaned)
        cleaned = cleaned.strip()
        # Escape special characters for Turtle
        cleaned = cleaned.replace("\\", "\\\\")  # Escape backslashes first
        cleaned = cleaned.replace('"', '\\"')  # Escape quotes
        cleaned = cleaned.replace("\n", " ")  # Replace newlines
        cleaned = cleaned.replace("\r", "")  # Remove carriage returns
        return cleaned[:500]  # Truncate for sanity
