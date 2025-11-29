"""Behavioral tests for InterfaceB HTTP client (workflow interface).

Chicago TDD: Tests describe EXTERNAL behavior matching Java's
InterfaceB_EnvironmentBasedClient.java.

Java Parity (InterfaceB_EnvironmentBasedClient.java):
    - uploadSpecification(specXML, handle) -> UploadResult
    - unloadSpecification(specID, handle) -> success
    - getSpecificationList(handle) -> XML list
    - getSpecification(specID, handle) -> XML
    - launchCase(specID, caseData, handle) -> caseID
    - cancelCase(caseID, handle) -> success
    - getRunningCases(specID, handle) -> XML list
    - getAllRunningCases(handle) -> XML list
    - getCaseData(caseID, handle) -> XML
    - getWorkItemsForCase(caseID, handle) -> XML list

Interface Path: /yawl/ib
"""

from unittest.mock import MagicMock, patch

import pytest

from kgcl.yawl.clients.interface_b_client import InterfaceBClient
from kgcl.yawl.clients.interface_client import YAWLConnectionError, YAWLResponseError
from kgcl.yawl.clients.models import YSpecificationID, YSpecVersion


class TestInterfaceBUploadSpecification:
    """Tests for uploadSpecification() (Java parity)."""

    def test_upload_specification_returns_result(self) -> None:
        """Upload returns parsed UploadResult."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = '<response><specification id="spec-001" version="1.0"/></response>'

            result = client.upload_specification("<specification>...</specification>")

            assert result.successful is True
            assert len(result.specifications) == 1
            assert result.specifications[0].identifier == "spec-001"

    def test_upload_sends_correct_params(self) -> None:
        """Upload sends specXML parameter."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = '<response><specification id="spec-001"/></response>'

            spec_xml = "<specification>content</specification>"
            client.upload_specification(spec_xml)

            call_args = mock_post.call_args
            assert call_args[0][0] == "/ib"
            params = call_args[0][1]
            assert params["action"] == "uploadSpecification"
            assert params["specXML"] == spec_xml

    def test_upload_failure_returns_errors(self) -> None:
        """Upload failure captured in UploadResult."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<failure>Invalid specification format</failure>"

            result = client.upload_specification("<bad/>")

            assert result.successful is False
            assert len(result.errors) >= 1


class TestInterfaceBUnloadSpecification:
    """Tests for unloadSpecification() (Java parity)."""

    def test_unload_specification_by_id(self) -> None:
        """Unload specification by YSpecificationID."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<success/>"

            spec_id = YSpecificationID("spec-001", "1.0", "MySpec")
            result = client.unload_specification(spec_id)

            assert result is True
            params = mock_post.call_args[0][1]
            assert params["action"] == "unloadSpecification"
            assert "specidentifier" in params or "specID" in params

    def test_unload_nonexistent_fails(self) -> None:
        """Unload nonexistent specification returns False."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<failure>Specification not found</failure>"

            spec_id = YSpecificationID("nonexistent", "1.0")
            result = client.unload_specification(spec_id)

            assert result is False


class TestInterfaceBSpecificationList:
    """Tests for getSpecificationList() (Java parity)."""

    def test_get_specification_list(self) -> None:
        """Get list of loaded specifications."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = '<specificationData><specification id="spec-001"/></specificationData>'

            result = client.get_specification_list()

            assert "<specification" in result
            params = mock_post.call_args[0][1]
            assert params["action"] == "getSpecificationList"

    def test_get_specification_by_id(self) -> None:
        """Get specific specification XML."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<specification>full XML content</specification>"

            spec_id = YSpecificationID("spec-001", "1.0")
            result = client.get_specification(spec_id)

            assert "specification" in result


class TestInterfaceBLaunchCase:
    """Tests for launchCase() (Java parity)."""

    def test_launch_case_returns_case_id(self) -> None:
        """Launch returns new case ID."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<caseID>123</caseID>"

            spec_id = YSpecificationID("spec-001", "1.0")
            case_id = client.launch_case(spec_id)

            assert case_id == "123"

    def test_launch_case_with_data(self) -> None:
        """Launch with initial case data."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<caseID>456</caseID>"

            spec_id = YSpecificationID("spec-001", "1.0")
            case_data = "<data><customer>ACME</customer></data>"
            case_id = client.launch_case(spec_id, case_data=case_data)

            assert case_id == "456"
            params = mock_post.call_args[0][1]
            assert params["caseData"] == case_data

    def test_launch_case_sends_spec_params(self) -> None:
        """Launch sends specification identification params."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<caseID>789</caseID>"

            spec_id = YSpecificationID("spec-001", "2.5", "MyWorkflow")
            client.launch_case(spec_id)

            params = mock_post.call_args[0][1]
            assert params["action"] == "launchCase"
            # Should include spec identification
            assert "specidentifier" in params or "specID" in params

    def test_launch_failure_raises_error(self) -> None:
        """Launch failure raises YAWLResponseError."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<failure>Specification not loaded</failure>"

            spec_id = YSpecificationID("nonexistent", "1.0")

            with pytest.raises(YAWLResponseError):
                client.launch_case(spec_id)


class TestInterfaceBCancelCase:
    """Tests for cancelCase() (Java parity)."""

    def test_cancel_case_success(self) -> None:
        """Cancel running case."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<success/>"

            result = client.cancel_case("123")

            assert result is True
            params = mock_post.call_args[0][1]
            assert params["action"] == "cancelCase"
            assert params["caseID"] == "123"

    def test_cancel_nonexistent_fails(self) -> None:
        """Cancel nonexistent case returns False."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<failure>Case not found</failure>"

            result = client.cancel_case("nonexistent")

            assert result is False


class TestInterfaceBRunningCases:
    """Tests for running case queries (Java parity)."""

    def test_get_running_cases_for_spec(self) -> None:
        """Get running cases for specific specification."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = '<cases><case id="123"/><case id="456"/></cases>'

            spec_id = YSpecificationID("spec-001", "1.0")
            result = client.get_running_cases(spec_id)

            assert "<case" in result
            params = mock_post.call_args[0][1]
            assert params["action"] == "getRunningCases"

    def test_get_all_running_cases(self) -> None:
        """Get all running cases across all specs."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = '<cases><case id="1"/><case id="2"/><case id="3"/></cases>'

            result = client.get_all_running_cases()

            assert "<case" in result
            params = mock_post.call_args[0][1]
            assert params["action"] == "getAllRunningCases"


class TestInterfaceBCaseData:
    """Tests for case data queries (Java parity)."""

    def test_get_case_data(self) -> None:
        """Get case data variables."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = "<data><customer>ACME</customer><amount>1000</amount></data>"

            result = client.get_case_data("123")

            assert "<customer>" in result
            params = mock_post.call_args[0][1]
            assert params["action"] == "getCaseData"
            assert params["caseID"] == "123"

    def test_get_work_items_for_case(self) -> None:
        """Get work items for a case."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        client._session_handle = "handle"

        with patch.object(client, "execute_post") as mock_post:
            mock_post.return_value = '<workItems><workItem id="wi-001" status="Offered"/></workItems>'

            result = client.get_work_items_for_case("123")

            assert "<workItem" in result


class TestInterfaceBBackendURI:
    """Tests for backend URI (Java parity)."""

    def test_get_ib_backend_uri(self) -> None:
        """getIBBackendURI returns the interface B endpoint."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")

        uri = client.get_ib_backend_uri()

        assert uri == "http://localhost:8080/yawl/ib"


class TestInterfaceBRequiresConnection:
    """Tests that operations require active session."""

    def test_upload_without_connection_raises(self) -> None:
        """Operations without session raise error."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")
        # No session handle set

        with pytest.raises(YAWLConnectionError) as exc_info:
            client.upload_specification("<spec/>")

        assert "Not connected" in str(exc_info.value)

    def test_launch_without_connection_raises(self) -> None:
        """Launch without session raises error."""
        client = InterfaceBClient(base_url="http://localhost:8080/yawl")

        spec_id = YSpecificationID("spec-001", "1.0")

        with pytest.raises(YAWLConnectionError):
            client.launch_case(spec_id)
