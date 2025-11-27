"""FMEA Failure Mode Data Structures.

This module provides structured representations of failure modes using frozen
dataclasses for immutability and type safety.

Examples
--------
Create a failure mode with automatic RPN calculation:

>>> from tests.hybrid.lss.fmea.ratings import Severity, Occurrence, Detection
>>> fm = FailureMode(
...     id="FM-001",
...     name="Empty Topology",
...     description="System receives empty or null topology",
...     effect="No tasks to process, potential null pointer errors",
...     severity=Severity.MODERATE,
...     occurrence=Occurrence.LOW,
...     detection=Detection.CERTAIN,
... )
>>> fm.rpn
15
>>> fm.risk_level()
'Low'

Create a critical failure mode:

>>> fm_critical = FailureMode(
...     id="FM-004",
...     name="Circular Dependency",
...     description="Tasks form a cycle with mutual dependencies",
...     effect="Infinite loop or deadlock",
...     severity=Severity.CRITICAL,
...     occurrence=Occurrence.LOW,
...     detection=Detection.MODERATE,
... )
>>> fm_critical.rpn
135
>>> fm_critical.risk_level()
'Critical'

Immutability ensures data integrity:

>>> try:
...     fm.severity = 10  # Attempt to modify
... except AttributeError as e:
...     print("Frozen dataclass prevents modification")
Frozen dataclass prevents modification

Compare failure modes by RPN:

>>> fm_low = FailureMode("FM-A", "Test A", "desc", "effect", 3, 3, 1)
>>> fm_high = FailureMode("FM-B", "Test B", "desc", "effect", 9, 7, 5)
>>> fm_low.rpn < fm_high.rpn
True
>>> fm_low.rpn, fm_high.rpn
(9, 315)
"""

from __future__ import annotations

from dataclasses import dataclass

from .ratings import calculate_rpn


@dataclass(frozen=True)
class FailureMode:
    """Structured representation of a failure mode.

    A failure mode describes a specific way in which a system component can fail,
    along with its impact, likelihood, and detectability. Frozen for immutability.

    Parameters
    ----------
    id : str
        Unique failure mode identifier (e.g., "FM-001")
    name : str
        Short descriptive name
    description : str
        Detailed description of the failure mode
    effect : str
        Impact on system operation
    severity : int
        Severity rating (1-10)
    occurrence : int
        Occurrence rating (1-10)
    detection : int
        Detection rating (1-10)
    mitigation : str, optional
        Mitigation strategy or test approach

    Attributes
    ----------
    rpn : int
        Risk Priority Number (severity × occurrence × detection)

    Examples
    --------
    Create a low-risk failure mode:

    >>> from tests.hybrid.lss.fmea.ratings import Severity, Occurrence, Detection
    >>> fm = FailureMode(
    ...     id="FM-001",
    ...     name="Empty Topology",
    ...     description="System receives empty or null topology",
    ...     effect="No tasks to process",
    ...     severity=Severity.MODERATE,
    ...     occurrence=Occurrence.LOW,
    ...     detection=Detection.CERTAIN,
    ... )
    >>> fm.id
    'FM-001'
    >>> fm.rpn
    15
    >>> fm.risk_level()
    'Low'

    Create a critical failure mode with mitigation:

    >>> fm_deadlock = FailureMode(
    ...     id="FM-004",
    ...     name="Circular Dependency",
    ...     description="Tasks form a cycle",
    ...     effect="System hangs indefinitely",
    ...     severity=Severity.CRITICAL,
    ...     occurrence=Occurrence.LOW,
    ...     detection=Detection.MODERATE,
    ...     mitigation="Enforce max_ticks limit to prevent infinite loops",
    ... )
    >>> fm_deadlock.rpn
    135
    >>> fm_deadlock.risk_level()
    'Critical'

    Notes
    -----
    The frozen=True parameter ensures immutability, making FailureMode instances
    safe to use as dictionary keys or in sets.

    See Also
    --------
    ratings.calculate_rpn : Compute RPN from severity, occurrence, detection
    """

    id: str
    name: str
    description: str
    effect: str
    severity: int
    occurrence: int
    detection: int
    mitigation: str | None = None

    @property
    def rpn(self) -> int:
        """Calculate Risk Priority Number.

        Returns
        -------
        int
            RPN value (severity × occurrence × detection)

        Examples
        --------
        >>> from tests.hybrid.lss.fmea.ratings import Severity, Occurrence, Detection
        >>> fm = FailureMode("FM-001", "Test", "desc", "effect", Severity.HIGH, Occurrence.MODERATE, Detection.LOW)
        >>> fm.rpn  # Severity.HIGH(7) * Occurrence.MODERATE(5) * Detection.LOW(7) = 245
        245

        RPN is always product of three ratings:

        >>> fm2 = FailureMode("FM-002", "Test", "d", "e", 9, 5, 3)
        >>> fm2.rpn == 9 * 5 * 3
        True
        """
        return calculate_rpn(self.severity, self.occurrence, self.detection)

    def risk_level(self) -> str:
        """Classify risk level based on RPN.

        Returns
        -------
        str
            One of: "Critical", "High", "Medium", "Low"

        Examples
        --------
        >>> fm_low = FailureMode("FM-A", "Test", "d", "e", 3, 3, 1)
        >>> fm_low.risk_level()
        'Low'

        >>> fm_medium = FailureMode("FM-B", "Test", "d", "e", 5, 4, 2)
        >>> fm_medium.risk_level()  # RPN=40, which is 20 <= 40 < 50
        'Medium'

        >>> fm_high = FailureMode("FM-C", "Test", "d", "e", 7, 5, 2)
        >>> fm_high.risk_level()  # RPN=70, which is 50 <= 70 <= 100
        'High'

        >>> fm_critical = FailureMode("FM-D", "Test", "d", "e", 9, 7, 5)
        >>> fm_critical.risk_level()
        'Critical'

        Edge cases at boundaries:

        >>> FailureMode("FM-E", "Test", "d", "e", 5, 4, 1).risk_level()  # RPN=20
        'Medium'
        >>> FailureMode("FM-F", "Test", "d", "e", 5, 5, 2).risk_level()  # RPN=50
        'High'
        >>> FailureMode("FM-G", "Test", "d", "e", 5, 5, 5).risk_level()  # RPN=125
        'Critical'

        Notes
        -----
        Risk level thresholds:
        - RPN > 100: Critical (requires immediate action)
        - RPN 50-100: High (requires mitigation)
        - RPN 20-50: Medium (acceptable with monitoring)
        - RPN < 20: Low (acceptable)
        """
        rpn = self.rpn
        if rpn > 100:
            return "Critical"
        if rpn >= 50:
            return "High"
        if rpn >= 20:
            return "Medium"
        return "Low"
