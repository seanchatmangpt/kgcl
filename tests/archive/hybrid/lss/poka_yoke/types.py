"""Poka-Yoke Type Definitions with Doctests.

This module defines the core types for Poka-Yoke error-proofing:
- PokaYokeFunction: SHUTDOWN, CONTROL, WARNING
- PokaYokeMethod: Contact, Fixed-Value, Motion-Step
"""

from __future__ import annotations

from enum import Enum


class PokaYokeFunction(Enum):
    """Poka-Yoke regulatory functions by severity level.

    The three functions define how the system responds to detected errors:

    - **SHUTDOWN**: Highest severity - stops process immediately (safety-critical)
    - **CONTROL**: Medium severity - gates process until corrected (regulation)
    - **WARNING**: Lowest severity - alerts without stopping (monitoring)

    Examples
    --------
    >>> func = PokaYokeFunction.SHUTDOWN
    >>> func.name
    'SHUTDOWN'
    >>> func.value
    'Shutdown'

    >>> # Check severity ordering (SHUTDOWN > CONTROL > WARNING)
    >>> PokaYokeFunction.SHUTDOWN.value
    'Shutdown'
    >>> PokaYokeFunction.CONTROL.value
    'Control'
    >>> PokaYokeFunction.WARNING.value
    'Warning'

    >>> # Use in validation logic
    >>> def validate_recursion(depth: int, max_depth: int = 100) -> PokaYokeFunction:
    ...     if depth > max_depth:
    ...         return PokaYokeFunction.SHUTDOWN  # Safety-critical
    ...     elif depth > max_depth * 0.8:
    ...         return PokaYokeFunction.WARNING  # Approaching limit
    ...     return PokaYokeFunction.CONTROL  # Normal operation
    >>> validate_recursion(150)
    <PokaYokeFunction.SHUTDOWN: 'Shutdown'>
    >>> validate_recursion(90)
    <PokaYokeFunction.WARNING: 'Warning'>

    >>> # Pattern matching
    >>> def handle_error(func: PokaYokeFunction) -> str:
    ...     match func:
    ...         case PokaYokeFunction.SHUTDOWN:
    ...             return "STOP: Safety-critical error"
    ...         case PokaYokeFunction.CONTROL:
    ...             return "GATE: Wait for correction"
    ...         case PokaYokeFunction.WARNING:
    ...             return "LOG: Non-critical alert"
    >>> handle_error(PokaYokeFunction.SHUTDOWN)
    'STOP: Safety-critical error'
    """

    SHUTDOWN = "Shutdown"
    CONTROL = "Control"
    WARNING = "Warning"


class PokaYokeMethod(Enum):
    """Poka-Yoke detection methods.

    The three methods define HOW errors are detected:

    - **CONTACT**: Physical/logical constraints prevent errors (prevention)
    - **FIXED_VALUE**: Ensure correct count/selection from valid set (detection)
    - **MOTION_STEP**: Ensure correct sequence of operations (correction)

    Examples
    --------
    >>> method = PokaYokeMethod.CONTACT
    >>> method.name
    'CONTACT'
    >>> method.value
    'Contact Method'

    >>> # All three methods
    >>> [m.value for m in PokaYokeMethod]
    ['Contact Method', 'Fixed-Value Method', 'Motion-Step Method']

    >>> # Use in validation
    >>> def validate_uri(uri: str) -> tuple[bool, PokaYokeMethod]:
    ...     # Contact method: structural constraint
    ...     if not uri.startswith(("http://", "https://", "urn:")):
    ...         return False, PokaYokeMethod.CONTACT
    ...     return True, PokaYokeMethod.CONTACT
    >>> validate_uri("urn:task:A")
    (True, <PokaYokeMethod.CONTACT: 'Contact Method'>)
    >>> validate_uri("invalid")
    (False, <PokaYokeMethod.CONTACT: 'Contact Method'>)

    >>> def validate_status(status: str, valid_set: set[str]) -> tuple[bool, PokaYokeMethod]:
    ...     # Fixed-Value method: selection from valid set
    ...     return status in valid_set, PokaYokeMethod.FIXED_VALUE
    >>> validate_status("Active", {"Pending", "Active", "Completed"})
    (True, <PokaYokeMethod.FIXED_VALUE: 'Fixed-Value Method'>)
    >>> validate_status("Running", {"Pending", "Active", "Completed"})
    (False, <PokaYokeMethod.FIXED_VALUE: 'Fixed-Value Method'>)

    >>> def validate_sequence(current: str, previous: str) -> tuple[bool, PokaYokeMethod]:
    ...     # Motion-Step method: sequence validation
    ...     valid_transitions = {
    ...         "Pending": {"Active", "Cancelled"},
    ...         "Active": {"Completed", "Cancelled"},
    ...         "Completed": {"Archived"},
    ...     }
    ...     allowed = valid_transitions.get(previous, set())
    ...     return current in allowed, PokaYokeMethod.MOTION_STEP
    >>> validate_sequence("Completed", "Active")
    (True, <PokaYokeMethod.MOTION_STEP: 'Motion-Step Method'>)
    >>> validate_sequence("Pending", "Completed")  # Backwards transition
    (False, <PokaYokeMethod.MOTION_STEP: 'Motion-Step Method'>)

    >>> # Combined validation example
    >>> def validate_task(uri: str, status: str, prev_status: str | None) -> dict[str, object]:
    ...     results = {}
    ...     # Contact: URI format
    ...     results["uri_valid"], results["uri_method"] = validate_uri(uri)
    ...     # Fixed-Value: Status vocabulary
    ...     valid_statuses = {"Pending", "Active", "Completed", "Cancelled", "Archived"}
    ...     results["status_valid"], results["status_method"] = validate_status(status, valid_statuses)
    ...     # Motion-Step: State transitions
    ...     if prev_status:
    ...         results["transition_valid"], results["transition_method"] = validate_sequence(status, prev_status)
    ...     return results
    >>> validate_task("urn:task:A", "Active", "Pending")  # doctest: +NORMALIZE_WHITESPACE
    {'uri_valid': True, 'uri_method': <PokaYokeMethod.CONTACT: 'Contact Method'>,
     'status_valid': True, 'status_method': <PokaYokeMethod.FIXED_VALUE: 'Fixed-Value Method'>,
     'transition_valid': True, 'transition_method': <PokaYokeMethod.MOTION_STEP: 'Motion-Step Method'>}
    """

    CONTACT = "Contact Method"
    FIXED_VALUE = "Fixed-Value Method"
    MOTION_STEP = "Motion-Step Method"
