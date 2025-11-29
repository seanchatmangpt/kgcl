"""Temporal reasoning port for LTL verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

from kgcl.hybrid.temporal.domain.event import WorkflowEvent
from kgcl.hybrid.temporal.domain.ltl_formula import LTLFormula, LTLResult


@dataclass(frozen=True)
class TemporalProperty:
    """Named temporal property with formula and description.

    Parameters
    ----------
    property_id : str
        Unique identifier for the property
    name : str
        Human-readable name
    description : str
        Detailed description of what the property verifies
    formula : LTLFormula
        LTL formula representing the property
    workflow_id : str | None
        Workflow to verify against, None applies to all workflows
    """

    property_id: str
    name: str
    description: str
    formula: LTLFormula
    workflow_id: str | None = None


@dataclass(frozen=True)
class PropertyVerificationResult:
    """Result of verifying a temporal property.

    Parameters
    ----------
    property : TemporalProperty
        The property that was verified
    result : LTLResult
        The verification result
    checked_events : int
        Number of events examined during verification
    duration_ms : float
        Time taken to verify the property in milliseconds
    """

    property: TemporalProperty
    result: LTLResult
    checked_events: int
    duration_ms: float


@runtime_checkable
class TemporalReasoner(Protocol):
    """Protocol for LTL temporal reasoning over event streams.

    Provides methods for evaluating LTL formulas and checking common
    temporal properties over workflow event histories.
    """

    def evaluate(self, formula: LTLFormula, workflow_id: str | None = None) -> LTLResult:
        """Evaluate LTL formula over event history.

        Parameters
        ----------
        formula : LTLFormula
            The LTL formula to evaluate
        workflow_id : str | None
            Optional workflow ID to filter events

        Returns
        -------
        LTLResult
            Evaluation result with satisfaction status and details
        """
        ...

    def check_always(self, condition: Callable[[WorkflowEvent], bool], workflow_id: str | None = None) -> LTLResult:
        """Check: ALWAYS (G) - condition holds for ALL events.

        Parameters
        ----------
        condition : Callable[[WorkflowEvent], bool]
            Predicate to check on each event
        workflow_id : str | None
            Optional workflow ID to filter events

        Returns
        -------
        LTLResult
            Result with early exit on first violation
        """
        ...

    def check_eventually(self, condition: Callable[[WorkflowEvent], bool], workflow_id: str | None = None) -> LTLResult:
        """Check: EVENTUALLY (F) - condition holds for SOME event.

        Parameters
        ----------
        condition : Callable[[WorkflowEvent], bool]
            Predicate to check on each event
        workflow_id : str | None
            Optional workflow ID to filter events

        Returns
        -------
        LTLResult
            Result with early exit on first satisfaction
        """
        ...

    def check_until(
        self,
        condition_phi: Callable[[WorkflowEvent], bool],
        condition_psi: Callable[[WorkflowEvent], bool],
        workflow_id: str | None = None,
    ) -> LTLResult:
        """Check: UNTIL (U) - phi holds until psi becomes true.

        Parameters
        ----------
        condition_phi : Callable[[WorkflowEvent], bool]
            Predicate that must hold until psi
        condition_psi : Callable[[WorkflowEvent], bool]
            Predicate that must eventually become true
        workflow_id : str | None
            Optional workflow ID to filter events

        Returns
        -------
        LTLResult
            Result indicating if phi held until psi became true
        """
        ...

    def check_next(
        self, condition: Callable[[WorkflowEvent], bool], after_sequence: int, workflow_id: str | None = None
    ) -> LTLResult:
        """Check: NEXT (X) - condition holds in next state after sequence.

        Parameters
        ----------
        condition : Callable[[WorkflowEvent], bool]
            Predicate to check on the next event
        after_sequence : int
            Sequence number to check after
        workflow_id : str | None
            Optional workflow ID to filter events

        Returns
        -------
        LTLResult
            Result indicating if condition holds in next state
        """
        ...

    def check_precedes(self, event_type_a: str, event_type_b: str, workflow_id: str | None = None) -> LTLResult:
        """Check: A always precedes B (no B without prior A).

        Parameters
        ----------
        event_type_a : str
            Event type that must come first
        event_type_b : str
            Event type that must come after A
        workflow_id : str | None
            Optional workflow ID to filter events

        Returns
        -------
        LTLResult
            Result indicating if A always precedes B
        """
        ...

    def verify_property(self, property: TemporalProperty) -> PropertyVerificationResult:
        """Verify a named temporal property.

        Parameters
        ----------
        property : TemporalProperty
            The property to verify

        Returns
        -------
        PropertyVerificationResult
            Verification result with timing information
        """
        ...

    def verify_all(self, properties: list[TemporalProperty]) -> list[PropertyVerificationResult]:
        """Verify multiple properties, return all results.

        Parameters
        ----------
        properties : list[TemporalProperty]
            Properties to verify

        Returns
        -------
        list[PropertyVerificationResult]
            Results for each property in order
        """
        ...
