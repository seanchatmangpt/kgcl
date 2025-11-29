"""JTBD Integration Test: Execute Parallel Work with Synchronization.

Job: As a workflow user, I need to execute multiple tasks in parallel and
synchronize their completion, so that I can handle concurrent work efficiently.

This test proves the YAWL engine can handle parallel execution by:
1. Splitting execution into parallel branches (AND-split, WCP-2)
2. Executing tasks concurrently
3. Synchronizing parallel branches (AND-join, WCP-3)
4. Continuing execution after synchronization

Chicago School TDD: Tests assert on ENGINE state (marking, work items, case
status), not on Python concurrency primitives or thread counts.
"""

from __future__ import annotations

import pytest

from kgcl.yawl import (
    CaseStatus,
    ConditionType,
    JoinType,
    SplitType,
    WorkItemStatus,
    YAtomicTask,
    YCondition,
    YEngine,
    YFlow,
    YNet,
    YSpecification,
    YTask,
)


class TestParallelSplit:
    """Test AND-split pattern (WCP-2): Execute multiple tasks in parallel."""

    @pytest.fixture
    def parallel_spec(self) -> YSpecification:
        """Create workflow with AND-split: A → (B, C, D) in parallel.

        Topology:
                 ┌─→ B ─┐
        start → A ├─→ C ─┤ → end
                 └─→ D ─┘
        """
        spec = YSpecification(id="parallel-split")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        # Task A with AND-split
        task_a = YTask(id="TaskA", split_type=SplitType.AND)
        task_b = YAtomicTask(id="TaskB")
        task_c = YAtomicTask(id="TaskC")
        task_d = YAtomicTask(id="TaskD")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task_a)
        net.add_task(task_b)
        net.add_task(task_c)
        net.add_task(task_d)

        # Flows
        net.add_flow(YFlow(id="f1", source_id="start", target_id="TaskA"))
        net.add_flow(YFlow(id="f2", source_id="TaskA", target_id="TaskB"))
        net.add_flow(YFlow(id="f3", source_id="TaskA", target_id="TaskC"))
        net.add_flow(YFlow(id="f4", source_id="TaskA", target_id="TaskD"))
        # For simplicity, parallel tasks flow directly to end (no join yet)
        net.add_flow(YFlow(id="f5", source_id="TaskB", target_id="end"))
        net.add_flow(YFlow(id="f6", source_id="TaskC", target_id="end"))
        net.add_flow(YFlow(id="f7", source_id="TaskD", target_id="end"))

        spec.set_root_net(net)
        return spec

    def test_and_split_creates_multiple_work_items(self, parallel_spec: YSpecification) -> None:
        """AND-split creates work items for all parallel branches.

        JTBD: Start multiple tasks in parallel.
        Proof: Completing TaskA creates work items for B, C, and D simultaneously.
        """
        engine = YEngine()
        engine.start()
        engine.load_specification(parallel_spec)
        engine.activate_specification(parallel_spec.id)
        case = engine.create_case(parallel_spec.id)
        engine.start_case(case.id)

        # GIVEN: TaskA is executing
        case = engine.get_case(case.id)
        assert case is not None
        task_a_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskA"]
        assert len(task_a_items) == 1

        # WHEN: Complete TaskA (AND-split)
        engine.complete_work_item(task_a_items[0].id, case.id, {})

        # THEN: All three parallel tasks (B, C, D) have work items
        case = engine.get_case(case.id)
        assert case is not None

        task_b_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskB"]
        task_c_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskC"]
        task_d_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskD"]

        assert len(task_b_items) == 1, "TaskB should have work item after AND-split"
        assert len(task_c_items) == 1, "TaskC should have work item after AND-split"
        assert len(task_d_items) == 1, "TaskD should have work item after AND-split"

        # All should be EXECUTING
        assert task_b_items[0].status == WorkItemStatus.EXECUTING
        assert task_c_items[0].status == WorkItemStatus.EXECUTING
        assert task_d_items[0].status == WorkItemStatus.EXECUTING

    def test_parallel_tasks_execute_independently(self, parallel_spec: YSpecification) -> None:
        """Parallel tasks can complete in any order.

        JTBD: Execute tasks concurrently without blocking.
        Proof: Completing C before B doesn't block either task.
        """
        engine = YEngine()
        engine.start()
        engine.load_specification(parallel_spec)
        engine.activate_specification(parallel_spec.id)
        case = engine.create_case(parallel_spec.id)
        engine.start_case(case.id)

        # Complete TaskA to trigger AND-split
        case = engine.get_case(case.id)
        assert case is not None
        task_a_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskA"]
        engine.complete_work_item(task_a_items[0].id, case.id, {})

        # Get parallel task work items
        case = engine.get_case(case.id)
        assert case is not None
        task_b_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskB"]
        task_c_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskC"]
        task_d_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskD"]

        # WHEN: Complete in non-sequential order (C, then B, then D)
        engine.complete_work_item(task_c_items[0].id, case.id, {})
        engine.complete_work_item(task_b_items[0].id, case.id, {})
        engine.complete_work_item(task_d_items[0].id, case.id, {})

        # THEN: All complete successfully (no deadlock or errors)
        # Case should complete (simplified topology flows to end)
        case = engine.get_case(case.id)
        assert case is not None
        # At minimum, case should still be RUNNING or COMPLETED
        assert case.status in [CaseStatus.RUNNING, CaseStatus.COMPLETED]


