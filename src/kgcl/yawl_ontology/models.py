"""Data models for YAWL Java → Python delta detection.

Defines all data structures used across delta detection analyzers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DeltaSeverity(str, Enum):
    """Severity levels for detected deltas."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(frozen=True)
class ClassDelta:
    """Represents a missing or different class."""

    java_class: str
    java_package: str
    python_class: str | None
    python_package: str | None
    severity: DeltaSeverity
    reason: str


@dataclass(frozen=True)
class MethodDelta:
    """Represents a missing method."""

    java_class: str
    java_method: str
    java_signature: str
    python_method: str | None
    severity: DeltaSeverity
    reason: str


@dataclass(frozen=True)
class SignatureDelta:
    """Represents a method signature mismatch."""

    java_class: str
    java_method: str
    java_signature: str
    python_signature: str
    differences: list[str]
    severity: DeltaSeverity


@dataclass(frozen=True)
class InheritanceDelta:
    """Represents inheritance hierarchy differences."""

    java_class: str
    java_extends: str | None
    java_implements: list[str]
    python_extends: str | None
    python_implements: list[str]
    differences: list[str]
    severity: DeltaSeverity


@dataclass(frozen=True)
class StructuralDeltas:
    """Structural differences between Java and Python."""

    missing_classes: list[ClassDelta] = field(default_factory=list)
    missing_methods: list[MethodDelta] = field(default_factory=list)
    signature_mismatches: list[SignatureDelta] = field(default_factory=list)
    inheritance_differences: list[InheritanceDelta] = field(default_factory=list)


@dataclass(frozen=True)
class FingerprintDelta:
    """Semantic fingerprint mismatch."""

    java_class: str
    java_method: str
    java_fingerprint: str
    python_fingerprint: str
    similarity_score: float
    severity: DeltaSeverity


@dataclass(frozen=True)
class AlgorithmDelta:
    """Algorithm or implementation approach difference."""

    java_class: str
    java_method: str
    java_approach: str
    python_approach: str
    complexity_difference: str | None
    severity: DeltaSeverity


@dataclass(frozen=True)
class CFGDelta:
    """Control flow graph difference."""

    java_class: str
    java_method: str
    java_complexity: int
    python_complexity: int
    missing_branches: list[str]
    severity: DeltaSeverity


@dataclass(frozen=True)
class DataFlowDelta:
    """Data flow or side effect difference."""

    java_class: str
    java_method: str
    java_mutations: list[str]
    python_mutations: list[str]
    missing_mutations: list[str]
    extra_mutations: list[str]
    severity: DeltaSeverity


@dataclass(frozen=True)
class SemanticDeltas:
    """Semantic differences between Java and Python."""

    fingerprint_mismatches: list[FingerprintDelta] = field(default_factory=list)
    algorithm_changes: list[AlgorithmDelta] = field(default_factory=list)
    control_flow_differences: list[CFGDelta] = field(default_factory=list)
    data_flow_differences: list[DataFlowDelta] = field(default_factory=list)


@dataclass(frozen=True)
class CallPath:
    """Represents a method call path."""

    caller_class: str
    caller_method: str
    callee_class: str
    callee_method: str


@dataclass(frozen=True)
class CallGraphDeltas:
    """Call graph differences."""

    missing_paths: list[CallPath] = field(default_factory=list)
    new_paths: list[CallPath] = field(default_factory=list)
    orphaned_methods: list[tuple[str, str]] = field(default_factory=list)  # (class, method)


@dataclass(frozen=True)
class TypeFlow:
    """Represents a type transformation."""

    class_name: str
    method_name: str
    input_types: list[str]
    output_type: str
    transformations: list[str]


@dataclass(frozen=True)
class TypeFlowDelta:
    """Type flow difference."""

    java_flow: TypeFlow
    python_flow: TypeFlow | None
    missing_validations: list[str]
    incompatible_types: list[str]
    severity: DeltaSeverity


@dataclass(frozen=True)
class TypeFlowDeltas:
    """Type flow differences."""

    type_mismatches: list[TypeFlowDelta] = field(default_factory=list)
    missing_validations: list[TypeFlowDelta] = field(default_factory=list)
    incompatible_returns: list[TypeFlowDelta] = field(default_factory=list)


@dataclass(frozen=True)
class ExceptionPattern:
    """Exception throwing or catching pattern."""

    class_name: str
    method_name: str
    exception_type: str
    is_thrown: bool
    is_caught: bool
    context: str


@dataclass(frozen=True)
class ExceptionDelta:
    """Exception handling difference."""

    java_class: str
    java_method: str
    java_pattern: ExceptionPattern
    python_pattern: ExceptionPattern | None
    missing_handling: bool
    changed_type: bool
    severity: DeltaSeverity


@dataclass(frozen=True)
class ExceptionDeltas:
    """Exception handling differences."""

    missing_exceptions: list[ExceptionDelta] = field(default_factory=list)
    changed_exceptions: list[ExceptionDelta] = field(default_factory=list)
    missing_handling: list[ExceptionDelta] = field(default_factory=list)


@dataclass(frozen=True)
class TestCoverage:
    """Test coverage information."""

    class_name: str
    method_name: str
    java_tests: list[str]
    python_tests: list[str]
    coverage_percent: float


