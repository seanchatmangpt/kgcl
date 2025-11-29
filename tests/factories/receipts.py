"""Factory Boy factories for receipt domain objects.

Chicago School TDD: Use these factories instead of mocking Receipt, ChainAnchor.

Examples
--------
>>> from tests.factories.receipts import ReceiptFactory, ChainAnchorFactory
>>> receipt = ReceiptFactory(hook_id="urn:hook:test", condition_result=True)
>>> anchor = ChainAnchorFactory(chain_height=0)
"""

from __future__ import annotations

from datetime import UTC, datetime

import factory_boy
from vendors.src.kgcl.hooks.receipts import ChainAnchor, Receipt


class ChainAnchorFactory(factory_boy.Factory):
    """Factory for ChainAnchor domain objects.

    Chicago School TDD: Use this instead of MagicMock() for chain anchors.

    Examples
    --------
    >>> anchor = ChainAnchorFactory(chain_height=0)
    >>> anchor.is_genesis()
    True
    """

    class Meta:
        model = ChainAnchor

    previous_receipt_hash = ""
    chain_height = 0
    timestamp = factory_boy.LazyFunction(lambda: datetime.now(UTC))


class ReceiptFactory(factory_boy.Factory):
    """Factory for Receipt domain objects.

    Chicago School TDD: Use this instead of MagicMock() for receipts.

    Examples
    --------
    >>> receipt = ReceiptFactory(hook_id="urn:hook:test")
    >>> receipt.condition_result
    True
    >>> receipt.chain_anchor
    None
    """

    class Meta:
        model = Receipt

    execution_id = factory_boy.Sequence(lambda n: f"exec-{n}")
    hook_id = factory_boy.Sequence(lambda n: f"urn:hook:hook-{n}")
    condition_result = True
    effect_result = True
    timestamp = factory_boy.LazyFunction(lambda: datetime.now(UTC))
    metadata = factory_boy.Dict({})
    chain_anchor = None
