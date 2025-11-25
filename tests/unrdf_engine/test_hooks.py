"""Tests for UNRDF hooks system."""

from __future__ import annotations

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from kgcl.unrdf_engine.hooks import (
    FeatureTemplateHook,
    HookContext,
    HookExecutor,
    HookPhase,
    HookRegistry,
    KnowledgeHook,
    TriggerCondition,
    ValidationFailureHook,
)


class TestHookPhase:
    """Test HookPhase enum."""

    def test_phases(self) -> None:
        """Test hook phases exist."""
        assert HookPhase.PRE_INGESTION.value == "pre_ingestion"
        assert HookPhase.ON_CHANGE.value == "on_change"
        assert HookPhase.POST_COMMIT.value == "post_commit"
        assert HookPhase.PRE_VALIDATION.value == "pre_validation"
        assert HookPhase.POST_VALIDATION.value == "post_validation"


class TestTriggerCondition:
    """Test TriggerCondition class."""

    def test_creation(self) -> None:
        """Test creating trigger condition."""
        trigger = TriggerCondition(pattern="?s ?p ?o", check_delta=True, min_matches=1)

        assert trigger.pattern == "?s ?p ?o"
        assert trigger.check_delta
        assert trigger.min_matches == 1

    def test_matches_delta(self) -> None:
        """Test matching against delta graph."""
        delta = Graph()
        delta.add(
            (
                URIRef("http://example.org/s"),
                RDF.type,
                URIRef("http://unrdf.org/ontology/FeatureTemplate"),
            )
        )

        trigger = TriggerCondition(
            pattern="?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://unrdf.org/ontology/FeatureTemplate>",
            check_delta=True,
            min_matches=1,
        )

        context = HookContext(
            phase=HookPhase.POST_COMMIT, graph=Graph(), delta=delta, transaction_id="txn-1"
        )

        assert trigger.matches(context)

    def test_no_matches(self) -> None:
        """Test condition when no matches."""
        delta = Graph()

        trigger = TriggerCondition(
            pattern="?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://example.org/NoSuchType>",
            check_delta=True,
            min_matches=1,
        )

        context = HookContext(
            phase=HookPhase.POST_COMMIT, graph=Graph(), delta=delta, transaction_id="txn-1"
        )

        assert not trigger.matches(context)


class SimpleHook(KnowledgeHook):
    """Simple hook for testing."""

    def __init__(self) -> None:
        """Initialize hook."""
        super().__init__(name="simple_hook", phases=[HookPhase.POST_COMMIT])
        self.executed = False

    def execute(self, context: HookContext) -> None:
        """Execute hook."""
        self.executed = True


class ConditionalHook(KnowledgeHook):
    """Hook with trigger condition."""

    def __init__(self) -> None:
        """Initialize hook."""
        super().__init__(
            name="conditional_hook",
            phases=[HookPhase.POST_COMMIT],
            trigger=TriggerCondition(pattern="?s ?p ?o", min_matches=1),
        )
        self.executed = False

    def execute(self, context: HookContext) -> None:
        """Execute hook."""
        self.executed = True


class TestKnowledgeHook:
    """Test KnowledgeHook base class."""

    def test_creation(self) -> None:
        """Test creating hook."""
        hook = SimpleHook()

        assert hook.name == "simple_hook"
        assert HookPhase.POST_COMMIT in hook.phases
        assert hook.enabled

    def test_should_execute_when_enabled(self) -> None:
        """Test should_execute returns true when conditions met."""
        hook = SimpleHook()

        context = HookContext(
            phase=HookPhase.POST_COMMIT, graph=Graph(), delta=Graph(), transaction_id="txn-1"
        )

        assert hook.should_execute(context)

    def test_should_not_execute_when_disabled(self) -> None:
        """Test should_execute returns false when disabled."""
        hook = SimpleHook()
        hook.enabled = False

        context = HookContext(
            phase=HookPhase.POST_COMMIT, graph=Graph(), delta=Graph(), transaction_id="txn-1"
        )

        assert not hook.should_execute(context)

    def test_should_not_execute_wrong_phase(self) -> None:
        """Test should_execute returns false for wrong phase."""
        hook = SimpleHook()

        context = HookContext(
            phase=HookPhase.PRE_INGESTION, graph=Graph(), delta=Graph(), transaction_id="txn-1"
        )

        assert not hook.should_execute(context)

    def test_should_not_execute_trigger_not_met(self) -> None:
        """Test should_execute returns false when trigger not met."""
        hook = ConditionalHook()

        context = HookContext(
            phase=HookPhase.POST_COMMIT,
            graph=Graph(),
            delta=Graph(),  # Empty delta
            transaction_id="txn-1",
        )

        assert not hook.should_execute(context)


