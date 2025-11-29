"""XML utility functions for YAWL workflows.

This module provides XML manipulation utilities including XNode for building
XML structures, parsers, DOM utilities, and JDOM utilities.
"""

from kgcl.yawl.util.xml.dom_util import (
    alphabetise_child_nodes,
    create_document_instance,
    create_namespaceless_document_instance,
    create_utf8_input_source,
    format_xml_string_for_display,
    get_document_from_string,
    get_namespaceless_document_from_document,
    get_namespaceless_document_from_string,
    get_node_text,
    get_xml_string_fragment_from_node,
    remove_all_attributes,
    remove_all_child_nodes,
    remove_empty_elements,
    remove_empty_nodes,
    select_node_list,
    select_node_text,
    select_single_node,
)
from kgcl.yawl.util.xml.jdom_util import (
    decode_escapes,
    document_to_file,
    document_to_string,
    element_to_string,
    encode_escapes,
    file_to_document,
    format_xml_string,
    select_element,
    select_element_list,
    string_to_document,
    string_to_element,
)
from kgcl.yawl.util.xml.xnode import ContentType, XNode
from kgcl.yawl.util.xml.xnode_io import XNodeIO
from kgcl.yawl.util.xml.xnode_parser import XNodeParser

__all__: list[str] = [
    "ContentType",
    "XNode",
    "XNodeIO",
    "XNodeParser",
    "alphabetise_child_nodes",
    "create_document_instance",
    "create_namespaceless_document_instance",
    "create_utf8_input_source",
    "decode_escapes",
    "document_to_file",
    "document_to_string",
    "element_to_string",
    "encode_escapes",
    "file_to_document",
    "format_xml_string",
    "format_xml_string_for_display",
    "get_document_from_string",
    "get_namespaceless_document_from_document",
    "get_namespaceless_document_from_string",
    "get_node_text",
    "get_xml_string_fragment_from_node",
    "remove_all_attributes",
    "remove_all_child_nodes",
    "remove_empty_elements",
    "remove_empty_nodes",
    "select_element",
    "select_element_list",
    "select_node_list",
    "select_node_text",
    "select_single_node",
    "string_to_document",
    "string_to_element",
]
