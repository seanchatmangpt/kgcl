"""8D Problem Solving Tests for Knowledge Hooks.

This module tests the 8D (Eight Disciplines) problem solving methodology
applied to Knowledge Hook failures and quality issues.

Test Strategy
-------------
- Test each 8D step (D0-D8) with realistic hook failure scenarios
- Verify data structures correctly model 8D workflow
- Validate immutability and type safety
- Document hook-specific 8D patterns

Real-World Hook Failure Scenarios
---------------------------------
1. Validation Hook Rejecting Valid Data (HOOK-001)
2. Performance Degradation in Transform Hook (HOOK-002)
3. Audit Hook Missing Critical Fields (HOOK-003)
4. Hook Priority Conflict Causing Race Condition (HOOK-004)
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.lss.hooks.eight_d import Hook8DReport, Hook8DStep, HookProblemTicket


class TestHook8DStepEnum:
    """Test Hook8DStep enum structure and values."""

    def test_enum_has_nine_steps(self) -> None:
        """8D methodology has 9 steps (D0 emergency + D1-D8)."""
        steps = list(Hook8DStep)
        assert len(steps) == 9

    def test_d0_emergency_response(self) -> None:
        """D0: Emergency response for immediate containment."""
        step = Hook8DStep.D0_EMERGENCY
        assert step.value == "D0: Emergency Response"
        assert step.name == "D0_EMERGENCY"

    def test_d1_team_formation(self) -> None:
        """D1: Team formation step."""
        step = Hook8DStep.D1_TEAM
        assert step.value == "D1: Team Formation"
        assert step.name == "D1_TEAM"

    def test_d2_problem_description(self) -> None:
        """D2: Problem description step."""
        step = Hook8DStep.D2_PROBLEM
        assert step.value == "D2: Problem Description"
        assert step.name == "D2_PROBLEM"

    def test_d3_containment(self) -> None:
        """D3: Interim containment step."""
        step = Hook8DStep.D3_CONTAINMENT
        assert step.value == "D3: Interim Containment"
        assert step.name == "D3_CONTAINMENT"

    def test_d4_root_cause(self) -> None:
        """D4: Root cause analysis step."""
        step = Hook8DStep.D4_ROOT_CAUSE
        assert step.value == "D4: Root Cause Analysis"
        assert step.name == "D4_ROOT_CAUSE"

    def test_d5_corrective_action(self) -> None:
        """D5: Corrective actions step."""
        step = Hook8DStep.D5_CORRECTIVE
        assert step.value == "D5: Corrective Actions"
        assert step.name == "D5_CORRECTIVE"

    def test_d6_verification(self) -> None:
        """D6: Verification step."""
        step = Hook8DStep.D6_VERIFICATION
        assert step.value == "D6: Verification"
        assert step.name == "D6_VERIFICATION"

    def test_d7_prevention(self) -> None:
        """D7: Prevention step."""
        step = Hook8DStep.D7_PREVENTION
        assert step.value == "D7: Prevention"
        assert step.name == "D7_PREVENTION"

    def test_d8_closure(self) -> None:
        """D8: Closure step."""
        step = Hook8DStep.D8_CLOSURE
        assert step.value == "D8: Closure"
        assert step.name == "D8_CLOSURE"

    def test_steps_iterable(self) -> None:
        """All 8D steps are iterable."""
        steps = list(Hook8DStep)
        assert steps[0] == Hook8DStep.D0_EMERGENCY
        assert steps[1] == Hook8DStep.D1_TEAM
        assert steps[8] == Hook8DStep.D8_CLOSURE


class TestHook8DReport:
    """Test Hook8DReport dataclass structure and immutability."""

    def test_complete_8d_report_structure(self) -> None:
        """Hook8DReport has all 9 fields (D0-D8)."""
        report = Hook8DReport(
            d0_emergency_response="Disabled validate-person hook",
            d1_team=["hook-dev", "qa-engineer"],
            d2_problem_description="Hook rejects valid Person with multiline name",
            d3_containment="Manual validation in pre-phase",
            d4_root_cause="SPARQL regex missing dotall flag",
            d5_corrective_action="Added 's' flag to FILTER regex",
            d6_implementation="All tests pass, p99 < 5ms",
            d7_preventive_action="Added edge case tests to CI",
            d8_closure="Documented in knowledge base",
        )

        assert report.d0_emergency_response == "Disabled validate-person hook"
        assert report.d1_team == ["hook-dev", "qa-engineer"]
        assert report.d2_problem_description.startswith("Hook rejects")
        assert report.d3_containment == "Manual validation in pre-phase"
        assert report.d4_root_cause == "SPARQL regex missing dotall flag"
        assert report.d5_corrective_action.startswith("Added 's' flag")
        assert report.d6_implementation.startswith("All tests pass")
        assert report.d7_preventive_action.startswith("Added edge case")
        assert report.d8_closure.startswith("Documented")

    def test_8d_report_immutability(self) -> None:
        """Hook8DReport is frozen (immutable)."""
        report = Hook8DReport(
            d0_emergency_response="Emergency action",
            d1_team=["dev"],
            d2_problem_description="Problem",
            d3_containment="Containment",
            d4_root_cause="Root cause",
            d5_corrective_action="Corrective",
            d6_implementation="Verification",
            d7_preventive_action="Prevention",
            d8_closure="Closure",
        )

        with pytest.raises(AttributeError):
            report.d0_emergency_response = "Different action"  # type: ignore[misc]

    def test_8d_report_team_list_structure(self) -> None:
        """D1 team field is a list of strings."""
        report = Hook8DReport(
            d0_emergency_response="Emergency",
            d1_team=["hook-developer", "ontology-expert", "qa-engineer", "product-owner"],
            d2_problem_description="Problem",
            d3_containment="Containment",
            d4_root_cause="Root cause",
            d5_corrective_action="Corrective",
            d6_implementation="Verification",
            d7_preventive_action="Prevention",
            d8_closure="Closure",
        )

        assert len(report.d1_team) == 4
        assert "hook-developer" in report.d1_team
        assert "ontology-expert" in report.d1_team


class TestHookProblemTicket:
    """Test HookProblemTicket dataclass for tracking 8D workflows."""

    def test_ticket_initial_creation_d0(self) -> None:
        """Create ticket at D0 (emergency response)."""
        ticket = HookProblemTicket(
            id="HOOK-001",
            hook_id="validate-person",
            symptom="Hook rejects valid Person entities",
            current_step=Hook8DStep.D0_EMERGENCY,
            report=None,
        )

        assert ticket.id == "HOOK-001"
        assert ticket.hook_id == "validate-person"
        assert ticket.symptom.startswith("Hook rejects")
        assert ticket.current_step == Hook8DStep.D0_EMERGENCY
        assert ticket.report is None

    def test_ticket_progression_through_steps(self) -> None:
        """Ticket progresses through 8D steps."""
        # D1: Team formation
        ticket_d1 = HookProblemTicket(
            id="HOOK-001",
            hook_id="validate-person",
            symptom="Hook rejects valid data",
            current_step=Hook8DStep.D1_TEAM,
            report=None,
        )
        assert ticket_d1.current_step == Hook8DStep.D1_TEAM

        # D4: Root cause analysis
        ticket_d4 = HookProblemTicket(
            id="HOOK-001",
            hook_id="validate-person",
            symptom="Hook rejects valid data",
            current_step=Hook8DStep.D4_ROOT_CAUSE,
            report=None,
        )
        assert ticket_d4.current_step == Hook8DStep.D4_ROOT_CAUSE

        # D8: Closure with complete report
        report = Hook8DReport(
            d0_emergency_response="Disabled hook",
            d1_team=["dev"],
            d2_problem_description="Problem identified",
            d3_containment="Workaround applied",
            d4_root_cause="Root cause found",
            d5_corrective_action="Fix implemented",
            d6_implementation="Tests pass",
            d7_preventive_action="CI updated",
            d8_closure="Knowledge documented",
        )
        ticket_d8 = HookProblemTicket(
            id="HOOK-001",
            hook_id="validate-person",
            symptom="Hook rejects valid data",
            current_step=Hook8DStep.D8_CLOSURE,
            report=report,
        )
        assert ticket_d8.current_step == Hook8DStep.D8_CLOSURE
        assert ticket_d8.report is not None
        assert ticket_d8.report.d8_closure == "Knowledge documented"

    def test_ticket_immutability(self) -> None:
        """HookProblemTicket is frozen (immutable)."""
        ticket = HookProblemTicket(
            id="HOOK-001",
            hook_id="validate-person",
            symptom="Hook failure",
            current_step=Hook8DStep.D0_EMERGENCY,
            report=None,
        )

        with pytest.raises(AttributeError):
            ticket.current_step = Hook8DStep.D1_TEAM  # type: ignore[misc]

    def test_multiple_tickets_tracking(self) -> None:
        """Track multiple concurrent 8D investigations."""
        tickets = [
            HookProblemTicket(
                id="HOOK-001",
                hook_id="validate-person",
                symptom="Rejects valid data",
                current_step=Hook8DStep.D0_EMERGENCY,
                report=None,
            ),
            HookProblemTicket(
                id="HOOK-002",
                hook_id="audit-log",
                symptom="Missing timestamps",
                current_step=Hook8DStep.D2_PROBLEM,
                report=None,
            ),
            HookProblemTicket(
                id="HOOK-003",
                hook_id="transform-uri",
                symptom="Performance degradation",
                current_step=Hook8DStep.D4_ROOT_CAUSE,
                report=None,
            ),
        ]

        assert len(tickets) == 3
        assert tickets[0].hook_id == "validate-person"
        assert tickets[1].current_step == Hook8DStep.D2_PROBLEM
        assert tickets[2].symptom == "Performance degradation"


class TestRealWorldHookFailureScenarios:
    """Test realistic 8D investigations for common hook failures."""

    def test_scenario_validation_hook_rejects_valid_data(self) -> None:
        """HOOK-001: Validation hook incorrectly rejects valid Person entities.

        Scenario: validate-person hook rejects Person entities with multiline names.
        Root Cause: SPARQL condition query uses FILTER without dotall flag.
        Fix: Updated regex to handle multiline strings.
        """
        report = Hook8DReport(
            d0_emergency_response="Disabled validate-person hook via HookRegistry.disable('validate-person')",
            d1_team=["hook-developer", "ontology-expert", "qa-engineer", "product-owner"],
            d2_problem_description=(
                "IS: Hook rejects valid Person entities when kgc:name contains newlines. "
                "IS NOT: Hook correctly validates Person with single-line names. "
                "DIFFERENCE: SPARQL FILTER uses literal string match without whitespace normalization."
            ),
            d3_containment="Temporary pre-validation hook normalizes whitespace before validate-person runs",
            d4_root_cause=(
                "Root Cause: SPARQL condition query 'FILTER NOT EXISTS { ?s kgc:name ?name }' "
                "fails on multiline literals because PyOxigraph literal matching is strict. "
                "Why 1: Query doesn't normalize whitespace. "
                "Why 2: Test suite only covered ASCII single-line names. "
                "Why 3: No integration tests with real-world data. "
                "Why 4: Code review checklist missing edge case verification. "
                "Why 5: Hook testing documentation incomplete."
            ),
            d5_corrective_action=(
                "Updated condition query to: "
                "'ASK { ?s a kgc:Person . "
                "FILTER NOT EXISTS { ?s kgc:name ?name . FILTER(STRLEN(STR(?name)) > 0) } }' "
                "This validates name exists AND is non-empty after normalization."
            ),
            d6_implementation=(
                "Verification Steps: "
                "1. Added test_validate_person_multiline_name() - PASS. "
                "2. Added test_validate_person_unicode_name() - PASS. "
                "3. Tested with 100 real-world Person entities from production - 100% success. "
                "4. Performance: p50=2ms, p99=5ms (within <10ms SLO). "
                "5. Rollback test: Disabled corrected hook, verified old failure reappears."
            ),
            d7_preventive_action=(
                "Systemic Improvements: "
                "1. Added docs/hook-testing-guide.md with edge case checklist. "
                "2. Created hook-code-review-checklist.md requiring edge case coverage. "
                "3. Added pre-commit hook to enforce 80% test coverage on hook modules. "
                "4. Updated CI pipeline to run hook integration tests with production-like data. "
                "5. Created hook-patterns.md documenting SPARQL best practices."
            ),
            d8_closure=(
                "Team Recognition: hook-developer (root cause analysis + fix), "
                "qa-engineer (comprehensive test suite), ontology-expert (validation logic review). "
                "Lessons Learned: ALL validation hooks MUST test multiline, unicode, and whitespace edge cases. "
                "Knowledge Base: Updated internal wiki with SPARQL literal matching gotchas."
            ),
        )

        ticket = HookProblemTicket(
            id="HOOK-001",
            hook_id="validate-person",
            symptom="Hook rejects valid Person entities with error 'name validation failed' when name contains newlines",
            current_step=Hook8DStep.D8_CLOSURE,
            report=report,
        )

        assert ticket.current_step == Hook8DStep.D8_CLOSURE
        assert ticket.report is not None
        assert "newlines" in ticket.report.d2_problem_description
        assert "SPARQL" in ticket.report.d4_root_cause
        assert len(ticket.report.d1_team) == 4

    def test_scenario_performance_degradation_transform_hook(self) -> None:
        """HOOK-002: Transform hook causes performance degradation.

        Scenario: transform-uri hook p99 latency increases from 10ms to 250ms.
        Root Cause: Hook added N^2 complexity SPARQL query without LIMIT.
        Fix: Optimized query with LIMIT and index hints.
        """
        report = Hook8DReport(
            d0_emergency_response="Reduced hook priority to 10 (lowest) to delay execution",
            d1_team=["performance-engineer", "hook-developer", "sre"],
            d2_problem_description=(
                "IS: transform-uri hook p99 latency = 250ms (exceeds 100ms SLO). "
                "IS NOT: Other transform hooks meet latency SLO. "
                "DIFFERENCE: transform-uri uses SELECT query without LIMIT clause."
            ),
            d3_containment="Added hook:timeout 50ms to fail-fast and prevent cascade",
            d4_root_cause=(
                "Root Cause: SPARQL query 'SELECT ?uri ?newUri WHERE { ?uri kgc:shouldTransform true }' "
                "scans entire graph without LIMIT, causing O(N) performance. "
                "Why 1: No LIMIT clause. "
                "Why 2: No index on kgc:shouldTransform predicate. "
                "Why 3: Performance testing only used small graphs (<1000 triples). "
                "Why 4: No p99 latency monitoring on hooks. "
                "Why 5: Performance SLOs not enforced in CI."
            ),
            d5_corrective_action=(
                "1. Added 'LIMIT 100' to SPARQL query. "
                "2. Added index hint: '# @index kgc:shouldTransform'. "
                "3. Changed hook phase from PRE_TICK to POST_TICK (less critical path)."
            ),
            d6_implementation=(
                "Verification: "
                "1. Benchmarked with 100K triple graph: p50=8ms, p99=45ms (within SLO). "
                "2. Load tested at 100 req/s for 1 hour: stable latency, no degradation. "
                "3. Compared with/without fix: 5.5x latency improvement."
            ),
            d7_preventive_action=(
                "1. Added performance benchmarks to CI for all hooks. "
                "2. Created hook-performance-slo.md documenting latency targets. "
                "3. Added automated alerting on p99 latency > 100ms. "
                "4. Required load testing for hooks touching >1000 triples."
            ),
            d8_closure=(
                "Team Recognition: performance-engineer (benchmarking), sre (monitoring). "
                "Lessons Learned: ALL hooks with SELECT queries MUST have LIMIT clauses. "
                "Performance SLOs are non-negotiable for production hooks."
            ),
        )

        ticket = HookProblemTicket(
            id="HOOK-002",
            hook_id="transform-uri",
            symptom="Hook p99 latency increased from 10ms to 250ms, causing timeout errors",
            current_step=Hook8DStep.D8_CLOSURE,
            report=report,
        )

        assert ticket.report is not None
        assert "latency" in ticket.report.d2_problem_description.lower()
        assert "LIMIT" in ticket.report.d5_corrective_action

    def test_scenario_audit_hook_missing_critical_fields(self) -> None:
        """HOOK-003: Audit hook fails to log critical security fields.

        Scenario: audit-user-login hook missing IP address and user agent.
        Root Cause: Hook action only asserts kgc:loginTimestamp, omits other fields.
        Fix: Updated handler to assert all required audit fields.
        """
        report = Hook8DReport(
            d0_emergency_response="No immediate action - non-critical audit data",
            d1_team=["security-engineer", "hook-developer", "compliance-officer"],
            d2_problem_description=(
                "IS: Audit logs missing kgc:clientIP and kgc:userAgent. "
                "IS NOT: Audit logs correctly contain kgc:loginTimestamp and kgc:userId. "
                "DIFFERENCE: Hook handler only asserts 2 of 4 required fields."
            ),
            d3_containment="Manual log enrichment script backfills IP/UserAgent from application logs",
            d4_root_cause=(
                "Root Cause: Hook handler_data only contains 'timestamp' assertion. "
                "Why 1: Original spec only required timestamp. "
                "Why 2: Security requirements updated after hook implementation. "
                "Why 3: No regression testing of audit field completeness. "
                "Why 4: Hook schema validation incomplete."
            ),
            d5_corrective_action=(
                "Updated handler_data to assert all 4 fields: "
                "{ 'assertions': ['timestamp', 'userId', 'clientIP', 'userAgent'] }"
            ),
            d6_implementation=(
                "Verification: "
                "1. Test audit-user-login hook with mock data - all 4 fields present. "
                "2. Reviewed 1000 audit entries: 100% complete. "
                "3. Schema validation enforces required fields."
            ),
            d7_preventive_action=(
                "1. Created audit-field-schema.json requiring all fields. "
                "2. Added pre-commit validation of audit hook assertions. "
                "3. Updated security requirements doc with audit standards."
            ),
            d8_closure=(
                "Team Recognition: security-engineer (requirements), compliance-officer (validation). "
                "Lessons Learned: Audit hooks require schema validation to prevent incomplete logs."
            ),
        )

        ticket = HookProblemTicket(
            id="HOOK-003",
            hook_id="audit-user-login",
            symptom="Security audit logs missing IP address and user agent fields",
            current_step=Hook8DStep.D8_CLOSURE,
            report=report,
        )

        assert ticket.report is not None
        assert "audit" in ticket.symptom.lower()
        assert "all 4 fields" in ticket.report.d5_corrective_action.lower()
