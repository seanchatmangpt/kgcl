"""EYE reasoner subprocess integration for KGCL hybrid reasoning.

This module provides a Python interface to the EYE (Euler Yet another proof Engine)
N3 reasoner, enabling rule-based deductive reasoning over RDF/N3 state.
"""

import subprocess
import time
from dataclasses import dataclass
from shutil import which


# Custom exceptions
class EYENotFoundError(Exception):
    """Raised when EYE reasoner executable is not found in PATH."""

    pass


class EYETimeoutError(Exception):
    """Raised when EYE reasoning operation exceeds timeout."""

    pass


class EYEReasoningError(Exception):
    """Raised when EYE reasoning fails with an error."""

    pass


@dataclass(frozen=True)
class EYEReasonerConfig:
    """Configuration for EYE reasoner subprocess execution.

    Parameters
    ----------
    eye_path : str
        Path or command name for EYE executable (default: "eye")
    timeout_seconds : int
        Maximum execution time before timeout (default: 30)
    nope : bool
        Disable proof trace output (default: True)
    pass_all : bool
        Output deductive closure/pass-all reasoning (default: True)
    """

    eye_path: str = "eye"
    timeout_seconds: int = 30
    nope: bool = True
    pass_all: bool = True


@dataclass(frozen=True)
class ReasoningResult:
    """Result of EYE reasoning execution.

    Parameters
    ----------
    success : bool
        Whether reasoning completed successfully
    output : str
        N3 output from EYE if successful, empty otherwise
    error : str | None
        Error message if reasoning failed, None otherwise
    duration_ms : float
        Execution duration in milliseconds
    command : str
        Full command executed for debugging
    """

    success: bool
    output: str
    error: str | None
    duration_ms: float
    command: str


class EYEReasoner:
    """Interface to EYE N3 reasoner subprocess.

    Provides methods to execute EYE reasoning over N3 state and rules files,
    with configurable timeout and output options.

    Parameters
    ----------
    config : EYEReasonerConfig | None
        Configuration for reasoner execution. If None, uses defaults.

    Raises
    ------
    EYENotFoundError
        If EYE executable is not found at initialization

    Examples
    --------
    >>> config = EYEReasonerConfig(timeout_seconds=60)
    >>> reasoner = EYEReasoner(config)
    >>> result = reasoner.reason("state.n3", "rules.n3")
    >>> if result.success:
    ...     print(result.output)
    """

    def __init__(self, config: EYEReasonerConfig | None = None) -> None:
        """Initialize EYE reasoner with configuration.

        Parameters
        ----------
        config : EYEReasonerConfig | None
            Configuration for reasoner execution. If None, uses defaults.

        Raises
        ------
        EYENotFoundError
            If EYE executable is not found
        """
        self.config = config or EYEReasonerConfig()
        if not self.is_available():
            msg = f"EYE reasoner not found at '{self.config.eye_path}'. Install from https://github.com/eyereasoner/eye"
            raise EYENotFoundError(msg)

    def is_available(self) -> bool:
        """Check if EYE reasoner executable is available.

        Returns
        -------
        bool
            True if EYE executable is found in PATH or at configured path

        Examples
        --------
        >>> reasoner = EYEReasoner()
        >>> if reasoner.is_available():
        ...     print("EYE is installed")
        """
        return which(self.config.eye_path) is not None

    def _build_command(self, state_path: str, rules_path: str) -> list[str]:
        """Build EYE command line arguments.

        Parameters
        ----------
        state_path : str
            Path to N3 file containing current state
        rules_path : str
            Path to N3 file containing reasoning rules

        Returns
        -------
        list[str]
            Command arguments for subprocess execution

        Examples
        --------
        >>> reasoner = EYEReasoner()
        >>> cmd = reasoner._build_command("state.n3", "rules.n3")
        >>> print(" ".join(cmd))
        eye --nope --pass state.n3 rules.n3
        """
        cmd = [self.config.eye_path]

        if self.config.nope:
            cmd.append("--nope")

        if self.config.pass_all:
            cmd.append("--pass")

        cmd.extend([state_path, rules_path])

        return cmd

    def reason(self, state_path: str, rules_path: str) -> ReasoningResult:
        """Execute EYE reasoning over state and rules.

        Runs EYE reasoner as subprocess with configured timeout and options.
        Returns detailed result including output, errors, and timing.

        Parameters
        ----------
        state_path : str
            Path to N3 file containing current state
        rules_path : str
            Path to N3 file containing reasoning rules

        Returns
        -------
        ReasoningResult
            Detailed result of reasoning execution

        Raises
        ------
        EYETimeoutError
            If reasoning exceeds configured timeout
        EYENotFoundError
            If EYE executable becomes unavailable

        Examples
        --------
        >>> reasoner = EYEReasoner()
        >>> result = reasoner.reason("state.n3", "rules.n3")
        >>> if result.success:
        ...     print(f"Reasoning completed in {result.duration_ms:.2f}ms")
        ...     print(result.output)
        ... else:
        ...     print(f"Error: {result.error}")
        """
        cmd = self._build_command(state_path, rules_path)
        cmd_str = " ".join(cmd)

        start = time.perf_counter()
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.config.timeout_seconds, check=True
            )
            duration = (time.perf_counter() - start) * 1000
            return ReasoningResult(
                success=True, output=result.stdout, error=None, duration_ms=duration, command=cmd_str
            )
        except subprocess.TimeoutExpired:
            duration = (time.perf_counter() - start) * 1000
            msg = f"EYE reasoning timed out after {self.config.timeout_seconds}s"
            # Return failed result instead of raising to allow caller to handle
            return ReasoningResult(success=False, output="", error=msg, duration_ms=duration, command=cmd_str)
        except subprocess.CalledProcessError as e:
            duration = (time.perf_counter() - start) * 1000
            return ReasoningResult(
                success=False,
                output="",
                error=e.stderr if e.stderr else f"EYE process exited with code {e.returncode}",
                duration_ms=duration,
                command=cmd_str,
            )
        except FileNotFoundError as e:
            # Handle case where EYE executable disappears during execution
            raise EYENotFoundError(f"EYE executable not found: {e}") from e
