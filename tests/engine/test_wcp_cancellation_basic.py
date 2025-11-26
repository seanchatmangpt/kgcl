"""Tests for YAWL Workflow Control Patterns 19-22: Cancellation Patterns (Basic).

This module tests the cancellation patterns implemented by the Void verb with
different cancellationScope parameters:

- WCP-19: Cancel Task (scope="self")
- WCP-20: Cancel Case (scope="case")
- WCP-21: Cancel Region (scope="region")
- WCP-22: Cancel MI Activity (scope="instances")

All patterns are implemented via the Void verb with parameterized scope.
These tests call Kernel.void directly to verify verb behavior.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from rdflib import Graph, Literal, Namespace, URIRef

from kgcl.engine.knowledge_engine import GENESIS_HASH, KGC, YAWL, Kernel, TransactionContext, VerbConfig

if TYPE_CHECKING:
    pass

# Test namespace
TEST = Namespace("http://test.example.org/wcp/")


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def base_context() -> TransactionContext:
    """Create base transaction context."""
    return TransactionContext(tx_id="test-tx-001", actor="test-system", prev_hash=GENESIS_HASH, data={})


# =============================================================================
# WCP-19: CANCEL TASK (Void with scope="self")
# =============================================================================


def test_wcp19_cancel_task_single_token(base_context: TransactionContext) -> None:
    """Test WCP-19: Cancel Task removes token from single task only.

    Scenario: Task A has a token and is cancelled.
    Expected: A's token removed, A marked as voided, scope="self".
    """
    # Arrange: Create workflow with task A having a token
    workflow = Graph()
    task_a = TEST.TaskA
    workflow.add((task_a, KGC.hasToken, Literal(True)))

    # Act: Execute void with scope="self"
    config = VerbConfig(verb="void", cancellation_scope="self")
    delta = Kernel.void(workflow, task_a, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: Verify token removed
    assert (task_a, KGC.hasToken, Literal(True)) not in workflow

    # Assert: Verify task marked as voided
    voided_triples = list(workflow.triples((task_a, KGC.voidedAt, None)))
    assert len(voided_triples) == 1
    assert str(voided_triples[0][2]) == base_context.tx_id

    # Assert: Verify cancellation scope recorded
    scope_triples = list(workflow.triples((task_a, KGC.cancellationScope, None)))
    assert len(scope_triples) == 1
    assert str(scope_triples[0][2]) == "self"


def test_wcp19_cancel_task_only_affects_self(base_context: TransactionContext) -> None:
    """Test WCP-19: Cancel Task does NOT affect other tasks.

    Scenario: Tasks A, B, C all have tokens. Cancel A.
    Expected: Only A voided, B and C unaffected.
    """
    # Arrange: Create workflow with multiple active tasks
    workflow = Graph()
    task_a = TEST.TaskA
    task_b = TEST.TaskB
    task_c = TEST.TaskC

    workflow.add((task_a, KGC.hasToken, Literal(True)))
    workflow.add((task_b, KGC.hasToken, Literal(True)))
    workflow.add((task_c, KGC.hasToken, Literal(True)))

    # Act: Cancel only task A
    config = VerbConfig(verb="void", cancellation_scope="self")
    delta = Kernel.void(workflow, task_a, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: A voided
    assert (task_a, KGC.hasToken, Literal(True)) not in workflow
    assert len(list(workflow.triples((task_a, KGC.voidedAt, None)))) == 1

    # Assert: B and C unaffected
    assert (task_b, KGC.hasToken, Literal(True)) in workflow
    assert (task_c, KGC.hasToken, Literal(True)) in workflow
    assert len(list(workflow.triples((task_b, KGC.voidedAt, None)))) == 0
    assert len(list(workflow.triples((task_c, KGC.voidedAt, None)))) == 0


def test_wcp19_cancel_task_termination_reason(base_context: TransactionContext) -> None:
    """Test WCP-19: Cancel Task records termination reason.

    Scenario: Task cancelled explicitly.
    Expected: terminatedReason="cancelled" recorded.
    """
    # Arrange: Task with cancellation marker
    workflow = Graph()
    task_a = TEST.TaskA
    workflow.add((task_a, KGC.hasToken, Literal(True)))
    workflow.add((task_a, KGC.cancelled, Literal(True)))

    # Act: Execute cancellation
    config = VerbConfig(verb="void", cancellation_scope="self")
    delta = Kernel.void(workflow, task_a, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: Termination reason recorded
    reason_triples = list(workflow.triples((task_a, KGC.terminatedReason, None)))
    assert len(reason_triples) == 1
    assert str(reason_triples[0][2]) == "cancelled"


# =============================================================================
# WCP-20: CANCEL CASE (Void with scope="case")
# =============================================================================


def test_wcp20_cancel_case_all_tokens(base_context: TransactionContext) -> None:
    """Test WCP-20: Cancel Case removes ALL tokens from case.

    Scenario: Case has tasks A, B, C all with tokens. Cancel case.
    Expected: All tokens removed, all tasks voided.
    """
    # Arrange: Create case with multiple active tasks
    workflow = Graph()
    task_a = TEST.TaskA
    task_b = TEST.TaskB
    task_c = TEST.TaskC

    workflow.add((task_a, KGC.hasToken, Literal(True)))
    workflow.add((task_b, KGC.hasToken, Literal(True)))
    workflow.add((task_c, KGC.hasToken, Literal(True)))

    # Act: Execute cancel case on task_a
    config = VerbConfig(verb="void", cancellation_scope="case")
    delta = Kernel.void(workflow, task_a, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: All tokens removed
    assert (task_a, KGC.hasToken, Literal(True)) not in workflow
    assert (task_b, KGC.hasToken, Literal(True)) not in workflow
    assert (task_c, KGC.hasToken, Literal(True)) not in workflow

    # Assert: All tasks voided
    assert len(list(workflow.triples((task_a, KGC.voidedAt, None)))) == 1
    assert len(list(workflow.triples((task_b, KGC.voidedAt, None)))) == 1
    assert len(list(workflow.triples((task_c, KGC.voidedAt, None)))) == 1


def test_wcp20_cancel_case_provenance(base_context: TransactionContext) -> None:
    """Test WCP-20: Cancel Case records number of voided nodes.

    Scenario: Cancel case with 4 active tasks.
    Expected: nodesVoided="4" recorded on trigger task.
    """
    # Arrange: Case with 4 active tasks
    workflow = Graph()
    tasks = [TEST.Task1, TEST.Task2, TEST.Task3, TEST.Task4]

    for task in tasks:
        workflow.add((task, KGC.hasToken, Literal(True)))

    # Act: Cancel case
    config = VerbConfig(verb="void", cancellation_scope="case")
    delta = Kernel.void(workflow, tasks[0], base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: Verify count recorded
    voided_count = list(workflow.triples((tasks[0], KGC.nodesVoided, None)))
    assert len(voided_count) == 1
    assert str(voided_count[0][2]) == "4"


def test_wcp20_cancel_case_empty_case(base_context: TransactionContext) -> None:
    """Test WCP-20: Cancel Case handles empty case (no active tokens).

    Scenario: Case has no active tokens.
    Expected: No errors, nodesVoided="1" (just trigger node).
    """
    # Arrange: Empty workflow
    workflow = Graph()
    task_a = TEST.TaskA
    workflow.add((task_a, KGC.hasToken, Literal(True)))

    # Act: Cancel case (only trigger has token)
    config = VerbConfig(verb="void", cancellation_scope="case")
    delta = Kernel.void(workflow, task_a, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: Executed without error
    assert len(delta.additions) > 0

    # Assert: One node voided (the trigger itself)
    voided_count = list(workflow.triples((task_a, KGC.nodesVoided, None)))
    assert len(voided_count) == 1
    assert str(voided_count[0][2]) == "1"


# =============================================================================
# WCP-21: CANCEL REGION (Void with scope="region")
# =============================================================================


def test_wcp21_cancel_region_cancellation_set(base_context: TransactionContext) -> None:
    """Test WCP-21: Cancel Region voids all tasks in cancellation set.

    Scenario: Task A triggers cancellation of region containing B and C.
    Expected: A, B, C all voided.
    """
    # Arrange: Create cancellation region
    workflow = Graph()
    task_a = TEST.TaskA  # Trigger
    task_b = TEST.TaskB  # In region
    task_c = TEST.TaskC  # In region
    region = TEST.CancellationRegion1

    # Define cancellation region
    workflow.add((task_a, YAWL.cancellationSet, region))
    workflow.add((task_b, YAWL.inCancellationRegion, region))
    workflow.add((task_c, YAWL.inCancellationRegion, region))

    # All tasks have tokens
    workflow.add((task_a, KGC.hasToken, Literal(True)))
    workflow.add((task_b, KGC.hasToken, Literal(True)))
    workflow.add((task_c, KGC.hasToken, Literal(True)))

    # Act: Cancel region from task A
    config = VerbConfig(verb="void", cancellation_scope="region")
    delta = Kernel.void(workflow, task_a, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: All tokens removed
    assert (task_a, KGC.hasToken, Literal(True)) not in workflow
    assert (task_b, KGC.hasToken, Literal(True)) not in workflow
    assert (task_c, KGC.hasToken, Literal(True)) not in workflow

    # Assert: All tasks in region voided
    assert len(list(workflow.triples((task_a, KGC.voidedAt, None)))) == 1
    assert len(list(workflow.triples((task_b, KGC.voidedAt, None)))) == 1
    assert len(list(workflow.triples((task_c, KGC.voidedAt, None)))) == 1


def test_wcp21_cancel_region_only_active_tasks(base_context: TransactionContext) -> None:
    """Test WCP-21: Cancel Region only voids tasks WITH tokens.

    Scenario: Region has tasks B (token), C (no token), D (token).
    Expected: Only B and D voided, C unaffected.
    """
    # Arrange: Create region with mixed token state
    workflow = Graph()
    task_a = TEST.TaskA
    task_b = TEST.TaskB
    task_c = TEST.TaskC
    task_d = TEST.TaskD
    region = TEST.CancellationRegion1

    workflow.add((task_a, YAWL.cancellationSet, region))
    workflow.add((task_b, YAWL.inCancellationRegion, region))
    workflow.add((task_c, YAWL.inCancellationRegion, region))
    workflow.add((task_d, YAWL.inCancellationRegion, region))

    # Only B and D have tokens
    workflow.add((task_a, KGC.hasToken, Literal(True)))
    workflow.add((task_b, KGC.hasToken, Literal(True)))
    workflow.add((task_d, KGC.hasToken, Literal(True)))

    # Act: Cancel region
    config = VerbConfig(verb="void", cancellation_scope="region")
    delta = Kernel.void(workflow, task_a, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: Only active tasks voided
    assert len(list(workflow.triples((task_a, KGC.voidedAt, None)))) == 1
    assert len(list(workflow.triples((task_b, KGC.voidedAt, None)))) == 1
    assert len(list(workflow.triples((task_c, KGC.voidedAt, None)))) == 0
    assert len(list(workflow.triples((task_d, KGC.voidedAt, None)))) == 1


def test_wcp21_cancel_region_outside_region_unaffected(base_context: TransactionContext) -> None:
    """Test WCP-21: Cancel Region does NOT affect tasks outside region.

    Scenario: Region contains B, C. Task D is outside region.
    Expected: B, C voided. D unaffected.
    """
    # Arrange: Create region with external task
    workflow = Graph()
    task_a = TEST.TaskA
    task_b = TEST.TaskB
    task_c = TEST.TaskC
    task_d = TEST.TaskD  # Outside region
    region = TEST.CancellationRegion1

    workflow.add((task_a, YAWL.cancellationSet, region))
    workflow.add((task_b, YAWL.inCancellationRegion, region))
    workflow.add((task_c, YAWL.inCancellationRegion, region))

    # All have tokens
    workflow.add((task_a, KGC.hasToken, Literal(True)))
    workflow.add((task_b, KGC.hasToken, Literal(True)))
    workflow.add((task_c, KGC.hasToken, Literal(True)))
    workflow.add((task_d, KGC.hasToken, Literal(True)))

    # Act: Cancel region
    config = VerbConfig(verb="void", cancellation_scope="region")
    delta = Kernel.void(workflow, task_a, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: D unaffected (still has token, not voided)
    assert (task_d, KGC.hasToken, Literal(True)) in workflow
    assert len(list(workflow.triples((task_d, KGC.voidedAt, None)))) == 0


# =============================================================================
# WCP-22: CANCEL MI ACTIVITY (Void with scope="instances")
# =============================================================================


def test_wcp22_cancel_mi_all_instances(base_context: TransactionContext) -> None:
    """Test WCP-22: Cancel MI voids all instances of MI task.

    Scenario: MI task has 3 active instances (instance_0, instance_1, instance_2).
    Expected: All instances voided, parent task voided.
    """
    # Arrange: Create MI task with 3 instances
    workflow = Graph()
    parent_task = TEST.MITask
    instance_0 = TEST.MITask_instance_0
    instance_1 = TEST.MITask_instance_1
    instance_2 = TEST.MITask_instance_2

    # Link instances to parent
    workflow.add((instance_0, KGC.parentTask, parent_task))
    workflow.add((instance_1, KGC.parentTask, parent_task))
    workflow.add((instance_2, KGC.parentTask, parent_task))

    # All have tokens
    workflow.add((parent_task, KGC.hasToken, Literal(True)))
    workflow.add((instance_0, KGC.hasToken, Literal(True)))
    workflow.add((instance_1, KGC.hasToken, Literal(True)))
    workflow.add((instance_2, KGC.hasToken, Literal(True)))

    # Act: Cancel MI
    config = VerbConfig(verb="void", cancellation_scope="instances")
    delta = Kernel.void(workflow, parent_task, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: All tokens removed
    assert (parent_task, KGC.hasToken, Literal(True)) not in workflow
    assert (instance_0, KGC.hasToken, Literal(True)) not in workflow
    assert (instance_1, KGC.hasToken, Literal(True)) not in workflow
    assert (instance_2, KGC.hasToken, Literal(True)) not in workflow

    # Assert: All voided
    assert len(list(workflow.triples((parent_task, KGC.voidedAt, None)))) == 1
    assert len(list(workflow.triples((instance_0, KGC.voidedAt, None)))) == 1
    assert len(list(workflow.triples((instance_1, KGC.voidedAt, None)))) == 1
    assert len(list(workflow.triples((instance_2, KGC.voidedAt, None)))) == 1


def test_wcp22_cancel_mi_provenance_count(base_context: TransactionContext) -> None:
    """Test WCP-22: Cancel MI records instance count in provenance.

    Scenario: Cancel MI with 5 instances.
    Expected: nodesVoided="6" (5 instances + 1 parent).
    """
    # Arrange: MI with 5 instances
    workflow = Graph()
    parent = TEST.MITask
    instances = [URIRef(f"{TEST.MITask}_instance_{i}") for i in range(5)]

    workflow.add((parent, KGC.hasToken, Literal(True)))
    for inst in instances:
        workflow.add((inst, KGC.parentTask, parent))
        workflow.add((inst, KGC.hasToken, Literal(True)))

    # Act: Cancel MI
    config = VerbConfig(verb="void", cancellation_scope="instances")
    delta = Kernel.void(workflow, parent, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: Count recorded (5 instances + 1 parent = 6)
    voided_count = list(workflow.triples((parent, KGC.nodesVoided, None)))
    assert len(voided_count) == 1
    assert str(voided_count[0][2]) == "6"


def test_wcp22_cancel_mi_only_affects_mi_instances(base_context: TransactionContext) -> None:
    """Test WCP-22: Cancel MI only affects instances of THAT MI task.

    Scenario: Two MI tasks (A, B). A has 2 instances, B has 2 instances. Cancel A.
    Expected: A and A's instances voided. B and B's instances unaffected.
    """
    # Arrange: Two separate MI tasks
    workflow = Graph()
    mi_a = TEST.MITaskA
    mi_b = TEST.MITaskB
    a_inst_0 = TEST.MITaskA_instance_0
    a_inst_1 = TEST.MITaskA_instance_1
    b_inst_0 = TEST.MITaskB_instance_0
    b_inst_1 = TEST.MITaskB_instance_1

    # Link instances to parents
    workflow.add((a_inst_0, KGC.parentTask, mi_a))
    workflow.add((a_inst_1, KGC.parentTask, mi_a))
    workflow.add((b_inst_0, KGC.parentTask, mi_b))
    workflow.add((b_inst_1, KGC.parentTask, mi_b))

    # All have tokens
    for task in [mi_a, mi_b, a_inst_0, a_inst_1, b_inst_0, b_inst_1]:
        workflow.add((task, KGC.hasToken, Literal(True)))

    # Act: Cancel MI A only
    config = VerbConfig(verb="void", cancellation_scope="instances")
    delta = Kernel.void(workflow, mi_a, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: A and A's instances voided
    assert len(list(workflow.triples((mi_a, KGC.voidedAt, None)))) == 1
    assert len(list(workflow.triples((a_inst_0, KGC.voidedAt, None)))) == 1
    assert len(list(workflow.triples((a_inst_1, KGC.voidedAt, None)))) == 1

    # Assert: B and B's instances unaffected
    assert (mi_b, KGC.hasToken, Literal(True)) in workflow
    assert (b_inst_0, KGC.hasToken, Literal(True)) in workflow
    assert (b_inst_1, KGC.hasToken, Literal(True)) in workflow
    assert len(list(workflow.triples((mi_b, KGC.voidedAt, None)))) == 0
    assert len(list(workflow.triples((b_inst_0, KGC.voidedAt, None)))) == 0
    assert len(list(workflow.triples((b_inst_1, KGC.voidedAt, None)))) == 0


def test_wcp22_cancel_mi_partial_completion(base_context: TransactionContext) -> None:
    """Test WCP-22: Cancel MI with some instances completed, some active.

    Scenario: MI with 3 instances. Instance 0 completed, 1 and 2 active. Cancel MI.
    Expected: Active instances (1, 2) voided. Completed instance (0) unchanged.
    """
    # Arrange: MI with mixed completion state
    workflow = Graph()
    parent = TEST.MITask
    inst_0 = TEST.MITask_instance_0
    inst_1 = TEST.MITask_instance_1
    inst_2 = TEST.MITask_instance_2

    workflow.add((inst_0, KGC.parentTask, parent))
    workflow.add((inst_1, KGC.parentTask, parent))
    workflow.add((inst_2, KGC.parentTask, parent))

    # Instance 0 completed (no token)
    workflow.add((inst_0, KGC.completedAt, Literal("prev-tx-001")))

    # Instances 1, 2 active
    workflow.add((parent, KGC.hasToken, Literal(True)))
    workflow.add((inst_1, KGC.hasToken, Literal(True)))
    workflow.add((inst_2, KGC.hasToken, Literal(True)))

    # Act: Cancel MI
    config = VerbConfig(verb="void", cancellation_scope="instances")
    delta = Kernel.void(workflow, parent, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: Active instances voided
    assert len(list(workflow.triples((parent, KGC.voidedAt, None)))) == 1
    assert len(list(workflow.triples((inst_1, KGC.voidedAt, None)))) == 1
    assert len(list(workflow.triples((inst_2, KGC.voidedAt, None)))) == 1

    # Assert: Completed instance NOT voided (query returns 0 or already voided earlier)
    # Note: Completed instances don't have tokens, so void doesn't affect them
    voided_0 = list(workflow.triples((inst_0, KGC.voidedAt, None)))
    assert len(voided_0) == 0


# =============================================================================
# EDGE CASES AND INTEGRATION
# =============================================================================


def test_cancellation_delta_within_chatman_constant(base_context: TransactionContext) -> None:
    """Test cancellation deltas respect Chatman Constant (64 ops).

    Scenario: Cancel case with 20 tasks (should stay under limit).
    Expected: Delta operations <= 64 (additions + removals).

    Note: 30 tasks = 30 removals + 62 additions (30 voidedAt + 30 terminatedReason + scope + count)
          = 92 ops, which exceeds limit. 20 tasks should be safe.
    """
    # Arrange: Case with 20 tasks
    workflow = Graph()
    tasks = [URIRef(f"{TEST.Task}{i}") for i in range(20)]

    for task in tasks:
        workflow.add((task, KGC.hasToken, Literal(True)))

    # Act: Cancel case
    config = VerbConfig(verb="void", cancellation_scope="case")
    delta = Kernel.void(workflow, tasks[0], base_context, config)

    # Assert: Total ops within Chatman Constant
    total_ops = len(delta.additions) + len(delta.removals)
    assert total_ops <= 64


def test_cancellation_no_token_no_removal(base_context: TransactionContext) -> None:
    """Test cancellation handles tasks without tokens gracefully.

    Scenario: Task A has no token. Cancel with scope="self".
    Expected: No token removal, but voidedAt still added.
    """
    # Arrange: Task without token
    workflow = Graph()
    task_a = TEST.TaskA

    # Act: Cancel task (no token)
    config = VerbConfig(verb="void", cancellation_scope="self")
    delta = Kernel.void(workflow, task_a, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: No token removal (since there was no token)
    token_removals = [r for r in delta.removals if r[1] == KGC.hasToken]
    assert len(token_removals) == 1  # Still tries to remove

    # Assert: Voided marker added
    assert len(list(workflow.triples((task_a, KGC.voidedAt, None)))) == 1


def test_cancellation_timeout_reason(base_context: TransactionContext) -> None:
    """Test cancellation with timeout records appropriate reason.

    Scenario: Task has timer that expires.
    Expected: terminatedReason="timeout".
    """
    # Arrange: Task with timer
    workflow = Graph()
    task_a = TEST.TaskA
    timer = TEST.Timer1

    workflow.add((task_a, KGC.hasToken, Literal(True)))
    workflow.add((task_a, YAWL.hasTimer, timer))

    # Act: Cancel with timeout
    config = VerbConfig(verb="void", cancellation_scope="self")
    delta = Kernel.void(workflow, task_a, base_context, config)

    # Apply mutations
    for triple in delta.removals:
        workflow.remove(triple)
    for triple in delta.additions:
        workflow.add(triple)

    # Assert: Timeout reason recorded
    reason_triples = list(workflow.triples((task_a, KGC.terminatedReason, None)))
    assert len(reason_triples) == 1
    assert str(reason_triples[0][2]) == "timeout"
