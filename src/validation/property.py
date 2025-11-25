"""Property-Based Testing

Provides generators and property tests for example-driven testing.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")
P = TypeVar("P")


class PropertyGenerator(Generic[T]):
    """Generates values for property-based testing

    Example:
        @test
        def test_property():
            gen = PropertyGenerator.integers(min=0, max=100)
            for value in gen.take(10):
                assert value >= 0 and value <= 100
    """

    def __init__(self, generator_fn: Callable[[], T]) -> None:
        self._generator_fn = generator_fn

    def generate(self) -> T:
        """Generate a single value"""
        return self._generator_fn()

    def take(self, n: int) -> list[T]:
        """Generate n values"""
        return [self.generate() for _ in range(n)]

    @staticmethod
    def integers(min: int = 0, max: int = 100) -> "PropertyGenerator[int]":
        """Generate random integers in range"""
        return PropertyGenerator(lambda: random.randint(min, max))

    @staticmethod
    def floats(min: float = 0.0, max: float = 1.0) -> "PropertyGenerator[float]":
        """Generate random floats in range"""
        return PropertyGenerator(lambda: random.uniform(min, max))

    @staticmethod
    def strings(
        length: int = 10, chars: str = "abcdefghijklmnopqrstuvwxyz"
    ) -> "PropertyGenerator[str]":
        """Generate random strings"""
        return PropertyGenerator(lambda: "".join(random.choice(chars) for _ in range(length)))

    @staticmethod
    def booleans() -> "PropertyGenerator[bool]":
        """Generate random booleans"""
        return PropertyGenerator(lambda: random.choice([True, False]))

    @staticmethod
    def one_of(values: list[T]) -> "PropertyGenerator[T]":
        """Generate from a list of values"""
        return PropertyGenerator(lambda: random.choice(values))

    @staticmethod
    def lists(
        element_generator: "PropertyGenerator[T]", min_length: int = 0, max_length: int = 10
    ) -> "PropertyGenerator[list[T]]":
        """Generate lists of values"""

        def gen() -> list[T]:
            length = random.randint(min_length, max_length)
            return element_generator.take(length)

        return PropertyGenerator(gen)


@dataclass
class PropertyTest:
    """A property test with examples

    Example:
        test = PropertyTest(
            "commutative_addition",
            lambda a, b: a + b == b + a,
            examples=[
                (1, 2),
                (5, 3),
                (-1, 1),
            ]
        )
    """

    name: str
    predicate: Callable[..., bool]
    examples: list[tuple] = None
    generator: PropertyGenerator[Any] | None = None
    failed_examples: list[tuple] = None

    def __post_init__(self) -> None:
        if self.examples is None:
            self.examples = []
        if self.failed_examples is None:
            self.failed_examples = []

    def add_example(self, *args: Any) -> None:
        """Add an example to test"""
        self.examples.append(args)

    def run(self) -> bool:
        """Run property test against all examples

        Returns
        -------
            True if all examples pass, False if any fail
        """
        self.failed_examples = []

        for example in self.examples:
            try:
                if not self.predicate(*example):
                    self.failed_examples.append(example)
            except Exception:
                self.failed_examples.append(example)

        return len(self.failed_examples) == 0

    def run_generated(self, count: int = 100) -> bool:
        """Run property test with generated examples

        Args:
            count: Number of examples to generate

        Returns
        -------
            True if all examples pass, False if any fail

        Raises
        ------
            ValueError: If no generator configured
        """
        if self.generator is None:
            raise ValueError("No generator configured for property test")

        self.failed_examples = []

        for _ in range(count):
            example = self.generator.generate()
            try:
                if isinstance(example, tuple):
                    if not self.predicate(*example):
                        self.failed_examples.append(example)
                elif not self.predicate(example):
                    self.failed_examples.append((example,))
            except Exception:
                if isinstance(example, tuple):
                    self.failed_examples.append(example)
                else:
                    self.failed_examples.append((example,))

        return len(self.failed_examples) == 0

    def failure_count(self) -> int:
        """Get number of failed examples"""
        return len(self.failed_examples)

    def success_rate(self) -> float:
        """Calculate success rate"""
        total = len(self.examples) + len(self.failed_examples)
        if total == 0:
            return 0.0
        return ((total - len(self.failed_examples)) / total) * 100


class Property:
    """Builder for property tests

    Example:
        test = (Property()
            .name("commutative_addition")
            .predicate(lambda a, b: a + b == b + a)
            .example(1, 2)
            .example(5, 3)
            .build())
    """

    def __init__(self) -> None:
        self._name = "property_test"
        self._predicate: Callable[..., bool] | None = None
        self._examples: list[tuple] = []

    def name(self, name: str) -> "Property":
        """Set property name"""
        self._name = name
        return self

    def predicate(self, predicate: Callable[..., bool]) -> "Property":
        """Set property predicate"""
        self._predicate = predicate
        return self

    def example(self, *args: Any) -> "Property":
        """Add example"""
        self._examples.append(args)
        return self

    def examples(self, examples: list[tuple]) -> "Property":
        """Set all examples"""
        self._examples = examples
        return self

    def build(self) -> PropertyTest:
        """Build property test"""
        if self._predicate is None:
            raise ValueError("Predicate not set")
        return PropertyTest(
            name=self._name, predicate=self._predicate, examples=self._examples.copy()
        )
