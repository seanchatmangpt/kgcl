"""YAWL Client interfaces for engine, resource, worklet, and document services.

This module provides Python equivalents of the Java YAWL UI service clients,
enabling workflow operations through a consistent client interface pattern.

Clients:
    AbstractClient: Base client class with connection and event management
    InterfaceClient: HTTP client base (Interface_Client.java parity)
    EngineClient: Workflow engine operations (specs, cases, work items)
    ResourceClient: Resource management (participants, roles, work queues)
    WorkletClient: Worklet and exception handling operations
    DocStoreClient: Document storage operations

Models (Java Parity):
    YSpecVersion: Major.minor version object (YSpecVersion.java)
    YSpecificationID: identifier + version + uri (YSpecificationID.java)
    RunningCase: Spec ID + Case ID tuple (RunningCase.java)

Exceptions:
    YAWLConnectionError: Connection failure (Java: IOException)
    YAWLResponseError: Engine returned failure response
"""

from kgcl.yawl.clients.base_client import AbstractClient
from kgcl.yawl.clients.engine_client import EngineClient
from kgcl.yawl.clients.events import ClientAction, ClientEvent, ClientEventListener
from kgcl.yawl.clients.http_engine_client import HTTPEngineClient
from kgcl.yawl.clients.interface_a_client import InterfaceAClient
from kgcl.yawl.clients.interface_b_client import InterfaceBClient
from kgcl.yawl.clients.interface_client import InterfaceClient, YAWLConnectionError, YAWLResponseError
from kgcl.yawl.clients.models import (
    CalendarEntry,
    ChainedCase,
    NonHumanResource,
    PiledTask,
    RunningCase,
    TaskInformation,
    UploadResult,
    WorkQueue,
    YSpecificationID,
    YSpecVersion,
)

__all__ = [
    # Base
    "AbstractClient",
    "InterfaceClient",
    "InterfaceAClient",
    "InterfaceBClient",
    # Exceptions
    "YAWLConnectionError",
    "YAWLResponseError",
    # Clients
    "EngineClient",
    "HTTPEngineClient",
    # Events
    "ClientAction",
    "ClientEvent",
    "ClientEventListener",
    # Models
    "CalendarEntry",
    "ChainedCase",
    "NonHumanResource",
    "PiledTask",
    "RunningCase",
    "TaskInformation",
    "UploadResult",
    "WorkQueue",
    "YSpecificationID",
    "YSpecVersion",
]
