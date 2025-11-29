"""YAWL Engine client for workflow specification and case management.

Provides async client for YAWL Engine Interface A and B operations:
- Specification upload, unload, and retrieval
- Case launching and cancellation
- Work item instance creation
- Task information retrieval
"""

from dataclasses import dataclass

import httpx

from kgcl.yawl_ui.clients.base_client import AbstractClient, ClientEventAction


@dataclass(frozen=True)
class YSpecificationID:
    """YAWL specification identifier."""

    identifier: str
    version: str
    uri: str


@dataclass(frozen=True)
class RunningCase:
    """Running case information."""

    spec_id: YSpecificationID
    case_id: str


@dataclass(frozen=True)
class UploadResult:
    """Specification upload result."""

    message: str


class EngineClient(AbstractClient):
    """YAWL Engine client for Interface A and B operations.

    Provides async interface to:
    - Interface A: Specification management, client applications
    - Interface B: Case management, work items, task information

    Parameters
    ----------
    engine_host : str
        YAWL Engine host name or IP address
    engine_port : str
        YAWL Engine port number
    timeout : float, optional
        Request timeout in seconds, by default 30.0
    """

    def __init__(self, engine_host: str, engine_port: str, timeout: float = 30.0) -> None:
        """Initialize engine client.

        Parameters
        ----------
        engine_host : str
            YAWL Engine host name or IP address
        engine_port : str
            YAWL Engine port number
        timeout : float, optional
            Request timeout in seconds, by default 30.0
        """
        base_url = self.build_uri(engine_host, engine_port, "yawl")
        super().__init__(base_url, timeout)
        self._ia_url = f"{base_url}/ia"
        self._ib_url = f"{base_url}/ib"

    async def connect(self) -> None:
        """Connect to YAWL Engine and obtain session handle.

        Tries service credentials first, then falls back to default admin credentials.

        Raises
        ------
        httpx.HTTPError
            If connection fails with both credential sets
        """
        if await self.connected():
            return

        # Try service credentials first
        response = await self._client.post(
            f"{self._ia_url}",
            params={"action": "connect", "userid": self._SERVICE_USERNAME, "password": self._SERVICE_PASSWORD},
        )
        response.raise_for_status()

        if self._is_successful(response.text):
            self._handle = self._unwrap_xml(response.text)
            return

        # Fall back to default credentials
        response = await self._client.post(
            f"{self._ia_url}",
            params={"action": "connect", "userid": self._DEFAULT_USERNAME, "password": self._DEFAULT_PASSWORD},
        )
        response.raise_for_status()

        if not self._is_successful(response.text):
            msg = "Failed to connect to YAWL Engine"
            raise httpx.HTTPError(msg)

        self._handle = self._unwrap_xml(response.text)

    async def disconnect(self) -> None:
        """Disconnect from YAWL Engine.

        Raises
        ------
        httpx.HTTPError
            If disconnection fails
        """
        handle = await self.get_handle()
        response = await self._client.post(f"{self._ia_url}", params={"action": "disconnect", "sessionHandle": handle})
        response.raise_for_status()
        self._handle = None

    async def connected(self) -> bool:
        """Check if connected to YAWL Engine.

        Returns
        -------
        bool
            True if connected, False otherwise
        """
        if self._handle is None:
            return False

        try:
            response = await self._client.post(
                f"{self._ia_url}", params={"action": "checkConnection", "sessionHandle": self._handle}
            )
            response.raise_for_status()
            return self._is_successful(response.text)
        except httpx.HTTPError:
            return False

    async def get_build_properties(self) -> dict[str, str]:
        """Get YAWL Engine build properties.

        Returns
        -------
        dict[str, str]
            Build properties

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._ia_url}", params={"action": "getBuildProperties", "sessionHandle": handle}
        )
        response.raise_for_status()

        if not self._is_successful(response.text):
            msg = f"Failed to load engine build properties: {self._unwrap_xml(response.text)}"
            raise httpx.HTTPError(msg)

        return self._parse_xml_properties(self._unwrap_xml(response.text))

    async def get_client_applications(self) -> list[dict[str, str]]:
        """Get registered client applications.

        Returns
        -------
        list[dict[str, str]]
            List of client application information

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._ia_url}", params={"action": "getClientAccounts", "sessionHandle": handle}
        )
        response.raise_for_status()

        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.text)
        clients = []
        for client_elem in root.findall(".//client"):
            clients.append(
                {
                    "username": client_elem.get("username", ""),
                    "password": client_elem.get("password", ""),
                    "documentation": client_elem.get("documentation", ""),
                }
            )
        return clients

    async def get_running_cases(self) -> list[RunningCase]:
        """Get all running cases.

        Returns
        -------
        list[RunningCase]
            List of running cases

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._ib_url}", params={"action": "getAllRunningCases", "sessionHandle": handle}
        )
        response.raise_for_status()

        if not self._is_successful(response.text):
            return []

        import xml.etree.ElementTree as ET

        xml_content = self._unwrap_xml(response.text)
        root = ET.fromstring(xml_content)

        cases = []
        for spec_elem in root.findall(".//specification"):
            spec_id = YSpecificationID(
                identifier=spec_elem.get("id", ""), version=spec_elem.get("version", ""), uri=spec_elem.get("uri", "")
            )
            for case_elem in spec_elem.findall("caseID"):
                case_id = case_elem.text or ""
                cases.append(RunningCase(spec_id=spec_id, case_id=case_id))

        return cases

    async def upload_specification(self, content: str) -> UploadResult:
        """Upload workflow specification to engine.

        Parameters
        ----------
        content : str
            YAWL specification XML content

        Returns
        -------
        UploadResult
            Upload result

        Raises
        ------
        httpx.HTTPError
            If upload fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._ia_url}", params={"action": "upload", "sessionHandle": handle}, data=content
        )
        response.raise_for_status()

        if not self._is_successful(response.text):
            msg = self._unwrap_xml(response.text)
            raise httpx.HTTPError(msg)

        return UploadResult(message=response.text)

    async def unload_specification(self, spec_id: YSpecificationID) -> bool:
        """Unload specification from engine.

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification identifier

        Returns
        -------
        bool
            True if successful

        Raises
        ------
        httpx.HTTPError
            If unload fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._ia_url}",
            params={
                "action": "unload",
                "specidentifier": spec_id.identifier,
                "specversion": spec_id.version,
                "specuri": spec_id.uri,
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

        if not self._is_successful(response.text):
            msg = self._unwrap_xml(response.text)
            raise httpx.HTTPError(msg)

        self._announce_event_from_action(ClientEventAction.SPECIFICATION_UNLOAD, spec_id)
        return True

    async def launch_case(self, spec_id: YSpecificationID, case_data: str, delay_ms: int | None = None) -> str:
        """Launch new case instance.

        Parameters
        ----------
        spec_id : YSpecificationID
            Specification identifier
        case_data : str
            Case data XML
        delay_ms : int | None, optional
            Delay in milliseconds before launch, by default None

        Returns
        -------
        str
            Case ID

        Raises
        ------
        httpx.HTTPError
            If launch fails
        """
        handle = await self.get_handle()
        params: dict[str, str | int] = {
            "action": "launchCase",
            "specidentifier": spec_id.identifier,
            "specversion": spec_id.version,
            "specuri": spec_id.uri,
            "sessionHandle": handle,
        }

        if delay_ms is not None:
            params["delay"] = delay_ms

        response = await self._client.post(f"{self._ib_url}", params=params, data=case_data)
        response.raise_for_status()

        if not self._is_successful(response.text):
            msg = self._unwrap_xml(response.text)
            raise httpx.HTTPError(msg)

        case_id = response.text
        self._announce_event_from_action(ClientEventAction.LAUNCH_CASE, case_id)
        return case_id

    async def cancel_case(self, case_id: str) -> None:
        """Cancel running case.

        Parameters
        ----------
        case_id : str
            Case identifier

        Raises
        ------
        httpx.HTTPError
            If cancellation fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._ib_url}", params={"action": "cancelCase", "caseID": case_id, "sessionHandle": handle}
        )
        response.raise_for_status()

    async def can_create_new_instance(self, item_id: str) -> bool:
        """Check if new instance can be created for work item.

        Parameters
        ----------
        item_id : str
            Work item identifier

        Returns
        -------
        bool
            True if new instance can be created

        Raises
        ------
        httpx.HTTPError
            If check fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._ib_url}",
            params={"action": "checkPermissionToAddInstances", "workItemID": item_id, "sessionHandle": handle},
        )
        response.raise_for_status()
        return self._is_successful(response.text)

    async def create_new_instance(self, item_id: str, param_value: str) -> dict[str, str]:
        """Create new work item instance.

        Parameters
        ----------
        item_id : str
            Work item identifier
        param_value : str
            Parameter value XML

        Returns
        -------
        dict[str, str]
            Work item record

        Raises
        ------
        httpx.HTTPError
            If creation fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._ib_url}",
            params={
                "action": "createNewInstance",
                "workItemID": item_id,
                "paramValueForMICreation": param_value,
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

        if not self._is_successful(response.text):
            msg = response.text
            raise httpx.HTTPError(msg)

        # Parse work item record from XML
        import xml.etree.ElementTree as ET

        wir_xml = self._unwrap_xml(response.text)
        root = ET.fromstring(wir_xml)
        return {child.tag: child.text or "" for child in root}

    async def get_specification_id_for_case(self, case_id: str) -> YSpecificationID:
        """Get specification ID for case.

        Parameters
        ----------
        case_id : str
            Case identifier

        Returns
        -------
        YSpecificationID
            Specification identifier

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._ib_url}",
            params={"action": "getSpecificationIDForCase", "caseID": case_id, "sessionHandle": handle},
        )
        response.raise_for_status()

        if not self._is_successful(response.text):
            msg = "Malformed specification id returned from engine"
            raise httpx.HTTPError(msg)

        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.text)
        spec_elem = root.find(".//specificationID")
        if spec_elem is None:
            msg = "Malformed specification id returned from engine"
            raise httpx.HTTPError(msg)

        return YSpecificationID(
            identifier=spec_elem.get("identifier", ""),
            version=spec_elem.get("version", ""),
            uri=spec_elem.get("uri", ""),
        )
