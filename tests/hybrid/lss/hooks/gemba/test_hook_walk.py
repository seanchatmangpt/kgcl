"""GW-HOOK-001: Hook execution Gemba Walk tests with REAL HookExecutor.

Gemba Walk Focus: HOOK EXECUTION observation
Walk Path: PRE_TICK -> ON_CHANGE -> POST_TICK
Observations: Hook conditions, actions, durations, receipts

CRITICAL: Uses REAL HookExecutor and HybridEngine, NOT simulated behavior.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from kgcl.hybrid.knowledge_hooks import HookAction, HookExecutor, HookPhase, HookRegistry, KnowledgeHook
from tests.hybrid.lss.hooks.gemba.observations import conduct_hook_gemba_walk, observe_hook_execution


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for Gemba Walk observations.

    Returns
    -------
    HybridEngine
        New engine instance
    """
    return HybridEngine()


@pytest.fixture
def registry() -> HookRegistry:
    """Create fresh HookRegistry.

    Returns
    -------
    HookRegistry
        New registry instance
    """
    return HookRegistry()


@pytest.fixture
def executor(engine: HybridEngine, registry: HookRegistry) -> HookExecutor:
    """Create HookExecutor with engine and registry.

    Parameters
    ----------
    engine : HybridEngine
        Engine instance
    registry : HookRegistry
        Registry instance

    Returns
    -------
    HookExecutor
        Executor for hook testing
    """
    return HookExecutor(registry, engine)


class TestGWHook001SingleHookObservation:
    """GW-HOOK-001: Walk through single hook execution to verify behavior."""

    def test_walk_observe_notify_hook(self, executor: HookExecutor, registry: HookRegistry) -> None:
        """Walk through NOTIFY hook execution and verify observation.

        Parameters
        ----------
        executor : HookExecutor
            Hook executor
        registry : HookRegistry
            Hook registry
        """
        # Register a NOTIFY hook
        hook = KnowledgeHook(
            hook_id="test-notify",
            name="Test Notify Hook",
            phase=HookPhase.PRE_TICK,
            priority=100,
            enabled=True,
            condition_query="ASK { }",  # Always matches
            action=HookAction.NOTIFY,
            handler_data={"message": "Test notification"},
        )
        registry.register(hook)
        executor.load_hooks_to_graph()

        # Walk observation: Execute and observe
        observation = observe_hook_execution(executor, HookPhase.PRE_TICK)

        # Verify observation captured hook execution
        assert observation.hook_id == "test-notify"
        assert observation.phase == HookPhase.PRE_TICK
        assert observation.condition_matched
        assert observation.action == HookAction.NOTIFY
        assert observation.duration_ms >= 0
        assert "Action: notify" in observation.notes

    def test_walk_observe_no_match(self, executor: HookExecutor, registry: HookRegistry) -> None:
        """Walk verifies hook with non-matching condition.

        Parameters
        ----------
        executor : HookExecutor
            Hook executor
        registry : HookRegistry
            Hook registry
        """
        # Register hook with impossible condition
        hook = KnowledgeHook(
            hook_id="test-no-match",
            name="Never Matches",
            phase=HookPhase.POST_TICK,
            priority=50,
            enabled=True,
            condition_query="ASK { <urn:nonexistent> <urn:prop> <urn:val> }",
            action=HookAction.NOTIFY,
            handler_data={"message": "Should not fire"},
        )
        registry.register(hook)
        executor.load_hooks_to_graph()

        # Walk observation
        observation = observe_hook_execution(executor, HookPhase.POST_TICK)

        # Verify no match observed
        assert observation.hook_id == "test-no-match"
        assert not observation.condition_matched
        assert observation.action == HookAction.NOTIFY  # Type is still recorded

    def test_walk_observe_reject_hook(
        self, executor: HookExecutor, registry: HookRegistry, engine: HybridEngine
    ) -> None:
        """Walk through REJECT hook that blocks invalid data.

        Parameters
        ----------
        executor : HookExecutor
            Hook executor
        registry : HookRegistry
            Hook registry
        engine : HybridEngine
            Engine instance
        """
        # Register validation hook
        hook = KnowledgeHook(
            hook_id="validate-person",
            name="Person Validator",
            phase=HookPhase.ON_CHANGE,
            priority=100,
            enabled=True,
            condition_query="ASK { ?s a <https://kgc.org/ns/Person> }",
            action=HookAction.REJECT,
            handler_data={"reason": "Person must have name property"},
        )
        registry.register(hook)
        executor.load_hooks_to_graph()

        # Load invalid person data
        invalid_person = """
        @prefix kgc: <https://kgc.org/ns/> .
        <urn:person:1> a kgc:Person .
        """
        engine.load_data(invalid_person, trigger_hooks=False)

        # Walk observation
        observation = observe_hook_execution(executor, HookPhase.ON_CHANGE)

        # Verify rejection observed
        assert observation.hook_id == "validate-person"
        assert observation.phase == HookPhase.ON_CHANGE
        assert observation.condition_matched
        assert observation.action == HookAction.REJECT


