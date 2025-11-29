"""Verification utilities for YAWL workflows.

Provides verification message handling for validation and error reporting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from kgcl.yawl.util.xml.xnode import XNode


class MessageType(Enum):
    """Type of verification message."""

    ERROR = "error"
    WARNING = "warning"


@dataclass
class YVerificationMessage:
    """Verification message with source and message text.

    Parameters
    ----------
    source : object | None
        Source object that generated the message
    message : str
        Message text
    """

    source: object | None
    message: str

    def get_source(self) -> object | None:
        """Get source object.

        Returns
        -------
        object | None
            Source object
        """
        return self.source

    def get_message(self) -> str:
        """Get message text.

        Returns
        -------
        str
            Message text
        """
        return self.message

    def set_source(self, source: object | None) -> None:
        """Set source object.

        Parameters
        ----------
        source : object | None
            Source object
        """
        self.source = source


class YVerificationHandler:
    """Handler for verification messages (errors and warnings).

    Collects and manages verification messages during validation or
    processing operations.

    Attributes
    ----------
    errors : list[YVerificationMessage]
        List of error messages
    warnings : list[YVerificationMessage]
        List of warning messages
    """

    def __init__(self) -> None:
        """Initialize verification handler."""
        self.errors: list[YVerificationMessage] = []
        self.warnings: list[YVerificationMessage] = []

    def error(self, obj: object, message: str) -> None:
        """Add an error message.

        Parameters
        ----------
        obj : object
            Source object
        message : str
            Error message
        """
        self.errors.append(YVerificationMessage(obj, message))

    def warn(self, obj: object, message: str) -> None:
        """Add a warning message.

        Parameters
        ----------
        obj : object
            Source object
        message : str
            Warning message
        """
        self.warnings.append(YVerificationMessage(obj, message))

    def add(self, obj: object, message: str, msg_type: MessageType) -> None:
        """Add a message of specified type.

        Parameters
        ----------
        obj : object
            Source object
        message : str
            Message text
        msg_type : MessageType
            Type of message (error or warning)
        """
        if msg_type == MessageType.ERROR:
            self.error(obj, message)
        elif msg_type == MessageType.WARNING:
            self.warn(obj, message)

    def reset(self) -> None:
        """Clear all messages."""
        self.errors.clear()
        self.warnings.clear()

    def has_errors(self) -> bool:
        """Check if there are any errors.

        Returns
        -------
        bool
            True if there are errors
        """
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any warnings.

        Returns
        -------
        bool
            True if there are warnings
        """
        return len(self.warnings) > 0

    def has_messages(self) -> bool:
        """Check if there are any messages (errors or warnings).

        Returns
        -------
        bool
            True if there are any messages
        """
        return self.has_errors() or self.has_warnings()

    def get_errors(self) -> list[YVerificationMessage]:
        """Get all error messages.

        Returns
        -------
        list[YVerificationMessage]
            List of error messages
        """
        return list(self.errors)

    def get_warnings(self) -> list[YVerificationMessage]:
        """Get all warning messages.

        Returns
        -------
        list[YVerificationMessage]
            List of warning messages
        """
        return list(self.warnings)

    def get_messages(self) -> list[YVerificationMessage]:
        """Get all messages (errors and warnings).

        Returns
        -------
        list[YVerificationMessage]
            List of all messages
        """
        return list(self.errors) + list(self.warnings)

    def get_message_count(self) -> int:
        """Get total number of messages.

        Returns
        -------
        int
            Total count of errors and warnings
        """
        return len(self.errors) + len(self.warnings)

    def get_messages_xml(self) -> str:
        """Get XML representation of all messages.

        Returns
        -------
        str
            XML string containing all verification messages
        """
        parent_node = XNode("verificationMessages")
        for message in self.errors:
            self._populate_node(parent_node.add_child("error"), message)
        for message in self.warnings:
            self._populate_node(parent_node.add_child("warning"), message)
        return parent_node.to_string()

    def _populate_node(self, msg_node: XNode, message: YVerificationMessage) -> None:
        """Populate XML node with message data.

        Parameters
        ----------
        msg_node : XNode
            XML node to populate
        message : YVerificationMessage
            Message to add
        """
        if message.get_source() is not None:
            source_str = str(message.get_source())
            msg_node.add_child("source", source_str)
        msg_node.add_child("message", message.get_message())
