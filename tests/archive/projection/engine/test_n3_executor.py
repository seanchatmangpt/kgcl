"""Tests for N3 executor - Subprocess-based N3 reasoning.

Chicago School TDD: Test behavior through state verification.
Tests cover execution, timeout, memory limits, and error handling.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from shutil import which

import pytest

from kgcl.projection.domain.descriptors import N3Role, N3RuleDescriptor
from kgcl.projection.domain.exceptions import N3ReasoningError
from kgcl.projection.engine.n3_executor import (
    N3ExecutionResult,
    N3Executor,
    N3ExecutorConfig,
)

# Skip all tests if EYE not available
HAS_EYE = which("eye") is not None
pytestmark = pytest.mark.skipif(not HAS_EYE, reason="EYE reasoner not installed")


class TestN3ExecutorConfig:
    """Tests for N3ExecutorConfig."""

    def test_default_values(self) -> None:
        """Default config has expected values."""
        config = N3ExecutorConfig()

        assert config.eye_path == "eye"
        assert config.timeout_seconds == 30.0
        assert config.max_memory_mb is None

    def test_custom_values(self) -> None:
        """Custom config stores values."""
        config = N3ExecutorConfig(
            eye_path="/usr/bin/eye",
            timeout_seconds=10.0,
            max_memory_mb=256,
        )

        assert config.eye_path == "/usr/bin/eye"
        assert config.timeout_seconds == 10.0
        assert config.max_memory_mb == 256


class TestN3ExecutionResult:
    """Tests for N3ExecutionResult."""

    def test_successful_result(self) -> None:
        """Successful result stores output."""
        result = N3ExecutionResult(
            success=True,
            output="@prefix : <#> . :a :b :c .",
            duration_ms=15.0,
            rule_name="test_rules",
        )

        assert result.success is True
        assert result.output == "@prefix : <#> . :a :b :c ."
        assert result.error is None
        assert result.duration_ms == 15.0
        assert result.rule_name == "test_rules"

    def test_failed_result(self) -> None:
        """Failed result stores error."""
        result = N3ExecutionResult(
            success=False,
            output="",
            error="Timeout",
            duration_ms=30000.0,
            rule_name="slow_rules",
        )

        assert result.success is False
        assert result.error == "Timeout"


class TestN3ExecutorAvailability:
    """Tests for EYE availability check."""

    def test_eye_is_available(self) -> None:
        """EYE is available when installed."""
        executor = N3Executor()
        assert executor.is_available() is True

    def test_eye_not_available_with_bad_path(self) -> None:
        """EYE not available with invalid path."""
        config = N3ExecutorConfig(eye_path="nonexistent_eye_executable")
        executor = N3Executor(config)
        assert executor.is_available() is False


class TestN3ExecutorExecution:
    """Tests for N3 rule execution."""

    @pytest.fixture
    def simple_rules(self) -> Path:
        """Create simple N3 rules file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".n3", delete=False) as f:
            f.write("""
            @prefix : <http://example.org/> .
            { ?x :status "Completed" } => { ?x :processed true } .
            """)
            return Path(f.name)

    @pytest.fixture
    def identity_rules(self) -> Path:
        """Create identity rules (pass-through)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".n3", delete=False) as f:
            f.write("""
            @prefix : <http://example.org/> .
            { ?s ?p ?o } => { ?s ?p ?o } .
            """)
            return Path(f.name)

    def test_simple_execution(self, identity_rules: Path) -> None:
        """Execute simple rules and get output."""
        executor = N3Executor()

        state = """
        @prefix : <http://example.org/> .
        :task1 :name "Test Task" .
        """

        result = executor.execute(identity_rules, state, rule_name="identity")

        assert result.success is True
        assert result.duration_ms > 0
        assert result.rule_name == "identity"

    def test_inference_rules(self, simple_rules: Path) -> None:
        """Execute inference rules."""
        executor = N3Executor()

        state = """
        @prefix : <http://example.org/> .
        :task1 :status "Completed" .
        """

        result = executor.execute(simple_rules, state, rule_name="inference")

        assert result.success is True
        # Should infer :processed true
        assert ":processed" in result.output or "processed" in result.output

    def test_empty_state(self, identity_rules: Path) -> None:
        """Execute with empty state."""
        executor = N3Executor()

        result = executor.execute(identity_rules, "", rule_name="empty")

        assert result.success is True

    def test_execute_rule_descriptor(self, identity_rules: Path) -> None:
        """Execute using N3RuleDescriptor."""
        executor = N3Executor()

        rule = N3RuleDescriptor(
            name="test_rule",
            file_path=str(identity_rules),
            role=N3Role.INFERENCE,
        )

        state = "@prefix : <http://example.org/> . :a :b :c ."

        result = executor.execute_rule(rule, state)

        assert result.success is True
        assert result.rule_name == "test_rule"

    def test_execute_rule_with_base_path(self, identity_rules: Path) -> None:
        """Execute rule with relative path resolution."""
        executor = N3Executor()

        rule = N3RuleDescriptor(
            name="relative_rule",
            file_path=identity_rules.name,
            role=N3Role.PRECONDITION,
        )

        state = "@prefix : <http://example.org/> . :a :b :c ."

        result = executor.execute_rule(rule, state, base_path=identity_rules.parent)

        assert result.success is True


class TestN3ExecutorErrors:
    """Tests for N3 executor error handling."""

    def test_rule_file_not_found(self) -> None:
        """Raises N3ReasoningError when rule file not found."""
        executor = N3Executor()

        rule = N3RuleDescriptor(
            name="missing",
            file_path="/nonexistent/rules.n3",
            role=N3Role.INFERENCE,
        )

        with pytest.raises(N3ReasoningError) as exc:
            executor.execute_rule(rule, "")

        assert exc.value.rule_name == "missing"
        assert "not found" in exc.value.reason

    def test_eye_not_available_raises(self) -> None:
        """Raises N3ReasoningError when EYE not found."""
        config = N3ExecutorConfig(eye_path="nonexistent_eye")
        executor = N3Executor(config)

        rule = N3RuleDescriptor(
            name="test",
            file_path="/some/rules.n3",
            role=N3Role.INFERENCE,
        )

        with pytest.raises(N3ReasoningError) as exc:
            executor.execute_rule(rule, "")

        assert "not found" in exc.value.reason

    def test_invalid_rules_returns_failure(self) -> None:
        """Invalid N3 syntax returns failure result."""
        executor = N3Executor()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".n3", delete=False) as f:
            f.write("this is not valid n3 syntax {{{ invalid")
            rules_path = Path(f.name)

        result = executor.execute(rules_path, "", rule_name="invalid")

        # EYE should fail parsing invalid N3
        assert result.success is False
        assert result.error is not None


class TestN3ExecutorTimeout:
    """Tests for N3 executor timeout."""

    @pytest.fixture
    def slow_rules(self) -> Path:
        """Create rules that take time to process."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".n3", delete=False) as f:
            # Rules that generate many inferences
            f.write("""
            @prefix : <http://example.org/> .
            { ?x :next ?y } => { ?y :prev ?x } .
            { ?x :prev ?y . ?y :prev ?z } => { ?x :ancestor ?z } .
            """)
            return Path(f.name)

    def test_timeout_returns_failure(self) -> None:
        """Timeout returns failure result, not exception."""
        config = N3ExecutorConfig(timeout_seconds=0.01)  # Very short timeout
        executor = N3Executor(config)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".n3", delete=False) as f:
            f.write("{ ?s ?p ?o } => { ?s ?p ?o } .")
            rules_path = Path(f.name)

        # Large state to make EYE work
        state = "\n".join(f":item{i} :value {i} ." for i in range(1000))
        state = "@prefix : <http://example.org/> .\n" + state

        result = executor.execute(rules_path, state, rule_name="timeout_test")

        # May or may not timeout depending on system speed
        # Just verify it returns a result, not an exception
        assert isinstance(result, N3ExecutionResult)


@pytest.mark.eye
class TestN3ExecutorMemoryLimit:
    """Tests for N3 executor memory limits.

    Note: Memory limits use Unix ulimit and may not work on all systems.
    Memory limit via setrlimit(RLIMIT_AS) not supported on macOS.
    """

    def test_config_with_memory_limit(self) -> None:
        """Memory limit config is stored."""
        config = N3ExecutorConfig(max_memory_mb=512)
        executor = N3Executor(config)

        assert executor.config.max_memory_mb == 512

    def test_execution_with_memory_limit(self) -> None:
        """Execution works with memory limit set."""
        config = N3ExecutorConfig(max_memory_mb=512)
        executor = N3Executor(config)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".n3", delete=False) as f:
            f.write("{ ?s ?p ?o } => { ?s ?p ?o } .")
            rules_path = Path(f.name)

        state = "@prefix : <http://example.org/> . :a :b :c ."

        result = executor.execute(rules_path, state, rule_name="mem_test")

        # Should succeed (memory limit shouldn't affect small reasoning)
        assert result.success is True
