"""Session management utility for YAWL workflows.

A generic session manager utility that can be used by custom services to allow
connections from any service or client application that has been registered in
the engine.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

_INVALID_CREDENTIALS = "Invalid credentials"
_INACTIVITY_TIMEOUT_MINUTES = 60


class Sessions:
    """Session manager for YAWL services.

    Manages user sessions with inactivity timeouts. Sessions expire after
    60 minutes of inactivity.

    Parameters
    ----------
    ia_uri : str | None, optional
        URI of engine's Interface A, by default None
    ia_userid : str | None, optional
        Userid for Interface A connection, by default None
    ia_password : str | None, optional
        Password for Interface A connection, by default None
    """

    def __init__(self, ia_uri: str | None = None, ia_userid: str | None = None, ia_password: str | None = None) -> None:
        """Initialize Sessions manager.

        Parameters
        ----------
        ia_uri : str | None, optional
            URI of engine's Interface A, by default None
        ia_userid : str | None, optional
            Userid for Interface A connection, by default None
        ia_password : str | None, optional
            Password for Interface A connection, by default None
        """
        self._id_to_handle: dict[str, str] = {}
        self._handle_to_timer: dict[str, asyncio.Task[None]] = {}
        self._background_tasks: set[asyncio.Task[None]] = set()
        self._ia_client: InterfaceAClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        if ia_uri and ia_userid and ia_password:
            self.setup_interface_a(ia_uri, ia_userid, ia_password)

    def setup_interface_a(self, ia_uri: str, ia_userid: str, ia_password: str) -> None:
        """Setup Interface A connection for credential retrieval.

        Uses the parameters passed to connect to the engine via Interface A
        so that registered services' and client applications' credentials can
        be retrieved. This method must be called before any sessions can be
        authenticated.

        Parameters
        ----------
        ia_uri : str
            URI of the engine's Interface A
        ia_userid : str
            Userid of the registered service or client app
        ia_password : str
            Password of the registered service or client app
        """
        self._ia_client = InterfaceAClient(ia_uri, ia_userid, ia_password)

    async def shutdown(self) -> None:
        """Cancel all current sessions and their inactivity timers.

        Usually called from cleanup/shutdown handlers.
        """
        handles = list(self._handle_to_timer.keys())
        for handle in handles:
            await self._remove_activity_timer(handle)

    def connect(self, userid: str, password: str) -> str:
        """Attempt to establish a session using credentials.

        Parameters
        ----------
        userid : str
            Userid of a registered service or client application
        password : str
            Corresponding password

        Returns
        -------
        str
            Session handle if successful, or XML error message if not
        """
        try:
            if not self._ia_client:
                return self._fail_msg("Interface A not configured")

            stored_password = self._ia_client.get_password(userid)
            if not stored_password or stored_password.startswith("<fail"):
                return self._fail_msg(_INVALID_CREDENTIALS)

            if stored_password == password:
                return self._get_handle(userid)

            return self._fail_msg(_INVALID_CREDENTIALS)

        except Exception as e:
            return self._fail_msg(str(e))

    def check_connection(self, handle: str | None) -> bool:
        """Check that a session handle is valid and active.

        Parameters
        ----------
        handle : str | None
            Session handle to check

        Returns
        -------
        bool
            True if session handle is known and active, False otherwise
        """
        if handle and handle in self._handle_to_timer:
            # Refresh activity timer
            task = asyncio.create_task(self._refresh_activity_timer(handle))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
            return True

        return False

    def disconnect(self, handle: str) -> bool:
        """End a session.

        Parameters
        ----------
        handle : str
            Session handle to cancel

        Returns
        -------
        bool
            True if session was known and has been disconnected,
            False if handle was already disconnected
        """
        for userid, active_handle in list(self._id_to_handle.items()):
            if active_handle == handle:
                del self._id_to_handle[userid]
                # Clean up timer
                task = asyncio.create_task(self._remove_activity_timer(handle))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
                return True

        return False

    def _get_handle(self, userid: str) -> str:
        """Create and store a new session handle for a userid.

        Parameters
        ----------
        userid : str
            Userid to create handle for (assumed authenticated)

        Returns
        -------
        str
            Session handle
        """
        handle = self._id_to_handle.get(userid)
        if handle is None:
            handle = str(uuid.uuid4())
            self._id_to_handle[userid] = handle

        # Start inactivity timer
        task = asyncio.create_task(self._start_activity_timer(handle))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return handle

    async def _refresh_activity_timer(self, handle: str) -> None:
        """Restart inactivity timer for a session handle.

        Parameters
        ----------
        handle : str
            Session handle to refresh timer for
        """
        await self._remove_activity_timer(handle)
        await self._start_activity_timer(handle)

    async def _start_activity_timer(self, handle: str) -> None:
        """Start inactivity timer for a session handle.

        The handle will expire after 60 minutes of inactivity.

        Parameters
        ----------
        handle : str
            Session handle to start timer for
        """

        async def timeout_handler() -> None:
            await asyncio.sleep(_INACTIVITY_TIMEOUT_MINUTES * 60)
            self.disconnect(handle)

        task = asyncio.create_task(timeout_handler())
        self._handle_to_timer[handle] = task

    async def _remove_activity_timer(self, handle: str) -> None:
        """Cancel inactivity timer for a session handle.

        Parameters
        ----------
        handle : str
            Session handle to cancel timer for
        """
        task = self._handle_to_timer.pop(handle, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    def _fail_msg(self, msg: str) -> str:
        """Format failure message as XML.

        Parameters
        ----------
        msg : str
            Error message

        Returns
        -------
        str
            XML-wrapped failure message
        """
        from kgcl.yawl.util.string_util import wrap

        return wrap(msg, "failure")


class InterfaceAClient:
    """Client for engine Interface A to obtain credentials.

    Creates a client to the engine via Interface A to obtain logon credentials
    for custom services and client applications registered with the engine.

    Parameters
    ----------
    uri : str
        URI of engine's Interface A
    userid : str
        Userid registered as custom service or client app
    password : str
        Corresponding password
    """

    _NO_CREDENTIALS = "No Interface A credentials supplied to service"

    def __init__(self, uri: str, userid: str, password: str) -> None:
        """Initialize Interface A client.

        Parameters
        ----------
        uri : str
            URI of engine's Interface A
        userid : str
            Userid for connection
        password : str
            Password for connection

        Notes
        -----
        Currently uses MockInterfaceAClient for testing. For production use with
        a real YAWL engine, set USE_MOCK_INTERFACE_A=False environment variable.
        """
        self.ia_uri: str = uri
        self.ia_userid: str = userid
        self.ia_password: str = password
        self.ia_handle: str | None = None

        # MIGRATION: Use mock by default, real client when available
        # See: docs/adr/001-mock-interface-a-client.md
        import os

        use_mock = os.getenv("USE_MOCK_INTERFACE_A", "true").lower() == "true"

        if use_mock:
            from kgcl.yawl.util.mock_interface_a import MockInterfaceAClient

            self._ia_client: Any = MockInterfaceAClient(uri, userid, password)
            # Pre-register the connecting user for convenience
            self._ia_client.register_user(userid, password)
        else:
            # Real implementation: InterfaceA_EnvironmentBasedClient
            self._ia_client: Any = None  # Set to real client when available

    def get_password(self, userid: str) -> str | None:
        """Get password from engine for a userid.

        Parameters
        ----------
        userid : str
            Userid to get password for

        Returns
        -------
        str | None
            Retrieved password, or error message if userid is unknown

        Raises
        ------
        OSError
            If there's a problem connecting to the engine

        Notes
        -----
        Uses MockInterfaceAClient by default for testing. For production:
        - Set USE_MOCK_INTERFACE_A=false environment variable
        - Implement real InterfaceA_EnvironmentBasedClient
        """
        self._check_connection()
        if not userid:
            raise OSError(_INVALID_CREDENTIALS)

        # With mock client, this works directly
        if self._ia_client:
            return self._ia_client.get_password(userid)

        # Real implementation path (when USE_MOCK_INTERFACE_A=false)
        # MIGRATION: Implement when InterfaceA client is available
        # service = self._get_service_account(userid)
        # if service:
        #     return service.get_password()
        # return self._ia_client.get_password(userid, self.ia_handle)

        return None

    def _get_service_account(self, userid: str) -> Any | None:
        """Get YAWL service using userid.

        Parameters
        ----------
        userid : str
            Userid of service to get

        Returns
        -------
        Any | None
            Matching service, or None if not found

        Raises
        ------
        OSError
            If there's a problem connecting to the engine
        """
        # TODO: Implement when InterfaceA client is available
        # for service in self._ia_client.get_registered_yawl_services(
        #     self.ia_handle
        # ):
        #     if service.get_service_name() == userid:
        #         return service
        return None

    def _check_connection(self) -> None:
        """Check and establish Interface A connection if needed.

        Raises
        ------
        OSError
            If URI or credentials are missing, or connection fails

        Notes
        -----
        With MockInterfaceAClient, this always succeeds for testing.
        Real implementation requires actual network connection.
        """
        if not self.ia_userid or not self.ia_password or not self.ia_uri:
            raise OSError(self._NO_CREDENTIALS)

        # Mock client doesn't need connection check
        if self._ia_client and hasattr(self._ia_client, "check_connection"):
            # Already connected or mock
            return

        # Real implementation path
        # MIGRATION: Uncomment when InterfaceA_EnvironmentBasedClient available
        # if not self._ia_client:
        #     self._ia_client = InterfaceA_EnvironmentBasedClient(self.ia_uri)
        #
        # if (
        #     not self.ia_handle
        #     or not self._ia_client.successful(self.ia_handle)
        #     or not self._ia_client.successful(
        #         self._ia_client.check_connection(self.ia_handle)
        #     )
        # ):
        #     self.ia_handle = self._ia_client.connect(
        #         self.ia_userid, self.ia_password
        #     )
        #     if not self._ia_client.successful(self.ia_handle):
        #         raise OSError(self._get_inner_msg(self.ia_handle))

    def _get_inner_msg(self, xml_message: str) -> str:
        """Strip XML tags from error message.

        Parameters
        ----------
        xml_message : str
            XML message to strip

        Returns
        -------
        str
            Innermost text
        """
        from kgcl.yawl.util.string_util import unwrap

        result = xml_message
        while result and result.startswith("<"):
            result = unwrap(result) or result
            if result == xml_message:  # Prevent infinite loop
                break

        return result
