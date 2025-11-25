"""Tests for swarm orchestration."""

import pytest
from src.swarm import (
    SwarmMember,
    TaskResult,
    TaskStatus,
    TestComposition,
    TestCoordinator,
    TestTask,
)


class TestSwarmMember:
    """Test swarm member functionality."""

    def test_member_creation(self):
        """Test creating a swarm member."""
        member = SwarmMember("test-worker")
        assert member.name() == "test-worker"

    def test_register_handler(self):
        """Test registering task handler."""
        member = SwarmMember("worker")

        def handler(task):
            return TaskResult(task_name=task.name, status=TaskStatus.SUCCESS, output="done")

        member.register_handler("unit_test", handler)
        assert "unit_test" in [h for h in dir(member)]

    def test_execute_task(self):
        """Test executing a task."""
        member = SwarmMember("worker")

        def handler(task):
            return TaskResult(task_name=task.name, status=TaskStatus.SUCCESS)

        member.register_handler("test", handler)

        task = TestTask("my_test", task_type="test")
        result = member.execute_task(task)

        assert result.is_success()
        assert result.task_name == "my_test"


class TestCoordinator:
    """Test test coordinator."""

    def test_coordinator_creation(self):
        """Test creating coordinator."""
        coordinator = TestCoordinator(max_workers=4)
        assert coordinator.member_count() == 0

    def test_register_member(self):
        """Test registering members."""
        coordinator = TestCoordinator()
        member = SwarmMember("worker-1")
        coordinator.register_member(member)
        assert coordinator.member_count() == 1

    def test_execute_task(self):
        """Test executing task across members."""
        coordinator = TestCoordinator()

        # Create member with handler
        member = SwarmMember("worker")

        def handler(task):
            return TaskResult(task_name=task.name, status=TaskStatus.SUCCESS)

        member.register_handler("test", handler)

        coordinator.register_member(member)

        # Execute task
        task = TestTask("test_task", task_type="test")
        results = coordinator.execute(task)

        assert "worker" in results
        assert results["worker"].is_success()

    def test_metrics(self):
        """Test coordination metrics."""
        coordinator = TestCoordinator()
        member = SwarmMember("worker")

        def handler(task):
            return TaskResult(task_name=task.name, status=TaskStatus.SUCCESS)

        member.register_handler("test", handler)
        coordinator.register_member(member)

        task = TestTask("test", task_type="test")
        coordinator.execute(task)

        metrics = coordinator.metrics()
        assert metrics.total_tasks == 1
        assert metrics.completed_tasks == 1


class TestTask:
    """Test task functionality."""

    def test_task_creation(self):
        """Test creating task."""
        task = TestTask("my_test", task_type="unit_test")
        assert task.name == "my_test"
        assert task.task_type == "unit_test"

    def test_task_with_payload(self):
        """Test task with payload."""
        task = TestTask("test")
        task.with_payload("key", "value")
        assert task.get_payload("key") == "value"

    def test_task_result(self):
        """Test task result."""
        result = TaskResult(task_name="test", status=TaskStatus.SUCCESS, output="done")
        assert result.is_success()
        assert result.output == "done"


class TestComposition:
    """Test test composition."""

    def test_sequential_execution(self):
        """Test sequential test composition."""
        results = []

        composition = (
            TestComposition("sequential")
            .sequential()
            .add_test(lambda: results.append(1))
            .add_test(lambda: results.append(2))
            .add_test(lambda: results.append(3))
        )

        composition.execute()
        assert results == [1, 2, 3]

    def test_composition_with_hooks(self):
        """Test composition with before/after hooks."""
        state = {"setup": False, "teardown": False}

        composition = (
            TestComposition("with_hooks")
            .before(lambda: state.update({"setup": True}))
            .add_test(lambda: None)
            .after(lambda: state.update({"teardown": True}))
        )

        composition.execute()
        assert state["setup"] is True
        assert state["teardown"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
