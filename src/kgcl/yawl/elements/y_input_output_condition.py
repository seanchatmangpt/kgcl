"""Input and output conditions (mirrors Java YInputCondition, YOutputCondition).

These are specialized conditions for the unique start and end places
of a YAWL workflow net.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kgcl.yawl.elements.y_condition import ConditionType, YCondition


@dataclass
class YInputCondition(YCondition):
    """Input condition - unique start place (mirrors Java YInputCondition).

    Every YAWL net has exactly one input condition, which is the
    initial place where execution begins. A token is placed here
    when a case starts.

    Parameters
    ----------
    id : str
        Unique identifier
    name : str
        Human-readable name
    documentation : str
        Optional documentation

    Notes
    -----
    Input conditions cannot have preset flows (nothing leads to them)
    as they are the entry point of the net.

    Examples
    --------
    >>> start = YInputCondition(id="start", name="Process Start")
    >>> start.is_input_condition()
    True
    >>> start.can_have_preset()
    False
    """

    documentation: str = ""

    def __post_init__(self) -> None:
        """Set condition type to INPUT."""
        self.condition_type = ConditionType.INPUT

    def can_have_preset(self) -> bool:
        """Input conditions cannot have preset flows.

        Returns
        -------
        bool
            Always False
        """
        return False

    def get_element_type(self) -> str:
        """Get element type.

        Returns
        -------
        str
            "inputCondition"
        """
        return "inputCondition"

    def validate(self) -> tuple[bool, list[str]]:
        """Validate input condition structure.

        Returns
        -------
        tuple[bool, list[str]]
            (is_valid, list of error messages)
        """
        errors = []

        if len(self.preset_flows) > 0:
            errors.append(f"Input condition '{self.id}' has preset flows (should have none)")

        if len(self.postset_flows) == 0:
            errors.append(f"Input condition '{self.id}' has no postset flows (should have at least one)")

        return len(errors) == 0, errors


@dataclass
class YOutputCondition(YCondition):
    """Output condition - unique end place (mirrors Java YOutputCondition).

    Every YAWL net has exactly one output condition, which is the
    final place where execution ends. When a token reaches here,
    the case (or sub-case) is complete.

    Parameters
    ----------
    id : str
        Unique identifier
    name : str
        Human-readable name
    documentation : str
        Optional documentation

    Notes
    -----
    Output conditions cannot have postset flows (nothing leads from them)
    as they are the exit point of the net.

    Examples
    --------
    >>> end = YOutputCondition(id="end", name="Process Complete")
    >>> end.is_output_condition()
    True
    >>> end.can_have_postset()
    False
    """

    documentation: str = ""

    def __post_init__(self) -> None:
        """Set condition type to OUTPUT."""
        self.condition_type = ConditionType.OUTPUT

    def can_have_postset(self) -> bool:
        """Output conditions cannot have postset flows.

        Returns
        -------
        bool
            Always False
        """
        return False

    def get_element_type(self) -> str:
        """Get element type.

        Returns
        -------
        str
            "outputCondition"
        """
        return "outputCondition"

    def validate(self) -> tuple[bool, list[str]]:
        """Validate output condition structure.

        Returns
        -------
        tuple[bool, list[str]]
            (is_valid, list of error messages)
        """
        errors = []

        if len(self.postset_flows) > 0:
            errors.append(f"Output condition '{self.id}' has postset flows (should have none)")

        if len(self.preset_flows) == 0:
            errors.append(f"Output condition '{self.id}' has no preset flows (should have at least one)")

        return len(errors) == 0, errors


@dataclass
class YImplicitCondition(YCondition):
    """Implicit condition between directly connected tasks.

    When tasks are directly connected (without an explicit condition),
    an implicit condition is created. This maintains the Petri net
    semantics while allowing simplified workflow notation.

    Parameters
    ----------
    id : str
        Auto-generated identifier
    source_task_id : str
        ID of source task
    target_task_id : str
        ID of target task

    Examples
    --------
    >>> implicit = YImplicitCondition(id="c_A_B", source_task_id="A", target_task_id="B")
    >>> implicit.is_implicit()
    True
    """

    source_task_id: str = ""
    target_task_id: str = ""

    def __post_init__(self) -> None:
        """Set condition type to IMPLICIT."""
        self.condition_type = ConditionType.IMPLICIT

    def get_element_type(self) -> str:
        """Get element type.

        Returns
        -------
        str
            "implicitCondition"
        """
        return "implicitCondition"

    @staticmethod
    def create_between(source_task_id: str, target_task_id: str) -> YImplicitCondition:
        """Create implicit condition between two tasks.

        Parameters
        ----------
        source_task_id : str
            ID of source task
        target_task_id : str
            ID of target task

        Returns
        -------
        YImplicitCondition
            New implicit condition

        Examples
        --------
        >>> cond = YImplicitCondition.create_between("A", "B")
        >>> cond.id
        'c_A_B'
        """
        return YImplicitCondition(
            id=f"c_{source_task_id}_{target_task_id}", source_task_id=source_task_id, target_task_id=target_task_id
        )
