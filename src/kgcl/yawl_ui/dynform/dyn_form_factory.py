"""Dynamic form factory for generating YAWL work item forms.

This module is responsible for generating dynamic forms from XSD schemas.
Converted from org.yawlfoundation.yawl.ui.dynform.DynFormFactory
"""

from __future__ import annotations

from typing import Any

from kgcl.yawl_ui.dynform.data_list_generator import DataListGenerator
from kgcl.yawl_ui.dynform.dyn_form_component_builder import DynFormComponentBuilder
from kgcl.yawl_ui.dynform.dyn_form_field import DynFormField
from kgcl.yawl_ui.dynform.dyn_form_field_assembler import DynFormFieldAssembler
from kgcl.yawl_ui.dynform.dyn_form_layout import DynFormLayout
from kgcl.yawl_ui.dynform.dyn_form_user_attributes import DynFormUserAttributes
from kgcl.yawl_ui.dynform.dyn_form_validator import DynFormValidator
from kgcl.yawl_ui.dynform.sub_panel_controller import SubPanelController


class DynFormFactory:
    """Factory for generating dynamic forms from XSD schemas.

    This class builds forms to capture work item output data or case start input data.
    Forms are generated from XSD schemas with SHACL constraints.

    Attributes
    ----------
    _sub_panel_table : dict[str, SubPanelController]
        Map of subpanel IDs to their controllers
    _component_field_table : dict[Any, DynFormField]
        Map of UI components to their field definitions
    _user_attributes : DynFormUserAttributes
        Decomposition-level extended attributes
    _field_assembler : DynFormFieldAssembler
        Assembles form fields from schema
    _wir : Any | None
        Current work item record
    _container : DynFormLayout | None
        Top-level form container
    """

    def __init__(self) -> None:
        """Initialize dynamic form factory."""
        self._sub_panel_table: dict[str, SubPanelController] = {}
        self._component_field_table: dict[Any, DynFormField] = {}
        self._user_attributes = DynFormUserAttributes()
        self._field_assembler: DynFormFieldAssembler | None = None
        self._wir: Any | None = None
        self._container: DynFormLayout | None = None

    def create_form_for_workitem(self, schema: str, wir: Any, participant: Any) -> DynFormLayout:
        """Build form to capture work item output data from user.

        Parameters
        ----------
        schema : str
            XSD schema of data types and attributes to display
        wir : Any
            Work item record
        participant : Any
            Participant performing the work

        Returns
        -------
        DynFormLayout
            Generated form layout

        Raises
        ------
        Exception
            If form generation fails
        """
        self._wir = wir
        self._user_attributes.set(wir.get_attribute_table())
        data = self._get_workitem_data(wir)
        param_info = self._get_param_info(wir)
        return self._build_form(schema, data, param_info, participant)

    def create_form_for_case(self, schema: str, parameters: list[Any], participant: Any) -> DynFormLayout:
        """Build form to capture case start input data from user.

        Parameters
        ----------
        schema : str
            XSD schema of data types and attributes
        parameters : list[Any]
            Root net's input parameters
        participant : Any
            Participant starting the case

        Returns
        -------
        DynFormLayout
            Generated form layout
        """
        param_map = self._get_case_param_map(parameters)
        return self._build_form(schema, None, param_map, participant)

    def get_data_list(self) -> str:
        """Get form's data as well-formed XML.

        Returns data list with opening and closing tag matching the task name
        or root net name.

        Returns
        -------
        str
            Well-formed XML string of form's data values

        Raises
        ------
        ValueError
            If container or field assembler not initialized
        """
        if not self._container or not self._field_assembler:
            msg = "Form not initialized - call create_form first"
            raise ValueError(msg)

        generator = DataListGenerator(self)
        return generator.generate(self._container, self._field_assembler.get_field_list())

    def get_doc_component_ids(self) -> list[int]:
        """Get IDs of all document components in form.

        Returns
        -------
        list[int]
            List of document component IDs
        """
        if not self._container:
            return []

        ids: list[int] = []
        # Filter children for DocComponent instances
        for child in self._container.get_children():
            if hasattr(child, "get_id"):
                ids.append(child.get_id())
        return ids

    def validate(self) -> bool:
        """Validate form inputs.

        Returns
        -------
        bool
            True if all validations pass, False otherwise
        """
        if not self._container or not self._component_field_table:
            return False

        validator = DynFormValidator()
        return validator.validate(self._container, self._component_field_table)

    def get_default_form_name(self) -> str:
        """Get default form name.

        Returns
        -------
        str
            Form name from field assembler
        """
        if not self._field_assembler:
            return ""
        return self._field_assembler.get_form_name()

    def get_field_for_component(self, component: Any) -> DynFormField | None:
        """Get field definition for a UI component.

        Parameters
        ----------
        component : Any
            UI component

        Returns
        -------
        DynFormField | None
            Field definition, or None if not found
        """
        if component is None:
            return None
        return self._component_field_table.get(component)

    def get_user_attributes(self) -> DynFormUserAttributes:
        """Get decomposition-level extended attributes.

        Returns
        -------
        DynFormUserAttributes
            User-defined attributes
        """
        return self._user_attributes

    def _build_form(self, schema: str, data: str | None, param_map: dict[str, Any], participant: Any) -> DynFormLayout:
        """Build form from schema and data.

        Parameters
        ----------
        schema : str
            XSD schema
        data : str | None
            Existing data (for work items)
        param_map : dict[str, Any]
            Parameter definitions
        participant : Any
            Current participant

        Returns
        -------
        DynFormLayout
            Complete form layout
        """
        self._field_assembler = DynFormFieldAssembler(schema, data, param_map)
        self._build_form_internal(participant)
        return self._container  # type: ignore

    def _build_form_internal(self, participant: Any) -> None:
        """Internal form building logic.

        Parameters
        ----------
        participant : Any
            Current participant
        """
        builder = DynFormComponentBuilder(self)
        field_list = self._field_assembler.get_field_list()  # type: ignore

        # First pass: adjust fields with dynamic attributes
        # DynAttributeFactory.adjustFields(fieldList, _wir, participant)

        # Create container
        self._container = DynFormLayout(self.get_default_form_name())

        # Build inner form
        component_list = self._build_inner_form(builder, field_list)
        self._container.add(component_list)

        # Set form background color
        self._set_form_background_color()

        # Second pass: apply dynamic attributes to completed form
        # DynAttributeFactory.applyAttributes(_container, _wir, participant)

        # Store component-field mappings
        self._component_field_table = builder.get_component_field_map()

    def _build_inner_form(self, builder: DynFormComponentBuilder, field_list: list[DynFormField]) -> Any:
        """Build inner form components from field list.

        Parameters
        ----------
        builder : DynFormComponentBuilder
            Component builder
        field_list : list[DynFormField]
            Form field definitions

        Returns
        -------
        Any
            Component list
        """
        component_list = []

        if not field_list:
            return component_list

        for field in field_list:
            if field.is_field_container():
                # Complex type - recurse with subpanel
                component_list.extend(self._build_sub_panel(builder, field))
            elif not field.is_empty_optional_input_only():
                # Create field (possibly in subpanel if min/max defined)
                if field.is_grouped_field():
                    component_list.extend(self._build_sub_panel(builder, field))
                else:
                    component_list.extend(builder.make_input_field(field))

        # Consolidate choice components
        # componentList.consolidateChoiceComponents(fieldList)

        return component_list

    def _build_sub_panel(self, builder: DynFormComponentBuilder, field: DynFormField) -> list[Any]:
        """Build subpanel for field.

        Parameters
        ----------
        builder : DynFormComponentBuilder
            Component builder
        field : DynFormField
            Field requiring subpanel

        Returns
        -------
        list[Any]
            List of components
        """
        comp_list = builder.make_peripheral_components(field, True)

        # Get or create subpanel controller
        spc = self._sub_panel_table.get(field.get_group_id())
        sub_panel = builder.make_sub_panel(field, spc)
        self._sub_panel_table[field.get_group_id()] = sub_panel.get_controller()

        # Build inner content
        if field.is_field_container():
            inner_content = self._build_inner_form(builder, field.get_sub_field_list())
        else:
            inner_content = builder.make_input_field(field)
            field.add_sub_field(field.clone())

        sub_panel.add_content(inner_content)
        comp_list.append(sub_panel)
        comp_list.extend(builder.make_peripheral_components(field, False))

        return comp_list

    def _get_param_info(self, wir: Any) -> dict[str, Any]:
        """Get parameter info for work item.

        Parameters
        ----------
        wir : Any
            Work item record

        Returns
        -------
        dict[str, Any]
            Parameter map
        """
        # TODO: Implement via Clients.getEngineClient().getTaskInformation(wir)
        return {}

    def _get_case_param_map(self, param_list: list[Any]) -> dict[str, Any]:
        """Get parameter map for case.

        Parameters
        ----------
        param_list : list[Any]
            Parameter list

        Returns
        -------
        dict[str, Any]
            Parameter map
        """
        # TODO: Implement ParameterMap().toMap(paramList)
        return {}

    def _get_workitem_data(self, wir: Any) -> str | None:
        """Get work item data as XML.

        Parameters
        ----------
        wir : Any
            Work item record

        Returns
        -------
        str | None
            XML data string, or None
        """
        if wir is None:
            return None

        # Get updated data or original data
        data = wir.get_updated_data() if hasattr(wir, "get_updated_data") else wir.get_data_list()

        # Convert to XML string
        # return JDOMUtil.elementToStringDump(data)
        return str(data) if data else None

    def _set_form_background_color(self) -> None:
        """Set form background color from user attributes."""
        if not self._container:
            return

        bg_color = self._get_panel_background_color()
        if bg_color:
            # self._container.getStyle().set("background-color", bgColor)
            pass

    def _get_panel_background_color(self) -> str | None:
        """Get panel background color from attributes.

        Returns
        -------
        str | None
            Color string or None
        """
        return self._user_attributes.get_value("background-color")
