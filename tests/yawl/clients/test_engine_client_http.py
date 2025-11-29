"""Behavioral tests for EngineClient HTTP integration.

Chicago TDD: Tests describe EXTERNAL behavior matching Java's EngineClient.java
which wraps InterfaceA and InterfaceB clients.

Java Parity (EngineClient.java):
    - Uses InterfaceA for authentication (connect/disconnect)
    - Uses InterfaceB for workflow operations
    - Shares session handle between interfaces
    - Provides unified API for engine operations
"""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from kgcl.yawl.clients.http_engine_client import HTTPEngineClient
from kgcl.yawl.clients.interface_client import YAWLConnectionError, YAWLResponseError
from kgcl.yawl.clients.models import UploadResult, YSpecificationID


class TestHTTPEngineClientConnect:
    """Tests for connection via InterfaceA (Java parity)."""

    def test_connect_uses_interface_a(self) -> None:
        """Connect delegates to InterfaceA client."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")

        with patch.object(client._ia_client, "connect") as mock_connect:
            mock_connect.return_value = "handle-123"

            client.connect("admin", "YAWL")

            mock_connect.assert_called_once_with("admin", "YAWL")

    def test_connect_stores_handle(self) -> None:
        """Session handle shared between interfaces."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")

        with patch.object(client._ia_client, "connect") as mock_connect:
            mock_connect.return_value = "shared-handle"
            # Simulate the connect storing the handle (real method does this)

            handle = client.connect("admin", "YAWL")

            assert handle == "shared-handle"
            # HTTPEngineClient.connect() sets the IB handle from the returned value
            assert client._ib_client._session_handle == "shared-handle"

    def test_connect_failure_raises(self) -> None:
        """Connection failure propagates."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")

        with patch.object(client._ia_client, "connect") as mock_connect:
            mock_connect.side_effect = YAWLResponseError("Invalid credentials")

            with pytest.raises(YAWLResponseError):
                client.connect("bad", "creds")


class TestHTTPEngineClientDisconnect:
    """Tests for disconnect via InterfaceA (Java parity)."""

    def test_disconnect_uses_interface_a(self) -> None:
        """Disconnect delegates to InterfaceA client."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        client._ia_client._session_handle = "handle"
        client._ib_client._session_handle = "handle"

        with patch.object(client._ia_client, "disconnect") as mock_disconnect:
            mock_disconnect.return_value = True

            client.disconnect()

            mock_disconnect.assert_called_once()

    def test_disconnect_clears_handles(self) -> None:
        """InterfaceB handle cleared by HTTPEngineClient on disconnect."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        client._ia_client._session_handle = "handle"
        client._ib_client._session_handle = "handle"

        with patch.object(client._ia_client, "disconnect") as mock_disconnect:
            mock_disconnect.return_value = True

            client.disconnect()

            # HTTPEngineClient clears IB handle (IA handle cleared by its disconnect)
            assert client._ib_client._session_handle is None
            mock_disconnect.assert_called_once()


class TestHTTPEngineClientCheckConnection:
    """Tests for connection checking (Java parity)."""

    def test_connected_delegates_to_interface_a(self) -> None:
        """Connection check uses InterfaceA."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        client._ia_client._session_handle = "handle"

        with patch.object(client._ia_client, "check_connection") as mock_check:
            mock_check.return_value = True

            result = client.connected()

            assert result is True
            mock_check.assert_called_once()

    def test_connected_returns_false_when_no_handle(self) -> None:
        """Returns False when not connected."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        # No session handle

        result = client.connected()

        assert result is False


class TestHTTPEngineClientUpload:
    """Tests for specification upload via InterfaceB (Java parity)."""

    def test_upload_uses_interface_b(self) -> None:
        """Upload delegates to InterfaceB client."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        client._ia_client._session_handle = "handle"
        client._ib_client._session_handle = "handle"

        with patch.object(client._ib_client, "upload_specification") as mock_upload:
            mock_upload.return_value = UploadResult(specifications=[YSpecificationID("spec-001", "1.0")])

            result = client.upload_specification("<spec/>")

            mock_upload.assert_called_once_with("<spec/>")
            assert result.successful is True

    def test_upload_requires_connection(self) -> None:
        """Upload requires active session."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        # No session handle

        with pytest.raises(YAWLConnectionError):
            client.upload_specification("<spec/>")


class TestHTTPEngineClientUnload:
    """Tests for specification unload via InterfaceB (Java parity)."""

    def test_unload_uses_interface_b(self) -> None:
        """Unload delegates to InterfaceB client."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        client._ia_client._session_handle = "handle"
        client._ib_client._session_handle = "handle"

        with patch.object(client._ib_client, "unload_specification") as mock_unload:
            mock_unload.return_value = True

            spec_id = YSpecificationID("spec-001", "1.0")
            result = client.unload_specification(spec_id)

            assert result is True
            mock_unload.assert_called_once_with(spec_id)


