"""Poka-Yoke (Error-Proofing) Test Suite for WCP-43 Patterns.

This package implements systematic error-proofing validation based on Poka-Yoke principles
developed by Shigeo Shingo for the Toyota Production System.

Poka-Yoke Philosophy
--------------------
Error-proofing aims to eliminate defects by preventing, detecting, or correcting errors
at their source. The three core principles:

1. **Prevention**: Make it impossible to make errors (Contact Methods)
2. **Detection**: Detect errors immediately when they occur (Fixed-Value Methods)
3. **Correction**: Automatically correct or flag errors (Motion-Step Methods)

Poka-Yoke Functions
-------------------
The three regulatory functions by severity:

1. **SHUTDOWN**: Safety-critical errors that stop the process immediately
   - Used for: Infinite recursion, critical section violations, invalid cancellation
   - Examples: WCP-10 (Arbitrary Cycles), WCP-22 (Recursion), WCP-39 (Critical Section)

2. **CONTROL**: Process regulation that gates continuation until corrected
   - Used for: Synchronization, threshold waiting, milestone gating
   - Examples: WCP-3 (AND-Join), WCP-18 (Milestone), WCP-30 (Partial Join)

3. **WARNING**: Non-critical alerts that inform without stopping
   - Used for: Missing optional fields, orphaned resources, monitoring
   - Examples: Tasks without status, empty workflows, orphan flows

Poka-Yoke Methods
-----------------
The three detection methods:

1. **Contact Method**: Physical/logical constraints that prevent errors
   - Examples: Type validation, URI format validation, prefix validation

2. **Fixed-Value Method**: Ensure correct quantity/count/selection
   - Examples: Status vocabulary, split/join types, pattern catalog integrity

3. **Motion-Step Method**: Ensure correct sequence of operations
   - Examples: Flow integrity, idempotency, state transition validation

Error Classifications
--------------------
Six error classes tested:

- **Type 1**: Input validation errors (bad topology, malformed URIs)
- **Type 2**: State transition errors (invalid status changes)
- **Type 3**: Sequence errors (wrong order of operations)
- **Type 4**: Omission errors (missing required elements)
- **Type 5**: Selection errors (wrong choice from valid set)
- **Type 6**: Resource constraint errors (memory, ticks, limits)

Module Organization
-------------------
- **types.py**: Core enums (PokaYokeFunction, PokaYokeMethod) with doctests
- **test_shutdown.py**: SHUTDOWN function tests (safety-critical)
- **test_control.py**: CONTROL function tests (gating/regulation)
- **test_warning.py**: WARNING function tests (alerting/monitoring)
- **test_validation.py**: Input validation tests (all error types)

References
----------
- Shigeo Shingo: "Zero Quality Control: Source Inspection and the Poka-Yoke System"
- Toyota Production System (TPS): Error-Proofing Methods
- IEC 62366: Usability Engineering for Medical Devices
- IEC 61508: Functional Safety of Safety-Related Systems

Examples
--------
>>> from tests.hybrid.lss.poka_yoke.types import PokaYokeFunction, PokaYokeMethod
>>> func = PokaYokeFunction.SHUTDOWN
>>> func.name
'SHUTDOWN'
>>> method = PokaYokeMethod.CONTACT
>>> method.value
'Contact Method'
"""

from __future__ import annotations

__all__ = ["PokaYokeFunction", "PokaYokeMethod"]

from tests.hybrid.lss.poka_yoke.types import PokaYokeFunction, PokaYokeMethod
