"""PostgreSQL Lockchain Writer for cryptographic workflow provenance.

Provides persistent storage for tick receipts with cryptographic chaining
using SHA-256 hashes, enabling tamper-evident audit trails.

Examples
--------
>>> writer = PostgresLockchainWriter(connection)
>>> receipt_id = writer.write_tick_receipt(
...     workflow_id="WF-001", tick_number=1, graph_hash="abc123...", hook_results=[{"hook_id": "h1", "result": True}]
... )  # doctest: +SKIP
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TickReceipt:
    """Immutable tick receipt with cryptographic chain link.

    Attributes
    ----------
    id : int | None
        Database-assigned ID (None before persistence).
    workflow_id : str
        Identifier for the workflow instance.
    tick_number : int
        Sequential tick number within workflow.
    graph_hash : str
        SHA-256 hash of RDF graph state after tick.
    previous_hash : str
        Hash of previous tick receipt (chain link).
    receipt_hash : str
        Hash of this receipt (for chain verification).
    hook_results : list[dict[str, Any]]
        Results from hook executions during tick.
    created_at : datetime | None
        Timestamp of receipt creation.
    metadata : dict[str, Any] | None
        Additional receipt metadata.
    """

    id: int | None
    workflow_id: str
    tick_number: int
    graph_hash: str
    previous_hash: str
    receipt_hash: str
    hook_results: list[dict[str, Any]]
    created_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class PostgresLockchainWriter:
    """PostgreSQL-based lockchain writer for tick receipts.

    Implements cryptographic chaining for workflow tick receipts,
    enabling tamper-evident audit trails with verifiable history.

    Parameters
    ----------
    connection : Any
        Active psycopg connection object.

    Examples
    --------
    >>> import psycopg
    >>> conn = psycopg.connect("postgresql://...")  # doctest: +SKIP
    >>> writer = PostgresLockchainWriter(conn)  # doctest: +SKIP
    >>> receipt_id = writer.write_tick_receipt(
    ...     workflow_id="WF-001", tick_number=1, graph_hash="abc123...", hook_results=[]
    ... )  # doctest: +SKIP
    """

    GENESIS_HASH = "0" * 64  # SHA-256 genesis block hash

    def __init__(self, connection: Any) -> None:
        """Initialize PostgresLockchainWriter.

        Parameters
        ----------
        connection : Any
            Active psycopg connection object.
        """
        self._conn = connection

    def write_tick_receipt(
        self,
        workflow_id: str,
        tick_number: int,
        graph_hash: str,
        hook_results: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Write a tick receipt with cryptographic chain link.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.
        tick_number : int
            Sequential tick number within workflow.
        graph_hash : str
            SHA-256 hash of RDF graph state after tick.
        hook_results : list[dict[str, Any]] | None, optional
            Results from hook executions.
        metadata : dict[str, Any] | None, optional
            Additional metadata.

        Returns
        -------
        int
            Database ID of the created receipt.

        Examples
        --------
        >>> receipt_id = writer.write_tick_receipt(  # doctest: +SKIP
        ...     workflow_id="ORD-001",
        ...     tick_number=1,
        ...     graph_hash="abc123...",
        ...     hook_results=[{"hook_id": "validate", "result": True}],
        ... )
        42
        """
        hook_results = hook_results or []

        # Get previous hash for chain link
        previous_hash = self._get_previous_hash(workflow_id)

        # Compute receipt hash
        receipt_hash = self._compute_receipt_hash(
            workflow_id=workflow_id,
            tick_number=tick_number,
            graph_hash=graph_hash,
            previous_hash=previous_hash,
            hook_results=hook_results,
        )

        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tick_receipts
                    (workflow_id, tick_number, graph_hash, previous_hash, receipt_hash, hook_results, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    workflow_id,
                    tick_number,
                    graph_hash,
                    previous_hash,
                    receipt_hash,
                    json.dumps(hook_results),
                    json.dumps(metadata) if metadata else None,
                ),
            )
            result = cursor.fetchone()
            self._conn.commit()

            logger.debug(f"Wrote tick receipt: workflow={workflow_id}, tick={tick_number}, hash={receipt_hash[:16]}...")
            return result[0] if result else 0

    def _get_previous_hash(self, workflow_id: str) -> str:
        """Get hash of previous tick receipt in chain.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.

        Returns
        -------
        str
            Previous receipt hash, or genesis hash if first tick.
        """
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT receipt_hash FROM tick_receipts
                WHERE workflow_id = %s
                ORDER BY tick_number DESC
                LIMIT 1
                """,
                (workflow_id,),
            )
            result = cursor.fetchone()

        return result[0] if result else self.GENESIS_HASH

    def _compute_receipt_hash(
        self,
        workflow_id: str,
        tick_number: int,
        graph_hash: str,
        previous_hash: str,
        hook_results: list[dict[str, Any]],
    ) -> str:
        """Compute SHA-256 hash for tick receipt.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.
        tick_number : int
            Sequential tick number.
        graph_hash : str
            Hash of RDF graph state.
        previous_hash : str
            Hash of previous receipt.
        hook_results : list[dict[str, Any]]
            Hook execution results.

        Returns
        -------
        str
            SHA-256 hex digest of receipt data.
        """
        # Create deterministic string representation
        data = json.dumps(
            {
                "workflow_id": workflow_id,
                "tick_number": tick_number,
                "graph_hash": graph_hash,
                "previous_hash": previous_hash,
                "hook_results": hook_results,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def get_receipt(self, workflow_id: str, tick_number: int) -> TickReceipt | None:
        """Get a specific tick receipt.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.
        tick_number : int
            Sequential tick number.

        Returns
        -------
        TickReceipt | None
            Receipt if found, None otherwise.
        """
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, workflow_id, tick_number, graph_hash, previous_hash,
                       receipt_hash, hook_results, created_at, metadata
                FROM tick_receipts
                WHERE workflow_id = %s AND tick_number = %s
                """,
                (workflow_id, tick_number),
            )
            row = cursor.fetchone()

        if not row:
            return None

        return TickReceipt(
            id=row[0],
            workflow_id=row[1],
            tick_number=row[2],
            graph_hash=row[3],
            previous_hash=row[4],
            receipt_hash=row[5],
            hook_results=json.loads(row[6]) if row[6] else [],
            created_at=row[7],
            metadata=json.loads(row[8]) if row[8] else None,
        )

    def get_chain(self, workflow_id: str) -> list[TickReceipt]:
        """Get complete receipt chain for a workflow.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.

        Returns
        -------
        list[TickReceipt]
            List of receipts ordered by tick number.
        """
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, workflow_id, tick_number, graph_hash, previous_hash,
                       receipt_hash, hook_results, created_at, metadata
                FROM tick_receipts
                WHERE workflow_id = %s
                ORDER BY tick_number
                """,
                (workflow_id,),
            )
            rows = cursor.fetchall()

        return [
            TickReceipt(
                id=row[0],
                workflow_id=row[1],
                tick_number=row[2],
                graph_hash=row[3],
                previous_hash=row[4],
                receipt_hash=row[5],
                hook_results=json.loads(row[6]) if row[6] else [],
                created_at=row[7],
                metadata=json.loads(row[8]) if row[8] else None,
            )
            for row in rows
        ]

    def verify_chain(self, workflow_id: str) -> tuple[bool, str]:
        """Verify integrity of receipt chain.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.

        Returns
        -------
        tuple[bool, str]
            (is_valid, message) tuple indicating verification result.

        Examples
        --------
        >>> is_valid, message = writer.verify_chain("WF-001")  # doctest: +SKIP
        >>> if not is_valid:  # doctest: +SKIP
        ...     print(f"Chain integrity failure: {message}")
        """
        chain = self.get_chain(workflow_id)

        if not chain:
            return True, "Empty chain"

        # Verify genesis block
        if chain[0].previous_hash != self.GENESIS_HASH:
            return False, f"Invalid genesis: expected {self.GENESIS_HASH}, got {chain[0].previous_hash}"

        # Verify each link in chain
        for i, receipt in enumerate(chain):
            # Recompute hash
            expected_hash = self._compute_receipt_hash(
                workflow_id=receipt.workflow_id,
                tick_number=receipt.tick_number,
                graph_hash=receipt.graph_hash,
                previous_hash=receipt.previous_hash,
                hook_results=receipt.hook_results,
            )

            if receipt.receipt_hash != expected_hash:
                return (
                    False,
                    f"Hash mismatch at tick {receipt.tick_number}: expected {expected_hash}, got {receipt.receipt_hash}",
                )

            # Verify chain link (except first)
            if i > 0:
                if receipt.previous_hash != chain[i - 1].receipt_hash:
                    return False, f"Chain break at tick {receipt.tick_number}: previous_hash doesn't match"

        return True, f"Chain verified: {len(chain)} receipts"

    def get_latest_receipt(self, workflow_id: str) -> TickReceipt | None:
        """Get the most recent tick receipt for a workflow.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.

        Returns
        -------
        TickReceipt | None
            Latest receipt if found, None otherwise.
        """
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, workflow_id, tick_number, graph_hash, previous_hash,
                       receipt_hash, hook_results, created_at, metadata
                FROM tick_receipts
                WHERE workflow_id = %s
                ORDER BY tick_number DESC
                LIMIT 1
                """,
                (workflow_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        return TickReceipt(
            id=row[0],
            workflow_id=row[1],
            tick_number=row[2],
            graph_hash=row[3],
            previous_hash=row[4],
            receipt_hash=row[5],
            hook_results=json.loads(row[6]) if row[6] else [],
            created_at=row[7],
            metadata=json.loads(row[8]) if row[8] else None,
        )

    def count_ticks(self, workflow_id: str) -> int:
        """Count total ticks for a workflow.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.

        Returns
        -------
        int
            Number of tick receipts.
        """
        with self._conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM tick_receipts WHERE workflow_id = %s", (workflow_id,))
            result = cursor.fetchone()
            return result[0] if result else 0

    def clear_workflow(self, workflow_id: str) -> int:
        """Delete all receipts for a workflow.

        Parameters
        ----------
        workflow_id : str
            Identifier for the workflow instance.

        Returns
        -------
        int
            Number of receipts deleted.
        """
        with self._conn.cursor() as cursor:
            cursor.execute("DELETE FROM tick_receipts WHERE workflow_id = %s", (workflow_id,))
            deleted = cursor.rowcount
            self._conn.commit()
            return deleted
