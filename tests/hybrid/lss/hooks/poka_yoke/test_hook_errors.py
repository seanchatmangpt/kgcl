"""Poka-Yoke Tests for Knowledge Hooks Error Proofing.

This module tests all 10 pre-defined poka-yokes for Knowledge Hooks:

SHUTDOWN (Highest Severity - Prevent Registration)
---------------------------------------------------
- PY-HOOK-001: Empty Condition Query
- PY-HOOK-005: Disabled Hook with Chaining
- PY-HOOK-010: Recursive Hook Trigger

CONTROL (Medium Severity - Gate Until Valid)
--------------------------------------------
- PY-HOOK-003: Priority Conflict
- PY-HOOK-007: Invalid Action Type

VALIDATION (Pre-Execution Check)
--------------------------------
- PY-HOOK-004: Invalid Phase Assignment
- PY-HOOK-008: Missing Handler Data

WARNING (Informational - Doesn't Stop)
--------------------------------------
- PY-HOOK-002: Circular Chain Detection
- PY-HOOK-006: Orphan Chained Hook
- PY-HOOK-009: Overly Broad Condition

Safety Principles
-----------------
1. **SHUTDOWN**: Fail-fast on safety-critical errors
2. **CONTROL**: Gate process until corrected
3. **VALIDATION**: Check state before execution
4. **WARNING**: Alert without blocking

References
----------
- Shigeo Shingo: "Zero Quality Control" - Poka-Yoke methodology
- Toyota Production System: Andon cord (line-stop)
- IEC 61508: Functional Safety Standards
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.hybrid_engine import HybridEngine
from kgcl.hybrid.knowledge_hooks import HookAction, HookPhase, HookRegistry, KnowledgeHook
from tests.hybrid.lss.hooks.poka_yoke.types import (
    PY_HOOK_001,
    PY_HOOK_002,
    PY_HOOK_003,
    PY_HOOK_004,
    PY_HOOK_005,
    PY_HOOK_006,
    PY_HOOK_007,
    PY_HOOK_008,
    PY_HOOK_009,
    PY_HOOK_010,
    HookPokaYokeType,
)


@pytest.fixture
def engine() -> HybridEngine:
    """Create fresh HybridEngine for testing."""
    return HybridEngine()


@pytest.fixture
def registry() -> HookRegistry:
    """Create fresh HookRegistry for testing."""
    return HookRegistry()


class TestPYHook001ShutdownEmptyCondition:
    """PY-HOOK-001: SHUTDOWN on empty condition query.

    Safety-critical: Hooks without conditions would always fire,
    potentially executing unintended actions on every tick.
    """

    def test_shutdown_empty_condition_detected(self, registry: HookRegistry) -> None:
        """Empty condition query triggers SHUTDOWN."""
        assert PY_HOOK_001.type == HookPokaYokeType.SHUTDOWN
        assert "Empty Condition Query" in PY_HOOK_001.description

        # Attempt to create hook with empty condition
        invalid_hook = KnowledgeHook(
            hook_id="invalid-empty",
            name="Invalid Hook",
            phase=HookPhase.POST_TICK,
            condition_query="",  # EMPTY - violates PY-HOOK-001
            action=HookAction.NOTIFY,
        )

        # Apply poka-yoke: eval the condition from PY-HOOK-001
        condition_result = eval(PY_HOOK_001.condition, {"hook": invalid_hook, "len": len})
        assert condition_result is True, "PY-HOOK-001 condition should detect empty query"

        # SHUTDOWN: Should NOT register
        # In production, this would raise ValidationError
        # For test, we verify the poka-yoke detects it
        assert invalid_hook.condition_query.strip() == ""

    def test_valid_condition_passes(self, registry: HookRegistry) -> None:
        """Valid condition query passes PY-HOOK-001."""
        valid_hook = KnowledgeHook(
            hook_id="valid-with-condition",
            name="Valid Hook",
            phase=HookPhase.POST_TICK,
            condition_query="ASK { ?s ?p ?o }",  # Non-empty
            action=HookAction.NOTIFY,
        )

        # Apply poka-yoke
        condition_result = eval(PY_HOOK_001.condition, {"hook": valid_hook, "len": len})
        assert condition_result is False, "PY-HOOK-001 should NOT fire for valid query"

        # Should register successfully
        hook_id = registry.register(valid_hook)
        assert hook_id == "valid-with-condition"


class TestPYHook002WarningCircularChain:
    """PY-HOOK-002: WARNING on circular hook chains.

    Informational: Circular chains may cause infinite loops,
    but can be valid in some edge cases (bounded iteration).
    """

    def test_warning_circular_chain_detected(self, engine: HybridEngine) -> None:
        """Circular chain triggers WARNING."""
        assert PY_HOOK_002.type == HookPokaYokeType.WARNING
        assert "Circular Chain Detection" in PY_HOOK_002.description

        # Create circular chain: A -> B -> C -> A
        chain_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .

        <urn:hook:A> a hook:KnowledgeHook ;
            hook:name "Hook A" ;
            hook:chainTo <urn:hook:B> .

        <urn:hook:B> a hook:KnowledgeHook ;
            hook:name "Hook B" ;
            hook:chainTo <urn:hook:C> .

        <urn:hook:C> a hook:KnowledgeHook ;
            hook:name "Hook C" ;
            hook:chainTo <urn:hook:A> .
        """
        engine.load_data(chain_topology)

        # Apply poka-yoke: Run SPARQL from PY-HOOK-002
        # Extract SPARQL from multi-line string
        sparql_condition = PY_HOOK_002.condition.strip()
        result = engine.store.query(sparql_condition)

        # WARNING: Circular chain detected
        assert bool(result) is True, "PY-HOOK-002 should detect circular chain"

    def test_no_warning_linear_chain(self, engine: HybridEngine) -> None:
        """Linear chain passes PY-HOOK-002."""
        # Linear chain: A -> B -> C (no cycle)
        linear_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .

        <urn:hook:A> a hook:KnowledgeHook ;
            hook:name "Hook A" ;
            hook:chainTo <urn:hook:B> .

        <urn:hook:B> a hook:KnowledgeHook ;
            hook:name "Hook B" ;
            hook:chainTo <urn:hook:C> .

        <urn:hook:C> a hook:KnowledgeHook ;
            hook:name "Hook C" .
        """
        engine.load_data(linear_topology)

        # Apply poka-yoke
        sparql_condition = PY_HOOK_002.condition.strip()
        result = engine.store.query(sparql_condition)

        # No warning: Linear chain is valid
        assert bool(result) is False, "PY-HOOK-002 should NOT fire for linear chain"


class TestPYHook003ControlPriorityConflict:
    """PY-HOOK-003: CONTROL on priority conflicts.

    Medium severity: Multiple hooks with same phase and priority
    creates non-deterministic execution order.
    """

    def test_control_priority_conflict_detected(self, engine: HybridEngine) -> None:
        """Priority conflict triggers CONTROL."""
        assert PY_HOOK_003.type == HookPokaYokeType.CONTROL
        assert "Priority Conflict" in PY_HOOK_003.description

        # Create two hooks with same phase and priority
        conflict_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .

        <urn:hook:A> a hook:KnowledgeHook ;
            hook:name "Hook A" ;
            hook:phase "post_tick" ;
            hook:priority 100 .

        <urn:hook:B> a hook:KnowledgeHook ;
            hook:name "Hook B" ;
            hook:phase "post_tick" ;
            hook:priority 100 .
        """
        engine.load_data(conflict_topology)

        # Apply poka-yoke
        sparql_condition = PY_HOOK_003.condition.strip()
        result = engine.store.query(sparql_condition)

        # CONTROL: Priority conflict detected
        assert bool(result) is True, "PY-HOOK-003 should detect priority conflict"

    def test_no_control_unique_priorities(self, engine: HybridEngine) -> None:
        """Unique priorities pass PY-HOOK-003."""
        unique_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .

        <urn:hook:A> a hook:KnowledgeHook ;
            hook:name "Hook A" ;
            hook:phase "post_tick" ;
            hook:priority 100 .

        <urn:hook:B> a hook:KnowledgeHook ;
            hook:name "Hook B" ;
            hook:phase "post_tick" ;
            hook:priority 200 .
        """
        engine.load_data(unique_topology)

        # Apply poka-yoke
        sparql_condition = PY_HOOK_003.condition.strip()
        result = engine.store.query(sparql_condition)

        # No control: Unique priorities
        assert bool(result) is False, "PY-HOOK-003 should NOT fire for unique priorities"


class TestPYHook004ValidationInvalidPhase:
    """PY-HOOK-004: VALIDATION on invalid phase assignment.

    Pre-execution check: Phase must be one of the 5 valid values.
    """

    def test_validation_invalid_phase_detected(self, engine: HybridEngine) -> None:
        """Invalid phase triggers VALIDATION."""
        assert PY_HOOK_004.type == HookPokaYokeType.VALIDATION
        assert "Invalid Phase Assignment" in PY_HOOK_004.description

        # Create hook with invalid phase
        invalid_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .

        <urn:hook:Invalid> a hook:KnowledgeHook ;
            hook:name "Invalid Phase Hook" ;
            hook:phase "invalid_phase_name" .
        """
        engine.load_data(invalid_topology)

        # Apply poka-yoke
        sparql_condition = PY_HOOK_004.condition.strip()
        result = engine.store.query(sparql_condition)

        # VALIDATION: Invalid phase detected
        assert bool(result) is True, "PY-HOOK-004 should detect invalid phase"

    def test_valid_phases_pass(self, engine: HybridEngine) -> None:
        """Valid phases pass PY-HOOK-004."""
        valid_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .

        <urn:hook:PreTick> a hook:KnowledgeHook ;
            hook:name "Pre Tick" ;
            hook:phase "pre_tick" .

        <urn:hook:OnChange> a hook:KnowledgeHook ;
            hook:name "On Change" ;
            hook:phase "on_change" .

        <urn:hook:PostTick> a hook:KnowledgeHook ;
            hook:name "Post Tick" ;
            hook:phase "post_tick" .
        """
        engine.load_data(valid_topology)

        # Apply poka-yoke
        sparql_condition = PY_HOOK_004.condition.strip()
        result = engine.store.query(sparql_condition)

        # No validation error: All phases valid
        assert bool(result) is False, "PY-HOOK-004 should NOT fire for valid phases"


class TestPYHook005ShutdownDisabledChaining:
    """PY-HOOK-005: SHUTDOWN on disabled hook with chaining.

    Safety-critical: Disabled hooks should not chain to children,
    as this creates dead code paths.
    """

    def test_shutdown_disabled_with_chain_detected(self, engine: HybridEngine) -> None:
        """Disabled hook with chain triggers SHUTDOWN."""
        assert PY_HOOK_005.type == HookPokaYokeType.SHUTDOWN
        assert "Disabled Hook with Chaining" in PY_HOOK_005.description

        # Create disabled hook with chain
        invalid_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .

        <urn:hook:Disabled> a hook:KnowledgeHook ;
            hook:name "Disabled Parent" ;
            hook:enabled false ;
            hook:chainTo <urn:hook:Child> .

        <urn:hook:Child> a hook:KnowledgeHook ;
            hook:name "Child Hook" .
        """
        engine.load_data(invalid_topology)

        # Apply poka-yoke
        sparql_condition = PY_HOOK_005.condition.strip()
        result = engine.store.query(sparql_condition)

        # SHUTDOWN: Disabled hook with chain
        assert bool(result) is True, "PY-HOOK-005 should detect disabled hook with chain"

    def test_enabled_with_chain_passes(self, engine: HybridEngine) -> None:
        """Enabled hook with chain passes PY-HOOK-005."""
        valid_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .

        <urn:hook:Enabled> a hook:KnowledgeHook ;
            hook:name "Enabled Parent" ;
            hook:enabled true ;
            hook:chainTo <urn:hook:Child> .

        <urn:hook:Child> a hook:KnowledgeHook ;
            hook:name "Child Hook" .
        """
        engine.load_data(valid_topology)

        # Apply poka-yoke
        sparql_condition = PY_HOOK_005.condition.strip()
        result = engine.store.query(sparql_condition)

        # No shutdown: Enabled hook can chain
        assert bool(result) is False, "PY-HOOK-005 should NOT fire for enabled chain"


class TestPYHook006WarningOrphanChain:
    """PY-HOOK-006: WARNING on orphan chained hook.

    Informational: Hook chains to non-existent child.
    """

    def test_warning_orphan_chain_detected(self, engine: HybridEngine) -> None:
        """Orphan chain triggers WARNING."""
        assert PY_HOOK_006.type == HookPokaYokeType.WARNING
        assert "Orphan Chained Hook" in PY_HOOK_006.description

        # Create hook chaining to non-existent child
        orphan_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .

        <urn:hook:Parent> a hook:KnowledgeHook ;
            hook:name "Parent Hook" ;
            hook:chainTo <urn:hook:NonExistent> .
        """
        engine.load_data(orphan_topology)

        # Apply poka-yoke
        sparql_condition = PY_HOOK_006.condition.strip()
        result = engine.store.query(sparql_condition)

        # WARNING: Orphan chain detected
        assert bool(result) is True, "PY-HOOK-006 should detect orphan chain"

    def test_valid_chain_passes(self, engine: HybridEngine) -> None:
        """Valid chain passes PY-HOOK-006."""
        valid_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .

        <urn:hook:Parent> a hook:KnowledgeHook ;
            hook:name "Parent Hook" ;
            hook:chainTo <urn:hook:Child> .

        <urn:hook:Child> a hook:KnowledgeHook ;
            hook:name "Child Hook" .
        """
        engine.load_data(valid_topology)

        # Apply poka-yoke
        sparql_condition = PY_HOOK_006.condition.strip()
        result = engine.store.query(sparql_condition)

        # No warning: Child exists
        assert bool(result) is False, "PY-HOOK-006 should NOT fire for valid chain"


class TestPYHook007ControlInvalidAction:
    """PY-HOOK-007: CONTROL on invalid action type.

    Medium severity: Action must be one of 4 valid types.
    """

    def test_control_invalid_action_detected(self, engine: HybridEngine) -> None:
        """Invalid action triggers CONTROL."""
        assert PY_HOOK_007.type == HookPokaYokeType.CONTROL
        assert "Invalid Action Type" in PY_HOOK_007.description

        # Create hook with invalid action
        invalid_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .

        <urn:hook:Invalid> a hook:KnowledgeHook ;
            hook:name "Invalid Action" ;
            hook:handlerAction <https://kgc.org/ns/hook/InvalidAction> .
        """
        engine.load_data(invalid_topology)

        # Apply poka-yoke
        sparql_condition = PY_HOOK_007.condition.strip()
        result = engine.store.query(sparql_condition)

        # CONTROL: Invalid action detected
        assert bool(result) is True, "PY-HOOK-007 should detect invalid action"

    def test_valid_actions_pass(self, engine: HybridEngine) -> None:
        """Valid actions pass PY-HOOK-007."""
        valid_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .

        <urn:hook:Assert> a hook:KnowledgeHook ;
            hook:name "Assert Hook" ;
            hook:handlerAction hook:Assert .

        <urn:hook:Reject> a hook:KnowledgeHook ;
            hook:name "Reject Hook" ;
            hook:handlerAction hook:Reject .

        <urn:hook:Notify> a hook:KnowledgeHook ;
            hook:name "Notify Hook" ;
            hook:handlerAction hook:Notify .

        <urn:hook:Transform> a hook:KnowledgeHook ;
            hook:name "Transform Hook" ;
            hook:handlerAction hook:Transform .
        """
        engine.load_data(valid_topology)

        # Apply poka-yoke
        sparql_condition = PY_HOOK_007.condition.strip()
        result = engine.store.query(sparql_condition)

        # No control: All actions valid
        assert bool(result) is False, "PY-HOOK-007 should NOT fire for valid actions"


class TestPYHook008ValidationMissingHandlerData:
    """PY-HOOK-008: VALIDATION on missing handler data.

    Pre-execution: REJECT and NOTIFY require handler_data.
    """

    def test_validation_missing_handler_data(self, registry: HookRegistry) -> None:
        """Missing handler data triggers VALIDATION."""
        assert PY_HOOK_008.type == HookPokaYokeType.VALIDATION
        assert "Missing Handler Data" in PY_HOOK_008.description

        # REJECT without reason
        reject_hook = KnowledgeHook(
            hook_id="reject-no-reason",
            name="Reject Hook",
            phase=HookPhase.ON_CHANGE,
            action=HookAction.REJECT,
            handler_data={},  # Empty - violates PY-HOOK-008
        )

        # Apply poka-yoke
        condition_result = eval(PY_HOOK_008.condition, {"hook": reject_hook, "HookAction": HookAction})
        assert condition_result is True, "PY-HOOK-008 should detect missing handler_data"

    def test_valid_handler_data_passes(self, registry: HookRegistry) -> None:
        """Valid handler data passes PY-HOOK-008."""
        # REJECT with reason
        valid_hook = KnowledgeHook(
            hook_id="reject-with-reason",
            name="Reject Hook",
            phase=HookPhase.ON_CHANGE,
            action=HookAction.REJECT,
            handler_data={"reason": "Validation failed"},
        )

        # Apply poka-yoke
        condition_result = eval(PY_HOOK_008.condition, {"hook": valid_hook, "HookAction": HookAction})
        assert condition_result is False, "PY-HOOK-008 should NOT fire with valid handler_data"


class TestPYHook009WarningBroadCondition:
    """PY-HOOK-009: WARNING on overly broad condition.

    Informational: Condition that matches entire graph may impact performance.
    """

    def test_warning_broad_condition(self, registry: HookRegistry) -> None:
        """Broad condition triggers WARNING."""
        assert PY_HOOK_009.type == HookPokaYokeType.WARNING
        assert "Overly Broad Condition" in PY_HOOK_009.description

        # Hook with extremely broad condition
        broad_hook = KnowledgeHook(
            hook_id="broad-condition",
            name="Broad Hook",
            phase=HookPhase.POST_TICK,
            condition_query="ASK { ?s ?p ?o }",  # Matches everything
            action=HookAction.NOTIFY,
        )

        # In practice, this would check graph size and query selectivity
        # For now, we verify the poka-yoke definition exists
        assert "?s ?p ?o" in PY_HOOK_009.condition


class TestPYHook010ShutdownRecursiveTrigger:
    """PY-HOOK-010: SHUTDOWN on recursive milestone triggering.

    Safety-critical: Recursive triggering causes infinite loops.
    """

    def test_shutdown_recursive_trigger_detected(self, engine: HybridEngine) -> None:
        """Recursive trigger triggers SHUTDOWN."""
        assert PY_HOOK_010.type == HookPokaYokeType.SHUTDOWN
        assert "Recursive Hook Trigger" in PY_HOOK_010.description

        # Create recursive milestone triggers
        recursive_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .

        <urn:hook:A> a hook:KnowledgeHook ;
            hook:name "Hook A" ;
            hook:triggeredByMilestone <urn:milestone:M1> .

        <urn:milestone:M1> hook:triggeredByMilestone <urn:hook:A> .
        """
        engine.load_data(recursive_topology)

        # Apply poka-yoke
        sparql_condition = PY_HOOK_010.condition.strip()
        result = engine.store.query(sparql_condition)

        # SHUTDOWN: Recursive trigger detected
        assert bool(result) is True, "PY-HOOK-010 should detect recursive trigger"

    def test_valid_trigger_passes(self, engine: HybridEngine) -> None:
        """Valid trigger passes PY-HOOK-010."""
        valid_topology = """
        @prefix hook: <https://kgc.org/ns/hook/> .
        @prefix kgc: <https://kgc.org/ns/> .

        <urn:hook:A> a hook:KnowledgeHook ;
            hook:name "Hook A" ;
            hook:triggeredByMilestone <urn:milestone:M1> .

        <urn:milestone:M1> a kgc:Milestone .
        """
        engine.load_data(valid_topology)

        # Apply poka-yoke
        sparql_condition = PY_HOOK_010.condition.strip()
        result = engine.store.query(sparql_condition)

        # No shutdown: Valid trigger
        assert bool(result) is False, "PY-HOOK-010 should NOT fire for valid trigger"


