"""Decomposition base class (mirrors Java YDecomposition).

A decomposition represents what a task actually does - either a
net decomposition (subprocess) or a web service decomposition.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

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

    # Interaction mode
    external_interaction: str = "none"

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


@dataclass
class YWebServiceGateway(YDecomposition):
    """Web service decomposition (mirrors Java YAWLServiceGateway).

    Represents a task that invokes an external web service.

    Parameters
    ----------
    service_uri : str
        URI of the web service
    service_operation : str
        Operation to invoke
    enable_worklist : bool
        Whether to show on worklist before invocation

    Examples
    --------
    >>> gateway = YWebServiceGateway(
    ...     id="paymentService", service_uri="http://payment.example.com/api", service_operation="processPayment"
    ... )
    """

    service_uri: str = ""
    service_operation: str = ""
    enable_worklist: bool = False

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
