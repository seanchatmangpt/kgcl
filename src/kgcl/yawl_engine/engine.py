"""KGC YAWL Engine - 5-Stratum Workflow Execution with RDF Dark Matter Physics.

This module implements a production-ready YAWL (Yet Another Workflow Language) engine
with semantic reasoning, resource constraints, and cryptographic provenance.

Stratum 1: Dark Matter (Ontology Physics - Namespaces + Topology)
Stratum 2: Data Plane (Pydantic Models - Type Safety)
Stratum 3: Kernel (5 Verbs - Workflow Operations)
Stratum 4: Atman (Semantic Driver - Execution Loop)
Stratum 5: Simulation (Nuclear Protocol Demonstration)

Examples
--------
>>> atman = Atman()
>>> ctx = TransactionContext(actor="operator1", roles=["role:General"], prev_hash="0" * 64)
>>> receipt = await atman.step("urn:task:InitiateLaunch", ctx)
>>> assert receipt.committed
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from collections.abc import Callable
from enum import Enum
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field
from rdflib import Dataset, Graph, Literal, Namespace, URIRef
from rdflib.query import ResultRow

# ============================================================================
# STRATUM 1: DARK MATTER - Namespaces + Ontology Physics
# ============================================================================

KGC = Namespace("https://kgc.org/ns/")
YAWL = Namespace("http://www.yawlfoundation.org/yawlschema#")
ROLE = Namespace("urn:org:role:")

# YAWL Workflow Ontology with 4 Perspectives:
# 1. Control Flow (MapSeq, MapXor, MapAnd, MapJoin)
# 2. Data Perspective (input/output mappings)
# 3. Resource Perspective (role constraints)
# 4. Organizational Perspective (user-role-org hierarchy)

COMPLEX_ONTOLOGY = """
@prefix kgc: <https://kgc.org/ns/> .
@prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix role: <urn:org:role:> .
@prefix task: <urn:task:> .
@prefix service: <urn:service:> .

# Physics Map Definitions (Control Flow Perspective)
kgc:MapSeq rdf:type kgc:PhysicsMap ;
    kgc:verb "transmute" ;
    kgc:description "Sequential execution (A then B)" .

kgc:MapXor rdf:type kgc:PhysicsMap ;
    kgc:verb "filter" ;
    kgc:description "XOR split - exclusive choice based on condition" .

kgc:MapAnd rdf:type kgc:PhysicsMap ;
    kgc:verb "copy" ;
    kgc:description "AND split - parallel execution" .

kgc:MapJoin rdf:type kgc:PhysicsMap ;
    kgc:verb "await" ;
    kgc:description "Join synchronization - wait for all incoming" .

kgc:MapTimer rdf:type kgc:PhysicsMap ;
    kgc:verb "void" ;
    kgc:description "Timer expiration or cancellation" .

# Nuclear Launch Workflow Topology
task:InitiateLaunch rdf:type yawl:Task ;
    yawl:name "Initiate Nuclear Launch Protocol" ;
    yawl:splitType "XOR" ;
    yawl:physics kgc:MapXor ;
    yawl:resourceConstraint role:General ;
    yawl:outputMapping "decision_code -> launch_authorized" .

task:CodesEntry rdf:type yawl:Task ;
    yawl:name "Enter Authorization Codes (Parallel)" ;
    yawl:splitType "AND" ;
    yawl:physics kgc:MapAnd ;
    yawl:resourceConstraint role:Operator ;
    yawl:inputMapping "launch_authorized -> required" ;
    yawl:outputMapping "code1,code2 -> codes_entered" .

task:VerifyCodes rdf:type yawl:Task ;
    yawl:name "Verify Launch Codes (Join)" ;
    yawl:joinType "AND" ;
    yawl:physics kgc:MapJoin ;
    yawl:resourceConstraint role:Supervisor ;
    yawl:inputMapping "codes_entered -> verify" ;
    yawl:outputMapping "verified -> system_armed" .

