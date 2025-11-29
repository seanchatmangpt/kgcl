"""Tests for MockInterfaceAClient.

Chicago School TDD - tests verify real behavior of mock client
for session authentication scenarios.
"""

from kgcl.yawl.util.mock_interface_a import MockInterfaceAClient


def test_mock_client_initialization() -> None:
    """Test mock client initializes with default admin user."""
    client = MockInterfaceAClient("http://localhost:8080/ia", "admin", "admin")

    # Admin user should be pre-registered
    assert client.get_password("admin") == "admin"


def test_mock_client_registers_connecting_user() -> None:
    """Test connecting user is auto-registered."""
    client = MockInterfaceAClient("http://localhost:8080/ia", "testuser", "testpass")

    # Connecting user should be registered
    assert client.get_password("testuser") == "testpass"


def test_register_user() -> None:
    """Test manual user registration."""
    client = MockInterfaceAClient("http://localhost:8080/ia", "admin", "admin")
    client.register_user("newuser", "newpass")

    assert client.get_password("newuser") == "newpass"


def test_register_service() -> None:
    """Test service registration."""
    client = MockInterfaceAClient("http://localhost:8080/ia", "admin", "admin")
    client.register_service("WorkletService", "workletpass", "http://localhost:8080/worklet")

    assert client.get_password("WorkletService") == "workletpass"


def test_get_password_unknown_user() -> None:
    """Test get_password returns None for unknown users."""
    client = MockInterfaceAClient("http://localhost:8080/ia", "admin", "admin")

    assert client.get_password("unknown") is None


def test_mock_connection_always_succeeds() -> None:
    """Test mock connection check always succeeds."""
    client = MockInterfaceAClient("http://localhost:8080/ia", "admin", "admin")

    result = client.check_connection()
    assert "<success" in result


def test_mock_connect_with_valid_credentials() -> None:
    """Test connect with valid credentials returns handle."""
    client = MockInterfaceAClient("http://localhost:8080/ia", "admin", "admin")

    handle = client.connect("admin", "admin")
    assert handle.startswith("mock-handle")
    assert "admin" in handle


def test_mock_connect_with_invalid_credentials() -> None:
    """Test connect with invalid credentials returns failure."""
    client = MockInterfaceAClient("http://localhost:8080/ia", "admin", "admin")

    result = client.connect("admin", "wrong")
    assert "<failure>" in result
    assert "Invalid credentials" in result
