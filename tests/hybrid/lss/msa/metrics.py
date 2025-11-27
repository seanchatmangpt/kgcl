"""MSA metric dataclasses with comprehensive doctests.

This module defines core measurement system analysis metrics including
individual measurement results and aggregate Gage R&R statistics.

All dataclasses are frozen (immutable) for value object semantics.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MeasurementResult:
    """Single measurement trial for MSA study.

    Parameters
    ----------
    trial : int
        Sequential trial identifier (1, 2, 3...)
    value : float
        The measured value from this trial
    operator : str
        Identifier for who/what made the measurement
    expected : float | None, optional
        Expected/reference value (if known)

    Examples
    --------
    >>> m = MeasurementResult(trial=1, value=10.5, operator="engine1", expected=10.0)
    >>> m.bias
    0.5
    >>> m.percent_error
    5.0

    >>> # Measurement without expected value
    >>> m2 = MeasurementResult(trial=2, value=20.3, operator="engine2")
    >>> m2.bias is None
    True
    >>> m2.percent_error is None
    True

    >>> # Zero expected value (division by zero protection)
    >>> m3 = MeasurementResult(trial=3, value=1.0, operator="engine3", expected=0.0)
    >>> m3.percent_error is None
    True
    """

    trial: int
    value: float
    operator: str
    expected: float | None = None

    @property
    def bias(self) -> float | None:
        """Calculate measurement bias (error from expected).

        Returns
        -------
        float | None
            Difference between measured and expected (None if no expected value).

        Examples
        --------
        >>> m = MeasurementResult(trial=1, value=10.5, operator="op1", expected=10.0)
        >>> m.bias
        0.5

        >>> # Negative bias (underestimation)
        >>> m2 = MeasurementResult(trial=2, value=9.5, operator="op1", expected=10.0)
        >>> m2.bias
        -0.5
        """
        if self.expected is None:
            return None
        return self.value - self.expected

    @property
    def percent_error(self) -> float | None:
        """Calculate percent error from expected value.

        Returns
        -------
        float | None
            Percentage error (None if no expected value or division by zero).

        Examples
        --------
        >>> m = MeasurementResult(trial=1, value=10.5, operator="op1", expected=10.0)
        >>> m.percent_error
        5.0

        >>> # Large negative error
        >>> m2 = MeasurementResult(trial=2, value=8.0, operator="op1", expected=10.0)
        >>> m2.percent_error
        -20.0

        >>> # No expected value
        >>> m3 = MeasurementResult(trial=3, value=10.0, operator="op1")
        >>> m3.percent_error is None
        True
        """
        if self.expected is None or self.expected == 0:
            return None
        bias = self.bias
        if bias is None:
            return None
        return (bias / self.expected) * 100.0


@dataclass(frozen=True)
class GageRR:
    """Gage Repeatability and Reproducibility (R&R) statistics.

    Parameters
    ----------
    repeatability : float
        Within-operator variation (standard deviation)
    reproducibility : float
        Between-operator variation (standard deviation)
    grr_percent : float
        Total %GRR = (6 * σ_total / tolerance) * 100
    tolerance : float
        Measurement tolerance used for %GRR calculation
    mean : float
        Mean of all measurements
    std_dev : float
        Total standard deviation

    Notes
    -----
    %GRR Formula: 6σ_total / tolerance * 100
    - 6σ represents 99.73% coverage (±3 standard deviations)
    - Total variance: σ²_total = σ²_repeatability + σ²_reproducibility

    Examples
    --------
    >>> # Excellent measurement system (%GRR < 10%)
    >>> grr = GageRR(repeatability=0.05, reproducibility=0.03, grr_percent=8.3, tolerance=1.0, mean=10.0, std_dev=0.058)
    >>> grr.is_excellent
    True
    >>> grr.is_acceptable
    True
    >>> abs(grr.total_variation - 0.05831) < 0.001
    True

    >>> # Acceptable measurement system (10% ≤ %GRR < 30%)
    >>> grr2 = GageRR(
    ...     repeatability=0.15, reproducibility=0.10, grr_percent=25.0, tolerance=1.0, mean=10.0, std_dev=0.18
    ... )
    >>> grr2.is_excellent
    False
    >>> grr2.is_acceptable
    True

    >>> # Unacceptable measurement system (%GRR ≥ 30%)
    >>> grr3 = GageRR(
    ...     repeatability=0.30, reproducibility=0.20, grr_percent=35.0, tolerance=1.0, mean=10.0, std_dev=0.36
    ... )
    >>> grr3.is_excellent
    False
    >>> grr3.is_acceptable
    False

    >>> # Zero tolerance edge case
    >>> grr4 = GageRR(repeatability=0.0, reproducibility=0.0, grr_percent=0.0, tolerance=0.0, mean=10.0, std_dev=0.0)
    >>> grr4.is_excellent
    True
    """

    repeatability: float
    reproducibility: float
    grr_percent: float
    tolerance: float
    mean: float
    std_dev: float

    @property
    def total_variation(self) -> float:
        """Calculate total measurement variation.

        Returns
        -------
        float
            Combined repeatability and reproducibility variation.

        Notes
        -----
        σ_total = √(σ²_repeatability + σ²_reproducibility)

        Examples
        --------
        >>> grr = GageRR(
        ...     repeatability=0.3, reproducibility=0.4, grr_percent=30.0, tolerance=1.0, mean=10.0, std_dev=0.5
        ... )
        >>> grr.total_variation
        0.5

        >>> # Zero variation
        >>> grr2 = GageRR(
        ...     repeatability=0.0, reproducibility=0.0, grr_percent=0.0, tolerance=1.0, mean=10.0, std_dev=0.0
        ... )
        >>> grr2.total_variation
        0.0
        """
        return (self.repeatability**2 + self.reproducibility**2) ** 0.5

    @property
    def is_excellent(self) -> bool:
        """Check if measurement system is excellent (%GRR < 10%).

        Returns
        -------
        bool
            True if %GRR < 10%

        Examples
        --------
        >>> grr = GageRR(0.05, 0.03, 8.3, 1.0, 10.0, 0.058)
        >>> grr.is_excellent
        True

        >>> grr2 = GageRR(0.10, 0.05, 12.0, 1.0, 10.0, 0.10)
        >>> grr2.is_excellent
        False
        """
        return self.grr_percent < 10.0

    @property
    def is_acceptable(self) -> bool:
        """Check if measurement system is acceptable (%GRR < 30%).

        Returns
        -------
        bool
            True if %GRR < 30%

        Examples
        --------
        >>> grr = GageRR(0.15, 0.10, 25.0, 1.0, 10.0, 0.18)
        >>> grr.is_acceptable
        True

        >>> grr2 = GageRR(0.30, 0.20, 35.0, 1.0, 10.0, 0.36)
        >>> grr2.is_acceptable
        False
        """
        return self.grr_percent < 30.0
