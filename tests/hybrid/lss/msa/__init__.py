"""Measurement System Analysis (MSA) module for WCP-43 patterns.

This package implements MSA methodology to validate measurement systems with:
- **Accuracy**: Measurements match expected values (bias)
- **Precision**: Repeatability of measurements (consistency)
- **Linearity**: Consistency across measurement range
- **Stability**: Measurements consistent over time
- **Gage R&R**: Reproducibility and repeatability

MSA Acceptance Criteria
-----------------------
- %GRR < 10%: Excellent measurement system
- %GRR 10-30%: Acceptable (may need improvement)
- %GRR > 30%: Unacceptable, system needs improvement
- Accuracy: Within ±2% of true value
- Precision: CV (coefficient of variation) < 5%

References
----------
- AIAG MSA Manual (4th Edition)
- ISO 22514-7:2021 Statistical methods in process management
- ASME B89.7.3.1 Guidelines for decision rules
"""

from __future__ import annotations

__all__ = ["GageRR", "MeasurementResult", "calculate_grr", "calculate_precision"]

from tests.hybrid.lss.msa.calculations import calculate_grr, calculate_precision
from tests.hybrid.lss.msa.metrics import GageRR, MeasurementResult
