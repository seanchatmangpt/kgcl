"""Main delta detector orchestrator.

Coordinates all analyzers to detect differences between Java YAWL and Python
conversion, generating comprehensive structured reports.
"""

import json
from pathlib import Path
from typing import Any

import yaml

from kgcl.yawl_ontology.call_graph_analyzer import CallGraphAnalyzer
from kgcl.yawl_ontology.dependency_analyzer import DependencyAnalyzer
from kgcl.yawl_ontology.enhanced_java_parser import EnhancedJavaParser
from kgcl.yawl_ontology.enhanced_python_analyzer import EnhancedPythonCodeAnalyzer
from kgcl.yawl_ontology.exception_analyzer import ExceptionAnalyzer
from kgcl.yawl_ontology.gap_analyzer import PythonCodeAnalyzer, YawlGapAnalyzer
from kgcl.yawl_ontology.models import (
    DeltaReport,
    DeltaSeverity,
    DeltaSummary,
    DependencyDeltas,
    ExceptionDeltas,
    PerformanceDeltas,
    SemanticDeltas,
    StructuralDeltas,
    TestCoverageDeltas,
    TypeFlowDeltas,
)
from kgcl.yawl_ontology.performance_analyzer import PerformanceAnalyzer
from kgcl.yawl_ontology.semantic_detector import SemanticDetector
from kgcl.yawl_ontology.test_mapper import TestMapper
from kgcl.yawl_ontology.type_flow_analyzer import TypeFlowAnalyzer


