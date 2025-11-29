"""SHACL Validator Port - Interface for constraint validation.

This port defines the contract for closed-world SHACL validation,
providing pre/post condition checking for workflow state.

SHACL provides what N3 cannot: closed-world assumption validation.
While N3 operates under open-world assumption (absence != falsehood),
SHACL explicitly validates constraints like "exactly one status".
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Protocol


class ValidationSeverity(Enum):
    """SHACL validation result severity levels."""

    INFO = auto()
    WARNING = auto()
    VIOLATION = auto()


@dataclass(frozen=True)
class ValidationViolation:
    """A single SHACL validation violation.

    Parameters
    ----------
    focus_node : str
        The node that failed validation.
    path : str | None
        The property path that was violated.
    constraint : str
        The constraint that was violated.
    message : str
        Human-readable violation message.
    severity : ValidationSeverity
        Severity level of the violation.
    shape : str | None
        The SHACL shape that was violated.
    value : str | None
        The value that caused the violation.
    """

    focus_node: str
    constraint: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.VIOLATION
    path: str | None = None
    shape: str | None = None
    value: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Result of SHACL validation.

    Parameters
    ----------
    conforms : bool
        Whether the data conforms to all shapes.
    violations : tuple[ValidationViolation, ...]
        List of constraint violations found.
    shapes_evaluated : int
        Number of shapes that were evaluated.
    focus_nodes_validated : int
        Number of focus nodes validated.
    """

    conforms: bool
    violations: tuple[ValidationViolation, ...] = field(default_factory=tuple)
    shapes_evaluated: int = 0
    focus_nodes_validated: int = 0

    @property
    def violation_count(self) -> int:
        """Count of violations with VIOLATION severity."""
        return sum(1 for v in self.violations if v.severity == ValidationSeverity.VIOLATION)

    @property
    def warning_count(self) -> int:
        """Count of violations with WARNING severity."""
        return sum(1 for v in self.violations if v.severity == ValidationSeverity.WARNING)

    def get_violations_for_node(self, focus_node: str) -> tuple[ValidationViolation, ...]:
        """Get all violations for a specific focus node.

        Parameters
        ----------
        focus_node : str
            The focus node IRI.

        Returns
        -------
        tuple[ValidationViolation, ...]
            Violations for the specified node.
        """
        return tuple(v for v in self.violations if v.focus_node == focus_node)


# Standard SHACL shapes for workflow validation
WORKFLOW_SHAPES = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Task must have exactly one status (functional property enforcement)
kgc:TaskStatusShape a sh:NodeShape ;
    sh:targetClass yawl:Task ;
    sh:property [
        sh:path kgc:status ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:in ("Pending" "Active" "Completed" "Cancelled") ;
        sh:message "Task must have exactly one valid status" ;
    ] .

# Counter must have exactly one value (functional property enforcement)
kgc:CounterShape a sh:NodeShape ;
    sh:targetSubjectsOf kgc:instanceCount ;
    sh:property [
        sh:path kgc:instanceCount ;
        sh:maxCount 1 ;
        sh:datatype xsd:integer ;
        sh:message "Counter must have at most one integer value" ;
    ] .

# XOR split must have at most one selected branch
kgc:XORSplitShape a sh:NodeShape ;
    sh:targetSubjectsOf kgc:xorBranchSelected ;
    sh:sparql [
        sh:message "XOR split must have at most one active branch" ;
        sh:prefixes kgc:prefixes ;
        sh:select '''
            SELECT $this (COUNT(?active) AS ?count)
            WHERE {
                $this yawl:flowsInto ?flow .
                ?flow yawl:nextElementRef ?branch .
                ?branch kgc:status "Active" .
            }
            GROUP BY $this
            HAVING (COUNT(?active) > 1)
        ''' ;
    ] .

# Flow must reference existing tasks
kgc:FlowShape a sh:NodeShape ;
    sh:targetClass yawl:Flow ;
    sh:property [
        sh:path yawl:nextElementRef ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:message "Flow must reference exactly one next element" ;
    ] .
"""


class WorkflowValidator(Protocol):
    """Protocol for SHACL-based workflow validation.

    Implementations validate workflow state against SHACL shapes,
    ensuring constraints like "exactly one status" are enforced.

    This provides the closed-world validation that N3 cannot:
    - N3: Open-world assumption (missing data != violation)
    - SHACL: Closed-world constraints (missing data = violation)
    """

    @abstractmethod
    def validate(self, data_graph: str, shapes_graph: str | None = None) -> ValidationResult:
        """Validate data graph against SHACL shapes.

        Parameters
        ----------
        data_graph : str
            RDF data to validate (Turtle/N3 format).
        shapes_graph : str | None, optional
            SHACL shapes graph. If None, uses default workflow shapes.

        Returns
        -------
        ValidationResult
            Validation result with any violations.
        """
        ...

    @abstractmethod
    def validate_preconditions(self, data_graph: str) -> ValidationResult:
        """Validate preconditions before tick execution.

        Checks that the workflow state is valid before
        applying inference and mutations.

        Parameters
        ----------
        data_graph : str
            Current workflow state.

        Returns
        -------
        ValidationResult
            Validation result.
        """
        ...

    @abstractmethod
    def validate_postconditions(self, data_graph: str) -> ValidationResult:
        """Validate postconditions after tick execution.

        Checks that the workflow state is valid after
        mutations have been applied. If validation fails,
        the transaction should be rolled back.

        Parameters
        ----------
        data_graph : str
            New workflow state after mutations.

        Returns
        -------
        ValidationResult
            Validation result.
        """
        ...

    @abstractmethod
    def get_shapes(self) -> str:
        """Get the SHACL shapes being used for validation.

        Returns
        -------
        str
            SHACL shapes in Turtle format.
        """
        ...
