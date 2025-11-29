"""Enhanced Python analyzer for delta detection.

Extends the base Python analyzer to extract:
- Method bodies (AST nodes)
- Call sites (function/method calls)
- Exception patterns (raise/except)
- Type hints (parameter types, return types)
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PythonCallSite:
    """Represents a Python method/function call site."""

    caller_method: str
    callee_name: str
    callee_attr: str | None  # For method calls like obj.method()
    arguments: list[str]
    line_number: int


@dataclass(frozen=True)
class PythonExceptionInfo:
    """Exception raising or catching information."""

    exception_type: str
    is_raised: bool
    is_caught: bool
    context: str  # method name where it occurs
    line_number: int


@dataclass(frozen=True)
class PythonMethodBody:
    """Enhanced Python method information with body analysis."""

    name: str
    return_type: str | None  # From type hints
    parameters: list[str]
    parameter_types: dict[str, str] = field(default_factory=dict)
    docstring: str
    body_ast: Any  # ast.FunctionDef node
    body_text: str
    call_sites: list[PythonCallSite] = field(default_factory=list)
    exceptions: list[PythonExceptionInfo] = field(default_factory=list)
    complexity: int = 0  # Cyclomatic complexity
    has_loops: bool = False
    has_recursion: bool = False
    type_hints: dict[str, str] = field(default_factory=dict)  # parameter -> type


@dataclass(frozen=True)
class EnhancedPythonClassInfo:
    """Enhanced Python class information with method bodies and dependencies."""

    name: str
    file_path: str
    methods: list[PythonMethodBody] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=list)
    fields: list[str] = field(default_factory=list)
    field_types: dict[str, str] = field(default_factory=dict)
    is_stub: bool = False
    imports: list[str] = field(default_factory=list)
    dependencies: set[str] = field(default_factory=set)  # Class/module names this class depends on


class EnhancedPythonCodeAnalyzer:
    """Enhanced Python code analyzer for delta detection."""

    def __init__(self, python_root: Path) -> None:
        """Initialize enhanced analyzer.

        Parameters
        ----------
        python_root : Path
            Root directory of Python YAWL implementation
        """
        self.python_root = python_root
        self.classes: dict[str, EnhancedPythonClassInfo] = {}
        self.source_code: dict[str, str] = {}  # file_path -> source code
        self._scan_python_files()

    def _scan_python_files(self) -> None:
        """Scan Python files and extract enhanced class information."""
        for py_file in self.python_root.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue

            try:
                self._parse_python_file(py_file)
            except Exception as e:
                print(f"Warning: Could not parse {py_file}: {e}")

    def _parse_python_file(self, file_path: Path) -> None:
        """Parse Python file and extract enhanced class info."""
        content = file_path.read_text(encoding="utf-8")
        self.source_code[str(file_path)] = content
        tree = ast.parse(content)

        # Extract imports first
        imports = self._extract_imports(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._extract_enhanced_class_info(node, imports, file_path, content)
                self.classes[node.name] = class_info

    def _extract_imports(self, tree: ast.AST) -> list[str]:
        """Extract import statements from AST."""
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                    for alias in node.names:
                        imports.append(f"{node.module}.{alias.name}")
        return imports

    def _extract_enhanced_class_info(
        self, node: ast.ClassDef, imports: list[str], file_path: Path, content: str
    ) -> EnhancedPythonClassInfo:
        """Extract enhanced class information from AST node."""
        methods = []
        fields: list[str] = []
        field_types: dict[str, str] = {}

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_body = self._extract_method_body(item, node.name, content)
                methods.append(method_body)
            elif isinstance(item, ast.Assign):
                # Extract field assignments
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        fields.append(target.id)
                        # Try to infer type from value
                        if isinstance(item.value, ast.Name):
                            field_types[target.id] = item.value.id
                        elif isinstance(item.value, ast.Constant):
                            field_types[target.id] = type(item.value.value).__name__

        base_classes = [self._get_base_name(base) for base in node.bases]
        is_stub = self._is_stub_class(node)

        # Extract dependencies
        dependencies = self._extract_dependencies(imports, field_types, methods)

        return EnhancedPythonClassInfo(
            name=node.name,
            file_path=str(file_path.relative_to(self.python_root)),
            methods=methods,
            base_classes=base_classes,
            fields=fields,
            field_types=field_types,
            is_stub=is_stub,
            imports=imports,
            dependencies=dependencies,
        )

    def _extract_method_body(
        self, node: ast.FunctionDef, class_name: str, content: str
    ) -> PythonMethodBody:
        """Extract method body with call sites and exception patterns."""
        # Extract return type from type hints
        return_type = None
        if node.returns:
            return_type = self._ast_to_type_string(node.returns)

        # Extract parameters and their types
        parameters: list[str] = []
        parameter_types: dict[str, str] = {}
        type_hints: dict[str, str] = {}

        for arg in node.args.args:
            param_name = arg.arg
            parameters.append(param_name)
            if arg.annotation:
                param_type = self._ast_to_type_string(arg.annotation)
                parameter_types[param_name] = param_type
                type_hints[param_name] = param_type

        # Extract docstring
        docstring = ast.get_docstring(node) or ""

        # Extract body text
        body_text = self._extract_body_text(node, content)

        # Extract call sites
        call_sites = self._extract_call_sites(node, node.name)

        # Extract exceptions
        exceptions = self._extract_exceptions(node, node.name)

        # Calculate complexity
        complexity = self._calculate_complexity(node)

        # Check for loops and recursion
        has_loops = self._has_loops(node)
        has_recursion = self._has_recursion(node, node.name)

        return PythonMethodBody(
            name=node.name,
            return_type=return_type,
            parameters=parameters,
            parameter_types=parameter_types,
            docstring=docstring,
            body_ast=node,
            body_text=body_text,
            call_sites=call_sites,
            exceptions=exceptions,
            complexity=complexity,
            has_loops=has_loops,
            has_recursion=has_recursion,
            type_hints=type_hints,
        )

    def _ast_to_type_string(self, node: ast.AST) -> str:
        """Convert AST type annotation node to string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Subscript):
            # Handle generics like List[str], Dict[str, int]
            value = self._ast_to_type_string(node.value)
            if isinstance(node.slice, ast.Index):
                slice_str = self._ast_to_type_string(node.slice.value)
            elif isinstance(node.slice, ast.Tuple):
                slice_str = ", ".join(self._ast_to_type_string(el) for el in node.slice.elts)
            else:
                slice_str = self._ast_to_type_string(node.slice)
            return f"{value}[{slice_str}]"
        elif isinstance(node, ast.Attribute):
            return f"{self._ast_to_type_string(node.value)}.{node.attr}"
        else:
            return str(type(node).__name__)

    def _extract_body_text(self, node: ast.FunctionDef, content: str) -> str:
        """Extract method body text from source code."""
        if not node.body:
            return ""

        try:
            lines = content.split("\n")
            start_line = node.lineno - 1
            end_line = node.end_lineno if hasattr(node, "end_lineno") else len(lines)
            return "\n".join(lines[start_line:end_line])
        except Exception:
            return ""

    def _extract_call_sites(self, node: ast.FunctionDef, method_name: str) -> list[PythonCallSite]:
        """Extract all call sites from method body."""
        call_sites: list[PythonCallSite] = []

        def visit_call(ast_node: ast.AST) -> None:
            """Recursively visit AST nodes to find function/method calls."""
            if isinstance(ast_node, ast.Call):
                callee_name = ""
                callee_attr = None

                if isinstance(ast_node.func, ast.Name):
                    callee_name = ast_node.func.id
                elif isinstance(ast_node.func, ast.Attribute):
                    callee_name = ast_node.func.attr
                    if isinstance(ast_node.func.value, ast.Name):
                        callee_attr = ast_node.func.value.id

                arguments = []
                for arg in ast_node.args:
                    if isinstance(arg, ast.Name):
                        arguments.append(arg.id)
                    elif isinstance(arg, ast.Constant):
                        arguments.append(str(arg.value))
                    else:
                        arguments.append(type(arg).__name__)

                line_number = ast_node.lineno if hasattr(ast_node, "lineno") else 0

                call_sites.append(
                    PythonCallSite(
                        caller_method=method_name,
                        callee_name=callee_name,
                        callee_attr=callee_attr,
                        arguments=arguments,
                        line_number=line_number,
                    )
                )

            # Recursively visit child nodes
            for child in ast.iter_child_nodes(ast_node):
                visit_call(child)

        for stmt in node.body:
            visit_call(stmt)

        return call_sites

    def _extract_exceptions(self, node: ast.FunctionDef, method_name: str) -> list[PythonExceptionInfo]:
        """Extract exception raising and catching patterns."""
        exceptions: list[PythonExceptionInfo] = []

        def visit_exceptions(ast_node: ast.AST) -> None:
            """Recursively visit AST nodes to find exceptions."""
            if isinstance(ast_node, ast.Raise):
                exc_type = "Exception"
                if ast_node.exc:
                    if isinstance(ast_node.exc, ast.Name):
                        exc_type = ast_node.exc.id
                    elif isinstance(ast_node.exc, ast.Call):
                        if isinstance(ast_node.exc.func, ast.Name):
                            exc_type = ast_node.exc.func.id

                line_number = ast_node.lineno if hasattr(ast_node, "lineno") else 0
                exceptions.append(
                    PythonExceptionInfo(
                        exception_type=exc_type,
                        is_raised=True,
                        is_caught=False,
                        context=method_name,
                        line_number=line_number,
                    )
                )

            if isinstance(ast_node, ast.Try):
                for handler in ast_node.handlers:
                    exc_type = "Exception"
                    if handler.type:
                        if isinstance(handler.type, ast.Name):
                            exc_type = handler.type.id
                        elif isinstance(handler.type, ast.Tuple):
                            # Multiple exception types
                            for elt in handler.type.elts:
                                if isinstance(elt, ast.Name):
                                    exc_type = elt.id
                                    line_number = handler.lineno if hasattr(handler, "lineno") else 0
                                    exceptions.append(
                                        PythonExceptionInfo(
                                            exception_type=exc_type,
                                            is_raised=False,
                                            is_caught=True,
                                            context=method_name,
                                            line_number=line_number,
                                        )
                                    )
                        else:
                            line_number = handler.lineno if hasattr(handler, "lineno") else 0
                            exceptions.append(
                                PythonExceptionInfo(
                                    exception_type=exc_type,
                                    is_raised=False,
                                    is_caught=True,
                                    context=method_name,
                                    line_number=line_number,
                                )
                            )

            # Recursively visit child nodes
            for child in ast.iter_child_nodes(ast_node):
                visit_exceptions(child)

        for stmt in node.body:
            visit_exceptions(stmt)

        return exceptions

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of method."""
        complexity = 1  # Base complexity

        def count_branches(ast_node: ast.AST) -> None:
            """Recursively count branch points."""
            nonlocal complexity
            if isinstance(
                ast_node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.Try, ast.With, ast.AsyncWith)
            ):
                complexity += 1
            # Recursively visit children
            for child in ast.iter_child_nodes(ast_node):
                count_branches(child)

        for stmt in node.body:
            count_branches(stmt)

        return complexity

    def _has_loops(self, node: ast.FunctionDef) -> bool:
        """Check if method contains loops."""
        has_loops = False

        def check_loops(ast_node: ast.AST) -> None:
            """Recursively check for loops."""
            nonlocal has_loops
            if isinstance(ast_node, (ast.While, ast.For, ast.AsyncFor)):
                has_loops = True
            # Recursively visit children
            for child in ast.iter_child_nodes(ast_node):
                check_loops(child)

        for stmt in node.body:
            check_loops(stmt)

        return has_loops

    def _has_recursion(self, node: ast.FunctionDef, method_name: str) -> bool:
        """Check if method contains recursive calls."""
        has_recursion = False

        def check_recursion(ast_node: ast.AST) -> None:
            """Recursively check for recursive calls."""
            nonlocal has_recursion
            if isinstance(ast_node, ast.Call):
                if isinstance(ast_node.func, ast.Name) and ast_node.func.id == method_name:
                    has_recursion = True
            # Recursively visit children
            for child in ast.iter_child_nodes(ast_node):
                check_recursion(child)

        for stmt in node.body:
            check_recursion(stmt)

        return has_recursion

    def _get_base_name(self, base: ast.expr) -> str:
        """Extract base class name from AST node."""
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute):
            return base.attr
        return "Unknown"

    def _is_stub_class(self, class_node: ast.ClassDef) -> bool:
        """Check if class is a stub (only pass/NotImplementedError)."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                if not self._is_stub_method(item):
                    return False
        return True

    def _is_stub_method(self, method: ast.FunctionDef) -> bool:
        """Check if method is a stub."""
        if not method.body:
            return True

        for stmt in method.body:
            # Skip docstrings
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                continue
            # Pass statement
            if isinstance(stmt, ast.Pass):
                continue
            # raise NotImplementedError
            if isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Name):
                if stmt.exc.id == "NotImplementedError":
                    continue
            # If we get here, there's actual implementation
            return False

        return True

    def _extract_dependencies(
        self, imports: list[str], field_types: dict[str, str], methods: list[PythonMethodBody]
    ) -> set[str]:
        """Extract class dependencies from imports, fields, and method calls."""
        dependencies: set[str] = set()

        # Extract from imports (get class name from full import path)
        for imp in imports:
            if "." in imp:
                parts = imp.split(".")
                # Add both the module and the class name
                dependencies.add(parts[-1])
                if len(parts) > 1:
                    dependencies.add(parts[-2])

        # Extract from field types
        for field_type in field_types.values():
            dependencies.add(field_type)

        # Extract from method call sites
        for method in methods:
            for call_site in method.call_sites:
                if call_site.callee_attr:
                    dependencies.add(call_site.callee_attr)
                dependencies.add(call_site.callee_name)

        return dependencies

