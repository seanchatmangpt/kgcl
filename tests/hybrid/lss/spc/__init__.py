"""Statistical Process Control (SPC) for Workflow Pattern Quality Analysis.

This package implements manufacturing-grade Six Sigma quality metrics for workflow
pattern execution. It provides control limits, process capability indices, and
statistical stability analysis following ASQ standards.

Modules
-------
metrics
    Core SPC data structures: SPCMetrics, ControlLimits, ProcessCapability
test_control_limits
    Control limit calculation and outlier detection tests
test_process_capability
    Cp/Cpk process capability index tests
test_pattern_spc
    WCP pattern SPC validation tests

SPC Concepts
------------
- **Control Limits**: UCL/LCL define acceptable variation (mean ± 3σ)
- **Process Capability**: Cp (potential) and Cpk (actual) measure quality level
- **Coefficient of Variation**: CV = (σ/μ) × 100 indicates relative variability
- **Run Charts**: Detect special cause variation over time
- **Moving Range**: Track measurement-to-measurement changes

Quality Standards
-----------------
- Cpk ≥ 1.33: Capable process (industry standard)
- Cpk ≥ 2.0: Six Sigma world-class process
- CV < 10%: Low variation
- CV < 20%: Acceptable variation

References
----------
- Six Sigma: https://asq.org/quality-resources/six-sigma
- SPC: https://asq.org/quality-resources/statistical-process-control
- YAWL WCP: http://www.workflowpatterns.com

Examples
--------
>>> from tests.hybrid.lss.spc.metrics import calculate_spc_metrics
>>> measurements = [10.0, 10.2, 9.8, 10.1, 9.9]
>>> spc = calculate_spc_metrics(measurements, usl=12.0, lsl=8.0)
>>> spc.is_capable()
True
>>> spc.is_in_control(10.1)  # Within control limits (LCL=9.53, UCL=10.47)
True
"""

from __future__ import annotations

__all__ = [
    "SPCMetrics",
    "ProcessCapability",
    "calculate_spc_metrics",
    "calculate_moving_range",
    "check_run_chart_stability",
]

from tests.hybrid.lss.spc.metrics import (
    ProcessCapability,
    SPCMetrics,
    calculate_moving_range,
    calculate_spc_metrics,
    check_run_chart_stability,
)
