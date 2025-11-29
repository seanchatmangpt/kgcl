"""Component builder for dynamic forms."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl_ui.dynform.dyn_form_factory import DynFormFactory
    from kgcl.yawl_ui.dynform.dyn_form_field import DynFormField
    from kgcl.yawl_ui.dynform.sub_panel import SubPanel
    from kgcl.yawl_ui.dynform.sub_panel_controller import SubPanelController


class DynFormComponentBuilder:
    """Builds UI components from field definitions.

    This class creates appropriate input components based on field types
    and maintains the component→field mapping.

    Attributes
    ----------
    _factory : DynFormFactory
        Parent factory reference
    _component_field_map : dict[Any, DynFormField]
        Maps components to their field definitions
    """

    def __init__(self, factory: DynFormFactory) -> None:
        """Initialize component builder.

        Parameters
        ----------
        factory : DynFormFactory
            Parent factory
        """
        self._factory = factory
        self._component_field_map: dict[Any, DynFormField] = {}

    def make_input_field(self, field: DynFormField) -> list[Any]:
        """Create input component for field.

        Parameters
        ----------
        field : DynFormField
            Field definition

        Returns
        -------
        list[Any]
            List containing the input component
        """
        # Create component based on datatype
        component = self._create_component_for_datatype(field)
        self._component_field_map[component] = field
        return [component]

    def make_peripheral_components(self, field: DynFormField, is_before: bool) -> list[Any]:
        """Create peripheral components (labels, images, lines).

        Parameters
        ----------
        field : DynFormField
            Field definition
        is_before : bool
            True for components before the field, False for after

        Returns
        -------
        list[Any]
            List of peripheral components
        """
        components: list[Any] = []

        if is_before:
            # Add label
            if field.get_name():
                label = {"type": "label", "text": field.get_name()}
                components.append(label)

            # Add image above
            if field.get_image_above():
                image = {"type": "image", "src": field.get_image_above()}
                components.append(image)
        # Add image below
        elif field.get_image_below():
            image = {"type": "image", "src": field.get_image_below()}
            components.append(image)

        return components

    def make_sub_panel(self, field: DynFormField, controller: SubPanelController | None) -> SubPanel:
        """Create subpanel for grouped field.

        Parameters
        ----------
        field : DynFormField
            Field definition
        controller : SubPanelController | None
            Controller for repeating fields

        Returns
        -------
        SubPanel
            Created subpanel
        """
        from kgcl.yawl_ui.dynform.sub_panel import SubPanel

        return SubPanel(field, controller)

    def get_component_field_map(self) -> dict[Any, DynFormField]:
        """Get component→field mapping.

        Returns
        -------
        dict[Any, DynFormField]
            Component to field map
        """
        return self._component_field_map

    def _create_component_for_datatype(self, field: DynFormField) -> Any:
        """Create component based on field datatype.

        Parameters
        ----------
        field : DynFormField
            Field definition

        Returns
        -------
        Any
            UI component
        """
        datatype = field.get_datatype()

        # Map XSD datatypes to component types
        if datatype in ("boolean", "xs:boolean"):
            return {"type": "checkbox", "name": field.get_name(), "value": field.get_value()}

        if datatype in ("date", "xs:date"):
            return {"type": "date", "name": field.get_name(), "value": field.get_value()}

        if datatype in ("int", "integer", "xs:int", "xs:integer", "long", "xs:long"):
            return {"type": "number", "name": field.get_name(), "value": field.get_value()}

        if datatype in ("decimal", "double", "float", "xs:decimal", "xs:double", "xs:float"):
            return {"type": "number", "name": field.get_name(), "value": field.get_value(), "step": "any"}

        # Check for enumeration (restricted values)
        if field.has_enumeration():
            return {
                "type": "select",
                "name": field.get_name(),
                "options": field.get_enumeration_values(),
                "value": field.get_value(),
            }

        # Check for multi-line text
        if field.is_text_area():
            return {"type": "textarea", "name": field.get_name(), "value": field.get_value()}

        # Default: text input
        return {"type": "text", "name": field.get_name(), "value": field.get_value()}
