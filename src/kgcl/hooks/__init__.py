"""KGCL Hooks - Monitoring, Resilience, and Advanced Distributed Processing."""

from kgcl.hooks.adaptive_monitor import AdaptiveMonitor, MetricThreshold

# Advanced UNRDF modules
from kgcl.hooks.dark_matter import (
    DarkMatterOptimizer,
    OptimizationRule,
    OptimizedPlan,
    QueryStep,
)
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
    "AdaptiveMonitor",
    "AndonBoard",
    "AndonSignal",
    "Change",
    "ChangeFeed",
    "ChangeType",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "ConsistencyLevel",
    # Advanced UNRDF modules
    "DarkMatterOptimizer",
    "EdgeCaseHandler",
    "EffectHandler",
    "ExecutionContext",
    "ExecutionResult",
    "FederationCoordinator",
    "GossipProtocol",
    "HookDefinition",
    "HookEffect",
    # Hook orchestration
    "HookLoader",
    "HookOrchestrator",
    "HookRegistry",
    "HookScheduler",
    "HookStatus",
    "MetricThreshold",
    "Node",
    "NodeStatus",
    "OptimizationRule",
    "OptimizedPlan",
    "QueryStep",
    "RegisteredHook",
    "ReplicationConfig",
    "ReplicationResult",
    "ScheduledExecution",
    "SignalSeverity",
    "StreamProcessor",
    "WindowedStreamProcessor",
]
