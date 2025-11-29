"""Behavioral tests for InterfaceA HTTP client (management interface).

Chicago TDD: Tests describe EXTERNAL behavior matching Java's
InterfaceA_EnvironmentBasedClient.java.

Java Parity (InterfaceA_EnvironmentBasedClient.java):
    - connect(userID, password) -> sessionHandle
    - disconnect(handle) -> success
    - checkConnection(handle) -> boolean
    - getAccounts(handle) -> XML list
    - createAccount(username, password, isAdmin, handle) -> success
    - deleteAccount(username, handle) -> success
    - updatePassword(username, oldPassword, newPassword, handle) -> success
    - getYAWLServices(handle) -> XML list
    - addYAWLService(service, handle) -> success
    - removeYAWLService(serviceURI, handle) -> success
    - getExternalDBGateways(handle) -> XML list
    - getBuildProperties(handle) -> properties XML
    - getClientAccount(handle) -> account XML
    - getIABackendURI() -> String

Interface Path: /yawl/ia (or /ia relative to base)
"""

from unittest.mock import MagicMock, patch

import pytest

from kgcl.yawl.clients.interface_a_client import InterfaceAClient
from kgcl.yawl.clients.interface_client import YAWLConnectionError, YAWLResponseError


class TestInterfaceAConnect:
    """Tests for connect() authentication (Java parity)."""

    def test_connect_returns_session_handle(self) -> None:
        """Successful connect returns session handle string."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<sessionHandle>abc123</sessionHandle>"

            handle = client.connect("admin", "YAWL")

            assert handle == "abc123"
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "/ia"
            params = call_args[0][1]
            assert params["action"] == "connect"
            assert params["userid"] == "admin"
            # Password should be encrypted (Java: PasswordEncryptor.encrypt)
            assert "password" in params

    def test_connect_stores_handle_in_client(self) -> None:
        """Session handle stored in client after connect."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<sessionHandle>handle-xyz</sessionHandle>"

            client.connect("admin", "YAWL")

            assert client.session_handle == "handle-xyz"
            assert client.is_connected is True

    def test_connect_failure_raises_error(self) -> None:
        """Failed connect raises YAWLResponseError."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<failure>Invalid credentials</failure>"

            with pytest.raises(YAWLResponseError) as exc_info:
                client.connect("bad", "credentials")

            assert "Invalid credentials" in str(exc_info.value)

    def test_connect_network_error_raises_connection_error(self) -> None:
        """Network failure raises YAWLConnectionError."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")

        with patch.object(client, "execute_post") as mock_post:
            mock_post.side_effect = YAWLConnectionError("Connection refused")

            with pytest.raises(YAWLConnectionError):
                client.connect("admin", "YAWL")


class TestInterfaceADisconnect:
    """Tests for disconnect() session termination (Java parity)."""

    def test_disconnect_clears_session(self) -> None:
        """Disconnect clears session handle."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle-123"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<success/>"

            client.disconnect()

            assert client.session_handle is None
            assert client.is_connected is False

    def test_disconnect_sends_correct_action(self) -> None:
        """Disconnect sends 'disconnect' action with handle."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle-123"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<success/>"

            client.disconnect()

            call_args = mock_post.call_args
            params = call_args[0][1]
            assert params["action"] == "disconnect"
            assert params["sessionHandle"] == "handle-123"

    def test_disconnect_with_explicit_handle(self) -> None:
        """Can disconnect with explicit handle."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<success/>"

            client.disconnect(handle="other-handle")

            params = mock_post.call_args[0][1]
            assert params["sessionHandle"] == "other-handle"


class TestInterfaceACheckConnection:
    """Tests for checkConnection() session validation (Java parity)."""

    def test_check_connection_returns_true_for_valid(self) -> None:
        """Returns True for valid session."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "valid-handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<response>true</response>"

            result = client.check_connection()

            assert result is True

    def test_check_connection_returns_false_for_invalid(self) -> None:
        """Returns False for invalid/expired session."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "expired-handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<failure>Invalid session</failure>"

            result = client.check_connection()

            assert result is False

    def test_check_connection_with_explicit_handle(self) -> None:
        """Can check specific handle."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<response>true</response>"

            result = client.check_connection(handle="check-handle")

            params = mock_post.call_args[0][1]
            assert params["sessionHandle"] == "check-handle"


