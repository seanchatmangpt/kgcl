#!/usr/bin/env python3
"""Research PyOxigraph API - SPARQL UPDATE Support.

Test if PyOxigraph supports SPARQL UPDATE operations.
"""

import io
import pyoxigraph as ox


def test_sparql_update() -> None:
    """Test SPARQL UPDATE operations."""
    print("=" * 60)
    print("TEST: SPARQL UPDATE Support")
    print("=" * 60)

    # Create store with initial data
    store = ox.Store()

    turtle_data = '''
    @prefix ex: <http://example.org/> .

    ex:task1 ex:status "Active" ;
             ex:priority 1 .

    ex:task2 ex:status "Pending" ;
             ex:priority 2 .
    '''

    for quad in ox.parse(input=turtle_data, format=ox.RdfFormat.TURTLE):
        store.add(quad)

    print("Initial data loaded:")
    print_store(store)

    # Test INSERT DATA
    print("\n" + "=" * 60)
    print("TEST 1: INSERT DATA")
    print("=" * 60)

    insert_query = '''
    PREFIX ex: <http://example.org/>
    INSERT DATA {
        ex:task3 ex:status "Active" ;
                 ex:priority 3 .
    }
    '''

    try:
        store.update(insert_query)
        print("✓ INSERT DATA succeeded")
        print_store(store)
    except Exception as e:
        print(f"✗ INSERT DATA failed: {e}")

    # Test DELETE WHERE
    print("\n" + "=" * 60)
    print("TEST 2: DELETE WHERE")
    print("=" * 60)

    delete_query = '''
    PREFIX ex: <http://example.org/>
    DELETE WHERE {
        ?task ex:status "Pending" .
    }
    '''

    try:
        store.update(delete_query)
        print("✓ DELETE WHERE succeeded")
        print_store(store)
    except Exception as e:
        print(f"✗ DELETE WHERE failed: {e}")

    # Test DELETE/INSERT
    print("\n" + "=" * 60)
    print("TEST 3: DELETE/INSERT (Update existing)")
    print("=" * 60)

    update_query = '''
    PREFIX ex: <http://example.org/>
    DELETE { ?task ex:status ?oldStatus }
    INSERT { ?task ex:status "Completed" }
    WHERE {
        ?task ex:status ?oldStatus ;
              ex:priority 1 .
    }
    '''

    try:
        store.update(update_query)
        print("✓ DELETE/INSERT succeeded")
        print_store(store)
    except Exception as e:
        print(f"✗ DELETE/INSERT failed: {e}")

    # Test CLEAR
    print("\n" + "=" * 60)
    print("TEST 4: CLEAR (clear all data)")
    print("=" * 60)

    clear_query = 'CLEAR DEFAULT'

    try:
        store.update(clear_query)
        print("✓ CLEAR succeeded")
        print_store(store)
    except Exception as e:
        print(f"✗ CLEAR failed: {e}")


def print_store(store: ox.Store) -> None:
    """Print all triples in store."""
    print(str(store))


if __name__ == "__main__":
    test_sparql_update()
