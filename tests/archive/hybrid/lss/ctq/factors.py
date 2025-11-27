"""CTQ Factor Definitions and Enumerations.

This module defines the CTQ (Critical-to-Quality) factor data model and dimension
enumeration used throughout the WCP-43 test suite.

Classes
-------
CTQDimension
    Enumeration of 5 CTQ dimensions from Lean Six Sigma
CTQFactor
    Frozen dataclass representing a single CTQ validation factor

Examples
--------
>>> from tests.hybrid.lss.ctq.factors import CTQDimension, CTQFactor
>>> factor = CTQFactor(dimension=CTQDimension.PERFORMANCE, pattern_id=2, description="WCP-2 converges in <5 ticks")
>>> factor.dimension_name
'Performance'
>>> factor.is_valid()
True
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CTQDimension(Enum):
    """CTQ Dimensions from Lean Six Sigma Quality Standards.

    Each dimension represents a critical quality factor for validating YAWL
    workflow control patterns.

    Attributes
    ----------
    CORRECTNESS : str
        Pattern produces expected state transitions
    COMPLETENESS : str
        All execution paths are handled
    CONSISTENCY : str
        Deterministic behavior across multiple runs
    PERFORMANCE : str
        Execution within acceptable tick/time bounds
    RELIABILITY : str
        Graceful handling of edge cases and failure modes

    Examples
    --------
    >>> from tests.hybrid.lss.ctq.factors import CTQDimension
    >>> CTQDimension.CORRECTNESS.value
    'correctness'
    >>> CTQDimension.PERFORMANCE.name
    'PERFORMANCE'
    >>> len(list(CTQDimension))
    5
    >>> all(isinstance(d.value, str) for d in CTQDimension)
    True

    Notes
    -----
    These dimensions map to ISO 9001:2015 quality management principles:
    - Correctness → Customer focus (correct results)
    - Completeness → Process approach (all paths covered)
    - Consistency → Evidence-based decision making
    - Performance → Engagement of people (efficiency)
    - Reliability → Improvement (robustness)
    """

    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"


@dataclass(frozen=True)
class CTQFactor:
    """Critical-to-Quality Factor for WCP Pattern Validation.

    Represents a single testable quality factor for a YAWL workflow control
    pattern. Immutable by design (frozen=True).

    Parameters
    ----------
    dimension : CTQDimension
        The CTQ dimension being validated
    pattern_id : int
        YAWL pattern number (1-43)
    description : str
        Human-readable description of the quality requirement

    Attributes
    ----------
    dimension : CTQDimension
        The CTQ dimension being validated
    pattern_id : int
        YAWL pattern number (1-43)
    description : str
        Human-readable description of the quality requirement

    Examples
    --------
    >>> from tests.hybrid.lss.ctq.factors import CTQDimension, CTQFactor
    >>> factor = CTQFactor(
    ...     dimension=CTQDimension.CORRECTNESS,
    ...     pattern_id=1,
    ...     description="WCP-1 Sequence produces correct linear state transition",
    ... )
    >>> factor.dimension.value
    'correctness'
    >>> factor.pattern_id
    1
    >>> factor.dimension_name
    'Correctness'

    >>> # Test is_valid() with valid pattern
    >>> factor.is_valid()
    True

    >>> # Test is_valid() with invalid pattern (out of range)
    >>> invalid_factor = CTQFactor(dimension=CTQDimension.PERFORMANCE, pattern_id=44, description="Invalid pattern")
    >>> invalid_factor.is_valid()
    False

    >>> # Test __repr__
    >>> repr(factor)  # doctest: +ELLIPSIS
    "CTQFactor(dimension=<CTQDimension.CORRECTNESS: 'correctness'>, pattern_id=1, description='WCP-1 Sequence...')"

    >>> # Test immutability (frozen=True)
    >>> try:
    ...     factor.pattern_id = 2
    ... except AttributeError:
    ...     print("Immutable")
    Immutable

    Notes
    -----
    The frozen dataclass ensures CTQFactor instances are hashable and can be
    used in sets/dicts for deduplication and lookups.
    """

    dimension: CTQDimension
    pattern_id: int
    description: str

    @property
    def dimension_name(self) -> str:
        """Get human-readable dimension name.

        Returns
        -------
        str
            Title-cased dimension name (e.g., "Correctness", "Performance")

        Examples
        --------
        >>> from tests.hybrid.lss.ctq.factors import CTQDimension, CTQFactor
        >>> factor = CTQFactor(
        ...     dimension=CTQDimension.RELIABILITY, pattern_id=19, description="Handles cancellation gracefully"
        ... )
        >>> factor.dimension_name
        'Reliability'

        >>> # Test all dimensions
        >>> dims = [
        ...     CTQDimension.CORRECTNESS,
        ...     CTQDimension.COMPLETENESS,
        ...     CTQDimension.CONSISTENCY,
        ...     CTQDimension.PERFORMANCE,
        ...     CTQDimension.RELIABILITY,
        ... ]
        >>> factors = [CTQFactor(d, 1, "test") for d in dims]
        >>> [f.dimension_name for f in factors]
        ['Correctness', 'Completeness', 'Consistency', 'Performance', 'Reliability']
        """
        return self.dimension.value.capitalize()

    def is_valid(self) -> bool:
        """Validate pattern_id is within WCP-43 range.

        Returns
        -------
        bool
            True if pattern_id is in range [1, 43], False otherwise

        Examples
        --------
        >>> from tests.hybrid.lss.ctq.factors import CTQDimension, CTQFactor
        >>> valid = CTQFactor(CTQDimension.CORRECTNESS, 1, "Valid")
        >>> valid.is_valid()
        True

        >>> boundary_low = CTQFactor(CTQDimension.CORRECTNESS, 1, "Boundary")
        >>> boundary_low.is_valid()
        True

        >>> boundary_high = CTQFactor(CTQDimension.CORRECTNESS, 43, "Boundary")
        >>> boundary_high.is_valid()
        True

        >>> invalid_low = CTQFactor(CTQDimension.CORRECTNESS, 0, "Invalid")
        >>> invalid_low.is_valid()
        False

        >>> invalid_high = CTQFactor(CTQDimension.CORRECTNESS, 44, "Invalid")
        >>> invalid_high.is_valid()
        False

        >>> negative = CTQFactor(CTQDimension.CORRECTNESS, -1, "Negative")
        >>> negative.is_valid()
        False
        """
        return 1 <= self.pattern_id <= 43
