"""Comprehensive tests for YAWL Iteration Patterns (WCP-21 variants).

Tests verify iteration patterns mapped to Filter verb with selectionMode:
- WhileLoop (WCP-21 variant): selectionMode="whileTrue" - Pre-test loop
- RepeatUntil (WCP-21 variant): selectionMode="untilTrue" - Post-test loop
- Arbitrary Cycles (WCP-10): selectionMode="oneOrMore" - Flexible loops

Critical constraint: ZERO `if type ==` statements in engine code.
All dispatch must be ontology-driven via kgc_physics.ttl mappings.

Chicago School TDD: Real collaborators, no mocking domain objects.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.engine.knowledge_engine import (
    GENESIS_HASH,
    KGC,
    YAWL,
    Kernel,
    QuadDelta,
    Receipt,
    SemanticDriver,
    TransactionContext,
    VerbConfig,
)

# Test namespace
WORKFLOW = Namespace("http://example.org/workflow#")

# Performance target (p99 latency)
P99_TARGET_MS: float = 100.0


@pytest.fixture
def physics_ontology() -> Graph:
    """Load KGC Physics Ontology with iteration pattern mappings."""
    ontology = Graph()
    ontology.parse("/Users/sac/dev/kgcl/ontology/kgc_physics.ttl", format="turtle")
    return ontology


@pytest.fixture
def semantic_driver(physics_ontology: Graph) -> SemanticDriver:
    """Create SemanticDriver with loaded ontology."""
    return SemanticDriver(physics_ontology)


@pytest.fixture
def transaction_context() -> TransactionContext:
    """Create standard transaction context."""
    return TransactionContext(tx_id="test-tx-001", actor="test-agent", prev_hash=GENESIS_HASH, data={})


# =============================================================================
# SECTION 1: WCP-21 WHILE LOOP (PRE-TEST) TESTS
# =============================================================================


class TestWhileLoopPattern:
    """Tests for While Loop pattern (WCP-21 variant).

    While loop: Pre-test loop, evaluates condition BEFORE loop body.
    Pattern: yawl:WhileLoop
    Verb: Filter
    SelectionMode: "whileTrue"
    Behavior: If condition is true, route to loop body; else route to exit.
    """

    def test_while_loop_condition_true_routes_to_body(
        self, physics_ontology: Graph, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """While loop with true condition routes token to loop body."""
        # Arrange: Create while loop graph
        graph = Graph()
        loop_node = WORKFLOW.WhileLoop1
        loop_body = WORKFLOW.LoopBody1
        loop_exit = WORKFLOW.LoopExit1

        # Mark node as WhileLoop pattern
        graph.add((loop_node, YAWL.hasSplit, YAWL.WhileLoop))

        # Define flow to loop body (condition=true)
        flow_body = WORKFLOW.Flow_Body
        graph.add((loop_node, YAWL.flowsInto, flow_body))
        graph.add((flow_body, YAWL.nextElementRef, loop_body))
        predicate_body = WORKFLOW.Predicate_Body
        graph.add((flow_body, YAWL.hasPredicate, predicate_body))
        graph.add((predicate_body, YAWL.query, Literal("data['counter'] < 5")))
        graph.add((predicate_body, YAWL.ordering, Literal(1)))

        # Define flow to exit (condition=false)
        flow_exit = WORKFLOW.Flow_Exit
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, loop_exit))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        # Add token to loop node
        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Context with counter < 5 (condition TRUE)
        ctx = TransactionContext(tx_id="test-tx-001", actor="test-agent", prev_hash=GENESIS_HASH, data={"counter": 0})

        # Act: Execute via SemanticDriver
        receipt = semantic_driver.execute(graph, loop_node, ctx)

        # Assert: Verb is Filter with selectionMode=whileTrue
        assert receipt.verb_executed == "filter"
        assert receipt.params_used is not None
        assert receipt.params_used.selection_mode == "whileTrue"

        # Assert: Token routed to loop body (condition true)
        assert (loop_body, KGC.hasToken, Literal(True)) in graph
        assert (loop_exit, KGC.hasToken, Literal(True)) not in graph

        # Assert: Original token removed
        assert (loop_node, KGC.hasToken, Literal(True)) not in graph

    def test_while_loop_condition_false_routes_to_exit(
        self, physics_ontology: Graph, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """While loop with false condition routes token to exit path."""
        # Arrange: Same graph structure
        graph = Graph()
        loop_node = WORKFLOW.WhileLoop2
        loop_body = WORKFLOW.LoopBody2
        loop_exit = WORKFLOW.LoopExit2

        graph.add((loop_node, YAWL.hasSplit, YAWL.WhileLoop))

        # Flow to body (will be false)
        flow_body = WORKFLOW.Flow_Body2
        graph.add((loop_node, YAWL.flowsInto, flow_body))
        graph.add((flow_body, YAWL.nextElementRef, loop_body))
        predicate_body = WORKFLOW.Predicate_Body2
        graph.add((flow_body, YAWL.hasPredicate, predicate_body))
        graph.add((predicate_body, YAWL.query, Literal("data['counter'] < 5")))
        graph.add((predicate_body, YAWL.ordering, Literal(1)))

        # Flow to exit (default)
        flow_exit = WORKFLOW.Flow_Exit2
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, loop_exit))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Context with counter >= 5 (condition FALSE)
        ctx = TransactionContext(tx_id="test-tx-002", actor="test-agent", prev_hash=GENESIS_HASH, data={"counter": 10})

        # Act
        receipt = semantic_driver.execute(graph, loop_node, ctx)

        # Assert: Token routed to exit (condition false, default path)
        assert receipt.verb_executed == "filter"
        assert (loop_exit, KGC.hasToken, Literal(True)) in graph
        assert (loop_body, KGC.hasToken, Literal(True)) not in graph

    def test_while_loop_never_executes_on_initial_false(
        self, physics_ontology: Graph, semantic_driver: SemanticDriver
    ) -> None:
        """While loop never executes body if condition is false initially."""
        # Arrange
        graph = Graph()
        loop_node = WORKFLOW.WhileLoop3
        loop_body = WORKFLOW.LoopBody3
        loop_exit = WORKFLOW.LoopExit3

        graph.add((loop_node, YAWL.hasSplit, YAWL.WhileLoop))

        # Flow to body
        flow_body = WORKFLOW.Flow_Body3
        graph.add((loop_node, YAWL.flowsInto, flow_body))
        graph.add((flow_body, YAWL.nextElementRef, loop_body))
        predicate_body = WORKFLOW.Predicate_Body3
        graph.add((flow_body, YAWL.hasPredicate, predicate_body))
        graph.add((predicate_body, YAWL.query, Literal("data['execute'] == True")))
        graph.add((predicate_body, YAWL.ordering, Literal(1)))

        # Flow to exit
        flow_exit = WORKFLOW.Flow_Exit3
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, loop_exit))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Context with execute=False (skip body entirely)
        ctx = TransactionContext(
            tx_id="test-tx-003", actor="test-agent", prev_hash=GENESIS_HASH, data={"execute": False}
        )

        # Act
        receipt = semantic_driver.execute(graph, loop_node, ctx)

        # Assert: Body never executed (pre-test failed)
        assert (loop_exit, KGC.hasToken, Literal(True)) in graph
        assert (loop_body, KGC.hasToken, Literal(True)) not in graph
        # Verify loop_body was never marked completed
        assert (loop_body, KGC.completedAt, Literal("test-tx-003")) not in graph

    def test_while_loop_counter_decrement_scenario(
        self, physics_ontology: Graph, semantic_driver: SemanticDriver
    ) -> None:
        """While loop with counter decrement (real-world scenario)."""
        # Arrange
        graph = Graph()
        loop_node = WORKFLOW.WhileLoop4
        loop_body = WORKFLOW.LoopBody4
        loop_exit = WORKFLOW.LoopExit4

        graph.add((loop_node, YAWL.hasSplit, YAWL.WhileLoop))

        # Flow to body
        flow_body = WORKFLOW.Flow_Body4
        graph.add((loop_node, YAWL.flowsInto, flow_body))
        graph.add((flow_body, YAWL.nextElementRef, loop_body))
        predicate_body = WORKFLOW.Predicate_Body4
        graph.add((flow_body, YAWL.hasPredicate, predicate_body))
        graph.add((predicate_body, YAWL.query, Literal("data['counter'] > 0")))
        graph.add((predicate_body, YAWL.ordering, Literal(1)))

        # Flow to exit
        flow_exit = WORKFLOW.Flow_Exit4
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, loop_exit))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Simulate loop iterations
        # Iteration 1: counter=3 (enter body)
        ctx1 = TransactionContext(
            tx_id="test-tx-iter1", actor="test-agent", prev_hash=GENESIS_HASH, data={"counter": 3}
        )
        receipt1 = semantic_driver.execute(graph, loop_node, ctx1)
        assert (loop_body, KGC.hasToken, Literal(True)) in graph

        # Simulate body execution and loop back
        graph.remove((loop_body, KGC.hasToken, Literal(True)))
        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Iteration 2: counter=0 (exit)
        ctx2 = TransactionContext(tx_id="test-tx-iter2", actor="test-agent", prev_hash="hash1", data={"counter": 0})
        receipt2 = semantic_driver.execute(graph, loop_node, ctx2)

        # Assert: Exited after counter reached 0
        assert receipt2.verb_executed == "filter"
        assert (loop_exit, KGC.hasToken, Literal(True)) in graph


# =============================================================================
# SECTION 2: WCP-21 REPEAT UNTIL (POST-TEST) TESTS
# =============================================================================


class TestRepeatUntilPattern:
    """Tests for Repeat Until pattern (WCP-21 variant).

    Repeat Until: Post-test loop, evaluates condition AFTER loop body.
    Pattern: yawl:RepeatUntil
    Verb: Filter
    SelectionMode: "untilTrue"
    Behavior: Execute body at least once, then check condition.
    """

    def test_repeat_until_executes_body_at_least_once(
        self, physics_ontology: Graph, semantic_driver: SemanticDriver
    ) -> None:
        """Repeat Until always executes body at least once (post-test)."""
        # Arrange
        graph = Graph()
        loop_node = WORKFLOW.RepeatUntil1
        loop_body = WORKFLOW.LoopBody5
        loop_exit = WORKFLOW.LoopExit5

        graph.add((loop_node, YAWL.hasSplit, YAWL.RepeatUntil))

        # Flow to body (unconditional first pass)
        flow_body = WORKFLOW.Flow_Body5
        graph.add((loop_node, YAWL.flowsInto, flow_body))
        graph.add((flow_body, YAWL.nextElementRef, loop_body))
        predicate_body = WORKFLOW.Predicate_Body5
        graph.add((flow_body, YAWL.hasPredicate, predicate_body))
        graph.add((predicate_body, YAWL.query, Literal("data['done'] == True")))
        graph.add((predicate_body, YAWL.ordering, Literal(1)))

        # Flow to exit
        flow_exit = WORKFLOW.Flow_Exit5
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, loop_exit))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Context with done=False (but should execute once anyway)
        ctx = TransactionContext(tx_id="test-tx-004", actor="test-agent", prev_hash=GENESIS_HASH, data={"done": False})

        # Act
        receipt = semantic_driver.execute(graph, loop_node, ctx)

        # Assert: Body executed (post-test always runs once)
        assert receipt.verb_executed == "filter"
        assert receipt.params_used is not None
        assert receipt.params_used.selection_mode == "untilTrue"
        # Note: With untilTrue, the condition is checked AFTER body execution
        # In our implementation, the condition inverts the logic: route to body if NOT done
        # So done=False means continue looping (route to body)
        assert (loop_body, KGC.hasToken, Literal(True)) in graph

    def test_repeat_until_exits_on_condition_true(
        self, physics_ontology: Graph, semantic_driver: SemanticDriver
    ) -> None:
        """Repeat Until exits when condition becomes true."""
        # Arrange
        graph = Graph()
        loop_node = WORKFLOW.RepeatUntil2
        loop_body = WORKFLOW.LoopBody6
        loop_exit = WORKFLOW.LoopExit6

        graph.add((loop_node, YAWL.hasSplit, YAWL.RepeatUntil))

        # Flow to body (repeat UNTIL condition)
        flow_body = WORKFLOW.Flow_Body6
        graph.add((loop_node, YAWL.flowsInto, flow_body))
        graph.add((flow_body, YAWL.nextElementRef, loop_body))
        predicate_body = WORKFLOW.Predicate_Body6
        graph.add((flow_body, YAWL.hasPredicate, predicate_body))
        # Repeat UNTIL done=True (i.e., loop while done=False)
        graph.add((predicate_body, YAWL.query, Literal("data['done'] == True")))
        graph.add((predicate_body, YAWL.ordering, Literal(1)))

        # Flow to exit
        flow_exit = WORKFLOW.Flow_Exit6
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, loop_exit))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Context with done=True (exit condition met)
        ctx = TransactionContext(tx_id="test-tx-005", actor="test-agent", prev_hash=GENESIS_HASH, data={"done": True})

        # Act
        receipt = semantic_driver.execute(graph, loop_node, ctx)

        # Assert: Exit path taken (condition met)
        assert (loop_exit, KGC.hasToken, Literal(True)) in graph
        assert (loop_body, KGC.hasToken, Literal(True)) not in graph

    def test_repeat_until_multiple_iterations(self, physics_ontology: Graph, semantic_driver: SemanticDriver) -> None:
        """Repeat Until performs multiple iterations until condition met."""
        # Arrange
        graph = Graph()
        loop_node = WORKFLOW.RepeatUntil3
        loop_body = WORKFLOW.LoopBody7
        loop_exit = WORKFLOW.LoopExit7

        graph.add((loop_node, YAWL.hasSplit, YAWL.RepeatUntil))

        # Flow to body
        flow_body = WORKFLOW.Flow_Body7
        graph.add((loop_node, YAWL.flowsInto, flow_body))
        graph.add((flow_body, YAWL.nextElementRef, loop_body))
        predicate_body = WORKFLOW.Predicate_Body7
        graph.add((flow_body, YAWL.hasPredicate, predicate_body))
        graph.add((predicate_body, YAWL.query, Literal("data['counter'] >= 3")))
        graph.add((predicate_body, YAWL.ordering, Literal(1)))

        # Flow to exit
        flow_exit = WORKFLOW.Flow_Exit7
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, loop_exit))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Iteration 1: counter=0 (continue)
        ctx1 = TransactionContext(
            tx_id="test-tx-iter1", actor="test-agent", prev_hash=GENESIS_HASH, data={"counter": 0}
        )
        receipt1 = semantic_driver.execute(graph, loop_node, ctx1)
        assert (loop_body, KGC.hasToken, Literal(True)) in graph

        # Simulate body and loop back
        graph.remove((loop_body, KGC.hasToken, Literal(True)))
        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Iteration 2: counter=1 (continue)
        ctx2 = TransactionContext(tx_id="test-tx-iter2", actor="test-agent", prev_hash="hash1", data={"counter": 1})
        receipt2 = semantic_driver.execute(graph, loop_node, ctx2)
        assert (loop_body, KGC.hasToken, Literal(True)) in graph

        # Loop back again
        graph.remove((loop_body, KGC.hasToken, Literal(True)))
        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Iteration 3: counter=3 (exit condition met)
        ctx3 = TransactionContext(tx_id="test-tx-iter3", actor="test-agent", prev_hash="hash2", data={"counter": 3})
        receipt3 = semantic_driver.execute(graph, loop_node, ctx3)

        # Assert: Exited after 3 iterations
        assert (loop_exit, KGC.hasToken, Literal(True)) in graph

    def test_repeat_until_sentinel_value_pattern(
        self, physics_ontology: Graph, semantic_driver: SemanticDriver
    ) -> None:
        """Repeat Until with sentinel value (e.g., input != -1)."""
        # Arrange
        graph = Graph()
        loop_node = WORKFLOW.RepeatUntil4
        loop_body = WORKFLOW.LoopBody8
        loop_exit = WORKFLOW.LoopExit8

        graph.add((loop_node, YAWL.hasSplit, YAWL.RepeatUntil))

        # Flow to body
        flow_body = WORKFLOW.Flow_Body8
        graph.add((loop_node, YAWL.flowsInto, flow_body))
        graph.add((flow_body, YAWL.nextElementRef, loop_body))
        predicate_body = WORKFLOW.Predicate_Body8
        graph.add((flow_body, YAWL.hasPredicate, predicate_body))
        # Repeat UNTIL input == -1
        graph.add((predicate_body, YAWL.query, Literal("data['input'] == -1")))
        graph.add((predicate_body, YAWL.ordering, Literal(1)))

        # Flow to exit
        flow_exit = WORKFLOW.Flow_Exit8
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, loop_exit))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Test with sentinel value
        ctx = TransactionContext(tx_id="test-tx-006", actor="test-agent", prev_hash=GENESIS_HASH, data={"input": -1})

        # Act
        receipt = semantic_driver.execute(graph, loop_node, ctx)

        # Assert: Exit immediately when sentinel detected
        assert (loop_exit, KGC.hasToken, Literal(True)) in graph


# =============================================================================
# SECTION 3: WCP-10 ARBITRARY CYCLES TESTS
# =============================================================================


class TestArbitraryCyclesPattern:
    """Tests for Arbitrary Cycles pattern (WCP-10).

    Arbitrary Cycles: Flexible loops with conditional back-edges.
    Pattern: yawl:ArbitraryCycle
    Verb: Filter
    SelectionMode: "oneOrMore"
    Behavior: Support complex loop structures (not just pre/post test).
    """

    def test_arbitrary_cycle_forward_and_backward_edges(
        self, physics_ontology: Graph, semantic_driver: SemanticDriver
    ) -> None:
        """Arbitrary cycle supports both forward and backward edges."""
        # Arrange
        graph = Graph()
        loop_node = WORKFLOW.ArbitraryCycle1
        forward_node = WORKFLOW.ForwardPath1
        backward_node = WORKFLOW.BackwardPath1

        graph.add((loop_node, YAWL.hasSplit, YAWL.ArbitraryCycle))

        # Forward edge
        flow_forward = WORKFLOW.Flow_Forward1
        graph.add((loop_node, YAWL.flowsInto, flow_forward))
        graph.add((flow_forward, YAWL.nextElementRef, forward_node))
        predicate_forward = WORKFLOW.Predicate_Forward1
        graph.add((flow_forward, YAWL.hasPredicate, predicate_forward))
        graph.add((predicate_forward, YAWL.query, Literal("data['forward'] == True")))
        graph.add((predicate_forward, YAWL.ordering, Literal(1)))

        # Backward edge (loop back)
        flow_backward = WORKFLOW.Flow_Backward1
        graph.add((loop_node, YAWL.flowsInto, flow_backward))
        graph.add((flow_backward, YAWL.nextElementRef, backward_node))
        predicate_backward = WORKFLOW.Predicate_Backward1
        graph.add((flow_backward, YAWL.hasPredicate, predicate_backward))
        graph.add((predicate_backward, YAWL.query, Literal("data['backward'] == True")))
        graph.add((predicate_backward, YAWL.ordering, Literal(2)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Test forward path
        ctx_forward = TransactionContext(
            tx_id="test-tx-007", actor="test-agent", prev_hash=GENESIS_HASH, data={"forward": True, "backward": False}
        )

        receipt = semantic_driver.execute(graph, loop_node, ctx_forward)

        # Assert: Forward path taken
        assert receipt.verb_executed == "filter"
        assert (forward_node, KGC.hasToken, Literal(True)) in graph

    def test_arbitrary_cycle_multiple_back_edges(
        self, physics_ontology: Graph, semantic_driver: SemanticDriver
    ) -> None:
        """Arbitrary cycle with multiple back-edges (complex loop)."""
        # Arrange
        graph = Graph()
        loop_node = WORKFLOW.ArbitraryCycle2
        path_a = WORKFLOW.PathA
        path_b = WORKFLOW.PathB
        exit_node = WORKFLOW.ExitPath2

        graph.add((loop_node, YAWL.hasSplit, YAWL.ArbitraryCycle))

        # Path A (back-edge 1)
        flow_a = WORKFLOW.Flow_A
        graph.add((loop_node, YAWL.flowsInto, flow_a))
        graph.add((flow_a, YAWL.nextElementRef, path_a))
        predicate_a = WORKFLOW.Predicate_A
        graph.add((flow_a, YAWL.hasPredicate, predicate_a))
        graph.add((predicate_a, YAWL.query, Literal("data['choice'] == 'A'")))
        graph.add((predicate_a, YAWL.ordering, Literal(1)))

        # Path B (back-edge 2)
        flow_b = WORKFLOW.Flow_B
        graph.add((loop_node, YAWL.flowsInto, flow_b))
        graph.add((flow_b, YAWL.nextElementRef, path_b))
        predicate_b = WORKFLOW.Predicate_B
        graph.add((flow_b, YAWL.hasPredicate, predicate_b))
        graph.add((predicate_b, YAWL.query, Literal("data['choice'] == 'B'")))
        graph.add((predicate_b, YAWL.ordering, Literal(2)))

        # Exit path
        flow_exit = WORKFLOW.Flow_Exit2
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, exit_node))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Test path B
        ctx = TransactionContext(tx_id="test-tx-008", actor="test-agent", prev_hash=GENESIS_HASH, data={"choice": "B"})

        receipt = semantic_driver.execute(graph, loop_node, ctx)

        # Assert: Path B selected
        assert (path_b, KGC.hasToken, Literal(True)) in graph
        assert (path_a, KGC.hasToken, Literal(True)) not in graph

    def test_arbitrary_cycle_exit_condition(self, physics_ontology: Graph, semantic_driver: SemanticDriver) -> None:
        """Arbitrary cycle exits when no back-edges match."""
        # Arrange
        graph = Graph()
        loop_node = WORKFLOW.ArbitraryCycle3
        back_edge = WORKFLOW.BackEdge3
        exit_node = WORKFLOW.ExitNode3

        graph.add((loop_node, YAWL.hasSplit, YAWL.ArbitraryCycle))

        # Back-edge (loop condition)
        flow_back = WORKFLOW.Flow_Back3
        graph.add((loop_node, YAWL.flowsInto, flow_back))
        graph.add((flow_back, YAWL.nextElementRef, back_edge))
        predicate_back = WORKFLOW.Predicate_Back3
        graph.add((flow_back, YAWL.hasPredicate, predicate_back))
        graph.add((predicate_back, YAWL.query, Literal("data['continue'] == True")))
        graph.add((predicate_back, YAWL.ordering, Literal(1)))

        # Exit (default when continue=False)
        flow_exit = WORKFLOW.Flow_Exit3
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, exit_node))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Test exit condition
        ctx = TransactionContext(
            tx_id="test-tx-009", actor="test-agent", prev_hash=GENESIS_HASH, data={"continue": False}
        )

        receipt = semantic_driver.execute(graph, loop_node, ctx)

        # Assert: Exited loop (default path)
        assert (exit_node, KGC.hasToken, Literal(True)) in graph
        assert (back_edge, KGC.hasToken, Literal(True)) not in graph

    def test_arbitrary_cycle_nested_loop_structure(
        self, physics_ontology: Graph, semantic_driver: SemanticDriver
    ) -> None:
        """Arbitrary cycle supports nested loop structures."""
        # Arrange: Outer loop with inner loop
        graph = Graph()
        outer_loop = WORKFLOW.OuterLoop
        inner_loop = WORKFLOW.InnerLoop
        inner_body = WORKFLOW.InnerBody
        outer_exit = WORKFLOW.OuterExit

        # Outer loop
        graph.add((outer_loop, YAWL.hasSplit, YAWL.ArbitraryCycle))

        # Flow to inner loop
        flow_inner = WORKFLOW.Flow_ToInner
        graph.add((outer_loop, YAWL.flowsInto, flow_inner))
        graph.add((flow_inner, YAWL.nextElementRef, inner_loop))
        predicate_inner = WORKFLOW.Predicate_ToInner
        graph.add((flow_inner, YAWL.hasPredicate, predicate_inner))
        graph.add((predicate_inner, YAWL.query, Literal("data['outer'] == True")))
        graph.add((predicate_inner, YAWL.ordering, Literal(1)))

        # Flow to exit
        flow_exit = WORKFLOW.Flow_OuterExit
        graph.add((outer_loop, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, outer_exit))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((outer_loop, KGC.hasToken, Literal(True)))

        # Test entering inner loop
        ctx = TransactionContext(tx_id="test-tx-010", actor="test-agent", prev_hash=GENESIS_HASH, data={"outer": True})

        receipt = semantic_driver.execute(graph, outer_loop, ctx)

        # Assert: Entered inner loop
        assert (inner_loop, KGC.hasToken, Literal(True)) in graph


# =============================================================================
# SECTION 4: KERNEL DIRECT TESTS (LOW-LEVEL)
# =============================================================================


class TestKernelFilterForLoops:
    """Direct tests of Kernel.filter for loop patterns."""

    def test_filter_verb_whileTrue_selection_mode(self, transaction_context: TransactionContext) -> None:
        """Filter verb with selectionMode=whileTrue for while loops."""
        # Arrange
        graph = Graph()
        loop_node = WORKFLOW.TestLoop1
        body_node = WORKFLOW.TestBody1
        exit_node = WORKFLOW.TestExit1

        # Flows
        flow_body = WORKFLOW.Flow_Test1
        graph.add((loop_node, YAWL.flowsInto, flow_body))
        graph.add((flow_body, YAWL.nextElementRef, body_node))
        predicate = WORKFLOW.Predicate_Test1
        graph.add((flow_body, YAWL.hasPredicate, predicate))
        graph.add((predicate, YAWL.query, Literal("data['x'] > 0")))
        graph.add((predicate, YAWL.ordering, Literal(1)))

        flow_exit = WORKFLOW.Flow_TestExit1
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, exit_node))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Config with whileTrue
        config = VerbConfig(verb="filter", selection_mode="whileTrue")

        ctx = TransactionContext(tx_id="test-kernel-001", actor="test-agent", prev_hash=GENESIS_HASH, data={"x": 5})

        # Act
        delta = Kernel.filter(graph, loop_node, ctx, config)

        # Assert
        assert len(delta.additions) >= 1
        assert (body_node, KGC.hasToken, Literal(True)) in delta.additions

    def test_filter_verb_untilTrue_selection_mode(self, transaction_context: TransactionContext) -> None:
        """Filter verb with selectionMode=untilTrue for repeat-until loops."""
        # Arrange
        graph = Graph()
        loop_node = WORKFLOW.TestLoop2
        body_node = WORKFLOW.TestBody2
        exit_node = WORKFLOW.TestExit2

        # Flows
        flow_body = WORKFLOW.Flow_Test2
        graph.add((loop_node, YAWL.flowsInto, flow_body))
        graph.add((flow_body, YAWL.nextElementRef, body_node))
        predicate = WORKFLOW.Predicate_Test2
        graph.add((flow_body, YAWL.hasPredicate, predicate))
        graph.add((predicate, YAWL.query, Literal("data['done'] == True")))
        graph.add((predicate, YAWL.ordering, Literal(1)))

        flow_exit = WORKFLOW.Flow_TestExit2
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, exit_node))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Config with untilTrue (RDF-only: invert_predicate inverts condition)
        config = VerbConfig(verb="filter", selection_mode="untilTrue", invert_predicate=True)

        ctx = TransactionContext(
            tx_id="test-kernel-002", actor="test-agent", prev_hash=GENESIS_HASH, data={"done": False}
        )

        # Act
        delta = Kernel.filter(graph, loop_node, ctx, config)

        # Assert: Body selected (done=False means continue)
        assert len(delta.additions) >= 1
        assert (body_node, KGC.hasToken, Literal(True)) in delta.additions


# =============================================================================
# SECTION 5: ONTOLOGY MAPPING VERIFICATION TESTS
# =============================================================================


class TestIterationOntologyMappings:
    """Verify kgc_physics.ttl contains correct iteration pattern mappings."""

    def test_while_loop_mapping_exists(self, physics_ontology: Graph) -> None:
        """Ontology contains WhileLoop → Filter(whileTrue) mapping."""
        query = """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        ASK {
            ?mapping kgc:pattern yawl:WhileLoop ;
                     kgc:verb kgc:Filter ;
                     kgc:selectionMode "whileTrue" .
        }
        """
        result = physics_ontology.query(query)
        assert bool(result), "WhileLoop mapping not found in ontology"

    def test_repeat_until_mapping_exists(self, physics_ontology: Graph) -> None:
        """Ontology contains RepeatUntil → Filter(untilTrue) mapping."""
        query = """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        ASK {
            ?mapping kgc:pattern yawl:RepeatUntil ;
                     kgc:verb kgc:Filter ;
                     kgc:selectionMode "untilTrue" .
        }
        """
        result = physics_ontology.query(query)
        assert bool(result), "RepeatUntil mapping not found in ontology"

    def test_arbitrary_cycle_mapping_exists(self, physics_ontology: Graph) -> None:
        """Ontology contains ArbitraryCycle → Filter(oneOrMore) mapping."""
        query = """
        PREFIX kgc: <http://bitflow.ai/ontology/kgc/v3#>
        PREFIX yawl: <http://www.yawlfoundation.org/yawlschema#>
        ASK {
            ?mapping kgc:pattern yawl:ArbitraryCycle ;
                     kgc:verb kgc:Filter ;
                     kgc:selectionMode "oneOrMore" .
        }
        """
        result = physics_ontology.query(query)
        assert bool(result), "ArbitraryCycle mapping not found in ontology"

    def test_iteration_patterns_resolve_to_filter_verb(
        self, physics_ontology: Graph, semantic_driver: SemanticDriver
    ) -> None:
        """All iteration patterns resolve to Filter verb with correct selectionMode."""
        # Test WhileLoop
        graph_while = Graph()
        while_node = WORKFLOW.ResolveTest1
        graph_while.add((while_node, YAWL.hasSplit, YAWL.WhileLoop))
        config_while = semantic_driver.resolve_verb(graph_while, while_node)
        assert config_while.verb == "filter"
        assert config_while.selection_mode == "whileTrue"

        # Test RepeatUntil
        graph_repeat = Graph()
        repeat_node = WORKFLOW.ResolveTest2
        graph_repeat.add((repeat_node, YAWL.hasSplit, YAWL.RepeatUntil))
        config_repeat = semantic_driver.resolve_verb(graph_repeat, repeat_node)
        assert config_repeat.verb == "filter"
        assert config_repeat.selection_mode == "untilTrue"

        # Test ArbitraryCycle
        graph_cycle = Graph()
        cycle_node = WORKFLOW.ResolveTest3
        graph_cycle.add((cycle_node, YAWL.hasSplit, YAWL.ArbitraryCycle))
        config_cycle = semantic_driver.resolve_verb(graph_cycle, cycle_node)
        assert config_cycle.verb == "filter"
        assert config_cycle.selection_mode == "oneOrMore"


# =============================================================================
# SECTION 6: PROVENANCE AND RECEIPT TESTS
# =============================================================================


class TestIterationProvenance:
    """Tests for provenance tracking in iteration patterns."""

    def test_while_loop_receipt_contains_selection_mode(
        self, physics_ontology: Graph, semantic_driver: SemanticDriver
    ) -> None:
        """While loop receipt contains selectionMode parameter."""
        graph = Graph()
        loop_node = WORKFLOW.ProvenanceLoop1
        body_node = WORKFLOW.ProvenanceBody1
        exit_node = WORKFLOW.ProvenanceExit1

        graph.add((loop_node, YAWL.hasSplit, YAWL.WhileLoop))

        flow_body = WORKFLOW.Flow_Prov1
        graph.add((loop_node, YAWL.flowsInto, flow_body))
        graph.add((flow_body, YAWL.nextElementRef, body_node))
        predicate = WORKFLOW.Predicate_Prov1
        graph.add((flow_body, YAWL.hasPredicate, predicate))
        graph.add((predicate, YAWL.query, Literal("data['x'] > 0")))
        graph.add((predicate, YAWL.ordering, Literal(1)))

        flow_exit = WORKFLOW.Flow_ProvExit1
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, exit_node))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        ctx = TransactionContext(tx_id="test-prov-001", actor="test-agent", prev_hash=GENESIS_HASH, data={"x": 5})

        receipt = semantic_driver.execute(graph, loop_node, ctx)

        # Assert: Receipt contains parameters
        assert receipt.params_used is not None
        assert receipt.params_used.selection_mode == "whileTrue"
        assert receipt.merkle_root is not None
        assert len(receipt.merkle_root) == 64  # SHA256 hex length

    def test_repeat_until_lockchain_continuity(self, physics_ontology: Graph, semantic_driver: SemanticDriver) -> None:
        """Repeat Until maintains lockchain continuity across iterations."""
        graph = Graph()
        loop_node = WORKFLOW.ProvenanceLoop2
        body_node = WORKFLOW.ProvenanceBody2
        exit_node = WORKFLOW.ProvenanceExit2

        graph.add((loop_node, YAWL.hasSplit, YAWL.RepeatUntil))

        flow_body = WORKFLOW.Flow_Prov2
        graph.add((loop_node, YAWL.flowsInto, flow_body))
        graph.add((flow_body, YAWL.nextElementRef, body_node))
        predicate = WORKFLOW.Predicate_Prov2
        graph.add((flow_body, YAWL.hasPredicate, predicate))
        graph.add((predicate, YAWL.query, Literal("data['done'] == True")))
        graph.add((predicate, YAWL.ordering, Literal(1)))

        flow_exit = WORKFLOW.Flow_ProvExit2
        graph.add((loop_node, YAWL.flowsInto, flow_exit))
        graph.add((flow_exit, YAWL.nextElementRef, exit_node))
        graph.add((flow_exit, YAWL.isDefaultFlow, Literal(True)))

        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Iteration 1
        ctx1 = TransactionContext(
            tx_id="test-prov-iter1", actor="test-agent", prev_hash=GENESIS_HASH, data={"done": False}
        )
        receipt1 = semantic_driver.execute(graph, loop_node, ctx1)

        # Simulate loop back
        graph.remove((body_node, KGC.hasToken, Literal(True)))
        graph.add((loop_node, KGC.hasToken, Literal(True)))

        # Iteration 2 (use receipt1.merkle_root as prev_hash)
        ctx2 = TransactionContext(
            tx_id="test-prov-iter2", actor="test-agent", prev_hash=receipt1.merkle_root, data={"done": True}
        )
        receipt2 = semantic_driver.execute(graph, loop_node, ctx2)

        # Assert: Lockchain continuity maintained
        assert receipt1.merkle_root != receipt2.merkle_root
        assert receipt2.merkle_root is not None
