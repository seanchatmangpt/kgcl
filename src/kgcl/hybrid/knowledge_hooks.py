"""Pure N3 Logic Knowledge Hooks System.

This module implements Knowledge Hooks using the same architecture as workflow physics:
- N3 Rules define hook behavior (Pure Logic)
- PyOxigraph stores hook state (Matter)
- Python orchestrates tick-based execution (Time)

Architecture
------------
Following the Hard Separation principle:
- Hook definitions are RDF data in the graph
- Hook trigger conditions are SPARQL ASK/SELECT queries (stored as literals)
- Hook handlers are N3 rules that fire when conditions match
- Python ONLY orchestrates - NO hook logic in Python

Hook Lifecycle (N3-Driven)
--------------------------
1. PRE_TICK: Hooks with kgc:phase "pre_tick" evaluated before tick
2. ON_CHANGE: Hooks with kgc:phase "on_change" evaluate delta graph
3. POST_TICK: Hooks with kgc:phase "post_tick" evaluated after tick

The N3 rules detect when:
- A hook's condition matches current graph state
- The hook should fire based on its phase and priority
- The handler assertions should be added to the graph

Examples
--------
>>> from kgcl.hybrid import HybridEngine
>>> engine = HybridEngine()
>>>
>>> # Define a hook in RDF (stored in graph)
>>> hook_def = '''
... @prefix hook: <https://kgc.org/ns/hook/> .
... @prefix kgc: <https://kgc.org/ns/> .
...
... <urn:hook:validate-person> a hook:KnowledgeHook ;
...     hook:name "validate-person" ;
...     hook:phase "on_change" ;
...     hook:priority 100 ;
...     hook:enabled true ;
...     hook:conditionQuery \"\"\"
...         ASK { ?s a kgc:Person . FILTER NOT EXISTS { ?s kgc:name ?name } }
...     \"\"\" ;
...     hook:handlerAction hook:RejectChange ;
...     hook:handlerReason "Person must have a name" .
... '''
>>> engine.load_data(hook_def)
>>>
>>> # The N3 rules will automatically detect when conditions match
>>> # and fire the appropriate handler assertions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from enum import Enum
from typing import Any


class HookPhase(Enum):
    """Lifecycle phases when hooks can execute.

    Each phase corresponds to a point in the tick execution cycle.
    Hooks declare which phase(s) they respond to via kgc:phase.
    """

    PRE_TICK = "pre_tick"
    ON_CHANGE = "on_change"
    POST_TICK = "post_tick"
    PRE_VALIDATION = "pre_validation"
    POST_VALIDATION = "post_validation"


class HookAction(Enum):
    """Actions a hook can take when its condition matches.

    These are stored as RDF resources in the graph and matched by N3 rules.
    """

    ASSERT = "assert"  # Add triples to graph
    REJECT = "reject"  # Reject the change (rollback)
    NOTIFY = "notify"  # Record notification (audit)
    TRANSFORM = "transform"  # Modify triples before commit


@dataclass(frozen=True)
class HookReceipt:
    """Immutable record of hook execution.

    Follows the cryptographic receipt pattern from UNRDF architecture.
    All receipts are stored in the graph for provenance.

    Attributes
    ----------
    hook_id : str
        URI of the hook that executed
    phase : HookPhase
        Phase when hook executed
    timestamp : datetime
        Execution timestamp (UTC)
    condition_matched : bool
        Whether the condition query returned true
    action_taken : HookAction | None
        Action performed (if condition matched)
    duration_ms : float
        Execution time in milliseconds
    error : str | None
        Error message if execution failed
    triples_affected : int
        Number of triples added/modified/removed
    """

    hook_id: str
    phase: HookPhase
    timestamp: datetime
    condition_matched: bool
    action_taken: HookAction | None
    duration_ms: float
    error: str | None = None
    triples_affected: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_rdf(self) -> str:
        """Serialize receipt to RDF Turtle format.

        Returns
        -------
        str
            Receipt as Turtle triples
        """
        receipt_uri = f"<urn:receipt:{self.hook_id}:{self.timestamp.isoformat()}>"
        action_str = self.action_taken.value if self.action_taken else "none"

        return f"""
{receipt_uri} a <https://kgc.org/ns/hook/Receipt> ;
    <https://kgc.org/ns/hook/hookId> "{self.hook_id}" ;
    <https://kgc.org/ns/hook/phase> "{self.phase.value}" ;
    <https://kgc.org/ns/hook/timestamp> "{self.timestamp.isoformat()}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
    <https://kgc.org/ns/hook/conditionMatched> {str(self.condition_matched).lower()} ;
    <https://kgc.org/ns/hook/actionTaken> "{action_str}" ;
    <https://kgc.org/ns/hook/durationMs> {self.duration_ms} ;
    <https://kgc.org/ns/hook/triplesAffected> {self.triples_affected} .
