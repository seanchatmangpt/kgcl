"""YAWL Resource Service client for work queue and organizational resource management.

Provides async client for YAWL Resource Service operations:
- Work queue management (offer, allocate, start, complete items)
- Participant and organizational hierarchy management
- Calendar and availability management
- Secondary resource allocation
"""

from dataclasses import dataclass
from typing import Any

import httpx

from kgcl.yawl_ui.clients.base_client import AbstractClient, ClientEventAction
from kgcl.yawl_ui.clients.engine_client import YSpecificationID


@dataclass(frozen=True)
class QueueSet:
    """Work queue set containing offered, allocated, and started items."""

    offered: list[dict[str, Any]]
    allocated: list[dict[str, Any]]
    started: list[dict[str, Any]]


@dataclass(frozen=True)
class Participant:
    """Participant (human resource) information."""

    id: str
    user_id: str
    first_name: str
    last_name: str
    admin: bool


@dataclass(frozen=True)
class UserPrivileges:
    """User privilege information."""

    can_choose_item_to_start: bool
    can_start_concurrent: bool
    can_reorder: bool
    can_view_team_items: bool
    can_view_org_group_items: bool
    can_chain: bool
    can_manage_cases: bool


class ResourceClient(AbstractClient):
    """YAWL Resource Service client.

    Provides async interface to:
    - Work queue operations (offer, allocate, start, complete)
    - Participant management
    - Organizational hierarchy (roles, capabilities, positions, org groups)
    - Calendar and resource availability

    Parameters
    ----------
    resource_host : str
        Resource Service host name or IP address
    resource_port : str
        Resource Service port number
    timeout : float, optional
        Request timeout in seconds, by default 30.0
    """

    def __init__(self, resource_host: str, resource_port: str, timeout: float = 30.0) -> None:
        """Initialize resource client.

        Parameters
        ----------
        resource_host : str
            Resource Service host name or IP address
        resource_port : str
            Resource Service port number
        timeout : float, optional
            Request timeout in seconds, by default 30.0
        """
        base_url = self.build_uri(resource_host, resource_port, "resourceService")
        super().__init__(base_url, timeout)
        self._gateway_url = f"{base_url}/gateway"
        self._wq_url = f"{base_url}/workqueuegateway"
        self._log_url = f"{base_url}/logGateway"
        self._cal_url = f"{base_url}/calendarGateway"

    async def connect(self) -> None:
        """Connect to Resource Service and obtain session handle.

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

        if self._is_successful(response.text):
            self._handle = self._unwrap_xml(response.text)
            return

        # Fall back to default credentials
        response = await self._client.post(
            f"{self._gateway_url}",
            params={"action": "connect", "userid": self._DEFAULT_USERNAME, "password": self._DEFAULT_PASSWORD},
        )
        response.raise_for_status()

        if not self._is_successful(response.text):
            msg = "Failed to connect to YAWL Resource Service"
            raise httpx.HTTPError(msg)

        self._handle = self._unwrap_xml(response.text)

    async def disconnect(self) -> None:
        """Disconnect from Resource Service.

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
        """Check if connected to Resource Service.

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
            return self._is_successful(response.text)
        except httpx.HTTPError:
            return False

    async def get_build_properties(self) -> dict[str, str]:
        """Get Resource Service build properties.

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

        if not self._is_successful(response.text):
            msg = f"Failed to load resource service build properties: {self._unwrap_xml(response.text)}"
            raise httpx.HTTPError(msg)

        return self._parse_xml_properties(response.text)

    async def get_admin_work_queues(self) -> QueueSet:
        """Get admin work queues.

        Returns
        -------
        QueueSet
            Admin queue set

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._wq_url}", params={"action": "getAdminQueues", "sessionHandle": handle}
        )
        response.raise_for_status()
        return self._parse_queue_set(response.text)

    async def get_user_work_queues(self, participant_id: str) -> QueueSet:
        """Get participant work queues.

        Parameters
        ----------
        participant_id : str
            Participant identifier

        Returns
        -------
        QueueSet
            Participant queue set

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._wq_url}",
            params={"action": "getParticipantQueues", "participantID": participant_id, "sessionHandle": handle},
        )
        response.raise_for_status()
        return self._parse_queue_set(response.text)

    async def offer_item(self, item_id: str, participant_ids: set[str]) -> None:
        """Offer work item to participants.

        Parameters
        ----------
        item_id : str
            Work item identifier
        participant_ids : set[str]
            Set of participant identifiers

        Raises
        ------
        httpx.HTTPError
            If operation fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._wq_url}",
            params={
                "action": "offerItem",
                "workItemID": item_id,
                "participantIDs": ",".join(participant_ids),
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

    async def allocate_item(self, item_id: str, participant_id: str) -> None:
        """Allocate work item to participant.

        Parameters
        ----------
        item_id : str
            Work item identifier
        participant_id : str
            Participant identifier

        Raises
        ------
        httpx.HTTPError
            If operation fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._wq_url}",
            params={
                "action": "allocateItem",
                "workItemID": item_id,
                "participantID": participant_id,
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

    async def start_item(self, item_id: str, participant_id: str) -> None:
        """Start work item.

        Parameters
        ----------
        item_id : str
            Work item identifier
        participant_id : str
            Participant identifier

        Raises
        ------
        httpx.HTTPError
            If operation fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._wq_url}",
            params={
                "action": "startItem",
                "workItemID": item_id,
                "participantID": participant_id,
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

    async def complete_item(self, item_id: str, participant_id: str, data: str) -> None:
        """Complete work item.

        Parameters
        ----------
        item_id : str
            Work item identifier
        participant_id : str
            Participant identifier
        data : str
            Work item data XML

        Raises
        ------
        httpx.HTTPError
            If operation fails
        """
        handle = await self.get_handle()

        # Update work item data first
        await self._client.post(
            f"{self._wq_url}",
            params={"action": "updateWorkItemData", "workItemID": item_id, "data": data, "sessionHandle": handle},
        )

        # Complete the item
        response = await self._client.post(
            f"{self._wq_url}",
            params={
                "action": "completeItem",
                "workItemID": item_id,
                "participantID": participant_id,
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

    async def suspend_item(self, item_id: str, participant_id: str) -> None:
        """Suspend work item.

        Parameters
        ----------
        item_id : str
            Work item identifier
        participant_id : str
            Participant identifier

        Raises
        ------
        httpx.HTTPError
            If operation fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._wq_url}",
            params={
                "action": "suspendItem",
                "workItemID": item_id,
                "participantID": participant_id,
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

    async def unsuspend_item(self, item_id: str, participant_id: str) -> None:
        """Unsuspend work item.

        Parameters
        ----------
        item_id : str
            Work item identifier
        participant_id : str
            Participant identifier

        Raises
        ------
        httpx.HTTPError
            If operation fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._wq_url}",
            params={
                "action": "unsuspendItem",
                "workItemID": item_id,
                "participantID": participant_id,
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

    async def skip_item(self, item_id: str, participant_id: str) -> None:
        """Skip work item.

        Parameters
        ----------
        item_id : str
            Work item identifier
        participant_id : str
            Participant identifier

        Raises
        ------
        httpx.HTTPError
            If operation fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._wq_url}",
            params={
                "action": "skipItem",
                "workItemID": item_id,
                "participantID": participant_id,
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

    async def delegate_item(self, item_id: str, from_participant_id: str, to_participant_id: str) -> None:
        """Delegate work item to another participant.

        Parameters
        ----------
        item_id : str
            Work item identifier
        from_participant_id : str
            Source participant identifier
        to_participant_id : str
            Target participant identifier

        Raises
        ------
        httpx.HTTPError
            If operation fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._wq_url}",
            params={
                "action": "delegateItem",
                "workItemID": item_id,
                "fromParticipantID": from_participant_id,
                "toParticipantID": to_participant_id,
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

    async def get_participants(self) -> list[Participant]:
        """Get all participants.

        Returns
        -------
        list[Participant]
            List of participants

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._gateway_url}", params={"action": "getParticipants", "sessionHandle": handle}
        )
        response.raise_for_status()

        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.text)
        participants = []
        for p_elem in root.findall(".//participant"):
            participants.append(
                Participant(
                    id=p_elem.get("id", ""),
                    user_id=p_elem.findtext("userid", ""),
                    first_name=p_elem.findtext("firstname", ""),
                    last_name=p_elem.findtext("lastname", ""),
                    admin=p_elem.findtext("administrator", "false") == "true",
                )
            )
        return participants

    async def get_participant(self, user_name: str) -> Participant | None:
        """Get participant by username.

        Parameters
        ----------
        user_name : str
            User name

        Returns
        -------
        Participant | None
            Participant or None if admin or not found

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        if user_name == "admin":
            return None

        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._gateway_url}",
            params={"action": "getParticipantFromUserID", "userid": user_name, "sessionHandle": handle},
        )
        response.raise_for_status()

        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.text)
        p_elem = root.find(".//participant")
        if p_elem is None:
            return None

        return Participant(
            id=p_elem.get("id", ""),
            user_id=p_elem.findtext("userid", ""),
            first_name=p_elem.findtext("firstname", ""),
            last_name=p_elem.findtext("lastname", ""),
            admin=p_elem.findtext("administrator", "false") == "true",
        )

    async def get_user_privileges(self, participant_id: str) -> UserPrivileges:
        """Get user privileges.

        Parameters
        ----------
        participant_id : str
            Participant identifier

        Returns
        -------
        UserPrivileges
            User privileges

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._wq_url}",
            params={"action": "getUserPrivileges", "participantID": participant_id, "sessionHandle": handle},
        )
        response.raise_for_status()

        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.text)
        return UserPrivileges(
            can_choose_item_to_start=root.findtext("canChooseItemToStart", "false") == "true",
            can_start_concurrent=root.findtext("canStartConcurrent", "false") == "true",
            can_reorder=root.findtext("canReorder", "false") == "true",
            can_view_team_items=root.findtext("canViewTeamItems", "false") == "true",
            can_view_org_group_items=root.findtext("canViewOrgGroupItems", "false") == "true",
            can_chain=root.findtext("canChain", "false") == "true",
            can_manage_cases=root.findtext("canManageCases", "false") == "true",
        )

    @staticmethod
    def _parse_queue_set(xml: str) -> QueueSet:
        """Parse queue set from XML.

        Parameters
        ----------
        xml : str
            Queue set XML

        Returns
        -------
        QueueSet
            Parsed queue set
        """
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml)
        offered = []
        allocated = []
        started = []

        for queue_elem in root.findall(".//queue"):
            queue_type = queue_elem.get("type", "")
            items = []
            for item_elem in queue_elem.findall(".//workitem"):
                items.append(
                    {
                        "id": item_elem.get("id", ""),
                        "task": item_elem.findtext("task", ""),
                        "case": item_elem.findtext("case", ""),
                    }
                )

            if queue_type == "offered":
                offered = items
            elif queue_type == "allocated":
                allocated = items
            elif queue_type == "started":
                started = items

        return QueueSet(offered=offered, allocated=allocated, started=started)
