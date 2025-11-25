"""
Federation Coordinator for Distributed Knowledge Graphs.

Implements node coordination, data replication, and consensus protocols
for federated knowledge graph deployments.
Ported from UNRDF federation/federation-coordinator.mjs.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class NodeStatus(Enum):
    """Status of a federation node."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ConsistencyLevel(Enum):
    """Consistency level for operations."""

    ONE = "one"  # Single node confirmation
    QUORUM = "quorum"  # Majority confirmation
    ALL = "all"  # All nodes confirmation


@dataclass
class Node:
    """Node in federated knowledge graph.

    Parameters
    ----------
    node_id : str
        Unique node identifier
    address : str
        Network address (host:port)
    is_healthy : bool
        Health status
    last_heartbeat : float
        Last heartbeat timestamp
    metadata : Dict[str, Any]
        Node metadata
    """

    node_id: str
    address: str
    is_healthy: bool = True
    last_heartbeat: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    status: NodeStatus = NodeStatus.HEALTHY

    def update_heartbeat(self, timestamp: float) -> None:
        """Update last heartbeat timestamp."""
        self.last_heartbeat = timestamp
        if not self.is_healthy:
            self.is_healthy = True
            self.status = NodeStatus.HEALTHY


@dataclass
class ReplicationConfig:
    """Configuration for data replication.

    Parameters
    ----------
    replication_factor : int
        Number of replicas to maintain
    consistency_level : ConsistencyLevel
        Required consistency level
    sync_interval_ms : int
        Synchronization interval
    """

    replication_factor: int = 3
    consistency_level: ConsistencyLevel = ConsistencyLevel.QUORUM
    sync_interval_ms: int = 1000
    timeout_ms: int = 5000
    max_retries: int = 3


@dataclass
class ReplicationResult:
    """Result of replication operation."""

    success: bool
    nodes_confirmed: list[str]
    nodes_failed: list[str]
    consistency_achieved: bool
    timestamp: float