"""


# =============================================================================
# N3 HOOK PHYSICS - Pure Logic Rules
# =============================================================================
# These rules are appended to the main N3_PHYSICS and govern hook behavior.
# ALL hook logic is expressed in N3 - Python only orchestrates execution.

N3_HOOK_PHYSICS = """
# =============================================================================
# KNOWLEDGE HOOKS ONTOLOGY
# =============================================================================
@prefix hook: <https://kgc.org/ns/hook/> .
@prefix kgc: <https://kgc.org/ns/> .
@prefix log: <http://www.w3.org/2000/10/swap/log#> .
@prefix string: <http://www.w3.org/2000/10/swap/string#> .

# =============================================================================
# HOOK LAW 1: CONDITION MATCH DETECTION
# =============================================================================
# Detects when a hook's SPARQL condition matches the current graph state.
# This rule fires when:
#   1. Hook is enabled
#   2. Hook's condition query has been evaluated and returned true
#   3. Hook hasn't already fired this tick (guard against re-firing)
{
    ?hook a hook:KnowledgeHook .
    ?hook hook:enabled true .
    ?hook hook:conditionMatched true .
    # Guard: Only fire if hook hasn't already executed this tick
    ?scope log:notIncludes { ?hook hook:executedThisTick true } .
}
=>
{
    ?hook hook:shouldFire true .
} .

# =============================================================================
# HOOK LAW 2: ASSERT ACTION HANDLER
# =============================================================================
# When a hook with ASSERT action fires, add its assertions to the graph.
{
    ?hook hook:shouldFire true .
    ?hook hook:handlerAction hook:Assert .
    ?hook hook:assertTriple ?assertion .
}
=>
{
    ?assertion hook:assertedBy ?hook .
    ?hook hook:executedThisTick true .
    ?hook hook:actionResult "asserted" .
} .

# =============================================================================
# HOOK LAW 3: REJECT ACTION HANDLER
# =============================================================================
# When a hook with REJECT action fires, mark the change for rollback.
{
    ?hook hook:shouldFire true .
    ?hook hook:handlerAction hook:Reject .
    ?hook hook:handlerReason ?reason .
}
=>
{
    ?hook hook:executedThisTick true .
    ?hook hook:actionResult "rejected" .
    ?hook kgc:rollbackRequested true .
    ?hook kgc:rollbackReason ?reason .
} .

# =============================================================================
# HOOK LAW 4: NOTIFY ACTION HANDLER
# =============================================================================
# When a hook with NOTIFY action fires, create a notification record.
{
    ?hook hook:shouldFire true .
    ?hook hook:handlerAction hook:Notify .
    ?hook hook:notifyMessage ?message .
}
=>
{
    ?hook hook:executedThisTick true .
    ?hook hook:actionResult "notified" .
    ?hook hook:notificationPending true .
    ?hook hook:notification ?message .
} .

# =============================================================================
# HOOK LAW 5: TRANSFORM ACTION HANDLER
# =============================================================================
# When a hook with TRANSFORM action fires, apply the transform pattern.
{
    ?hook hook:shouldFire true .
    ?hook hook:handlerAction hook:Transform .
    ?hook hook:transformPattern ?pattern .
}
=>
{
    ?hook hook:executedThisTick true .
    ?hook hook:actionResult "transformed" .
    ?hook hook:pendingTransform ?pattern .
} .