class TestInterfaceAAccounts:
    """Tests for account management (Java parity)."""

    def test_get_accounts_returns_list(self) -> None:
        """getAccounts returns XML list of accounts."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = '<accounts><account name="admin"/></accounts>'

            result = client.get_accounts()

            assert "<account" in result
            params = mock_post.call_args[0][1]
            assert params["action"] == "getAccounts"

    def test_create_account(self) -> None:
        """createAccount creates new user."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<success/>"

            result = client.create_account("newuser", "password123", is_admin=False)

            assert result is True
            params = mock_post.call_args[0][1]
            assert params["action"] == "createAccount"
            assert params["username"] == "newuser"

    def test_delete_account(self) -> None:
        """deleteAccount removes user."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<success/>"

            result = client.delete_account("olduser")

            assert result is True
            params = mock_post.call_args[0][1]
            assert params["action"] == "deleteAccount"
            assert params["username"] == "olduser"

    def test_update_password(self) -> None:
        """updatePassword changes user password."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<success/>"

            result = client.update_password("user", "oldpwd", "newpwd")

            assert result is True
            params = mock_post.call_args[0][1]
            assert params["action"] == "updatePassword"


class TestInterfaceAServices:
    """Tests for YAWL service management (Java parity)."""

    def test_get_yawl_services(self) -> None:
        """getYAWLServices returns service list."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = '<services><service uri="http://localhost/ws"/></services>'

            result = client.get_yawl_services()

            assert "<service" in result
            params = mock_post.call_args[0][1]
            assert params["action"] == "getYAWLServices"

    def test_add_yawl_service(self) -> None:
        """addYAWLService registers new service."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<success/>"

            service_xml = '<service uri="http://new.service"/>'
            result = client.add_yawl_service(service_xml)

            assert result is True
            params = mock_post.call_args[0][1]
            assert params["action"] == "addYAWLService"
            assert params["service"] == service_xml

    def test_remove_yawl_service(self) -> None:
        """removeYAWLService unregisters service."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<success/>"

            result = client.remove_yawl_service("http://old.service")

            assert result is True
            params = mock_post.call_args[0][1]
            assert params["action"] == "removeYAWLService"
            assert params["serviceURI"] == "http://old.service"


class TestInterfaceAProperties:
    """Tests for system properties (Java parity)."""

    def test_get_build_properties(self) -> None:
        """getBuildProperties returns version info."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<properties><version>4.5</version></properties>"

            result = client.get_build_properties()

            assert "version" in result
            params = mock_post.call_args[0][1]
            assert params["action"] == "getBuildProperties"

    def test_get_external_db_gateways(self) -> None:
        """getExternalDBGateways returns gateway list."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = '<gateways><gateway name="HibernateGateway"/></gateways>'

            result = client.get_external_db_gateways()

            assert "<gateway" in result

    def test_get_client_account(self) -> None:
        """getClientAccount returns current user's account info."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = '<account name="admin" isAdmin="true"/>'

            result = client.get_client_account()

            assert "admin" in result


class TestInterfaceABackendURI:
    """Tests for backend URI (Java parity)."""

    def test_get_ia_backend_uri(self) -> None:
        """getIABackendURI returns the interface A endpoint."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")

        uri = client.get_ia_backend_uri()

        assert uri == "http://localhost:8080/yawl/ia"

    def test_backend_uri_normalized(self) -> None:
        """Backend URI normalized regardless of base URL format."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl/")

        uri = client.get_ia_backend_uri()

        assert uri == "http://localhost:8080/yawl/ia"


class TestInterfaceARequiresConnection:
    """Tests that operations require active session."""

    def test_get_accounts_without_connection_raises(self) -> None:
        """Operations without session raise error."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        # No session handle set

        with pytest.raises(YAWLConnectionError) as exc_info:
            client.get_accounts()

        assert "Not connected" in str(exc_info.value)

    def test_operations_use_stored_handle(self) -> None:
        """Operations use stored session handle."""
        client = InterfaceAClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "stored-handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<success/>"

            client.get_accounts()

            params = mock_post.call_args[0][1]
            assert params["sessionHandle"] == "stored-handle"
