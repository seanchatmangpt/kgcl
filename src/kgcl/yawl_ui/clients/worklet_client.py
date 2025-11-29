"""YAWL Worklet Service client for dynamic process selection and exception handling.

Provides async client for YAWL Worklet Service operations:
- Running worklet retrieval
- Administration task management
- External exception handling
"""

from dataclasses import dataclass

import httpx

from kgcl.yawl_ui.clients.base_client import AbstractClient


@dataclass(frozen=True)
class WorkletRunner:
    """Running worklet information."""

    case_id: str
    worklet_name: str
    parent_task_id: str


@dataclass(frozen=True)
class AdministrationTask:
    """Worklet administration task."""

    task_id: int | None
    case_id: str
    item_id: str
    title: str
    scenario: str
    process: str
    task_type: str


class WorkletClient(AbstractClient):
    """YAWL Worklet Service client.

    Provides async interface to:
    - Retrieve running worklets
    - Manage administration tasks
    - Raise external exceptions for dynamic process selection

    Parameters
    ----------
    worklet_host : str
        Worklet Service host name or IP address
    worklet_port : str
        Worklet Service port number
    timeout : float, optional
        Request timeout in seconds, by default 30.0
    """

    def __init__(self, worklet_host: str, worklet_port: str, timeout: float = 30.0) -> None:
        """Initialize worklet service client.

        Parameters
        ----------
        worklet_host : str
            Worklet Service host name or IP address
        worklet_port : str
            Worklet Service port number
        timeout : float, optional
            Request timeout in seconds, by default 30.0
        """
        base_url = self.build_uri(worklet_host, worklet_port, "workletService")
        super().__init__(base_url, timeout)
        self._gateway_url = f"{base_url}/gateway"

    async def connect(self) -> None:
        """Connect to Worklet Service and obtain session handle.

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
            f"{self._gateway_url}",
            params={"action": "connect", "userid": self._SERVICE_USERNAME, "password": self._SERVICE_PASSWORD},
        )
        response.raise_for_status()

        if self._is_successful_worklet(response.text):
            self._handle = self._unwrap_xml(response.text)
            return

        # Fall back to default credentials
        response = await self._client.post(
            f"{self._gateway_url}",
            params={"action": "connect", "userid": self._DEFAULT_USERNAME, "password": self._DEFAULT_PASSWORD},
        )
        response.raise_for_status()

        if not self._is_successful_worklet(response.text):
            msg = "Failed to connect to YAWL Worklet Service"
            raise httpx.HTTPError(msg)

        self._handle = self._unwrap_xml(response.text)

    async def disconnect(self) -> None:
        """Disconnect from Worklet Service.

        Raises
        ------
        httpx.HTTPError
            If disconnection fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._gateway_url}", params={"action": "disconnect", "sessionHandle": handle}
        )
        response.raise_for_status()
        self._handle = None

    async def connected(self) -> bool:
        """Check if connected to Worklet Service.

        Returns
        -------
        bool
            True if connected, False otherwise
        """
        if self._handle is None:
            return False

        try:
            response = await self._client.post(
                f"{self._gateway_url}", params={"action": "checkConnection", "sessionHandle": self._handle}
            )
            response.raise_for_status()
            return response.text.lower() == "true"
        except httpx.HTTPError:
            return False

    async def get_build_properties(self) -> dict[str, str]:
        """Get Worklet Service build properties.

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
            f"{self._gateway_url}", params={"action": "getBuildProperties", "sessionHandle": handle}
        )
        response.raise_for_status()

        if not self._is_successful_worklet(response.text):
            msg = f"Failed to load worklet service build properties: {self._unwrap_xml(response.text)}"
            raise httpx.HTTPError(msg)

        return self._parse_xml_properties(response.text)

    async def get_running_worklets(self) -> list[WorkletRunner]:
        """Get running worklets.

        Returns
        -------
        list[WorkletRunner]
            List of running worklets

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._gateway_url}", params={"action": "getRunningWorklets", "sessionHandle": handle}
        )
        response.raise_for_status()

        if not self._is_successful_worklet(response.text):
            msg = self._unwrap_xml(response.text)
            raise httpx.HTTPError(msg)

        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.text)
        worklets = []
        for w_elem in root.findall(".//worklet"):
            worklets.append(
                WorkletRunner(
                    case_id=w_elem.findtext("caseID", ""),
                    worklet_name=w_elem.findtext("name", ""),
                    parent_task_id=w_elem.findtext("parentTaskID", ""),
                )
            )
        return worklets

    async def get_worklet_administration_task(self, task_id: int) -> AdministrationTask:
        """Get administration task by ID.

        Parameters
        ----------
        task_id : int
            Task identifier

        Returns
        -------
        AdministrationTask
            Administration task

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._gateway_url}",
            params={"action": "getAdministrationTask", "taskID": str(task_id), "sessionHandle": handle},
        )
        response.raise_for_status()

        return self._parse_administration_task(response.text)

    async def get_worklet_administration_tasks(self) -> list[AdministrationTask]:
        """Get all administration tasks.

        Returns
        -------
        list[AdministrationTask]
            List of administration tasks

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._gateway_url}", params={"action": "getAdministrationTasks", "sessionHandle": handle}
        )
        response.raise_for_status()

        if not self._is_successful_worklet(response.text):
            msg = self._unwrap_xml(response.text)
            raise httpx.HTTPError(msg)

        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.text)
        tasks = []
        for task_elem in root.findall(".//task"):
            tasks.append(self._parse_task_element(task_elem))
        return tasks

    async def add_worklet_administration_task(self, task: AdministrationTask) -> AdministrationTask:
        """Add administration task.

        Parameters
        ----------
        task : AdministrationTask
            Task to add

        Returns
        -------
        AdministrationTask
            Added task with assigned ID

        Raises
        ------
        httpx.HTTPError
            If addition fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._gateway_url}",
            params={
                "action": "addAdministrationTask",
                "caseID": task.case_id,
                "itemID": task.item_id,
                "title": task.title,
                "scenario": task.scenario,
                "process": task.process,
                "taskType": task.task_type,
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

        return self._parse_administration_task(response.text)

    async def remove_worklet_administration_task(self, task_id: int) -> None:
        """Remove administration task.

        Parameters
        ----------
        task_id : int
            Task identifier

        Raises
        ------
        httpx.HTTPError
            If removal fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._gateway_url}",
            params={"action": "removeAdministrationTask", "taskID": str(task_id), "sessionHandle": handle},
        )
        response.raise_for_status()

        if not self._is_successful_worklet(response.text):
            msg = self._unwrap_xml(response.text)
            raise httpx.HTTPError(msg)

    async def raise_case_external_exception(self, case_id: str, trigger: str) -> None:
        """Raise external exception for case.

        Parameters
        ----------
        case_id : str
            Case identifier
        trigger : str
            Exception trigger

        Raises
        ------
        httpx.HTTPError
            If operation fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._gateway_url}",
            params={
                "action": "raiseCaseExternalException",
                "caseID": case_id,
                "trigger": trigger,
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

        if not self._is_successful_worklet(response.text):
            msg = self._unwrap_xml(response.text)
            raise httpx.HTTPError(msg)

    async def raise_item_external_exception(self, item_id: str, trigger: str) -> None:
        """Raise external exception for work item.

        Parameters
        ----------
        item_id : str
            Work item identifier
        trigger : str
            Exception trigger

        Raises
        ------
        httpx.HTTPError
            If operation fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._gateway_url}",
            params={
                "action": "raiseItemExternalException",
                "itemID": item_id,
                "trigger": trigger,
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

        if not self._is_successful_worklet(response.text):
            msg = self._unwrap_xml(response.text)
            raise httpx.HTTPError(msg)

    async def get_external_triggers_for_case(self, case_id: str) -> list[str]:
        """Get external triggers for case.

        Parameters
        ----------
        case_id : str
            Case identifier

        Returns
        -------
        list[str]
            List of external triggers

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._gateway_url}",
            params={"action": "getExternalTriggersForCase", "caseID": case_id, "sessionHandle": handle},
        )
        response.raise_for_status()

        if not self._is_successful_worklet(response.text):
            msg = self._unwrap_xml(response.text)
            raise httpx.HTTPError(msg)

        return self._parse_string_list(response.text)

    async def get_external_triggers_for_item(self, item_id: str) -> list[str]:
        """Get external triggers for work item.

        Parameters
        ----------
        item_id : str
            Work item identifier

        Returns
        -------
        list[str]
            List of external triggers

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._gateway_url}",
            params={"action": "getExternalTriggersForItem", "itemID": item_id, "sessionHandle": handle},
        )
        response.raise_for_status()

        if not self._is_successful_worklet(response.text):
            msg = self._unwrap_xml(response.text)
            raise httpx.HTTPError(msg)

        return self._parse_string_list(response.text)

    @staticmethod
    def _parse_administration_task(xml: str) -> AdministrationTask:
        """Parse administration task from XML.

        Parameters
        ----------
        xml : str
            XML string

        Returns
        -------
        AdministrationTask
            Parsed task

        Raises
        ------
        httpx.HTTPError
            If parsing fails
        """
        import xml.etree.ElementTree as ET

        if not xml or "Fail" in xml:
            msg = xml if xml else "Empty response"
            raise httpx.HTTPError(msg)

        try:
            root = ET.fromstring(xml)
            task_elem = root.find(".//task")
            if task_elem is None:
                msg = "Unable to retrieve administration task: malformed XML"
                raise httpx.HTTPError(msg)
            return WorkletClient._parse_task_element(task_elem)
        except ET.ParseError as e:
            msg = f"Unable to retrieve administration task: malformed XML - {e}"
            raise httpx.HTTPError(msg) from e

    @staticmethod
    def _parse_task_element(task_elem: Any) -> AdministrationTask:
        """Parse task from XML element.

        Parameters
        ----------
        task_elem : Any
            XML element

        Returns
        -------
        AdministrationTask
            Parsed task
        """
        task_id_str = task_elem.findtext("id")
        return AdministrationTask(
            task_id=int(task_id_str) if task_id_str else None,
            case_id=task_elem.findtext("caseID", ""),
            item_id=task_elem.findtext("itemID", ""),
            title=task_elem.findtext("title", ""),
            scenario=task_elem.findtext("scenario", ""),
            process=task_elem.findtext("process", ""),
            task_type=task_elem.findtext("taskType", ""),
        )

    @staticmethod
    def _parse_string_list(xml: str) -> list[str]:
        """Parse list of strings from XML.

        Parameters
        ----------
        xml : str
            XML string

        Returns
        -------
        list[str]
            List of strings

        Raises
        ------
        httpx.HTTPError
            If parsing fails
        """
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml)
            return [child.text or "" for child in root]
        except ET.ParseError as e:
            msg = f"Unable to parse string list: malformed XML - {e}"
            raise httpx.HTTPError(msg) from e

    @staticmethod
    def _is_successful_worklet(xml: str) -> bool:
        """Check if Worklet Service response is successful.

        Parameters
        ----------
        xml : str
            XML response

        Returns
        -------
        bool
            True if successful (Worklet Service uses "Fail" string, not XML tags)
        """
        return bool(xml and "Fail" not in xml)