class TestParallelSynchronization:
    """Test AND-join pattern (WCP-3): Synchronize parallel branches."""

    @pytest.fixture
    def sync_spec(self) -> YSpecification:
        """Create workflow with AND-join: (B, C, D) → synchronized → E.

        Topology:
                 ┌─→ B ─┐
        start → A ├─→ C ─┤ E → end
                 └─→ D ─┘
                   (AND-join at E)
        """
        spec = YSpecification(id="parallel-sync")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        # Task A with AND-split
        task_a = YTask(id="TaskA", split_type=SplitType.AND)
        task_b = YAtomicTask(id="TaskB")
        task_c = YAtomicTask(id="TaskC")
        task_d = YAtomicTask(id="TaskD")
        # Task E with AND-join (waits for B, C, D)
        task_e = YTask(id="TaskE", join_type=JoinType.AND)

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task_a)
        net.add_task(task_b)
        net.add_task(task_c)
        net.add_task(task_d)
        net.add_task(task_e)

        # Flows
        net.add_flow(YFlow(id="f1", source_id="start", target_id="TaskA"))
        # AND-split: A → B, C, D
        net.add_flow(YFlow(id="f2", source_id="TaskA", target_id="TaskB"))
        net.add_flow(YFlow(id="f3", source_id="TaskA", target_id="TaskC"))
        net.add_flow(YFlow(id="f4", source_id="TaskA", target_id="TaskD"))
        # AND-join: B, C, D → E
        net.add_flow(YFlow(id="f5", source_id="TaskB", target_id="TaskE"))
        net.add_flow(YFlow(id="f6", source_id="TaskC", target_id="TaskE"))
        net.add_flow(YFlow(id="f7", source_id="TaskD", target_id="TaskE"))
        # E → end
        net.add_flow(YFlow(id="f8", source_id="TaskE", target_id="end"))

        spec.set_root_net(net)
        return spec

    def test_and_join_waits_for_all_branches(self, sync_spec: YSpecification) -> None:
        """AND-join task waits until all incoming branches complete.

        JTBD: Synchronize parallel work before continuing.
        Proof: TaskE doesn't execute until B, C, and D all complete.
        """
        engine = YEngine()
        engine.start()
        engine.load_specification(sync_spec)
        engine.activate_specification(sync_spec.id)
        case = engine.create_case(sync_spec.id)
        engine.start_case(case.id)

        # Complete TaskA to trigger AND-split
        case = engine.get_case(case.id)
        assert case is not None
        task_a_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskA"]
        engine.complete_work_item(task_a_items[0].id, case.id, {})

        # Get parallel task work items
        case = engine.get_case(case.id)
        assert case is not None
        task_b_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskB"]
        task_c_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskC"]
        task_d_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskD"]

        # WHEN: Complete only B and C (not D yet)
        engine.complete_work_item(task_b_items[0].id, case.id, {})
        engine.complete_work_item(task_c_items[0].id, case.id, {})

        # THEN: TaskE should NOT execute yet (waiting for D)
        case = engine.get_case(case.id)
        assert case is not None
        task_e_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskE"]
        # TaskE should not have a work item yet (or should be ENABLED but not EXECUTING)
        if len(task_e_items) > 0:
            # If work item exists, it should not be EXECUTING
            assert task_e_items[0].status != WorkItemStatus.EXECUTING

        # WHEN: Complete D (final branch)
        engine.complete_work_item(task_d_items[0].id, case.id, {})

        # THEN: TaskE now executes (all branches synchronized)
        case = engine.get_case(case.id)
        assert case is not None
        task_e_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskE"]
        assert len(task_e_items) == 1, "TaskE should execute after all branches complete"
        assert task_e_items[0].status == WorkItemStatus.EXECUTING

    def test_complete_synchronized_workflow(self, sync_spec: YSpecification) -> None:
        """Complete workflow with parallel split and synchronization.

        JTBD: Execute full parallel-sync workflow end-to-end.
        Proof: Case completes after all parallel branches synchronize and final task completes.
        """
        engine = YEngine()
        engine.start()
        engine.load_specification(sync_spec)
        engine.activate_specification(sync_spec.id)
        case = engine.create_case(sync_spec.id)
        engine.start_case(case.id)

        # Complete TaskA (AND-split)
        case = engine.get_case(case.id)
        assert case is not None
        task_a_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskA"]
        engine.complete_work_item(task_a_items[0].id, case.id, {})

        # Complete all parallel branches (B, C, D)
        case = engine.get_case(case.id)
        assert case is not None
        for task_id in ["TaskB", "TaskC", "TaskD"]:
            task_items = [wi for wi in case.work_items.values() if wi.task_id == task_id]
            assert len(task_items) == 1
            engine.complete_work_item(task_items[0].id, case.id, {})

        # Complete TaskE (synchronized task)
        case = engine.get_case(case.id)
        assert case is not None
        task_e_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskE"]
        assert len(task_e_items) == 1
        engine.complete_work_item(task_e_items[0].id, case.id, {})

        # THEN: Case completes
        case = engine.get_case(case.id)
        assert case is not None
        assert case.status == CaseStatus.COMPLETED, "Case should complete after synchronized workflow"


