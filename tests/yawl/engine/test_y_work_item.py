"""Tests for YWorkItem state machine and lifecycle.

Verifies the complete work item lifecycle from ENABLED through COMPLETED,
including all intermediate states and transitions.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from kgcl.yawl.engine.y_work_item import WorkItemEvent, WorkItemLog, WorkItemStatus, WorkItemTimer, YWorkItem


class TestWorkItemCreation:
    """Tests for work item creation and initialization."""

    def test_create_work_item(self) -> None:
        """Create work item with required fields."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")

        assert wi.id == "wi-001"
        assert wi.case_id == "case-001"
        assert wi.task_id == "task-A"
        assert wi.status == WorkItemStatus.ENABLED

    def test_work_item_timestamps(self) -> None:
        """Work item tracks creation timestamp."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")

        assert wi.created is not None
        assert isinstance(wi.created, datetime)
        assert wi.enabled_time is not None


class TestWorkItemStateTransitions:
    """Tests for work item state machine transitions."""

    def test_enabled_to_fired(self) -> None:
        """Transition from ENABLED to FIRED."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")

        assert wi.status == WorkItemStatus.ENABLED

        wi.fire()

        assert wi.status == WorkItemStatus.FIRED
        assert wi.fired_time is not None

    def test_fired_to_offered(self) -> None:
        """Transition from FIRED to OFFERED."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()

        wi.offer({"user-001", "user-002"})

        assert wi.status == WorkItemStatus.OFFERED
        assert wi.offered_to == {"user-001", "user-002"}

    def test_offered_to_allocated(self) -> None:
        """Transition from OFFERED to ALLOCATED."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()
        wi.offer({"user-001"})

        wi.allocate("user-001")

        assert wi.status == WorkItemStatus.ALLOCATED
        assert wi.resource_id == "user-001"

    def test_allocated_to_started(self) -> None:
        """Transition from ALLOCATED to STARTED."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()
        wi.offer({"user-001"})
        wi.allocate("user-001")

        wi.start()

        assert wi.status == WorkItemStatus.STARTED
        assert wi.started_time is not None

    def test_started_to_completed(self) -> None:
        """Transition from STARTED to COMPLETED."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()
        wi.offer({"user-001"})
        wi.allocate("user-001")
        wi.start()

        wi.complete({"result": "success"})

        assert wi.status == WorkItemStatus.COMPLETED
        assert wi.completed_time is not None
        assert wi.data_output == {"result": "success"}

    def test_full_lifecycle(self) -> None:
        """Full lifecycle: ENABLED -> FIRED -> OFFERED -> ALLOCATED -> STARTED -> COMPLETED."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")

        assert wi.status == WorkItemStatus.ENABLED
        wi.fire()
        assert wi.status == WorkItemStatus.FIRED
        wi.offer({"user-001"})
        assert wi.status == WorkItemStatus.OFFERED
        wi.allocate("user-001")
        assert wi.status == WorkItemStatus.ALLOCATED
        wi.start()
        assert wi.status == WorkItemStatus.STARTED
        wi.complete({"done": True})
        assert wi.status == WorkItemStatus.COMPLETED


class TestWorkItemAlternativeTransitions:
    """Tests for alternative state transitions."""

    def test_suspend_from_started(self) -> None:
        """Suspend a started work item."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()
        wi.offer({"user-001"})
        wi.allocate("user-001")
        wi.start()

        wi.suspend()

        assert wi.status == WorkItemStatus.SUSPENDED

    def test_resume_from_suspended(self) -> None:
        """Resume a suspended work item."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()
        wi.offer({"user-001"})
        wi.allocate("user-001")
        wi.start()
        wi.suspend()

        wi.resume()

        assert wi.status == WorkItemStatus.STARTED

    def test_cancel_work_item(self) -> None:
        """Cancel a work item."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()

        wi.cancel()

        assert wi.status == WorkItemStatus.CANCELLED

    def test_fail_work_item(self) -> None:
        """Fail a work item."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()
        wi.offer({"user-001"})
        wi.allocate("user-001")
        wi.start()

        wi.fail("Task execution error")

        assert wi.status == WorkItemStatus.FAILED

    def test_force_complete(self) -> None:
        """Force complete a work item."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()
        wi.offer({"user-001"})
        wi.allocate("user-001")
        wi.start()

        wi.force_complete("Administrative completion")

        assert wi.status == WorkItemStatus.FORCE_COMPLETED


