"""Factory Boy factories for domain objects.

Chicago School TDD requires real objects, not mocks.
These factories provide a proper way to create test data.

Usage
-----
>>> from tests.factories import HookFactory, HookReceiptFactory
>>> hook = HookFactory(name="test-hook")
>>> receipt = HookReceiptFactory(hook_id=hook.hook_id)
"""

from tests.factories.conditions import ConditionFactory, ConditionResultFactory
from tests.factories.hooks import HookFactory, HookReceiptFactory
from tests.factories.receipts import ChainAnchorFactory, ReceiptFactory
from tests.factories.yawl import (
    YCaseFactory,
    YSpecificationFactory,
    YTaskFactory,
    YWorkItemFactory,
)

__all__ = [
    # Hooks
    "HookFactory",
    "HookReceiptFactory",
    # Conditions
    "ConditionFactory",
    "ConditionResultFactory",
    # Receipts
    "ReceiptFactory",
    "ChainAnchorFactory",
    # YAWL
    "YCaseFactory",
    "YWorkItemFactory",
    "YTaskFactory",
    "YSpecificationFactory",
]


