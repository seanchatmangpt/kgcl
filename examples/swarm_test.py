"""Swarm test orchestration example."""

from src.swarm import SwarmMember, TaskStatus, TestCoordinator, TestTask


def create_test_member(name: str):
    """Create a test member with handlers."""
    member = SwarmMember(name)

    # Register handler for unit_test tasks
    def unit_test_handler(task):
        from src.swarm.task import TaskResult

        # Simulate test execution
        output = f"{name} executed unit_test task: {task.name}"
        return TaskResult(task_name=task.name, status=TaskStatus.SUCCESS, output=output)

    member.register_handler("unit_test", unit_test_handler)
    return member


def main():
    """Run swarm test example."""
    # Create coordinator
    coordinator = TestCoordinator(max_workers=2)

    # Register members
    member1 = create_test_member("worker-1")
    member2 = create_test_member("worker-2")
    coordinator.register_member(member1)
    coordinator.register_member(member2)

    # Execute task across swarm
    task = TestTask("integration_test", task_type="unit_test")
    results = coordinator.execute(task)

    # Check results
    print(f"Task executed across {coordinator.member_count()} members")
    for member_name, result in results.items():
        print(f"  {member_name}: {result.status.value}")

    metrics = coordinator.metrics()
    print(f"Success rate: {metrics.success_rate():.1f}%")


if __name__ == "__main__":
    main()
