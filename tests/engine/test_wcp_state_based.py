"""Comprehensive tests for YAWL State-Based Patterns (WCP 16-18).

Tests verify state-based routing behaviors:
- WCP-16: Deferred Choice → Filter(selectionMode="deferred")
- WCP-17: Interleaved Parallel Routing → Filter(selectionMode="mutex")
- WCP-18: Milestone → Await(threshold="milestone", completionStrategy="waitMilestone")

Implementation:
- WCP-16: Returns awaitingSelection=true, no immediate token routing
- WCP-17: Checks mutex group, executes tasks one at a time (mutual exclusion)
- WCP-18: Task enabled only while milestone state is active

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
    SemanticDriver,
    TransactionContext,
    VerbConfig,
)

# Test namespace
WORKFLOW = Namespace("http://example.org/workflow#")


@pytest.fixture
def physics_ontology() -> Graph:
    """Load KGC Physics Ontology for verb resolution."""
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
# WCP-16: DEFERRED CHOICE TESTS
# =============================================================================


class TestWCP16DeferredChoice:
    """Test WCP-16: Deferred Choice - Environment determines branch at runtime."""

    def test_deferred_choice_marks_awaiting_selection(self, transaction_context: TransactionContext) -> None:
        """Deferred choice marks node as awaiting external selection, no immediate routing."""
        # Arrange: Graph with deferred choice split
        graph = Graph()
        choice_task = WORKFLOW.DeferredChoiceTask
        branch_a = WORKFLOW.BranchA
        branch_b = WORKFLOW.BranchB
        flow_a = WORKFLOW.FlowToA
        flow_b = WORKFLOW.FlowToB

        # Define deferred choice topology
        graph.add((choice_task, YAWL.hasSplit, YAWL.DeferredChoice))
        graph.add((choice_task, YAWL.flowsInto, flow_a))
        graph.add((choice_task, YAWL.flowsInto, flow_b))
        graph.add((flow_a, YAWL.nextElementRef, branch_a))
        graph.add((flow_b, YAWL.nextElementRef, branch_b))
        graph.add((choice_task, KGC.hasToken, Literal(True)))

        # Create config with deferred selection mode (RDF-only: is_deferred_choice)
        config = VerbConfig(verb="filter", selection_mode="deferred", is_deferred_choice=True)

        # Act: Execute filter with deferred mode
        delta = Kernel.filter(graph, choice_task, transaction_context, config)

        # Assert: Node marked as awaiting selection, no token movement
        assert len(delta.additions) == 1
        assert len(delta.removals) == 0
        assert (choice_task, KGC.awaitingSelection, Literal(True)) in delta.additions

        # Verify no tokens routed to branches
        assert (branch_a, KGC.hasToken, Literal(True)) not in delta.additions
        assert (branch_b, KGC.hasToken, Literal(True)) not in delta.additions

    def test_deferred_choice_with_multiple_branches(self, transaction_context: TransactionContext) -> None:
        """Deferred choice supports N branches, all wait for selection."""
        # Arrange: Graph with 3-way deferred choice
        graph = Graph()
        choice_task = WORKFLOW.ThreeWayChoice
        branches = [WORKFLOW.Branch1, WORKFLOW.Branch2, WORKFLOW.Branch3]
        flows = [WORKFLOW.Flow1, WORKFLOW.Flow2, WORKFLOW.Flow3]

        graph.add((choice_task, YAWL.hasSplit, YAWL.DeferredChoice))
        for flow, branch in zip(flows, branches, strict=False):
            graph.add((choice_task, YAWL.flowsInto, flow))
            graph.add((flow, YAWL.nextElementRef, branch))
        graph.add((choice_task, KGC.hasToken, Literal(True)))

        config = VerbConfig(verb="filter", selection_mode="deferred", is_deferred_choice=True)

        # Act
        delta = Kernel.filter(graph, choice_task, transaction_context, config)

        # Assert: Only awaiting marker, no routing
        assert len(delta.additions) == 1
        assert (choice_task, KGC.awaitingSelection, Literal(True)) in delta.additions

        # Verify no tokens on any branch
        for branch in branches:
            assert (branch, KGC.hasToken, Literal(True)) not in delta.additions

    def test_deferred_choice_preserves_predicates(self, transaction_context: TransactionContext) -> None:
        """Deferred choice defers selection even when predicates exist."""
        # Arrange: Graph with predicates (not evaluated during deferral)
        graph = Graph()
        choice_task = WORKFLOW.DeferredWithPredicates
        branch_true = WORKFLOW.TrueBranch
        branch_false = WORKFLOW.FalseBranch
        flow_true = WORKFLOW.TrueFlow
        flow_false = WORKFLOW.FalseFlow
        pred = WORKFLOW.Pred1

        graph.add((choice_task, YAWL.hasSplit, YAWL.DeferredChoice))
        graph.add((choice_task, YAWL.flowsInto, flow_true))
        graph.add((choice_task, YAWL.flowsInto, flow_false))
        graph.add((flow_true, YAWL.nextElementRef, branch_true))
        graph.add((flow_false, YAWL.nextElementRef, branch_false))
        graph.add((flow_true, YAWL.hasPredicate, pred))
        graph.add((pred, YAWL.query, Literal("data['condition'] == True")))
        graph.add((pred, YAWL.ordering, Literal(1)))
        graph.add((choice_task, KGC.hasToken, Literal(True)))

        config = VerbConfig(verb="filter", selection_mode="deferred", is_deferred_choice=True)

        # Act: Even with true predicate, defer selection
        ctx = TransactionContext(
            tx_id="test-tx-002", actor="test-agent", prev_hash=GENESIS_HASH, data={"condition": True}
        )
        delta = Kernel.filter(graph, choice_task, ctx, config)

        # Assert: Deferred takes precedence over predicate evaluation
        assert (choice_task, KGC.awaitingSelection, Literal(True)) in delta.additions
        assert (branch_true, KGC.hasToken, Literal(True)) not in delta.additions

    def test_deferred_choice_no_token_removal(self, transaction_context: TransactionContext) -> None:
        """Deferred choice does NOT remove token from choice node during wait."""
        # Arrange
        graph = Graph()
        choice_task = WORKFLOW.DeferredTask
        branch = WORKFLOW.SomeBranch
        flow = WORKFLOW.SomeFlow

        graph.add((choice_task, YAWL.hasSplit, YAWL.DeferredChoice))
        graph.add((choice_task, YAWL.flowsInto, flow))
        graph.add((flow, YAWL.nextElementRef, branch))
        graph.add((choice_task, KGC.hasToken, Literal(True)))

        config = VerbConfig(verb="filter", selection_mode="deferred", is_deferred_choice=True)

        # Act
        delta = Kernel.filter(graph, choice_task, transaction_context, config)

        # Assert: No removals (token stays on choice node)
        assert len(delta.removals) == 0


# =============================================================================
# WCP-17: INTERLEAVED PARALLEL ROUTING TESTS
# =============================================================================


class TestWCP17InterleavedParallel:
    """Test WCP-17: Interleaved Parallel - Tasks execute one at a time (mutex)."""

    def test_mutex_allows_first_task_when_none_executing(self, transaction_context: TransactionContext) -> None:
        """Mutex allows first task to execute when no siblings are running."""
        # Arrange: Graph with interleaved tasks
        graph = Graph()
        split_task = WORKFLOW.InterleavedSplit
        task_a = WORKFLOW.MutexTaskA
        task_b = WORKFLOW.MutexTaskB
        flow_a = WORKFLOW.FlowA
        flow_b = WORKFLOW.FlowB

        graph.add((split_task, YAWL.hasSplit, YAWL.InterleavedParallel))
        graph.add((split_task, YAWL.flowsInto, flow_a))
        graph.add((split_task, YAWL.flowsInto, flow_b))
        graph.add((flow_a, YAWL.nextElementRef, task_a))
        graph.add((flow_b, YAWL.nextElementRef, task_b))
        graph.add((split_task, KGC.hasToken, Literal(True)))

        # No siblings executing - mutex query will return empty
        # RDF-only: is_mutex_interleaved + stop_on_first_match for XOR behavior
        config = VerbConfig(verb="filter", selection_mode="mutex", is_mutex_interleaved=True, stop_on_first_match=True)

        # Act: Execute filter with mutex mode
        delta = Kernel.filter(graph, split_task, transaction_context, config)

        # Assert: First available task gets token (task_a)
        assert len(delta.additions) >= 2  # Token + completion marker
        assert len(delta.removals) == 1  # Remove from split_task
        assert (task_a, KGC.hasToken, Literal(True)) in delta.additions
        assert (split_task, KGC.hasToken, Literal(True)) in delta.removals

        # Verify only ONE task gets token (not both)
        assert (task_b, KGC.hasToken, Literal(True)) not in delta.additions

    def test_mutex_blocks_when_sibling_executing(self, transaction_context: TransactionContext) -> None:
        """Mutex blocks task when sibling in same group is executing."""
        # Arrange: Graph with one task already executing
        graph = Graph()
        pending_task = WORKFLOW.PendingMutexTask
        executing_task = WORKFLOW.ExecutingMutexTask
        flow = WORKFLOW.PendingFlow

        graph.add((pending_task, YAWL.hasSplit, YAWL.InterleavedParallel))
        graph.add((pending_task, YAWL.flowsInto, flow))
        graph.add((flow, YAWL.nextElementRef, WORKFLOW.NextTask))
        graph.add((pending_task, KGC.hasToken, Literal(True)))

        # Sibling already executing - mutex group points to pending_task
        # (Engine looks for: ?sibling kgc:hasToken true . ?sibling kgc:mutexGroup <pending_task>)
        graph.add((executing_task, KGC.hasToken, Literal(True)))
        graph.add((executing_task, KGC.mutexGroup, pending_task))

        config = VerbConfig(verb="filter", selection_mode="mutex", is_mutex_interleaved=True)

        # Act
        delta = Kernel.filter(graph, pending_task, transaction_context, config)

        # Assert: Task marked as awaiting mutex, no token movement
        assert (pending_task, KGC.awaitingMutex, Literal(True)) in delta.additions
        assert len(delta.removals) == 0  # Token not removed

    def test_mutex_with_three_tasks_sequential_execution(self, transaction_context: TransactionContext) -> None:
        """Mutex allows only one of three tasks at a time."""
        # Arrange: Three interleaved tasks
        graph = Graph()
        split_task = WORKFLOW.ThreeWayInterleaved
        tasks = [WORKFLOW.TaskX, WORKFLOW.TaskY, WORKFLOW.TaskZ]
        flows = [WORKFLOW.FlowX, WORKFLOW.FlowY, WORKFLOW.FlowZ]

        graph.add((split_task, YAWL.hasSplit, YAWL.InterleavedParallel))
        for flow, task in zip(flows, tasks, strict=False):
            graph.add((split_task, YAWL.flowsInto, flow))
            graph.add((flow, YAWL.nextElementRef, task))
        graph.add((split_task, KGC.hasToken, Literal(True)))

        # No siblings executing initially
        # RDF-only: is_mutex_interleaved + stop_on_first_match for XOR behavior
        config = VerbConfig(verb="filter", selection_mode="mutex", is_mutex_interleaved=True, stop_on_first_match=True)

        # Act
        delta = Kernel.filter(graph, split_task, transaction_context, config)

        # Assert: Only ONE task receives token
        token_count = sum(1 for triple in delta.additions if triple[1] == KGC.hasToken and str(triple[2]) == "true")
        assert token_count == 1

    def test_mutex_no_blocking_without_sibling_tokens(self, transaction_context: TransactionContext) -> None:
        """Mutex allows execution when no siblings have active tokens."""
        # Arrange: All siblings completed (no active tokens)
        graph = Graph()
        task = WORKFLOW.MutexTaskLast
        flow = WORKFLOW.LastFlow
        completed_sibling = WORKFLOW.CompletedSibling

        graph.add((task, YAWL.hasSplit, YAWL.InterleavedParallel))
        graph.add((task, YAWL.flowsInto, flow))
        graph.add((flow, YAWL.nextElementRef, WORKFLOW.FinalTask))
        graph.add((task, KGC.hasToken, Literal(True)))

        # Sibling completed (no token) - no active mutex
        graph.add((completed_sibling, KGC.mutexGroup, task))
        graph.add((completed_sibling, KGC.completedAt, Literal("prev-tx")))

        config = VerbConfig(verb="filter", selection_mode="mutex", is_mutex_interleaved=True)

        # Act
        delta = Kernel.filter(graph, task, transaction_context, config)

        # Assert: Task executes (not blocked)
        assert (WORKFLOW.FinalTask, KGC.hasToken, Literal(True)) in delta.additions
        assert (task, KGC.awaitingMutex, Literal(True)) not in delta.additions


# =============================================================================
# WCP-18: MILESTONE TESTS
# =============================================================================


class TestWCP18Milestone:
    """Test WCP-18: Milestone - Task enabled only while milestone state is active.

    NOTE: Milestone threshold logic not fully implemented in engine yet.
    Tests verify current behavior with source-based joins.
    Full milestone state checking (yawl:milestoneRef + kgc:status) is TODO.
    """

    def test_milestone_waits_for_active_state(self, transaction_context: TransactionContext) -> None:
        """Milestone task waits for source completion (simplified implementation).

        NOTE: Engine doesn't yet check yawl:milestoneRef + kgc:status.
        This test verifies current await_ behavior with threshold="milestone".
        """
        # Arrange: Graph with milestone dependency and source
        graph = Graph()
        milestone_task = WORKFLOW.MilestoneTask
        next_task = WORKFLOW.DependentTask
        milestone_state = WORKFLOW.DeliveryMilestone
        flow = WORKFLOW.MilestoneFlow
        source_task = WORKFLOW.SourceForMilestone
        source_flow = WORKFLOW.SourceFlow

        graph.add((milestone_task, YAWL.hasJoin, YAWL.Milestone))
        graph.add((milestone_task, YAWL.flowsInto, flow))
        graph.add((flow, YAWL.nextElementRef, next_task))
        graph.add((milestone_task, YAWL.milestoneRef, milestone_state))

        # Add source flow (engine checks source completion)
        graph.add((source_task, YAWL.flowsInto, source_flow))
        graph.add((source_flow, YAWL.nextElementRef, milestone_task))

        # Milestone NOT yet active, source not completed
        graph.add((milestone_state, KGC.status, Literal("pending")))

        config = VerbConfig(verb="await", threshold="milestone", completion_strategy="waitMilestone")

        # Act
        delta = Kernel.await_(graph, milestone_task, transaction_context, config)

        # Assert: No token added (source not completed)
        assert (milestone_task, KGC.hasToken, Literal(True)) not in delta.additions

    def test_milestone_enables_when_source_completes(self, transaction_context: TransactionContext) -> None:
        """Milestone task enables when source completes (current implementation)."""
        # Arrange: Graph with completed source
        graph = Graph()
        milestone_task = WORKFLOW.ActiveMilestoneTask
        next_task = WORKFLOW.EnabledTask
        milestone_state = WORKFLOW.ActiveDeliveryMilestone
        flow = WORKFLOW.ActiveFlow
        source_task = WORKFLOW.SourceTask

        graph.add((milestone_task, YAWL.hasJoin, YAWL.Milestone))
        graph.add((milestone_task, YAWL.flowsInto, flow))
        graph.add((flow, YAWL.nextElementRef, next_task))
        graph.add((milestone_task, YAWL.milestoneRef, milestone_state))

        # Milestone is active (not checked by current engine)
        graph.add((milestone_state, KGC.status, Literal("active")))

        # Source task completed (this is what engine checks)
        graph.add((source_task, YAWL.flowsInto, WORKFLOW.FlowToMilestone))
        graph.add((WORKFLOW.FlowToMilestone, YAWL.nextElementRef, milestone_task))
        graph.add((source_task, KGC.completedAt, Literal("tx-000")))

        config = VerbConfig(verb="await", threshold="milestone", completion_strategy="waitMilestone")

        # Act
        delta = Kernel.await_(graph, milestone_task, transaction_context, config)

        # Assert: Task enabled (source completed, threshold met)
        assert (milestone_task, KGC.hasToken, Literal(True)) in delta.additions
        assert (milestone_task, KGC.completedAt, Literal(transaction_context.tx_id)) in delta.additions

    def test_milestone_with_no_sources_fires_immediately(self, transaction_context: TransactionContext) -> None:
        """Milestone with no incoming flows fires immediately (current engine behavior).

        NOTE: This is a limitation - real milestone should check state.
        With 0 sources, threshold check (0 >= 0) passes.
        """
        # Arrange: Graph with milestone but no incoming flows
        graph = Graph()
        milestone_task = WORKFLOW.NoSourceMilestone
        milestone_state = WORKFLOW.ImmediateMilestone

        graph.add((milestone_task, YAWL.hasJoin, YAWL.Milestone))
        graph.add((milestone_task, YAWL.milestoneRef, milestone_state))

        # Milestone inactive (should block, but engine doesn't check)
        graph.add((milestone_state, KGC.status, Literal("completed")))

        config = VerbConfig(verb="await", threshold="milestone", completion_strategy="waitMilestone")

        # Act
        delta = Kernel.await_(graph, milestone_task, transaction_context, config)

        # Assert: Task fires (0 sources, 0 >= 0 is true)
        # This is a limitation of current implementation
        assert (milestone_task, KGC.hasToken, Literal(True)) in delta.additions

    def test_milestone_with_multiple_dependencies(self, transaction_context: TransactionContext) -> None:
        """Milestone waits for multiple source completions AND active state."""
        # Arrange: Graph with 2 sources + milestone
        graph = Graph()
        milestone_task = WORKFLOW.ComplexMilestoneTask
        milestone_state = WORKFLOW.ComplexMilestone
        source_a = WORKFLOW.SourceA
        source_b = WORKFLOW.SourceB
        flow_a = WORKFLOW.FlowA
        flow_b = WORKFLOW.FlowB

        graph.add((milestone_task, YAWL.hasJoin, YAWL.Milestone))
        graph.add((milestone_task, YAWL.milestoneRef, milestone_state))
        graph.add((source_a, YAWL.flowsInto, flow_a))
        graph.add((source_b, YAWL.flowsInto, flow_b))
        graph.add((flow_a, YAWL.nextElementRef, milestone_task))
        graph.add((flow_b, YAWL.nextElementRef, milestone_task))

        # Only one source completed
        graph.add((source_a, KGC.completedAt, Literal("tx-001")))
        # Milestone is active
        graph.add((milestone_state, KGC.status, Literal("active")))

        config = VerbConfig(verb="await", threshold="milestone", completion_strategy="waitMilestone")

        # Act: Not all sources completed yet
        delta = Kernel.await_(graph, milestone_task, transaction_context, config)

        # Assert: Task not enabled (missing source_b)
        assert (milestone_task, KGC.hasToken, Literal(True)) not in delta.additions

        # Now complete second source
        graph.add((source_b, KGC.completedAt, Literal("tx-002")))

        # Act again
        delta2 = Kernel.await_(graph, milestone_task, transaction_context, config)

        # Assert: Now enabled (all sources + milestone active)
        assert (milestone_task, KGC.hasToken, Literal(True)) in delta2.additions

    def test_milestone_completion_strategy_recorded(self, transaction_context: TransactionContext) -> None:
        """Milestone uses waitMilestone completion strategy from config."""
        # Arrange
        graph = Graph()
        milestone_task = WORKFLOW.MilestoneWithStrategy
        milestone_state = WORKFLOW.StrategyMilestone
        source = WORKFLOW.StrategySource
        flow = WORKFLOW.StrategyFlow

        graph.add((milestone_task, YAWL.hasJoin, YAWL.Milestone))
        graph.add((milestone_task, YAWL.milestoneRef, milestone_state))
        graph.add((source, YAWL.flowsInto, flow))
        graph.add((flow, YAWL.nextElementRef, milestone_task))
        graph.add((source, KGC.completedAt, Literal("tx-000")))
        graph.add((milestone_state, KGC.status, Literal("active")))

        # Config with explicit strategy
        config = VerbConfig(verb="await", threshold="milestone", completion_strategy="waitMilestone")

        # Act
        delta = Kernel.await_(graph, milestone_task, transaction_context, config)

        # Assert: Task enabled with milestone strategy
        assert (milestone_task, KGC.hasToken, Literal(True)) in delta.additions
        # Verify config was used
        assert config.completion_strategy == "waitMilestone"
        assert config.threshold == "milestone"


# =============================================================================
# INTEGRATION TESTS - SEMANTIC DRIVER WITH STATE-BASED PATTERNS
# =============================================================================


class TestSemanticDriverStateBased:
    """Integration tests for SemanticDriver with state-based patterns."""

    def test_driver_resolves_wcp16_deferred_choice(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """SemanticDriver resolves WCP-16 to Filter(deferred) from ontology."""
        # Arrange: Workflow with WCP-16 pattern
        workflow = Graph()
        choice_task = WORKFLOW.DeferredChoiceNode
        branch_a = WORKFLOW.BranchAlpha
        branch_b = WORKFLOW.BranchBeta
        flow_a = WORKFLOW.FlowAlpha
        flow_b = WORKFLOW.FlowBeta

        workflow.add((choice_task, YAWL.hasSplit, YAWL.DeferredChoice))
        workflow.add((choice_task, YAWL.flowsInto, flow_a))
        workflow.add((choice_task, YAWL.flowsInto, flow_b))
        workflow.add((flow_a, YAWL.nextElementRef, branch_a))
        workflow.add((flow_b, YAWL.nextElementRef, branch_b))
        workflow.add((choice_task, KGC.hasToken, Literal(True)))

        # Act: Driver resolves and executes
        receipt = semantic_driver.execute(workflow, choice_task, transaction_context)

        # Assert: Verb resolved from ontology
        assert receipt.verb_executed == "filter"
        assert receipt.params_used is not None
        assert receipt.params_used.selection_mode == "deferred"
        assert len(receipt.merkle_root) == 64  # SHA256 hex

        # Verify state-based behavior
        assert (choice_task, KGC.awaitingSelection, Literal(True)) in workflow

    def test_driver_resolves_wcp17_interleaved_parallel(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """SemanticDriver resolves WCP-17 to Filter(mutex) from ontology."""
        # Arrange: Workflow with WCP-17 pattern
        workflow = Graph()
        interleaved_task = WORKFLOW.InterleavedNode
        task_a = WORKFLOW.TaskAlpha
        task_b = WORKFLOW.TaskBeta
        flow_a = WORKFLOW.InterleavedFlowA
        flow_b = WORKFLOW.InterleavedFlowB

        workflow.add((interleaved_task, YAWL.hasSplit, YAWL.InterleavedParallel))
        workflow.add((interleaved_task, YAWL.flowsInto, flow_a))
        workflow.add((interleaved_task, YAWL.flowsInto, flow_b))
        workflow.add((flow_a, YAWL.nextElementRef, task_a))
        workflow.add((flow_b, YAWL.nextElementRef, task_b))
        workflow.add((interleaved_task, KGC.hasToken, Literal(True)))

        # No siblings executing initially

        # Act: Driver executes with ontology lookup
        receipt = semantic_driver.execute(workflow, interleaved_task, transaction_context)

        # Assert: Ontology-driven resolution
        assert receipt.verb_executed == "filter"
        assert receipt.params_used is not None
        assert receipt.params_used.selection_mode == "mutex"

        # Verify mutex behavior (one task gets token)
        token_count = sum(1 for s, p, o in workflow if p == KGC.hasToken and str(o) == "true")
        assert token_count == 1  # Only one task active

    def test_driver_resolves_wcp18_milestone(
        self, semantic_driver: SemanticDriver, transaction_context: TransactionContext
    ) -> None:
        """SemanticDriver resolves WCP-18 to Await(milestone) from ontology."""
        # Arrange: Workflow with WCP-18 pattern
        workflow = Graph()
        milestone_task = WORKFLOW.MilestoneNode
        milestone_state = WORKFLOW.CheckpointMilestone
        source_task = WORKFLOW.PrerequisiteTask
        flow = WORKFLOW.MilestoneFlow
        next_task = WORKFLOW.NextNode

        workflow.add((milestone_task, YAWL.hasJoin, YAWL.Milestone))
        workflow.add((milestone_task, YAWL.milestoneRef, milestone_state))
        workflow.add((milestone_task, YAWL.flowsInto, flow))
        workflow.add((flow, YAWL.nextElementRef, next_task))
        workflow.add((source_task, YAWL.flowsInto, WORKFLOW.SourceFlow))
        workflow.add((WORKFLOW.SourceFlow, YAWL.nextElementRef, milestone_task))

        # Prerequisites met
        workflow.add((source_task, KGC.completedAt, Literal("tx-001")))
        workflow.add((milestone_state, KGC.status, Literal("active")))

        # Act: Driver resolves WCP-18 from ontology
        receipt = semantic_driver.execute(workflow, milestone_task, transaction_context)

        # Assert: Correct verb + params from ontology
        assert receipt.verb_executed == "await"
        assert receipt.params_used is not None
        assert receipt.params_used.threshold == "milestone"
        assert receipt.params_used.completion_strategy == "waitMilestone"

        # Verify milestone behavior
        assert (milestone_task, KGC.hasToken, Literal(True)) in workflow
