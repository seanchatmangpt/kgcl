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

from kgcl.yawl.interface import InterfaceAClient

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

        # Establish connection to engine and get session handle
        try:
            response = self._ia_client.connect()
            if not self._ia_client.successful(response):
                logger.error(f"Failed to connect to Interface A: {response}")
        except OSError as e:
            logger.error(f"Failed to setup Interface A: {e}")

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

            if not self._ia_client.session_handle:
                return self._fail_msg("Interface A not connected")

            # Get stored password from engine via Interface A
            stored_password = self._ia_client.get_client_password(userid, self._ia_client.session_handle)

            if not self._ia_client.successful(stored_password):
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
