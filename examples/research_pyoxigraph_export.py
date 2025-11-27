#!/usr/bin/env python3
"""Research PyOxigraph API - Export Capabilities.

Test different serialization formats for exporting store data.
"""

import io

import pyoxigraph as ox


def test_export_formats() -> None:
    """Test different export/serialization formats."""
    print("=" * 60)
    print("TEST: Export Formats")
    print("=" * 60)

    # Create store with test data
    store = ox.Store()

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

    print("\n1. Using str(store) - NQuads format")
    print("-" * 60)
    nquads_output = str(store)
    print(nquads_output)

    print("\n2. Using dump_dataset() - Turtle format")
    print("-" * 60)
    try:
        output = io.BytesIO()
        store.dump_dataset(output, format=ox.RdfFormat.TURTLE)
        turtle_output = output.getvalue().decode()
        print(turtle_output)
    except Exception as e:
        print(f"✗ dump_dataset with Turtle failed: {e}")

    print("\n3. Using dump_dataset() - NQuads format")
    print("-" * 60)
    try:
        output = io.BytesIO()
        store.dump_dataset(output, format=ox.RdfFormat.N_QUADS)
        nquads_output = output.getvalue().decode()
        print(nquads_output)
    except Exception as e:
        print(f"✗ dump_dataset with NQuads failed: {e}")

    print("\n4. Using dump_dataset() - TriG format")
    print("-" * 60)
    try:
        output = io.BytesIO()
        store.dump_dataset(output, format=ox.RdfFormat.TRIG)
        trig_output = output.getvalue().decode()
        print(trig_output)
    except Exception as e:
        print(f"✗ dump_dataset with TriG failed: {e}")

    print("\n5. Using dump_dataset() - RDF/XML format")
    print("-" * 60)
    try:
        output = io.BytesIO()
        store.dump_dataset(output, format=ox.RdfFormat.RDF_XML)
        rdfxml_output = output.getvalue().decode()
        print(rdfxml_output)
    except Exception as e:
        print(f"✗ dump_dataset with RDF/XML failed: {e}")

    print("\n" + "=" * 60)
    print("CONCLUSION:")
    print("=" * 60)
    print("For hybrid engine, we can use:")
    print("1. Turtle format for human-readable state exports")
    print("2. NQuads for fast serialization via str(store)")
    print("3. dump_dataset() for specific format requirements")


if __name__ == "__main__":
    test_export_formats()