class TestHookRegistry:
    """Test HookRegistry class."""

    def test_initialization(self) -> None:
        """Test registry initialization."""
        registry = HookRegistry()

        assert len(registry.list_all()) == 0

    def test_register_hook(self) -> None:
        """Test registering hook."""
        registry = HookRegistry()
        hook = SimpleHook()

        registry.register(hook)

        assert len(registry.list_all()) == 1
        assert registry.get("simple_hook") == hook

    def test_register_duplicate_fails(self) -> None:
        """Test registering duplicate hook fails."""
        registry = HookRegistry()
        hook1 = SimpleHook()
        hook2 = SimpleHook()

        registry.register(hook1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(hook2)

    def test_unregister_hook(self) -> None:
        """Test unregistering hook."""
        registry = HookRegistry()
        hook = SimpleHook()

        registry.register(hook)
        assert len(registry.list_all()) == 1

        registry.unregister("simple_hook")
        assert len(registry.list_all()) == 0

    def test_unregister_nonexistent_fails(self) -> None:
        """Test unregistering nonexistent hook fails."""
        registry = HookRegistry()

        with pytest.raises(ValueError, match="not found"):
            registry.unregister("nonexistent")

    def test_get_for_phase(self) -> None:
        """Test getting hooks for phase."""
        registry = HookRegistry()
        hook1 = SimpleHook()

        class PreIngestionHook(KnowledgeHook):
            def __init__(self) -> None:
                super().__init__(name="pre_hook", phases=[HookPhase.PRE_INGESTION])

            def execute(self, context: HookContext) -> None:
                pass

        hook2 = PreIngestionHook()

        registry.register(hook1)
        registry.register(hook2)

        post_commit_hooks = registry.get_for_phase(HookPhase.POST_COMMIT)
        assert len(post_commit_hooks) == 1
        assert post_commit_hooks[0] == hook1

        pre_ingestion_hooks = registry.get_for_phase(HookPhase.PRE_INGESTION)
        assert len(pre_ingestion_hooks) == 1
        assert pre_ingestion_hooks[0] == hook2

    def test_priority_ordering(self) -> None:
        """Test hooks ordered by priority."""
        registry = HookRegistry()

        class HighPriorityHook(KnowledgeHook):
            def __init__(self) -> None:
                super().__init__(name="high_priority", phases=[HookPhase.POST_COMMIT], priority=100)

            def execute(self, context: HookContext) -> None:
                pass

        class LowPriorityHook(KnowledgeHook):
            def __init__(self) -> None:
                super().__init__(name="low_priority", phases=[HookPhase.POST_COMMIT], priority=10)

            def execute(self, context: HookContext) -> None:
                pass

        high = HighPriorityHook()
        low = LowPriorityHook()

        registry.register(low)
        registry.register(high)

        hooks = registry.get_for_phase(HookPhase.POST_COMMIT)
        assert hooks[0] == high  # Higher priority first
        assert hooks[1] == low


class TestHookExecutor:
    """Test HookExecutor class."""

    def test_initialization(self) -> None:
        """Test executor initialization."""
        registry = HookRegistry()
        executor = HookExecutor(registry)

        assert executor.registry == registry

    def test_execute_phase(self) -> None:
        """Test executing hooks for a phase."""
        registry = HookRegistry()
        executor = HookExecutor(registry)

        hook = SimpleHook()
        registry.register(hook)

        context = HookContext(
            phase=HookPhase.POST_COMMIT, graph=Graph(), delta=Graph(), transaction_id="txn-1"
        )

        results = executor.execute_phase(HookPhase.POST_COMMIT, context)

        assert len(results) == 1
        assert results[0]["success"]
        assert results[0]["executed"]
        assert hook.executed

    def test_execute_phase_no_hooks(self) -> None:
        """Test executing phase with no hooks."""
        registry = HookRegistry()
        executor = HookExecutor(registry)

        context = HookContext(
            phase=HookPhase.POST_COMMIT, graph=Graph(), delta=Graph(), transaction_id="txn-1"
        )

        results = executor.execute_phase(HookPhase.POST_COMMIT, context)

        assert len(results) == 0

    def test_execute_phase_skips_disabled(self) -> None:
        """Test that disabled hooks are skipped."""
        registry = HookRegistry()
        executor = HookExecutor(registry)

        hook = SimpleHook()
        hook.enabled = False
        registry.register(hook)

        context = HookContext(
            phase=HookPhase.POST_COMMIT, graph=Graph(), delta=Graph(), transaction_id="txn-1"
        )

        results = executor.execute_phase(HookPhase.POST_COMMIT, context)

        assert len(results) == 1
        assert not results[0]["executed"]
        assert not hook.executed

    def test_execute_phase_handles_errors(self) -> None:
        """Test that executor handles hook errors."""

        class ErrorHook(KnowledgeHook):
            def __init__(self) -> None:
                super().__init__(name="error_hook", phases=[HookPhase.POST_COMMIT])

            def execute(self, context: HookContext) -> None:
                msg = "Hook error"
                raise RuntimeError(msg)

        registry = HookRegistry()
        executor = HookExecutor(registry)

        hook = ErrorHook()
        registry.register(hook)

        context = HookContext(
            phase=HookPhase.POST_COMMIT, graph=Graph(), delta=Graph(), transaction_id="txn-1"
        )

        results = executor.execute_phase(HookPhase.POST_COMMIT, context)

        assert len(results) == 1
        assert not results[0]["success"]
        assert results[0]["error"] == "Hook error"

    def test_fail_fast(self) -> None:
        """Test fail-fast behavior."""

        class ErrorHook(KnowledgeHook):
            def __init__(self) -> None:
                super().__init__(name="error_hook", phases=[HookPhase.POST_COMMIT], priority=100)

            def execute(self, context: HookContext) -> None:
                msg = "Hook error"
                raise RuntimeError(msg)

        registry = HookRegistry()
        executor = HookExecutor(registry)

        error_hook = ErrorHook()
        success_hook = SimpleHook()

        registry.register(error_hook)
        registry.register(success_hook)

        context = HookContext(
            phase=HookPhase.POST_COMMIT, graph=Graph(), delta=Graph(), transaction_id="txn-1"
        )

        results = executor.execute_phase(HookPhase.POST_COMMIT, context, fail_fast=True)

        # Should stop after error hook
        assert len(results) == 1
        assert not results[0]["success"]
        assert not success_hook.executed

    def test_execution_history(self) -> None:
        """Test execution history tracking."""
        registry = HookRegistry()
        executor = HookExecutor(registry)

        hook = SimpleHook()
        registry.register(hook)

        context = HookContext(
            phase=HookPhase.POST_COMMIT, graph=Graph(), delta=Graph(), transaction_id="txn-1"
        )

        executor.execute_phase(HookPhase.POST_COMMIT, context)

        history = executor.get_execution_history()
        assert len(history) == 1
        assert history[0]["hook"] == "simple_hook"

    def test_clear_history(self) -> None:
        """Test clearing execution history."""
        registry = HookRegistry()
        executor = HookExecutor(registry)

        hook = SimpleHook()
        registry.register(hook)

        context = HookContext(
            phase=HookPhase.POST_COMMIT, graph=Graph(), delta=Graph(), transaction_id="txn-1"
        )

        executor.execute_phase(HookPhase.POST_COMMIT, context)
        assert len(executor.get_execution_history()) == 1

        executor.clear_history()
        assert len(executor.get_execution_history()) == 0


class TestValidationFailureHook:
    """Test ValidationFailureHook."""

    def test_rollback_on_failure(self) -> None:
        """Test that hook signals rollback on validation failure."""
        hook = ValidationFailureHook(rollback_on_failure=True)

        context = HookContext(
            phase=HookPhase.POST_VALIDATION,
            graph=Graph(),
            delta=Graph(),
            transaction_id="txn-1",
            metadata={"validation_report": {"conforms": False}},
        )

        hook.execute(context)

        assert context.metadata["should_rollback"]
        assert "rollback_reason" in context.metadata

    def test_no_rollback_when_valid(self) -> None:
        """Test that hook doesn't rollback when validation passes."""
        hook = ValidationFailureHook(rollback_on_failure=True)

        context = HookContext(
            phase=HookPhase.POST_VALIDATION,
            graph=Graph(),
            delta=Graph(),
            transaction_id="txn-1",
            metadata={"validation_report": {"conforms": True}},
        )

        hook.execute(context)

        assert "should_rollback" not in context.metadata


class TestFeatureTemplateHook:
    """Test FeatureTemplateHook."""

    def test_creation(self) -> None:
        """Test creating feature template hook."""
        hook = FeatureTemplateHook()

        assert hook.name == "feature_template_materializer"
        assert HookPhase.POST_COMMIT in hook.phases
        assert hook.trigger is not None

    def test_materializer_called(self) -> None:
        """Test that materializer is called."""
        called = False

        def materializer(context: HookContext) -> None:
            nonlocal called
            called = True

        hook = FeatureTemplateHook(materializer=materializer)

        context = HookContext(
            phase=HookPhase.POST_COMMIT, graph=Graph(), delta=Graph(), transaction_id="txn-1"
        )

        hook.execute(context)

        assert called
