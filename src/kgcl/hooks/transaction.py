"""
Transaction Manager for ACID hook execution.

This module provides transaction management with support for ACID properties,
ensuring atomic, consistent, isolated, and durable hook execution.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class TransactionState(Enum):
    """Transaction lifecycle states."""

    PENDING = "pending"
    EXECUTING = "executing"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class TransactionError(Exception):
    """Raised when transaction operation fails.

    Attributes
    ----------
    tx_id : str
        Transaction identifier
    reason : str
        Failure reason
    """

    def __init__(self, tx_id: str, reason: str) -> None:
        """Initialize TransactionError.

        Parameters
        ----------
        tx_id : str
            Transaction identifier
        reason : str
            Failure reason
        """
        self.tx_id = tx_id
        self.reason = reason
        super().__init__(f"Transaction '{tx_id}' failed: {reason}")


class IsolationViolation(TransactionError):
    """Raised when transaction isolation is violated.

    Attributes
    ----------
    tx_id : str
        Transaction identifier
    conflicting_tx_id : str
        ID of conflicting transaction
    """

    def __init__(self, tx_id: str, conflicting_tx_id: str) -> None:
        """Initialize IsolationViolation.

        Parameters
        ----------
        tx_id : str
            Transaction identifier
        conflicting_tx_id : str
            ID of conflicting transaction
        """
        self.conflicting_tx_id = conflicting_tx_id
        super().__init__(tx_id, f"Isolation violated by transaction '{conflicting_tx_id}'")


@dataclass
class Transaction:
    """
    Manages ACID properties for hook execution.

    Parameters
    ----------
    tx_id : str
        Unique transaction identifier
    state : TransactionState
        Current transaction state
    added_triples : List[tuple]
        Triples added in this transaction
    removed_triples : List[tuple]
        Triples removed in this transaction
    started_at : datetime
        Transaction start time
    completed_at : Optional[datetime]
        Transaction completion time
    metadata : Dict[str, Any]
        Additional transaction metadata
    isolation_level : str
        Transaction isolation level (READ_COMMITTED, SERIALIZABLE)
    """

    tx_id: str
    state: TransactionState = TransactionState.PENDING
    added_triples: list[tuple[str, str, str]] = field(default_factory=list)
    removed_triples: list[tuple[str, str, str]] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    isolation_level: str = "READ_COMMITTED"

    def begin(self) -> None:
        """
        Start transaction.

        Raises
        ------
        TransactionError
            If transaction is not in PENDING state
        """
        if self.state != TransactionState.PENDING:
            raise TransactionError(self.tx_id, f"Cannot begin transaction in state {self.state.value}")
        self.state = TransactionState.EXECUTING

    def commit(self) -> None:
        """
        Commit transaction.

        Raises
        ------
        TransactionError
            If transaction is not in EXECUTING state
        """
        if self.state != TransactionState.EXECUTING:
            raise TransactionError(self.tx_id, f"Cannot commit transaction in state {self.state.value}")
        self.state = TransactionState.COMMITTED
        self.completed_at = datetime.now(UTC)

    def rollback(self) -> None:
        """
        Rollback transaction.

        Clears all changes and marks transaction as rolled back.
        """
        self.added_triples.clear()
        self.removed_triples.clear()
        self.state = TransactionState.ROLLED_BACK
        self.completed_at = datetime.now(UTC)

    def fail(self, error: str) -> None:
        """
        Mark transaction as failed.

        Parameters
        ----------
        error : str
            Error message describing failure
        """
        self.state = TransactionState.FAILED
        self.completed_at = datetime.now(UTC)
        self.metadata["error"] = error

    def add_triple(self, subject: str, predicate: str, obj: str) -> None:
        """
        Record triple addition.

        Parameters
        ----------
        subject : str
            Triple subject
        predicate : str
            Triple predicate
        obj : str
            Triple object
        """
        self.added_triples.append((subject, predicate, obj))

    def remove_triple(self, subject: str, predicate: str, obj: str) -> None:
        """
        Record triple removal.

        Parameters
        ----------
        subject : str
            Triple subject
        predicate : str
            Triple predicate
        obj : str
            Triple object
        """
        self.removed_triples.append((subject, predicate, obj))

    def get_changes(self) -> dict[str, list[tuple[str, str, str]]]:
        """
        Get all changes in transaction.

        Returns
        -------
        Dict[str, List[Tuple[str, str, str]]]
            Dictionary with 'added' and 'removed' keys
        """
        return {"added": self.added_triples.copy(), "removed": self.removed_triples.copy()}


class TransactionManager:
    """
    Manage ACID transaction lifecycle.

    Provides transaction creation, execution, commit, rollback, and isolation.
    """

    def __init__(self, max_concurrent: int = 100) -> None:
        """
        Initialize transaction manager.

        Parameters
        ----------
        max_concurrent : int
            Maximum number of concurrent transactions
        """
        self.transactions: dict[str, Transaction] = {}
        self.max_concurrent = max_concurrent
        self.committed_transactions: list[Transaction] = []
        self.rolled_back_transactions: list[Transaction] = []
        self._locks: dict[str, str] = {}  # resource_id -> tx_id

    def begin_transaction(self, tx_id: str | None = None, isolation_level: str = "READ_COMMITTED") -> Transaction:
        """
        Start new transaction.

        Parameters
        ----------
        tx_id : Optional[str]
            Transaction ID (auto-generated if not provided)
        isolation_level : str
            Isolation level (READ_COMMITTED or SERIALIZABLE)

        Returns
        -------
        Transaction
            New transaction instance

        Raises
        ------
        TransactionError
            If too many concurrent transactions or tx_id already exists
        """
        if len(self.transactions) >= self.max_concurrent:
            raise TransactionError("SYSTEM", f"Too many concurrent transactions (max: {self.max_concurrent})")

        if tx_id is None:
            tx_id = str(uuid.uuid4())

        if tx_id in self.transactions:
            raise TransactionError(tx_id, "Transaction already exists")

        tx = Transaction(tx_id=tx_id, isolation_level=isolation_level)
        tx.begin()
        self.transactions[tx_id] = tx
        return tx

    def commit_transaction(self, tx_id: str) -> None:
        """
        Commit transaction.

        Parameters
        ----------
        tx_id : str
            Transaction ID

        Raises
        ------
        TransactionError
            If transaction not found or cannot be committed
        """
        if tx_id not in self.transactions:
            raise TransactionError(tx_id, "Transaction not found")

        tx = self.transactions[tx_id]

        # Check for isolation violations
        if tx.isolation_level == "SERIALIZABLE":
            self._check_serializability(tx)

        tx.commit()

        # Move to committed list
        self.committed_transactions.append(tx)
        del self.transactions[tx_id]

        # Release locks
        self._release_locks(tx_id)

    def rollback_transaction(self, tx_id: str) -> None:
        """
        Rollback transaction.

        Parameters
        ----------
        tx_id : str
            Transaction ID

        Raises
        ------
        TransactionError
            If transaction not found
        """
        if tx_id not in self.transactions:
            raise TransactionError(tx_id, "Transaction not found")

        tx = self.transactions[tx_id]
        tx.rollback()

        # Move to rolled back list
        self.rolled_back_transactions.append(tx)
        del self.transactions[tx_id]

        # Release locks
        self._release_locks(tx_id)

    def get_transaction(self, tx_id: str) -> Transaction | None:
        """
        Get transaction by ID.

        Parameters
        ----------
        tx_id : str
            Transaction ID

        Returns
        -------
        Optional[Transaction]
            Transaction if found, None otherwise
        """
        return self.transactions.get(tx_id)

    def get_active_transactions(self) -> list[Transaction]:
        """
        Get all active transactions.

        Returns
        -------
        List[Transaction]
            List of active transactions
        """
        return list(self.transactions.values())

    def get_stats(self) -> dict[str, Any]:
        """
        Get transaction statistics.

        Returns
        -------
        Dict[str, Any]
            Statistics including active, committed, rolled back counts
        """
        return {
            "active": len(self.transactions),
            "committed": len(self.committed_transactions),
            "rolled_back": len(self.rolled_back_transactions),
            "max_concurrent": self.max_concurrent,
        }

    def acquire_lock(self, tx_id: str, resource_id: str) -> bool:
        """
        Acquire lock on resource for transaction.

        Parameters
        ----------
        tx_id : str
            Transaction ID
        resource_id : str
            Resource to lock

        Returns
        -------
        bool
            True if lock acquired, False if already locked

        Raises
        ------
        TransactionError
            If transaction not found
        """
        if tx_id not in self.transactions:
            raise TransactionError(tx_id, "Transaction not found")

        if resource_id in self._locks:
            # Already locked by another transaction
            if self._locks[resource_id] != tx_id:
                return False
            # Already locked by this transaction
            return True

        self._locks[resource_id] = tx_id
        return True

    def release_lock(self, tx_id: str, resource_id: str) -> None:
        """
        Release lock on resource.

        Parameters
        ----------
        tx_id : str
            Transaction ID
        resource_id : str
            Resource to unlock
        """
        if resource_id in self._locks and self._locks[resource_id] == tx_id:
            del self._locks[resource_id]

    def _release_locks(self, tx_id: str) -> None:
        """Release all locks held by transaction."""
        to_release = [rid for rid, tid in self._locks.items() if tid == tx_id]
        for resource_id in to_release:
            del self._locks[resource_id]

    def _check_serializability(self, tx: Transaction) -> None:
        """
        Check if transaction can be serialized.

        Raises
        ------
        IsolationViolation
            If transaction conflicts with others
        """
        # Simplified serializability check
        # In production, would use more sophisticated conflict detection
        for other_tx in self.transactions.values():
            if other_tx.tx_id == tx.tx_id:
                continue

            # Check for conflicting changes
            for triple in tx.added_triples:
                if triple in other_tx.removed_triples:
                    raise IsolationViolation(f"Transaction {tx.tx_id} conflicts with {other_tx.tx_id}")

            for triple in tx.removed_triples:
                if triple in other_tx.added_triples:
                    raise IsolationViolation(f"Transaction {tx.tx_id} conflicts with {other_tx.tx_id}")
