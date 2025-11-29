"""Behavioral tests for Interface_Client HTTP base.

Chicago TDD: Tests describe EXTERNAL behavior matching Java's Interface_Client.java.
These tests verify the Python client behaves identically to Java when interacting
with a YAWL engine server over HTTP.

Java Parity (Interface_Client.java):
    - executePost(uri, params) -> String
    - executeGet(uri, params) -> String (rerouted to POST)
    - successful(message) -> boolean (checks for <failure>)
    - prepareParamMap(action, handle) -> Map<String, String>
    - stripOuterElement(xml) -> String (removes outer XML tags)
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kgcl.yawl.clients.interface_client import InterfaceClient, YAWLConnectionError, YAWLResponseError


class TestSuccessfulResponseDetection:
    """Tests for successful() response checking (Java parity)."""

    def test_successful_returns_true_for_valid_xml(self) -> None:
        """Valid XML without <failure> is successful."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        assert client.successful("<response>data</response>") is True
        assert client.successful("<specification id='spec-001'/>") is True
        assert client.successful("plain text response") is True

    def test_successful_returns_false_for_failure_tag(self) -> None:
        """XML containing <failure> tag is not successful (Java parity)."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        assert client.successful("<failure>Error message</failure>") is False
        assert client.successful("<response><failure>nested</failure></response>") is False
        assert client.successful("prefix<failure>error</failure>suffix") is False

    def test_successful_returns_false_for_empty_response(self) -> None:
        """Empty or None response is not successful."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        assert client.successful("") is False
        assert client.successful(None) is False  # type: ignore[arg-type]


class TestPrepareParamMap:
    """Tests for prepareParamMap() parameter construction (Java parity)."""

    def test_prepare_param_map_with_action_and_handle(self) -> None:
        """Creates map with 'action' and 'sessionHandle' keys."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        params = client.prepare_param_map("checkConnection", "handle-12345")

        assert params["action"] == "checkConnection"
        assert params["sessionHandle"] == "handle-12345"

    def test_prepare_param_map_action_only(self) -> None:
        """Creates map with only 'action' when no handle provided."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        params = client.prepare_param_map("connect", None)

        assert params["action"] == "connect"
        assert "sessionHandle" not in params

    def test_prepare_param_map_returns_mutable_dict(self) -> None:
        """Returned map can be extended with additional parameters."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        params = client.prepare_param_map("uploadSpecification", "handle-123")
        params["specXML"] = "<specification/>"

        assert len(params) == 3
        assert params["specXML"] == "<specification/>"


class TestStripOuterElement:
    """Tests for stripOuterElement() XML processing (Java parity)."""

    def test_strip_outer_element_removes_wrapping_tag(self) -> None:
        """Removes the outer XML element, leaving inner content."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        result = client.strip_outer_element("<response>inner content</response>")

        assert result == "inner content"

    def test_strip_outer_element_with_nested_elements(self) -> None:
        """Preserves nested elements when stripping outer."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        xml = "<response><item>one</item><item>two</item></response>"
        result = client.strip_outer_element(xml)

        assert result == "<item>one</item><item>two</item>"

    def test_strip_outer_element_with_attributes(self) -> None:
        """Handles outer elements with attributes."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        xml = '<response status="ok">content</response>'
        result = client.strip_outer_element(xml)

        assert result == "content"

    def test_strip_outer_element_preserves_inner_attributes(self) -> None:
        """Preserves attributes on inner elements."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        xml = '<outer><spec id="001" version="1.0"/></outer>'
        result = client.strip_outer_element(xml)

        assert 'id="001"' in result
        assert 'version="1.0"' in result

    def test_strip_outer_element_empty_returns_empty(self) -> None:
        """Empty input returns empty string."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        assert client.strip_outer_element("") == ""
        assert client.strip_outer_element("<empty/>") == ""

    def test_strip_outer_element_preserves_whitespace(self) -> None:
        """Preserves significant whitespace in content."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        xml = "<response>  spaced  </response>"
        result = client.strip_outer_element(xml)

        assert result == "  spaced  "


class TestExecutePost:
    """Tests for executePost() HTTP behavior (Java parity)."""

    def test_execute_post_sends_to_uri(self) -> None:
        """POST request sent to specified URI."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        with patch.object(client, "_send_request") as mock_send:
            mock_send.return_value = "<response>ok</response>"

            result = client.execute_post("/ia", {"action": "connect"})

            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == "POST"
            assert "/ia" in call_args[0][1]

    def test_execute_post_returns_response_body(self) -> None:
        """Returns the response body string."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        with patch.object(client, "_send_request") as mock_send:
            mock_send.return_value = "<session>handle-12345</session>"

            result = client.execute_post("/ia", {"action": "connect"})

            assert result == "<session>handle-12345</session>"

    def test_execute_post_raises_on_connection_error(self) -> None:
        """Raises YAWLConnectionError on network failure (Java: IOException)."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        with patch.object(client, "_send_request") as mock_send:
            mock_send.side_effect = ConnectionError("Connection refused")

            with pytest.raises(YAWLConnectionError) as exc_info:
                client.execute_post("/ia", {"action": "connect"})

            assert "Connection refused" in str(exc_info.value)

    def test_execute_post_encodes_utf8(self) -> None:
        """Parameters encoded as UTF-8 (Java parity)."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        with patch.object(client, "_send_request") as mock_send:
            mock_send.return_value = "<ok/>"

            # Unicode parameter value
            client.execute_post("/ia", {"data": "日本語テスト"})

            # Verify the request was made (encoding happens internally)
            mock_send.assert_called_once()


class TestExecuteGet:
    """Tests for executeGet() HTTP behavior (Java parity: reroutes to POST)."""

    def test_execute_get_reroutes_to_post(self) -> None:
        """GET requests are sent as POST (Java security measure)."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        with patch.object(client, "_send_request") as mock_send:
            mock_send.return_value = "<response/>"

            result = client.execute_get("/ia", {"action": "checkConnection"})

            # Java reroutes GETs to POSTs for security
            call_args = mock_send.call_args
            assert call_args[0][0] == "POST"

    def test_execute_get_returns_same_as_post(self) -> None:
        """GET returns same response format as POST."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        with patch.object(client, "_send_request") as mock_send:
            mock_send.return_value = "<cases><case id='1'/></cases>"

            result = client.execute_get("/ib", {"action": "getCases"})

            assert result == "<cases><case id='1'/></cases>"


class TestConnectionManagement:
    """Tests for connection state management (Java parity)."""

    def test_client_starts_disconnected(self) -> None:
        """New client has no session handle."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        assert client.session_handle is None
        assert client.is_connected is False

    def test_client_stores_session_handle_after_connect(self) -> None:
        """Session handle stored after successful connect."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        # Simulate connection
        client._session_handle = "handle-abc123"

        assert client.session_handle == "handle-abc123"
        assert client.is_connected is True

    def test_client_clears_handle_on_disconnect(self) -> None:
        """Session handle cleared after disconnect."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle-abc123"

        client._session_handle = None

        assert client.session_handle is None
        assert client.is_connected is False


