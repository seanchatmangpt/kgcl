"""FMEA Rating Scales and RPN Calculation.

This module provides the standard FMEA rating scales (Severity, Occurrence, Detection)
and the Risk Priority Number (RPN) calculation. These ratings follow AIAG FMEA
Handbook (4th Edition) methodology.

Examples
--------
Calculate RPN for different failure scenarios:

>>> # Low-risk failure: Empty topology with good detection
>>> rpn = calculate_rpn(Severity.MODERATE, Occurrence.LOW, Detection.CERTAIN)
>>> rpn
15

>>> # High-risk failure: Deadlock with poor detection
>>> rpn = calculate_rpn(Severity.CRITICAL, Occurrence.MODERATE, Detection.MODERATE)
>>> rpn
225

>>> # Using class constants for clarity
>>> rpn = calculate_rpn(severity=Severity.HIGH, occurrence=Occurrence.MODERATE, detection=Detection.LOW)
>>> rpn
245

Risk level interpretation:

>>> def risk_level(rpn: int) -> str:
...     if rpn > 100:
...         return "Critical"
...     if rpn >= 50:
...         return "High"
...     if rpn >= 20:
...         return "Medium"
...     return "Low"
>>> risk_level(15)
'Low'
>>> risk_level(245)
'Critical'
"""

from __future__ import annotations


class Severity:
    """FMEA Severity ratings (1-10 scale).

    Severity measures the impact of a failure mode on system operation,
    safety, or compliance.

    Attributes
    ----------
    NONE : int
        No effect on system operation (rating: 1)
    MINOR : int
        Minor degradation, system continues (rating: 3)
    MODERATE : int
        Moderate degradation, workaround exists (rating: 5)
    HIGH : int
        High impact, no workaround available (rating: 7)
    CRITICAL : int
        Safety or compliance impact (rating: 9)
    HAZARDOUS : int
        Complete system failure (rating: 10)

    Examples
    --------
    >>> Severity.NONE
    1
    >>> Severity.CRITICAL
    9
    >>> Severity.HAZARDOUS
    10
    """

    NONE = 1  # No effect
    MINOR = 3  # Minor degradation
    MODERATE = 5  # Moderate degradation, workaround exists
    HIGH = 7  # High impact, no workaround
    CRITICAL = 9  # Safety/compliance impact
    HAZARDOUS = 10  # Complete system failure


class Occurrence:
    """FMEA Occurrence ratings (1-10 scale).

    Occurrence measures the likelihood that a failure mode will happen
    during system operation.

    Attributes
    ----------
    REMOTE : int
        Failure unlikely, <1 in 1,000,000 (rating: 1)
    LOW : int
        Low probability, 1 in 20,000 (rating: 3)
    MODERATE : int
        Occasional, 1 in 400 (rating: 5)
    HIGH : int
        Frequent, 1 in 80 (rating: 7)
    VERY_HIGH : int
        Almost certain, 1 in 8 (rating: 9)

    Examples
    --------
    >>> Occurrence.REMOTE
    1
    >>> Occurrence.VERY_HIGH
    9
    """

    REMOTE = 1  # Failure unlikely (<1 in 1,000,000)
    LOW = 3  # Low probability (1 in 20,000)
    MODERATE = 5  # Occasional (1 in 400)
    HIGH = 7  # Frequent (1 in 80)
    VERY_HIGH = 9  # Almost certain (1 in 8)


class Detection:
    """FMEA Detection ratings (1-10 scale).

    Detection measures the ability to identify a failure mode before it
    causes impact. Lower ratings indicate better detection capability.

    Attributes
    ----------
    CERTAIN : int
        Will definitely detect failure (rating: 1)
    HIGH : int
        High probability of detection (rating: 3)
    MODERATE : int
        May detect failure (rating: 5)
    LOW : int
        Low probability of detection (rating: 7)
    NONE : int
        Cannot detect before impact (rating: 10)

    Examples
    --------
    >>> Detection.CERTAIN
    1
    >>> Detection.NONE
    10
    """

    CERTAIN = 1  # Will definitely detect
    HIGH = 3  # High probability of detection
    MODERATE = 5  # May detect
    LOW = 7  # Low probability of detection
    NONE = 10  # Cannot detect


def calculate_rpn(severity: int, occurrence: int, detection: int) -> int:
    """Calculate Risk Priority Number (RPN).

    RPN is the product of Severity, Occurrence, and Detection ratings.
    Higher RPN values indicate higher risk requiring immediate attention.

    Parameters
    ----------
    severity : int
        Severity rating (1-10), impact of failure
    occurrence : int
        Occurrence rating (1-10), likelihood of failure
    detection : int
        Detection rating (1-10), ability to detect failure

    Returns
    -------
    int
        RPN value (1-1000)

    Examples
    --------
    Low-risk scenario (good detection, rare occurrence):

    >>> calculate_rpn(severity=Severity.MODERATE, occurrence=Occurrence.LOW, detection=Detection.CERTAIN)
    15

    Medium-risk scenario:

    >>> calculate_rpn(severity=Severity.HIGH, occurrence=Occurrence.MODERATE, detection=Detection.MODERATE)
    175

    Demonstrating the multiplication:

    >>> # Minimum RPN (best case)
    >>> calculate_rpn(1, 1, 1)
    1
    >>> # Maximum RPN (worst case)
    >>> calculate_rpn(10, 10, 10)
    1000

    Notes
    -----
    RPN thresholds for action:
    - RPN > 100: Critical, requires immediate mitigation
    - RPN 50-100: High, requires mitigation planning
    - RPN 20-50: Medium, acceptable with monitoring
    - RPN < 20: Low, acceptable

    References
    ----------
    AIAG FMEA Handbook (4th Edition), Section 3.2.4
    """
    return severity * occurrence * detection
