"""Reasoner - Protocol for N3 reasoning engine.

This module defines the abstract interface for N3 reasoners.
The hybrid engine depends on this protocol for applying physics rules.

Examples
--------
>>> from kgcl.hybrid.ports.reasoner_port import Reasoner, ReasoningOutput
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ReasoningOutput:
    """Result of reasoning execution.

    Parameters
    ----------
    success : bool
        Whether reasoning completed successfully.
    output : str
        N3 output from reasoner (deductive closure).
    error : str | None
        Error message if reasoning failed.
    duration_ms : float
        Execution duration in milliseconds.

    Examples
    --------
    Successful reasoning:

    >>> result = ReasoningOutput(
    ...     success=True, output="@prefix ex: <http://example.org/> . ex:a ex:b ex:c .", error=None, duration_ms=15.5
    ... )
    >>> result.success
    True

    Failed reasoning:

    >>> result = ReasoningOutput(success=False, output="", error="EYE timed out after 30 seconds", duration_ms=30000.0)
    >>> result.success
    False
    """

    success: bool
    output: str
    error: str | None
    duration_ms: float


@runtime_checkable
class Reasoner(Protocol):
    """Protocol for N3 reasoning engine.

    This protocol defines the interface for N3 reasoners that apply
    physics rules to RDF state. The primary implementation wraps
    the EYE reasoner subprocess.

    Methods
    -------
    reason(state, rules)
        Apply rules to state and return deductive closure.
    is_available()
        Check if the reasoner is available for use.

    Examples
    --------
    Any class implementing this protocol can be used:

    >>> class MockReasoner:
    ...     def reason(self, state: str, rules: str) -> ReasoningOutput:
    ...         return ReasoningOutput(
    ...             success=True,
    ...             output=state,  # No new inferences
    ...             error=None,
    ...             duration_ms=0.0,
    ...         )
    ...
    ...     def is_available(self) -> bool:
    ...         return True
    """

    def reason(self, state: str, rules: str) -> ReasoningOutput:
        """Apply rules to state and return deductive closure.

        The reasoner takes current RDF state and N3 rules, and returns
        the deductive closure (all inferred triples plus original state).

        Parameters
        ----------
        state : str
            Current RDF state in Turtle/N3 format.
        rules : str
            N3 physics rules to apply.

        Returns
        -------
        ReasoningOutput
            Result containing success status, output, and metrics.
        """
        ...

    def is_available(self) -> bool:
        """Check if reasoner is available for use.

        Returns
        -------
        bool
            True if reasoner can be used.
        """
        ...
