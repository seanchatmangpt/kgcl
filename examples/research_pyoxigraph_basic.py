#!/usr/bin/env python3
"""Research PyOxigraph API - Basic Operations.

Test in-memory store creation, Turtle loading, SPARQL queries, and data dumping.
"""

import io
import pyoxigraph as ox


def test_basic_operations() -> None:
    """Test basic PyOxigraph operations."""
    print("=" * 60)
    print("TEST 1: In-Memory Store Creation")
    print("=" * 60)

    # Create in-memory store
    store = ox.Store()
    print(f"✓ Created in-memory store: {type(store)}")

    print("\n" + "=" * 60)
    print("TEST 2: Loading Turtle Data")
    print("=" * 60)

    # Load Turtle data
    turtle_data = '''
    @prefix ex: <http://example.org/> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

    ex:task1 ex:status "Active" ;
             ex:priority 1 ;
             rdf:type ex:Task .

    ex:task2 ex:status "Pending" ;
             ex:priority 2 ;
             rdf:type ex:Task .
    '''

    quad_count = 0
    for quad in ox.parse(input=turtle_data, format=ox.RdfFormat.TURTLE):
        store.add(quad)
        quad_count += 1
        print(f"  Added quad: {quad}")

    print(f"✓ Loaded {quad_count} quads from Turtle")

    print("\n" + "=" * 60)
    print("TEST 3: SPARQL SELECT Query")
    print("=" * 60)

    # Query data
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
    print("Query results:")
    for row in results:
        print(f"  Task: {row['task']}, Status: {row['status']}, Priority: {row['priority']}")

    print("\n" + "=" * 60)
    print("TEST 4: SPARQL ASK Query")
    print("=" * 60)

    ask_query = '''
    PREFIX ex: <http://example.org/>
    ASK {
        ?task ex:status "Active" .
    }
    '''

    ask_result = store.query(ask_query)
    print(f"Has active tasks: {ask_result}")

    print("\n" + "=" * 60)
    print("TEST 5: Dumping Store to Turtle String")
    print("=" * 60)

    # Dump to string using store's __str__ (outputs NQuads)
    turtle_output = str(store)
    print("Dumped NQuads:")
    print(turtle_output)

    print("\n" + "=" * 60)
    print("TEST 6: Store Statistics")
    print("=" * 60)

    # Count triples
    count_query = 'SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }'
    count_result = store.query(count_query)
    for row in count_result:
        print(f"Total triples in store: {row['count']}")


if __name__ == "__main__":
    test_basic_operations()
