"""Testcontainer fixtures for external service integration.

Provides pytest fixtures for:
- HTTPBin (for HTTP client testing)
- Mock API server (for service gateway testing)
- Oxigraph SPARQL server (for RemoteStoreAdapter)
- PostgreSQL (for audit/lockchain adapters)
- Redis (for distributed lock manager)
- RabbitMQ (for event coordinator)

Usage
-----
Run container tests:
    uv run pytest tests/integration/ -v

Skip if Docker unavailable:
    Tests auto-skip when Docker is not available.

Examples
--------
>>> @pytest.mark.asyncio
... async def test_service_gateway(httpbin_container):
...     from kgcl.daemon import ServiceGateway, ServiceReference
...
...     gateway = ServiceGateway()
...     ref = ServiceReference(service_id="test", uri=f"{httpbin_container['url']}/post")
...     gateway.register(ref)
...     result = await gateway.invoke("test", "task-1", {"data": "test"})
...     assert result.status == ServiceStatus.COMPLETED
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, Generator

import pytest

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Disable Ryuk (testcontainers reaper) which can cause issues on macOS
# Containers will still be cleaned up by pytest fixture teardown
os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"


def _check_docker_available() -> bool:
    """Check if Docker is available for testcontainers."""
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


# Skip all container tests if Docker unavailable
DOCKER_AVAILABLE = _check_docker_available()
pytestmark = pytest.mark.skipif(not DOCKER_AVAILABLE, reason="Docker not available")


@pytest.fixture(scope="session")
def httpbin_container() -> Generator[dict[str, Any], None, None]:
    """HTTPBin container for testing HTTP clients.

    Provides a standard HTTP testing service with various endpoints:
    - /post: Echo POST request data
    - /get: Echo GET request parameters
    - /status/:code: Return specific status code
    - /delay/:seconds: Delay response
    - /headers: Echo request headers

    Yields
    ------
    dict[str, Any]
        Dictionary with connection details:
        - url: Base URL (http://host:port)
        - host: Hostname
        - port: Port number

    Examples
    --------
    >>> def test_http_client(httpbin_container):
    ...     import aiohttp
    ...
    ...     async with aiohttp.ClientSession() as session:
    ...         async with session.post(f"{httpbin_container['url']}/post", json={"test": 1}) as resp:
    ...             assert resp.status == 200
    """
    import time

    from testcontainers.core.container import DockerContainer

    container = DockerContainer("kennethreitz/httpbin:latest")
    container.with_exposed_ports(80)
    container.start()

    # Wait for port mapping to be available with retry
    deadline = time.time() + 60
    port = None
    host = None
    while time.time() < deadline:
        try:
            host = container.get_container_host_ip()
            port = container.get_exposed_port(80)
            if port:
                break
        except (ConnectionError, Exception):
            pass
        time.sleep(1)

    if port is None or host is None:
        raise TimeoutError("HTTPBin container port mapping not available in 60 seconds")

    base_url = f"http://{host}:{port}"

    # Wait for HTTPBin to respond to requests
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            import urllib.request

            urllib.request.urlopen(f"{base_url}/get", timeout=5)
            break
        except Exception:
            time.sleep(1)
    else:
        raise TimeoutError("HTTPBin container did not become ready in 60 seconds")

    details = {"url": base_url, "host": host, "port": int(port)}

    logger.info(f"HTTPBin container started: {details['url']}")

    yield details

    container.stop()
    logger.info("HTTPBin container stopped")


@pytest.fixture(scope="session")
def mock_api_container(httpbin_container: dict[str, Any]) -> Generator[dict[str, Any], None, None]:
    """Mock API container using HTTPBin as backend.

    Provides endpoint aliases that map to HTTPBin functionality:
    - task_endpoint: POST endpoint (echoes JSON)
    - validate_endpoint: POST endpoint (echoes JSON)
    - slow_endpoint: 3 second delay endpoint
    - error_endpoint: 500 error endpoint
    - echo_endpoint: POST endpoint (echoes JSON)

    Uses HTTPBin for all functionality since it's more reliable.

    Yields
    ------
    dict[str, Any]
        Dictionary with endpoint URLs

    Examples
    --------
    >>> def test_mock_api(mock_api_container):
    ...     import requests
    ...
    ...     resp = requests.post(mock_api_container["task_endpoint"], json={"task_id": "123"})
    ...     assert resp.json()["json"]["task_id"] == "123"
    """
    base_url = httpbin_container["url"]

    details = {
        "base_url": base_url,
        "task_endpoint": f"{base_url}/post",
        "validate_endpoint": f"{base_url}/post",
        "slow_endpoint": f"{base_url}/delay/3",
        "error_endpoint": f"{base_url}/status/500",
        "echo_endpoint": f"{base_url}/post",
        "host": httpbin_container["host"],
        "port": httpbin_container["port"],
    }

    logger.info(f"Mock API container (HTTPBin) endpoints configured: {details['base_url']}")

    yield details


@pytest.fixture(scope="session")
def oxigraph_container() -> Generator[dict[str, str], None, None]:
    """Oxigraph SPARQL server container.

    Provides endpoints for:
    - query: SPARQL query endpoint
    - update: SPARQL update endpoint
    - store: Graph Store Protocol endpoint

    Yields
    ------
    dict[str, str]
        Dictionary with query, update, and store endpoint URLs.

    Examples
    --------
    >>> def test_sparql(oxigraph_container):
    ...     adapter = RemoteStoreAdapter(
    ...         query_endpoint=oxigraph_container["query"], update_endpoint=oxigraph_container["update"]
    ...     )
    """
    import time

    from testcontainers.core.container import DockerContainer

    container = DockerContainer("oxigraph/oxigraph:latest")
    container.with_exposed_ports(7878)
    container.start()

    # Wait for Oxigraph to be ready (poll container logs)
    deadline = time.time() + 30
    while time.time() < deadline:
        logs = container.get_logs()
        if isinstance(logs, tuple):
            stdout, stderr = logs
            log_text = (stdout or b"").decode() + (stderr or b"").decode()
        else:
            log_text = logs.decode() if isinstance(logs, bytes) else str(logs)
        if "Listening" in log_text:
            break
        time.sleep(0.5)
    else:
        raise TimeoutError("Oxigraph container did not become ready in 30 seconds")

    host = container.get_container_host_ip()
    port = container.get_exposed_port(7878)

    endpoints = {
        "query": f"http://{host}:{port}/query",
        "update": f"http://{host}:{port}/update",
        "store": f"http://{host}:{port}/store",
    }

    logger.info(f"Oxigraph container started: {endpoints['query']}")

    yield endpoints

    container.stop()
    logger.info("Oxigraph container stopped")


@pytest.fixture(scope="session")
def postgres_container() -> Generator[dict[str, Any], None, None]:
    """PostgreSQL container for audit/lockchain adapters.

    Yields
    ------
    dict[str, Any]
        Dictionary with connection details:
        - url: Full connection URL
        - host: Hostname
        - port: Port number
        - user: Username
        - password: Password
        - database: Database name

    Examples
    --------
    >>> def test_postgres(postgres_container):
    ...     import psycopg
    ...
    ...     conn = psycopg.connect(postgres_container["url"])
    """
    from testcontainers.postgres import PostgresContainer

    container = PostgresContainer("postgres:15")
    container.start()

    # Get connection details for psycopg3 (not SQLAlchemy format)
    host = container.get_container_host_ip()
    port = container.get_exposed_port(5432)
    # Build postgresql:// URL for psycopg3 (not psycopg2 SQLAlchemy format)
    connection_url = f"postgresql://{container.username}:{container.password}@{host}:{port}/{container.dbname}"

    details = {
        "url": connection_url,
        "host": host,
        "port": port,
        "user": container.username,
        "password": container.password,
        "database": container.dbname,
    }

    logger.info(f"PostgreSQL container started: {details['host']}:{details['port']}")

    yield details

    container.stop()
    logger.info("PostgreSQL container stopped")


@pytest.fixture(scope="session")
def redis_container() -> Generator[dict[str, Any], None, None]:
    """Redis container for distributed lock manager.

    Yields
    ------
    dict[str, Any]
        Dictionary with connection details:
        - url: Redis URL (redis://host:port)
        - host: Hostname
        - port: Port number

    Examples
    --------
    >>> def test_redis(redis_container):
    ...     import redis
    ...
    ...     client = redis.from_url(redis_container["url"])
    """
    from testcontainers.redis import RedisContainer

    container = RedisContainer("redis:7")
    container.start()

    host = container.get_container_host_ip()
    port = container.get_exposed_port(6379)

    details = {"url": f"redis://{host}:{port}", "host": host, "port": int(port)}

    logger.info(f"Redis container started: {details['url']}")

    yield details

    container.stop()
    logger.info("Redis container stopped")


@pytest.fixture(scope="session")
def rabbitmq_container() -> Generator[dict[str, Any], None, None]:
    """RabbitMQ container for event coordinator.

    Yields
    ------
    dict[str, Any]
        Dictionary with connection details:
        - host: Hostname
        - port: AMQP port (5672)
        - management_port: Management UI port (15672)
        - user: Username
        - password: Password
        - url: AMQP URL

    Examples
    --------
    >>> def test_rabbitmq(rabbitmq_container):
    ...     import pika
    ...
    ...     connection = pika.BlockingConnection(
    ...         pika.ConnectionParameters(host=rabbitmq_container["host"], port=rabbitmq_container["port"])
    ...     )
    """
    import time

    from testcontainers.core.container import DockerContainer

    # Use DockerContainer directly for more control over port exposure
    container = DockerContainer("rabbitmq:3-management")
    container.with_exposed_ports(5672, 15672)
    container.start()

    # Wait for RabbitMQ to be ready (check AMQP port connectivity)
    host = container.get_container_host_ip()
    amqp_port = container.get_exposed_port(5672)

    # Wait for RabbitMQ to accept connections
    deadline = time.time() + 60  # RabbitMQ can take a while to start
    while time.time() < deadline:
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, int(amqp_port)))
            sock.close()
            if result == 0:
                # Port is open, try AMQP connection
                import pika

                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host=host, port=int(amqp_port), connection_attempts=1, retry_delay=0.5)
                )
                connection.close()
                break
        except Exception:
            time.sleep(1)
    else:
        raise TimeoutError("RabbitMQ container did not become ready in 60 seconds")

    # Management port may not be exposed with DockerContainer - try to get it
    try:
        mgmt_port = container.get_exposed_port(15672)
    except Exception:
        mgmt_port = None

    details = {
        "host": host,
        "port": int(amqp_port),
        "management_port": int(mgmt_port) if mgmt_port else None,
        "user": "guest",
        "password": "guest",
        "url": f"amqp://guest:guest@{host}:{amqp_port}/",
    }

    logger.info(f"RabbitMQ container started: {details['host']}:{details['port']}")

    yield details

    container.stop()
    logger.info("RabbitMQ container stopped")
