"""Hook MSA metric dataclasses with comprehensive doctests.

This module defines measurement system analysis metrics for Knowledge Hooks,
including repeatability, reproducibility, and Gage R&R statistics adapted
for hook execution measurement.

All dataclasses are frozen (immutable) for value object semantics.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HookMSAMetrics:
    """Gage Repeatability and Reproducibility metrics for Knowledge Hooks.

    Parameters
    ----------
    repeatability : float
        Within-evaluator variation: same hook, same condition, same result?
        Measures consistency when same hook evaluates same condition repeatedly.
    reproducibility : float
        Between-evaluator variation: different evaluators, same result?
        Measures agreement when different hook instances evaluate same condition.
    gage_rr : float
        Total measurement system variation (%GRR)
        Formula: (6 * σ_total / tolerance) * 100
    ndc : int
        Number of distinct categories the measurement system can distinguish
        NDC >= 5 required for acceptable measurement system
    is_acceptable : bool
        True if gage_rr < 10% (excellent) or 10% <= gage_rr < 30% (acceptable)

    Notes
    -----
    Acceptance Criteria:
    - %GRR < 10%: Excellent measurement system
    - 10% <= %GRR < 30%: Acceptable measurement system
    - %GRR >= 30%: Unacceptable measurement system
    - NDC >= 5: Adequate discrimination capability

    Examples
    --------
    >>> # Excellent hook measurement system
    >>> metrics = HookMSAMetrics(repeatability=0.05, reproducibility=0.03, gage_rr=8.3, ndc=7, is_acceptable=True)
    >>> metrics.is_excellent
    True
    >>> abs(metrics.total_variation - 0.05831) < 0.0001
    True
    >>> metrics.is_adequate_ndc
    True

    >>> # Acceptable hook measurement system
    >>> metrics2 = HookMSAMetrics(repeatability=0.15, reproducibility=0.10, gage_rr=25.0, ndc=5, is_acceptable=True)
    >>> metrics2.is_excellent
    False
    >>> metrics2.is_acceptable
    True

    >>> # Unacceptable hook measurement system
    >>> metrics3 = HookMSAMetrics(repeatability=0.30, reproducibility=0.20, gage_rr=35.0, ndc=3, is_acceptable=False)
    >>> metrics3.is_acceptable
    False
    >>> metrics3.is_adequate_ndc
    False
    """

    repeatability: float
    reproducibility: float
    gage_rr: float
    ndc: int
    is_acceptable: bool

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
        >>> metrics = HookMSAMetrics(repeatability=0.3, reproducibility=0.4, gage_rr=30.0, ndc=5, is_acceptable=True)
        >>> metrics.total_variation
        0.5
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
        >>> metrics = HookMSAMetrics(0.05, 0.03, 8.3, 7, True)
        >>> metrics.is_excellent
        True

        >>> metrics2 = HookMSAMetrics(0.10, 0.05, 12.0, 5, True)
        >>> metrics2.is_excellent
        False
        """
        return self.gage_rr < 10.0

    @property
    def is_adequate_ndc(self) -> bool:
        """Check if NDC is adequate (>= 5).

        Returns
        -------
        bool
            True if NDC >= 5

        Examples
        --------
        >>> metrics = HookMSAMetrics(0.05, 0.03, 8.3, 7, True)
        >>> metrics.is_adequate_ndc
        True

        >>> metrics2 = HookMSAMetrics(0.05, 0.03, 8.3, 3, False)
        >>> metrics2.is_adequate_ndc
        False
        """
        return self.ndc >= 5