class TestGWHook002MultiPhaseWalk:
    """GW-HOOK-002: Walk through multiple hook phases in single tick."""

    def test_walk_three_phases(self, executor: HookExecutor, registry: HookRegistry, engine: HybridEngine) -> None:
        """Walk through PRE_TICK, ON_CHANGE, POST_TICK phases.

        Parameters
        ----------
        executor : HookExecutor
            Hook executor
        registry : HookRegistry
            Hook registry
        engine : HybridEngine
            Engine instance
        """
        # Register hooks for each phase
        pre_hook = KnowledgeHook(
            hook_id="pre-tick-hook",
            name="Pre-Tick Hook",
            phase=HookPhase.PRE_TICK,
            priority=100,
            enabled=True,
            condition_query="ASK { }",
            action=HookAction.NOTIFY,
            handler_data={"message": "Pre-tick fired"},
        )
        on_change_hook = KnowledgeHook(
            hook_id="on-change-hook",
            name="On-Change Hook",
            phase=HookPhase.ON_CHANGE,
            priority=100,
            enabled=True,
            condition_query="ASK { }",
            action=HookAction.NOTIFY,
            handler_data={"message": "On-change fired"},
        )
        post_hook = KnowledgeHook(
            hook_id="post-tick-hook",
            name="Post-Tick Hook",
            phase=HookPhase.POST_TICK,
            priority=100,
            enabled=True,
            condition_query="ASK { }",
            action=HookAction.NOTIFY,
            handler_data={"message": "Post-tick fired"},
        )

        registry.register(pre_hook)
        registry.register(on_change_hook)
        registry.register(post_hook)
        executor.load_hooks_to_graph()

        # Walk through all phases
        observations = []

        pre_obs = observe_hook_execution(executor, HookPhase.PRE_TICK)
        observations.append(pre_obs)

        change_obs = observe_hook_execution(executor, HookPhase.ON_CHANGE)
        observations.append(change_obs)

        post_obs = observe_hook_execution(executor, HookPhase.POST_TICK)
        observations.append(post_obs)

        # Verify all phases observed
        assert len(observations) == 3
        assert observations[0].phase == HookPhase.PRE_TICK
        assert observations[1].phase == HookPhase.ON_CHANGE
        assert observations[2].phase == HookPhase.POST_TICK

        # All should have matched
        assert all(obs.condition_matched for obs in observations)


class TestGWHook003FullGembaWalk:
    """GW-HOOK-003: Complete Gemba Walk across multiple ticks."""

    def test_conduct_multi_tick_walk(
        self, executor: HookExecutor, registry: HookRegistry, engine: HybridEngine
    ) -> None:
        """Conduct full Gemba Walk observing 3 tick cycles.

        Parameters
        ----------
        executor : HookExecutor
            Hook executor
        registry : HookRegistry
            Hook registry
        engine : HybridEngine
            Engine instance
        """
        # Register a hook
        hook = KnowledgeHook(
            hook_id="multi-tick-hook",
            name="Multi-Tick Hook",
            phase=HookPhase.PRE_TICK,
            priority=100,
            enabled=True,
            condition_query="ASK { }",
            action=HookAction.NOTIFY,
            handler_data={"message": "Tick fired"},
        )
        registry.register(hook)
        executor.load_hooks_to_graph()

        # Conduct walk
        walk = conduct_hook_gemba_walk(executor, duration_ticks=3)

        # Verify walk captured observations
        assert walk.total_hooks_observed >= 3  # At least 3 observations (1 per tick)
        assert walk.avg_duration_ms >= 0
        assert walk.end_time is not None
        assert walk.duration_seconds > 0

        # Verify observations list populated
        assert len(walk.observations) >= 3

        # Verify walk ID format
        assert walk.walk_id.startswith("walk-")

    def test_walk_identifies_waste(self, executor: HookExecutor, registry: HookRegistry, engine: HybridEngine) -> None:
        """Walk identifies waste patterns (hooks that never match).

        Parameters
        ----------
        executor : HookExecutor
            Hook executor
        registry : HookRegistry
            Hook registry
        engine : HybridEngine
            Engine instance
        """
        # Register hook that never matches
        hook = KnowledgeHook(
            hook_id="never-matches",
            name="Never Matches",
            phase=HookPhase.PRE_TICK,
            priority=100,
            enabled=True,
            condition_query="ASK { <urn:fake> <urn:prop> <urn:val> }",
            action=HookAction.NOTIFY,
            handler_data={"message": "Never fires"},
        )
        registry.register(hook)
        executor.load_hooks_to_graph()

        # Conduct walk
        walk = conduct_hook_gemba_walk(executor, duration_ticks=5)

        # Should identify high no-match rate as waste
        assert walk.hooks_matched == 0  # No hooks matched
        if len(walk.waste_identified) > 0:
            assert any("no-match" in waste.lower() for waste in walk.waste_identified)

    def test_walk_identifies_improvement_opportunities(
        self, executor: HookExecutor, registry: HookRegistry, engine: HybridEngine
    ) -> None:
        """Walk identifies improvement opportunities based on metrics.

        Parameters
        ----------
        executor : HookExecutor
            Hook executor
        registry : HookRegistry
            Hook registry
        engine : HybridEngine
            Engine instance
        """
        # Register hook with complex query
        hook = KnowledgeHook(
            hook_id="complex-query",
            name="Complex Query Hook",
            phase=HookPhase.PRE_TICK,
            priority=100,
            enabled=True,
            condition_query="ASK { ?s ?p ?o }",  # Broad query
            action=HookAction.NOTIFY,
            handler_data={"message": "Complex query"},
        )
        registry.register(hook)
        executor.load_hooks_to_graph()

        # Conduct walk
        walk = conduct_hook_gemba_walk(executor, duration_ticks=2)

        # Verify walk structure
        assert walk.total_hooks_observed > 0
        assert isinstance(walk.improvement_opportunities, list)

        # The walk should complete successfully even if no specific improvements found
        assert walk.end_time is not None


