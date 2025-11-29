"""Enhanced Java parser for delta detection.

Extends the base Java parser to extract:
- Method bodies (AST nodes)
- Call sites (method invocations)
- Exception patterns (throw/catch)
- Type information (parameter types, return types, field types)
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import javalang
from javalang.tree import (
    CatchClause,
    FieldDeclaration,
    ForStatement,
    ForEachStatement,
    IfStatement,
    Literal,
    MethodDeclaration,
    MethodInvocation,
    ThrowStatement,
    TryStatement,
    WhileStatement,
)


@dataclass(frozen=True)
class CallSite:
    """Represents a method call site."""

    caller_method: str
    callee_name: str
    callee_class: str | None
    arguments: list[str]
    line_number: int


@dataclass(frozen=True)
class ExceptionInfo:
    """Exception throwing or catching information."""

    exception_type: str
    is_thrown: bool
    is_caught: bool
    context: str  # method name where it occurs
    line_number: int


@dataclass(frozen=True)
class MethodBody:
    """Enhanced method information with body analysis."""

    name: str
    return_type: str
    parameters: list[str]
    modifiers: set[str]
    javadoc: str
    body_ast: Any  # javalang AST node
    body_text: str
    call_sites: list[CallSite] = field(default_factory=list)
    exceptions: list[ExceptionInfo] = field(default_factory=list)
    complexity: int = 0  # Cyclomatic complexity
    has_loops: bool = False
    has_recursion: bool = False


@dataclass(frozen=True)
class EnhancedClassInfo:
    """Enhanced class information with method bodies and dependencies."""

    name: str
    package: str
    file_path: str
    modifiers: set[str]
    javadoc: str
    methods: list[MethodBody] = field(default_factory=list)
    fields: list[str] = field(default_factory=list)
    field_types: dict[str, str] = field(default_factory=dict)
    extends: str | None = None
    implements: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    dependencies: set[str] = field(default_factory=set)  # Class names this class depends on


class EnhancedJavaParser:
    """Enhanced Java parser for delta detection analysis."""

    def __init__(self) -> None:
        """Initialize enhanced parser."""
        self.source_code: str = ""
        self.current_class: str = ""
        self.current_package: str = ""

    def parse_file(self, file_path: Path) -> list[EnhancedClassInfo]:
        """Parse a Java file and extract enhanced class information.

        Parameters
        ----------
        file_path : Path
            Path to Java source file

        Returns
        -------
        list[EnhancedClassInfo]
            List of enhanced class information
        """
        self.source_code = file_path.read_text(encoding="utf-8")
        try:
            tree = javalang.parse.parse(self.source_code)
        except javalang.parser.JavaSyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return []

        self.current_package = tree.package.name if tree.package else "default"
        imports = [imp.path for imp in tree.imports] if tree.imports else []

        classes = []
        for path, node in tree.filter(javalang.tree.ClassDeclaration):
            class_info = self._extract_enhanced_class_info(node, imports, str(file_path))
            classes.append(class_info)

        return classes

    def _extract_enhanced_class_info(
        self, node: javalang.tree.ClassDeclaration, imports: list[str], file_path: str
    ) -> EnhancedClassInfo:
        """Extract enhanced class information from AST node."""
        self.current_class = node.name

        methods = []
        fields = []
        field_types: dict[str, str] = {}

        for member in node.body:
            if isinstance(member, MethodDeclaration):
                method_body = self._extract_method_body(member)
                methods.append(method_body)
            elif isinstance(member, FieldDeclaration):
                field_names, types = self._extract_field_info(member)
                fields.extend(field_names)
                for field_name, field_type in zip(field_names, types):
                    field_types[field_name] = field_type

        javadoc = self._clean_javadoc(node.documentation) if node.documentation else ""

        # Extract dependencies from imports, fields, and method parameters
        dependencies = self._extract_dependencies(imports, field_types, methods)

        return EnhancedClassInfo(
            name=node.name,
            package=self.current_package,
            file_path=file_path,
            modifiers=set(node.modifiers) if node.modifiers else set(),
            javadoc=javadoc,
            methods=methods,
            fields=fields,
            field_types=field_types,
            extends=node.extends.name if node.extends else None,
            implements=[impl.name for impl in node.implements] if node.implements else [],
            imports=imports,
            dependencies=dependencies,
        )

    def _extract_method_body(self, node: MethodDeclaration) -> MethodBody:
        """Extract method body with call sites and exception patterns."""
        return_type = node.return_type.name if node.return_type else "void"
        parameters = []
        param_types: list[str] = []

        if node.parameters:
            for param in node.parameters:
                param_type = param.type.name if hasattr(param.type, "name") else str(param.type)
                param_types.append(param_type)
                parameters.append(f"{param_type} {param.name}")

        javadoc = self._clean_javadoc(node.documentation) if node.documentation else ""

        # Extract body text
        body_text = ""
        body_ast = None
        if node.body:
            body_ast = node.body
            # Extract body text from source
            start_line = node.position.line if hasattr(node, "position") and node.position else 0
            body_text = self._extract_body_text(node)

        # Extract call sites
        call_sites = self._extract_call_sites(node, node.name)

        # Extract exceptions
        exceptions = self._extract_exceptions(node, node.name)

        # Calculate complexity
        complexity = self._calculate_complexity(node)

        # Check for loops and recursion
        has_loops = self._has_loops(node)
        has_recursion = self._has_recursion(node, node.name)

        return MethodBody(
            name=node.name,
            return_type=return_type,
            parameters=parameters,
            modifiers=set(node.modifiers) if node.modifiers else set(),
            javadoc=javadoc,
            body_ast=body_ast,
            body_text=body_text,
            call_sites=call_sites,
            exceptions=exceptions,
            complexity=complexity,
            has_loops=has_loops,
            has_recursion=has_recursion,
        )

    def _extract_body_text(self, node: MethodDeclaration) -> str:
        """Extract method body text from source code."""
        if not node.body or not hasattr(node, "position"):
            return ""

        try:
            # Get line numbers for the method
            start_line = node.position.line if node.position else 0
            # Find the end of the method body
            lines = self.source_code.split("\n")
            brace_count = 0
            start_idx = 0
            end_idx = len(lines)

            # Find the opening brace
            for i, line in enumerate(lines[start_line - 1 :], start=start_line - 1):
                if "{" in line:
                    start_idx = i
                    brace_count = 1
                    break

            # Find the matching closing brace
            for i, line in enumerate(lines[start_idx + 1 :], start=start_idx + 1):
                brace_count += line.count("{") - line.count("}")
                if brace_count == 0:
                    end_idx = i + 1
                    break

            return "\n".join(lines[start_idx:end_idx])
        except Exception:
            return ""

    def _extract_call_sites(self, node: MethodDeclaration, method_name: str) -> list[CallSite]:
        """Extract all method call sites from method body."""
        call_sites: list[CallSite] = []

        def visit_call(node: Any) -> None:
            """Recursively visit AST nodes to find method calls."""
            if isinstance(node, MethodInvocation):
                callee_name = node.member if hasattr(node, "member") else ""
                callee_class = None
                if hasattr(node, "qualifier") and node.qualifier:
                    callee_class = str(node.qualifier)

                arguments = []
                if hasattr(node, "arguments") and node.arguments:
                    for arg in node.arguments:
                        if isinstance(arg, Literal):
                            arguments.append(str(arg.value))
                        else:
                            arguments.append(str(type(arg).__name__))

                line_number = node.position.line if hasattr(node, "position") and node.position else 0

                call_sites.append(
                    CallSite(
                        caller_method=method_name,
                        callee_name=callee_name,
                        callee_class=callee_class,
                        arguments=arguments,
                        line_number=line_number,
                    )
                )

            # Recursively visit child nodes
            for child in getattr(node, "children", []):
                if isinstance(child, (list, tuple)):
                    for item in child:
                        if hasattr(item, "__dict__"):
                            visit_call(item)
                elif hasattr(child, "__dict__"):
                    visit_call(child)

        if node.body:
            for stmt in node.body:
                visit_call(stmt)

        return call_sites

    def _extract_exceptions(self, node: MethodDeclaration, method_name: str) -> list[ExceptionInfo]:
        """Extract exception throwing and catching patterns."""
        exceptions: list[ExceptionInfo] = []

        def visit_exceptions(ast_node: Any) -> None:
            """Recursively visit AST nodes to find exceptions."""
            if isinstance(ast_node, ThrowStatement):
                exc_type = (
                    ast_node.expression.type.name
                    if hasattr(ast_node, "expression")
                    and hasattr(ast_node.expression, "type")
                    and hasattr(ast_node.expression.type, "name")
                    else "Exception"
                )
                line_number = (
                    ast_node.position.line if hasattr(ast_node, "position") and ast_node.position else 0
                )
                exceptions.append(
                    ExceptionInfo(
                        exception_type=exc_type,
                        is_thrown=True,
                        is_caught=False,
                        context=method_name,
                        line_number=line_number,
                    )
                )

            if isinstance(ast_node, TryStatement):
                if hasattr(ast_node, "catches") and ast_node.catches:
                    for catch in ast_node.catches:
                        if isinstance(catch, CatchClause):
                            exc_type = (
                                catch.parameter.type.name
                                if hasattr(catch, "parameter")
                                and hasattr(catch.parameter, "type")
                                and hasattr(catch.parameter.type, "name")
                                else "Exception"
                            )
                            line_number = (
                                catch.position.line
                                if hasattr(catch, "position") and catch.position
                                else 0
                            )
                            exceptions.append(
                                ExceptionInfo(
                                    exception_type=exc_type,
                                    is_thrown=False,
                                    is_caught=True,
                                    context=method_name,
                                    line_number=line_number,
                                )
                            )

            # Recursively visit children
            for child in getattr(ast_node, "children", []):
                if isinstance(child, (list, tuple)):
                    for item in child:
                        if hasattr(item, "__dict__"):
                            visit_exceptions(item)
                elif hasattr(child, "__dict__"):
                    visit_exceptions(child)

        if node.body:
            for stmt in node.body:
                visit_exceptions(stmt)

        return exceptions

    def _calculate_complexity(self, node: MethodDeclaration) -> int:
        """Calculate cyclomatic complexity of method."""
        complexity = 1  # Base complexity

        def count_branches(ast_node: Any) -> None:
            """Recursively count branch points."""
            nonlocal complexity
            if isinstance(ast_node, (IfStatement, WhileStatement, ForStatement, ForEachStatement)):
                complexity += 1
            # Recursively visit children
            for child in getattr(ast_node, "children", []):
                if isinstance(child, (list, tuple)):
                    for item in child:
                        if hasattr(item, "__dict__"):
                            count_branches(item)
                elif hasattr(child, "__dict__"):
                    count_branches(child)

        if node.body:
            for stmt in node.body:
                count_branches(stmt)

        return complexity

    def _has_loops(self, node: MethodDeclaration) -> bool:
        """Check if method contains loops."""
        has_loops = False

        def check_loops(ast_node: Any) -> None:
            """Recursively check for loops."""
            nonlocal has_loops
            if isinstance(ast_node, (WhileStatement, ForStatement, ForEachStatement)):
                has_loops = True
            # Recursively visit children
            for child in getattr(ast_node, "children", []):
                if isinstance(child, (list, tuple)):
                    for item in child:
                        if hasattr(item, "__dict__"):
                            check_loops(item)
                elif hasattr(child, "__dict__"):
                    check_loops(child)

        if node.body:
            for stmt in node.body:
                check_loops(stmt)

        return has_loops

    def _has_recursion(self, node: MethodDeclaration, method_name: str) -> bool:
        """Check if method contains recursive calls."""
        has_recursion = False

        def check_recursion(ast_node: Any) -> None:
            """Recursively check for recursive calls."""
            nonlocal has_recursion
            if isinstance(ast_node, MethodInvocation):
                if hasattr(ast_node, "member") and ast_node.member == method_name:
                    has_recursion = True
            # Recursively visit children
            for child in getattr(ast_node, "children", []):
                if isinstance(child, (list, tuple)):
                    for item in child:
                        if hasattr(item, "__dict__"):
                            check_recursion(item)
                elif hasattr(child, "__dict__"):
                    check_recursion(child)

        if node.body:
            for stmt in node.body:
                check_recursion(stmt)

        return has_recursion

    def _extract_field_info(self, node: FieldDeclaration) -> tuple[list[str], list[str]]:
        """Extract field names and types."""
        field_names = [declarator.name for declarator in node.declarators]
        field_type = node.type.name if hasattr(node.type, "name") else str(node.type)
        field_types = [field_type] * len(field_names)
        return field_names, field_types

    def _extract_dependencies(
        self, imports: list[str], field_types: dict[str, str], methods: list[MethodBody]
    ) -> set[str]:
        """Extract class dependencies from imports, fields, and method parameters."""
        dependencies: set[str] = set()

        # Extract from imports (get class name from full import path)
        for imp in imports:
            if "." in imp:
                class_name = imp.split(".")[-1]
                dependencies.add(class_name)

        # Extract from field types
        for field_type in field_types.values():
            # Remove generics
            clean_type = field_type.split("<")[0].split("[")[0]
            dependencies.add(clean_type)

        # Extract from method call sites
        for method in methods:
            for call_site in method.call_sites:
                if call_site.callee_class:
                    dependencies.add(call_site.callee_class)

        return dependencies

    def _clean_javadoc(self, doc: str) -> str:
        """Clean and normalize javadoc comments."""
        if not doc:
            return ""
        cleaned = re.sub(r"/\*\*|\*/|\*", "", doc)
        cleaned = re.sub(r"\n\s+", " ", cleaned)
        cleaned = cleaned.strip()
        cleaned = cleaned.replace("\\", "\\\\")
        cleaned = cleaned.replace('"', '\\"')
        cleaned = cleaned.replace("\n", " ")
        cleaned = cleaned.replace("\r", "")
        return cleaned[:500]

