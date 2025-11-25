"""Core Chicago TDD functionality

Provides assertion utilities, test fixtures, and decorators following Chicago TDD principles:
- Type-first design with Python type hints
- Behavior verification with real collaborators (not mocks)
- Error prevention through runtime validation (Poka-Yoke)
- Zero-cost abstractions where possible
"""

from .assertions import (
    assert_success,
    assert_error,
    assert_eq_with_msg,
    assert_in_range,
    assert_that,
    AssertionError as ChicagoAssertionError,
)
from .decorators import test, async_test, fixture_test
from .fixture import TestFixture, FixtureMetadata, FixtureError, FixtureResult
from .builders import Builder
from .state import StateManager
from .fail_fast import FailFastValidator
from .poka_yoke import Poka, PokaYokeError

__all__ = [
    "assert_success",
    "assert_error",
    "assert_eq_with_msg",
    "assert_in_range",
    "assert_that",
    "test",
    "async_test",
    "fixture_test",
    "TestFixture",
    "FixtureMetadata",
    "FixtureError",
    "FixtureResult",
    "Builder",
    "StateManager",
    "FailFastValidator",
    "Poka",
    "PokaYokeError",
    "ChicagoAssertionError",
]
