"""Pytest fixtures for Knowledge Hooks LSS testing.

This module provides comprehensive test fixtures for validating Knowledge Hooks
following Lean Six Sigma methodology. Fixtures generate sample hooks, receipts,
and configured engines for integration testing across all LSS dimensions.

Fixtures
--------
sample_hook_registry
    HookRegistry with 5 sample hooks across all phases
sample_hook_receipts
    List of 20 HookReceipt objects with varied durations for SPC analysis
hybrid_engine_with_hooks
    HybridEngine instance pre-configured with hooks loaded
hook_executor
    HookExecutor ready for testing with registry and engine
sample_execution_data
    Dictionary of execution metrics for LSS analysis
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from kgcl.hybrid.knowledge_hooks import HookAction, HookExecutor, HookPhase, HookReceipt, HookRegistry, KnowledgeHook

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def sample_hook_registry() -> HookRegistry:
    """Create HookRegistry with 5 sample hooks across all phases.

    Returns
    -------
    HookRegistry
        Registry with hooks for PRE_TICK, ON_CHANGE, POST_TICK, PRE_VALIDATION,
        and POST_VALIDATION phases.

    Examples
    --------
    >>> def test_hook_phases(sample_hook_registry):
    ...     assert len(sample_hook_registry.get_all()) == 5
    ...     pre_tick = sample_hook_registry.get_by_phase(HookPhase.PRE_TICK)
    ...     assert len(pre_tick) >= 1
    """
    registry = HookRegistry()

    # Hook 1: PRE_TICK validation (highest priority)
    hook1 = KnowledgeHook(
        hook_id="pre-tick-validation",
        name="Pre-Tick State Validation",
        phase=HookPhase.PRE_TICK,
        priority=100,
        condition_query="""
            PREFIX kgc: <https://kgc.org/ns/>
            ASK { ?s a kgc:InvalidState }
        """,
        action=HookAction.REJECT,
        handler_data={"reason": "Invalid state detected before tick"},
    )
    registry.register(hook1)

    # Hook 2: ON_CHANGE entity validation
    hook2 = KnowledgeHook(
        hook_id="on-change-entity",
        name="Entity Change Validation",
        phase=HookPhase.ON_CHANGE,
        priority=80,
        condition_query="""
            PREFIX kgc: <https://kgc.org/ns/>
            ASK {
                ?s a kgc:Person .
                FILTER NOT EXISTS { ?s kgc:name ?name }
            }
        """,
        action=HookAction.REJECT,
        handler_data={"reason": "Person entity must have name property"},
    )
    registry.register(hook2)

    # Hook 3: POST_TICK notification
    hook3 = KnowledgeHook(
        hook_id="post-tick-notify",
        name="Post-Tick Completion Notification",
        phase=HookPhase.POST_TICK,
        priority=50,
        condition_query="",  # Always fires
        action=HookAction.NOTIFY,
        handler_data={"message": "Tick completed successfully"},
    )
    registry.register(hook3)

    # Hook 4: PRE_VALIDATION constraint check
    hook4 = KnowledgeHook(
        hook_id="pre-validation-constraint",
        name="Pre-Validation Constraint Check",
        phase=HookPhase.PRE_VALIDATION,
        priority=90,
        condition_query="""
            PREFIX kgc: <https://kgc.org/ns/>
            ASK {
                ?s kgc:age ?age .
                FILTER (?age < 0 || ?age > 150)
            }
        """,
        action=HookAction.REJECT,
        handler_data={"reason": "Age must be between 0 and 150"},
    )
    registry.register(hook4)

    # Hook 5: POST_VALIDATION transform
    hook5 = KnowledgeHook(
        hook_id="post-validation-transform",
        name="Post-Validation Data Transform",
        phase=HookPhase.POST_VALIDATION,
        priority=60,
        condition_query="""
            PREFIX kgc: <https://kgc.org/ns/>
            ASK { ?s kgc:requiresTransform true }
        """,
        action=HookAction.TRANSFORM,
        handler_data={"pattern": "normalize-data"},
    )
    registry.register(hook5)

    return registry


@pytest.fixture
def sample_hook_receipts() -> list[HookReceipt]:
    """Create list of 20 HookReceipt objects with varied durations.

    Generates realistic execution receipts with:
    - Normal distribution of durations (mean ~10ms, std ~2ms)
    - Mix of phases and actions
    - Some condition matches, some misses
    - Occasional errors (1 in 20)

    Returns
    -------
    list[HookReceipt]
        20 receipts suitable for SPC and statistical analysis.

    Examples
    --------
    >>> def test_receipt_statistics(sample_hook_receipts):
    ...     assert len(sample_hook_receipts) == 20
    ...     durations = [r.duration_ms for r in sample_hook_receipts]
    ...     assert 8.0 < statistics.mean(durations) < 12.0
    """
    import random

    random.seed(42)  # Reproducible test data

    base_time = datetime.now(UTC)
    receipts = []

    phases = list(HookPhase)
    actions = list(HookAction)
    hook_ids = [
        "pre-tick-validation",
        "on-change-entity",
        "post-tick-notify",
        "pre-validation-constraint",
        "post-validation-transform",
    ]

    for i in range(20):
        # Generate realistic duration with normal distribution
        mean_duration = 10.0
        std_duration = 2.0
        duration = max(1.0, random.gauss(mean_duration, std_duration))

        # Occasional errors (5% rate)
        error = "Timeout error" if random.random() < 0.05 else None

        # 70% condition match rate
        matched = random.random() < 0.7

        receipt = HookReceipt(
            hook_id=random.choice(hook_ids),
            phase=random.choice(phases),
            timestamp=base_time + timedelta(milliseconds=i * 100),
            condition_matched=matched and error is None,
            action_taken=random.choice(actions) if matched and error is None else None,
            duration_ms=duration,
            error=error,
            triples_affected=random.randint(0, 10),
            metadata={"execution_id": f"exec-{i:03d}"},
        )
        receipts.append(receipt)

    return receipts


@pytest.fixture
def hybrid_engine_with_hooks(sample_hook_registry: HookRegistry) -> HybridEngine:
    """Create HybridEngine with hooks pre-loaded into graph.

    Parameters
    ----------
    sample_hook_registry : HookRegistry
        Registry with sample hooks

    Returns
    -------
    HybridEngine
        Engine with hooks loaded as RDF in the graph.

    Examples
    --------
    >>> def test_engine_has_hooks(hybrid_engine_with_hooks):
    ...     # Query for hooks in the graph
    ...     query = "PREFIX hook: <https://kgc.org/ns/hook/> ASK { ?h a hook:KnowledgeHook }"
    ...     result = hybrid_engine_with_hooks.store.query(query)
    ...     assert result is True
    """
    engine = HybridEngine()

    # Load all hooks as RDF into engine's graph
    hook_rdf = sample_hook_registry.export_all_rdf()
    if hook_rdf.strip():
        engine.load_data(hook_rdf, trigger_hooks=False)

    return engine


@pytest.fixture
def hook_executor(sample_hook_registry: HookRegistry, hybrid_engine_with_hooks: HybridEngine) -> HookExecutor:
    """Create HookExecutor with registry and engine ready for testing.

    Parameters
    ----------
    sample_hook_registry : HookRegistry
        Registry with sample hooks
    hybrid_engine_with_hooks : HybridEngine
        Engine with hooks pre-loaded

    Returns
    -------
    HookExecutor
        Executor ready for phase execution and testing.

    Examples
    --------
    >>> def test_executor_phases(hook_executor):
    ...     results = hook_executor.evaluate_conditions(HookPhase.PRE_TICK)
    ...     assert len(results) >= 1
    ...     assert all(isinstance(r, tuple) for r in results)
    """
    executor = HookExecutor(sample_hook_registry, hybrid_engine_with_hooks)
    executor.load_hooks_to_graph()
    return executor


@pytest.fixture
def sample_execution_data() -> dict[str, list[float]]:
    """Generate sample execution metrics for LSS analysis.

    Returns
    -------
    dict[str, list[float]]
        Dictionary with metrics:
        - execution_times: List of 50 durations
        - wait_times: List of 50 wait times
        - queue_depths: List of 50 queue depths

    Examples
    --------
    >>> def test_execution_data_format(sample_execution_data):
    ...     assert "execution_times" in sample_execution_data
    ...     assert len(sample_execution_data["execution_times"]) == 50
    ...     assert all(x > 0 for x in sample_execution_data["execution_times"])
    """
    import random

    random.seed(123)

    return {
        "execution_times": [random.gauss(10.0, 2.0) for _ in range(50)],
        "wait_times": [random.gauss(5.0, 1.0) for _ in range(50)],
        "queue_depths": [random.randint(0, 10) for _ in range(50)],
        "condition_eval_times": [random.gauss(2.0, 0.5) for _ in range(50)],
        "handler_exec_times": [random.gauss(8.0, 1.5) for _ in range(50)],
    }
