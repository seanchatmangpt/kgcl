"""Factory Boy factories for condition domain objects.

Chicago School TDD: Use these factories instead of mocking Condition, ConditionResult.

Examples
--------
>>> from tests.factories.conditions import ConditionFactory, ConditionResultFactory
>>> cond = ConditionFactory(kind=ConditionKind.THRESHOLD, expression="x > 5")
>>> result = ConditionResultFactory(matched=True, duration_ms=2.0)
"""

from __future__ import annotations

import factory_boy

from kgcl.hybrid.hooks.condition_evaluator import (
    Condition,
    ConditionKind,
    ConditionResult,
)


class ConditionFactory(factory_boy.Factory):
    """Factory for Condition domain objects.

    Chicago School TDD: Use this instead of MagicMock() for conditions.

    Examples
    --------
    >>> cond = ConditionFactory(kind=ConditionKind.SPARQL_ASK)
    >>> cond.kind
    <ConditionKind.SPARQL_ASK: 'sparql-ask'>
    >>> cond.expression
    'ASK { ?s a <https://kgc.org/ns/Person> }'
    """

    class Meta:
        model = Condition

    kind = ConditionKind.SPARQL_ASK
    expression = "ASK { ?s a <https://kgc.org/ns/Person> }"
    parameters = factory_boy.Dict({})


class ConditionResultFactory(factory_boy.Factory):
    """Factory for ConditionResult domain objects.

    Chicago School TDD: Use this instead of MagicMock() for condition results.

    Examples
    --------
    >>> result = ConditionResultFactory(matched=True)
    >>> result.matched
    True
    >>> result.duration_ms
    1.5
    """

    class Meta:
        model = ConditionResult

    matched = True
    bindings = factory_boy.Dict({})
    duration_ms = 1.5
    metadata = factory_boy.Dict({})

