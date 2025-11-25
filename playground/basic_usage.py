"""
Basic usage playground - Uses installed package, not source.
This demonstrates the Chicago TDD Tools framework in action.
"""

# Import from the built package (not src/)
from chicago_tdd_tools.core import (
    AssertionBuilder,
    TestFixture,
    assert_eq_with_msg,
    assert_that,
    fixture_test,
    test,
)
from chicago_tdd_tools.swarm import SwarmMember, TaskStatus, TestCoordinator, TestTask
from chicago_tdd_tools.testing import StateMachine
from chicago_tdd_tools.validation import Property

# ============================================================================
# Example 1: Simple assertions
# ============================================================================


@test
def example_basic_assertions():
    """Demonstrate basic assertion functions."""
    print("\n=== Example 1: Basic Assertions ===")

    # Arrange
    x, y = 5, 3

    # Act
    result = x + y

    # Assert
    assert_eq_with_msg(result, 8, "5 + 3 should equal 8")
    assert_that(result, lambda v: v > 0, "Result should be positive")
    print("✓ Basic assertions passed")


# ============================================================================
# Example 2: Fluent assertion builder
# ============================================================================


@test
def example_assertion_builder():
    """Demonstrate fluent assertion builder pattern."""
    print("\n=== Example 2: Assertion Builder ===")

    value = 42
    result = (
        AssertionBuilder(value)
        .assert_equal(42)
        .assert_that(lambda v: v > 0)
        .assert_that(lambda v: v < 100)
        .get()
    )

    assert result == 42
    print("✓ Assertion builder passed")


# ============================================================================
# Example 3: Test fixtures
# ============================================================================


class CounterFixture(TestFixture):
    """Simple counter fixture for testing."""

    def setup(self):
        self.counter = 0
        self.history = []
        self._initialized = True

    def increment(self):
        self.counter += 1
        self.history.append(self.counter)
        return self.counter

    def get_counter(self):
        return self.counter

    def cleanup(self):
        del self.counter
        del self.history


@fixture_test(CounterFixture)
def example_fixture(fixture):
    """Demonstrate fixture-based testing."""
    print("\n=== Example 3: Test Fixtures ===")

    assert fixture.increment() == 1
    assert fixture.increment() == 2
    assert fixture.increment() == 3
    assert fixture.get_counter() == 3
    assert len(fixture.history) == 3

    print(f"✓ Fixture test passed (counter={fixture.get_counter()}, history={fixture.history})")


# ============================================================================
# Example 4: Property-based testing
# ============================================================================


def example_property_testing():
    """Demonstrate property-based testing."""
    print("\n=== Example 4: Property-Based Testing ===")

    # Test: Addition is commutative
    test = (
        Property()
        .name("addition_commutative")
        .predicate(lambda a, b: a + b == b + a)
        .example(1, 2)
        .example(5, 3)
        .example(-1, 1)
        .example(0, 0)
        .build()
    )

    if test.run():
        print(f"✓ Property test passed ({len(test.examples)} examples)")
    else:
        print(f"✗ Property test failed ({test.failure_count()} failures)")


# ============================================================================
# Example 5: State machines
# ============================================================================


def example_state_machine():
    """Demonstrate state machine testing."""
    print("\n=== Example 5: State Machines ===")

    sm = StateMachine("pending")
    sm.add_transition("pending", "confirmed", "confirm")
    sm.add_transition("confirmed", "shipped", "ship")
    sm.add_transition("shipped", "delivered", "deliver")

    # Execute workflow
    assert sm.perform_action("confirm")
    assert sm.current_state() == "confirmed"

    assert sm.perform_action("ship")
    assert sm.current_state() == "shipped"

    assert sm.perform_action("deliver")
    assert sm.current_state() == "delivered"

    # Check history
    expected = ["pending", "confirmed", "shipped", "delivered"]
    assert sm.history() == expected

    print(f"✓ State machine test passed (workflow: {' → '.join(sm.history())})")


# ============================================================================
# Example 6: Swarm coordination
# ============================================================================


def example_swarm_coordination():
    """Demonstrate test swarm orchestration."""
    print("\n=== Example 6: Swarm Coordination ===")

    # Create coordinator
    coordinator = TestCoordinator(max_workers=2)

    # Create test members
    for i in range(2):
        member = SwarmMember(f"worker-{i + 1}")

        # Register task handler
        def handler(task):
            from chicago_tdd_tools.swarm import TaskResult

            return TaskResult(
                task_name=task.name, status=TaskStatus.SUCCESS, output=f"Executed {task.name}"
            )

        member.register_handler("unit_test", handler)
        coordinator.register_member(member)

    # Execute task across swarm
    task = TestTask("integration_test", task_type="unit_test")
    results = coordinator.execute(task)

    # Check results
    success_count = sum(1 for r in results.values() if r.is_success())
    print(f"✓ Swarm test passed ({success_count}/{coordinator.member_count()} members succeeded)")


# ============================================================================
# Main execution
# ============================================================================


def main():
    """Run all playground examples."""
    print("=" * 70)
    print("Chicago TDD Tools - Python Implementation")
    print("Playground Examples (Using Installed Package)")
    print("=" * 70)

    try:
        # Run basic tests
        example_basic_assertions()
        example_assertion_builder()
        example_fixture()

        # Run property and state machine examples
        example_property_testing()
        example_state_machine()
        example_swarm_coordination()

        print("\n" + "=" * 70)
        print("✓ All playground examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error during execution: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
