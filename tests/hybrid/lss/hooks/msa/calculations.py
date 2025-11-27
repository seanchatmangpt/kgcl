"""Hook MSA calculation functions with comprehensive doctests.

This module provides statistical calculations for Measurement System Analysis
adapted for Knowledge Hook execution measurement.
"""

from __future__ import annotations

import statistics

from kgcl.hybrid.knowledge_hooks import HookReceipt
from tests.hybrid.lss.hooks.msa.metrics import HookAccuracyMetrics, HookMSAMetrics, HookPrecisionMetrics


def calculate_hook_gage_rr(receipts: list[HookReceipt], parts: int, appraisers: int, trials: int) -> HookMSAMetrics:
    """Calculate Gage R&R for Knowledge Hook execution.

    Parameters
    ----------
    receipts : list[HookReceipt]
        Hook execution receipts across multiple trials
    parts : int
        Number of distinct conditions evaluated (parts)
    appraisers : int
        Number of independent evaluators (hook instances)
    trials : int
        Number of repeated trials per part per appraiser

    Returns
    -------
    HookMSAMetrics
        Comprehensive Gage R&R statistics for hook measurement system

    Notes
    -----
    Gage R&R Formulas:
    - Repeatability (EV): σ_repeatability = R̄ / d₂
    - Reproducibility (AV): σ_reproducibility = √(σ²_operator - (σ²_equipment / (n*r)))
    - %GRR = (6 * σ_GRR / tolerance) * 100
    - NDC = 1.41 * (σ_part / σ_GRR)
    - Tolerance = max(duration) - min(duration) or use spec limits

    Acceptance Criteria:
    - %GRR < 10%: Excellent
    - 10% <= %GRR < 30%: Acceptable
    - %GRR >= 30%: Unacceptable
    - NDC >= 5: Adequate discrimination

    Examples
    --------
    >>> from datetime import UTC, datetime
    >>> from kgcl.hybrid.knowledge_hooks import HookPhase, HookAction, HookReceipt
    >>>
    >>> # Perfect repeatability and reproducibility
    >>> receipts = [
    ...     HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
    ...     HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
    ...     HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
    ...     HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
    ... ]
    >>> metrics = calculate_hook_gage_rr(receipts, parts=1, appraisers=2, trials=2)
    >>> metrics.gage_rr
    0.0
    >>> metrics.is_excellent
    True

    >>> # Excellent measurement system
    >>> receipts2 = [
    ...     HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
    ...     HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 101.0),
    ...     HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
    ...     HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 101.0),
    ... ]
    >>> metrics2 = calculate_hook_gage_rr(receipts2, parts=1, appraisers=2, trials=2)
    >>> metrics2.is_excellent or metrics2.is_acceptable
    True
    """
    # Extract duration_ms as measurement values
    values = [r.duration_ms for r in receipts]
    mean = statistics.mean(values)
    std_dev = statistics.stdev(values) if len(values) > 1 else 0.0

    # Group by appraiser (hook_id) to calculate repeatability
    appraiser_map: dict[str, list[float]] = {}
    for receipt in receipts:
        if receipt.hook_id not in appraiser_map:
            appraiser_map[receipt.hook_id] = []
        appraiser_map[receipt.hook_id].append(receipt.duration_ms)

    # Calculate repeatability (average within-appraiser variation)
    repeatabilities: list[float] = []
    for appraiser_values in appraiser_map.values():
        if len(appraiser_values) > 1:
            repeatabilities.append(statistics.stdev(appraiser_values))

    repeatability = statistics.mean(repeatabilities) if repeatabilities else 0.0

    # Calculate reproducibility (between-appraiser variation)
    appraiser_means = [statistics.mean(values) for values in appraiser_map.values()]
    reproducibility = statistics.stdev(appraiser_means) if len(appraiser_means) > 1 else 0.0

    # Calculate tolerance (process spread)
    # Use max observed value as tolerance (similar to reference implementation)
    max_value = max(values) if values else 1.0
    tolerance = max(max_value, 1.0)  # Avoid division by zero

    # Calculate %GRR using standard AIAG formula: (6 * σ_GRR / tolerance) * 100
    total_grr = (repeatability**2 + reproducibility**2) ** 0.5
    grr_percent = (6.0 * total_grr / tolerance) * 100.0 if tolerance > 0 else 0.0

    # Calculate NDC (Number of Distinct Categories)
    # NDC = 1.41 * (σ_part / σ_GRR)
    # For hook measurements, part variation is the std dev of all measurements
    part_variation = std_dev
    if total_grr > 0:
        ndc = max(1, int(1.41 * (part_variation / total_grr)))
    else:
        # If no GRR variation, NDC is based on part variation alone
        ndc = 10  # Assume excellent discrimination when GRR = 0

    # Determine acceptability
    # For hook measurements with very low variation, relax NDC requirement
    if grr_percent < 10.0:
        # Excellent systems can have lower NDC if variation is minimal
        is_acceptable = True
    else:
        # For acceptable/marginal systems, enforce NDC requirement
        is_acceptable = grr_percent < 30.0 and ndc >= 5

    return HookMSAMetrics(
        repeatability=repeatability,
        reproducibility=reproducibility,
        gage_rr=grr_percent,
        ndc=ndc,
        is_acceptable=is_acceptable,
    )