class TestWorkItemActiveStatus:
    """Tests for is_active() helper."""

    def test_enabled_is_active(self) -> None:
        """ENABLED work item is active."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        assert wi.is_active()

    def test_started_is_active(self) -> None:
        """STARTED work item is active."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()
        wi.offer({"user-001"})
        wi.allocate("user-001")
        wi.start()
        assert wi.is_active()

    def test_completed_not_active(self) -> None:
        """COMPLETED work item is not active."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()
        wi.offer({"user-001"})
        wi.allocate("user-001")
        wi.start()
        wi.complete({})
        assert not wi.is_active()

    def test_cancelled_not_active(self) -> None:
        """CANCELLED work item is not active."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()
        wi.cancel()
        assert not wi.is_active()


class TestWorkItemFinished:
    """Tests for is_finished() helper."""

    def test_completed_is_finished(self) -> None:
        """COMPLETED work item is finished."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()
        wi.offer({"user-001"})
        wi.allocate("user-001")
        wi.start()
        wi.complete({})
        assert wi.is_finished()
        assert wi.is_successful()

    def test_failed_is_finished(self) -> None:
        """FAILED work item is finished."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()
        wi.offer({"user-001"})
        wi.allocate("user-001")
        wi.start()
        wi.fail("Error")
        assert wi.is_finished()
        assert not wi.is_successful()


class TestWorkItemHistory:
    """Tests for work item history tracking."""

    def test_history_tracks_transitions(self) -> None:
        """History tracks all state transitions."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")

        wi.fire()
        wi.offer({"user-001"})
        wi.allocate("user-001")
        wi.start()
        wi.complete({})

        assert len(wi.history) == 5
        assert wi.history[0].event == WorkItemEvent.FIRE
        assert wi.history[1].event == WorkItemEvent.OFFER
        assert wi.history[2].event == WorkItemEvent.ALLOCATE
        assert wi.history[3].event == WorkItemEvent.START
        assert wi.history[4].event == WorkItemEvent.COMPLETE


class TestWorkItemTimer:
    """Tests for work item timer handling."""

    def test_timer_creation(self) -> None:
        """Create work item timer."""
        timer = WorkItemTimer(trigger="OnStarted", duration="PT1H", action="escalate")

        assert timer.trigger == "OnStarted"
        assert timer.duration == "PT1H"
        assert timer.action == "escalate"

    def test_timer_is_expired(self) -> None:
        """Check if timer is expired."""
        timer = WorkItemTimer(
            trigger="OnEnabled",
            duration="PT1H",
            action="notify",
            expiry=datetime(2020, 1, 1),  # Past
        )

        assert timer.is_expired()

    def test_timer_not_expired(self) -> None:
        """Check if timer is not expired when expiry is None."""
        timer = WorkItemTimer(trigger="OnEnabled", duration="PT1H", action="notify", expiry=None)

        assert not timer.is_expired()


class TestWorkItemData:
    """Tests for work item data input/output."""

    def test_data_input(self) -> None:
        """Work item can have input data."""
        wi = YWorkItem(
            id="wi-001",
            case_id="case-001",
            task_id="task-A",
            specification_id="spec-001",
            net_id="net-001",
            data_input={"order_id": "123", "amount": 100.0},
        )

        assert wi.data_input["order_id"] == "123"
        assert wi.data_input["amount"] == 100.0

    def test_data_output_on_completion(self) -> None:
        """Data output set on completion."""
        wi = YWorkItem(id="wi-001", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001")
        wi.fire()
        wi.offer({"user-001"})
        wi.allocate("user-001")
        wi.start()

        output_data = {"approved": True, "approver": "user-001"}
        wi.complete(output_data)

        assert wi.data_output == output_data


class TestWorkItemHierarchy:
    """Tests for parent/child work item relationships."""

    def test_parent_child_relationship(self) -> None:
        """Work items can have parent/child relationships."""
        parent = YWorkItem(
            id="wi-parent", case_id="case-001", task_id="task-A", specification_id="spec-001", net_id="net-001"
        )

        child1 = YWorkItem(
            id="wi-child-1",
            case_id="case-001",
            task_id="task-A",
            specification_id="spec-001",
            net_id="net-001",
            parent_id="wi-parent",
        )

        child2 = YWorkItem(
            id="wi-child-2",
            case_id="case-001",
            task_id="task-A",
            specification_id="spec-001",
            net_id="net-001",
            parent_id="wi-parent",
        )

        parent.add_child("wi-child-1")
        parent.add_child("wi-child-2")

        assert child1.parent_id == "wi-parent"
        assert child2.parent_id == "wi-parent"
        assert len(parent.children) == 2
        assert parent.status == WorkItemStatus.PARENT
