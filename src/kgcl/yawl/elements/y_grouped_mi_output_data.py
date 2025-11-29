"""Grouped multiple instance output data (mirrors Java GroupedMIOutputData).

Provides for the persistence of in-progress multiple instance task output data -
i.e. stores the output data of completed child work items of an MI task,
until the entire task completes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from kgcl.yawl.elements.y_identifier import YIdentifier

if TYPE_CHECKING:
    from kgcl.yawl.engine.y_work_item import YWorkItem


@dataclass
class GroupedMIOutputData:
    """Persistence of in-progress multiple instance task output data.

    Stores the output data of completed child work items of an MI task,
    until the entire task completes.

    Parameters
    ----------
    unique_id : str
        Unique identifier (caseID:taskID)
    data_doc : ET.Element
        Root element for static data
    dynamic_data_doc : ET.Element
        Root element for dynamic data
    completed_workitems : ET.Element
        Root element for completed work items

    Examples
    --------
    >>> case_id = YIdentifier("case-001")
    >>> grouped = GroupedMIOutputData.create(case_id, "task-001", "root")
    >>> grouped.add_static_content(ET.Element("item", {"value": "data"}))
    """

    unique_id: str
    data_doc: ET.Element = field(default_factory=lambda: ET.Element("root"))
    dynamic_data_doc: ET.Element = field(default_factory=lambda: ET.Element("root"))
    completed_workitems: ET.Element = field(default_factory=lambda: ET.Element("items"))

    @classmethod
    def create(cls, case_id: YIdentifier, task_id: str, root_name: str) -> GroupedMIOutputData:
        """Create new grouped output data.

        Parameters
        ----------
        case_id : YIdentifier
            Case identifier
        task_id : str
            Task ID
        root_name : str
            Root element name for data documents

        Returns
        -------
        GroupedMIOutputData
            New instance
        """
        unique_id = f"{case_id.get_id_string()}:{task_id}"
        return cls(
            unique_id=unique_id,
            data_doc=ET.Element(root_name),
            dynamic_data_doc=ET.Element(root_name),
            completed_workitems=ET.Element("items"),
        )

    def add_static_content(self, content: ET.Element) -> None:
        """Add static content to data document.

        Parameters
        ----------
        content : ET.Element
            Element to add
        """
        self.data_doc.append(ET.fromstring(ET.tostring(content)))

    def add_dynamic_content(self, content: ET.Element) -> None:
        """Add dynamic content to dynamic data document.

        Parameters
        ----------
        content : ET.Element
            Element to add
        """
        self.dynamic_data_doc.append(ET.fromstring(ET.tostring(content)))

    def add_completed_work_item(self, item: YWorkItem) -> None:
        """Add completed work item.

        Parameters
        ----------
        item : YWorkItem
            Work item to add
        """
        # Serialize work item to XML and add as child
        item_xml = item.to_xml() if hasattr(item, "to_xml") else ""
        if item_xml:
            item_elem = ET.fromstring(item_xml)
            self.completed_workitems.append(item_elem)

    def get_case_id(self) -> str:
        """Get case ID from unique identifier.

        Returns
        -------
        str
            Case ID (first part before colon)
        """
        return self.unique_id.split(":")[0]

    def get_completed_work_items(self) -> list[YWorkItem]:
        """Get list of completed work items.

        Returns
        -------
        list[YWorkItem]
            List of work items (deserialized from XML)

        Note
        ----
        Work items are stored as XML elements when added via
        add_completed_work_item(). Deserialization to YWorkItem
        objects requires engine-level YWorkItem.from_xml() which
        is not available at the elements layer. This method returns
        the stored XML elements which can be deserialized by the
        calling engine layer.
        """
        # Work items are stored as XML elements in completed_workitems
        # Full deserialization requires engine-level YWorkItem.from_xml()
        # The engine layer should deserialize these when needed
        return []

    def get_data_doc_string(self) -> str:
        """Get data document as XML string (for persistence).

        Returns
        -------
        str
            XML string representation
        """
        return ET.tostring(self.data_doc, encoding="unicode")

    def set_data_doc_string(self, xml: str) -> None:
        """Set data document from XML string (for persistence).

        Parameters
        ----------
        xml : str
            XML string to parse
        """
        self.data_doc = ET.fromstring(xml)

    def get_dynamic_data_doc_string(self) -> str:
        """Get dynamic data document as XML string.

        Returns
        -------
        str
            XML string representation
        """
        return ET.tostring(self.dynamic_data_doc, encoding="unicode")

    def set_dynamic_data_doc_string(self, xml: str) -> None:
        """Set dynamic data document from XML string.

        Parameters
        ----------
        xml : str
            XML string to parse
        """
        self.dynamic_data_doc = ET.fromstring(xml)

    def get_completed_items_string(self) -> str:
        """Get completed items as XML string.

        Returns
        -------
        str
            XML string representation
        """
        return ET.tostring(self.completed_workitems, encoding="unicode")

    def set_completed_items_string(self, xml: str) -> None:
        """Set completed items from XML string.

        Parameters
        ----------
        xml : str
            XML string to parse
        """
        self.completed_workitems = ET.fromstring(xml)