# =============================================================================
# HOOK LAW 6: PRIORITY ORDERING
# =============================================================================
# Higher priority hooks block lower priority hooks from firing on same condition.
# This ensures deterministic execution order.
{
    ?hook1 hook:shouldFire true .
    ?hook1 hook:priority ?p1 .
    ?hook2 hook:shouldFire true .
    ?hook2 hook:priority ?p2 .
    ?hook1 log:uri ?uri1 .
    ?hook2 log:uri ?uri2 .
    ?uri1 string:notEqualIgnoringCase ?uri2 .
    ?p1 math:greaterThan ?p2 .
    # Both hooks respond to same phase
    ?hook1 hook:phase ?phase .
    ?hook2 hook:phase ?phase .
}
=>
{
    ?hook2 hook:blockedBy ?hook1 .
} .

# =============================================================================
# HOOK LAW 7: BLOCKED HOOK SUPPRESSION
# =============================================================================
# Blocked hooks should not fire until blocking hook completes.
{
    ?hook hook:blockedBy ?blocker .
    ?scope log:notIncludes { ?blocker hook:executedThisTick true } .
}
=>
{
    ?hook hook:shouldFire false .
} .

# =============================================================================
# HOOK LAW 8: HOOK CHAINING
# =============================================================================
# Hooks can chain to other hooks via hook:chainTo.
# The chained hook activates after the parent completes.
{
    ?parent hook:executedThisTick true .
    ?parent hook:chainTo ?child .
    ?child hook:enabled true .
}
=>
{
    ?child hook:triggeredByChain true .
    ?child hook:conditionMatched true .
} .

# =============================================================================
# HOOK LAW 9: MILESTONE HOOKS
# =============================================================================
# Hooks can be triggered by milestone achievement (workflow integration).
{
    ?milestone kgc:status "Reached" .
    ?hook hook:triggeredByMilestone ?milestone .
    ?hook hook:enabled true .
}
=>
{
    ?hook hook:conditionMatched true .
} .

# =============================================================================
# HOOK LAW 10: DELTA-BASED HOOKS
# =============================================================================
# Hooks can react to specific delta patterns (changes in the graph).
# The delta triple pattern is matched against hook:deltaPattern.
{
    ?subject ?predicate ?object .
    ?hook hook:deltaPattern ?pattern .
    ?pattern hook:subjectType ?subjectType .
    ?subject a ?subjectType .
    ?hook hook:enabled true .
}
=>
{
    ?hook hook:deltaTriggered true .
    ?hook hook:conditionMatched true .
} .

# =============================================================================
# HOOK LAW 11: COMPOSITE CONDITIONS (AND)
# =============================================================================
# Hook fires only when ALL sub-conditions match.
{
    ?hook hook:compositeCondition ?composite .
    ?composite hook:operator hook:And .
    ?composite hook:subCondition ?cond1 .
    ?composite hook:subCondition ?cond2 .
    ?cond1 hook:matched true .
    ?cond2 hook:matched true .
    ?cond1 log:uri ?uri1 .
    ?cond2 log:uri ?uri2 .
    ?uri1 string:notEqualIgnoringCase ?uri2 .
}
=>
{
    ?hook hook:conditionMatched true .
} .

# =============================================================================
# HOOK LAW 12: COMPOSITE CONDITIONS (OR)
# =============================================================================
# Hook fires when ANY sub-condition matches.
{
    ?hook hook:compositeCondition ?composite .
    ?composite hook:operator hook:Or .
    ?composite hook:subCondition ?cond .
    ?cond hook:matched true .
}
=>
{
    ?hook hook:conditionMatched true .
} .

