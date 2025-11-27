"""PhysicsResult - Result of applying physics (one tick).

This module contains the immutable result object returned after each tick
of physics application in the hybrid engine.

Examples
--------
>>> result = PhysicsResult(tick_number=1, duration_ms=12.5, triples_before=100, triples_after=105, delta=5)
>>> result.delta
5
>>> result.converged
False
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhysicsResult:
    """Result of applying physics (one tick).

    Immutable value object containing metrics from a single tick of physics
    application via the EYE reasoner.

    Parameters
    ----------
    tick_number : int
        Sequential tick identifier.
    duration_ms : float
        Time taken for physics application in milliseconds.
    triples_before : int
        Triple count before physics application.
    triples_after : int
        Triple count after physics application.
    delta : int
        Change in triple count (triples_after - triples_before).

    Attributes
    ----------
    converged : bool
        True if system reached fixed point (delta == 0).

    Examples
    --------
    Create a result showing new inferences:

    >>> result = PhysicsResult(tick_number=1, duration_ms=12.5, triples_before=100, triples_after=105, delta=5)
    >>> result.delta
    5
    >>> result.converged
    False

    Create a result showing convergence:

    >>> result = PhysicsResult(tick_number=3, duration_ms=8.2, triples_before=150, triples_after=150, delta=0)
    >>> result.converged
    True

    Results are immutable:

    >>> result = PhysicsResult(1, 10.0, 100, 105, 5)
    >>> try:
    ...     result.delta = 10  # type: ignore[misc]
    ... except AttributeError:
    ...     print("Cannot modify frozen dataclass")
    Cannot modify frozen dataclass
    """

    tick_number: int
    duration_ms: float
    triples_before: int
    triples_after: int
    delta: int

    @property
    def converged(self) -> bool:
        """Check if system reached fixed point (no changes).

        Returns
        -------
        bool
            True if delta is zero (no new triples inferred).

        Examples
        --------
        >>> result = PhysicsResult(1, 10.0, 100, 100, 0)
        >>> result.converged
        True

        >>> result2 = PhysicsResult(1, 10.0, 100, 105, 5)
        >>> result2.converged
        False
        """
        return self.delta == 0

    def __repr__(self) -> str:
        """Return string representation.

        Returns
        -------
        str
            Human-readable representation with key metrics.

        Examples
        --------
        >>> result = PhysicsResult(1, 10.5, 100, 105, 5)
        >>> repr(result)
        'PhysicsResult(tick=1, delta=5, converged=False, duration=10.50ms)'
        """
        return (
            f"PhysicsResult(tick={self.tick_number}, delta={self.delta}, "
            f"converged={self.converged}, duration={self.duration_ms:.2f}ms)"
        )
