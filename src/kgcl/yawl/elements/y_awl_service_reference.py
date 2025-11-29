"""YAWL service reference (mirrors Java YAWLServiceReference).

Represents a server-side reference to a YAWL Custom Service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from kgcl.yawl.elements.y_verifiable import YVerifiable
from kgcl.yawl.engine.y_engine import YEngine, YVerificationHandler

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_decomposition import YWebServiceGateway


@dataclass
class YAWLServiceReference(YVerifiable):
    """Server-side reference to a YAWL Custom Service.

    Parameters
    ----------
    service_id : str
        Unique service URI/ID
    service_name : str
        Service name (username)
    service_password : str
        Service password
    documentation : str
        Service documentation
    assignable : bool
        Whether service can be assigned to a task
    web_service_gateway : YWebServiceGateway | None
        Associated web service gateway

    Examples
    --------
    >>> service = YAWLServiceReference(
    ...     service_id="http://example.com/service", service_name="MyService", service_password="secret"
    ... )
    >>> service.get_scheme()
    'http'
    """

    service_id: str
    service_name: str = ""
    service_password: str = ""
    documentation: str = ""
    assignable: bool = True
    web_service_gateway: YWebServiceGateway | None = field(default=None, repr=False)

    def get_service_id(self) -> str:
        """Get service ID.

        Returns
        -------
        str
            Service ID/URI
        """
        return self.service_id

    def get_uri(self) -> str:
        """Get service URI.

        Returns
        -------
        str
            Service URI (same as service_id)
        """
        return self.service_id

    def get_scheme(self) -> str | None:
        """Get URI scheme (protocol).

        Returns
        -------
        str | None
            Scheme component (e.g., "http", "https"), or None if no scheme
        """
        pos = self.service_id.find(":")
        return self.service_id[:pos] if pos > -1 else None

    def can_be_assigned_to_task(self) -> bool:
        """Check if service can be assigned to a task.

        Returns
        -------
        bool
            True if assignable
        """
        return self.assignable

    def verify(self, handler: YVerificationHandler) -> None:
        """Verify service is registered with engine.

        Parameters
        ----------
        handler : YVerificationHandler
            Verification handler to report issues
        """
        try:
            if YEngine.is_running():
                engine = YEngine.get_instance()
                service = engine.get_registered_yawl_service(self.service_id)
                if service is None:
                    gateway_info = ""
                    if self.web_service_gateway:
                        gateway_info = f"at WSGateway [{self.web_service_gateway.id}] "
                    handler.warn(self, f"YAWL service [{self.service_id}] {gateway_info}is not registered with engine.")
        except Exception:
            # May occur if called in standalone mode (e.g., from editor)
            # caused by call to static YEngine - ok to ignore
            pass

    def to_xml(self) -> str:
        """Serialize to XML (basic format).

        Returns
        -------
        str
            XML representation
        """
        root = ET.Element("yawlService")
        root.set("id", self.service_id)
        if self.documentation:
            ET.SubElement(root, "documentation").text = self.documentation
        return ET.tostring(root, encoding="unicode")

    def to_xml_complete(self) -> str:
        """Serialize to XML (complete format with credentials).

        Returns
        -------
        str
            Complete XML representation
        """
        root = ET.Element("yawlService")
        root.set("id", self.service_id)
        if self.documentation:
            ET.SubElement(root, "documentation").text = self.documentation
        ET.SubElement(root, "servicename").text = self.service_name
        ET.SubElement(root, "servicepassword").text = self.service_password
        ET.SubElement(root, "assignable").text = "true" if self.assignable else "false"
        return ET.tostring(root, encoding="unicode")

    def from_xml(self, xml: str) -> None:
        """Deserialize from XML.

        Parameters
        ----------
        xml : str
            XML string to parse
        """
        root = ET.fromstring(xml)
        self.service_id = root.get("id", "")
        doc_elem = root.find("documentation")
        self.documentation = doc_elem.text if doc_elem is not None else ""
        name_elem = root.find("servicename")
        self.service_name = name_elem.text if name_elem is not None else ""
        pass_elem = root.find("servicepassword")
        self.service_password = pass_elem.text if pass_elem is not None else ""
        assign_elem = root.find("assignable")
        assign_str = assign_elem.text if assign_elem is not None else None
        self.assignable = assign_str is not None and assign_str.lower() == "true"

    @classmethod
    def unmarshal(cls, serialised_service: str) -> YAWLServiceReference | None:
        """Create service reference from XML.

        Parameters
        ----------
        serialised_service : str
            XML string

        Returns
        -------
        YAWLServiceReference | None
            Service reference, or None if XML invalid
        """
        try:
            root = ET.fromstring(serialised_service)
            uri = root.get("id")
            if not uri:
                return None

            name_elem = root.find("servicename")
            name = name_elem.text if name_elem is not None else ""

            pass_elem = root.find("servicepassword")
            password = pass_elem.text if pass_elem is not None else ""

            doc_elem = root.find("documentation")
            doc_str = doc_elem.text if doc_elem is not None else ""

            assign_elem = root.find("assignable")
            assign_str = assign_elem.text if assign_elem is not None else None

            service = cls(service_id=uri, service_name=name, service_password=password)
            service.documentation = doc_str
            if assign_str is not None:
                service.assignable = assign_str.lower() == "true"

            return service
        except Exception:
            return None

    def __eq__(self, other: object) -> bool:
        """Equality by service ID."""
        if not isinstance(other, YAWLServiceReference):
            return NotImplemented
        if self.service_id:
            return self.service_id == other.service_id
        return super().__eq__(other)

    def __hash__(self) -> int:
        """Hash by service ID."""
        return hash(self.service_id) if self.service_id else hash(id(self))
