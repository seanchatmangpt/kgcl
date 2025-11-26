"""Quality report generator for SHACL validation results.

Converts SHACL validation violations to actionable quality reports,
categorized by severity with recommendations for fixes.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDFS, SH

from .base import ProjectionGenerator

# Define namespaces
KGC = Namespace("http://example.org/kgc/")


@dataclass
class Violation:
    """Domain object for SHACL validation violations."""

    focus_node: str
    result_path: str | None
    message: str
    severity: str  # "high", "medium", "low"
    source_constraint: str
    value: str | None = None

    def severity_priority(self) -> int:
        """Get numeric priority for severity (1=high, 2=medium, 3=low)."""
        return {"high": 1, "medium": 2, "low": 3}.get(self.severity, 3)


@dataclass
class QualityCategory:
    """Domain object for quality violation category."""

    name: str
    description: str
    violations: list[Violation] = field(default_factory=list)
    recommendation: str = ""

    def count_by_severity(self) -> dict[str, int]:
        """Count violations by severity level."""
        counts = {"high": 0, "medium": 0, "low": 0}
        for v in self.violations:
            counts[v.severity] = counts.get(v.severity, 0) + 1
        return counts


@dataclass
class QualityTrend:
    """Domain object for tracking quality trends over time."""

    date: str
    total_violations: int
    high_severity: int
    medium_severity: int
    low_severity: int


class QualityReportGenerator(ProjectionGenerator):
    """Generate quality reports from SHACL validation results.

    Converts SHACL violations to categorized reports with:
    - Severity levels (high/medium/low)
    - Recommendations for fixes
    - Links to ontology definitions
    - Trend tracking
    """

    def __init__(self, graph: Graph, validation_graph: Graph | None = None) -> None:
        """Initialize quality report generator.

        Args:
            graph: Main RDF graph (ontology + data)
            validation_graph: Graph containing SHACL validation results
        """
        super().__init__(graph)
        self.validation_graph = validation_graph or graph

    def gather_data(self) -> dict[str, Any]:
        """Gather SHACL violations and categorize by type.

        Returns
        -------
            Dictionary with violations, categories, and recommendations
        """
        violations = self._query_violations()
        categories = self._categorize_violations(violations)
        trends = self._query_trends()

        return {
            "total_violations": len(violations),
            "violations_by_severity": self._count_by_severity(violations),
            "categories": sorted(categories, key=lambda c: c.name),
            "trends": trends,
            "ontology_link": self._get_ontology_link(),
        }

    def _query_violations(self) -> list[Violation]:
        """Query validation graph for SHACL violations."""
        violations = []

        query = f"""
        PREFIX sh: <{SH}>
        PREFIX rdfs: <{RDFS}>

        SELECT ?report ?focusNode ?path ?message ?severity ?constraint ?value
        WHERE {{
            ?report a sh:ValidationReport .
            ?report sh:result ?result .
            ?result sh:focusNode ?focusNode .
            ?result sh:resultMessage ?message .
            ?result sh:resultSeverity ?severity .
            ?result sh:sourceConstraintComponent ?constraint .
            OPTIONAL {{ ?result sh:resultPath ?path }}
            OPTIONAL {{ ?result sh:value ?value }}
        }}
        """

        results = self.validation_graph.query(query)

        for row in results:
            severity = self._map_severity(row.severity)

            violations.append(
                Violation(
                    focus_node=self._format_uri(row.focusNode),
                    result_path=self._format_uri(row.path) if row.path else None,
                    message=str(row.message),
                    severity=severity,
                    source_constraint=self._format_uri(row.constraint),
                    value=str(row.value) if row.value else None,
                )
            )

        return violations

    def _categorize_violations(self, violations: list[Violation]) -> list[QualityCategory]:
        """Categorize violations by constraint type."""
        categories_map = defaultdict(list)

        for v in violations:
            category = self._get_category_name(v.source_constraint)
            categories_map[category].append(v)

        categories = []
        for name, category_violations in categories_map.items():
            category = QualityCategory(
                name=name,
                description=self._get_category_description(name),
                violations=sorted(category_violations, key=lambda v: v.severity_priority()),
                recommendation=self._get_recommendation(name),
            )
            categories.append(category)

        return categories

    def _map_severity(self, severity_uri: URIRef) -> str:
        """Map SHACL severity URI to readable severity level."""
        severity_map = {str(SH.Violation): "high", str(SH.Warning): "medium", str(SH.Info): "low"}
        return severity_map.get(str(severity_uri), "medium")

    def _get_category_name(self, constraint: str) -> str:
        """Extract category name from constraint URI."""
        # Map constraint types to readable categories
        if "MinCount" in constraint:
            return "Missing Required Properties"
        if "MaxCount" in constraint:
            return "Too Many Values"
        if "Datatype" in constraint:
            return "Invalid Data Types"
        if "Pattern" in constraint:
            return "Format Violations"
        if "Class" in constraint:
            return "Type Mismatches"
        if "NodeKind" in constraint:
            return "Node Kind Violations"
        return "Other Violations"

    def _get_category_description(self, category: str) -> str:
        """Get description for category."""
        descriptions = {
            "Missing Required Properties": "Required properties are not present on nodes",
            "Too Many Values": "Properties have more values than allowed",
            "Invalid Data Types": "Property values have incorrect data types",
            "Format Violations": "Values don't match required patterns",
            "Type Mismatches": "Nodes don't match expected types",
            "Node Kind Violations": "Nodes are not the correct kind (IRI, literal, blank)",
            "Other Violations": "Miscellaneous validation failures",
        }
        return descriptions.get(category, "")

    def _get_recommendation(self, category: str) -> str:
        """Get recommendation for fixing category violations."""
        recommendations = {
            "Missing Required Properties": "Add missing properties or review shape definitions",
            "Too Many Values": "Remove excess values or update cardinality constraints",
            "Invalid Data Types": "Convert values to correct data types",
            "Format Violations": "Update values to match required patterns",
            "Type Mismatches": "Add correct rdf:type or update class definitions",
            "Node Kind Violations": "Ensure nodes are IRIs, literals, or blank nodes as required",
            "Other Violations": "Review SHACL shapes and update data accordingly",
        }
        return recommendations.get(category, "Review validation report for details")

    def _count_by_severity(self, violations: list[Violation]) -> dict[str, int]:
        """Count violations by severity level."""
        counts = {"high": 0, "medium": 0, "low": 0}
        for v in violations:
            counts[v.severity] = counts.get(v.severity, 0) + 1
        return counts

    def _query_trends(self) -> list[QualityTrend]:
        """Query historical validation results for trends.

        Returns
        -------
        list[QualityTrend]
            Historical quality trends (empty if no historical data stored)
        """
        # No historical data stored yet - return empty list
        return []

    def _get_ontology_link(self) -> str:
        """Get link to ontology documentation."""
        return "src/kgcl/ontology/types.ttl"

    def _format_uri(self, uri: URIRef) -> str:
        """Format URI for display (extract local name)."""
        uri_str = str(uri)
        if "#" in uri_str:
            return uri_str.split("#")[-1]
        if "/" in uri_str:
            return uri_str.split("/")[-1]
        return uri_str

    def generate(self, template_name: str = "default.md") -> str:
        """Generate quality report artifact.

        Args:
            template_name: Template file name

        Returns
        -------
            Rendered markdown quality report
        """
        data = self.gather_data()
        self.validate_data(data, ["total_violations", "categories"])
        return self.render_template(template_name, data)
