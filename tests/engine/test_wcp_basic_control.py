"""Comprehensive tests for YAWL Workflow Control Patterns 1-5 (Basic Control Flow).

Tests verify that the Semantic Driver correctly resolves YAWL patterns to KGC verbs
with appropriate parameters by querying the physics ontology (kgc_physics.ttl).

Patterns Tested:
- WCP-1: Sequence → Transmute
- WCP-2: Parallel Split (AND-split) → Copy(cardinality="topology")
- WCP-3: Synchronization (AND-join) → Await(threshold="all", completionStrategy="waitAll")
- WCP-4: Exclusive Choice (XOR-split) → Filter(selectionMode="exactlyOne")
- WCP-5: Simple Merge (XOR-join) → Transmute

This follows Chicago School TDD: tests verify actual behavior through the engine,
not through mocks. Each test sets up real RDF graphs and executes the full pipeline.
"""

from __future__ import annotations

from pathlib import Path

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
    VerbConfig,
)

# Test fixtures
ONTOLOGY_PATH = Path(__file__).parent.parent.parent / "ontology" / "kgc_physics.ttl"

# Test URIs
TEST_NAMESPACE = Namespace("urn:test:")


@pytest.fixture
def physics_ontology() -> Graph:
    """Load the KGC Physics Ontology for all tests."""
    ontology = Graph()
    ontology.parse(str(ONTOLOGY_PATH), format="turtle")
    return ontology


@pytest.fixture
def driver(physics_ontology: Graph) -> SemanticDriver:
    """Create SemanticDriver with loaded physics ontology."""
    return SemanticDriver(physics_ontology)


@pytest.fixture
def transaction_context() -> TransactionContext:
    """Create standard transaction context for tests."""
    return TransactionContext(tx_id="tx-test-001", actor="test-system", prev_hash=GENESIS_HASH, data={"test": "data"})


# =============================================================================
# WCP-1: SEQUENCE → TRANSMUTE
# =============================================================================


def test_wcp1_sequence_resolves_to_transmute(driver: SemanticDriver) -> None:
    """WCP-1: Simple sequence A→B resolves to Transmute verb.

    Arrange:
        - Workflow with two sequential tasks
        - Task A has token
        - Task A flows to Task B
    Act:
        - Resolve verb for Task A
    Assert:
        - Verb is "transmute"
        - No parameters (Transmute is parameterless)
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    flow = TEST_NAMESPACE.flow_1

    # Set up sequence topology
    workflow.add((task_a, YAWL.flowsInto, flow))
    workflow.add((flow, YAWL.nextElementRef, task_b))
    workflow.add((task_a, KGC.hasToken, Literal(True)))

    config = driver.resolve_verb(workflow, task_a)

    assert config.verb == "transmute"
    assert config.threshold is None
    assert config.cardinality is None
    assert config.selection_mode is None


def test_wcp1_sequence_execution_moves_token(driver: SemanticDriver, transaction_context: TransactionContext) -> None:
    """WCP-1: Transmute execution moves token from A to B.

    Arrange:
        - Workflow with sequence A→B
        - Task A has token
    Act:
        - Execute Task A
    Assert:
        - Receipt shows transmute executed
        - Delta removes token from A
        - Delta adds token to B
        - Task A marked as completed
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    flow = TEST_NAMESPACE.flow_1

    workflow.add((task_a, YAWL.flowsInto, flow))
    workflow.add((flow, YAWL.nextElementRef, task_b))
    workflow.add((task_a, KGC.hasToken, Literal(True)))

    receipt = driver.execute(workflow, task_a, transaction_context)

    assert receipt.verb_executed == "transmute"
    assert isinstance(receipt.delta, QuadDelta)
    assert (task_a, KGC.hasToken, Literal(True)) in receipt.delta.removals
    assert (task_b, KGC.hasToken, Literal(True)) in receipt.delta.additions
    assert any(task_a == triple[0] and KGC.completedAt == triple[1] for triple in receipt.delta.additions)


