"""Tests for YAWL Service Gateway - External service integration.

Chicago School TDD: Test behavior through state verification.
Tests cover service registration, invocation, and error handling.
"""

from __future__ import annotations

import asyncio
import time
from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kgcl.daemon.service_gateway import (
    ServiceGateway,
    ServiceInvocation,
    ServiceReference,
    ServiceStatus,
)


class TestServiceReference:
    """Tests for ServiceReference - External service endpoint representation."""

    def test_create_with_required_fields(self) -> None:
        """Create service reference with minimal fields."""
        ref = ServiceReference(
            service_id="svc-001",
            uri="http://localhost:8080/api/task",
        )

        assert ref.service_id == "svc-001"
        assert ref.uri == "http://localhost:8080/api/task"
        assert ref.assignable is True  # default
        assert ref.description == ""  # default
        assert ref.timeout_seconds == 30.0  # default

    def test_create_with_all_fields(self) -> None:
        """Create service reference with all fields."""
        ref = ServiceReference(
            service_id="svc-002",
            uri="https://api.example.com/workflow",
            description="External workflow service",
            assignable=False,
            timeout_seconds=60.0,
            headers={"Authorization": "Bearer token"},
        )

        assert ref.service_id == "svc-002"
        assert ref.uri == "https://api.example.com/workflow"
        assert ref.description == "External workflow service"
        assert ref.assignable is False
        assert ref.timeout_seconds == 60.0
        assert ref.headers == {"Authorization": "Bearer token"}

    def test_is_frozen(self) -> None:
        """ServiceReference is immutable."""
        ref = ServiceReference(service_id="svc-001", uri="http://localhost:8080")

        with pytest.raises(AttributeError):
            ref.uri = "http://other"  # type: ignore[misc]


class TestServiceInvocation:
    """Tests for ServiceInvocation - Request/response tracking."""

    def test_create_pending_invocation(self) -> None:
        """Create invocation in pending state."""
        inv = ServiceInvocation(
            invocation_id="inv-001",
            service_id="svc-001",
            task_id="task-123",
            payload={"action": "process"},
            timestamp=1700000000.0,
        )

        assert inv.invocation_id == "inv-001"
        assert inv.service_id == "svc-001"
        assert inv.task_id == "task-123"
        assert inv.payload == {"action": "process"}
        assert inv.status == ServiceStatus.PENDING
        assert inv.response is None
        assert inv.error is None
        assert inv.duration_ms is None

    def test_create_completed_invocation(self) -> None:
        """Create completed invocation with response."""
        inv = ServiceInvocation(
            invocation_id="inv-002",
            service_id="svc-001",
            task_id="task-456",
            payload={"action": "validate"},
            timestamp=1700000000.0,
            status=ServiceStatus.COMPLETED,
            response={"valid": True, "score": 0.95},
            duration_ms=150.5,
        )

        assert inv.status == ServiceStatus.COMPLETED
        assert inv.response == {"valid": True, "score": 0.95}
        assert inv.duration_ms == 150.5

    def test_create_failed_invocation(self) -> None:
        """Create failed invocation with error."""
        inv = ServiceInvocation(
            invocation_id="inv-003",
            service_id="svc-001",
            task_id="task-789",
            payload={},
            timestamp=1700000000.0,
            status=ServiceStatus.FAILED,
            error="Connection refused",
            duration_ms=5000.0,
        )

        assert inv.status == ServiceStatus.FAILED
        assert inv.error == "Connection refused"


