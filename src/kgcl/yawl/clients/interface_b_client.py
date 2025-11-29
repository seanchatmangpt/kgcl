"""InterfaceB HTTP client for YAWL workflow operations.

This module implements InterfaceB_EnvironmentBasedClient.java behavior -
the workflow interface for specifications, cases, and work items.

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

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from xml.etree import ElementTree as ET

from kgcl.yawl.clients.interface_client import InterfaceClient, YAWLConnectionError, YAWLResponseError
from kgcl.yawl.clients.models import UploadResult, YSpecificationID


@dataclass
class InterfaceBClient(InterfaceClient):
    """InterfaceB client for YAWL workflow operations (Java parity).

    Provides specification upload, case management, and work item
    operations matching Java's InterfaceB_EnvironmentBasedClient.java.

    Parameters
    ----------
    base_url : str
        Base URL of the YAWL engine (e.g., "http://localhost:8080/yawl")

    Examples
    --------
    >>> client = InterfaceBClient("http://localhost:8080/yawl")
    >>> client._session_handle = "handle-from-interface-a"
    >>> result = client.upload_specification(spec_xml)
    >>> case_id = client.launch_case(result.specifications[0])
    """

    _interface_path: str = field(default="/ib", repr=False)

    def upload_specification(self, spec_xml: str, handle: str | None = None) -> UploadResult:
        """Upload workflow specification to engine.

        Parameters
        ----------
        spec_xml : str
            YAWL specification XML
        handle : str | None
            Session handle

        Returns
        -------
        UploadResult
            Result containing uploaded specs or errors
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("uploadSpecification", use_handle)
        params["specXML"] = spec_xml

        response = self.execute_post(self._interface_path, params)
        return UploadResult.from_xml(response)

    def unload_specification(self, spec_id: YSpecificationID, handle: str | None = None) -> bool:
        """Unload specification from engine.

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification to unload
        handle : str | None
            Session handle

        Returns
        -------
        bool
            True if unloaded successfully
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("unloadSpecification", use_handle)
        self._add_spec_id_params(params, spec_id)

        response = self.execute_post(self._interface_path, params)
        return self.successful(response)

    def get_specification_list(self, handle: str | None = None) -> str:
        """Get list of loaded specifications.

        Parameters
        ----------
        handle : str | None
            Session handle

        Returns
        -------
        str
            XML list of specifications
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("getSpecificationList", use_handle)
        return self.execute_post(self._interface_path, params)

    def get_specification(self, spec_id: YSpecificationID, handle: str | None = None) -> str:
        """Get full specification XML.

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification identifier
        handle : str | None
            Session handle

        Returns
        -------
        str
            Full specification XML
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("getSpecification", use_handle)
        self._add_spec_id_params(params, spec_id)

        return self.execute_post(self._interface_path, params)

    def launch_case(self, spec_id: YSpecificationID, case_data: str | None = None, handle: str | None = None) -> str:
        """Launch new case from specification.

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification to launch
        case_data : str | None
            Initial case data XML
        handle : str | None
            Session handle

        Returns
        -------
        str
            New case ID

        Raises
        ------
        YAWLResponseError
            If launch fails
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("launchCase", use_handle)
        self._add_spec_id_params(params, spec_id)

        if case_data:
            params["caseData"] = case_data

        response = self.execute_post(self._interface_path, params)

        if not self.successful(response):
            raise YAWLResponseError(self.extract_failure_message(response))

        return self._extract_case_id(response)

    def cancel_case(self, case_id: str, handle: str | None = None) -> bool:
        """Cancel running case.

        Parameters
        ----------
        case_id : str
            Case to cancel
        handle : str | None
            Session handle

        Returns
        -------
        bool
            True if cancelled successfully
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("cancelCase", use_handle)
        params["caseID"] = case_id

        response = self.execute_post(self._interface_path, params)
        return self.successful(response)

    def get_running_cases(self, spec_id: YSpecificationID, handle: str | None = None) -> str:
        """Get running cases for specification.

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification to query
        handle : str | None
            Session handle

        Returns
        -------
        str
            XML list of running cases
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("getRunningCases", use_handle)
        self._add_spec_id_params(params, spec_id)

        return self.execute_post(self._interface_path, params)

    def get_all_running_cases(self, handle: str | None = None) -> str:
        """Get all running cases across all specifications.

        Parameters
        ----------
        handle : str | None
            Session handle

        Returns
        -------
        str
            XML list of all running cases
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("getAllRunningCases", use_handle)
        return self.execute_post(self._interface_path, params)

    def get_case_data(self, case_id: str, handle: str | None = None) -> str:
        """Get case data variables.

        Parameters
        ----------
        case_id : str
            Case identifier
        handle : str | None
            Session handle

        Returns
        -------
        str
            Case data XML
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("getCaseData", use_handle)
        params["caseID"] = case_id

        return self.execute_post(self._interface_path, params)

    def get_work_items_for_case(self, case_id: str, handle: str | None = None) -> str:
        """Get work items for case.

        Parameters
        ----------
        case_id : str
            Case identifier
        handle : str | None
            Session handle

        Returns
        -------
        str
            XML list of work items
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("getWorkItemsForCase", use_handle)
        params["caseID"] = case_id

        return self.execute_post(self._interface_path, params)

    def get_ib_backend_uri(self) -> str:
        """Get the InterfaceB backend URI.

        Returns
        -------
        str
            Full URI for InterfaceB endpoint
        """
        return self._build_uri(self._interface_path)

    def _require_connection(self, handle: str | None) -> None:
        """Raise if no connection handle available.

        Parameters
        ----------
        handle : str | None
            Handle to check

        Raises
        ------
        YAWLConnectionError
            If handle is None
        """
        if handle is None:
            raise YAWLConnectionError("Not connected - call connect() first")

    def _add_spec_id_params(self, params: dict[str, str], spec_id: YSpecificationID) -> None:
        """Add specification identification parameters.

        Parameters
        ----------
        params : dict[str, str]
            Parameter dict to update
        spec_id : YSpecificationID
            Specification identifier
        """
        params["specidentifier"] = spec_id.identifier
        params["specversion"] = spec_id.get_version_as_string()
        if spec_id.uri:
            params["specuri"] = spec_id.uri

    def _extract_case_id(self, response: str) -> str:
        """Extract case ID from launch response.

        Parameters
        ----------
        response : str
            XML response containing case ID

        Returns
        -------
        str
            Case ID string
        """
        # Try XML parsing first
        try:
            root = ET.fromstring(response)
            if root.tag == "caseID" and root.text:
                return root.text.strip()
            case_elem = root.find(".//caseID")
            if case_elem is not None and case_elem.text:
                return case_elem.text.strip()
        except ET.ParseError:
            pass

        # Fallback: regex extraction
        match = re.search(r"<caseID>(.*?)</caseID>", response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # If response is just the ID (no XML wrapper)
        if response and "<" not in response:
            return response.strip()

        return response
