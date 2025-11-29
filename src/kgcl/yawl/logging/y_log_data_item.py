"""Log data item for event logging (mirrors Java YLogDataItem).

Represents a single data item logged with an event.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree as ET

from kgcl.yawl.util.string_util import StringUtil
from kgcl.yawl.util.xml.jdom_util import JDOMUtil


@dataclass
class YLogDataItem:
    """Log data item (mirrors Java YLogDataItem).

    Represents a single data item that can be logged with an event.
    Contains name, value, data type information, and a descriptor.

    Parameters
    ----------
    descriptor : str
        Descriptor string (class, category, or group)
    name : str
        Data item name
    value : str
        Data item value
    data_type_name : str
        Data type name
    data_type_definition : str
        Data type definition (schema)

    Examples
    --------
    >>> item = YLogDataItem("input", "customerId", "12345", "string")
    >>> item.get_name()
    'customerId'
    >>> item.get_value()
    '12345'
    """

    descriptor: str = ""
    name: str = ""
    value: str = ""
    data_type_name: str = ""
    data_type_definition: str = ""

    def __init__(
        self,
        descriptor: str = "",
        name: str = "",
        value: str = "",
        data_type: str = "",
        data_type_definition: str | None = None,
        xml: str | ET.Element | None = None,
    ) -> None:
        """Initialize log data item.

        Parameters
        ----------
        descriptor : str
            Descriptor string
        name : str
            Data item name
        value : str
            Data item value
        data_type : str
            Data type name
        data_type_definition : str | None
            Data type definition (defaults to data_type if None)
        xml : str | ET.Element | None
            XML string or element to parse from
        """
        if xml is not None:
            if isinstance(xml, str):
                self.from_xml(xml)
            else:
                self.from_xml_element(xml)
        else:
            self.descriptor = descriptor
            self.name = name
            self.value = value
            self.data_type_name = data_type
            self.data_type_definition = data_type_definition if data_type_definition else data_type

    def get_name(self) -> str:
        """Get data item name.

        Java signature: String getName()

        Returns
        -------
        str
            Data item name
        """
        return self.name

    def set_name(self, name: str) -> None:
        """Set data item name.

        Java signature: void setName(String name)

        Parameters
        ----------
        name : str
            Data item name
        """
        self.name = name

    def get_value(self) -> str:
        """Get data item value.

        Java signature: String getValue()

        Returns
        -------
        str
            Data item value
        """
        return self.value

    def set_value(self, value: str | object) -> None:
        """Set data item value.

        Java signature: void setValue(String value)
        Java signature: void setValue(Object value)

        Parameters
        ----------
        value : str | object
            Data item value (converted to string if object)
        """
        self.value = str(value)

    def get_data_type_name(self) -> str:
        """Get data type name.

        Java signature: String getDataTypeName()

        Returns
        -------
        str
            Data type name
        """
        return self.data_type_name

    def set_data_type_name(self, data_type_name: str) -> None:
        """Set data type name.

        Java signature: void setDataTypeName(String dataTypeName)

        Parameters
        ----------
        data_type_name : str
            Data type name
        """
        self.data_type_name = data_type_name

    def get_descriptor(self) -> str:
        """Get descriptor.

        Java signature: String getDescriptor()

        Returns
        -------
        str
            Descriptor string
        """
        return self.descriptor

    def set_descriptor(self, descriptor: str) -> None:
        """Set descriptor.

        Java signature: void setDescriptor(String descriptor)

        Parameters
        ----------
        descriptor : str
            Descriptor string
        """
        self.descriptor = descriptor

    def get_data_type_definition(self) -> str:
        """Get data type definition.

        Java signature: String getDataTypeDefinition()

        Returns
        -------
        str
            Data type definition (schema)
        """
        return self.data_type_definition

    def set_data_type_definition(self, data_type_definition: str) -> None:
        """Set data type definition.

        Java signature: void setDataTypeDefinition(String dataTypeDefinition)

        Parameters
        ----------
        data_type_definition : str
            Data type definition
        """
        self.data_type_definition = data_type_definition

    def to_xml(self) -> str:
        """Convert to XML.

        Java signature: String toXML()

        Returns
        -------
        str
            XML representation
        """
        xml_parts: list[str] = []
        xml_parts.append("<logdataitem>")
        xml_parts.append(self.to_xml_short())
        xml_parts.append(StringUtil.wrap_escaped(self.data_type_name, "datatype"))
        xml_parts.append(StringUtil.wrap_escaped(self.data_type_definition, "datatypedefinition"))
        xml_parts.append("</logdataitem>")
        return "".join(xml_parts)

    def to_xml_short(self) -> str:
        """Convert to short XML (without data type info).

        Java signature: String toXMLShort()

        Returns
        -------
        str
            Short XML representation
        """
        xml_parts: list[str] = []
        xml_parts.append(StringUtil.wrap_escaped(self.name, "name"))
        xml_parts.append(StringUtil.wrap_escaped(self.value, "value"))
        xml_parts.append(StringUtil.wrap_escaped(self.descriptor, "descriptor"))
        return "".join(xml_parts)

    def from_xml(self, xml: str) -> None:
        """Parse from XML string.

        Java signature: private void fromXML(String xml)

        Parameters
        ----------
        xml : str
            XML string
        """
        element = JDOMUtil.string_to_element(xml)
        self.from_xml_element(element)

    def from_xml_element(self, element: ET.Element | None) -> None:
        """Parse from XML element.

        Java signature: private void fromXML(Element e)

        Parameters
        ----------
        element : ET.Element | None
            XML element
        """
        if element is not None:
            self.name = JDOMUtil.decode_escapes(element.findtext("name") or "")
            self.value = JDOMUtil.decode_escapes(element.findtext("value") or "")
            self.descriptor = JDOMUtil.decode_escapes(element.findtext("descriptor") or "")
            self.data_type_name = JDOMUtil.decode_escapes(element.findtext("datatype") or "")
            self.data_type_definition = JDOMUtil.decode_escapes(element.findtext("datatypedefinition") or "")


