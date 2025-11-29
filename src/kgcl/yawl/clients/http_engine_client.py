"""HTTP-based Engine client for YAWL workflow operations.

This module implements EngineClient.java behavior - wrapping InterfaceA
and InterfaceB HTTP clients for a unified workflow API.

Java Parity (EngineClient.java):
    - Uses _iaClient for authentication (connect/disconnect/checkConnection)
    - Uses _ibClient for workflow operations (specs, cases, work items)
    - Shares session handle between both interfaces
    - Methods throw IOException on failure (Python: raises exceptions)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kgcl.yawl.clients.interface_a_client import InterfaceAClient
from kgcl.yawl.clients.interface_b_client import InterfaceBClient
from kgcl.yawl.clients.interface_client import YAWLConnectionError, YAWLResponseError
from kgcl.yawl.clients.models import UploadResult, YSpecificationID


@dataclass
class HTTPEngineClient:
    """HTTP-based engine client wrapping InterfaceA and InterfaceB (Java parity).

    This client delegates authentication to InterfaceA and workflow operations
    to InterfaceB, matching Java's EngineClient architecture.

    Parameters
    ----------
    base_url : str
        Base URL of the YAWL engine (e.g., "http://localhost:8080/yawl")

    Examples
    --------
    >>> client = HTTPEngineClient("http://localhost:8080/yawl")
    >>> client.connect("admin", "YAWL")
    >>> result = client.upload_specification(spec_xml)
    >>> case_id = client.launch_case(result.specifications[0])
    >>> client.disconnect()
    """

    base_url: str
    _ia_client: InterfaceAClient = field(init=False, repr=False)
    _ib_client: InterfaceBClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize interface clients."""
        self._ia_client = InterfaceAClient(base_url=self.base_url)
        self._ib_client = InterfaceBClient(base_url=self.base_url)

    @property
    def session_handle(self) -> str | None:
        """Get current session handle.

        Returns
        -------
        str | None
            Active session handle or None if not connected
        """
        return self._ia_client.session_handle

    # =========================================================================
    # Authentication (InterfaceA)
    # =========================================================================

    def connect(self, user_id: str, password: str) -> str:
        """Connect to YAWL engine and obtain session handle.

        The session handle is shared between InterfaceA and InterfaceB.

        Parameters
        ----------
        user_id : str
            Username for authentication
        password : str
            Password

        Returns
        -------
        str
            Session handle

        Raises
        ------
        YAWLResponseError
            If authentication fails
        YAWLConnectionError
            If network error occurs
        """
        handle = self._ia_client.connect(user_id, password)
        # Share handle with InterfaceB
        self._ib_client._session_handle = handle
        return handle

    def disconnect(self) -> bool:
        """Disconnect from YAWL engine.

        Clears session handles on both interface clients.

        Returns
        -------
        bool
            True if disconnect successful
        """
        result = self._ia_client.disconnect()
        # Clear InterfaceB handle too
        self._ib_client._session_handle = None
        return result

    def connected(self) -> bool:
        """Check if session is valid.

        Returns
        -------
        bool
            True if session is valid
        """
        if not self._ia_client.session_handle:
            return False
        return self._ia_client.check_connection()

    # =========================================================================
    # Specification Operations (InterfaceB)
    # =========================================================================

    def upload_specification(self, spec_xml: str) -> UploadResult:
        """Upload workflow specification to engine.

        Parameters
        ----------
        spec_xml : str
            YAWL specification XML

        Returns
        -------
        UploadResult
            Result containing uploaded specs or errors

        Raises
        ------
        YAWLConnectionError
            If not connected
        """
        self._require_connection()
        return self._ib_client.upload_specification(spec_xml)

    def unload_specification(self, spec_id: YSpecificationID) -> bool:
        """Unload specification from engine.

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification to unload

        Returns
        -------
        bool
            True if unloaded successfully
        """
        self._require_connection()
        return self._ib_client.unload_specification(spec_id)

    def get_specification_list(self) -> str:
        """Get list of loaded specifications.

        Returns
        -------
        str
            XML list of specifications
        """
        self._require_connection()
        return self._ib_client.get_specification_list()

    def get_specification(self, spec_id: YSpecificationID) -> str:
        """Get full specification XML.

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification identifier

        Returns
        -------
        str
            Full specification XML
        """
        self._require_connection()
        return self._ib_client.get_specification(spec_id)

    # =========================================================================
    # Case Operations (InterfaceB)
    # =========================================================================

    def launch_case(self, spec_id: YSpecificationID, case_data: str | None = None) -> str:
        """Launch new case from specification.

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification to launch
        case_data : str | None
            Initial case data XML

        Returns
        -------
        str
            New case ID

        Raises
        ------
        YAWLResponseError
            If launch fails
        """
        self._require_connection()
        return self._ib_client.launch_case(spec_id, case_data=case_data)

    def cancel_case(self, case_id: str) -> bool:
        """Cancel running case.

        Parameters
        ----------
        case_id : str
            Case to cancel

        Returns
        -------
        bool
            True if cancelled successfully
        """
        self._require_connection()
        return self._ib_client.cancel_case(case_id)

    def get_running_cases_xml(self) -> str:
        """Get all running cases as XML.

        Returns
        -------
        str
            XML list of running cases
        """
        self._require_connection()
        return self._ib_client.get_all_running_cases()

    def get_running_cases_for_spec_xml(self, spec_id: YSpecificationID) -> str:
        """Get running cases for specification as XML.

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification to query

        Returns
        -------
        str
            XML list of running cases
        """
        self._require_connection()
        return self._ib_client.get_running_cases(spec_id)

    def get_case_data(self, case_id: str) -> str:
        """Get case data variables.

        Parameters
        ----------
        case_id : str
            Case identifier

        Returns
        -------
        str
            Case data XML
        """
        self._require_connection()
        return self._ib_client.get_case_data(case_id)

    def get_work_items_for_case(self, case_id: str) -> str:
        """Get work items for case.

        Parameters
        ----------
        case_id : str
            Case identifier

        Returns
        -------
        str
            XML list of work items
        """
        self._require_connection()
        return self._ib_client.get_work_items_for_case(case_id)

    # =========================================================================
    # Engine Properties (InterfaceA)
    # =========================================================================

    def get_build_properties(self) -> str:
        """Get YAWL engine build properties.

        Returns
        -------
        str
            Properties XML
        """
        self._require_connection()
        return self._ia_client.get_build_properties()

    def get_yawl_services(self) -> str:
        """Get list of registered YAWL services.

        Returns
        -------
        str
            XML list of services
        """
        self._require_connection()
        return self._ia_client.get_yawl_services()

    def get_external_db_gateways(self) -> str:
        """Get list of external database gateways.

        Returns
        -------
        str
            Gateways XML
        """
        self._require_connection()
        return self._ia_client.get_external_db_gateways()

    # =========================================================================
    # Backend URIs
    # =========================================================================

    def get_ia_uri(self) -> str:
        """Get InterfaceA backend URI.

        Returns
        -------
        str
            Full URI for InterfaceA endpoint
        """
        return self._ia_client.get_ia_backend_uri()

    def get_ib_uri(self) -> str:
        """Get InterfaceB backend URI.

        Returns
        -------
        str
            Full URI for InterfaceB endpoint
        """
        return self._ib_client.get_ib_backend_uri()

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _require_connection(self) -> None:
        """Raise if not connected.

        Raises
        ------
        YAWLConnectionError
            If no active session
        """
        if not self._ia_client.session_handle:
            raise YAWLConnectionError("Not connected - call connect() first")