class FederationCoordinator:
    """Coordinate knowledge graph across multiple nodes.

    Implements:
    - Node registration and health monitoring
    - Data replication with configurable consistency
    - Quorum-based consensus writes
    - Failure detection and recovery
    """

    def __init__(self, local_node_id: str) -> None:
        """Initialize federation coordinator.

        Parameters
        ----------
        local_node_id : str
            ID of the local node
        """
        self.local_node_id = local_node_id
        self.nodes: dict[str, Node] = {}
        self.replication_config = ReplicationConfig()
        self._pending_writes: dict[str, set[str]] = {}  # write_id -> confirmed nodes

    def register_node(self, node: Node) -> None:
        """Register new node in federation.

        Parameters
        ----------
        node : Node
            Node to register
        """
        self.nodes[node.node_id] = node
        logger.info(f"Registered node {node.node_id} at {node.address}")

    def unregister_node(self, node_id: str) -> bool:
        """Unregister node from federation.

        Parameters
        ----------
        node_id : str
            Node ID to unregister

        Returns
        -------
        bool
            True if node was removed
        """
        if node_id in self.nodes:
            del self.nodes[node_id]
            logger.info(f"Unregistered node {node_id}")
            return True
        return False

    def get_healthy_nodes(self) -> list[Node]:
        """Get all healthy nodes.

        Returns
        -------
        List[Node]
            List of healthy nodes
        """
        return [n for n in self.nodes.values() if n.is_healthy]

    def mark_node_unhealthy(self, node_id: str) -> None:
        """Mark node as unhealthy.

        Parameters
        ----------
        node_id : str
            Node ID to mark unhealthy
        """
        if node_id in self.nodes:
            self.nodes[node_id].is_healthy = False
            self.nodes[node_id].status = NodeStatus.FAILED
            logger.warning(f"Marked node {node_id} as unhealthy")

    def check_heartbeat(self, node_id: str, max_age_ms: float = 5000) -> bool:
        """Check if node heartbeat is recent.

        Parameters
        ----------
        node_id : str
            Node ID to check
        max_age_ms : float
            Maximum age of heartbeat in milliseconds

        Returns
        -------
        bool
            True if heartbeat is recent
        """
        if node_id not in self.nodes:
            return False

        node = self.nodes[node_id]
        now = datetime.utcnow().timestamp()
        age_ms = (now - node.last_heartbeat) * 1000

        if age_ms > max_age_ms:
            self.mark_node_unhealthy(node_id)
            return False

        return True

    async def replicate_change(
        self, triple: tuple, write_id: str | None = None
    ) -> ReplicationResult:
        """Replicate change to other nodes.

        Parameters
        ----------
        triple : tuple
            Triple to replicate (subject, predicate, object)
        write_id : Optional[str]
            Unique write identifier

        Returns
        -------
        ReplicationResult
            Result of replication operation
        """
        if write_id is None:
            write_id = f"write_{datetime.utcnow().timestamp()}"

        healthy_nodes = self.get_healthy_nodes()
        target_count = min(self.replication_config.replication_factor, len(healthy_nodes))

        # Select nodes for replication
        target_nodes = healthy_nodes[:target_count]

        # Track confirmations
        self._pending_writes[write_id] = set()

        # Simulate replication to nodes (in real implementation, would use network calls)
        confirmed: list[str] = []
        failed: list[str] = []

        for node in target_nodes:
            try:
                # Simulate async replication
                success = await self._replicate_to_node(node, triple)
                if success:
                    confirmed.append(node.node_id)
                    self._pending_writes[write_id].add(node.node_id)
                else:
                    failed.append(node.node_id)
            except Exception as e:
                logger.error(f"Replication to {node.node_id} failed: {e}")
                failed.append(node.node_id)

        # Check consistency
        consistency_achieved = self._check_consistency(len(confirmed), len(target_nodes))

        result = ReplicationResult(
            success=consistency_achieved,
            nodes_confirmed=confirmed,
            nodes_failed=failed,
            consistency_achieved=consistency_achieved,
            timestamp=datetime.utcnow().timestamp(),
        )

        # Clean up pending write
        if write_id in self._pending_writes:
            del self._pending_writes[write_id]

        return result

    async def _replicate_to_node(self, node: Node, triple: tuple) -> bool:
        """Replicate triple to specific node.

        Parameters
        ----------
        node : Node
            Target node
        triple : tuple
            Triple to replicate

        Returns
        -------
        bool
            True if replication succeeded
        """
        # Simulate network delay
        await asyncio.sleep(0.001)

        # Simulate 95% success rate
        import random

        return random.random() < 0.95

    def _check_consistency(self, confirmed_count: int, target_count: int) -> bool:
        """Check if consistency level is achieved.

        Parameters
        ----------
        confirmed_count : int
            Number of nodes that confirmed
        target_count : int
            Total number of target nodes

        Returns
        -------
        bool
            True if consistency level achieved
        """
        level = self.replication_config.consistency_level

        if level == ConsistencyLevel.ONE:
            return confirmed_count >= 1
        if level == ConsistencyLevel.QUORUM:
            return confirmed_count >= (target_count // 2 + 1)
        if level == ConsistencyLevel.ALL:
            return confirmed_count == target_count

        return False

    async def consensus_write(self, triple: tuple) -> ReplicationResult:
        """Write with quorum consensus.

        Parameters
        ----------
        triple : tuple
            Triple to write

        Returns
        -------
        ReplicationResult
            Result of consensus write
        """
        # Set consistency level to quorum
        original_level = self.replication_config.consistency_level
        self.replication_config.consistency_level = ConsistencyLevel.QUORUM

        try:
            result = await self.replicate_change(triple)
            return result
        finally:
            self.replication_config.consistency_level = original_level

    def get_cluster_stats(self) -> dict[str, Any]:
        """Get cluster statistics.

        Returns
        -------
        Dict[str, Any]
            Cluster statistics
        """
        healthy_nodes = self.get_healthy_nodes()
        return {
            "total_nodes": len(self.nodes),
            "healthy_nodes": len(healthy_nodes),
            "failed_nodes": len(self.nodes) - len(healthy_nodes),
            "replication_factor": self.replication_config.replication_factor,
            "consistency_level": self.replication_config.consistency_level.value,
            "pending_writes": len(self._pending_writes),
        }

    def select_read_node(self) -> Node | None:
        """Select node for read operation.

        Uses simple load balancing (round-robin over healthy nodes).

        Returns
        -------
        Optional[Node]
            Selected node or None if no healthy nodes
        """
        healthy = self.get_healthy_nodes()
        if not healthy:
            return None

        # Simple round-robin (in real implementation, would track position)
        return healthy[0]

    def get_quorum_size(self) -> int:
        """Calculate quorum size.

        Returns
        -------
        int
            Number of nodes needed for quorum
        """
        total = len(self.nodes)
        return total // 2 + 1

    def has_quorum(self) -> bool:
        """Check if cluster has quorum.

        Returns
        -------
        bool
            True if quorum is available
        """
        healthy_count = len(self.get_healthy_nodes())
        return healthy_count >= self.get_quorum_size()


class GossipProtocol:
    """Gossip-based information dissemination.

    Implements epidemic protocol for spreading updates across federation.
    """

    def __init__(self, coordinator: FederationCoordinator) -> None:
        """Initialize gossip protocol.

        Parameters
        ----------
        coordinator : FederationCoordinator
            Federation coordinator
        """
        self.coordinator = coordinator
        self.gossip_fanout = 3  # Number of nodes to gossip to
        self.gossip_interval_ms = 100

    async def gossip_update(self, update: dict[str, Any]) -> list[str]:
        """Gossip update to random nodes.

        Parameters
        ----------
        update : Dict[str, Any]
            Update to disseminate

        Returns
        -------
        List[str]
            List of node IDs that received update
        """
        import random

        healthy_nodes = self.coordinator.get_healthy_nodes()

        # Select random subset of nodes
        fanout = min(self.gossip_fanout, len(healthy_nodes))
        targets = random.sample(healthy_nodes, fanout)

        notified: list[str] = []

        for node in targets:
            try:
                # Simulate gossip (in real implementation, would send update)
                await asyncio.sleep(0.001)
                notified.append(node.node_id)
            except Exception as e:
                logger.error(f"Gossip to {node.node_id} failed: {e}")

        return notified
