"""
Value objects and enums for hook invariants.

This module centralizes the strongly typed identifiers used across the hook
subsystem so that misuse is prevented at construction time (poka-yoke).
"""

from __future__ import annotations

import re
import uuid
from enum import Enum


class HookName(str):
    """Validated hook name that enforces formatting constraints."""

    _VALID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")
    _MAX_LENGTH = 120

    @classmethod
    def new(cls, raw: str) -> HookName:
        """Create a validated hook name."""
        trimmed = raw.strip()
        if not trimmed:
            raise ValueError("Hook names must be non-empty and trimmed")
        if len(trimmed) > cls._MAX_LENGTH:
            raise ValueError(f"Hook names must be <= {cls._MAX_LENGTH} characters")
        if not cls._VALID_PATTERN.fullmatch(trimmed):
            raise ValueError("Hook names may only contain A-Za-z0-9_.:- characters")
        return cls(trimmed)

    @classmethod
    def ensure(cls, value: str | HookName) -> HookName:
        """Coerce arbitrary input into a validated HookName."""
        if isinstance(value, cls):
            return value
        return cls.new(str(value))


class ExecutionId(str):
    """UUID-backed execution identifier."""

    @classmethod
    def new(cls) -> ExecutionId:
        """Generate a new execution identifier."""
        return cls(str(uuid.uuid4()))

    @classmethod
    def ensure(cls, value: str | ExecutionId) -> ExecutionId:
        """Validate that the provided value is a UUID."""
        try:
            parsed = str(uuid.UUID(str(value)))
        except (TypeError, ValueError) as exc:
            raise ValueError("ExecutionId must be a valid UUID string") from exc
        return cls(parsed)


class LifecycleEventType(str, Enum):
    """Lifecycle events emitted by the hook executor."""

    PRE_CONDITION = "pre_condition"
    POST_CONDITION = "post_condition"
    PRE_EXECUTE = "pre_execute"
    POST_EXECUTE = "post_execute"
