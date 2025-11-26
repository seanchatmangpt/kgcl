"""Builder Pattern Support for Tests.

Provides fluent builder interfaces for constructing complex test objects.
"""

from collections.abc import Callable
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class Builder[T]:
    """Generic builder pattern for constructing test objects.

    Provides fluent interface for building complex objects in tests.

    Example:
        class PersonBuilder(Builder[Person]):
            def __init__(self):
                super().__init__()
                self._name = ""
                self._age = 0

            def with_name(self, name: str) -> "PersonBuilder":
                self._name = name
                return self

            def with_age(self, age: int) -> "PersonBuilder":
                self._age = age
                return self

            def build(self) -> Person:
                return Person(name=self._name, age=self._age)

        @test
        def test_person():
            person = (PersonBuilder()
                .with_name("Alice")
                .with_age(30)
                .build())
            assert person.name == "Alice"
    """

    def __init__(self) -> None:
        self._mutations: list[Callable[[Any], None]] = []
        self._validators: list[Callable[[Any], bool]] = []
        self._transformers: list[Callable[[Any], Any]] = []

    def add_mutation(self, mutation: Callable[[Any], None]) -> "Builder[T]":
        """Add a mutation function."""
        self._mutations.append(mutation)
        return self

    def add_validator(self, validator: Callable[[Any], bool]) -> "Builder[T]":
        """Add a validator function."""
        self._validators.append(validator)
        return self

    def add_transformer(self, transformer: Callable[[Any], Any]) -> "Builder[T]":
        """Add a transformer function."""
        self._transformers.append(transformer)
        return self

    def build(self) -> T:
        """Build the object (override in subclasses)."""
        raise NotImplementedError("Subclasses must implement build()")

    def mutate(self, obj: T) -> T:
        """Apply all mutations to object."""
        for mutation in self._mutations:
            mutation(obj)
        return obj

    def validate(self, obj: T) -> bool:
        """Validate object against all validators."""
        return all(validator(obj) for validator in self._validators)

    def transform(self, obj: T) -> T:
        """Apply all transformations to object."""
        result = obj
        for transformer in self._transformers:
            result = transformer(result)
        return result


class SimpleBuilder(Builder[T]):
    """Simple builder for basic object construction."""

    def __init__(self, factory: Callable[..., T], **kwargs: Any) -> None:
        super().__init__()
        self._factory = factory
        self._attributes: dict[str, Any] = kwargs

    def with_attr(self, key: str, value: Any) -> "SimpleBuilder[T]":
        """Set an attribute."""
        self._attributes[key] = value
        return self

    def with_attrs(self, attrs: dict[str, Any]) -> "SimpleBuilder[T]":
        """Set multiple attributes."""
        self._attributes.update(attrs)
        return self

    def build(self) -> T:
        """Build object using factory and attributes."""
        obj = self._factory(**self._attributes)
        obj = self.mutate(obj)
        if not self.validate(obj):
            raise ValueError("Object failed validation")
        return self.transform(obj)
