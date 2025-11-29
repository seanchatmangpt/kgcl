"""DOM utility functions using ElementTree and lxml.

Pythonic equivalents to DOMUtil.java for DOM manipulation, XPath queries,
and XSLT transformations.
"""

from __future__ import annotations

import io
import logging
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

try:
    from lxml import etree

    HAS_LXML = True
except ImportError:
    HAS_LXML = False

logger = logging.getLogger(__name__)

_EMPTY_ELEMENT_REMOVAL_XSLT = """<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0">
    <xsl:template match="@*|*">
        <xsl:copy>
            <xsl:apply-templates select="@*|*|text()"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="*[not(.//text())]"/>
</xsl:stylesheet>"""

_empty_element_xslt: object | None = None


def get_document_from_string(xml: str) -> ET.ElementTree:
    """Convert XML string to ElementTree Document.

    Parameters
    ----------
    xml : str
        XML string to parse

    Returns
    -------
    ET.ElementTree
        ElementTree document

    Raises
    ------
    ET.ParseError
        If XML is malformed
    """
    root = ET.fromstring(xml)
    return ET.ElementTree(root)


def create_document_instance() -> ET.ElementTree:
    """Create a new namespace-aware Document.

    Returns
    -------
    ET.ElementTree
        New empty document
    """
    root = ET.Element("root")
    return ET.ElementTree(root)


def create_namespaceless_document_instance() -> ET.ElementTree:
    """Create a new document (namespace handling same as above in ElementTree).

    Returns
    -------
    ET.ElementTree
        New empty document
    """
    # ElementTree doesn't distinguish namespace-aware vs not
    return create_document_instance()


def get_namespaceless_document_from_string(xml: str) -> ET.ElementTree:
    """Get document from string without namespace processing.

    Parameters
    ----------
    xml : str
        XML string

    Returns
    -------
    ET.ElementTree
        ElementTree document
    """
    # ElementTree always processes namespaces, but we can ignore them
    return get_document_from_string(xml)


def get_namespaceless_document_from_document(doc: ET.ElementTree) -> ET.ElementTree:
    """Get namespaceless document from existing document.

    Parameters
    ----------
    doc : ET.ElementTree
        Source document

    Returns
    -------
    ET.ElementTree
        New document without namespace processing
    """
    xml_str = get_xml_string_fragment_from_node(doc.getroot())
    return get_namespaceless_document_from_string(xml_str)


def get_node_text(node: Element | None) -> str:
    """Extract text from node and its children.

    Parameters
    ----------
    node : Element | None
        Node to extract text from

    Returns
    -------
    str
        Text content
    """
    if node is None:
        return ""

    # ElementTree's text and tail properties handle this
    text_parts: list[str] = []

    if node.text:
        text_parts.append(node.text)

    for child in node:
        text_parts.append(get_node_text(child))
        if child.tail:
            text_parts.append(child.tail)

    return "".join(text_parts)


def get_xml_string_fragment_from_node(
    node: Element, omit_declaration: bool = True, encoding: str = "UTF-8", collapse_empty_tags: bool = True
) -> str:
    """Convert ElementTree Element to XML string.

    Parameters
    ----------
    node : Element
        Element to convert
    omit_declaration : bool, optional
        Whether to omit XML declaration, by default True
    encoding : str, optional
        Target encoding, by default "UTF-8"
    collapse_empty_tags : bool, optional
        Whether to collapse empty tags, by default True

    Returns
    -------
    str
        XML string representation
    """
    # Pretty print by indenting
    _indent(node)

    xml_str = ET.tostring(node, encoding=encoding, xml_declaration=not omit_declaration)

    if isinstance(xml_str, bytes):
        return xml_str.decode(encoding)

    return xml_str


def remove_empty_nodes(node: Element) -> ET.ElementTree:
    """Remove empty nodes using XSLT transformation.

    Parameters
    ----------
    node : Element
        Root node

    Returns
    -------
    ET.ElementTree
        Document with empty nodes removed

    Raises
    ------
    ValueError
        If lxml is not available (required for XSLT)
    """
    global _empty_element_xslt

    if not HAS_LXML:
        raise ValueError("lxml required for XSLT transformations")

    if _empty_element_xslt is None:
        xslt_doc = etree.parse(io.BytesIO(_EMPTY_ELEMENT_REMOVAL_XSLT.encode("utf-8")))
        _empty_element_xslt = etree.XSLT(xslt_doc)

    # Convert ElementTree to lxml for transformation
    xml_str = ET.tostring(node, encoding="unicode")
    lxml_root = etree.fromstring(xml_str.encode("utf-8"))
    result = _empty_element_xslt(lxml_root)

    # Convert back to ElementTree
    result_str = etree.tostring(result, encoding="unicode")
    root = ET.fromstring(result_str)
    return ET.ElementTree(root)


