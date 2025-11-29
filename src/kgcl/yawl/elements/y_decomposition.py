"""Decomposition base class (mirrors Java YDecomposition).

A decomposition represents what a task actually does - either a
net decomposition (subprocess) or a web service decomposition.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

# Import for runtime use (not just type checking)
from kgcl.yawl.elements.y_awl_service_reference import YAWLServiceReference
from kgcl.yawl.engine.y_engine import YVerificationHandler

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_specification import YSpecification


class DecompositionType(Enum):
    """Type of decomposition.

    Attributes
    ----------
    NET : auto
        Net decomposition (subprocess)
    WEB_SERVICE : auto
        Web service decomposition
    MANUAL : auto
        Manual task (human work)
    AUTOMATED : auto
        Automated task (system work)
    """

    NET = auto()
    WEB_SERVICE = auto()
    MANUAL = auto()
    AUTOMATED = auto()


@dataclass
class YParameter:
    """Parameter definition for decomposition I/O (mirrors Java YParameter).

    Parameters represent the input and output data elements of a decomposition.
    They define the interface through which data flows in and out of tasks.

    Parameters
    ----------
    name : str
        Parameter name (unique within decomposition)
    data_type : str
        Data type (e.g., "string", "integer", "boolean", "anyType")
    ordering : int
        Order in parameter list
    is_mandatory : bool
        Whether parameter is required
    initial_value : Any
        Default value if not provided
    documentation : str
        Optional documentation
    namespace : str
        XML namespace for complex types

    Examples
    --------
    >>> param = YParameter(name="customerId", data_type="string")
    >>> param.is_mandatory
    True
    """

    name: str
    data_type: str = "string"
    ordering: int = 0
    is_mandatory: bool = True
    initial_value: Any = None
    documentation: str = ""
    namespace: str = ""

    def __hash__(self) -> int:
        """Hash by name."""
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        """Equality by name."""
        if not isinstance(other, YParameter):
            return NotImplemented
        return self.name == other.name


@dataclass
class YVariable:
    """Variable for net-level data (mirrors Java YVariable).

    Variables hold data at the net level and can be local (internal)
    or mapped to inputs/outputs of the net.

    Parameters
    ----------
    name : str
        Variable name
    data_type : str
        Data type
    scope : str
        Scope: "local", "input", "output", or "inputOutput"
    initial_value : Any
        Initial value
    documentation : str
        Optional documentation
    namespace : str
        XML namespace for complex types

    Examples
    --------
    >>> var = YVariable(name="totalAmount", data_type="decimal", scope="local")
    """

    name: str
    data_type: str = "string"
    scope: str = "local"
    initial_value: Any = None
    documentation: str = ""
    namespace: str = ""

    # Additional fields for extended functionality (not in __init__)
    _attributes: dict[str, Any] = field(default_factory=dict, init=False)
    _element_name: str = field(default="", init=False)
    _ordering: int = field(default=0, init=False)
    _is_mandatory: bool = field(default=True, init=False)
    _is_optional: bool = field(default=False, init=False)
    _is_untyped: bool = field(default=False, init=False)
    _is_empty_typed: bool = field(default=False, init=False)
    _parent_decomposition: YDecomposition | None = field(default=None, init=False)
    _log_predicate: Any = field(default=None, init=False)

    def is_input(self) -> bool:
        """Check if variable is an input.

        Returns
        -------
        bool
            True if variable receives input data
        """
        return self.scope in ("input", "inputOutput")

    def is_output(self) -> bool:
        """Check if variable is an output.

        Returns
        -------
        bool
            True if variable produces output data
        """
        return self.scope in ("output", "inputOutput")

    def is_local(self) -> bool:
        """Check if variable is local only.

        Returns
        -------
        bool
            True if variable is local scope
        """
        return self.scope == "local"

    def __hash__(self) -> int:
        """Hash by name."""
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        """Equality by name."""
        if not isinstance(other, YVariable):
            return NotImplemented
        return self.name == other.name

    # ===== Java YAWL Methods =====

    def get_default_value(self) -> str:
        """Get default value for variable.

        Java signature: String getDefaultValue()

        Returns
        -------
        str
            Default value (initial_value as string), or empty string if None

        Notes
        -----
        Mirrors Java YAWL YVariable.getDefaultValue()
        """
        if self.initial_value is None:
            return ""
        return str(self.initial_value)

    def get_initial_value(self) -> str:
        """Get initial value as string.

        Java signature: String getInitialValue()

        Returns
        -------
        str
            Initial value as string, or empty string if None

        Notes
        -----
        Mirrors Java YAWL YVariable.getInitialValue()
        """
        if self.initial_value is None:
            return ""
        return str(self.initial_value)

    def set_initial_value(self, initial_value: str) -> None:
        """Set initial value.

        Java signature: void setInitialValue(String initialValue)

        Parameters
        ----------
        initial_value : str
            Initial value to set

        Notes
        -----
        Mirrors Java YAWL YVariable.setInitialValue()
        """
        self.initial_value = initial_value

    def set_default_value(self, value: str) -> None:
        """Set default value (alias for set_initial_value).

        Java signature: void setDefaultValue(String value)

        Parameters
        ----------
        value : str
            Default value to set

        Notes
        -----
        Mirrors Java YAWL YVariable.setDefaultValue()
        """
        self.initial_value = value

    def get_data_type_name(self) -> str:
        """Get data type name.

        Java signature: String getDataTypeName()

        Returns
        -------
        str
            Full data type name (with prefix if present)

        Notes
        -----
        Mirrors Java YAWL YVariable.getDataTypeName()
        """
        return self.data_type

    def get_data_type_name_unprefixed(self) -> str:
        """Get data type name without prefix.

        Java signature: String getDataTypeNameUnprefixed()

        Returns
        -------
        str
            Data type name with prefix removed

        Notes
        -----
        Mirrors Java YAWL YVariable.getDataTypeNameUnprefixed()
        If data type is "xs:string", returns "string"
        """
        if ":" in self.data_type:
            return self.data_type.split(":", 1)[1]
        return self.data_type

    def get_data_type_prefix(self) -> str:
        """Get data type namespace prefix.

        Java signature: String getDataTypePrefix()

        Returns
        -------
        str
            Namespace prefix (e.g., "xs" from "xs:string"), or empty string

        Notes
        -----
        Mirrors Java YAWL YVariable.getDataTypePrefix()
        """
        if ":" in self.data_type:
            return self.data_type.split(":", 1)[0]
        return ""

    def get_data_type_name_space(self) -> str:
        """Get data type namespace URI.

        Java signature: String getDataTypeNameSpace()

        Returns
        -------
        str
            Namespace URI

        Notes
        -----
        Mirrors Java YAWL YVariable.getDataTypeNameSpace()
        """
        return self.namespace

    def set_data_type_and_name(self, data_type: str, name: str, namespace_uri: str) -> None:
        """Set data type, name, and namespace together.

        Java signature: void setDataTypeAndName(String dataType, String name, String namespace)

        Parameters
        ----------
        data_type : str
            Data type to set
        name : str
            Variable name to set
        namespace_uri : str
            Namespace URI to set

        Notes
        -----
        Mirrors Java YAWL YVariable.setDataTypeAndName()
        """
        self.data_type = data_type
        self.name = name
        self.namespace = namespace_uri

    def is_empty_typed(self) -> bool:
        """Check if variable has type but no value.

        Java signature: boolean isEmptyTyped()

        Returns
        -------
        bool
            True if has data type but initial_value is None

        Notes
        -----
        Mirrors Java YAWL YVariable.isEmptyTyped()
        """
        return self._is_empty_typed or (self.data_type != "" and self.initial_value is None)

    def set_empty_typed(self, empty: bool) -> None:
        """Set empty typed flag.

        Java signature: void setEmptyTyped(boolean empty)

        Parameters
        ----------
        empty : bool
            Whether variable is empty typed

        Notes
        -----
        Mirrors Java YAWL YVariable.setEmptyTyped()
        """
        self._is_empty_typed = empty

    def is_untyped(self) -> bool:
        """Check if variable has no type.

        Java signature: boolean isUntyped()

        Returns
        -------
        bool
            True if data_type is empty or "anyType"

        Notes
        -----
        Mirrors Java YAWL YVariable.isUntyped()
        """
        return self._is_untyped or self.data_type in ("", "anyType")

    def set_untyped(self, is_untyped: bool) -> None:
        """Set untyped flag.

        Java signature: void setUntyped(boolean isUntyped)

        Parameters
        ----------
        is_untyped : bool
            Whether variable is untyped

        Notes
        -----
        Mirrors Java YAWL YVariable.setUntyped()
        """
        self._is_untyped = is_untyped

    def is_user_defined_type(self) -> bool:
        """Check if variable uses user-defined type.

        Java signature: boolean isUserDefinedType()

        Returns
        -------
        bool
            True if data type is not a standard XML Schema type

        Notes
        -----
        Mirrors Java YAWL YVariable.isUserDefinedType()
        Standard types: string, int, integer, boolean, decimal, double, float, etc.
        """
        standard_types = {
            "string",
            "int",
            "integer",
            "boolean",
            "decimal",
            "double",
            "float",
            "long",
            "short",
            "byte",
            "date",
            "dateTime",
            "time",
            "duration",
            "anyType",
        }
        unprefixed = self.get_data_type_name_unprefixed()
        return unprefixed not in standard_types and unprefixed != ""

    def get_name(self) -> str:
        """Get variable name.

        Java signature: String getName()

        Returns
        -------
        str
            Variable name

        Notes
        -----
        Mirrors Java YAWL YVariable.getName()
        """
        return self.name

    def set_name(self, name: str) -> None:
        """Set variable name.

        Java signature: void setName(String name)

        Parameters
        ----------
        name : str
            Variable name to set

        Notes
        -----
        Mirrors Java YAWL YVariable.setName()
        """
        self.name = name

    def get_element_name(self) -> str:
        """Get XML element name.

        Java signature: String getElementName()

        Returns
        -------
        str
            Element name (or variable name if not set)

        Notes
        -----
        Mirrors Java YAWL YVariable.getElementName()
        """
        return self._element_name or self.name

    def set_element_name(self, element_name: str) -> None:
        """Set XML element name.

        Java signature: void setElementName(String elementName)

        Parameters
        ----------
        element_name : str
            Element name to set

        Notes
        -----
        Mirrors Java YAWL YVariable.setElementName()
        """
        self._element_name = element_name

    def get_preferred_name(self) -> str:
        """Get preferred name (element name if set, otherwise variable name).

        Java signature: String getPreferredName()

        Returns
        -------
        str
            Preferred name for display

        Notes
        -----
        Mirrors Java YAWL YVariable.getPreferredName()
        """
        return self._element_name or self.name

    def get_documentation(self) -> str:
        """Get documentation string.

        Java signature: String getDocumentation()

        Returns
        -------
        str
            Documentation

        Notes
        -----
        Mirrors Java YAWL YVariable.getDocumentation()
        """
        return self.documentation

    def set_documentation(self, documentation: str) -> None:
        """Set documentation string.

        Java signature: void setDocumentation(String documentation)

        Parameters
        ----------
        documentation : str
            Documentation to set

        Notes
        -----
        Mirrors Java YAWL YVariable.setDocumentation()
        """
        self.documentation = documentation

    def get_ordering(self) -> int:
        """Get ordering value.

        Java signature: int getOrdering()

        Returns
        -------
        int
            Ordering value (for parameter order)

        Notes
        -----
        Mirrors Java YAWL YVariable.getOrdering()
        """
        return self._ordering

    def set_ordering(self, ordering: int) -> None:
        """Set ordering value.

        Java signature: void setOrdering(int ordering)

        Parameters
        ----------
        ordering : int
            Ordering value to set

        Notes
        -----
        Mirrors Java YAWL YVariable.setOrdering()
        """
        self._ordering = ordering

    def is_mandatory(self) -> bool:
        """Check if variable is mandatory.

        Java signature: boolean isMandatory()

        Returns
        -------
        bool
            True if variable must have a value

        Notes
        -----
        Mirrors Java YAWL YVariable.isMandatory()
        """
        return self._is_mandatory

    def set_mandatory(self, mandatory: bool) -> None:
        """Set mandatory flag.

        Java signature: void setMandatory(boolean mandatory)

        Parameters
        ----------
        mandatory : bool
            Whether variable is mandatory

        Notes
        -----
        Mirrors Java YAWL YVariable.setMandatory()
        """
        self._is_mandatory = mandatory

    def is_optional(self) -> bool:
        """Check if variable is optional.

        Java signature: boolean isOptional()

        Returns
        -------
        bool
            True if variable is optional

        Notes
        -----
        Mirrors Java YAWL YVariable.isOptional()
        """
        return self._is_optional

    def set_optional(self, option: bool) -> None:
        """Set optional flag.

        Java signature: void setOptional(boolean option)

        Parameters
        ----------
        option : bool
            Whether variable is optional

        Notes
        -----
        Mirrors Java YAWL YVariable.setOptional()
        """
        self._is_optional = option

    def is_required(self) -> bool:
        """Check if variable requires a value.

        Java signature: boolean isRequired()

        Returns
        -------
        bool
            True if variable is mandatory and not optional

        Notes
        -----
        Mirrors Java YAWL YVariable.isRequired()
        """
        return self._is_mandatory and not self._is_optional

    def requires_input_value(self) -> bool:
        """Check if variable requires input value.

        Java signature: boolean requiresInputValue()

        Returns
        -------
        bool
            True if input variable is required

        Notes
        -----
        Mirrors Java YAWL YVariable.requiresInputValue()
        Only input variables can require values
        """
        return self.is_input() and self.is_required()

    def get_parent_decomposition(self) -> YDecomposition | None:
        """Get parent decomposition.

        Java signature: YDecomposition getParentDecomposition()

        Returns
        -------
        YDecomposition | None
            Parent decomposition or None

        Notes
        -----
        Mirrors Java YAWL YVariable.getParentDecomposition()
        """
        return self._parent_decomposition

    def set_parent_decomposition(self, parent_decomposition: YDecomposition) -> None:
        """Set parent decomposition.

        Java signature: void setParentDecomposition(YDecomposition parentDecomposition)

        Parameters
        ----------
        parent_decomposition : YDecomposition
            Parent decomposition to set

        Notes
        -----
        Mirrors Java YAWL YVariable.setParentDecomposition()
        """
        self._parent_decomposition = parent_decomposition

    def get_attributes(self) -> YAttributeMap:
        """Get extended attributes.

        Java signature: YAttributeMap getAttributes()

        Returns
        -------
        YAttributeMap
            Extended attributes map

        Notes
        -----
        Mirrors Java YAWL YVariable.getAttributes()
        Returns YAttributeMap in both Java and Python
        """
        from kgcl.yawl.elements.y_attribute_map import YAttributeMap

        attr_map = YAttributeMap()
        attr_map.update(self._attributes)
        return attr_map

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        """Set extended attributes.

        Java signature: void setAttributes(Map attributes)

        Parameters
        ----------
        attributes : dict[str, Any]
            Attributes to set

        Notes
        -----
        Mirrors Java YAWL YVariable.setAttributes()
        """
        self._attributes = attributes

    def add_attribute(self, key: str, value: str | DynamicValue | Any) -> None:
        """Add extended attribute.

        Java signature: void addAttribute(String key, String value)
        Java signature: void addAttribute(String name, DynamicValue value)

        Parameters
        ----------
        key : str
            Attribute key
        value : str | DynamicValue | Any
            Attribute value (string or dynamic value)

        Notes
        -----
        Mirrors Java YAWL YVariable.addAttribute()
        Handles both String and DynamicValue overloads from Java
        """
        from kgcl.yawl.elements.y_attribute_map import DynamicValue

        # Convert DynamicValue to string for storage
        if isinstance(value, DynamicValue):
            self._attributes[key] = str(value)
        else:
            self._attributes[key] = value

    def has_attributes(self) -> bool:
        """Check if variable has extended attributes.

        Java signature: boolean hasAttributes()

        Returns
        -------
        bool
            True if attributes dictionary is not empty

        Notes
        -----
        Mirrors Java YAWL YVariable.hasAttributes()
        """
        return len(self._attributes) > 0

    def get_log_predicate(self) -> Any:
        """Get log predicate.

        Java signature: YLogPredicate getLogPredicate()

        Returns
        -------
        Any
            Log predicate object or None

        Notes
        -----
        Mirrors Java YAWL YVariable.getLogPredicate()
        Placeholder for YLogPredicate type
        """
        return self._log_predicate

    def set_log_predicate(self, predicate: Any) -> None:
        """Set log predicate.

        Java signature: void setLogPredicate(YLogPredicate predicate)

        Parameters
        ----------
        predicate : Any
            Log predicate to set

        Notes
        -----
        Mirrors Java YAWL YVariable.setLogPredicate()
        Placeholder for YLogPredicate type
        """
        self._log_predicate = predicate

    def compare_to(self, other: YVariable) -> int:
        """Compare to another variable by name.

        Java signature: int compareTo(YVariable other)

        Parameters
        ----------
        other : YVariable
            Variable to compare to

        Returns
        -------
        int
            -1 if self < other, 0 if equal, 1 if self > other

        Notes
        -----
        Mirrors Java YAWL YVariable.compareTo()
        Implements Comparable interface
        """
        if self.name < other.name:
            return -1
        if self.name > other.name:
            return 1
        return 0

    def to_string(self) -> str:
        """Get string representation.

        Java signature: String toString()

        Returns
        -------
        str
            String representation of variable

        Notes
        -----
        Mirrors Java YAWL YVariable.toString()
        """
        return f"YVariable(name={self.name}, type={self.data_type}, scope={self.scope})"

    def to_xml(self) -> str:
        """Convert to XML representation.

        Java signature: String toXML()

        Returns
        -------
        str
            XML string representation

        Notes
        -----
        Mirrors Java YAWL YVariable.toXML()
        Basic XML serialization
        """
        tag = self.get_element_name()
        attrs = f' type="{self.data_type}"' if self.data_type else ""
        if self.initial_value is not None:
            return f"<{tag}{attrs}>{self.initial_value}</{tag}>"
        return f"<{tag}{attrs} />"

    def to_xml_guts(self) -> str:
        """Get XML inner content (without outer tag).

        Java signature: String toXMLGuts()

        Returns
        -------
        str
            Inner XML content

        Notes
        -----
        Mirrors Java YAWL YVariable.toXMLGuts()
        """
        if self.initial_value is not None:
            return str(self.initial_value)
        return ""

    def uses_element_declaration(self) -> bool:
        """Check if variable uses element declaration.

        Java signature: boolean usesElementDeclaration()

        Returns
        -------
        bool
            True if element name is set

        Notes
        -----
        Mirrors Java YAWL YVariable.usesElementDeclaration()
        """
        return self._element_name != ""

    def uses_type_declaration(self) -> bool:
        """Check if variable uses type declaration.

        Java signature: boolean usesTypeDeclaration()

        Returns
        -------
        bool
            True if data type is set and not using element declaration

        Notes
        -----
        Mirrors Java YAWL YVariable.usesTypeDeclaration()
        """
        return self.data_type != "" and not self.uses_element_declaration()

    def is_valid_type_name_for_schema(self, data_type_name: str) -> bool:
        """Validate type name for schema.

        Java signature: boolean isValidTypeNameForSchema(String dataTypeName)

        Parameters
        ----------
        data_type_name : str
            Type name to validate

        Returns
        -------
        bool
            True if valid XML Schema type name

        Notes
        -----
        Mirrors Java YAWL YVariable.isValidTypeNameForSchema()
        Basic validation - checks if non-empty and valid identifier
        """
        if not data_type_name:
            return False
        # Basic identifier check: starts with letter, contains alphanumeric/underscore/colon
        if not data_type_name[0].isalpha():
            return False
        return all(c.isalnum() or c in ("_", ":", "-", ".") for c in data_type_name)

    def is_schema_version_at_least_2_1(self) -> bool:
        """Check if schema version is at least 2.1.

        Java signature: boolean isSchemaVersionAtLeast2_1()

        Returns
        -------
        bool
            True if schema version >= 2.1

        Notes
        -----
        Mirrors Java YAWL YVariable.isSchemaVersionAtLeast2_1()
        Python YAWL implementation assumes YAWL schema version 2.1+
        """
        # Python implementation assumes modern YAWL schema version >= 2.1
        return True

    def clone(self) -> YVariable:
        """Create a copy of this variable.

        Java signature: Object clone()

        Returns
        -------
        YVariable
            Deep copy of this variable

        Notes
        -----
        Mirrors Java YAWL YVariable.clone()
        """
        cloned = YVariable(
            name=self.name,
            data_type=self.data_type,
            scope=self.scope,
            initial_value=self.initial_value,
            documentation=self.documentation,
            namespace=self.namespace,
        )
        cloned._attributes = self._attributes.copy()
        cloned._element_name = self._element_name
        cloned._ordering = self._ordering
        cloned._is_mandatory = self._is_mandatory
        cloned._is_optional = self._is_optional
        cloned._is_untyped = self._is_untyped
        cloned._is_empty_typed = self._is_empty_typed
        cloned._parent_decomposition = self._parent_decomposition
        cloned._log_predicate = self._log_predicate
        return cloned

    def verify(self, handler: Any) -> None:
        """Verify variable validity.

        Java signature: void verify(YVerificationHandler handler)

        Parameters
        ----------
        handler : Any
            Verification handler to report errors (duck-typed for add_error/add_warning)

        Notes
        -----
        Mirrors Java YAWL YVariable.verify()
        Validates variable name and required value constraints
        """
        if not self.name:
            if handler and hasattr(handler, "add_error"):
                handler.add_error("Variable must have a name")

        if self.is_required() and self.initial_value is None:
            if handler and hasattr(handler, "add_warning"):
                handler.add_warning(f"Required variable {self.name} has no initial value")

    def check_value(self, value: str, label: str, handler: Any) -> None:
        """Check if value is valid for this variable's type.

        Java signature: void checkValue(String value, String label, YVerificationHandler handler)

        Parameters
        ----------
        value : str
            Value to check
        label : str
            Label for error reporting
        handler : Any
            Verification handler to report errors (duck-typed for add_error)

        Notes
        -----
        Mirrors Java YAWL YVariable.checkValue()
        Validates that required variables have non-empty values
        """
        if not value and self.is_required():
            if handler and hasattr(handler, "add_error"):
                handler.add_error(f"{label}: Required variable {self.name} has empty value")

    def check_data_type_value(self, value: Any) -> None:
        """Check if value matches data type.

        Java signature: void checkDataTypeValue(Element value)

        Parameters
        ----------
        value : Any
            Value to check (Element in Java, Any in Python)

        Notes
        -----
        Mirrors Java YAWL YVariable.checkDataTypeValue()
        Full XML Schema validation deferred to schema validation layer
        """
        # Full implementation deferred to XML Schema validation layer
        # This method is a hook for future schema validation integration
        pass


@dataclass
class YDecomposition(ABC):
    """Abstract base for decompositions (mirrors Java YDecomposition).

    A decomposition defines what a task actually does. This can be:
    - A net decomposition (subprocess with its own workflow)
    - A web service decomposition (external service call)
    - Manual work (human task)
    - Automated work (system task)

    Parameters
    ----------
    id : str
        Unique identifier
    name : str
        Human-readable name
    documentation : str
        Optional documentation
    decomposition_type : DecompositionType
        Type of decomposition
    input_parameters : dict[str, YParameter]
        Input parameters by name
    output_parameters : dict[str, YParameter]
        Output parameters by name
    specification_id : str | None
        ID of containing specification
    attributes : dict[str, Any]
        Extended attributes (key-value pairs)
    codelet : str | None
        Class name for automated tasks
    external_interaction : str
        Interaction mode: "manual", "automated", or "none"

    Notes
    -----
    In Java, YDecomposition has subclasses YNet (for net decompositions)
    and YAWLServiceGateway (for web service decompositions).
    """

    id: str
    name: str = ""
    documentation: str = ""
    decomposition_type: DecompositionType = DecompositionType.MANUAL

    # Parameters define the I/O interface
    input_parameters: dict[str, YParameter] = field(default_factory=dict)
    output_parameters: dict[str, YParameter] = field(default_factory=dict)

    # Parent specification
    specification_id: str | None = None

    # Extended attributes
    attributes: dict[str, Any] = field(default_factory=dict)

    # For automated tasks
    codelet: str | None = None

    # Interaction mode (Java YAWL defaults to manual)
    external_interaction: str = "manual"

    # Additional fields for extended functionality (not in __init__)
    _local_variables: dict[str, YVariable] = field(default_factory=dict, init=False)
    _output_expression: str = field(default="", init=False)
    _enablement_parameter: YParameter | None = field(default=None, init=False)
    _log_predicate: Any = field(default=None, init=False)
    _internal_data_document: Any = field(default=None, init=False)
    _specification: YSpecification | None = field(default=None, init=False)

    @abstractmethod
    def get_decomposition_category(self) -> str:
        """Get category of this decomposition.

        Returns
        -------
        str
            Category (e.g., "NetDecomposition", "WebServiceGateway")
        """

    def add_input_parameter(self, param: YParameter) -> None:
        """Add input parameter.

        Parameters
        ----------
        param : YParameter
            Parameter to add
        """
        self.input_parameters[param.name] = param

    def add_output_parameter(self, param: YParameter) -> None:
        """Add output parameter.

        Parameters
        ----------
        param : YParameter
            Parameter to add
        """
        self.output_parameters[param.name] = param

    def get_input_parameter(self, name: str) -> YParameter | None:
        """Get input parameter by name.

        Parameters
        ----------
        name : str
            Parameter name

        Returns
        -------
        YParameter | None
            Parameter or None if not found
        """
        return self.input_parameters.get(name)

    def get_output_parameter(self, name: str) -> YParameter | None:
        """Get output parameter by name.

        Parameters
        ----------
        name : str
            Parameter name

        Returns
        -------
        YParameter | None
            Parameter or None if not found
        """
        return self.output_parameters.get(name)

    def get_input_parameter_names(self) -> list[str]:
        """Get names of all input parameters.

        Returns
        -------
        list[str]
            Input parameter names in order
        """
        params = sorted(self.input_parameters.values(), key=lambda p: p.ordering)
        return [p.name for p in params]

    def get_output_parameter_names(self) -> list[str]:
        """Get names of all output parameters.

        Returns
        -------
        list[str]
            Output parameter names in order
        """
        params = sorted(self.output_parameters.values(), key=lambda p: p.ordering)
        return [p.name for p in params]

    def requires_resourcing(self) -> bool:
        """Check if decomposition requires human resources.

        Returns
        -------
        bool
            True if manual or external interaction required
        """
        return self.decomposition_type == DecompositionType.MANUAL or self.external_interaction == "manual"

    def is_automated(self) -> bool:
        """Check if decomposition is automated.

        Returns
        -------
        bool
            True if automated task
        """
        return self.decomposition_type == DecompositionType.AUTOMATED or self.external_interaction == "automated"

    def set_attribute(self, key: str, value: Any) -> None:
        """Set extended attribute.

        Parameters
        ----------
        key : str
            Attribute key
        value : Any
            Attribute value
        """
        self.attributes[key] = value

    def get_attribute(self, key: str) -> Any | None:
        """Get extended attribute.

        Parameters
        ----------
        key : str
            Attribute key

        Returns
        -------
        Any | None
            Attribute value or None
        """
        return self.attributes.get(key)

    def __hash__(self) -> int:
        """Hash by ID."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality by ID."""
        if not isinstance(other, YDecomposition):
            return NotImplemented
        return self.id == other.id

    # ===== Java YAWL Methods (from ydecomposition_missing_methods.py) =====

    def add_variable(self, variable: YVariable) -> None:
        """Add a local variable to this decomposition.

        Java signature: void addVariable(YVariable variable)

        Parameters
        ----------
        variable : YVariable
            Variable to add

        Notes
        -----
        Mirrors Java YAWL YDecomposition.addVariable()
        Variables are stored by name in the local variables dictionary
        """
        variable.set_parent_decomposition(self)
        self._local_variables[variable.name] = variable

    def remove_variable(self, name: str) -> YVariable | None:
        """Remove a local variable by name.

        Java signature: YVariable removeVariable(String name)

        Parameters
        ----------
        name : str
            Variable name to remove

        Returns
        -------
        YVariable | None
            Removed variable or None if not found

        Notes
        -----
        Mirrors Java YAWL YDecomposition.removeVariable()
        """
        return self._local_variables.pop(name, None)

    def get_variable(self, name: str) -> YVariable | None:
        """Get a local variable by name.

        Java signature: YVariable getVariable(String name)

        Parameters
        ----------
        name : str
            Variable name

        Returns
        -------
        YVariable | None
            Variable or None if not found

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getVariable()
        """
        return self._local_variables.get(name)

    def get_variables(self) -> dict[str, YVariable]:
        """Get all local variables.

        Java signature: Map getVariables()

        Returns
        -------
        dict[str, YVariable]
            Dictionary of all local variables by name

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getVariables()
        """
        return self._local_variables.copy()

    def set_variables(self, variables: dict[str, YVariable]) -> None:
        """Set local variables.

        Java signature: void setVariables(Map variables)

        Parameters
        ----------
        variables : dict[str, YVariable]
            Variables to set

        Notes
        -----
        Mirrors Java YAWL YDecomposition.setVariables()
        """
        self._local_variables = variables.copy()

    def get_id(self) -> str:
        """Get decomposition ID.

        Java signature: String getID()

        Returns
        -------
        str
            Decomposition ID

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getID()
        """
        return self.id

    def set_id(self, id_value: str) -> None:
        """Set decomposition ID.

        Java signature: void setID(String id)

        Parameters
        ----------
        id_value : str
            ID to set

        Notes
        -----
        Mirrors Java YAWL YDecomposition.setID()
        """
        self.id = id_value

    def get_name(self) -> str:
        """Get decomposition name.

        Java signature: String getName()

        Returns
        -------
        str
            Decomposition name

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getName()
        """
        return self.name

    def set_name(self, name: str) -> None:
        """Set decomposition name.

        Java signature: void setName(String name)

        Parameters
        ----------
        name : str
            Name to set

        Notes
        -----
        Mirrors Java YAWL YDecomposition.setName()
        """
        self.name = name

    def get_documentation(self) -> str:
        """Get documentation string.

        Java signature: String getDocumentation()

        Returns
        -------
        str
            Documentation

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getDocumentation()
        """
        return self.documentation

    def set_documentation(self, documentation: str) -> None:
        """Set documentation string.

        Java signature: void setDocumentation(String documentation)

        Parameters
        ----------
        documentation : str
            Documentation to set

        Notes
        -----
        Mirrors Java YAWL YDecomposition.setDocumentation()
        """
        self.documentation = documentation

    def get_codelet(self) -> str:
        """Get codelet class name.

        Java signature: String getCodelet()

        Returns
        -------
        str
            Codelet class name or empty string

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getCodelet()
        Codelets are Java classes that execute automated tasks
        """
        return self.codelet or ""

    def set_codelet(self, codelet: str) -> None:
        """Set codelet class name.

        Java signature: void setCodelet(String codelet)

        Parameters
        ----------
        codelet : str
            Codelet class name

        Notes
        -----
        Mirrors Java YAWL YDecomposition.setCodelet()
        """
        self.codelet = codelet

    def get_input_parameters(self) -> dict[str, YParameter]:
        """Get input parameters map.

        Java signature: Map getInputParameters()

        Returns
        -------
        dict[str, YParameter]
            Input parameters dictionary

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getInputParameters()
        """
        return self.input_parameters.copy()

    def get_output_parameters(self) -> dict[str, YParameter]:
        """Get output parameters map.

        Java signature: Map getOutputParameters()

        Returns
        -------
        dict[str, YParameter]
            Output parameters dictionary

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getOutputParameters()
        """
        return self.output_parameters.copy()

    def remove_input_parameter(self, param: YParameter | str) -> YParameter | None:
        """Remove input parameter.

        Java signature: YParameter removeInputParameter(String name)
        Java signature: YParameter removeInputParameter(YParameter parameter)

        Parameters
        ----------
        param : YParameter | str
            Parameter object or name to remove

        Returns
        -------
        YParameter | None
            Removed parameter or None if not found

        Notes
        -----
        Mirrors Java YAWL YDecomposition.removeInputParameter()
        Handles both overloads: by name and by parameter object
        """
        if isinstance(param, str):
            return self.input_parameters.pop(param, None)
        return self.input_parameters.pop(param.name, None)

    def remove_output_parameter(self, param: YParameter | str) -> YParameter | None:
        """Remove output parameter.

        Java signature: YParameter removeOutputParameter(String name)
        Java signature: YParameter removeOutputParameter(YParameter parameter)

        Parameters
        ----------
        param : YParameter | str
            Parameter object or name to remove

        Returns
        -------
        YParameter | None
            Removed parameter or None if not found

        Notes
        -----
        Mirrors Java YAWL YDecomposition.removeOutputParameter()
        Handles both overloads: by name and by parameter object
        """
        if isinstance(param, str):
            return self.output_parameters.pop(param, None)
        return self.output_parameters.pop(param.name, None)

    def get_specification(self) -> YSpecification | None:
        """Get parent specification.

        Java signature: YSpecification getSpecification()

        Returns
        -------
        YSpecification | None
            Parent specification or None

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getSpecification()
        """
        return self._specification

    def set_specification(self, specification: YSpecification) -> None:
        """Set parent specification.

        Java signature: void setSpecification(YSpecification specification)

        Parameters
        ----------
        specification : YSpecification
            Parent specification to set

        Notes
        -----
        Mirrors Java YAWL YDecomposition.setSpecification()
        """
        self._specification = specification

    def get_attributes(self) -> YAttributeMap:
        """Get extended attributes map.

        Java signature: YAttributeMap getAttributes()

        Returns
        -------
        YAttributeMap
            Attributes map

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getAttributes()
        """
        from kgcl.yawl.elements.y_attribute_map import YAttributeMap

        attr_map = YAttributeMap()
        attr_map.update(self.attributes)
        return attr_map

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        """Set extended attributes.

        Java signature: void setAttributes(Map attributes)

        Parameters
        ----------
        attributes : dict[str, Any]
            Attributes to set

        Notes
        -----
        Mirrors Java YAWL YDecomposition.setAttributes()
        """
        self.attributes = attributes.copy()

    def get_log_predicate(self) -> Any:
        """Get log predicate.

        Java signature: YLogPredicate getLogPredicate()

        Returns
        -------
        Any
            Log predicate object or None

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getLogPredicate()
        YLogPredicate type is placeholder for future implementation
        """
        return self._log_predicate

    def set_log_predicate(self, predicate: Any) -> None:
        """Set log predicate.

        Java signature: void setLogPredicate(YLogPredicate predicate)

        Parameters
        ----------
        predicate : Any
            Log predicate to set

        Notes
        -----
        Mirrors Java YAWL YDecomposition.setLogPredicate()
        """
        self._log_predicate = predicate

    def set_external_interaction(self, interaction: bool) -> None:
        """Set external interaction flag.

        Java signature: void setExternalInteraction(boolean interaction)

        Parameters
        ----------
        interaction : bool
            Whether decomposition requires external interaction

        Notes
        -----
        Mirrors Java YAWL YDecomposition.setExternalInteraction()
        Sets external_interaction to "manual" if True, "automated" if False
        """
        self.external_interaction = "manual" if interaction else "automated"

    def requires_resourcing_decisions(self) -> bool:
        """Check if decomposition requires resourcing decisions.

        Java signature: boolean requiresResourcingDecisions()

        Returns
        -------
        bool
            True if manual task requiring resource allocation

        Notes
        -----
        Mirrors Java YAWL YDecomposition.requiresResourcingDecisions()
        """
        return self.requires_resourcing()

    def get_output_expression(self) -> str:
        """Get output expression query.

        Java signature: String getOutputExpression()

        Returns
        -------
        str
            Output expression or empty string

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getOutputExpression()
        Output expressions are XQuery strings for data extraction
        """
        return self._output_expression

    def set_output_expression(self, query: str) -> None:
        """Set output expression query.

        Java signature: void setOutputExpression(String query)

        Parameters
        ----------
        query : str
            XQuery expression for output extraction

        Notes
        -----
        Mirrors Java YAWL YDecomposition.setOutputExpression()
        """
        self._output_expression = query

    def get_output_queries(self) -> set[str]:
        """Get all output query expressions.

        Java signature: Set getOutputQueries()

        Returns
        -------
        set[str]
            Set of output query expressions

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getOutputQueries()
        Returns set containing output expression if present
        """
        if self._output_expression:
            return {self._output_expression}
        return set()

    def set_enablement_parameter(self, parameter: YParameter) -> None:
        """Set enablement parameter.

        Java signature: void setEnablementParameter(YParameter parameter)

        Parameters
        ----------
        parameter : YParameter
            Enablement parameter (controls task enabling)

        Notes
        -----
        Mirrors Java YAWL YDecomposition.setEnablementParameter()
        """
        self._enablement_parameter = parameter

    def get_enablement_parameter(self) -> YParameter | None:
        """Get enablement parameter.

        Java signature: YParameter getEnablementParameter()

        Returns
        -------
        YParameter | None
            Enablement parameter or None

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getEnablementParameter()
        """
        return self._enablement_parameter

    def get_root_data_element_name(self) -> str:
        """Get root data element name.

        Java signature: String getRootDataElementName()

        Returns
        -------
        str
            Root element name (typically the net/decomposition ID)

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getRootDataElementName()
        """
        return self.id

    def get_variable_data_by_name(self, name: str) -> Any:
        """Get variable data element by name.

        Java signature: Element getVariableDataByName(String name)

        Parameters
        ----------
        name : str
            Variable name

        Returns
        -------
        Any
            Variable data element or None

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getVariableDataByName()
        Returns the YVariable object (Element in Java is XML DOM)
        """
        return self._local_variables.get(name)

    def get_internal_data_document(self) -> Any:
        """Get internal data document.

        Java signature: Document getInternalDataDocument()

        Returns
        -------
        Any
            Internal data document (XML Document in Java)

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getInternalDataDocument()
        Placeholder for XML Document representation
        """
        return self._internal_data_document

    def get_output_data(self) -> Any:
        """Get output data document.

        Java signature: Document getOutputData()

        Returns
        -------
        Any
            Output data document

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getOutputData()
        Placeholder for XML Document representation
        """
        # Return internal data document as output data
        return self._internal_data_document

    def get_net_data_document(self, net_data: str) -> Any:
        """Get net data as document.

        Java signature: Document getNetDataDocument(String netData)

        Parameters
        ----------
        net_data : str
            Net data as XML string

        Returns
        -------
        Any
            Parsed data document

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getNetDataDocument()
        Placeholder for XML parsing
        """
        # XML parsing handled by XML parser layer
        return net_data

    def get_state_space_bypass_params(self) -> dict[str, YParameter]:
        """Get state space bypass parameters.

        Java signature: Map getStateSpaceBypassParams()

        Returns
        -------
        dict[str, YParameter]
            Bypass parameters dictionary

        Notes
        -----
        Mirrors Java YAWL YDecomposition.getStateSpaceBypassParams()
        Used for state space analysis optimization
        """
        # Return empty dict - state space bypass is advanced feature
        return {}

    def param_map_to_xml(self, param_map: dict[str, YParameter]) -> str:
        """Convert parameter map to XML.

        Java signature: String paramMapToXML(Map paramMap)

        Parameters
        ----------
        param_map : dict[str, YParameter]
            Parameters to serialize

        Returns
        -------
        str
            XML representation of parameters

        Notes
        -----
        Mirrors Java YAWL YDecomposition.paramMapToXML()
        """
        xml_parts = ["<data>"]
        for name, param in param_map.items():
            xml_parts.append(f"  <{name} type='{param.data_type}' />")
        xml_parts.append("</data>")
        return "\n".join(xml_parts)

    def initialise(self, pmgr: Any = None) -> None:
        """Initialize decomposition data store.

        Java signature: void initialise()
        Java signature: void initialise(YPersistenceManager pmgr)

        Parameters
        ----------
        pmgr : Any, optional
            Persistence manager (for database persistence)

        Notes
        -----
        Mirrors Java YAWL YDecomposition.initialise()
        Handles both overloads with optional pmgr parameter
        """
        # Initialize internal data document if needed
        if self._internal_data_document is None:
            self._internal_data_document = {}

    def initialize_data_store(self, casedata: Any, pmgr: Any = None) -> None:
        """Initialize data store with case data.

        Java signature: void initializeDataStore(YNetData casedata)
        Java signature: void initializeDataStore(YPersistenceManager pmgr, YNetData casedata)

        Parameters
        ----------
        casedata : Any
            Case data (YNetData in Java)
        pmgr : Any, optional
            Persistence manager

        Notes
        -----
        Mirrors Java YAWL YDecomposition.initializeDataStore()
        Handles both overloads with optional pmgr parameter
        """
        # Initialize with case data
        self._internal_data_document = casedata

    def add_data(self, element: Any, pmgr: Any = None) -> None:
        """Add data element.

        Java signature: void addData(Element element)
        Java signature: void addData(YPersistenceManager pmgr, Element element)

        Parameters
        ----------
        element : Any
            Data element to add (XML Element in Java)
        pmgr : Any, optional
            Persistence manager

        Notes
        -----
        Mirrors Java YAWL YDecomposition.addData()
        Handles both overloads with optional pmgr parameter
        """
        # Add element to internal data document
        if self._internal_data_document is None:
            self._internal_data_document = {}
        if isinstance(self._internal_data_document, dict) and isinstance(element, dict):
            self._internal_data_document.update(element)

    def assign_data(self, variable: Any, pmgr: Any = None) -> None:
        """Assign data to variable.

        Java signature: void assignData(Element variable)
        Java signature: void assignData(YPersistenceManager pmgr, Element variable)

        Parameters
        ----------
        variable : Any
            Variable element with data (XML Element in Java)
        pmgr : Any, optional
            Persistence manager

        Notes
        -----
        Mirrors Java YAWL YDecomposition.assignData()
        Handles both overloads with optional pmgr parameter
        """
        # Assign variable data
        if isinstance(variable, dict):
            if self._internal_data_document is None:
                self._internal_data_document = {}
            if isinstance(self._internal_data_document, dict):
                self._internal_data_document.update(variable)

    def restore_data(self, casedata: Any) -> None:
        """Restore data from case data.

        Java signature: void restoreData(YNetData casedata)

        Parameters
        ----------
        casedata : Any
            Case data to restore from (YNetData in Java)

        Notes
        -----
        Mirrors Java YAWL YDecomposition.restoreData()
        """
        self._internal_data_document = casedata

    def verify(self, handler: Any) -> None:
        """Verify decomposition validity.

        Java signature: void verify(YVerificationHandler handler)

        Parameters
        ----------
        handler : Any
            Verification handler to report errors (duck-typed for add_error/add_warning)

        Notes
        -----
        Mirrors Java YAWL YDecomposition.verify()
        Validates decomposition structure and data
        """
        # Verify ID is set
        if not self.id:
            if handler and hasattr(handler, "add_error"):
                handler.add_error("Decomposition must have an ID")

        # Verify name is set
        if not self.name:
            if handler and hasattr(handler, "add_warning"):
                handler.add_warning(f"Decomposition {self.id} has no name")

        # Verify variables
        for var_name, var in self._local_variables.items():
            if hasattr(var, "verify"):
                var.verify(handler)

    def clone(self) -> YDecomposition:
        """Create a deep copy of this decomposition.

        Java signature: Object clone()

        Returns
        -------
        YDecomposition
            Deep copy of this decomposition

        Notes
        -----
        Mirrors Java YAWL YDecomposition.clone()
        Creates new instance with copied data
        """
        # Create new instance with same type
        cloned = type(self)(
            id=self.id, name=self.name, documentation=self.documentation, decomposition_type=self.decomposition_type
        )
        cloned.input_parameters = {k: v for k, v in self.input_parameters.items()}
        cloned.output_parameters = {k: v for k, v in self.output_parameters.items()}
        cloned.specification_id = self.specification_id
        cloned.attributes = self.attributes.copy()
        cloned.codelet = self.codelet
        cloned.external_interaction = self.external_interaction
        cloned._local_variables = {k: v.clone() for k, v in self._local_variables.items()}
        cloned._output_expression = self._output_expression
        cloned._enablement_parameter = self._enablement_parameter
        cloned._log_predicate = self._log_predicate
        cloned._internal_data_document = self._internal_data_document
        cloned._specification = self._specification
        return cloned

    def to_string(self) -> str:
        """Get string representation.

        Java signature: String toString()

        Returns
        -------
        str
            String representation of decomposition

        Notes
        -----
        Mirrors Java YAWL YDecomposition.toString()
        """
        return f"YDecomposition(id={self.id}, name={self.name}, type={self.decomposition_type.name})"

    def to_xml(self) -> str:
        """Convert to XML representation.

        Java signature: String toXML()

        Returns
        -------
        str
            XML string representation

        Notes
        -----
        Mirrors Java YAWL YDecomposition.toXML()
        Basic XML serialization
        """
        xml_parts = [f'<decomposition id="{self.id}" name="{self.name}">']

        # Input parameters
        if self.input_parameters:
            xml_parts.append("  <inputParameters>")
            for param in self.input_parameters.values():
                xml_parts.append(f'    <parameter name="{param.name}" type="{param.data_type}" />')
            xml_parts.append("  </inputParameters>")

        # Output parameters
        if self.output_parameters:
            xml_parts.append("  <outputParameters>")
            for param in self.output_parameters.values():
                xml_parts.append(f'    <parameter name="{param.name}" type="{param.data_type}" />')
            xml_parts.append("  </outputParameters>")

        # Local variables
        if self._local_variables:
            xml_parts.append("  <localVariables>")
            for var in self._local_variables.values():
                xml_parts.append(f'    <variable name="{var.name}" type="{var.data_type}" />')
            xml_parts.append("  </localVariables>")

        xml_parts.append("</decomposition>")
        return "\n".join(xml_parts)


