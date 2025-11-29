"""Comprehensive unit tests for YEngine core functionality.

Tests the core workflow engine capabilities including:
- Engine lifecycle (start, stop, pause, resume)
- Specification loading and validation
- Case creation and execution
- Work item lifecycle
- Resource management
- Timer handling
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from kgcl.yawl.elements.y_atomic_task import YAtomicTask
from kgcl.yawl.elements.y_condition import YCondition
from kgcl.yawl.elements.y_flow import YFlow
from kgcl.yawl.elements.y_input_output_condition import YInputCondition, YOutputCondition
from kgcl.yawl.elements.y_net import YNet
from kgcl.yawl.elements.y_specification import YSpecification
from kgcl.yawl.engine.engine_types import EngineEvent, EngineStatus
from kgcl.yawl.engine.y_case import CaseStatus
from kgcl.yawl.engine.y_engine import YEngine
from kgcl.yawl.engine.y_timer import TimerAction, TimerTrigger, YTimer
from kgcl.yawl.engine.y_work_item import WorkItemStatus

# === Engine Lifecycle Tests ===


def test_engine_starts_correctly() -> None:
    """Test engine starts and changes status."""
    engine = YEngine()

    assert engine.status == EngineStatus.STOPPED
    assert engine.started is None

    engine.start()

    assert engine.status == EngineStatus.RUNNING
    assert engine.started is not None
    assert isinstance(engine.started, datetime)


def test_engine_stops_correctly() -> None:
    """Test engine stops and changes status."""
    engine = YEngine()
    engine.start()

    engine.stop()

    assert engine.status == EngineStatus.STOPPED


def test_engine_pause_resume() -> None:
    """Test engine can be paused and resumed."""
    engine = YEngine()
    engine.start()

    engine.pause()
    assert engine.status == EngineStatus.PAUSED

    engine.resume()
    assert engine.status == EngineStatus.RUNNING


def test_engine_is_running_check() -> None:
    """Test is_running status check."""
    engine = YEngine()

    assert not engine.is_running()

    engine.start()
    assert engine.is_running()

    engine.pause()
    assert not engine.is_running()

    engine.stop()
    assert not engine.is_running()


def test_engine_timer_service_starts_with_engine() -> None:
    """Test timer service is started when engine starts."""
    engine = YEngine()

    assert not engine.timer_service.running

    engine.start()

    assert engine.timer_service.running


# === Specification Management Tests ===


def test_load_valid_specification() -> None:
    """Test loading a valid specification."""
    engine = YEngine()
    spec = _create_valid_spec()

    loaded_spec = engine.load_specification(spec)

    assert loaded_spec == spec
    assert spec.id in engine.specifications
    assert engine.get_specification(spec.id) == spec


def test_unload_specification() -> None:
    """Test unloading a specification."""
    engine = YEngine()
    spec = _create_valid_spec()
    engine.load_specification(spec)

    result = engine.unload_specification(spec.id)

    assert result is True
    assert spec.id not in engine.specifications
    assert engine.get_specification(spec.id) is None


def test_cannot_unload_spec_with_running_cases() -> None:
    """Test cannot unload specification with running cases."""
    engine = YEngine()
    engine.start()
    spec = _create_valid_spec()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)
    engine.create_case(spec.id)

    result = engine.unload_specification(spec.id)

    assert result is False
    assert spec.id in engine.specifications


def test_activate_specification() -> None:
    """Test activating a loaded specification."""
    engine = YEngine()
    spec = _create_valid_spec()
    engine.load_specification(spec)

    result = engine.activate_specification(spec.id)

    assert result is True


# === Case Management Tests ===


def test_create_case_with_input_data() -> None:
    """Test creating a case with input data."""
    engine = YEngine()
    engine.start()
    spec = _create_valid_spec()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)

    case = engine.create_case(spec.id, input_data={"x": 10, "y": 20})

    assert case is not None
    assert case.specification_id == spec.id
    assert case.data.data["x"] == 10
    assert case.data.data["y"] == 20
    assert case.status == CaseStatus.CREATED


def test_create_case_generates_unique_id() -> None:
    """Test each created case has unique ID."""
    engine = YEngine()
    engine.start()
    spec = _create_valid_spec()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)

    case1 = engine.create_case(spec.id)
    case2 = engine.create_case(spec.id)

    assert case1.id != case2.id


def test_start_case() -> None:
    """Test starting a created case."""
    engine = YEngine()
    engine.start()
    spec = _create_valid_spec()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)
    case = engine.create_case(spec.id)

    started_case = engine.start_case(case.id)

    assert started_case.status == CaseStatus.RUNNING
    assert case.id in engine.cases


def test_cancel_case() -> None:
    """Test canceling a running case."""
    engine = YEngine()
    engine.start()
    spec = _create_valid_spec()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)
    case = engine.create_case(spec.id)
    engine.start_case(case.id)

    result = engine.cancel_case(case.id, reason="Test cancellation")

    assert result is True
    assert case.status == CaseStatus.CANCELLED


def test_suspend_resume_case() -> None:
    """Test suspending and resuming a case."""
    engine = YEngine()
    engine.start()
    spec = _create_valid_spec()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)
    case = engine.create_case(spec.id)
    engine.start_case(case.id)

    # Suspend
    result = engine.suspend_case(case.id, reason="Test suspension")
    assert result is True
    assert case.status == CaseStatus.SUSPENDED

    # Resume
    result = engine.resume_case(case.id)
    assert result is True
    assert case.status == CaseStatus.RUNNING


def test_get_running_cases() -> None:
    """Test getting all running cases."""
    engine = YEngine()
    engine.start()
    spec = _create_valid_spec()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)

    case1 = engine.create_case(spec.id)
    case2 = engine.create_case(spec.id)
    engine.start_case(case1.id)
    engine.start_case(case2.id)

    running_cases = engine.get_running_cases()

    assert len(running_cases) == 2
    assert case1 in running_cases
    assert case2 in running_cases


# === Work Item Management Tests ===


def test_work_items_created_for_enabled_tasks() -> None:
    """Test work items are created when tasks become enabled."""
    engine = YEngine()
    engine.start()
    spec = _create_spec_with_task()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)
    case = engine.create_case(spec.id)

    engine.start_case(case.id)

    # Task should be enabled and have work item
    work_items = engine.get_enabled_work_items(case.id)
    assert len(work_items) >= 1


def test_allocate_work_item() -> None:
    """Test allocating work item to participant."""
    engine = YEngine()
    engine.start()

    # Add participant
    from kgcl.yawl.resources.y_resource import YParticipant

    participant = YParticipant(id="user1", user_id="user1", first_name="User", last_name="One")
    engine.resource_manager.add_participant(participant)

    # Create case with task
    spec = _create_spec_with_task()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)
    case = engine.create_case(spec.id)
    engine.start_case(case.id)

    # Get enabled work item
    work_items = engine.get_enabled_work_items(case.id)
    assert len(work_items) > 0
    work_item = work_items[0]

    # Allocate to participant
    result = engine.allocate_work_item(work_item.id, "user1")

    assert result is True
    assert work_item.status == WorkItemStatus.ALLOCATED
    assert work_item.allocated_to == "user1"


def test_start_work_item() -> None:
    """Test starting an allocated work item."""
    engine = YEngine()
    engine.start()

    # Setup participant and case
    from kgcl.yawl.resources.y_resource import YParticipant

    participant = YParticipant(id="user1", user_id="user1", first_name="User", last_name="One")
    engine.resource_manager.add_participant(participant)

    spec = _create_spec_with_task()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)
    case = engine.create_case(spec.id)
    engine.start_case(case.id)

    work_items = engine.get_enabled_work_items(case.id)
    work_item = work_items[0]
    engine.allocate_work_item(work_item.id, "user1")

    # Start work item
    result = engine.start_work_item(work_item.id, "user1")

    assert result is True
    assert work_item.status == WorkItemStatus.STARTED


def test_complete_work_item() -> None:
    """Test completing a started work item."""
    engine = YEngine()
    engine.start()

    # Setup participant and case
    from kgcl.yawl.resources.y_resource import YParticipant

    participant = YParticipant(id="user1", user_id="user1", first_name="User", last_name="One")
    engine.resource_manager.add_participant(participant)

    spec = _create_spec_with_task()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)
    case = engine.create_case(spec.id)
    engine.start_case(case.id)

    work_items = engine.get_enabled_work_items(case.id)
    work_item = work_items[0]
    engine.allocate_work_item(work_item.id, "user1")
    engine.start_work_item(work_item.id, "user1")

    # Complete work item
    result = engine.complete_work_item(work_item.id, output_data={"result": 42})

    assert result is True
    assert work_item.status == WorkItemStatus.COMPLETED


def test_fail_work_item() -> None:
    """Test failing a work item."""
    engine = YEngine()
    engine.start()

    from kgcl.yawl.resources.y_resource import YParticipant

    participant = YParticipant(id="user1", name="User One")
    engine.resource_manager.add_participant(participant)

    spec = _create_spec_with_task()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)
    case = engine.create_case(spec.id)
    engine.start_case(case.id)

    work_items = engine.get_enabled_work_items(case.id)
    work_item = work_items[0]
    engine.allocate_work_item(work_item.id, "user1")
    engine.start_work_item(work_item.id, "user1")

    # Fail work item
    result = engine.fail_work_item(work_item.id, reason="Test failure")

    assert result is True
    assert work_item.status == WorkItemStatus.FAILED


# === Event Handling Tests ===


def test_add_event_listener() -> None:
    """Test adding event listener."""
    engine = YEngine()
    events: list[EngineEvent] = []

    def listener(event: EngineEvent) -> None:
        events.append(event)

    engine.add_event_listener(listener)

    assert listener in engine.event_listeners


def test_remove_event_listener() -> None:
    """Test removing event listener."""
    engine = YEngine()

    def listener(event: EngineEvent) -> None:
        pass

    engine.add_event_listener(listener)
    engine.remove_event_listener(listener)

    assert listener not in engine.event_listeners


def test_events_emitted_on_engine_operations() -> None:
    """Test events are emitted for engine operations."""
    engine = YEngine()
    events: list[EngineEvent] = []

    def listener(event: EngineEvent) -> None:
        events.append(event)

    engine.add_event_listener(listener)

    engine.start()

    # Should emit ENGINE_STARTED event
    assert len(events) > 0
    assert any(e.event_type == "ENGINE_STARTED" for e in events)


# === Timer Tests ===


def test_timer_created_for_work_item_with_timer() -> None:
    """Test timer is created for work item when task has timer."""
    engine = YEngine()
    engine.start()

    # Create spec with task that has timer
    spec = _create_spec_with_timer_task()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)
    case = engine.create_case(spec.id)
    engine.start_case(case.id)

    # Timer should be created
    work_items = engine.get_enabled_work_items(case.id)
    assert len(work_items) > 0
    work_item = work_items[0]

    # Check timer service has timer for this work item
    assert len(engine.timer_service.timers) > 0


def test_timer_cancelled_when_work_item_completed() -> None:
    """Test timer is cancelled when work item completes."""
    engine = YEngine()
    engine.start()

    from kgcl.yawl.resources.y_resource import YParticipant

    participant = YParticipant(id="user1", name="User One")
    engine.resource_manager.add_participant(participant)

    spec = _create_spec_with_timer_task()
    engine.load_specification(spec)
    engine.activate_specification(spec.id)
    case = engine.create_case(spec.id)
    engine.start_case(case.id)

    work_items = engine.get_enabled_work_items(case.id)
    work_item = work_items[0]

    # Allocate, start, and complete
    engine.allocate_work_item(work_item.id, "user1")
    engine.start_work_item(work_item.id, "user1")
    engine.complete_work_item(work_item.id)

    # Timer should be cancelled
    assert work_item.id not in [t.work_item_id for t in engine.timer_service.timers]


# === Helper Functions ===


def _create_valid_spec() -> YSpecification:
    """Create a valid minimal specification."""
    spec = YSpecification(id="test_spec", root_net_id="net1")
    net = YNet(id="net1", name="Test Net")

    # Add input and output conditions
    input_cond = YInputCondition(id="input")
    output_cond = YOutputCondition(id="output")
    net.add_condition(input_cond)
    net.add_condition(output_cond)

    # Connect input to output (minimal valid net)
    flow = YFlow(id="flow1", source_id="input", target_id="output")
    net.add_flow(flow)

    spec.add_net(net)
    return spec


def _create_spec_with_task() -> YSpecification:
    """Create specification with a simple task."""
    spec = YSpecification(id="test_spec", root_net_id="net1")
    net = YNet(id="net1", name="Test Net")

    # Add conditions
    input_cond = YInputCondition(id="input")
    output_cond = YOutputCondition(id="output")
    net.add_condition(input_cond)
    net.add_condition(output_cond)

    # Add task
    task = YAtomicTask(id="task1", name="Task 1")
    net.add_task(task)

    # Connect: input -> task -> output
    net.add_flow(YFlow(id="flow1", source_id="input", target_id="task1"))
    net.add_flow(YFlow(id="flow2", source_id="task1", target_id="output"))

    spec.add_net(net)
    return spec


def _create_spec_with_timer_task() -> YSpecification:
    """Create specification with task that has timer."""
    spec = YSpecification(id="test_spec", root_net_id="net1")
    net = YNet(id="net1", name="Test Net")

    # Add conditions
    input_cond = YInputCondition(id="input")
    output_cond = YOutputCondition(id="output")
    net.add_condition(input_cond)
    net.add_condition(output_cond)

    # Add task with timer
    task = YAtomicTask(id="task1", name="Task 1")
    task.timer_trigger = TimerTrigger.ON_ENABLED
    task.timer_duration = timedelta(seconds=60)
    task.timer_action = TimerAction.FAIL
    net.add_task(task)

    # Connect: input -> task -> output
    net.add_flow(YFlow(id="flow1", source_id="input", target_id="task1"))
    net.add_flow(YFlow(id="flow2", source_id="task1", target_id="output"))

    spec.add_net(net)
    return spec
