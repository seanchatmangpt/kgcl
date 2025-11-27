"""Tests for Lockchain Anchor integration.

Chicago School TDD: Test behavior, not implementation.
"""

import subprocess
from datetime import UTC, datetime, timezone
from pathlib import Path

import pytest


class MockRDFStore:
    """Mock RDF store for testing lockchain."""

    def __init__(self) -> None:
        """Initialize mock store."""
        self._data: str = ""

    def dump(self) -> str:
        """Dump store contents."""
        return self._data

    def load_turtle(self, data: str) -> int:
        """Load turtle data."""
        self._data += data + "\n"
        return 1

    def __len__(self) -> int:
        """Return triple count."""
        return len(self._data.strip().split("\n")) if self._data.strip() else 0


from kgcl.hybrid.lockchain import LockchainHook, LockchainWriter, TickReceipt
from kgcl.hybrid.tick_controller import TickResult


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository.

    Parameters
    ----------
    tmp_path : Path
        Pytest temporary directory fixture

    Returns
    -------
    Path
        Path to initialized git repository
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)

    return repo_path


@pytest.fixture
def mock_store() -> MockRDFStore:
    """Create mock RDF store.

    Returns
    -------
    MockRDFStore
        Mock store instance
    """
    return MockRDFStore()


@pytest.fixture
def lockchain_writer(temp_git_repo: Path) -> LockchainWriter:
    """Create lockchain writer.

    Parameters
    ----------
    temp_git_repo : Path
        Temporary git repository

    Returns
    -------
    LockchainWriter
        Writer instance
    """
    return LockchainWriter(temp_git_repo)


class TestTickReceipt:
    """Test TickReceipt frozen dataclass."""

    def test_receipt_is_frozen(self) -> None:
        """Receipt should be immutable."""
        receipt = TickReceipt(
            tick_number=1,
            state_hash_before="sha256:abc",
            state_hash_after="sha256:def",
            rules_fired=("rule1",),
            triples_added=5,
            triples_removed=2,
            timestamp=datetime.now(UTC),
            converged=False,
        )

        with pytest.raises(AttributeError):
            receipt.tick_number = 2  # type: ignore[misc]

    def test_rules_fired_is_tuple(self) -> None:
        """Rules fired should be stored as immutable tuple."""
        rules = ["rule1", "rule2", "rule3"]
        receipt = TickReceipt(
            tick_number=1,
            state_hash_before="sha256:abc",
            state_hash_after="sha256:def",
            rules_fired=tuple(rules),
            triples_added=5,
            triples_removed=0,
            timestamp=datetime.now(UTC),
            converged=False,
        )

        assert isinstance(receipt.rules_fired, tuple)
        assert receipt.rules_fired == ("rule1", "rule2", "rule3")

    def test_to_yaml_format(self) -> None:
        """YAML serialization should match specified format."""
        timestamp = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        receipt = TickReceipt(
            tick_number=1,
            state_hash_before="sha256:abc123",
            state_hash_after="sha256:def456",
            rules_fired=("kgc:WCP1_Sequence", "kgc:WCP2_ParallelSplit"),
            triples_added=5,
            triples_removed=2,
            timestamp=timestamp,
            converged=False,
        )

        yaml_str = receipt.to_yaml()

        # Verify structure
        assert "tick: 1" in yaml_str
        assert "timestamp: '2025-01-15T10:30:00+00:00'" in yaml_str
        assert "state:" in yaml_str
        assert "before: sha256:abc123" in yaml_str
        assert "after: sha256:def456" in yaml_str
        assert "mutations:" in yaml_str
        assert "triples_added: 5" in yaml_str
        assert "triples_removed: 2" in yaml_str
        assert "converged: false" in yaml_str
        assert "kgc:WCP1_Sequence" in yaml_str
        assert "kgc:WCP2_ParallelSplit" in yaml_str

    def test_from_yaml_round_trip(self) -> None:
        """Deserialization should reconstruct original receipt."""
        original = TickReceipt(
            tick_number=42,
            state_hash_before="sha256:abc123",
            state_hash_after="sha256:def456",
            rules_fired=("rule1", "rule2"),
            triples_added=10,
            triples_removed=3,
            timestamp=datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC),
            converged=True,
        )

        yaml_str = original.to_yaml()
        reconstructed = TickReceipt.from_yaml(yaml_str)

        assert reconstructed.tick_number == original.tick_number
        assert reconstructed.state_hash_before == original.state_hash_before
        assert reconstructed.state_hash_after == original.state_hash_after
        assert reconstructed.rules_fired == original.rules_fired
        assert reconstructed.triples_added == original.triples_added
        assert reconstructed.triples_removed == original.triples_removed
        assert reconstructed.timestamp == original.timestamp
        assert reconstructed.converged == original.converged

    def test_from_yaml_invalid_raises(self) -> None:
        """Invalid YAML should raise ValueError."""
        invalid_yaml = "invalid: yaml: structure:"

        with pytest.raises(ValueError, match="Invalid receipt YAML"):
            TickReceipt.from_yaml(invalid_yaml)


