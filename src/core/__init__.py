"""Core Chicago TDD functionality

Provides assertion utilities, test fixtures, and decorators following Chicago TDD principles:
- Type-first design with Python type hints
- Behavior verification with real collaborators (not mocks)
- Error prevention through runtime validation (Poka-Yoke)
- Zero-cost abstractions where possible
"""

from .assertions import AssertionError as ChicagoAssertionError
from .assertions import (
    assert_eq_with_msg,
    assert_error,
    assert_in_range,
    assert_success,
    assert_that,
)
from .builders import Builder
from .decorators import async_test, fixture_test, test
from .fail_fast import FailFastValidator
from .fixture import FixtureError, FixtureMetadata, FixtureResult, TestFixture
from .poka_yoke import Poka, PokaYokeError
from .state import StateManager

__all__ = [
    "Builder",
    "ChicagoAssertionError",
    "FailFastValidator",
    "FixtureError",
    "FixtureMetadata",
    "FixtureResult",
    "Poka",
    "PokaYokeError",
    "StateManager",
    "TestFixture",
    "assert_eq_with_msg",
    "assert_error",
    "assert_in_range",
    "assert_success",
    "assert_that",
    "async_test",
    "fixture_test",
    "test",
]
