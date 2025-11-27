"""Knowledge Hooks Failure Mode Definitions.

This module defines failure modes specific to the Knowledge Hooks system,
following AIAG FMEA Handbook methodology with Severity, Occurrence, and
Detection ratings on a 1-10 scale.

Examples
--------
Create a failure mode with automatic RPN calculation:

>>> from tests.hybrid.lss.hooks.fmea.failure_modes import HOOK_FAILURE_MODES
>>> fm = HOOK_FAILURE_MODES["FM-HOOK-001"]
>>> fm.rpn
45
>>> fm.risk_level()
'Medium'

Check critical failure modes:

>>> fm_deadlock = HOOK_FAILURE_MODES["FM-HOOK-003"]
>>> fm_deadlock.rpn
315
>>> fm_deadlock.risk_level()
'Critical'

All failure modes follow Lean Six Sigma standards:

>>> all(fm.severity >= 1 and fm.severity <= 10 for fm in HOOK_FAILURE_MODES.values())
True
>>> all(fm.occurrence >= 1 and fm.occurrence <= 10 for fm in HOOK_FAILURE_MODES.values())
True
>>> all(fm.detection >= 1 and fm.detection <= 10 for fm in HOOK_FAILURE_MODES.values())
True
"""

from __future__ import annotations

from dataclasses import dataclass

from tests.hybrid.lss.fmea.ratings import Detection, Occurrence, Severity, calculate_rpn


@dataclass(frozen=True)
class HookFailureMode:
    """Structured representation of a Knowledge Hooks failure mode.

    A failure mode describes a specific way the hook system can fail,
    along with its impact, likelihood, and detectability. Frozen for immutability.

    Parameters
    ----------
    id : str
        Unique failure mode identifier (e.g., "FM-HOOK-001")
    name : str
        Short descriptive name
    description : str
        Detailed description of the failure mode
    effect : str
        Impact on system operation
    severity : int
        Severity rating (1-10)
    occurrence : int
        Occurrence rating (1-10)
    detection : int
        Detection rating (1-10)
    mitigation : str, optional
        Mitigation strategy or test approach

    Attributes
    ----------
    rpn : int
        Risk Priority Number (severity × occurrence × detection)

    Examples
    --------
    Create a medium-risk failure mode:

    >>> fm = HookFailureMode(
    ...     id="FM-HOOK-001",
    ...     name="Condition Query Timeout",
    ...     description="SPARQL condition query exceeds timeout limit",
    ...     effect="Hook never triggers or triggers late",
    ...     severity=Severity.MODERATE,
    ...     occurrence=Occurrence.LOW,
    ...     detection=Detection.HIGH,
    ... )
    >>> fm.id
    'FM-HOOK-001'
    >>> fm.rpn
    45
    >>> fm.risk_level()
    'Medium'

    Create a critical failure mode with mitigation:

    >>> fm_critical = HookFailureMode(
    ...     id="FM-HOOK-003",
    ...     name="Priority Deadlock",
    ...     description="Two hooks block each other via priority",
    ...     effect="Neither hook can execute",
    ...     severity=Severity.CRITICAL,
    ...     occurrence=Occurrence.MODERATE,
    ...     detection=Detection.LOW,
    ...     mitigation="Implement priority tie-breaking by hook ID lexicographic order",
    ... )
    >>> fm_critical.rpn
    315
    >>> fm_critical.risk_level()
    'Critical'

    Notes
    -----
    The frozen=True parameter ensures immutability, making HookFailureMode instances
    safe to use as dictionary keys or in sets.

    See Also
    --------
    tests.hybrid.lss.fmea.ratings.calculate_rpn : Compute RPN from ratings
    """

    id: str
    name: str
    description: str
    effect: str
    severity: int
    occurrence: int
    detection: int
    mitigation: str | None = None

    @property
    def rpn(self) -> int:
        """Calculate Risk Priority Number.

        Returns
        -------
        int
            RPN value (severity × occurrence × detection)

        Examples
        --------
        >>> fm = HookFailureMode(
        ...     "FM-HOOK-TEST", "Test", "desc", "effect", Severity.HIGH, Occurrence.MODERATE, Detection.MODERATE
        ... )
        >>> fm.rpn  # Severity.HIGH(7) * Occurrence.MODERATE(5) * Detection.MODERATE(5) = 175
        175

        RPN is always product of three ratings:

        >>> fm2 = HookFailureMode("FM-HOOK-002", "Test", "d", "e", 9, 5, 3)
        >>> fm2.rpn == 9 * 5 * 3
        True
        """
        return calculate_rpn(self.severity, self.occurrence, self.detection)

    def risk_level(self) -> str:
        """Classify risk level based on RPN.

        Returns
        -------
        str
            One of: "Critical", "High", "Medium", "Low"

        Examples
        --------
        >>> fm_low = HookFailureMode("FM-A", "Test", "d", "e", 3, 3, 1)
        >>> fm_low.risk_level()
        'Low'

        >>> fm_medium = HookFailureMode("FM-B", "Test", "d", "e", 5, 4, 2)
        >>> fm_medium.risk_level()  # RPN=40
        'Medium'

        >>> fm_high = HookFailureMode("FM-C", "Test", "d", "e", 7, 5, 2)
        >>> fm_high.risk_level()  # RPN=70
        'High'

        >>> fm_critical = HookFailureMode("FM-D", "Test", "d", "e", 9, 7, 5)
        >>> fm_critical.risk_level()  # RPN=315
        'Critical'

        Notes
        -----
        Risk level thresholds:
        - RPN > 100: Critical (requires immediate action)
        - RPN 50-100: High (requires mitigation)
        - RPN 20-50: Medium (acceptable with monitoring)
        - RPN < 20: Low (acceptable)
        """
        rpn = self.rpn
        if rpn > 100:
            return "Critical"
        if rpn >= 50:
            return "High"
        if rpn >= 20:
            return "Medium"
        return "Low"


