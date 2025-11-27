"""Testcontainers session fixtures and Docker availability checks.

This module provides the root fixtures for all container-based tests:
- Docker availability check (skips tests if Docker unavailable)
- Session-scoped container fixtures imported from submodules
- Container lifecycle management
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

# Re-export all container fixtures for easy import
from tests.containers.databases import postgres_connection, postgres_container, redis_client, redis_container
from tests.containers.message_queues import (
    cancellation_exchange,
    rabbitmq_channel,
    rabbitmq_container,
    workflow_exchange,
)
from tests.containers.network import container_network, network_name
from tests.containers.rdf_stores import FusekiContainer, OxigraphContainer

if TYPE_CHECKING:
    from collections.abc import Generator

# Make fixtures available to pytest
__all__ = [
    # RDF Stores
    "OxigraphContainer",
    "FusekiContainer",
    "oxigraph_container",
    "fuseki_container",
    # Databases
    "postgres_container",
    "postgres_connection",
    "redis_container",
    "redis_client",
    # Message Queues
    "rabbitmq_container",
    "rabbitmq_channel",
    "workflow_exchange",
    "cancellation_exchange",
    # Network
    "container_network",
    "network_name",
]


def _is_docker_available() -> bool:
    """Check if Docker is available and running.

    Returns
    -------
    bool
        True if Docker daemon is accessible, False otherwise.
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


# Check Docker availability at module load
DOCKER_AVAILABLE = _is_docker_available()


@pytest.fixture(scope="module")
def oxigraph_container() -> Generator[OxigraphContainer, None, None]:
    """Module-scoped Oxigraph Server container.

    Provides a clean RDF store for each test module.
    Use for tests requiring a fresh SPARQL endpoint.

    Yields
    ------
    OxigraphContainer
        Running Oxigraph Server instance.
    """
    if not DOCKER_AVAILABLE:
        pytest.skip("Docker not available")

    with OxigraphContainer() as container:
        yield container


@pytest.fixture(scope="module")
def fuseki_container() -> Generator[FusekiContainer, None, None]:
    """Module-scoped Fuseki SPARQL container.

    Provides a Fuseki instance for SPARQL 1.1 compliance testing.
    Use for tests requiring full SPARQL 1.1 support.

    Yields
    ------
    FusekiContainer
        Running Fuseki instance.
    """
    if not DOCKER_AVAILABLE:
        pytest.skip("Docker not available")

    with FusekiContainer(dataset_name="kgcl_test") as container:
        yield container


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip container tests if Docker is not available.

    This hook runs during test collection and adds skip markers
    to any test marked with container-related markers.

    Parameters
    ----------
    config : pytest.Config
        Pytest configuration object.
    items : list[pytest.Item]
        List of collected test items.
    """
    if DOCKER_AVAILABLE:
        return

    skip_marker = pytest.mark.skip(reason="Docker not available")
    container_markers = {
        "container",
        "chaos",
        "postgres",
        "redis",
        "rabbitmq",
        "fuseki",
        "oxigraph_server",
        "multi_engine",
    }

    for item in items:
        item_markers = {marker.name for marker in item.iter_markers()}
        if item_markers & container_markers:
            item.add_marker(skip_marker)
