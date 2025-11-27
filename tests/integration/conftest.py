"""Integration test fixtures.

This module provides fixtures specific to integration tests,
building on the container fixtures from tests/containers/.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

# Import container fixtures for use in integration tests
from tests.containers.conftest import (
    cancellation_exchange,
    fuseki_container,
    oxigraph_container,
    postgres_connection,
    postgres_container,
    rabbitmq_channel,
    rabbitmq_container,
    redis_client,
    redis_container,
    workflow_exchange,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from tests.containers.rdf_stores import OxigraphContainer

# Re-export all container fixtures
__all__ = [
    "oxigraph_container",
    "fuseki_container",
    "postgres_container",
    "postgres_connection",
    "redis_container",
    "redis_client",
    "rabbitmq_container",
    "rabbitmq_channel",
    "workflow_exchange",
    "cancellation_exchange",
    "remote_store_adapter",
    "workflow_audit_logger",
]


@pytest.fixture
def remote_store_adapter(oxigraph_container: OxigraphContainer) -> Generator[Any, None, None]:
    """Create a RemoteStoreAdapter connected to Oxigraph container.

    Parameters
    ----------
    oxigraph_container : OxigraphContainer
        Running Oxigraph Server instance.

    Yields
    ------
    RemoteStoreAdapter
        Adapter implementing RDFStore protocol for remote SPARQL endpoint.
    """
    from kgcl.hybrid.adapters.remote_store_adapter import RemoteStoreAdapter

    adapter = RemoteStoreAdapter(
        query_endpoint=oxigraph_container.get_sparql_endpoint(),
        update_endpoint=oxigraph_container.get_update_endpoint(),
    )
    yield adapter
    # Clear store after test
    adapter.clear()


@pytest.fixture
def workflow_audit_logger(postgres_connection: Any) -> Generator[Any, None, None]:
    """Create a workflow audit logger connected to PostgreSQL.

    Parameters
    ----------
    postgres_connection : psycopg.Connection
        Active PostgreSQL connection.

    Yields
    ------
    WorkflowAuditLogger
        Logger for workflow events.
    """
    from kgcl.hybrid.adapters.postgres_audit import WorkflowAuditLogger

    logger = WorkflowAuditLogger(postgres_connection)
    yield logger
