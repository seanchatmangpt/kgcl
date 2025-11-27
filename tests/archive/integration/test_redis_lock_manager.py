"""Integration tests for RedisLockManager against container.

Tests verify the RedisLockManager can correctly:
- Connect to Redis
- Acquire and release exclusive locks
- Handle semaphores for rate limiting
- Manage distributed barriers for synchronization
- Support read/write lock patterns

Examples
--------
>>> uv run pytest tests/integration/test_redis_lock_manager.py -v
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

import pytest

from kgcl.hybrid.adapters.redis_lock_manager import (
    BarrierState,
    LockInfo,
    LockType,
    RedisLockManager,
)

if TYPE_CHECKING:
    pass


@pytest.fixture
def redis_client(redis_container: dict[str, Any]) -> Any:
    """Create a Redis client connected to the container."""
    import redis

    client = redis.from_url(redis_container["url"])
    # Clear any existing data
    client.flushdb()
    yield client
    client.flushdb()
    client.close()


@pytest.fixture
def lock_manager(redis_client: Any) -> RedisLockManager:
    """Create a RedisLockManager instance."""
    return RedisLockManager(redis_client, default_ttl=10, retry_interval=0.05)


@pytest.mark.container
class TestExclusiveLocks:
    """Integration tests for exclusive lock operations."""

    def test_acquire_exclusive_lock(self, lock_manager: RedisLockManager) -> None:
        """Verify exclusive lock can be acquired."""
        lock = lock_manager.acquire_exclusive("resource-1", timeout=5.0)

        assert lock is not None
        assert isinstance(lock, LockInfo)
        assert lock.lock_type == LockType.EXCLUSIVE
        assert "resource-1" in lock.lock_key

        # Cleanup
        lock_manager.release_exclusive("resource-1")

    def test_exclusive_lock_blocks_others(self, redis_client: Any) -> None:
        """Verify exclusive lock prevents other acquisitions."""
        manager1 = RedisLockManager(redis_client)
        manager2 = RedisLockManager(redis_client)

        # First manager acquires
        lock1 = manager1.acquire_exclusive("shared-resource", timeout=5.0)
        assert lock1 is not None

        # Second manager should fail (non-blocking)
        lock2 = manager2.acquire_exclusive("shared-resource", timeout=0.5, blocking=False)
        assert lock2 is None

        # Release and try again
        manager1.release_exclusive("shared-resource")
        lock2 = manager2.acquire_exclusive("shared-resource", timeout=1.0)
        assert lock2 is not None

        manager2.release_exclusive("shared-resource")

    def test_exclusive_lock_context_manager(self, lock_manager: RedisLockManager) -> None:
        """Verify context manager acquires and releases lock."""
        with lock_manager.exclusive_lock("ctx-resource", timeout=5.0) as lock:
            assert lock is not None
            assert lock_manager.is_locked("ctx-resource")

        # Lock should be released after context
        assert not lock_manager.is_locked("ctx-resource")

    def test_renew_exclusive_lock(self, lock_manager: RedisLockManager) -> None:
        """Verify lock TTL can be renewed."""
        lock = lock_manager.acquire_exclusive("renew-test", ttl=5)
        assert lock is not None

        # Renew with longer TTL
        renewed = lock_manager.renew_exclusive("renew-test", ttl=60)
        assert renewed is True

        lock_manager.release_exclusive("renew-test")

    def test_release_non_owned_lock_fails(self, redis_client: Any) -> None:
        """Verify releasing a lock owned by another manager fails."""
        manager1 = RedisLockManager(redis_client)
        manager2 = RedisLockManager(redis_client)

        lock = manager1.acquire_exclusive("owned-resource", timeout=5.0)
        assert lock is not None

        # Manager2 should not be able to release
        released = manager2.release_exclusive("owned-resource")
        assert released is False

        # Manager1 can release
        released = manager1.release_exclusive("owned-resource")
        assert released is True


@pytest.mark.container
class TestSemaphores:
    """Integration tests for semaphore operations."""

    def test_acquire_semaphore_slot(self, lock_manager: RedisLockManager) -> None:
        """Verify semaphore slot can be acquired."""
        slot = lock_manager.acquire_semaphore("rate-limiter", max_count=3, timeout=5.0)

        assert slot is not None
        assert isinstance(slot, str)

        lock_manager.release_semaphore("rate-limiter", slot)

    def test_semaphore_limits_concurrent(self, redis_client: Any) -> None:
        """Verify semaphore limits concurrent holders."""
        manager = RedisLockManager(redis_client)

        # Acquire up to max_count
        slots = []
        for i in range(3):
            slot = manager.acquire_semaphore("limited", max_count=3, timeout=1.0)
            assert slot is not None, f"Failed to acquire slot {i}"
            slots.append(slot)

        # Next acquisition should fail (non-blocking)
        extra_slot = manager.acquire_semaphore("limited", max_count=3, timeout=0.2, blocking=False)
        assert extra_slot is None, "Should not exceed max_count"

        # Release one and try again
        manager.release_semaphore("limited", slots[0])
        new_slot = manager.acquire_semaphore("limited", max_count=3, timeout=1.0)
        assert new_slot is not None

        # Cleanup
        for slot in slots[1:] + [new_slot]:
            manager.release_semaphore("limited", slot)

    def test_semaphore_context_manager(self, lock_manager: RedisLockManager) -> None:
        """Verify semaphore context manager works."""
        with lock_manager.semaphore("ctx-sem", max_count=5, timeout=5.0) as slot:
            assert slot is not None


@pytest.mark.container
class TestBarriers:
    """Integration tests for distributed barrier operations."""

    def test_create_barrier(self, lock_manager: RedisLockManager) -> None:
        """Verify barrier can be created."""
        barrier_key = lock_manager.create_barrier("sync-point", count=3, ttl=60)

        assert barrier_key == "barrier:sync-point"

        lock_manager.delete_barrier("sync-point")

    def test_barrier_waits_for_participants(self, lock_manager: RedisLockManager) -> None:
        """Verify barrier waits for required participants."""
        lock_manager.create_barrier("wait-test", count=3)

        # First participant arrives
        state1 = lock_manager.arrive_at_barrier("wait-test", "participant-1")
        assert state1.current_count == 1
        assert state1.released is False

        # Second participant arrives
        state2 = lock_manager.arrive_at_barrier("wait-test", "participant-2")
        assert state2.current_count == 2
        assert state2.released is False

        # Third participant releases the barrier
        state3 = lock_manager.arrive_at_barrier("wait-test", "participant-3")
        assert state3.current_count == 3
        assert state3.released is True

        lock_manager.delete_barrier("wait-test")

    def test_barrier_returns_participants(self, lock_manager: RedisLockManager) -> None:
        """Verify barrier tracks participant IDs."""
        lock_manager.create_barrier("track-test", count=2)

        state = lock_manager.arrive_at_barrier("track-test", "worker-A")
        assert "worker-A" in state.participants

        state = lock_manager.arrive_at_barrier("track-test", "worker-B")
        assert "worker-A" in state.participants
        assert "worker-B" in state.participants

        lock_manager.delete_barrier("track-test")


@pytest.mark.container
class TestReadWriteLocks:
    """Integration tests for read/write lock operations."""

    def test_acquire_read_lock(self, lock_manager: RedisLockManager) -> None:
        """Verify read lock can be acquired."""
        lock = lock_manager.acquire_read_lock("document", timeout=5.0)

        assert lock is not None
        assert lock.lock_type == LockType.READ

        lock_manager.release_read_lock("document", lock.owner_id)

    def test_multiple_readers_allowed(self, redis_client: Any) -> None:
        """Verify multiple readers can hold locks simultaneously."""
        manager = RedisLockManager(redis_client)

        readers = []
        for i in range(5):
            lock = manager.acquire_read_lock(f"shared-doc", timeout=5.0)
            assert lock is not None, f"Reader {i} should acquire lock"
            readers.append(lock)

        # All readers acquired successfully
        assert len(readers) == 5

        # Cleanup
        for lock in readers:
            manager.release_read_lock("shared-doc", lock.owner_id)

    def test_write_lock_blocks_readers(self, redis_client: Any) -> None:
        """Verify write lock blocks reader acquisition."""
        manager = RedisLockManager(redis_client)

        # Acquire write lock
        write_lock = manager.acquire_write_lock("exclusive-doc", timeout=5.0)
        assert write_lock is not None

        # Read lock should fail (non-blocking would timeout)
        read_lock = manager.acquire_read_lock("exclusive-doc", timeout=0.3)
        assert read_lock is None

        # Release write, read should succeed
        manager.release_write_lock("exclusive-doc")
        read_lock = manager.acquire_read_lock("exclusive-doc", timeout=1.0)
        assert read_lock is not None

        manager.release_read_lock("exclusive-doc", read_lock.owner_id)

    def test_write_lock_waits_for_readers(self, redis_client: Any) -> None:
        """Verify write lock waits for all readers to finish."""
        manager = RedisLockManager(redis_client)

        # Acquire read lock
        read_lock = manager.acquire_read_lock("rw-doc", timeout=5.0)
        assert read_lock is not None

        # Write lock should fail while reader holds
        write_lock = manager.acquire_write_lock("rw-doc", timeout=0.3)
        assert write_lock is None

        # Release read, write should succeed
        manager.release_read_lock("rw-doc", read_lock.owner_id)
        write_lock = manager.acquire_write_lock("rw-doc", timeout=1.0)
        assert write_lock is not None

        manager.release_write_lock("rw-doc")

    def test_read_write_context_managers(self, lock_manager: RedisLockManager) -> None:
        """Verify read/write context managers work."""
        with lock_manager.read_lock("ctx-doc", timeout=5.0) as rlock:
            assert rlock is not None

        with lock_manager.write_lock("ctx-doc", timeout=5.0) as wlock:
            assert wlock is not None


@pytest.mark.container
class TestLockUtilities:
    """Integration tests for lock utility methods."""

    def test_is_locked(self, lock_manager: RedisLockManager) -> None:
        """Verify is_locked reports correct state."""
        assert not lock_manager.is_locked("check-resource")

        lock = lock_manager.acquire_exclusive("check-resource", timeout=5.0)
        assert lock_manager.is_locked("check-resource")

        lock_manager.release_exclusive("check-resource")
        assert not lock_manager.is_locked("check-resource")

    def test_get_lock_info(self, lock_manager: RedisLockManager) -> None:
        """Verify lock info retrieval."""
        lock = lock_manager.acquire_exclusive("info-resource", timeout=5.0)

        info = lock_manager.get_lock_info("info-resource", LockType.EXCLUSIVE)

        assert info is not None
        assert "owner" in info
        assert info["owner"] == lock.owner_id

        lock_manager.release_exclusive("info-resource")

    def test_force_release(self, lock_manager: RedisLockManager) -> None:
        """Verify force release works."""
        lock = lock_manager.acquire_exclusive("force-resource", timeout=5.0)
        assert lock is not None

        # Force release (admin operation)
        released = lock_manager.force_release("force-resource")
        assert released is True

        assert not lock_manager.is_locked("force-resource")

    def test_release_all_held(self, lock_manager: RedisLockManager) -> None:
        """Verify release_all_held releases all locks."""
        # Acquire multiple locks
        lock_manager.acquire_exclusive("multi-1", timeout=5.0)
        lock_manager.acquire_exclusive("multi-2", timeout=5.0)

        released = lock_manager.release_all_held()

        assert released == 2
        assert not lock_manager.is_locked("multi-1")
        assert not lock_manager.is_locked("multi-2")
