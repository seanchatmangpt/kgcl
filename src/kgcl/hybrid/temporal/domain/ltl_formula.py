"""Linear Temporal Logic formulas for workflow verification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class LTLOperator(Enum):
    """Linear Temporal Logic operators.

    LTL extends propositional logic with temporal modalities:
    - ALWAYS (G): property holds in all future states
    - EVENTUALLY (F): property holds in some future state
    - NEXT (X): property holds in next state
    - UNTIL (U): first property holds until second becomes true
    """

    ALWAYS = "G"  # Globally (all states)
    EVENTUALLY = "F"  # Finally (some state)
    NEXT = "X"  # Next state
    UNTIL = "U"  # phi Until psi


@dataclass(frozen=True)
class LTLFormula:
    """Linear Temporal Logic formula.

    LTL formulas express temporal properties over infinite sequences of states.
    Inner formulas can be SPARQL ASK queries (strings) or nested LTL formulas.

    Parameters
    ----------
    operator : LTLOperator
        Temporal operator (G, F, X, U)
    inner : str | LTLFormula
        Inner formula (SPARQL ASK query or nested LTL)
    right : str | LTLFormula | None, optional
        Right-hand formula for UNTIL operator
    """

    operator: LTLOperator
    inner: str | LTLFormula
    right: str | LTLFormula | None = None

    def __post_init__(self) -> None:
        """Validate formula structure."""
        if self.operator == LTLOperator.UNTIL and self.right is None:
            msg = "UNTIL operator requires right-hand formula"
            raise ValueError(msg)


@dataclass(frozen=True)
class LTLResult:
    """Result of LTL evaluation over event trace.

    Parameters
    ----------
    holds : bool
        Whether formula holds over the trace
    violated_at : datetime | None, optional
        Timestamp when formula was violated (if any)
    violating_event_id : str | None, optional
        Event ID that violated formula (if any)
    explanation : str, optional
        Human-readable explanation of result
    """

    holds: bool
    violated_at: datetime | None = None
    violating_event_id: str | None = None
    explanation: str = ""
