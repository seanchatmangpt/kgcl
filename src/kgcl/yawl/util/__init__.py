"""YAWL utility functions.

This module provides utility functions for YAWL workflows, including
string manipulation, XML processing, HTTP operations, session management,
and build properties.
"""

# String utilities
# Build properties
from kgcl.yawl.util.build_properties import YBuildProperties

# HTTP utilities
from kgcl.yawl.util.http import (
    SoapClient,
    cancel_all,
    download,
    is_port_active,
    is_responsive,
    is_tomcat_running,
    ping_until_available,
    resolve_url,
    simple_ping,
    validate,
)

# Identifier bag
from kgcl.yawl.util.identifier_bag import YIdentifierBag

# Miscellaneous utilities
from kgcl.yawl.util.misc import (
    CheckSummer,
    DynamicValue,
    MailSettings,
    NamedThreadFactory,
    encrypt_password,
    evaluate_list_query,
    evaluate_query,
    evaluate_tree_query,
)

# Parsers
from kgcl.yawl.util.parser import YNetElementDocoParser, YPredicateParser

# Session management
from kgcl.yawl.util.session import InterfaceAClient, Sessions
from kgcl.yawl.util.string_util import (
    capitalise,
    convert_throwable_to_string,
    de_quote,
    en_quote,
    extract,
    file_to_string,
    find,
    findAll,
    format_decimal_cost,
    format_for_html,
    format_postcode,
    format_sort_code,
    format_time,
    format_ui_date,
    get_debug_message,
    get_iso_formatted_date,
    get_random_string,
    insert,
    is_integer_string,
    is_null_or_empty,
    join,
    pad,
    remove_all_white_space,
    replace_in_file,
    replace_tokens,
    reverse_string,
    split_to_list,
    str_to_boolean,
    str_to_double,
    str_to_int,
    str_to_long,
    stream_to_string,
    string_to_file,
    string_to_temp_file,
    unwrap,
    wrap,
    wrap_escaped,
    xml_decode,
    xml_encode,
)

# Verification
from kgcl.yawl.util.verification import MessageType, YVerificationHandler, YVerificationMessage

# XML utilities
from kgcl.yawl.util.xml import ContentType, XNode
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
from kgcl.yawl.util.xml.xnode_io import XNodeIO
from kgcl.yawl.util.xml.xnode_parser import XNodeParser

__all__: list[str] = [
    # String utilities
    "capitalise",
    "convert_throwable_to_string",
    "de_quote",
    "en_quote",
    "extract",
    "file_to_string",
    "find",
    "findAll",
    "format_decimal_cost",
    "format_for_html",
    "format_postcode",
    "format_sort_code",
    "format_time",
    "format_ui_date",
    "get_debug_message",
    "get_iso_formatted_date",
    "get_random_string",
    "insert",
    "is_integer_string",
    "is_null_or_empty",
    "join",
    "pad",
    "remove_all_white_space",
    "replace_in_file",
    "replace_tokens",
    "reverse_string",
    "split_to_list",
    "str_to_boolean",
    "str_to_double",
    "str_to_int",
    "str_to_long",
    "stream_to_string",
    "string_to_file",
    "string_to_temp_file",
    "unwrap",
    "wrap",
    "wrap_escaped",
    "xml_decode",
    "xml_encode",
    # XML utilities
    "ContentType",
    "XNode",
    "XNodeIO",
    "XNodeParser",
    "decode_escapes",
    "document_to_file",
    "document_to_string",
    "element_to_string",
    "encode_escapes",
    "file_to_document",
    "format_xml_string",
    "select_element",
    "select_element_list",
    "string_to_document",
    "string_to_element",
    # HTTP utilities
    "SoapClient",
    "cancel_all",
    "download",
    "is_port_active",
    "is_responsive",
    "is_tomcat_running",
    "ping_until_available",
    "resolve_url",
    "simple_ping",
    "validate",
    # Session management
    "InterfaceAClient",
    "Sessions",
    # Build properties
    "YBuildProperties",
    # Verification
    "MessageType",
    "YVerificationHandler",
    "YVerificationMessage",
    # Miscellaneous
    "CheckSummer",
    "DynamicValue",
    "MailSettings",
    "NamedThreadFactory",
    "encrypt_password",
    "evaluate_list_query",
    "evaluate_query",
    "evaluate_tree_query",
    # Parsers
    "YNetElementDocoParser",
    "YPredicateParser",
    # Identifier bag
    "YIdentifierBag",
]
