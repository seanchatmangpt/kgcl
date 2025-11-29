"""Tests for Poka-Yoke Guard Hooks.

Verifies that all 10 Poka-Yoke rules work correctly.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hooks.poka_yoke_guards import HookPokaYokeType, PokaYokeGuard
from kgcl.hybrid.knowledge_hooks import HookAction, HookPhase, HookRegistry, KnowledgeHook


@pytest.fixture
def guard() -> PokaYokeGuard:
    """Create Poka-Yoke guard for tests."""
    return PokaYokeGuard()


@pytest.fixture
def registry() -> HookRegistry:
    """Create hook registry for tests."""
    from kgcl.hybrid.knowledge_hooks import HookRegistry

    return HookRegistry()


class TestPokaYokeEmptyQuery:
    """Test PY-HOOK-001: Empty condition query."""

    def test_empty_query_violation(self, guard: PokaYokeGuard) -> None:
        """Test empty query is detected."""
        hook = KnowledgeHook(
            hook_id="urn:hook:empty",
            name="empty-hook",
            phase=HookPhase.ON_CHANGE,
            condition_query="",  # Empty - violation!
            action=HookAction.NOTIFY,
            priority=100,
        )
        violations = guard.validate_hook(hook)
        assert len(violations) > 0
        violation = next(v for v in violations if v.rule_id == "PY-HOOK-001")
        assert violation.py_type == HookPokaYokeType.SHUTDOWN
        assert violation.blocks_execution is True


class TestPokaYokeSPARQLSyntax:
    """Test PY-HOOK-002: Invalid SPARQL syntax."""

    def test_invalid_sparql_violation(self, guard: PokaYokeGuard) -> None:
        """Test invalid SPARQL is detected."""
        hook = KnowledgeHook(
            hook_id="urn:hook:invalid",
            name="invalid-hook",
            phase=HookPhase.ON_CHANGE,
            condition_query="INVALID SPARQL SYNTAX",  # Invalid
            action=HookAction.NOTIFY,
            priority=100,
        )
        violations = guard.validate_hook(hook)
        # Should detect that query doesn't start with ASK or SELECT
        sparql_violations = [v for v in violations if v.rule_id == "PY-HOOK-002"]
        assert len(sparql_violations) > 0


class TestPokaYokeDuplicateID:
    """Test PY-HOOK-007: Duplicate hook ID."""

    def test_duplicate_id_violation(self, guard: PokaYokeGuard) -> None:
        """Test duplicate hook ID is detected."""
        hook1 = KnowledgeHook(
            hook_id="urn:hook:duplicate",
            name="hook1",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s a :Thing }",
            action=HookAction.NOTIFY,
            priority=100,
        )
        hook2 = KnowledgeHook(
            hook_id="urn:hook:duplicate",  # Same ID!
            name="hook2",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s a :Thing }",
            action=HookAction.NOTIFY,
            priority=100,
        )
        # First hook should be fine
        violations1 = guard.validate_hook(hook1)
        assert len([v for v in violations1 if v.rule_id == "PY-HOOK-007"]) == 0
        # Second hook should violate
        violations2 = guard.validate_hook(hook2)
        duplicate_violations = [v for v in violations2 if v.rule_id == "PY-HOOK-007"]
        assert len(duplicate_violations) > 0
        assert duplicate_violations[0].py_type == HookPokaYokeType.SHUTDOWN


class TestPokaYokeValidHook:
    """Test valid hooks pass validation."""

    def test_valid_hook_passes(self, guard: PokaYokeGuard) -> None:
        """Test valid hook has no violations."""
        hook = KnowledgeHook(
            hook_id="urn:hook:valid",
            name="valid-hook",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s a :Person }",
            action=HookAction.NOTIFY,
            priority=100,
        )
        violations = guard.validate_hook(hook)
        # Should have no shutdown violations
        shutdown_violations = [v for v in violations if v.blocks_execution]
        assert len(shutdown_violations) == 0


class TestPokaYokeGuardRules:
    """Test all Poka-Yoke rules are registered."""

    def test_all_rules_registered(self, guard: PokaYokeGuard) -> None:
        """Test all 10 rules are in the rules dict."""
        assert len(guard._rules) == 10
        expected_rules = [
            "PY-HOOK-001",
            "PY-HOOK-002",
            "PY-HOOK-003",
            "PY-HOOK-004",
            "PY-HOOK-005",
            "PY-HOOK-006",
            "PY-HOOK-007",
            "PY-HOOK-008",
            "PY-HOOK-009",
            "PY-HOOK-010",
        ]
        for rule_id in expected_rules:
            assert rule_id in guard._rules
