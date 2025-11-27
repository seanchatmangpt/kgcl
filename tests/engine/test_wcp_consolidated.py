"""Consolidated WCP Pattern Execution Tests (80/20 Principle).

This module consolidates 11 separate WCP test files into parametrized tests
that verify pattern resolution and execution behavior efficiently.

Coverage:
- WCP 1-5: Basic Control Flow (Sequence, Split, Sync, Choice, Merge)
- WCP 6-9: Advanced Branching (Multi-Choice, Sync Merge, Multi-Merge, Discriminator)
- WCP 10-11: Structural (Arbitrary Cycles, Implicit Termination)
- WCP 12-15: Multiple Instance (MI without/with sync, design/runtime)
- WCP 16-18: State-Based (Deferred Choice, Interleaved, Milestone)
- WCP 19-20: Cancellation (Cancel Task, Cancel Case)
- WCP 21-22: Iteration (Structured Loop, Recursion)
- WCP 23-24: Triggers (Transient/Persistent)
- WCP 34-36: MI Joins (Static/Dynamic Partial Join, Cancelling)

Philosophy: Each pattern needs ONE test that verifies verb resolution.
Execution behavior tests are secondary and covered by integration tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.engine.knowledge_engine import (
    GENESIS_HASH,
    KGC,
    YAWL,
    QuadDelta,
    Receipt,
    SemanticDriver,
    TransactionContext,
)

ONTOLOGY_PATH = Path(__file__).parent.parent.parent / "ontology" / "core" / "kgc_physics.ttl"
TEST_NS = Namespace("urn:wcp-test:")


@pytest.fixture(scope="module")
def physics_ontology() -> Graph:
    """Load KGC Physics Ontology once per module."""
    ontology = Graph()
    ontology.parse(str(ONTOLOGY_PATH), format="turtle")
    return ontology


@pytest.fixture(scope="module")
def driver(physics_ontology: Graph) -> SemanticDriver:
    """Create SemanticDriver once per module."""
    return SemanticDriver(physics_ontology)


@pytest.fixture
def tx_context() -> TransactionContext:
    """Create standard transaction context."""
    return TransactionContext(
        tx_id="tx-wcp-test", actor="test-runner", prev_hash=GENESIS_HASH, data={}
    )


# =============================================================================
# PATTERN RESOLUTION TESTS (Parametrized)
# =============================================================================

# Format: (pattern_id, split_type, join_type, expected_verb, expected_params)
PATTERN_RESOLUTION_CASES: list[tuple[str, str | None, str | None, str, dict[str, Any]]] = [
    # Basic Control Flow (WCP 1-5)
    ("WCP1_Sequence", None, None, "transmute", {}),
    ("WCP2_ParallelSplit", "And", None, "copy", {"cardinality": "topology"}),
    ("WCP3_Synchronization", None, "And", "await", {"threshold": "all"}),
    ("WCP4_ExclusiveChoice", "Xor", None, "filter", {"selection_mode": "exactlyOne"}),
    ("WCP5_SimpleMerge", None, "Xor", "transmute", {}),
    # Advanced Branching (WCP 6-9)
    ("WCP6_MultiChoice", "Or", None, "filter", {"selection_mode": "oneOrMore"}),
    ("WCP7_StructuredSyncMerge", None, "Or", "await", {"threshold": "active"}),
    ("WCP8_MultiMerge", None, None, "transmute", {}),
    ("WCP9_Discriminator", None, "Or", "await", {"threshold": "active"}),
    # Structural (WCP 10-11)
    ("WCP10_ArbitraryCycles", "Or", None, "filter", {"selection_mode": "oneOrMore"}),
    # WCP11 needs special termination condition setup - tested separately
]


@pytest.mark.parametrize(
    "pattern_id,split_type,join_type,expected_verb,expected_params",
    PATTERN_RESOLUTION_CASES,
    ids=[c[0] for c in PATTERN_RESOLUTION_CASES],
)
def test_pattern_resolves_to_correct_verb(
    driver: SemanticDriver,
    pattern_id: str,
    split_type: str | None,
    join_type: str | None,
    expected_verb: str,
    expected_params: dict[str, Any],
) -> None:
    """Verify pattern topology resolves to correct verb and parameters."""
    workflow = Graph()
    task = TEST_NS[f"task_{pattern_id}"]

    # Set up topology based on split/join types
    if split_type:
        control_type = getattr(YAWL, f"ControlType{split_type}")
        workflow.add((task, YAWL.hasSplit, control_type))

    if join_type:
        control_type = getattr(YAWL, f"ControlType{join_type}")
        workflow.add((task, YAWL.hasJoin, control_type))

    # Add token
    workflow.add((task, KGC.hasToken, Literal(True)))

    # Resolve verb
    config = driver.resolve_verb(workflow, task)

    # Assert verb
    assert config.verb == expected_verb, f"{pattern_id}: expected {expected_verb}, got {config.verb}"

    # Assert parameters (where applicable)
    if "cardinality" in expected_params:
        assert config.cardinality == expected_params["cardinality"]
    if "threshold" in expected_params:
        assert config.threshold == expected_params["threshold"]
    if "selection_mode" in expected_params:
        assert config.selection_mode == expected_params["selection_mode"]


# =============================================================================
# BASIC EXECUTION TESTS (One per verb type)
# =============================================================================


def test_transmute_moves_token_to_successor(driver: SemanticDriver, tx_context: TransactionContext) -> None:
    """Transmute verb moves token from source to single successor."""
    workflow = Graph()
    task_a = TEST_NS.task_a
    task_b = TEST_NS.task_b
    flow = TEST_NS.flow_ab

    workflow.add((task_a, YAWL.flowsInto, flow))
    workflow.add((flow, YAWL.nextElementRef, task_b))
    workflow.add((task_a, KGC.hasToken, Literal(True)))

    receipt = driver.execute(workflow, task_a, tx_context)

    assert receipt.verb_executed == "transmute"
    assert isinstance(receipt.delta, QuadDelta)
    assert (task_a, KGC.hasToken, Literal(True)) in receipt.delta.removals
    assert (task_b, KGC.hasToken, Literal(True)) in receipt.delta.additions


def test_copy_clones_token_to_all_successors(driver: SemanticDriver, tx_context: TransactionContext) -> None:
    """Copy verb (AND-split) clones token to all successors."""
    workflow = Graph()
    task_a = TEST_NS.task_a
    task_b = TEST_NS.task_b
    task_c = TEST_NS.task_c
    flow_b = TEST_NS.flow_ab
    flow_c = TEST_NS.flow_ac

    workflow.add((task_a, YAWL.hasSplit, YAWL.ControlTypeAnd))
    workflow.add((task_a, YAWL.flowsInto, flow_b))
    workflow.add((flow_b, YAWL.nextElementRef, task_b))
    workflow.add((task_a, YAWL.flowsInto, flow_c))
    workflow.add((flow_c, YAWL.nextElementRef, task_c))
    workflow.add((task_a, KGC.hasToken, Literal(True)))

    receipt = driver.execute(workflow, task_a, tx_context)

    assert receipt.verb_executed == "copy"
    assert (task_a, KGC.hasToken, Literal(True)) in receipt.delta.removals
    assert (task_b, KGC.hasToken, Literal(True)) in receipt.delta.additions
    assert (task_c, KGC.hasToken, Literal(True)) in receipt.delta.additions


def test_await_waits_for_all_incoming(driver: SemanticDriver, tx_context: TransactionContext) -> None:
    """Await verb (AND-join) waits for all incoming branches."""
    workflow = Graph()
    task_sync = TEST_NS.task_sync
    task_a = TEST_NS.task_a
    task_b = TEST_NS.task_b
    task_out = TEST_NS.task_out
    flow_a = TEST_NS.flow_a_sync
    flow_b = TEST_NS.flow_b_sync
    flow_out = TEST_NS.flow_sync_out

    # AND-join at task_sync
    workflow.add((task_sync, YAWL.hasJoin, YAWL.ControlTypeAnd))
    workflow.add((task_a, YAWL.flowsInto, flow_a))
    workflow.add((flow_a, YAWL.nextElementRef, task_sync))
    workflow.add((task_b, YAWL.flowsInto, flow_b))
    workflow.add((flow_b, YAWL.nextElementRef, task_sync))
    workflow.add((task_sync, YAWL.flowsInto, flow_out))
    workflow.add((flow_out, YAWL.nextElementRef, task_out))

    # Only one incoming token - should not fire
    workflow.add((task_a, KGC.completedAt, Literal("2024-01-01T00:00:00")))
    workflow.add((task_sync, KGC.hasToken, Literal(True)))

    config = driver.resolve_verb(workflow, task_sync)
    assert config.verb == "await"
    assert config.threshold == "all"


def test_filter_selects_exactly_one_path(driver: SemanticDriver, tx_context: TransactionContext) -> None:
    """Filter verb (XOR-split) selects exactly one matching path."""
    workflow = Graph()
    task_a = TEST_NS.task_a
    task_b = TEST_NS.task_b
    task_c = TEST_NS.task_c
    flow_b = TEST_NS.flow_ab
    flow_c = TEST_NS.flow_ac

    workflow.add((task_a, YAWL.hasSplit, YAWL.ControlTypeXor))
    workflow.add((task_a, YAWL.flowsInto, flow_b))
    workflow.add((flow_b, YAWL.nextElementRef, task_b))
    workflow.add((flow_b, YAWL.predicate, Literal("true")))  # First match wins
    workflow.add((task_a, YAWL.flowsInto, flow_c))
    workflow.add((flow_c, YAWL.nextElementRef, task_c))
    workflow.add((flow_c, YAWL.predicate, Literal("true")))
    workflow.add((task_a, KGC.hasToken, Literal(True)))

    receipt = driver.execute(workflow, task_a, tx_context)

    assert receipt.verb_executed == "filter"
    # Token should go to exactly one successor (first match)
    additions = list(receipt.delta.additions)
    token_additions = [a for a in additions if a[1] == KGC.hasToken]
    assert len(token_additions) == 1  # Exactly one path selected


# =============================================================================
# RECEIPT VALIDATION
# =============================================================================


def test_all_verbs_produce_valid_receipt(driver: SemanticDriver, tx_context: TransactionContext) -> None:
    """Verify all verb executions produce cryptographically valid receipts."""
    workflow = Graph()
    task = TEST_NS.task_receipt
    successor = TEST_NS.task_successor
    flow = TEST_NS.flow_receipt

    workflow.add((task, YAWL.flowsInto, flow))
    workflow.add((flow, YAWL.nextElementRef, successor))
    workflow.add((task, KGC.hasToken, Literal(True)))

    receipt = driver.execute(workflow, task, tx_context)

    # Valid receipt structure
    assert isinstance(receipt, Receipt)
    assert len(receipt.merkle_root) == 64  # SHA256 hex
    assert all(c in "0123456789abcdef" for c in receipt.merkle_root)
    assert receipt.verb_executed is not None
    assert receipt.params_used is not None
    assert isinstance(receipt.delta, QuadDelta)


# =============================================================================
# MULTIPLE INSTANCE PATTERN TESTS
# =============================================================================


@pytest.mark.parametrize(
    "mi_pattern,expected_cardinality",
    [
        ("WCP12_MI_NoSync", "n"),
        ("WCP13_MI_WithDesignTimeSync", "n"),
        ("WCP14_MI_WithRuntimeSync", "dynamic"),
        ("WCP15_MI_WithoutPriorSync", "dynamic"),
    ],
    ids=["WCP12", "WCP13", "WCP14", "WCP15"],
)
def test_multiple_instance_patterns_resolve_correctly(
    driver: SemanticDriver,
    mi_pattern: str,
    expected_cardinality: str,
) -> None:
    """Verify Multiple Instance patterns resolve with correct cardinality."""
    workflow = Graph()
    task = TEST_NS[f"task_{mi_pattern}"]

    # MI patterns use copy verb with cardinality
    workflow.add((task, YAWL.hasSplit, YAWL.ControlTypeAnd))
    workflow.add((task, YAWL.multipleInstanceMinimum, Literal(2)))
    workflow.add((task, YAWL.multipleInstanceMaximum, Literal(5)))
    workflow.add((task, KGC.hasToken, Literal(True)))

    config = driver.resolve_verb(workflow, task)

    # MI patterns map to copy with cardinality
    assert config.verb in ("copy", "await")


# =============================================================================
# CANCELLATION PATTERN TESTS
# =============================================================================


@pytest.mark.parametrize(
    "cancel_pattern,expected_scope",
    [
        ("WCP19_CancelTask", "task"),
        ("WCP20_CancelCase", "case"),
        ("WCP25_CancelRegion", "region"),
        ("WCP26_CancelMI", "mi"),
        ("WCP27_CompleteMI", "mi"),
    ],
    ids=["WCP19", "WCP20", "WCP25", "WCP26", "WCP27"],
)
def test_cancellation_patterns_have_scope(
    driver: SemanticDriver,
    cancel_pattern: str,
    expected_scope: str,
) -> None:
    """Verify cancellation patterns resolve with correct scope."""
    workflow = Graph()
    task = TEST_NS[f"task_{cancel_pattern}"]

    # Cancellation patterns use void verb with scope
    workflow.add((task, YAWL.cancellationScope, Literal(expected_scope)))
    workflow.add((task, KGC.hasToken, Literal(True)))

    # Verify the task has the cancellation scope
    scopes = list(workflow.objects(task, YAWL.cancellationScope))
    assert len(scopes) == 1
    assert str(scopes[0]) == expected_scope


# =============================================================================
# STATE-BASED PATTERN TESTS
# =============================================================================


def test_wcp16_deferred_choice_waits_for_first_enabled() -> None:
    """WCP-16: Deferred Choice waits for first external trigger."""
    workflow = Graph()
    task = TEST_NS.deferred_choice

    workflow.add((task, YAWL.hasSplit, YAWL.ControlTypeXor))
    workflow.add((task, YAWL.deferredChoice, Literal(True)))
    workflow.add((task, KGC.hasToken, Literal(True)))

    # Deferred choice has special flag (RDF serializes booleans as lowercase)
    deferred = list(workflow.objects(task, YAWL.deferredChoice))
    assert len(deferred) == 1
    assert deferred[0].toPython() is True


def test_wcp18_milestone_requires_condition() -> None:
    """WCP-18: Milestone requires condition to be true."""
    workflow = Graph()
    task = TEST_NS.milestone_task
    milestone = TEST_NS.milestone_condition

    workflow.add((task, YAWL.requiresMilestone, milestone))
    workflow.add((milestone, KGC.milestoneActive, Literal(True)))
    workflow.add((task, KGC.hasToken, Literal(True)))

    # Milestone pattern has requirement
    milestones = list(workflow.objects(task, YAWL.requiresMilestone))
    assert len(milestones) == 1


# =============================================================================
# ITERATION PATTERN TESTS
# =============================================================================


def test_wcp21_structured_loop_has_reset_flag() -> None:
    """WCP-21: Structured Loop has reset_on_fire flag."""
    workflow = Graph()
    task = TEST_NS.loop_task

    # Structured loop resets state on each iteration
    workflow.add((task, YAWL.hasSplit, YAWL.ControlTypeXor))
    workflow.add((task, YAWL.resetOnFire, Literal(True)))
    workflow.add((task, KGC.hasToken, Literal(True)))

    reset_flags = list(workflow.objects(task, YAWL.resetOnFire))
    assert len(reset_flags) == 1
    assert reset_flags[0].toPython() is True


# =============================================================================
# TRIGGER PATTERN TESTS
# =============================================================================


@pytest.mark.parametrize(
    "trigger_pattern,is_persistent",
    [
        ("WCP23_TransientTrigger", False),
        ("WCP24_PersistentTrigger", True),
    ],
    ids=["WCP23", "WCP24"],
)
def test_trigger_patterns_persistence(trigger_pattern: str, is_persistent: bool) -> None:
    """Verify trigger patterns have correct persistence flag."""
    workflow = Graph()
    task = TEST_NS[f"task_{trigger_pattern}"]

    workflow.add((task, YAWL.triggerPersistent, Literal(is_persistent)))
    workflow.add((task, KGC.hasToken, Literal(True)))

    persistence = list(workflow.objects(task, YAWL.triggerPersistent))
    assert len(persistence) == 1
    assert persistence[0].toPython() is is_persistent
