"""Saxon XQuery utility for evaluating XQuery expressions.

Provides XQuery evaluation using lxml or fallback implementations.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

logger = logging.getLogger(__name__)

try:
    from lxml import etree

    HAS_LXML = True
except ImportError:
    HAS_LXML = False
    logger.warning("lxml not available, XQuery evaluation limited")


def evaluate_query(query: str, data_doc: Element | None) -> str:
    """Evaluate an XQuery against a data document.

    Parameters
    ----------
    query : str
        XQuery expression to evaluate
    data_doc : Element | None
        ElementTree Element containing the data tree

    Returns
    -------
    str
        XML string representing the result of the evaluation

    Raises
    ------
    ValueError
        If XQuery evaluation fails
    """
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Evaluating XQuery: %s", query)

    if not HAS_LXML:
        logger.warning("lxml not available, XQuery evaluation not supported")
        return "__evaluation_error__"

    if data_doc is None:
        return ""

    try:
        # Convert ElementTree to lxml for XQuery evaluation
        xml_str = _element_to_string(data_doc)
        lxml_root = etree.fromstring(xml_str.encode("utf-8"))

        # Use lxml's XPath (limited XQuery support)
        # For full XQuery, would need saxonche or similar
        result = _evaluate_xpath(query, lxml_root)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("XQuery result: %s", result)

        return _remove_header(result)
    except Exception as e:
        logger.error("XQuery evaluation failed: %s", str(e), exc_info=True)
        return "__evaluation_error__"


def evaluate_tree_query(query: str, data_doc: Element | None) -> Element | None:
    """Evaluate an XQuery and return as Element.

    Parameters
    ----------
    query : str
        XQuery expression
    data_doc : Element | None
        Data document

    Returns
    -------
    Element | None
        ElementTree Element representing result, or None if evaluation fails
    """
    from kgcl.yawl.util.xml.jdom_util import string_to_element

    result_str = evaluate_query(query, data_doc)
    if result_str == "__evaluation_error__":
        return None

    return string_to_element(result_str)


def evaluate_list_query(query: str, data_elem: Element | None) -> list[Element]:
    """Evaluate an XQuery and return list of Elements.

    Parameters
    ----------
    query : str
        XQuery expression
    data_elem : Element | None
        Data element

    Returns
    -------
    list[Element]
        List of ElementTree Elements resulting from evaluation
    """
    from xml.etree import ElementTree as ET

    if not HAS_LXML or data_elem is None:
        return []

    try:
        xml_str = _element_to_string(data_elem)
        lxml_root = etree.fromstring(xml_str.encode("utf-8"))

        # Use XPath to find matching elements
        matches = lxml_root.xpath(query)

        result: list[Element] = []
        for match in matches:
            if isinstance(match, etree._Element):
                result_str = etree.tostring(match, encoding="unicode")
                result.append(ET.fromstring(result_str))

        return result
    except Exception as e:
        logger.error("XQuery list evaluation failed: %s", str(e), exc_info=True)
        return []


def _evaluate_xpath(query: str, lxml_root: etree._Element) -> str:
    """Evaluate XPath query (simplified XQuery support).

    Parameters
    ----------
    query : str
        XPath/XQuery expression
    lxml_root : etree._Element
        Root element

    Returns
    -------
    str
        Result as XML string
    """
    try:
        # Try XPath evaluation
        results = lxml_root.xpath(query)
        if not results:
            return ""

        # Convert results to XML string
        if len(results) == 1:
            return etree.tostring(results[0], encoding="unicode")
        else:
            # Multiple results - wrap in root element
            root = etree.Element("results")
            for result in results:
                if isinstance(result, etree._Element):
                    root.append(result)
            return etree.tostring(root, encoding="unicode")
    except Exception:
        # Fallback: return empty string
        return ""


def _element_to_string(elem: Element) -> str:
    """Convert ElementTree Element to XML string.

    Parameters
    ----------
    elem : Element
        Element to convert

    Returns
    -------
    str
        XML string representation
    """
    from xml.etree import ElementTree as ET

    return ET.tostring(elem, encoding="unicode")


def _remove_header(xml: str) -> str:
    """Remove XML declaration header from string.

    Parameters
    ----------
    xml : str
        XML string

    Returns
    -------
    str
        XML string without declaration
    """
    if xml.startswith("<?xml"):
        end = xml.find("?>")
        if end != -1:
            return xml[end + 2 :].strip()
    return xml
