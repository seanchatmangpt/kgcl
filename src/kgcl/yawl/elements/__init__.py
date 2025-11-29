"""YAWL workflow elements (conditions, tasks, flows, nets, specifications).

This module provides the core building blocks for YAWL workflow definitions,
mirroring the Java au.edu.qut.yawl.elements package.
"""

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

__all__ = [
    # Base
    "YExternalNetElement",
    # Identifier
    "YIdentifier",
    # Condition
    "YCondition",
    "ConditionType",
    "YInputCondition",
    "YOutputCondition",
    "YImplicitCondition",
    # Task
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
    # Multi-instance
    "YMultiInstanceAttributes",
    "MICreationMode",
    "MICompletionMode",
    # Flow
    "YFlow",
    # Net
    "YNet",
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
]
