"""Tests for core module."""

import pytest
from src.core import (
    ChicagoAssertionError,
    FailFastValidator,
    Poka,
    PokaYokeError,
    StateManager,
    TestFixture,
    assert_eq_with_msg,
    assert_error,
    assert_in_range,
    assert_success,
    assert_that,
)


class TestAssertions:
    """Test assertion functions."""

    def test_assert_success_with_true(self):
        """Test assert_success with truthy value."""
        assert_success(True)
        assert_success(42)
        assert_success("non-empty")

    def test_assert_error_with_false(self):
        """Test assert_error with falsy value."""
        assert_error(False)
        assert_error(None)

    def test_assert_eq_with_msg(self):
        """Test equality assertion."""
        assert_eq_with_msg(5, 5, "values should match")
        with pytest.raises(ChicagoAssertionError):
            assert_eq_with_msg(5, 6, "values should match")

    def test_assert_in_range(self):
        """Test range assertion."""
        assert_in_range(50, 0, 100, "value in range")
        with pytest.raises(ChicagoAssertionError):
            assert_in_range(150, 0, 100, "value in range")

    def test_assert_that(self):
        """Test predicate assertion."""
        assert_that(42, lambda v: v > 0)
        with pytest.raises(ChicagoAssertionError):
            assert_that(-1, lambda v: v > 0)

    def test_assertion_builder(self):
        """Test assertion builder pattern."""
        result = (
            AssertionBuilder(42).assert_equal(42).assert_that(lambda v: v > 0).assert_true().get()
        )
        assert result == 42


class TestFixtures:
    """Test fixture functionality."""

    def test_fixture_basic(self):
        """Test basic fixture lifecycle."""

        class TestFixture1(TestFixture):
            def setup(self):
                self.value = 42

            def cleanup(self):
                del self.value

        fixture = TestFixture1()
        fixture.setup()
        assert fixture.value == 42
        fixture.cleanup()

    def test_fixture_metadata(self):
        """Test fixture metadata tracking."""
        fixture = TestFixture()
        fixture.setup()
        metadata = fixture.metadata()
        assert metadata is not None
        assert metadata.age_seconds() >= 0

    def test_fixture_state(self):
        """Test fixture state management."""
        fixture = TestFixture()
        fixture.set_state("key", "value")
        assert fixture.get_state("key") == "value"
        assert fixture.get_state("missing", "default") == "default"


class TestStateManager:
    """Test state management."""

    def test_state_transitions(self):
        """Test state transitions."""
        from enum import Enum

        class State(Enum):
            START = "start"
            END = "end"

        sm = StateManager(State.START)
        assert sm.current_state() == State.START

        sm.transition_to(State.END)
        assert sm.current_state() == State.END
        assert len(sm.history()) == 2

    def test_state_history(self):
        """Test state history."""
        from enum import Enum

        class State(Enum):
            A = "a"
            B = "b"
            C = "c"

        sm = StateManager(State.A)
        sm.transition_to(State.B)
        sm.transition_to(State.C)

        assert sm.history() == [State.A, State.B, State.C]


class TestFailFastValidator:
    """Test fail-fast validation."""

    def test_fail_fast_validator(self):
        """Test fail-fast behavior."""
        validator = FailFastValidator(fail_fast=False)

        assert validator.check_that("positive", lambda: True)
        assert not validator.check_that("negative", lambda: False)
        assert validator.failure_count() == 1

    def test_assert_all_pass(self):
        """Test assertion of all checks passing."""
        validator = FailFastValidator()
        validator.check_that("test", lambda: True)
        validator.assert_all_pass()  # Should not raise


class TestPoka:
    """Test Poka-Yoke error prevention."""

    def test_unwrap_success(self):
        """Test unwrap with valid value."""
        result = Poka.unwrap(42, "value")
        assert result == 42

    def test_unwrap_none(self):
        """Test unwrap with None."""
        with pytest.raises(PokaYokeError):
            Poka.unwrap(None, "expected value")

    def test_expect_alias(self):
        """Test expect as alias for unwrap."""
        assert Poka.expect(42, "msg") == 42

    def test_unwrap_or(self):
        """Test unwrap with default."""
        assert Poka.unwrap_or(42, 0) == 42
        assert Poka.unwrap_or(None, 0) == 0

    def test_not_none(self):
        """Test not_none check."""
        assert Poka.not_none(42, "expected value") == 42
        with pytest.raises(PokaYokeError):
            Poka.not_none(None, "value is None")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
