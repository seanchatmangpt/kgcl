"""Subpanel for grouped or repeating fields."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl_ui.dynform.dyn_form_field import DynFormField
    from kgcl.yawl_ui.dynform.sub_panel_controller import SubPanelController


class SubPanel:
    """Container for a group of related fields.

    Used for complex types or fields with minOccurs/maxOccurs.

    Attributes
    ----------
    _field : DynFormField
        Field definition
    _controller : SubPanelController | None
        Controller managing this panel
    _content : list[Any]
        Panel content (components)
    """

    def __init__(self, field: DynFormField, controller: SubPanelController | None = None) -> None:
        """Initialize subpanel.

        Parameters
        ----------
        field : DynFormField
            Field definition
        controller : SubPanelController | None
            Controller (for repeating fields)
        """
        self._field = field
        self._controller = controller
        self._content: list[Any] = []

        if controller:
            controller.add_panel(self)

    def add_content(self, components: list[Any] | Any) -> None:
        """Add components to panel.

        Parameters
        ----------
        components : list[Any] | Any
            Component or list of components
        """
        if isinstance(components, list):
            self._content.extend(components)
        else:
            self._content.append(components)

    def get_content(self) -> list[Any]:
        """Get panel content.

        Returns
        -------
        list[Any]
            Panel components
        """
        return self._content

    def get_controller(self) -> SubPanelController | None:
        """Get panel controller.

        Returns
        -------
        SubPanelController | None
            Controller managing this panel
        """
        return self._controller

    def get_field(self) -> DynFormField:
        """Get field definition.

        Returns
        -------
        DynFormField
            Associated field
        """
        return self._field