class TestServiceGateway:
    """Tests for ServiceGateway - Service registration and invocation."""

    def test_create_empty_gateway(self) -> None:
        """Create gateway with no services."""
        gateway = ServiceGateway()

        assert len(gateway.services) == 0
        assert len(gateway.invocations) == 0

    def test_register_service(self) -> None:
        """Register a service reference."""
        gateway = ServiceGateway()

        ref = ServiceReference(
            service_id="svc-001",
            uri="http://localhost:8080/api",
            description="Test service",
        )
        gateway.register(ref)

        assert "svc-001" in gateway.services
        assert gateway.services["svc-001"] == ref

    def test_register_duplicate_raises(self) -> None:
        """Registering duplicate service_id raises ValueError."""
        gateway = ServiceGateway()

        ref1 = ServiceReference(service_id="svc-001", uri="http://localhost:8080")
        ref2 = ServiceReference(service_id="svc-001", uri="http://localhost:9090")

        gateway.register(ref1)

        with pytest.raises(ValueError, match="already registered"):
            gateway.register(ref2)

    def test_unregister_service(self) -> None:
        """Unregister a service."""
        gateway = ServiceGateway()

        ref = ServiceReference(service_id="svc-001", uri="http://localhost:8080")
        gateway.register(ref)
        gateway.unregister("svc-001")

        assert "svc-001" not in gateway.services

    def test_unregister_nonexistent_raises(self) -> None:
        """Unregistering nonexistent service raises KeyError."""
        gateway = ServiceGateway()

        with pytest.raises(KeyError, match="not registered"):
            gateway.unregister("nonexistent")

    def test_get_service(self) -> None:
        """Get registered service by ID."""
        gateway = ServiceGateway()

        ref = ServiceReference(service_id="svc-001", uri="http://localhost:8080")
        gateway.register(ref)

        assert gateway.get("svc-001") == ref
        assert gateway.get("nonexistent") is None

    def test_list_assignable_services(self) -> None:
        """List only assignable services."""
        gateway = ServiceGateway()

        ref1 = ServiceReference(service_id="svc-001", uri="http://a", assignable=True)
        ref2 = ServiceReference(service_id="svc-002", uri="http://b", assignable=False)
        ref3 = ServiceReference(service_id="svc-003", uri="http://c", assignable=True)

        gateway.register(ref1)
        gateway.register(ref2)
        gateway.register(ref3)

        assignable = gateway.list_assignable()

        assert len(assignable) == 2
        assert ref1 in assignable
        assert ref2 not in assignable
        assert ref3 in assignable


class TestServiceGatewayInvocation:
    """Tests for ServiceGateway invocation behavior."""

    @pytest.fixture
    def gateway_with_service(self) -> ServiceGateway:
        """Create gateway with one registered service."""
        gateway = ServiceGateway()
        ref = ServiceReference(
            service_id="svc-001",
            uri="http://localhost:8080/api/task",
            timeout_seconds=5.0,
        )
        gateway.register(ref)
        return gateway

    @pytest.mark.asyncio
    async def test_invoke_success(self, gateway_with_service: ServiceGateway) -> None:
        """Successful invocation returns completed status."""
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.json = AsyncMock(return_value={"result": "success"})

        # Create proper async context manager chain
        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__.return_value = mock_response
        mock_post_cm.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_cm

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            result = await gateway_with_service.invoke(
                service_id="svc-001",
                task_id="task-123",
                payload={"action": "process"},
            )

        assert result.status == ServiceStatus.COMPLETED
        assert result.response == {"result": "success"}
        assert result.duration_ms is not None
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_invoke_http_error(self, gateway_with_service: ServiceGateway) -> None:
        """HTTP error returns failed status."""
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.INTERNAL_SERVER_ERROR
        mock_response.text = AsyncMock(return_value="Internal Server Error")

        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__.return_value = mock_response
        mock_post_cm.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_cm

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            result = await gateway_with_service.invoke(
                service_id="svc-001",
                task_id="task-456",
                payload={},
            )

        assert result.status == ServiceStatus.FAILED
        assert "500" in (result.error or "")

    @pytest.mark.asyncio
    async def test_invoke_connection_error(self, gateway_with_service: ServiceGateway) -> None:
        """Connection error returns failed status."""
        mock_session = MagicMock()
        mock_session.post.side_effect = Exception("Connection refused")

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            result = await gateway_with_service.invoke(
                service_id="svc-001",
                task_id="task-789",
                payload={},
            )

        assert result.status == ServiceStatus.FAILED
        assert "Connection refused" in (result.error or "")

    @pytest.mark.asyncio
    async def test_invoke_nonexistent_service(self) -> None:
        """Invoking nonexistent service raises KeyError."""
        gateway = ServiceGateway()

        with pytest.raises(KeyError, match="not registered"):
            await gateway.invoke(
                service_id="nonexistent",
                task_id="task-001",
                payload={},
            )

    @pytest.mark.asyncio
    async def test_invoke_records_history(self, gateway_with_service: ServiceGateway) -> None:
        """Invocation is recorded in history."""
        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.json = AsyncMock(return_value={})

        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__.return_value = mock_response
        mock_post_cm.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_cm

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            await gateway_with_service.invoke(
                service_id="svc-001",
                task_id="task-001",
                payload={},
            )
            await gateway_with_service.invoke(
                service_id="svc-001",
                task_id="task-002",
                payload={},
            )

        assert len(gateway_with_service.invocations) == 2
        assert gateway_with_service.invocations[0].task_id == "task-001"
        assert gateway_with_service.invocations[1].task_id == "task-002"

    @pytest.mark.asyncio
    async def test_invoke_with_custom_headers(self) -> None:
        """Custom headers are included in request."""
        gateway = ServiceGateway()
        ref = ServiceReference(
            service_id="svc-auth",
            uri="http://localhost:8080/api",
            headers={"Authorization": "Bearer test-token", "X-Custom": "value"},
        )
        gateway.register(ref)

        mock_response = MagicMock()
        mock_response.status = HTTPStatus.OK
        mock_response.json = AsyncMock(return_value={})

        mock_post_cm = AsyncMock()
        mock_post_cm.__aenter__.return_value = mock_response
        mock_post_cm.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_cm

        mock_session_cm = AsyncMock()
        mock_session_cm.__aenter__.return_value = mock_session
        mock_session_cm.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            await gateway.invoke(
                service_id="svc-auth",
                task_id="task-001",
                payload={},
            )

            # Verify headers were passed
            call_kwargs = mock_session.post.call_args.kwargs
            assert "headers" in call_kwargs
            assert call_kwargs["headers"]["Authorization"] == "Bearer test-token"
            assert call_kwargs["headers"]["X-Custom"] == "value"


