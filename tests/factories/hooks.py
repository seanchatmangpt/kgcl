"""Factory Boy factories for hook domain objects.

Chicago School TDD: Use these factories instead of mocking Hook, HookReceipt.

Examples
--------
>>> from tests.factories.hooks import HookFactory, HookReceiptFactory
>>> hook = HookFactory(name="validate-person", phase=HookPhase.ON_CHANGE)
>>> receipt = HookReceiptFactory(hook_id=hook.hook_id, condition_matched=True)
"""

from __future__ import annotations

from datetime import UTC, datetime

import factory_boy

from kgcl.hybrid.knowledge_hooks import HookAction, HookPhase, HookReceipt, KnowledgeHook


class HookFactory(factory_boy.Factory):
    """Factory for KnowledgeHook domain objects.

    Chicago School TDD: Use this instead of MagicMock() for hooks.

    Examples
    --------
    >>> hook = HookFactory(name="test-hook")
    >>> hook.name
    'test-hook'
    >>> hook.enabled
    True
    """

    class Meta:
        model = KnowledgeHook

    hook_id = factory_boy.Sequence(lambda n: f"urn:hook:hook-{n}")
    name = factory_boy.Sequence(lambda n: f"hook-{n}")
    phase = HookPhase.ON_CHANGE
    priority = 50
    enabled = True
    condition_query = "ASK { ?s a <https://kgc.org/ns/Person> }"
    action = HookAction.NOTIFY
    handler_data = factory_boy.Dict({"message": "Hook triggered"})


class HookReceiptFactory(factory_boy.Factory):
    """Factory for HookReceipt domain objects.

    Chicago School TDD: Use this instead of MagicMock() for receipts.

    Examples
    --------
    >>> receipt = HookReceiptFactory(hook_id="urn:hook:test", condition_matched=True)
    >>> receipt.condition_matched
    True
    >>> receipt.action_taken
    <HookAction.NOTIFY: 'notify'>
    """

    class Meta:
        model = HookReceipt

    hook_id = factory_boy.Sequence(lambda n: f"urn:hook:hook-{n}")
    phase = HookPhase.ON_CHANGE
    timestamp = factory_boy.LazyFunction(lambda: datetime.now(UTC))
    condition_matched = True
    action_taken = HookAction.NOTIFY
    duration_ms = 1.5
    error = None
    triples_affected = 0
    metadata = factory_boy.Dict({})
