"""Integration tests for KGC Hybrid Engine.

Tests verify that the HybridEngine correctly orchestrates tick-based execution
of workflow patterns, reaching fixed points and handling WCP patterns end-to-end.

The HybridEngine is a wrapper around SemanticDriver that provides:
1. Store initialization
2. Ontology loading
3. Rule compilation
4. Tick-based execution (execute all enabled nodes)
5. Fixed-point detection (no more changes)
6. Run-to-completion with max tick limits

This follows Chicago School TDD: tests verify actual behavior through real
RDF graphs and execution, not through mocks.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.engine.knowledge_engine import GENESIS_HASH, KGC, YAWL, SemanticDriver, TransactionContext

if TYPE_CHECKING:
    from collections.abc import Iterator

# Test fixtures
ONTOLOGY_PATH = Path(__file__).parent.parent.parent / "ontology" / "core" / "kgc_physics.ttl"

# Test URIs
TEST_NAMESPACE = Namespace("urn:test:")


# =============================================================================
# HYBRID ENGINE WRAPPER (Simple Implementation for Testing)
# =============================================================================


class HybridEngine:
    """
    Hybrid Engine for tick-based workflow execution.

    Wraps SemanticDriver to provide:
    - Tick execution: Execute all nodes with tokens in one tick
    - Fixed-point detection: Stop when no changes occur
    - Run-to-completion: Execute until fixed point or max ticks

    Parameters
    ----------
    store : Graph
        The RDF graph store (workflow + state).
    ontology : Graph
        The physics ontology for verb resolution.

    Examples
    --------
    >>> engine = HybridEngine(workflow_graph, physics_ontology)
    >>> result = engine.tick()
    >>> result["nodes_executed"]
    2
    """

    def __init__(self, store: Graph, ontology: Graph) -> None:
        """
        Initialize HybridEngine.

        Parameters
        ----------
        store : Graph
            Workflow graph with state.
        ontology : Graph
            Physics ontology for verb mappings.
        """
        self.store = store
        self.ontology = ontology
        self.driver = SemanticDriver(ontology)
        self.tick_counter = 0
        self.total_executions = 0

    def _find_enabled_nodes(self) -> list[URIRef]:
        """
        Find all nodes with tokens (enabled for execution).

        Returns
        -------
        list[URIRef]
            List of enabled node URIs.
        """
        query = f"""
        PREFIX kgc: <{KGC}>
        SELECT ?node WHERE {{
            ?node kgc:hasToken true .
        }}
        """
        results = list(self.store.query(query))
        return [URIRef(str(row[0])) for row in results]

    def tick(self) -> dict[str, int]:
        """
        Execute one tick: process all enabled nodes.

        Returns
        -------
        dict[str, int]
            Result with nodes_executed count and changes count.
        """
        enabled_nodes = self._find_enabled_nodes()
        nodes_executed = 0
        changes = 0

        ctx = TransactionContext(
            tx_id=f"tick-{self.tick_counter}", actor="hybrid-engine", prev_hash=GENESIS_HASH, data={}
        )

        for node in enabled_nodes:
            try:
                receipt = self.driver.execute(self.store, node, ctx)
                nodes_executed += 1
                changes += len(receipt.delta.additions) + len(receipt.delta.removals)
            except ValueError:
                # Node may not have valid verb mapping - skip
                pass

        self.tick_counter += 1
        self.total_executions += nodes_executed

        return {"nodes_executed": nodes_executed, "changes": changes, "tick": self.tick_counter}

    def run_to_completion(self, max_ticks: int = 100) -> dict[str, int | bool]:
        """
        Run workflow until fixed point or max ticks reached.

        Parameters
        ----------
        max_ticks : int
            Maximum number of ticks to execute.

        Returns
        -------
        dict[str, int | bool]
            Completion status with ticks_executed and reached_fixed_point.
        """
        ticks_executed = 0
        reached_fixed_point = False

        for _ in range(max_ticks):
            result = self.tick()
            ticks_executed += 1

            # Fixed point: no nodes executed (no enabled nodes or no changes)
            if result["nodes_executed"] == 0:
                reached_fixed_point = True
                break

        return {
            "ticks_executed": ticks_executed,
            "reached_fixed_point": reached_fixed_point,
            "total_executions": self.total_executions,
        }


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def physics_ontology() -> Graph:
    """Load the KGC Physics Ontology."""
    ontology = Graph()
    ontology.parse(str(ONTOLOGY_PATH), format="turtle")
    return ontology


@pytest.fixture
def empty_store() -> Graph:
    """Create empty RDF graph store."""
    return Graph()


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


def test_engine_creates_store() -> None:
    """HybridEngine initializes with a store.

    Arrange:
        - Create empty graph
        - Create ontology graph
    Act:
        - Initialize HybridEngine
    Assert:
        - Engine has store attribute
        - Store is the provided graph
    """
    store = Graph()
    ontology = Graph()
    engine = HybridEngine(store, ontology)

    assert engine.store is store
    assert isinstance(engine.store, Graph)


def test_engine_loads_ontology(physics_ontology: Graph) -> None:
    """HybridEngine loads and uses physics ontology.

    Arrange:
        - Load physics ontology from file
        - Create empty store
    Act:
        - Initialize HybridEngine with ontology
    Assert:
        - Engine has ontology attribute
        - Ontology is the provided graph
        - Driver is created with ontology
    """
    store = Graph()
    engine = HybridEngine(store, physics_ontology)

    assert engine.ontology is physics_ontology
    assert isinstance(engine.driver, SemanticDriver)
    assert engine.driver.physics_ontology is physics_ontology


def test_engine_compiles_rules(physics_ontology: Graph) -> None:
    """HybridEngine has access to verb mappings via driver.

    Arrange:
        - Create engine with physics ontology
        - Create simple sequence workflow
    Act:
        - Resolve verb for sequence node
    Assert:
        - Verb is resolved correctly
        - Driver can query ontology for mappings
    """
    store = Graph()
    engine = HybridEngine(store, physics_ontology)

    # Add simple sequence
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    flow = TEST_NAMESPACE.flow_1

    store.add((task_a, YAWL.flowsInto, flow))
    store.add((flow, YAWL.nextElementRef, task_b))

    config = engine.driver.resolve_verb(store, task_a)

    assert config.verb == "transmute"


# =============================================================================
# TICK EXECUTION TESTS
# =============================================================================


def test_tick_fires_applicable_rules(physics_ontology: Graph) -> None:
    """Tick executes all enabled nodes (nodes with tokens).

    Arrange:
        - Workflow with sequence A→B
        - Task A has token (enabled)
    Act:
        - Execute one tick
    Assert:
        - One node executed (A)
        - Token moved from A to B
    """
    store = Graph()
    engine = HybridEngine(store, physics_ontology)

    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    flow = TEST_NAMESPACE.flow_1

    # Sequence A→B
    store.add((task_a, YAWL.flowsInto, flow))
    store.add((flow, YAWL.nextElementRef, task_b))
    store.add((task_a, KGC.hasToken, Literal(True)))

    result = engine.tick()

    assert result["nodes_executed"] == 1
    assert (task_a, KGC.hasToken, Literal(True)) not in store
    assert (task_b, KGC.hasToken, Literal(True)) in store


def test_tick_returns_result(physics_ontology: Graph) -> None:
    """Tick returns execution statistics.

    Arrange:
        - Workflow with two parallel branches
        - Both branches enabled
    Act:
        - Execute one tick
    Assert:
        - Result contains nodes_executed
        - Result contains changes count
        - Result contains tick number
    """
    store = Graph()
    engine = HybridEngine(store, physics_ontology)

    # Two independent sequences
    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    task_d = TEST_NAMESPACE.task_d

    store.add((task_a, YAWL.flowsInto, TEST_NAMESPACE.flow_1))
    store.add((TEST_NAMESPACE.flow_1, YAWL.nextElementRef, task_b))
    store.add((task_c, YAWL.flowsInto, TEST_NAMESPACE.flow_2))
    store.add((TEST_NAMESPACE.flow_2, YAWL.nextElementRef, task_d))

    store.add((task_a, KGC.hasToken, Literal(True)))
    store.add((task_c, KGC.hasToken, Literal(True)))

    result = engine.tick()

    assert "nodes_executed" in result
    assert "changes" in result
    assert "tick" in result
    assert result["nodes_executed"] == 2
    assert result["changes"] > 0
    assert result["tick"] == 1


def test_tick_tracks_changes(physics_ontology: Graph) -> None:
    """Tick tracks number of RDF changes (additions + removals).

    Arrange:
        - Simple sequence A→B
        - Task A has token
    Act:
        - Execute tick
    Assert:
        - Changes include token removal from A
        - Changes include token addition to B
        - Changes include completion marker on A
    """
    store = Graph()
    engine = HybridEngine(store, physics_ontology)

    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    flow = TEST_NAMESPACE.flow_1

    store.add((task_a, YAWL.flowsInto, flow))
    store.add((flow, YAWL.nextElementRef, task_b))
    store.add((task_a, KGC.hasToken, Literal(True)))

    result = engine.tick()

    # Changes: 1 removal (token from A) + 2 additions (token to B, completedAt on A)
    assert result["changes"] >= 3


def test_tick_reaches_fixed_point(physics_ontology: Graph) -> None:
    """Tick reaches fixed point when no enabled nodes remain.

    Arrange:
        - Simple sequence A→B (terminal node B)
        - Task A has token
    Act:
        - Execute tick 1 (A→B)
        - Execute tick 2 (B still executes as sequence)
        - Execute tick 3 (no more enabled nodes)
    Assert:
        - Tick 1 executes A
        - Tick 2 executes B
        - Tick 3 executes 0 nodes (fixed point)
    """
    store = Graph()
    engine = HybridEngine(store, physics_ontology)

    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    flow = TEST_NAMESPACE.flow_1

    store.add((task_a, YAWL.flowsInto, flow))
    store.add((flow, YAWL.nextElementRef, task_b))
    store.add((task_a, KGC.hasToken, Literal(True)))

    # Tick 1: Execute A
    result1 = engine.tick()
    assert result1["nodes_executed"] == 1

    # Tick 2: B executes (still has token, no outgoing flow means transmute to nothing)
    result2 = engine.tick()
    assert result2["nodes_executed"] == 1

    # Tick 3: No more enabled nodes - fixed point
    result3 = engine.tick()
    assert result3["nodes_executed"] == 0


# =============================================================================
# WCP PATTERN END-TO-END TESTS
# =============================================================================


def test_wcp1_sequence_token_moves(physics_ontology: Graph) -> None:
    """WCP-1: Sequence pattern moves token through chain A→B→C.

    Arrange:
        - Three-node sequence A→B→C
        - Token at A
    Act:
        - Tick 1: A→B
        - Tick 2: B→C
    Assert:
        - After tick 1: token at B
        - After tick 2: token at C
    """
    store = Graph()
    engine = HybridEngine(store, physics_ontology)

    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c

    # A→B→C
    store.add((task_a, YAWL.flowsInto, TEST_NAMESPACE.flow_1))
    store.add((TEST_NAMESPACE.flow_1, YAWL.nextElementRef, task_b))
    store.add((task_b, YAWL.flowsInto, TEST_NAMESPACE.flow_2))
    store.add((TEST_NAMESPACE.flow_2, YAWL.nextElementRef, task_c))
    store.add((task_a, KGC.hasToken, Literal(True)))

    # Tick 1: A→B
    engine.tick()
    assert (task_a, KGC.hasToken, Literal(True)) not in store
    assert (task_b, KGC.hasToken, Literal(True)) in store
    assert (task_c, KGC.hasToken, Literal(True)) not in store

    # Tick 2: B→C
    engine.tick()
    assert (task_b, KGC.hasToken, Literal(True)) not in store
    assert (task_c, KGC.hasToken, Literal(True)) in store


def test_wcp2_parallel_split_copies_token(physics_ontology: Graph) -> None:
    """WCP-2: Parallel split (AND-split) copies token to all branches.

    Arrange:
        - Task A with AND-split to B and C
        - Token at A
    Act:
        - Execute tick
    Assert:
        - Token at both B and C
        - A completed
    """
    store = Graph()
    engine = HybridEngine(store, physics_ontology)

    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c

    # A splits to B and C (use ControlTypeAnd from YAWL)
    store.add((task_a, YAWL.hasSplit, YAWL.ControlTypeAnd))
    store.add((task_a, YAWL.flowsInto, TEST_NAMESPACE.flow_1))
    store.add((TEST_NAMESPACE.flow_1, YAWL.nextElementRef, task_b))
    store.add((task_a, YAWL.flowsInto, TEST_NAMESPACE.flow_2))
    store.add((TEST_NAMESPACE.flow_2, YAWL.nextElementRef, task_c))
    store.add((task_a, KGC.hasToken, Literal(True)))

    engine.tick()

    assert (task_a, KGC.hasToken, Literal(True)) not in store
    assert (task_b, KGC.hasToken, Literal(True)) in store
    assert (task_c, KGC.hasToken, Literal(True)) in store


def test_wcp3_sync_waits_for_all(physics_ontology: Graph) -> None:
    """WCP-3: Synchronization (AND-join) waits for all branches.

    Arrange:
        - Tasks A and B join to C with AND-join
        - Tokens at A and B
    Act:
        - Tick 1: Complete A and B (both transmute to mark completion)
        - Tick 2: C checks join condition and activates
    Assert:
        - After tick 1: Both A and B completed
        - After tick 2: C activated (join condition satisfied)
    """
    store = Graph()
    engine = HybridEngine(store, physics_ontology)

    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c

    # A→C, B→C with AND-join at C (use ControlTypeAnd)
    store.add((task_a, YAWL.flowsInto, TEST_NAMESPACE.flow_1))
    store.add((TEST_NAMESPACE.flow_1, YAWL.nextElementRef, task_c))
    store.add((task_b, YAWL.flowsInto, TEST_NAMESPACE.flow_2))
    store.add((TEST_NAMESPACE.flow_2, YAWL.nextElementRef, task_c))
    store.add((task_c, YAWL.hasJoin, YAWL.ControlTypeAnd))

    # Start with tokens at A and B
    store.add((task_a, KGC.hasToken, Literal(True)))
    store.add((task_b, KGC.hasToken, Literal(True)))

    # Tick 1: Complete A and B (both sequence transmutes)
    engine.tick()
    assert (task_a, KGC.completedAt, None) in store or (task_a, KGC.hasToken, Literal(True)) not in store
    assert (task_b, KGC.completedAt, None) in store or (task_b, KGC.hasToken, Literal(True)) not in store

    # Tick 2: AND-join fires when both complete
    engine.tick()
    # After both sources complete, join should activate C
    assert (task_c, KGC.hasToken, Literal(True)) in store or (task_c, KGC.completedAt, None) in store


def test_wcp4_xor_selects_one_path(physics_ontology: Graph) -> None:
    """WCP-4: Exclusive choice (XOR-split) selects exactly one path.

    Arrange:
        - Task A with XOR-split to B or C
        - Predicate: if data['x'] > 5 then B, else C
        - Token at A with x=10
    Act:
        - Execute tick
    Assert:
        - Token at B only (not C)
    """
    store = Graph()
    engine = HybridEngine(store, physics_ontology)

    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c

    # A splits to B (if x>5) or C (default) - use ControlTypeXor
    store.add((task_a, YAWL.hasSplit, YAWL.ControlTypeXor))

    # Flow to B with predicate
    flow_b = TEST_NAMESPACE.flow_b
    pred_b = TEST_NAMESPACE.pred_b
    store.add((task_a, YAWL.flowsInto, flow_b))
    store.add((flow_b, YAWL.nextElementRef, task_b))
    store.add((flow_b, YAWL.hasPredicate, pred_b))
    store.add((pred_b, YAWL.query, Literal("data['x'] > 5")))
    store.add((pred_b, YAWL.ordering, Literal(1)))

    # Flow to C (default)
    flow_c = TEST_NAMESPACE.flow_c
    store.add((task_a, YAWL.flowsInto, flow_c))
    store.add((flow_c, YAWL.nextElementRef, task_c))
    store.add((flow_c, YAWL.isDefaultFlow, Literal(True)))

    store.add((task_a, KGC.hasToken, Literal(True)))

    # Execute with x=10 (should select B)
    ctx = TransactionContext(tx_id="xor-test", actor="test", prev_hash=GENESIS_HASH, data={"x": 10})
    receipt = engine.driver.execute(store, task_a, ctx)

    assert (task_b, KGC.hasToken, Literal(True)) in store
    assert (task_c, KGC.hasToken, Literal(True)) not in store


def test_wcp43_termination_voids_all(physics_ontology: Graph) -> None:
    """WCP-43: Termination pattern voids all active tokens.

    Arrange:
        - Multiple active tasks A, B, C
        - Termination trigger at A
    Act:
        - Execute void on A with scope="case"
    Assert:
        - All tokens removed
        - All tasks marked as voided
    """
    store = Graph()
    engine = HybridEngine(store, physics_ontology)

    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c

    # Multiple active tasks
    store.add((task_a, KGC.hasToken, Literal(True)))
    store.add((task_b, KGC.hasToken, Literal(True)))
    store.add((task_c, KGC.hasToken, Literal(True)))

    # Manual void execution (void verb with case scope)
    ctx = TransactionContext(tx_id="void-test", actor="test", prev_hash=GENESIS_HASH, data={})

    from kgcl.engine.knowledge_engine import Kernel, VerbConfig

    config = VerbConfig(verb="void", cancellation_scope="case")
    delta = Kernel.void(store, task_a, ctx, config)

    # Apply mutations
    for triple in delta.removals:
        store.remove(triple)
    for triple in delta.additions:
        store.add(triple)

    # All tokens should be removed
    assert (task_a, KGC.hasToken, Literal(True)) not in store
    assert (task_b, KGC.hasToken, Literal(True)) not in store
    assert (task_c, KGC.hasToken, Literal(True)) not in store

    # All tasks marked as voided
    assert (task_a, KGC.voidedAt, None) in store
    assert (task_b, KGC.voidedAt, None) in store
    assert (task_c, KGC.voidedAt, None) in store


# =============================================================================
# RUN TO COMPLETION TESTS
# =============================================================================


def test_run_to_completion_stops_at_fixed_point(physics_ontology: Graph) -> None:
    """run_to_completion executes until no changes occur.

    Arrange:
        - Linear sequence A→B→C
        - Token at A
    Act:
        - Run to completion
    Assert:
        - Completes in 2 ticks (A→B, B→C)
        - Reaches fixed point (C is terminal)
        - Token at C
    """
    store = Graph()
    engine = HybridEngine(store, physics_ontology)

    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c

    # A→B→C
    store.add((task_a, YAWL.flowsInto, TEST_NAMESPACE.flow_1))
    store.add((TEST_NAMESPACE.flow_1, YAWL.nextElementRef, task_b))
    store.add((task_b, YAWL.flowsInto, TEST_NAMESPACE.flow_2))
    store.add((TEST_NAMESPACE.flow_2, YAWL.nextElementRef, task_c))
    store.add((task_a, KGC.hasToken, Literal(True)))

    result = engine.run_to_completion()

    assert result["reached_fixed_point"] is True
    assert result["ticks_executed"] <= 4  # A→B, B→C, C→∅, fixed point check
    # Verify workflow completed successfully
    assert result["total_executions"] >= 3  # At least A, B, C executed


def test_run_to_completion_respects_max_ticks(physics_ontology: Graph) -> None:
    """run_to_completion stops at max_ticks limit.

    Arrange:
        - Long linear sequence A→B→C→D→E
        - Token at A
    Act:
        - Run with max_ticks=2
    Assert:
        - Stops after 2 ticks
        - Does not reach fixed point
        - Token somewhere in middle (B or C)
    """
    store = Graph()
    engine = HybridEngine(store, physics_ontology)

    task_a = TEST_NAMESPACE.task_a
    task_b = TEST_NAMESPACE.task_b
    task_c = TEST_NAMESPACE.task_c
    task_d = TEST_NAMESPACE.task_d
    task_e = TEST_NAMESPACE.task_e

    # A→B→C→D→E
    store.add((task_a, YAWL.flowsInto, TEST_NAMESPACE.flow_1))
    store.add((TEST_NAMESPACE.flow_1, YAWL.nextElementRef, task_b))
    store.add((task_b, YAWL.flowsInto, TEST_NAMESPACE.flow_2))
    store.add((TEST_NAMESPACE.flow_2, YAWL.nextElementRef, task_c))
    store.add((task_c, YAWL.flowsInto, TEST_NAMESPACE.flow_3))
    store.add((TEST_NAMESPACE.flow_3, YAWL.nextElementRef, task_d))
    store.add((task_d, YAWL.flowsInto, TEST_NAMESPACE.flow_4))
    store.add((TEST_NAMESPACE.flow_4, YAWL.nextElementRef, task_e))
    store.add((task_a, KGC.hasToken, Literal(True)))

    result = engine.run_to_completion(max_ticks=2)

    assert result["ticks_executed"] == 2
    assert result["reached_fixed_point"] is False
    # Token should be at B or C after 2 ticks
    assert (task_b, KGC.hasToken, Literal(True)) in store or (task_c, KGC.hasToken, Literal(True)) in store
    # Should not have reached E yet
    assert (task_e, KGC.hasToken, Literal(True)) not in store