# =============================================================================
# HOOK LAW 13: TICK BOUNDARY CLEANUP
# =============================================================================
# At end of tick, clear temporary hook state for next tick.
# This is triggered by Python setting kgc:tickComplete.
{
    ?tick kgc:tickComplete true .
    ?hook hook:executedThisTick true .
}
=>
{
    ?hook hook:executedThisTick false .
    ?hook hook:shouldFire false .
    ?hook hook:conditionMatched false .
} .
"""


@dataclass
class KnowledgeHook:
    """Python representation of an N3 Knowledge Hook.

    This class provides a convenient Python interface for creating hooks,
    but the actual hook logic lives in N3 rules. This class generates
    the RDF representation that gets loaded into the graph.

    Attributes
    ----------
    hook_id : str
        Unique hook identifier (becomes URI)
    name : str
        Human-readable hook name
    phase : HookPhase
        Lifecycle phase when hook executes
    priority : int
        Execution priority (higher = earlier)
    enabled : bool
        Whether hook is active
    condition_query : str
        SPARQL ASK/SELECT query as condition
    action : HookAction
        Action to take when condition matches
    handler_data : dict[str, Any]
        Action-specific handler configuration
    """

    hook_id: str
    name: str
    phase: HookPhase
    priority: int = 50
    enabled: bool = True
    condition_query: str = ""
    action: HookAction = HookAction.NOTIFY
    handler_data: dict[str, Any] = field(default_factory=dict)

    def to_rdf(self) -> str:
        """Generate RDF Turtle representation of this hook.

        Returns
        -------
        str
            Hook definition as Turtle triples
        """
        uri = f"<urn:hook:{self.hook_id}>"

        # Escape backslashes first, then quotes, then normalize whitespace for Turtle
        escaped_query = self.condition_query.replace("\\", "\\\\")
        escaped_query = escaped_query.replace('"', '\\"')
        # Normalize whitespace - replace newlines with spaces and collapse multiple spaces
        escaped_query = " ".join(escaped_query.split())

        base = f"""
@prefix hook: <https://kgc.org/ns/hook/> .
@prefix kgc: <https://kgc.org/ns/> .

