#!/usr/bin/env python3
"""Research PyOxigraph API - Final Summary.

Complete working examples for the hybrid engine implementation.
"""

import io

import pyoxigraph as ox


def test_complete_workflow() -> None:
    """Test complete workflow: create, load, query, update, export."""
    print("=" * 70)
    print("PYOXIGRAPH COMPLETE WORKFLOW FOR HYBRID ENGINE")
    print("=" * 70)

    # 1. CREATE IN-MEMORY STORE
    print("\n1. Creating in-memory store")
    print("-" * 70)
    store = ox.Store()
    print("✓ Created in-memory store (no persistence)")

    # 2. LOAD TURTLE DATA
    print("\n2. Loading Turtle data")
    print("-" * 70)
    turtle_data = '''
    @prefix ex: <http://example.org/> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

    ex:task1 ex:status "Active" ;
             ex:priority 1 ;
             rdf:type ex:Task .

    ex:task2 ex:status "Pending" ;
             ex:priority 2 ;
             rdf:type ex:Task .
    '''

    for quad in ox.parse(input=turtle_data, format=ox.RdfFormat.TURTLE):
        store.add(quad)
    print("✓ Loaded Turtle data into store")

    # 3. SPARQL SELECT QUERY
    print("\n3. Running SPARQL SELECT query")
    print("-" * 70)
    query = '''
    PREFIX ex: <http://example.org/>
    SELECT ?task ?status ?priority
    WHERE {
        ?task ex:status ?status ;
              ex:priority ?priority .
    }
    ORDER BY ?priority
    '''

    results = store.query(query)
    for row in results:
        print(f"  Task: {row['task']}, Status: {row['status']}, Priority: {row['priority']}")

    # 4. SPARQL UPDATE (INSERT)
    print("\n4. Running SPARQL UPDATE (INSERT)")
    print("-" * 70)
    insert_query = '''
    PREFIX ex: <http://example.org/>
    INSERT DATA {
        ex:task3 ex:status "Active" ;
                 ex:priority 3 .
    }
    '''
    store.update(insert_query)
    print("✓ Inserted new task")

    # 5. SPARQL UPDATE (DELETE/INSERT)
    print("\n5. Running SPARQL UPDATE (DELETE/INSERT)")
    print("-" * 70)
    update_query = '''
    PREFIX ex: <http://example.org/>
    DELETE { ?task ex:status ?oldStatus }
    INSERT { ?task ex:status "Completed" }
    WHERE {
        ?task ex:status ?oldStatus ;
              ex:priority 1 .
    }
    '''
    store.update(update_query)
    print("✓ Updated task1 status to Completed")

    # 6. EXPORT AS NQUADS (fastest)
    print("\n6. Export as NQuads (fastest)")
    print("-" * 70)
    nquads = str(store)
    print(nquads)

    # 7. EXPORT AS TURTLE (human-readable)
    print("\n7. Export as Turtle (human-readable)")
    print("-" * 70)
    turtle_output = ox.serialize(store, format=ox.RdfFormat.TURTLE)
    print(turtle_output.decode())

    # 8. ITERATE OVER QUADS
    print("\n8. Iterate over quads (custom processing)")
    print("-" * 70)
    quad_count = 0
    for quad in store:
        quad_count += 1
    print(f"✓ Total quads in store: {quad_count}")

    # 9. PERSISTENT STORE
    print("\n9. Creating persistent store")
    print("-" * 70)
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "hybrid_store"
        persistent_store = ox.Store(path=str(store_path))

        # Copy data to persistent store
        for quad in store:
            persistent_store.add(quad)

        print(f"✓ Created persistent store at: {store_path}")

        # Close and reopen
        del persistent_store
        persistent_store = ox.Store(path=str(store_path))

        # Verify data persisted
        count_query = 'SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }'
        count_result = persistent_store.query(count_query)
        for row in count_result:
            print(f"✓ Data persisted: {row['count']} quads")

    print("\n" + "=" * 70)
    print("SUMMARY: PYOXIGRAPH CAPABILITIES FOR HYBRID ENGINE")
    print("=" * 70)
    print("✓ In-memory stores: ox.Store()")
    print("✓ Persistent stores: ox.Store(path='...')")
    print("✓ Load Turtle: ox.parse(input=data, format=ox.RdfFormat.TURTLE)")
    print("✓ SPARQL SELECT: store.query(query)")
    print("✓ SPARQL UPDATE: store.update(query)")
    print("✓ Export NQuads: str(store)")
    print("✓ Export Turtle: ox.serialize(store, format=ox.RdfFormat.TURTLE)")
    print("✓ Iterate quads: for quad in store")
    print("")
    print("⚠️  N3 with implications (=>) NOT supported")
    print("    → Use Turtle for state, N3 rules for EYE")


if __name__ == "__main__":
    test_complete_workflow()
