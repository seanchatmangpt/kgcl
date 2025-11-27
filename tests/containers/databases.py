"""Database container fixtures for PostgreSQL and Redis.

Provides container configurations for:
- PostgreSQL: Lockchain persistence, audit trails, workflow state
- Redis: Caching, distributed locks, rate limiting
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

if TYPE_CHECKING:
    from collections.abc import Generator

# PostgreSQL schema for Lockchain persistence
LOCKCHAIN_SCHEMA = """
-- Tick receipts for cryptographic provenance
CREATE TABLE IF NOT EXISTS tick_receipts (
    id SERIAL PRIMARY KEY,
    tick_number INTEGER NOT NULL,
    state_hash_before VARCHAR(64) NOT NULL,
    state_hash_after VARCHAR(64) NOT NULL,
    rules_fired JSONB DEFAULT '[]',
    triples_added INTEGER DEFAULT 0,
    triples_removed INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    converged BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'
);

-- Index for efficient chain traversal
CREATE INDEX IF NOT EXISTS idx_tick_receipts_tick ON tick_receipts(tick_number);

-- Workflow execution audit log
CREATE TABLE IF NOT EXISTS workflow_audit (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(255) NOT NULL,
    pattern_id INTEGER NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    task_id VARCHAR(255),
    token_state JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Index for workflow queries
CREATE INDEX IF NOT EXISTS idx_workflow_audit_workflow ON workflow_audit(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_audit_pattern ON workflow_audit(pattern_id);

-- Hook execution receipts
CREATE TABLE IF NOT EXISTS hook_receipts (
    id SERIAL PRIMARY KEY,
    hook_id VARCHAR(255) NOT NULL,
    phase VARCHAR(50) NOT NULL,
    condition_matched BOOLEAN NOT NULL,
    action_taken VARCHAR(50),
    duration_ms FLOAT,
    error TEXT,
    triples_affected INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Index for hook analysis
CREATE INDEX IF NOT EXISTS idx_hook_receipts_hook ON hook_receipts(hook_id);
CREATE INDEX IF NOT EXISTS idx_hook_receipts_phase ON hook_receipts(phase);
"""


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """Session-scoped PostgreSQL container for Lockchain persistence.

    Provides a PostgreSQL 15 Alpine instance with pre-created schema
    for tick receipts, workflow audit, and hook receipts.

    Yields
    ------
    PostgresContainer
        Running PostgreSQL container with initialized schema.

    Examples
    --------
    >>> def test_lockchain_persistence(postgres_container):
    ...     conn_url = postgres_container.get_connection_url()
    ...     # Use connection URL for database operations
    """
    with PostgresContainer(
        image="postgres:15-alpine",
        username="kgcl",
        password="kgcl_test_pass",
        dbname="kgcl_test",
    ) as postgres:
        # Initialize schema
        _init_postgres_schema(postgres)
        yield postgres


def _init_postgres_schema(container: PostgresContainer) -> None:
    """Initialize PostgreSQL schema for KGCL.

    Parameters
    ----------
    container : PostgresContainer
        Running PostgreSQL container.
    """
    import psycopg

    conn_url = container.get_connection_url()
    # Convert SQLAlchemy URL to psycopg format
    psycopg_url = conn_url.replace("postgresql+psycopg2://", "postgresql://")

    with psycopg.connect(psycopg_url) as conn:
        with conn.cursor() as cur:
            cur.execute(LOCKCHAIN_SCHEMA)
        conn.commit()


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer, None, None]:
    """Session-scoped Redis container for caching and distributed locks.

    Provides a Redis 7 Alpine instance for:
    - Query result caching
    - Distributed lock management
    - Rate limiting
    - State-based pattern triggers

    Yields
    ------
    RedisContainer
        Running Redis container.

    Examples
    --------
    >>> def test_distributed_lock(redis_container):
    ...     host = redis_container.get_container_host_ip()
    ...     port = redis_container.get_exposed_port(6379)
    ...     # Use Redis for locking
    """
    with RedisContainer(image="redis:7-alpine") as redis:
        yield redis


@pytest.fixture
def postgres_connection(postgres_container: PostgresContainer) -> Generator[Any, None, None]:
    """Function-scoped PostgreSQL connection with automatic cleanup.

    Creates a fresh connection for each test and rolls back any
    uncommitted transactions on teardown.

    Parameters
    ----------
    postgres_container : PostgresContainer
        Session-scoped PostgreSQL container.

    Yields
    ------
    psycopg.Connection
        Active database connection.
    """
    import psycopg

    conn_url = postgres_container.get_connection_url()
    psycopg_url = conn_url.replace("postgresql+psycopg2://", "postgresql://")

    with psycopg.connect(psycopg_url) as conn:
        yield conn
        conn.rollback()  # Ensure cleanup


@pytest.fixture
def redis_client(redis_container: RedisContainer) -> Generator[Any, None, None]:
    """Function-scoped Redis client with automatic flush.

    Creates a Redis client for each test and flushes the database
    on teardown to ensure test isolation.

    Parameters
    ----------
    redis_container : RedisContainer
        Session-scoped Redis container.

    Yields
    ------
    redis.Redis
        Active Redis client.
    """
    import redis

    client = redis.Redis(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
        decode_responses=True,
    )
    yield client
    client.flushdb()
    client.close()
