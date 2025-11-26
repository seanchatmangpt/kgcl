"""Lockchain Anchor integration for KGC Hybrid Engine tick receipts.

Provides immutable, git-backed audit trail for hybrid engine execution.
Each tick receipt is cryptographically hashed and stored in a verifiable chain.
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import yaml

from kgcl.hybrid.tick_controller import TickHook, TickResult


class RDFStore(Protocol):
    """Protocol for RDF stores that can be hashed.

    Any store implementing dump() method can be used with lockchain.
    """

    def dump(self) -> str:
        """Dump entire store contents.

        Returns
        -------
        str
            Store contents as string (e.g., Turtle, N-Quads)
        """
        ...


@dataclass(frozen=True)
class TickReceipt:
    """Immutable record of a single tick execution.

    Attributes
    ----------
    tick_number : int
        Sequential tick identifier
    state_hash_before : str
        SHA-256 hash of graph state before tick execution
    state_hash_after : str
        SHA-256 hash of graph state after tick execution
    rules_fired : tuple[str, ...]
        Tuple of rule URIs that fired during tick (immutable)
    triples_added : int
        Number of triples added to graph
    triples_removed : int
        Number of triples removed from graph
    timestamp : datetime
        UTC timestamp of tick execution
    converged : bool
        Whether fixed point was reached (no rules fired)
    """

    tick_number: int
    state_hash_before: str
    state_hash_after: str
    rules_fired: tuple[str, ...]
    triples_added: int
    triples_removed: int
    timestamp: datetime
    converged: bool

    def to_yaml(self) -> str:
        """Serialize receipt to YAML format.

        Returns
        -------
        str
            YAML representation of receipt
        """
        data = {
            "tick": self.tick_number,
            "timestamp": self.timestamp.isoformat(),
            "state": {"before": self.state_hash_before, "after": self.state_hash_after},
            "mutations": {
                "rules_fired": list(self.rules_fired),
                "triples_added": self.triples_added,
                "triples_removed": self.triples_removed,
            },
            "converged": self.converged,
        }
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> TickReceipt:
        """Deserialize receipt from YAML format.

        Parameters
        ----------
        yaml_str : str
            YAML representation of receipt

        Returns
        -------
        TickReceipt
            Reconstructed receipt instance

        Raises
        ------
        ValueError
            If YAML is malformed or missing required fields
        """
        try:
            data = yaml.safe_load(yaml_str)
            return cls(
                tick_number=data["tick"],
                state_hash_before=data["state"]["before"],
                state_hash_after=data["state"]["after"],
                rules_fired=tuple(data["mutations"]["rules_fired"]),
                triples_added=data["mutations"]["triples_added"],
                triples_removed=data["mutations"]["triples_removed"],
                timestamp=datetime.fromisoformat(data["timestamp"]),
                converged=data["converged"],
            )
        except (KeyError, TypeError, ValueError, yaml.YAMLError) as e:
            raise ValueError(f"Invalid receipt YAML: {e}") from e


class LockchainWriter:
    """Git-backed immutable receipt chain writer.

    Writes tick receipts to a git repository for tamper-evident audit trails.
    Each receipt is stored in `.kgc/lockchain/` and committed with hash verification.

    Parameters
    ----------
    repo_path : Path
        Path to git repository root
    branch : str, optional
        Git branch for lockchain commits (default: "lockchain")

    Attributes
    ----------
    _repo_path : Path
        Repository root directory
    _branch : str
        Git branch for commits
    _lockchain_dir : Path
        Directory for receipt files (.kgc/lockchain/)
    """

    def __init__(self, repo_path: Path, branch: str = "lockchain") -> None:
        """Initialize lockchain writer.

        Parameters
        ----------
        repo_path : Path
            Path to git repository root
        branch : str, optional
            Git branch for lockchain commits (default: "lockchain")

        Raises
        ------
        ValueError
            If repo_path is not a valid git repository
        """
        self._repo_path = Path(repo_path).resolve()
        self._branch = branch
        self._lockchain_dir = self._repo_path / ".kgc" / "lockchain"

        # Verify git repository
        if not (self._repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {self._repo_path}")

        # Ensure lockchain directory exists
        self._lockchain_dir.mkdir(parents=True, exist_ok=True)

    def compute_state_hash(self, store: RDFStore) -> str:
        """Compute SHA-256 hash of canonical graph state.

        Uses N-Quads serialization for deterministic hashing.

        Parameters
        ----------
        store : RDFStore
            RDF store to hash

        Returns
        -------
        str
            SHA-256 hash in format "sha256:hexdigest"

        Raises
        ------
        RuntimeError
            If store dump or hashing fails
        """
        try:
            # Dump store to canonical N-Quads format
            nquads = store.dump()

            # Sort lines for deterministic hash
            sorted_nquads = "\n".join(sorted(nquads.strip().split("\n")))

            # Compute SHA-256
            hash_obj = hashlib.sha256(sorted_nquads.encode("utf-8"))
            return f"sha256:{hash_obj.hexdigest()}"
        except Exception as e:
            raise RuntimeError(f"Failed to compute state hash: {e}") from e

    def write_receipt(self, receipt: TickReceipt) -> str:
        """Write receipt to git repository.

        Creates receipt file, commits to git, and returns commit SHA.

        Parameters
        ----------
        receipt : TickReceipt
            Receipt to write

        Returns
        -------
        str
            Git commit SHA

        Raises
        ------
        RuntimeError
            If git operations fail
        """
        try:
            # Write receipt to file
            receipt_file = self._lockchain_dir / f"tick_{receipt.tick_number:06d}.yaml"
            receipt_file.write_text(receipt.to_yaml(), encoding="utf-8")

            # Git add
            self._git_run(["add", str(receipt_file)])

            # Compute receipt hash for commit message
            receipt_hash = hashlib.sha256(receipt.to_yaml().encode("utf-8")).hexdigest()[:16]

            # Git commit with hash verification
            commit_msg = (
                f"lockchain: tick {receipt.tick_number}\n\n"
                f"state_before: {receipt.state_hash_before}\n"
                f"state_after: {receipt.state_hash_after}\n"
                f"receipt_hash: {receipt_hash}\n"
                f"converged: {receipt.converged}"
            )

            self._git_run(["commit", "-m", commit_msg], check_output=False)

            # Get commit SHA
            commit_sha = self._git_run(["rev-parse", "HEAD"]).strip()

            return commit_sha
        except Exception as e:
            raise RuntimeError(f"Failed to write receipt: {e}") from e

    def get_receipt_chain(self, limit: int = 100) -> list[TickReceipt]:
        """Read receipt history from lockchain.

        Parameters
        ----------
        limit : int, optional
            Maximum number of receipts to read (default: 100)

        Returns
        -------
        list[TickReceipt]
            List of receipts in chronological order (oldest first)

        Raises
        ------
        RuntimeError
            If reading receipts fails
        """
        try:
            receipt_files = sorted(self._lockchain_dir.glob("tick_*.yaml"))

            # Apply limit
            if limit > 0:
                receipt_files = receipt_files[-limit:]

            receipts: list[TickReceipt] = []
            for receipt_file in receipt_files:
                yaml_content = receipt_file.read_text(encoding="utf-8")
                receipts.append(TickReceipt.from_yaml(yaml_content))

            return receipts
        except Exception as e:
            raise RuntimeError(f"Failed to read receipt chain: {e}") from e

    def verify_chain(self) -> bool:
        """Verify hash chain integrity.

        Ensures each receipt's state_hash_before matches the previous
        receipt's state_hash_after.

        Returns
        -------
        bool
            True if chain is valid, False otherwise

        Raises
        ------
        RuntimeError
            If verification process fails (I/O errors, etc.)
        """
        try:
            receipts = self.get_receipt_chain(limit=-1)  # Get all receipts

            if len(receipts) < 2:
                return True  # Empty or single-receipt chain is valid

            # Verify each link in the chain
            for i in range(1, len(receipts)):
                prev_receipt = receipts[i - 1]
                curr_receipt = receipts[i]

                if curr_receipt.state_hash_before != prev_receipt.state_hash_after:
                    return False

            return True
        except Exception as e:
            raise RuntimeError(f"Chain verification failed: {e}") from e

    def _git_run(self, args: list[str], check_output: bool = True) -> str:
        """Run git command in repository.

        Parameters
        ----------
        args : list[str]
            Git command arguments (without 'git' prefix)
        check_output : bool, optional
            Whether to capture and return output (default: True)

        Returns
        -------
        str
            Command output (empty if check_output=False)

        Raises
        ------
        RuntimeError
            If git command fails
        """
        try:
            cmd = ["git", "-C", str(self._repo_path), *args]
            if check_output:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return result.stdout
            else:
                subprocess.run(cmd, check=True, capture_output=True)
                return ""
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e.stderr}") from e


class LockchainHook:
    """Tick hook that automatically writes receipts to lockchain.

    Integrates with TickController to capture state hashes before/after
    each tick and write immutable receipts to git.

    Parameters
    ----------
    writer : LockchainWriter
        Lockchain writer instance
    store : RDFStore
        RDF store to hash

    Attributes
    ----------
    _writer : LockchainWriter
        Lockchain writer
    _store : RDFStore
        Store to hash
    _state_hash_before : str
        Hash captured in on_pre_tick
    _rules_fired_uris : list[str]
        Rule URIs collected during tick
    """

    def __init__(self, writer: LockchainWriter, store: RDFStore) -> None:
        """Initialize lockchain hook.

        Parameters
        ----------
        writer : LockchainWriter
            Lockchain writer instance
        store : RDFStore
            RDF store to hash
        """
        self._writer = writer
        self._store = store
        self._state_hash_before: str = ""
        self._rules_fired_uris: list[str] = []

    def on_pre_tick(self, engine: Any, tick_number: int) -> bool:
        """Capture state hash before tick execution.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        tick_number : int
            Current tick number

        Returns
        -------
        bool
            Always True (no validation failures)
        """
        # Compute and store pre-tick state hash
        self._state_hash_before = self._writer.compute_state_hash(self._store)
        self._rules_fired_uris.clear()
        return True

    def on_rule_fired(self, engine: Any, rule: Any, tick_number: int) -> None:
        """Record rule firing.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        rule : Any
            Rule that fired
        tick_number : int
            Current tick number
        """
        # Extract rule URI
        rule_uri = getattr(rule, "uri", None) or getattr(rule, "id", str(rule))
        self._rules_fired_uris.append(rule_uri)

    def on_post_tick(self, engine: Any, result: TickResult) -> None:
        """Write receipt to lockchain after tick completion.

        Parameters
        ----------
        engine : Any
            Hybrid engine instance
        result : TickResult
            Tick execution result
        """
        # Compute post-tick state hash
        state_hash_after = self._writer.compute_state_hash(self._store)

        # Create receipt
        receipt = TickReceipt(
            tick_number=result.tick_number,
            state_hash_before=self._state_hash_before,
            state_hash_after=state_hash_after,
            rules_fired=tuple(self._rules_fired_uris),
            triples_added=result.triples_added,
            triples_removed=result.triples_removed,
            timestamp=datetime.now(UTC),
            converged=result.converged,
        )

        # Write to lockchain
        self._writer.write_receipt(receipt)
