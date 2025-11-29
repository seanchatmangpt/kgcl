"""Transaction Manager - ACID transactions with snapshot rollback.

This adapter implements the TransactionManager port using PyOxigraph's
dump/load capabilities for snapshot-based rollback.

The transaction pattern ensures workflow state is never inconsistent:
1. Snapshot before changes
2. Validate preconditions
3. Apply changes
4. Validate postconditions
5. Commit (success) or Rollback (failure)
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import TYPE_CHECKING

import pyoxigraph as ox

from kgcl.hybrid.ports.transaction_port import (
    Snapshot,
    Transaction,
    TransactionError,
    TransactionResult,
    TransactionState,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class PyOxigraphTransactionManager:
    """Transaction manager using PyOxigraph snapshots.

    Provides ACID-like semantics via dump/load snapshots:
    - Atomicity: All changes commit together or none do
    - Consistency: SHACL validation ensures valid state
    - Isolation: Single-threaded execution
    - Durability: Persistent store option

    Parameters
    ----------
    store : ox.Store
        PyOxigraph store to manage.

    Examples
    --------
    >>> import pyoxigraph as ox
    >>> store = ox.Store()
    >>> manager = PyOxigraphTransactionManager(store)
    >>> with manager.transaction_context() as txn:
    ...     store.update("INSERT DATA { <urn:s> <urn:p> <urn:o> }")
    ...     txn.log_operation("Inserted triple")
    ... # Auto-commits on success
    """

    def __init__(self, store: ox.Store) -> None:
        """Initialize transaction manager.

        Parameters
        ----------
        store : ox.Store
            PyOxigraph store.
        """
        self._store = store
        self._active_transaction: Transaction | None = None
        logger.info("PyOxigraphTransactionManager initialized")

    def begin(self) -> Transaction:
        """Begin a new transaction.

        Creates a snapshot for potential rollback.

        Returns
        -------
        Transaction
            The new active transaction.

        Raises
        ------
        TransactionError
            If a transaction is already active.
        """
        if self._active_transaction is not None:
            raise TransactionError(
                "Cannot begin: transaction already active", transaction_id=self._active_transaction.transaction_id
            )

        snapshot = self.create_snapshot()
        transaction = Transaction(transaction_id=str(uuid.uuid4()), snapshot=snapshot, state=TransactionState.ACTIVE)
        self._active_transaction = transaction

        logger.info(f"Transaction {transaction.transaction_id} started")
        return transaction

    def commit(self, transaction: Transaction) -> TransactionResult:
        """Commit the transaction.

        Discards the snapshot, making changes permanent.

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
            If transaction is not active.
        """
        if transaction.state != TransactionState.ACTIVE:
            raise TransactionError(
                f"Cannot commit: transaction in state {transaction.state}", transaction_id=transaction.transaction_id
            )

        if self._active_transaction != transaction:
            raise TransactionError(
                "Cannot commit: not the active transaction", transaction_id=transaction.transaction_id
            )

        # Calculate duration
        duration_ms = (datetime.now() - transaction.started_at).total_seconds() * 1000

        # Mark as committed
        transaction.state = TransactionState.COMMITTED
        self._active_transaction = None

        logger.info(
            f"Transaction {transaction.transaction_id} committed "
            f"({len(transaction.operations)} operations, {duration_ms:.2f}ms)"
        )

        return TransactionResult(
            success=True,
            state=TransactionState.COMMITTED,
            operations_count=len(transaction.operations),
            duration_ms=duration_ms,
        )

    def rollback(self, transaction: Transaction, reason: str = "") -> TransactionResult:
        """Rollback the transaction.

        Restores state from snapshot.

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
            If rollback fails.
        """
        if transaction.state != TransactionState.ACTIVE:
            raise TransactionError(
                f"Cannot rollback: transaction in state {transaction.state}", transaction_id=transaction.transaction_id
            )

        duration_ms = (datetime.now() - transaction.started_at).total_seconds() * 1000

        try:
            self.restore_snapshot(transaction.snapshot)
            transaction.state = TransactionState.ROLLED_BACK
            self._active_transaction = None

            logger.warning(f"Transaction {transaction.transaction_id} rolled back: {reason or 'no reason given'}")

            return TransactionResult(
                success=True,
                state=TransactionState.ROLLED_BACK,
                operations_count=len(transaction.operations),
                duration_ms=duration_ms,
                error=reason if reason else None,
            )
        except Exception as e:
            logger.error(f"CRITICAL: Rollback failed: {e}")
            raise TransactionError(f"Rollback failed: {e}", transaction_id=transaction.transaction_id, cause=e) from e

    def create_snapshot(self) -> Snapshot:
        """Create a snapshot of current state.

        Returns
        -------
        Snapshot
            Immutable snapshot.
        """
        snapshot_id = str(uuid.uuid4())
        triple_count = len(self._store)

        # Serialize to N-Quads (includes named graphs)
        result = self._store.dump(format=ox.RdfFormat.N_QUADS)
        if result is None:
            data = b""
        else:
            data = result

        snapshot = Snapshot(snapshot_id=snapshot_id, data=data, triple_count=triple_count, created_at=datetime.now())

        logger.debug(f"Snapshot {snapshot_id} created ({triple_count} triples)")
        return snapshot

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
        try:
            self._store.clear()
            self._store.load(snapshot.data, ox.RdfFormat.N_QUADS)

            logger.debug(f"Snapshot {snapshot.snapshot_id} restored")
        except Exception as e:
            raise TransactionError(f"Failed to restore snapshot: {e}") from e

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
        ...     # Do work
        ...     txn.log_operation("Did something")
        ... # Auto-commits or rolls back
        """
        transaction = self.begin()
        try:
            yield transaction
            self.commit(transaction)
        except Exception as e:
            logger.error(f"Transaction failed, rolling back: {e}")
            self.rollback(transaction, reason=str(e))
            raise

    @property
    def has_active_transaction(self) -> bool:
        """Check if there's an active transaction.

        Returns
        -------
        bool
            True if transaction is active.
        """
        return self._active_transaction is not None

    @property
    def active_transaction(self) -> Transaction | None:
        """Get the active transaction if any.

        Returns
        -------
        Transaction | None
            Active transaction or None.
        """
        return self._active_transaction


# Convenience factory
def create_transaction_manager(store: ox.Store) -> PyOxigraphTransactionManager:
    """Create a transaction manager for the given store.

    Parameters
    ----------
    store : ox.Store
        PyOxigraph store.

    Returns
    -------
    PyOxigraphTransactionManager
        Configured manager.
    """
    return PyOxigraphTransactionManager(store)
