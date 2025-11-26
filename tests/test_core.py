"""Tests for core module."""

from typing import Final

import pytest
from src.core import (
    ChicagoAssertionError,
    FailFastValidator,
    Fixture,
    Poka,
    PokaYokeError,
    StateManager,
    assert_eq_with_msg,
    assert_error,
    assert_in_range,
    assert_success,
    assert_that,
)
from src.core.assertions import AssertionBuilder
from src.core.state import State as CoreState

POSITIVE_SENTINEL: Final[int] = 42
NEGATIVE_SENTINEL: Final[int] = -1
DEFAULT_FALLBACK: Final[int] = 0
RANGE_MIN: Final[int] = 0
RANGE_MAX: Final[int] = 100
STATE_HISTORY_LENGTH: Final[int] = 2


class TestAssertions:
    """Test assertion functions."""

    def test_assert_success_with_true(self) -> None:
        """Test assert_success with truthy value."""
        assert_success(result=True)
        assert_success(POSITIVE_SENTINEL)
        assert_success("non-empty")

    def test_assert_error_with_false(self) -> None:
        """Test assert_error with falsy value."""
        assert_error(result=False)
        assert_error(None)

    def test_assert_eq_with_msg(self) -> None:
        """Test equality assertion."""
        assert_eq_with_msg(5, 5, "values should match")
        with pytest.raises(ChicagoAssertionError):
            assert_eq_with_msg(5, 6, "values should match")

    def test_assert_in_range(self) -> None:
        """Test range assertion."""
        midpoint = 50
        assert_in_range(midpoint, RANGE_MIN, RANGE_MAX, "value in range")
        with pytest.raises(ChicagoAssertionError):
            assert_in_range(150, RANGE_MIN, RANGE_MAX, "value in range")

    def test_assert_that(self) -> None:
        """Test predicate assertion."""
        assert_that(POSITIVE_SENTINEL, lambda value: value > 0)
        with pytest.raises(ChicagoAssertionError):
            assert_that(NEGATIVE_SENTINEL, lambda value: value > 0)

    def test_assertion_builder(self) -> None:
        """Test assertion builder pattern."""
        result = (
            AssertionBuilder(POSITIVE_SENTINEL)
            .assert_equal(POSITIVE_SENTINEL)
            .assert_that(lambda value: value > 0)
            .assert_true()
            .get()
        )
        assert result == POSITIVE_SENTINEL


class TestFixtures:
    """Test fixture functionality."""

    def test_fixture_basic(self) -> None:
        """Test basic fixture lifecycle."""

        class LocalFixture(Fixture):
            def setup(self) -> None:
                self.value = POSITIVE_SENTINEL

            def cleanup(self) -> None:
                del self.value

        fixture = LocalFixture()
        fixture.setup()
        assert fixture.value == POSITIVE_SENTINEL
        fixture.cleanup()

    def test_fixture_metadata(self) -> None:
        """Test fixture metadata tracking."""
        fixture = Fixture()
        fixture.setup()
        metadata = fixture.metadata()
        assert metadata is not None
        assert metadata.age_seconds() >= 0

    def test_fixture_state(self) -> None:
        """Test fixture state management."""
        fixture = Fixture()
        fixture.set_state("key", "value")
        assert fixture.get_state("key") == "value"
        assert fixture.get_state("missing", "default") == "default"


class TestStateManager:
    """Test state management."""

    def test_state_transitions(self) -> None:
        """Test state transitions."""

        class SampleState(CoreState):
            START = "start"
            END = "end"

        sm = StateManager(SampleState.START)
        assert sm.current_state() == SampleState.START

        sm.transition_to(SampleState.END)
        assert sm.current_state() == SampleState.END
        assert len(sm.history()) == STATE_HISTORY_LENGTH

    def test_state_history(self) -> None:
        """Test state history."""

        class ExtendedState(CoreState):
            A = "a"
            B = "b"
            C = "c"

        sm = StateManager(ExtendedState.A)
        sm.transition_to(ExtendedState.B)
        sm.transition_to(ExtendedState.C)

        assert sm.history() == [ExtendedState.A, ExtendedState.B, ExtendedState.C]


class TestFailFastValidator:
    """Test fail-fast validation."""

    def test_fail_fast_validator(self) -> None:
        """Test fail-fast behavior."""
        validator = FailFastValidator(fail_fast=False)

        assert validator.check_that("positive", lambda: True)
        assert not validator.check_that("negative", lambda: False)
        assert validator.failure_count() == 1

    def test_assert_all_pass(self) -> None:
        """Test assertion of all checks passing."""
        validator = FailFastValidator()
        validator.check_that("test", lambda: True)
        validator.assert_all_pass()  # Should not raise


class TestPoka:
    """Test Poka-Yoke error prevention."""

    def test_unwrap_success(self) -> None:
        """Test unwrap with valid value."""
        result = Poka.unwrap(POSITIVE_SENTINEL, "value")
        assert result == POSITIVE_SENTINEL

    def test_unwrap_none(self) -> None:
        """Test unwrap with None."""
        with pytest.raises(PokaYokeError):
            Poka.unwrap(None, "expected value")

    def test_expect_alias(self) -> None:
        """Test expect as alias for unwrap."""
        assert Poka.expect(POSITIVE_SENTINEL, "msg") == POSITIVE_SENTINEL

    def test_unwrap_or(self) -> None:
        """Test unwrap with default."""
        assert Poka.unwrap_or(POSITIVE_SENTINEL, DEFAULT_FALLBACK) == POSITIVE_SENTINEL
        assert Poka.unwrap_or(None, DEFAULT_FALLBACK) == DEFAULT_FALLBACK

    def test_not_none(self) -> None:
        """Test not_none check."""
        assert Poka.not_none(POSITIVE_SENTINEL, "expected value") == POSITIVE_SENTINEL
        with pytest.raises(PokaYokeError):
            Poka.not_none(None, "value is None")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
