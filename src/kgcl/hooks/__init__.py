"""KGCL Hooks - Monitoring, Resilience, and Advanced Distributed Processing."""

from kgcl.hooks.monitoring import AndonBoard, AndonSignal, SignalSeverity
from kgcl.hooks.resilience import CircuitBreaker, CircuitBreakerConfig, CircuitState
from kgcl.hooks.adaptive_monitor import AdaptiveMonitor, MetricThreshold
from kgcl.hooks.edge_cases import EdgeCaseHandler

# Advanced UNRDF modules
from kgcl.hooks.dark_matter import (
  DarkMatterOptimizer,
  OptimizedPlan,
  OptimizationRule,
  QueryStep,
)
from kgcl.hooks.streaming import (
  Change,
  ChangeFeed,
  ChangeType,
  StreamProcessor,
  WindowedStreamProcessor,
)
from kgcl.hooks.federation import (
  ConsistencyLevel,
  FederationCoordinator,
  GossipProtocol,
  Node,
  NodeStatus,
  ReplicationConfig,
  ReplicationResult,
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
