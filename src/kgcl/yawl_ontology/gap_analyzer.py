"""Gap analyzer for YAWL Java → Python porting.

Compares Java YAWL ontology against Python implementation to identify:
- Missing core classes
- Missing methods
- Incomplete implementations
- Critical architecture gaps
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path

from kgcl.yawl_ontology.explorer import ClassInfo, MethodSignature, YawlOntologyExplorer


@dataclass
class PythonClassInfo:
    """Python class metadata from AST parsing."""

    name: str
    file_path: str
    methods: list[str] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=list)
    is_stub: bool = False  # Has only pass/raise NotImplementedError


@dataclass
class GapAnalysis:
    """Gap analysis results."""

    missing_classes: list[ClassInfo]
    missing_methods: dict[str, list[MethodSignature]]
    stub_classes: list[str]
    partial_implementations: dict[str, tuple[int, int]]  # class -> (implemented, total)
    coverage_percent: float


class PythonCodeAnalyzer:
    """Analyze existing Python implementation."""

    def __init__(self, python_root: Path) -> None:
        """Initialize analyzer.

        Parameters
        ----------
        python_root : Path
            Root directory of Python YAWL implementation
        """
        self.python_root = python_root
        self.classes: dict[str, PythonClassInfo] = {}
        self._scan_python_files()

    def _scan_python_files(self) -> None:
        """Scan Python files and extract class information."""
        for py_file in self.python_root.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue

            try:
                self._parse_python_file(py_file)
            except Exception as e:
                print(f"Warning: Could not parse {py_file}: {e}")

    def _parse_python_file(self, file_path: Path) -> None:
        """Parse Python file and extract class info."""
        content = file_path.read_text()
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                base_classes = [self._get_base_name(base) for base in node.bases]

                # Check if stub (all methods are pass/raise NotImplementedError)
                is_stub = self._is_stub_class(node)

                class_info = PythonClassInfo(
                    name=node.name,
                    file_path=str(file_path.relative_to(self.python_root)),
                    methods=methods,
                    base_classes=base_classes,
                    is_stub=is_stub,
                )
                self.classes[node.name] = class_info

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


class YawlGapAnalyzer:
    """Analyze gaps between Java YAWL and Python implementation."""

    def __init__(self, ontology_path: Path, python_root: Path) -> None:
        """Initialize gap analyzer.

        Parameters
        ----------
        ontology_path : Path
            Path to YAWL ontology file
        python_root : Path
            Root directory of Python implementation
        """
        self.explorer = YawlOntologyExplorer(ontology_path)
        self.python_analyzer = PythonCodeAnalyzer(python_root)

    def discover_important_classes(self, min_methods: int = 10, limit: int = 20) -> list[str]:
        """Discover important classes from ontology based on method count.

        Parameters
        ----------
        min_methods : int
            Minimum number of methods to be considered important
        limit : int
            Maximum number of classes to return

        Returns
        -------
        list[str]
            List of important class names
        """
        query = f"""
        PREFIX yawl: <http://yawlfoundation.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?className (COUNT(?method) as ?methodCount)
        WHERE {{
            ?class a yawl:Class .
            ?class rdfs:label ?className .
            ?class yawl:hasMethod ?method .
        }}
        GROUP BY ?className
        HAVING (COUNT(?method) >= {min_methods})
        ORDER BY DESC(?methodCount)
        LIMIT {limit}
        """

        result = self.explorer.query(query, "Discovering important classes by method count")
        return [row["className"] for row in result.data]

    def discover_base_classes(self) -> list[str]:
        """Discover base classes that have subclasses (architectural patterns).

        Returns
        -------
        list[str]
            List of base class names
        """
        query = """
        PREFIX yawl: <http://yawlfoundation.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?baseClassName
        WHERE {
            ?subclass yawl:extends ?baseClass .
            ?baseClass rdfs:label ?baseClassName .
        }
        ORDER BY ?baseClassName
        """

        result = self.explorer.query(query, "Discovering base classes (architectural patterns)")
        return [row["baseClassName"] for row in result.data]

    def analyze_discovered_classes(
        self, min_methods: int = 10, class_limit: int = 20, include_base_classes: bool = True
    ) -> GapAnalysis:
        """Analyze gaps using dynamically discovered important classes.

        Parameters
        ----------
        min_methods : int
            Minimum methods for a class to be analyzed
        class_limit : int
            Maximum number of classes to analyze
        include_base_classes : bool
            Whether to include architectural base classes

        Returns
        -------
        GapAnalysis
            Comprehensive gap analysis
        """
        # Discover important classes dynamically
        important_classes = self.discover_important_classes(min_methods, class_limit)

        # Also include base classes (architectural patterns)
        if include_base_classes:
            base_classes = self.discover_base_classes()
            # Combine and deduplicate
            all_classes = list(set(important_classes + base_classes))
        else:
            all_classes = important_classes

        print(f"\nAnalyzing {len(all_classes)} discovered classes...")

        missing_classes = []
        missing_methods: dict[str, list[MethodSignature]] = {}
        stub_classes = []
        partial_implementations: dict[str, tuple[int, int]] = {}

        for java_class in all_classes:
            # Get Java methods
            java_methods = self.explorer.get_class_methods(java_class)
            java_method_names = {m.name for m in java_methods}

            # Check if Python class exists
            if java_class not in self.python_analyzer.classes:
                missing_classes.append(ClassInfo(name=java_class, package="kgcl.yawl"))
                continue

            py_class = self.python_analyzer.classes[java_class]

            # Check if stub
            if py_class.is_stub:
                stub_classes.append(java_class)
                missing_methods[java_class] = java_methods
                continue

            # Compare methods
            py_method_names = set(py_class.methods)
            missing = java_method_names - py_method_names

            if missing:
                missing_method_objs = [m for m in java_methods if m.name in missing]
                missing_methods[java_class] = missing_method_objs

            # Calculate partial implementation
            implemented = len(java_method_names & py_method_names)
            total = len(java_method_names)
            partial_implementations[java_class] = (implemented, total)

        # Calculate coverage
        total_classes = len(all_classes)
        implemented_classes = total_classes - len(missing_classes) - len(stub_classes)
        coverage = (implemented_classes / total_classes) * 100 if total_classes > 0 else 0

        return GapAnalysis(
            missing_classes=missing_classes,
            missing_methods=missing_methods,
            stub_classes=stub_classes,
            partial_implementations=partial_implementations,
            coverage_percent=coverage,
        )

    def analyze_core_classes(self) -> GapAnalysis:
        """Analyze gaps in core YAWL classes (backward compatibility wrapper).

        Returns
        -------
        GapAnalysis
            Comprehensive gap analysis

        .. deprecated::
            Use analyze_discovered_classes() for dynamic discovery
        """
        return self.analyze_discovered_classes(min_methods=10, class_limit=20, include_base_classes=True)

    def get_implementation_priority(self) -> list[tuple[str, str]]:
        """Get prioritized list of classes to implement.

        Returns
        -------
        list[tuple[str, str]]
            List of (class_name, reason) tuples in priority order
        """
        priority = []

        # 1. Core engine first
        if "YEngine" not in self.python_analyzer.classes or self.python_analyzer.classes["YEngine"].is_stub:
            priority.append(("YEngine", "Core: Entry point for all operations"))

        # 2. Work item management
        if "YWorkItem" not in self.python_analyzer.classes or self.python_analyzer.classes["YWorkItem"].is_stub:
            priority.append(("YWorkItem", "Core: Represents executable work units"))

        # 3. Specification/Net structure
        if "YNet" not in self.python_analyzer.classes or self.python_analyzer.classes["YNet"].is_stub:
            priority.append(("YNet", "Core: Workflow structure representation"))

        if (
            "YSpecification" not in self.python_analyzer.classes
            or self.python_analyzer.classes["YSpecification"].is_stub
        ):
            priority.append(("YSpecification", "Core: Top-level workflow definition"))

        # 4. Task and condition nodes
        if "YTask" not in self.python_analyzer.classes or self.python_analyzer.classes["YTask"].is_stub:
            priority.append(("YTask", "Structure: Atomic work unit"))

        if "YCondition" not in self.python_analyzer.classes or self.python_analyzer.classes["YCondition"].is_stub:
            priority.append(("YCondition", "Structure: Data flow node"))

        # 5. Service integration
        if (
            "YAWLServiceGateway" not in self.python_analyzer.classes
            or self.python_analyzer.classes["YAWLServiceGateway"].is_stub
        ):
            priority.append(("YAWLServiceGateway", "Integration: External service connector"))

        return priority

    def export_gap_report(
        self, output_path: Path, min_methods: int = 10, class_limit: int = 20, include_base_classes: bool = True
    ) -> None:
        """Export detailed gap analysis report.

        Parameters
        ----------
        output_path : Path
            Output markdown file path
        min_methods : int
            Minimum methods for a class to be analyzed
        class_limit : int
            Maximum number of classes to analyze
        include_base_classes : bool
            Whether to include architectural base classes
        """
        analysis = self.analyze_discovered_classes(min_methods, class_limit, include_base_classes)
        priority = self.get_implementation_priority()

        lines = [
            "# YAWL Java → Python Gap Analysis",
            "",
            f"**Coverage:** {analysis.coverage_percent:.1f}% of core classes implemented",
            "",
            "## Summary",
            "",
            f"- **Missing Classes:** {len(analysis.missing_classes)}",
            f"- **Stub Classes:** {len(analysis.stub_classes)}",
            f"- **Partial Implementations:** {len(analysis.partial_implementations)}",
            "",
        ]

        # Missing classes
        if analysis.missing_classes:
            lines.append("## Missing Classes")
            lines.append("")
            for cls in analysis.missing_classes:
                lines.append(f"- `{cls.name}` - Not found in Python implementation")
            lines.append("")

        # Stub classes
        if analysis.stub_classes:
            lines.append("## Stub Classes (Empty Implementations)")
            lines.append("")
            for cls in analysis.stub_classes:
                java_methods = self.explorer.get_class_methods(cls)
                lines.append(f"### {cls}")
                lines.append(f"- Java methods: {len(java_methods)}")
                lines.append("- Python implementation: **STUB ONLY**")
                lines.append("")

        # Partial implementations
        if analysis.partial_implementations:
            lines.append("## Partial Implementations")
            lines.append("")
            lines.append("| Class | Implemented | Total | Completion |")
            lines.append("|-------|-------------|-------|------------|")
            for cls, (impl, total) in sorted(analysis.partial_implementations.items()):
                if cls not in analysis.stub_classes:  # Don't duplicate stubs
                    pct = (impl / total * 100) if total > 0 else 0
                    lines.append(f"| `{cls}` | {impl} | {total} | {pct:.1f}% |")
            lines.append("")

        # Missing methods details
        if analysis.missing_methods:
            lines.append("## Missing Methods (Top 5 per class)")
            lines.append("")
            for cls, methods in analysis.missing_methods.items():
                if cls not in analysis.stub_classes:  # Skip full stubs
                    lines.append(f"### {cls}")
                    for method in methods[:5]:
                        lines.append(f"- `{method.name}` → `{method.return_type}`")
                    if len(methods) > 5:
                        lines.append(f"- *...and {len(methods) - 5} more*")
                    lines.append("")

        # Implementation priority
        lines.append("## Implementation Priority")
        lines.append("")
        for i, (cls, reason) in enumerate(priority, 1):
            lines.append(f"{i}. **{cls}** - {reason}")
        lines.append("")

        # Existing Python classes
        lines.append("## Existing Python Implementation")
        lines.append("")
        for cls_name, cls_info in sorted(self.python_analyzer.classes.items()):
            status = "STUB" if cls_info.is_stub else f"{len(cls_info.methods)} methods"
            lines.append(f"- `{cls_name}` ({cls_info.file_path}) - {status}")

        output_path.write_text("\n".join(lines))
        print(f"✓ Exported gap analysis: {output_path}")
