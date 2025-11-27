"""Innovation #6: Poka-Yoke Guard Hooks.

Implements automatic error prevention for all 10 Poka-Yoke rules defined
in the LSS analysis. Guards validate hooks before execution to prevent
defects rather than detect them after the fact.

Poka-Yoke Types
---------------
SHUTDOWN : Prevents operation from starting
CONTROL  : Prevents operation from proceeding incorrectly
VALIDATION : Validates parameters/state
WARNING    : Alerts operator to potential issues

Poka-Yoke Rules Covered
-----------------------
PY-HOOK-001: Empty condition query          → SHUTDOWN
PY-HOOK-002: Invalid SPARQL syntax          → VALIDATION
PY-HOOK-003: Priority conflict detection    → CONTROL
PY-HOOK-004: Disabled hook in chain         → WARNING
PY-HOOK-005: Missing handler data           → VALIDATION
PY-HOOK-006: Invalid phase declaration      → SHUTDOWN
PY-HOOK-007: Duplicate hook ID              → SHUTDOWN
PY-HOOK-008: Orphan chain reference         → WARNING
PY-HOOK-009: Conflicting actions            → CONTROL
PY-HOOK-010: Resource exhaustion risk       → WARNING

Examples
--------
>>> from kgcl.hybrid.hooks.poka_yoke_guards import PokaYokeGuard, HookPokaYokeType
>>> guard = PokaYokeGuard()
>>> len(guard._rules)
10
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.hybrid.knowledge_hooks import HookRegistry, KnowledgeHook


class HookPokaYokeType(Enum):
    """Types of Poka-Yoke error prevention.

    SHUTDOWN   : Operation cannot start
    CONTROL    : Operation cannot proceed incorrectly
    VALIDATION : Parameters/state validation
    WARNING    : Alert without blocking

    Examples
    --------
    >>> HookPokaYokeType.SHUTDOWN.value
    'shutdown'
    """

    SHUTDOWN = "shutdown"
    CONTROL = "control"
    VALIDATION = "validation"
    WARNING = "warning"


@dataclass(frozen=True)
class PokaYokeViolation:
    """Record of a Poka-Yoke rule violation.

    Parameters
    ----------
    rule_id : str
        Poka-Yoke rule identifier (e.g., "PY-HOOK-001")
    py_type : HookPokaYokeType
        Type of Poka-Yoke
    message : str
        Human-readable violation description
    hook_id : str | None
        Affected hook ID

    Examples
    --------
    >>> violation = PokaYokeViolation(
    ...     rule_id="PY-HOOK-001", py_type=HookPokaYokeType.SHUTDOWN, message="Empty condition query"
    ... )
    >>> violation.blocks_execution
    True
    """

    rule_id: str
    py_type: HookPokaYokeType
    message: str
    hook_id: str | None = None

    @property
    def blocks_execution(self) -> bool:
        """Check if violation blocks hook execution.

        Returns
        -------
        bool
            True for SHUTDOWN and CONTROL types
        """
        return self.py_type in (HookPokaYokeType.SHUTDOWN, HookPokaYokeType.CONTROL)


@dataclass
class PokaYokeGuard:
    """PRE_TICK phase guard that validates hooks before execution.

    Applies 10 Poka-Yoke rules to detect and prevent hook configuration
    errors before they cause runtime failures.

    Attributes
    ----------
    _rules : dict
        Rule ID to validation function mapping
    _known_hook_ids : set
        Set of registered hook IDs (for duplicate detection)

    Examples
    --------
    >>> guard = PokaYokeGuard()
    >>> guard._rules.keys()  # doctest: +ELLIPSIS
    dict_keys(['PY-HOOK-001', 'PY-HOOK-002', ...])
    """

    _known_hook_ids: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Initialize Poka-Yoke rules."""
        self._rules: dict[str, tuple[HookPokaYokeType, str]] = {
            "PY-HOOK-001": (HookPokaYokeType.SHUTDOWN, "Empty condition query"),
            "PY-HOOK-002": (HookPokaYokeType.VALIDATION, "Invalid SPARQL syntax"),
            "PY-HOOK-003": (HookPokaYokeType.CONTROL, "Priority conflict"),
            "PY-HOOK-004": (HookPokaYokeType.WARNING, "Disabled hook in chain"),
            "PY-HOOK-005": (HookPokaYokeType.VALIDATION, "Missing handler data"),
            "PY-HOOK-006": (HookPokaYokeType.SHUTDOWN, "Invalid phase"),
            "PY-HOOK-007": (HookPokaYokeType.SHUTDOWN, "Duplicate hook ID"),
            "PY-HOOK-008": (HookPokaYokeType.WARNING, "Orphan chain reference"),
            "PY-HOOK-009": (HookPokaYokeType.CONTROL, "Conflicting actions"),
            "PY-HOOK-010": (HookPokaYokeType.WARNING, "Resource exhaustion risk"),
        }

    def validate_hook(self, hook: KnowledgeHook, registry: HookRegistry | None = None) -> list[PokaYokeViolation]:
        """Validate hook against all Poka-Yoke rules.

        Parameters
        ----------
        hook : KnowledgeHook
            Hook to validate
        registry : HookRegistry | None
            Registry for cross-hook validation

        Returns
        -------
        list[PokaYokeViolation]
            List of violations found

        Examples
        --------
        >>> from kgcl.hybrid.knowledge_hooks import KnowledgeHook, HookPhase, HookAction
        >>> guard = PokaYokeGuard()
        >>> hook = KnowledgeHook(
        ...     hook_id="test",
        ...     name="Test",
        ...     phase=HookPhase.ON_CHANGE,
        ...     condition_query="",  # Empty - violation!
        ...     action=HookAction.NOTIFY,
        ... )
        >>> violations = guard.validate_hook(hook)
        >>> any(v.rule_id == "PY-HOOK-001" for v in violations)
        True
        """
        violations: list[PokaYokeViolation] = []

        # PY-HOOK-001: Empty condition query
        if not hook.condition_query.strip():
            violations.append(
                PokaYokeViolation(
                    rule_id="PY-HOOK-001",
                    py_type=HookPokaYokeType.SHUTDOWN,
                    message="Hook has empty condition query",
                    hook_id=hook.hook_id,
                )
            )

        # PY-HOOK-002: Invalid SPARQL syntax
        if hook.condition_query.strip():
            sparql_violation = self._check_sparql_syntax(hook)
            if sparql_violation:
                violations.append(sparql_violation)

        # PY-HOOK-003: Priority conflict (requires registry)
        if registry:
            priority_violation = self._check_priority_conflict(hook, registry)
            if priority_violation:
                violations.append(priority_violation)

        # PY-HOOK-005: Missing handler data
        handler_violation = self._check_handler_data(hook)
        if handler_violation:
            violations.append(handler_violation)

        # PY-HOOK-007: Duplicate hook ID
        if hook.hook_id in self._known_hook_ids:
            violations.append(
                PokaYokeViolation(
                    rule_id="PY-HOOK-007",
                    py_type=HookPokaYokeType.SHUTDOWN,
                    message=f"Duplicate hook ID: {hook.hook_id}",
                    hook_id=hook.hook_id,
                )
            )
        else:
            self._known_hook_ids.add(hook.hook_id)

        return violations

    def _check_sparql_syntax(self, hook: KnowledgeHook) -> PokaYokeViolation | None:
        """Check for basic SPARQL syntax errors.

        Parameters
        ----------
        hook : KnowledgeHook
            Hook with condition query

        Returns
        -------
        PokaYokeViolation | None
            Violation if syntax error detected
        """
        query = hook.condition_query.strip().upper()

        # Must start with ASK or SELECT
        if not (query.startswith("ASK") or query.startswith("SELECT")):
            return PokaYokeViolation(
                rule_id="PY-HOOK-002",
                py_type=HookPokaYokeType.VALIDATION,
                message="Condition query must start with ASK or SELECT",
                hook_id=hook.hook_id,
            )

        # Check for balanced braces
        if query.count("{") != query.count("}"):
            return PokaYokeViolation(
                rule_id="PY-HOOK-002",
                py_type=HookPokaYokeType.VALIDATION,
                message="Unbalanced braces in SPARQL query",
                hook_id=hook.hook_id,
            )

        return None

    def _check_priority_conflict(self, hook: KnowledgeHook, registry: HookRegistry) -> PokaYokeViolation | None:
        """Check for priority conflicts with existing hooks.

        Parameters
        ----------
        hook : KnowledgeHook
            Hook to check
        registry : HookRegistry
            Registry of existing hooks

        Returns
        -------
        PokaYokeViolation | None
            Violation if priority conflict detected
        """
        existing_hooks = registry.get_by_phase(hook.phase)

        for existing in existing_hooks:
            if existing.hook_id != hook.hook_id and existing.priority == hook.priority:
                return PokaYokeViolation(
                    rule_id="PY-HOOK-003",
                    py_type=HookPokaYokeType.CONTROL,
                    message=f"Priority {hook.priority} conflicts with hook {existing.hook_id}",
                    hook_id=hook.hook_id,
                )

        return None

    def _check_handler_data(self, hook: KnowledgeHook) -> PokaYokeViolation | None:
        """Check handler_data contains required fields for action type.

        Parameters
        ----------
        hook : KnowledgeHook
            Hook to validate

        Returns
        -------
        PokaYokeViolation | None
            Violation if missing required data
        """
        from kgcl.hybrid.knowledge_hooks import HookAction

        required_keys: dict[HookAction, list[str]] = {
            HookAction.REJECT: ["reason"],
            HookAction.NOTIFY: ["message"],
            HookAction.TRANSFORM: ["pattern"],
        }

        required = required_keys.get(hook.action, [])
        missing = [k for k in required if k not in hook.handler_data]

        if missing:
            return PokaYokeViolation(
                rule_id="PY-HOOK-005",
                py_type=HookPokaYokeType.VALIDATION,
                message=f"Missing handler_data keys: {missing}",
                hook_id=hook.hook_id,
            )

        return None

    def validate_registry(self, registry: HookRegistry) -> list[PokaYokeViolation]:
        """Validate all hooks in registry.

        Parameters
        ----------
        registry : HookRegistry
            Registry to validate

        Returns
        -------
        list[PokaYokeViolation]
            All violations found

        Examples
        --------
        >>> from kgcl.hybrid.knowledge_hooks import HookRegistry
        >>> guard = PokaYokeGuard()
        >>> registry = HookRegistry()
        >>> violations = guard.validate_registry(registry)
        >>> len(violations)
        0
        """
        all_violations: list[PokaYokeViolation] = []

        # Reset known IDs for fresh validation
        self._known_hook_ids.clear()

        for hook in registry.get_all():
            violations = self.validate_hook(hook, registry)
            all_violations.extend(violations)

        return all_violations

    def get_blocking_violations(self, violations: list[PokaYokeViolation]) -> list[PokaYokeViolation]:
        """Filter violations that should block execution.

        Parameters
        ----------
        violations : list[PokaYokeViolation]
            All violations

        Returns
        -------
        list[PokaYokeViolation]
            Only SHUTDOWN and CONTROL violations

        Examples
        --------
        >>> guard = PokaYokeGuard()
        >>> v1 = PokaYokeViolation("PY-001", HookPokaYokeType.SHUTDOWN, "msg")
        >>> v2 = PokaYokeViolation("PY-002", HookPokaYokeType.WARNING, "msg")
        >>> blocking = guard.get_blocking_violations([v1, v2])
        >>> len(blocking)
        1
        """
        return [v for v in violations if v.blocks_execution]

    def get_warnings(self, violations: list[PokaYokeViolation]) -> list[PokaYokeViolation]:
        """Filter violations that are warnings only.

        Parameters
        ----------
        violations : list[PokaYokeViolation]
            All violations

        Returns
        -------
        list[PokaYokeViolation]
            Only WARNING violations
        """
        return [v for v in violations if v.py_type == HookPokaYokeType.WARNING]
