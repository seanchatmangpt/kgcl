"""Redis Lock Manager for distributed workflow locking.

Provides distributed locking primitives for workflow patterns:
- Exclusive locks for critical sections
- Read/write locks for shared resources
- Semaphores for rate limiting
- Distributed barriers for synchronization
- Lock ownership tracking

Real-World Scenarios
--------------------
- WCP-16 Deferred Choice: Mutex for exclusive path selection
- WCP-17 Interleaved Parallel: Shared resource access control
- WCP-35 Cancelling Partial Join: Rate-limited instance spawning
- WCP-3 Synchronization: Barrier for parallel branch convergence
"""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Generator

if TYPE_CHECKING:
    from redis import Redis


class LockType(Enum):
    """Types of distributed locks."""

    EXCLUSIVE = "exclusive"
    READ = "read"
    WRITE = "write"
    SEMAPHORE = "semaphore"


@dataclass(frozen=True)
class LockInfo:
    """Information about an acquired lock.

    Parameters
    ----------
    lock_key : str
        The key identifying the lock
    owner_id : str
        Unique identifier of the lock owner
    lock_type : LockType
        Type of lock
    acquired_at : float
        Unix timestamp when lock was acquired
    ttl : int
        Time-to-live in seconds
    """

    lock_key: str
    owner_id: str
    lock_type: LockType
    acquired_at: float
    ttl: int


@dataclass
class BarrierState:
    """State of a distributed barrier.

    Parameters
    ----------
    barrier_key : str
        Key identifying the barrier
    required_count : int
        Number of participants required
    current_count : int
        Current number of participants
    released : bool
        Whether barrier has been released
    participants : list[str]
        IDs of participants that have arrived
    """

    barrier_key: str
    required_count: int
    current_count: int = 0
    released: bool = False
    participants: list[str] = field(default_factory=list)


