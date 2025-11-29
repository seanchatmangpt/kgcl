"""YAWL Document Store client for document management.

Provides async client for YAWL Document Store operations:
- Document storage and retrieval
- Document removal
"""

from dataclasses import dataclass

import httpx

from kgcl.yawl_ui.clients.base_client import AbstractClient


@dataclass(frozen=True)
class YDocument:
    """YAWL document information."""

    doc_id: int | None
    name: str
    content: bytes
    content_type: str


class DocStoreClient(AbstractClient):
    """YAWL Document Store client.

    Provides async interface to:
    - Store documents
    - Retrieve documents
    - Remove documents

    Parameters
    ----------
    docstore_host : str
        Document Store host name or IP address
    docstore_port : str
        Document Store port number
    timeout : float, optional
        Request timeout in seconds, by default 30.0
    """

    def __init__(self, docstore_host: str, docstore_port: str, timeout: float = 30.0) -> None:
        """Initialize document store client.

        Parameters
        ----------
        docstore_host : str
            Document Store host name or IP address
        docstore_port : str
            Document Store port number
        timeout : float, optional
            Request timeout in seconds, by default 30.0
        """
        base_url = self.build_uri(docstore_host, docstore_port, "documentStore")
        super().__init__(base_url, timeout)

    async def connect(self) -> None:
        """Connect to Document Store and obtain session handle.

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
            f"{self._base_url}",
            params={"action": "connect", "userid": self._SERVICE_USERNAME, "password": self._SERVICE_PASSWORD},
        )
        response.raise_for_status()

        if self._is_successful(response.text):
            self._handle = self._unwrap_xml(response.text)
            return

        # Fall back to default credentials
        response = await self._client.post(
            f"{self._base_url}",
            params={"action": "connect", "userid": self._DEFAULT_USERNAME, "password": self._DEFAULT_PASSWORD},
        )
        response.raise_for_status()

        if not self._is_successful(response.text):
            msg = "Failed to connect to YAWL Document Store"
            raise httpx.HTTPError(msg)

        self._handle = self._unwrap_xml(response.text)

    async def disconnect(self) -> None:
        """Disconnect from Document Store.

        Raises
        ------
        httpx.HTTPError
            If disconnection fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._base_url}", params={"action": "disconnect", "sessionHandle": handle}
        )
        response.raise_for_status()
        self._handle = None

    async def connected(self) -> bool:
        """Check if connected to Document Store.

        Returns
        -------
        bool
            True if connected, False otherwise
        """
        if self._handle is None:
            return False

        try:
            response = await self._client.post(
                f"{self._base_url}", params={"action": "checkConnection", "sessionHandle": self._handle}
            )
            response.raise_for_status()
            return self._is_successful(response.text)
        except httpx.HTTPError:
            return False

    async def get_build_properties(self) -> dict[str, str]:
        """Get Document Store build properties.

        Returns
        -------
        dict[str, str]
            Empty dictionary (Document Store doesn't provide build properties)
        """
        return {}

    async def get_stored_document(self, doc_id: int) -> YDocument:
        """Get stored document by ID.

        Parameters
        ----------
        doc_id : int
            Document identifier

        Returns
        -------
        YDocument
            Document information and content

        Raises
        ------
        httpx.HTTPError
            If retrieval fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._base_url}", params={"action": "getDocument", "documentID": str(doc_id), "sessionHandle": handle}
        )
        response.raise_for_status()

        import xml.etree.ElementTree as ET

        root = ET.fromstring(response.text)
        doc_elem = root.find(".//document")
        if doc_elem is None:
            msg = "Document not found"
            raise httpx.HTTPError(msg)

        import base64

        return YDocument(
            doc_id=doc_id,
            name=doc_elem.findtext("name", ""),
            content=base64.b64decode(doc_elem.findtext("content", "")),
            content_type=doc_elem.findtext("contentType", "application/octet-stream"),
        )

    async def put_stored_document(self, document: YDocument) -> int:
        """Store document.

        Parameters
        ----------
        document : YDocument
            Document to store

        Returns
        -------
        int
            Document identifier

        Raises
        ------
        httpx.HTTPError
            If storage fails
        """
        handle = await self.get_handle()

        import base64

        content_b64 = base64.b64encode(document.content).decode("ascii")

        response = await self._client.post(
            f"{self._base_url}",
            params={
                "action": "putDocument",
                "name": document.name,
                "content": content_b64,
                "contentType": document.content_type,
                "sessionHandle": handle,
            },
        )
        response.raise_for_status()

        if not self._is_successful(response.text):
            msg = self._unwrap_xml(response.text)
            raise httpx.HTTPError(msg)

        return int(self._unwrap_xml(response.text))

    async def remove_stored_document(self, doc_id: int) -> None:
        """Remove stored document.

        Parameters
        ----------
        doc_id : int
            Document identifier

        Raises
        ------
        httpx.HTTPError
            If removal fails
        """
        handle = await self.get_handle()
        response = await self._client.post(
            f"{self._base_url}", params={"action": "removeDocument", "documentID": str(doc_id), "sessionHandle": handle}
        )
        response.raise_for_status()
