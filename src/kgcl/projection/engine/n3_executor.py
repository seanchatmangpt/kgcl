"""N3 rule executor - Subprocess-based N3 reasoning with resource limits.

This module provides the N3Executor which runs EYE reasoner subprocess
with configurable timeouts and memory limits for projection pipelines.

Examples
--------
>>> from kgcl.projection.engine.n3_executor import N3Executor, N3ExecutorConfig
>>> config = N3ExecutorConfig(timeout_seconds=10.0, max_memory_mb=256)
>>> executor = N3Executor(config)
>>> result = executor.execute(rules_path="rules.n3", state_ttl="@prefix : <#> . :a :b :c .")
>>> result.success
True
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from typing import Any

from kgcl.projection.domain.descriptors import N3RuleDescriptor
from kgcl.projection.domain.exceptions import N3ReasoningError

__all__ = ["N3ExecutorConfig", "N3ExecutionResult", "N3Executor"]


@dataclass(frozen=True)
class N3ExecutorConfig:
    """Configuration for N3 executor.

    Parameters
    ----------
    eye_path : str
        Path to EYE executable (default: "eye")
    timeout_seconds : float
        Maximum execution time in seconds
    max_memory_mb : int | None
        Maximum memory in MB (None = no limit, uses ulimit on Unix)

    Examples
    --------
    >>> config = N3ExecutorConfig(timeout_seconds=30.0, max_memory_mb=512)
    >>> config.timeout_seconds
    30.0
    """

    eye_path: str = "eye"
    timeout_seconds: float = 30.0
    max_memory_mb: int | None = None


@dataclass
class N3ExecutionResult:
    """Result from N3 rule execution.

    Parameters
    ----------
    success : bool
        Whether execution succeeded
    output : str
        N3 output if successful
    error : str | None
        Error message if failed
    duration_ms : float
        Execution time in milliseconds
    rule_name : str
        Name of the rule set that was executed

    Examples
    --------
    >>> result = N3ExecutionResult(success=True, output="...", duration_ms=15.0, rule_name="validation")
    >>> result.success
    True
    """

    success: bool
    output: str
    error: str | None = None
    duration_ms: float = 0.0
    rule_name: str = ""


class N3Executor:
    """Execute N3 rules using EYE reasoner subprocess.

    Provides subprocess-based N3 reasoning with timeout and memory limits
    for integration into projection pipelines.

    Parameters
    ----------
    config : N3ExecutorConfig | None
        Executor configuration

    Examples
    --------
    >>> executor = N3Executor()
    >>> result = executor.execute_rule(rule_descriptor, state_ttl)
    >>> if result.success:
    ...     print(result.output)
    """

    def __init__(self, config: N3ExecutorConfig | None = None) -> None:
        """Initialize N3 executor.

        Parameters
        ----------
        config : N3ExecutorConfig | None
            Configuration options (uses defaults if None)
        """
        self.config = config or N3ExecutorConfig()
        self._eye_available: bool | None = None

    def is_available(self) -> bool:
        """Check if EYE reasoner is available.

        Returns
        -------
        bool
            True if EYE is found in PATH

        Examples
        --------
        >>> executor = N3Executor()
        >>> executor.is_available()  # depends on system
        """
        if self._eye_available is None:
            self._eye_available = which(self.config.eye_path) is not None
        return self._eye_available

    def execute_rule(self, rule: N3RuleDescriptor, state_ttl: str, base_path: Path | None = None) -> N3ExecutionResult:
        """Execute N3 rule against state.

        Parameters
        ----------
        rule : N3RuleDescriptor
            Rule descriptor with file path and role
        state_ttl : str
            RDF/Turtle state to reason over
        base_path : Path | None
            Base path for resolving relative rule file paths

        Returns
        -------
        N3ExecutionResult
            Execution result with output or error

        Raises
        ------
        N3ReasoningError
            If EYE is not available or rule file not found

        Examples
        --------
        >>> from kgcl.projection.domain.descriptors import N3RuleDescriptor, N3Role
        >>> rule = N3RuleDescriptor(name="test", file_path="rules.n3", role=N3Role.INFERENCE)
        >>> executor = N3Executor()
        >>> result = executor.execute_rule(rule, "@prefix : <#> . :a :b :c .")
        """
        if not self.is_available():
            raise N3ReasoningError(rule.name, f"EYE reasoner not found at '{self.config.eye_path}'")

        # Resolve rule file path
        if base_path is not None:
            rules_path = base_path / rule.file_path
        else:
            rules_path = Path(rule.file_path)

        if not rules_path.exists():
            raise N3ReasoningError(rule.name, f"Rule file not found: {rules_path}")

        return self._execute(rule_name=rule.name, rules_path=rules_path, state_ttl=state_ttl)

    def execute(self, rules_path: str | Path, state_ttl: str, rule_name: str = "unnamed") -> N3ExecutionResult:
        """Execute N3 rules from file against state.

        Parameters
        ----------
        rules_path : str | Path
            Path to N3 rules file
        state_ttl : str
            RDF/Turtle state to reason over
        rule_name : str
            Name for error reporting

        Returns
        -------
        N3ExecutionResult
            Execution result

        Raises
        ------
        N3ReasoningError
            If EYE is not available

        Examples
        --------
        >>> executor = N3Executor()
        >>> result = executor.execute("rules.n3", "@prefix : <#> . :a :b :c .")
        """
        if not self.is_available():
            raise N3ReasoningError(rule_name, f"EYE reasoner not found at '{self.config.eye_path}'")

        return self._execute(rule_name=rule_name, rules_path=Path(rules_path), state_ttl=state_ttl)

    def _execute(self, rule_name: str, rules_path: Path, state_ttl: str) -> N3ExecutionResult:
        """Execute EYE subprocess with resource limits.

        Parameters
        ----------
        rule_name : str
            Name for the rule set
        rules_path : Path
            Path to N3 rules file
        state_ttl : str
            RDF/Turtle state

        Returns
        -------
        N3ExecutionResult
            Execution result
        """
        start = time.perf_counter()

        # Write state to temp file
        state_fd, state_path = tempfile.mkstemp(suffix=".ttl", text=True)
        try:
            with os.fdopen(state_fd, "w") as f:
                f.write(state_ttl)

            # Build EYE command
            cmd = [self.config.eye_path, "--nope", "--pass", "--quiet", state_path, str(rules_path)]

            # Apply memory limit via preexec_fn on Unix
            preexec = self._get_preexec_fn() if self.config.max_memory_mb else None

            try:
                result = subprocess.run(
                    cmd,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout_seconds,
                    preexec_fn=preexec,
                )

                duration_ms = (time.perf_counter() - start) * 1000

                if result.returncode == 0:
                    return N3ExecutionResult(
                        success=True, output=result.stdout, duration_ms=duration_ms, rule_name=rule_name
                    )
                else:
                    return N3ExecutionResult(
                        success=False,
                        output="",
                        error=result.stderr or f"Exit code {result.returncode}",
                        duration_ms=duration_ms,
                        rule_name=rule_name,
                    )

            except subprocess.TimeoutExpired:
                duration_ms = (time.perf_counter() - start) * 1000
                return N3ExecutionResult(
                    success=False,
                    output="",
                    error=f"Timeout after {self.config.timeout_seconds}s",
                    duration_ms=duration_ms,
                    rule_name=rule_name,
                )
            except OSError as e:
                duration_ms = (time.perf_counter() - start) * 1000
                return N3ExecutionResult(
                    success=False,
                    output="",
                    error=f"Subprocess error: {e}",
                    duration_ms=duration_ms,
                    rule_name=rule_name,
                )

        finally:
            if os.path.exists(state_path):
                os.unlink(state_path)

    def _get_preexec_fn(self) -> Any:
        """Get preexec_fn for memory limiting on Unix.

        Returns
        -------
        Callable | None
            Function to set resource limits, or None on Windows/macOS
        """
        if self.config.max_memory_mb is None:
            return None

        try:
            import resource
            import sys

            # RLIMIT_AS doesn't work reliably on macOS
            if sys.platform == "darwin":
                return None

            max_bytes = self.config.max_memory_mb * 1024 * 1024

            def set_limits() -> None:
                """Set memory limits before exec."""
                try:
                    resource.setrlimit(resource.RLIMIT_AS, (max_bytes, max_bytes))
                except (OSError, ValueError):
                    # Silently ignore if limits can't be set
                    pass

            return set_limits
        except ImportError:
            # resource module not available (Windows)
            return None
