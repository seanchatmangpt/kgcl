"""Test Decorators for Chicago TDD.

Provides decorators for test functions following AAA (Arrange-Act-Assert) pattern.
Supports synchronous, asynchronous, and fixture-based tests.
"""

import asyncio
import functools
from collections.abc import Callable
from typing import Any, TypeVar

from .fixture import Fixture

F = TypeVar("F", bound=Callable[..., Any])


def test[F: Callable[..., Any]](func: F) -> F:
    """Decorator for synchronous unit tests.

    Enforces AAA pattern and provides test metadata.

    Example:
        @test
        def test_addition():
            # Arrange
            x, y = 5, 3
            # Act
            result = x + y
            # Assert
            assert result == 8
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"FAILED: {func.__name__} - {type(e).__name__}: {e}")
            raise

    wrapper.__test_name__ = func.__name__  # Mark as test
    wrapper.__test_type__ = "sync"
    return wrapper


def async_test[F: Callable[..., Any]](func: F) -> F:
    """Decorator for asynchronous unit tests.

    Enforces AAA pattern with async/await support.

    Example:
        @async_test
        async def test_async_addition():
            # Arrange
            x, y = 5, 3
            # Act
            result = await async_add(x, y)
            # Assert
            assert result == 8
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if asyncio.iscoroutinefunction(func):
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            try:
                return loop.run_until_complete(func(*args, **kwargs))
            except Exception as e:
                print(f"FAILED: {func.__name__} - {type(e).__name__}: {e}")
                raise
        else:
            return func(*args, **kwargs)

    wrapper.__test_name__ = func.__name__
    wrapper.__test_type__ = "async"
    return wrapper


def fixture_test(fixture_class: type[Fixture]) -> Callable[[F], F]:
    """Decorator factory for fixture-based tests.

    Creates a test that receives a fixture instance as an argument.

    Args:
        fixture_class: The Fixture subclass to instantiate

    Example:
        class CounterFixture(Fixture):
            def setup(self):
                self.counter = 0

            def get_counter(self):
                return self.counter

        @fixture_test(CounterFixture)
        def test_counter(fixture):
            assert fixture.get_counter() == 0
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            fixture = fixture_class()
            try:
                fixture.setup()
                if asyncio.iscoroutinefunction(func):
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(func(fixture, *args, **kwargs))
                else:
                    result = func(fixture, *args, **kwargs)
                return result
            finally:
                fixture.cleanup()

        wrapper.__test_name__ = func.__name__
        wrapper.__test_type__ = "fixture"
        wrapper.__fixture_class__ = fixture_class
        return wrapper

    return decorator


class TestMetadata:
    """Metadata about a test function."""

    def __init__(self, func: Callable[..., Any]) -> None:
        self.name = getattr(func, "__test_name__", func.__name__)
        self.test_type = getattr(func, "__test_type__", "unknown")
        self.fixture_class = getattr(func, "__fixture_class__", None)
        self.is_async = asyncio.iscoroutinefunction(func)
        self.func = func

    def __repr__(self) -> str:
        return (
            f"TestMetadata(name={self.name!r}, type={self.test_type!r}, "
            f"async={self.is_async}, fixture={self.fixture_class})"
        )