class TestLockchainWriter:
    """Test LockchainWriter git-backed storage."""

    def test_init_requires_git_repo(self, tmp_path: Path) -> None:
        """Writer initialization should fail for non-git directories."""
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()

        with pytest.raises(ValueError, match="Not a git repository"):
            LockchainWriter(non_repo)

    def test_init_creates_lockchain_directory(self, lockchain_writer: LockchainWriter) -> None:
        """Writer should create .kgc/lockchain directory."""
        lockchain_dir = lockchain_writer._lockchain_dir

        assert lockchain_dir.exists()
        assert lockchain_dir.is_dir()
        assert lockchain_dir.name == "lockchain"
        assert lockchain_dir.parent.name == ".kgc"

    def test_compute_state_hash_deterministic(
        self, mock_store: MockRDFStore, lockchain_writer: LockchainWriter
    ) -> None:
        """State hash should be deterministic for same store content."""
        # Load data
        ttl_data = """
        @prefix ex: <http://example.org/> .
        ex:subject1 ex:predicate1 "object1" .
        ex:subject2 ex:predicate2 "object2" .
        """
        mock_store.load_turtle(ttl_data)

        # Compute hash twice
        hash1 = lockchain_writer.compute_state_hash(mock_store)
        hash2 = lockchain_writer.compute_state_hash(mock_store)

        assert hash1 == hash2
        assert hash1.startswith("sha256:")
        assert len(hash1) == 71  # "sha256:" + 64 hex chars

    def test_compute_state_hash_changes_with_content(
        self, mock_store: MockRDFStore, lockchain_writer: LockchainWriter
    ) -> None:
        """State hash should change when store content changes."""
        # Initial data
        mock_store.load_turtle('@prefix ex: <http://example.org/> . ex:s ex:p "o1" .')
        hash1 = lockchain_writer.compute_state_hash(mock_store)

        # Add more data
        mock_store.load_turtle('@prefix ex: <http://example.org/> . ex:s ex:p "o2" .')
        hash2 = lockchain_writer.compute_state_hash(mock_store)

        assert hash1 != hash2

    def test_write_receipt_creates_file(self, lockchain_writer: LockchainWriter) -> None:
        """Writing receipt should create YAML file."""
        receipt = TickReceipt(
            tick_number=1,
            state_hash_before="sha256:abc",
            state_hash_after="sha256:def",
            rules_fired=("rule1",),
            triples_added=5,
            triples_removed=0,
            timestamp=datetime.now(UTC),
            converged=False,
        )

        lockchain_writer.write_receipt(receipt)

        receipt_file = lockchain_writer._lockchain_dir / "tick_000001.yaml"
        assert receipt_file.exists()
        assert "tick: 1" in receipt_file.read_text()

    def test_write_receipt_creates_git_commit(self, lockchain_writer: LockchainWriter, temp_git_repo: Path) -> None:
        """Writing receipt should create git commit."""
        receipt = TickReceipt(
            tick_number=1,
            state_hash_before="sha256:abc",
            state_hash_after="sha256:def",
            rules_fired=("rule1",),
            triples_added=5,
            triples_removed=0,
            timestamp=datetime.now(UTC),
            converged=False,
        )

        commit_sha = lockchain_writer.write_receipt(receipt)

        # Verify commit exists
        assert len(commit_sha) == 40  # Git SHA-1 is 40 hex chars

        # Verify commit message
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"], cwd=temp_git_repo, capture_output=True, text=True, check=True
        )
        commit_msg = result.stdout

        assert "lockchain: tick 1" in commit_msg
        assert "state_before: sha256:abc" in commit_msg
        assert "state_after: sha256:def" in commit_msg
        assert "converged: False" in commit_msg

    def test_get_receipt_chain_empty(self, lockchain_writer: LockchainWriter) -> None:
        """Empty chain should return empty list."""
        receipts = lockchain_writer.get_receipt_chain()

        assert receipts == []

    def test_get_receipt_chain_chronological_order(self, lockchain_writer: LockchainWriter) -> None:
        """Receipts should be returned in chronological order."""
        # Write 3 receipts
        for i in range(1, 4):
            receipt = TickReceipt(
                tick_number=i,
                state_hash_before=f"sha256:before{i}",
                state_hash_after=f"sha256:after{i}",
                rules_fired=(),
                triples_added=0,
                triples_removed=0,
                timestamp=datetime.now(UTC),
                converged=False,
            )
            lockchain_writer.write_receipt(receipt)

        # Read chain
        receipts = lockchain_writer.get_receipt_chain()

        assert len(receipts) == 3
        assert receipts[0].tick_number == 1
        assert receipts[1].tick_number == 2
        assert receipts[2].tick_number == 3

    def test_get_receipt_chain_respects_limit(self, lockchain_writer: LockchainWriter) -> None:
        """Limit parameter should restrict number of receipts."""
        # Write 5 receipts
        for i in range(1, 6):
            receipt = TickReceipt(
                tick_number=i,
                state_hash_before=f"sha256:before{i}",
                state_hash_after=f"sha256:after{i}",
                rules_fired=(),
                triples_added=0,
                triples_removed=0,
                timestamp=datetime.now(UTC),
                converged=False,
            )
            lockchain_writer.write_receipt(receipt)

        # Read last 2 receipts
        receipts = lockchain_writer.get_receipt_chain(limit=2)

        assert len(receipts) == 2
        assert receipts[0].tick_number == 4
        assert receipts[1].tick_number == 5

    def test_verify_chain_empty(self, lockchain_writer: LockchainWriter) -> None:
        """Empty chain should be valid."""
        assert lockchain_writer.verify_chain() is True

    def test_verify_chain_single_receipt(self, lockchain_writer: LockchainWriter) -> None:
        """Single receipt chain should be valid."""
        receipt = TickReceipt(
            tick_number=1,
            state_hash_before="sha256:abc",
            state_hash_after="sha256:def",
            rules_fired=(),
            triples_added=0,
            triples_removed=0,
            timestamp=datetime.now(UTC),
            converged=False,
        )
        lockchain_writer.write_receipt(receipt)

        assert lockchain_writer.verify_chain() is True

    def test_verify_chain_valid_sequence(self, lockchain_writer: LockchainWriter) -> None:
        """Valid chain should verify successfully."""
        # Receipt 1
        receipt1 = TickReceipt(
            tick_number=1,
            state_hash_before="sha256:initial",
            state_hash_after="sha256:after1",
            rules_fired=(),
            triples_added=5,
            triples_removed=0,
            timestamp=datetime.now(UTC),
            converged=False,
        )
        lockchain_writer.write_receipt(receipt1)

        # Receipt 2 (before hash matches receipt1 after hash)
        receipt2 = TickReceipt(
            tick_number=2,
            state_hash_before="sha256:after1",
            state_hash_after="sha256:after2",
            rules_fired=(),
            triples_added=3,
            triples_removed=0,
            timestamp=datetime.now(UTC),
            converged=False,
        )
        lockchain_writer.write_receipt(receipt2)

        # Receipt 3
        receipt3 = TickReceipt(
            tick_number=3,
            state_hash_before="sha256:after2",
            state_hash_after="sha256:final",
            rules_fired=(),
            triples_added=0,
            triples_removed=0,
            timestamp=datetime.now(UTC),
            converged=True,
        )
        lockchain_writer.write_receipt(receipt3)

        assert lockchain_writer.verify_chain() is True

    def test_verify_chain_detects_tampering(self, lockchain_writer: LockchainWriter) -> None:
        """Chain verification should detect hash mismatch."""
        # Write valid chain
        receipt1 = TickReceipt(
            tick_number=1,
            state_hash_before="sha256:initial",
            state_hash_after="sha256:after1",
            rules_fired=(),
            triples_added=0,
            triples_removed=0,
            timestamp=datetime.now(UTC),
            converged=False,
        )
        lockchain_writer.write_receipt(receipt1)

        # Write receipt with mismatched hash (simulating tampering)
        receipt2 = TickReceipt(
            tick_number=2,
            state_hash_before="sha256:TAMPERED",  # Should be "sha256:after1"
            state_hash_after="sha256:after2",
            rules_fired=(),
            triples_added=0,
            triples_removed=0,
            timestamp=datetime.now(UTC),
            converged=False,
        )
        lockchain_writer.write_receipt(receipt2)

        assert lockchain_writer.verify_chain() is False