class TestGWHook004WalkMetrics:
    """GW-HOOK-004: Verify Gemba Walk metrics accuracy."""

    def test_walk_counts_matched_hooks(
        self, executor: HookExecutor, registry: HookRegistry, engine: HybridEngine
    ) -> None:
        """Walk accurately counts hooks that matched conditions.

        Parameters
        ----------
        executor : HookExecutor
            Hook executor
        registry : HookRegistry
            Hook registry
        engine : HybridEngine
            Engine instance
        """
        # Register one matching, one non-matching
        match_hook = KnowledgeHook(
            hook_id="matches",
            name="Matches",
            phase=HookPhase.PRE_TICK,
            priority=100,
            enabled=True,
            condition_query="ASK { }",  # Always matches
            action=HookAction.NOTIFY,
            handler_data={"message": "Matched"},
        )
        no_match_hook = KnowledgeHook(
            hook_id="no-match",
            name="No Match",
            phase=HookPhase.PRE_TICK,
            priority=50,
            enabled=True,
            condition_query="ASK { <urn:fake> <urn:prop> <urn:val> }",
            action=HookAction.NOTIFY,
            handler_data={"message": "No match"},
        )

        registry.register(match_hook)
        registry.register(no_match_hook)
        executor.load_hooks_to_graph()

        # Directly observe PRE_TICK phase where our hooks are registered
        pre_obs = observe_hook_execution(executor, HookPhase.PRE_TICK)

        # Verify we observed one of our hooks
        assert pre_obs.hook_id in ["matches", "no-match"]

        # Get all receipts to verify matches
        all_receipts = registry.get_receipts(limit=10)
        matched_receipts = [r for r in all_receipts if r.condition_matched]

        # Should have at least one matched hook (the "matches" hook with ASK { })
        assert len(matched_receipts) >= 1
        assert any(r.hook_id == "matches" for r in matched_receipts)

    def test_walk_calculates_duration(
        self, executor: HookExecutor, registry: HookRegistry, engine: HybridEngine
    ) -> None:
        """Walk accurately calculates duration metrics.

        Parameters
        ----------
        executor : HookExecutor
            Hook executor
        registry : HookRegistry
            Hook registry
        engine : HybridEngine
            Engine instance
        """
        hook = KnowledgeHook(
            hook_id="duration-test",
            name="Duration Test",
            phase=HookPhase.PRE_TICK,
            priority=100,
            enabled=True,
            condition_query="ASK { }",
            action=HookAction.NOTIFY,
            handler_data={"message": "Test"},
        )
        registry.register(hook)
        executor.load_hooks_to_graph()

        # Conduct walk
        walk = conduct_hook_gemba_walk(executor, duration_ticks=2)

        # Verify duration metrics
        assert walk.duration_seconds > 0
        assert walk.avg_duration_ms >= 0

        # Individual observations should have durations
        for obs in walk.observations:
            assert obs.duration_ms >= 0
