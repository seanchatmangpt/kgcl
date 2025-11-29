"""InterfaceA HTTP client for YAWL engine management operations.

This module implements InterfaceA_EnvironmentBasedClient.java behavior -
the management interface for authentication, accounts, and services.

Java Parity (InterfaceA_EnvironmentBasedClient.java):
    - connect(userID, password) -> sessionHandle
    - disconnect(handle) -> success
    - checkConnection(handle) -> boolean
    - getAccounts(handle) -> XML list
    - createAccount, deleteAccount, updatePassword
    - getYAWLServices, addYAWLService, removeYAWLService
    - getExternalDBGateways, getBuildProperties, getClientAccount
    - getIABackendURI() -> String

Interface Path: /yawl/ia
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any
from xml.etree import ElementTree as ET

from kgcl.yawl.clients.interface_client import InterfaceClient, YAWLConnectionError, YAWLResponseError


@dataclass
class InterfaceAClient(InterfaceClient):
    """InterfaceA client for YAWL engine management (Java parity).

    Provides authentication, account management, and service registration
    operations matching Java's InterfaceA_EnvironmentBasedClient.java.

    Parameters
    ----------
    base_url : str
        Base URL of the YAWL engine (e.g., "http://localhost:8080/yawl")

    Examples
    --------
    >>> client = InterfaceAClient("http://localhost:8080/yawl")
    >>> handle = client.connect("admin", "YAWL")
    >>> services = client.get_yawl_services()
    >>> client.disconnect()
    """

    _interface_path: str = field(default="/ia", repr=False)

    def connect(self, user_id: str, password: str) -> str:
        """Connect to YAWL engine and obtain session handle.

        Parameters
        ----------
        user_id : str
            Username for authentication
        password : str
            Password (will be encrypted)

        Returns
        -------
        str
            Session handle for subsequent operations

        Raises
        ------
        YAWLResponseError
            If authentication fails
        YAWLConnectionError
            If network error occurs
        """
        params = self.prepare_param_map("connect", None)
        params["userid"] = user_id
        params["password"] = self._encrypt_password(password)

        response = self.execute_post(self._interface_path, params)

        if not self.successful(response):
            raise YAWLResponseError(self.extract_failure_message(response))

        # Extract session handle from response
        handle = self._extract_session_handle(response)
        self._session_handle = handle
        return handle

    def disconnect(self, handle: str | None = None) -> bool:
        """Disconnect from YAWL engine.

        Parameters
        ----------
        handle : str | None
            Session handle to disconnect (uses stored handle if None)

        Returns
        -------
        bool
            True if disconnect successful
        """
        use_handle = handle or self._session_handle
        params = self.prepare_param_map("disconnect", use_handle)

        response = self.execute_post(self._interface_path, params)

        # Clear stored handle if disconnecting our session
        if handle is None or handle == self._session_handle:
            self._session_handle = None

        return self.successful(response)

    def check_connection(self, handle: str | None = None) -> bool:
        """Check if session is valid.

        Parameters
        ----------
        handle : str | None
            Session handle to check (uses stored handle if None)

        Returns
        -------
        bool
            True if session is valid
        """
        use_handle = handle or self._session_handle
        params = self.prepare_param_map("checkConnection", use_handle)

        response = self.execute_post(self._interface_path, params)

        return self.successful(response)

    def get_accounts(self, handle: str | None = None) -> str:
        """Get list of user accounts.

        Parameters
        ----------
        handle : str | None
            Session handle (uses stored handle if None)

        Returns
        -------
        str
            XML list of accounts

        Raises
        ------
        YAWLConnectionError
            If not connected
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("getAccounts", use_handle)
        return self.execute_post(self._interface_path, params)

    def create_account(self, username: str, password: str, is_admin: bool = False, handle: str | None = None) -> bool:
        """Create new user account.

        Parameters
        ----------
        username : str
            New username
        password : str
            New password
        is_admin : bool
            Whether user is admin
        handle : str | None
            Session handle

        Returns
        -------
        bool
            True if account created
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("createAccount", use_handle)
        params["username"] = username
        params["password"] = self._encrypt_password(password)
        params["isAdmin"] = str(is_admin).lower()

        response = self.execute_post(self._interface_path, params)
        return self.successful(response)

    def delete_account(self, username: str, handle: str | None = None) -> bool:
        """Delete user account.

        Parameters
        ----------
        username : str
            Username to delete
        handle : str | None
            Session handle

        Returns
        -------
        bool
            True if account deleted
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("deleteAccount", use_handle)
        params["username"] = username

        response = self.execute_post(self._interface_path, params)
        return self.successful(response)

    def update_password(self, username: str, old_password: str, new_password: str, handle: str | None = None) -> bool:
        """Update user password.

        Parameters
        ----------
        username : str
            Username
        old_password : str
            Current password
        new_password : str
            New password
        handle : str | None
            Session handle

        Returns
        -------
        bool
            True if password updated
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("updatePassword", use_handle)
        params["username"] = username
        params["oldPassword"] = self._encrypt_password(old_password)
        params["newPassword"] = self._encrypt_password(new_password)

        response = self.execute_post(self._interface_path, params)
        return self.successful(response)

    def get_yawl_services(self, handle: str | None = None) -> str:
        """Get list of registered YAWL services.

        Parameters
        ----------
        handle : str | None
            Session handle

        Returns
        -------
        str
            XML list of services
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("getYAWLServices", use_handle)
        return self.execute_post(self._interface_path, params)

    def add_yawl_service(self, service_xml: str, handle: str | None = None) -> bool:
        """Register a new YAWL service.

        Parameters
        ----------
        service_xml : str
            Service definition XML
        handle : str | None
            Session handle

        Returns
        -------
        bool
            True if service added
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("addYAWLService", use_handle)
        params["service"] = service_xml

        response = self.execute_post(self._interface_path, params)
        return self.successful(response)

    def remove_yawl_service(self, service_uri: str, handle: str | None = None) -> bool:
        """Unregister a YAWL service.

        Parameters
        ----------
        service_uri : str
            URI of service to remove
        handle : str | None
            Session handle

        Returns
        -------
        bool
            True if service removed
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("removeYAWLService", use_handle)
        params["serviceURI"] = service_uri

        response = self.execute_post(self._interface_path, params)
        return self.successful(response)

    def get_build_properties(self, handle: str | None = None) -> str:
        """Get YAWL engine build properties.

        Parameters
        ----------
        handle : str | None
            Session handle

        Returns
        -------
        str
            Properties XML
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("getBuildProperties", use_handle)
        return self.execute_post(self._interface_path, params)

    def get_external_db_gateways(self, handle: str | None = None) -> str:
        """Get list of external database gateways.

        Parameters
        ----------
        handle : str | None
            Session handle

        Returns
        -------
        str
            Gateways XML
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("getExternalDBGateways", use_handle)
        return self.execute_post(self._interface_path, params)

    def get_client_account(self, handle: str | None = None) -> str:
        """Get current user's account information.

        Parameters
        ----------
        handle : str | None
            Session handle

        Returns
        -------
        str
            Account XML
        """
        use_handle = handle or self._session_handle
        self._require_connection(use_handle)

        params = self.prepare_param_map("getClientAccount", use_handle)
        return self.execute_post(self._interface_path, params)

    def get_ia_backend_uri(self) -> str:
        """Get the InterfaceA backend URI.

        Returns
        -------
        str
            Full URI for InterfaceA endpoint
        """
        return self._build_uri(self._interface_path)

    def _require_connection(self, handle: str | None) -> None:
        """Raise if no connection handle available.

        Parameters
        ----------
        handle : str | None
            Handle to check

        Raises
        ------
        YAWLConnectionError
            If handle is None
        """
        if handle is None:
            raise YAWLConnectionError("Not connected - call connect() first")

    def _encrypt_password(self, password: str) -> str:
        """Encrypt password (Java parity: PasswordEncryptor.encrypt).

        Java uses SHA-256 hash encoded as hex string.

        Parameters
        ----------
        password : str
            Plain text password

        Returns
        -------
        str
            Encrypted password (SHA-256 hex)
        """
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _extract_session_handle(self, response: str) -> str:
        """Extract session handle from connect response.

        Parameters
        ----------
        response : str
            XML response containing session handle

        Returns
        -------
        str
            Session handle string
        """
        # Try XML parsing first
        try:
            root = ET.fromstring(response)
            if root.tag == "sessionHandle" and root.text:
                return root.text.strip()
            handle_elem = root.find(".//sessionHandle")
            if handle_elem is not None and handle_elem.text:
                return handle_elem.text.strip()
        except ET.ParseError:
            pass

        # Fallback: regex extraction
        match = re.search(r"<sessionHandle>(.*?)</sessionHandle>", response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # If response is just the handle (no XML wrapper)
        if response and "<" not in response:
            return response.strip()

        return response