class TestNestedParallelism:
    """Test nested parallel patterns: parallel within parallel."""

    def test_nested_and_splits(self) -> None:
        """Nested AND-splits create hierarchical parallelism.

        JTBD: Handle complex parallel structures.
        Proof: A → (B → (D, E), C) creates correct parallel structure.
        """
        spec = YSpecification(id="nested-parallel")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        # A splits to B and C
        task_a = YTask(id="TaskA", split_type=SplitType.AND)
        # B splits to D and E
        task_b = YTask(id="TaskB", split_type=SplitType.AND)
        task_c = YAtomicTask(id="TaskC")
        task_d = YAtomicTask(id="TaskD")
        task_e = YAtomicTask(id="TaskE")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task_a)
        net.add_task(task_b)
        net.add_task(task_c)
        net.add_task(task_d)
        net.add_task(task_e)

        # Flows
        net.add_flow(YFlow(id="f1", source_id="start", target_id="TaskA"))
        # A → B, C
        net.add_flow(YFlow(id="f2", source_id="TaskA", target_id="TaskB"))
        net.add_flow(YFlow(id="f3", source_id="TaskA", target_id="TaskC"))
        # B → D, E
        net.add_flow(YFlow(id="f4", source_id="TaskB", target_id="TaskD"))
        net.add_flow(YFlow(id="f5", source_id="TaskB", target_id="TaskE"))
        # All to end (simplified)
        net.add_flow(YFlow(id="f6", source_id="TaskC", target_id="end"))
        net.add_flow(YFlow(id="f7", source_id="TaskD", target_id="end"))
        net.add_flow(YFlow(id="f8", source_id="TaskE", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)
        engine.start_case(case.id)

        # Complete TaskA (first AND-split)
        case = engine.get_case(case.id)
        assert case is not None
        task_a_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskA"]
        engine.complete_work_item(task_a_items[0].id, case.id, {})

        # THEN: B and C should have work items
        case = engine.get_case(case.id)
        assert case is not None
        task_b_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskB"]
        task_c_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskC"]
        assert len(task_b_items) == 1
        assert len(task_c_items) == 1

        # Complete TaskB (nested AND-split)
        engine.complete_work_item(task_b_items[0].id, case.id, {})

        # THEN: D and E should have work items
        case = engine.get_case(case.id)
        assert case is not None
        task_d_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskD"]
        task_e_items = [wi for wi in case.work_items.values() if wi.task_id == "TaskE"]
        assert len(task_d_items) == 1, "Nested AND-split should create TaskD work item"
        assert len(task_e_items) == 1, "Nested AND-split should create TaskE work item"

        # C should still be executing (independent branch)
        assert task_c_items[0].status == WorkItemStatus.EXECUTING
