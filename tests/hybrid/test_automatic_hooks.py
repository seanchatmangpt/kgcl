"""Integration tests for automatic hook execution on data load.

Chicago School TDD: Real HybridEngine, real HookRegistry, real PyOxigraph.
No mocking. Tests verify hooks fire automatically when data is added.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid import HybridEngine
from kgcl.hybrid.knowledge_hooks import HookAction, HookPhase, HookRegistry, KnowledgeHook


class TestAutomaticHookExecution:
    """Tests for automatic ON_CHANGE hook execution on load_data()."""

    def test_engine_without_registry_loads_normally(self) -> None:
        """Engine without hook registry loads data without hook execution.

        Verifies backward compatibility - engines created without registry
        behave exactly as before.
        """
        engine = HybridEngine()

        data = """
        @prefix ex: <http://example.org/> .
        ex:Alice ex:name "Alice" .
        """
        engine.load_data(data)

        # Data loaded successfully
        assert len(list(engine.store)) > 0

    def test_load_data_triggers_on_change_hooks(self) -> None:
        """ON_CHANGE hooks fire automatically when data is loaded.

        Verifies the reactive event-driven architecture - hooks respond
        to state changes immediately upon data addition.
        """
        # Setup: Create registry with ON_CHANGE hook
        registry = HookRegistry()
        hook = KnowledgeHook(
            hook_id="track-person",
            name="Track Person Addition",
            phase=HookPhase.ON_CHANGE,
            priority=50,
            enabled=True,
            condition_query="ASK { ?s a <http://example.org/Person> }",
            action=HookAction.NOTIFY,
            handler_data={"message": "Person added to graph"},
        )
        registry.register(hook)

        # Create engine with registry
        engine = HybridEngine(hook_registry=registry)

        # Load data that matches hook condition
        data = """
        @prefix ex: <http://example.org/> .
        ex:Alice a ex:Person ;
            ex:name "Alice" .
        """
        engine.load_data(data)

        # Verify hook executed - check receipts
        receipts = registry.get_receipts(hook_id="track-person")
        assert len(receipts) >= 1
        assert receipts[0].phase == HookPhase.ON_CHANGE
        assert receipts[0].condition_matched is True

    def test_load_data_with_trigger_hooks_false_skips_hooks(self) -> None:
        """Setting trigger_hooks=False skips hook execution.

        This is useful when loading hook definitions themselves to avoid
        infinite recursion or when bulk-loading data.
        """
        # Setup: Create registry with ON_CHANGE hook
        registry = HookRegistry()
        hook = KnowledgeHook(
            hook_id="always-fire",
            name="Always Fire",
            phase=HookPhase.ON_CHANGE,
            priority=50,
            enabled=True,
            condition_query="",  # Empty = always match
            action=HookAction.NOTIFY,
            handler_data={"message": "Data loaded"},
        )
        registry.register(hook)

        engine = HybridEngine(hook_registry=registry)

        # Load with hooks disabled
        data = """
        @prefix ex: <http://example.org/> .
        ex:Bob ex:name "Bob" .
        """
        engine.load_data(data, trigger_hooks=False)

        # Verify NO receipts recorded (hook didn't fire)
        receipts = registry.get_receipts(hook_id="always-fire")
        assert len(receipts) == 0

    def test_hook_condition_not_matched_does_not_fire_action(self) -> None:
        """Hook with unmatched condition does not fire its action.

        Verifies conditional execution - only matching hooks activate.
        """
        registry = HookRegistry()
        hook = KnowledgeHook(
            hook_id="detect-task",
            name="Detect Task",
            phase=HookPhase.ON_CHANGE,
            priority=50,
            enabled=True,
            condition_query="ASK { ?s a <http://example.org/Task> }",
            action=HookAction.NOTIFY,
            handler_data={"message": "Task detected"},
        )
        registry.register(hook)

        engine = HybridEngine(hook_registry=registry)

        # Load data that does NOT match hook condition (Person, not Task)
        data = """
        @prefix ex: <http://example.org/> .
        ex:Alice a ex:Person .
        """
        engine.load_data(data)

        # Hook evaluated but condition not matched
        receipts = registry.get_receipts(hook_id="detect-task")
        assert len(receipts) >= 1
        assert receipts[0].condition_matched is False

    def test_notify_hook_records_notification_on_load(self) -> None:
        """NOTIFY hook records notification when condition matches.

        Verifies the audit/logging use case for hooks.
        """
        registry = HookRegistry()
        hook = KnowledgeHook(
            hook_id="audit-status",
            name="Audit Status Change",
            phase=HookPhase.ON_CHANGE,
            priority=50,
            enabled=True,
            condition_query="ASK { ?s <https://kgc.org/ns/status> ?status }",
            action=HookAction.NOTIFY,
            handler_data={"message": "Status change detected"},
        )
        registry.register(hook)

        engine = HybridEngine(hook_registry=registry)

        # Load workflow data with status
        data = """
        @prefix kgc: <https://kgc.org/ns/> .
        <urn:task:Start> kgc:status "Completed" .
        """
        engine.load_data(data)

        # Verify notification recorded
        receipts = registry.get_receipts(hook_id="audit-status")
        assert len(receipts) >= 1
        assert receipts[0].condition_matched is True
        assert receipts[0].action_taken == HookAction.NOTIFY

    def test_multiple_hooks_execute_in_priority_order(self) -> None:
        """Multiple hooks execute in priority order (highest first).

        Verifies deterministic execution ordering.
        """
        registry = HookRegistry()

        # Low priority hook
        hook_low = KnowledgeHook(
            hook_id="low-priority",
            name="Low Priority",
            phase=HookPhase.ON_CHANGE,
            priority=10,
            enabled=True,
            condition_query="",  # Always match
            action=HookAction.NOTIFY,
            handler_data={"message": "Low"},
        )
        registry.register(hook_low)

        # High priority hook
        hook_high = KnowledgeHook(
            hook_id="high-priority",
            name="High Priority",
            phase=HookPhase.ON_CHANGE,
            priority=100,
            enabled=True,
            condition_query="",  # Always match
            action=HookAction.NOTIFY,
            handler_data={"message": "High"},
        )
        registry.register(hook_high)

        engine = HybridEngine(hook_registry=registry)

        data = "@prefix ex: <http://example.org/> . ex:x ex:y ex:z ."
        engine.load_data(data)

        # Both hooks executed
        high_receipts = registry.get_receipts(hook_id="high-priority")
        low_receipts = registry.get_receipts(hook_id="low-priority")

        assert len(high_receipts) >= 1
        assert len(low_receipts) >= 1

        # High priority executed first (earlier timestamp)
        assert high_receipts[0].timestamp <= low_receipts[0].timestamp

    def test_disabled_hook_does_not_execute(self) -> None:
        """Disabled hooks are skipped during execution.

        Verifies enable/disable control.
        """
        registry = HookRegistry()
        hook = KnowledgeHook(
            hook_id="disabled-hook",
            name="Disabled Hook",
            phase=HookPhase.ON_CHANGE,
            priority=50,
            enabled=False,  # Disabled
            condition_query="",
            action=HookAction.NOTIFY,
            handler_data={"message": "Should not fire"},
        )
        registry.register(hook)

        engine = HybridEngine(hook_registry=registry)

        data = "@prefix ex: <http://example.org/> . ex:a ex:b ex:c ."
        engine.load_data(data)

        # No receipts for disabled hook
        receipts = registry.get_receipts(hook_id="disabled-hook")
        assert len(receipts) == 0

    def test_hook_executor_accessible_on_engine(self) -> None:
        """Hook executor is accessible for manual phase execution.

        Verifies the executor is stored and accessible for advanced use cases
        like PRE_TICK or POST_TICK phases that don't auto-fire on load.
        """
        registry = HookRegistry()
        engine = HybridEngine(hook_registry=registry)

        assert engine._hook_executor is not None
        assert engine._hook_registry is registry

    def test_engine_without_registry_has_no_executor(self) -> None:
        """Engine without registry has no executor (backward compatible).

        Verifies null object pattern - no executor when no registry.
        """
        engine = HybridEngine()

        assert engine._hook_executor is None
        assert engine._hook_registry is None


class TestHookRejection:
    """Tests for REJECT action and data validation."""

    def test_hook_reject_raises_value_error(self) -> None:
        """REJECT hook raises ValueError to prevent invalid data.

        Verifies reactive validation - invalid data is rejected immediately.
        """
        registry = HookRegistry()
        hook = KnowledgeHook(
            hook_id="validate-name-required",
            name="Validate Name Required",
            phase=HookPhase.ON_CHANGE,
            priority=100,
            enabled=True,
            # Condition: Person exists without name
            condition_query="""
                ASK {
                    ?s a <http://example.org/Person> .
                    FILTER NOT EXISTS { ?s <http://example.org/name> ?name }
                }
            """,
            action=HookAction.REJECT,
            handler_data={"reason": "Person must have a name"},
        )
        registry.register(hook)

        engine = HybridEngine(hook_registry=registry)

        # Try to load invalid data (Person without name)
        invalid_data = """
        @prefix ex: <http://example.org/> .
        ex:Anonymous a ex:Person .
        """

        with pytest.raises(ValueError, match="Person must have a name"):
            engine.load_data(invalid_data)

    def test_valid_data_passes_reject_hook(self) -> None:
        """Valid data passes REJECT hook validation.

        Verifies rejection only happens when condition matches.
        """
        registry = HookRegistry()
        hook = KnowledgeHook(
            hook_id="validate-name-required",
            name="Validate Name Required",
            phase=HookPhase.ON_CHANGE,
            priority=100,
            enabled=True,
            condition_query="""
                ASK {
                    ?s a <http://example.org/Person> .
                    FILTER NOT EXISTS { ?s <http://example.org/name> ?name }
                }
            """,
            action=HookAction.REJECT,
            handler_data={"reason": "Person must have a name"},
        )
        registry.register(hook)

        engine = HybridEngine(hook_registry=registry)

        # Load valid data (Person WITH name)
        valid_data = """
        @prefix ex: <http://example.org/> .
        ex:Alice a ex:Person ;
            ex:name "Alice" .
        """

        # Should not raise
        engine.load_data(valid_data)

        # Data was loaded
        assert len(list(engine.store)) > 0
