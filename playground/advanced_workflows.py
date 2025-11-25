"""
Advanced workflows playground - Demonstrates complex test scenarios.
Uses the installed chicago-tdd-tools package, not source.
"""

from chicago_tdd_tools.core import (
    test,
    TestFixture,
    fixture_test,
    StateManager,
    FailFastValidator,
    Poka,
    PokaYokeError,
)
from chicago_tdd_tools.validation import (
    InvariantValidator,
    Guard,
    ValidatedValue,
)
from chicago_tdd_tools.testing import PropertyBasedTest, SnapshotTest
from enum import Enum
import tempfile


# ============================================================================
# Example 1: State management with validators
# ============================================================================

class OrderState(Enum):
    """Order workflow states."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


def example_state_management():
    """Demonstrate state management with validators."""
    print("\n=== Example 1: State Management with Validators ===")

    sm = StateManager(OrderState.PENDING)

    # Add validator: can only transition to CONFIRMED from PENDING
    def can_confirm(current_state):
        return current_state == OrderState.PENDING

    sm.add_validator(OrderState.CONFIRMED, can_confirm)

    # Execute valid transition
    assert sm.transition_to(OrderState.CONFIRMED)
    assert sm.current_state() == OrderState.CONFIRMED

    # Try invalid transition (should fail validation)
    assert not sm.transition_to(OrderState.PENDING)
    assert sm.current_state() == OrderState.CONFIRMED

    print(f"✓ State management passed (history: {[s.value for s in sm.history()]})")


# ============================================================================
# Example 2: Fail-fast validation
# ============================================================================

def example_fail_fast():
    """Demonstrate fail-fast validation."""
    print("\n=== Example 2: Fail-Fast Validation ===")

    validator = FailFastValidator(fail_fast=False)

    # Check multiple conditions
    validator.check_equal("first_check", 5, 5)
    validator.check_equal("second_check", 10, 10)
    validator.check_that("positive_test", lambda: 42 > 0)
    validator.check_false("false_test", False)

    # Assert all passed
    validator.assert_all_pass()
    print(f"✓ Fail-fast validation passed (all checks succeeded)")


# ============================================================================
# Example 3: Poka-Yoke error prevention
# ============================================================================

def example_poka_yoke():
    """Demonstrate Poka-Yoke error prevention."""
    print("\n=== Example 3: Poka-Yoke Error Prevention ===")

    # Unwrap with valid value
    value = Poka.unwrap(42, "expected value")
    assert value == 42

    # Unwrap with default
    default_value = Poka.unwrap_or(None, 0)
    assert default_value == 0

    # Not none check
    result = Poka.not_none(42, "value should not be none")
    assert result == 42

    # Try unwrap with None (should raise)
    try:
        Poka.unwrap(None, "this should fail")
        assert False, "Should have raised PokaYokeError"
    except PokaYokeError:
        pass

    print("✓ Poka-Yoke error prevention passed")


# ============================================================================
# Example 4: Invariant validation
# ============================================================================

def example_invariant_validation():
    """Demonstrate invariant validation."""
    print("\n=== Example 4: Invariant Validation ===")

    validator = InvariantValidator()

    # Add invariants for a list
    validator.add("non_empty", lambda lst: len(lst) > 0)
    validator.add("all_positive", lambda lst: all(x > 0 for x in lst))
    validator.add("ascending", lambda lst: lst == sorted(lst))

    # Valid list
    valid_list = [1, 2, 3, 4, 5]
    assert validator.validate_all(valid_list)
    assert not validator.has_violations()

    # Invalid list
    validator.reset()
    invalid_list = [5, 2, 3, 1, 4]  # Not sorted
    assert not validator.validate_all(invalid_list)
    assert validator.has_violations()

    print(f"✓ Invariant validation passed ({len(validator._invariants)} invariants checked)")


# ============================================================================
# Example 5: Guard types
# ============================================================================

def example_guard_types():
    """Demonstrate guard types for validated values."""
    print("\n=== Example 5: Guard Types ===")

    # Create validated guard
    positive_guard = Guard.validated(42, lambda x: x > 0)
    assert positive_guard.get() == 42

    # Try invalid value
    try:
        Guard.validated(-1, lambda x: x > 0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

    # ValidatedValue with multiple validators
    val = ValidatedValue(
        50,
        [
            ("positive", lambda x: x > 0),
            ("under_100", lambda x: x < 100),
        ]
    )
    assert val.is_valid()
    assert val.get() == 50

    print("✓ Guard types passed")


# ============================================================================
# Example 6: Property-based testing with statistics
# ============================================================================

def example_property_statistics():
    """Demonstrate property-based testing with statistics."""
    print("\n=== Example 6: Property Statistics ===")

    test = PropertyBasedTest(
        "multiplication_property",
        lambda a, b: a * b == b * a  # Commutative property
    )

    # Add examples
    for a in range(1, 6):
        for b in range(1, 6):
            test.add_example(a * b)

    # Run test
    test.run()
    success_rate = test.success_rate()

    print(f"✓ Property statistics passed (success rate: {success_rate:.1f}%)")


# ============================================================================
# Example 7: Snapshot testing
# ============================================================================

def example_snapshot_testing():
    """Demonstrate snapshot testing for regression detection."""
    print("\n=== Example 7: Snapshot Testing ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot_file = f"{tmpdir}/snapshot.json"

        # Create initial snapshot
        api_response = {
            "status": 200,
            "data": [1, 2, 3],
            "timestamp": "2024-01-01T00:00:00Z"
        }

        test = SnapshotTest("api_response", api_response)
        test.matches_snapshot(snapshot_file, update=True)
        assert test.matched

        # Verify snapshot matches on re-run
        test2 = SnapshotTest("api_response", api_response)
        assert test2.matches_snapshot(snapshot_file)

        # Detect regression (changed data)
        test3 = SnapshotTest("api_response", {"status": 200, "data": [4, 5, 6]})
        assert not test3.matches_snapshot(snapshot_file)

    print("✓ Snapshot testing passed")


# ============================================================================
# Example 8: Complex fixture with state
# ============================================================================

class DatabaseFixture(TestFixture):
    """Simulated database fixture."""

    def setup(self):
        self.data = {}
        self.transaction_count = 0
        self._initialized = True

    def insert(self, key, value):
        self.data[key] = value
        self.transaction_count += 1

    def query(self, key):
        return self.data.get(key)

    def delete(self, key):
        if key in self.data:
            del self.data[key]
            self.transaction_count += 1

    def cleanup(self):
        self.data.clear()


@fixture_test(DatabaseFixture)
def example_complex_fixture(fixture):
    """Demonstrate complex fixture with state tracking."""
    print("\n=== Example 8: Complex Fixture ===")

    # Insert data
    fixture.insert("user:1", {"name": "Alice", "email": "alice@example.com"})
    fixture.insert("user:2", {"name": "Bob", "email": "bob@example.com"})

    # Query data
    alice = fixture.query("user:1")
    assert alice["name"] == "Alice"

    # Check transaction count
    assert fixture.transaction_count == 2

    # Delete and verify
    fixture.delete("user:1")
    assert fixture.query("user:1") is None
    assert fixture.transaction_count == 3

    print(f"✓ Complex fixture passed ({fixture.transaction_count} transactions)")


# ============================================================================
# Main execution
# ============================================================================

def main():
    """Run all advanced workflow examples."""
    print("=" * 70)
    print("Chicago TDD Tools - Advanced Workflows")
    print("(Using Installed Package)")
    print("=" * 70)

    try:
        example_state_management()
        example_fail_fast()
        example_poka_yoke()
        example_invariant_validation()
        example_guard_types()
        example_property_statistics()
        example_snapshot_testing()
        example_complex_fixture()

        print("\n" + "=" * 70)
        print("✓ All advanced workflow examples completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error during execution: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
