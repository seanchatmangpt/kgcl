"""Exception types for Hybrid Engine domain.

This module defines custom exceptions for the hybrid engine architecture.
All exceptions inherit from HybridEngineError for easy catch-all handling.

Examples
--------
>>> raise ConvergenceError(max_ticks=100, final_delta=5)
Traceback (most recent call last):
...
kgcl.hybrid.domain.exceptions.ConvergenceError: System did not converge after 100 ticks. Final delta: 5
"""

from __future__ import annotations


class HybridEngineError(Exception):
    """Base exception for all hybrid engine errors.

    All domain-specific exceptions inherit from this class,
    allowing callers to catch all engine errors with a single handler.

    Examples
    --------
    >>> try:
    ...     raise ConvergenceError(max_ticks=10, final_delta=5)
    ... except HybridEngineError as e:
    ...     print(f"Engine error: {e}")
    Engine error: System did not converge after 10 ticks. Final delta: 5
    """


class ConvergenceError(HybridEngineError):
    """Raised when system fails to converge within maximum ticks.

    This exception indicates that the physics rules did not reach a fixed point
    (delta=0) within the allowed number of ticks.

    Parameters
    ----------
    max_ticks : int
        Maximum number of ticks that were executed.
    final_delta : int
        Delta (triple change) on the final tick.

    Attributes
    ----------
    max_ticks : int
        Maximum ticks before failure.
    final_delta : int
        Final delta value.

    Examples
    --------
    >>> exc = ConvergenceError(max_ticks=100, final_delta=5)
    >>> exc.max_ticks
    100
    >>> exc.final_delta
    5
    >>> str(exc)
    'System did not converge after 100 ticks. Final delta: 5'
    """

    def __init__(self, max_ticks: int, final_delta: int) -> None:
        """Initialize ConvergenceError.

        Parameters
        ----------
        max_ticks : int
            Maximum number of ticks executed.
        final_delta : int
            Delta on the final tick.
        """
        self.max_ticks = max_ticks
        self.final_delta = final_delta
        message = f"System did not converge after {max_ticks} ticks. Final delta: {final_delta}"
        super().__init__(message)


class ReasonerError(HybridEngineError):
    """Raised when the EYE reasoner fails.

    This exception wraps errors from the EYE subprocess, providing
    context about what went wrong during reasoning.

    Parameters
    ----------
    message : str
        Description of the error.
    command : str | None
        The EYE command that failed.

    Attributes
    ----------
    command : str | None
        Failed command for debugging.

    Examples
    --------
    >>> exc = ReasonerError("EYE timed out", command="eye --nope --pass state.n3 rules.n3")
    >>> exc.command
    'eye --nope --pass state.n3 rules.n3'
    """

    def __init__(self, message: str, command: str | None = None) -> None:
        """Initialize ReasonerError.

        Parameters
        ----------
        message : str
            Error description.
        command : str | None
            Failed EYE command.
        """
        self.command = command
        super().__init__(message)


class StoreOperationError(HybridEngineError):
    """Raised when an RDF store operation fails.

    This exception wraps errors from PyOxigraph operations like
    loading data, executing queries, or dumping state.

    Parameters
    ----------
    operation : str
        The operation that failed (e.g., "load", "query", "dump").
    message : str
        Description of what went wrong.

    Attributes
    ----------
    operation : str
        Failed operation name.

    Examples
    --------
    >>> exc = StoreOperationError("load", "Invalid Turtle syntax")
    >>> exc.operation
    'load'
    """

    def __init__(self, operation: str, message: str) -> None:
        """Initialize StoreOperationError.

        Parameters
        ----------
        operation : str
            Failed operation name.
        message : str
            Error description.
        """
        self.operation = operation
        full_message = f"Store operation '{operation}' failed: {message}"
        super().__init__(full_message)
