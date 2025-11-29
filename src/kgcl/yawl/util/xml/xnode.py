"""XNode class for building XML strings.

A utility for building XML strings. Handles elements, attributes, comments, text
and CDATA.

NOTE: To keep things simple, while this class allows a node to have both child
nodes and text, where both have values set the child nodes have precedence
(i.e. the text is ignored).
"""

from __future__ import annotations

import os
from enum import Enum
from typing import TYPE_CHECKING, Any, Collection

if TYPE_CHECKING:
    from collections.abc import Iterator

_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'
_NEWLINE = os.linesep
_DEF_TAB_SIZE = 2


class ContentType(Enum):
    """Content type for XNode."""

    TEXT = "text"
    COMMENT = "comment"
    CDATA = "cdata"


class XNode:
    """A utility for building XML strings.

    Handles elements, attributes, comments, text and CDATA.

    Parameters
    ----------
    name : str
        Element name
    text : str | None, optional
        Text content, by default None

    Attributes
    ----------
    name : str
        Element name
    text : str | None
        Text content
    content_type : ContentType
        Type of content (text, comment, or CDATA)
    depth : int
        Depth in XML tree (0 for root)
    parent : XNode | None
        Parent node
    children : list[XNode]
        Child nodes
    attributes : dict[str, str]
        Element attributes
    opening_comments : list[str]
        Comments before root element
    closing_comments : list[str]
        Comments after all content
    """

    # XNode is mutable and should not be hashed
    __hash__ = None  # type: ignore[assignment]

    def __init__(self, name: str, text: str | None = None) -> None:
        """Initialize XNode.

        Parameters
        ----------
        name : str
            Element name
        text : str | None, optional
            Text content, by default None
        """
        self.name: str = name
        self.text: str | None = text
        self.content_type: ContentType = ContentType.TEXT
        self.depth: int = 0
        self.parent: XNode | None = None
        self.children: list[XNode] = []
        self.attributes: dict[str, str] = {}
        self.opening_comments: list[str] = []
        self.closing_comments: list[str] = []

    def __str__(self) -> str:
        """Return XML string representation.

        Returns
        -------
        str
            XML string
        """
        return self._to_string(False, self.depth, _DEF_TAB_SIZE, False)

    def __repr__(self) -> str:
        """Return string representation for debugging.

        Returns
        -------
        str
            Debug representation
        """
        return f"XNode(name={self.name!r}, text={self.text!r}, children={len(self.children)})"

    def __lt__(self, other: object) -> bool:
        """Compare XNode for sorting.

        Parameters
        ----------
        other : object
            Other XNode to compare

        Returns
        -------
        bool
            True if this node is less than other
        """
        if not isinstance(other, XNode):
            return NotImplemented

        if self.name != other.name:
            return self.name < other.name

        self_text = self.text or ""
        other_text = other.text or ""
        return self_text < other_text

    def __eq__(self, other: object) -> bool:
        """Check equality with another XNode.

        Parameters
        ----------
        other : object
            Other XNode to compare

        Returns
        -------
        bool
            True if nodes are equal
        """
        if not isinstance(other, XNode):
            return False

        return (
            self.name == other.name
            and self.text == other.text
            and self.attributes == other.attributes
            and len(self.children) == len(other.children)
        )

    # Attribute methods

    def add_attribute(self, key: str, value: str | bool | int | float | object, escape: bool = False) -> None:
        """Add an attribute to the element.

        Parameters
        ----------
        key : str
            Attribute key
        value : str | bool | int | float | object
            Attribute value (will be converted to string)
        escape : bool, optional
            Whether to escape XML entities, by default False
        """
        str_value = str(value)
        if escape:
            # Import here to avoid circular dependency
            from kgcl.yawl.util.xml.jdom_util import encode_escapes

            str_value = encode_escapes(str_value)

        self.attributes[key] = str_value

    def add_attributes(self, attributes: dict[str, str] | None) -> None:
        """Add multiple attributes from a dictionary.

        Parameters
        ----------
        attributes : dict[str, str] | None
            Dictionary of attributes to add
        """
        if attributes:
            self.attributes.update(attributes)

    def get_attribute_value(self, key: str) -> str | None:
        """Get attribute value by key.

        Parameters
        ----------
        key : str
            Attribute key

        Returns
        -------
        str | None
            Attribute value, or None if not found
        """
        return self.attributes.get(key)

    def has_attribute(self, key: str) -> bool:
        """Check if attribute exists.

        Parameters
        ----------
        key : str
            Attribute key

        Returns
        -------
        bool
            True if attribute exists
        """
        return key in self.attributes

    def set_attributes(self, attributes: dict[str, str]) -> None:
        """Set all attributes (replaces existing).

        Parameters
        ----------
        attributes : dict[str, str]
            Dictionary of attributes
        """
        self.attributes = attributes

    def get_attribute_count(self) -> int:
        """Get number of attributes.

        Returns
        -------
        int
            Number of attributes
        """
        return len(self.attributes)

    # Child methods

    def add_child(
        self, child_or_name: XNode | str, text: str | bool | int | float | object | None = None, escape: bool = False
    ) -> XNode:
        """Add a child node.

        Parameters
        ----------
        child_or_name : XNode | str
            Child XNode or name for new child
        text : str | bool | int | float | object | None, optional
            Text content if creating new child, by default None
        escape : bool, optional
            Whether to escape XML entities in text, by default False

        Returns
        -------
        XNode
            Added child node
        """
        if isinstance(child_or_name, XNode):
            child = child_or_name
        else:
            name = child_or_name
            if text is not None:
                str_text = str(text)
                if escape:
                    from kgcl.yawl.util.xml.jdom_util import encode_escapes

                    str_text = encode_escapes(str_text)
                child = XNode(name, str_text)
            else:
                child = XNode(name)

        if child is not None:
            self._accept_child(child)
            self.children.append(child)

        return child

    def insert_child(self, index: int, child: XNode | None) -> XNode | None:
        """Insert a child node at a specific index.

        Parameters
        ----------
        index : int
            Index to insert at
        child : XNode | None
            Child node to insert

        Returns
        -------
        XNode | None
            Inserted child, or None if child is None
        """
        if child is not None:
            self._accept_child(child)
            self.children.insert(index, child)

        return child

    def add_children(self, children: Collection[XNode] | dict[str, str]) -> None:
        """Add multiple children.

        Parameters
        ----------
        children : Collection[XNode] | dict[str, str]
            Collection of XNode children or dict mapping names to text
        """
        if isinstance(children, dict):
            for key, value in children.items():
                self.add_child(key, value)
        else:
            for child in children:
                self.add_child(child)

    def remove_child(self, child: XNode) -> bool:
        """Remove a child node.

        Parameters
        ----------
        child : XNode
            Child to remove

        Returns
        -------
        bool
            True if child was removed
        """
        if child in self.children:
            self.children.remove(child)
            child.parent = None
            return True

        return False

    def remove_children(self) -> None:
        """Remove all children."""
        for child in self.children:
            child.parent = None
        self.children.clear()

    def get_child(self, name_or_index: str | int | None = None) -> XNode | None:
        """Get a child node by name, index, or first text child.

        Parameters
        ----------
        name_or_index : str | int | None, optional
            Child name, index, or None for first text child, by default None

        Returns
        -------
        XNode | None
            Child node, or None if not found
        """
        if name_or_index is None:
            # Return first text-type child
            for child in self.children:
                if child.content_type == ContentType.TEXT:
                    return child
            return None

        if isinstance(name_or_index, int):
            index = name_or_index
            if 0 <= index < len(self.children):
                return self.children[index]
            return None

        # Search by name
        name = name_or_index
        for child in self.children:
            if child.name == name:
                return child

        return None

    def get_or_add_child(self, name: str) -> XNode:
        """Get a child by name, or create it if it doesn't exist.

        Parameters
        ----------
        name : str
            Child name

        Returns
        -------
        XNode
            Existing or newly created child
        """
        child = self.get_child(name)
        if child is None:
            child = self.add_child(name)

        return child

    def get_children(self, name_or_type: str | ContentType | None = None) -> list[XNode]:
        """Get children by name or content type.

        Parameters
        ----------
        name_or_type : str | ContentType | None, optional
            Filter by name or content type, by default None (all children)

        Returns
        -------
        list[XNode]
            List of matching children
        """
        if name_or_type is None:
            return list(self.children)

        if isinstance(name_or_type, ContentType):
            ctype = name_or_type
            return [child for child in self.children if child.content_type == ctype]

        # Filter by name
        name = name_or_type
        return [child for child in self.children if child.name == name]

    def get_child_text(self, name: str, escape: bool = False) -> str | None:
        """Get text content of a child by name.

        Parameters
        ----------
        name : str
            Child name
        escape : bool, optional
            Whether to decode XML entities, by default False

        Returns
        -------
        str | None
            Child text, or None if child not found
        """
        child = self.get_child(name)
        if child is not None:
            return child.get_text(escape)

        return None

    def pos_child_with_name(self, name: str) -> int:
        """Get position of first child with given name.

        Parameters
        ----------
        name : str
            Child name

        Returns
        -------
        int
            Index of child, or -1 if not found
        """
        for i, child in enumerate(self.children):
            if child.name == name:
                return i

        return -1

    def pos_child_with_attribute(self, key: str, value: str) -> int:
        """Get position of first child with given attribute.

        Parameters
        ----------
        key : str
            Attribute key
        value : str
            Attribute value

        Returns
        -------
        int
            Index of child, or -1 if not found
        """
        for i, child in enumerate(self.children):
            attr_value = child.get_attribute_value(key)
            if attr_value == value:
                return i

        return -1

    def has_children(self, name: str | None = None) -> bool:
        """Check if node has children.

        Parameters
        ----------
        name : str | None, optional
            If provided, check for children with this name, by default None

        Returns
        -------
        bool
            True if has children (matching name if provided)
        """
        if name is None:
            return len(self.children) > 0

        return len(self.get_children(name)) > 0

    def has_child(self, name: str) -> bool:
        """Check if node has a child with given name.

        Parameters
        ----------
        name : str
            Child name

        Returns
        -------
        bool
            True if child exists
        """
        return self.get_child(name) is not None

    def get_child_count(self) -> int:
        """Get number of children.

        Returns
        -------
        int
            Number of children
        """
        return len(self.children)

    def remove_duplicate_children(self) -> None:
        """Remove duplicate children (based on string representation)."""
        child_map: dict[str, XNode] = {}
        for child in self.children:
            child_map[str(child)] = child

        self.remove_children()
        self.add_children(child_map.values())

    def sort(self, key: Any = None) -> None:
        """Sort children.

        Parameters
        ----------
        key : Any, optional
            Sort key function, by default None (uses natural ordering)
        """
        if key is None:
            self.children.sort()
        else:
            self.children.sort(key=key)

    # Text methods

    def set_text(self, text: str | bool | int | float | None, escape: bool = False) -> None:
        """Set text content.

        Parameters
        ----------
        text : str | bool | int | float | None
            Text content (will be converted to string)
        escape : bool, optional
            Whether to escape XML entities, by default False
        """
        if text is None:
            self.text = None
            return

        str_text = str(text)
        if escape:
            from kgcl.yawl.util.xml.jdom_util import encode_escapes

            str_text = encode_escapes(str_text)

        self.text = str_text

    def get_text(self, escape: bool = False) -> str | None:
        """Get text content.

        Parameters
        ----------
        escape : bool, optional
            Whether to decode XML entities, by default False

        Returns
        -------
        str | None
            Text content
        """
        if escape and self.text:
            from kgcl.yawl.util.xml.jdom_util import decode_escapes

            return decode_escapes(self.text)

        return self.text

    def get_text_length(self) -> int:
        """Get length of text content.

        Returns
        -------
        int
            Text length, or 0 if no text
        """
        return len(self.text) if self.text else 0

    # Comment methods

    def add_comment(self, comment: str) -> XNode:
        """Add a comment as a child.

        Parameters
        ----------
        comment : str
            Comment text

        Returns
        -------
        XNode
            Comment node
        """
        child = self.add_child("_!_", comment)
        child.content_type = ContentType.COMMENT
        return child

    def insert_comment(self, index: int, comment: str) -> XNode:
        """Insert a comment at a specific index.

        Parameters
        ----------
        index : int
            Index to insert at
        comment : str
            Comment text

        Returns
        -------
        XNode
            Comment node
        """
        child = XNode("_!_", comment)
        child.content_type = ContentType.COMMENT
        return self.insert_child(index, child) or child

    def is_comment(self) -> bool:
        """Check if this node is a comment.

        Returns
        -------
        bool
            True if node is a comment
        """
        return self.content_type == ContentType.COMMENT

    def add_opening_comment(self, comment: str) -> None:
        """Add a comment before the root element.

        Parameters
        ----------
        comment : str
            Comment text
        """
        self.opening_comments.append(comment)

    def add_closing_comment(self, comment: str) -> None:
        """Add a comment after all content.

        Parameters
        ----------
        comment : str
            Comment text
        """
        self.closing_comments.append(comment)

    # CDATA methods

    def add_cdata(self, cdata: str) -> XNode:
        """Add CDATA as a child.

        Parameters
        ----------
        cdata : str
            CDATA content

        Returns
        -------
        XNode
            CDATA node
        """
        child = self.add_child("_[_", cdata)
        child.content_type = ContentType.CDATA
        return child

    def is_cdata(self) -> bool:
        """Check if this node is CDATA.

        Returns
        -------
        bool
            True if node is CDATA
        """
        return self.content_type == ContentType.CDATA

    # Content methods

    def add_content(self, content: str, ns_prefix: str | None = None, ns_uri: str | None = None) -> None:
        """Add XML content by parsing it.

        Parameters
        ----------
        content : str
            XML content to parse and add
        ns_prefix : str | None, optional
            Namespace prefix, by default None
        ns_uri : str | None, optional
            Namespace URI, by default None
        """
        if content is None:
            return

        content = content.strip()
        if content.startswith(_HEADER):
            content = content[len(_HEADER) :].strip()

        wrapped_content = self._wrap_content(content, ns_prefix, ns_uri)

        # Import here to avoid circular dependency
        from kgcl.yawl.util.xml.xnode_parser import XNodeParser

        parser = XNodeParser(check=True)
        temp_node = parser.parse(wrapped_content)
        if temp_node:
            for child in temp_node.get_children():
                self.add_child(child)

    def add_collection(self, items: Collection[Any]) -> None:
        """Add child nodes from a collection of XNodeIO objects.

        Parameters
        ----------
        items : Collection[Any]
            Collection of objects with to_xnode() method
        """
        if not items:
            return

        for item in items:
            if hasattr(item, "to_xnode"):
                xnode = item.to_xnode()
                self.add_child(xnode)

    def populate_collection(self, items: list[Any], instance: Any) -> None:
        """Populate a list from child nodes.

        Parameters
        ----------
        items : list[Any]
            List to populate
        instance : Any
            Instance with from_xnode() and new_instance() methods
        """
        for child in self.get_children(ContentType.TEXT):
            if hasattr(instance, "new_instance"):
                new_item = instance.new_instance(child)
                items.append(new_item)

    # Property accessors

    def get_name(self) -> str:
        """Get element name.

        Returns
        -------
        str
            Element name
        """
        return self.name

    def set_name(self, name: str) -> None:
        """Set element name.

        Parameters
        ----------
        name : str
            New element name
        """
        self.name = name

    def get_parent(self) -> XNode | None:
        """Get parent node.

        Returns
        -------
        XNode | None
            Parent node, or None if root
        """
        return self.parent

    def set_parent(self, parent: XNode | None) -> None:
        """Set parent node.

        Parameters
        ----------
        parent : XNode | None
            Parent node
        """
        self.parent = parent

    def get_depth(self) -> int:
        """Get depth in XML tree.

        Returns
        -------
        int
            Depth (0 for root)
        """
        return self.depth

    def set_depth(self, depth: int) -> None:
        """Set depth and update children.

        Parameters
        ----------
        depth : int
            New depth
        """
        self.depth = depth
        if self.has_children():
            child_depth = depth + 1
            for child in self.children:
                child.set_depth(child_depth)

    def length(self) -> int:
        """Get length of XML string representation.

        Returns
        -------
        int
            Length of XML string
        """
        return len(str(self))

    # String representation methods

    def to_string(self, header: bool = False) -> str:
        """Convert to XML string.

        Parameters
        ----------
        header : bool, optional
            Whether to include XML header, by default False

        Returns
        -------
        str
            XML string
        """
        return self._to_string(False, self.depth, _DEF_TAB_SIZE, header)

    def to_pretty_string(self, header: bool = False, tab_size: int | None = None, offset: int | None = None) -> str:
        """Convert to pretty-printed XML string.

        Parameters
        ----------
        header : bool, optional
            Whether to include XML header, by default False
        tab_size : int | None, optional
            Tab size for indentation, by default None (uses default)
        offset : int | None, optional
            Depth offset, by default None (uses node depth)

        Returns
        -------
        str
            Pretty-printed XML string
        """
        tab = tab_size if tab_size is not None else _DEF_TAB_SIZE
        off = offset if offset is not None else self.depth
        return self._to_string(True, off, tab, header)

    # Private helper methods

    def _accept_child(self, child: XNode) -> None:
        """Accept a child node and set its parent/depth.

        Parameters
        ----------
        child : XNode
            Child node to accept
        """
        if child is not None:
            child.set_parent(self)
            child.set_depth(self.depth + 1)

    def _wrap_content(self, content: str, ns_prefix: str | None, ns_uri: str | None) -> str:
        """Wrap content in a temporary element.

        Parameters
        ----------
        content : str
            Content to wrap
        ns_prefix : str | None
            Namespace prefix
        ns_uri : str | None
            Namespace URI

        Returns
        -------
        str
            Wrapped content
        """
        parts = ["<temp"]
        if ns_prefix and ns_uri:
            parts.append(f' xmlns:{ns_prefix}="{ns_uri}"')
        parts.append(">")
        parts.append(content)
        parts.append("</temp>")
        return "".join(parts)

    def _to_string(self, pretty: bool, offset: int, tab_size: int, header: bool) -> str:
        """Internal method to convert to string.

        Parameters
        ----------
        pretty : bool
            Whether to pretty-print
        offset : int
            Depth offset
        tab_size : int
            Tab size
        header : bool
            Whether to include XML header

        Returns
        -------
        str
            XML string
        """
        tabs = self._get_indent(offset, tab_size)

        if self.is_comment():
            return self._print_comment(pretty, tabs)
        if self.is_cdata():
            return self._print_cdata(pretty, tabs)

        parts: list[str] = []

        if header:
            parts.append(_HEADER)
            parts.append(_NEWLINE)

        if self.depth == 0:
            parts.append(self._print_opening_comments(pretty))

        if pretty:
            parts.append(tabs)

        parts.append("<")
        parts.append(self.name)

        if self.attributes:
            for key, value in self.attributes.items():
                parts.append(" ")
                parts.append(key)
                parts.append('="')
                parts.append(value)
                parts.append('"')

        if not self.children and not self.text:
            parts.append("/>")
        else:
            parts.append(">")
            if self.children:
                if pretty:
                    parts.append(_NEWLINE)
                for child in self.children:
                    parts.append(child._to_string(pretty, offset, tab_size, False))
                if pretty:
                    parts.append(tabs)
            else:
                parts.append(self.text or "")

            parts.append("</")
            parts.append(self.name)
            parts.append(">")

        if self.depth == 0:
            if pretty:
                parts.append(_NEWLINE)
            parts.append(self._print_closing_comments(pretty))

        if pretty:
            parts.append(_NEWLINE)

        return "".join(parts)

    def _get_indent(self, offset: int, tab_size: int) -> str:
        """Get indentation string.

        Parameters
        ----------
        offset : int
            Depth offset
        tab_size : int
            Tab size

        Returns
        -------
        str
            Indentation string
        """
        tab_count = self.depth - offset
        if tab_count < 1:
            return ""

        return " " * (tab_count * tab_size)

    def _print_comment(self, pretty: bool, tabs: str) -> str:
        """Print comment node.

        Parameters
        ----------
        pretty : bool
            Whether to pretty-print
        tabs : str
            Indentation

        Returns
        -------
        str
            Comment XML string
        """
        if not self.is_comment():
            return ""

        return self._print_special_text("<!-- ", " -->", pretty, tabs)

    def _print_cdata(self, pretty: bool, tabs: str) -> str:
        """Print CDATA node.

        Parameters
        ----------
        pretty : bool
            Whether to pretty-print
        tabs : str
            Indentation

        Returns
        -------
        str
            CDATA XML string
        """
        if not self.is_cdata():
            return ""

        return self._print_special_text("<![CDATA[", "]]>", pretty, tabs)

    def _print_special_text(self, head: str, foot: str, pretty: bool, tabs: str) -> str:
        """Print special text (comment or CDATA).

        Parameters
        ----------
        head : str
            Opening tag
        foot : str
            Closing tag
        pretty : bool
            Whether to pretty-print
        tabs : str
            Indentation

        Returns
        -------
        str
            Special text XML string
        """
        parts: list[str] = []
        if pretty:
            parts.append(tabs)
        parts.append(head)
        parts.append(self.text or "")
        parts.append(foot)
        if pretty:
            parts.append(_NEWLINE)

        return "".join(parts)

    def _print_opening_comments(self, pretty: bool) -> str:
        """Print opening comments.

        Parameters
        ----------
        pretty : bool
            Whether to pretty-print

        Returns
        -------
        str
            Opening comments XML string
        """
        return self._print_outlying_comments(self.opening_comments, pretty)

    def _print_closing_comments(self, pretty: bool) -> str:
        """Print closing comments.

        Parameters
        ----------
        pretty : bool
            Whether to pretty-print

        Returns
        -------
        str
            Closing comments XML string
        """
        return self._print_outlying_comments(self.closing_comments, pretty)

    def _print_outlying_comments(self, comment_list: list[str], pretty: bool) -> str:
        """Print outlying comments.

        Parameters
        ----------
        comment_list : list[str]
            List of comments
        pretty : bool
            Whether to pretty-print

        Returns
        -------
        str
            Comments XML string
        """
        if not comment_list:
            return ""

        parts: list[str] = []
        for comment in comment_list:
            parts.append("<!-- ")
            parts.append(comment)
            parts.append(" -->")
            if pretty:
                parts.append(_NEWLINE)

        return "".join(parts)