def test_wcp1_sequence_produces_valid_receipt(driver: SemanticDriver, transaction_context: TransactionContext) -> None:
    """WCP-1: Execution produces cryptographically valid receipt.

    Arrange:
        - Workflow with sequence A→B
    Act:
        - Execute Task A
    Assert:
        - Receipt has merkle_root (64 hex chars)
        - Receipt includes verb and delta
        - Receipt.params_used includes VerbConfig
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    flow = TEST_NAMESPACE.flow_1

    workflow.add((task_a, YAWL.flowsInto, flow))
    workflow.add((flow, YAWL.nextElementRef, task_b))
    workflow.add((task_a, KGC.hasToken, Literal(True)))

    receipt = driver.execute(workflow, task_a, transaction_context)

    assert isinstance(receipt, Receipt)
    assert len(receipt.merkle_root) == 64  # SHA256 hex digest
    assert all(c in "0123456789abcdef" for c in receipt.merkle_root)
    assert receipt.verb_executed == "transmute"
    assert receipt.params_used is not None
    assert receipt.params_used.verb == "transmute"


# =============================================================================
# WCP-2: PARALLEL SPLIT (AND-SPLIT) → COPY
# =============================================================================


def test_wcp2_parallel_split_resolves_to_copy(driver: SemanticDriver) -> None:
    """WCP-2: AND-split resolves to Copy with cardinality=topology.

    Arrange:
        - Task A with yawl:hasSplit = yawl:ControlTypeAnd
        - Task A flows to Task B and Task C
    Act:
        - Resolve verb for Task A
    Assert:
        - Verb is "copy"
        - cardinality is "topology"
        - No threshold or selection_mode
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2

    # Set up AND-split topology
    workflow.add((task_a, YAWL.hasSplit, YAWL.ControlTypeAnd))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_b))
    workflow.add((task_a, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))
    workflow.add((task_a, KGC.hasToken, Literal(True)))

    config = driver.resolve_verb(workflow, task_a)

    assert config.verb == "copy"
    assert config.cardinality == "topology"
    assert config.threshold is None
    assert config.selection_mode is None


def test_wcp2_parallel_split_execution_clones_to_all_successors(
    driver: SemanticDriver, transaction_context: TransactionContext
) -> None:
    """WCP-2: Copy execution clones token to ALL successors.

    Arrange:
        - Task A with AND-split to B, C, D
    Act:
        - Execute Task A
    Assert:
        - Receipt shows copy executed
        - Delta removes token from A
        - Delta adds token to B, C, and D
        - All three successors receive tokens
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    task_d = TEST_NAMESPACE.task_d
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2
    flow_3 = TEST_NAMESPACE.flow_3

    workflow.add((task_a, YAWL.hasSplit, YAWL.ControlTypeAnd))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_b))
    workflow.add((task_a, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))
    workflow.add((task_a, YAWL.flowsInto, flow_3))
    workflow.add((flow_3, YAWL.nextElementRef, task_d))
    workflow.add((task_a, KGC.hasToken, Literal(True)))

    receipt = driver.execute(workflow, task_a, transaction_context)

    assert receipt.verb_executed == "copy"
    assert (task_a, KGC.hasToken, Literal(True)) in receipt.delta.removals
    assert (task_b, KGC.hasToken, Literal(True)) in receipt.delta.additions
    assert (task_c, KGC.hasToken, Literal(True)) in receipt.delta.additions
    assert (task_d, KGC.hasToken, Literal(True)) in receipt.delta.additions


def test_wcp2_parallel_split_with_two_branches(driver: SemanticDriver, transaction_context: TransactionContext) -> None:
    """WCP-2: AND-split with exactly 2 branches creates 2 tokens.

    Arrange:
        - Task A with AND-split to B and C only
    Act:
        - Execute Task A
    Assert:
        - Token removed from A
        - Tokens added to B and C only
        - Task A marked completed
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2

    workflow.add((task_a, YAWL.hasSplit, YAWL.ControlTypeAnd))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_b))
    workflow.add((task_a, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))
    workflow.add((task_a, KGC.hasToken, Literal(True)))

    receipt = driver.execute(workflow, task_a, transaction_context)

    assert receipt.verb_executed == "copy"
    # Verify exactly 2 tokens created
    token_additions = [t for t in receipt.delta.additions if t[1] == KGC.hasToken]
    assert len(token_additions) == 2
    assert (task_b, KGC.hasToken, Literal(True)) in token_additions
    assert (task_c, KGC.hasToken, Literal(True)) in token_additions


