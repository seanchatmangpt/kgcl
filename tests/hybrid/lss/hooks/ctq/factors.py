"""CTQ Factor Definitions for Knowledge Hooks.

This module defines the CTQ (Critical-to-Quality) factor data model and dimension
enumeration for the Knowledge Hooks system, aligned with Lean Six Sigma quality
standards.

Classes
-------
HookCTQDimension
    Enumeration of 5 CTQ dimensions for hook validation
HookCTQFactor
    Frozen dataclass representing a single CTQ validation factor for hooks

Examples
--------
>>> from tests.hybrid.lss.hooks.ctq.factors import HookCTQDimension, HookCTQFactor
>>> from kgcl.hybrid.knowledge_hooks import HookPhase
>>> factor = HookCTQFactor(
...     dimension=HookCTQDimension.CORRECTNESS,
...     hook_id="validate-person",
...     phase=HookPhase.ON_CHANGE,
...     description="Hook produces correct validation result",
... )
>>> factor.dimension_name
'Correctness'
>>> factor.is_valid()
True
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from kgcl.hybrid.knowledge_hooks import HookPhase


class HookCTQDimension(Enum):
    """CTQ Dimensions for Knowledge Hooks Quality Standards.

    Each dimension represents a critical quality factor for validating hook
    execution behavior, aligned with Lean Six Sigma principles.

    Attributes
    ----------
    CORRECTNESS : str
        Hook produces expected state changes (validation logic is correct)
    COMPLETENESS : str
        All hook phases are handled properly (no missing lifecycle coverage)
    CONSISTENCY : str
        Deterministic execution across multiple runs (same input = same output)
    PERFORMANCE : str
        Execution within SLA bounds (p99 < 100ms per UNRDF requirements)
    RELIABILITY : str
        Graceful handling of condition evaluation failures (no crashes)

    Examples
    --------
    >>> from tests.hybrid.lss.hooks.ctq.factors import HookCTQDimension
    >>> HookCTQDimension.CORRECTNESS.value
    'correctness'
    >>> HookCTQDimension.PERFORMANCE.name
    'PERFORMANCE'
    >>> len(list(HookCTQDimension))
    5
    >>> all(isinstance(d.value, str) for d in HookCTQDimension)
    True

    Notes
    -----
    These dimensions map to hook execution quality requirements:
    - Correctness → Validation logic produces correct results
    - Completeness → All phases (pre_tick, on_change, post_tick) handled
    - Consistency → Same SPARQL condition = same action across runs
    - Performance → Hook execution within p99 < 100ms SLA
    - Reliability → Graceful degradation when SPARQL queries fail
    """

    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"


@dataclass(frozen=True)
class HookCTQFactor:
    """Critical-to-Quality Factor for Knowledge Hook Validation.

    Represents a single testable quality factor for a Knowledge Hook execution.
    Immutable by design (frozen=True) to ensure factor definitions remain stable
    across test runs.

    Parameters
    ----------
    dimension : HookCTQDimension
        The CTQ dimension being validated
    hook_id : str
        Hook identifier (e.g., "validate-person", "enforce-required-fields")
    phase : HookPhase
        Lifecycle phase when hook executes
    description : str
        Human-readable description of the quality requirement

    Attributes
    ----------
    dimension : HookCTQDimension
        The CTQ dimension being validated
    hook_id : str
        Hook identifier
    phase : HookPhase
        Lifecycle phase when hook executes
    description : str
        Human-readable description of the quality requirement

    Examples
    --------
    >>> from tests.hybrid.lss.hooks.ctq.factors import HookCTQDimension, HookCTQFactor
    >>> from kgcl.hybrid.knowledge_hooks import HookPhase
    >>> factor = HookCTQFactor(
    ...     dimension=HookCTQDimension.CORRECTNESS,
    ...     hook_id="validate-person",
    ...     phase=HookPhase.ON_CHANGE,
    ...     description="Hook correctly validates Person entity requires name field",
    ... )
    >>> factor.dimension.value
    'correctness'
    >>> factor.hook_id
    'validate-person'
    >>> factor.dimension_name
    'Correctness'

    >>> # Test is_valid() with valid hook_id
    >>> factor.is_valid()
    True

    >>> # Test is_valid() with empty hook_id
    >>> invalid_factor = HookCTQFactor(
    ...     dimension=HookCTQDimension.PERFORMANCE, hook_id="", phase=HookPhase.PRE_TICK, description="Invalid hook"
    ... )
    >>> invalid_factor.is_valid()
    False

    >>> # Test __repr__
    >>> repr(factor)  # doctest: +ELLIPSIS
    "HookCTQFactor(dimension=<HookCTQDimension.CORRECTNESS: 'correctness'>, hook_id='validate-person', phase=<HookPhase.ON_CHANGE: 'on_change'>, description='Hook correctly validates...')"

    >>> # Test immutability (frozen=True)
    >>> try:
    ...     factor.hook_id = "other-hook"
    ... except AttributeError:
    ...     print("Immutable")
    Immutable

    Notes
    -----
    The frozen dataclass ensures HookCTQFactor instances are hashable and can be
    used in sets/dicts for deduplication and lookups across test suites.
    """

    dimension: HookCTQDimension
    hook_id: str
    phase: HookPhase
    description: str

    @property
    def dimension_name(self) -> str:
        """Get human-readable dimension name.

        Returns
        -------
        str
            Title-cased dimension name (e.g., "Correctness", "Performance")

        Examples
        --------
        >>> from tests.hybrid.lss.hooks.ctq.factors import HookCTQDimension, HookCTQFactor
        >>> from kgcl.hybrid.knowledge_hooks import HookPhase
        >>> factor = HookCTQFactor(
        ...     dimension=HookCTQDimension.RELIABILITY,
        ...     hook_id="graceful-failure",
        ...     phase=HookPhase.POST_TICK,
        ...     description="Handles SPARQL errors gracefully",
        ... )
        >>> factor.dimension_name
        'Reliability'

        >>> # Test all dimensions
        >>> dims = [
        ...     HookCTQDimension.CORRECTNESS,
        ...     HookCTQDimension.COMPLETENESS,
        ...     HookCTQDimension.CONSISTENCY,
        ...     HookCTQDimension.PERFORMANCE,
        ...     HookCTQDimension.RELIABILITY,
        ... ]
        >>> factors = [HookCTQFactor(d, "test-hook", HookPhase.ON_CHANGE, "test") for d in dims]
        >>> [f.dimension_name for f in factors]
        ['Correctness', 'Completeness', 'Consistency', 'Performance', 'Reliability']
        """
        return self.dimension.value.capitalize()

    def is_valid(self) -> bool:
        """Validate hook_id is non-empty and phase is valid HookPhase.

        Returns
        -------
        bool
            True if hook_id is non-empty string and phase is valid, False otherwise

        Examples
        --------
        >>> from tests.hybrid.lss.hooks.ctq.factors import HookCTQDimension, HookCTQFactor
        >>> from kgcl.hybrid.knowledge_hooks import HookPhase
        >>> valid = HookCTQFactor(HookCTQDimension.CORRECTNESS, "validate-person", HookPhase.ON_CHANGE, "Valid hook")
        >>> valid.is_valid()
        True

        >>> # Test all valid phases
        >>> phases = [
        ...     HookPhase.PRE_TICK,
        ...     HookPhase.ON_CHANGE,
        ...     HookPhase.POST_TICK,
        ...     HookPhase.PRE_VALIDATION,
        ...     HookPhase.POST_VALIDATION,
        ... ]
        >>> factors = [HookCTQFactor(HookCTQDimension.CORRECTNESS, "hook", phase, "test") for phase in phases]
        >>> all(f.is_valid() for f in factors)
        True

        >>> # Test invalid: empty hook_id
        >>> invalid_empty = HookCTQFactor(HookCTQDimension.CORRECTNESS, "", HookPhase.ON_CHANGE, "Empty hook_id")
        >>> invalid_empty.is_valid()
        False

        >>> # Test invalid: whitespace-only hook_id
        >>> invalid_whitespace = HookCTQFactor(
        ...     HookCTQDimension.CORRECTNESS, "   ", HookPhase.ON_CHANGE, "Whitespace hook_id"
        ... )
        >>> invalid_whitespace.is_valid()
        False
        """
        # Check hook_id is non-empty after stripping whitespace
        if not self.hook_id or not self.hook_id.strip():
            return False

        # Check phase is a valid HookPhase enum member
        if not isinstance(self.phase, HookPhase):
            return False

        return True