class TestLockchainHook:
    """Test LockchainHook integration with TickController."""

    def test_on_pre_tick_captures_state_hash(self, lockchain_writer: LockchainWriter, mock_store: MockRDFStore) -> None:
        """on_pre_tick should capture state hash."""
        mock_store.load_turtle('@prefix ex: <http://example.org/> . ex:s ex:p "o" .')

        hook = LockchainHook(lockchain_writer, mock_store)
        hook.on_pre_tick(None, 1)

        # Verify hash was captured
        assert hook._state_hash_before.startswith("sha256:")
        assert len(hook._state_hash_before) == 71

    def test_on_rule_fired_records_uri(self, lockchain_writer: LockchainWriter, mock_store: MockRDFStore) -> None:
        """on_rule_fired should record rule URIs."""
        hook = LockchainHook(lockchain_writer, mock_store)

        # Create mock rule with uri attribute
        class MockRule:
            uri = "kgc:WCP1_Sequence"

        hook.on_rule_fired(None, MockRule(), 1)

        assert "kgc:WCP1_Sequence" in hook._rules_fired_uris

    def test_on_post_tick_writes_receipt(self, lockchain_writer: LockchainWriter, mock_store: MockRDFStore) -> None:
        """on_post_tick should write complete receipt."""
        mock_store.load_turtle('@prefix ex: <http://example.org/> . ex:s ex:p "o" .')

        hook = LockchainHook(lockchain_writer, mock_store)

        # Simulate tick
        hook.on_pre_tick(None, 1)

        class MockRule:
            uri = "kgc:TestRule"

        hook.on_rule_fired(None, MockRule(), 1)

        tick_result = TickResult(
            tick_number=1, rules_fired=1, triples_added=5, triples_removed=0, duration_ms=10.5, converged=False
        )

        hook.on_post_tick(None, tick_result)

        # Verify receipt was written
        receipts = lockchain_writer.get_receipt_chain()
        assert len(receipts) == 1

        receipt = receipts[0]
        assert receipt.tick_number == 1
        assert receipt.triples_added == 5
        assert receipt.triples_removed == 0
        assert receipt.converged is False
        assert "kgc:TestRule" in receipt.rules_fired

    def test_full_integration_with_tick_controller(
        self, lockchain_writer: LockchainWriter, mock_store: MockRDFStore
    ) -> None:
        """Test full integration with actual tick execution."""
        from kgcl.hybrid.tick_controller import TickController

        # Create mock engine
        class MockEngine:
            def __init__(self, store: MockRDFStore) -> None:
                self.graph = store
                self.rules: list[MockRule] = []

        class MockRule:
            uri = "kgc:TestRule"

            def execute(self, graph: MockRDFStore) -> int:
                # Simulate adding triples
                graph.load_turtle('@prefix ex: <http://example.org/> . ex:new ex:triple "value" .')
                return 1

        engine = MockEngine(mock_store)
        engine.rules.append(MockRule())

        # Initialize controller with lockchain hook
        controller = TickController(engine)
        hook = LockchainHook(lockchain_writer, mock_store)
        controller.register_hook(hook)

        # Execute tick
        result = controller.execute_tick()

        # Verify receipt was written
        receipts = lockchain_writer.get_receipt_chain()
        assert len(receipts) == 1

        receipt = receipts[0]
        assert receipt.tick_number == 1
        assert receipt.rules_fired == ("kgc:TestRule",)
        assert receipt.state_hash_before != receipt.state_hash_after
        assert lockchain_writer.verify_chain() is True