class TestHTTPEngineClientLaunchCase:
    """Tests for case launch via InterfaceB (Java parity)."""

    def test_launch_uses_interface_b(self) -> None:
        """Launch delegates to InterfaceB client."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        client._ia_client._session_handle = "handle"
        client._ib_client._session_handle = "handle"

        with patch.object(client._ib_client, "launch_case") as mock_launch:
            mock_launch.return_value = "case-123"

            spec_id = YSpecificationID("spec-001", "1.0")
            result = client.launch_case(spec_id)

            assert result == "case-123"
            mock_launch.assert_called_once()

    def test_launch_with_data(self) -> None:
        """Launch passes case data to InterfaceB."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        client._ia_client._session_handle = "handle"
        client._ib_client._session_handle = "handle"

        with patch.object(client._ib_client, "launch_case") as mock_launch:
            mock_launch.return_value = "case-456"

            spec_id = YSpecificationID("spec-001", "1.0")
            case_data = "<data><customer>ACME</customer></data>"
            client.launch_case(spec_id, case_data=case_data)

            mock_launch.assert_called_once_with(spec_id, case_data=case_data)


class TestHTTPEngineClientCancelCase:
    """Tests for case cancellation via InterfaceB (Java parity)."""

    def test_cancel_uses_interface_b(self) -> None:
        """Cancel delegates to InterfaceB client."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        client._ia_client._session_handle = "handle"
        client._ib_client._session_handle = "handle"

        with patch.object(client._ib_client, "cancel_case") as mock_cancel:
            mock_cancel.return_value = True

            result = client.cancel_case("case-123")

            assert result is True
            mock_cancel.assert_called_once_with("case-123")


class TestHTTPEngineClientRunningCases:
    """Tests for running case queries (Java parity)."""

    def test_get_running_cases_uses_interface_b(self) -> None:
        """Running cases query uses InterfaceB."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        client._ia_client._session_handle = "handle"
        client._ib_client._session_handle = "handle"

        with patch.object(client._ib_client, "get_all_running_cases") as mock_get:
            mock_get.return_value = '<cases><case id="1"/></cases>'

            result = client.get_running_cases_xml()

            assert "<case" in result

    def test_get_running_cases_for_spec(self) -> None:
        """Get running cases for specific spec."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        client._ia_client._session_handle = "handle"
        client._ib_client._session_handle = "handle"

        with patch.object(client._ib_client, "get_running_cases") as mock_get:
            mock_get.return_value = '<cases><case id="1"/></cases>'

            spec_id = YSpecificationID("spec-001", "1.0")
            result = client.get_running_cases_for_spec_xml(spec_id)

            assert "<case" in result
            mock_get.assert_called_once_with(spec_id)


class TestHTTPEngineClientProperties:
    """Tests for engine properties (Java parity)."""

    def test_get_build_properties_uses_interface_a(self) -> None:
        """Build properties from InterfaceA."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        client._ia_client._session_handle = "handle"

        with patch.object(client._ia_client, "get_build_properties") as mock_props:
            mock_props.return_value = "<properties><version>5.0</version></properties>"

            result = client.get_build_properties()

            assert "version" in result

    def test_get_yawl_services(self) -> None:
        """YAWL services from InterfaceA."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")
        client._ia_client._session_handle = "handle"

        with patch.object(client._ia_client, "get_yawl_services") as mock_services:
            mock_services.return_value = '<services><service uri="http://ws"/></services>'

            result = client.get_yawl_services()

            assert "<service" in result


class TestHTTPEngineClientURIs:
    """Tests for backend URIs (Java parity)."""

    def test_get_ia_uri(self) -> None:
        """Get InterfaceA backend URI."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")

        uri = client.get_ia_uri()

        assert uri == "http://localhost:8080/yawl/ia"

    def test_get_ib_uri(self) -> None:
        """Get InterfaceB backend URI."""
        client = HTTPEngineClient(base_url="http://localhost:8080/yawl")

        uri = client.get_ib_uri()

        assert uri == "http://localhost:8080/yawl/ib"
