"""FMEA (Failure Mode and Effects Analysis) for WCP-43 Patterns.

This package implements systematic failure mode testing based on FMEA methodology
for YAWL Workflow Control Patterns. FMEA (Failure Mode and Effects Analysis) is a
systematic approach to identifying and prioritizing potential failure modes.

FMEA Methodology
----------------
FMEA evaluates each failure mode using three dimensions:

1. **Severity (S)**: Impact of the failure (1-10 scale)
2. **Occurrence (O)**: Likelihood of failure (1-10 scale)
3. **Detection (D)**: Ability to detect before impact (1-10 scale)

The Risk Priority Number (RPN) combines these: RPN = S × O × D

RPN Thresholds
--------------
- **Critical (RPN > 100)**: Must not occur, requires immediate mitigation
- **High (RPN 50-100)**: Requires mitigation, graceful handling
- **Medium (RPN 20-50)**: Acceptable with logging/monitoring
- **Low (RPN < 20)**: Acceptable, informational only

FMEA Categories for WCP-43
---------------------------
1. **Input Failures**: Invalid/missing topology data (FM-001, FM-002)
2. **State Failures**: Corrupted/inconsistent state transitions (FM-003)
3. **Logic Failures**: Rule misfires, infinite loops, deadlocks (FM-004, FM-005, FM-006)
4. **Resource Failures**: Memory exhaustion, timeout conditions (FM-007)
5. **Integration Failures**: EYE subprocess failures, store errors (FM-008)
6. **Concurrency Failures**: Race conditions, duplicate activations (FM-009)

Examples
--------
Calculate RPN for a failure mode:

>>> from tests.hybrid.lss.fmea.ratings import Severity, Occurrence, Detection, calculate_rpn
>>> # Example: Empty topology failure
>>> rpn = calculate_rpn(Severity.MODERATE, Occurrence.LOW, Detection.CERTAIN)
>>> rpn
15
>>> # Low risk - acceptable with graceful handling

Define a failure mode:

>>> from tests.hybrid.lss.fmea.failure_modes import FailureMode
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

References
----------
- AIAG FMEA Handbook (4th Edition)
- ISO 31000:2018 Risk Management
- YAWL Pattern Failure Analysis

See Also
--------
ratings : Severity, Occurrence, Detection rating scales and RPN calculation
failure_modes : FailureMode dataclass for structured failure documentation
test_input_failures : Tests for FM-001 (Empty Topology), FM-002 (Malformed RDF)
test_state_failures : Tests for FM-003 (Missing Task Status)
test_logic_failures : Tests for FM-004/005/006 (Deadlock, Join, Split failures)
"""

from __future__ import annotations

__all__ = ["Severity", "Occurrence", "Detection", "calculate_rpn", "FailureMode"]

from .failure_modes import FailureMode
from .ratings import Detection, Occurrence, Severity, calculate_rpn