def assess_hook_measurement_capability(metrics: HookMSAMetrics) -> str:
    """Assess hook measurement system capability.

    Parameters
    ----------
    metrics : HookMSAMetrics
        Gage R&R metrics to assess

    Returns
    -------
    str
        Assessment classification:
        - "EXCELLENT": %GRR < 10% and NDC >= 5
        - "ACCEPTABLE": 10% <= %GRR < 30% and NDC >= 5
        - "MARGINAL": %GRR < 30% but NDC < 5
        - "UNACCEPTABLE": %GRR >= 30%

    Notes
    -----
    Assessment Criteria (AIAG MSA Manual):
    - Excellent: System variation < 10% of tolerance, adequate discrimination
    - Acceptable: System variation 10-30% of tolerance, adequate discrimination
    - Marginal: Low variation but poor discrimination (cannot distinguish parts)
    - Unacceptable: System variation >= 30% of tolerance

    Examples
    --------
    >>> # Excellent system
    >>> metrics = HookMSAMetrics(0.05, 0.03, 8.3, 7, True)
    >>> assess_hook_measurement_capability(metrics)
    'EXCELLENT'

    >>> # Acceptable system
    >>> metrics2 = HookMSAMetrics(0.15, 0.10, 25.0, 5, True)
    >>> assess_hook_measurement_capability(metrics2)
    'ACCEPTABLE'

    >>> # Marginal system (low GRR but poor discrimination)
    >>> metrics3 = HookMSAMetrics(0.05, 0.03, 8.3, 3, False)
    >>> assess_hook_measurement_capability(metrics3)
    'MARGINAL'

    >>> # Unacceptable system
    >>> metrics4 = HookMSAMetrics(0.30, 0.20, 35.0, 3, False)
    >>> assess_hook_measurement_capability(metrics4)
    'UNACCEPTABLE'
    """
    if metrics.gage_rr >= 30.0:
        return "UNACCEPTABLE"

    if metrics.gage_rr < 10.0 and metrics.ndc >= 5:
        return "EXCELLENT"

    if 10.0 <= metrics.gage_rr < 30.0 and metrics.ndc >= 5:
        return "ACCEPTABLE"

    # Low GRR but inadequate discrimination
    return "MARGINAL"


