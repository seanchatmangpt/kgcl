#!/usr/bin/env python3
"""Lockchain Anchor demonstration.

Shows how tick receipts are written to git-backed immutable chain.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

# Mock RDF store for demo
class DemoRDFStore:
    """Simple RDF store for demonstration."""

    def __init__(self) -> None:
        """Initialize store."""
        self._data: str = ""

    def dump(self) -> str:
        """Dump store contents."""
        return self._data

    def add_triple(self, triple: str) -> None:
        """Add triple to store."""
        self._data += triple + "\n"

    def __len__(self) -> int:
        """Return triple count."""
        return len(self._data.strip().split("\n")) if self._data.strip() else 0


def main() -> None:
    """Run lockchain demonstration."""
    import subprocess

    from kgcl.hybrid.lockchain import LockchainHook, LockchainWriter, TickReceipt
    from kgcl.hybrid.tick_controller import TickController, TickResult

    print("=== Lockchain Anchor Demo ===\n")

    # Create temporary git repo
    with TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / "demo_repo"
        repo_path.mkdir()

        # Initialize git
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "demo@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Demo User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create lockchain writer
        writer = LockchainWriter(repo_path)
        print(f"✓ Lockchain initialized at: {writer._lockchain_dir}")

        # Create store
        store = DemoRDFStore()
        print("✓ RDF store created\n")

        # Create mock engine
        class DemoEngine:
            def __init__(self, store: DemoRDFStore) -> None:
                self.graph = store
                self.rules: list[DemoRule] = []

        class DemoRule:
            uri = "demo:ExampleRule"

            def execute(self, graph: DemoRDFStore) -> int:
                graph.add_triple(":subject :predicate :object .")
                return 1

        engine = DemoEngine(store)
        engine.rules.append(DemoRule())

        # Setup tick controller with lockchain hook
        controller = TickController(engine)
        hook = LockchainHook(writer, store)
        controller.register_hook(hook)

        print("=== Executing Ticks ===\n")

        # Execute 3 ticks
        for i in range(3):
            result = controller.execute_tick()
            print(
                f"Tick {result.tick_number}: "
                f"rules={result.rules_fired}, "
                f"added={result.triples_added}, "
                f"converged={result.converged}"
            )

        print("\n=== Receipt Chain ===\n")

        # Read receipt chain
        receipts = writer.get_receipt_chain()
        for receipt in receipts:
            print(f"Tick {receipt.tick_number}:")
            print(f"  State before: {receipt.state_hash_before}")
            print(f"  State after:  {receipt.state_hash_after}")
            print(f"  Rules fired:  {receipt.rules_fired}")
            print(f"  Triples added: {receipt.triples_added}")
            print(f"  Converged: {receipt.converged}")
            print()

        # Verify chain integrity
        is_valid = writer.verify_chain()
        print(f"{'✓' if is_valid else '✗'} Chain verification: {'PASSED' if is_valid else 'FAILED'}")

        # Show git log
        print("\n=== Git Commit Log ===\n")
        result = subprocess.run(
            ["git", "log", "--oneline", "--no-decorate"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        print(result.stdout)

        print("=== Demo Complete ===")


if __name__ == "__main__":
    main()
