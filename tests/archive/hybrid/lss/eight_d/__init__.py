"""8D Problem-Solving Methodology for WCP-43 Patterns.

The 8-Discipline (8D) Problem-Solving methodology provides systematic quality
improvement for YAWL workflow patterns.

8D Disciplines
--------------
D1. **Team Formation**: Multi-agent/pattern coordination
D2. **Problem Description**: Failure mode identification
D3. **Interim Containment**: Prevent runaway execution (max_ticks)
D4. **Root Cause Analysis**: Why patterns fail
D5. **Corrective Actions**: Topology fixes and guards
D6. **Verification**: Corrections work as expected
D7. **Prevention**: Guards, constraints, error-proofing
D8. **Recognition**: Success criteria (convergence, correctness)

WCP-43 Failure Scenarios
-------------------------
- **Deadlock**: AND-join waiting for impossible predecessor
- **Infinite Loop**: Unbounded recursion or cycles
- **Missing Status**: Tasks without status never activate
- **Invalid Topology**: Dangling flows, orphan tasks, circular dependencies

Examples
--------
>>> from kgcl.hybrid.hybrid_engine import HybridEngine
>>> from tests.hybrid.lss.eight_d.steps import EightDStep, ProblemReport
>>> # D1: Team Formation
>>> report = ProblemReport(problem_id="WCP-43-001", description="AND-join deadlock", step=EightDStep.D1_TEAM)
>>> report.step.value
'D1: Team Formation'
>>> # D3: Containment
>>> engine = HybridEngine()
>>> # max_ticks prevents runaway execution
>>> # D8: Recognition - verify success
>>> bool(report.problem_id)
True

References
----------
- Ford Motor Company 8D Problem Solving
- ISO 9001:2015 Quality Management Systems
- AIAG CQI-20: Effective Problem Solving
- YAWL Workflow Control Patterns (van der Aalst et al.)

See Also
--------
steps : EightDStep enum and ProblemReport dataclass
test_d1_d2 : D1 Team Formation + D2 Problem Description tests
test_d3_d4 : D3 Containment + D4 Root Cause Analysis tests
test_d5_d6 : D5 Corrective Actions + D6 Verification tests
test_d7_d8 : D7 Prevention + D8 Recognition tests
"""

from __future__ import annotations

from tests.hybrid.lss.eight_d.steps import EightDStep, ProblemReport

__all__ = ["EightDStep", "ProblemReport"]
