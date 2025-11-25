"""KGCL Hooks - Monitoring, Resilience, and Advanced Distributed Processing."""

from kgcl.hooks.adaptive_monitor import AdaptiveMonitor, MetricThreshold

# Advanced UNRDF modules
from kgcl.hooks.dark_matter import DarkMatterOptimizer, OptimizationRule, OptimizedPlan, QueryStep
from kgcl.hooks.edge_cases import EdgeCaseHandler
from kgcl.hooks.federation import (
    ConsistencyLevel,
    FederationCoordinator,
    GossipProtocol,
    Node,
    NodeStatus,
    ReplicationConfig,
    ReplicationResult,
)

# Hook orchestration and execution
from kgcl.hooks.loader import HookDefinition, HookEffect, HookLoader
from kgcl.hooks.monitoring import AndonBoard, AndonSignal, SignalSeverity
from kgcl.hooks.orchestrator import (
    EffectHandler,
    ExecutionContext,
    ExecutionResult,
    HookOrchestrator,
)
from kgcl.hooks.registry import HookRegistry, HookStatus, RegisteredHook
from kgcl.hooks.resilience import CircuitBreaker, CircuitBreakerConfig, CircuitState
from kgcl.hooks.scheduler import HookScheduler, ScheduledExecution
from kgcl.hooks.streaming import (
    Change,
    ChangeFeed,
    ChangeType,
    StreamProcessor,
    WindowedStreamProcessor,
)

__all__ = [
    "AndonBoard",
    "AndonSignal",
    "SignalSeverity",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "AdaptiveMonitor",
    "MetricThreshold",
    "EdgeCaseHandler",
    # Hook orchestration
    "HookLoader",
    "HookDefinition",
    "HookEffect",
    "HookOrchestrator",
    "ExecutionContext",
    "ExecutionResult",
    "EffectHandler",
    "HookRegistry",
    "HookStatus",
    "RegisteredHook",
    "HookScheduler",
    "ScheduledExecution",
    # Advanced UNRDF modules
    "DarkMatterOptimizer",
    "OptimizedPlan",
    "OptimizationRule",
    "QueryStep",
    "Change",
    "ChangeFeed",
    "ChangeType",
    "StreamProcessor",
    "WindowedStreamProcessor",
    "ConsistencyLevel",
    "FederationCoordinator",
    "GossipProtocol",
    "Node",
    "NodeStatus",
    "ReplicationConfig",
    "ReplicationResult",
]
