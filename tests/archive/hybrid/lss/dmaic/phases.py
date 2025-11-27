"""DMAIC Phase Definitions and Result Tracking.

This module defines the DMAIC phases enum and result dataclass for tracking
test execution metrics across all 5 phases of the DMAIC methodology.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DMAICPhase(str, Enum):
    """DMAIC methodology phases for WCP-43 pattern testing.

    Examples
    --------
    >>> DMAICPhase.DEFINE
    <DMAICPhase.DEFINE: 'define'>
    >>> [p.value for p in DMAICPhase]
    ['define', 'measure', 'analyze', 'improve', 'control']
    >>> len(DMAICPhase)
    5
    >>> DMAICPhase("measure")
    <DMAICPhase.MEASURE: 'measure'>
    """

    DEFINE = "define"
    MEASURE = "measure"
    ANALYZE = "analyze"
    IMPROVE = "improve"
    CONTROL = "control"


@dataclass(frozen=True)
class PhaseResult:
    """Result tracking for DMAIC phase execution.

    Examples
    --------
    >>> result = PhaseResult(DMAICPhase.DEFINE, 5, 5, 0, 234.5)
    >>> result.success_rate
    1.0
    >>> result.is_passing
    True
    >>> PhaseResult(DMAICPhase.MEASURE, 10, 7, 3, 500.0).is_passing
    False
    >>> PhaseResult(DMAICPhase.ANALYZE, 0, 0, 0, 0.0).success_rate
    0.0
    >>> PhaseResult(DMAICPhase.CONTROL, 10, 10, 0, 1000.0).avg_duration_ms
    100.0
    """

    phase: DMAICPhase
    test_count: int
    passed: int
    failed: int
    duration_ms: float

    @property
    def success_rate(self) -> float:
        """Calculate success rate (passed/total).

        Examples
        --------
        >>> PhaseResult(DMAICPhase.DEFINE, 10, 10, 0, 100.0).success_rate
        1.0
        >>> PhaseResult(DMAICPhase.MEASURE, 20, 15, 5, 200.0).success_rate
        0.75
        """
        if self.test_count == 0:
            return 0.0
        return self.passed / self.test_count

    @property
    def is_passing(self) -> bool:
        """Check if phase meets 80% success threshold.

        Examples
        --------
        >>> PhaseResult(DMAICPhase.IMPROVE, 10, 8, 2, 100.0).is_passing
        True
        >>> PhaseResult(DMAICPhase.CONTROL, 10, 7, 3, 100.0).is_passing
        False
        """
        return self.success_rate >= 0.8

    @property
    def avg_duration_ms(self) -> float:
        """Calculate average duration per test.

        Examples
        --------
        >>> PhaseResult(DMAICPhase.MEASURE, 10, 10, 0, 1000.0).avg_duration_ms
        100.0
        >>> PhaseResult(DMAICPhase.ANALYZE, 5, 5, 0, 250.0).avg_duration_ms
        50.0
        """
        if self.test_count == 0:
            return 0.0
        return self.duration_ms / self.test_count