class DeltaDetector:
    """Main delta detector orchestrator."""

    def __init__(
        self,
        java_root: Path,
        python_root: Path,
        ontology_path: Path | None = None,
        java_test_root: Path | None = None,
        python_test_root: Path | None = None,
    ) -> None:
        """Initialize delta detector.

        Parameters
        ----------
        java_root : Path
            Root directory of Java YAWL implementation
        python_root : Path
            Root directory of Python YAWL implementation
        ontology_path : Path | None
            Path to YAWL ontology file (optional, for structural analysis)
        java_test_root : Path | None
            Root directory of Java test files (optional)
        python_test_root : Path | None
            Root directory of Python test files (optional)
        """
        self.java_root = java_root
        self.python_root = python_root
        self.ontology_path = ontology_path
        self.java_test_root = java_test_root or java_root.parent / "test"
        self.python_test_root = python_test_root or python_root.parent / "tests"

        # Initialize parsers and analyzers
        self.java_parser = EnhancedJavaParser()
        self.python_analyzer = EnhancedPythonCodeAnalyzer(python_root)

        # Initialize gap analyzer for structural deltas
        self.gap_analyzer: YawlGapAnalyzer | None = None
        if ontology_path:
            self.gap_analyzer = YawlGapAnalyzer(ontology_path, python_root)

        # Initialize specialized analyzers
        self.semantic_detector = SemanticDetector(self.java_parser, self.python_analyzer)
        self.call_graph_analyzer = CallGraphAnalyzer(self.java_parser, self.python_analyzer)
        self.type_flow_analyzer = TypeFlowAnalyzer(self.java_parser, self.python_analyzer)
        self.exception_analyzer = ExceptionAnalyzer(self.java_parser, self.python_analyzer)
        self.dependency_analyzer = DependencyAnalyzer(self.java_parser, self.python_analyzer)
        self.performance_analyzer = PerformanceAnalyzer(self.java_parser, self.python_analyzer)
        self.test_mapper = TestMapper(self.java_test_root, self.python_test_root)

    def detect_all_deltas(self) -> DeltaReport:
        """Detect all types of deltas between Java and Python.

        Returns
        -------
        DeltaReport
            Comprehensive delta report
        """
        print("Loading Java classes...")
        java_classes = self._load_java_classes()

        print("Loading Python classes...")
        python_classes = {cls.name: cls for cls in self.python_analyzer.classes.values()}

        print("Detecting structural deltas...")
        structural_deltas = self._detect_structural_deltas(java_classes, python_classes)

        print("Detecting semantic deltas...")
        semantic_deltas = self.semantic_detector.detect_deltas(java_classes, python_classes)

        print("Detecting call graph deltas...")
        call_graph_deltas = self.call_graph_analyzer.detect_deltas(java_classes, python_classes)

        print("Detecting type flow deltas...")
        type_flow_deltas = self.type_flow_analyzer.detect_deltas(java_classes, python_classes)

        print("Detecting exception deltas...")
        exception_deltas = self.exception_analyzer.detect_deltas(java_classes, python_classes)

        print("Detecting dependency deltas...")
        dependency_deltas = self.dependency_analyzer.detect_deltas(java_classes, python_classes)

        print("Detecting performance deltas...")
        performance_deltas = self.performance_analyzer.detect_deltas(java_classes, python_classes)

        print("Detecting test coverage deltas...")
        test_coverage_deltas = self.test_mapper.detect_deltas(java_classes, python_classes)

        # Generate summary
        summary = self._generate_summary(
            java_classes,
            python_classes,
            structural_deltas,
            semantic_deltas,
            call_graph_deltas,
            type_flow_deltas,
            exception_deltas,
            dependency_deltas,
            performance_deltas,
            test_coverage_deltas,
        )

        return DeltaReport(
            structural_deltas=structural_deltas,
            semantic_deltas=semantic_deltas,
            call_graph_deltas=call_graph_deltas,
            type_flow_deltas=type_flow_deltas,
            exception_deltas=exception_deltas,
            test_coverage_deltas=test_coverage_deltas,
            dependency_deltas=dependency_deltas,
            performance_deltas=performance_deltas,
            summary=summary,
        )

    def _load_java_classes(self) -> list[Any]:
        """Load all Java classes from Java root.

        Returns
        -------
        list[Any]
            List of enhanced Java class info
        """
        java_classes: list[Any] = []

        if not self.java_root.exists():
            print(f"Warning: Java root does not exist: {self.java_root}")
            return java_classes

        for java_file in self.java_root.rglob("*.java"):
            try:
                classes = self.java_parser.parse_file(java_file)
                java_classes.extend(classes)
            except Exception as e:
                print(f"Warning: Could not parse {java_file}: {e}")

        return java_classes

    def _detect_structural_deltas(
        self, java_classes: list[Any], python_classes: dict[str, Any]
    ) -> StructuralDeltas:
        """Detect structural deltas using gap analyzer.

        Parameters
        ----------
        java_classes : list[Any]
            List of Java classes
        python_classes : dict[str, Any]
            Dictionary of Python classes

        Returns
        -------
        StructuralDeltas
            Structural deltas
        """
        if not self.gap_analyzer:
            # Fallback: basic structural comparison
            from kgcl.yawl_ontology.models import ClassDelta, MethodDelta, SignatureDelta

            missing_classes: list[ClassDelta] = []
            missing_methods: list[MethodDelta] = []

            java_class_names = {cls.name for cls in java_classes}
            python_class_names = set(python_classes.keys())

            for java_class in java_classes:
                if java_class.name not in python_class_names:
                    missing_classes.append(
                        ClassDelta(
                            java_class=java_class.name,
                            java_package=java_class.package,
                            python_class=None,
                            python_package=None,
                            severity=DeltaSeverity.HIGH,
                            reason="Class not found in Python implementation",
                        )
                    )

            return StructuralDeltas(
                missing_classes=missing_classes,
                missing_methods=missing_methods,
                signature_mismatches=[],
                inheritance_differences=[],
            )

        # Use gap analyzer for comprehensive structural analysis
        gap_analysis = self.gap_analyzer.analyze_discovered_classes()

        from kgcl.yawl_ontology.models import ClassDelta, MethodDelta

        missing_classes = [
            ClassDelta(
                java_class=cls.name,
                java_package=cls.package,
                python_class=None,
                python_package=None,
                severity=DeltaSeverity.HIGH,
                reason="Class not found in Python implementation",
            )
            for cls in gap_analysis.missing_classes
        ]

        missing_methods: list[MethodDelta] = []
        for class_name, methods in gap_analysis.missing_methods.items():
            for method in methods:
                missing_methods.append(
                    MethodDelta(
                        java_class=class_name,
                        java_method=method.name,
                        java_signature=method.signature if hasattr(method, "signature") else "",
                        python_method=None,
                        severity=DeltaSeverity.MEDIUM,
                        reason="Method not found in Python implementation",
                    )
                )

        return StructuralDeltas(
            missing_classes=missing_classes,
            missing_methods=missing_methods,
            signature_mismatches=[],
            inheritance_differences=[],
        )

    def _generate_summary(
        self,
        java_classes: list[Any],
        python_classes: dict[str, Any],
        structural_deltas: StructuralDeltas,
        semantic_deltas: SemanticDeltas,
        call_graph_deltas: Any,
        type_flow_deltas: TypeFlowDeltas,
        exception_deltas: ExceptionDeltas,
        dependency_deltas: DependencyDeltas,
        performance_deltas: PerformanceDeltas,
        test_coverage_deltas: TestCoverageDeltas,
    ) -> DeltaSummary:
        """Generate summary statistics.

        Parameters
        ----------
        java_classes : list[Any]
            List of Java classes
        python_classes : dict[str, Any]
            Dictionary of Python classes
        structural_deltas : StructuralDeltas
            Structural deltas
        semantic_deltas : SemanticDeltas
            Semantic deltas
        call_graph_deltas : Any
            Call graph deltas
        type_flow_deltas : TypeFlowDeltas
            Type flow deltas
        exception_deltas : ExceptionDeltas
            Exception deltas
        dependency_deltas : DependencyDeltas
            Dependency deltas
        performance_deltas : PerformanceDeltas
            Performance deltas
        test_coverage_deltas : TestCoverageDeltas
            Test coverage deltas

        Returns
        -------
        DeltaSummary
            Summary statistics
        """
        total_classes = len(java_classes)
        total_methods = sum(len(cls.methods) for cls in java_classes)

        # Count deltas by severity
        all_deltas: list[Any] = []
        all_deltas.extend(structural_deltas.missing_classes)
        all_deltas.extend(structural_deltas.missing_methods)
        all_deltas.extend(semantic_deltas.fingerprint_mismatches)
        all_deltas.extend(semantic_deltas.algorithm_changes)
        all_deltas.extend(type_flow_deltas.type_mismatches)
        all_deltas.extend(exception_deltas.missing_handling)
        all_deltas.extend(dependency_deltas.missing_dependencies)
        all_deltas.extend(performance_deltas.complexity_regressions)

        critical = sum(1 for d in all_deltas if hasattr(d, "severity") and d.severity == DeltaSeverity.CRITICAL)
        high = sum(1 for d in all_deltas if hasattr(d, "severity") and d.severity == DeltaSeverity.HIGH)
        medium = sum(1 for d in all_deltas if hasattr(d, "severity") and d.severity == DeltaSeverity.MEDIUM)
        low = sum(1 for d in all_deltas if hasattr(d, "severity") and d.severity == DeltaSeverity.LOW)
        info = sum(1 for d in all_deltas if hasattr(d, "severity") and d.severity == DeltaSeverity.INFO)

        # Calculate coverage
        implemented_classes = len(python_classes)
        coverage_percent = (implemented_classes / total_classes * 100) if total_classes > 0 else 0.0

        warnings = len(call_graph_deltas.missing_paths) + len(call_graph_deltas.new_paths)

        return DeltaSummary(
            total_classes_analyzed=total_classes,
            total_methods_analyzed=total_methods,
            coverage_percent=coverage_percent,
            critical_deltas=critical,
            high_deltas=high,
            medium_deltas=medium,
            low_deltas=low,
            info_deltas=info,
            warnings=warnings,
        )

    def export_report(self, report: DeltaReport, output_path: Path, format: str = "json") -> None:
        """Export delta report to file.

        Parameters
        ----------
        report : DeltaReport
            Delta report to export
        output_path : Path
            Output file path
        format : str
            Output format: "json" or "yaml"
        """
        if format.lower() == "json":
            output_path.write_text(json.dumps(report.to_dict(), indent=2))
        elif format.lower() == "yaml":
            output_path.write_text(yaml.dump(report.to_dict(), default_flow_style=False))
        else:
            msg = f"Unsupported format: {format}. Use 'json' or 'yaml'"
            raise ValueError(msg)

        print(f"✓ Exported delta report: {output_path}")

