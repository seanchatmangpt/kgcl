"""Transaction Manager Port - Interface for ACID transactions.

This port defines the contract for transaction management with
snapshot-based rollback support, implementing Design by Contract
for workflow execution.

The transaction pattern:
1. Begin transaction (create snapshot)
2. Validate preconditions (SHACL)
3. Apply inference (EYE)
4. Execute mutations (SPARQL UPDATE)
5. Validate postconditions (SHACL)
6. Commit (discard snapshot) or Rollback (restore snapshot)
"""

from __future__ import annotations

from abc import abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator


class TransactionState(Enum):
    """State of a transaction."""

    PENDING = auto()  # Not yet started
    ACTIVE = auto()  # In progress
    COMMITTED = auto()  # Successfully completed
    ROLLED_BACK = auto()  # Reverted due to error


@dataclass(frozen=True)
class Snapshot:
    """Immutable snapshot of store state for rollback.

    Parameters
    ----------
    snapshot_id : str
        Unique identifier for this snapshot.
    data : bytes
        Serialized graph state (N-Quads format).
    triple_count : int
        Number of triples at snapshot time.
    created_at : datetime
        When the snapshot was created.
    """

    snapshot_id: str
    data: bytes
    triple_count: int
    created_at: datetime


@dataclass
class Transaction:
    """Represents an active transaction.

    Parameters
    ----------
    transaction_id : str
        Unique identifier for this transaction.
    snapshot : Snapshot
        Snapshot for rollback.
    state : TransactionState
        Current transaction state.
    started_at : datetime
        When transaction began.
    operations : list[str]
        Log of operations performed.
    """

    transaction_id: str
    snapshot: Snapshot
    state: TransactionState = TransactionState.ACTIVE
    started_at: datetime = field(default_factory=datetime.now)
    operations: list[str] = field(default_factory=list)

    def log_operation(self, operation: str) -> None:
        """Log an operation within this transaction.

        Parameters
        ----------
        operation : str
            Description of the operation.
        """
        self.operations.append(f"{datetime.now().isoformat()}: {operation}")


@dataclass(frozen=True)
class TransactionResult:
    """Result of a transaction.

    Parameters
    ----------
    success : bool
        Whether transaction completed successfully.
    state : TransactionState
        Final transaction state.
    operations_count : int
        Number of operations performed.
    duration_ms : float
        Total transaction duration.
    error : str | None
        Error message if transaction failed.
    """

    success: bool
    state: TransactionState
    operations_count: int = 0
    duration_ms: float = 0.0
    error: str | None = None


class TransactionManager(Protocol):
    """Protocol for ACID transaction management.

    Provides snapshot-based rollback for atomic workflow operations.
    Implements the Design by Contract pattern:
    - Preconditions validated before execution
    - Postconditions validated after execution
    - Rollback on any failure

    This ensures workflow state is never left in an inconsistent state,
    critical for the hybrid architecture where EYE inference and
    SPARQL UPDATE mutations must be atomic.
    """

    @abstractmethod
    def begin(self) -> Transaction:
        """Begin a new transaction.

        Creates a snapshot of current state for potential rollback.

        Returns
        -------
        Transaction
            The new active transaction.

        Raises
        ------
        TransactionError
            If a transaction is already active.
        """
        ...

    @abstractmethod
    def commit(self, transaction: Transaction) -> TransactionResult:
        """Commit the transaction.

        Discards the snapshot and makes changes permanent.

        Parameters
        ----------
        transaction : Transaction
            The transaction to commit.

        Returns
        -------
        TransactionResult
            Result of the commit.

        Raises
        ------
        TransactionError
            If transaction is not active or already committed.
        """
        ...

    @abstractmethod
    def rollback(self, transaction: Transaction, reason: str = "") -> TransactionResult:
        """Rollback the transaction.

        Restores state from snapshot, discarding all changes.

        Parameters
        ----------
        transaction : Transaction
            The transaction to rollback.
        reason : str, optional
            Reason for rollback.

        Returns
        -------
        TransactionResult
            Result of the rollback.

        Raises
        ------
        TransactionError
            If rollback fails (critical error).
        """
        ...

    @abstractmethod
    def create_snapshot(self) -> Snapshot:
        """Create a snapshot of current state.

        Returns
        -------
        Snapshot
            Immutable snapshot of current state.
        """
        ...

    @abstractmethod
    def restore_snapshot(self, snapshot: Snapshot) -> None:
        """Restore state from a snapshot.

        Parameters
        ----------
        snapshot : Snapshot
            Snapshot to restore.

        Raises
        ------
        TransactionError
            If restoration fails.
        """
        ...

    @abstractmethod
    @contextmanager
    def transaction_context(self) -> Iterator[Transaction]:
        """Context manager for automatic transaction handling.

        Commits on successful exit, rolls back on exception.

        Yields
        ------
        Transaction
            The active transaction.

        Examples
        --------
        >>> with manager.transaction_context() as txn:
        ...     # Operations here
        ...     txn.log_operation("Applied mutation")
        ... # Auto-commits on success, rolls back on exception
        """
        ...


class TransactionError(Exception):
    """Exception for transaction-related errors.

    Parameters
    ----------
    message : str
        Error message.
    transaction_id : str | None
        ID of the failed transaction.
    cause : Exception | None
        Original exception that caused this error.
    """

    def __init__(self, message: str, transaction_id: str | None = None, cause: Exception | None = None) -> None:
        """Initialize transaction error.

        Parameters
        ----------
        message : str
            Error message.
        transaction_id : str | None
            ID of the failed transaction.
        cause : Exception | None
            Original exception.
        """
        super().__init__(message)
        self.transaction_id = transaction_id
        self.cause = cause
