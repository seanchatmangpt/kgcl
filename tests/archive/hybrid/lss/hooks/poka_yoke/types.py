"""Poka-Yoke Type Definitions for Knowledge Hooks.

This module defines error-proofing types for Knowledge Hooks following
Shigeo Shingo's Poka-Yoke methodology:
- SHUTDOWN: Prevent catastrophic hook registration errors
- WARNING: Alert on suspicious hook patterns
- CONTROL: Gate hook configuration until valid
- VALIDATION: Validate hook before execution

References
----------
- Shigeo Shingo: "Zero Quality Control" - Poka-Yoke functions
- KGCL Knowledge Hooks: src/kgcl/hybrid/knowledge_hooks.py
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HookPokaYokeType(Enum):
    """Poka-Yoke error-proofing types for Knowledge Hooks.

    Four severity levels for hook validation and safety:

    - **SHUTDOWN**: Highest severity - prevent invalid hook registration
    - **WARNING**: Lowest severity - warn on suspicious patterns
    - **CONTROL**: Medium severity - gate until hook is valid
    - **VALIDATION**: Pre-execution validation of hook state

    Examples
    --------
    >>> poka_type = HookPokaYokeType.SHUTDOWN
    >>> poka_type.name
    'SHUTDOWN'
    >>> poka_type.value
    'Shutdown'

    >>> # All four types
    >>> [t.value for t in HookPokaYokeType]
    ['Shutdown', 'Warning', 'Control', 'Validation']

    >>> # Use in hook validation
    >>> def validate_hook_condition(condition: str) -> HookPokaYokeType:
    ...     # SHUTDOWN: Empty condition is invalid
    ...     if not condition.strip():
    ...         return HookPokaYokeType.SHUTDOWN
    ...     # CONTROL: Must contain SPARQL keywords
    ...     elif "ASK" not in condition and "SELECT" not in condition:
    ...         return HookPokaYokeType.CONTROL
    ...     # WARNING: Suspiciously simple condition
    ...     elif len(condition) < 30:
    ...         return HookPokaYokeType.WARNING
    ...     # VALIDATION: Valid condition
    ...     else:
    ...         return HookPokaYokeType.VALIDATION
    >>> validate_hook_condition("")
    <HookPokaYokeType.SHUTDOWN: 'Shutdown'>
    >>> validate_hook_condition("ASK { ?s ?p ?o . FILTER(?s != ?o) }")
    <HookPokaYokeType.VALIDATION: 'Validation'>
    """

    SHUTDOWN = "Shutdown"
    WARNING = "Warning"
    CONTROL = "Control"
    VALIDATION = "Validation"


@dataclass(frozen=True)
class HookPokaYoke:
    """Poka-Yoke error proofing definition for Knowledge Hooks.

    Defines specific error-proofing rules that prevent hook configuration
    and execution errors following Toyota Production System principles.

    Attributes
    ----------
    id : str
        Unique poka-yoke identifier (e.g., "PY-HOOK-001")
    type : HookPokaYokeType
        Error-proofing severity level
    description : str
        Human-readable description of what this prevents
    condition : str
        SPARQL query or Python condition to detect error
    action : str
        What happens when error is detected (reject, warn, gate)

    Examples
    --------
    >>> py = HookPokaYoke(
    ...     id="PY-HOOK-001",
    ...     type=HookPokaYokeType.SHUTDOWN,
    ...     description="Empty Condition Query",
    ...     condition="len(hook.condition_query.strip()) == 0",
    ...     action="Reject hook registration",
    ... )
    >>> py.id
    'PY-HOOK-001'
    >>> py.type
    <HookPokaYokeType.SHUTDOWN: 'Shutdown'>

    >>> # Priority ordering (SHUTDOWN > CONTROL > VALIDATION > WARNING)
    >>> def get_priority(py: HookPokaYoke) -> int:
    ...     priorities = {
    ...         HookPokaYokeType.SHUTDOWN: 1000,
    ...         HookPokaYokeType.CONTROL: 500,
    ...         HookPokaYokeType.VALIDATION: 100,
    ...         HookPokaYokeType.WARNING: 10,
    ...     }
    ...     return priorities[py.type]
    >>> get_priority(py)
    1000
    """

    id: str
    type: HookPokaYokeType
    description: str
    condition: str
    action: str


# =============================================================================
# PRE-DEFINED POKA-YOKES FOR KNOWLEDGE HOOKS
# =============================================================================

PY_HOOK_001 = HookPokaYoke(
    id="PY-HOOK-001",
    type=HookPokaYokeType.SHUTDOWN,
    description="Empty Condition Query",
    condition="len(hook.condition_query.strip()) == 0",
    action="REJECT: Hook must have non-empty condition query",
)

PY_HOOK_002 = HookPokaYoke(
    id="PY-HOOK-002",
    type=HookPokaYokeType.WARNING,
    description="Circular Chain Detection",
    condition="""
    ASK {
        ?hook <https://kgc.org/ns/hook/chainTo> ?child .
        ?child <https://kgc.org/ns/hook/chainTo>+ ?hook .
    }
    """,
    action="WARN: Circular hook chain detected - may cause infinite loop",
)

PY_HOOK_003 = HookPokaYoke(
    id="PY-HOOK-003",
    type=HookPokaYokeType.CONTROL,
    description="Priority Conflict",
    condition="""
    ASK {
        ?hook1 <https://kgc.org/ns/hook/phase> ?phase .
        ?hook1 <https://kgc.org/ns/hook/priority> ?p1 .
        ?hook2 <https://kgc.org/ns/hook/phase> ?phase .
        ?hook2 <https://kgc.org/ns/hook/priority> ?p1 .
        FILTER(?hook1 != ?hook2)
    }
    """,
    action="GATE: Multiple hooks with same phase and priority - must assign unique priorities",
)

PY_HOOK_004 = HookPokaYoke(
    id="PY-HOOK-004",
    type=HookPokaYokeType.VALIDATION,
    description="Invalid Phase Assignment",
    condition="""
    ASK {
        ?hook <https://kgc.org/ns/hook/phase> ?phase .
        FILTER(?phase NOT IN ("pre_tick", "on_change", "post_tick", "pre_validation", "post_validation"))
    }
    """,
    action="VALIDATE: Hook phase must be one of: pre_tick, on_change, post_tick, pre_validation, post_validation",
)

PY_HOOK_005 = HookPokaYoke(
    id="PY-HOOK-005",
    type=HookPokaYokeType.SHUTDOWN,
    description="Disabled Hook with Chaining",
    condition="""
    ASK {
        ?hook <https://kgc.org/ns/hook/enabled> false .
        ?hook <https://kgc.org/ns/hook/chainTo> ?child .
    }
    """,
    action="REJECT: Disabled hook cannot chain to other hooks",
)

PY_HOOK_006 = HookPokaYoke(
    id="PY-HOOK-006",
    type=HookPokaYokeType.WARNING,
    description="Orphan Chained Hook",
    condition="""
    ASK {
        ?parent <https://kgc.org/ns/hook/chainTo> ?child .
        FILTER NOT EXISTS { ?child a <https://kgc.org/ns/hook/KnowledgeHook> }
    }
    """,
    action="WARN: Hook chains to non-existent child hook",
)

PY_HOOK_007 = HookPokaYoke(
    id="PY-HOOK-007",
    type=HookPokaYokeType.CONTROL,
    description="Invalid Action Type",
    condition="""
    ASK {
        ?hook <https://kgc.org/ns/hook/handlerAction> ?action .
        FILTER(?action NOT IN (
            <https://kgc.org/ns/hook/Assert>,
            <https://kgc.org/ns/hook/Reject>,
            <https://kgc.org/ns/hook/Notify>,
            <https://kgc.org/ns/hook/Transform>
        ))
    }
    """,
    action="GATE: Hook action must be one of: Assert, Reject, Notify, Transform",
)

PY_HOOK_008 = HookPokaYoke(
    id="PY-HOOK-008",
    type=HookPokaYokeType.VALIDATION,
    description="Missing Handler Data",
    condition="hook.action in [HookAction.REJECT, HookAction.NOTIFY] and not hook.handler_data",
    action="VALIDATE: REJECT and NOTIFY actions require handler_data (reason/message)",
)

PY_HOOK_009 = HookPokaYoke(
    id="PY-HOOK-009",
    type=HookPokaYokeType.WARNING,
    description="Overly Broad Condition",
    condition="""
    ASK { ?s ?p ?o }
    """,
    action="WARN: Hook condition matches entire graph - may have performance impact",
)

PY_HOOK_010 = HookPokaYoke(
    id="PY-HOOK-010",
    type=HookPokaYokeType.SHUTDOWN,
    description="Recursive Hook Trigger",
    condition="""
    ASK {
        ?hook <https://kgc.org/ns/hook/triggeredByMilestone> ?milestone .
        ?milestone <https://kgc.org/ns/hook/triggeredByMilestone> ?hook .
    }
    """,
    action="REJECT: Recursive milestone triggering detected",
)

# Collection of all pre-defined poka-yokes
ALL_HOOK_POKA_YOKES: list[HookPokaYoke] = [
    PY_HOOK_001,
    PY_HOOK_002,
    PY_HOOK_003,
    PY_HOOK_004,
    PY_HOOK_005,
    PY_HOOK_006,
    PY_HOOK_007,
    PY_HOOK_008,
    PY_HOOK_009,
    PY_HOOK_010,
]


def get_poka_yoke_by_id(poka_yoke_id: str) -> HookPokaYoke | None:
    """Get poka-yoke by ID.

    Parameters
    ----------
    poka_yoke_id : str
        Poka-yoke identifier (e.g., "PY-HOOK-001")

    Returns
    -------
    HookPokaYoke | None
        Poka-yoke if found

    Examples
    --------
    >>> py = get_poka_yoke_by_id("PY-HOOK-001")
    >>> py.description if py else None
    'Empty Condition Query'
    >>> get_poka_yoke_by_id("PY-HOOK-999")
    """
    for py in ALL_HOOK_POKA_YOKES:
        if py.id == poka_yoke_id:
            return py
    return None


def get_poka_yokes_by_type(poka_type: HookPokaYokeType) -> list[HookPokaYoke]:
    """Get all poka-yokes of a specific type.

    Parameters
    ----------
    poka_type : HookPokaYokeType
        Error-proofing type

    Returns
    -------
    list[HookPokaYoke]
        All poka-yokes of that type

    Examples
    --------
    >>> shutdown_pys = get_poka_yokes_by_type(HookPokaYokeType.SHUTDOWN)
    >>> len(shutdown_pys)
    3
    >>> all(py.type == HookPokaYokeType.SHUTDOWN for py in shutdown_pys)
    True
    """
    return [py for py in ALL_HOOK_POKA_YOKES if py.type == poka_type]
