"""Chaos engineering test fixtures.

Provides fixtures for failure injection and recovery testing,
including ToxiProxy integration for network fault simulation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

# Import container fixtures
from tests.containers.conftest import oxigraph_container, postgres_container, rabbitmq_container, redis_container

if TYPE_CHECKING:
    from collections.abc import Generator

# Re-export container fixtures
__all__ = ["oxigraph_container", "postgres_container", "redis_container", "rabbitmq_container", "toxiproxy_client"]


@pytest.fixture(scope="session")
def toxiproxy_client() -> Generator[Any, None, None]:
    """Session-scoped ToxiProxy client for network fault injection.

    ToxiProxy allows simulating network conditions:
    - Latency injection
    - Bandwidth limiting
    - Connection timeouts
    - Connection resets

    Yields
    ------
    toxiproxy.Toxiproxy
        ToxiProxy client instance.
    """
    try:
        from toxiproxy import Toxiproxy
    except ImportError:
        pytest.skip("toxiproxy-python not installed")
        return

    # ToxiProxy runs as a sidecar container
    # For now, skip if not available
    try:
        client = Toxiproxy()
        client.proxies()  # Test connection
        yield client
    except Exception:
        pytest.skip("ToxiProxy not available")
