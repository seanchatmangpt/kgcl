"""Comprehensive tests for YAWL Workflow Control Patterns 10-11 (Structural).

Tests verify structural patterns using the 5-Verb Kernel:
- WCP-10: Arbitrary Cycles (Filter with loop back-edges)
- WCP-11: Implicit Termination (Void when no tokens remain)

These patterns test graph topology handling for loops and termination conditions.
All behavior resolved via SPARQL queries against the physics ontology.

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

# Test namespaces
WORKFLOW = Namespace("http://example.org/workflow#")

# Test constants
SHA256_HEX_LENGTH: int = 64


@pytest.fixture
def physics_ontology() -> Graph:
    """Load KGC Physics Ontology for verb resolution."""
    ontology = Graph()
    ontology.parse("/Users/sac/dev/kgcl/ontology/core/kgc_physics.ttl", format="turtle")
    return ontology


@pytest.fixture
def semantic_driver(physics_ontology: Graph) -> SemanticDriver:
    """Create SemanticDriver with physics ontology."""
    return SemanticDriver(physics_ontology)


@pytest.fixture
def transaction_context() -> TransactionContext:
    """Create standard transaction context."""
    return TransactionContext(tx_id="tx-test-001", actor="test-agent", prev_hash=GENESIS_HASH, data={})


class TestWCP10ArbitraryCycles:
    """Tests for WCP-10: Arbitrary Cycles (Loops via conditional back-edges).

    Pattern: yawl:ArbitraryCycle → Filter(selectionMode="oneOrMore")
    Behavior: Loop back to earlier node based on condition evaluation.
    """

    def test_loop_with_back_edge_true_condition(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Loop back-edge selected when condition evaluates to true."""
        # Arrange: Create loop topology A → B → C with C → A back-edge
        workflow = Graph()
        task_a = WORKFLOW.TaskA
        task_b = WORKFLOW.TaskB
        task_c = WORKFLOW.LoopDecision
        flow_forward = WORKFLOW.FlowForward
        flow_backward = WORKFLOW.FlowBackward
        task_exit = WORKFLOW.TaskExit

        # Graph: A → B → C →[loop]→ A or C → Exit
        workflow.add((task_a, YAWL.flowsInto, WORKFLOW.FlowAB))
        workflow.add((WORKFLOW.FlowAB, YAWL.nextElementRef, task_b))

        workflow.add((task_b, YAWL.flowsInto, WORKFLOW.FlowBC))
        workflow.add((WORKFLOW.FlowBC, YAWL.nextElementRef, task_c))

        # Loop decision point: C has two paths
        workflow.add((task_c, YAWL.hasSplit, YAWL.ControlTypeOr))
        workflow.add((task_c, YAWL.flowsInto, flow_backward))
        workflow.add((flow_backward, YAWL.nextElementRef, task_a))  # Back-edge
        workflow.add((flow_backward, YAWL.hasPredicate, WORKFLOW.LoopPredicate))
        workflow.add((WORKFLOW.LoopPredicate, YAWL.query, Literal("data['iteration'] < 3")))
        workflow.add((WORKFLOW.LoopPredicate, YAWL.ordering, Literal(1)))

        workflow.add((task_c, YAWL.flowsInto, flow_forward))
        workflow.add((flow_forward, YAWL.nextElementRef, task_exit))  # Exit path
        workflow.add((flow_forward, YAWL.isDefaultFlow, Literal(True)))

        # Token at loop decision point
        workflow.add((task_c, KGC.hasToken, Literal(True)))

        # Context data: iteration count less than threshold
        ctx = TransactionContext(tx_id="tx-loop-001", actor="test-agent", prev_hash=GENESIS_HASH, data={"iteration": 1})

        # Act: Execute Filter verb (should select back-edge)
        config = VerbConfig(verb="filter", selection_mode="oneOrMore")
        delta = Kernel.filter(workflow, task_c, ctx, config)

        # Assert: Token moved to task_a (back-edge) and task_exit (default)
        # Filter with oneOrMore selects ALL matching paths
        assert len(delta.additions) >= 1, "Should add at least one token"
        assert len(delta.removals) == 1, "Should remove token from loop decision"
        assert (task_c, KGC.hasToken, Literal(True)) in delta.removals
        # Back-edge should be selected (predicate true)
        token_targets = [triple[0] for triple in delta.additions if triple[1] == KGC.hasToken]
        assert task_a in token_targets, "Back-edge should loop to TaskA"

    def test_loop_exit_when_condition_false(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Loop exits when condition evaluates to false."""
        # Arrange: Same loop topology, but condition is false
        workflow = Graph()
        task_c = WORKFLOW.LoopDecision
        task_a = WORKFLOW.TaskA
        task_exit = WORKFLOW.TaskExit
        flow_backward = WORKFLOW.FlowBackward
        flow_forward = WORKFLOW.FlowForward

        workflow.add((task_c, YAWL.hasSplit, YAWL.ControlTypeXor))
        workflow.add((task_c, YAWL.flowsInto, flow_backward))
        workflow.add((flow_backward, YAWL.nextElementRef, task_a))
        workflow.add((flow_backward, YAWL.hasPredicate, WORKFLOW.LoopPredicate))
        workflow.add((WORKFLOW.LoopPredicate, YAWL.query, Literal("data['iteration'] < 3")))
        workflow.add((WORKFLOW.LoopPredicate, YAWL.ordering, Literal(1)))

        workflow.add((task_c, YAWL.flowsInto, flow_forward))
        workflow.add((flow_forward, YAWL.nextElementRef, task_exit))
        workflow.add((flow_forward, YAWL.isDefaultFlow, Literal(True)))

        workflow.add((task_c, KGC.hasToken, Literal(True)))

        # Context: iteration >= 3, should exit loop
        ctx = TransactionContext(tx_id="tx-exit-001", actor="test-agent", prev_hash=GENESIS_HASH, data={"iteration": 5})

        # Act: Execute Filter (should select default exit path)
        config = VerbConfig(verb="filter", selection_mode="exactlyOne")
        delta = Kernel.filter(workflow, task_c, ctx, config)

        # Assert: Token moved to exit path
        assert len(delta.removals) == 1
        assert (task_c, KGC.hasToken, Literal(True)) in delta.removals
        # Should route to exit (back-edge condition false)
        token_targets = [triple[0] for triple in delta.additions if triple[1] == KGC.hasToken]
        assert task_exit in token_targets, "Should exit loop to TaskExit"
        assert task_a not in token_targets, "Should NOT loop back to TaskA"

    def test_multiple_loop_iterations_with_state_tracking(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Loop executes multiple iterations with state tracking."""
        # Arrange: Loop with counter increment
        workflow = Graph()
        task_a = WORKFLOW.TaskA
        task_b = WORKFLOW.LoopBody
        task_c = WORKFLOW.LoopDecision
        task_exit = WORKFLOW.TaskExit

        # A → B → C → [back to A or exit]
        workflow.add((task_a, YAWL.flowsInto, WORKFLOW.FlowAB))
        workflow.add((WORKFLOW.FlowAB, YAWL.nextElementRef, task_b))

        workflow.add((task_b, YAWL.flowsInto, WORKFLOW.FlowBC))
        workflow.add((WORKFLOW.FlowBC, YAWL.nextElementRef, task_c))

        workflow.add((task_c, YAWL.hasSplit, YAWL.ControlTypeXor))
        workflow.add((task_c, YAWL.flowsInto, WORKFLOW.FlowLoop))
        workflow.add((WORKFLOW.FlowLoop, YAWL.nextElementRef, task_a))
        workflow.add((WORKFLOW.FlowLoop, YAWL.hasPredicate, WORKFLOW.LoopPred))
        workflow.add((WORKFLOW.LoopPred, YAWL.query, Literal("data['count'] < 3")))
        workflow.add((WORKFLOW.LoopPred, YAWL.ordering, Literal(1)))

        workflow.add((task_c, YAWL.flowsInto, WORKFLOW.FlowExit))
        workflow.add((WORKFLOW.FlowExit, YAWL.nextElementRef, task_exit))
        workflow.add((WORKFLOW.FlowExit, YAWL.isDefaultFlow, Literal(True)))

        # Simulate 4 iterations (0, 1, 2 loop; 3 exits)
        for iteration in range(4):
            workflow.add((task_c, KGC.hasToken, Literal(True)))
            ctx = TransactionContext(
                tx_id=f"tx-iter-{iteration}", actor="test-agent", prev_hash=GENESIS_HASH, data={"count": iteration}
            )

            config = VerbConfig(verb="filter", selection_mode="exactlyOne")
            delta = Kernel.filter(workflow, task_c, ctx, config)

            # Apply mutations to workflow
            for triple in delta.removals:
                workflow.remove(triple)
            for triple in delta.additions:
                workflow.add(triple)

            # Verify loop behavior
            if iteration < 3:  # iterations 0, 1, 2 satisfy count < 3
                # Should loop back
                assert (task_a, KGC.hasToken, Literal(True)) in workflow
            else:  # iteration 3 fails count < 3
                # Should exit on final iteration
                assert (task_exit, KGC.hasToken, Literal(True)) in workflow

    def test_nested_loops_with_independent_conditions(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Nested loops with independent exit conditions."""
        # Arrange: Outer loop with inner loop
        workflow = Graph()
        outer_start = WORKFLOW.OuterStart
        inner_loop = WORKFLOW.InnerLoop
        inner_decision = WORKFLOW.InnerDecision
        outer_decision = WORKFLOW.OuterDecision
        task_exit = WORKFLOW.TaskExit

        # Outer loop: outer_start → inner_loop → outer_decision → [back or exit]
        workflow.add((outer_start, YAWL.flowsInto, WORKFLOW.FlowOI))
        workflow.add((WORKFLOW.FlowOI, YAWL.nextElementRef, inner_loop))

        # Inner loop: inner_loop → inner_decision → [back to inner_loop or continue]
        workflow.add((inner_loop, YAWL.flowsInto, WORKFLOW.FlowID))
        workflow.add((WORKFLOW.FlowID, YAWL.nextElementRef, inner_decision))

        workflow.add((inner_decision, YAWL.hasSplit, YAWL.ControlTypeXor))
        workflow.add((inner_decision, YAWL.flowsInto, WORKFLOW.FlowInnerLoop))
        workflow.add((WORKFLOW.FlowInnerLoop, YAWL.nextElementRef, inner_loop))
        workflow.add((WORKFLOW.FlowInnerLoop, YAWL.hasPredicate, WORKFLOW.InnerPred))
        workflow.add((WORKFLOW.InnerPred, YAWL.query, Literal("data['inner'] < 2")))
        workflow.add((WORKFLOW.InnerPred, YAWL.ordering, Literal(1)))

        workflow.add((inner_decision, YAWL.flowsInto, WORKFLOW.FlowOD))
        workflow.add((WORKFLOW.FlowOD, YAWL.nextElementRef, outer_decision))
        workflow.add((WORKFLOW.FlowOD, YAWL.isDefaultFlow, Literal(True)))

        # Outer loop back-edge
        workflow.add((outer_decision, YAWL.hasSplit, YAWL.ControlTypeXor))
        workflow.add((outer_decision, YAWL.flowsInto, WORKFLOW.FlowOuterLoop))
        workflow.add((WORKFLOW.FlowOuterLoop, YAWL.nextElementRef, outer_start))
        workflow.add((WORKFLOW.FlowOuterLoop, YAWL.hasPredicate, WORKFLOW.OuterPred))
        workflow.add((WORKFLOW.OuterPred, YAWL.query, Literal("data['outer'] < 2")))
        workflow.add((WORKFLOW.OuterPred, YAWL.ordering, Literal(1)))

        workflow.add((outer_decision, YAWL.flowsInto, WORKFLOW.FlowExit))
        workflow.add((WORKFLOW.FlowExit, YAWL.nextElementRef, task_exit))
        workflow.add((WORKFLOW.FlowExit, YAWL.isDefaultFlow, Literal(True)))

        # Act: Test inner loop exit
        workflow.add((inner_decision, KGC.hasToken, Literal(True)))
        ctx = TransactionContext(
            tx_id="tx-inner-exit", actor="test-agent", prev_hash=GENESIS_HASH, data={"inner": 3, "outer": 1}
        )

        config = VerbConfig(verb="filter", selection_mode="exactlyOne")
        delta = Kernel.filter(workflow, inner_decision, ctx, config)

        # Assert: Inner loop exits to outer decision
        token_targets = [triple[0] for triple in delta.additions if triple[1] == KGC.hasToken]
        assert outer_decision in token_targets, "Inner loop should exit to outer decision"
        assert inner_loop not in token_targets, "Inner loop should NOT continue"

    def test_loop_with_complex_predicate(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Loop with complex multi-variable predicate."""
        # Arrange: Loop with AND/OR conditions
        workflow = Graph()
        task_loop = WORKFLOW.TaskLoop
        task_body = WORKFLOW.TaskBody
        task_decision = WORKFLOW.LoopDecision
        task_exit = WORKFLOW.TaskExit

        workflow.add((task_loop, YAWL.flowsInto, WORKFLOW.FlowBody))
        workflow.add((WORKFLOW.FlowBody, YAWL.nextElementRef, task_body))

        workflow.add((task_body, YAWL.flowsInto, WORKFLOW.FlowDec))
        workflow.add((WORKFLOW.FlowDec, YAWL.nextElementRef, task_decision))

        workflow.add((task_decision, YAWL.hasSplit, YAWL.ControlTypeXor))
        workflow.add((task_decision, YAWL.flowsInto, WORKFLOW.FlowBack))
        workflow.add((WORKFLOW.FlowBack, YAWL.nextElementRef, task_loop))
        workflow.add((WORKFLOW.FlowBack, YAWL.hasPredicate, WORKFLOW.ComplexPred))
        workflow.add((WORKFLOW.ComplexPred, YAWL.query, Literal("data['x'] > 5 and data['y'] < 10")))
        workflow.add((WORKFLOW.ComplexPred, YAWL.ordering, Literal(1)))

        workflow.add((task_decision, YAWL.flowsInto, WORKFLOW.FlowExit))
        workflow.add((WORKFLOW.FlowExit, YAWL.nextElementRef, task_exit))
        workflow.add((WORKFLOW.FlowExit, YAWL.isDefaultFlow, Literal(True)))

        workflow.add((task_decision, KGC.hasToken, Literal(True)))

        # Act: Test with x=7, y=8 (both conditions true)
        ctx = TransactionContext(
            tx_id="tx-complex-true", actor="test-agent", prev_hash=GENESIS_HASH, data={"x": 7, "y": 8}
        )

        config = VerbConfig(verb="filter", selection_mode="exactlyOne")
        delta = Kernel.filter(workflow, task_decision, ctx, config)

        # Assert: Should loop back
        token_targets = [triple[0] for triple in delta.additions if triple[1] == KGC.hasToken]
        assert task_loop in token_targets, "Complex predicate true should loop"

        # Act: Test with x=3, y=8 (first condition false)
        workflow.add((task_decision, KGC.hasToken, Literal(True)))
        ctx2 = TransactionContext(
            tx_id="tx-complex-false", actor="test-agent", prev_hash=GENESIS_HASH, data={"x": 3, "y": 8}
        )

        delta2 = Kernel.filter(workflow, task_decision, ctx2, config)

        # Assert: Should exit
        token_targets2 = [triple[0] for triple in delta2.additions if triple[1] == KGC.hasToken]
        assert task_exit in token_targets2, "Complex predicate false should exit"


class TestWCP11ImplicitTermination:
    """Tests for WCP-11: Implicit Termination (Case terminates when no tokens remain).

    Pattern: yawl:ImplicitTermination → Void(cancellationScope="case")
    Behavior: Workflow case completes naturally when all execution paths finish.
    """

    def test_simple_sequence_terminates_naturally(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Simple sequence A → B → C terminates when C completes."""
        # Arrange: Linear workflow with explicit end node
        workflow = Graph()
        task_a = WORKFLOW.TaskA
        task_b = WORKFLOW.TaskB
        task_c = WORKFLOW.TaskC
        task_end = WORKFLOW.TaskEnd

        workflow.add((task_a, YAWL.flowsInto, WORKFLOW.FlowAB))
        workflow.add((WORKFLOW.FlowAB, YAWL.nextElementRef, task_b))

        workflow.add((task_b, YAWL.flowsInto, WORKFLOW.FlowBC))
        workflow.add((WORKFLOW.FlowBC, YAWL.nextElementRef, task_c))

        workflow.add((task_c, YAWL.flowsInto, WORKFLOW.FlowCEnd))
        workflow.add((WORKFLOW.FlowCEnd, YAWL.nextElementRef, task_end))

        # Token at task_c
        workflow.add((task_c, KGC.hasToken, Literal(True)))

        # Act: Execute transmute to move to end node
        config = VerbConfig(verb="transmute")
        delta = Kernel.transmute(workflow, task_c, transaction_context, config)

        # Assert: Token moved to end node, task_c marked completed
        assert len(delta.additions) >= 2, "Should add token to end and mark completion"
        assert (task_end, KGC.hasToken, Literal(True)) in delta.additions
        assert (task_c, KGC.completedAt, Literal(transaction_context.tx_id)) in delta.additions
        assert (task_c, KGC.hasToken, Literal(True)) in delta.removals

        # Apply mutations
        for triple in delta.removals:
            workflow.remove(triple)
        for triple in delta.additions:
            workflow.add(triple)

        # Now transmute end node with no successors (implicit termination)
        delta_end = Kernel.transmute(workflow, task_end, transaction_context, config)

        # Assert: Empty delta when no successors (implicit termination)
        assert len(delta_end.additions) == 0, "No successors means implicit termination"
        assert len(delta_end.removals) == 0, "Token remains but workflow is complete"

        # Verify token still at end (case is implicitly terminated)
        active_tokens = list(workflow.triples((None, KGC.hasToken, Literal(True))))
        assert len(active_tokens) == 1, "Token at end node indicates implicit termination"
        assert (task_end, KGC.hasToken, Literal(True)) in workflow

    def test_parallel_branches_terminate_when_all_complete(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Parallel split A → {B, C} terminates when both B and C complete."""
        # Arrange: AND-split with end nodes for each branch
        workflow = Graph()
        task_a = WORKFLOW.TaskA
        task_b = WORKFLOW.TaskB
        task_c = WORKFLOW.TaskC
        end_b = WORKFLOW.EndB
        end_c = WORKFLOW.EndC

        # A splits to B and C
        workflow.add((task_a, YAWL.hasSplit, YAWL.ControlTypeAnd))
        workflow.add((task_a, YAWL.flowsInto, WORKFLOW.FlowAB))
        workflow.add((WORKFLOW.FlowAB, YAWL.nextElementRef, task_b))
        workflow.add((task_a, YAWL.flowsInto, WORKFLOW.FlowAC))
        workflow.add((WORKFLOW.FlowAC, YAWL.nextElementRef, task_c))

        # B → EndB, C → EndC
        workflow.add((task_b, YAWL.flowsInto, WORKFLOW.FlowBEnd))
        workflow.add((WORKFLOW.FlowBEnd, YAWL.nextElementRef, end_b))
        workflow.add((task_c, YAWL.flowsInto, WORKFLOW.FlowCEnd))
        workflow.add((WORKFLOW.FlowCEnd, YAWL.nextElementRef, end_c))

        # Both B and C have tokens (parallel execution)
        workflow.add((task_b, KGC.hasToken, Literal(True)))
        workflow.add((task_c, KGC.hasToken, Literal(True)))

        # Act: Complete task_b (move to end_b)
        config = VerbConfig(verb="transmute")
        delta_b = Kernel.transmute(workflow, task_b, transaction_context, config)

        # Apply mutations
        for triple in delta_b.removals:
            workflow.remove(triple)
        for triple in delta_b.additions:
            workflow.add(triple)

        # Verify task_c still has token, end_b has token
        assert (task_c, KGC.hasToken, Literal(True)) in workflow
        assert (end_b, KGC.hasToken, Literal(True)) in workflow

        # Act: Complete task_c (move to end_c)
        delta_c = Kernel.transmute(workflow, task_c, transaction_context, config)

        # Apply mutations
        for triple in delta_c.removals:
            workflow.remove(triple)
        for triple in delta_c.additions:
            workflow.add(triple)

        # Assert: Both branches at end nodes (implicit termination)
        active_tokens = list(workflow.triples((None, KGC.hasToken, Literal(True))))
        assert len(active_tokens) == 2, "Both branches at end nodes"
        assert (end_b, KGC.hasToken, Literal(True)) in workflow
        assert (end_c, KGC.hasToken, Literal(True)) in workflow

        # Transmute end nodes (no successors = implicit termination)
        delta_end_b = Kernel.transmute(workflow, end_b, transaction_context, config)
        delta_end_c = Kernel.transmute(workflow, end_c, transaction_context, config)

        # Both should return empty deltas (implicit termination)
        assert len(delta_end_b.additions) == 0, "No successors on end_b"
        assert len(delta_end_c.additions) == 0, "No successors on end_c"

        # Tokens remain at end nodes, indicating complete workflow
        assert (end_b, KGC.hasToken, Literal(True)) in workflow
        assert (end_c, KGC.hasToken, Literal(True)) in workflow

    def test_implicit_termination_with_or_split(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """OR-split terminates when all selected paths complete."""
        # Arrange: OR-split with multiple possible paths
        workflow = Graph()
        task_a = WORKFLOW.TaskA
        task_b = WORKFLOW.TaskB
        task_c = WORKFLOW.TaskC

        workflow.add((task_a, YAWL.hasSplit, YAWL.ControlTypeOr))
        workflow.add((task_a, YAWL.flowsInto, WORKFLOW.FlowAB))
        workflow.add((WORKFLOW.FlowAB, YAWL.nextElementRef, task_b))
        workflow.add((WORKFLOW.FlowAB, YAWL.hasPredicate, WORKFLOW.PredB))
        workflow.add((WORKFLOW.PredB, YAWL.query, Literal("data['select_b']")))
        workflow.add((WORKFLOW.PredB, YAWL.ordering, Literal(1)))

        workflow.add((task_a, YAWL.flowsInto, WORKFLOW.FlowAC))
        workflow.add((WORKFLOW.FlowAC, YAWL.nextElementRef, task_c))
        workflow.add((WORKFLOW.FlowAC, YAWL.hasPredicate, WORKFLOW.PredC))
        workflow.add((WORKFLOW.PredC, YAWL.query, Literal("data['select_c']")))
        workflow.add((WORKFLOW.PredC, YAWL.ordering, Literal(2)))

        workflow.add((task_a, KGC.hasToken, Literal(True)))

        # Act: Execute Filter (select both paths)
        ctx = TransactionContext(
            tx_id="tx-or-split", actor="test-agent", prev_hash=GENESIS_HASH, data={"select_b": True, "select_c": True}
        )

        config = VerbConfig(verb="filter", selection_mode="oneOrMore")
        delta = Kernel.filter(workflow, task_a, ctx, config)

        # Apply mutations
        for triple in delta.removals:
            workflow.remove(triple)
        for triple in delta.additions:
            workflow.add(triple)

        # Both paths selected
        assert (task_b, KGC.hasToken, Literal(True)) in workflow
        assert (task_c, KGC.hasToken, Literal(True)) in workflow

        # Act: Complete both tasks (no successors = implicit termination)
        delta_b = Kernel.transmute(workflow, task_b, transaction_context, config)
        delta_c = Kernel.transmute(workflow, task_c, transaction_context, config)

        # Assert: Empty deltas (no successors)
        assert len(delta_b.additions) == 0, "task_b has no successors"
        assert len(delta_c.additions) == 0, "task_c has no successors"

        # Tokens remain at end of paths (implicit termination condition)
        assert (task_b, KGC.hasToken, Literal(True)) in workflow
        assert (task_c, KGC.hasToken, Literal(True)) in workflow

        # This represents implicit termination: workflow is complete,
        # no more transitions possible
        active_tokens = list(workflow.triples((None, KGC.hasToken, Literal(True))))
        assert len(active_tokens) == 2, "Tokens remain at terminal nodes (implicit termination)"

    def test_implicit_termination_with_cancellation(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Case terminates when all tokens voided via cancellation."""
        # Arrange: Parallel branches with one triggering cancellation
        workflow = Graph()
        task_a = WORKFLOW.TaskA
        task_b = WORKFLOW.TaskB
        task_cancel = WORKFLOW.CancelTask

        workflow.add((task_a, YAWL.hasSplit, YAWL.ControlTypeAnd))
        workflow.add((task_a, YAWL.flowsInto, WORKFLOW.FlowAB))
        workflow.add((WORKFLOW.FlowAB, YAWL.nextElementRef, task_b))
        workflow.add((task_a, YAWL.flowsInto, WORKFLOW.FlowAC))
        workflow.add((WORKFLOW.FlowAC, YAWL.nextElementRef, task_cancel))

        # Both tasks have tokens
        workflow.add((task_b, KGC.hasToken, Literal(True)))
        workflow.add((task_cancel, KGC.hasToken, Literal(True)))

        # Act: Execute Void on cancel task with scope="case"
        config = VerbConfig(verb="void", cancellation_scope="case")
        delta = Kernel.void(workflow, task_cancel, transaction_context, config)

        # Apply mutations
        for triple in delta.removals:
            workflow.remove(triple)
        for triple in delta.additions:
            workflow.add(triple)

        # Assert: All tokens voided
        active_tokens = list(workflow.triples((None, KGC.hasToken, Literal(True))))
        assert len(active_tokens) == 0, "Case-level void removes all tokens"

        # Verify voided markers
        voided_tasks = list(workflow.triples((None, KGC.voidedAt, None)))
        assert len(voided_tasks) >= 2, "Both tasks should be marked voided"

    def test_complex_workflow_implicit_termination(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Complex workflow with splits, joins, and loops terminates naturally."""
        # Arrange: Complex topology
        # Start → AND-split → {Branch1, Branch2} → AND-join → Loop → End
        workflow = Graph()
        start = WORKFLOW.Start
        split = WORKFLOW.Split
        branch1 = WORKFLOW.Branch1
        branch2 = WORKFLOW.Branch2
        join = WORKFLOW.Join
        loop_decision = WORKFLOW.LoopDecision
        end = WORKFLOW.End

        # Start → Split
        workflow.add((start, YAWL.flowsInto, WORKFLOW.FlowStartSplit))
        workflow.add((WORKFLOW.FlowStartSplit, YAWL.nextElementRef, split))

        # Split → {Branch1, Branch2}
        workflow.add((split, YAWL.hasSplit, YAWL.ControlTypeAnd))
        workflow.add((split, YAWL.flowsInto, WORKFLOW.FlowSB1))
        workflow.add((WORKFLOW.FlowSB1, YAWL.nextElementRef, branch1))
        workflow.add((split, YAWL.flowsInto, WORKFLOW.FlowSB2))
        workflow.add((WORKFLOW.FlowSB2, YAWL.nextElementRef, branch2))

        # {Branch1, Branch2} → Join
        workflow.add((branch1, YAWL.flowsInto, WORKFLOW.FlowB1J))
        workflow.add((WORKFLOW.FlowB1J, YAWL.nextElementRef, join))
        workflow.add((branch2, YAWL.flowsInto, WORKFLOW.FlowB2J))
        workflow.add((WORKFLOW.FlowB2J, YAWL.nextElementRef, join))
        workflow.add((join, YAWL.hasJoin, YAWL.ControlTypeAnd))

        # Join → Loop
        workflow.add((join, YAWL.flowsInto, WORKFLOW.FlowJL))
        workflow.add((WORKFLOW.FlowJL, YAWL.nextElementRef, loop_decision))

        # Loop decision → [back to Split or End]
        workflow.add((loop_decision, YAWL.hasSplit, YAWL.ControlTypeXor))
        workflow.add((loop_decision, YAWL.flowsInto, WORKFLOW.FlowLoop))
        workflow.add((WORKFLOW.FlowLoop, YAWL.nextElementRef, split))
        workflow.add((WORKFLOW.FlowLoop, YAWL.hasPredicate, WORKFLOW.LoopPred))
        workflow.add((WORKFLOW.LoopPred, YAWL.query, Literal("data['continue']")))
        workflow.add((WORKFLOW.LoopPred, YAWL.ordering, Literal(1)))

        workflow.add((loop_decision, YAWL.flowsInto, WORKFLOW.FlowEnd))
        workflow.add((WORKFLOW.FlowEnd, YAWL.nextElementRef, end))
        workflow.add((WORKFLOW.FlowEnd, YAWL.isDefaultFlow, Literal(True)))

        # Simulate execution: Start with token at end (after loop exits)
        workflow.add((end, KGC.hasToken, Literal(True)))

        # Act: Complete end task (no successors = implicit termination)
        config = VerbConfig(verb="transmute")
        delta = Kernel.transmute(workflow, end, transaction_context, config)

        # Assert: Empty delta (no successors)
        assert len(delta.additions) == 0, "End node has no successors"
        assert len(delta.removals) == 0, "Token remains at end node"

        # Token remains at end node, indicating workflow completion (implicit termination)
        active_tokens = list(workflow.triples((None, KGC.hasToken, Literal(True))))
        assert len(active_tokens) == 1, "Token at end node indicates implicit termination"
        assert (end, KGC.hasToken, Literal(True)) in workflow

    def test_void_case_scope_triggers_implicit_termination(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """Void with case scope removes all tokens, triggering implicit termination."""
        # Arrange: Multiple active tasks
        workflow = Graph()
        task_a = WORKFLOW.TaskA
        task_b = WORKFLOW.TaskB
        task_c = WORKFLOW.TaskC

        workflow.add((task_a, KGC.hasToken, Literal(True)))
        workflow.add((task_b, KGC.hasToken, Literal(True)))
        workflow.add((task_c, KGC.hasToken, Literal(True)))

        # Act: Void case scope from task_a
        config = VerbConfig(verb="void", cancellation_scope="case")
        delta = Kernel.void(workflow, task_a, transaction_context, config)

        # Assert: All tokens removed
        assert len(delta.removals) == 3, "Should remove all 3 tokens"
        assert (task_a, KGC.hasToken, Literal(True)) in delta.removals
        assert (task_b, KGC.hasToken, Literal(True)) in delta.removals
        assert (task_c, KGC.hasToken, Literal(True)) in delta.removals

        # Verify voided markers added
        voided_count = sum(1 for triple in delta.additions if triple[1] == KGC.voidedAt)
        assert voided_count == 3, "All tasks should be marked voided"

        # Apply mutations
        for triple in delta.removals:
            workflow.remove(triple)
        for triple in delta.additions:
            workflow.add(triple)

        # Assert: Implicit termination (no active tokens)
        active_tokens = list(workflow.triples((None, KGC.hasToken, Literal(True))))
        assert len(active_tokens) == 0, "Case voided, implicit termination achieved"