class RedisLockManager:
    """Distributed lock manager using Redis.

    Provides reliable distributed locking with:
    - Automatic lock expiration (TTL)
    - Lock renewal for long-running operations
    - Ownership verification for safe release
    - Lua scripts for atomic operations

    Parameters
    ----------
    redis_client : Redis
        Redis connection
    default_ttl : int
        Default lock TTL in seconds
    retry_interval : float
        Interval between lock acquisition retries

    Example
    -------
    >>> manager = RedisLockManager(redis_client)
    >>> with manager.exclusive_lock("resource-1", timeout=10) as lock:
    ...     # Critical section
    ...     process_resource()
    """

    # Lua script for atomic lock acquisition
    ACQUIRE_LOCK_SCRIPT = """
    local key = KEYS[1]
    local owner = ARGV[1]
    local ttl = tonumber(ARGV[2])

    if redis.call("EXISTS", key) == 0 then
        redis.call("HSET", key, "owner", owner, "acquired_at", ARGV[3])
        redis.call("EXPIRE", key, ttl)
        return 1
    end
    return 0
    """

    # Lua script for atomic lock release with ownership check
    RELEASE_LOCK_SCRIPT = """
    local key = KEYS[1]
    local owner = ARGV[1]

    if redis.call("HGET", key, "owner") == owner then
        redis.call("DEL", key)
        return 1
    end
    return 0
    """

    # Lua script for lock renewal with ownership check
    RENEW_LOCK_SCRIPT = """
    local key = KEYS[1]
    local owner = ARGV[1]
    local ttl = tonumber(ARGV[2])

    if redis.call("HGET", key, "owner") == owner then
        redis.call("EXPIRE", key, ttl)
        return 1
    end
    return 0
    """

    # Lua script for semaphore acquisition
    ACQUIRE_SEMAPHORE_SCRIPT = """
    local key = KEYS[1]
    local owner = ARGV[1]
    local max_count = tonumber(ARGV[2])
    local ttl = tonumber(ARGV[3])

    local current = redis.call("SCARD", key)
    if current < max_count then
        redis.call("SADD", key, owner)
        redis.call("EXPIRE", key, ttl)
        return 1
    end
    return 0
    """

    def __init__(self, redis_client: Redis, default_ttl: int = 30, retry_interval: float = 0.1) -> None:  # type: ignore[type-arg]
        """Initialize the lock manager.

        Parameters
        ----------
        redis_client : Redis
            Redis connection
        default_ttl : int
            Default lock TTL in seconds
        retry_interval : float
            Retry interval in seconds
        """
        self._redis = redis_client
        self._default_ttl = default_ttl
        self._retry_interval = retry_interval
        self._owner_id = f"{uuid.uuid4().hex[:8]}-{threading.current_thread().ident}"
        self._held_locks: dict[str, LockInfo] = {}
        self._local_lock = threading.Lock()

        # Register Lua scripts
        self._acquire_script = self._redis.register_script(self.ACQUIRE_LOCK_SCRIPT)
        self._release_script = self._redis.register_script(self.RELEASE_LOCK_SCRIPT)
        self._renew_script = self._redis.register_script(self.RENEW_LOCK_SCRIPT)
        self._semaphore_script = self._redis.register_script(self.ACQUIRE_SEMAPHORE_SCRIPT)

    def _make_lock_key(self, name: str, lock_type: LockType) -> str:
        """Create a lock key from name and type.

        Parameters
        ----------
        name : str
            Lock name
        lock_type : LockType
            Type of lock

        Returns
        -------
        str
            Redis key for the lock
        """
        return f"lock:{lock_type.value}:{name}"

    def acquire_exclusive(
        self, name: str, ttl: int | None = None, timeout: float = 10.0, blocking: bool = True
    ) -> LockInfo | None:
        """Acquire an exclusive lock.

        Parameters
        ----------
        name : str
            Name of the resource to lock
        ttl : int | None
            Lock TTL in seconds (uses default if None)
        timeout : float
            Maximum time to wait for lock
        blocking : bool
            Whether to block until acquired

        Returns
        -------
        LockInfo | None
            Lock info if acquired, None if failed
        """
        lock_key = self._make_lock_key(name, LockType.EXCLUSIVE)
        ttl = ttl or self._default_ttl
        start = time.time()

        while True:
            acquired_at = time.time()
            result = self._acquire_script(keys=[lock_key], args=[self._owner_id, ttl, str(acquired_at)])

            if result == 1:
                lock_info = LockInfo(
                    lock_key=lock_key,
                    owner_id=self._owner_id,
                    lock_type=LockType.EXCLUSIVE,
                    acquired_at=acquired_at,
                    ttl=ttl,
                )
                with self._local_lock:
                    self._held_locks[lock_key] = lock_info
                return lock_info

            if not blocking:
                return None

            if time.time() - start >= timeout:
                return None

            time.sleep(self._retry_interval)

    def release_exclusive(self, name: str) -> bool:
        """Release an exclusive lock.

        Parameters
        ----------
        name : str
            Name of the resource

        Returns
        -------
        bool
            True if released, False if not owner or not held
        """
        lock_key = self._make_lock_key(name, LockType.EXCLUSIVE)
        result = self._release_script(keys=[lock_key], args=[self._owner_id])

        if result == 1:
            with self._local_lock:
                self._held_locks.pop(lock_key, None)
            return True
        return False

    def renew_exclusive(self, name: str, ttl: int | None = None) -> bool:
        """Renew an exclusive lock's TTL.

        Parameters
        ----------
        name : str
            Name of the resource
        ttl : int | None
            New TTL in seconds

        Returns
        -------
        bool
            True if renewed, False if not owner
        """
        lock_key = self._make_lock_key(name, LockType.EXCLUSIVE)
        ttl = ttl or self._default_ttl
        result = self._renew_script(keys=[lock_key], args=[self._owner_id, ttl])
        return result == 1

    @contextmanager
    def exclusive_lock(
        self, name: str, ttl: int | None = None, timeout: float = 10.0
    ) -> Generator[LockInfo | None, None, None]:
        """Context manager for exclusive locks.

        Parameters
        ----------
        name : str
            Name of the resource
        ttl : int | None
            Lock TTL in seconds
        timeout : float
            Maximum time to wait for lock

        Yields
        ------
        LockInfo | None
            Lock info if acquired

        Example
        -------
        >>> with manager.exclusive_lock("resource") as lock:
        ...     if lock:
        ...         process()
        """
        lock = self.acquire_exclusive(name, ttl, timeout)
        try:
            yield lock
        finally:
            if lock:
                self.release_exclusive(name)

    def acquire_semaphore(
        self, name: str, max_count: int, ttl: int | None = None, timeout: float = 10.0, blocking: bool = True
    ) -> str | None:
        """Acquire a slot in a counting semaphore.

        Parameters
        ----------
        name : str
            Semaphore name
        max_count : int
            Maximum concurrent holders
        ttl : int | None
            Slot TTL in seconds
        timeout : float
            Maximum wait time
        blocking : bool
            Whether to block until acquired

        Returns
        -------
        str | None
            Slot ID if acquired, None if failed
        """
        sem_key = f"semaphore:{name}"
        ttl = ttl or self._default_ttl
        slot_id = f"{self._owner_id}:{uuid.uuid4().hex[:8]}"
        start = time.time()

        while True:
            result = self._semaphore_script(keys=[sem_key], args=[slot_id, max_count, ttl])

            if result == 1:
                return slot_id

            if not blocking:
                return None

            if time.time() - start >= timeout:
                return None

            time.sleep(self._retry_interval)

    def release_semaphore(self, name: str, slot_id: str) -> bool:
        """Release a semaphore slot.

        Parameters
        ----------
        name : str
            Semaphore name
        slot_id : str
            Slot ID from acquire_semaphore

        Returns
        -------
        bool
            True if released
        """
        sem_key = f"semaphore:{name}"
        removed = self._redis.srem(sem_key, slot_id)
        return removed > 0

    @contextmanager
    def semaphore(
        self, name: str, max_count: int, ttl: int | None = None, timeout: float = 10.0
    ) -> Generator[str | None, None, None]:
        """Context manager for semaphore slots.

        Parameters
        ----------
        name : str
            Semaphore name
        max_count : int
            Maximum concurrent holders
        ttl : int | None
            Slot TTL
        timeout : float
            Maximum wait time

        Yields
        ------
        str | None
            Slot ID if acquired
        """
        slot_id = self.acquire_semaphore(name, max_count, ttl, timeout)
        try:
            yield slot_id
        finally:
            if slot_id:
                self.release_semaphore(name, slot_id)

    def create_barrier(self, name: str, count: int, ttl: int = 60) -> str:
        """Create a distributed barrier.

        Parameters
        ----------
        name : str
            Barrier name
        count : int
            Number of participants required
        ttl : int
            Barrier TTL in seconds

        Returns
        -------
        str
            Barrier key
        """
        barrier_key = f"barrier:{name}"
        self._redis.hset(barrier_key, mapping={"required": str(count), "released": "0"})
        self._redis.expire(barrier_key, ttl)
        return barrier_key

    def arrive_at_barrier(self, name: str, participant_id: str | None = None) -> BarrierState:
        """Arrive at a barrier and wait for release.

        Parameters
        ----------
        name : str
            Barrier name
        participant_id : str | None
            Optional participant ID

        Returns
        -------
        BarrierState
            Current barrier state
        """
        barrier_key = f"barrier:{name}"
        participants_key = f"{barrier_key}:participants"
        participant_id = participant_id or self._owner_id

        # Add participant
        self._redis.sadd(participants_key, participant_id)

        # Get state
        data = self._redis.hgetall(barrier_key)
        participants = self._redis.smembers(participants_key)

        required = int(data.get(b"required", data.get("required", 0)))
        released = data.get(b"released", data.get("released", b"0"))
        if isinstance(released, bytes):
            released = released.decode()
        released_bool = released == "1"

        current = len(participants)

        # Check if barrier should be released
        if current >= required and not released_bool:
            self._redis.hset(barrier_key, "released", "1")
            released_bool = True

        # Decode participant IDs
        decoded_participants = [p.decode() if isinstance(p, bytes) else p for p in participants]

        return BarrierState(
            barrier_key=barrier_key,
            required_count=required,
            current_count=current,
            released=released_bool,
            participants=decoded_participants,
        )

    def wait_at_barrier(
        self, name: str, participant_id: str | None = None, timeout: float = 30.0, poll_interval: float = 0.1
    ) -> BarrierState:
        """Wait at barrier until released.

        Parameters
        ----------
        name : str
            Barrier name
        participant_id : str | None
            Optional participant ID
        timeout : float
            Maximum wait time
        poll_interval : float
            Polling interval

        Returns
        -------
        BarrierState
            Final barrier state
        """
        participant_id = participant_id or self._owner_id
        start = time.time()

        # Initial arrival
        state = self.arrive_at_barrier(name, participant_id)

        while not state.released:
            if time.time() - start >= timeout:
                break
            time.sleep(poll_interval)
            state = self.arrive_at_barrier(name, participant_id)

        return state

    def delete_barrier(self, name: str) -> None:
        """Delete a barrier and its participants.

        Parameters
        ----------
        name : str
            Barrier name
        """
        barrier_key = f"barrier:{name}"
        participants_key = f"{barrier_key}:participants"
        self._redis.delete(barrier_key, participants_key)

    def acquire_read_lock(self, name: str, ttl: int | None = None, timeout: float = 10.0) -> LockInfo | None:
        """Acquire a read lock (multiple readers allowed).

        Parameters
        ----------
        name : str
            Resource name
        ttl : int | None
            Lock TTL
        timeout : float
            Maximum wait time

        Returns
        -------
        LockInfo | None
            Lock info if acquired
        """
        read_key = self._make_lock_key(name, LockType.READ)
        write_key = self._make_lock_key(name, LockType.WRITE)
        ttl = ttl or self._default_ttl
        start = time.time()

        while True:
            # Check no write lock exists
            if not self._redis.exists(write_key):
                # Add to readers set
                reader_id = f"{self._owner_id}:{uuid.uuid4().hex[:8]}"
                self._redis.sadd(read_key, reader_id)
                self._redis.expire(read_key, ttl)

                lock_info = LockInfo(
                    lock_key=f"{read_key}:{reader_id}",
                    owner_id=reader_id,
                    lock_type=LockType.READ,
                    acquired_at=time.time(),
                    ttl=ttl,
                )
                with self._local_lock:
                    self._held_locks[lock_info.lock_key] = lock_info
                return lock_info

            if time.time() - start >= timeout:
                return None

            time.sleep(self._retry_interval)

    def release_read_lock(self, name: str, reader_id: str) -> bool:
        """Release a read lock.

        Parameters
        ----------
        name : str
            Resource name
        reader_id : str
            Reader ID from lock info

        Returns
        -------
        bool
            True if released
        """
        read_key = self._make_lock_key(name, LockType.READ)
        removed = self._redis.srem(read_key, reader_id)

        if removed > 0:
            lock_key = f"{read_key}:{reader_id}"
            with self._local_lock:
                self._held_locks.pop(lock_key, None)
            return True
        return False

    def acquire_write_lock(self, name: str, ttl: int | None = None, timeout: float = 10.0) -> LockInfo | None:
        """Acquire a write lock (exclusive, waits for readers).

        Parameters
        ----------
        name : str
            Resource name
        ttl : int | None
            Lock TTL
        timeout : float
            Maximum wait time

        Returns
        -------
        LockInfo | None
            Lock info if acquired
        """
        read_key = self._make_lock_key(name, LockType.READ)
        write_key = self._make_lock_key(name, LockType.WRITE)
        ttl = ttl or self._default_ttl
        start = time.time()

        while True:
            # Check no readers and no other writer
            readers = self._redis.scard(read_key)
            writer_exists = self._redis.exists(write_key)

            if readers == 0 and not writer_exists:
                acquired_at = time.time()
                result = self._acquire_script(keys=[write_key], args=[self._owner_id, ttl, str(acquired_at)])

                if result == 1:
                    lock_info = LockInfo(
                        lock_key=write_key,
                        owner_id=self._owner_id,
                        lock_type=LockType.WRITE,
                        acquired_at=acquired_at,
                        ttl=ttl,
                    )
                    with self._local_lock:
                        self._held_locks[write_key] = lock_info
                    return lock_info

            if time.time() - start >= timeout:
                return None

            time.sleep(self._retry_interval)

    def release_write_lock(self, name: str) -> bool:
        """Release a write lock.

        Parameters
        ----------
        name : str
            Resource name

        Returns
        -------
        bool
            True if released
        """
        write_key = self._make_lock_key(name, LockType.WRITE)
        result = self._release_script(keys=[write_key], args=[self._owner_id])

        if result == 1:
            with self._local_lock:
                self._held_locks.pop(write_key, None)
            return True
        return False

    @contextmanager
    def read_lock(
        self, name: str, ttl: int | None = None, timeout: float = 10.0
    ) -> Generator[LockInfo | None, None, None]:
        """Context manager for read locks.

        Parameters
        ----------
        name : str
            Resource name
        ttl : int | None
            Lock TTL
        timeout : float
            Maximum wait time

        Yields
        ------
        LockInfo | None
            Lock info if acquired
        """
        lock = self.acquire_read_lock(name, ttl, timeout)
        try:
            yield lock
        finally:
            if lock:
                self.release_read_lock(name, lock.owner_id)

    @contextmanager
    def write_lock(
        self, name: str, ttl: int | None = None, timeout: float = 10.0
    ) -> Generator[LockInfo | None, None, None]:
        """Context manager for write locks.

        Parameters
        ----------
        name : str
            Resource name
        ttl : int | None
            Lock TTL
        timeout : float
            Maximum wait time

        Yields
        ------
        LockInfo | None
            Lock info if acquired
        """
        lock = self.acquire_write_lock(name, ttl, timeout)
        try:
            yield lock
        finally:
            if lock:
                self.release_write_lock(name)

    def get_lock_info(self, name: str, lock_type: LockType) -> dict[str, Any] | None:
        """Get information about a lock.

        Parameters
        ----------
        name : str
            Resource name
        lock_type : LockType
            Type of lock

        Returns
        -------
        dict[str, Any] | None
            Lock information or None if not held
        """
        lock_key = self._make_lock_key(name, lock_type)
        data = self._redis.hgetall(lock_key)

        if not data:
            return None

        return {
            k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v
            for k, v in data.items()
        }

    def is_locked(self, name: str, lock_type: LockType = LockType.EXCLUSIVE) -> bool:
        """Check if a resource is locked.

        Parameters
        ----------
        name : str
            Resource name
        lock_type : LockType
            Type of lock to check

        Returns
        -------
        bool
            True if locked
        """
        lock_key = self._make_lock_key(name, lock_type)
        return bool(self._redis.exists(lock_key))

    def force_release(self, name: str, lock_type: LockType = LockType.EXCLUSIVE) -> bool:
        """Force release a lock (admin operation).

        Parameters
        ----------
        name : str
            Resource name
        lock_type : LockType
            Type of lock

        Returns
        -------
        bool
            True if lock was deleted
        """
        lock_key = self._make_lock_key(name, lock_type)
        deleted = self._redis.delete(lock_key)
        return deleted > 0

    def release_all_held(self) -> int:
        """Release all locks held by this manager instance.

        Returns
        -------
        int
            Number of locks released
        """
        released = 0
        with self._local_lock:
            for lock_key, lock_info in list(self._held_locks.items()):
                if lock_info.lock_type == LockType.EXCLUSIVE:
                    name = lock_key.replace(f"lock:{LockType.EXCLUSIVE.value}:", "")
                    if self.release_exclusive(name):
                        released += 1
                elif lock_info.lock_type == LockType.WRITE:
                    name = lock_key.replace(f"lock:{LockType.WRITE.value}:", "")
                    if self.release_write_lock(name):
                        released += 1
                elif lock_info.lock_type == LockType.READ:
                    parts = lock_key.split(":")
                    name = parts[2]
                    reader_id = lock_info.owner_id
                    if self.release_read_lock(name, reader_id):
                        released += 1
        return released
