"""JDOM utility functions using ElementTree.

Pythonic equivalents to JDOMUtil.java, using xml.etree.ElementTree
instead of JDOM for XML manipulation.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

logger = logging.getLogger(__name__)

UTF8_BOM = "\ufeff"


def document_to_string(doc: ET.ElementTree | None, pretty: bool = True) -> str | None:
    """Convert ElementTree Document to string.

    Parameters
    ----------
    doc : ET.ElementTree | None
        ElementTree document
    pretty : bool, optional
        Whether to pretty-print, by default True

    Returns
    -------
    str | None
        XML string, or None if doc is None
    """
    if doc is None:
        return None

    root = doc.getroot()
    return element_to_string(root, pretty)


def document_to_string_dump(doc: ET.ElementTree | None) -> str | None:
    """Convert ElementTree Document to compact string.

    Parameters
    ----------
    doc : ET.ElementTree | None
        ElementTree document

    Returns
    -------
    str | None
        Compact XML string, or None if doc is None
    """
    return document_to_string(doc, pretty=False)


def element_to_string(elem: Element | None, pretty: bool = True) -> str | None:
    """Convert ElementTree Element to string.

    Parameters
    ----------
    elem : Element | None
        ElementTree element
    pretty : bool, optional
        Whether to pretty-print, by default True

    Returns
    -------
    str | None
        XML string, or None if elem is None
    """
    if elem is None:
        return None

    # ElementTree doesn't have built-in pretty printing, so we use a workaround
    if pretty:
        _indent(elem)

    return ET.tostring(elem, encoding="unicode")


def element_to_string_dump(elem: Element | None) -> str | None:
    """Convert ElementTree Element to compact string.

    Parameters
    ----------
    elem : Element | None
        ElementTree element

    Returns
    -------
    str | None
        Compact XML string, or None if elem is None
    """
    return element_to_string(elem, pretty=False)


def string_to_document(s: str | None) -> ET.ElementTree | None:
    """Convert XML string to ElementTree Document.

    Parameters
    ----------
    s : str | None
        XML string

    Returns
    -------
    ET.ElementTree | None
        ElementTree document, or None if parsing fails
    """
    if s is None:
        return None

    # Remove UTF-8 BOM if present
    if s.startswith(UTF8_BOM):
        s = s[1:]

    try:
        root = ET.fromstring(s)
        return ET.ElementTree(root)
    except ET.ParseError as e:
        logger.error("ParseError converting to Document, String = %s", s, exc_info=e)
        return None
    except Exception as e:
        logger.error("Error converting to Document, String = %s", s, exc_info=e)
        return None


def string_to_document_uncaught(s: str | None) -> ET.ElementTree:
    """Convert XML string to ElementTree Document (raises exceptions).

    Parameters
    ----------
    s : str | None
        XML string

    Returns
    -------
    ET.ElementTree
        ElementTree document

    Raises
    ------
    ValueError
        If s is None
    ET.ParseError
        If XML is malformed
    """
    if s is None:
        raise ValueError("Attempt to convert null string to document")

    # Remove UTF-8 BOM if present
    if s.startswith(UTF8_BOM):
        s = s[1:]

    root = ET.fromstring(s)
    return ET.ElementTree(root)


def string_to_element(s: str | None) -> Element | None:
    """Convert XML string to ElementTree Element.

    Parameters
    ----------
    s : str | None
        XML string

    Returns
    -------
    Element | None
        Root element, or None if parsing fails
    """
    if s is None:
        return None

    doc = string_to_document(s)
    return doc.getroot() if doc is not None else None


def file_to_document(path: str | Path) -> ET.ElementTree | None:
    """Load XML file into ElementTree Document.

    Parameters
    ----------
    path : str | Path
        File path

    Returns
    -------
    ET.ElementTree | None
        ElementTree document, or None if file doesn't exist or parsing fails
    """
    file_path = Path(path)
    if not file_path.exists():
        return None

    try:
        tree = ET.parse(file_path)
        return tree
    except ET.ParseError as e:
        logger.error("ParseError loading file into Document, filepath = %s", file_path.absolute(), exc_info=e)
        return None
    except Exception as e:
        logger.error("Error loading file into Document, filepath = %s", file_path.absolute(), exc_info=e)
        return None


def document_to_file(doc: ET.ElementTree | None, path: str | Path) -> None:
    """Save ElementTree Document to file.

    Parameters
    ----------
    doc : ET.ElementTree | None
        ElementTree document
    path : str | Path
        File path
    """
    if doc is None:
        return

    try:
        file_path = Path(path)
        # Pretty print by indenting
        _indent(doc.getroot())
        doc.write(file_path, encoding="utf-8", xml_declaration=True)
    except Exception as e:
        logger.error("IO Exception in saving Document to file, filepath = %s", path, exc_info=e)


def get_default_value_for_type(data_type: str | None) -> str:
    """Get default value for an XSD data type.

    Parameters
    ----------
    data_type : str | None
        XSD data type name

    Returns
    -------
    str
        Default value string
    """
    if data_type is None:
        return "null"

    data_type_lower = data_type.lower()
    if data_type_lower == "boolean":
        return "false"
    elif data_type_lower == "string":
        return ""
    else:
        # For other built-in types, return "0"
        # Note: XSDType.isBuiltInType check would require schema module
        return "0"


def encode_escapes(s: str | None) -> str | None:
    """Encode XML special characters.

    Parameters
    ----------
    s : str | None
        String to encode

    Returns
    -------
    str | None
        Encoded string, or None if input is None
    """
    if s is None:
        return None

    result: list[str] = []
    for char in s:
        if char == "'":
            result.append("&apos;")
        elif char == '"':
            result.append("&quot;")
        elif char == ">":
            result.append("&gt;")
        elif char == "<":
            result.append("&lt;")
        elif char == "&":
            result.append("&amp;")
        else:
            result.append(char)

    return "".join(result)


def encode_attribute_escapes(attr_value: str | None) -> str | None:
    """Encode XML attribute value escapes.

    Parameters
    ----------
    attr_value : str | None
        Attribute value to encode

    Returns
    -------
    str | None
        Encoded attribute value, or None if input is None
    """
    if attr_value is None:
        return None

    # Use ElementTree's built-in escaping for attributes
    # Create a temporary element to leverage ET's escaping
    temp_elem = ET.Element("temp")
    temp_elem.set("key", attr_value)
    return temp_elem.get("key")


def decode_attribute_escapes(attr_value: str | None) -> str | None:
    """Decode XML attribute value escapes.

    Parameters
    ----------
    attr_value : str | None
        Attribute value to decode

    Returns
    -------
    str | None
        Decoded attribute value, or None if input is None
    """
    if attr_value is None:
        return None

    # Parse as XML to decode
    temp = f'<temp key="{attr_value}"/>'
    try:
        elem = ET.fromstring(temp)
        return elem.get("key")
    except Exception:
        return attr_value


def decode_escapes(s: str | None) -> str | None:
    """Decode XML special characters.

    Parameters
    ----------
    s : str | None
        String to decode

    Returns
    -------
    str | None
        Decoded string, or None if input is None
    """
    if s is None or "&" not in s:
        return s

    return (
        s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&")
    )


def select_element(doc: ET.ElementTree | Element, path: str, namespace: dict[str, str] | None = None) -> Element | None:
    """Select first element matching XPath expression.

    Parameters
    ----------
    doc : ET.ElementTree | Element
        Document or element to search
    path : str
        XPath expression
    namespace : dict[str, str] | None, optional
        Namespace mapping, by default None

    Returns
    -------
    Element | None
        First matching element, or None if not found
    """
    if isinstance(doc, ET.ElementTree):
        root = doc.getroot()
    else:
        root = doc

    try:
        # ElementTree supports limited XPath
        matches = root.findall(path, namespace or {})
        return matches[0] if matches else None
    except Exception:
        return None


def select_element_list(
    doc: ET.ElementTree | Element, path: str, namespace: dict[str, str] | None = None
) -> list[Element]:
    """Select all elements matching XPath expression.

    Parameters
    ----------
    doc : ET.ElementTree | Element
        Document or element to search
    path : str
        XPath expression
    namespace : dict[str, str] | None, optional
        Namespace mapping, by default None

    Returns
    -------
    list[Element]
        List of matching elements
    """
    if isinstance(doc, ET.ElementTree):
        root = doc.getroot()
    else:
        root = doc

    try:
        return root.findall(path, namespace or {})
    except Exception:
        return []


def format_xml_string(s: str | None) -> str | None:
    """Format XML string (pretty print).

    Parameters
    ----------
    s : str | None
        XML string to format

    Returns
    -------
    str | None
        Formatted XML string, or None if input is None
    """
    if s is None:
        return None

    if s.strip().startswith("<?xml"):
        return format_xml_string_as_document(s)
    else:
        return format_xml_string_as_element(s)


def format_xml_string_as_document(s: str | None) -> str | None:
    """Format XML string as document.

    Parameters
    ----------
    s : str | None
        XML string

    Returns
    -------
    str | None
        Formatted document string
    """
    if s is None:
        return None

    doc = string_to_document(s)
    return document_to_string(doc) if doc else None


def format_xml_string_as_element(s: str | None) -> str | None:
    """Format XML string as element.

    Parameters
    ----------
    s : str | None
        XML string

    Returns
    -------
    str | None
        Formatted element string
    """
    if s is None:
        return None

    elem = string_to_element(s)
    return element_to_string(elem) if elem else None


def strip(s: str | None) -> str | None:
    """Extract text content from XML string.

    Parameters
    ----------
    s : str | None
        XML string

    Returns
    -------
    str | None
        Text content, or original string if parsing fails
    """
    if s is None:
        return None

    elem = string_to_element(s)
    if elem is not None:
        return elem.text or ""

    return s


def strip_attributes(elem: Element) -> Element:
    """Remove all attributes from element and children recursively.

    Parameters
    ----------
    elem : Element
        Element to strip

    Returns
    -------
    Element
        Element with attributes removed
    """
    # Clear attributes
    elem.attrib.clear()

    # Recurse to children
    for child in elem:
        strip_attributes(child)

    return elem


def _indent(elem: Element, level: int = 0) -> None:
    """Add indentation to element tree for pretty printing.

    Parameters
    ----------
    elem : Element
        Element to indent
    level : int, optional
        Current indentation level, by default 0
    """
    indent = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
    elif level and (not elem.tail or not elem.tail.strip()):
        elem.tail = indent
