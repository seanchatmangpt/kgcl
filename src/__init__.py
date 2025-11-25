"""Chicago TDD Tools - Python Implementation

A testing framework enforcing Chicago-style TDD (Classicist Test-Driven Development)
with compile-time guarantees translated to Python type hints and runtime validation.

Key Modules:
- core: Assertions, fixtures, and decorators
- swarm: Test orchestration and coordination
- validation: Property testing and invariant validation
- testing: Advanced testing utilities (state machines, mutation, property-based testing)

Quick Start:
    from chicago_tdd_tools.core import test, assert_eq_with_msg

    @test
    def test_addition():
        assert_eq_with_msg(5 + 3, 8, "math works")
"""

__version__ = "1.4.0"
__author__ = "Chicago TDD Tools Contributors"
__license__ = "MIT"
__all__ = [
    "core",
    "swarm",
    "validation",
    "testing",
    "assert_success",
    "assert_error",
    "assert_eq_with_msg",
    "assert_in_range",
    "assert_that",
    "test",
    "async_test",
    "fixture_test",
    "TestFixture",
]

from . import core, swarm, validation, testing
from .core import (
    assert_success,
    assert_error,
    assert_eq_with_msg,
    assert_in_range,
    assert_that,
    test,
    async_test,
    fixture_test,
    TestFixture,
)
