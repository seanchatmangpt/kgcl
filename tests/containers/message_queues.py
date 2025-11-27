"""Message queue container fixtures for RabbitMQ.

Provides container configurations for event-driven workflow coordination,
cross-engine communication, and asynchronous pattern execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from testcontainers.rabbitmq import RabbitMqContainer

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(scope="session")
def rabbitmq_container() -> Generator[RabbitMqContainer, None, None]:
    """Session-scoped RabbitMQ container for event-driven coordination.

    Provides a RabbitMQ 3.12 Management Alpine instance with:
    - AMQP protocol on port 5672
    - Management UI on port 15672
    - Default guest/guest credentials

    Yields
    ------
    RabbitMqContainer
        Running RabbitMQ container.

    Examples
    --------
    >>> def test_event_coordination(rabbitmq_container):
    ...     amqp_url = rabbitmq_container.get_amqp_url()
    ...     # Use AMQP URL for message publishing
    """
    with RabbitMqContainer(image="rabbitmq:3.12-management-alpine") as rabbitmq:
        yield rabbitmq


@pytest.fixture
def rabbitmq_channel(rabbitmq_container: RabbitMqContainer) -> Generator[Any, None, None]:
    """Function-scoped RabbitMQ channel with automatic cleanup.

    Creates a fresh channel for each test and closes it on teardown.
    Queues created during tests are automatically deleted.

    Parameters
    ----------
    rabbitmq_container : RabbitMqContainer
        Session-scoped RabbitMQ container.

    Yields
    ------
    pika.channel.Channel
        Active AMQP channel.
    """
    import pika

    # Get connection parameters from container
    host = rabbitmq_container.get_container_host_ip()
    port = int(rabbitmq_container.get_exposed_port(5672))

    # Create connection and channel
    credentials = pika.PlainCredentials("guest", "guest")
    parameters = pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials,
    )
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    yield channel

    # Cleanup
    channel.close()
    connection.close()


@pytest.fixture
def workflow_exchange(rabbitmq_channel: Any) -> str:
    """Create a workflow events exchange for testing.

    Creates a fanout exchange for broadcasting workflow events
    (tick completion, cancellation, state changes).

    Parameters
    ----------
    rabbitmq_channel : pika.channel.Channel
        Active AMQP channel.

    Returns
    -------
    str
        Name of the created exchange.
    """
    exchange_name = "kgcl.workflow.events"
    rabbitmq_channel.exchange_declare(
        exchange=exchange_name,
        exchange_type="fanout",
        durable=False,
        auto_delete=True,
    )
    return exchange_name


@pytest.fixture
def cancellation_exchange(rabbitmq_channel: Any) -> str:
    """Create a cancellation events exchange for testing.

    Creates a topic exchange for routing cancellation events
    by scope (case, region, activity).

    Parameters
    ----------
    rabbitmq_channel : pika.channel.Channel
        Active AMQP channel.

    Returns
    -------
    str
        Name of the created exchange.
    """
    exchange_name = "kgcl.cancellation"
    rabbitmq_channel.exchange_declare(
        exchange=exchange_name,
        exchange_type="topic",
        durable=False,
        auto_delete=True,
    )
    return exchange_name


def create_test_queue(channel: Any, exchange: str, routing_key: str = "#") -> str:
    """Create a temporary queue bound to an exchange.

    Parameters
    ----------
    channel : pika.channel.Channel
        Active AMQP channel.
    exchange : str
        Exchange name to bind to.
    routing_key : str
        Routing key pattern. Defaults to "#" (all messages).

    Returns
    -------
    str
        Name of the created queue.
    """
    result = channel.queue_declare(queue="", exclusive=True, auto_delete=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange=exchange, queue=queue_name, routing_key=routing_key)
    return queue_name
