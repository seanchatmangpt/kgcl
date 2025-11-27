"""Tests for EYEAdapter.

Tests verify Reasoner protocol implementation wrapping EYE subprocess.
Note: These tests require EYE to be installed for full functionality.
"""

from __future__ import annotations

import pytest

from kgcl.hybrid.adapters.eye_adapter import EYEAdapter
from kgcl.hybrid.eye_reasoner import EYEReasonerConfig
from kgcl.hybrid.ports.reasoner_port import ReasoningOutput


class TestEYEAdapterCreation:
    """Tests for adapter initialization."""

    def test_create_with_skip_check(self) -> None:
        """Create adapter without availability check."""
        adapter = EYEAdapter(skip_availability_check=True)
        assert adapter.config.timeout_seconds == 30

    def test_create_with_custom_config(self) -> None:
        """Create adapter with custom configuration."""
        config = EYEReasonerConfig(timeout_seconds=60)
        adapter = EYEAdapter(config=config, skip_availability_check=True)

        assert adapter.config.timeout_seconds == 60


class TestEYEAdapterAvailability:
    """Tests for availability checking."""

    def test_is_available_returns_bool(self) -> None:
        """is_available returns boolean."""
        adapter = EYEAdapter(skip_availability_check=True)
        result = adapter.is_available()

        assert isinstance(result, bool)


class TestEYEAdapterReason:
    """Tests for reasoning execution."""

    @pytest.fixture
    def eye_adapter(self) -> EYEAdapter:
        """Create EYE adapter for testing."""
        return EYEAdapter()

    def test_reason_returns_reasoning_output(self, eye_adapter: EYEAdapter) -> None:
        """reason method returns ReasoningOutput."""
        if not eye_adapter.is_available():
            pytest.skip("EYE reasoner not installed")

        state = "@prefix ex: <http://example.org/> . ex:a ex:b ex:c ."
        rules = "{ ?x ex:b ?y } => { ?x ex:processed true } ."

        result = eye_adapter.reason(state, rules)

        assert isinstance(result, ReasoningOutput)

    def test_reason_unavailable_returns_error(self) -> None:
        """reason returns error when EYE unavailable."""
        # Force unavailable state
        adapter = EYEAdapter(skip_availability_check=True)
        adapter._available = False

        result = adapter.reason("state", "rules")

        assert result.success is False
        assert "not available" in (result.error or "")

    def test_reason_successful_has_output(self, eye_adapter: EYEAdapter) -> None:
        """Successful reasoning has output content."""
        if not eye_adapter.is_available():
            pytest.skip("EYE reasoner not installed")

        state = "@prefix ex: <http://example.org/> . ex:a ex:b ex:c ."
        rules = ""  # No rules, just pass through

        result = eye_adapter.reason(state, rules)

        if result.success:
            assert len(result.output) > 0


class TestEYEAdapterReasonWithFiles:
    """Tests for file-based reasoning."""

    @pytest.fixture
    def eye_adapter(self) -> EYEAdapter:
        """Create EYE adapter for testing."""
        return EYEAdapter()

    def test_reason_with_files_returns_output(self, eye_adapter: EYEAdapter, tmp_path: pytest.TempPathFactory) -> None:
        """reason_with_files works with file paths."""
        if not eye_adapter.is_available():
            pytest.skip("EYE reasoner not installed")

        # Create temp files using tmp_path
        import os
        import tempfile

        state_path = os.path.join(str(tmp_path), "state.ttl")  # type: ignore[arg-type]
        rules_path = os.path.join(str(tmp_path), "rules.n3")  # type: ignore[arg-type]

        with open(state_path, "w") as f:
            f.write("@prefix ex: <http://example.org/> . ex:a ex:b ex:c .")
        with open(rules_path, "w") as f:
            f.write("")  # Empty rules

        result = eye_adapter.reason_with_files(state_path, rules_path)

        assert isinstance(result, ReasoningOutput)
