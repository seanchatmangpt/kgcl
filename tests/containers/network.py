"""Docker network configuration for container communication.

Provides shared network fixtures for multi-container test scenarios
where containers need to communicate directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from testcontainers.core.network import Network

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(scope="session")
def container_network() -> Generator[Network, None, None]:
    """Session-scoped Docker network for container communication.

    Creates a shared network that allows containers to communicate
    using container names as hostnames.

    Yields
    ------
    Network
        Docker network instance.

    Examples
    --------
    >>> def test_multi_container(container_network, oxigraph_container):
    ...     # Containers on same network can communicate
    ...     pass
    """
    with Network() as network:
        yield network


@pytest.fixture(scope="session")
def network_name(container_network: Network) -> str:
    """Get the name of the shared container network.

    Parameters
    ----------
    container_network : Network
        Session-scoped Docker network.

    Returns
    -------
    str
        Network name for use in container configuration.
    """
    return container_network.name
