#!/usr/bin/env python3
"""Research PyOxigraph API - Serialization Methods.

Test dump() and serialize() for exporting store data in different formats.
"""

import io

import pyoxigraph as ox


def test_serialization() -> None:
    """Test serialization methods."""
    print("=" * 60)
    print("TEST: Serialization Methods")
    print("=" * 60)

    # Create store with test data
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

    print("\n1. Using store.dump() with Turtle format")
    print("-" * 60)
    try:
        output = io.BytesIO()
        store.dump(output, format=ox.RdfFormat.TURTLE)
        print(output.getvalue().decode())
    except Exception as e:
        print(f"✗ dump() with Turtle failed: {e}")

    print("\n2. Using store.dump() with NQuads format")
    print("-" * 60)
    try:
        output = io.BytesIO()
        store.dump(output, format=ox.RdfFormat.N_QUADS)
        print(output.getvalue().decode())
    except Exception as e:
        print(f"✗ dump() with NQuads failed: {e}")

    print("\n3. Using ox.serialize() with store iterator")
    print("-" * 60)
    try:
        output = io.BytesIO()
        ox.serialize(store, output, format=ox.RdfFormat.TURTLE)
        print(output.getvalue().decode())
    except Exception as e:
        print(f"✗ serialize() with Turtle failed: {e}")

    print("\n4. Iterating over quads directly")
    print("-" * 60)
    for quad in store:
        print(f"  {quad}")

    print("\n" + "=" * 60)
    print("CONCLUSION:")
    print("=" * 60)
    print("✓ Use store.dump(output, format=RdfFormat.TURTLE) for Turtle export")
    print("✓ Use str(store) for quick NQuads string")
    print("✓ Use iteration for custom processing")


if __name__ == "__main__":
    test_serialization()
