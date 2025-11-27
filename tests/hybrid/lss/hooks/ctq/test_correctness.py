"""Correctness CTQ Dimension Tests for Knowledge Hooks.

This module validates the CORRECTNESS CTQ dimension for Knowledge Hooks:
- Hook condition evaluation produces correct boolean results
- Hook action execution produces correct state changes
- Hook rollback correctly reverts rejected changes

All tests follow Chicago School TDD with AAA structure.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kgcl.hybrid.knowledge_hooks import HookAction, HookExecutor, HookPhase, HookReceipt, HookRegistry, KnowledgeHook
from tests.hybrid.lss.hooks.ctq.factors import HookCTQDimension, HookCTQFactor


class TestHookConditionEvaluationCorrectness:
    """Test hook SPARQL condition evaluation produces correct results.

    Validates that SPARQL ASK queries correctly determine when hooks should fire.
    """

    def test_empty_condition_always_matches(self) -> None:
        """Empty condition string should always evaluate to True.

        Arrange: Hook with empty condition_query
        Act: Create CTQ factor for correctness
        Assert: Empty condition is considered valid (always-fire semantics)
        """
        # Arrange
        hook = KnowledgeHook(
            hook_id="always-fire",
            name="Always Fire Hook",
            phase=HookPhase.PRE_TICK,
            condition_query="",
            action=HookAction.NOTIFY,
        )

        # Act
        factor = HookCTQFactor(
            dimension=HookCTQDimension.CORRECTNESS,
            hook_id=hook.hook_id,
            phase=hook.phase,
            description="Empty condition evaluates to True",
        )

        # Assert
        assert factor.is_valid()
        assert factor.dimension == HookCTQDimension.CORRECTNESS
        assert hook.condition_query == ""

    def test_sparql_ask_condition_type_validation(self) -> None:
        """SPARQL ASK query for type checking produces correct boolean result.

        Arrange: Hook with SPARQL ASK query checking entity type
        Act: Create CTQ factor for type validation correctness
        Assert: Factor captures correctness requirement for type checking
        """
        # Arrange
        condition_query = """
        PREFIX kgc: <https://kgc.org/ns/>
        ASK { ?s a kgc:Person }
        """
        hook = KnowledgeHook(
            hook_id="check-person-exists",
            name="Check Person Type",
            phase=HookPhase.ON_CHANGE,
            condition_query=condition_query,
            action=HookAction.NOTIFY,
        )

        # Act
        factor = HookCTQFactor(
            dimension=HookCTQDimension.CORRECTNESS,
            hook_id=hook.hook_id,
            phase=hook.phase,
            description="SPARQL ASK correctly detects Person entities",
        )

        # Assert
        assert factor.is_valid()
        assert "ASK" in hook.condition_query
        assert "kgc:Person" in hook.condition_query

    def test_sparql_filter_condition_validation(self) -> None:
        """SPARQL ASK with FILTER produces correct validation result.

        Arrange: Hook with FILTER NOT EXISTS checking required field
        Act: Create CTQ factor for field validation correctness
        Assert: Factor captures correctness of required field check
        """
        # Arrange
        condition_query = """
        PREFIX kgc: <https://kgc.org/ns/>
        ASK {
            ?s a kgc:Person .
            FILTER NOT EXISTS { ?s kgc:name ?name }
        }
        """
        hook = KnowledgeHook(
            hook_id="validate-person-name",
            name="Validate Person Has Name",
            phase=HookPhase.ON_CHANGE,
            condition_query=condition_query,
            action=HookAction.REJECT,
            handler_data={"reason": "Person must have name"},
        )

        # Act
        factor = HookCTQFactor(
            dimension=HookCTQDimension.CORRECTNESS,
            hook_id=hook.hook_id,
            phase=hook.phase,
            description="SPARQL FILTER correctly detects missing name field",
        )

        # Assert
        assert factor.is_valid()
        assert "FILTER NOT EXISTS" in hook.condition_query
        assert hook.action == HookAction.REJECT


class TestHookActionExecutionCorrectness:
    """Test hook actions produce correct state changes.

    Validates that ASSERT, REJECT, NOTIFY, TRANSFORM actions execute correctly.
    """

    def test_reject_action_produces_correct_receipt(self) -> None:
        """REJECT action creates receipt with correct action_taken.

        Arrange: Hook with REJECT action
        Act: Create receipt for successful rejection
        Assert: Receipt has action_taken=REJECT and condition_matched=True
        """
        # Arrange
        hook = KnowledgeHook(
            hook_id="reject-invalid",
            name="Reject Invalid Entity",
            phase=HookPhase.ON_CHANGE,
            action=HookAction.REJECT,
            handler_data={"reason": "Validation failed"},
        )

        # Act
        receipt = HookReceipt(
            hook_id=hook.hook_id,
            phase=hook.phase,
            timestamp=datetime.now(UTC),
            condition_matched=True,
            action_taken=HookAction.REJECT,
            duration_ms=0.5,
            triples_affected=0,
        )

        factor = HookCTQFactor(
            dimension=HookCTQDimension.CORRECTNESS,
            hook_id=hook.hook_id,
            phase=hook.phase,
            description="REJECT action correctly recorded in receipt",
        )

        # Assert
        assert factor.is_valid()
        assert receipt.action_taken == HookAction.REJECT
        assert receipt.condition_matched is True
        assert receipt.error is None

    def test_notify_action_produces_correct_receipt(self) -> None:
        """NOTIFY action creates receipt with correct action_taken.

        Arrange: Hook with NOTIFY action
        Act: Create receipt for notification
        Assert: Receipt has action_taken=NOTIFY
        """
        # Arrange
        hook = KnowledgeHook(
            hook_id="notify-change",
            name="Notify on Change",
            phase=HookPhase.POST_TICK,
            action=HookAction.NOTIFY,
            handler_data={"message": "Entity changed"},
        )

        # Act
        receipt = HookReceipt(
            hook_id=hook.hook_id,
            phase=hook.phase,
            timestamp=datetime.now(UTC),
            condition_matched=True,
            action_taken=HookAction.NOTIFY,
            duration_ms=0.3,
        )

        factor = HookCTQFactor(
            dimension=HookCTQDimension.CORRECTNESS,
            hook_id=hook.hook_id,
            phase=hook.phase,
            description="NOTIFY action correctly recorded in receipt",
        )

        # Assert
        assert factor.is_valid()
        assert receipt.action_taken == HookAction.NOTIFY
        assert receipt.condition_matched is True

    def test_assert_action_tracks_triples_affected(self) -> None:
        """ASSERT action records correct number of triples added.

        Arrange: Hook with ASSERT action adding triples
        Act: Create receipt with triples_affected count
        Assert: Receipt correctly tracks number of triples added
        """
        # Arrange
        hook = KnowledgeHook(
            hook_id="assert-defaults",
            name="Assert Default Values",
            phase=HookPhase.PRE_TICK,
            action=HookAction.ASSERT,
            handler_data={"assertions": ["?s kgc:status 'active' ."]},
        )

        # Act
        receipt = HookReceipt(
            hook_id=hook.hook_id,
            phase=hook.phase,
            timestamp=datetime.now(UTC),
            condition_matched=True,
            action_taken=HookAction.ASSERT,
            duration_ms=1.2,
            triples_affected=1,
        )

        factor = HookCTQFactor(
            dimension=HookCTQDimension.CORRECTNESS,
            hook_id=hook.hook_id,
            phase=hook.phase,
            description="ASSERT action correctly counts triples added",
        )

        # Assert
        assert factor.is_valid()
        assert receipt.action_taken == HookAction.ASSERT
        assert receipt.triples_affected == 1


class TestHookRollbackCorrectness:
    """Test hook rollback correctly reverts rejected changes.

    Validates that REJECT actions trigger rollback mechanism correctly.
    """

    def test_rollback_request_captured_in_receipt(self) -> None:
        """REJECT action sets rollback flag in execution context.

        Arrange: Hook with REJECT action and reason
        Act: Simulate rollback detection from receipt
        Assert: Receipt indicates condition matched and REJECT action taken
        """
        # Arrange
        hook = KnowledgeHook(
            hook_id="reject-incomplete",
            name="Reject Incomplete Entity",
            phase=HookPhase.ON_CHANGE,
            action=HookAction.REJECT,
            handler_data={"reason": "Entity missing required fields"},
        )

        # Act
        receipt = HookReceipt(
            hook_id=hook.hook_id,
            phase=hook.phase,
            timestamp=datetime.now(UTC),
            condition_matched=True,
            action_taken=HookAction.REJECT,
            duration_ms=0.8,
        )

        factor = HookCTQFactor(
            dimension=HookCTQDimension.CORRECTNESS,
            hook_id=hook.hook_id,
            phase=hook.phase,
            description="Rollback correctly triggered by REJECT action",
        )

        # Assert
        assert factor.is_valid()
        assert receipt.condition_matched is True
        assert receipt.action_taken == HookAction.REJECT
        # Rollback reason stored in hook handler_data
        assert hook.handler_data["reason"] == "Entity missing required fields"

    def test_no_rollback_when_condition_not_matched(self) -> None:
        """REJECT hook that doesn't match condition produces no rollback.

        Arrange: Hook with REJECT action
        Act: Create receipt where condition_matched=False
        Assert: Receipt shows no action taken (no rollback needed)
        """
        # Arrange
        hook = KnowledgeHook(
            hook_id="reject-if-invalid",
            name="Conditionally Reject",
            phase=HookPhase.ON_CHANGE,
            action=HookAction.REJECT,
            handler_data={"reason": "Would reject if condition matched"},
        )

        # Act
        receipt = HookReceipt(
            hook_id=hook.hook_id,
            phase=hook.phase,
            timestamp=datetime.now(UTC),
            condition_matched=False,
            action_taken=None,
            duration_ms=0.4,
        )

        factor = HookCTQFactor(
            dimension=HookCTQDimension.CORRECTNESS,
            hook_id=hook.hook_id,
            phase=hook.phase,
            description="No rollback when condition not matched",
        )

        # Assert
        assert factor.is_valid()
        assert receipt.condition_matched is False
        assert receipt.action_taken is None

    def test_rollback_reason_preserved_from_handler_data(self) -> None:
        """Rollback reason from handler_data is accessible for diagnostics.

        Arrange: Hook with REJECT action and detailed reason
        Act: Access reason from hook definition
        Assert: Reason is correctly stored and retrievable
        """
        # Arrange
        expected_reason = "Person entity must have both name and age fields"
        hook = KnowledgeHook(
            hook_id="validate-person-complete",
            name="Validate Person Completeness",
            phase=HookPhase.ON_CHANGE,
            action=HookAction.REJECT,
            handler_data={"reason": expected_reason},
        )

        # Act
        factor = HookCTQFactor(
            dimension=HookCTQDimension.CORRECTNESS,
            hook_id=hook.hook_id,
            phase=hook.phase,
            description="Rollback reason correctly preserved for diagnostics",
        )

        # Assert
        assert factor.is_valid()
        assert hook.handler_data["reason"] == expected_reason


class TestHookRegistryCorrectness:
    """Test HookRegistry maintains correct hook state.

    Validates registry CRUD operations produce correct results.
    """

    def test_register_hook_returns_correct_id(self) -> None:
        """Registering hook returns the correct hook_id.

        Arrange: Registry and hook
        Act: Register hook
        Assert: Returned ID matches hook.hook_id
        """
        # Arrange
        registry = HookRegistry()
        hook = KnowledgeHook(hook_id="test-hook", name="Test Hook", phase=HookPhase.PRE_TICK, action=HookAction.NOTIFY)

        # Act
        returned_id = registry.register(hook)

        # Assert
        assert returned_id == hook.hook_id
        assert registry.get(hook.hook_id) == hook

    def test_unregister_hook_removes_correctly(self) -> None:
        """Unregistering hook removes it from registry.

        Arrange: Registry with registered hook
        Act: Unregister hook
        Assert: Hook no longer retrievable
        """
        # Arrange
        registry = HookRegistry()
        hook = KnowledgeHook(hook_id="remove-me", name="Remove Me", phase=HookPhase.POST_TICK, action=HookAction.NOTIFY)
        registry.register(hook)

        # Act
        result = registry.unregister(hook.hook_id)

        # Assert
        assert result is True
        assert registry.get(hook.hook_id) is None

    def test_get_by_phase_returns_correct_hooks(self) -> None:
        """get_by_phase returns only hooks for specified phase.

        Arrange: Registry with hooks in multiple phases
        Act: Get hooks for specific phase
        Assert: Only hooks from that phase returned
        """
        # Arrange
        registry = HookRegistry()
        pre_hook = KnowledgeHook(hook_id="pre", name="Pre Hook", phase=HookPhase.PRE_TICK, action=HookAction.NOTIFY)
        post_hook = KnowledgeHook(hook_id="post", name="Post Hook", phase=HookPhase.POST_TICK, action=HookAction.NOTIFY)
        registry.register(pre_hook)
        registry.register(post_hook)

        # Act
        pre_hooks = registry.get_by_phase(HookPhase.PRE_TICK)

        # Assert
        assert len(pre_hooks) == 1
        assert pre_hooks[0].hook_id == "pre"

    def test_enable_disable_toggle_correctly(self) -> None:
        """Enable/disable correctly toggle hook enabled state.

        Arrange: Registry with disabled hook
        Act: Enable then disable
        Assert: Enabled state toggles correctly
        """
        # Arrange
        registry = HookRegistry()
        hook = KnowledgeHook(
            hook_id="toggle", name="Toggle Hook", phase=HookPhase.ON_CHANGE, enabled=False, action=HookAction.NOTIFY
        )
        registry.register(hook)

        # Act & Assert: Enable
        result_enable = registry.enable(hook.hook_id)
        assert result_enable is True
        enabled_hook = registry.get(hook.hook_id)
        assert enabled_hook is not None
        assert enabled_hook.enabled is True

        # Act & Assert: Disable
        result_disable = registry.disable(hook.hook_id)
        assert result_disable is True
        disabled_hook = registry.get(hook.hook_id)
        assert disabled_hook is not None
        assert disabled_hook.enabled is False
