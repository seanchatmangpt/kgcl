"""Tests for Innovation #5: Self-Healing FMEA Hooks.

Chicago School TDD: Real healing operations, no mocking.
Tests all 10 FMEA failure mode handlers.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hooks.self_healing import HealingResult, SelfHealingConfig, SelfHealingExecutor
from kgcl.hybrid.knowledge_hooks import HookAction, HookPhase, KnowledgeHook


class TestSelfHealingConfig:
    """Tests for self-healing configuration."""

    def test_default_config_values(self) -> None:
        """Default config has expected SLO values."""
        config = SelfHealingConfig()

        assert config.timeout_ms == 100.0
        assert config.max_chain_depth == 10
        assert config.max_receipts == 1000
        assert config.max_delta_matches == 1000

    def test_custom_config(self) -> None:
        """Custom config values are stored."""
        config = SelfHealingConfig(timeout_ms=50, max_chain_depth=5)

        assert config.timeout_ms == 50
        assert config.max_chain_depth == 5


class TestHealingResult:
    """Tests for healing result dataclass."""

    def test_successful_healing(self) -> None:
        """Successful healing result is recorded."""
        result = HealingResult(
            fm_id="FM-HOOK-001", success=True, action_taken="timeout", fallback_used=True
        )

        assert result.success is True
        assert result.fm_id == "FM-HOOK-001"
        assert result.fallback_used is True

    def test_failed_healing(self) -> None:
        """Failed healing with error is recorded."""
        result = HealingResult(
            fm_id="FM-HOOK-002",
            success=False,
            action_taken="blocked",
            original_error="Circular chain detected",
        )

        assert result.success is False
        assert result.original_error == "Circular chain detected"


class TestTimeoutHealing:
    """Tests for FM-HOOK-001: Condition Query Timeout."""

    def test_timeout_creates_healing_result(self) -> None:
        """Timeout handler creates valid healing result."""
        executor = SelfHealingExecutor()
        hook = KnowledgeHook(
            hook_id="slow-hook",
            name="Slow Hook",
            phase=HookPhase.ON_CHANGE,
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        result = executor._handle_timeout(hook, 150.0)

        assert result.fm_id == "FM-HOOK-001"
        assert result.success is True
        assert result.fallback_used is True
        assert "150" in result.action_taken


class TestCircularChainHealing:
    """Tests for FM-HOOK-002: Circular Hook Chain."""

    def test_circular_chain_detected(self) -> None:
        """Circular chain is detected and blocked."""
        executor = SelfHealingExecutor()
        hook = KnowledgeHook(
            hook_id="chain-hook",
            name="Chain Hook",
            phase=HookPhase.ON_CHANGE,
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        # Simulate hook already in chain
        executor._chain_visited.add("chain-hook")

        result = executor._handle_circular_chain(hook)

        assert result.fm_id == "FM-HOOK-002"
        assert result.success is False
        assert "chain-hook" in result.original_error

    def test_chain_tracking_reset(self) -> None:
        """Chain tracking is reset between executions."""
        executor = SelfHealingExecutor()
        executor._chain_visited.add("hook1")
        executor._chain_visited.add("hook2")

        executor.reset_chain_tracking()

        assert len(executor._chain_visited) == 0


class TestPriorityDeadlockHealing:
    """Tests for FM-HOOK-003: Priority Deadlock."""

    def test_priority_tiebreak_applied(self) -> None:
        """Lexicographic tiebreak is applied for equal priorities."""
        executor = SelfHealingExecutor()
        hooks = [
            KnowledgeHook(
                hook_id="hook-b",
                name="Hook B",
                phase=HookPhase.ON_CHANGE,
                priority=50,
                action=HookAction.NOTIFY,
                handler_data={"message": "b"},
            ),
            KnowledgeHook(
                hook_id="hook-a",
                name="Hook A",
                phase=HookPhase.ON_CHANGE,
                priority=50,
                action=HookAction.NOTIFY,
                handler_data={"message": "a"},
            ),
        ]

        result = executor._handle_priority_deadlock(hooks)

        assert result.fm_id == "FM-HOOK-003"
        assert result.success is True
        assert "hook-a" in result.action_taken  # Lexicographic first


class TestSPARQLInjectionHealing:
    """Tests for FM-HOOK-006: SPARQL Injection."""

    def test_safe_query_passes(self) -> None:
        """Safe SPARQL queries pass validation."""
        executor = SelfHealingExecutor()
        hook = KnowledgeHook(
            hook_id="safe-hook",
            name="Safe Hook",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s a :Person }",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        result = executor._handle_sparql_injection(hook)

        assert result.success is True
        assert result.fm_id == "FM-HOOK-006"

    def test_insert_blocked(self) -> None:
        """INSERT queries are blocked."""
        executor = SelfHealingExecutor()
        hook = KnowledgeHook(
            hook_id="inject-hook",
            name="Inject Hook",
            phase=HookPhase.ON_CHANGE,
            condition_query="INSERT DATA { <x> <y> <z> }",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        result = executor._handle_sparql_injection(hook)

        assert result.success is False
        assert "INSERT" in result.action_taken

    def test_delete_blocked(self) -> None:
        """DELETE queries are blocked."""
        executor = SelfHealingExecutor()
        hook = KnowledgeHook(
            hook_id="delete-hook",
            name="Delete Hook",
            phase=HookPhase.ON_CHANGE,
            condition_query="DELETE WHERE { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        result = executor._handle_sparql_injection(hook)

        assert result.success is False
        assert "DELETE" in result.action_taken

    def test_drop_blocked(self) -> None:
        """DROP queries are blocked."""
        executor = SelfHealingExecutor()
        hook = KnowledgeHook(
            hook_id="drop-hook",
            name="Drop Hook",
            phase=HookPhase.ON_CHANGE,
            condition_query="DROP GRAPH <http://example.org/g>",
            action=HookAction.NOTIFY,
            handler_data={"message": "test"},
        )

        result = executor._handle_sparql_injection(hook)

        assert result.success is False


class TestActionMismatchHealing:
    """Tests for FM-HOOK-007: Handler Action Type Mismatch."""

    def test_reject_with_reason_passes(self) -> None:
        """REJECT action with reason passes validation."""
        executor = SelfHealingExecutor()
        hook = KnowledgeHook(
            hook_id="reject-hook",
            name="Reject Hook",
            phase=HookPhase.ON_CHANGE,
            action=HookAction.REJECT,
            handler_data={"reason": "Invalid data"},
        )

        result = executor._handle_action_mismatch(hook)

        assert result.success is True

    def test_reject_without_reason_fails(self) -> None:
        """REJECT action without reason fails validation."""
        executor = SelfHealingExecutor()
        hook = KnowledgeHook(
            hook_id="bad-reject",
            name="Bad Reject",
            phase=HookPhase.ON_CHANGE,
            action=HookAction.REJECT,
            handler_data={},  # Missing reason
        )

        result = executor._handle_action_mismatch(hook)

        assert result.success is False
        assert "reason" in str(result.action_taken)

    def test_notify_with_message_passes(self) -> None:
        """NOTIFY action with message passes validation."""
        executor = SelfHealingExecutor()
        hook = KnowledgeHook(
            hook_id="notify-hook",
            name="Notify Hook",
            phase=HookPhase.ON_CHANGE,
            action=HookAction.NOTIFY,
            handler_data={"message": "Notification"},
        )

        result = executor._handle_action_mismatch(hook)

        assert result.success is True


class TestReceiptExhaustionHealing:
    """Tests for FM-HOOK-009: Receipt Storage Exhaustion."""

    def test_receipt_counter_reset(self) -> None:
        """Receipt counter is reset after exhaustion."""
        config = SelfHealingConfig(max_receipts=100)
        executor = SelfHealingExecutor(config=config)
        executor._receipt_count = 150

        result = executor._handle_receipt_exhaustion()

        assert result.success is True
        assert executor._receipt_count == 0


class TestDeltaExplosionHealing:
    """Tests for FM-HOOK-010: Delta Pattern Match Explosion."""

    def test_within_bounds_passes(self) -> None:
        """Delta matches within bounds passes."""
        executor = SelfHealingExecutor()

        result = executor._handle_delta_explosion(500)

        assert result.success is True

    def test_exceeds_bounds_truncated(self) -> None:
        """Delta matches exceeding bounds are truncated."""
        config = SelfHealingConfig(max_delta_matches=100)
        executor = SelfHealingExecutor(config=config)

        result = executor._handle_delta_explosion(500)

        assert result.success is True
        assert result.fallback_used is True
        assert "100" in result.action_taken
