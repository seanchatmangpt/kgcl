"""Tests for validation module."""

import pytest
from src.validation import (
    Property, PropertyTest, PropertyGenerator,
    Invariant, InvariantValidator,
    Guard, ValidatedValue
)


class TestProperty:
    """Test property-based testing."""

    def test_property_builder(self):
        """Test property builder."""
        test = (Property()
            .name("test_add")
            .predicate(lambda a, b: a + b == b + a)
            .example(1, 2)
            .example(3, 4)
            .build())
        
        assert test.name == "test_add"
        assert len(test.examples) == 2

    def test_property_test_run(self):
        """Test running property test."""
        test = PropertyTest(
            "commutative",
            lambda a, b: a + b == b + a,
            examples=[(1, 2), (3, 4), (5, 6)]
        )
        
        assert test.run() is True
        assert test.failure_count() == 0

    def test_property_test_failure(self):
        """Test property test with failures."""
        test = PropertyTest(
            "always_true",
            lambda x: False,
            examples=[(1,), (2,), (3,)]
        )
        
        assert test.run() is False
        assert test.failure_count() == 3


class TestPropertyGenerator:
    """Test property generators."""

    def test_integer_generator(self):
        """Test integer generator."""
        gen = PropertyGenerator.integers(min=0, max=100)
        values = gen.take(10)
        assert len(values) == 10
        assert all(0 <= v <= 100 for v in values)

    def test_boolean_generator(self):
        """Test boolean generator."""
        gen = PropertyGenerator.booleans()
        values = gen.take(5)
        assert len(values) == 5
        assert all(isinstance(v, bool) for v in values)

    def test_one_of_generator(self):
        """Test one_of generator."""
        gen = PropertyGenerator.one_of([1, 2, 3])
        values = gen.take(5)
        assert all(v in [1, 2, 3] for v in values)


class TestInvariant:
    """Test invariant functionality."""

    def test_invariant_validation(self):
        """Test invariant validation."""
        inv = Invariant(
            "positive",
            lambda x: x > 0
        )
        assert inv.validate(42) is True
        assert inv.validate(-1) is False

    def test_invariant_validator(self):
        """Test invariant validator."""
        validator = InvariantValidator()
        validator.add("positive", lambda x: x > 0)
        validator.add("under_100", lambda x: x < 100)
        
        assert validator.validate_all(50) is True
        assert validator.validate_all(150) is False
        assert validator.failure_count() == 1

    def test_no_violations(self):
        """Test assert no violations."""
        validator = InvariantValidator()
        validator.add("true", lambda x: True)
        validator.validate_all(None)
        validator.assert_no_violations()  # Should not raise


class TestGuard:
    """Test guard types."""

    def test_guard_success(self):
        """Test guard with valid value."""
        guard = Guard.validated(42, lambda x: x > 0)
        assert guard.get() == 42

    def test_guard_failure(self):
        """Test guard with invalid value."""
        with pytest.raises(ValueError):
            Guard.validated(-1, lambda x: x > 0)

    def test_guard_map(self):
        """Test guard transformation."""
        guard = Guard.validated(42, lambda x: x > 0)
        result = guard.map(lambda x: x * 2)
        assert result == 84


class TestValidatedValue:
    """Test validated value wrapper."""

    def test_valid_value(self):
        """Test valid value."""
        val = ValidatedValue(
            42,
            [("positive", lambda x: x > 0)]
        )
        assert val.is_valid() is True
        assert val.get() == 42

    def test_invalid_value(self):
        """Test invalid value."""
        val = ValidatedValue(
            -1,
            [("positive", lambda x: x > 0)]
        )
        assert val.is_valid() is False
        with pytest.raises(ValueError):
            val.get()

    def test_multiple_validators(self):
        """Test multiple validators."""
        val = ValidatedValue(
            50,
            [
                ("positive", lambda x: x > 0),
                ("under_100", lambda x: x < 100),
            ]
        )
        assert val.is_valid() is True

    def test_get_or(self):
        """Test get_or with default."""
        val = ValidatedValue(-1, [("positive", lambda x: x > 0)])
        assert val.get_or(0) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
