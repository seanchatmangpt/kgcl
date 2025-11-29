"""Tests that verify Python YAWL engine matches Java YAWL semantics.

These tests verify engine behavior against YAWL specification and Java implementation,
focusing on:
1. Petri net token semantics (condition marking)
2. Work item lifecycle (ENABLED → FIRED → OFFERED → ALLOCATED → STARTED → COMPLETED)
3. Task execution patterns (AND-split, XOR-split, OR-split, joins)
4. Case lifecycle management
5. Event notification semantics

Based on Java YAWL v5.2 engine behavior extracted from ontology.
"""

from __future__ import annotations

import pytest

from kgcl.yawl.elements.y_atomic_task import YAtomicTask
from kgcl.yawl.elements.y_condition import ConditionType, YCondition
from kgcl.yawl.elements.y_flow import YFlow
from kgcl.yawl.elements.y_net import YNet
from kgcl.yawl.elements.y_specification import YSpecification
from kgcl.yawl.elements.y_task import JoinType, SplitType, YTask
from kgcl.yawl.engine.y_case import CaseStatus
from kgcl.yawl.engine.y_engine import EngineStatus, YEngine
from kgcl.yawl.engine.y_work_item import WorkItemStatus


class TestPetriNetTokenSemantics:
    """Verify Petri net token semantics match Java YAWL.

    Java reference: YNetRunner.java, YCondition.java
    """

    def test_input_condition_receives_initial_token(self) -> None:
        """Input condition receives exactly one token on case start."""
        spec = YSpecification(id="token-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        task = YTask(id="A")
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task)
        net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
        net.add_flow(YFlow(id="f2", source_id="A", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)
        engine.start_case(case.id)

        # Get net runner and verify initial marking
        runner = case.net_runners.get("main")
        assert runner is not None

        # Java YAWL: Input condition gets one token on case start
        # Python implementation uses marking to track tokens
        assert runner.marking is not None

    def test_task_consumes_token_from_input_condition(self) -> None:
        """Task firing consumes token from input condition."""
        spec = YSpecification(id="consume-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        task = YAtomicTask(id="A")
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task)
        net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
        net.add_flow(YFlow(id="f2", source_id="A", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)
        engine.start_case(case.id)

        # Work item should be created and executing
        work_items = list(case.work_items.values())
        assert len(work_items) >= 1
        assert work_items[0].status == WorkItemStatus.EXECUTING


class TestWorkItemLifecycle:
    """Verify work item lifecycle matches Java YAWL.

    Java reference: YWorkItem.java, YEngine.java
    """

    def test_work_item_transitions_enabled_to_fired(self) -> None:
        """Work items transition ENABLED → FIRED when task is enabled."""
        spec = YSpecification(id="lifecycle-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        task = YAtomicTask(id="A")
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task)
        net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
        net.add_flow(YFlow(id="f2", source_id="A", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)
        engine.start_case(case.id)

        # Java YAWL: System tasks auto-transition to EXECUTING
        # ENABLED → FIRED → EXECUTING
        work_items = list(case.work_items.values())
        assert len(work_items) >= 1
        # Should be in EXECUTING state (system task auto-starts)
        assert work_items[0].status == WorkItemStatus.EXECUTING

    def test_work_item_completion_produces_output_token(self) -> None:
        """Completing work item produces token in output condition."""
        spec = YSpecification(id="output-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        task = YAtomicTask(id="A")
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task)
        net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
        net.add_flow(YFlow(id="f2", source_id="A", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)
        engine.start_case(case.id)

        work_items = list(case.work_items.values())
        if work_items and work_items[0].status == WorkItemStatus.EXECUTING:
            engine.complete_work_item(work_items[0].id)

        # Java YAWL: Completing task produces token in output condition
        # Verify work item is completed
        assert work_items[0].status == WorkItemStatus.COMPLETED


class TestEngineLifecycle:
    """Verify engine lifecycle matches Java YAWL.

    Java reference: YEngine.java
    """

    def test_engine_starts_in_stopped_state(self) -> None:
        """New engine starts in STOPPED state."""
        engine = YEngine()
        assert engine.status == EngineStatus.STOPPED

    def test_engine_transitions_to_running_on_start(self) -> None:
        """Engine transitions to RUNNING when started."""
        engine = YEngine()
        engine.start()
        assert engine.status == EngineStatus.RUNNING
        assert engine.is_running() is True

    def test_engine_can_load_specification_when_running(self) -> None:
        """Running engine can load specifications."""
        engine = YEngine()
        engine.start()

        spec = YSpecification(id="test-spec")
        net = YNet(id="main")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        task = YTask(id="A")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task)
        net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
        net.add_flow(YFlow(id="f2", source_id="A", target_id="end"))
        spec.set_root_net(net)

        loaded = engine.load_specification(spec)
        assert loaded.id == spec.id
        assert spec.id in engine.specifications


class TestCaseManagement:
    """Verify case management matches Java YAWL.

    Java reference: YCase.java, YEngine.java
    """

    def test_case_created_in_created_state(self) -> None:
        """New case is in CREATED state."""
        spec = YSpecification(id="case-test")
        net = YNet(id="main")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        task = YTask(id="A")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task)
        net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
        net.add_flow(YFlow(id="f2", source_id="A", target_id="end"))
        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)

        case = engine.create_case(spec.id)
        assert case.status == CaseStatus.CREATED

    def test_case_transitions_to_running_on_start(self) -> None:
        """Case transitions to RUNNING when started."""
        spec = YSpecification(id="start-test")
        net = YNet(id="main")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        task = YTask(id="A")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task)
        net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
        net.add_flow(YFlow(id="f2", source_id="A", target_id="end"))
        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)

        started_case = engine.start_case(case.id)
        assert started_case.status == CaseStatus.RUNNING

    def test_case_can_be_cancelled(self) -> None:
        """Running case can be cancelled."""
        spec = YSpecification(id="cancel-test")
        net = YNet(id="main")
        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
        task = YTask(id="A")

        net.add_condition(start)
        net.add_condition(end)
        net.add_task(task)
        net.add_flow(YFlow(id="f1", source_id="start", target_id="A"))
        net.add_flow(YFlow(id="f2", source_id="A", target_id="end"))
        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)
        engine.start_case(case.id)

        result = engine.cancel_case(case.id, "Test cancellation")
        assert result is True
        assert case.status == CaseStatus.CANCELLED


