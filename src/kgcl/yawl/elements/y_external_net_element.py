"""Base class for external net elements (mirrors Java YExternalNetElement).

YExternalNetElement is the abstract base for conditions and tasks -
the elements that are externally visible in a workflow net.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_net import YNet


@dataclass
class YExternalNetElement(ABC):
    """Abstract base for conditions and tasks (mirrors Java YExternalNetElement).

    This is the base class for all elements that appear in the visible
    structure of a YAWL net - conditions (places) and tasks (transitions).
    It provides common attributes and methods for net elements.

    Parameters
    ----------
    id : str
        Unique identifier within the net
    name : str
        Human-readable name
    documentation : str
        Optional documentation/description
    net_id : str | None
        ID of containing net (set when added)
    preset_flows : list[str]
        IDs of incoming flows
    postset_flows : list[str]
        IDs of outgoing flows

    Notes
    -----
    In the Java implementation, this extends YNetElement which extends
    YVerifiable. We flatten this hierarchy for Python simplicity.
    """

    id: str
    name: str = ""
    documentation: str = ""
    net_id: str | None = None

    # Flow connections
    preset_flows: list[str] = field(default_factory=list)
    postset_flows: list[str] = field(default_factory=list)

    @abstractmethod
    def get_element_type(self) -> str:
        """Get the type of this element.

        Returns
        -------
        str
            Element type (e.g., "condition", "task", "inputCondition")
        """

    def get_display_name(self) -> str:
        """Get display name (name if set, else ID).

        Returns
        -------
        str
            Name or ID for display
        """
        return self.name if self.name else self.id

    def has_preset(self) -> bool:
        """Check if element has any incoming flows.

        Returns
        -------
        bool
            True if element has at least one incoming flow
        """
        return len(self.preset_flows) > 0

    def has_postset(self) -> bool:
        """Check if element has any outgoing flows.

        Returns
        -------
        bool
            True if element has at least one outgoing flow
        """
        return len(self.postset_flows) > 0

    def get_preset_size(self) -> int:
        """Get number of incoming flows.

        Returns
        -------
        int
            Number of flows in preset
        """
        return len(self.preset_flows)

    def get_postset_size(self) -> int:
        """Get number of outgoing flows.

        Returns
        -------
        int
            Number of flows in postset
        """
        return len(self.postset_flows)

    def add_preset_flow(self, flow_id: str) -> None:
        """Add incoming flow.

        Parameters
        ----------
        flow_id : str
            ID of the incoming flow
        """
        if flow_id not in self.preset_flows:
            self.preset_flows.append(flow_id)

    def add_postset_flow(self, flow_id: str) -> None:
        """Add outgoing flow.

        Parameters
        ----------
        flow_id : str
            ID of the outgoing flow
        """
        if flow_id not in self.postset_flows:
            self.postset_flows.append(flow_id)

    def remove_preset_flow(self, flow_id: str) -> bool:
        """Remove incoming flow.

        Parameters
        ----------
        flow_id : str
            ID of the flow to remove

        Returns
        -------
        bool
            True if flow was present and removed
        """
        if flow_id in self.preset_flows:
            self.preset_flows.remove(flow_id)
            return True
        return False

    def remove_postset_flow(self, flow_id: str) -> bool:
        """Remove outgoing flow.

        Parameters
        ----------
        flow_id : str
            ID of the flow to remove

        Returns
        -------
        bool
            True if flow was present and removed
        """
        if flow_id in self.postset_flows:
            self.postset_flows.remove(flow_id)
            return True
        return False

    def __hash__(self) -> int:
        """Hash by ID for use in sets/dicts."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality by ID and type."""
        if not isinstance(other, YExternalNetElement):
            return NotImplemented
        return self.id == other.id and type(self) is type(other)
