"""Factory Boy factories for YAWL domain objects.

Chicago School TDD: Use these factories instead of mocking YCase, YWorkItem, etc.

Examples
--------
>>> from tests.factories.yawl import YCaseFactory, YWorkItemFactory
>>> case = YCaseFactory(id="case-001", specification_id="spec-order")
>>> work_item = YWorkItemFactory(id="wi-001", case_id=case.id)
"""

from __future__ import annotations

import factory_boy
from datetime import datetime

from kgcl.yawl.elements.y_specification import YSpecification
from kgcl.yawl.elements.y_task import YTask
from kgcl.yawl.engine.y_case import CaseStatus, YCase
from kgcl.yawl.engine.y_work_item import WorkItemStatus, YWorkItem


class YCaseFactory(factory_boy.Factory):
    """Factory for YCase domain objects.

    Chicago School TDD: Use this instead of MagicMock() for cases.

    Examples
    --------
    >>> case = YCaseFactory(id="case-001")
    >>> case.status
    <CaseStatus.CREATED: 1>
    >>> case.specification_id
    'spec-0'
    """

    class Meta:
        model = YCase

    id = factory_boy.Sequence(lambda n: f"case-{n:03d}")
    specification_id = factory_boy.Sequence(lambda n: f"spec-{n}")
    root_net_id = factory_boy.Sequence(lambda n: f"net-{n}")
    status = CaseStatus.CREATED
    created = factory_boy.LazyFunction(datetime.now)
    started = None
    completed = None


class YWorkItemFactory(factory_boy.Factory):
    """Factory for YWorkItem domain objects.

    Chicago School TDD: Use this instead of MagicMock() for work items.

    Examples
    --------
    >>> work_item = YWorkItemFactory(id="wi-001", case_id="case-123")
    >>> work_item.status
    <WorkItemStatus.ENABLED: 1>
    >>> work_item.case_id
    'case-123'
    """

    class Meta:
        model = YWorkItem

    id = factory_boy.Sequence(lambda n: f"wi-{n:03d}")
    case_id = factory_boy.Sequence(lambda n: f"case-{n}")
    task_id = factory_boy.Sequence(lambda n: f"task-{n}")
    specification_id = factory_boy.Sequence(lambda n: f"spec-{n}/v1.0")
    status = WorkItemStatus.ENABLED
    created = factory_boy.LazyFunction(datetime.now)


class YTaskFactory(factory_boy.Factory):
    """Factory for YTask domain objects.

    Chicago School TDD: Use this instead of MagicMock() for tasks.

    Examples
    --------
    >>> task = YTaskFactory(id="task-001", name="Process Order")
    >>> task.id
    'task-001'
    >>> task.name
    'Process Order'
    """

    class Meta:
        model = YTask

    id = factory_boy.Sequence(lambda n: f"task-{n:03d}")
    name = factory_boy.Sequence(lambda n: f"Task {n}")


class YSpecificationFactory(factory_boy.Factory):
    """Factory for YSpecification domain objects.

    Chicago School TDD: Use this instead of MagicMock() for specifications.

    Examples
    --------
    >>> spec = YSpecificationFactory(id="urn:spec:order-process")
    >>> spec.id
    'urn:spec:order-process'
    >>> spec.name
    'spec-0'
    """

    class Meta:
        model = YSpecification

    id = factory_boy.Sequence(lambda n: f"urn:spec:spec-{n}")
    name = factory_boy.Sequence(lambda n: f"spec-{n}")