@dataclass(frozen=True)
class HookAccuracyMetrics:
    """Accuracy metrics for Knowledge Hook measurements.

    Measures systematic errors in hook condition evaluation.

    Parameters
    ----------
    bias : float
        Systematic error: average deviation from expected result
        Positive bias = tendency to over-evaluate (false positives)
        Negative bias = tendency to under-evaluate (false negatives)
    linearity : float
        Consistency of bias across measurement range
        Low linearity = bias changes with input magnitude
    stability : float
        Consistency of bias over time
        Low stability = bias drifts over time

    Examples
    --------
    >>> # Accurate hook with minimal bias
    >>> acc = HookAccuracyMetrics(bias=0.01, linearity=0.005, stability=0.002)
    >>> acc.is_unbiased()
    True
    >>> acc.is_linear()
    True
    >>> acc.is_stable()
    True

    >>> # Hook with systematic bias
    >>> acc2 = HookAccuracyMetrics(bias=0.15, linearity=0.05, stability=0.03)
    >>> acc2.is_unbiased()
    False
    """

    bias: float
    linearity: float
    stability: float

    def is_unbiased(self, threshold: float = 0.05) -> bool:
        """Check if bias is acceptable.

        Parameters
        ----------
        threshold : float
            Maximum acceptable bias (default 5%)

        Returns
        -------
        bool
            True if absolute bias < threshold

        Examples
        --------
        >>> acc = HookAccuracyMetrics(0.02, 0.01, 0.005)
        >>> acc.is_unbiased()
        True
        >>> acc.is_unbiased(threshold=0.01)
        False
        """
        return abs(self.bias) < threshold

    def is_linear(self, threshold: float = 0.1) -> bool:
        """Check if linearity is acceptable.

        Parameters
        ----------
        threshold : float
            Maximum acceptable linearity (default 10%)

        Returns
        -------
        bool
            True if linearity < threshold

        Examples
        --------
        >>> acc = HookAccuracyMetrics(0.02, 0.05, 0.01)
        >>> acc.is_linear()
        True
        >>> acc.is_linear(threshold=0.03)
        False
        """
        return self.linearity < threshold

    def is_stable(self, threshold: float = 0.05) -> bool:
        """Check if stability is acceptable.

        Parameters
        ----------
        threshold : float
            Maximum acceptable stability drift (default 5%)

        Returns
        -------
        bool
            True if stability < threshold

        Examples
        --------
        >>> acc = HookAccuracyMetrics(0.02, 0.05, 0.03)
        >>> acc.is_stable()
        True
        >>> acc.is_stable(threshold=0.02)
        False
        """
        return self.stability < threshold


@dataclass(frozen=True)
class HookPrecisionMetrics:
    """Precision metrics for Knowledge Hook measurements.

    Measures random variation in hook execution.

    Parameters
    ----------
    within_appraiser_variation : float
        Repeatability: variation within same evaluator
    between_appraiser_variation : float
        Reproducibility: variation between different evaluators
    total_variation : float
        Combined measurement variation

    Examples
    --------
    >>> # High precision hook
    >>> prec = HookPrecisionMetrics(
    ...     within_appraiser_variation=0.05, between_appraiser_variation=0.03, total_variation=0.058
    ... )
    >>> prec.coefficient_of_variation()
    0.058

    >>> # Low precision hook
    >>> prec2 = HookPrecisionMetrics(
    ...     within_appraiser_variation=0.20, between_appraiser_variation=0.15, total_variation=0.25
    ... )
    >>> prec2.coefficient_of_variation()
    0.25
    """

    within_appraiser_variation: float
    between_appraiser_variation: float
    total_variation: float

    def coefficient_of_variation(self) -> float:
        """Calculate coefficient of variation.

        Returns
        -------
        float
            CV = total_variation (already normalized)

        Examples
        --------
        >>> prec = HookPrecisionMetrics(0.05, 0.03, 0.058)
        >>> prec.coefficient_of_variation()
        0.058
        """
        return self.total_variation

    def is_precise(self, threshold: float = 0.1) -> bool:
        """Check if precision is acceptable.

        Parameters
        ----------
        threshold : float
            Maximum acceptable total variation (default 10%)

        Returns
        -------
        bool
            True if total_variation < threshold

        Examples
        --------
        >>> prec = HookPrecisionMetrics(0.05, 0.03, 0.058)
        >>> prec.is_precise()
        True
        >>> prec.is_precise(threshold=0.05)
        False
        """
        return self.total_variation < threshold
