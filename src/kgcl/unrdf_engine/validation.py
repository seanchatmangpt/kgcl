"""SHACL validation system for the UNRDF engine.

Provides RDF data validation using SHACL shapes with detailed reporting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from opentelemetry import trace
from pyshacl import validate
from rdflib import Graph

tracer = trace.get_tracer(__name__)


@dataclass
class ValidationResult:
    """Result of SHACL validation.

    Parameters
    ----------
    conforms : bool
        Whether the data conforms to the shapes
    violations : list[dict[str, Any]]
        Validation violations found
    report_graph : Graph
        Full SHACL validation report as RDF
    report_text : str
        Human-readable validation report

    """

    conforms: bool
    violations: list[dict[str, Any]] = field(default_factory=list)
    report_graph: Graph | None = None
    report_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns
        -------
        dict[str, Any]
            Validation result as dictionary

        """
        return {
            "conforms": self.conforms,
            "violations": self.violations,
            "report_text": self.report_text,
        }


class ShaclValidator:
    """SHACL validator for RDF graphs.

    Loads SHACL shapes from Turtle files and validates RDF data against them.

    Examples
    --------
    >>> validator = ShaclValidator()
    >>> validator.load_shapes(Path("shapes.ttl"))
    >>> result = validator.validate(data_graph)
    >>> if not result.conforms:
    ...     print(result.report_text)

    """

    def __init__(self) -> None:
        """Initialize SHACL validator."""
        self.shapes_graph = Graph()
        self._shapes_loaded = False

    @tracer.start_as_current_span("shacl.load_shapes")
    def load_shapes(self, shapes_file: Path) -> None:
        """Load SHACL shapes from a Turtle file.

        Parameters
        ----------
        shapes_file : Path
            Path to Turtle file containing SHACL shapes

        """
        span = trace.get_current_span()
        span.set_attribute("shapes.file", str(shapes_file))

        if not shapes_file.exists():
            msg = f"Shapes file not found: {shapes_file}"
            raise FileNotFoundError(msg)

        self.shapes_graph.parse(shapes_file, format="turtle")
        self._shapes_loaded = True

        span.set_attribute("shapes.count", len(self.shapes_graph))

    @tracer.start_as_current_span("shacl.load_shapes_from_string")
    def load_shapes_from_string(self, shapes_ttl: str) -> None:
        """Load SHACL shapes from a Turtle string.

        Parameters
        ----------
        shapes_ttl : str
            Turtle-formatted SHACL shapes

        """
        self.shapes_graph.parse(data=shapes_ttl, format="turtle")
        self._shapes_loaded = True

        span = trace.get_current_span()
        span.set_attribute("shapes.count", len(self.shapes_graph))

    @tracer.start_as_current_span("shacl.validate")
    def validate(
        self, data_graph: Graph, inference: str | None = None, abort_on_first: bool = False
    ) -> ValidationResult:
        """Validate an RDF graph against loaded SHACL shapes.

        Parameters
        ----------
        data_graph : Graph
            RDF graph to validate
        inference : str, optional
            Inference engine to use (e.g., "rdfs", "owlrl")
        abort_on_first : bool, default=False
            Stop validation on first violation

        Returns
        -------
        ValidationResult
            Detailed validation results

        """
        if not self._shapes_loaded:
            msg = "No SHACL shapes loaded. Call load_shapes() first."
            raise ValueError(msg)

        span = trace.get_current_span()
        span.set_attribute("data.triples", len(data_graph))
        span.set_attribute("shapes.triples", len(self.shapes_graph))

        # Run pyshacl validation
        conforms, report_graph, report_text = validate(
            data_graph,
            shacl_graph=self.shapes_graph,
            inference=inference,
            abort_on_first=abort_on_first,
            advanced=True,  # Enable SHACL Advanced Features
        )

        span.set_attribute("validation.conforms", conforms)

        # Parse violations from report graph
        violations = self._parse_violations(report_graph) if report_graph else []

        span.set_attribute("validation.violations", len(violations))

        return ValidationResult(
            conforms=conforms,
            violations=violations,
            report_graph=report_graph,
            report_text=report_text,
        )

    def _parse_violations(self, report_graph: Graph) -> list[dict[str, Any]]:
        """Parse violations from SHACL validation report graph.

        Parameters
        ----------
        report_graph : Graph
            SHACL validation report graph

        Returns
        -------
        list[dict[str, Any]]
            List of violation details

        """
        violations = []

        # SHACL namespace
        sh = "http://www.w3.org/ns/shacl#"

        # Query for validation results
        query = f"""
        PREFIX sh: <{sh}>
        SELECT ?result ?focusNode ?resultPath ?value ?message ?severity
        WHERE {{
            ?report a sh:ValidationReport .
            ?report sh:result ?result .
            ?result sh:focusNode ?focusNode .
            OPTIONAL {{ ?result sh:resultPath ?resultPath }}
            OPTIONAL {{ ?result sh:value ?value }}
            OPTIONAL {{ ?result sh:resultMessage ?message }}
            OPTIONAL {{ ?result sh:resultSeverity ?severity }}
        }}
        """

        results = report_graph.query(query)

        for row in results:
            violation = {
                "focus_node": str(row.focusNode) if row.focusNode else None,
                "result_path": str(row.resultPath) if row.resultPath else None,
                "value": str(row.value) if row.value else None,
                "message": str(row.message) if row.message else "Validation failed",
                "severity": str(row.severity) if row.severity else f"{sh}Violation",
            }
            violations.append(violation)

        return violations

    @tracer.start_as_current_span("shacl.validate_with_custom_shapes")
    def validate_with_custom_shapes(
        self, data_graph: Graph, custom_shapes: Graph
    ) -> ValidationResult:
        """Validate using custom shapes instead of loaded ones.

        Parameters
        ----------
        data_graph : Graph
            RDF graph to validate
        custom_shapes : Graph
            Custom SHACL shapes graph

        Returns
        -------
        ValidationResult
            Validation results

        """
        span = trace.get_current_span()
        span.set_attribute("custom_shapes.triples", len(custom_shapes))

        conforms, report_graph, report_text = validate(
            data_graph, shacl_graph=custom_shapes, advanced=True
        )

        violations = self._parse_violations(report_graph) if report_graph else []

        return ValidationResult(
            conforms=conforms,
            violations=violations,
            report_graph=report_graph,
            report_text=report_text,
        )

    def has_shapes(self) -> bool:
        """Check if shapes have been loaded.

        Returns
        -------
        bool
            True if shapes are loaded

        """
        return self._shapes_loaded

    def get_shape_count(self) -> int:
        """Get number of triples in shapes graph.

        Returns
        -------
        int
            Triple count

        """
        return len(self.shapes_graph)
