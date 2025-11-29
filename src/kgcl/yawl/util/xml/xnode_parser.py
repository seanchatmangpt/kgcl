"""XNodeParser for parsing XML strings into XNode structures.

Parses simple XML strings into XNode structures, handling elements, attributes,
comments, and CDATA.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

from kgcl.yawl.util.xml.xnode import ContentType, XNode

_UTF8_BOM = "\ufeff"
_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'

logger = logging.getLogger(__name__)


class XNodeParser:
    """Parser for converting XML strings to XNode structures.

    Parameters
    ----------
    check : bool, optional
        Whether to validate XML well-formedness, by default False
    suppress_messages : bool, optional
        Whether to suppress error messages, by default False
    """

    def __init__(self, check: bool = False, suppress_messages: bool = False) -> None:
        """Initialize XNodeParser.

        Parameters
        ----------
        check : bool, optional
            Whether to validate XML well-formedness, by default False
        suppress_messages : bool, optional
            Whether to suppress error messages, by default False
        """
        self.check = check
        self._suppress_messages = suppress_messages
        self._attribute_splitter = re.compile(r'\s*=\s*"|"\s*')
        self._opening_comments: list[str] | None = None
        self._closing_comments: list[str] | None = None

    def parse(self, xml: str | Element | None) -> XNode | None:
        """Parse XML string, Element, or Document into XNode.

        Parameters
        ----------
        xml : str | Element | None
            XML string, ElementTree Element, or None

        Returns
        -------
        XNode | None
            Parsed XNode, or None if parsing fails
        """
        if xml is None:
            return None

        # Handle ElementTree Element
        if hasattr(xml, "tag"):
            from kgcl.yawl.util.xml.jdom_util import element_to_string

            xml_str = element_to_string(xml)
            if xml_str:
                return self._parse_string(xml_str)
            return None

        # Handle string
        if isinstance(xml, str):
            return self._parse_string(xml)

        return None

    def suppress_messages(self, suppress: bool) -> None:
        """Set whether to suppress error messages.

        Parameters
        ----------
        suppress : bool
            True to suppress messages, False to show them
        """
        self._suppress_messages = suppress

    def _parse_string(self, s: str) -> XNode | None:
        """Parse XML string into XNode.

        Parameters
        ----------
        s : str
            XML string to parse

        Returns
        -------
        XNode | None
            Parsed XNode, or None if parsing fails
        """
        if not s or not s.strip():
            return None

        # Remove UTF-8 BOM if present
        if s.startswith(_UTF8_BOM):
            s = s[1:]

        # Remove XML header
        if s.strip().startswith("<?xml"):
            idx = s.find("?>")
            if idx != -1:
                s = s[idx + 2 :].strip()

        # Remove DOCTYPE
        if s.strip().startswith("<!DOCTYPE"):
            idx = s.find(">")
            if idx != -1:
                s = s[idx + 1 :].strip()

        # Validate well-formedness if requested
        if self.check:
            from kgcl.yawl.util.xml.jdom_util import string_to_element

            if string_to_element(s) is None:
                return None

        return self._parse(s, 0)

    def _parse(self, s: str, depth: int) -> XNode | None:
        """Internal recursive parse method.

        Parameters
        ----------
        s : str
            XML string to parse
        depth : int
            Current depth in tree

        Returns
        -------
        XNode | None
            Parsed XNode, or None if parsing fails
        """
        self._init()

        try:
            s = s.strip()
            if not s.startswith("<"):
                raise ValueError("bad input string")

            # Handle outlying comments at root level
            if depth == 0:
                s = self._process_outlying_comments(s)

            # Get tag definition (content of opening tag)
            tag_end = s.find(">")
            if tag_end == -1:
                raise ValueError("missing closing '>'")

            tag_def = s[1:tag_end]
            node = self._new_node(tag_def, depth)

            # If not self-closing tag, parse content
            if not tag_def.endswith("/"):
                # Get content between opening and closing tags
                content_start = tag_end + 1
                content_end = s.rfind("<")
                if content_end > content_start:
                    inner_content = s[content_start:content_end].strip()

                    # Parse content pieces
                    for content_piece in self._parse_content(inner_content):
                        if content_piece.startswith("<!--"):
                            comment = self._extract_comment(content_piece)
                            node.add_comment(comment)
                        elif content_piece.startswith("<![CDATA["):
                            cdata = self._extract_cdata(content_piece)
                            node.add_cdata(cdata)
                        elif content_piece.startswith("<"):
                            # Recursive parse child element
                            child = self._parse(content_piece, depth + 1)
                            if child:
                                node.add_child(child)
                        else:
                            # Text content
                            if "{" in content_piece:
                                from kgcl.yawl.util.xml.jdom_util import decode_escapes

                                content_piece = decode_escapes(content_piece)
                            node.set_text(content_piece)

            return node

        except Exception as e:
            if not self._suppress_messages:
                logger.error("Invalid format parsing string [%s] - %s", s, str(e))
            return None

    def _new_node(self, tag_def: str, depth: int) -> XNode:
        """Create a new XNode from tag definition.

        Parameters
        ----------
        tag_def : str
            Tag definition (name + attributes)
        depth : int
            Depth in tree

        Returns
        -------
        XNode
            New XNode
        """
        # Remove trailing '/' if self-closing
        if tag_def.endswith("/"):
            tag_def = tag_def[:-1]

        tag_def = tag_def.strip()
        name = self._get_first_word(tag_def)
        node = XNode(name)
        node.set_depth(depth)

        # Parse attributes
        attributes = self._str_subtract(tag_def, name).strip()
        if attributes:
            # Split attributes using regex
            parts = self._attribute_splitter.split(attributes)
            # Parts alternate: key, value, key, value, ...
            for i in range(0, len(parts) - 1, 2):
                if i + 1 < len(parts):
                    key = parts[i].strip()
                    value = parts[i + 1].strip()
                    if key and value:
                        node.add_attribute(key, value)

        # Add outlying comments if root node
        if depth == 0:
            self._add_outlying_comments(node)

        return node

    def _get_first_word(self, s: str) -> str:
        """Get first word from string (up to first whitespace).

        Parameters
        ----------
        s : str
            String to extract word from

        Returns
        -------
        str
            First word
        """
        for i, char in enumerate(s):
            if char.isspace():
                return s[:i]

        return s

    def _str_subtract(self, subtractee: str, subtractor: str) -> str:
        """Remove substring from string.

        Parameters
        ----------
        subtractee : str
            String to subtract from
        subtractor : str
            Substring to remove

        Returns
        -------
        str
            String with substring removed
        """
        idx = subtractee.find(subtractor)
        if idx != -1:
            return subtractee[idx + len(subtractor) :]

        return subtractee

    def _parse_content(self, content: str) -> list[str]:
        """Parse content into list of pieces (comments, CDATA, elements, text).

        Parameters
        ----------
        content : str
            Content to parse

        Returns
        -------
        list[str]
            List of content pieces
        """
        content_list: list[str] = []
        content = content.strip()

        while content:
            if content.startswith("<!--"):
                # Comment
                end_idx = content.find("-->")
                if end_idx != -1:
                    sub_content = content[: end_idx + 3]
                    content_list.append(sub_content)
                    content = content[len(sub_content) :].strip()
                else:
                    break
            elif content.startswith("<![CDATA["):
                # CDATA
                end_idx = content.find("]]>")
                if end_idx != -1:
                    sub_content = content[: end_idx + 3]
                    content_list.append(sub_content)
                    content = content[len(sub_content) :].strip()
                else:
                    break
            elif content.startswith("<"):
                # Child element
                sub_content = self._get_sub_content(content)
                content_list.append(sub_content)
                content = content[len(sub_content) :].strip()
            else:
                # Text content (take everything up to next '<')
                next_tag = content.find("<")
                if next_tag != -1:
                    sub_content = content[:next_tag]
                    content_list.append(sub_content)
                    content = content[len(sub_content) :].strip()
                else:
                    # Last piece of text
                    content_list.append(content)
                    break

        return content_list

    def _get_sub_content(self, s: str) -> str:
        """Get sub-content for a child element (including the element itself).

        Parameters
        ----------
        s : str
            String starting with '<'

        Returns
        -------
        str
            Complete element string including tags
        """
        tag_end = s.find(">")
        if tag_end == -1:
            return s

        tag = s[1:tag_end]

        # If self-closing, return just this tag
        if tag.endswith("/"):
            return s[: tag_end + 1]

        # Find matching closing tag
        tag_name = self._get_first_word(tag)
        openers = self._get_index_list(s, f"<{tag_name}")
        closers = self._get_index_list(s, f"</{tag_name}")

        if not openers or not closers:
            return s[: tag_end + 1]

        closer_pos = self._get_corresponding_closer_pos(openers, closers)
        if closer_pos != -1:
            end_pos = closer_pos + len(tag_name) + 2  # "</tagname>"
            return s[: end_pos + 1]

        return s[: tag_end + 1]

    def _get_index_list(self, s: str, sub: str) -> list[int]:
        """Get list of indices where substring appears as a tag.

        Parameters
        ----------
        s : str
            String to search
        sub : str
            Substring to find (e.g., "<tagname" or "</tagname")

        Returns
        -------
        list[int]
            List of indices
        """
        index_list: list[int] = []
        offset = len(sub)
        pos = s.find(sub)

        while pos != -1:
            if self._is_book_end_tag(s, pos + offset):
                index_list.append(pos)
            pos = s.find(sub, pos + offset)

        return index_list

    def _is_book_end_tag(self, s: str, pos: int) -> bool:
        """Check if position is a proper tag end (not self-closing).

        Parameters
        ----------
        s : str
            String
        pos : int
            Position after tag name

        Returns
        -------
        bool
            True if proper tag end
        """
        return self._last_char_delineates_tag(s, pos) and not self._is_self_closing_tag(s, pos)

    def _last_char_delineates_tag(self, s: str, pos: int) -> bool:
        """Check if character at position delineates tag end.

        Parameters
        ----------
        s : str
            String
        pos : int
            Position to check

        Returns
        -------
        bool
            True if character delineates tag
        """
        if pos >= len(s) - 1:
            return s[-1] == ">"

        return s[pos].isspace() or s[pos] == ">"

    def _is_self_closing_tag(self, s: str, pos: int) -> bool:
        """Check if tag is self-closing.

        Parameters
        ----------
        s : str
            String
        pos : int
            Position after tag name

        Returns
        -------
        bool
            True if self-closing
        """
        # Skip whitespace
        while pos < len(s) - 2 and s[pos].isspace():
            pos += 1

        return pos < len(s) - 1 and s[pos] == "/" and s[pos + 1] == ">"

    def _get_corresponding_closer_pos(self, openers: list[int], closers: list[int]) -> int:
        """Get position of corresponding closing tag.

        Parameters
        ----------
        openers : list[int]
            List of opening tag positions
        closers : list[int]
            List of closing tag positions

        Returns
        -------
        int
            Position of corresponding closer, or -1 if not found
        """
        if len(openers) == 1 or len(closers) == 1:
            return closers[0] if closers else -1

        open_index = 1
        close_index = 0
        accumulator = 1

        while accumulator > 0:
            if open_index < len(openers) and close_index < len(closers):
                if openers[open_index] < closers[close_index]:
                    accumulator += 1
                    open_index += 1
                else:
                    accumulator -= 1
                    if accumulator > 0:
                        close_index += 1
            else:
                # Use last closer
                return closers[-1] if closers else -1

        return closers[close_index] if close_index < len(closers) else -1

    def _init(self) -> None:
        """Initialize parser state."""
        self._opening_comments = None
        self._closing_comments = None

    def _process_opening_comments(self, s: str) -> str:
        """Process opening comments (before root).

        Parameters
        ----------
        s : str
            String to process

        Returns
        -------
        str
            String with opening comments removed and stored
        """
        if not s.startswith("<!--"):
            return s

        if self._opening_comments is None:
            self._opening_comments = []

        while s.startswith("<!--"):
            comment = self._extract_comment(s)
            self._opening_comments.append(comment)
            end_idx = s.find("-->")
            if end_idx != -1:
                s = s[end_idx + 3 :].strip()
            else:
                break

        return s

    def _process_closing_comments(self, s: str) -> str:
        """Process closing comments (after root).

        Parameters
        ----------
        s : str
            String to process

        Returns
        -------
        str
            String with closing comments removed and stored
        """
        if not s.endswith("-->"):
            return s

        if self._closing_comments is None:
            self._closing_comments = []

        while s.endswith("-->"):
            comment = self._extract_trailing_comment(s)
            self._closing_comments.append(comment)
            start_idx = s.rfind("<!--")
            if start_idx != -1:
                s = s[:start_idx].strip()
            else:
                break

        return s

    def _process_outlying_comments(self, s: str) -> str:
        """Process both opening and closing comments.

        Parameters
        ----------
        s : str
            String to process

        Returns
        -------
        str
            String with comments processed
        """
        return self._process_opening_comments(self._process_closing_comments(s))

    def _add_outlying_comments(self, node: XNode) -> None:
        """Add outlying comments to node.

        Parameters
        ----------
        node : XNode
            Node to add comments to
        """
        if self._opening_comments:
            for comment in self._opening_comments:
                node.add_opening_comment(comment)

        if self._closing_comments:
            for comment in self._closing_comments:
                node.add_closing_comment(comment)

    def _extract_comment(self, raw_comment: str) -> str:
        """Extract comment text from comment tag.

        Parameters
        ----------
        raw_comment : str
            Raw comment string (e.g., "<!-- comment -->")

        Returns
        -------
        str
            Comment text
        """
        end_idx = raw_comment.find("-->")
        if end_idx != -1:
            return raw_comment[4:end_idx].strip()

        return raw_comment[4:].strip()

    def _extract_trailing_comment(self, raw_comment: str) -> str:
        """Extract trailing comment text.

        Parameters
        ----------
        raw_comment : str
            Raw comment string

        Returns
        -------
        str
            Comment text
        """
        start_idx = raw_comment.rfind("<!--")
        if start_idx != -1:
            return raw_comment[start_idx + 4 : -3].strip()

        return raw_comment[4:-3].strip()

    def _extract_cdata(self, raw_cdata: str) -> str:
        """Extract CDATA content.

        Parameters
        ----------
        raw_cdata : str
            Raw CDATA string (e.g., "<![CDATA[content]]>")

        Returns
        -------
        str
            CDATA content
        """
        end_idx = raw_cdata.find("]]>")
        if end_idx != -1:
            return raw_cdata[9:end_idx]

        return raw_cdata[9:]
