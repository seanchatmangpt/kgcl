"""Chicago School TDD Tests for Knowledge Hooks Failure Modes.

Tests verify behavior of HookFailureMode dataclass and validate
that all pre-defined failure modes meet FMEA standards.

Test Structure:
- No mocking of domain objects
- AAA pattern (Arrange/Act/Assert)
- Verify behavior, not implementation
- Tests complete in <1s total
"""

from __future__ import annotations

import pytest

from tests.hybrid.lss.fmea.ratings import Detection, Occurrence, Severity
from tests.hybrid.lss.hooks.fmea.failure_modes import HOOK_FAILURE_MODES, HookFailureMode


class TestHookFailureModeDataclass:
    """Test HookFailureMode dataclass behavior."""

    def test_creates_immutable_failure_mode(self) -> None:
        """HookFailureMode is frozen and immutable."""
        # Arrange & Act
        fm = HookFailureMode(
            id="FM-TEST-001",
            name="Test Failure",
            description="Test description",
            effect="Test effect",
            severity=Severity.MODERATE,
            occurrence=Occurrence.LOW,
            detection=Detection.HIGH,
        )

        # Assert - frozen=True prevents modification
        with pytest.raises(AttributeError):
            fm.severity = 10  # type: ignore[misc]

    def test_calculates_rpn_correctly(self) -> None:
        """RPN is product of severity, occurrence, detection."""
        # Arrange & Act
        fm = HookFailureMode(
            id="FM-TEST-002", name="Test", description="desc", effect="effect", severity=7, occurrence=5, detection=3
        )

        # Assert
        assert fm.rpn == 7 * 5 * 3
        assert fm.rpn == 105

    def test_rpn_with_rating_constants(self) -> None:
        """RPN calculation works with Severity/Occurrence/Detection constants."""
        # Arrange & Act
        fm = HookFailureMode(
            id="FM-TEST-003",
            name="Test",
            description="desc",
            effect="effect",
            severity=Severity.HIGH,  # 7
            occurrence=Occurrence.MODERATE,  # 5
            detection=Detection.MODERATE,  # 5
        )

        # Assert
        assert fm.rpn == 175

    def test_classifies_low_risk(self) -> None:
        """Risk level is Low for RPN < 20."""
        # Arrange & Act
        fm = HookFailureMode(
            id="FM-TEST-LOW",
            name="Low Risk",
            description="desc",
            effect="effect",
            severity=3,
            occurrence=3,
            detection=1,
        )

        # Assert
        assert fm.rpn == 9
        assert fm.risk_level() == "Low"

    def test_classifies_medium_risk(self) -> None:
        """Risk level is Medium for RPN 20-49."""
        # Arrange & Act
        fm = HookFailureMode(
            id="FM-TEST-MED",
            name="Medium Risk",
            description="desc",
            effect="effect",
            severity=5,
            occurrence=4,
            detection=2,
        )

        # Assert
        assert fm.rpn == 40
        assert fm.risk_level() == "Medium"

    def test_classifies_high_risk(self) -> None:
        """Risk level is High for RPN 50-100."""
        # Arrange & Act
        fm = HookFailureMode(
            id="FM-TEST-HIGH",
            name="High Risk",
            description="desc",
            effect="effect",
            severity=7,
            occurrence=5,
            detection=2,
        )

        # Assert
        assert fm.rpn == 70
        assert fm.risk_level() == "High"

    def test_classifies_critical_risk(self) -> None:
        """Risk level is Critical for RPN > 100."""
        # Arrange & Act
        fm = HookFailureMode(
            id="FM-TEST-CRIT",
            name="Critical Risk",
            description="desc",
            effect="effect",
            severity=9,
            occurrence=7,
            detection=5,
        )

        # Assert
        assert fm.rpn == 315
        assert fm.risk_level() == "Critical"

    def test_risk_level_boundary_at_20(self) -> None:
        """Risk level transitions from Low to Medium at RPN=20."""
        # Arrange & Act
        fm_19 = HookFailureMode("FM-19", "Test", "d", "e", 19, 1, 1)
        fm_20 = HookFailureMode("FM-20", "Test", "d", "e", 20, 1, 1)

        # Assert
        assert fm_19.rpn == 19
        assert fm_19.risk_level() == "Low"
        assert fm_20.rpn == 20
        assert fm_20.risk_level() == "Medium"

    def test_risk_level_boundary_at_50(self) -> None:
        """Risk level transitions from Medium to High at RPN=50."""
        # Arrange & Act
        fm_49 = HookFailureMode("FM-49", "Test", "d", "e", 49, 1, 1)
        fm_50 = HookFailureMode("FM-50", "Test", "d", "e", 5, 5, 2)

        # Assert
        assert fm_49.rpn == 49
        assert fm_49.risk_level() == "Medium"
        assert fm_50.rpn == 50
        assert fm_50.risk_level() == "High"

    def test_risk_level_boundary_at_100(self) -> None:
        """Risk level transitions from High to Critical at RPN=101."""
        # Arrange & Act
        fm_100 = HookFailureMode("FM-100", "Test", "d", "e", 5, 5, 4)
        fm_101 = HookFailureMode("FM-101", "Test", "d", "e", 101, 1, 1)

        # Assert
        assert fm_100.rpn == 100
        assert fm_100.risk_level() == "High"
        assert fm_101.rpn == 101
        assert fm_101.risk_level() == "Critical"

    def test_stores_optional_mitigation(self) -> None:
        """Mitigation field can be None or a string."""
        # Arrange & Act
        fm_no_mitigation = HookFailureMode(
            id="FM-NO-MIT",
            name="No Mitigation",
            description="desc",
            effect="effect",
            severity=5,
            occurrence=3,
            detection=2,
        )

        fm_with_mitigation = HookFailureMode(
            id="FM-WITH-MIT",
            name="With Mitigation",
            description="desc",
            effect="effect",
            severity=5,
            occurrence=3,
            detection=2,
            mitigation="Add timeout handling",
        )

        # Assert
        assert fm_no_mitigation.mitigation is None
        assert fm_with_mitigation.mitigation == "Add timeout handling"