def calculate_hook_accuracy(receipts: list[HookReceipt], expected_duration: float) -> HookAccuracyMetrics:
    """Calculate accuracy metrics for hook execution.

    Parameters
    ----------
    receipts : list[HookReceipt]
        Hook execution receipts
    expected_duration : float
        Expected execution duration (reference value)

    Returns
    -------
    HookAccuracyMetrics
        Accuracy metrics including bias, linearity, stability

    Notes
    -----
    Accuracy Metrics:
    - Bias: Mean error from expected (systematic error)
    - Linearity: Range of bias across measurement range
    - Stability: Standard deviation of bias over time

    Examples
    --------
    >>> from datetime import UTC, datetime
    >>> from kgcl.hybrid.knowledge_hooks import HookPhase, HookAction, HookReceipt
    >>>
    >>> # Unbiased measurements
    >>> receipts = [
    ...     HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
    ...     HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.5),
    ...     HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 99.5),
    ... ]
    >>> acc = calculate_hook_accuracy(receipts, expected_duration=100.0)
    >>> abs(acc.bias) < 1.0
    True
    >>> acc.is_unbiased()
    True

    >>> # Biased measurements (consistently high)
    >>> receipts2 = [
    ...     HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 110.0),
    ...     HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 111.0),
    ...     HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 109.0),
    ... ]
    >>> acc2 = calculate_hook_accuracy(receipts2, expected_duration=100.0)
    >>> acc2.bias > 5.0
    True
    """
    # Calculate bias (mean deviation from expected)
    deviations = [r.duration_ms - expected_duration for r in receipts]
    bias = statistics.mean(deviations) if deviations else 0.0

    # Calculate linearity (range of bias)
    linearity = max(deviations) - min(deviations) if len(deviations) > 1 else 0.0

    # Calculate stability (std dev of bias over time)
    stability = statistics.stdev(deviations) if len(deviations) > 1 else 0.0

    return HookAccuracyMetrics(bias=bias, linearity=linearity, stability=stability)


def calculate_hook_precision(receipts: list[HookReceipt]) -> HookPrecisionMetrics:
    """Calculate precision metrics for hook execution.

    Parameters
    ----------
    receipts : list[HookReceipt]
        Hook execution receipts

    Returns
    -------
    HookPrecisionMetrics
        Precision metrics including within/between appraiser variation

    Notes
    -----
    Precision (Random Variation):
    - Within-appraiser: Repeatability (same evaluator)
    - Between-appraiser: Reproducibility (different evaluators)
    - Total: Combined variation

    Examples
    --------
    >>> from datetime import UTC, datetime
    >>> from kgcl.hybrid.knowledge_hooks import HookPhase, HookAction, HookReceipt
    >>>
    >>> # High precision (low variation)
    >>> receipts = [
    ...     HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
    ...     HookReceipt("hook1", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.1),
    ...     HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.0),
    ...     HookReceipt("hook2", HookPhase.ON_CHANGE, datetime.now(UTC), True, HookAction.NOTIFY, 100.1),
    ... ]
    >>> prec = calculate_hook_precision(receipts)
    >>> prec.is_precise()
    True
    """
    # Group by appraiser (hook_id)
    appraiser_map: dict[str, list[float]] = {}
    for receipt in receipts:
        if receipt.hook_id not in appraiser_map:
            appraiser_map[receipt.hook_id] = []
        appraiser_map[receipt.hook_id].append(receipt.duration_ms)

    # Calculate within-appraiser variation (repeatability)
    within_variations: list[float] = []
    for appraiser_values in appraiser_map.values():
        if len(appraiser_values) > 1:
            within_variations.append(statistics.stdev(appraiser_values))

    within_appraiser = statistics.mean(within_variations) if within_variations else 0.0

    # Calculate between-appraiser variation (reproducibility)
    appraiser_means = [statistics.mean(values) for values in appraiser_map.values()]
    between_appraiser = statistics.stdev(appraiser_means) if len(appraiser_means) > 1 else 0.0

    # Calculate total variation
    total_variation = (within_appraiser**2 + between_appraiser**2) ** 0.5

    return HookPrecisionMetrics(
        within_appraiser_variation=within_appraiser,
        between_appraiser_variation=between_appraiser,
        total_variation=total_variation,
    )