# =============================================================================
# WCP-3: SYNCHRONIZATION (AND-JOIN) → AWAIT
# =============================================================================


def test_wcp3_synchronization_resolves_to_await_all(driver: SemanticDriver) -> None:
    """WCP-3: AND-join resolves to Await with threshold='all'.

    Arrange:
        - Task C with yawl:hasJoin = yawl:ControlTypeAnd
        - Tasks A and B flow to Task C
    Act:
        - Resolve verb for Task C
    Assert:
        - Verb is "await"
        - threshold is "all"
        - completionStrategy is "waitAll"
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2

    # Set up AND-join topology
    workflow.add((task_c, YAWL.hasJoin, YAWL.ControlTypeAnd))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_c))
    workflow.add((task_b, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))

    config = driver.resolve_verb(workflow, task_c)

    assert config.verb == "await"
    assert config.threshold == "all"
    assert config.completion_strategy == "waitAll"


def test_wcp3_synchronization_waits_for_all_branches(
    driver: SemanticDriver, transaction_context: TransactionContext
) -> None:
    """WCP-3: Await does NOT fire until ALL branches complete.

    Arrange:
        - Task C with AND-join from A and B
        - Only Task A completed (not B)
    Act:
        - Execute Task C
    Assert:
        - Receipt shows await executed
        - Delta is empty (no token added to C yet)
        - Task C does not have token
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2

    workflow.add((task_c, YAWL.hasJoin, YAWL.ControlTypeAnd))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_c))
    workflow.add((task_b, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))
    # Only A completed
    workflow.add((task_a, KGC.completedAt, Literal("tx-prev")))

    receipt = driver.execute(workflow, task_c, transaction_context)

    assert receipt.verb_executed == "await"
    # No token added yet (waiting for B)
    assert (task_c, KGC.hasToken, Literal(True)) not in receipt.delta.additions


def test_wcp3_synchronization_fires_when_all_complete(
    driver: SemanticDriver, transaction_context: TransactionContext
) -> None:
    """WCP-3: Await fires when ALL incoming branches complete.

    Arrange:
        - Task C with AND-join from A and B
        - Both A and B completed
    Act:
        - Execute Task C
    Assert:
        - Receipt shows await executed
        - Delta adds token to C
        - Task C marked as completed
        - Threshold achieved recorded
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2

    workflow.add((task_c, YAWL.hasJoin, YAWL.ControlTypeAnd))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_c))
    workflow.add((task_b, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))
    # Both A and B completed
    workflow.add((task_a, KGC.completedAt, Literal("tx-1")))
    workflow.add((task_b, KGC.completedAt, Literal("tx-2")))

    receipt = driver.execute(workflow, task_c, transaction_context)

    assert receipt.verb_executed == "await"
    assert (task_c, KGC.hasToken, Literal(True)) in receipt.delta.additions
    assert any(task_c == triple[0] and KGC.completedAt == triple[1] for triple in receipt.delta.additions)
    assert any(task_c == triple[0] and KGC.thresholdAchieved == triple[1] for triple in receipt.delta.additions)


def test_wcp3_synchronization_three_branches(driver: SemanticDriver, transaction_context: TransactionContext) -> None:
    """WCP-3: AND-join with 3 branches waits for all 3.

    Arrange:
        - Task D with AND-join from A, B, C
        - All three completed
    Act:
        - Execute Task D
    Assert:
        - Task D receives token
        - Threshold achieved = 3
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    task_d = TEST_NAMESPACE.task_d
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2
    flow_3 = TEST_NAMESPACE.flow_3

    workflow.add((task_d, YAWL.hasJoin, YAWL.ControlTypeAnd))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_d))
    workflow.add((task_b, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_d))
    workflow.add((task_c, YAWL.flowsInto, flow_3))
    workflow.add((flow_3, YAWL.nextElementRef, task_d))
    workflow.add((task_a, KGC.completedAt, Literal("tx-1")))
    workflow.add((task_b, KGC.completedAt, Literal("tx-2")))
    workflow.add((task_c, KGC.completedAt, Literal("tx-3")))

    receipt = driver.execute(workflow, task_d, transaction_context)

    assert receipt.verb_executed == "await"
    assert (task_d, KGC.hasToken, Literal(True)) in receipt.delta.additions
    # Check threshold achieved
    threshold_triples = [t for t in receipt.delta.additions if t[1] == KGC.thresholdAchieved]
    assert len(threshold_triples) == 1
    assert str(threshold_triples[0][2]) == "3"