def remove_empty_elements(node: Element) -> Element:
    """Recursively remove empty elements (deprecated, use remove_empty_nodes).

    Parameters
    ----------
    node : Element
        Node to process

    Returns
    -------
    Element
        Node with empty elements removed
    """
    # Find and remove empty child elements
    children_to_remove: list[Element] = []
    for child in node:
        if isinstance(child, ET.Element):
            # Check if element is empty (no text, no children with text)
            if not child.text and not any(get_node_text(grandchild) for grandchild in child):
                children_to_remove.append(child)
            else:
                # Recurse
                remove_empty_elements(child)

    for child in children_to_remove:
        node.remove(child)

    return node


def select_single_node(node: Element, expression: str) -> Element | None:
    """Select first node matching XPath expression.

    Parameters
    ----------
    node : Element
        Root node to search
    expression : str
        XPath expression

    Returns
    -------
    Element | None
        First matching element, or None if not found
    """
    try:
        if HAS_LXML:
            # Use lxml for full XPath support
            lxml_node = etree.fromstring(ET.tostring(node, encoding="unicode"))
            matches = lxml_node.xpath(expression)
            if matches:
                # Convert back to ElementTree Element
                result_str = etree.tostring(matches[0], encoding="unicode")
                return ET.fromstring(result_str)
        else:
            # Use ElementTree's limited XPath
            matches = node.findall(expression)
            return matches[0] if matches else None
    except Exception:
        return None


def select_node_text(node: Element, expression: str) -> str:
    """Select text from node matching XPath expression.

    Parameters
    ----------
    node : Element
        Root node to search
    expression : str
        XPath expression

    Returns
    -------
    str
        Text content of matching node
    """
    selected = select_single_node(node, expression)
    return get_node_text(selected) if selected else ""


def select_node_list(node: Element, expression: str) -> list[Element]:
    """Select all nodes matching XPath expression.

    Parameters
    ----------
    node : Element
        Root node to search
    expression : str
        XPath expression

    Returns
    -------
    list[Element]
        List of matching elements
    """
    try:
        if HAS_LXML:
            # Use lxml for full XPath support
            lxml_node = etree.fromstring(ET.tostring(node, encoding="unicode"))
            matches = lxml_node.xpath(expression)
            result: list[Element] = []
            for match in matches:
                if isinstance(match, etree._Element):
                    result_str = etree.tostring(match, encoding="unicode")
                    result.append(ET.fromstring(result_str))
            return result
        else:
            # Use ElementTree's limited XPath
            return list(node.findall(expression))
    except Exception:
        return []


def format_xml_string_for_display(xml: str, omit_declaration: bool = True) -> str:
    """Format XML string for display (pretty-printed).

    Parameters
    ----------
    xml : str
        XML string to format
    omit_declaration : bool, optional
        Whether to omit XML declaration, by default True

    Returns
    -------
    str
        Formatted XML, or original string if formatting fails
    """
    try:
        doc = get_document_from_string(xml)
        return get_xml_string_fragment_from_node(doc.getroot(), omit_declaration=omit_declaration)
    except Exception:
        return xml


def remove_all_child_nodes(node: Element) -> None:
    """Remove all child nodes from element.

    Parameters
    ----------
    node : Element
        Element to remove children from
    """
    children = list(node)
    for child in children:
        node.remove(child)


def remove_all_attributes(element: Element) -> None:
    """Remove all attributes from element.

    Parameters
    ----------
    element : Element
        Element to remove attributes from
    """
    # Get list of attribute names first (can't modify while iterating)
    attr_names = list(element.attrib.keys())
    for name in attr_names:
        del element.attrib[name]


def create_utf8_input_source(xml: str | Element) -> io.BytesIO:
    """Create UTF-8 input source from XML string or element.

    Parameters
    ----------
    xml : str | Element
        XML string or ElementTree element

    Returns
    -------
    io.BytesIO
        Input source as BytesIO stream
    """
    if isinstance(xml, str):
        return io.BytesIO(xml.encode("utf-8"))
    else:
        xml_str = get_xml_string_fragment_from_node(xml)
        return io.BytesIO(xml_str.encode("utf-8"))


def alphabetise_child_nodes(root: Element) -> Element:
    """Alphabetize top-level children of root node.

    Parameters
    ----------
    root : Element
        Root node to alphabetize

    Returns
    -------
    Element
        Root node with alphabetized children
    """
    root = remove_empty_elements(root)
    children = list(root)

    # Sort by tag name
    children.sort(key=lambda child: child.tag if child.tag else "")

    # Remove and re-add in sorted order
    remove_all_child_nodes(root)
    for child in children:
        root.append(child)

    return root


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
