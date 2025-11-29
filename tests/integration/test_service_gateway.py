"""Integration tests for ServiceGateway with testcontainers.

Tests real HTTP invocations against containerized services:
- HTTPBin: Standard HTTP testing endpoints
- Mock API: Custom endpoints for task delegation scenarios

Requirements
-----------
Docker must be available for these tests to run.
Tests auto-skip when Docker is not available.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import pytest

from kgcl.daemon import ServiceGateway, ServiceReference, ServiceStatus

if TYPE_CHECKING:
    pass


class TestServiceGatewayWithHTTPBin:
    """Integration tests using HTTPBin container."""

    @pytest.mark.asyncio
    async def test_invoke_post_endpoint_success(self, httpbin_container: dict[str, Any]) -> None:
        """Verify successful POST to HTTPBin /post endpoint."""
        gateway = ServiceGateway()
        ref = ServiceReference(
            service_id="httpbin-post", uri=f"{httpbin_container['url']}/post", description="HTTPBin POST endpoint"
        )
        gateway.register(ref)

        result = await gateway.invoke(
            service_id="httpbin-post", task_id="task-001", payload={"test_data": "hello", "number": 42}
        )

        assert result.status == ServiceStatus.COMPLETED
        assert result.service_id == "httpbin-post"
        assert result.task_id == "task-001"
        assert result.response is not None
        # HTTPBin echoes the JSON we sent
        assert result.response.get("json") == {"test_data": "hello", "number": 42}
        assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_invoke_with_custom_headers(self, httpbin_container: dict[str, Any]) -> None:
        """Verify custom headers are sent correctly."""
        gateway = ServiceGateway()
        ref = ServiceReference(
            service_id="httpbin-headers",
            uri=f"{httpbin_container['url']}/post",
            headers={"X-Custom-Header": "test-value", "X-App-Version": "1.2.3"},
        )
        gateway.register(ref)

        result = await gateway.invoke(service_id="httpbin-headers", task_id="task-002", payload={"check": "headers"})

        assert result.status == ServiceStatus.COMPLETED
        # HTTPBin returns request headers in the response (case may vary)
        headers = result.response.get("headers", {})
        # Check headers case-insensitively
        headers_lower = {k.lower(): v for k, v in headers.items()}
        assert headers_lower.get("x-custom-header") == "test-value"
        assert headers_lower.get("x-app-version") == "1.2.3"

    @pytest.mark.asyncio
    async def test_invoke_error_status_code(self, httpbin_container: dict[str, Any]) -> None:
        """Verify handling of HTTP error status codes."""
        gateway = ServiceGateway()
        ref = ServiceReference(
            service_id="httpbin-error",
            uri=f"{httpbin_container['url']}/status/500",
            description="HTTPBin 500 error endpoint",
        )
        gateway.register(ref)

        result = await gateway.invoke(service_id="httpbin-error", task_id="task-003", payload={})

        assert result.status == ServiceStatus.FAILED
        assert "500" in (result.error or "")

    @pytest.mark.asyncio
    async def test_invoke_404_not_found(self, httpbin_container: dict[str, Any]) -> None:
        """Verify handling of 404 responses."""
        gateway = ServiceGateway()
        ref = ServiceReference(service_id="httpbin-404", uri=f"{httpbin_container['url']}/status/404")
        gateway.register(ref)

        result = await gateway.invoke(service_id="httpbin-404", task_id="task-404", payload={})

        assert result.status == ServiceStatus.FAILED
        assert "404" in (result.error or "")

    @pytest.mark.asyncio
    async def test_invoke_timeout_with_delay(self, httpbin_container: dict[str, Any]) -> None:
        """Verify timeout handling with delayed response."""
        gateway = ServiceGateway()
        ref = ServiceReference(
            service_id="httpbin-delay",
            uri=f"{httpbin_container['url']}/delay/5",  # 5 second delay
            timeout_seconds=1.0,  # 1 second timeout
        )
        gateway.register(ref)

        result = await gateway.invoke(service_id="httpbin-delay", task_id="task-timeout", payload={})

        assert result.status == ServiceStatus.TIMEOUT
        assert result.duration_ms >= 1000  # At least 1 second

    @pytest.mark.asyncio
    async def test_invoke_multiple_services_parallel(self, httpbin_container: dict[str, Any]) -> None:
        """Verify parallel invocation of multiple services."""
        gateway = ServiceGateway()

        # Register multiple service endpoints
        for i in range(3):
            ref = ServiceReference(service_id=f"httpbin-parallel-{i}", uri=f"{httpbin_container['url']}/post")
            gateway.register(ref)

        # Invoke all in parallel
        tasks = [gateway.invoke(f"httpbin-parallel-{i}", f"task-p{i}", {"index": i}) for i in range(3)]
        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert all(r.status == ServiceStatus.COMPLETED for r in results)
        assert len(results) == 3

        # Verify each got correct response
        for i, result in enumerate(results):
            assert result.response["json"]["index"] == i


class TestServiceGatewayWithMockAPI:
    """Integration tests using Mock API container (backed by HTTPBin)."""

    @pytest.mark.asyncio
    async def test_invoke_task_endpoint(self, mock_api_container: dict[str, Any]) -> None:
        """Verify task delegation to mock API."""
        gateway = ServiceGateway()
        ref = ServiceReference(
            service_id="mock-task", uri=mock_api_container["task_endpoint"], description="Mock task processor"
        )
        gateway.register(ref)

        result = await gateway.invoke(
            service_id="mock-task",
            task_id="task-mock-001",
            payload={"task_id": "delegated-123", "data": "process this"},
        )

        assert result.status == ServiceStatus.COMPLETED
        # HTTPBin echoes JSON in the "json" field
        assert result.response["json"]["task_id"] == "delegated-123"
        assert result.response["json"]["data"] == "process this"

    @pytest.mark.asyncio
    async def test_invoke_validate_endpoint(self, mock_api_container: dict[str, Any]) -> None:
        """Verify validation service invocation."""
        gateway = ServiceGateway()
        ref = ServiceReference(service_id="mock-validate", uri=mock_api_container["validate_endpoint"])
        gateway.register(ref)

        result = await gateway.invoke(
            service_id="mock-validate", task_id="validate-001", payload={"document": "test document content"}
        )

        assert result.status == ServiceStatus.COMPLETED
        # HTTPBin echoes JSON in the "json" field
        assert result.response["json"]["document"] == "test document content"

    @pytest.mark.asyncio
    async def test_invoke_slow_endpoint_within_timeout(self, mock_api_container: dict[str, Any]) -> None:
        """Verify slow endpoint completes when timeout is sufficient."""
        gateway = ServiceGateway()
        ref = ServiceReference(
            service_id="mock-slow",
            uri=mock_api_container["slow_endpoint"],
            timeout_seconds=10.0,  # 10 second timeout for 3 second delay
        )
        gateway.register(ref)

        result = await gateway.invoke(service_id="mock-slow", task_id="slow-001", payload={})

        assert result.status == ServiceStatus.COMPLETED
        # HTTPBin delay endpoint returns delay info
        assert result.duration_ms >= 3000  # At least 3 seconds

    @pytest.mark.asyncio
    async def test_invoke_slow_endpoint_timeout(self, mock_api_container: dict[str, Any]) -> None:
        """Verify slow endpoint times out when timeout is too short."""
        gateway = ServiceGateway()
        ref = ServiceReference(
            service_id="mock-slow-timeout",
            uri=mock_api_container["slow_endpoint"],
            timeout_seconds=1.0,  # 1 second timeout for 3 second delay
        )
        gateway.register(ref)

        result = await gateway.invoke(service_id="mock-slow-timeout", task_id="slow-timeout-001", payload={})

        assert result.status == ServiceStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_invoke_error_endpoint(self, mock_api_container: dict[str, Any]) -> None:
        """Verify handling of 500 Internal Server Error."""
        gateway = ServiceGateway()
        ref = ServiceReference(service_id="mock-error", uri=mock_api_container["error_endpoint"])
        gateway.register(ref)

        result = await gateway.invoke(service_id="mock-error", task_id="error-001", payload={})

        assert result.status == ServiceStatus.FAILED
        assert "500" in (result.error or "")

    @pytest.mark.asyncio
    async def test_invoke_echo_endpoint(self, mock_api_container: dict[str, Any]) -> None:
        """Verify echo endpoint returns request details."""
        gateway = ServiceGateway()
        ref = ServiceReference(
            service_id="mock-echo", uri=mock_api_container["echo_endpoint"], headers={"X-Test-Header": "echo-test"}
        )
        gateway.register(ref)

        result = await gateway.invoke(
            service_id="mock-echo",
            task_id="echo-001",
            payload={"message": "echo this back", "nested": {"key": "value"}},
        )

        assert result.status == ServiceStatus.COMPLETED
        # HTTPBin echoes JSON in the "json" field
        assert result.response["json"]["message"] == "echo this back"
        assert result.response["json"]["nested"]["key"] == "value"
        # Headers are also echoed in HTTPBin (case-insensitive check)
        headers_lower = {k.lower(): v for k, v in result.response["headers"].items()}
        assert "x-test-header" in headers_lower

    @pytest.mark.asyncio
    async def test_invocation_history_tracking(self, mock_api_container: dict[str, Any]) -> None:
        """Verify invocation history is properly tracked."""
        gateway = ServiceGateway()
        ref = ServiceReference(service_id="mock-history", uri=mock_api_container["task_endpoint"])
        gateway.register(ref)

        # Make multiple invocations
        for i in range(3):
            await gateway.invoke(service_id="mock-history", task_id=f"history-{i}", payload={"index": i})

        # Check history
        all_invocations = gateway.get_invocations()
        service_invocations = gateway.get_invocations(service_id="mock-history")

        assert len(service_invocations) == 3
        assert all(inv.status == ServiceStatus.COMPLETED for inv in service_invocations)

        # Verify task IDs
        task_ids = {inv.task_id for inv in service_invocations}
        assert task_ids == {"history-0", "history-1", "history-2"}


class TestServiceGatewayMultiContainer:
    """Integration tests using multiple containers together."""

    @pytest.mark.asyncio
    async def test_delegate_to_multiple_backends(
        self, httpbin_container: dict[str, Any], mock_api_container: dict[str, Any]
    ) -> None:
        """Verify delegation to multiple backend services."""
        gateway = ServiceGateway()

        # Register both backends
        gateway.register(ServiceReference(service_id="backend-httpbin", uri=f"{httpbin_container['url']}/post"))
        gateway.register(ServiceReference(service_id="backend-mock", uri=mock_api_container["task_endpoint"]))

        # Invoke both in parallel
        results = await asyncio.gather(
            gateway.invoke("backend-httpbin", "task-h1", {"source": "httpbin"}),
            gateway.invoke("backend-mock", "task-m1", {"source": "mock", "task_id": "t1"}),
        )

        # Both should succeed
        assert all(r.status == ServiceStatus.COMPLETED for r in results)

        # Verify correct responses (both use HTTPBin, so JSON is in 'json' field)
        httpbin_result, mock_result = results
        assert httpbin_result.response["json"]["source"] == "httpbin"
        assert mock_result.response["json"]["task_id"] == "t1"

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(
        self, httpbin_container: dict[str, Any], mock_api_container: dict[str, Any]
    ) -> None:
        """Verify handling of mixed success/failure results."""
        gateway = ServiceGateway()

        gateway.register(ServiceReference(service_id="success-service", uri=f"{httpbin_container['url']}/post"))
        gateway.register(ServiceReference(service_id="failure-service", uri=mock_api_container["error_endpoint"]))

        results = await asyncio.gather(
            gateway.invoke("success-service", "task-s", {}), gateway.invoke("failure-service", "task-f", {})
        )

        success_result, failure_result = results
        assert success_result.status == ServiceStatus.COMPLETED
        assert failure_result.status == ServiceStatus.FAILED

    @pytest.mark.asyncio
    async def test_service_discovery_pattern(
        self, httpbin_container: dict[str, Any], mock_api_container: dict[str, Any]
    ) -> None:
        """Verify dynamic service registration and invocation."""
        gateway = ServiceGateway()

        # Simulate service discovery - register services dynamically
        services = [
            ("validator", mock_api_container["validate_endpoint"]),
            ("processor", mock_api_container["task_endpoint"]),
            ("echo", f"{httpbin_container['url']}/post"),
        ]

        for service_id, uri in services:
            gateway.register(ServiceReference(service_id=service_id, uri=uri, assignable=True))

        # List registered services (assignable ones)
        registered = gateway.list_assignable()
        assert len(registered) == 3
        assert all(ref.assignable for ref in registered)

        # Invoke each
        results = await asyncio.gather(
            gateway.invoke("validator", "t1", {"document": "doc"}),
            gateway.invoke("processor", "t2", {"task_id": "process"}),
            gateway.invoke("echo", "t3", {"echo": "test"}),
        )

        assert all(r.status == ServiceStatus.COMPLETED for r in results)


class TestServiceGatewayRobustness:
    """Robustness tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_payload(self, httpbin_container: dict[str, Any]) -> None:
        """Verify handling of empty payload."""
        gateway = ServiceGateway()
        gateway.register(ServiceReference(service_id="empty-payload", uri=f"{httpbin_container['url']}/post"))

        result = await gateway.invoke("empty-payload", "task-empty", {})

        assert result.status == ServiceStatus.COMPLETED
        assert result.response["json"] == {}

    @pytest.mark.asyncio
    async def test_large_payload(self, httpbin_container: dict[str, Any]) -> None:
        """Verify handling of large payload."""
        gateway = ServiceGateway()
        gateway.register(ServiceReference(service_id="large-payload", uri=f"{httpbin_container['url']}/post"))

        # Create a large payload (100KB of data)
        large_data = {"data": "x" * 100000, "items": list(range(1000))}

        result = await gateway.invoke("large-payload", "task-large", large_data)

        assert result.status == ServiceStatus.COMPLETED
        assert len(result.response["json"]["data"]) == 100000

    @pytest.mark.asyncio
    async def test_special_characters_in_payload(self, httpbin_container: dict[str, Any]) -> None:
        """Verify handling of special characters in payload."""
        gateway = ServiceGateway()
        gateway.register(ServiceReference(service_id="special-chars", uri=f"{httpbin_container['url']}/post"))

        special_payload = {
            "unicode": "Hello 世界 🌍",
            "escapes": 'quote: " backslash: \\ newline: \n tab: \t',
            "html": "<script>alert('xss')</script>",
            "url": "https://example.com?foo=bar&baz=qux",
        }

        result = await gateway.invoke("special-chars", "task-special", special_payload)

        assert result.status == ServiceStatus.COMPLETED
        assert result.response["json"]["unicode"] == "Hello 世界 🌍"
        assert "<script>" in result.response["json"]["html"]

    @pytest.mark.asyncio
    async def test_rapid_sequential_invocations(self, mock_api_container: dict[str, Any]) -> None:
        """Verify handling of rapid sequential invocations."""
        gateway = ServiceGateway()
        gateway.register(ServiceReference(service_id="rapid-seq", uri=mock_api_container["task_endpoint"]))

        # Make 10 rapid invocations
        results = []
        for i in range(10):
            result = await gateway.invoke("rapid-seq", f"rapid-{i}", {"index": i})
            results.append(result)

        assert all(r.status == ServiceStatus.COMPLETED for r in results)
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_concurrent_high_load(self, mock_api_container: dict[str, Any]) -> None:
        """Verify handling of high concurrent load."""
        gateway = ServiceGateway()
        gateway.register(ServiceReference(service_id="high-load", uri=mock_api_container["task_endpoint"]))

        # Make 20 concurrent invocations
        tasks = [gateway.invoke("high-load", f"load-{i}", {"index": i}) for i in range(20)]
        results = await asyncio.gather(*tasks)

        # All should complete (may have some failures under high load, but no crashes)
        completed = [r for r in results if r.status == ServiceStatus.COMPLETED]
        assert len(completed) >= 15  # At least 75% success rate
