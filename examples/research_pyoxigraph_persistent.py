#!/usr/bin/env python3
"""Research PyOxigraph API - Persistent Store.

Test creating and using persistent (disk-based) stores.
"""

import tempfile
from pathlib import Path

import pyoxigraph as ox


def test_persistent_store() -> None:
    """Test persistent store operations."""
    print("=" * 60)
    print("TEST: Persistent Store")
    print("=" * 60)

    # Create temporary directory for store
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "test_store"

        print(f"\n1. Creating persistent store at: {store_path}")

        # Create persistent store
        store = ox.Store(path=str(store_path))
        print(f"✓ Created persistent store: {type(store)}")

        # Add data
        print("\n2. Adding data to persistent store")
        turtle_data = '''
        @prefix ex: <http://example.org/> .

        ex:task1 ex:status "Active" ;
                 ex:priority 1 .

        ex:task2 ex:status "Pending" ;
                 ex:priority 2 .
        '''

        quad_count = 0
        for quad in ox.parse(input=turtle_data, format=ox.RdfFormat.TURTLE):
            store.add(quad)
            quad_count += 1

        print(f"✓ Added {quad_count} quads to persistent store")

        # Close and reopen store
        print("\n3. Closing store")
        del store
        print("✓ Store closed")

        print("\n4. Reopening store from disk")
        store2 = ox.Store(path=str(store_path))
        print("✓ Store reopened")

        # Query to verify data persisted
        print("\n5. Querying reopened store")
        query = '''
        PREFIX ex: <http://example.org/>
        SELECT ?task ?status ?priority
        WHERE {
            ?task ex:status ?status ;
                  ex:priority ?priority .
        }
        ORDER BY ?priority
        '''

        results = store2.query(query)
        result_count = 0
        for row in results:
            result_count += 1
            print(f"  Task: {row['task']}, Status: {row['status']}, Priority: {row['priority']}")

        if result_count == 2:
            print(f"✓ Data persisted correctly ({result_count} results)")
        else:
            print(f"✗ Data persistence issue (expected 2 results, got {result_count})")

        # Test file structure
        print("\n6. Examining store file structure")
        if store_path.exists():
            print(f"✓ Store directory exists: {store_path}")
            files = list(store_path.rglob("*"))
            print(f"  Store contains {len(files)} files/directories:")
            for f in sorted(files)[:10]:  # Show first 10
                rel_path = f.relative_to(store_path)
                print(f"    - {rel_path}")
        else:
            print(f"✗ Store directory not found: {store_path}")


if __name__ == "__main__":
    test_persistent_store()