{uri} a hook:KnowledgeHook ;
    hook:name "{self.name}" ;
    hook:phase "{self.phase.value}" ;
    hook:priority {self.priority} ;
    hook:enabled {str(self.enabled).lower()} ;
    hook:conditionQuery "{escaped_query}" ;
    hook:handlerAction hook:{self.action.value.title()} """

        # Add action-specific properties
        if self.action == HookAction.REJECT:
            reason = self.handler_data.get("reason", "Validation failed")
            base += f';\n    hook:handlerReason "{reason}" '

        if self.action == HookAction.NOTIFY:
            message = self.handler_data.get("message", "Hook triggered")
            base += f';\n    hook:notifyMessage "{message}" '

        if self.action == HookAction.TRANSFORM:
            pattern = self.handler_data.get("pattern", "")
            base += f';\n    hook:transformPattern "{pattern}" '

        base += ".\n"
        return base


class HookRegistry:
    """Registry for managing knowledge hooks.

    Provides Python interface for hook CRUD operations,
    but all hooks are stored as RDF in the engine's graph.

    Attributes
    ----------
    _hooks : dict[str, KnowledgeHook]
        In-memory cache of hooks (source of truth is graph)
    _receipts : list[HookReceipt]
        Execution history
    """

    def __init__(self) -> None:
        """Initialize hook registry."""
        self._hooks: dict[str, KnowledgeHook] = {}
        self._receipts: list[HookReceipt] = []

    def register(self, hook: KnowledgeHook) -> str:
        """Register a new hook.

        Parameters
        ----------
        hook : KnowledgeHook
            Hook to register

        Returns
        -------
        str
            Hook ID
        """
        self._hooks[hook.hook_id] = hook
        return hook.hook_id

    def unregister(self, hook_id: str) -> bool:
        """Unregister a hook.

        Parameters
        ----------
        hook_id : str
            Hook to unregister

        Returns
        -------
        bool
            True if hook was found and removed
        """
        if hook_id in self._hooks:
            del self._hooks[hook_id]
            return True
        return False

    def get(self, hook_id: str) -> KnowledgeHook | None:
        """Get hook by ID.

        Parameters
        ----------
        hook_id : str
            Hook identifier

        Returns
        -------
        KnowledgeHook | None
            Hook if found
        """
        return self._hooks.get(hook_id)

    def get_all(self) -> list[KnowledgeHook]:
        """Get all registered hooks.

        Returns
        -------
        list[KnowledgeHook]
            All hooks
        """
        return list(self._hooks.values())

    def get_by_phase(self, phase: HookPhase) -> list[KnowledgeHook]:
        """Get hooks for a specific phase.

        Parameters
        ----------
        phase : HookPhase
            Lifecycle phase

        Returns
        -------
        list[KnowledgeHook]
            Hooks sorted by priority (descending)
        """
        hooks = [h for h in self._hooks.values() if h.phase == phase and h.enabled]
        return sorted(hooks, key=lambda h: h.priority, reverse=True)

    def enable(self, hook_id: str) -> bool:
        """Enable a hook.

        Parameters
        ----------
        hook_id : str
            Hook to enable

        Returns
        -------
        bool
            True if hook was found
        """
        hook = self._hooks.get(hook_id)
        if hook:
            # Create new hook with enabled=True (dataclass is frozen-ish for this)
            self._hooks[hook_id] = KnowledgeHook(
                hook_id=hook.hook_id,
                name=hook.name,
                phase=hook.phase,
                priority=hook.priority,
                enabled=True,
                condition_query=hook.condition_query,
                action=hook.action,
                handler_data=hook.handler_data,
            )
            return True
        return False

    def disable(self, hook_id: str) -> bool:
        """Disable a hook.

        Parameters
        ----------
        hook_id : str
            Hook to disable

        Returns
        -------
        bool
            True if hook was found
        """
        hook = self._hooks.get(hook_id)
        if hook:
            self._hooks[hook_id] = KnowledgeHook(
                hook_id=hook.hook_id,
                name=hook.name,
                phase=hook.phase,
                priority=hook.priority,
                enabled=False,
                condition_query=hook.condition_query,
                action=hook.action,
                handler_data=hook.handler_data,
            )
            return True
        return False

    def add_receipt(self, receipt: HookReceipt) -> None:
        """Record hook execution receipt.

        Parameters
        ----------
        receipt : HookReceipt
            Execution receipt
        """
        self._receipts.append(receipt)

    def get_receipts(self, hook_id: str | None = None, limit: int = 100) -> list[HookReceipt]:
        """Get execution receipts.

        Parameters
        ----------
        hook_id : str | None
            Filter by hook ID
        limit : int
            Maximum receipts to return

        Returns
        -------
        list[HookReceipt]
            Recent receipts (newest first)
        """
        receipts = self._receipts
        if hook_id:
            receipts = [r for r in receipts if r.hook_id == hook_id]
        return sorted(receipts, key=lambda r: r.timestamp, reverse=True)[:limit]

    def export_all_rdf(self) -> str:
        """Export all hooks as RDF.

        Returns
        -------
        str
            All hooks in Turtle format
        """
        return "\n".join(hook.to_rdf() for hook in self._hooks.values())

    def get_statistics(self) -> dict[str, Any]:
        """Get registry statistics.

        Returns
        -------
        dict[str, Any]
            Statistics including:
            - total_hooks
            - enabled_hooks
            - disabled_hooks
            - hooks_by_phase
            - hooks_by_action
            - total_executions
        """
        hooks = list(self._hooks.values())
        enabled = [h for h in hooks if h.enabled]
        disabled = [h for h in hooks if not h.enabled]

        by_phase: dict[str, int] = {}
        for hook in hooks:
            by_phase[hook.phase.value] = by_phase.get(hook.phase.value, 0) + 1

        by_action: dict[str, int] = {}
        for hook in hooks:
            by_action[hook.action.value] = by_action.get(hook.action.value, 0) + 1

        return {
            "total_hooks": len(hooks),
            "enabled_hooks": len(enabled),
            "disabled_hooks": len(disabled),
            "hooks_by_phase": by_phase,
            "hooks_by_action": by_action,
            "total_executions": len(self._receipts),
        }


class HookExecutor:
    """Executes hooks within tick lifecycle.

    Integrates with the tick controller to evaluate hook conditions
    and execute handlers at appropriate phases.

    The executor:
    1. Loads hook definitions from registry to graph
    2. Evaluates SPARQL conditions
    3. Sets conditionMatched flags for N3 rules to fire
    4. Collects execution results
    5. Records receipts

    Attributes
    ----------
    _registry : HookRegistry
        Hook registry
    _engine : Any
        Hybrid engine instance
    """

    def __init__(self, registry: HookRegistry, engine: Any) -> None:
        """Initialize hook executor.

        Parameters
        ----------
        registry : HookRegistry
            Hook registry
        engine : Any
            Hybrid engine instance
        """
        self._registry = registry
        self._engine = engine

    def load_hooks_to_graph(self) -> int:
        """Load all registered hooks as RDF into the engine graph.

        Returns
        -------
        int
            Number of hooks loaded
        """
        rdf = self._registry.export_all_rdf()
        if rdf.strip():
            # Use trigger_hooks=False to avoid infinite recursion
            # (loading hooks should not trigger hooks)
            self._engine.load_data(rdf, trigger_hooks=False)
        return len(self._registry.get_all())

    def evaluate_conditions(self, phase: HookPhase) -> list[tuple[str, bool]]:
        """Evaluate condition queries for hooks in a phase.

        Parameters
        ----------
        phase : HookPhase
            Current execution phase

        Returns
        -------
        list[tuple[str, bool]]
            List of (hook_id, condition_matched) pairs
        """
        import time

        results: list[tuple[str, bool]] = []
        hooks = self._registry.get_by_phase(phase)

        for hook in hooks:
            start = time.perf_counter()
            matched = False

            if hook.condition_query.strip():
                try:
                    # Execute SPARQL ASK query on engine's store
                    query_result = self._engine.store.query(hook.condition_query)
                    matched = bool(query_result)
                except Exception as e:
                    # Log error but don't fail
                    import logging

                    logging.getLogger(__name__).warning(f"Hook {hook.hook_id} condition evaluation failed: {e}")
                    matched = False
            else:
                # Empty condition = always match
                matched = True

            duration_ms = (time.perf_counter() - start) * 1000

            # Set conditionMatched in graph so N3 rules can fire
            if matched:
                uri = f"<urn:hook:{hook.hook_id}>"
                # Use trigger_hooks=False to avoid infinite recursion
                self._engine.load_data(f"{uri} <https://kgc.org/ns/hook/conditionMatched> true .", trigger_hooks=False)

            results.append((hook.hook_id, matched))

            # Record receipt
            receipt = HookReceipt(
                hook_id=hook.hook_id,
                phase=phase,
                timestamp=datetime.now(UTC),
                condition_matched=matched,
                action_taken=hook.action if matched else None,
                duration_ms=duration_ms,
            )
            self._registry.add_receipt(receipt)

        return results

    def execute_phase(self, phase: HookPhase) -> list[HookReceipt]:
        """Execute all hooks for a phase.

        Parameters
        ----------
        phase : HookPhase
            Phase to execute

        Returns
        -------
        list[HookReceipt]
            Receipts from this phase
        """
        # Evaluate conditions (sets flags for N3 rules)
        self.evaluate_conditions(phase)

        # Apply physics (N3 rules fire based on conditionMatched flags)
        # The N3 rules handle the actual hook logic
        self._engine.apply_physics()

        # Return receipts for this phase
        hooks = self._registry.get_by_phase(phase)
        return [r for r in self._registry.get_receipts(limit=len(hooks) * 2) if r.phase == phase]

    def check_rollback_requested(self) -> tuple[bool, str | None]:
        """Check if any hook requested a rollback.

        Returns
        -------
        tuple[bool, str | None]
            (rollback_requested, reason)

        Notes
        -----
        This checks receipts from the most recent phase execution.
        If a REJECT action was taken, returns the rejection reason.
        """
        # Check recent receipts for REJECT actions
        # This is more reliable than querying N3 rules since it works
        # without requiring EYE reasoner for simple validation hooks
        recent_receipts = self._registry.get_receipts(limit=100)
        for receipt in recent_receipts:
            if receipt.action_taken == HookAction.REJECT and receipt.condition_matched:
                # Find the hook to get the reason
                hook = self._registry.get(receipt.hook_id)
                if hook:
                    reason = hook.handler_data.get("reason", "Validation failed")
                    return (True, reason)
        return (False, None)

    def clear_tick_state(self) -> None:
        """Clear temporary hook state at end of tick.

        Sets kgc:tickComplete flag which triggers N3 cleanup rules.
        """
        tick_complete = """
        <urn:tick:current> <https://kgc.org/ns/tickComplete> true .
        """
        # Use trigger_hooks=False to avoid infinite recursion
        self._engine.load_data(tick_complete, trigger_hooks=False)
        self._engine.apply_physics()