@dataclass(frozen=True)
class TestCoverageDelta:
    """Test coverage difference."""

    class_name: str
    method_name: str
    java_coverage: float
    python_coverage: float
    missing_tests: list[str]
    severity: DeltaSeverity


@dataclass(frozen=True)
class TestCoverageDeltas:
    """Test coverage differences."""

    uncovered_methods: list[TestCoverageDelta] = field(default_factory=list)
    coverage_gaps: list[TestCoverageDelta] = field(default_factory=list)


@dataclass(frozen=True)
class Dependency:
    """Class dependency information."""

    dependent_class: str
    dependency_class: str
    dependency_type: str  # import, field, parameter, return
    is_circular: bool


@dataclass(frozen=True)
class DependencyDelta:
    """Dependency difference."""

    java_class: str
    missing_dependencies: list[Dependency] = field(default_factory=list)
    new_dependencies: list[Dependency] = field(default_factory=list)
    circular_differences: list[Dependency] = field(default_factory=list)
    severity: DeltaSeverity


@dataclass(frozen=True)
class DependencyDeltas:
    """Dependency graph differences."""

    missing_dependencies: list[DependencyDelta] = field(default_factory=list)
    new_dependencies: list[DependencyDelta] = field(default_factory=list)
    circular_differences: list[DependencyDelta] = field(default_factory=list)


@dataclass(frozen=True)
class PerformanceMetric:
    """Performance characteristic metric."""

    class_name: str
    method_name: str
    complexity: str  # O(1), O(n), O(n^2), etc.
    loop_count: int
    recursion_depth: int
    has_nested_loops: bool


@dataclass(frozen=True)
class PerformanceDelta:
    """Performance characteristic difference."""

    java_class: str
    java_method: str
    java_metrics: PerformanceMetric
    python_metrics: PerformanceMetric | None
    complexity_regression: bool
    optimization_opportunity: bool
    severity: DeltaSeverity


@dataclass(frozen=True)
class PerformanceDeltas:
    """Performance characteristic differences."""

    complexity_regressions: list[PerformanceDelta] = field(default_factory=list)
    optimization_opportunities: list[PerformanceDelta] = field(default_factory=list)


@dataclass(frozen=True)
class DeltaSummary:
    """Summary statistics for delta detection."""

    total_classes_analyzed: int
    total_methods_analyzed: int
    coverage_percent: float
    critical_deltas: int
    high_deltas: int
    medium_deltas: int
    low_deltas: int
    info_deltas: int
    warnings: int


@dataclass(frozen=True)
class DeltaReport:
    """Complete delta detection report."""

    structural_deltas: StructuralDeltas
    semantic_deltas: SemanticDeltas
    call_graph_deltas: CallGraphDeltas
    type_flow_deltas: TypeFlowDeltas
    exception_deltas: ExceptionDeltas
    test_coverage_deltas: TestCoverageDeltas
    dependency_deltas: DependencyDeltas
    performance_deltas: PerformanceDeltas
    summary: DeltaSummary

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for JSON serialization.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the report
        """
        return {
            "summary": {
                "total_classes_analyzed": self.summary.total_classes_analyzed,
                "total_methods_analyzed": self.summary.total_methods_analyzed,
                "coverage_percent": self.summary.coverage_percent,
                "critical_deltas": self.summary.critical_deltas,
                "high_deltas": self.summary.high_deltas,
                "medium_deltas": self.summary.medium_deltas,
                "low_deltas": self.summary.low_deltas,
                "info_deltas": self.summary.info_deltas,
                "warnings": self.summary.warnings,
            },
            "structural_deltas": {
                "missing_classes": [
                    {
                        "java_class": d.java_class,
                        "java_package": d.java_package,
                        "python_class": d.python_class,
                        "severity": d.severity.value,
                        "reason": d.reason,
                    }
                    for d in self.structural_deltas.missing_classes
                ],
                "missing_methods": [
                    {
                        "java_class": d.java_class,
                        "java_method": d.java_method,
                        "java_signature": d.java_signature,
                        "severity": d.severity.value,
                        "reason": d.reason,
                    }
                    for d in self.structural_deltas.missing_methods
                ],
                "signature_mismatches": [
                    {
                        "java_class": d.java_class,
                        "java_method": d.java_method,
                        "java_signature": d.java_signature,
                        "python_signature": d.python_signature,
                        "differences": d.differences,
                        "severity": d.severity.value,
                    }
                    for d in self.structural_deltas.signature_mismatches
                ],
            },
            "semantic_deltas": {
                "fingerprint_mismatches": [
                    {
                        "java_class": d.java_class,
                        "java_method": d.java_method,
                        "similarity_score": d.similarity_score,
                        "severity": d.severity.value,
                    }
                    for d in self.semantic_deltas.fingerprint_mismatches
                ],
            },
            "call_graph_deltas": {
                "missing_paths": [
                    {
                        "caller_class": p.caller_class,
                        "caller_method": p.caller_method,
                        "callee_class": p.callee_class,
                        "callee_method": p.callee_method,
                    }
                    for p in self.call_graph_deltas.missing_paths
                ],
            },
        }

