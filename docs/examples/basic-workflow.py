#!/usr/bin/env python3
"""Basic workflow execution example.

This example demonstrates:
1. Creating a HybridEngine
2. Loading a simple workflow topology
3. Running to completion
4. Inspecting results

Run with:
    python docs/examples/basic-workflow.py
"""

from kgcl.hybrid import HybridEngine, ConvergenceError


def main() -> None:
    """Execute a simple sequence workflow."""
    # Create in-memory engine
    engine = HybridEngine()

    # Define workflow topology in Turtle format
    # This is WCP-1 (Sequence): A -> B -> C
    topology = """
    @prefix kgc: <https://kgc.org/ns/> .
    @prefix yawl: <http://www.yawlfoundation.org/yawlschema#> .

    # Task A is completed (starting point)
    <urn:task:A> a yawl:Task ;
        kgc:status "Completed" ;
        yawl:flowsInto <urn:flow:AB> .

    # Flow from A to B
    <urn:flow:AB> yawl:nextElementRef <urn:task:B> .

    # Task B is pending
    <urn:task:B> a yawl:Task ;
        kgc:status "Pending" ;
        yawl:flowsInto <urn:flow:BC> .

    # Flow from B to C
    <urn:flow:BC> yawl:nextElementRef <urn:task:C> .

    # Task C is pending
    <urn:task:C> a yawl:Task ;
        kgc:status "Pending" .
    """

    # Load the topology
    engine.load_data(topology)
    print("Loaded workflow topology")
    print(f"Initial triple count: {engine.store.__len__()}")
    print()

    # Show initial statuses
    print("Initial task statuses:")
    for task, status in engine.inspect().items():
        print(f"  {task} -> {status}")
    print()

    # Run to completion
    try:
        results = engine.run_to_completion(max_ticks=10)

        print(f"Converged in {len(results)} tick(s)")
        print()

        # Show tick details
        print("Tick history:")
        for result in results:
            print(f"  Tick {result.tick_number}: delta={result.delta}, "
                  f"duration={result.duration_ms:.2f}ms, "
                  f"converged={result.converged}")
        print()

    except ConvergenceError as e:
        print(f"Failed to converge after {e.max_ticks} ticks")
        print(f"Final delta: {e.final_delta}")
        return

    # Show final statuses
    print("Final task statuses:")
    for task, status in engine.inspect().items():
        print(f"  {task} -> {status}")
    print()

    # Summary
    total_delta = sum(r.delta for r in results)
    total_time = sum(r.duration_ms for r in results)
    print(f"Total triples added: {total_delta}")
    print(f"Total execution time: {total_time:.2f}ms")


if __name__ == "__main__":
    main()
