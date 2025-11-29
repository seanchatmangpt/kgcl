"""User-defined extended attributes for dynamic forms.

Manages design-time extended attributes that affect form display and behavior.
Provides type-safe accessors for boolean, string, and font attributes.

Converted from org.yawlfoundation.yawl.ui.dynform.DynFormUserAttributes
"""

from __future__ import annotations


class DynFormUserAttributes:
    """User-defined extended attributes for work items.

    Wraps a dictionary of attribute key-value pairs with type-safe accessors.
    Attributes are defined at design-time and control form rendering behavior.

    Standard Attributes
    -------------------
    - readOnly : bool - Field is read-only
    - hide : bool - Field is hidden
    - skipValidation : bool - Skip validation for this field
    - blackout : bool - Black out field value
    - mandatory : bool - Field is mandatory
    - optional : bool - Field is optional
    - hideIf : str - XPath/XQuery expression for conditional hiding
    - alert : str - Validation error message
    - label : str - Custom field label
    - tooltip : str - Custom tooltip text
    - textarea : bool - Use textarea instead of text field
    - justify : str - Text justification (left/center/right)
    - background-color : str - Background color
    - font-color : str - Font color
    - font-family : str - Font family
    - font-size : str - Font size
    - font-style : str - Font style (bold/italic)
    - image-above : str - Image URL to display above field
    - image-below : str - Image URL to display below field
    - line-above : bool - Display line above field
    - line-below : bool - Display line below field
    - text-above : str - Text to display above field
    - text-below : str - Text to display below field

    Examples
    --------
    >>> attrs = DynFormUserAttributes({"readOnly": "true", "label": "Username"})
    >>> attrs.is_read_only()
    True
    >>> attrs.get_label_text()
    'Username'
    """

    def __init__(self, attribute_map: dict[str, str] | None = None) -> None:
        """Initialize user attributes.

        Parameters
        ----------
        attribute_map : dict[str, str] | None
            Initial attribute key-value pairs
        """
        self._attribute_map: dict[str, str] = attribute_map or {}

    def set(self, attribute_map: dict[str, str]) -> None:
        """Set entire attribute map.

        Parameters
        ----------
        attribute_map : dict[str, str]
            New attribute key-value pairs
        """
        self._attribute_map = attribute_map

    def merge(self, merge_map: dict[str, str] | None) -> None:
        """Merge attributes from another map.

        Parameters
        ----------
        merge_map : dict[str, str] | None
            Attributes to merge (None is ignored)
        """
        if merge_map:
            self._attribute_map.update(merge_map)

    def get_value(self, attribute: str) -> str | None:
        """Get attribute value by name.

        Parameters
        ----------
        attribute : str
            Attribute name

        Returns
        -------
        str | None
            Attribute value, or None if not set
        """
        return self._attribute_map.get(attribute)

    def has_value(self, attribute: str) -> bool:
        """Check if attribute is set.

        Parameters
        ----------
        attribute : str
            Attribute name

        Returns
        -------
        bool
            True if attribute has a value
        """
        return self.get_value(attribute) is not None

    def get_boolean_value(self, attribute: str) -> bool:
        """Get boolean attribute value.

        Parameters
        ----------
        attribute : str
            Attribute name

        Returns
        -------
        bool
            True if value is "true" (case-insensitive), False otherwise
        """
        value = self.get_value(attribute)
        return value is not None and value.lower() == "true"

    def get_integer_value(self, attribute: str, default: int = -1) -> int:
        """Get integer attribute value.

        Parameters
        ----------
        attribute : str
            Attribute name
        default : int
            Default value if not set or invalid

        Returns
        -------
        int
            Integer value, or default if not set or invalid
        """
        value = self.get_value(attribute)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    # Standard boolean attributes

    def is_read_only(self) -> bool:
        """Check if field is read-only."""
        return self.get_boolean_value("readOnly")

    def is_hidden(self) -> bool:
        """Check if field is hidden."""
        return self.get_boolean_value("hide")

    def is_skip_validation(self) -> bool:
        """Check if validation should be skipped."""
        return self.get_boolean_value("skipValidation")

    def is_blackout(self) -> bool:
        """Check if field value should be blacked out."""
        return self.get_boolean_value("blackout")

    def is_mandatory(self) -> bool:
        """Check if field is mandatory."""
        return self.get_boolean_value("mandatory")

    def is_optional(self) -> bool:
        """Check if field is optional."""
        return self.get_boolean_value("optional")

    def is_text_area(self) -> bool:
        """Check if field should use textarea instead of text field."""
        return self.get_boolean_value("textarea")

    def is_line_above(self) -> bool:
        """Check if line should be displayed above field."""
        return self.get_boolean_value("line-above")

    def is_line_below(self) -> bool:
        """Check if line should be displayed below field."""
        return self.get_boolean_value("line-below")

    # Conditional hiding

    def has_hide_if_query(self) -> bool:
        """Check if hideIf query is defined."""
        return self.has_value("hideIf")

    def is_hide_if(self, data: str) -> bool:
        """Evaluate hideIf query against data.

        Parameters
        ----------
        data : str
            XML data to evaluate query against

        Returns
        -------
        bool
            True if hideIf query evaluates to "true"

        Notes
        -----
        Query evaluation requires Saxon XPath processor.
        Returns False if query fails to evaluate.
        """
        query = self.get_value("hideIf")
        if not query:
            return False

        try:
            from kgcl.yawl.util.misc.saxon_util import evaluate_query
            from kgcl.yawl.util.xml.jdom_util import string_to_document

            data_doc = string_to_document(data)
            if data_doc is None:
                return False
            data_elem = data_doc.getroot()
            query_result = evaluate_query(query, data_elem)
            return query_result.lower() == "true"
        except Exception:
        return False

    # String attributes

    def get_alert_text(self) -> str | None:
        """Get validation error alert text."""
        return self.get_value("alert")

    def get_label_text(self) -> str | None:
        """Get custom field label."""
        return self.get_value("label")

    def get_tool_tip_text(self) -> str | None:
        """Get custom tooltip text."""
        return self.get_value("tooltip")

    def get_text_justify(self) -> str | None:
        """Get text justification.

        Returns
        -------
        str | None
            One of "left", "center", "right", or None if invalid
        """
        justify = self.get_value("justify")
        if justify in ("left", "center", "right"):
            return justify
        return None

    def get_background_colour(self) -> str | None:
        """Get background color."""
        return self.get_value("background-color")

    def get_image_above(self) -> str | None:
        """Get image URL to display above field."""
        return self.get_value("image-above")

    def get_image_below(self) -> str | None:
        """Get image URL to display below field."""
        return self.get_value("image-below")

    def get_image_above_align(self) -> str | None:
        """Get alignment for image above field."""
        return self.get_value("image-above-align")

    def get_image_below_align(self) -> str | None:
        """Get alignment for image below field."""
        return self.get_value("image-below-align")

    def get_text_above(self) -> str | None:
        """Get text to display above field."""
        return self.get_value("text-above")

    def get_text_below(self) -> str | None:
        """Get text to display below field."""
        return self.get_value("text-below")

    def get_max_field_width(self) -> int:
        """Get maximum field width."""
        return self.get_integer_value("max-field-width")

    # Font attributes

    def get_user_defined_font_styles(self, header: bool = False) -> dict[str, str]:
        """Get user-defined font styles as CSS properties.

        Parameters
        ----------
        header : bool
            Get header font styles instead of field font styles

        Returns
        -------
        dict[str, str]
            CSS property-value pairs (e.g., {"color": "#ff0000", "font-size": "14px"})
        """
        styles: dict[str, str] = {}
        prefix = "header-" if header else ""

        # Font color
        font_color = self.get_value(f"{prefix}font-color")
        if font_color and not self.is_blackout():
            styles["color"] = font_color

        # Font family
        font_family = self.get_value(f"{prefix}font-family")
        if font_family:
            styles["font-family"] = font_family

        # Font size
        font_size = self.get_value(f"{prefix}font-size")
        if font_size:
            styles["font-size"] = font_size

        # Font style (bold/italic)
        font_style = self.get_value(f"{prefix}font-style")
        if font_style:
            if "bold" in font_style:
                styles["font-weight"] = "bold"
            if "italic" in font_style:
                styles["font-style"] = "italic"

        return styles

    def get_form_header_font_style(self) -> dict[str, str]:
        """Get form header font styles."""
        return self.get_user_defined_font_styles(header=True)

    def _has_font_attributes(self, header: bool = False) -> bool:
        """Check if any font attributes are defined.

        Parameters
        ----------
        header : bool
            Check header font attributes instead of field font attributes

        Returns
        -------
        bool
            True if any font attributes are set
        """
        prefix = "header-" if header else ""
        return (
            self.has_value(f"{prefix}font-family")
            or self.has_value(f"{prefix}font-size")
            or self.has_value(f"{prefix}font-style")
        )
