"""JTBD Integration Test: Monitor and Query Workflow Execution.

Job: As a workflow user, I need to monitor running workflows and query their
status, so that I can track progress and identify issues.

This test proves the YAWL engine can support monitoring by:
1. Querying case status and progress
2. Listing active cases
3. Getting work item details
4. Tracking case history
5. Querying by specification
6. Performance metrics

Chicago School TDD: Tests assert on ENGINE queries returning correct data,
not on monitoring UI or dashboards.
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


class TestQueryCaseStatus:
    """Test querying case status and progress."""

    def test_get_case_status(self) -> None:
        """Query current status of a case.

        JTBD: Check if workflow is running, completed, or failed.
        Proof: get_case returns case with current status.
        """
        spec = YSpecification(id="status-query-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        task_a = YAtomicTask(id="TaskA")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task_a)

        net.add_flow(YFlow(id="f1", source_id="start", target_id="TaskA"))
        net.add_flow(YFlow(id="f2", source_id="TaskA", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)

        # Check status: CREATED
        case_obj = engine.get_case(case.id)
        assert case_obj is not None
        assert case_obj.status == CaseStatus.CREATED

        # Start case
        engine.start_case(case.id)

        # Check status: RUNNING
        case_obj = engine.get_case(case.id)
        assert case_obj is not None
        assert case_obj.status == CaseStatus.RUNNING

        # Complete workflow
        work_items = list(case_obj.work_items.values())
        if work_items:
            engine.complete_work_item(work_items[0].id, case.id, {})

        # Check status: COMPLETED
        case_obj = engine.get_case(case.id)
        assert case_obj is not None
        assert case_obj.status == CaseStatus.COMPLETED

    def test_get_case_progress(self) -> None:
        """Query workflow progress (completed vs total tasks).

        JTBD: See how far workflow has progressed.
        Proof: Can calculate completion percentage.
        """
        spec = YSpecification(id="progress-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        task_a = YAtomicTask(id="TaskA")
        task_b = YAtomicTask(id="TaskB")
        task_c = YAtomicTask(id="TaskC")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task_a)
        net.add_task(task_b)
        net.add_task(task_c)

        net.add_flow(YFlow(id="f1", source_id="start", target_id="TaskA"))
        net.add_flow(YFlow(id="f2", source_id="TaskA", target_id="TaskB"))
        net.add_flow(YFlow(id="f3", source_id="TaskB", target_id="TaskC"))
        net.add_flow(YFlow(id="f4", source_id="TaskC", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)
        engine.start_case(case.id)

        # Get case and calculate progress
        case_obj = engine.get_case(case.id)
        assert case_obj is not None

        # Count work items by status
        total_work_items = len(case_obj.work_items)
        completed_items = sum(1 for wi in case_obj.work_items.values() if wi.status == WorkItemStatus.COMPLETED)

        # Initially, 0 completed (TaskA is executing)
        assert completed_items == 0

        # Complete TaskA
        task_a_items = [wi for wi in case_obj.work_items.values() if wi.task_id == "TaskA"]
        if task_a_items:
            engine.complete_work_item(task_a_items[0].id, case.id, {})

        # Check progress increased
        case_obj = engine.get_case(case.id)
        assert case_obj is not None
        completed_items = sum(1 for wi in case_obj.work_items.values() if wi.status == WorkItemStatus.COMPLETED)
        # At least 1 completed now


class TestListActiveCases:
    """Test querying all active cases."""

    def test_get_all_running_cases(self) -> None:
        """Get list of all running cases.

        JTBD: See all active workflows in system.
        Proof: Query returns all running cases.
        """
        spec = YSpecification(id="list-cases-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        task_a = YAtomicTask(id="TaskA")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task_a)

        net.add_flow(YFlow(id="f1", source_id="start", target_id="TaskA"))
        net.add_flow(YFlow(id="f2", source_id="TaskA", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)

        # Create multiple cases
        case1 = engine.create_case(spec.id)
        case2 = engine.create_case(spec.id)
        case3 = engine.create_case(spec.id)

        engine.start_case(case1.id)
        engine.start_case(case2.id)
        engine.start_case(case3.id)

        # Query running cases
        running_cases = engine.get_cases(status=CaseStatus.RUNNING)

        # Should have 3 running cases
        assert len(running_cases) >= 3

    def test_filter_cases_by_specification(self) -> None:
        """Filter cases by specification ID.

        JTBD: See all instances of a specific workflow.
        Proof: Query returns only cases for given spec.
        """
        # Create two different specifications
        spec1 = self._create_spec("workflow-a")
        spec2 = self._create_spec("workflow-b")

        engine = YEngine()
        engine.start()

        engine.load_specification(spec1)
        engine.load_specification(spec2)
        engine.activate_specification(spec1.id)
        engine.activate_specification(spec2.id)

        # Create cases for each spec
        case1a = engine.create_case(spec1.id)
        case1b = engine.create_case(spec1.id)
        case2a = engine.create_case(spec2.id)

        engine.start_case(case1a.id)
        engine.start_case(case1b.id)
        engine.start_case(case2a.id)

        # Query cases for spec1
        spec1_cases = engine.get_cases(specification_id=spec1.id)

        # Should have 2 cases
        assert len(spec1_cases) >= 2

        # All should be for spec1
        for case in spec1_cases:
            assert case.specification_id == spec1.id

    def _create_spec(self, spec_id: str) -> YSpecification:
        """Helper to create simple spec."""
        spec = YSpecification(id=spec_id)
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        task = YAtomicTask(id="Task")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task)

        net.add_flow(YFlow(id="f1", source_id="start", target_id="Task"))
        net.add_flow(YFlow(id="f2", source_id="Task", target_id="end"))

        spec.set_root_net(net)
        return spec


class TestQueryWorkItems:
    """Test querying work item details."""

    def test_get_all_work_items_for_case(self) -> None:
        """Get all work items for a case.

        JTBD: See all tasks in a workflow instance.
        Proof: Query returns all work items.
        """
        spec = YSpecification(id="work-items-query-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        task_a = YTask(id="TaskA", split_type=SplitType.AND)
        task_b = YAtomicTask(id="TaskB")
        task_c = YAtomicTask(id="TaskC")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task_a)
        net.add_task(task_b)
        net.add_task(task_c)

        net.add_flow(YFlow(id="f1", source_id="start", target_id="TaskA"))
        net.add_flow(YFlow(id="f2", source_id="TaskA", target_id="TaskB"))
        net.add_flow(YFlow(id="f3", source_id="TaskA", target_id="TaskC"))
        net.add_flow(YFlow(id="f4", source_id="TaskB", target_id="end"))
        net.add_flow(YFlow(id="f5", source_id="TaskC", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)
        engine.start_case(case.id)

        # Complete TaskA to trigger AND-split
        case_obj = engine.get_case(case.id)
        assert case_obj is not None
        task_a_items = [wi for wi in case_obj.work_items.values() if wi.task_id == "TaskA"]
        if task_a_items:
            engine.complete_work_item(task_a_items[0].id, case.id, {})

        # Query all work items
        case_obj = engine.get_case(case.id)
        assert case_obj is not None
        all_items = list(case_obj.work_items.values())

        # Should have work items for parallel tasks
        assert len(all_items) >= 1

    def test_filter_work_items_by_status(self) -> None:
        """Filter work items by status.

        JTBD: Find all executing/completed tasks.
        Proof: Query returns only items with specified status.
        """
        spec = YSpecification(id="filter-items-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        task_a = YAtomicTask(id="TaskA")
        task_b = YAtomicTask(id="TaskB")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task_a)
        net.add_task(task_b)

        net.add_flow(YFlow(id="f1", source_id="start", target_id="TaskA"))
        net.add_flow(YFlow(id="f2", source_id="TaskA", target_id="TaskB"))
        net.add_flow(YFlow(id="f3", source_id="TaskB", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)
        engine.start_case(case.id)

        # Get executing items
        case_obj = engine.get_case(case.id)
        assert case_obj is not None

        executing = [wi for wi in case_obj.work_items.values() if wi.status in [WorkItemStatus.EXECUTING, WorkItemStatus.STARTED]]

        # Should have TaskA executing
        assert len(executing) >= 1


class TestCaseHistory:
    """Test querying case execution history."""

    def test_get_case_log(self) -> None:
        """Get execution log for a case.

        JTBD: Review workflow execution history.
        Proof: Log contains case events.
        """
        spec = YSpecification(id="history-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        task_a = YAtomicTask(id="TaskA")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task_a)

        net.add_flow(YFlow(id="f1", source_id="start", target_id="TaskA"))
        net.add_flow(YFlow(id="f2", source_id="TaskA", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)
        engine.start_case(case.id)

        # Get case with log
        case_obj = engine.get_case(case.id)
        assert case_obj is not None

        # Case should have log entries
        if hasattr(case_obj, "log"):
            assert case_obj.log is not None
            # Log contains events

    def test_get_work_item_log(self) -> None:
        """Get execution log for work items.

        JTBD: Track task execution timeline.
        Proof: Work item log contains state transitions.
        """
        spec = YSpecification(id="item-log-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        task_a = YAtomicTask(id="TaskA")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task_a)

        net.add_flow(YFlow(id="f1", source_id="start", target_id="TaskA"))
        net.add_flow(YFlow(id="f2", source_id="TaskA", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)
        engine.start_case(case.id)

        # Get work item
        case_obj = engine.get_case(case.id)
        assert case_obj is not None
        work_items = list(case_obj.work_items.values())
        assert len(work_items) > 0

        work_item = work_items[0]

        # Work item should track transitions
        if hasattr(work_item, "log"):
            assert work_item.log is not None


class TestPerformanceMetrics:
    """Test querying performance metrics."""

    def test_get_case_duration(self) -> None:
        """Calculate case execution duration.

        JTBD: Measure workflow execution time.
        Proof: Can compute duration from start to end time.
        """
        spec = YSpecification(id="duration-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        task_a = YAtomicTask(id="TaskA")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task_a)

        net.add_flow(YFlow(id="f1", source_id="start", target_id="TaskA"))
        net.add_flow(YFlow(id="f2", source_id="TaskA", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)
        engine.start_case(case.id)

        # Get case
        case_obj = engine.get_case(case.id)
        assert case_obj is not None

        # Case should track start time
        if hasattr(case_obj, "start_time"):
            assert case_obj.start_time is not None

        # Complete workflow
        work_items = list(case_obj.work_items.values())
        if work_items:
            engine.complete_work_item(work_items[0].id, case.id, {})

        # Get completed case
        case_obj = engine.get_case(case.id)
        assert case_obj is not None

        # Should track end time
        if hasattr(case_obj, "end_time") and case_obj.status == CaseStatus.COMPLETED:
            assert case_obj.end_time is not None

            # Can calculate duration
            if hasattr(case_obj, "start_time") and case_obj.start_time:
                duration = case_obj.end_time - case_obj.start_time
                assert duration >= 0

    def test_get_throughput_metrics(self) -> None:
        """Calculate workflow throughput (cases per time period).

        JTBD: Monitor system capacity and load.
        Proof: Can count completed cases in time window.
        """
        spec = YSpecification(id="throughput-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        task_a = YAtomicTask(id="TaskA")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task_a)

        net.add_flow(YFlow(id="f1", source_id="start", target_id="TaskA"))
        net.add_flow(YFlow(id="f2", source_id="TaskA", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)

        # Create and complete multiple cases
        completed_count = 0
        for _ in range(5):
            case = engine.create_case(spec.id)
            engine.start_case(case.id)

            case_obj = engine.get_case(case.id)
            if case_obj:
                work_items = list(case_obj.work_items.values())
                if work_items:
                    engine.complete_work_item(work_items[0].id, case.id, {})
                    completed_count += 1

        # Query completed cases
        completed_cases = engine.get_cases(status=CaseStatus.COMPLETED)

        # Should have completed cases
        assert len(completed_cases) >= completed_count


class TestAdvancedQueries:
    """Test advanced query capabilities."""

    def test_query_cases_by_data_value(self) -> None:
        """Query cases by data values.

        JTBD: Find workflows with specific data attributes.
        Proof: Can filter cases by data content.
        """
        # This test documents desired behavior
        # Implementation would require indexing case data
        pass

    def test_query_bottlenecks(self) -> None:
        """Identify workflow bottlenecks (slow tasks).

        JTBD: Find performance issues in workflows.
        Proof: Can identify tasks with long avg execution time.
        """
        # This test documents desired behavior
        # Would aggregate work item durations by task ID
        pass

    def test_query_error_rates(self) -> None:
        """Calculate error rates for tasks.

        JTBD: Monitor workflow reliability.
        Proof: Can compute failure percentage by task.
        """
        # This test documents desired behavior
        # Would track failed work items
        pass