# =============================================================================
# WCP-4: EXCLUSIVE CHOICE (XOR-SPLIT) → FILTER
# =============================================================================


def test_wcp4_exclusive_choice_resolves_to_filter_exactly_one(driver: SemanticDriver) -> None:
    """WCP-4: XOR-split resolves to Filter with selectionMode='exactlyOne'.

    Arrange:
        - Task A with yawl:hasSplit = yawl:ControlTypeXor
        - Task A flows to B or C (with predicates)
    Act:
        - Resolve verb for Task A
    Assert:
        - Verb is "filter"
        - selectionMode is "exactlyOne"
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2

    # Set up XOR-split topology
    workflow.add((task_a, YAWL.hasSplit, YAWL.ControlTypeXor))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_b))
    workflow.add((task_a, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))

    config = driver.resolve_verb(workflow, task_a)

    assert config.verb == "filter"
    assert config.selection_mode == "exactlyOne"


def test_wcp4_exclusive_choice_selects_first_matching_path(
    driver: SemanticDriver, transaction_context: TransactionContext
) -> None:
    """WCP-4: Filter with exactlyOne selects first matching path only.

    Arrange:
        - Task A with XOR-split to B and C
        - Flow to B has predicate "data['x'] > 5"
        - Flow to C has predicate "data['x'] <= 5"
        - Context data has x=10
    Act:
        - Execute Task A
    Assert:
        - Receipt shows filter executed
        - Token removed from A
        - Token added ONLY to B (first match)
        - No token to C
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2
    pred_1 = TEST_NAMESPACE.predicate_1
    pred_2 = TEST_NAMESPACE.predicate_2

    workflow.add((task_a, YAWL.hasSplit, YAWL.ControlTypeXor))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_b))
    workflow.add((flow_1, YAWL.hasPredicate, pred_1))
    workflow.add((pred_1, YAWL.query, Literal("data['x'] > 5")))
    workflow.add((pred_1, YAWL.ordering, Literal(1)))

    workflow.add((task_a, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))
    workflow.add((flow_2, YAWL.hasPredicate, pred_2))
    workflow.add((pred_2, YAWL.query, Literal("data['x'] <= 5")))
    workflow.add((pred_2, YAWL.ordering, Literal(2)))

    workflow.add((task_a, KGC.hasToken, Literal(True)))

    # Context with x=10 (matches first predicate)
    ctx = TransactionContext(tx_id="tx-001", actor="test", prev_hash=GENESIS_HASH, data={"x": 10})
    receipt = driver.execute(workflow, task_a, ctx)

    assert receipt.verb_executed == "filter"
    assert (task_a, KGC.hasToken, Literal(True)) in receipt.delta.removals
    assert (task_b, KGC.hasToken, Literal(True)) in receipt.delta.additions
    assert (task_c, KGC.hasToken, Literal(True)) not in receipt.delta.additions


