"""Log data item list for event logging (mirrors Java YLogDataItemList).

Container for multiple log data items.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from kgcl.yawl.logging.y_log_data_item import YLogDataItem
from kgcl.yawl.util.xml.jdom_util import JDOMUtil


class YLogDataItemList(list[YLogDataItem]):
    """Log data item list (mirrors Java YLogDataItemList).

    Extends list to provide XML serialization for log data items.

    Examples
    --------
    >>> items = YLogDataItemList()
    >>> items.append(YLogDataItem("input", "customerId", "12345", "string"))
    >>> xml = items.to_xml()
    >>> "customerId" in xml
    True
    """

    def __init__(self, first_item: YLogDataItem | None = None, xml: str | ET.Element | None = None) -> None:
        """Initialize log data item list.

        Parameters
        ----------
        first_item : YLogDataItem | None
            First item to add (optional)
        xml : str | ET.Element | None
            XML string or element to parse from
        """
        super().__init__()
        if xml is not None:
            if isinstance(xml, str):
                self.from_xml(xml)
            else:
                self.from_xml(JDOMUtil.element_to_string(xml))
        elif first_item is not None:
            self.append(first_item)

    def to_xml(self) -> str:
        """Convert to XML.

        Java signature: String toXML()

        Returns
        -------
        str
            XML representation
        """
        xml_parts: list[str] = []
        xml_parts.append("<logdataitemlist>")
        for item in self:
            xml_parts.append(item.to_xml())
        xml_parts.append("</logdataitemlist>")
        return "".join(xml_parts)

    def from_xml(self, xml: str) -> None:
        """Parse from XML string.

        Java signature: void fromXML(String xml)

        Parameters
        ----------
        xml : str
            XML string
        """
        element = JDOMUtil.string_to_element(xml)
        if element is not None:
            for child in element:
                self.append(YLogDataItem(xml=child))


