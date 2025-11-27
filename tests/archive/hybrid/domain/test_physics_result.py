"""Tests for PhysicsResult domain object.

Tests verify the immutable value object behavior and convergence property.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.domain.physics_result import PhysicsResult


class TestPhysicsResultCreation:
    """Tests for PhysicsResult creation and attributes."""

    def test_create_with_positive_delta(self) -> None:
        """PhysicsResult stores tick metrics correctly."""
        result = PhysicsResult(tick_number=1, duration_ms=12.5, triples_before=100, triples_after=105, delta=5)

        assert result.tick_number == 1
        assert result.duration_ms == 12.5
        assert result.triples_before == 100
        assert result.triples_after == 105
        assert result.delta == 5

    def test_create_with_zero_delta(self) -> None:
        """PhysicsResult handles convergence case (delta=0)."""
        result = PhysicsResult(tick_number=3, duration_ms=8.2, triples_before=150, triples_after=150, delta=0)

        assert result.tick_number == 3
        assert result.delta == 0


class TestPhysicsResultConverged:
    """Tests for the converged property."""

    def test_converged_when_delta_zero(self) -> None:
        """converged returns True when delta is zero."""
        result = PhysicsResult(tick_number=3, duration_ms=8.0, triples_before=150, triples_after=150, delta=0)

        assert result.converged is True

    def test_not_converged_when_delta_positive(self) -> None:
        """converged returns False when delta is positive."""
        result = PhysicsResult(tick_number=1, duration_ms=10.0, triples_before=100, triples_after=105, delta=5)

        assert result.converged is False

    def test_not_converged_when_delta_negative(self) -> None:
        """converged returns False when delta is negative (edge case)."""
        result = PhysicsResult(tick_number=1, duration_ms=10.0, triples_before=100, triples_after=95, delta=-5)

        assert result.converged is False


class TestPhysicsResultImmutability:
    """Tests for frozen dataclass immutability."""

    def test_cannot_modify_delta(self) -> None:
        """Frozen dataclass prevents modification."""
        result = PhysicsResult(1, 10.0, 100, 105, 5)

        with pytest.raises(AttributeError):
            result.delta = 10  # type: ignore[misc]

    def test_cannot_modify_tick_number(self) -> None:
        """Frozen dataclass prevents tick_number modification."""
        result = PhysicsResult(1, 10.0, 100, 105, 5)

        with pytest.raises(AttributeError):
            result.tick_number = 2  # type: ignore[misc]


class TestPhysicsResultRepr:
    """Tests for string representation."""

    def test_repr_shows_key_metrics(self) -> None:
        """repr includes tick, delta, converged, duration."""
        result = PhysicsResult(1, 10.5, 100, 105, 5)

        repr_str = repr(result)

        assert "tick=1" in repr_str
        assert "delta=5" in repr_str
        assert "converged=False" in repr_str
        assert "10.50ms" in repr_str

    def test_repr_shows_converged_true(self) -> None:
        """repr shows converged=True when delta is zero."""
        result = PhysicsResult(3, 8.0, 150, 150, 0)

        repr_str = repr(result)

        assert "converged=True" in repr_str
