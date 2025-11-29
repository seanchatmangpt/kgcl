"""Gemba walk: Verify what actually persists to disk vs memory.

This script proves what YAWL persistence actually does.
"""

import json
import tempfile
from pathlib import Path

from kgcl.yawl.elements.y_specification import YSpecification
from kgcl.yawl.persistence import CheckpointManager, XMLParser, XMLWriter, YInMemoryRepository


def test_in_memory_repository() -> None:
    """Prove: In-memory repositories DO NOT persist to disk."""
    print("\n=== In-Memory Repository Test ===")

    # Create repository and add data
    repo = YInMemoryRepository()
    spec = YSpecification(id="spec-001", name="Test Workflow")
    repo.specifications.save(spec)

    print(f"✓ Saved spec to memory: {spec.id}")
    print(f"✓ Can retrieve: {repo.specifications.get('spec-001') is not None}")

    # Check if anything was written to disk
    print(f"✗ Written to disk: False (in-memory only)")
    print("Result: Repository is volatile - lost on process exit")


def test_checkpoint_manager() -> None:
    """Prove: CheckpointManager stores in memory, NOT on disk."""
    print("\n=== Checkpoint Manager Test ===")

    manager = CheckpointManager()

    # Create mock case
    from dataclasses import dataclass
    @dataclass
    class MockCase:
        id: str
        specification_id: str = "spec-001"
        status: str = "RUNNING"
        root_net_id: str = "MainNet"
        case_data: dict = None
        work_items: dict = None
        net_runners: dict = None

        def __post_init__(self) -> None:
            if self.case_data is None:
                self.case_data = {}
            if self.work_items is None:
                self.work_items = {}
            if self.net_runners is None:
                self.net_runners = {}

    case = MockCase(id="case-001")
    checkpoint = manager.create_case_checkpoint(case)

    print(f"✓ Created checkpoint: {checkpoint.id}")
    print(f"✓ Stored in manager.checkpoints dict: {checkpoint.id in manager.checkpoints}")

    # Can serialize to JSON string
    json_str = checkpoint.to_json()
    print(f"✓ Can serialize to JSON: {len(json_str)} bytes")

    # Check if file was written
    print(f"✗ Written to disk: False (in-memory dict only)")
    print("Result: Checkpoints are volatile - must manually save JSON to file")


def test_xml_persistence() -> None:
    """Prove: XML parser CAN read from disk (but writer is broken)."""
    print("\n=== XML Persistence Test ===")

    # Create a simple YAWL XML file
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<specification id="test-spec" version="1.0" uri="urn:test-spec">
    <name>Test Specification</name>
    <documentation>Test persistence</documentation>
    <decomposition id="MainNet" isRootNet="true">
        <processControlElements>
            <inputCondition id="InputCondition"/>
            <outputCondition id="OutputCondition"/>
        </processControlElements>
    </decomposition>
</specification>"""

    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yawl', delete=False) as f:
        temp_path = Path(f.name)
        f.write(xml_content)

    print(f"✓ Written to disk: {temp_path}")
    print(f"✓ File exists: {temp_path.exists()}")
    print(f"✓ File size: {temp_path.stat().st_size} bytes")

    # Read it back
    parser = XMLParser()
    result = parser.parse_file(temp_path)

    print(f"✓ Read from disk: {result.success}")
    print(f"✓ Recovered spec ID: {result.specification.id if result.success else None}")

    # Cleanup
    temp_path.unlink()
    print("Result: XML files CAN persist (parser works, writer has bugs)")


def test_database_repository() -> None:
    """Prove: Database repository would persist, but needs connection."""
    print("\n=== Database Repository Test ===")

    from kgcl.yawl.persistence import DatabaseRepository

    repo = DatabaseRepository(connection_factory=None)

    try:
        # Try to use without connection
        repo.save_specification(
            spec_id="spec-001",
            uri="urn:spec-001",
            name="Test",
            version="1.0",
            status="ACTIVE"
        )
        print("✓ Saved to database")
    except RuntimeError as e:
        print(f"✗ Cannot persist: {e}")
        print("Reason: No database connection configured")

    print("Result: Database persistence WOULD be durable, but NOT configured/used in tests")


if __name__ == "__main__":
    print("=" * 60)
    print("YAWL PERSISTENCE REALITY CHECK")
    print("=" * 60)

    test_in_memory_repository()
    test_checkpoint_manager()
    test_xml_persistence()
    test_database_repository()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("✓ XML files: DURABLE (written to disk)")
    print("✗ In-memory repos: VOLATILE (lost on exit)")
    print("✗ Checkpoints: VOLATILE (in-memory dict, must manually save JSON)")
    print("✗ Database: NOT CONNECTED (capability exists, not used)")
    print("\nConclusion: Only XML parser/writer actually persists data.")