def test_wcp4_exclusive_choice_uses_default_path(
    driver: SemanticDriver, transaction_context: TransactionContext
) -> None:
    """WCP-4: Filter uses default path when no predicates match.

    Arrange:
        - Task A with XOR-split to B and C
        - Flow to B has predicate "data['x'] > 100"
        - Flow to C is default (yawl:isDefaultFlow = true)
        - Context data has x=10 (no match)
    Act:
        - Execute Task A
    Assert:
        - Token goes to C (default path)
        - No token to B
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2
    pred_1 = TEST_NAMESPACE.predicate_1

    workflow.add((task_a, YAWL.hasSplit, YAWL.ControlTypeXor))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_b))
    workflow.add((flow_1, YAWL.hasPredicate, pred_1))
    workflow.add((pred_1, YAWL.query, Literal("data['x'] > 100")))
    workflow.add((pred_1, YAWL.ordering, Literal(1)))

    workflow.add((task_a, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))
    workflow.add((flow_2, YAWL.isDefaultFlow, Literal(True)))

    workflow.add((task_a, KGC.hasToken, Literal(True)))

    ctx = TransactionContext(tx_id="tx-001", actor="test", prev_hash=GENESIS_HASH, data={"x": 10})
    receipt = driver.execute(workflow, task_a, ctx)

    assert receipt.verb_executed == "filter"
    assert (task_b, KGC.hasToken, Literal(True)) not in receipt.delta.additions
    assert (task_c, KGC.hasToken, Literal(True)) in receipt.delta.additions


def test_wcp4_exclusive_choice_stops_at_first_match(
    driver: SemanticDriver, transaction_context: TransactionContext
) -> None:
    """WCP-4: Filter with exactlyOne stops after first match even if others match.

    Arrange:
        - Task A with XOR-split to B, C, D
        - All three flows have predicates that WOULD match
        - Ordering: B(1), C(2), D(3)
    Act:
        - Execute Task A
    Assert:
        - Token ONLY to B (first in ordering)
        - No tokens to C or D
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    task_d = TEST_NAMESPACE.task_d
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2
    flow_3 = TEST_NAMESPACE.flow_3
    pred_1 = TEST_NAMESPACE.predicate_1
    pred_2 = TEST_NAMESPACE.predicate_2
    pred_3 = TEST_NAMESPACE.predicate_3

    workflow.add((task_a, YAWL.hasSplit, YAWL.ControlTypeXor))

    # All predicates will match
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_b))
    workflow.add((flow_1, YAWL.hasPredicate, pred_1))
    workflow.add((pred_1, YAWL.query, Literal("data['x'] > 0")))
    workflow.add((pred_1, YAWL.ordering, Literal(1)))

    workflow.add((task_a, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))
    workflow.add((flow_2, YAWL.hasPredicate, pred_2))
    workflow.add((pred_2, YAWL.query, Literal("data['x'] > 0")))
    workflow.add((pred_2, YAWL.ordering, Literal(2)))

    workflow.add((task_a, YAWL.flowsInto, flow_3))
    workflow.add((flow_3, YAWL.nextElementRef, task_d))
    workflow.add((flow_3, YAWL.hasPredicate, pred_3))
    workflow.add((pred_3, YAWL.query, Literal("data['x'] > 0")))
    workflow.add((pred_3, YAWL.ordering, Literal(3)))

    workflow.add((task_a, KGC.hasToken, Literal(True)))

    ctx = TransactionContext(tx_id="tx-001", actor="test", prev_hash=GENESIS_HASH, data={"x": 10})
    receipt = driver.execute(workflow, task_a, ctx)

    assert receipt.verb_executed == "filter"
    # Only B gets token
    token_additions = [t for t in receipt.delta.additions if t[1] == KGC.hasToken]
    assert len(token_additions) == 1
    assert (task_b, KGC.hasToken, Literal(True)) in token_additions


# =============================================================================
# WCP-5: SIMPLE MERGE (XOR-JOIN) → TRANSMUTE
# =============================================================================


def test_wcp5_simple_merge_resolves_to_transmute(driver: SemanticDriver) -> None:
    """WCP-5: XOR-join resolves to Transmute (first arrival continues).

    Arrange:
        - Task C with yawl:hasJoin = yawl:ControlTypeXor
        - Tasks A and B can flow to Task C
    Act:
        - Resolve verb for Task C
    Assert:
        - Verb is "transmute"
        - No synchronization parameters
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2

    # Set up XOR-join topology
    workflow.add((task_c, YAWL.hasJoin, YAWL.ControlTypeXor))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_c))
    workflow.add((task_b, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))

    config = driver.resolve_verb(workflow, task_c)

    assert config.verb == "transmute"
    assert config.threshold is None
    assert config.completion_strategy is None


def test_wcp5_simple_merge_first_arrival_continues(
    driver: SemanticDriver, transaction_context: TransactionContext
) -> None:
    """WCP-5: Transmute fires on first arrival without waiting.

    Arrange:
        - Task C with XOR-join from A or B
        - Task C has token (arrived from A)
        - Task C flows to Task D
    Act:
        - Execute Task C
    Assert:
        - Token moves from C to D
        - No synchronization delay
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    task_d = TEST_NAMESPACE.task_d
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2
    flow_3 = TEST_NAMESPACE.flow_3

    workflow.add((task_c, YAWL.hasJoin, YAWL.ControlTypeXor))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_c))
    workflow.add((task_b, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))
    # C flows to D
    workflow.add((task_c, YAWL.flowsInto, flow_3))
    workflow.add((flow_3, YAWL.nextElementRef, task_d))
    # C has token (arrived from A)
    workflow.add((task_c, KGC.hasToken, Literal(True)))

    receipt = driver.execute(workflow, task_c, transaction_context)

    assert receipt.verb_executed == "transmute"
    assert (task_c, KGC.hasToken, Literal(True)) in receipt.delta.removals
    assert (task_d, KGC.hasToken, Literal(True)) in receipt.delta.additions


