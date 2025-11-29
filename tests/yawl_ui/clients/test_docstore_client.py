"""Tests for YAWL Document Store client.

Tests verify:
- Document storage and retrieval
- Document removal
- Base64 encoding/decoding
"""

import base64

import pytest
from httpx import AsyncClient

from kgcl.yawl_ui.clients.docstore_client import DocStoreClient, YDocument


class MockResponse:
    """Mock HTTP response."""

    def __init__(self, text: str, status_code: int = 200) -> None:
        """Initialize mock response."""
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        """Raise for HTTP errors."""
        if self.status_code >= 400:
            from httpx import HTTPError

            raise HTTPError("HTTP error")


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock httpx AsyncClient."""
    test_content = b"Test document content"
    content_b64 = base64.b64encode(test_content).decode("ascii")

    responses: dict[str, str] = {
        "connect": "<success>handle-789</success>",
        "checkConnection": "<success>true</success>",
        "disconnect": "<success>disconnected</success>",
        "putDocument": "<success>42</success>",
        "getDocument": f"""<document>
            <name>test.pdf</name>
            <content>{content_b64}</content>
            <contentType>application/pdf</contentType>
        </document>""",
        "removeDocument": "<success>removed</success>",
    }

    async def mock_post(url: str, **kwargs: dict) -> MockResponse:
        action = kwargs.get("params", {}).get("action", "")
        return MockResponse(responses.get(action, "<failure>Unknown action</failure>"))

    monkeypatch.setattr(AsyncClient, "post", mock_post)


@pytest.mark.asyncio
async def test_connect_with_service_credentials(mock_client: None) -> None:
    """Test connecting with service credentials."""
    # Arrange
    client = DocStoreClient(docstore_host="localhost", docstore_port="8081")

    # Act
    await client.connect()

    # Assert
    assert client._handle == "handle-789"
    assert await client.connected()


@pytest.mark.asyncio
async def test_get_build_properties_returns_empty_dict(mock_client: None) -> None:
    """Test getting build properties returns empty dict."""
    # Arrange
    client = DocStoreClient(docstore_host="localhost", docstore_port="8081")
    await client.connect()

    # Act
    props = await client.get_build_properties()

    # Assert
    assert props == {}


@pytest.mark.asyncio
async def test_put_stored_document_returns_document_id(mock_client: None) -> None:
    """Test storing document returns document ID."""
    # Arrange
    client = DocStoreClient(docstore_host="localhost", docstore_port="8081")
    await client.connect()

    document = YDocument(doc_id=None, name="test.pdf", content=b"Test document content", content_type="application/pdf")

    # Act
    doc_id = await client.put_stored_document(document)

    # Assert
    assert doc_id == 42


@pytest.mark.asyncio
async def test_get_stored_document_returns_document(mock_client: None) -> None:
    """Test retrieving document returns document."""
    # Arrange
    client = DocStoreClient(docstore_host="localhost", docstore_port="8081")
    await client.connect()

    # Act
    document = await client.get_stored_document(42)

    # Assert
    assert isinstance(document, YDocument)
    assert document.doc_id == 42
    assert document.name == "test.pdf"
    assert document.content == b"Test document content"
    assert document.content_type == "application/pdf"


@pytest.mark.asyncio
async def test_remove_stored_document_sends_request(mock_client: None) -> None:
    """Test removing document sends request."""
    # Arrange
    client = DocStoreClient(docstore_host="localhost", docstore_port="8081")
    await client.connect()

    # Act
    await client.remove_stored_document(42)

    # Assert - No exception raised means success


def test_ydocument_is_immutable() -> None:
    """Test YDocument is immutable."""
    # Arrange
    document = YDocument(doc_id=42, name="test.pdf", content=b"Test content", content_type="application/pdf")

    # Act & Assert
    with pytest.raises(AttributeError):
        document.doc_id = 43  # type: ignore


def test_ydocument_handles_binary_content() -> None:
    """Test YDocument handles binary content correctly."""
    # Arrange
    binary_content = bytes([0x00, 0x01, 0x02, 0xFF, 0xFE, 0xFD])

    # Act
    document = YDocument(
        doc_id=None, name="binary.dat", content=binary_content, content_type="application/octet-stream"
    )

    # Assert
    assert document.content == binary_content
    assert len(document.content) == 6
