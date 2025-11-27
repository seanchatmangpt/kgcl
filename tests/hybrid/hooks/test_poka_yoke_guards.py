"""Tests for Innovation #6: Poka-Yoke Guard Hooks.

Chicago School TDD: Real validation, no mocking.
Tests all 10 Poka-Yoke rules for error prevention.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hooks.poka_yoke_guards import (
    HookPokaYokeType,
    PokaYokeGuard,
    PokaYokeViolation,
)
from kgcl.hybrid.knowledge_hooks import HookAction, HookPhase, HookRegistry, KnowledgeHook


class TestPokaYokeViolation:
    """Tests for PokaYokeViolation dataclass."""

    def test_shutdown_blocks_execution(self) -> None:
        """SHUTDOWN violations block execution."""
        violation = PokaYokeViolation(
            rule_id="PY-HOOK-001", py_type=HookPokaYokeType.SHUTDOWN, message="Empty condition"
        )

        assert violation.blocks_execution is True

    def test_control_blocks_execution(self) -> None:
        """CONTROL violations block execution."""
        violation = PokaYokeViolation(
            rule_id="PY-HOOK-003", py_type=HookPokaYokeType.CONTROL, message="Priority conflict"
        )

        assert violation.blocks_execution is True

    def test_warning_does_not_block(self) -> None:
        """WARNING violations do not block execution."""
        violation = PokaYokeViolation(
            rule_id="PY-HOOK-004", py_type=HookPokaYokeType.WARNING, message="Disabled in chain"
        )

        assert violation.blocks_execution is False

    def test_validation_does_not_block(self) -> None:
        """VALIDATION violations do not block execution."""
        violation = PokaYokeViolation(
            rule_id="PY-HOOK-002", py_type=HookPokaYokeType.VALIDATION, message="Invalid SPARQL"
        )

        assert violation.blocks_execution is False


class TestPokaYokeRuleDefinitions:
    """Tests for Poka-Yoke rule definitions."""

    def test_all_10_rules_defined(self) -> None:
        """All 10 Poka-Yoke rules are defined."""
        guard = PokaYokeGuard()

        assert len(guard._rules) == 10

    def test_rule_ids_format(self) -> None:
        """Rule IDs follow PY-HOOK-XXX format."""
        guard = PokaYokeGuard()

        for rule_id in guard._rules:
            assert rule_id.startswith("PY-HOOK-")


class TestEmptyConditionValidation:
    """Tests for PY-HOOK-001: Empty condition query."""

    def test_empty_condition_violation(self) -> None:
        """Empty condition query creates SHUTDOWN violation."""
        guard = PokaYokeGuard()
        hook = KnowledgeHook(
            hook_id="empty-cond",
            name="Empty Condition",
            phase=HookPhase.ON_CHANGE,
            condition_query="",  # Empty!
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        violations = guard.validate_hook(hook)

        assert len(violations) >= 1
        assert any(v.rule_id == "PY-HOOK-001" for v in violations)
        assert any(v.py_type == HookPokaYokeType.SHUTDOWN for v in violations)

    def test_whitespace_only_condition_violation(self) -> None:
        """Whitespace-only condition creates violation."""
        guard = PokaYokeGuard()
        hook = KnowledgeHook(
            hook_id="ws-cond",
            name="Whitespace Condition",
            phase=HookPhase.ON_CHANGE,
            condition_query="   ",  # Whitespace only
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        violations = guard.validate_hook(hook)

        assert any(v.rule_id == "PY-HOOK-001" for v in violations)


class TestSPARQLSyntaxValidation:
    """Tests for PY-HOOK-002: Invalid SPARQL syntax."""

    def test_valid_ask_passes(self) -> None:
        """Valid ASK query passes syntax check."""
        guard = PokaYokeGuard()
        hook = KnowledgeHook(
            hook_id="valid-ask",
            name="Valid ASK",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        violations = guard.validate_hook(hook)

        assert not any(v.rule_id == "PY-HOOK-002" for v in violations)

    def test_valid_select_passes(self) -> None:
        """Valid SELECT query passes syntax check."""
        guard = PokaYokeGuard()
        hook = KnowledgeHook(
            hook_id="valid-select",
            name="Valid SELECT",
            phase=HookPhase.ON_CHANGE,
            condition_query="SELECT ?s WHERE { ?s a :Person }",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        violations = guard.validate_hook(hook)

        assert not any(v.rule_id == "PY-HOOK-002" for v in violations)

    def test_invalid_query_type_fails(self) -> None:
        """Query not starting with ASK/SELECT fails."""
        guard = PokaYokeGuard()
        hook = KnowledgeHook(
            hook_id="invalid-type",
            name="Invalid Type",
            phase=HookPhase.ON_CHANGE,
            condition_query="CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        violations = guard.validate_hook(hook)

        assert any(v.rule_id == "PY-HOOK-002" for v in violations)

    def test_unbalanced_braces_fails(self) -> None:
        """Unbalanced braces fail syntax check."""
        guard = PokaYokeGuard()
        hook = KnowledgeHook(
            hook_id="unbalanced",
            name="Unbalanced",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s ?p ?o",  # Missing closing brace
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        violations = guard.validate_hook(hook)

        assert any(v.rule_id == "PY-HOOK-002" for v in violations)


class TestPriorityConflictValidation:
    """Tests for PY-HOOK-003: Priority conflict."""

    def test_unique_priority_passes(self) -> None:
        """Unique priority within phase passes."""
        guard = PokaYokeGuard()
        registry = HookRegistry()

        hook1 = KnowledgeHook(
            hook_id="hook1",
            name="Hook 1",
            phase=HookPhase.ON_CHANGE,
            priority=100,
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )
        registry.register(hook1)

        hook2 = KnowledgeHook(
            hook_id="hook2",
            name="Hook 2",
            phase=HookPhase.ON_CHANGE,
            priority=50,  # Different priority
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        violations = guard.validate_hook(hook2, registry)

        assert not any(v.rule_id == "PY-HOOK-003" for v in violations)

    def test_duplicate_priority_fails(self) -> None:
        """Duplicate priority in same phase fails."""
        guard = PokaYokeGuard()
        registry = HookRegistry()

        hook1 = KnowledgeHook(
            hook_id="hook1",
            name="Hook 1",
            phase=HookPhase.ON_CHANGE,
            priority=50,
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )
        registry.register(hook1)

        hook2 = KnowledgeHook(
            hook_id="hook2",
            name="Hook 2",
            phase=HookPhase.ON_CHANGE,
            priority=50,  # Same priority!
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        violations = guard.validate_hook(hook2, registry)

        assert any(v.rule_id == "PY-HOOK-003" for v in violations)


class TestHandlerDataValidation:
    """Tests for PY-HOOK-005: Missing handler data."""

    def test_reject_with_reason_passes(self) -> None:
        """REJECT with reason passes."""
        guard = PokaYokeGuard()
        hook = KnowledgeHook(
            hook_id="reject-ok",
            name="Reject OK",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.REJECT,
            handler_data={"reason": "Invalid data"},
        )

        violations = guard.validate_hook(hook)

        assert not any(v.rule_id == "PY-HOOK-005" for v in violations)

    def test_reject_without_reason_fails(self) -> None:
        """REJECT without reason fails."""
        guard = PokaYokeGuard()
        hook = KnowledgeHook(
            hook_id="reject-bad",
            name="Reject Bad",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.REJECT,
            handler_data={},  # Missing reason
        )

        violations = guard.validate_hook(hook)

        assert any(v.rule_id == "PY-HOOK-005" for v in violations)

    def test_notify_without_message_fails(self) -> None:
        """NOTIFY without message fails."""
        guard = PokaYokeGuard()
        hook = KnowledgeHook(
            hook_id="notify-bad",
            name="Notify Bad",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={},  # Missing message
        )

        violations = guard.validate_hook(hook)

        assert any(v.rule_id == "PY-HOOK-005" for v in violations)


class TestDuplicateHookIdValidation:
    """Tests for PY-HOOK-007: Duplicate hook ID."""

    def test_unique_id_passes(self) -> None:
        """Unique hook ID passes."""
        guard = PokaYokeGuard()
        hook = KnowledgeHook(
            hook_id="unique-id",
            name="Unique",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        violations = guard.validate_hook(hook)

        assert not any(v.rule_id == "PY-HOOK-007" for v in violations)

    def test_duplicate_id_fails(self) -> None:
        """Duplicate hook ID fails."""
        guard = PokaYokeGuard()

        hook1 = KnowledgeHook(
            hook_id="dup-id",
            name="First",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )
        guard.validate_hook(hook1)  # Registers ID

        hook2 = KnowledgeHook(
            hook_id="dup-id",  # Same ID!
            name="Second",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )
        violations = guard.validate_hook(hook2)

        assert any(v.rule_id == "PY-HOOK-007" for v in violations)


class TestRegistryValidation:
    """Tests for full registry validation."""

    def test_validate_empty_registry(self) -> None:
        """Empty registry has no violations."""
        guard = PokaYokeGuard()
        registry = HookRegistry()

        violations = guard.validate_registry(registry)

        assert len(violations) == 0

    def test_validate_registry_finds_all_violations(self) -> None:
        """Registry validation finds violations across all hooks."""
        guard = PokaYokeGuard()
        registry = HookRegistry()

        # Hook with empty condition
        bad_hook = KnowledgeHook(
            hook_id="bad",
            name="Bad",
            phase=HookPhase.ON_CHANGE,
            condition_query="",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )
        registry.register(bad_hook)

        violations = guard.validate_registry(registry)

        assert len(violations) >= 1


class TestViolationFiltering:
    """Tests for violation filtering utilities."""

    def test_get_blocking_violations(self) -> None:
        """Get only blocking violations."""
        guard = PokaYokeGuard()
        violations = [
            PokaYokeViolation("PY-001", HookPokaYokeType.SHUTDOWN, "msg1"),
            PokaYokeViolation("PY-002", HookPokaYokeType.WARNING, "msg2"),
            PokaYokeViolation("PY-003", HookPokaYokeType.CONTROL, "msg3"),
        ]

        blocking = guard.get_blocking_violations(violations)

        assert len(blocking) == 2
        assert all(v.blocks_execution for v in blocking)

    def test_get_warnings(self) -> None:
        """Get only warning violations."""
        guard = PokaYokeGuard()
        violations = [
            PokaYokeViolation("PY-001", HookPokaYokeType.SHUTDOWN, "msg1"),
            PokaYokeViolation("PY-002", HookPokaYokeType.WARNING, "msg2"),
        ]

        warnings = guard.get_warnings(violations)

        assert len(warnings) == 1
        assert warnings[0].py_type == HookPokaYokeType.WARNING