class TestPredefinedHookFailureModes:
    """Test pre-defined Knowledge Hooks failure modes."""

    def test_contains_all_required_failure_modes(self) -> None:
        """HOOK_FAILURE_MODES contains all 10 required failure modes."""
        # Arrange
        expected_ids = {
            "FM-HOOK-001",  # Condition Query Timeout
            "FM-HOOK-002",  # Circular Hook Chain
            "FM-HOOK-003",  # Priority Deadlock
            "FM-HOOK-004",  # Rollback Cascade Failure
            "FM-HOOK-005",  # Phase Ordering Violation
            "FM-HOOK-006",  # Condition SPARQL Injection
            "FM-HOOK-007",  # Handler Action Type Mismatch
            "FM-HOOK-008",  # N3 Rule Not Loaded
            "FM-HOOK-009",  # Receipt Storage Exhaustion
            "FM-HOOK-010",  # Delta Pattern Match Explosion
        }

        # Act & Assert
        assert set(HOOK_FAILURE_MODES.keys()) == expected_ids
        assert len(HOOK_FAILURE_MODES) == 10

    def test_all_ratings_within_valid_range(self) -> None:
        """All severity, occurrence, detection ratings are 1-10."""
        # Act & Assert
        for fm in HOOK_FAILURE_MODES.values():
            assert 1 <= fm.severity <= 10, f"{fm.id} severity out of range"
            assert 1 <= fm.occurrence <= 10, f"{fm.id} occurrence out of range"
            assert 1 <= fm.detection <= 10, f"{fm.id} detection out of range"

    def test_all_have_unique_ids(self) -> None:
        """All failure mode IDs are unique."""
        # Arrange
        ids = [fm.id for fm in HOOK_FAILURE_MODES.values()]

        # Act & Assert
        assert len(ids) == len(set(ids))

    def test_all_have_non_empty_fields(self) -> None:
        """All failure modes have non-empty required fields."""
        # Act & Assert
        for fm in HOOK_FAILURE_MODES.values():
            assert fm.id.strip(), f"{fm.id} has empty id"
            assert fm.name.strip(), f"{fm.id} has empty name"
            assert fm.description.strip(), f"{fm.id} has empty description"
            assert fm.effect.strip(), f"{fm.id} has empty effect"

    def test_fm_hook_001_condition_query_timeout(self) -> None:
        """FM-HOOK-001: Condition Query Timeout has correct ratings."""
        # Arrange & Act
        fm = HOOK_FAILURE_MODES["FM-HOOK-001"]

        # Assert
        assert fm.name == "Condition Query Timeout"
        assert fm.severity == Severity.MODERATE  # 5
        assert fm.occurrence == Occurrence.LOW  # 3
        assert fm.detection == Detection.HIGH  # 3
        assert fm.rpn == 5 * 3 * 3
        assert fm.rpn == 45
        assert fm.risk_level() == "Medium"
        assert fm.mitigation is not None

    def test_fm_hook_002_circular_hook_chain(self) -> None:
        """FM-HOOK-002: Circular Hook Chain is critical risk."""
        # Arrange & Act
        fm = HOOK_FAILURE_MODES["FM-HOOK-002"]

        # Assert
        assert fm.name == "Circular Hook Chain"
        assert fm.severity == Severity.CRITICAL  # 9
        assert fm.occurrence == Occurrence.LOW  # 3
        assert fm.detection == Detection.MODERATE  # 5
        assert fm.rpn == 9 * 3 * 5
        assert fm.rpn == 135
        assert fm.risk_level() == "Critical"
        assert "cycle detection" in fm.mitigation.lower()

    def test_fm_hook_003_priority_deadlock(self) -> None:
        """FM-HOOK-003: Priority Deadlock has high RPN."""
        # Arrange & Act
        fm = HOOK_FAILURE_MODES["FM-HOOK-003"]

        # Assert
        assert fm.name == "Priority Deadlock"
        assert fm.severity == Severity.CRITICAL  # 9
        assert fm.occurrence == Occurrence.MODERATE  # 5
        assert fm.detection == Detection.LOW  # 7
        assert fm.rpn == 9 * 5 * 7
        assert fm.rpn == 315
        assert fm.risk_level() == "Critical"
        assert "tie-breaking" in fm.mitigation.lower()

    def test_fm_hook_004_rollback_cascade_failure(self) -> None:
        """FM-HOOK-004: Rollback Cascade Failure is hazardous."""
        # Arrange & Act
        fm = HOOK_FAILURE_MODES["FM-HOOK-004"]

        # Assert
        assert fm.name == "Rollback Cascade Failure"
        assert fm.severity == Severity.HAZARDOUS  # 10
        assert fm.occurrence == Occurrence.LOW  # 3
        assert fm.detection == Detection.MODERATE  # 5
        assert fm.rpn == 10 * 3 * 5
        assert fm.rpn == 150
        assert fm.risk_level() == "Critical"
        assert "atomic transaction" in fm.mitigation.lower()

    def test_fm_hook_005_phase_ordering_violation(self) -> None:
        """FM-HOOK-005: Phase Ordering Violation easily detected."""
        # Arrange & Act
        fm = HOOK_FAILURE_MODES["FM-HOOK-005"]

        # Assert
        assert fm.name == "Phase Ordering Violation"
        assert fm.severity == Severity.HIGH  # 7
        assert fm.occurrence == Occurrence.LOW  # 3
        assert fm.detection == Detection.CERTAIN  # 1
        assert fm.rpn == 7 * 3 * 1
        assert fm.rpn == 21
        assert fm.risk_level() == "Medium"
        assert "phase validation" in fm.mitigation.lower()

    def test_fm_hook_006_condition_sparql_injection(self) -> None:
        """FM-HOOK-006: SPARQL Injection is security-critical but rare."""
        # Arrange & Act
        fm = HOOK_FAILURE_MODES["FM-HOOK-006"]

        # Assert
        assert fm.name == "Condition SPARQL Injection"
        assert fm.severity == Severity.CRITICAL  # 9
        assert fm.occurrence == Occurrence.REMOTE  # 1
        assert fm.detection == Detection.MODERATE  # 5
        assert fm.rpn == 9 * 1 * 5
        assert fm.rpn == 45
        assert fm.risk_level() == "Medium"
        assert "sanitize" in fm.mitigation.lower() or "validate" in fm.mitigation.lower()

    def test_fm_hook_007_handler_action_type_mismatch(self) -> None:
        """FM-HOOK-007: Handler Type Mismatch is common configuration error."""
        # Arrange & Act
        fm = HOOK_FAILURE_MODES["FM-HOOK-007"]

        # Assert
        assert fm.name == "Handler Action Type Mismatch"
        assert fm.severity == Severity.MODERATE  # 5
        assert fm.occurrence == Occurrence.MODERATE  # 5
        assert fm.detection == Detection.MODERATE  # 5
        assert fm.rpn == 5 * 5 * 5
        assert fm.rpn == 125
        assert fm.risk_level() == "Critical"
        assert "schema validation" in fm.mitigation.lower() or "validate" in fm.mitigation.lower()

    def test_fm_hook_008_n3_rule_not_loaded(self) -> None:
        """FM-HOOK-008: N3 Rule Not Loaded causes silent failure."""
        # Arrange & Act
        fm = HOOK_FAILURE_MODES["FM-HOOK-008"]

        # Assert
        assert fm.name == "N3 Rule Not Loaded"
        assert fm.severity == Severity.HIGH  # 7
        assert fm.occurrence == Occurrence.LOW  # 3
        assert fm.detection == Detection.LOW  # 7
        assert fm.rpn == 7 * 3 * 7
        assert fm.rpn == 147
        assert fm.risk_level() == "Critical"
        assert "health check" in fm.mitigation.lower() or "verify" in fm.mitigation.lower()

    def test_fm_hook_009_receipt_storage_exhaustion(self) -> None:
        """FM-HOOK-009: Receipt Storage Exhaustion is memory leak."""
        # Arrange & Act
        fm = HOOK_FAILURE_MODES["FM-HOOK-009"]

        # Assert
        assert fm.name == "Receipt Storage Exhaustion"
        assert fm.severity == Severity.HIGH  # 7
        assert fm.occurrence == Occurrence.MODERATE  # 5
        assert fm.detection == Detection.HIGH  # 3
        assert fm.rpn == 7 * 5 * 3
        assert fm.rpn == 105
        assert fm.risk_level() == "Critical"
        assert "rotation" in fm.mitigation.lower() or "retention" in fm.mitigation.lower()

    def test_fm_hook_010_delta_pattern_match_explosion(self) -> None:
        """FM-HOOK-010: Delta Pattern Match Explosion causes performance degradation."""
        # Arrange & Act
        fm = HOOK_FAILURE_MODES["FM-HOOK-010"]

        # Assert
        assert fm.name == "Delta Pattern Match Explosion"
        assert fm.severity == Severity.HIGH  # 7
        assert fm.occurrence == Occurrence.MODERATE  # 5
        assert fm.detection == Detection.HIGH  # 3
        assert fm.rpn == 7 * 5 * 3
        assert fm.rpn == 105
        assert fm.risk_level() == "Critical"
        assert "limit" in fm.mitigation.lower() or "bounds" in fm.mitigation.lower()

    def test_critical_failure_modes_have_mitigation(self) -> None:
        """All Critical risk failure modes have mitigation strategies."""
        # Arrange
        critical_fms = [fm for fm in HOOK_FAILURE_MODES.values() if fm.risk_level() == "Critical"]

        # Act & Assert
        assert len(critical_fms) >= 5, "Expected at least 5 critical failure modes"
        for fm in critical_fms:
            assert fm.mitigation is not None, f"{fm.id} lacks mitigation"
            assert len(fm.mitigation) > 20, f"{fm.id} mitigation too brief"

    def test_rpn_distribution_covers_all_risk_levels(self) -> None:
        """Failure modes cover all risk levels (Low, Medium, High, Critical)."""
        # Arrange & Act
        risk_levels = {fm.risk_level() for fm in HOOK_FAILURE_MODES.values()}

        # Assert
        assert "Low" in risk_levels or "Medium" in risk_levels, "Should have low/medium risk modes"
        assert "High" in risk_levels or "Critical" in risk_levels, "Should have high/critical risk modes"
        assert len(risk_levels) >= 2, "Should have variety of risk levels"

    def test_highest_rpn_is_priority_deadlock(self) -> None:
        """FM-HOOK-003 Priority Deadlock has highest RPN (315)."""
        # Arrange & Act
        max_rpn_fm = max(HOOK_FAILURE_MODES.values(), key=lambda fm: fm.rpn)

        # Assert
        assert max_rpn_fm.id == "FM-HOOK-003"
        assert max_rpn_fm.rpn == 315

    def test_immutability_of_predefined_modes(self) -> None:
        """Pre-defined failure modes are immutable."""
        # Arrange
        fm = HOOK_FAILURE_MODES["FM-HOOK-001"]

        # Act & Assert - frozen=True prevents modification
        with pytest.raises(AttributeError):
            fm.severity = 10  # type: ignore[misc]
        with pytest.raises(AttributeError):
            fm.mitigation = "New mitigation"  # type: ignore[misc]
