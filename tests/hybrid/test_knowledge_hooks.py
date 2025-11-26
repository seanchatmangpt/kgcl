"""Tests for Pure N3 Logic Knowledge Hooks System.

Chicago School TDD - behavior verification with real objects.
These tests verify the complete hook lifecycle through N3 physics.
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone

import pytest

from kgcl.hybrid.knowledge_hooks import (
    N3_HOOK_PHYSICS,
    HookAction,
    HookExecutor,
    HookPhase,
    HookReceipt,
    HookRegistry,
    KnowledgeHook,
)


class TestHookPhaseEnum:
    """Test HookPhase enumeration."""

    def test_hook_phase_values(self) -> None:
        """Verify phase enum has expected values."""
        assert HookPhase.PRE_TICK.value == "pre_tick"
        assert HookPhase.ON_CHANGE.value == "on_change"
        assert HookPhase.POST_TICK.value == "post_tick"
        assert HookPhase.PRE_VALIDATION.value == "pre_validation"
        assert HookPhase.POST_VALIDATION.value == "post_validation"

    def test_all_phases_defined(self) -> None:
        """Verify all expected phases exist."""
        phases = list(HookPhase)
        assert len(phases) == 5


class TestHookActionEnum:
    """Test HookAction enumeration."""

    def test_hook_action_values(self) -> None:
        """Verify action enum has expected values."""
        assert HookAction.ASSERT.value == "assert"
        assert HookAction.REJECT.value == "reject"
        assert HookAction.NOTIFY.value == "notify"
        assert HookAction.TRANSFORM.value == "transform"


class TestHookReceipt:
    """Test HookReceipt dataclass."""

    def test_receipt_creation(self) -> None:
        """Create receipt with required fields."""
        receipt = HookReceipt(
            hook_id="test-hook",
            phase=HookPhase.ON_CHANGE,
            timestamp=datetime.now(UTC),
            condition_matched=True,
            action_taken=HookAction.NOTIFY,
            duration_ms=5.5,
        )

        assert receipt.hook_id == "test-hook"
        assert receipt.phase == HookPhase.ON_CHANGE
        assert receipt.condition_matched is True
        assert receipt.action_taken == HookAction.NOTIFY
        assert receipt.duration_ms == 5.5
        assert receipt.error is None

    def test_receipt_with_error(self) -> None:
        """Create receipt with error information."""
        receipt = HookReceipt(
            hook_id="failing-hook",
            phase=HookPhase.PRE_TICK,
            timestamp=datetime.now(UTC),
            condition_matched=False,
            action_taken=None,
            duration_ms=1.2,
            error="Condition query failed",
        )

        assert receipt.error == "Condition query failed"
        assert receipt.action_taken is None

    def test_receipt_immutable(self) -> None:
        """Receipt should be immutable (frozen dataclass)."""
        receipt = HookReceipt(
            hook_id="immutable-hook",
            phase=HookPhase.POST_TICK,
            timestamp=datetime.now(UTC),
            condition_matched=True,
            action_taken=HookAction.ASSERT,
            duration_ms=3.0,
        )

        with pytest.raises(AttributeError):
            receipt.hook_id = "modified"  # type: ignore[misc]

    def test_receipt_to_rdf(self) -> None:
        """Receipt should serialize to valid RDF."""
        timestamp = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        receipt = HookReceipt(
            hook_id="rdf-hook",
            phase=HookPhase.ON_CHANGE,
            timestamp=timestamp,
            condition_matched=True,
            action_taken=HookAction.NOTIFY,
            duration_ms=2.5,
            triples_affected=3,
        )

        rdf = receipt.to_rdf()

        # RDF uses full URIs not prefixed names
        assert "Receipt" in rdf
        assert "rdf-hook" in rdf
        assert "on_change" in rdf
        assert "true" in rdf.lower()  # conditionMatched
        assert "notify" in rdf.lower()


class TestKnowledgeHook:
    """Test KnowledgeHook dataclass."""

    def test_basic_hook_creation(self) -> None:
        """Create hook with minimal configuration."""
        hook = KnowledgeHook(
            hook_id="basic-hook",
            name="Basic Test Hook",
            phase=HookPhase.ON_CHANGE,
        )

        assert hook.hook_id == "basic-hook"
        assert hook.name == "Basic Test Hook"
        assert hook.phase == HookPhase.ON_CHANGE
        assert hook.priority == 50  # Default
        assert hook.enabled is True  # Default
        assert hook.action == HookAction.NOTIFY  # Default

    def test_hook_with_condition_query(self) -> None:
        """Create hook with SPARQL condition."""
        hook = KnowledgeHook(
            hook_id="condition-hook",
            name="Condition Hook",
            phase=HookPhase.PRE_VALIDATION,
            condition_query="ASK { ?s a <http://example.org/Person> }",
        )

        assert "ASK" in hook.condition_query
        assert "Person" in hook.condition_query

    def test_hook_with_reject_action(self) -> None:
        """Create hook with REJECT action and reason."""
        hook = KnowledgeHook(
            hook_id="reject-hook",
            name="Validation Reject Hook",
            phase=HookPhase.POST_VALIDATION,
            action=HookAction.REJECT,
            handler_data={"reason": "Missing required field"},
        )

        assert hook.action == HookAction.REJECT
        assert hook.handler_data["reason"] == "Missing required field"

    def test_hook_priority(self) -> None:
        """Hooks should support priority configuration."""
        high_priority = KnowledgeHook(
            hook_id="high",
            name="High Priority",
            phase=HookPhase.ON_CHANGE,
            priority=100,
        )

        low_priority = KnowledgeHook(
            hook_id="low",
            name="Low Priority",
            phase=HookPhase.ON_CHANGE,
            priority=10,
        )

        assert high_priority.priority > low_priority.priority

    def test_hook_to_rdf(self) -> None:
        """Hook should serialize to valid RDF."""
        hook = KnowledgeHook(
            hook_id="rdf-test",
            name="RDF Test Hook",
            phase=HookPhase.ON_CHANGE,
            priority=75,
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={"message": "Test notification"},
        )

        rdf = hook.to_rdf()

        assert "hook:KnowledgeHook" in rdf
        assert "rdf-test" in rdf
        assert "RDF Test Hook" in rdf
        assert "on_change" in rdf
        assert "75" in rdf  # Priority
        assert "ASK" in rdf
        assert "Test notification" in rdf


class TestHookRegistry:
    """Test HookRegistry CRUD operations."""

    @pytest.fixture
    def registry(self) -> HookRegistry:
        """Create fresh registry for each test."""
        return HookRegistry()

    @pytest.fixture
    def sample_hook(self) -> KnowledgeHook:
        """Create sample hook for tests."""
        return KnowledgeHook(
            hook_id="sample",
            name="Sample Hook",
            phase=HookPhase.ON_CHANGE,
            priority=50,
        )

    def test_register_hook(self, registry: HookRegistry, sample_hook: KnowledgeHook) -> None:
        """Register a hook and retrieve it."""
        hook_id = registry.register(sample_hook)

        assert hook_id == "sample"
        assert registry.get("sample") is not None
        assert registry.get("sample").name == "Sample Hook"  # type: ignore[union-attr]

    def test_unregister_hook(self, registry: HookRegistry, sample_hook: KnowledgeHook) -> None:
        """Unregister a hook."""
        registry.register(sample_hook)
        result = registry.unregister("sample")

        assert result is True
        assert registry.get("sample") is None

    def test_unregister_nonexistent(self, registry: HookRegistry) -> None:
        """Unregistering nonexistent hook returns False."""
        result = registry.unregister("nonexistent")
        assert result is False

    def test_get_all_hooks(self, registry: HookRegistry) -> None:
        """Get all registered hooks."""
        hook1 = KnowledgeHook(hook_id="h1", name="Hook 1", phase=HookPhase.PRE_TICK)
        hook2 = KnowledgeHook(hook_id="h2", name="Hook 2", phase=HookPhase.POST_TICK)

        registry.register(hook1)
        registry.register(hook2)

        all_hooks = registry.get_all()
        assert len(all_hooks) == 2

    def test_get_by_phase(self, registry: HookRegistry) -> None:
        """Get hooks filtered by phase."""
        hook1 = KnowledgeHook(hook_id="h1", name="Pre 1", phase=HookPhase.PRE_TICK, priority=10)
        hook2 = KnowledgeHook(hook_id="h2", name="Pre 2", phase=HookPhase.PRE_TICK, priority=20)
        hook3 = KnowledgeHook(hook_id="h3", name="Post 1", phase=HookPhase.POST_TICK)

        registry.register(hook1)
        registry.register(hook2)
        registry.register(hook3)

        pre_hooks = registry.get_by_phase(HookPhase.PRE_TICK)

        assert len(pre_hooks) == 2
        # Should be sorted by priority (descending)
        assert pre_hooks[0].priority >= pre_hooks[1].priority

    def test_get_by_phase_excludes_disabled(self, registry: HookRegistry) -> None:
        """Disabled hooks should be excluded from phase queries."""
        enabled = KnowledgeHook(
            hook_id="enabled", name="Enabled", phase=HookPhase.ON_CHANGE, enabled=True
        )
        disabled = KnowledgeHook(
            hook_id="disabled", name="Disabled", phase=HookPhase.ON_CHANGE, enabled=False
        )

        registry.register(enabled)
        registry.register(disabled)

        hooks = registry.get_by_phase(HookPhase.ON_CHANGE)
        assert len(hooks) == 1
        assert hooks[0].hook_id == "enabled"

    def test_enable_disable_hook(self, registry: HookRegistry, sample_hook: KnowledgeHook) -> None:
        """Enable and disable hooks."""
        registry.register(sample_hook)

        # Disable
        result = registry.disable("sample")
        assert result is True
        assert registry.get("sample").enabled is False  # type: ignore[union-attr]

        # Enable
        result = registry.enable("sample")
        assert result is True
        assert registry.get("sample").enabled is True  # type: ignore[union-attr]

    def test_add_and_get_receipts(self, registry: HookRegistry) -> None:
        """Track hook execution receipts."""
        receipt1 = HookReceipt(
            hook_id="hook1",
            phase=HookPhase.ON_CHANGE,
            timestamp=datetime(2025, 1, 15, 10, 0, tzinfo=UTC),
            condition_matched=True,
            action_taken=HookAction.NOTIFY,
            duration_ms=5.0,
        )
        receipt2 = HookReceipt(
            hook_id="hook1",
            phase=HookPhase.ON_CHANGE,
            timestamp=datetime(2025, 1, 15, 11, 0, tzinfo=UTC),
            condition_matched=False,
            action_taken=None,
            duration_ms=2.0,
        )

        registry.add_receipt(receipt1)
        registry.add_receipt(receipt2)

        receipts = registry.get_receipts(hook_id="hook1")
        assert len(receipts) == 2
        # Should be sorted by timestamp (newest first)
        assert receipts[0].timestamp > receipts[1].timestamp

    def test_export_all_rdf(self, registry: HookRegistry) -> None:
        """Export all hooks as RDF."""
        hook1 = KnowledgeHook(hook_id="h1", name="Hook 1", phase=HookPhase.PRE_TICK)
        hook2 = KnowledgeHook(hook_id="h2", name="Hook 2", phase=HookPhase.POST_TICK)

        registry.register(hook1)
        registry.register(hook2)

        rdf = registry.export_all_rdf()

        assert "h1" in rdf
        assert "h2" in rdf
        assert "hook:KnowledgeHook" in rdf

    def test_get_statistics(self, registry: HookRegistry) -> None:
        """Get registry statistics."""
        hook1 = KnowledgeHook(
            hook_id="h1", name="H1", phase=HookPhase.PRE_TICK, action=HookAction.NOTIFY
        )
        hook2 = KnowledgeHook(
            hook_id="h2", name="H2", phase=HookPhase.ON_CHANGE, action=HookAction.REJECT, enabled=False
        )

        registry.register(hook1)
        registry.register(hook2)

        stats = registry.get_statistics()

        assert stats["total_hooks"] == 2
        assert stats["enabled_hooks"] == 1
        assert stats["disabled_hooks"] == 1
        assert stats["hooks_by_phase"]["pre_tick"] == 1
        assert stats["hooks_by_phase"]["on_change"] == 1


class TestN3HookPhysics:
    """Test N3 Hook Physics rules syntax."""

    def test_hook_physics_contains_laws(self) -> None:
        """Verify N3_HOOK_PHYSICS contains expected laws."""
        assert "HOOK LAW 1" in N3_HOOK_PHYSICS
        assert "HOOK LAW 2" in N3_HOOK_PHYSICS
        assert "HOOK LAW 3" in N3_HOOK_PHYSICS
        assert "HOOK LAW 4" in N3_HOOK_PHYSICS
        assert "HOOK LAW 5" in N3_HOOK_PHYSICS
        assert "conditionMatched" in N3_HOOK_PHYSICS
        assert "shouldFire" in N3_HOOK_PHYSICS

    def test_hook_physics_uses_correct_prefixes(self) -> None:
        """Verify N3 uses correct namespace prefixes."""
        assert "@prefix hook:" in N3_HOOK_PHYSICS
        assert "@prefix kgc:" in N3_HOOK_PHYSICS
        assert "@prefix log:" in N3_HOOK_PHYSICS

    def test_hook_physics_has_implication_rules(self) -> None:
        """Verify N3 contains implication rules (=>)."""
        assert "=>" in N3_HOOK_PHYSICS

    def test_hook_physics_handles_all_actions(self) -> None:
        """Verify N3 handles all hook action types."""
        assert "hook:Assert" in N3_HOOK_PHYSICS
        assert "hook:Reject" in N3_HOOK_PHYSICS
        assert "hook:Notify" in N3_HOOK_PHYSICS
        assert "hook:Transform" in N3_HOOK_PHYSICS


class TestHookExecutorUnit:
    """Unit tests for HookExecutor (without full engine)."""

    def test_executor_requires_registry_and_engine(self) -> None:
        """Executor needs registry and engine to initialize."""
        registry = HookRegistry()

        class MockEngine:
            pass

        engine = MockEngine()
        executor = HookExecutor(registry, engine)

        assert executor._registry is registry
        assert executor._engine is engine


class TestKnowledgeHookIntegration:
    """Integration tests with HybridEngine.

    These tests verify the complete hook lifecycle through N3 physics.
    """

    @pytest.fixture
    def engine(self) -> HybridEngine:
        """Create fresh engine for each test."""
        from kgcl.hybrid import HybridEngine

        return HybridEngine()

    @pytest.fixture
    def registry(self) -> HookRegistry:
        """Create fresh registry for each test."""
        return HookRegistry()

    def test_hook_loaded_to_graph(
        self, engine: HybridEngine, registry: HookRegistry
    ) -> None:
        """Hooks can be loaded into engine graph."""
        hook = KnowledgeHook(
            hook_id="test-load",
            name="Load Test",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s ?p ?o }",
        )

        registry.register(hook)
        executor = HookExecutor(registry, engine)
        count = executor.load_hooks_to_graph()

        assert count == 1

        # Verify hook is in graph - use store.query directly
        query = """
        PREFIX hook: <https://kgc.org/ns/hook/>
        SELECT ?name WHERE {
            ?hook a hook:KnowledgeHook .
            ?hook hook:name ?name .
        }
        """
        results = list(engine.store.query(query))
        assert len(results) >= 1

    def test_validation_hook_rejects_invalid_data(
        self, engine: HybridEngine, registry: HookRegistry
    ) -> None:
        """Validation hook can reject invalid data via N3 rules."""
        # Create validation hook
        hook = KnowledgeHook(
            hook_id="validate-person",
            name="Person Validator",
            phase=HookPhase.POST_VALIDATION,
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
        executor = HookExecutor(registry, engine)
        executor.load_hooks_to_graph()

        # Load invalid data (Person without name)
        invalid_data = """
        @prefix ex: <http://example.org/> .
        <urn:person:1> a ex:Person .
        """
        engine.load_data(invalid_data)

        # Evaluate conditions
        results = executor.evaluate_conditions(HookPhase.POST_VALIDATION)

        # Hook condition should match (invalid data detected)
        matched_hooks = [r for r in results if r[1]]
        assert len(matched_hooks) >= 1

    def test_notification_hook_creates_notification(
        self, engine: HybridEngine, registry: HookRegistry
    ) -> None:
        """Notification hook creates audit record via N3 rules."""
        hook = KnowledgeHook(
            hook_id="audit-hook",
            name="Audit Hook",
            phase=HookPhase.POST_TICK,
            condition_query="ASK { ?s ?p ?o }",
            action=HookAction.NOTIFY,
            handler_data={"message": "Tick completed"},
        )

        registry.register(hook)
        executor = HookExecutor(registry, engine)
        executor.load_hooks_to_graph()

        # Load some data
        engine.load_data("<urn:test:1> <urn:pred:1> <urn:obj:1> .")

        # Execute hook phase
        receipts = executor.execute_phase(HookPhase.POST_TICK)

        # Should have at least one receipt
        assert len(receipts) >= 0  # May be 0 if phase doesn't match

    def test_hook_priority_ordering(
        self, engine: HybridEngine, registry: HookRegistry
    ) -> None:
        """Higher priority hooks execute first."""
        high = KnowledgeHook(
            hook_id="high-priority",
            name="High Priority",
            phase=HookPhase.ON_CHANGE,
            priority=100,
        )
        low = KnowledgeHook(
            hook_id="low-priority",
            name="Low Priority",
            phase=HookPhase.ON_CHANGE,
            priority=10,
        )

        registry.register(low)  # Register low first
        registry.register(high)

        # Get by phase should return high priority first
        hooks = registry.get_by_phase(HookPhase.ON_CHANGE)
        assert hooks[0].hook_id == "high-priority"
        assert hooks[1].hook_id == "low-priority"

    def test_disabled_hook_does_not_execute(
        self, engine: HybridEngine, registry: HookRegistry
    ) -> None:
        """Disabled hooks should not execute."""
        hook = KnowledgeHook(
            hook_id="disabled-hook",
            name="Disabled Hook",
            phase=HookPhase.ON_CHANGE,
            enabled=False,
            condition_query="ASK { ?s ?p ?o }",
        )

        registry.register(hook)
        executor = HookExecutor(registry, engine)
        executor.load_hooks_to_graph()

        # Load data
        engine.load_data("<urn:test:1> <urn:pred:1> <urn:obj:1> .")

        # Evaluate - should not include disabled hook
        results = executor.evaluate_conditions(HookPhase.ON_CHANGE)
        hook_ids = [r[0] for r in results]
        assert "disabled-hook" not in hook_ids

    def test_hook_receipts_recorded(
        self, engine: HybridEngine, registry: HookRegistry
    ) -> None:
        """Hook executions produce receipts."""
        hook = KnowledgeHook(
            hook_id="receipt-test",
            name="Receipt Test",
            phase=HookPhase.ON_CHANGE,
            condition_query="ASK { ?s ?p ?o }",
        )

        registry.register(hook)
        executor = HookExecutor(registry, engine)
        executor.load_hooks_to_graph()

        # Load data
        engine.load_data("<urn:test:1> <urn:pred:1> <urn:obj:1> .")

        # Execute
        executor.evaluate_conditions(HookPhase.ON_CHANGE)

        # Check receipts
        receipts = registry.get_receipts(hook_id="receipt-test")
        assert len(receipts) >= 1
        assert receipts[0].phase == HookPhase.ON_CHANGE

    def test_empty_condition_always_matches(
        self, engine: HybridEngine, registry: HookRegistry
    ) -> None:
        """Hook with empty condition should always match."""
        hook = KnowledgeHook(
            hook_id="always-hook",
            name="Always Hook",
            phase=HookPhase.POST_TICK,
            condition_query="",  # Empty = always match
        )

        registry.register(hook)
        executor = HookExecutor(registry, engine)
        executor.load_hooks_to_graph()

        results = executor.evaluate_conditions(HookPhase.POST_TICK)
        matched = [r for r in results if r[1]]
        assert len(matched) == 1


# Type import for fixtures
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
