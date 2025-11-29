"""YAWL task data models.

Ported from org.yawlfoundation.yawl.ui.service.PiledTask
"""

from dataclasses import dataclass

from kgcl.yawl_ui.models.case import SpecificationID


@dataclass(frozen=True)
class PiledTask:
    """Represents a task in a work pile.

    A piled task is a task that has been allocated to a user's work queue
    but not yet started. It tracks both the specification and task identifiers.

    Parameters
    ----------
    spec_id : SpecificationID
        Specification identifier containing this task
    task_id : str
        Task identifier

    Examples
    --------
    >>> spec = SpecificationID("OrderProcess", "1.0")
    >>> task = PiledTask(spec, "ApproveOrder")
    >>> str(task)
    'OrderProcess v.1.0 :: ApproveOrder'
    """

    spec_id: SpecificationID
    task_id: str

    def __str__(self) -> str:
        """Return string representation.

        Returns
        -------
        str
            Formatted string: "{uri} v.{version} :: {task_id}"
        """
        return f"{self.spec_id.uri} v.{self.spec_id.get_version_as_string()} :: {self.task_id}"
