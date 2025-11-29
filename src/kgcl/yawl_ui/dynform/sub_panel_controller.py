"""Controller for managing subpanel instances."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kgcl.yawl_ui.dynform.sub_panel import SubPanel


class SubPanelController:
    """Manages instances of a repeating field group.

    This controller handles add/remove operations for fields with minOccurs/maxOccurs.

    Attributes
    ----------
    _name : str
        Field group name
    _min_occurs : int
        Minimum instances required
    _max_occurs : int
        Maximum instances allowed
    _panels : list[SubPanel]
        Active panel instances
    """

    def __init__(self, name: str, min_occurs: int = 1, max_occurs: int = 1) -> None:
        """Initialize subpanel controller.

        Parameters
        ----------
        name : str
            Field group name
        min_occurs : int
            Minimum instances
        max_occurs : int
            Maximum instances
        """
        self._name = name
        self._min_occurs = min_occurs
        self._max_occurs = max_occurs
        self._panels: list[SubPanel] = []

    def add_panel(self, panel: SubPanel) -> None:
        """Add panel instance.

        Parameters
        ----------
        panel : SubPanel
            Panel to add
        """
        self._panels.append(panel)

    def get_panels(self) -> list[SubPanel]:
        """Get all panel instances.

        Returns
        -------
        list[SubPanel]
            Active panels
        """
        return self._panels

    def can_add(self) -> bool:
        """Check if more panels can be added.

        Returns
        -------
        bool
            True if under max_occurs limit
        """
        return len(self._panels) < self._max_occurs

    def can_remove(self) -> bool:
        """Check if panels can be removed.

        Returns
        -------
        bool
            True if above min_occurs requirement
        """
        return len(self._panels) > self._min_occurs
