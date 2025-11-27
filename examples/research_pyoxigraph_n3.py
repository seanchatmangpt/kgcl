#!/usr/bin/env python3
"""Research PyOxigraph API - N3 Format Support.

Test if PyOxigraph can parse N3 format with implications (=>).
"""

import pyoxigraph as ox


def test_n3_parsing() -> None:
    """Test N3 format parsing."""
    print("=" * 60)
    print("TEST: N3 Format Parsing")
    print("=" * 60)

    # Try parsing N3 with implications
    n3_data = '''
    @prefix ex: <http://example.org/> .
    @prefix log: <http://www.w3.org/2000/10/swap/log#> .

    { ?x ex:status "Active" } => { ?x ex:isReady true } .

    ex:task1 ex:status "Active" .
    '''

    store = ox.Store()

    try:
        print("\nAttempting to parse N3 with RdfFormat.N3...")
        quad_count = 0
        for quad in ox.parse(input=n3_data, format=ox.RdfFormat.N3):
            store.add(quad)
            quad_count += 1
            print(f"  Added quad: {quad}")
        print(f"✓ Successfully parsed {quad_count} quads from N3")
    except Exception as e:
        print(f"✗ Failed to parse N3 with RdfFormat.N3: {e}")

    try:
        print("\nAttempting to parse N3 with RdfFormat.TURTLE...")
        store2 = ox.Store()
        quad_count = 0
        for quad in ox.parse(input=n3_data, format=ox.RdfFormat.TURTLE):
            store2.add(quad)
            quad_count += 1
            print(f"  Added quad: {quad}")
        print(f"✓ Successfully parsed {quad_count} quads with TURTLE")
    except Exception as e:
        print(f"✗ Failed to parse N3 with RdfFormat.TURTLE: {e}")

    # Try simpler N3 without implications
    simple_n3 = '''
    @prefix ex: <http://example.org/> .

    ex:task1 ex:status "Active" .
    ex:task2 ex:status "Pending" .
    '''

    try:
        print("\nAttempting to parse simple N3 (no implications) with RdfFormat.TURTLE...")
        store3 = ox.Store()
        quad_count = 0
        for quad in ox.parse(input=simple_n3, format=ox.RdfFormat.TURTLE):
            store3.add(quad)
            quad_count += 1
            print(f"  Added quad: {quad}")
        print(f"✓ Successfully parsed {quad_count} quads from simple N3")
    except Exception as e:
        print(f"✗ Failed to parse simple N3: {e}")

    print("\n" + "=" * 60)
    print("CONCLUSION:")
    print("=" * 60)
    print("If N3 with implications failed, we need to:")
    print("1. Use Turtle for state storage in PyOxigraph")
    print("2. Keep N3 rules in separate files for EYE processing")
    print("3. EYE processes rules + state, outputs conclusions")


if __name__ == "__main__":
    test_n3_parsing()