def test_wcp5_simple_merge_handles_multiple_arrivals(
    driver: SemanticDriver, transaction_context: TransactionContext
) -> None:
    """WCP-5: Simple merge allows multiple arrivals (multi-merge behavior).

    Arrange:
        - Task C with XOR-join from A and B
        - First arrival: Execute C → moves to D
        - Second arrival: Execute C again → moves to D again
    Act:
        - Execute Task C twice
    Assert:
        - Both executions succeed
        - Each creates separate token on D
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    task_d = TEST_NAMESPACE.task_d
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2
    flow_3 = TEST_NAMESPACE.flow_3

    workflow.add((task_c, YAWL.hasJoin, YAWL.ControlTypeXor))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_c))
    workflow.add((task_b, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))
    workflow.add((task_c, YAWL.flowsInto, flow_3))
    workflow.add((flow_3, YAWL.nextElementRef, task_d))

    # First arrival
    workflow.add((task_c, KGC.hasToken, Literal(True)))
    receipt_1 = driver.execute(workflow, task_c, transaction_context)

    assert receipt_1.verb_executed == "transmute"
    assert (task_d, KGC.hasToken, Literal(True)) in receipt_1.delta.additions

    # Second arrival (graph now has token on D from first execution)
    workflow.add((task_c, KGC.hasToken, Literal(True)))
    receipt_2 = driver.execute(
        workflow, task_c, TransactionContext(tx_id="tx-002", actor="test", prev_hash=receipt_1.merkle_root, data={})
    )

    assert receipt_2.verb_executed == "transmute"
    assert (task_d, KGC.hasToken, Literal(True)) in receipt_2.delta.additions


def test_wcp5_simple_merge_no_synchronization_required(
    driver: SemanticDriver, transaction_context: TransactionContext
) -> None:
    """WCP-5: XOR-join does not require all sources to complete.

    Arrange:
        - Task C with XOR-join from A and B
        - Only A completed, B not completed
        - Token on C
    Act:
        - Execute Task C
    Assert:
        - Execution succeeds (no waiting for B)
        - Token moves to next task
    """
    workflow = Graph()
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    task_d = TEST_NAMESPACE.task_d
    flow_1 = TEST_NAMESPACE.flow_1
    flow_2 = TEST_NAMESPACE.flow_2
    flow_3 = TEST_NAMESPACE.flow_3

    workflow.add((task_c, YAWL.hasJoin, YAWL.ControlTypeXor))
    workflow.add((task_a, YAWL.flowsInto, flow_1))
    workflow.add((flow_1, YAWL.nextElementRef, task_c))
    workflow.add((task_b, YAWL.flowsInto, flow_2))
    workflow.add((flow_2, YAWL.nextElementRef, task_c))
    workflow.add((task_c, YAWL.flowsInto, flow_3))
    workflow.add((flow_3, YAWL.nextElementRef, task_d))

    # Only A completed
    workflow.add((task_a, KGC.completedAt, Literal("tx-1")))
    # B not completed
    workflow.add((task_c, KGC.hasToken, Literal(True)))

    receipt = driver.execute(workflow, task_c, transaction_context)

    assert receipt.verb_executed == "transmute"
    assert (task_c, KGC.hasToken, Literal(True)) in receipt.delta.removals
    assert (task_d, KGC.hasToken, Literal(True)) in receipt.delta.additions
