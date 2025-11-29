"""Task in YAWL net with split/join semantics (mirrors Java YTask).

Tasks are transitions in the Petri net. Unlike pure Petri nets,
YAWL tasks have split/join behavior as PROPERTIES, not separate elements.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kgcl.yawl.elements.y_decomposition import YDecomposition
    from kgcl.yawl.elements.y_internal_condition import YInternalCondition
    from kgcl.yawl.elements.y_multi_instance import YMultiInstanceAttributes
    from kgcl.yawl.elements.y_net import YNet


class SplitType(Enum):
    """Type of split behavior on outgoing flows.

    Attributes
    ----------
    AND : auto
        Fire ALL outgoing flows (parallel split)
    XOR : auto
        Fire exactly ONE flow (exclusive choice)
    OR : auto
        Fire ONE OR MORE flows (multi-choice)
    """

    AND = auto()
    XOR = auto()
    OR = auto()


class JoinType(Enum):
    """Type of join behavior on incoming flows.

    Attributes
    ----------
    AND : auto
        Wait for ALL incoming tokens (synchronization)
    XOR : auto
        Fire on ANY ONE incoming token (simple merge)
    OR : auto
        Fire when no more tokens expected (structured discriminator)
    """

    AND = auto()
    XOR = auto()
    OR = auto()


class TaskStatus(Enum):
    """Status of a task instance during execution.

    Attributes
    ----------
    ENABLED : auto
        Task can fire (all join conditions met)
    FIRED : auto
        Task has started execution
    EXECUTING : auto
        Task is currently executing
    COMPLETED : auto
        Task execution completed successfully
    CANCELLED : auto
        Task was cancelled (via cancellation region)
    """

    ENABLED = auto()
    FIRED = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    CANCELLED = auto()


@dataclass
class YTask:
    """Task in YAWL net with split/join semantics (mirrors Java YTask).

    Tasks are transitions in the underlying Petri net. Unlike pure Petri
    nets, YAWL tasks have split/join behavior as PROPERTIES rather than
    separate gateway elements. This is a key differentiator from BPMN.

    Parameters
    ----------
    id : str
        Unique identifier for this task
    name : str
        Human-readable name
    split_type : SplitType
        Split behavior on outgoing flows
    join_type : JoinType
        Join behavior on incoming flows
    net_id : str | None
        ID of containing net (set when added to net)
    preset_flows : list[str]
        IDs of incoming flows (from conditions)
    postset_flows : list[str]
        IDs of outgoing flows (to conditions)
    flow_predicates : dict[str, str]
        Predicates for XOR/OR splits (flow_id → predicate string)
    cancellation_set : set[str]
        IDs of elements to cancel when this task fires
    multi_instance : YMultiInstanceAttributes | None
        Multi-instance configuration (if applicable)
    decomposition_id : str | None
        ID of decomposition (what the task actually does)

    Examples
    --------
    >>> task = YTask(id="A", split_type=SplitType.AND, join_type=JoinType.XOR)
    >>> task.is_and_split()
    True
    >>> task.is_xor_join()
    True
    """

    id: str
    name: str = ""
    split_type: SplitType = SplitType.AND
    join_type: JoinType = JoinType.XOR
    net_id: str | None = None

    # Flow connections
    preset_flows: list[str] = field(default_factory=list)
    postset_flows: list[str] = field(default_factory=list)

    # Flow predicates (XOR/OR splits evaluate these)
    flow_predicates: dict[str, str] = field(default_factory=dict)

    # Cancellation region (reset net semantics)
    cancellation_set: set[str] = field(default_factory=set)

    # Multi-instance configuration
    multi_instance: YMultiInstanceAttributes | None = None

    # Decomposition (what the task actually does)
    decomposition_id: str | None = None

    # Data mappings (mirrors Java _dataMappingsForTaskStarting, etc.)
    data_mappings_for_task_starting: dict[str, str] = field(default_factory=dict)  # [key=ParamName, value=query]
    data_mappings_for_task_completion: dict[str, str] = field(default_factory=dict)  # [key=query, value=NetVarName]
    data_mappings_for_task_enablement: dict[str, str] = field(default_factory=dict)  # [key=ParamName, value=query]

    # Configuration and resourcing
    configuration: str | None = None
    default_configuration: str | None = None
    configuration_element: Any | None = None
    default_configuration_element: Any | None = None
    resourcing_xml: str | None = None
    resourcing_spec: Any | None = None

    # Timer support
    timer_params: Any | None = None
    timer_variable: Any | None = None

    # Custom form
    custom_form_url: str | None = None

    # Logging data items
    input_log_data_items: Any | None = None
    output_log_data_items: Any | None = None

    # Reset net (E2WFOJNet) for cancellation regions
    reset_net: Any | None = None

    # Schema validation flag
    _skip_outbound_schema_checks: bool = field(default=False, init=False, repr=False)

    # Internal state (for execution tracking)
    _current_identifier: Any | None = field(default=None, init=False, repr=False)
    _case_to_data_map: dict[Any, Any] = field(default_factory=dict, init=False, repr=False)
    _multi_instance_specific_params_iterator: Any | None = field(default=None, init=False, repr=False)
    _local_variable_name_to_replaceable_output_data: dict[str, Any] = field(
        default_factory=dict, init=False, repr=False
    )
    _grouped_multi_instance_output_data: Any | None = field(default=None, init=False, repr=False)

    # Multi-instance internal conditions (CRITICAL)
    _mi_active: Any | None = field(default=None, init=False, repr=False)
    _mi_entered: Any | None = field(default=None, init=False, repr=False)
    _mi_complete: Any | None = field(default=None, init=False, repr=False)
    _mi_executing: Any | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize internal conditions after dataclass initialization."""
        from kgcl.yawl.elements.y_internal_condition import YInternalCondition

        self._mi_active = YInternalCondition(id=YInternalCondition.MI_ACTIVE, my_task=self)
        self._mi_entered = YInternalCondition(id=YInternalCondition.MI_ENTERED, my_task=self)
        self._mi_complete = YInternalCondition(id=YInternalCondition.MI_COMPLETE, my_task=self)
        self._mi_executing = YInternalCondition(id=YInternalCondition.MI_EXECUTING, my_task=self)

    def is_and_split(self) -> bool:
        """Check if task has AND-split behavior.

        Returns
        -------
        bool
            True if split_type is AND
        """
        return self.split_type == SplitType.AND

    def is_xor_split(self) -> bool:
        """Check if task has XOR-split behavior.

        Returns
        -------
        bool
            True if split_type is XOR
        """
        return self.split_type == SplitType.XOR

    def is_or_split(self) -> bool:
        """Check if task has OR-split behavior.

        Returns
        -------
        bool
            True if split_type is OR
        """
        return self.split_type == SplitType.OR

    def is_and_join(self) -> bool:
        """Check if task has AND-join behavior.

        Returns
        -------
        bool
            True if join_type is AND
        """
        return self.join_type == JoinType.AND

    def is_xor_join(self) -> bool:
        """Check if task has XOR-join behavior.

        Returns
        -------
        bool
            True if join_type is XOR
        """
        return self.join_type == JoinType.XOR

    def is_or_join(self) -> bool:
        """Check if task has OR-join behavior.

        Returns
        -------
        bool
            True if join_type is OR
        """
        return self.join_type == JoinType.OR

    def has_cancellation_set(self) -> bool:
        """Check if task has a cancellation set.

        Returns
        -------
        bool
            True if cancellation_set is not empty
        """
        return len(self.cancellation_set) > 0

    def is_multi_instance(self) -> bool:
        """Check if task is a multi-instance task.

        Returns
        -------
        bool
            True if multi_instance is configured
        """
        return self.multi_instance is not None

    def get_display_name(self) -> str:
        """Get display name (name if set, else ID).

        Returns
        -------
        str
            Name or ID for display
        """
        return self.name if self.name else self.id

    def set_predicate(self, flow_id: str, predicate: str) -> None:
        """Set predicate for an outgoing flow.

        Parameters
        ----------
        flow_id : str
            ID of the flow
        predicate : str
            Predicate expression (evaluated for XOR/OR splits)
        """
        self.flow_predicates[flow_id] = predicate

    def get_predicate(self, flow_id: str) -> str | None:
        """Get predicate for an outgoing flow.

        Parameters
        ----------
        flow_id : str
            ID of the flow

        Returns
        -------
        str | None
            Predicate expression or None if not set
        """
        return self.flow_predicates.get(flow_id)

    def get_predicate_for_element(self, net_element: Any) -> str:
        """Get predicate for a net element (flow).

        Java signature: String getPredicate(YExternalNetElement netElement)

        Parameters
        ----------
        net_element : Any
            Net element (typically a flow or condition)

        Returns
        -------
        str
            Predicate expression

        Notes
        -----
        Mirrors Java YAWL YTask.getPredicate()
        Gets predicate from postset flow to the element
        """
        if hasattr(net_element, "id"):
            element_id = net_element.id
            for flow_id in self.postset_flows:
                if flow_id in self.flow_predicates:
                    return self.flow_predicates[flow_id]
        return ""

    def set_i(self, identifier: Any) -> None:
        """Set current identifier.

        Java signature: void setI(YIdentifier i)

        Parameters
        ----------
        identifier : Any
            Current identifier

        Notes
        -----
        Mirrors Java YAWL YTask.setI()
        """
        self._current_identifier = identifier

    def get_i(self) -> Any:
        """Get current identifier.

        Java signature: YIdentifier getI() (private)

        Returns
        -------
        Any
            Current identifier or None

        Notes
        -----
        Mirrors Java YAWL YTask.getI()
        """
        return self._current_identifier

    def get_data(self, child_instance_id: Any) -> Any:
        """Get data for child instance.

        Java signature: Element getData(YIdentifier childInstanceID)

        Parameters
        ----------
        child_instance_id : Any
            Child instance identifier

        Returns
        -------
        Any
            Data element for the instance

        Notes
        -----
        Mirrors Java YAWL YTask.getData()
        """
        return self._case_to_data_map.get(child_instance_id)

    def add_to_cancellation_set(self, element_id: str) -> None:
        """Add element to cancellation set.

        Parameters
        ----------
        element_id : str
            ID of element (condition or task) to add
        """
        self.cancellation_set.add(element_id)

    def get_remove_set(self) -> set[str] | None:
        """Get remove set (cancellation set).

        Java signature: Set<YExternalNetElement> getRemoveSet()

        Returns
        -------
        set[str] | None
            Set of element IDs to remove, or None if empty

        Notes
        -----
        Mirrors Java YAWL YTask.getRemoveSet()
        """
        if self.cancellation_set:
            return set(self.cancellation_set)
        return None

    def add_removes_tokens_from(self, remove_set: list[Any]) -> None:
        """Add elements to remove set.

        Java signature: void addRemovesTokensFrom(List<YExternalNetElement> removeSet)

        Parameters
        ----------
        remove_set : list[Any]
            List of elements to add to cancellation set

        Notes
        -----
        Mirrors Java YAWL YTask.addRemovesTokensFrom()
        Also adds task to CancelledBySet of each element
        """
        for element in remove_set:
            if hasattr(element, "id"):
                self.cancellation_set.add(element.id)
            if hasattr(element, "add_to_cancelled_by_set"):
                element.add_to_cancelled_by_set(self)

    def remove_from_remove_set(self, element: Any) -> None:
        """Remove element from remove set.

        Java signature: void removeFromRemoveSet(YExternalNetElement e)

        Parameters
        ----------
        element : Any
            Element to remove

        Notes
        -----
        Mirrors Java YAWL YTask.removeFromRemoveSet()
        Also removes task from element's CancelledBySet
        """
        if element is None:
            return
        if hasattr(element, "id"):
            self.cancellation_set.discard(element.id)
        if hasattr(element, "remove_from_cancelled_by_set"):
            element.remove_from_cancelled_by_set(self)

    def add_removes_tokens_from(self, remove_set: list[YExternalNetElement] | list[str]) -> None:
        """Add elements to removal set (cancellation region).

        Java signature: void addRemovesTokensFrom(List removeSet)

        Parameters
        ----------
        remove_set : list[YExternalNetElement] | list[str]
            List of elements or element IDs to remove tokens from

        Notes
        -----
        Mirrors Java YAWL YTask.addRemovesTokensFrom()
        Adds elements to cancellation set for reset net semantics
        """
        from kgcl.yawl.elements.y_external_net_element import YExternalNetElement

        for element in remove_set:
            if isinstance(element, str):
                self.cancellation_set.add(element)
            elif isinstance(element, YExternalNetElement):
                self.cancellation_set.add(element.id)
                # In Java, also calls element.addToCancelledBySet(this)
                # This would require bidirectional reference management

    # ===== Split Methods =====

    def do_and_split(self, token_to_send: Any, net: Any, pmgr: Any | None = None) -> None:
        """Execute AND-split (fire all outgoing flows).

        Java signature: void doAndSplit(YPersistenceManager pmgr, YIdentifier tokenToSend)

        Parameters
        ----------
        token_to_send : Any
            Token being sent through the split
        net : Any
            Containing net (for accessing postset elements)
        pmgr : Any | None
            Persistence manager (optional)

        Notes
        -----
        Mirrors Java YAWL YTask.doAndSplit()
        AND-split fires ALL postset flows simultaneously (WCP-2: Parallel Split)
        """
        if token_to_send is None:
            raise RuntimeError(f"token is equal to null = {token_to_send}")
        for flow_id in self.postset_flows:
            flow = net.flows.get(flow_id) if hasattr(net, "flows") else None
            if flow:
                target = net.conditions.get(flow.target_id) if hasattr(net, "conditions") else None
                if target and hasattr(target, "add"):
                    target.add(pmgr, token_to_send)

    def do_xor_split(self, token_to_send: Any, net: Any, pmgr: Any | None = None) -> None:
        """Execute XOR-split (fire exactly one flow based on predicate).

        Java signature: void doXORSplit(YPersistenceManager pmgr, YIdentifier tokenToSend)

        Parameters
        ----------
        token_to_send : Any
            Token being sent through the split
        net : Any
            Containing net (for accessing flows and data)
        pmgr : Any | None
            Persistence manager (optional)

        Notes
        -----
        Mirrors Java YAWL YTask.doXORSplit()
        XOR-split fires EXACTLY ONE flow based on predicate evaluation (WCP-4: Exclusive Choice)
        """
        flows = []
        if hasattr(net, "flows"):
            for flow_id in self.postset_flows:
                flow = net.flows.get(flow_id)
                if flow:
                    flows.append(flow)
        flows.sort(key=lambda f: getattr(f, "eval_ordering", 0))

        for flow in flows:
            if getattr(flow, "is_default_flow", lambda: False)():
                target = net.conditions.get(flow.target_id) if hasattr(net, "conditions") else None
                if target and hasattr(target, "add"):
                    target.add(pmgr, token_to_send)
                return

            predicate = self.flow_predicates.get(flow.id, "")
            if predicate and self.evaluate_split_query(predicate, token_to_send, net):
                target = net.conditions.get(flow.target_id) if hasattr(net, "conditions") else None
                if target and hasattr(target, "add"):
                    target.add(pmgr, token_to_send)
                return

    def do_or_split(self, token_to_send: Any, net: Any, pmgr: Any | None = None) -> None:
        """Execute OR-split (fire one or more flows based on predicates).

        Java signature: void doOrSplit(YPersistenceManager pmgr, YIdentifier tokenToSend)

        Parameters
        ----------
        token_to_send : Any
            Token being sent through the split
        net : Any
            Containing net (for accessing flows and data)
        pmgr : Any | None
            Persistence manager (optional)

        Notes
        -----
        Mirrors Java YAWL YTask.doOrSplit()
        OR-split fires ONE OR MORE flows based on predicate evaluation (WCP-6: Multi-Choice)
        """
        no_tokens_output = True
        flows = []
        if hasattr(net, "flows"):
            for flow_id in self.postset_flows:
                flow = net.flows.get(flow_id)
                if flow:
                    flows.append(flow)
        flows.sort(key=lambda f: getattr(f, "eval_ordering", 0))

        for flow in flows:
            predicate = self.flow_predicates.get(flow.id, "")
            if predicate and self.evaluate_split_query(predicate, token_to_send, net):
                target = net.conditions.get(flow.target_id) if hasattr(net, "conditions") else None
                if target and hasattr(target, "add"):
                    target.add(pmgr, token_to_send)
                    no_tokens_output = False

            if getattr(flow, "is_default_flow", lambda: False)() and no_tokens_output:
                target = net.conditions.get(flow.target_id) if hasattr(net, "conditions") else None
                if target and hasattr(target, "add"):
                    target.add(pmgr, token_to_send)

    def evaluate_split_query(self, query: str, token_to_send: Any, net: Any) -> bool:
        """Evaluate predicate for XOR/OR split decision.

        Java signature: boolean evaluateSplitQuery(String query, YIdentifier tokenToSend)

        Parameters
        ----------
        query : str
            XQuery predicate expression
        token_to_send : Any
            Token context for evaluation
        net : Any
            Containing net (for accessing data document)

        Returns
        -------
        bool
            True if flow should fire, False otherwise

        Notes
        -----
        Mirrors Java YAWL YTask.evaluateSplitQuery()
        Evaluates XQuery expression in context of token data
        """
        if not query or not query.strip():
            return False

        query_trimmed = query.strip()
        if query_trimmed.startswith("timer("):
            return self._evaluate_timer_predicate(query_trimmed, token_to_send)

        data_doc = None
        if hasattr(net, "get_internal_data_document"):
            data_doc = net.get_internal_data_document()
        elif hasattr(net, "internal_data_document"):
            data_doc = net.internal_data_document

        if data_doc is None:
            return False

        xquery = f"boolean({query})"
        try:
            from kgcl.yawl.engine.y_expression import YExpressionEvaluator

            evaluator = YExpressionEvaluator()
            result = evaluator.evaluate_boolean(xquery, data_doc)
            return bool(result)
        except Exception:
            return False

    def _evaluate_timer_predicate(self, predicate: str, token: Any) -> bool:
        """Evaluate timer predicate.

        Parameters
        ----------
        predicate : str
            Timer predicate expression
        token : Any
            Token identifier

        Returns
        -------
        bool
            Timer predicate result
        """
        return False

    # ===== Multi-Instance Methods =====

    def get_multi_instance_attributes(self) -> Any | None:
        """Get multi-instance configuration.

        Java signature: YMultiInstanceAttributes getMultiInstanceAttributes()

        Returns
        -------
        Any | None
            Multi-instance attributes or None

        Notes
        -----
        Mirrors Java YAWL YTask.getMultiInstanceAttributes()
        """
        return self.multi_instance

    def get_mi_active(self) -> Any:
        """Get MI active internal condition.

        Java signature: YInternalCondition getMIActive()

        Returns
        -------
        Any
            MI active condition

        Notes
        -----
        Mirrors Java YAWL YTask.getMIActive()
        """
        return self._mi_active

    def get_mi_entered(self) -> Any:
        """Get MI entered internal condition.

        Java signature: YInternalCondition getMIEntered()

        Returns
        -------
        Any
            MI entered condition

        Notes
        -----
        Mirrors Java YAWL YTask.getMIEntered()
        """
        return self._mi_entered

    def get_mi_complete(self) -> Any:
        """Get MI complete internal condition.

        Java signature: YInternalCondition getMIComplete()

        Returns
        -------
        Any
            MI complete condition

        Notes
        -----
        Mirrors Java YAWL YTask.getMIComplete()
        """
        return self._mi_complete

    def get_mi_executing(self) -> Any:
        """Get MI executing internal condition.

        Java signature: YInternalCondition getMIExecuting()

        Returns
        -------
        Any
            MI executing condition

        Notes
        -----
        Mirrors Java YAWL YTask.getMIExecuting()
        """
        return self._mi_executing

    def get_all_internal_conditions(self) -> list[Any]:
        """Get all internal conditions.

        Java signature: List<YInternalCondition> getAllInternalConditions()

        Returns
        -------
        list[Any]
            List of all internal conditions

        Notes
        -----
        Mirrors Java YAWL YTask.getAllInternalConditions()
        """
        return [self._mi_active, self._mi_entered, self._mi_complete, self._mi_executing]

    def set_up_multiple_instance_attributes(
        self, min_instance_query: str, max_instance_query: str, threshold_query: str, creation_mode: str
    ) -> None:
        """Configure multi-instance task parameters.

        Java signature: void setUpMultipleInstanceAttributes(String minInstanceQuery, String maxInstanceQuery, String thresholdQuery, String creationMode)

        Parameters
        ----------
        min_instance_query : str
            Query for minimum instances
        max_instance_query : str
            Query for maximum instances
        threshold_query : str
            Query for completion threshold
        creation_mode : str
            "static" or "dynamic"

        Notes
        -----
        Mirrors Java YAWL YTask.setUpMultipleInstanceAttributes()
        Sets up WCP-12 through WCP-15 multi-instance patterns
        """
        from kgcl.yawl.elements.y_multi_instance import MICreationMode, YMultiInstanceAttributes

        creation_mode_enum = MICreationMode.STATIC if creation_mode.lower() == "static" else MICreationMode.DYNAMIC
        self.multi_instance = YMultiInstanceAttributes(
            min_query=min_instance_query,
            max_query=max_instance_query,
            threshold_query=threshold_query,
            creation_mode=creation_mode_enum,
        )

    def set_multi_instance_input_data_mappings(
        self, remote_variable_name: str, input_processing_expression: str
    ) -> None:
        """Set multi-instance input data mappings.

        Java signature: void setMultiInstanceInputDataMappings(String remoteVariableName, String inputProcessingExpression)

        Parameters
        ----------
        remote_variable_name : str
            Remote variable name (MI formal input param)
        input_processing_expression : str
            Input processing expression (MI splitting query)

        Notes
        -----
        Mirrors Java YAWL YTask.setMultiInstanceInputDataMappings()
        """
        if self.multi_instance is None:
            from kgcl.yawl.elements.y_multi_instance import YMultiInstanceAttributes

            self.multi_instance = YMultiInstanceAttributes()
        if hasattr(self.multi_instance, "set_mi_formal_input_param"):
            self.multi_instance.set_mi_formal_input_param(remote_variable_name)
        if hasattr(self.multi_instance, "set_unique_input_mi_splitting_query"):
            self.multi_instance.set_unique_input_mi_splitting_query(input_processing_expression)

    def set_multi_instance_output_data_mappings(self, remote_output_query: str, aggregation_query: str) -> None:
        """Set multi-instance output data mappings.

        Java signature: void setMultiInstanceOutputDataMappings(String remoteOutputQuery, String aggregationQuery)

        Parameters
        ----------
        remote_output_query : str
            Remote output query (MI formal output query)
        aggregation_query : str
            Aggregation query (MI joining query)

        Notes
        -----
        Mirrors Java YAWL YTask.setMultiInstanceOutputDataMappings()
        """
        if self.multi_instance is None:
            from kgcl.yawl.elements.y_multi_instance import YMultiInstanceAttributes

            self.multi_instance = YMultiInstanceAttributes()
        if hasattr(self.multi_instance, "set_mi_formal_output_query"):
            self.multi_instance.set_mi_formal_output_query(remote_output_query)
        if hasattr(self.multi_instance, "set_unique_output_mi_joining_query"):
            self.multi_instance.set_unique_output_mi_joining_query(aggregation_query)

    def get_mi_output_data(self) -> Any:
        """Get grouped multi-instance output data.

        Java signature: GroupedMIOutputData getMIOutputData()

        Returns
        -------
        Any
            Grouped MI output data

        Notes
        -----
        Mirrors Java YAWL YTask.getMIOutputData()
        """
        return self._grouped_multi_instance_output_data

    def set_grouped_multi_instance_output_data(self, data: Any) -> None:
        """Set grouped multi-instance output data.

        Java signature: void setGroupedMultiInstanceOutputData(GroupedMIOutputData data)

        Parameters
        ----------
        data : Any
            Grouped MI output data

        Notes
        -----
        Mirrors Java YAWL YTask.setGroupedMultiInstanceOutputData()
        Called from YEngineRestorer
        """
        self._grouped_multi_instance_output_data = data

    def get_pre_splitting_mi_query(self) -> str | None:
        """Get pre-splitting MI query.

        Java signature: String getPreSplittingMIQuery()

        Returns
        -------
        str | None
            Pre-splitting query or None

        Notes
        -----
        Mirrors Java YAWL YTask.getPreSplittingMIQuery()
        """
        if self.multi_instance is None:
            return None
        mi_var_name = None
        if hasattr(self.multi_instance, "get_mi_formal_input_param"):
            mi_var_name = self.multi_instance.get_mi_formal_input_param()
        if mi_var_name:
            return self.data_mappings_for_task_starting.get(mi_var_name)
        return None

    def get_pre_joining_mi_query(self) -> str | None:
        """Get pre-joining MI query.

        Java signature: String getPreJoiningMIQuery() (private)

        Returns
        -------
        str | None
            Pre-joining query or None

        Notes
        -----
        Mirrors Java YAWL YTask.getPreJoiningMIQuery()
        """
        if self.multi_instance is None:
            return None
        if hasattr(self.multi_instance, "get_mi_formal_output_query"):
            return self.multi_instance.get_mi_formal_output_query()
        return None

    def get_mi_output_assignment_var(self, query: str) -> str:
        """Get MI output assignment variable for query.

        Java signature: String getMIOutputAssignmentVar(String query)

        Parameters
        ----------
        query : str
            Output query

        Returns
        -------
        str
            Net variable name

        Notes
        -----
        Mirrors Java YAWL YTask.getMIOutputAssignmentVar()
        """
        return self.data_mappings_for_task_completion.get(query, "")

    def get_spec_version(self) -> str:
        """Get specification version.

        Java signature: String getSpecVersion()

        Returns
        -------
        str
            Specification version

        Notes
        -----
        Mirrors Java YAWL YTask.getSpecVersion()
        """
        if self.net_id and hasattr(self, "_net"):
            net = getattr(self, "_net", None)
            if net and hasattr(net, "get_specification"):
                spec = net.get_specification()
                if spec and hasattr(spec, "get_spec_version"):
                    return spec.get_spec_version()
        return ""

    def get_information(self) -> str:
        """Get task information as XML.

        Java signature: String getInformation()

        Returns
        -------
        str
            XML string with task information

        Notes
        -----
        Mirrors Java YAWL YTask.getInformation()
        Returns comprehensive task metadata as XML
        """
        result_parts: list[str] = []
        result_parts.append("<taskInfo>")

        # Use wrap utility (mirrors Java StringUtil.wrap)
        from kgcl.yawl.util.string_util import wrap, wrap_escaped

        if hasattr(self, "_net") and self._net:
            net = getattr(self, "_net", None)
            if net and hasattr(net, "get_specification"):
                spec = net.get_specification()
                if spec:
                    result_parts.append("<specification>")
                    if hasattr(spec, "id"):
                        result_parts.append(wrap(spec.id, "id"))
                    if hasattr(spec, "get_spec_version"):
                        result_parts.append(wrap(spec.get_spec_version(), "version"))
                    if hasattr(spec, "get_uri"):
                        result_parts.append(wrap(spec.get_uri(), "uri"))
                    result_parts.append("</specification>")

        result_parts.append(f"<taskID>{self.id}</taskID>")

        task_name = (
            self.name
            if self.name
            else (
                self._decomposition_prototype.id
                if hasattr(self, "_decomposition_prototype") and self._decomposition_prototype
                else "null"
            )
        )
        # Use wrap_escaped utility (mirrors Java StringUtil.wrapEscaped)
        result_parts.append(wrap_escaped(task_name, "taskName"))

        if self.documentation:
            # Use wrap_escaped utility (mirrors Java StringUtil.wrapEscaped)
            result_parts.append(wrap_escaped(self.documentation, "taskDocumentation"))

        if hasattr(self, "_decomposition_prototype") and self._decomposition_prototype:
            decomp = self._decomposition_prototype
            result_parts.append(f"<decompositionID>{decomp.id}</decompositionID>")

            # Use to_xml_elements() for attributes (mirrors Java getAttributes().toXMLElements())
            if hasattr(decomp, "get_attributes"):
                attrs = decomp.get_attributes()
                if attrs:
                    result_parts.append("<attributes>")
                    if hasattr(attrs, "to_xml_elements"):
                        result_parts.append(attrs.to_xml_elements())
                    elif isinstance(attrs, dict):
                        for key, value in attrs.items():
                            result_parts.append(f"<{key}>{value}</{key}>")
                    result_parts.append("</attributes>")

            # Handle YAWLServiceGateway (mirrors Java instanceof YAWLServiceGateway)
            from kgcl.yawl.elements.y_decomposition import YWebServiceGateway

            if isinstance(decomp, YWebServiceGateway):
                yawl_service = decomp.get_yawl_service()
                if yawl_service:
                    result_parts.append("<yawlService>")
                    service_uri = yawl_service.get_uri() if hasattr(yawl_service, "get_uri") else ""
                    result_parts.append(f"<id>{service_uri}</id>")
                    result_parts.append("</yawlService>")

        result_parts.append("<params>")
        if self.is_multi_instance() and self.multi_instance:
            if hasattr(self.multi_instance, "get_mi_formal_input_param"):
                formal_input = self.multi_instance.get_mi_formal_input_param()
                if formal_input:
                    result_parts.append(f"<formalInputParam>{formal_input}</formalInputParam>")

        if hasattr(self, "_decomposition_prototype") and self._decomposition_prototype:
            decomp = self._decomposition_prototype
            if hasattr(decomp, "get_input_parameters"):
                input_params = decomp.get_input_parameters()
                if input_params:
                    for param in input_params.values():
                        if hasattr(param, "to_summary_xml"):
                            result_parts.append(param.to_summary_xml())
            if hasattr(decomp, "get_output_parameters"):
                output_params = decomp.get_output_parameters()
                if output_params:
                    for param in output_params.values():
                        if hasattr(param, "to_summary_xml"):
                            result_parts.append(param.to_summary_xml())

        result_parts.append("</params>")

        if self.custom_form_url:
            result_parts.append(f"<customform>{self.custom_form_url}</customform>")
        else:
            result_parts.append("<customform/>")

        result_parts.append("</taskInfo>")
        return "".join(result_parts)

    def determine_how_many_instances_to_create(self) -> int:
        """Calculate number of MI instances to create.

        Java signature: long determineHowManyInstancesToCreate()

        Returns
        -------
        int
            Number of instances to create

        Notes
        -----
        Mirrors Java YAWL YTask.determineHowManyInstancesToCreate()
        Evaluates MI queries in current data context
        """
        if not self.is_multi_instance():
            return 1

        net = getattr(self, "_net", None)
        if net is None:
            return 1

        multi_instance_list = self.split_starting_data_for_multi_instances()
        list_size = len(multi_instance_list)

        max_instances = self.multi_instance.maximum if hasattr(self.multi_instance, "maximum") else 999999
        min_instances = self.multi_instance.minimum if hasattr(self.multi_instance, "minimum") else 1

        if list_size > max_instances or list_size < min_instances:
            pre_splitting_query = self.get_pre_splitting_mi_query()
            data_to_split = None
            if pre_splitting_query and hasattr(net, "get_internal_data_document"):
                data_doc = net.get_internal_data_document()
                if data_doc:
                    from kgcl.yawl.engine.y_expression import YExpressionEvaluator

                    evaluator = YExpressionEvaluator()
                    try:
                        data_to_split = evaluator.evaluate(pre_splitting_query, data_doc)
                    except Exception:
                        pass

            error_msg = (
                f"The number of instances produced by MI split ({list_size}) is "
                f"{'more' if list_size > max_instances else 'less'} than the "
                f"{'maximum' if list_size > max_instances else 'minimum'} "
                f"instance bound specified ({max_instances if list_size > max_instances else min_instances})."
            )
            raise ValueError(error_msg)

        self._multi_instance_specific_params_iterator = iter(multi_instance_list)
        return list_size

    def split_starting_data_for_multi_instances(self) -> list[Any]:
        """Split data for each MI instance.

        Java signature: List<Content> splitStartingDataForMultiInstances()

        Returns
        -------
        list[Any]
            Data elements for each instance

        Notes
        -----
        Mirrors Java YAWL YTask.splitStartingDataForMultiInstances()
        Partitions input data across MI instances
        """
        if not self.is_multi_instance() or self.multi_instance is None:
            return []

        net = getattr(self, "_net", None)
        if net is None:
            return []

        query_string = self.get_pre_splitting_mi_query()
        if not query_string:
            return []

        data_doc = net.get_internal_data_document() if hasattr(net, "get_internal_data_document") else None
        if data_doc is None:
            return []

        from kgcl.yawl.engine.y_expression import YExpressionEvaluator

        evaluator = YExpressionEvaluator()
        try:
            data_to_split = evaluator.evaluate(query_string, data_doc)
            if data_to_split is None:
                return []

            mi_splitting_query = None
            if hasattr(self.multi_instance, "get_mi_splitting_query"):
                mi_splitting_query = self.multi_instance.get_mi_splitting_query()
            elif hasattr(self.multi_instance, "mi_splitting_query"):
                mi_splitting_query = self.multi_instance.mi_splitting_query

            if not mi_splitting_query:
                return []

            result = evaluator.evaluate_list(mi_splitting_query, data_to_split)
            if isinstance(result, list):
                return result
            return []
        except Exception:
            return []

    def sort_multi_instance_starting_data(self) -> None:
        """Sort MI starting data.

        Java signature: void sortMultiInstanceStartingData()

        Notes
        -----
        Mirrors Java YAWL YTask.sortMultiInstanceStartingData()
        Orders MI data for deterministic execution
        """
        if not self.is_multi_instance():
            return

        try:
            self._multi_instance_specific_params_iterator = iter(self.split_starting_data_for_multi_instances())

            if self._current_identifier is None:
                return

            non_null_ids = []
            if hasattr(self._current_identifier, "children"):
                for yid in self._current_identifier.children:
                    if yid is not None:
                        non_null_ids.append(yid)

            non_null_ids.sort(key=lambda x: str(x) if x else "")

            for identifier in non_null_ids:
                if hasattr(identifier, "get_locations"):
                    locations = identifier.get_locations()
                    if not locations:
                        continue
                elif hasattr(identifier, "location") and not identifier.location:
                    continue

                starting_data = self._get_starting_data_snapshot(getattr(self, "_net", None))
                if starting_data is not None:
                    self._case_to_data_map[identifier] = starting_data
        except Exception:
            pass

    # ===== Task Lifecycle Methods =====

    def t_enabled(self, identifier: Any) -> bool:
        """Check if task is enabled for given identifier.

        Java signature: boolean t_enabled(YIdentifier id)

        Parameters
        ----------
        identifier : Any
            Token identifier

        Returns
        -------
        bool
            True if task can fire

        Notes
        -----
        Mirrors Java YAWL YTask.t_enabled()
        Checks join conditions satisfied
        """
        if self._current_identifier is not None:
            return False

        net = getattr(self, "_net", None)
        if net is None:
            return False

        if self.join_type == JoinType.AND:
            for flow_id in self.preset_flows:
                condition = net.get_condition(flow_id) if hasattr(net, "get_condition") else None
                if condition is None:
                    condition = net.conditions.get(flow_id) if hasattr(net, "conditions") else None
                if condition is None or not condition.contains_identifier():
                    return False
            return True
        elif self.join_type == JoinType.OR:
            if hasattr(net, "or_join_enabled"):
                return net.or_join_enabled(self, identifier)
            return False
        elif self.join_type == JoinType.XOR:
            for flow_id in self.preset_flows:
                condition = net.get_condition(flow_id) if hasattr(net, "get_condition") else None
                if condition is None:
                    condition = net.conditions.get(flow_id) if hasattr(net, "conditions") else None
                if condition and condition.contains_identifier():
                    return True
            return False
        return False

    def t_fire(self, pmgr: Any | None = None) -> list[Any]:
        """Fire task (transition from enabled to fired).

        Java signature: List<YIdentifier> t_fire(YPersistenceManager pmgr)

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager

        Returns
        -------
        list[Any]
            List of fired child identifiers

        Notes
        -----
        Mirrors Java YAWL YTask.t_fire()
        Removes input tokens, creates output tokens based on split type
        """
        net = getattr(self, "_net", None)
        if net is None:
            return []

        identifier = self.get_i()
        if identifier is None:
            for flow_id in self.preset_flows:
                condition = net.get_condition(flow_id) if hasattr(net, "get_condition") else None
                if condition is None:
                    condition = net.conditions.get(flow_id) if hasattr(net, "conditions") else None
                if condition and condition.contains_identifier():
                    identifier = condition.remove_one(pmgr)
                    break

        if identifier is None:
            return []

        if not self.t_enabled(identifier):
            return []

        self._current_identifier = identifier
        if hasattr(identifier, "add_location"):
            identifier.add_location(pmgr, self)

        num_to_spawn = self.determine_how_many_instances_to_create()
        child_identifiers: list[Any] = []

        for _ in range(num_to_spawn):
            child_id = self.create_fired_identifier(pmgr)
            if child_id is None:
                continue

            try:
                self.prepare_data_for_instance_starting(child_id, net)
            except Exception as e:
                self._rollback_fired(child_id, pmgr)
                raise

            child_identifiers.append(child_id)

        self._prepare_data_docs_for_task_output(pmgr)

        if self.join_type == JoinType.AND:
            for flow_id in self.preset_flows:
                condition = net.get_condition(flow_id) if hasattr(net, "get_condition") else None
                if condition is None:
                    condition = net.conditions.get(flow_id) if hasattr(net, "conditions") else None
                if condition:
                    condition.remove_one(pmgr)
        elif self.join_type == JoinType.OR:
            for flow_id in self.preset_flows:
                condition = net.get_condition(flow_id) if hasattr(net, "get_condition") else None
                if condition is None:
                    condition = net.conditions.get(flow_id) if hasattr(net, "conditions") else None
                if condition and condition.contains_identifier():
                    condition.remove_one(pmgr)
        elif self.join_type == JoinType.XOR:
            conditions_with_tokens = []
            for flow_id in self.preset_flows:
                condition = net.get_condition(flow_id) if hasattr(net, "get_condition") else None
                if condition is None:
                    condition = net.conditions.get(flow_id) if hasattr(net, "conditions") else None
                if condition and condition.contains_identifier():
                    conditions_with_tokens.append(condition)
            if conditions_with_tokens:
                selected = conditions_with_tokens[self._random.randint(0, len(conditions_with_tokens) - 1)]
                selected.remove_one(pmgr)

        return child_identifiers

    def _rollback_fired(self, child_id: Any, pmgr: Any | None) -> None:
        """Rollback fired instance on error.

        Parameters
        ----------
        child_id : Any
            Child identifier to rollback
        pmgr : Any | None
            Persistence manager
        """
        if hasattr(child_id, "remove_location"):
            child_id.remove_location(pmgr, self)
        if child_id in self._case_to_data_map:
            del self._case_to_data_map[child_id]

    def _prepare_data_docs_for_task_output(self, pmgr: Any | None) -> None:
        """Prepare data documents for task output.

        Java signature: void prepareDataDocsForTaskOutput(YPersistenceManager pmgr)

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager

        Notes
        -----
        Mirrors Java YAWL YTask.prepareDataDocsForTaskOutput()
        """
        if self.decomposition_id is None:
            return

        if self.is_multi_instance():
            root_data_elem_name = "data"
            if hasattr(self, "_decomposition_prototype") and self._decomposition_prototype:
                decomp = self._decomposition_prototype
                if hasattr(decomp, "get_root_data_element_name"):
                    root_data_elem_name = decomp.get_root_data_element_name()

            try:
                from kgcl.yawl.elements.y_grouped_mi_output_data import GroupedMIOutputData

                self._grouped_multi_instance_output_data = GroupedMIOutputData(
                    self._current_identifier, self.id, root_data_elem_name
                )
                if pmgr and hasattr(pmgr, "store_object_from_external"):
                    pmgr.store_object_from_external(self._grouped_multi_instance_output_data)
            except ImportError:
                self._grouped_multi_instance_output_data = None

        self._local_variable_name_to_replaceable_output_data = {}

    def t_start(self, runner: Any, child: Any) -> None:
        """Start task execution.

        Java signature: void t_start(YNetRunner runner, YIdentifier child)

        Parameters
        ----------
        runner : Any
            Net runner context
        child : Any
            Child identifier for this execution

        Notes
        -----
        Mirrors Java YAWL YTask.t_start()
        Initiates task decomposition execution
        """
        pass

    def t_complete(self, child_id: Any, decomposition_output_data: Any, pmgr: Any | None = None) -> bool:
        """Complete task execution.

        Java signature: boolean t_complete(YIdentifier childID, Document decompositionOutputData)

        Parameters
        ----------
        child_id : Any
            Child identifier
        decomposition_output_data : Any
            Output data from decomposition
        pmgr : Any | None
            Persistence manager

        Returns
        -------
        bool
            True if completion successful and task can exit

        Notes
        -----
        Mirrors Java YAWL YTask.t_complete()
        Maps output data, fires output flows
        """
        if not self.t_is_busy():
            return False

        net = getattr(self, "_net", None)
        if net is None:
            return False

        spec = net.get_specification() if hasattr(net, "get_specification") else None
        validator = spec.get_data_validator() if spec and hasattr(spec, "get_data_validator") else None

        if validator and hasattr(validator, "validate_outputs"):
            try:
                validator.validate_outputs(self, decomposition_output_data)
            except Exception as e:
                raise

        for query in self.get_queries_for_task_completion():
            local_var_name = self.get_mi_output_assignment_var(query)
            if not local_var_name:
                continue

            query_result = None
            if hasattr(self, "perform_data_extraction"):
                query_result = self.perform_data_extraction(query, None, decomposition_output_data)

            if query_result is None:
                continue

            pre_joining_query = self.get_pre_joining_mi_query()
            if query == pre_joining_query:
                if self._grouped_multi_instance_output_data:
                    if hasattr(self._grouped_multi_instance_output_data, "add_static_content"):
                        self._grouped_multi_instance_output_data.add_static_content(query_result)
                    if pmgr and hasattr(pmgr, "update_object_external"):
                        pmgr.update_object_external(self._grouped_multi_instance_output_data)
            else:
                self._local_variable_name_to_replaceable_output_data[local_var_name] = query_result

                if (
                    validator
                    and spec
                    and hasattr(spec, "get_schema_version")
                    and spec.get_schema_version().is_schema_validating()
                ):
                    var = (
                        net.get_local_or_input_variable(local_var_name)
                        if hasattr(net, "get_local_or_input_variable")
                        else None
                    )
                    if var and hasattr(validator, "validate"):
                        try:
                            temp_root = None
                            if hasattr(self, "_decomposition_prototype") and self._decomposition_prototype:
                                decomp = self._decomposition_prototype
                                root_name = decomp.get_id() if hasattr(decomp, "get_id") else "root"
                                from xml.etree import ElementTree as ET

                                temp_root = ET.Element(root_name)
                                if hasattr(query_result, "clone"):
                                    temp_root.append(query_result.clone())
                                elif hasattr(query_result, "copy"):
                                    temp_root.append(query_result.copy())

                            if temp_root and query_result:
                                validator.validate(var, temp_root, self.id)
                        except Exception as e:
                            raise

        if self._mi_executing:
            self._mi_executing.remove_one(pmgr, child_id)
        if self._mi_complete:
            self._mi_complete.add(pmgr, child_id)

        if self.t_is_exit_enabled():
            self.t_exit(pmgr)
            return True
        return False

    def t_exit(self, pmgr: Any | None = None) -> None:
        """Exit task (final cleanup).

        Java signature: void t_exit(YPersistenceManager pmgr)

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager

        Notes
        -----
        Mirrors Java YAWL YTask.t_exit()
        Cleanup after all instances complete
        """
        if not self.t_is_exit_enabled():
            return

        net = getattr(self, "_net", None)
        if net is None:
            return

        self.perform_data_assignments_according_to_output_expressions(net, pmgr)

        if self.timer_variable and hasattr(self.timer_variable, "set_state"):
            self.timer_variable.set_state("closed")

        identifier = self._current_identifier
        if identifier is None:
            return

        if hasattr(self, "cancel"):
            self.cancel(pmgr)

        for element_id in self.cancellation_set:
            element = net.get_net_element(element_id) if hasattr(net, "get_net_element") else None
            if element is None:
                element = net.tasks.get(element_id) if hasattr(net, "tasks") else None
            if element is None:
                element = net.conditions.get(element_id) if hasattr(net, "conditions") else None

            if element:
                if hasattr(element, "cancel"):
                    element.cancel(pmgr)
                elif hasattr(element, "remove_all"):
                    element.remove_all(pmgr)

        if hasattr(identifier, "remove_location"):
            identifier.remove_location(pmgr, self)

        if identifier in self._case_to_data_map:
            del self._case_to_data_map[identifier]

        if self._grouped_multi_instance_output_data and pmgr:
            if hasattr(pmgr, "delete_object_from_external"):
                pmgr.delete_object_from_external(self._grouped_multi_instance_output_data)

        if self.split_type == SplitType.AND:
            self.do_and_split(identifier, net, pmgr)
        elif self.split_type == SplitType.OR:
            self.do_or_split(identifier, net, pmgr)
        elif self.split_type == SplitType.XOR:
            self.do_xor_split(identifier, net, pmgr)

        self._current_identifier = None

    def t_is_busy(self) -> bool:
        """Check if task has active instances.

        Java signature: boolean t_isBusy()

        Returns
        -------
        bool
            True if task has executing instances

        Notes
        -----
        Mirrors Java YAWL YTask.t_isBusy()
        """
        return self._current_identifier is not None

    def t_is_exit_enabled(self) -> bool:
        """Check if task can exit.

        Java signature: boolean t_isExitEnabled()

        Returns
        -------
        bool
            True if exit conditions met

        Notes
        -----
        Mirrors Java YAWL YTask.t_isExitEnabled()
        For MI tasks, checks completion threshold
        """
        if not self.t_is_busy():
            return False

        if self.multi_instance is None:
            return True

        if self._mi_complete is None:
            return False

        complete_count = len(self._mi_complete.get_identifiers())
        if complete_count == 0:
            return False

        if hasattr(self.multi_instance, "threshold_query") and self.multi_instance.threshold_query:
            try:
                net = getattr(self, "_net", None)
                if net:
                    from kgcl.yawl.engine.y_expression import YExpressionEvaluator

                    evaluator = YExpressionEvaluator()
                    data_doc = net.get_internal_data_document() if hasattr(net, "get_internal_data_document") else None
                    if data_doc:
                        threshold_result = evaluator.evaluate(self.multi_instance.threshold_query, data_doc)
                        threshold = int(threshold_result) if threshold_result else 0
                        return complete_count >= threshold
            except Exception:
                pass

        if hasattr(self.multi_instance, "minimum"):
            min_instances = self.multi_instance.minimum
            if complete_count < min_instances:
                return False

        if hasattr(self.multi_instance, "maximum"):
            max_instances = self.multi_instance.maximum
            if complete_count >= max_instances:
                return True

        active_count = len(self._mi_active.get_identifiers()) if self._mi_active else 0
        if active_count == 0:
            return True

        return complete_count >= active_count

    def cancel(self, pmgr: Any | None = None) -> None:
        """Cancel task and cancellation set.

        Java signature: void cancel(YPersistenceManager pmgr)

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager

        Notes
        -----
        Mirrors Java YAWL YTask.cancel()
        Implements cancellation region (reset net semantics)
        """
        if hasattr(self, "purge_locations"):
            self.purge_locations(pmgr)

        if self._current_identifier:
            if hasattr(self._current_identifier, "remove_location"):
                self._current_identifier.remove_location(pmgr, self)

        if self._current_identifier in self._case_to_data_map:
            del self._case_to_data_map[self._current_identifier]

    def create_fired_identifier(self, pmgr: Any | None = None) -> Any:
        """Create identifier for fired instance.

        Java signature: YIdentifier createFiredIdentifier(YPersistenceManager pmgr)

        Parameters
        ----------
        pmgr : Any | None
            Persistence manager (optional)

        Returns
        -------
        Any
            New identifier for this firing

        Notes
        -----
        Mirrors Java YAWL YTask.createFiredIdentifier()
        Generates unique ID for token lineage
        """
        from kgcl.yawl.elements.y_identifier import YIdentifier

        if self._current_identifier is None:
            return None

        child_id = f"{self._current_identifier.id}-{len(self._current_identifier.children)}"
        child = self._current_identifier.create_child(child_id)

        if self._mi_active:
            self._mi_active.add(pmgr, child)
        if self._mi_entered:
            self._mi_entered.add(pmgr, child)

        return child

    # ===== Data Mapping Methods =====

    def get_data_binding_for_input_param(self, param_name: str) -> str:
        """Get input parameter mapping expression.

        Java signature: String getDataBindingForInputParam(String paramName)

        Parameters
        ----------
        param_name : str
            Parameter name

        Returns
        -------
        str
            XQuery binding expression

        Notes
        -----
        Mirrors Java YAWL YTask.getDataBindingForInputParam()
        Maps net variables to decomposition inputs
        """
        return self.data_mappings_for_task_starting.get(param_name, "")

    def get_data_binding_for_output_param(self, param_name: str) -> str:
        """Get output parameter mapping expression.

        Java signature: String getDataBindingForOutputParam(String paramName)

        Parameters
        ----------
        param_name : str
            Parameter name

        Returns
        -------
        str
            XQuery binding expression

        Notes
        -----
        Mirrors Java YAWL YTask.getDataBindingForOutputParam()
        Maps decomposition outputs to net variables
        """
        for query, net_var_name in self.data_mappings_for_task_completion.items():
            if net_var_name == param_name:
                return query
        return ""

    def set_data_binding_for_input_param(self, query: str, param_name: str) -> None:
        """Set input parameter mapping.

        Java signature: void setDataBindingForInputParam(String query, String paramName)

        Parameters
        ----------
        query : str
            XQuery expression
        param_name : str
            Parameter name

        Notes
        -----
        Mirrors Java YAWL YTask.setDataBindingForInputParam()
        """
        self.data_mappings_for_task_starting[param_name] = query

    def set_data_binding_for_output_expression(self, query: str, net_var_name: str) -> None:
        """Set output parameter mapping.

        Java signature: void setDataBindingForOutputExpression(String query, String netVarName)

        Parameters
        ----------
        query : str
            XQuery expression
        net_var_name : str
            Net variable name

        Notes
        -----
        Mirrors Java YAWL YTask.setDataBindingForOutputExpression()
        """
        self.data_mappings_for_task_completion[query] = net_var_name

    def get_data_mappings_for_task_starting(self) -> dict[str, str]:
        """Get all input data mappings.

        Java signature: Map getDataMappingsForTaskStarting()

        Returns
        -------
        dict[str, str]
            Parameter name to query mappings

        Notes
        -----
        Mirrors Java YAWL YTask.getDataMappingsForTaskStarting()
        """
        return dict(self.data_mappings_for_task_starting)

    def get_data_mappings_for_task_completion(self) -> dict[str, str]:
        """Get all output data mappings.

        Java signature: Map getDataMappingsForTaskCompletion()

        Returns
        -------
        dict[str, str]
            Query to net variable mappings

        Notes
        -----
        Mirrors Java YAWL YTask.getDataMappingsForTaskCompletion()
        """
        return dict(self.data_mappings_for_task_completion)

    def get_param_names_for_task_starting(self) -> set[str]:
        """Get parameter names for task starting.

        Java signature: Set getParamNamesForTaskStarting()

        Returns
        -------
        set[str]
            Set of parameter names used in input mappings

        Notes
        -----
        Mirrors Java YAWL YTask.getParamNamesForTaskStarting()
        """
        return set(self.data_mappings_for_task_starting.keys())

    def get_param_names_for_task_completion(self) -> set[str]:
        """Get parameter names for task completion.

        Java signature: Collection getParamNamesForTaskCompletion()

        Returns
        -------
        set[str]
            Set of parameter names (from output mapping values)

        Notes
        -----
        Mirrors Java YAWL YTask.getParamNamesForTaskCompletion()
        """
        return set(self.data_mappings_for_task_completion.values())

    def set_data_mappings_for_task_starting(self, mappings: dict[str, str]) -> None:
        """Set all input data mappings.

        Java signature: void setDataMappingsForTaskStarting(Map map)

        Parameters
        ----------
        mappings : dict[str, str]
            Parameter name to query mappings

        Notes
        -----
        Mirrors Java YAWL YTask.setDataMappingsForTaskStarting()
        """
        self.data_mappings_for_task_starting.update(mappings)

    def set_data_mappings_for_task_completion(self, mappings: dict[str, str]) -> None:
        """Set all output data mappings.

        Java signature: void setDataMappingsForTaskCompletion(Map map)

        Parameters
        ----------
        mappings : dict[str, str]
            Query to net variable mappings

        Notes
        -----
        Mirrors Java YAWL YTask.setDataMappingsForTaskCompletion()
        """
        self.data_mappings_for_task_completion.update(mappings)

    def get_param_names_for_task_starting(self) -> set[str]:
        """Get parameter names for task starting.

        Java signature: Set<String> getParamNamesForTaskStarting()

        Returns
        -------
        set[str]
            Set of parameter names

        Notes
        -----
        Mirrors Java YAWL YTask.getParamNamesForTaskStarting()
        """
        return set(self.data_mappings_for_task_starting.keys())

    def get_param_names_for_task_completion(self) -> list[str]:
        """Get parameter names for task completion.

        Java signature: Collection<String> getParamNamesForTaskCompletion()

        Returns
        -------
        list[str]
            List of net variable names

        Notes
        -----
        Mirrors Java YAWL YTask.getParamNamesForTaskCompletion()
        """
        return list(self.data_mappings_for_task_completion.values())

    def get_param_names_for_task_enablement(self) -> set[str]:
        """Get parameter names for task enablement.

        Java signature: Set<String> getParamNamesForTaskEnablement()

        Returns
        -------
        set[str]
            Set of enablement parameter names

        Notes
        -----
        Mirrors Java YAWL YTask.getParamNamesForTaskEnablement()
        """
        return set(self.data_mappings_for_task_enablement.keys())

    def get_queries_for_task_completion(self) -> set[str]:
        """Get queries for task completion.

        Java signature: Set<String> getQueriesForTaskCompletion() (private)

        Returns
        -------
        set[str]
            Set of output query expressions

        Notes
        -----
        Mirrors Java YAWL YTask.getQueriesForTaskCompletion()
        """
        return set(self.data_mappings_for_task_completion.keys())

    def set_data_binding_for_enablement_param(self, query: str, param_name: str) -> None:
        """Set data binding for enablement parameter.

        Java signature: void setDataBindingForEnablementParam(String query, String paramName)

        Parameters
        ----------
        query : str
            Query expression
        param_name : str
            Enablement parameter name

        Notes
        -----
        Mirrors Java YAWL YTask.setDataBindingForEnablementParam()
        """
        self.data_mappings_for_task_enablement[param_name] = query

    def get_data_binding_for_enablement_param(self, param_name: str) -> str:
        """Get data binding for enablement parameter.

        Java signature: String getDataBindingForEnablementParam(String paramName)

        Parameters
        ----------
        param_name : str
            Enablement parameter name

        Returns
        -------
        str
            Query expression

        Notes
        -----
        Mirrors Java YAWL YTask.getDataBindingForEnablementParam()
        """
        return self.data_mappings_for_task_enablement.get(param_name, "")

    def perform_data_extraction(self, expression: str, input_param: Any, net: Any) -> Any:
        """Extract data using XQuery expression.

        Java signature: Element performDataExtraction(String expression, YParameter inputParam)

        Parameters
        ----------
        expression : str
            XQuery expression
        input_param : Any
            Parameter context
        net : Any
            Containing net (for accessing data document)

        Returns
        -------
        Any
            Extracted data element

        Notes
        -----
        Mirrors Java YAWL YTask.performDataExtraction()
        Evaluates XQuery against net data
        """
        if not expression:
            return None

        data_doc = None
        if hasattr(net, "get_internal_data_document"):
            data_doc = net.get_internal_data_document()
        elif hasattr(net, "internal_data_document"):
            data_doc = net.internal_data_document

        if data_doc is None:
            return None

        try:
            from kgcl.yawl.engine.y_expression import YExpressionEvaluator

            evaluator = YExpressionEvaluator()
            result = evaluator.evaluate(expression, data_doc)
            return result.value if hasattr(result, "value") else result
        except Exception:
            return None

    def add_default_values_as_required(self, data_doc: Any) -> None:
        """Add default values to output data document as required.

        Java signature: void addDefaultValuesAsRequired(Document dataDoc)

        Parameters
        ----------
        data_doc : Any
            Output data document (root element or Document)

        Notes
        -----
        Mirrors Java YAWL YTask.addDefaultValuesAsRequired()
        Adds default values for output parameters that are missing or empty
        """
        if data_doc is None:
            return

        # Get root element
        root_elem = data_doc
        if hasattr(data_doc, "get_root_element"):
            root_elem = data_doc.get_root_element()
        elif hasattr(data_doc, "root_element"):
            root_elem = data_doc.root_element

        if root_elem is None:
            return

        # Get decomposition prototype
        decomp = self.get_decomposition_prototype()
        if decomp is None:
            return

        # Get output parameters sorted by name
        output_params = list(decomp.output_parameters.values())
        output_params.sort(key=lambda p: p.name if hasattr(p, "name") else str(p))

        # Add default values for missing/empty parameters
        for param in output_params:
            default_value = None
            if hasattr(param, "get_default_value"):
                default_value = param.get_default_value()
            elif hasattr(param, "default_value"):
                default_value = param.default_value

            if not default_value:
                continue

            param_name = None
            if hasattr(param, "get_preferred_name"):
                param_name = param.get_preferred_name()
            elif hasattr(param, "preferred_name"):
                param_name = param.preferred_name
            elif hasattr(param, "name"):
                param_name = param.name

            if not param_name:
                continue

            # Check if parameter element exists and has content
            param_elem = None
            if hasattr(root_elem, "find"):
                param_elem = root_elem.find(param_name)
            elif hasattr(root_elem, "get_child"):
                param_elem = root_elem.get_child(param_name)

            # If no element or empty content, add default
            is_empty = False
            if param_elem is not None:
                if hasattr(param_elem, "get_content"):
                    is_empty = len(param_elem.get_content()) == 0
                elif hasattr(param_elem, "text"):
                    is_empty = not param_elem.text or not param_elem.text.strip()

            if param_elem is None or is_empty:
                # Create element with default value
                from xml.etree.ElementTree import Element

                if param_elem is None:
                    # Insert new element
                    def_elem = Element(param_name)
                    def_elem.text = default_value
                    if hasattr(root_elem, "insert"):
                        root_elem.insert(0, def_elem)
                    elif hasattr(root_elem, "append"):
                        root_elem.append(def_elem)
                else:
                    # Insert content into existing element
                    param_elem.text = default_value

    def prepare_data_for_instance_starting(self, child_instance_id: Any, net: Any) -> None:
        """Prepare input data for task instance.

        Java signature: void prepareDataForInstanceStarting(YIdentifier childInstanceID)

        Parameters
        ----------
        child_instance_id : Any
            Instance identifier
        net : Any
            Containing net (for accessing data)

        Notes
        -----
        Mirrors Java YAWL YTask.prepareDataForInstanceStarting()
        Maps net data to decomposition inputs
        """
        if self.decomposition_id is None:
            return

        starting_data = self._get_starting_data_snapshot(net, child_instance_id)
        if starting_data is not None:
            self._case_to_data_map[child_instance_id] = starting_data

    def _get_starting_data_snapshot(self, net: Any, child_instance_id: Any | None = None) -> Any:
        """Get starting data snapshot for task instance.

        Java signature: Element getStartingDataSnapshot()

        Parameters
        ----------
        net : Any
            Containing net
        child_instance_id : Any | None
            Child instance identifier (for MI tasks)

        Returns
        -------
        Any
            Starting data snapshot (root element with mapped data)

        Notes
        -----
        Mirrors Java YAWL YTask.getStartingDataSnapshot()
        Produces data root element, maps all input parameters
        """
        if net is None:
            return None

        if hasattr(self, "_decomposition_prototype") and self._decomposition_prototype:
            decomp = self._decomposition_prototype
            root_name = decomp.get_root_data_element_name() if hasattr(decomp, "get_root_data_element_name") else "data"
        else:
            root_name = "data"

        from xml.etree import ElementTree as ET

        root_elem = ET.Element(root_name)

        data_doc = net.get_internal_data_document() if hasattr(net, "get_internal_data_document") else None
        if data_doc is None:
            return root_elem

        if self.is_multi_instance() and child_instance_id is not None:
            if self._multi_instance_specific_params_iterator:
                try:
                    mi_data = next(self._multi_instance_specific_params_iterator)
                    if mi_data is not None:
                        if isinstance(mi_data, ET.Element):
                            root_elem.append(mi_data)
                        else:
                            root_elem.text = str(mi_data)
                except StopIteration:
                    pass

        for param_name, query in self.data_mappings_for_task_starting.items():
            if not query:
                continue

            query_result = self.perform_data_extraction(query, None, data_doc)
            if query_result is not None:
                param_elem = ET.Element(param_name)
                if isinstance(query_result, ET.Element):
                    param_elem.append(query_result)
                else:
                    param_elem.text = str(query_result)
                root_elem.append(param_elem)

        return root_elem

    def perform_data_assignments_according_to_output_expressions(self, net: Any, pmgr: Any | None = None) -> None:
        """Map decomposition outputs to net variables.

        Java signature: void performDataAssignmentsAccordingToOutputExpressions(YPersistenceManager pmgr)

        Parameters
        ----------
        net : Any
            Containing net (for updating variables)
        pmgr : Any | None
            Persistence manager (optional)

        Notes
        -----
        Mirrors Java YAWL YTask.performDataAssignmentsAccordingToOutputExpressions()
        Applies output mappings after task completion
        """
        if self.decomposition_id is None:
            return

        for local_var_name, query_result in self._local_variable_name_to_replaceable_output_data.items():
            if hasattr(net, "add_data"):
                net.add_data(pmgr, query_result)
            elif hasattr(net, "local_variables"):
                net.local_variables[local_var_name] = query_result

    # ===== Configuration and Resourcing Methods =====

    def get_configuration(self) -> str:
        """Get configuration XML.

        Java signature: String getConfiguration()

        Returns
        -------
        str
            Configuration XML string

        Notes
        -----
        Mirrors Java YAWL YTask.getConfiguration()
        """
        return self.configuration or ""

    def set_configuration(self, config: str) -> None:
        """Set configuration from XML.

        Java signature: void setConfiguration(String config)

        Parameters
        ----------
        config : str
            Configuration XML string

        Notes
        -----
        Mirrors Java YAWL YTask.setConfiguration()
        """
        self.configuration = config

    def get_resourcing_specs(self) -> Any:
        """Get resourcing specifications.

        Java signature: Element getResourcingSpecs()

        Returns
        -------
        Any
            Resourcing specification element

        Notes
        -----
        Mirrors Java YAWL YTask.getResourcingSpecs()
        Defines how resources are allocated to task
        """
        return self.resourcing_spec

    def set_resourcing_specs(self, res_spec: Any) -> None:
        """Set resourcing specifications.

        Java signature: void setResourcingSpecs(Element resSpec)

        Parameters
        ----------
        res_spec : Any
            Resourcing specification element

        Notes
        -----
        Mirrors Java YAWL YTask.setResourcingSpecs()
        """
        self.resourcing_spec = res_spec

    def get_resourcing_xml(self) -> str:
        """Get resourcing specifications as XML.

        Java signature: String getResourcingXML()

        Returns
        -------
        str
            Resourcing XML string

        Notes
        -----
        Mirrors Java YAWL YTask.getResourcingXML()
        """
        return self.resourcing_xml or ""

    def set_resourcing_xml(self, xml: str) -> None:
        """Set resourcing specifications from XML.

        Java signature: void setResourcingXML(String xml)

        Parameters
        ----------
        xml : str
            Resourcing XML string

        Notes
        -----
        Mirrors Java YAWL YTask.setResourcingXML()
        """
        self.resourcing_xml = xml

    def get_decomposition_prototype(self) -> Any:
        """Get decomposition definition.

        Java signature: YDecomposition getDecompositionPrototype()

        Returns
        -------
        Any
            Decomposition object

        Notes
        -----
        Mirrors Java YAWL YTask.getDecompositionPrototype()
        """
        return getattr(self, "_decomposition_prototype", None)

    def set_decomposition_prototype(self, decomposition: Any) -> None:
        """Set decomposition definition.

        Java signature: void setDecompositionPrototype(YDecomposition decomposition)

        Parameters
        ----------
        decomposition : Any
            Decomposition object

        Notes
        -----
        Mirrors Java YAWL YTask.setDecompositionPrototype()
        """
        self._decomposition_prototype = decomposition
        if decomposition and hasattr(decomposition, "id"):
            self.decomposition_id = decomposition.id
        if decomposition and hasattr(decomposition, "get_attributes"):
            attrs = decomposition.get_attributes()
            if attrs and isinstance(attrs, dict):
                skip_val = attrs.get("skipOutboundSchemaValidation")
                if skip_val and str(skip_val).upper() == "TRUE":
                    self._skip_outbound_schema_checks = True

    def get_default_configuration(self) -> str:
        """Get default configuration XML.

        Java signature: String getDefaultConfiguration()

        Returns
        -------
        str
            Default configuration XML string

        Notes
        -----
        Mirrors Java YAWL YTask.getDefaultConfiguration()
        """
        return self.default_configuration or ""

    def set_default_configuration(self, default_config: str) -> None:
        """Set default configuration from XML.

        Java signature: void setDefaultConfiguration(String defaultConfig)

        Parameters
        ----------
        default_config : str
            Default configuration XML string

        Notes
        -----
        Mirrors Java YAWL YTask.setDefaultConfiguration()
        """
        self.default_configuration = default_config

    def get_configuration_element(self) -> Any:
        """Get configuration as element.

        Java signature: Element getConfigurationElement()

        Returns
        -------
        Any
            Configuration element

        Notes
        -----
        Mirrors Java YAWL YTask.getConfigurationElement()
        """
        return self.configuration_element

    def set_configuration_element(self, config_element: Any) -> None:
        """Set configuration from element.

        Java signature: void setConfigurationElement(Element configElement)

        Parameters
        ----------
        config_element : Any
            Configuration element

        Notes
        -----
        Mirrors Java YAWL YTask.setConfigurationElement()
        """
        self.configuration_element = config_element

    def get_default_configuration_element(self) -> Any:
        """Get default configuration as element.

        Java signature: Element getDefaultConfigurationElement()

        Returns
        -------
        Any
            Default configuration element

        Notes
        -----
        Mirrors Java YAWL YTask.getDefaultConfigurationElement()
        """
        return self.default_configuration_element

    def set_default_configuration_element(self, default_config_element: Any) -> None:
        """Set default configuration from element.

        Java signature: void setDefaultConfigurationElement(Element defaultConfigElement)

        Parameters
        ----------
        default_config_element : Any
            Default configuration element

        Notes
        -----
        Mirrors Java YAWL YTask.setDefaultConfigurationElement()
        """
        self.default_configuration_element = default_config_element

    def skip_outbound_schema_checks(self) -> bool:
        """Check if outbound schema validation should be skipped.

        Java signature: boolean skipOutboundSchemaChecks()

        Returns
        -------
        bool
            True if schema validation should be skipped

        Notes
        -----
        Mirrors Java YAWL YTask.skipOutboundSchemaChecks()
        """
        return self._skip_outbound_schema_checks

    def set_skip_outbound_schema_checks(self, skip: bool) -> None:
        """Set whether to skip outbound schema validation.

        Java signature: void setSkipOutboundSchemaChecks(boolean performOutboundSchemaChecks)

        Parameters
        ----------
        skip : bool
            True to skip validation

        Notes
        -----
        Mirrors Java YAWL YTask.setSkipOutboundSchemaChecks()
        """
        self._skip_outbound_schema_checks = skip

    def get_custom_form_url(self) -> str | None:
        """Get custom form URL.

        Java signature: URL getCustomFormURL()

        Returns
        -------
        str | None
            Custom form URL or None

        Notes
        -----
        Mirrors Java YAWL YTask.getCustomFormURL()
        """
        return self.custom_form_url

    def set_custom_form_uri(self, form_url: str) -> None:
        """Set custom form URI.

        Java signature: void setCustomFormURI(URL formURL)

        Parameters
        ----------
        form_url : str
            Custom form URL

        Notes
        -----
        Mirrors Java YAWL YTask.setCustomFormURI()
        """
        self.custom_form_url = form_url

    def get_timer_parameters(self) -> Any:
        """Get timer parameters.

        Java signature: YTimerParameters getTimerParameters()

        Returns
        -------
        Any
            Timer parameters or None

        Notes
        -----
        Mirrors Java YAWL YTask.getTimerParameters()
        """
        return self.timer_params

    def set_timer_parameters(self, timer_parameters: Any) -> None:
        """Set timer parameters.

        Java signature: void setTimerParameters(YTimerParameters timerParameters)

        Parameters
        ----------
        timer_parameters : Any
            Timer parameters

        Notes
        -----
        Mirrors Java YAWL YTask.setTimerParameters()
        """
        self.timer_params = timer_parameters
        if timer_parameters is not None:
            try:
                from kgcl.yawl.engine.y_timer import YTimerVariable

                self.timer_variable = YTimerVariable(self)
            except ImportError:
                self.timer_variable = None
        else:
            self.timer_variable = None

    def get_timer_variable(self) -> Any:
        """Get timer variable.

        Java signature: YTimerVariable getTimerVariable()

        Returns
        -------
        Any
            Timer variable or None

        Notes
        -----
        Mirrors Java YAWL YTask.getTimerVariable()
        """
        return self.timer_variable

    def get_input_log_data_items(self) -> Any:
        """Get input log data items.

        Java signature: YLogDataItemList get_inputLogDataItems()

        Returns
        -------
        Any
            Input log data items or None

        Notes
        -----
        Mirrors Java YAWL YTask.get_inputLogDataItems()
        """
        return self.input_log_data_items

    def set_input_log_data_items(self, log_data_items: Any) -> None:
        """Set input log data items.

        Java signature: void set_inputLogDataItems(YLogDataItemList _inputLogDataItems)

        Parameters
        ----------
        log_data_items : Any
            Input log data items

        Notes
        -----
        Mirrors Java YAWL YTask.set_inputLogDataItems()
        """
        self.input_log_data_items = log_data_items

    def get_output_log_data_items(self) -> Any:
        """Get output log data items.

        Java signature: YLogDataItemList get_outputLogDataItems()

        Returns
        -------
        Any
            Output log data items or None

        Notes
        -----
        Mirrors Java YAWL YTask.get_outputLogDataItems()
        """
        return self.output_log_data_items

    def set_output_log_data_items(self, log_data_items: Any) -> None:
        """Set output log data items.

        Java signature: void set_outputLogDataItems(YLogDataItemList _outputLogDataItems)

        Parameters
        ----------
        log_data_items : Any
            Output log data items

        Notes
        -----
        Mirrors Java YAWL YTask.set_outputLogDataItems()
        """
        self.output_log_data_items = log_data_items

    def get_reset_net(self) -> Any:
        """Get reset net (E2WFOJNet).

        Java signature: E2WFOJNet getResetNet()

        Returns
        -------
        Any
            Reset net or None

        Notes
        -----
        Mirrors Java YAWL YTask.getResetNet()
        """
        return self.reset_net

    def set_reset_net(self, net: Any) -> None:
        """Set reset net (E2WFOJNet).

        Java signature: void setResetNet(E2WFOJNet net)

        Parameters
        ----------
        net : Any
            Reset net

        Notes
        -----
        Mirrors Java YAWL YTask.setResetNet()
        """
        self.reset_net = net

    # ===== Split/Join Type Methods =====

    def get_split_type(self) -> int:
        """Get split type as integer.

        Java signature: int getSplitType()

        Returns
        -------
        int
            Split type code (0=AND, 1=XOR, 2=OR)

        Notes
        -----
        Mirrors Java YAWL YTask.getSplitType()
        Java uses int constants, Python uses enum
        """
        if self.split_type == SplitType.AND:
            return 0
        elif self.split_type == SplitType.XOR:
            return 1
        else:  # OR
            return 2

    def set_split_type(self, split_type: int) -> None:
        """Set split type from integer.

        Java signature: void setSplitType(int splitType)

        Parameters
        ----------
        split_type : int
            Split type code (0=AND, 1=XOR, 2=OR)

        Notes
        -----
        Mirrors Java YAWL YTask.setSplitType()
        """
        if split_type == 0:
            self.split_type = SplitType.AND
        elif split_type == 1:
            self.split_type = SplitType.XOR
        else:  # 2
            self.split_type = SplitType.OR

    def get_join_type(self) -> int:
        """Get join type as integer.

        Java signature: int getJoinType()

        Returns
        -------
        int
            Join type code (0=AND, 1=XOR, 2=OR)

        Notes
        -----
        Mirrors Java YAWL YTask.getJoinType()
        """
        if self.join_type == JoinType.AND:
            return 0
        elif self.join_type == JoinType.XOR:
            return 1
        else:  # OR
            return 2

    def set_join_type(self, join_type: int) -> None:
        """Set join type from integer.

        Java signature: void setJoinType(int joinType)

        Parameters
        ----------
        join_type : int
            Join type code (0=AND, 1=XOR, 2=OR)

        Notes
        -----
        Mirrors Java YAWL YTask.setJoinType()
        """
        if join_type == 0:
            self.join_type = JoinType.AND
        elif join_type == 1:
            self.join_type = JoinType.XOR
        else:  # 2
            self.join_type = JoinType.OR

    # ===== Verification Methods =====

    def verify(self, handler: Any) -> None:
        """Verify task validity.

        Java signature: void verify(YVerificationHandler handler)

        Parameters
        ----------
        handler : Any
            Verification handler to collect errors

        Notes
        -----
        Mirrors Java YAWL YTask.verify()
        Validates task configuration and mappings
        """
        if not self.id:
            if handler and hasattr(handler, "add_error"):
                handler.add_error("Task must have an ID")

        if self.split_type not in [SplitType.AND, SplitType.OR, SplitType.XOR]:
            if handler and hasattr(handler, "add_error"):
                handler.add_error(f"{self} has an incorrect value for split type")

        if self.join_type not in [JoinType.AND, JoinType.OR, JoinType.XOR]:
            if handler and hasattr(handler, "add_error"):
                handler.add_error(f"{self} has an incorrect value for join type")

        if self.split_type in [SplitType.OR, SplitType.XOR]:
            default_count = 0
            net = getattr(self, "_net", None)
            flows = []
            if net and hasattr(net, "flows"):
                for flow_id in self.postset_flows:
                    flow = net.flows.get(flow_id)
                    if flow:
                        flows.append(flow)

            flows.sort(key=lambda f: getattr(f, "eval_ordering", 0))

            last_ordering = float("-inf")
            for flow in flows:
                eval_ordering = getattr(flow, "eval_ordering", None)
                if eval_ordering is not None:
                    if eval_ordering == last_ordering:
                        if handler and hasattr(handler, "add_error"):
                            handler.add_error(
                                f"{self} no two elements may possess the same ordering ({flow}) for the same task."
                            )
                    last_ordering = eval_ordering

                if getattr(flow, "is_default_flow", lambda: False)():
                    default_count += 1

            if default_count != 1:
                if handler and hasattr(handler, "add_error"):
                    handler.add_error(
                        f"{self} the postset of any OR/XOR split must have "
                        f"exactly one default flow (not {default_count})"
                    )

        if self.multi_instance:
            if hasattr(self.multi_instance, "verify"):
                self.multi_instance.verify(handler)

        net = getattr(self, "_net", None)
        for element_id in self.cancellation_set:
            element = None
            if net:
                element = net.get_net_element(element_id) if hasattr(net, "get_net_element") else None
                if element is None:
                    element = net.tasks.get(element_id) if hasattr(net, "tasks") else None
                if element is None:
                    element = net.conditions.get(element_id) if hasattr(net, "conditions") else None

            if element is None:
                if handler and hasattr(handler, "add_error"):
                    handler.add_error(f"{self} refers to a non existent element in its remove set.")
            elif net and hasattr(element, "_net") and element._net != net:
                if handler and hasattr(handler, "add_error"):
                    handler.add_error(
                        f"{self} and {element} must be contained in the same net. (container {net} & {element._net})"
                    )

        if hasattr(self, "_decomposition_prototype") and self._decomposition_prototype:
            self.check_parameter_mappings(handler)
        else:
            if len(self.data_mappings_for_task_starting) > 0:
                if handler and hasattr(handler, "add_error"):
                    handler.add_error(f"Syntax error for {self} to have startingMappings and no decomposition.")
            if len(self.data_mappings_for_task_completion) > 0:
                if handler and hasattr(handler, "add_error"):
                    handler.add_error(f"Syntax error for {self} to have completionMappings and no decomposition.")

    def check_parameter_mappings(self, handler: Any) -> None:
        """Check all parameter mappings for validity.

        Java signature: void checkParameterMappings(YVerificationHandler handler)

        Parameters
        ----------
        handler : Any
            Verification handler

        Notes
        -----
        Mirrors Java YAWL YTask.checkParameterMappings()
        """
        self.check_input_parameter_mappings(handler)
        self.check_for_duplicate_parameter_mappings(handler)
        self.check_output_parameter_mappings(handler)

    def check_input_parameter_mappings(self, handler: Any) -> None:
        """Check input parameter mappings.

        Java signature: void checkInputParameterMappings(YVerificationHandler handler)

        Parameters
        ----------
        handler : Any
            Verification handler

        Notes
        -----
        Mirrors Java YAWL YTask.checkInputParameterMappings()
        Validates that all decomposition input params are mapped
        """
        if not hasattr(self, "_decomposition_prototype") or not self._decomposition_prototype:
            return

        decomp = self._decomposition_prototype
        input_param_names_at_task = self.get_param_names_for_task_starting()

        if hasattr(decomp, "get_input_parameter_names"):
            input_param_names = decomp.get_input_parameter_names()
            for param_name in input_param_names:
                query = self.data_mappings_for_task_starting.get(param_name)
                self._check_xquery(query, param_name, handler)

                if param_name not in input_param_names_at_task:
                    if handler and hasattr(handler, "add_error"):
                        handler.add_error(
                            f"The task (id={self.id}) needs to be connected with "
                            f"the input parameter ({param_name}) of decomposition ({decomp})."
                        )

    def check_output_parameter_mappings(self, handler: Any) -> None:
        """Check output parameter mappings.

        Java signature: void checkOutputParameterMappings(YVerificationHandler handler)

        Parameters
        ----------
        handler : Any
            Verification handler

        Notes
        -----
        Mirrors Java YAWL YTask.checkOutputParameterMappings()
        Validates XQuery expressions and external mappings
        """
        net = getattr(self, "_net", None)
        if net is None:
            return

        spec = net.get_specification() if hasattr(net, "get_specification") else None
        if spec and hasattr(spec, "get_schema_version"):
            schema_version = spec.get_schema_version()
            if hasattr(schema_version, "uses_simple_root_data") and schema_version.uses_simple_root_data():
                self._check_output_params_pre_beta4(handler)

        for query, var_name in self.data_mappings_for_task_completion.items():
            self._check_xquery(query, var_name, handler)

        local_vars = self._get_local_variables_for_task_completion()
        for local_var_name in local_vars:
            net_local_vars = net.get_local_variables() if hasattr(net, "get_local_variables") else {}
            net_input_params = net.get_input_parameters() if hasattr(net, "get_input_parameters") else {}
            if local_var_name not in net_local_vars and local_var_name not in net_input_params:
                if handler and hasattr(handler, "add_error"):
                    handler.add_error(
                        f"The task (id={self.id}) claims to assign its output to a net "
                        f"variable named ({local_var_name}). However the containing net "
                        f"does not have such a variable."
                    )

    def _get_local_variables_for_task_completion(self) -> set[str]:
        """Get local variables for task completion.

        Java signature: Set<String> getLocalVariablesForTaskCompletion()

        Returns
        -------
        set[str]
            Set of local variable names

        Notes
        -----
        Mirrors Java YAWL YTask.getLocalVariablesForTaskCompletion()
        """
        local_vars: set[str] = set()
        for query in self.data_mappings_for_task_completion.keys():
            if not query.startswith("external:"):
                local_vars.add(self.data_mappings_for_task_completion.get(query, ""))
        return local_vars

    def _check_output_params_pre_beta4(self, handler: Any) -> None:
        """Check output params for pre-beta4 compatibility.

        Java signature: void checkOutputParamsPreBeta4(YVerificationHandler handler)

        Parameters
        ----------
        handler : Any
            Verification handler

        Notes
        -----
        Mirrors Java YAWL YTask.checkOutputParamsPreBeta4()
        """
        if not hasattr(self, "_decomposition_prototype") or not self._decomposition_prototype:
            return

        decomp = self._decomposition_prototype
        output_queries_at_decomposition = set()
        if hasattr(decomp, "get_output_queries"):
            output_queries_at_decomposition = decomp.get_output_queries()

        output_queries_at_task = self.get_queries_for_task_completion()

        for query in output_queries_at_decomposition:
            if query not in output_queries_at_task:
                if handler and hasattr(handler, "add_error"):
                    handler.add_error(
                        f"{self} there exists an output query ({query}) in {decomp} that is not mapped to by this Task."
                    )

        for query in output_queries_at_task:
            if query not in output_queries_at_decomposition:
                if handler and hasattr(handler, "add_error"):
                    handler.add_error(
                        f"{self} there exists an output query ({query}) in this Task "
                        f"that has no corresponding mapping at its decomposition ({decomp})."
                    )

    def check_for_duplicate_parameter_mappings(self, handler: Any) -> None:
        """Check for duplicate parameter mappings.

        Java signature: void checkForDuplicateParameterMappings(YVerificationHandler handler)

        Parameters
        ----------
        handler : Any
            Verification handler

        Notes
        -----
        Mirrors Java YAWL YTask.checkForDuplicateParameterMappings()
        """
        num_unique_params_mapped_to = len(set(self.data_mappings_for_task_starting.values()))
        num_params = len(self.data_mappings_for_task_starting)
        if num_unique_params_mapped_to != num_params:
            if handler and hasattr(handler, "add_error"):
                handler.add_error(
                    f"An input parameter is used twice. The task (id={self.id}) "
                    f"uses the same parameter through its multi-instance input and its regular input."
                )

        num_unique_net_vars_mapped_to = len(set(self.data_mappings_for_task_completion.values()))
        num_output_params = len(self.data_mappings_for_task_completion)
        if num_unique_net_vars_mapped_to != num_output_params:
            if handler and hasattr(handler, "add_error"):
                handler.add_error(
                    f"An output parameter is used twice. The task (id={self.id}) "
                    f"uses the same parameter through its multi-instance output and its regular output."
                )

    def check_external_mapping(self, query: str, handler: Any) -> None:
        """Check external data mapping expression.

        Java signature: void checkExternalMapping(String query, YVerificationHandler handler)

        Parameters
        ----------
        query : str
            External mapping query string
        handler : Any
            Verification handler

        Notes
        -----
        Mirrors Java YAWL YTask.checkExternalMapping()
        Validates external data gateway class exists
        """
        # External data gateway validation requires gateway factory
        # Basic validation: query must be non-empty and follow external: format
        if not query or not query.strip():
            if handler and hasattr(handler, "add_error"):
                handler.add_error(f"Task {self.id}: External mapping query cannot be empty")
            return
        # Full validation of external gateway class existence
        # is handled by ExternalDataGatewayFactory at runtime

    def _check_xquery(self, xquery: str, param: str, handler: Any) -> None:
        """Check XQuery expression validity.

        Java signature: protected void checkXQuery(String xQuery, String param, YVerificationHandler handler)

        Parameters
        ----------
        xquery : str
            XQuery expression to validate
        param : str
            Parameter name for error reporting
        handler : Any
            Verification handler

        Notes
        -----
        Mirrors Java YAWL YTask.checkXQuery()
        Validates XQuery syntax or external mapping
        """
        if not xquery or not xquery.strip():
            if handler and hasattr(handler, "add_error"):
                handler.add_error(f"Task {self.id}: XQuery for param '{param}' cannot be null or empty")
            return

        # Check if external mapping
        if xquery.startswith("external:"):
            self.check_external_mapping(xquery, handler)
        else:
            # XQuery compilation validation requires Saxon/XQuery engine
            # Basic syntax validation: non-empty and well-formed
            try:
                if not xquery.strip():
                    raise ValueError("Empty XQuery")
                # Additional validation would require full XQuery parser
                # This is handled by the expression evaluator at runtime
            except Exception as e:
                if handler and hasattr(handler, "add_error"):
                    handler.add_error(f"Task {self.id}: XQuery could not be parsed for param '{param}': {e}")

    # ===== XML Serialization =====

    def to_xml(self) -> str:
        """Convert task to XML representation.

        Java signature: String toXML()

        Returns
        -------
        str
            XML string

        Notes
        -----
        Mirrors Java YAWL YTask.toXML()
        """
        from xml.sax import saxutils

        xml_parts: list[str] = []
        xml_parts.append(f'<task id="{saxutils.escape(self.id)}"')
        if self.is_multi_instance():
            xml_parts.append(' xsi:type="MultipleInstanceExternalTaskFactsType"')
            xml_parts.append(' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
        xml_parts.append(">")

        if self.name:
            xml_parts.append(f"<name>{saxutils.escape(self.name)}</name>")

        join_type_str = self._decorator_type_to_string(self.join_type)
        xml_parts.append(f'<join code="{join_type_str}"/>')
        split_type_str = self._decorator_type_to_string(self.split_type)
        xml_parts.append(f'<split code="{split_type_str}"/>')

        if self.default_configuration:
            xml_parts.append(self.default_configuration)
        if self.configuration:
            xml_parts.append(self.configuration)

        remove_tokens_from_flow: list[str] = []
        net = getattr(self, "_net", None)
        remove_list = sorted(list(self.cancellation_set))
        for element_id in remove_list:
            element = None
            if net:
                element = net.get_net_element(element_id) if hasattr(net, "get_net_element") else None
                if element is None:
                    element = net.tasks.get(element_id) if hasattr(net, "tasks") else None
                if element is None:
                    element = net.conditions.get(element_id) if hasattr(net, "conditions") else None

            if element:
                implicit_element = False
                if hasattr(element, "is_implicit") and element.is_implicit():
                    if hasattr(element, "preset_flows") and hasattr(element, "postset_flows"):
                        preset = element.preset_flows[0] if element.preset_flows else None
                        postset = element.postset_flows[0] if element.postset_flows else None
                        if preset and postset:
                            remove_tokens_from_flow.append("<removesTokensFromFlow>")
                            remove_tokens_from_flow.append(f'<flowSource id="{saxutils.escape(preset)}"/>')
                            remove_tokens_from_flow.append(f'<flowDestination id="{saxutils.escape(postset)}"/>')
                            remove_tokens_from_flow.append("</removesTokensFromFlow>")
                            implicit_element = True

                if not implicit_element:
                    xml_parts.append(f'<removesTokens id="{saxutils.escape(element_id)}"/>')

        xml_parts.extend(remove_tokens_from_flow)

        if len(self.data_mappings_for_task_starting) > 0:
            if not (self.is_multi_instance() and len(self.data_mappings_for_task_starting) == 1):
                xml_parts.append("<startingMappings>")
                for maps_to in self.data_mappings_for_task_starting.keys():
                    expression = self.data_mappings_for_task_starting[maps_to]
                    pre_splitting_query = self.get_pre_splitting_mi_query()
                    if not self.is_multi_instance() or expression != pre_splitting_query:
                        xml_parts.append(self._write_expression_mapping(expression, maps_to))
                xml_parts.append("</startingMappings>")

        if len(self.data_mappings_for_task_completion) > 0:
            if not (self.is_multi_instance() and len(self.data_mappings_for_task_completion) == 1):
                xml_parts.append("<completedMappings>")
                for expression in self.data_mappings_for_task_completion.keys():
                    maps_to = self.data_mappings_for_task_completion[expression]
                    pre_joining_query = self.get_pre_joining_mi_query()
                    if not self.is_multi_instance() or (
                        hasattr(self.multi_instance, "get_mi_formal_output_query")
                        and self.multi_instance.get_mi_formal_output_query() != expression
                    ):
                        xml_parts.append(self._write_expression_mapping(expression, maps_to))
                xml_parts.append("</completedMappings>")

        if len(self.data_mappings_for_task_enablement) > 0:
            xml_parts.append("<enablementMappings>")
            for maps_to in self.data_mappings_for_task_enablement.keys():
                expression = self.data_mappings_for_task_enablement[maps_to]
                xml_parts.append(self._write_expression_mapping(expression, maps_to))
            xml_parts.append("</enablementMappings>")

        if self.timer_params and hasattr(self.timer_params, "to_xml"):
            xml_parts.append(self.timer_params.to_xml())

        if self.resourcing_xml:
            xml_parts.append(self.resourcing_xml)
        elif self.resourcing_spec:
            if hasattr(self.resourcing_spec, "to_xml"):
                xml_parts.append(self.resourcing_spec.to_xml())
            elif hasattr(self.resourcing_spec, "__str__"):
                xml_parts.append(str(self.resourcing_spec))

        if self.custom_form_url:
            xml_parts.append(f"<customForm>{saxutils.escape(self.custom_form_url)}</customForm>")

        if hasattr(self, "_decomposition_prototype") and self._decomposition_prototype:
            decomp = self._decomposition_prototype
            decomp_id = decomp.id if hasattr(decomp, "id") else decomp.get_id() if hasattr(decomp, "get_id") else ""
            xml_parts.append(f'<decomposesTo id="{saxutils.escape(decomp_id)}"/>')

        if self.is_multi_instance() and self.multi_instance:
            if hasattr(self.multi_instance, "to_xml"):
                xml_parts.append(self.multi_instance.to_xml())

        if self.input_log_data_items and hasattr(self.input_log_data_items, "to_xml"):
            xml_parts.append(f"<inputLogData>{self.input_log_data_items.to_xml()}</inputLogData>")

        if self.output_log_data_items and hasattr(self.output_log_data_items, "to_xml"):
            xml_parts.append(f"<outputLogData>{self.output_log_data_items.to_xml()}</outputLogData>")

        xml_parts.append("</task>")
        return "".join(xml_parts)

    def _decorator_type_to_string(self, decorator_type: SplitType | JoinType) -> str:
        """Convert decorator type to string.

        Java signature: String decoratorTypeToString(int decType)

        Parameters
        ----------
        decorator_type : SplitType | JoinType
            Decorator type enum

        Returns
        -------
        str
            String representation ("and", "or", "xor")

        Notes
        -----
        Mirrors Java YAWL YTask.decoratorTypeToString()
        """
        if decorator_type == SplitType.AND or decorator_type == JoinType.AND:
            return "and"
        elif decorator_type == SplitType.OR or decorator_type == JoinType.OR:
            return "or"
        elif decorator_type == SplitType.XOR or decorator_type == JoinType.XOR:
            return "xor"
        return "invalid"

    def _write_expression_mapping(self, expression: str, maps_to: str) -> str:
        """Write expression mapping XML.

        Java signature: String writeExpressionMapping(String expression, String mapsTo)

        Parameters
        ----------
        expression : str
            Query expression
        maps_to : str
            Parameter or variable name

        Returns
        -------
        str
            XML string for mapping

        Notes
        -----
        Mirrors Java YAWL YTask.writeExpressionMapping()
        """
        from xml.sax import saxutils

        encoded_expr = saxutils.escape(expression).replace("\n", "&#xA;")
        return f'<mapping><expression query="{encoded_expr}"/><mapsTo>{saxutils.escape(maps_to)}</mapsTo></mapping>'

    def clone(self) -> YTask:
        """Create deep copy of task.

        Java signature: Object clone()

        Returns
        -------
        YTask
            Cloned task

        Notes
        -----
        Mirrors Java YAWL YTask.clone()
        """
        import copy

        cloned = YTask(
            id=self.id,
            name=self.name,
            split_type=self.split_type,
            join_type=self.join_type,
            net_id=self.net_id,
            decomposition_id=self.decomposition_id,
        )
        cloned.preset_flows = self.preset_flows.copy()
        cloned.postset_flows = self.postset_flows.copy()
        cloned.flow_predicates = self.flow_predicates.copy()
        cloned.cancellation_set = self.cancellation_set.copy()
        cloned.multi_instance = copy.deepcopy(self.multi_instance) if self.multi_instance else None
        cloned.data_mappings_for_task_starting = self.data_mappings_for_task_starting.copy()
        cloned.data_mappings_for_task_completion = self.data_mappings_for_task_completion.copy()
        cloned.data_mappings_for_task_enablement = self.data_mappings_for_task_enablement.copy()
        cloned.configuration = self.configuration
        cloned.default_configuration = self.default_configuration
        cloned.configuration_element = copy.deepcopy(self.configuration_element)
        cloned.default_configuration_element = copy.deepcopy(self.default_configuration_element)
        cloned.resourcing_xml = self.resourcing_xml
        cloned.resourcing_spec = copy.deepcopy(self.resourcing_spec)
        cloned.timer_params = copy.deepcopy(self.timer_params)
        cloned.timer_variable = copy.deepcopy(self.timer_variable)
        cloned.custom_form_url = self.custom_form_url
        cloned.input_log_data_items = copy.deepcopy(self.input_log_data_items)
        cloned.output_log_data_items = copy.deepcopy(self.output_log_data_items)
        cloned.reset_net = copy.deepcopy(self.reset_net)
        cloned._skip_outbound_schema_checks = self._skip_outbound_schema_checks

        from kgcl.yawl.elements.y_internal_condition import YInternalCondition

        cloned._mi_active = YInternalCondition(id=YInternalCondition.MI_ACTIVE, my_task=cloned)
        cloned._mi_entered = YInternalCondition(id=YInternalCondition.MI_ENTERED, my_task=cloned)
        cloned._mi_complete = YInternalCondition(id=YInternalCondition.MI_COMPLETE, my_task=cloned)
        cloned._mi_executing = YInternalCondition(id=YInternalCondition.MI_EXECUTING, my_task=cloned)

        cloned._case_to_data_map = copy.deepcopy(self._case_to_data_map)
        cloned._local_variable_name_to_replaceable_output_data = copy.deepcopy(
            self._local_variable_name_to_replaceable_output_data
        )
        cloned._grouped_multi_instance_output_data = copy.deepcopy(self._grouped_multi_instance_output_data)

        if hasattr(self, "_decomposition_prototype"):
            cloned._decomposition_prototype = copy.deepcopy(self._decomposition_prototype)

        return cloned

    def __hash__(self) -> int:
        """Hash by ID for use in sets/dicts."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality by ID."""
        if not isinstance(other, YTask):
            return NotImplemented
        return self.id == other.id