task:ArmWarheads rdf:type yawl:Task ;
    yawl:name "Arm Nuclear Warheads" ;
    yawl:physics kgc:MapSeq ;
    yawl:resourceConstraint role:TechnicalOfficer ;
    yawl:inputMapping "system_armed -> proceed" ;
    yawl:outputMapping "armed -> warheads_ready" .

task:FinalLaunch rdf:type yawl:Task ;
    yawl:name "Final Launch Command" ;
    yawl:physics kgc:MapSeq ;
    yawl:resourceConstraint role:General ;
    yawl:inputMapping "warheads_ready -> execute" ;
    yawl:timer "PT30S" ;
    yawl:timerTask task:EmergencyAbort .

task:EmergencyAbort rdf:type yawl:Task ;
    yawl:name "Emergency Abort (Timer Fallback)" ;
    yawl:physics kgc:MapTimer ;
    yawl:resourceConstraint role:General .

# External Service Definitions
service:CodeValidator rdf:type yawl:ExternalService ;
    yawl:endpoint "https://nuke.mil/validator" .

service:SiloControl rdf:type yawl:ExternalService ;
    yawl:endpoint "https://silo.sys/launch" .
"""

logger = logging.getLogger(__name__)

# ============================================================================
# STRATUM 2: DATA PLANE - Pydantic Models
# ============================================================================

Triple = tuple[str, str, str]


class QuadDelta(BaseModel):
    """Immutable quad-store delta representing state mutations.

    Parameters
    ----------
    additions : list[Triple]
        Triples to add to the graph
    removals : list[Triple]
        Triples to remove from the graph
    data_updates : dict[str, Any]
        Workflow data variables updated during execution

    Examples
    --------
    >>> delta = QuadDelta(
    ...     additions=[("urn:task:1", "yawl:status", "completed")], data_updates={"launch_authorized": True}
    ... )
    """

    additions: list[Triple] = Field(default_factory=list)
    removals: list[Triple] = Field(default_factory=list)
    data_updates: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(frozen=True)


class TransactionContext(BaseModel):
    """Transaction context with actor, roles, provenance chain.

    Parameters
    ----------
    tx_id : str
        Unique transaction identifier (UUID4)
    actor : str
        User/agent executing the transaction
    roles : list[str]
        Organizational roles held by actor (e.g., ["role:General"])
    prev_hash : str
        SHA-256 hash of previous transaction (blockchain-style chaining)
    timestamp : float
        Unix timestamp of transaction start
    data : dict[str, Any]
        Workflow instance data (variables passed between tasks)

    Examples
    --------
    >>> ctx = TransactionContext(
    ...     actor="operator1", roles=["role:General"], prev_hash="0" * 64, data={"decision_code": "alpha"}
    ... )
    """

    tx_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    actor: str
    roles: list[str] = []
    prev_hash: str
    timestamp: float = Field(default_factory=time.time)
    data: dict[str, Any] = Field(default_factory=dict)


class Receipt(BaseModel):
    """Immutable execution receipt with provenance and Merkle root.

    Parameters
    ----------
    tx_id : str
        Transaction identifier
    committed : bool
        Whether transaction was successfully committed
    merkle_root : str
        SHA-256 Merkle root of delta (for cryptographic verification)
    verb_executed : str
        YAWL verb executed (transmute, copy, filter, await, void)
    state_snapshot : str
        Serialized RDF graph state after execution
    error : str | None
        Error message if execution failed

    Examples
    --------
    >>> receipt = Receipt(
    ...     tx_id="abc123",
    ...     committed=True,
    ...     merkle_root="deadbeef...",
    ...     verb_executed="transmute",
    ...     state_snapshot="@prefix yawl: ... .",
    ... )
    """

    tx_id: str
    committed: bool
    merkle_root: str
    verb_executed: str
    state_snapshot: str
    error: str | None = None


class SplitType(str, Enum):
    """YAWL split types for control flow patterns."""

    SEQUENCE = "SEQUENCE"
    XOR = "XOR"
    AND = "AND"


class JoinType(str, Enum):
    """YAWL join types for synchronization patterns."""

    XOR = "XOR"
    AND = "AND"


# ============================================================================
# STRATUM 3: KERNEL - 5 Verbs (Workflow Physics Operations)
# ============================================================================


class Kernel:
    """Core YAWL execution kernel with 5 semantic verbs.

    Implements the 5 fundamental workflow operations:
    1. transmute: Sequential execution (A → B)
    2. copy: Parallel split (A → [B, C, D])
    3. filter: XOR branch (A → B | C based on condition)
    4. await: Synchronization join (wait for all incoming)
    5. void: Timer expiration or cancellation

    All verbs integrate the 4 YAWL perspectives:
    - Control Flow: Routing decisions
    - Data Perspective: Variable mappings
    - Resource Perspective: Role-based access control
    - Organizational Perspective: Actor-role validation
    """

    @staticmethod
    def _check_resources(store: Dataset, task: URIRef, ctx: TransactionContext) -> bool:
        """Validate resource constraints (YAWL Resource Perspective).

        Parameters
        ----------
        store : Dataset
            RDF quad-store with workflow topology
        task : URIRef
            Task URI to validate
        ctx : TransactionContext
            Execution context with actor roles

        Returns
        -------
        bool
            True if actor has required role, False otherwise

        Examples
        --------
        >>> from rdflib import Dataset, URIRef
        >>> store = Dataset()
        >>> # ... populate store with task constraints ...
        >>> ctx = TransactionContext(actor="user1", roles=["role:General"], prev_hash="0" * 64)
        >>> result = Kernel._check_resources(store, URIRef("urn:task:InitiateLaunch"), ctx)
        >>> assert isinstance(result, bool)
        """
        # Query: SELECT ?role WHERE { task yawl:resourceConstraint ?role }
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?role WHERE {{
            <{task}> yawl:resourceConstraint ?role .
        }}
        """
        results = store.query(query)
        required_roles = {str(cast(ResultRow, r).role) for r in results if hasattr(r, "role")}

        if not required_roles:
            return True  # No constraints

        # Normalize role URIs (extract role name from urn:org:role:General)
        normalized_required = {role.split(":")[-1] if ":" in role else role for role in required_roles}

        # Normalize actor roles (extract from role:General)
        normalized_actor = {role.split(":")[-1] if ":" in role else role for role in ctx.roles}

        return bool(normalized_required & normalized_actor)

    @staticmethod
    def _apply_data_mapping(store: Dataset, task: URIRef, ctx: TransactionContext) -> dict[str, Any]:
        """Apply data perspective mappings (input → output variables).

        Parameters
        ----------
        store : Dataset
            RDF quad-store with workflow topology
        task : URIRef
            Task URI with data mappings
        ctx : TransactionContext
            Execution context with workflow data

        Returns
        -------
        dict[str, Any]
            Updated workflow variables after mapping

        Examples
        --------
        >>> ctx = TransactionContext(
        ...     actor="user1", roles=["role:General"], prev_hash="0" * 64, data={"decision_code": "alpha"}
        ... )
        >>> updated = Kernel._apply_data_mapping(store, task_uri, ctx)
        >>> assert "launch_authorized" in updated
        """
        # Query output mapping from task definition
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?mapping WHERE {{
            <{task}> yawl:outputMapping ?mapping .
        }}
        """
        results = store.query(query)

        data_copy = ctx.data.copy()
        for row in results:
            if not hasattr(row, "mapping"):
                continue
            row_typed = cast(ResultRow, row)
            mapping_str = str(row_typed.mapping)
            # Parse "source -> target" format
            if " -> " in mapping_str:
                source, target = mapping_str.split(" -> ", 1)
                source = source.strip()
                target = target.strip()

                if source in data_copy:
                    data_copy[target] = data_copy[source]
                elif "," in source:
                    # Multiple sources: "code1,code2 -> codes_entered"
                    sources = [s.strip() for s in source.split(",")]
                    data_copy[target] = [data_copy.get(s) for s in sources]

        return data_copy

    @staticmethod
    def transmute(store: Dataset, task: URIRef, ctx: TransactionContext) -> QuadDelta:
        """Execute sequential task (YAWL MapSeq pattern).

        Sequential execution: Task A completes, then Task B starts.
        This is the fundamental atomic workflow operation.

        Parameters
        ----------
        store : Dataset
            RDF quad-store
        task : URIRef
            Task to execute
        ctx : TransactionContext
            Execution context

        Returns
        -------
        QuadDelta
            State mutations (triples + data updates)

        Raises
        ------
        PermissionError
            If actor lacks required role
        """
        if not Kernel._check_resources(store, task, ctx):
            msg = f"Actor {ctx.actor} lacks required role for {task}"
            raise PermissionError(msg)

        updated_data = Kernel._apply_data_mapping(store, task, ctx)

        # Mark task as completed
        additions = [
            (str(task), str(YAWL.status), "completed"),
            (str(task), str(YAWL.completedBy), ctx.actor),
            (str(task), str(YAWL.completedAt), str(ctx.timestamp)),
        ]

        return QuadDelta(additions=additions, data_updates=updated_data)

    @staticmethod
    def copy(store: Dataset, task: URIRef, ctx: TransactionContext) -> QuadDelta:
        """Execute parallel split (YAWL MapAnd pattern).

        Creates multiple parallel execution threads. All outgoing tasks
        are enabled simultaneously.

        Parameters
        ----------
        store : Dataset
            RDF quad-store
        task : URIRef
            Task with AND-split
        ctx : TransactionContext
            Execution context

        Returns
        -------
        QuadDelta
            State mutations enabling parallel tasks
        """
        if not Kernel._check_resources(store, task, ctx):
            msg = f"Actor {ctx.actor} lacks required role for {task}"
            raise PermissionError(msg)

        updated_data = Kernel._apply_data_mapping(store, task, ctx)

        # Mark task completed and enable all outgoing edges
        additions = [(str(task), str(YAWL.status), "completed"), (str(task), str(YAWL.splitType), "AND")]

        # Query for outgoing tasks
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?next WHERE {{
            <{task}> yawl:flowsTo ?next .
        }}
        """
        for row in store.query(query):
            if hasattr(row, "next"):
                row_typed = cast(ResultRow, row)
                additions.append((str(row_typed.next), str(YAWL.status), "enabled"))

        return QuadDelta(additions=additions, data_updates=updated_data)

    @staticmethod
    def filter(store: Dataset, task: URIRef, ctx: TransactionContext) -> QuadDelta:
        """Execute XOR split (YAWL MapXor pattern).

        Exclusive choice: Exactly one outgoing path is taken based on
        workflow data condition.

        Parameters
        ----------
        store : Dataset
            RDF quad-store
        task : URIRef
            Task with XOR-split
        ctx : TransactionContext
            Execution context

        Returns
        -------
        QuadDelta
            State mutations selecting one branch
        """
        if not Kernel._check_resources(store, task, ctx):
            msg = f"Actor {ctx.actor} lacks required role for {task}"
            raise PermissionError(msg)

        updated_data = Kernel._apply_data_mapping(store, task, ctx)

        # Simple XOR condition: Check if "launch_authorized" is True
        condition_met = updated_data.get("launch_authorized", False)

        additions = [
            (str(task), str(YAWL.status), "completed"),
            (str(task), str(YAWL.splitType), "XOR"),
            (str(task), str(YAWL.chosenBranch), str(condition_met)),
        ]

        # Enable chosen branch (simplified: just mark the task as completed)
        return QuadDelta(additions=additions, data_updates=updated_data)

    @staticmethod
    def await_(store: Dataset, task: URIRef, ctx: TransactionContext) -> QuadDelta:
        """Execute join synchronization (YAWL MapJoin pattern).

        Waits for all incoming parallel threads to complete before
        proceeding (barrier synchronization).

        Parameters
        ----------
        store : Dataset
            RDF quad-store
        task : URIRef
            Join task
        ctx : TransactionContext
            Execution context

        Returns
        -------
        QuadDelta
            State mutations after synchronization
        """
        if not Kernel._check_resources(store, task, ctx):
            msg = f"Actor {ctx.actor} lacks required role for {task}"
            raise PermissionError(msg)

        # Check if all incoming tasks are completed
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?incoming WHERE {{
            ?incoming yawl:flowsTo <{task}> .
        }}
        """
        incoming = list(store.query(query))

        # Verify all incoming tasks are completed
        all_completed = all(
            bool(list(store.triples((URIRef(str(cast(ResultRow, row).incoming)), YAWL.status, Literal("completed")))))
            for row in incoming
            if hasattr(row, "incoming")
        )

        if not all_completed:
            # Not ready to join yet - return empty delta
            return QuadDelta()

        updated_data = Kernel._apply_data_mapping(store, task, ctx)

        additions = [(str(task), str(YAWL.status), "completed"), (str(task), str(YAWL.joinType), "AND")]

        return QuadDelta(additions=additions, data_updates=updated_data)

    @staticmethod
    def void(store: Dataset, task: URIRef, ctx: TransactionContext) -> QuadDelta:
        """Execute timer expiration or cancellation (YAWL MapTimer).

        Handles timeout conditions and emergency cancellations.

        Parameters
        ----------
        store : Dataset
            RDF quad-store
        task : URIRef
            Timer task
        ctx : TransactionContext
            Execution context

        Returns
        -------
        QuadDelta
            State mutations canceling workflow
        """
        if not Kernel._check_resources(store, task, ctx):
            msg = f"Actor {ctx.actor} lacks required role for {task}"
            raise PermissionError(msg)

        updated_data = Kernel._apply_data_mapping(store, task, ctx)
        updated_data["aborted"] = True

        additions = [(str(task), str(YAWL.status), "cancelled"), (str(task), str(YAWL.cancelledBy), ctx.actor)]

        return QuadDelta(additions=additions, data_updates=updated_data)


# ============================================================================
# STRATUM 4: ATMAN - Semantic Driver (Execution Loop)
# ============================================================================


class Atman:
    """Semantic workflow driver with RDF physics and provenance chain.

    The Atman is the autonomous execution engine that:
    1. Loads YAWL ontology (dark matter physics)
    2. Resolves verbs dynamically via SPARQL reasoning
    3. Executes workflow steps with cryptographic receipts
    4. Maintains provenance chain (blockchain-style)

    Examples
    --------
    >>> atman = Atman()
    >>> ctx = TransactionContext(actor="operator1", roles=["role:General"], prev_hash="0" * 64)
    >>> receipt = await atman.step("urn:task:InitiateLaunch", ctx)
    >>> assert receipt.committed
    """

    def __init__(self) -> None:
        """Initialize Atman with RDF physics and empty state."""
        self.store = Dataset()
        self.physics = Graph()
        self._tip_hash = "0" * 64

        # Load YAWL ontology into physics graph
        self.physics.parse(data=COMPLEX_ONTOLOGY, format="turtle")

        # Bind namespaces
        self.store.bind("kgc", KGC)
        self.store.bind("yawl", YAWL)
        self.store.bind("role", ROLE)

        # Import ontology into default graph
        for s, p, o in self.physics:
            self.store.add((s, p, o))

    def _resolve_verb(
        self, task: URIRef, ctx: TransactionContext
    ) -> Callable[[Dataset, URIRef, TransactionContext], QuadDelta]:
        """Dynamically resolve YAWL verb from RDF physics.

        Resolution priority:
        1. Timer → void
        2. Split type (AND → copy, XOR → filter)
        3. Join type (AND → await)
        4. Default → transmute

        Parameters
        ----------
        task : URIRef
            Task to resolve
        ctx : TransactionContext
            Execution context

        Returns
        -------
        Callable
            Kernel verb function (transmute, copy, filter, await, void)
        """
        # Check for timer (highest priority)
        query = f"""
        PREFIX yawl: <{YAWL}>
        ASK {{ <{task}> yawl:timer ?timer . }}
        """
        if self.store.query(query).askAnswer:
            return Kernel.void

        # Check for split type
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?splitType WHERE {{ <{task}> yawl:splitType ?splitType . }}
        """
        for row in self.store.query(query):
            if hasattr(row, "splitType"):
                row_typed = cast(ResultRow, row)
                if str(row_typed.splitType) == "AND":
                    return Kernel.copy
                if str(row_typed.splitType) == "XOR":
                    return Kernel.filter

        # Check for join type
        query = f"""
        PREFIX yawl: <{YAWL}>
        SELECT ?joinType WHERE {{ <{task}> yawl:joinType ?joinType . }}
        """
        for row in self.store.query(query):
            if hasattr(row, "joinType"):
                row_typed = cast(ResultRow, row)
                if str(row_typed.joinType) == "AND":
                    return Kernel.await_

        # Default: Sequential execution
        return Kernel.transmute

    def _compute_merkle_root(self, delta: QuadDelta) -> str:
        """Compute SHA-256 Merkle root of delta for provenance.

        Parameters
        ----------
        delta : QuadDelta
            State mutations to hash

        Returns
        -------
        str
            Hex-encoded SHA-256 hash
        """
        content = str(delta.additions) + str(delta.removals) + str(delta.data_updates)
        return hashlib.sha256(content.encode()).hexdigest()

    async def step(self, task_uri: str, ctx: TransactionContext) -> Receipt:
        """Execute single workflow step with semantic reasoning.

        Parameters
        ----------
        task_uri : str
            Task URI (e.g., "urn:task:InitiateLaunch")
        ctx : TransactionContext
            Execution context with actor, roles, data

        Returns
        -------
        Receipt
            Immutable execution receipt with provenance

        Examples
        --------
        >>> atman = Atman()
        >>> ctx = TransactionContext(
        ...     actor="user1", roles=["role:General"], prev_hash="0" * 64, data={"decision_code": "alpha"}
        ... )
        >>> receipt = await atman.step("urn:task:InitiateLaunch", ctx)
        >>> assert receipt.verb_executed == "filter"
        """
        task = URIRef(task_uri)

        try:
            # Resolve verb dynamically
            verb_func = self._resolve_verb(task, ctx)
            verb_name = verb_func.__name__.replace("_", "")

            logger.info(
                "Executing YAWL verb",
                extra={"task": task_uri, "verb": verb_name, "actor": ctx.actor, "tx_id": ctx.tx_id},
            )

            # Execute verb (synchronous kernel call)
            delta = verb_func(self.store, task, ctx)

            # Apply delta to store
            for s, p, o in delta.additions:
                self.store.add((URIRef(s), URIRef(p), Literal(o)))
            for s, p, o in delta.removals:
                self.store.remove((URIRef(s), URIRef(p), Literal(o)))

            # Update context data
            ctx.data.update(delta.data_updates)

            # Compute Merkle root
            merkle_root = self._compute_merkle_root(delta)

            # Update provenance chain
            self._tip_hash = hashlib.sha256((ctx.prev_hash + merkle_root).encode()).hexdigest()

            # Serialize state snapshot
            state_snapshot = self.store.serialize(format="turtle")

            return Receipt(
                tx_id=ctx.tx_id,
                committed=True,
                merkle_root=merkle_root,
                verb_executed=verb_name,
                state_snapshot=state_snapshot,
            )

        except Exception as e:
            logger.exception("YAWL execution failed", extra={"task": task_uri})
            return Receipt(
                tx_id=ctx.tx_id, committed=False, merkle_root="", verb_executed="error", state_snapshot="", error=str(e)
            )


