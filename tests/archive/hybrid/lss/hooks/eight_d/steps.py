"""8D Problem-Solving Steps for Knowledge Hooks.

This module defines the Hook8DStep enum and HookProblemTicket dataclass for
tracking 8D problem-solving workflows specific to Knowledge Hook failures.

The 8D methodology applies to hook-specific problems:
- D0: Emergency response (disable failing hook immediately)
- D1: Team formation (cross-functional: hook dev, domain expert, user)
- D2: Problem description (IS/IS NOT analysis of hook behavior)
- D3: Interim containment (temporary workaround)
- D4: Root cause analysis (5 Whys, fishbone for hook logic)
- D5: Corrective action (fix hook condition/handler)
- D6: Verification (test hook with real data)
- D7: Prevention (update hook patterns, add tests)
- D8: Closure (document learnings, recognize team)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Hook8DStep(Enum):
    """8D Problem-Solving Methodology Steps for Knowledge Hooks.

    Each step represents a discipline in the 8D process for systematic
    quality improvement of Knowledge Hook implementations.

    Attributes
    ----------
    D0_EMERGENCY : str
        Emergency Response - Immediate containment to protect production
    D1_TEAM : str
        Team Formation - Establish cross-functional team
    D2_PROBLEM : str
        Problem Description - Define and quantify the hook failure
    D3_CONTAINMENT : str
        Interim Containment - Protect users with interim actions
    D4_ROOT_CAUSE : str
        Root Cause Analysis - Identify and verify root causes
    D5_CORRECTIVE : str
        Corrective Actions - Choose and verify permanent corrections
    D6_VERIFICATION : str
        Verification - Validate corrections resolve problem
    D7_PREVENTION : str
        Prevention - Prevent recurrence through systemic changes
    D8_CLOSURE : str
        Closure - Recognize team and document learnings

    Examples
    --------
    >>> # D0: Emergency Response
    >>> step = Hook8DStep.D0_EMERGENCY
    >>> step.value
    'D0: Emergency Response'
    >>> step.name
    'D0_EMERGENCY'

    >>> # D1: Team Formation
    >>> Hook8DStep.D1_TEAM.value
    'D1: Team Formation'

    >>> # D2: Problem Description
    >>> Hook8DStep.D2_PROBLEM.value
    'D2: Problem Description'

    >>> # D3: Interim Containment
    >>> Hook8DStep.D3_CONTAINMENT.value
    'D3: Interim Containment'

    >>> # D4: Root Cause Analysis
    >>> Hook8DStep.D4_ROOT_CAUSE.value
    'D4: Root Cause Analysis'

    >>> # D5: Corrective Actions
    >>> Hook8DStep.D5_CORRECTIVE.value
    'D5: Corrective Actions'

    >>> # D6: Verification
    >>> Hook8DStep.D6_VERIFICATION.value
    'D6: Verification'

    >>> # D7: Prevention
    >>> Hook8DStep.D7_PREVENTION.value
    'D7: Prevention'

    >>> # D8: Closure
    >>> Hook8DStep.D8_CLOSURE.value
    'D8: Closure'

    >>> # Iterate through all steps
    >>> steps = list(Hook8DStep)
    >>> len(steps)
    9
    >>> steps[0]
    <Hook8DStep.D0_EMERGENCY: 'D0: Emergency Response'>
    """

    D0_EMERGENCY = "D0: Emergency Response"
    D1_TEAM = "D1: Team Formation"
    D2_PROBLEM = "D2: Problem Description"
    D3_CONTAINMENT = "D3: Interim Containment"
    D4_ROOT_CAUSE = "D4: Root Cause Analysis"
    D5_CORRECTIVE = "D5: Corrective Actions"
    D6_VERIFICATION = "D6: Verification"
    D7_PREVENTION = "D7: Prevention"
    D8_CLOSURE = "D8: Closure"


@dataclass(frozen=True)
class Hook8DReport:
    """Complete 8D problem report for Knowledge Hook failures.

    Immutable dataclass representing a complete 8D investigation of a
    Knowledge Hook failure or quality issue.

    Parameters
    ----------
    d0_emergency_response : str
        D0: Immediate containment action (disable hook, skip phase, rollback)
    d1_team : list[str]
        D1: Cross-functional team members (hook dev, domain expert, user, QA)
    d2_problem_description : str
        D2: IS/IS NOT analysis of hook behavior (when fails, when works, what differs)
    d3_containment : str
        D3: Temporary fix or workaround (manual validation, conditional disable)
    d4_root_cause : str
        D4: Root cause identified via 5 Whys, fishbone, or fault tree analysis
    d5_corrective_action : str
        D5: Permanent fix (corrected condition query, updated handler logic)
    d6_implementation : str
        D6: Verification steps and test results proving fix works
    d7_preventive_action : str
        D7: Systemic improvements (test patterns, code review checklist, CI gates)
    d8_closure : str
        D8: Team recognition, lessons learned, knowledge base updates

    Examples
    --------
    >>> # Complete 8D report for hook validation failure
    >>> report = Hook8DReport(
    ...     d0_emergency_response="Disabled validate-person hook immediately via HookRegistry.disable()",
    ...     d1_team=["hook-developer", "ontology-expert", "qa-engineer", "product-owner"],
    ...     d2_problem_description=(
    ...         "IS: Hook rejects valid Person entities with multi-line names. "
    ...         "IS NOT: Hook correctly validates single-line names. "
    ...         "DIFFERENCE: SPARQL query uses literal match, fails on whitespace normalization."
    ...     ),
    ...     d3_containment="Temporary whitespace normalization in pre-validation phase",
    ...     d4_root_cause=(
    ...         "Root Cause: SPARQL FILTER uses string:notMatches without SPARQL 1.1 REGEX flags. "
    ...         "Why 1: Query fails on newlines. "
    ...         "Why 2: No regex flags for multiline. "
    ...         "Why 3: Test suite only covered single-line cases. "
    ...         "Why 4: No edge case testing in CI. "
    ...         "Why 5: Hook testing guidance incomplete."
    ...     ),
    ...     d5_corrective_action="Updated condition query to use FILTER regex with 's' flag for dotall mode",
    ...     d6_implementation=(
    ...         "1. Added test_validate_multiline_name() - PASS. "
    ...         "2. Tested with 50 real-world Person entities - 100% success. "
    ...         "3. Performance: p99 latency <5ms (within SLO)."
    ...     ),
    ...     d7_preventive_action=(
    ...         "1. Added hook testing guide with edge cases to docs/. "
    ...         "2. Created hook-test-checklist.md for code reviews. "
    ...         "3. Added pre-commit hook to enforce test coverage. "
    ...         "4. Updated CI to run hook integration tests on every PR."
    ...     ),
    ...     d8_closure=(
    ...         "Team Recognition: hook-developer (root cause analysis), qa-engineer (test suite). "
    ...         "Lessons Learned: All hooks need multiline/whitespace edge case tests. "
    ...         "Knowledge Base: Updated hook-patterns.md with SPARQL regex best practices."
    ...     ),
    ... )
    >>> report.d1_team[0]
    'hook-developer'
    >>> report.d4_root_cause.startswith("Root Cause")
    True

    >>> # Frozen dataclass - immutable
    >>> try:
    ...     report.d0_emergency_response = "Different action"
    ... except AttributeError:
    ...     print("Cannot modify frozen dataclass")
    Cannot modify frozen dataclass

    >>> # Multiple 8D reports can be tracked
    >>> reports = [
    ...     Hook8DReport(
    ...         d0_emergency_response="Disable hook",
    ...         d1_team=["dev"],
    ...         d2_problem_description="Hook rejects valid data",
    ...         d3_containment="Manual validation",
    ...         d4_root_cause="Incorrect condition query",
    ...         d5_corrective_action="Fixed query",
    ...         d6_implementation="Tests pass",
    ...         d7_preventive_action="Added CI checks",
    ...         d8_closure="Lessons documented",
    ...     )
    ... ]
    >>> len(reports)
    1
    """

    d0_emergency_response: str
    d1_team: list[str]
    d2_problem_description: str
    d3_containment: str
    d4_root_cause: str
    d5_corrective_action: str
    d6_implementation: str
    d7_preventive_action: str
    d8_closure: str


@dataclass(frozen=True)
class HookProblemTicket:
    """Problem ticket tracking 8D investigation for a Knowledge Hook failure.

    Immutable dataclass representing an active 8D problem-solving workflow
    for a specific Knowledge Hook issue.

    Parameters
    ----------
    id : str
        Unique problem ticket identifier (e.g., "HOOK-001")
    hook_id : str
        ID of the failing Knowledge Hook (e.g., "validate-person")
    symptom : str
        Observable symptom of the failure (what users/system experienced)
    current_step : Hook8DStep
        Current 8D step being executed
    report : Hook8DReport | None
        Complete 8D report (populated when investigation completes at D8), by default None

    Examples
    --------
    >>> # D0: Create emergency ticket
    >>> ticket = HookProblemTicket(
    ...     id="HOOK-001",
    ...     hook_id="validate-person",
    ...     symptom="Hook rejects valid Person entities with error 'name validation failed'",
    ...     current_step=Hook8DStep.D0_EMERGENCY,
    ...     report=None,
    ... )
    >>> ticket.id
    'HOOK-001'
    >>> ticket.hook_id
    'validate-person'
    >>> ticket.current_step
    <Hook8DStep.D0_EMERGENCY: 'D0: Emergency Response'>

    >>> # D4: Ticket progressed to root cause analysis
    >>> ticket_d4 = HookProblemTicket(
    ...     id="HOOK-001",
    ...     hook_id="validate-person",
    ...     symptom="Hook rejects valid Person entities with error 'name validation failed'",
    ...     current_step=Hook8DStep.D4_ROOT_CAUSE,
    ...     report=None,
    ... )
    >>> ticket_d4.current_step
    <Hook8DStep.D4_ROOT_CAUSE: 'D4: Root Cause Analysis'>

    >>> # D8: Ticket closed with complete report
    >>> complete_report = Hook8DReport(
    ...     d0_emergency_response="Disabled hook",
    ...     d1_team=["dev", "qa"],
    ...     d2_problem_description="Hook fails on multiline names",
    ...     d3_containment="Manual validation",
    ...     d4_root_cause="SPARQL regex missing dotall flag",
    ...     d5_corrective_action="Added 's' flag to regex",
    ...     d6_implementation="All tests pass",
    ...     d7_preventive_action="Added edge case tests to CI",
    ...     d8_closure="Documented in knowledge base",
    ... )
    >>> ticket_d8 = HookProblemTicket(
    ...     id="HOOK-001",
    ...     hook_id="validate-person",
    ...     symptom="Hook rejects valid Person entities with error 'name validation failed'",
    ...     current_step=Hook8DStep.D8_CLOSURE,
    ...     report=complete_report,
    ... )
    >>> ticket_d8.report is not None
    True
    >>> ticket_d8.report.d4_root_cause
    'SPARQL regex missing dotall flag'

    >>> # Frozen dataclass - immutable
    >>> try:
    ...     ticket.current_step = Hook8DStep.D1_TEAM
    ... except AttributeError:
    ...     print("Cannot modify frozen dataclass")
    Cannot modify frozen dataclass

    >>> # Multiple tickets can be tracked simultaneously
    >>> tickets = [
    ...     HookProblemTicket("HOOK-001", "validate-person", "Rejects valid data", Hook8DStep.D0_EMERGENCY, None),
    ...     HookProblemTicket("HOOK-002", "audit-log", "Missing timestamps", Hook8DStep.D2_PROBLEM, None),
    ...     HookProblemTicket("HOOK-003", "transform-uri", "Performance degradation", Hook8DStep.D4_ROOT_CAUSE, None),
    ... ]
    >>> len(tickets)
    3
    >>> tickets[0].hook_id
    'validate-person'
    """

    id: str
    hook_id: str
    symptom: str
    current_step: Hook8DStep
    report: Hook8DReport | None = None