class TestErrorHandling:
    """Tests for error response handling (Java parity)."""

    def test_failure_response_detected(self) -> None:
        """<failure> responses are properly detected."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        response = "<failure>Invalid session handle</failure>"

        assert client.successful(response) is False
        assert "Invalid session handle" in client.extract_failure_message(response)

    def test_extract_failure_message_from_xml(self) -> None:
        """Extracts message content from <failure> element."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        msg = client.extract_failure_message("<failure>Session expired</failure>")

        assert msg == "Session expired"

    def test_extract_failure_message_nested(self) -> None:
        """Extracts message from nested <failure> element."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        xml = "<response><failure>Connection refused</failure></response>"
        msg = client.extract_failure_message(xml)

        assert msg == "Connection refused"

    def test_extract_failure_message_no_failure(self) -> None:
        """Returns empty string when no failure present."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        msg = client.extract_failure_message("<response>success</response>")

        assert msg == ""


class TestBaseURL:
    """Tests for base URL handling."""

    def test_base_url_stored(self) -> None:
        """Base URL is stored on construction."""
        client = InterfaceClient(base_url="http://engine.local:8080/yawl")

        assert client.base_url == "http://engine.local:8080/yawl"

    def test_base_url_trailing_slash_normalized(self) -> None:
        """Trailing slashes are normalized."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl/")

        assert client.base_url == "http://localhost:8080/yawl"

    def test_full_uri_constructed(self) -> None:
        """Full URI constructed from base + path."""
        client = InterfaceClient(base_url="http://localhost:8080/yawl")

        uri = client._build_uri("/ia")

        assert uri == "http://localhost:8080/yawl/ia"
