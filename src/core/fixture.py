"""Test Fixtures

Provides reusable test fixtures with state management and test isolation.
Supports sync and async setup/cleanup with metadata tracking.
"""

from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid


class FixtureError(Exception):
    """Fixture operation error"""
    pass


class FixtureResult(Exception):
    """Result type wrapper for fixture operations (Optional[T] in Python)"""
    pass


@dataclass
class FixtureMetadata:
    """Metadata about a fixture instance

    Tracks creation time and state snapshots for debugging and introspection.
    """
    created_at: datetime = field(default_factory=datetime.now)
    snapshots: List[Dict[str, Any]] = field(default_factory=list)
    fixture_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def capture_snapshot(self, state: Dict[str, Any]) -> None:
        """Capture current state snapshot"""
        self.snapshots.append(state.copy())

    def get_snapshot(self, index: int = -1) -> Optional[Dict[str, Any]]:
        """Get snapshot by index (default: most recent)"""
        if not self.snapshots:
            return None
        return self.snapshots[index]

    def snapshot_count(self) -> int:
        """Get number of captured snapshots"""
        return len(self.snapshots)

    def age_seconds(self) -> float:
        """Get fixture age in seconds since creation"""
        return (datetime.now() - self.created_at).total_seconds()

    def __repr__(self) -> str:
        return (
            f"FixtureMetadata(id={self.fixture_id!r}, "
            f"created_at={self.created_at!r}, snapshots={len(self.snapshots)})"
        )


class TestFixture:
    """Base class for test fixtures with lifecycle management

    Provides setup/cleanup lifecycle, metadata tracking, and state management.

    Example:
        class UserFixture(TestFixture):
            def setup(self):
                self.user = User(name="Alice")

            def get_user(self):
                return self.user

            def cleanup(self):
                del self.user

        @fixture_test(UserFixture)
        def test_user(fixture):
            user = fixture.get_user()
            assert user.name == "Alice"
    """

    def __init__(self) -> None:
        self._metadata = FixtureMetadata()
        self._state: Dict[str, Any] = {}
        self._initialized = False

    def setup(self) -> None:
        """Setup fixture state (override in subclasses)"""
        self._initialized = True

    def cleanup(self) -> None:
        """Cleanup fixture resources (override in subclasses)"""
        pass

    def set_state(self, key: str, value: Any) -> None:
        """Store state value"""
        self._state[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Retrieve state value"""
        return self._state.get(key, default)

    def capture_snapshot(self) -> None:
        """Capture current state as snapshot"""
        self._metadata.capture_snapshot(self._state.copy())

    def metadata(self) -> FixtureMetadata:
        """Get fixture metadata"""
        return self._metadata

    def is_initialized(self) -> bool:
        """Check if fixture is initialized"""
        return self._initialized

    def reset(self) -> None:
        """Reset fixture to initial state"""
        self._state.clear()
        self._initialized = False

    def __enter__(self) -> "TestFixture":
        """Context manager support"""
        self.setup()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager cleanup"""
        self.cleanup()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(metadata={self._metadata!r})"


class AsyncTestFixture(TestFixture):
    """Base class for async test fixtures

    Supports async setup and cleanup methods.
    """

    async def async_setup(self) -> None:
        """Async setup (override in subclasses)"""
        pass

    async def async_cleanup(self) -> None:
        """Async cleanup (override in subclasses)"""
        pass

    async def __aenter__(self) -> "AsyncTestFixture":
        """Async context manager support"""
        await self.async_setup()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager cleanup"""
        await self.async_cleanup()
