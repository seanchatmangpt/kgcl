"""YAWL Service Gateway - External service integration for task delegation.

This module implements YAWLServiceReference and YAWLServiceGateway patterns
for delegating task execution to external web services. Based on YAWL v5.2
architecture but adapted for KGCL's Python/RDF environment.

Architecture
------------
- ServiceReference: Immutable endpoint descriptor (URI, headers, timeout)
- ServiceInvocation: Request/response tracking with timing
- ServiceGateway: Registry + async HTTP client for service calls

Examples
--------
>>> from kgcl.daemon.service_gateway import ServiceGateway, ServiceReference
>>> gateway = ServiceGateway()
>>> ref = ServiceReference(service_id="validator", uri="http://api.example.com/validate")
>>> gateway.register(ref)
>>> result = await gateway.invoke("validator", "task-123", {"data": "payload"})
>>> result.status
<ServiceStatus.COMPLETED: 'completed'>
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from http import HTTPStatus
from typing import Any

import aiohttp

__all__ = [
    "ServiceGateway",
    "ServiceInvocation",
    "ServiceReference",
    "ServiceStatus",
]


class ServiceStatus(Enum):
    """Status of a service invocation.

    Examples
    --------
    >>> ServiceStatus.COMPLETED.value
    'completed'
    """

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class ServiceReference:
    """External service endpoint reference (YAWLServiceReference).

    Represents an external Custom Service that can receive delegated
    task execution requests. Immutable by design.

    Parameters
    ----------
    service_id : str
        Unique identifier for this service
    uri : str
        HTTP(S) endpoint URI for the service
    description : str
        Human-readable description (default: "")
    assignable : bool
        Whether tasks can be assigned to this service (default: True)
    timeout_seconds : float
        Request timeout in seconds (default: 30.0)
    headers : dict[str, str] | None
        Custom HTTP headers for requests (default: None)

    Examples
    --------
    >>> ref = ServiceReference(
    ...     service_id="validator",
    ...     uri="http://localhost:8080/api/validate",
    ...     description="Document validation service",
    ...     timeout_seconds=10.0,
    ... )
    >>> ref.assignable
    True
    """

    service_id: str
    uri: str
    description: str = ""
    assignable: bool = True
    timeout_seconds: float = 30.0
    headers: dict[str, str] | None = None


@dataclass(frozen=True)
class ServiceInvocation:
    """Record of a service invocation (request + response).

    Tracks the full lifecycle of a service call including timing,
    response data, and error information.

    Parameters
    ----------
    invocation_id : str
        Unique identifier for this invocation
    service_id : str
        ID of the invoked service
    task_id : str
        ID of the task being processed
    payload : dict[str, Any]
        Request payload sent to service
    timestamp : float
        Unix timestamp when invocation started
    status : ServiceStatus
        Current status (default: PENDING)
    response : dict[str, Any] | None
        Response data if successful (default: None)
    error : str | None
        Error message if failed (default: None)
    duration_ms : float | None
        Total duration in milliseconds (default: None)

    Examples
    --------
    >>> inv = ServiceInvocation(
    ...     invocation_id="inv-001",
    ...     service_id="validator",
    ...     task_id="task-123",
    ...     payload={"doc": "content"},
    ...     timestamp=time.time(),
    ...     status=ServiceStatus.COMPLETED,
    ...     response={"valid": True},
    ...     duration_ms=150.5,
    ... )
    """

    invocation_id: str
    service_id: str
    task_id: str
    payload: dict[str, Any]
    timestamp: float
    status: ServiceStatus = ServiceStatus.PENDING
    response: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: float | None = None


@dataclass
class ServiceGateway:
    """Gateway for external service registration and invocation (YAWLServiceGateway).

    Manages a registry of external service references and provides
    async HTTP client for invoking services with task payloads.

    Attributes
    ----------
    services : dict[str, ServiceReference]
        Registered services by ID
    invocations : list[ServiceInvocation]
        History of all invocations

    Examples
    --------
    >>> gateway = ServiceGateway()
    >>> ref = ServiceReference(service_id="api", uri="http://localhost:8080")
    >>> gateway.register(ref)
    >>> gateway.get("api").uri
    'http://localhost:8080'
    """

    _services: dict[str, ServiceReference] = field(default_factory=dict)
    _invocations: list[ServiceInvocation] = field(default_factory=list)

    @property
    def services(self) -> dict[str, ServiceReference]:
        """Registered services by ID (read-only view)."""
        return dict(self._services)

    @property
    def invocations(self) -> list[ServiceInvocation]:
        """Invocation history (read-only view)."""
        return list(self._invocations)

    def register(self, ref: ServiceReference) -> None:
        """Register an external service.

        Parameters
        ----------
        ref : ServiceReference
            Service reference to register

        Raises
        ------
        ValueError
            If service_id is already registered

        Examples
        --------
        >>> gateway = ServiceGateway()
        >>> ref = ServiceReference(service_id="svc", uri="http://example.com")
        >>> gateway.register(ref)
        >>> "svc" in gateway.services
        True
        """
        if ref.service_id in self._services:
            msg = f"Service '{ref.service_id}' already registered"
            raise ValueError(msg)
        self._services[ref.service_id] = ref

    def unregister(self, service_id: str) -> None:
        """Unregister an external service.

        Parameters
        ----------
        service_id : str
            ID of service to unregister

        Raises
        ------
        KeyError
            If service_id is not registered

        Examples
        --------
        >>> gateway.unregister("svc")
        >>> "svc" in gateway.services
        False
        """
        if service_id not in self._services:
            msg = f"Service '{service_id}' not registered"
            raise KeyError(msg)
        del self._services[service_id]

    def get(self, service_id: str) -> ServiceReference | None:
        """Get service reference by ID.

        Parameters
        ----------
        service_id : str
            ID of service to retrieve

        Returns
        -------
        ServiceReference | None
            Service reference or None if not found

        Examples
        --------
        >>> ref = gateway.get("svc")
        >>> ref is not None
        True
        """
        return self._services.get(service_id)

    def list_assignable(self) -> list[ServiceReference]:
        """List services that can be assigned tasks.

        Returns
        -------
        list[ServiceReference]
            Services with assignable=True

        Examples
        --------
        >>> assignable = gateway.list_assignable()
        >>> all(ref.assignable for ref in assignable)
        True
        """
        return [ref for ref in self._services.values() if ref.assignable]

    async def invoke(
        self,
        service_id: str,
        task_id: str,
        payload: dict[str, Any],
    ) -> ServiceInvocation:
        """Invoke an external service with task payload.

        Makes an async HTTP POST request to the service endpoint
        with JSON payload. Records invocation in history.

        Parameters
        ----------
        service_id : str
            ID of registered service to invoke
        task_id : str
            ID of task being processed
        payload : dict[str, Any]
            JSON-serializable request payload

        Returns
        -------
        ServiceInvocation
            Invocation record with response or error

        Raises
        ------
        KeyError
            If service_id is not registered

        Examples
        --------
        >>> result = await gateway.invoke("validator", "task-1", {"data": "x"})
        >>> result.status
        <ServiceStatus.COMPLETED: 'completed'>
        """
        ref = self._services.get(service_id)
        if ref is None:
            msg = f"Service '{service_id}' not registered"
            raise KeyError(msg)

        invocation_id = f"inv-{uuid.uuid4()}"
        start_time = time.time()
        timestamp = start_time

        # Prepare headers
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if ref.headers:
            headers.update(ref.headers)

        # Make HTTP request
        status = ServiceStatus.PENDING
        response_data: dict[str, Any] | None = None
        error: str | None = None

        try:
            timeout = aiohttp.ClientTimeout(total=ref.timeout_seconds)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(ref.uri, json=payload, headers=headers) as resp:
                    if resp.status == HTTPStatus.OK:
                        status = ServiceStatus.COMPLETED
                        response_data = await resp.json()
                    else:
                        status = ServiceStatus.FAILED
                        error_text = await resp.text()
                        error = f"HTTP {resp.status}: {error_text[:200]}"
        except TimeoutError:
            status = ServiceStatus.TIMEOUT
            error = f"Request timed out after {ref.timeout_seconds}s"
        except Exception as e:
            status = ServiceStatus.FAILED
            error = str(e)

        duration_ms = (time.time() - start_time) * 1000

        invocation = ServiceInvocation(
            invocation_id=invocation_id,
            service_id=service_id,
            task_id=task_id,
            payload=payload,
            timestamp=timestamp,
            status=status,
            response=response_data,
            error=error,
            duration_ms=duration_ms,
        )

        self._invocations.append(invocation)
        return invocation

    def get_invocations(
        self,
        *,
        service_id: str | None = None,
        task_id: str | None = None,
        status: ServiceStatus | None = None,
    ) -> list[ServiceInvocation]:
        """Query invocation history with filters.

        Parameters
        ----------
        service_id : str | None
            Filter by service ID
        task_id : str | None
            Filter by task ID
        status : ServiceStatus | None
            Filter by status

        Returns
        -------
        list[ServiceInvocation]
            Matching invocations

        Examples
        --------
        >>> failed = gateway.get_invocations(status=ServiceStatus.FAILED)
        >>> len(failed)
        1
        """
        result = self._invocations

        if service_id is not None:
            result = [inv for inv in result if inv.service_id == service_id]

        if task_id is not None:
            result = [inv for inv in result if inv.task_id == task_id]

        if status is not None:
            result = [inv for inv in result if inv.status == status]

        return result

    def clear_history(self) -> None:
        """Clear all invocation history.

        Examples
        --------
        >>> gateway.clear_history()
        >>> len(gateway.invocations)
        0
        """
        self._invocations.clear()
