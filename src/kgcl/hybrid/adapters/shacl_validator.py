"""SHACL Validator - Closed-world constraint validation.

This adapter implements the WorkflowValidator port using pySHACL,
providing pre/post condition validation for workflow state.

SHACL provides what N3 cannot:
- N3: Open-world assumption (missing data is not a violation)
- SHACL: Closed-world constraints (enforce exactly-one, cardinality)

This ensures functional properties like kgc:status have exactly one value.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rdflib import Graph

from kgcl.hybrid.ports.validator_port import WORKFLOW_SHAPES, ValidationResult, ValidationSeverity, ValidationViolation

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# Check if pySHACL is available
try:
    from pyshacl import validate as pyshacl_validate

    PYSHACL_AVAILABLE = True
except ImportError:
    PYSHACL_AVAILABLE = False
    logger.warning("pySHACL not available - validation will be no-op")


class PySHACLValidator:
    """SHACL validator using pySHACL library.

    Validates workflow state against SHACL shapes, ensuring
    constraints like "exactly one status" are enforced.

    Parameters
    ----------
    shapes : str | None, optional
        Custom SHACL shapes in Turtle format.
        If None, uses default workflow shapes.

    Examples
    --------
    >>> validator = PySHACLValidator()
    >>> data = '''
    ...     @prefix kgc: <https://kgc.org/ns/> .
    ...     @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
    ...     <urn:task:A> a yawl:Task ; kgc:status "Active" .
    ... '''
    >>> result = validator.validate(data)
    >>> result.conforms
    True
    """

    def __init__(self, shapes: str | None = None) -> None:
        """Initialize SHACL validator.

        Parameters
        ----------
        shapes : str | None, optional
            Custom SHACL shapes. Uses defaults if None.
        """
        self._shapes = shapes or WORKFLOW_SHAPES
        self._shapes_graph: Graph | None = None
        logger.info(f"PySHACLValidator initialized (pySHACL available: {PYSHACL_AVAILABLE})")

    def _get_shapes_graph(self) -> Graph:
        """Get or create the shapes graph.

        Returns
        -------
        Graph
            Parsed SHACL shapes graph.
        """
        if self._shapes_graph is None:
            self._shapes_graph = Graph()
            self._shapes_graph.parse(data=self._shapes, format="turtle")
        return self._shapes_graph

    def validate(self, data_graph: str, shapes_graph: str | None = None) -> ValidationResult:
        """Validate data graph against SHACL shapes.

        Parameters
        ----------
        data_graph : str
            RDF data to validate (Turtle/N3 format).
        shapes_graph : str | None, optional
            Custom shapes for this validation.

        Returns
        -------
        ValidationResult
            Validation result with any violations.
        """
        if not PYSHACL_AVAILABLE:
            logger.warning("pySHACL not available - returning conformant")
            return ValidationResult(conforms=True)

        # Parse data graph
        data_g = Graph()
        try:
            # Try Turtle first, then N3
            try:
                data_g.parse(data=data_graph, format="turtle")
            except Exception:
                data_g.parse(data=data_graph, format="n3")
        except Exception as e:
            logger.error(f"Failed to parse data graph: {e}")
            return ValidationResult(
                conforms=False,
                violations=(
                    ValidationViolation(
                        focus_node="",
                        constraint="parse",
                        message=f"Failed to parse data: {e}",
                        severity=ValidationSeverity.VIOLATION,
                    ),
                ),
            )

        # Get shapes graph
        if shapes_graph:
            shapes_g = Graph()
            shapes_g.parse(data=shapes_graph, format="turtle")
        else:
            shapes_g = self._get_shapes_graph()

        # Run validation
        try:
            conforms, results_graph, results_text = pyshacl_validate(
                data_g, shacl_graph=shapes_g, inference="rdfs", abort_on_first=False
            )
        except Exception as e:
            logger.error(f"SHACL validation failed: {e}")
            return ValidationResult(
                conforms=False,
                violations=(
                    ValidationViolation(
                        focus_node="",
                        constraint="validation",
                        message=f"Validation error: {e}",
                        severity=ValidationSeverity.VIOLATION,
                    ),
                ),
            )

        # Extract violations from results graph
        violations = self._extract_violations(results_graph) if not conforms else ()

        return ValidationResult(conforms=conforms, violations=violations, focus_nodes_validated=len(data_g))

    def validate_preconditions(self, data_graph: str) -> ValidationResult:
        """Validate preconditions before tick execution.

        Parameters
        ----------
        data_graph : str
            Current workflow state.

        Returns
        -------
        ValidationResult
            Validation result.
        """
        logger.debug("Validating preconditions")
        return self.validate(data_graph)

    def validate_postconditions(self, data_graph: str) -> ValidationResult:
        """Validate postconditions after tick execution.

        Parameters
        ----------
        data_graph : str
            New workflow state after mutations.

        Returns
        -------
        ValidationResult
            Validation result.
        """
        logger.debug("Validating postconditions")
        return self.validate(data_graph)

    def get_shapes(self) -> str:
        """Get the SHACL shapes being used.

        Returns
        -------
        str
            SHACL shapes in Turtle format.
        """
        return self._shapes

    def _extract_violations(self, results_graph: Graph) -> tuple[ValidationViolation, ...]:
        """Extract violations from SHACL results graph.

        Parameters
        ----------
        results_graph : Graph
            SHACL validation results graph.

        Returns
        -------
        tuple[ValidationViolation, ...]
            Extracted violations.
        """
        violations: list[ValidationViolation] = []

        # Query for validation results
        query = """
        PREFIX sh: <http://www.w3.org/ns/shacl#>

        SELECT ?focusNode ?path ?message ?severity ?sourceConstraint ?value
        WHERE {
            ?result a sh:ValidationResult ;
                    sh:focusNode ?focusNode ;
                    sh:resultMessage ?message .
            OPTIONAL { ?result sh:resultPath ?path }
            OPTIONAL { ?result sh:resultSeverity ?severity }
            OPTIONAL { ?result sh:sourceConstraintComponent ?sourceConstraint }
            OPTIONAL { ?result sh:value ?value }
        }
        """

        try:
            for row in results_graph.query(query):
                severity = ValidationSeverity.VIOLATION
                if row.severity:
                    severity_str = str(row.severity)
                    if "Warning" in severity_str:
                        severity = ValidationSeverity.WARNING
                    elif "Info" in severity_str:
                        severity = ValidationSeverity.INFO

                violations.append(
                    ValidationViolation(
                        focus_node=str(row.focusNode) if row.focusNode else "",
                        path=str(row.path) if row.path else None,
                        constraint=str(row.sourceConstraint) if row.sourceConstraint else "unknown",
                        message=str(row.message) if row.message else "Validation failed",
                        severity=severity,
                        value=str(row.value) if row.value else None,
                    )
                )
        except Exception as e:
            logger.error(f"Failed to extract violations: {e}")

        return tuple(violations)


# No-op validator for when pySHACL is not available
class NoOpValidator:
    """No-op validator when pySHACL is not available.

    Always returns conformant results.
    """

    def validate(self, data_graph: str, shapes_graph: str | None = None) -> ValidationResult:
        """Return conformant result."""
        return ValidationResult(conforms=True)

    def validate_preconditions(self, data_graph: str) -> ValidationResult:
        """Return conformant result."""
        return ValidationResult(conforms=True)

    def validate_postconditions(self, data_graph: str) -> ValidationResult:
        """Return conformant result."""
        return ValidationResult(conforms=True)

    def get_shapes(self) -> str:
        """Return empty shapes."""
        return ""


# Factory function
def create_validator(shapes: str | None = None) -> PySHACLValidator | NoOpValidator:
    """Create a SHACL validator.

    Returns PySHACLValidator if pySHACL is available,
    otherwise returns NoOpValidator.

    Parameters
    ----------
    shapes : str | None, optional
        Custom SHACL shapes.

    Returns
    -------
    PySHACLValidator | NoOpValidator
        Configured validator.
    """
    if PYSHACL_AVAILABLE:
        return PySHACLValidator(shapes)
    return NoOpValidator()