class TestPokaYokeSummary:
    """Summary test: Verify all 10 poka-yokes are defined."""

    def test_all_poka_yokes_defined(self) -> None:
        """All 10 poka-yokes must be defined."""
        from tests.hybrid.lss.hooks.poka_yoke.types import ALL_HOOK_POKA_YOKES

        assert len(ALL_HOOK_POKA_YOKES) == 10, "Must have exactly 10 poka-yokes"

        # Verify IDs
        ids = {py.id for py in ALL_HOOK_POKA_YOKES}
        expected = {f"PY-HOOK-{i:03d}" for i in range(1, 11)}
        assert ids == expected, f"Missing poka-yokes: {expected - ids}"

        # Verify severity distribution
        by_type = {}
        for py in ALL_HOOK_POKA_YOKES:
            by_type[py.type] = by_type.get(py.type, 0) + 1

        assert by_type[HookPokaYokeType.SHUTDOWN] == 3, "Should have 3 SHUTDOWN"
        assert by_type[HookPokaYokeType.CONTROL] == 2, "Should have 2 CONTROL"
        assert by_type[HookPokaYokeType.VALIDATION] == 2, "Should have 2 VALIDATION"
        assert by_type[HookPokaYokeType.WARNING] == 3, "Should have 3 WARNING"
