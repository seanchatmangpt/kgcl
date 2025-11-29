"""Client event system for YAWL service notifications.

This module implements the event pattern from Java's ClientEvent and
ClientEventListener, enabling pub/sub notifications for client operations.

Java Parity:
    - ClientEvent.java: ClientEvent, ClientEvent.Action enum (5 core actions)
    - ClientEventListener.java: ClientEventListener interface

Python Extensions:
    - CANCEL_CASE, WORK_ITEM_UPDATE (additional actions for engine operations)
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Protocol


class ClientAction(Enum):
    """Actions that trigger client events.

    Core actions (Java parity - ClientEvent.Action):
        SPECIFICATION_UPLOAD, SPECIFICATION_UNLOAD, LAUNCH_CASE,
        SERVICE_ADD, SERVICE_REMOVE

    Extended actions (Python):
        CANCEL_CASE, WORK_ITEM_UPDATE
    """

    # Java core actions (ClientEvent.Action)
    SPECIFICATION_UPLOAD = auto()
    SPECIFICATION_UNLOAD = auto()
    LAUNCH_CASE = auto()
    SERVICE_ADD = auto()
    SERVICE_REMOVE = auto()
    # Python extensions
    CANCEL_CASE = auto()
    WORK_ITEM_UPDATE = auto()


@dataclass(frozen=True)
class ClientEvent:
    """Event emitted by client operations (mirrors Java ClientEvent).

    Java fields:
        private final Action _action
        private final Object _object

    Parameters
    ----------
    action : ClientAction
        The type of action that triggered this event
    payload : Any
        The object associated with the event (e.g., specification ID, case ID)

    Examples
    --------
    >>> event = ClientEvent(action=ClientAction.SPECIFICATION_UPLOAD, payload=spec_id)
    >>> event.get_action()
    <ClientAction.SPECIFICATION_UPLOAD: 1>
    >>> event.get_object()  # Java-style getter
    spec_id
    """

    action: ClientAction
    payload: Any

    def __str__(self) -> str:
        """Return string representation of event."""
        return f"ClientEvent({self.action.name}, {self.payload})"

    def get_action(self) -> ClientAction:
        """Get action (Java parity method).

        Returns
        -------
        ClientAction
            The action that triggered this event
        """
        return self.action

    def get_object(self) -> Any:
        """Get payload object (Java parity method - _object field).

        Returns
        -------
        Any
            The object associated with the event
        """
        return self.payload


class ClientEventListener(Protocol):
    """Protocol for client event listeners.

    Mirrors Java's ClientEventListener interface. Implementations receive
    notifications when client operations occur.

    Examples
    --------
    >>> class MyListener:
    ...     def on_client_event(self, event: ClientEvent) -> None:
    ...         print(f"Received: {event}")
    """

    def on_client_event(self, event: ClientEvent) -> None:
        """Handle a client event.

        Parameters
        ----------
        event : ClientEvent
            The event to handle
        """
        ...
