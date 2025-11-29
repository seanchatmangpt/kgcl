"""YAWL Reference Python Implementation.

A faithful port of the YAWL v5.2 workflow engine, mirroring the Java
implementation as closely as possible.

This module provides Petri net-based workflow execution with:
- Token-based execution (YIdentifier, YMarking)
- Split/join semantics (AND, XOR, OR)
- Multi-instance task patterns (WCP 12-15)
- Cancellation regions (reset net semantics)
- Work item lifecycle management
- Resource allocation (roles, participants, capabilities)
- Timer and deadline support
- Exception handling
- Case management
- Full YEngine orchestration

Examples
--------
>>> from kgcl.yawl import YEngine, YSpecification, YNet, YCondition, YTask, YFlow
>>> from kgcl.yawl.elements import SplitType, JoinType, ConditionType
>>>
>>> # Build a simple specification
>>> spec = YSpecification(id="order-process")
>>> net = YNet(id="OrderNet")
>>> start = YCondition(id="start", condition_type=ConditionType.INPUT)
>>> end = YCondition(id="end", condition_type=ConditionType.OUTPUT)
>>> task = YTask(id="ProcessOrder")
>>>
>>> net.add_condition(start)
>>> net.add_condition(end)
>>> net.add_task(task)
>>> net.add_flow(YFlow(id="f1", source_id="start", target_id="ProcessOrder"))
>>> net.add_flow(YFlow(id="f2", source_id="ProcessOrder", target_id="end"))
>>> spec.set_root_net(net)
>>>
>>> # Execute with engine
>>> engine = YEngine()
>>> engine.start()
>>> engine.load_specification(spec)
>>> engine.activate_specification(spec.id)
>>> case = engine.create_case(spec.id)
>>> engine.start_case(case.id)
"""

# Core elements
# Extended elements
from kgcl.yawl.elements.y_atomic_task import (
    ResourcingType,
    TaskType,
    YAtomicTask,
    YCompositeTask,
    YDataBinding,
    YMultipleInstanceTask,
    YResourcingSpec,
)
from kgcl.yawl.elements.y_condition import ConditionType, YCondition
from kgcl.yawl.elements.y_decomposition import (
    DecompositionType,
    YDecomposition,
    YParameter,
    YVariable,
    YWebServiceGateway,
)
from kgcl.yawl.elements.y_external_net_element import YExternalNetElement
from kgcl.yawl.elements.y_flow import YFlow
from kgcl.yawl.elements.y_identifier import YIdentifier
from kgcl.yawl.elements.y_input_output_condition import YImplicitCondition, YInputCondition, YOutputCondition
from kgcl.yawl.elements.y_multi_instance import MICompletionMode, MICreationMode, YMultiInstanceAttributes
from kgcl.yawl.elements.y_net import YNet
from kgcl.yawl.elements.y_specification import SpecificationStatus, YMetaData, YSpecification, YSpecificationVersion
from kgcl.yawl.elements.y_task import JoinType, SplitType, TaskStatus, YTask
from kgcl.yawl.engine.y_case import CaseData, CaseFactory, CaseLog, CaseStatus, YCase
from kgcl.yawl.engine.y_engine import EngineEvent, EngineStatus, YEngine
from kgcl.yawl.engine.y_exception import (
    CompensationHandler,
    ExceptionAction,
    ExceptionRule,
    ExceptionType,
    RetryContext,
    YCompensationService,
    YExceptionService,
    YWorkflowException,
)

# Engine
from kgcl.yawl.engine.y_net_runner import FireResult, YNetRunner
from kgcl.yawl.engine.y_timer import TimerAction, TimerTrigger, YDeadline, YTimer, YTimerService, parse_duration
from kgcl.yawl.engine.y_work_item import WorkItemEvent, WorkItemLog, WorkItemStatus, WorkItemTimer, YWorkItem

# Persistence
from kgcl.yawl.persistence.y_repository import (
    YCaseRepository,
    YInMemoryRepository,
    YSpecificationRepository,
    YWorkItemRepository,
)
from kgcl.yawl.persistence.y_serializer import YCaseSerializer, YSpecificationSerializer

# Resources
from kgcl.yawl.resources.y_resource import (
    ResourceStatus,
    YCapability,
    YOrgGroup,
    YParticipant,
    YPosition,
    YResourceManager,
    YRole,
)

# State
from kgcl.yawl.state.y_marking import YMarking

__all__ = [
    # Core Elements
    "YIdentifier",
    "YCondition",
    "ConditionType",
    "YInputCondition",
    "YOutputCondition",
    "YImplicitCondition",
    "YTask",
    "SplitType",
    "JoinType",
    "TaskStatus",
    "TaskType",
    "YAtomicTask",
    "YCompositeTask",
    "YMultipleInstanceTask",
    "YResourcingSpec",
    "ResourcingType",
    "YDataBinding",
    "YFlow",
    "YNet",
    "YExternalNetElement",
    # Multi-instance
    "YMultiInstanceAttributes",
    "MICreationMode",
    "MICompletionMode",
    # Decomposition
    "YDecomposition",
    "DecompositionType",
    "YParameter",
    "YVariable",
    "YWebServiceGateway",
    # Specification
    "YSpecification",
    "YSpecificationVersion",
    "YMetaData",
    "SpecificationStatus",
    # State
    "YMarking",
    # Engine
    "YNetRunner",
    "FireResult",
    "YEngine",
    "EngineStatus",
    "EngineEvent",
    # Work Item
    "YWorkItem",
    "WorkItemStatus",
    "WorkItemEvent",
    "WorkItemTimer",
    "WorkItemLog",
    # Case
    "YCase",
    "CaseStatus",
    "CaseData",
    "CaseLog",
    "CaseFactory",
    # Timer
    "YTimer",
    "YDeadline",
    "YTimerService",
    "TimerTrigger",
    "TimerAction",
    "parse_duration",
    # Exception
    "YWorkflowException",
    "YExceptionService",
    "YCompensationService",
    "ExceptionType",
    "ExceptionAction",
    "ExceptionRule",
    "RetryContext",
    "CompensationHandler",
    # Resources
    "YRole",
    "YParticipant",
    "YPosition",
    "YCapability",
    "YOrgGroup",
    "YResourceManager",
    "ResourceStatus",
    # Persistence
    "YSpecificationRepository",
    "YCaseRepository",
    "YWorkItemRepository",
    "YInMemoryRepository",
    "YSpecificationSerializer",
    "YCaseSerializer",
]