@dataclass
class YWebServiceGateway(YDecomposition):
    """Web service decomposition (mirrors Java YAWLServiceGateway).

    A web service gateway contains a reference to a YAWL Service, which
    represents the service that will take responsibility for the execution
    of any task based on this gateway decomposition.

    Parameters
    ----------
    service_uri : str
        URI of the web service (legacy, use yawl_services instead)
    service_operation : str
        Operation to invoke (legacy)
    enable_worklist : bool
        Whether to show on worklist before invocation (legacy)
    yawl_services : dict[str, YAWLServiceReference]
        Map of YAWL service references by service ID
    enablement_parameters : dict[str, YParameter]
        Enablement parameters (deprecated since 2.0)

    Examples
    --------
    >>> from kgcl.yawl.elements.y_awl_service_reference import YAWLServiceReference
    >>> service = YAWLServiceReference(service_id="http://example.com/service")
    >>> gateway = YWebServiceGateway(id="gateway1")
    >>> gateway.set_yawl_service(service)
    """

    service_uri: str = ""  # Legacy
    service_operation: str = ""  # Legacy
    enable_worklist: bool = False  # Legacy
    yawl_services: dict[str, YAWLServiceReference] = field(default_factory=dict)
    enablement_parameters: dict[str, YParameter] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set decomposition type."""
        self.decomposition_type = DecompositionType.WEB_SERVICE

    def get_decomposition_category(self) -> str:
        """Get category as WebServiceGateway.

        Returns
        -------
        str
            "WebServiceGateway"
        """
        return "WebServiceGateway"

    def get_yawl_service(self, yawl_service_id: str | None = None) -> YAWLServiceReference | None:
        """Get YAWL service associated with this gateway.

        Parameters
        ----------
        yawl_service_id : str | None
            Service ID to get, or None for first service

        Returns
        -------
        YAWLServiceReference | None
            Service reference, or None if not found
        """
        if yawl_service_id:
            return self.yawl_services.get(yawl_service_id)
        # Return first service if any
        if self.yawl_services:
            return next(iter(self.yawl_services.values()))
        return None

    def set_yawl_service(self, yawl_service: YAWLServiceReference) -> None:
        """Set YAWL service associated with this gateway.

        Parameters
        ----------
        yawl_service : YAWLServiceReference
            Service to associate
        """
        if yawl_service:
            self.yawl_services[yawl_service.get_uri()] = yawl_service
            yawl_service.web_service_gateway = self

    def clear_yawl_service(self) -> None:
        """Clear any service associated with this gateway."""
        self.yawl_services.clear()

    def verify(self, handler: YVerificationHandler) -> None:
        """Verify this service gateway decomposition.

        Parameters
        ----------
        handler : YVerificationHandler
            Verification handler
        """
        super().verify(handler)
        for parameter in self.enablement_parameters.values():
            parameter.verify(handler)
        for yawl_service in self.yawl_services.values():
            yawl_service.verify(handler)
