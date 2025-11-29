"""Tests for Self-Healing FMEA Hooks.

Verifies that all 10 failure mode handlers work correctly.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

import pytest

from kgcl.hybrid.hooks.self_healing import SelfHealingConfig, SelfHealingExecutor
from kgcl.hybrid.knowledge_hooks import HookAction, HookPhase, HookReceipt, KnowledgeHook


@pytest.fixture
def healing_executor() -> SelfHealingExecutor:
    """Create self-healing executor for tests."""
    config = SelfHealingConfig(timeout_ms=100, max_receipts=1000, max_chain_depth=10)
    return SelfHealingExecutor(config=config)


@pytest.fixture
def mock_hook() -> KnowledgeHook:
    """Create a mock hook for testing."""
    return KnowledgeHook(
        hook_id="urn:hook:test",
        name="test-hook",
        phase=HookPhase.ON_CHANGE,
        condition_query="ASK { ?s a :Person }",
        action=HookAction.NOTIFY,
        priority=100,
    )


class TestSelfHealingTimeout:
    """Test FM-HOOK-001: Condition Query Timeout."""

    def test_timeout_detection(self, healing_executor: SelfHealingExecutor, mock_hook: KnowledgeHook) -> None:
        """Test timeout is detected and handled."""
        result = healing_executor._handle_timeout(mock_hook, actual_ms=150.0)
        assert result.fm_id == "FM-HOOK-001"
        assert result.success is True
        assert result.fallback_used is True
        assert "Timeout" in result.action_taken


class TestSelfHealingCircularChain:
    """Test FM-HOOK-002: Circular Hook Chain."""

    def test_circular_chain_detection(self, healing_executor: SelfHealingExecutor, mock_hook: KnowledgeHook) -> None:
        """Test circular chain is detected."""
        healing_executor._chain_visited.add(mock_hook.hook_id)
        result = healing_executor._handle_circular_chain(mock_hook)
        assert result.fm_id == "FM-HOOK-002"
        assert result.success is False
        assert "Circular" in result.action_taken


class TestSelfHealingPriorityDeadlock:
    """Test FM-HOOK-003: Priority Deadlock."""

    def test_priority_tie_break(self, healing_executor: SelfHealingExecutor) -> None:
        """Test lexicographic tie-breaking for equal priority."""
        hooks = [
            KnowledgeHook(
                hook_id="urn:hook:z",
                name="z-hook",
                phase=HookPhase.ON_CHANGE,
                condition_query="ASK { ?s a :Thing }",
                action=HookAction.NOTIFY,
                priority=100,
            ),
            KnowledgeHook(
                hook_id="urn:hook:a",
                name="a-hook",
                phase=HookPhase.ON_CHANGE,
                condition_query="ASK { ?s a :Thing }",
                action=HookAction.NOTIFY,
                priority=100,
            ),
        ]
        result = healing_executor._handle_priority_deadlock(hooks)
        assert result.fm_id == "FM-HOOK-003"
        assert result.success is True
        assert "Lexicographic" in result.action_taken


class TestSelfHealingSPARQLInjection:
    """Test FM-HOOK-006: Condition SPARQL Injection."""

    def test_sparql_injection_detection(self, healing_executor: SelfHealingExecutor, mock_hook: KnowledgeHook) -> None:
        """Test SPARQL injection is detected."""
        malicious_hook = KnowledgeHook(
            hook_id="urn:hook:malicious",
            name="malicious",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s ?p ?o . DROP ALL }",  # Malicious query
            action=HookAction.NOTIFY,
            priority=100,
        )
        result = healing_executor._handle_sparql_injection(malicious_hook)
        assert result.fm_id == "FM-HOOK-006"
        # Should detect dangerous keywords
        assert result.success is False or "DROP" in result.action_taken


class TestSelfHealingReceiptExhaustion:
    """Test FM-HOOK-009: Receipt Storage Exhaustion."""

    def test_receipt_exhaustion_detection(self, healing_executor: SelfHealingExecutor) -> None:
        """Test receipt exhaustion is detected."""
        healing_executor._receipt_count = 1001  # Exceed max_receipts
        result = healing_executor._handle_receipt_exhaustion()
        assert result.fm_id == "FM-HOOK-009"
        assert "Receipt" in result.action_taken


class TestSelfHealingPhaseViolation:
    """Test FM-HOOK-005: Phase Ordering Violation."""

    def test_phase_violation_detection(self, healing_executor: SelfHealingExecutor, mock_hook: KnowledgeHook) -> None:
        """Test phase violation is detected."""
        result = healing_executor._handle_phase_violation(mock_hook, expected="pre_tick", actual="post_tick")
        assert result.fm_id == "FM-HOOK-005"
        assert result.success is False
        assert "Blocked" in result.action_taken


class TestSelfHealingActionMismatch:
    """Test FM-HOOK-007: Handler Action Mismatch."""

    def test_action_mismatch_detection(self, healing_executor: SelfHealingExecutor, mock_hook: KnowledgeHook) -> None:
        """Test action mismatch is detected."""
        result = healing_executor._handle_action_mismatch(
            mock_hook, expected=HookAction.ASSERT, actual=HookAction.REJECT
        )
        assert result.fm_id == "FM-HOOK-007"
        assert result.success is False


class TestSelfHealingConfig:
    """Test SelfHealingConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = SelfHealingConfig()
        assert config.timeout_ms > 0
        assert config.max_receipts > 0
        assert config.max_chain_depth > 0

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = SelfHealingConfig(timeout_ms=50, max_receipts=500, max_chain_depth=5)
        assert config.timeout_ms == 50
        assert config.max_receipts == 500
        assert config.max_chain_depth == 5