class TestServiceGatewayHistory:
    """Tests for invocation history queries."""

    @pytest.fixture
    def gateway_with_history(self) -> ServiceGateway:
        """Create gateway with invocation history."""
        gateway = ServiceGateway()

        # Add invocations directly for testing (bypassing actual HTTP calls)
        gateway._invocations = [
            ServiceInvocation(
                invocation_id="inv-001",
                service_id="svc-001",
                task_id="task-001",
                payload={},
                timestamp=1700000000.0,
                status=ServiceStatus.COMPLETED,
                duration_ms=100.0,
            ),
            ServiceInvocation(
                invocation_id="inv-002",
                service_id="svc-002",
                task_id="task-002",
                payload={},
                timestamp=1700000001.0,
                status=ServiceStatus.FAILED,
                error="Timeout",
                duration_ms=5000.0,
            ),
            ServiceInvocation(
                invocation_id="inv-003",
                service_id="svc-001",
                task_id="task-003",
                payload={},
                timestamp=1700000002.0,
                status=ServiceStatus.COMPLETED,
                duration_ms=200.0,
            ),
        ]
        return gateway

    def test_get_invocations_by_service(self, gateway_with_history: ServiceGateway) -> None:
        """Filter invocations by service_id."""
        svc1_invocations = gateway_with_history.get_invocations(service_id="svc-001")

        assert len(svc1_invocations) == 2
        assert all(inv.service_id == "svc-001" for inv in svc1_invocations)

    def test_get_invocations_by_status(self, gateway_with_history: ServiceGateway) -> None:
        """Filter invocations by status."""
        failed = gateway_with_history.get_invocations(status=ServiceStatus.FAILED)

        assert len(failed) == 1
        assert failed[0].error == "Timeout"

    def test_get_invocations_by_task(self, gateway_with_history: ServiceGateway) -> None:
        """Filter invocations by task_id."""
        task_invocations = gateway_with_history.get_invocations(task_id="task-001")

        assert len(task_invocations) == 1
        assert task_invocations[0].invocation_id == "inv-001"

    def test_get_all_invocations(self, gateway_with_history: ServiceGateway) -> None:
        """Get all invocations without filter."""
        all_invocations = gateway_with_history.get_invocations()

        assert len(all_invocations) == 3

    def test_clear_history(self, gateway_with_history: ServiceGateway) -> None:
        """Clear invocation history."""
        gateway_with_history.clear_history()

        assert len(gateway_with_history.invocations) == 0