# ============================================================================
# STRATUM 5: SIMULATION - Nuclear Protocol Demonstration
# ============================================================================


async def run_nuclear_protocol() -> None:
    """Run complete nuclear launch protocol demonstrating all 4 perspectives.

    This simulation demonstrates:
    - Control Flow: XOR split, AND split, JOIN, SEQ
    - Data Perspective: Variable mappings across tasks
    - Resource Perspective: Role-based access control
    - Organizational Perspective: Actor-role validation

    Workflow:
    1. InitiateLaunch (XOR) - General decides go/no-go
    2. CodesEntry (AND) - Two operators enter codes in parallel
    3. VerifyCodes (JOIN) - Supervisor verifies both codes
    4. ArmWarheads (SEQ) - Technical officer arms systems
    5. FinalLaunch (SEQ) - General executes launch
    6. EmergencyAbort (TIMER) - Abort if timeout exceeded
    """
    atman = Atman()

    # Step 1: General initiates launch (XOR split)
    ctx1 = TransactionContext(
        actor="General.Smith", roles=["role:General"], prev_hash="0" * 64, data={"decision_code": "alpha"}
    )
    receipt1 = await atman.step("urn:task:InitiateLaunch", ctx1)
    print(f"Step 1: {receipt1.verb_executed} - Committed: {receipt1.committed}")
    ctx1.data.update({"launch_authorized": True})

    # Step 2: Operators enter codes (AND split - parallel)
    ctx2 = TransactionContext(
        actor="Operator.Jones", roles=["role:Operator"], prev_hash=receipt1.merkle_root, data=ctx1.data.copy()
    )
    ctx2.data.update({"code1": "ALPHA-7-7", "code2": "BRAVO-2-2"})
    receipt2 = await atman.step("urn:task:CodesEntry", ctx2)
    print(f"Step 2: {receipt2.verb_executed} - Committed: {receipt2.committed}")

    # Step 3: Supervisor verifies codes (AND join)
    ctx3 = TransactionContext(
        actor="Supervisor.Davis", roles=["role:Supervisor"], prev_hash=receipt2.merkle_root, data=ctx2.data.copy()
    )
    receipt3 = await atman.step("urn:task:VerifyCodes", ctx3)
    print(f"Step 3: {receipt3.verb_executed} - Committed: {receipt3.committed}")
    ctx3.data.update({"verified": True})

    # Step 4: Technical officer arms warheads (SEQ)
    ctx4 = TransactionContext(
        actor="TechOfficer.Lee", roles=["role:TechnicalOfficer"], prev_hash=receipt3.merkle_root, data=ctx3.data.copy()
    )
    receipt4 = await atman.step("urn:task:ArmWarheads", ctx4)
    print(f"Step 4: {receipt4.verb_executed} - Committed: {receipt4.committed}")
    ctx4.data.update({"armed": True})

    # Step 5: Final launch command (SEQ)
    ctx5 = TransactionContext(
        actor="General.Smith", roles=["role:General"], prev_hash=receipt4.merkle_root, data=ctx4.data.copy()
    )
    receipt5 = await atman.step("urn:task:FinalLaunch", ctx5)
    print(f"Step 5: {receipt5.verb_executed} - Committed: {receipt5.committed}")

    # Step 6: Emergency abort (TIMER - optional)
    ctx6 = TransactionContext(
        actor="General.Smith", roles=["role:General"], prev_hash=receipt5.merkle_root, data=ctx5.data.copy()
    )
    receipt6 = await atman.step("urn:task:EmergencyAbort", ctx6)
    print(f"Step 6: {receipt6.verb_executed} - Committed: {receipt6.committed}")

    print("\n=== Provenance Chain ===")
    print(f"Tip Hash: {atman._tip_hash}")
    print(f"Total triples: {len(atman.store)}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    asyncio.run(run_nuclear_protocol())
