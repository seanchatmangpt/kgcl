"""8D Problem-Solving Steps and Data Structures.

This module defines the EightDStep enum and ProblemReport dataclass for
tracking 8D problem-solving workflows.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EightDStep(Enum):
    """8D Problem-Solving Methodology Steps.

    Each step represents a discipline in the 8D process for systematic
    quality improvement.

    Attributes
    ----------
    D1_TEAM : str
        Team Formation - Establish cross-functional team
    D2_PROBLEM : str
        Problem Description - Define and quantify the problem
    D3_CONTAINMENT : str
        Interim Containment - Protect customers with interim actions
    D4_ROOT_CAUSE : str
        Root Cause Analysis - Identify and verify root causes
    D5_CORRECTIVE : str
        Corrective Actions - Choose and verify permanent corrections
    D6_VERIFICATION : str
        Verification - Validate corrections resolve problem
    D7_PREVENTION : str
        Prevention - Prevent recurrence through systemic changes
    D8_RECOGNITION : str
        Recognition - Recognize team and document learnings

    Examples
    --------
    >>> # D1: Team Formation
    >>> step = EightDStep.D1_TEAM
    >>> step.value
    'D1: Team Formation'
    >>> step.name
    'D1_TEAM'

    >>> # D2: Problem Description
    >>> EightDStep.D2_PROBLEM.value
    'D2: Problem Description'

    >>> # D3: Interim Containment
    >>> EightDStep.D3_CONTAINMENT.value
    'D3: Interim Containment'

    >>> # D4: Root Cause Analysis
    >>> EightDStep.D4_ROOT_CAUSE.value
    'D4: Root Cause Analysis'

    >>> # D5: Corrective Actions
    >>> EightDStep.D5_CORRECTIVE.value
    'D5: Corrective Actions'

    >>> # D6: Verification
    >>> EightDStep.D6_VERIFICATION.value
    'D6: Verification'

    >>> # D7: Prevention
    >>> EightDStep.D7_PREVENTION.value
    'D7: Prevention'

    >>> # D8: Recognition
    >>> EightDStep.D8_RECOGNITION.value
    'D8: Recognition'

    >>> # Iterate through all steps
    >>> steps = list(EightDStep)
    >>> len(steps)
    8
    >>> steps[0]
    <EightDStep.D1_TEAM: 'D1: Team Formation'>
    """

    D1_TEAM = "D1: Team Formation"
    D2_PROBLEM = "D2: Problem Description"
    D3_CONTAINMENT = "D3: Interim Containment"
    D4_ROOT_CAUSE = "D4: Root Cause Analysis"
    D5_CORRECTIVE = "D5: Corrective Actions"
    D6_VERIFICATION = "D6: Verification"
    D7_PREVENTION = "D7: Prevention"
    D8_RECOGNITION = "D8: Recognition"


@dataclass(frozen=True)
class ProblemReport:
    """Problem report for 8D problem-solving workflow.

    Immutable dataclass representing a problem being addressed through the
    8D methodology.

    Parameters
    ----------
    problem_id : str
        Unique identifier for the problem (e.g., "WCP-43-001")
    description : str
        Brief description of the problem
    step : EightDStep
        Current 8D step being executed
    root_cause : str | None
        Identified root cause (populated in D4), by default None
    corrective_action : str | None
        Chosen corrective action (populated in D5), by default None
    verified : bool
        Whether correction was verified (D6), by default False

    Examples
    --------
    >>> # D1: Create initial problem report
    >>> report = ProblemReport(
    ...     problem_id="WCP-43-001", description="AND-join deadlock - Task B never completes", step=EightDStep.D1_TEAM
    ... )
    >>> report.problem_id
    'WCP-43-001'
    >>> report.description
    'AND-join deadlock - Task B never completes'
    >>> report.step
    <EightDStep.D1_TEAM: 'D1: Team Formation'>

    >>> # D4: Add root cause
    >>> report_d4 = ProblemReport(
    ...     problem_id="WCP-43-001",
    ...     description="AND-join deadlock - Task B never completes",
    ...     step=EightDStep.D4_ROOT_CAUSE,
    ...     root_cause="Task B has status='Pending' instead of 'Completed'",
    ... )
    >>> report_d4.root_cause
    "Task B has status='Pending' instead of 'Completed'"

    >>> # D5: Add corrective action
    >>> report_d5 = ProblemReport(
    ...     problem_id="WCP-43-001",
    ...     description="AND-join deadlock - Task B never completes",
    ...     step=EightDStep.D5_CORRECTIVE,
    ...     root_cause="Task B has status='Pending' instead of 'Completed'",
    ...     corrective_action="Change Task B status to 'Completed'",
    ... )
    >>> report_d5.corrective_action
    "Change Task B status to 'Completed'"

    >>> # D6: Verify correction
    >>> report_d6 = ProblemReport(
    ...     problem_id="WCP-43-001",
    ...     description="AND-join deadlock - Task B never completes",
    ...     step=EightDStep.D6_VERIFICATION,
    ...     root_cause="Task B has status='Pending' instead of 'Completed'",
    ...     corrective_action="Change Task B status to 'Completed'",
    ...     verified=True,
    ... )
    >>> report_d6.verified
    True

    >>> # Frozen dataclass - immutable
    >>> try:
    ...     report.verified = True
    ... except AttributeError:
    ...     print("Cannot modify frozen dataclass")
    Cannot modify frozen dataclass

    >>> # Multiple problems can be tracked
    >>> problems = [
    ...     ProblemReport("WCP-001", "Deadlock", EightDStep.D1_TEAM),
    ...     ProblemReport("WCP-002", "Infinite loop", EightDStep.D2_PROBLEM),
    ...     ProblemReport("WCP-003", "Missing status", EightDStep.D3_CONTAINMENT),
    ... ]
    >>> len(problems)
    3
    >>> problems[0].problem_id
    'WCP-001'
    """

    problem_id: str
    description: str
    step: EightDStep
    root_cause: str | None = None
    corrective_action: str | None = None
    verified: bool = False
