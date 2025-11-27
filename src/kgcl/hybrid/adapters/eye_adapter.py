"""EYEAdapter - Wraps EYEReasoner to implement Reasoner protocol.

This adapter provides the Reasoner interface using the EYE N3 reasoner.
It wraps the existing EYEReasoner class from eye_reasoner.py.

Examples
--------
>>> adapter = EYEAdapter()
>>> adapter.is_available()  # True if EYE is installed
True or False
"""

from __future__ import annotations

import logging
import os
import tempfile

from kgcl.hybrid.eye_reasoner import EYENotFoundError, EYEReasoner, EYEReasonerConfig
from kgcl.hybrid.ports.reasoner_port import ReasoningOutput

logger = logging.getLogger(__name__)


class EYEAdapter:
    """Adapter wrapping EYEReasoner to implement Reasoner protocol.

    This adapter provides a clean interface to the EYE N3 reasoner,
    implementing the Reasoner protocol for use by the hybrid engine.

    Parameters
    ----------
    config : EYEReasonerConfig | None, optional
        Configuration for the EYE reasoner. If None, uses defaults.
    skip_availability_check : bool, optional
        If True, skip checking if EYE is available during init.
        Useful for testing without EYE installed.

    Attributes
    ----------
    config : EYEReasonerConfig
        The reasoner configuration.

    Examples
    --------
    Create adapter with default config:

    >>> adapter = EYEAdapter(skip_availability_check=True)
    >>> adapter.config.timeout_seconds
    30

    Create adapter with custom timeout:

    >>> config = EYEReasonerConfig(timeout_seconds=60)
    >>> adapter = EYEAdapter(config=config, skip_availability_check=True)
    >>> adapter.config.timeout_seconds
    60
    """

    def __init__(self, config: EYEReasonerConfig | None = None, skip_availability_check: bool = False) -> None:
        """Initialize EYEAdapter.

        Parameters
        ----------
        config : EYEReasonerConfig | None, optional
            Configuration for EYE reasoner. If None, uses defaults.
        skip_availability_check : bool, optional
            If True, skip EYE availability check.
        """
        self.config = config or EYEReasonerConfig()
        self._reasoner: EYEReasoner | None = None
        self._available: bool | None = None

        if not skip_availability_check:
            try:
                self._reasoner = EYEReasoner(self.config)
                self._available = True
                logger.info("EYEAdapter initialized with available reasoner")
            except EYENotFoundError:
                self._available = False
                logger.warning("EYE reasoner not available")

    def is_available(self) -> bool:
        """Check if EYE reasoner is available.

        Returns
        -------
        bool
            True if EYE is installed and accessible.

        Examples
        --------
        >>> adapter = EYEAdapter(skip_availability_check=True)
        >>> # Result depends on EYE installation
        >>> isinstance(adapter.is_available(), bool)
        True
        """
        if self._available is None:
            try:
                self._reasoner = EYEReasoner(self.config)
                self._available = True
            except EYENotFoundError:
                self._available = False
        return self._available

    def reason(self, state: str, rules: str) -> ReasoningOutput:
        """Apply rules to state and return deductive closure.

        Writes state and rules to temporary files, invokes EYE reasoner,
        and returns the deductive closure.

        Parameters
        ----------
        state : str
            Current RDF state in Turtle/TriG format.
        rules : str
            N3 physics rules to apply.

        Returns
        -------
        ReasoningOutput
            Result containing success status, output, and metrics.

        Examples
        --------
        >>> adapter = EYEAdapter()
        >>> if adapter.is_available():
        ...     result = adapter.reason(
        ...         "@prefix ex: <http://example.org/> . ex:a ex:b ex:c .",
        ...         "{ ?x ex:b ?y } => { ?x ex:processed true } .",
        ...     )
        ...     result.success
        True
        """
        if not self.is_available():
            return ReasoningOutput(success=False, output="", error="EYE reasoner not available", duration_ms=0.0)

        # Write state and rules to temp files
        state_fd, state_path = tempfile.mkstemp(suffix=".ttl", text=True)
        rules_fd, rules_path = tempfile.mkstemp(suffix=".n3", text=True)

        try:
            with os.fdopen(state_fd, "w") as f:
                f.write(state)
            with os.fdopen(rules_fd, "w") as f:
                f.write(rules)

            # Invoke EYE reasoner
            if self._reasoner is None:
                self._reasoner = EYEReasoner(self.config)

            result = self._reasoner.reason(state_path, rules_path)

            # Convert to ReasoningOutput
            return ReasoningOutput(
                success=result.success, output=result.output, error=result.error, duration_ms=result.duration_ms
            )

        finally:
            # Clean up temp files
            if os.path.exists(state_path):
                os.unlink(state_path)
            if os.path.exists(rules_path):
                os.unlink(rules_path)

    def reason_with_files(self, state_path: str, rules_path: str) -> ReasoningOutput:
        """Apply rules to state using file paths directly.

        This method is more efficient when state/rules are already on disk,
        avoiding redundant file writes.

        Parameters
        ----------
        state_path : str
            Path to file containing RDF state.
        rules_path : str
            Path to file containing N3 rules.

        Returns
        -------
        ReasoningOutput
            Result containing success status, output, and metrics.
        """
        if not self.is_available():
            return ReasoningOutput(success=False, output="", error="EYE reasoner not available", duration_ms=0.0)

        if self._reasoner is None:
            self._reasoner = EYEReasoner(self.config)

        result = self._reasoner.reason(state_path, rules_path)

        return ReasoningOutput(
            success=result.success, output=result.output, error=result.error, duration_ms=result.duration_ms
        )
