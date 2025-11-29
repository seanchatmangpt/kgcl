"""Mail settings utility for email configuration.

Manages email settings including SMTP configuration and message details.
"""

from __future__ import annotations

import logging

from kgcl.yawl.util.string_util import str_to_int
from kgcl.yawl.util.xml.xnode import XNode
from kgcl.yawl.util.xml.xnode_parser import XNodeParser

logger = logging.getLogger(__name__)


class MailSettings:
    """Mail settings configuration.

    Manages SMTP settings and email message details.

    Attributes
    ----------
    host : str | None
        SMTP host
    port : int
        SMTP port (default: 25)
    strategy : str
        Transport strategy (default: "SMTPS")
    user : str | None
        SMTP username
    password : str | None
        SMTP password
    from_name : str | None
        Sender name
    from_address : str | None
        Sender email address
    to_name : str | None
        Recipient name
    to_address : str | None
        Recipient email address
    cc_address : str | None
        CC email address
    bcc_address : str | None
        BCC email address
    subject : str | None
        Email subject
    content : str | None
        Email content
    """

    def __init__(self) -> None:
        """Initialize mail settings with defaults."""
        self.host: str | None = None
        self.port: int = 25
        self.strategy: str = "SMTPS"
        self.user: str | None = None
        self.password: str | None = None
        self.from_name: str | None = None
        self.from_address: str | None = None
        self.to_name: str | None = None
        self.to_address: str | None = None
        self.cc_address: str | None = None
        self.bcc_address: str | None = None
        self.subject: str | None = None
        self.content: str | None = None

    def get_setting(self, name: str) -> str | int | None:
        """Get setting value by name.

        Parameters
        ----------
        name : str
            Setting name

        Returns
        -------
        str | int | None
            Setting value, or None if not found
        """
        settings_map: dict[str, str | int | None] = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "senderName": self.from_name,
            "senderAddress": self.from_address,
            "recipientName": self.to_name,
            "recipientAddress": self.to_address,
            "CC": self.cc_address,
            "BCC": self.bcc_address,
            "subject": self.subject,
            "content": self.content,
        }
        return settings_map.get(name)

    def copy_of(self) -> MailSettings:
        """Create a copy of these settings.

        Returns
        -------
        MailSettings
            Copy of settings
        """
        logger.debug("enter MailSettings.copy_of()")
        settings = MailSettings()
        settings.host = self.host
        settings.port = self.port
        settings.strategy = self.strategy
        settings.user = self.user
        settings.password = self.password
        settings.from_name = self.from_name
        settings.from_address = self.from_address
        settings.to_name = self.to_name
        settings.to_address = self.to_address
        settings.cc_address = self.cc_address
        settings.bcc_address = self.bcc_address
        settings.subject = self.subject
        settings.content = self.content
        logger.debug("copyOf() returning %s", settings.to_xml())
        return settings

    def to_xml(self) -> str:
        """Convert settings to XML.

        Returns
        -------
        str
            XML representation of settings
        """
        node = XNode("mailsettings")
        node.add_child("host", self.host)
        node.add_child("port", self.port)
        node.add_child("user", self.user)
        node.add_child("password", self.password)
        node.add_child("fromname", self.from_name)
        node.add_child("fromaddress", self.from_address)
        node.add_child("toname", self.to_name)
        node.add_child("toaddress", self.to_address)
        node.add_child("CC", self.cc_address)
        node.add_child("BCC", self.bcc_address)
        node.add_child("subject", self.subject, escape=True)
        node.add_child("content", self.content, escape=True)
        return node.to_string()

    def from_xml(self, xml: str) -> None:
        """Load settings from XML.

        Parameters
        ----------
        xml : str
            XML string containing settings
        """
        logger.debug("enter fromXML(%s)", xml)
        parser = XNodeParser()
        node = parser.parse(xml)
        if node:
            self.host = node.get_child_text("host")
            self.port = str_to_int(node.get_child_text("port"), 25)
            self.user = node.get_child_text("user")
            self.password = node.get_child_text("password")
            self.from_name = node.get_child_text("fromname")
            self.from_address = node.get_child_text("fromaddress")
            self.to_name = node.get_child_text("toname")
            self.to_address = node.get_child_text("toaddress")
            self.cc_address = node.get_child_text("CC")
            self.bcc_address = node.get_child_text("BCC")
            self.subject = node.get_child_text("subject", escape=True)
            self.content = node.get_child_text("content", escape=True)
        logger.debug("returning from fromXML()")
