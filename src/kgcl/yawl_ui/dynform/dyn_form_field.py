"""Dynamic form field definition.

Represents a field in a dynamically generated form, with metadata from XSD schema,
extended attributes, restrictions, and hierarchical structure (parent/children).

Converted from org.yawlfoundation.yawl.ui.dynform.DynFormField
"""

from __future__ import annotations

from copy import copy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl_ui.dynform.dyn_form_field_list_facet import DynFormFieldListFacet
    from kgcl.yawl_ui.dynform.dyn_form_field_restriction import DynFormFieldRestriction
    from kgcl.yawl_ui.dynform.dyn_form_field_union import DynFormFieldUnion

from kgcl.yawl_ui.dynform.dyn_form_user_attributes import DynFormUserAttributes


class DynFormField:
    """Dynamic form field with XSD schema metadata and extended attributes.

    Represents a single field in a YAWL dynamic form, including:
    - Basic metadata (name, datatype, value)
    - Occurrence constraints (min/max occurs)
    - Hierarchical structure (parent/subfields)
    - Extended attributes (labels, tooltips, validation rules)
    - Restrictions (enumerations, patterns, ranges)
    - Unions and list types

    Attributes
    ----------
    _name : str
        Parameter name
    _datatype : str
        XSD datatype
    _value : str | None
        Current value
    _minoccurs : int
        Minimum occurrences (0 = optional)
    _maxoccurs : int
        Maximum occurrences (sys.maxsize = unbounded)
    _param : Any
        Form parameter definition
    _occurs_count : int
        Current occurrence count
    _level : int
        Nesting level in field hierarchy
    _order : int
        Display order
    _required : bool
        Whether field is required
    _hidden : bool
        Whether field is hidden
    _empty_complex_type_flag : bool
        Empty complex type marker
    _hide_applied : bool | None
        Cached hide evaluation result
    _parent : DynFormField | None
        Parent field (for hierarchical structures)
    _restriction : DynFormFieldRestriction | None
        Datatype restrictions
    _union : DynFormFieldUnion | None
        Union type definition
    _list : DynFormFieldListFacet | None
        List type definition
    _attributes : DynFormUserAttributes
        Extended attributes
    _sub_field_list : list[DynFormField] | None
        Child fields (for complex types)
    _group_id : str | None
        Group identifier (for min/max occurs > 1)
    _choice_id : str | None
        Choice identifier (for XSD choice constructs)
    """

    def __init__(
        self,
        name: str | None = None,
        datatype: str | None = None,
        value: str | None = None,
        sub_field_list: list[DynFormField] | None = None,
    ) -> None:
        """Initialize dynamic form field.

        Parameters
        ----------
        name : str | None
            Field name
        datatype : str | None
            XSD datatype
        value : str | None
            Initial value
        sub_field_list : list[DynFormField] | None
            Subfields (for complex types)
        """
        self._name = name
        self._datatype = datatype
        self._value = value
        self._minoccurs: int = 1
        self._maxoccurs: int = 1
        self._null_minoccurs: bool = True
        self._null_maxoccurs: bool = True
        self._param: Any = None
        self._occurs_count: int = 1
        self._level: int = 0
        self._order: int = 0
        self._required: bool = False
        self._hidden: bool = False
        self._empty_complex_type_flag: bool = False
        self._hide_applied: bool | None = None
        self._parent: DynFormField | None = None
        self._restriction: DynFormFieldRestriction | None = None
        self._union: DynFormFieldUnion | None = None
        self._list: DynFormFieldListFacet | None = None
        self._attributes = DynFormUserAttributes()
        self._sub_field_list = sub_field_list
        self._group_id: str | None = None
        self._choice_id: str | None = None

        # Set parent for all subfields
        if sub_field_list:
            for field in sub_field_list:
                field.set_parent(self)

    def clone(self) -> DynFormField:
        """Create shallow copy of field.

        Returns
        -------
        DynFormField
            Cloned field
        """
        return copy(self)

    # Name

    def get_name(self) -> str | None:
        """Get field name."""
        return self._name

    def set_name(self, name: str) -> None:
        """Set field name."""
        self._name = name

    # Datatype

    def get_datatype(self) -> str:
        """Get datatype name.

        Returns datatype from field or from parameter definition.
        """
        return self._datatype if self._datatype else self._param.get_data_type_name()

    def set_datatype(self, datatype: str) -> None:
        """Set datatype name."""
        self._datatype = datatype

    def get_data_type_unprefixed(self) -> str:
        """Get datatype without namespace prefix.

        Returns
        -------
        str
            Datatype with prefix removed (e.g., "string" instead of "xsd:string")
        """
        datatype = self.get_datatype()
        if datatype and ":" in datatype:
            return datatype.split(":", 1)[1]
        return datatype

    # Value

    def get_value(self) -> str | None:
        """Get current value."""
        return self._value

    def set_value(self, value: str) -> None:
        """Set current value."""
        self._value = value

    def has_null_value(self) -> bool:
        """Check if value is null.

        Returns
        -------
        bool
            True if value is None and datatype is not string
        """
        datatype = self.get_data_type_unprefixed()
        return self._value is None and datatype is not None and datatype != "string"

    # Occurrences

    def get_minoccurs(self) -> int:
        """Get minimum occurrences."""
        return self._minoccurs

    def set_minoccurs(self, minoccurs: str | None) -> None:
        """Set minimum occurrences.

        Parameters
        ----------
        minoccurs : str | None
            Minimum as string ("0", "1", etc.) or None
        """
        self._null_minoccurs = minoccurs is None
        self._minoccurs = self._convert_occurs(minoccurs)

    def get_maxoccurs(self) -> int:
        """Get maximum occurrences."""
        return self._maxoccurs

    def set_maxoccurs(self, maxoccurs: str | None) -> None:
        """Set maximum occurrences.

        Parameters
        ----------
        maxoccurs : str | None
            Maximum as string ("1", "unbounded", etc.) or None
        """
        self._null_maxoccurs = maxoccurs is None
        self._maxoccurs = self._convert_occurs(maxoccurs)

    def set_occurs_count(self, occurs_count: int) -> None:
        """Set current occurrence count."""
        self._occurs_count = occurs_count

    def has_zero_minimum(self) -> bool:
        """Check if minimum occurrences is zero.

        Returns
        -------
        bool
            True if this field or any parent has minoccurs = 0
        """
        if self.has_parent() and self._parent is not None:
            return self._parent.has_zero_minimum() or self._minoccurs == 0
        return self._minoccurs == 0

    def _convert_occurs(self, occurs: str | None) -> int:
        """Convert occurs string to integer.

        Parameters
        ----------
        occurs : str | None
            Occurrence string ("0", "1", "unbounded", etc.)

        Returns
        -------
        int
            Integer occurrence count (sys.maxsize for "unbounded")
        """
        if occurs is None:
            return 1
        if occurs == "unbounded":
            return 2**31 - 1  # Java's Integer.MAX_VALUE
        try:
            return int(occurs)
        except ValueError:
            return 1

    # Param

    def get_param(self) -> Any:
        """Get form parameter definition."""
        return self._param

    def set_param(self, param: Any) -> None:
        """Set form parameter definition."""
        self._param = param

    # Level and Order

    def get_level(self) -> int:
        """Get nesting level."""
        return self._level

    def set_level(self, level: int) -> None:
        """Set nesting level."""
        self._level = level

    def get_order(self) -> int:
        """Get display order."""
        return self._order

    def set_order(self, order: int) -> None:
        """Set display order."""
        self._order = order

    # Required

    def is_required(self) -> bool:
        """Check if field is required.

        Returns
        -------
        bool
            True if field is required for form submission
        """
        self._required = (
            not (self.is_input_only() or self.has_zero_minimum() or self._attributes.is_optional())
        ) or self._attributes.is_mandatory()
        return self._required

    def set_required(self, required: bool) -> None:
        """Set required flag."""
        self._required = required

    # Hidden

    def set_empty_complex_type_flag(self, flag: bool) -> None:
        """Set empty complex type flag."""
        self._empty_complex_type_flag = flag

    def is_empty_complex_type_flag(self) -> bool:
        """Check if field is empty complex type."""
        return self._empty_complex_type_flag

    # Parent

    def get_parent(self) -> DynFormField | None:
        """Get parent field."""
        return self._parent

    def set_parent(self, parent: DynFormField) -> None:
        """Set parent field."""
        self._parent = parent

    def has_parent(self) -> bool:
        """Check if field has parent."""
        return self._parent is not None

    # Enumeration

    def get_enumerated_values(self) -> list[str] | None:
        """Get enumeration values from restrictions or union.

        Returns
        -------
        list[str] | None
            List of allowed values, or None if not enumerated
        """
        values: list[str] | None = None
        if self._union and self._union.has_enumeration():
            values = self._union.get_enumeration()
        elif self._restriction and self._restriction.has_enumeration():
            values = self._restriction.get_enumeration()

        if values and not self.is_required():
            # Add optional default value for UI
            placeholder = " " if self.is_input_only() else "<-- Choose (optional) -->"
            values.insert(0, placeholder)

        return values

    def has_enumerated_values(self) -> bool:
        """Check if field has enumeration values."""
        return (self._union is not None and self._union.has_enumeration()) or (
            self._restriction is not None and self._restriction.has_enumeration()
        )

    # Subfields

    def get_sub_field_list(self) -> list[DynFormField] | None:
        """Get list of subfields."""
        return self._sub_field_list

    def get_sub_field(self, name: str) -> DynFormField | None:
        """Get subfield by name.

        Parameters
        ----------
        name : str
            Subfield name

        Returns
        -------
        DynFormField | None
            Subfield, or None if not found
        """
        if self._sub_field_list:
            for field in self._sub_field_list:
                if field.get_name() == name:
                    return field
        return None

    def add_sub_field(self, field: DynFormField) -> None:
        """Add subfield.

        Parameters
        ----------
        field : DynFormField
            Subfield to add
        """
        if self._sub_field_list is None:
            self._sub_field_list = []
        field.set_parent(self)
        self._sub_field_list.append(field)

    def add_sub_field_list(self, field_list: list[DynFormField] | None) -> None:
        """Add multiple subfields.

        Parameters
        ----------
        field_list : list[DynFormField] | None
            Subfields to add
        """
        if field_list:
            for field in field_list:
                self.add_sub_field(field)

    def is_field_container(self) -> bool:
        """Check if field contains subfields.

        Returns
        -------
        bool
            True if field is complex type or YDocument
        """
        return not (self.is_simple_field() or self.is_y_document())

    def is_simple_field(self) -> bool:
        """Check if field is simple type (no subfields)."""
        return self._sub_field_list is None

    # Group and Choice IDs

    def get_group_id(self) -> str | None:
        """Get group identifier."""
        return self._group_id

    def set_group_id(self, group_id: str) -> None:
        """Set group identifier."""
        self._group_id = group_id

    def get_choice_id(self) -> str | None:
        """Get choice identifier."""
        return self._choice_id

    def set_choice_id(self, choice_id: str) -> None:
        """Set choice identifier."""
        self._choice_id = choice_id

    def is_choice_field(self) -> bool:
        """Check if field is part of XSD choice."""
        return self._choice_id is not None

    def is_grouped_field(self) -> bool:
        """Check if field is grouped (min/max occurs > 1)."""
        return not (self.get_group_id() is None or self.is_y_document())

    # Restrictions and Unions

    def get_restriction(self) -> DynFormFieldRestriction | None:
        """Get datatype restriction."""
        return self._restriction

    def set_restriction(self, restriction: DynFormFieldRestriction) -> None:
        """Set datatype restriction."""
        self._restriction = restriction
        restriction.set_owner(self)

    def has_restriction(self) -> bool:
        """Check if field has restriction."""
        return self._restriction is not None

    def get_union(self) -> DynFormFieldUnion | None:
        """Get union type definition."""
        return self._union

    def set_union(self, union: DynFormFieldUnion) -> None:
        """Set union type definition."""
        self._union = union
        union.set_owner(self)

    def has_union(self) -> bool:
        """Check if field has union type."""
        return self._union is not None

    def set_list_type(self, list_facet: DynFormFieldListFacet) -> None:
        """Set list type definition."""
        self._list = list_facet
        list_facet.set_owner(self)

    def has_list_type(self) -> bool:
        """Check if field has list type."""
        return self._list is not None

    # Attributes

    def get_attributes(self) -> DynFormUserAttributes:
        """Get extended attributes."""
        return self._attributes

    def set_attributes(self, attributes: DynFormUserAttributes) -> None:
        """Set extended attributes."""
        self._attributes = attributes

    # Extended Attribute Accessors

    def get_alert_text(self) -> str | None:
        """Get validation error alert text."""
        if self.has_parent() and self._parent is not None:
            return self._parent.get_alert_text()
        return self._attributes.get_alert_text()

    def get_label(self) -> str:
        """Get field label.

        Returns
        -------
        str
            Custom label or field name if no label defined
        """
        label = self._attributes.get_label_text()
        return label if label else self._name

    def is_input_only(self) -> bool:
        """Check if field is read-only/input-only.

        Returns
        -------
        bool
            True if field is read-only
        """
        if self.has_parent() and self._parent is not None and self._parent.is_input_only():
            return True
        if self._param is not None and (self._param.is_input_only() or self._param.is_read_only()):
            return True
        return self._attributes.is_read_only() or self.has_blackout_attribute()

    def has_hide_attribute(self) -> bool:
        """Check if field has hide attribute."""
        if self.has_parent() and self._parent is not None and self._parent.has_hide_attribute():
            return True
        return self._hidden or self._attributes.is_hidden()

    def has_hide_if_attribute(self, data: str) -> bool:
        """Check if hideIf query evaluates to true.

        Parameters
        ----------
        data : str
            XML data for query evaluation

        Returns
        -------
        bool
            True if hideIf condition is met
        """
        if self.has_parent() and self._parent is not None:
            return self._parent.has_hide_if_attribute(data) or self._attributes.is_hide_if(data)
        return self._attributes.is_hide_if(data)

    def is_hidden(self, data: str | None) -> bool:
        """Check if field should be hidden.

        Parameters
        ----------
        data : str | None
            XML data for hideIf evaluation

        Returns
        -------
        bool
            True if field should be hidden
        """
        if data is None:
            return False
        if self._hide_applied is None:
            self._hide_applied = self.has_hide_attribute() or self.has_hide_if_attribute(data)
        return self._hide_applied

    def is_empty_optional_input_only(self) -> bool:
        """Check if field is empty optional input-only.

        Returns
        -------
        bool
            True if field is input-only, optional, and has null value
        """
        return self.is_input_only() and self._attributes.is_optional() and self.has_null_value()

    def get_tool_tip(self) -> str:
        """Get tooltip text.

        Returns
        -------
        str
            Custom tooltip or default based on datatype
        """
        tip = self._attributes.get_tool_tip_text()
        return tip if tip else self.get_default_tool_tip()

    def get_default_tool_tip(self) -> str:
        """Get default tooltip based on datatype and restrictions.

        Returns
        -------
        str
            Generated tooltip text
        """
        if self.has_blackout_attribute():
            return " This field is intentionally blacked-out "

        datatype_name = self._param.get_data_type_name() if self._param else ""
        datatype = "Duration or DateTime" if datatype_name == "YTimerType" else self.get_data_type_unprefixed()
        tip = f" Please enter a value of {datatype} type"

        if self.has_restriction() and self._restriction is not None:
            tip += self._restriction.get_tool_tip_extn()
        elif self.has_list_type() and self._list is not None:
            tip = f" Please enter {self._list.get_tool_tip_extn()}"

        return tip + " "

    def has_skip_validation_attribute(self) -> bool:
        """Check if validation should be skipped."""
        if self.has_parent() and self._parent is not None:
            return self._parent.has_skip_validation_attribute() or self._attributes.is_skip_validation()
        return self._attributes.is_skip_validation()

    def get_text_justify(self) -> str | None:
        """Get text justification."""
        if self.has_parent() and self._parent is not None:
            return self._parent.get_text_justify()
        return self._attributes.get_text_justify()

    def has_blackout_attribute(self) -> bool:
        """Check if field has blackout attribute."""
        if self.has_parent() and self._parent is not None:
            return self._parent.has_blackout_attribute() or self._attributes.is_blackout()
        return self._attributes.is_blackout()

    def get_user_defined_font_style(self) -> dict[str, str]:
        """Get user-defined font styles."""
        if self.has_parent() and self._parent is not None:
            return self._parent.get_user_defined_font_style()
        return self._attributes.get_user_defined_font_styles()

    def get_background_colour(self) -> str | None:
        """Get background color."""
        if self.has_parent() and self._parent is not None:
            return self._parent.get_background_colour()
        return self._attributes.get_background_colour()

    def is_text_area(self) -> bool:
        """Check if field should use textarea."""
        return self._attributes.is_text_area()

    def is_y_document(self) -> bool:
        """Check if field is YDocument type."""
        return self.get_data_type_unprefixed() == "YDocumentType"

    def get_image_above(self) -> str | None:
        """Get image URL to display above field."""
        return self._attributes.get_image_above()

    def get_image_below(self) -> str | None:
        """Get image URL to display below field."""
        return self._attributes.get_image_below()

    def get_image_above_align(self) -> str | None:
        """Get alignment for image above field."""
        return self._attributes.get_image_above_align()

    def get_image_below_align(self) -> str | None:
        """Get alignment for image below field."""
        return self._attributes.get_image_below_align()

    def is_line_above(self) -> bool:
        """Check if line should be displayed above field."""
        return self._attributes.is_line_above()

    def is_line_below(self) -> bool:
        """Check if line should be displayed below field."""
        return self._attributes.is_line_below()

    def get_text_above(self) -> str | None:
        """Get text to display above field."""
        return self._attributes.get_text_above()

    def get_text_below(self) -> str | None:
        """Get text to display below field."""
        return self._attributes.get_text_below()

    def set_restriction_attributes(self) -> None:
        """Set restriction facets from extended attributes.

        For built-in XSD types, reads restriction facets from attributes
        and applies them to the field's restriction object.
        """
        # Set restriction facets from extended attributes for built-in XSD types
        datatype_unprefixed = self.get_data_type_unprefixed()
        built_in_types = {
            "string",
            "boolean",
            "integer",
            "int",
            "long",
            "short",
            "byte",
            "decimal",
            "float",
            "double",
            "dateTime",
            "date",
            "time",
            "duration",
        }
        if datatype_unprefixed in built_in_types and self._restriction is not None:
            restriction = self._get_or_create_restriction()
            facet_names = [
                "minExclusive",
                "maxExclusive",
                "minInclusive",
                "maxInclusive",
                "minLength",
                "maxLength",
                "length",
                "totalDigits",
                "fractionDigits",
                "whiteSpace",
                "pattern",
            ]
            for facet_name in facet_names:
                value = self._attributes.get_value(facet_name)
                if value is not None and hasattr(restriction, f"set_{facet_name.lower()}"):
                    getattr(restriction, f"set_{facet_name.lower()}")(value)

    def _get_or_create_restriction(self) -> DynFormFieldRestriction:
        """Get existing restriction or create new one.

        Returns
        -------
        DynFormFieldRestriction
            Restriction object
        """
        if not self.has_restriction():
            # Import here to avoid circular dependency
            from kgcl.yawl_ui.dynform.dyn_form_field_restriction import DynFormFieldRestriction

            self._restriction = DynFormFieldRestriction(self)
            self._restriction.set_base_type(self.get_datatype())

        if self._restriction is not None:
            self._restriction.set_modified_flag()
        return self._restriction

    def equals(self, other: DynFormField) -> bool:
        """Check equality with another field.

        Parameters
        ----------
        other : DynFormField
            Field to compare

        Returns
        -------
        bool
            True if name and datatype match
        """
        return other.get_name() == self.get_name() and other.get_datatype() == self.get_datatype()
