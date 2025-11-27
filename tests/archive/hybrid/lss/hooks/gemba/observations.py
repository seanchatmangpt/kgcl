"""Hook Gemba Walk observation framework with dataclasses and doctests.

This module provides Gemba Walk observations for Knowledge Hooks,
allowing inspection of hook execution behavior during tick cycles.

Examples
--------
>>> from kgcl.hybrid.knowledge_hooks import HookPhase, HookAction
>>> from tests.hybrid.lss.hooks.gemba.observations import HookGembaObservation
>>> from datetime import datetime, UTC
>>> obs = HookGembaObservation(
...     timestamp=datetime.now(UTC),
...     hook_id="validate-person",
...     phase=HookPhase.PRE_TICK,
...     action=HookAction.NOTIFY,
...     duration_ms=1.5,
...     condition_matched=True,
...     notes="Validated person entity",
... )
>>> obs.condition_matched
True
>>> obs.phase == HookPhase.PRE_TICK
True
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from kgcl.hybrid.knowledge_hooks import HookAction, HookExecutor, HookPhase


@dataclass(frozen=True)
class HookGembaObservation:
    """A single Gemba Walk observation of hook execution.

    Parameters
    ----------
    timestamp : datetime
        When the observation was made
    hook_id : str
        Hook identifier
    phase : HookPhase
        Execution phase (PRE_TICK, ON_CHANGE, POST_TICK, etc.)
    action : HookAction
        Hook action type (ASSERT, REJECT, NOTIFY, TRANSFORM)
    duration_ms : float
        Execution duration in milliseconds
    condition_matched : bool
        Whether hook condition matched
    notes : str
        Additional observation notes

    Examples
    --------
    >>> from kgcl.hybrid.knowledge_hooks import HookPhase, HookAction
    >>> from datetime import datetime, UTC
    >>> obs = HookGembaObservation(
    ...     timestamp=datetime.now(UTC),
    ...     hook_id="test-hook",
    ...     phase=HookPhase.POST_TICK,
    ...     action=HookAction.ASSERT,
    ...     duration_ms=2.3,
    ...     condition_matched=True,
    ...     notes="Hook fired successfully",
    ... )
    >>> obs.hook_id
    'test-hook'
    >>> obs.condition_matched
    True
    """

    timestamp: datetime
    hook_id: str
    phase: HookPhase
    action: HookAction
    duration_ms: float
    condition_matched: bool
    notes: str

    def __repr__(self) -> str:
        """Return string representation.

        Returns
        -------
        str
            Summary of observation

        Examples
        --------
        >>> from kgcl.hybrid.knowledge_hooks import HookPhase, HookAction
        >>> from datetime import datetime, UTC
        >>> obs = HookGembaObservation(
        ...     timestamp=datetime.now(UTC),
        ...     hook_id="hook1",
        ...     phase=HookPhase.PRE_TICK,
        ...     action=HookAction.NOTIFY,
        ...     duration_ms=1.5,
        ...     condition_matched=True,
        ...     notes="Test",
        ... )
        >>> "hook1" in repr(obs)
        True
        >>> "MATCHED" in repr(obs)
        True
        """
        match_status = "MATCHED" if self.condition_matched else "NO_MATCH"
        return f"HookGembaObservation({match_status}: {self.hook_id} @ {self.phase.value}, {self.duration_ms:.2f}ms)"


@dataclass(frozen=True)
class HookGembaWalk:
    """Result of a complete Gemba Walk across hook executions.

    Parameters
    ----------
    walk_id : str
        Unique walk identifier
    start_time : datetime
        Walk start timestamp
    end_time : datetime | None
        Walk end timestamp (None if still in progress)
    observations : list[HookGembaObservation]
        All observations made during walk
    total_hooks_observed : int
        Total number of hooks observed
    avg_duration_ms : float
        Average hook execution duration
    waste_identified : list[str]
        Waste patterns detected (Lean principle)
    improvement_opportunities : list[str]
        Opportunities for optimization

    Examples
    --------
    >>> from datetime import datetime, UTC
    >>> walk = HookGembaWalk(
    ...     walk_id="walk-001",
    ...     start_time=datetime.now(UTC),
    ...     end_time=datetime.now(UTC),
    ...     observations=[],
    ...     total_hooks_observed=5,
    ...     avg_duration_ms=1.8,
    ...     waste_identified=["Hook fired but no action taken"],
    ...     improvement_opportunities=["Cache SPARQL query results"],
    ... )
    >>> walk.total_hooks_observed
    5
    >>> len(walk.waste_identified)
    1
    """

    walk_id: str
    start_time: datetime
    end_time: datetime | None
    observations: list[HookGembaObservation]
    total_hooks_observed: int
    avg_duration_ms: float
    waste_identified: list[str] = field(default_factory=list)
    improvement_opportunities: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        """Return string representation.

        Returns
        -------
        str
            Walk summary

        Examples
        --------
        >>> from datetime import datetime, UTC
        >>> walk = HookGembaWalk(
        ...     walk_id="walk-001",
        ...     start_time=datetime.now(UTC),
        ...     end_time=datetime.now(UTC),
        ...     observations=[],
        ...     total_hooks_observed=3,
        ...     avg_duration_ms=2.5,
        ...     waste_identified=[],
        ...     improvement_opportunities=[],
        ... )
        >>> "walk-001" in repr(walk)
        True
        >>> "3 hooks" in repr(walk)
        True
        """
        status = "COMPLETE" if self.end_time else "IN_PROGRESS"
        return f"HookGembaWalk({status}: {self.walk_id}, {self.total_hooks_observed} hooks, {self.avg_duration_ms:.2f}ms avg)"

    @property
    def duration_seconds(self) -> float:
        """Calculate walk duration in seconds.

        Returns
        -------
        float
            Duration in seconds (0 if not complete)

        Examples
        --------
        >>> from datetime import datetime, UTC, timedelta
        >>> start = datetime.now(UTC)
        >>> end = start + timedelta(seconds=5)
        >>> walk = HookGembaWalk(
        ...     walk_id="walk-001",
        ...     start_time=start,
        ...     end_time=end,
        ...     observations=[],
        ...     total_hooks_observed=0,
        ...     avg_duration_ms=0.0,
        ... )
        >>> walk.duration_seconds >= 5.0
        True
        """
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def hooks_matched(self) -> int:
        """Count hooks that matched conditions.

        Returns
        -------
        int
            Number of matched hooks

        Examples
        --------
        >>> from datetime import datetime, UTC
        >>> from kgcl.hybrid.knowledge_hooks import HookPhase, HookAction
        >>> obs1 = HookGembaObservation(
        ...     timestamp=datetime.now(UTC),
        ...     hook_id="hook1",
        ...     phase=HookPhase.PRE_TICK,
        ...     action=HookAction.NOTIFY,
        ...     duration_ms=1.0,
        ...     condition_matched=True,
        ...     notes="",
        ... )
        >>> obs2 = HookGembaObservation(
        ...     timestamp=datetime.now(UTC),
        ...     hook_id="hook2",
        ...     phase=HookPhase.PRE_TICK,
        ...     action=HookAction.NOTIFY,
        ...     duration_ms=1.0,
        ...     condition_matched=False,
        ...     notes="",
        ... )
        >>> walk = HookGembaWalk(
        ...     walk_id="walk-001",
        ...     start_time=datetime.now(UTC),
        ...     end_time=datetime.now(UTC),
        ...     observations=[obs1, obs2],
        ...     total_hooks_observed=2,
        ...     avg_duration_ms=1.0,
        ... )
        >>> walk.hooks_matched
        1
        """
        return sum(1 for obs in self.observations if obs.condition_matched)


def observe_hook_execution(executor: HookExecutor, phase: HookPhase) -> HookGembaObservation:
    """Observe a single hook execution phase.

    Parameters
    ----------
    executor : HookExecutor
        Hook executor instance
    phase : HookPhase
        Phase to observe

    Returns
    -------
    HookGembaObservation
        Observation of hook execution

    Notes
    -----
    This function evaluates hook conditions and observes the results.
    It does NOT invoke the full N3 rule execution (which requires EYE).
    Instead, it directly observes the condition evaluation phase.
    """
    import time

    start = time.perf_counter()

    # Evaluate conditions for this phase (does NOT require EYE)
    # This will create receipts in the registry
    results = executor.evaluate_conditions(phase)

    duration_ms = (time.perf_counter() - start) * 1000

    # Get most recent receipts for this phase
    all_receipts = executor._registry.get_receipts(limit=100)
    phase_receipts = [r for r in all_receipts if r.phase == phase]

    # Get most recent receipt if any
    if phase_receipts:
        receipt = phase_receipts[0]  # Most recent
        return HookGembaObservation(
            timestamp=receipt.timestamp,
            hook_id=receipt.hook_id,
            phase=receipt.phase,
            action=receipt.action_taken or HookAction.NOTIFY,
            duration_ms=receipt.duration_ms,
            condition_matched=receipt.condition_matched,
            notes=f"Action: {receipt.action_taken.value if receipt.action_taken else 'none'}",
        )

    # No hooks executed
    return HookGembaObservation(
        timestamp=datetime.now(UTC),
        hook_id="none",
        phase=phase,
        action=HookAction.NOTIFY,
        duration_ms=duration_ms,
        condition_matched=False,
        notes="No hooks registered for phase",
    )


def conduct_hook_gemba_walk(executor: HookExecutor, duration_ticks: int) -> HookGembaWalk:
    """Conduct a full Gemba Walk across multiple tick cycles.

    Parameters
    ----------
    executor : HookExecutor
        Hook executor instance
    duration_ticks : int
        Number of ticks to observe

    Returns
    -------
    HookGembaWalk
        Complete walk result with all observations

    Notes
    -----
    This function observes hook behavior over multiple ticks,
    collecting metrics and identifying waste/improvement opportunities.

    Examples
    --------
    >>> from kgcl.hybrid.knowledge_hooks import HookRegistry, HookExecutor
    >>> from kgcl.hybrid.hybrid_engine import HybridEngine
    >>> engine = HybridEngine()
    >>> registry = HookRegistry()
    >>> executor = HookExecutor(registry, engine)
    >>> walk = conduct_hook_gemba_walk(executor, duration_ticks=3)
    >>> walk.total_hooks_observed >= 0
    True
    >>> isinstance(walk.observations, list)
    True
    """
    walk_id = f"walk-{datetime.now(UTC).isoformat()}"
    start_time = datetime.now(UTC)
    observations: list[HookGembaObservation] = []
    total_duration_ms = 0.0

    # Observe across tick cycles
    for tick in range(duration_ticks):
        # Observe PRE_TICK phase
        pre_obs = observe_hook_execution(executor, HookPhase.PRE_TICK)
        observations.append(pre_obs)
        total_duration_ms += pre_obs.duration_ms

        # Observe ON_CHANGE phase
        change_obs = observe_hook_execution(executor, HookPhase.ON_CHANGE)
        observations.append(change_obs)
        total_duration_ms += change_obs.duration_ms

        # Observe POST_TICK phase
        post_obs = observe_hook_execution(executor, HookPhase.POST_TICK)
        observations.append(post_obs)
        total_duration_ms += post_obs.duration_ms

    end_time = datetime.now(UTC)
    total_hooks = len(observations)
    avg_duration = total_duration_ms / total_hooks if total_hooks > 0 else 0.0

    # Identify waste patterns (Lean principle)
    waste_identified: list[str] = []
    if total_hooks > 0:
        no_match_rate = sum(1 for obs in observations if not obs.condition_matched) / total_hooks
        if no_match_rate > 0.8:
            waste_identified.append(f"High no-match rate: {no_match_rate:.1%} of hooks didn't match")

        slow_hooks = [obs for obs in observations if obs.duration_ms > 10.0]
        if slow_hooks:
            waste_identified.append(f"Slow execution: {len(slow_hooks)} hooks > 10ms")

    # Identify improvement opportunities
    improvement_opportunities: list[str] = []
    if avg_duration > 5.0:
        improvement_opportunities.append("Consider caching SPARQL query results")
    if total_hooks > duration_ticks * 10:
        improvement_opportunities.append("High hook count may indicate over-instrumentation")

    return HookGembaWalk(
        walk_id=walk_id,
        start_time=start_time,
        end_time=end_time,
        observations=observations,
        total_hooks_observed=total_hooks,
        avg_duration_ms=avg_duration,
        waste_identified=waste_identified,
        improvement_opportunities=improvement_opportunities,
    )
