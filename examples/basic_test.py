"""Basic test example using Chicago TDD principles."""

from src.core import AssertionBuilder, assert_eq_with_msg, assert_that, test


@test
def test_addition():
    """Simple arithmetic test following AAA pattern."""
    # Arrange
    x, y = 5, 3

    # Act
    result = x + y

    # Assert
    assert_eq_with_msg(result, 8, "5 + 3 should equal 8")


@test
def test_with_predicate():
    """Test using predicate-based assertions."""
    value = 42
    assert_that(value, lambda v: v > 0, "Value should be positive")
    assert_that(value, lambda v: v < 100, "Value should be under 100")


@test
def test_assertion_builder():
    """Test using fluent assertion builder."""
    value = 42
    result = (
        AssertionBuilder(value)
        .assert_that(lambda v: v > 0)
        .assert_that(lambda v: v < 100)
        .assert_equal(42)
        .get()
    )

    assert result == 42


if __name__ == "__main__":
    test_addition()
    test_with_predicate()
    test_assertion_builder()
    print("✓ All tests passed!")