# =============================================================================
# PRE-DEFINED HOOK FAILURE MODES
# =============================================================================

HOOK_FAILURE_MODES: dict[str, HookFailureMode] = {
    "FM-HOOK-001": HookFailureMode(
        id="FM-HOOK-001",
        name="Condition Query Timeout",
        description=(
            "SPARQL condition query (hook:conditionQuery) exceeds timeout limit "
            "during evaluate_conditions(). Complex queries with many joins or "
            "large datasets may not complete within allowed time."
        ),
        effect=(
            "Hook never triggers or triggers late. Time-critical validation "
            "or transformations missed. System proceeds with unvalidated data."
        ),
        severity=Severity.MODERATE,  # 5 - Moderate impact
        occurrence=Occurrence.LOW,  # 3 - Occasional with complex queries
        detection=Detection.HIGH,  # 3 - Easily detected via execution logs
        mitigation=(
            "Implement query timeout handling with fallback to default behavior. "
            "Test: Verify timeout exception caught and logged. "
            "Monitor query execution times and alert on >100ms p99."
        ),
    ),
    "FM-HOOK-002": HookFailureMode(
        id="FM-HOOK-002",
        name="Circular Hook Chain",
        description=(
            "Hook A chains to Hook B (hook:chainTo) and Hook B chains back to Hook A, "
            "creating an infinite activation loop. N3 HOOK LAW 8 triggers chains "
            "but has no cycle detection."
        ),
        effect=(
            "Infinite loop exhausts CPU and memory. System hangs indefinitely. "
            "Other hooks blocked from executing. Requires manual intervention."
        ),
        severity=Severity.CRITICAL,  # 9 - System failure
        occurrence=Occurrence.LOW,  # 3 - Rare unless hooks misconfigured
        detection=Detection.MODERATE,  # 5 - Requires runtime monitoring
        mitigation=(
            "Implement chain cycle detection using visited set during chain traversal. "
            "Test: Verify circular chains rejected at registration time. "
            "Enforce max chain depth limit (e.g., 10 levels)."
        ),
    ),
    "FM-HOOK-003": HookFailureMode(
        id="FM-HOOK-003",
        name="Priority Deadlock",
        description=(
            "Two hooks in same phase have equal priority and both set shouldFire=true. "
            "N3 HOOK LAW 6 blocks lower priority hooks, but equal priorities create "
            "non-deterministic execution order or mutual blocking."
        ),
        effect=(
            "Neither hook executes reliably. Race condition determines which fires first. "
            "Inconsistent validation results across runs. System behavior unpredictable."
        ),
        severity=Severity.CRITICAL,  # 9 - Non-deterministic behavior
        occurrence=Occurrence.MODERATE,  # 5 - Common when multiple validation hooks
        detection=Detection.LOW,  # 7 - Hard to detect, appears as intermittent failure
        mitigation=(
            "Implement priority tie-breaking by hook ID lexicographic order. "
            "Test: Verify deterministic execution order for equal priority hooks. "
            "Validate at registration that same-phase hooks have unique priorities."
        ),
    ),
    "FM-HOOK-004": HookFailureMode(
        id="FM-HOOK-004",
        name="Rollback Cascade Failure",
        description=(
            "Hook with REJECT action triggers rollback, but rollback itself fails "
            "due to inconsistent graph state. System left in partial rollback state "
            "with some changes committed and others reverted."
        ),
        effect=(
            "Data corruption. Graph in inconsistent state violating ontology constraints. "
            "Subsequent operations fail. Manual database recovery required."
        ),
        severity=Severity.HAZARDOUS,  # 10 - Complete system failure
        occurrence=Occurrence.LOW,  # 3 - Rare with proper transaction handling
        detection=Detection.MODERATE,  # 5 - Detected via integrity checks
        mitigation=(
            "Implement atomic transaction boundaries around hook execution phases. "
            "Test: Verify rollback always succeeds or system halts safely. "
            "Add pre-rollback validation to ensure graph can be restored."
        ),
    ),
    "FM-HOOK-005": HookFailureMode(
        id="FM-HOOK-005",
        name="Phase Ordering Violation",
        description=(
            "Hook executes in wrong lifecycle phase (e.g., POST_TICK hook fires during "
            "PRE_TICK). Caused by incorrect hook:phase value or executor logic error. "
            "Breaks assumptions about graph state at each phase."
        ),
        effect=(
            "Hook sees incomplete or inconsistent data. Validation performed on stale state. "
            "Transformations applied too early or too late. Workflow physics violated."
        ),
        severity=Severity.HIGH,  # 7 - High impact on correctness
        occurrence=Occurrence.LOW,  # 3 - Rare with proper phase enforcement
        detection=Detection.CERTAIN,  # 1 - Phase logged in receipts
        mitigation=(
            "Enforce phase validation at hook registration and execution. "
            "Test: Verify hooks only fire in declared phase. "
            "Add phase transition guards in tick controller."
        ),
    ),
    "FM-HOOK-006": HookFailureMode(
        id="FM-HOOK-006",
        name="Condition SPARQL Injection",
        description=(
            "Malicious or malformed SPARQL in hook:conditionQuery allows injection "
            "attacks when evaluated against engine store. Could read sensitive data "
            "or corrupt graph via UPDATE queries disguised as ASK."
        ),
        effect=(
            "Unauthorized data access. Graph corruption. Security breach. "
            "System integrity compromised. Potential data exfiltration."
        ),
        severity=Severity.CRITICAL,  # 9 - Security impact
        occurrence=Occurrence.REMOTE,  # 1 - Only if untrusted hook definitions loaded
        detection=Detection.MODERATE,  # 5 - SPARQL parsing can detect some attacks
        mitigation=(
            "Sanitize and validate SPARQL queries at hook registration. "
            "Test: Verify injection attempts rejected. "
            "Enforce read-only query execution (ASK/SELECT only, no UPDATE)."
        ),
    ),
    "FM-HOOK-007": HookFailureMode(
        id="FM-HOOK-007",
        name="Handler Action Type Mismatch",
        description=(
            "Hook declares action=ASSERT but handler_data contains REJECT-specific "
            "fields (e.g., reason). N3 rules expect specific predicates per action type. "
            "Mismatch causes handler to fail silently or execute wrong logic."
        ),
        effect=(
            "Hook appears to execute but performs no action. Validation bypassed. "
            "Expected assertions not added to graph. No error reported."
        ),
        severity=Severity.MODERATE,  # 5 - Silent failure
        occurrence=Occurrence.MODERATE,  # 5 - Common configuration error
        detection=Detection.MODERATE,  # 5 - Requires checking handler execution
        mitigation=(
            "Validate handler_data schema matches action type at registration. "
            "Test: Verify schema validation rejects mismatched configs. "
            "Add runtime assertion that expected predicates present."
        ),
    ),
    "FM-HOOK-008": HookFailureMode(
        id="FM-HOOK-008",
        name="N3 Rule Not Loaded",
        description=(
            "N3_HOOK_PHYSICS rules not loaded into engine or overwritten by "
            "subsequent load_data() call. Hook definitions exist in graph but "
            "logic rules missing, so hooks never fire."
        ),
        effect=(
            "All hooks disabled. No validation or transformation occurs. "
            "System appears functional but hook system completely inactive."
        ),
        severity=Severity.HIGH,  # 7 - Critical feature disabled
        occurrence=Occurrence.LOW,  # 3 - Rare initialization error
        detection=Detection.LOW,  # 7 - Difficult to detect, appears as silent failure
        mitigation=(
            "Verify N3 physics rules present in graph after initialization. "
            "Test: Check that test hooks fire in fixture setup. "
            "Add health check query for presence of hook: namespace rules."
        ),
    ),
    "FM-HOOK-009": HookFailureMode(
        id="FM-HOOK-009",
        name="Receipt Storage Exhaustion",
        description=(
            "HookReceipt history grows unbounded in _receipts list. With high-frequency "
            "hooks, memory exhaustion occurs as receipts accumulate over time. "
            "No cleanup or archival mechanism exists."
        ),
        effect=(
            "Memory leak. System slowdown as list operations become O(n). "
            "Eventually out-of-memory crash. System becomes unresponsive."
        ),
        severity=Severity.HIGH,  # 7 - Eventual system failure
        occurrence=Occurrence.MODERATE,  # 5 - Common with long-running systems
        detection=Detection.HIGH,  # 3 - Memory monitoring detects growth
        mitigation=(
            "Implement receipt rotation with configurable retention (e.g., 1000 receipts). "
            "Test: Verify old receipts purged after threshold. "
            "Add option to archive receipts to external storage."
        ),
    ),
    "FM-HOOK-010": HookFailureMode(
        id="FM-HOOK-010",
        name="Delta Pattern Match Explosion",
        description=(
            "Hook with overly broad deltaPattern matches thousands of triples in "
            "large graph delta. N3 HOOK LAW 10 triggers condition for each match, "
            "causing exponential rule evaluation and performance degradation."
        ),
        effect=(
            "System hangs during delta processing. Tick duration exceeds SLO. "
            "Other hooks starved. Eventually timeout or crash."
        ),
        severity=Severity.HIGH,  # 7 - System unresponsive
        occurrence=Occurrence.MODERATE,  # 5 - Common with generic patterns
        detection=Detection.HIGH,  # 3 - Performance monitoring detects slowdown
        mitigation=(
            "Limit delta pattern matches to specific subject types with cardinality bounds. "
            "Test: Verify performance with 10K+ triple deltas stays <100ms. "
            "Add max_matches limit to delta pattern evaluation."
        ),
    ),
}
