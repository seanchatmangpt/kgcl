"""Tests for validation module."""

import pytest
from src.validation.guards import Guard, ValidatedValue
from src.validation.invariants import Invariant, InvariantValidator
from src.validation.property import Property, PropertyGenerator, PropertyTest

POSITIVE_VALUE: int = 42
SECONDARY_POSITIVE_VALUE: int = 50
NEGATIVE_VALUE: int = -1
MAX_THRESHOLD: int = 100
DOUBLE_FACTOR: int = 2
DEFAULT_VALUE: int = 0
PROPERTY_EXAMPLE_COUNT: int = 2
PROPERTY_FAILURE_COUNT: int = 3
INTEGER_SAMPLE_COUNT: int = 10
BOOLEAN_SAMPLE_COUNT: int = 5


class TestProperty:
    """Test property-based testing."""

    def test_property_builder(self) -> None:
        """Test property builder."""
        test = (
            Property()
            .name("test_add")
            .predicate(lambda a, b: a + b == b + a)
            .example(1, 2)
            .example(3, 4)
            .build()
        )

        assert test.name == "test_add"
        assert len(test.examples) == PROPERTY_EXAMPLE_COUNT

    def test_property_test_run(self) -> None:
        """Test running property test."""
        test = PropertyTest(
            "commutative",
            lambda a, b: a + b == b + a,
            examples=[(1, 2), (3, 4), (5, 6)],
        )

        assert test.run() is True
        assert test.failure_count() == 0

    def test_property_test_failure(self) -> None:
        """Test property test with failures."""
        test = PropertyTest("always_true", lambda _: False, examples=[(1,), (2,), (3,)])

        assert test.run() is False
        assert test.failure_count() == PROPERTY_FAILURE_COUNT


class TestPropertyGenerator:
    """Test property generators."""

    def test_integer_generator(self) -> None:
        """Test integer generator."""
        gen = PropertyGenerator.integers(min=0, max=MAX_THRESHOLD)
        values = gen.take(INTEGER_SAMPLE_COUNT)
        assert len(values) == INTEGER_SAMPLE_COUNT
        assert all(0 <= v <= MAX_THRESHOLD for v in values)

    def test_boolean_generator(self) -> None:
        """Test boolean generator."""
        gen = PropertyGenerator.booleans()
        values = gen.take(BOOLEAN_SAMPLE_COUNT)
        assert len(values) == BOOLEAN_SAMPLE_COUNT
        assert all(isinstance(v, bool) for v in values)

    def test_one_of_generator(self) -> None:
        """Test one_of generator."""
        gen = PropertyGenerator.one_of([1, 2, 3])
        values = gen.take(5)
        assert all(v in [1, 2, 3] for v in values)


class TestInvariant:
    """Test invariant functionality."""

    def test_invariant_validation(self) -> None:
        """Test invariant validation."""
        inv = Invariant("positive", lambda x: x > 0)
        assert inv.validate(42) is True
        assert inv.validate(-1) is False

    def test_invariant_validator(self) -> None:
        """Test invariant validator."""
        validator = InvariantValidator()
        validator.add("positive", lambda x: x > 0)
        validator.add("under_100", lambda x: x < MAX_THRESHOLD)

        assert validator.validate_all(SECONDARY_POSITIVE_VALUE) is True
        assert validator.validate_all(150) is False
        assert validator.violation_count() == 1

    def test_no_violations(self) -> None:
        """Test assert no violations."""
        validator = InvariantValidator()
        validator.add("true", lambda _: True)
        validator.validate_all(None)
        validator.assert_no_violations()  # Should not raise


class TestGuard:
    """Test guard types."""

    def test_guard_success(self) -> None:
        """Test guard with valid value."""
        guard = Guard.validated(POSITIVE_VALUE, lambda x: x > 0)
        assert guard.get() == POSITIVE_VALUE

    def test_guard_failure(self) -> None:
        """Test guard with invalid value."""
        with pytest.raises(ValueError, match="failed validation"):
            Guard.validated(NEGATIVE_VALUE, lambda x: x > 0)

    def test_guard_map(self) -> None:
        """Test guard transformation."""
        guard = Guard.validated(POSITIVE_VALUE, lambda x: x > 0)
        result = guard.map(lambda x: x * DOUBLE_FACTOR)
        assert result == POSITIVE_VALUE * DOUBLE_FACTOR


class TestValidatedValue:
    """Test validated value wrapper."""

    def test_valid_value(self) -> None:
        """Test valid value."""
        val = ValidatedValue(POSITIVE_VALUE, [("positive", lambda x: x > 0)])
        assert val.is_valid() is True
        assert val.get() == POSITIVE_VALUE

    def test_invalid_value(self) -> None:
        """Test invalid value."""
        val = ValidatedValue(NEGATIVE_VALUE, [("positive", lambda x: x > 0)])
        assert val.is_valid() is False
        with pytest.raises(ValueError, match="failed validators"):
            val.get()

    def test_multiple_validators(self) -> None:
        """Test multiple validators."""
        val = ValidatedValue(
            SECONDARY_POSITIVE_VALUE,
            [("positive", lambda x: x > 0), ("under_100", lambda x: x < MAX_THRESHOLD)],
        )
        assert val.is_valid() is True

    def test_get_or(self) -> None:
        """Test get_or with default."""
        val = ValidatedValue(NEGATIVE_VALUE, [("positive", lambda x: x > 0)])
        assert val.get_or(DEFAULT_VALUE) == DEFAULT_VALUE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