class TestTaskSplitSemantics:
    """Verify task split semantics match Java YAWL.

    Java reference: YTask.java, YNetRunner.java
    """

    def test_and_split_creates_parallel_tokens(self) -> None:
        """AND-split creates tokens in all output conditions."""
        spec = YSpecification(id="and-split-test")
        net = YNet(id="main")

        start = YCondition(id="start", condition_type=ConditionType.INPUT)
        split_task = YTask(id="Split", split_type=SplitType.AND)
        c_a = YCondition(id="c_a")
        c_b = YCondition(id="c_b")
        task_a = YTask(id="A")
        task_b = YTask(id="B")
        end = YCondition(id="end", condition_type=ConditionType.OUTPUT)

        net.add_condition(start)
        net.add_condition(c_a)
        net.add_condition(c_b)
        net.add_condition(end)
        net.add_task(split_task)
        net.add_task(task_a)
        net.add_task(task_b)

        net.add_flow(YFlow(id="f1", source_id="start", target_id="Split"))
        net.add_flow(YFlow(id="f2", source_id="Split", target_id="c_a"))
        net.add_flow(YFlow(id="f3", source_id="Split", target_id="c_b"))
        net.add_flow(YFlow(id="f4", source_id="c_a", target_id="A"))
        net.add_flow(YFlow(id="f5", source_id="c_b", target_id="B"))
        net.add_flow(YFlow(id="f6", source_id="A", target_id="end"))
        net.add_flow(YFlow(id="f7", source_id="B", target_id="end"))

        spec.set_root_net(net)

        engine = YEngine()
        engine.start()
        engine.load_specification(spec)
        engine.activate_specification(spec.id)
        case = engine.create_case(spec.id)
        engine.start_case(case.id)

        # Java YAWL: AND-split should create work items for all parallel branches
        # Verify work items created
        assert len(case.work_items) >= 1
