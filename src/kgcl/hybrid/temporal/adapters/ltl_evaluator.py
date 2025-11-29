"""LTL evaluator implementation over event stores."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from kgcl.hybrid.temporal.domain.event import WorkflowEvent
from kgcl.hybrid.temporal.domain.ltl_formula import LTLFormula, LTLOperator, LTLResult
from kgcl.hybrid.temporal.ports.event_store_port import EventStore
from kgcl.hybrid.temporal.ports.temporal_reasoner_port import (
    PropertyVerificationResult,
    TemporalProperty,
    TemporalReasoner,
)


@dataclass
class LTLEvaluator:
    """LTL formula evaluator over event streams.

    Implements incremental evaluation where possible:
    - ALWAYS: Early exit on first violation (O(E) worst case)
    - EVENTUALLY: Early exit on first satisfaction (O(E) worst case)
    - UNTIL: Track phi until psi found (O(E) worst case)
    - NEXT: Check single event after position (O(1))

    Parameters
    ----------
    event_store : EventStore
        Event store to query for event history
    """

    event_store: EventStore

    def evaluate(self, formula: LTLFormula, workflow_id: str | None = None) -> LTLResult:
        """Evaluate arbitrary LTL formula recursively.

        Parameters
        ----------
        formula : LTLFormula
            The LTL formula to evaluate
        workflow_id : str | None
            Optional workflow ID to filter events

        Returns
        -------
        LTLResult
            Evaluation result

        Raises
        ------
        ValueError
            If formula operator is not supported
        """
        # Extract callable from inner (can be string SPARQL or callable)
        if formula.inner is None:
            return LTLResult(holds=False, explanation=f"{formula.operator.name} formula missing inner condition")

        if not callable(formula.inner):
            return LTLResult(holds=False, explanation=f"Inner condition must be callable, got {type(formula.inner)}")

        match formula.operator:
            case LTLOperator.ALWAYS:
                return self.check_always(formula.inner, workflow_id)
            case LTLOperator.EVENTUALLY:
                return self.check_eventually(formula.inner, workflow_id)
            case LTLOperator.UNTIL:
                if formula.right is None:
                    return LTLResult(holds=False, explanation="UNTIL formula missing right-hand condition")
                if not callable(formula.right):
                    return LTLResult(
                        holds=False, explanation=f"Right condition must be callable, got {type(formula.right)}"
                    )
                return self.check_until(formula.inner, formula.right, workflow_id)
            case LTLOperator.NEXT:
                # For NEXT, we need to handle after_sequence differently
                # Since LTLFormula doesn't have after_sequence field, this needs special handling
                return LTLResult(holds=False, explanation="NEXT operator requires special handling via check_next()")
            case _:
                return LTLResult(holds=False, explanation=f"Unsupported operator: {formula.operator}")

    def check_always(self, condition: Callable[[WorkflowEvent], bool], workflow_id: str | None = None) -> LTLResult:
        """G(phi) - for all events: condition(event) is true.

        Returns violation on first event where condition is false.

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
        for event in self._get_events(workflow_id):
            if not condition(event):
                return LTLResult(
                    holds=False,
                    violated_at=event.timestamp,
                    violating_event_id=event.event_id,
                    explanation=f"Condition violated at event {event.event_id}",
                )
        return LTLResult(holds=True, explanation="Condition holds for all events")

    def check_eventually(self, condition: Callable[[WorkflowEvent], bool], workflow_id: str | None = None) -> LTLResult:
        """F(phi) - exists some event where condition is true.

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
        for event in self._get_events(workflow_id):
            if condition(event):
                return LTLResult(holds=True, explanation=f"Condition satisfied at event {event.event_id}")
        return LTLResult(holds=False, explanation="Condition never satisfied")

    def check_until(
        self,
        condition_phi: Callable[[WorkflowEvent], bool],
        condition_psi: Callable[[WorkflowEvent], bool],
        workflow_id: str | None = None,
    ) -> LTLResult:
        """phi U psi - phi holds until psi becomes true.

        Algorithm:
        1. For each event in order:
           - If psi(event): SATISFIED
           - If not phi(event): VIOLATED
        2. If end reached without psi: VIOLATED (psi never occurred)

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
        for event in self._get_events(workflow_id):
            if condition_psi(event):
                return LTLResult(holds=True, explanation="Until condition reached")
            if not condition_phi(event):
                return LTLResult(
                    holds=False,
                    violated_at=event.timestamp,
                    violating_event_id=event.event_id,
                    explanation="Phi violated before psi became true",
                )
        return LTLResult(holds=False, explanation="Psi never became true")

    def check_next(
        self, condition: Callable[[WorkflowEvent], bool], after_sequence: int, workflow_id: str | None = None
    ) -> LTLResult:
        """X(phi) - condition holds in the next state after sequence.

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
        next_event = self.event_store.get_by_sequence(after_sequence + 1)
        if next_event is None:
            return LTLResult(holds=False, explanation="No next event exists")
        if workflow_id and next_event.workflow_id != workflow_id:
            return LTLResult(holds=False, explanation="Next event is for different workflow")
        if condition(next_event):
            return LTLResult(holds=True, explanation="Condition holds in next state")
        return LTLResult(
            holds=False,
            violated_at=next_event.timestamp,
            violating_event_id=next_event.event_id,
            explanation="Condition violated in next state",
        )

    def check_precedes(self, event_type_a: str, event_type_b: str, workflow_id: str | None = None) -> LTLResult:
        """A precedes B: no B occurs without A having occurred first.

        Track if A has been seen, fail if B seen before A.

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
        a_seen = False
        for event in self._get_events(workflow_id):
            if event.event_type.name == event_type_a:
                a_seen = True
            elif event.event_type.name == event_type_b and not a_seen:
                return LTLResult(
                    holds=False,
                    violated_at=event.timestamp,
                    violating_event_id=event.event_id,
                    explanation=f"{event_type_b} occurred before {event_type_a}",
                )
        return LTLResult(holds=True, explanation=f"{event_type_a} always precedes {event_type_b}")

    def verify_property(self, property: TemporalProperty) -> PropertyVerificationResult:
        """Verify named property with timing.

        Parameters
        ----------
        property : TemporalProperty
            The property to verify

        Returns
        -------
        PropertyVerificationResult
            Verification result with timing information
        """
        start = time.monotonic()
        result = self.evaluate(property.formula, property.workflow_id)
        duration = (time.monotonic() - start) * 1000
        return PropertyVerificationResult(
            property=property,
            result=result,
            checked_events=self.event_store.count(property.workflow_id),
            duration_ms=duration,
        )

    def verify_all(self, properties: list[TemporalProperty]) -> list[PropertyVerificationResult]:
        """Verify all properties.

        Parameters
        ----------
        properties : list[TemporalProperty]
            Properties to verify

        Returns
        -------
        list[PropertyVerificationResult]
            Results for each property in order
        """
        return [self.verify_property(p) for p in properties]

    def _get_events(self, workflow_id: str | None) -> list[WorkflowEvent]:
        """Get event iterator, optionally filtered by workflow.

        Parameters
        ----------
        workflow_id : str | None
            Optional workflow ID to filter events

        Returns
        -------
        list[WorkflowEvent]
            Filtered event list
        """
        return list(self.event_store.replay(workflow_id=workflow_id))
