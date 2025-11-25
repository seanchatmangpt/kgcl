"""Property-based testing example."""

from src.validation import Property, PropertyGenerator, PropertyTest


def example_commutative():
    """Example: addition is commutative."""
    test = (
        Property()
        .name("addition_is_commutative")
        .predicate(lambda a, b: a + b == b + a)
        .example(1, 2)
        .example(5, 3)
        .example(-1, 1)
        .example(0, 0)
        .build()
    )

    if test.run():
        print(f"✓ Commutative property: {len(test.examples)} examples passed")
    else:
        print(f"✗ Commutative property: {test.failure_count()} failures")
        for failure in test.failures():
            print(f"  Failed: {failure}")


def example_associative():
    """Example: addition is associative."""
    test = (
        Property()
        .name("addition_is_associative")
        .predicate(lambda a, b, c: (a + b) + c == a + (b + c))
        .example(1, 2, 3)
        .example(5, 3, 2)
        .example(-1, 1, 0)
        .build()
    )

    if test.run():
        print(f"✓ Associative property: {len(test.examples)} examples passed")
    else:
        print(f"✗ Associative property: {test.failure_count()} failures")


def example_with_generator():
    """Example using property generator."""
    gen = PropertyGenerator.integers(min=1, max=100)
    test = PropertyTest(name="positive_integers", predicate=lambda x: x > 0)

    # Add generated examples
    for value in gen.take(10):
        test.add_example(value)

    if test.run():
        print(f"✓ Generated property: {test.results['passed']} passed")
    else:
        print(f"✗ Generated property: {test.results['failed']} failed")


if __name__ == "__main__":
    example_commutative()
    example_associative()
    example_with_generator()
