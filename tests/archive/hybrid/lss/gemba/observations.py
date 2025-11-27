"""Gemba Walk observation framework with dataclasses and doctests.

This module provides the core observation framework for Gemba Walk testing,
including observation points, walk results, and helper functions.

Examples
--------
>>> from tests.hybrid.lss.gemba.observations import gemba_observe, WalkResult
>>> result = gemba_observe("Task state check", "Active", "Active")
>>> result.passed
True
>>> "PASS" in repr(result)
True

>>> failing = gemba_observe("Mismatch", "Expected", "Actual")
>>> failing.passed
False
>>> "FAIL" in repr(failing)
True
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ObservationPoint:
    """Defines what to observe during a Gemba Walk.

    Examples
    --------
    >>> ObservationPoint.TASK_STATE
    'task_state'
    >>> ObservationPoint.FLOW_DIRECTION
    'flow_direction'
    >>> ObservationPoint.TIMING
    'timing'
    """

    TASK_STATE = "task_state"
    FLOW_DIRECTION = "flow_direction"
    RESOURCE_USAGE = "resource_usage"
    TIMING = "timing"
    SEQUENCE = "sequence"
    THROUGHPUT = "throughput"
    BOTTLENECK = "bottleneck"
    HANDOFF = "handoff"


@dataclass(frozen=True)
class WalkResult:
    """Result of a Gemba Walk observation.

    Parameters
    ----------
    observation : str
        What was observed
    expected : Any
        Expected value
    actual : Any
        Actual value observed
    passed : bool
        Whether observation matched expectation

    Examples
    --------
    >>> result = WalkResult("Task completed", "Active", "Active", True)
    >>> result.passed
    True
    >>> result.observation
    'Task completed'
    >>> "PASS" in repr(result)
    True

    >>> failed = WalkResult("State mismatch", 1, 2, False)
    >>> failed.passed
    False
    >>> "FAIL" in repr(failed)
    True
    """

    observation: str
    expected: Any
    actual: Any
    passed: bool

    def __repr__(self) -> str:
        """Return string representation.

        Returns
        -------
        str
            Status and observation description

        Examples
        --------
        >>> result = WalkResult("Test", 1, 1, True)
        >>> "PASS: Test" in repr(result)
        True
        """
        status = "PASS" if self.passed else "FAIL"
        return f"WalkResult({status}: {self.observation})"


@dataclass(frozen=True)
class GembaObservation:
    """A structured Gemba Walk observation with metadata.

    Parameters
    ----------
    point : str
        Observation point type (from ObservationPoint)
    description : str
        Human-readable description
    expected : Any
        Expected value or condition
    actual : Any
        Actual observed value
    tick : int | None
        Tick count when observed (optional)

    Examples
    --------
    >>> obs = GembaObservation(
    ...     point=ObservationPoint.TASK_STATE,
    ...     description="Task A should be completed",
    ...     expected="Completed",
    ...     actual="Completed",
    ...     tick=1,
    ... )
    >>> obs.passed
    True
    >>> obs.point == ObservationPoint.TASK_STATE
    True

    >>> failed_obs = GembaObservation(
    ...     point=ObservationPoint.TIMING, description="Should complete in 5 ticks", expected=5, actual=10, tick=10
    ... )
    >>> failed_obs.passed
    False
    """

    point: str
    description: str
    expected: Any
    actual: Any
    tick: int | None = None

    @property
    def passed(self) -> bool:
        """Check if observation passed.

        Returns
        -------
        bool
            True if actual matches expected

        Examples
        --------
        >>> obs = GembaObservation("state", "Match", 1, 1)
        >>> obs.passed
        True

        >>> obs2 = GembaObservation("state", "Mismatch", 1, 2)
        >>> obs2.passed
        False
        """
        return self.expected == self.actual

    def to_walk_result(self) -> WalkResult:
        """Convert to WalkResult.

        Returns
        -------
        WalkResult
            Walk result representation

        Examples
        --------
        >>> obs = GembaObservation("state", "Test", "A", "A")
        >>> result = obs.to_walk_result()
        >>> result.passed
        True
        >>> result.observation
        'Test'
        """
        return WalkResult(observation=self.description, expected=self.expected, actual=self.actual, passed=self.passed)


def gemba_observe(observation: str, expected: Any, actual: Any) -> WalkResult:
    """Record a Gemba Walk observation.

    Parameters
    ----------
    observation : str
        What is being observed
    expected : Any
        Expected value
    actual : Any
        Actual value observed

    Returns
    -------
    WalkResult
        Observation result

    Examples
    --------
    >>> result = gemba_observe("Task state", "Active", "Active")
    >>> result.passed
    True
    >>> result.observation
    'Task state'

    >>> result = gemba_observe("Count", 3, 2)
    >>> result.passed
    False
    >>> result.expected
    3
    >>> result.actual
    2
    """
    passed = expected == actual
    return WalkResult(observation, expected, actual, passed)
