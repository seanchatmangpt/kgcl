"""YAWL exception classes (mirrors Java org.yawlfoundation.yawl.exceptions).

All YAWL-specific exceptions inherit from YAWLException, providing
a consistent exception hierarchy for workflow operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element


class YAWLException(Exception):
    """Base exception for all YAWL operations (mirrors Java YAWLException).

    All YAWL-specific exceptions inherit from this base class,
    allowing catch-all exception handling when needed.

    Parameters
    ----------
    message : str
        Exception message
    cause : Exception | None
        Underlying exception that caused this one

    Examples
    --------
    >>> raise YAWLException("Workflow execution failed")
    >>> raise YStateException("Invalid state transition")
    """

    MESSAGE_NM = "message"

    def __init__(self, message: str = "", cause: Exception | None = None) -> None:
        """Initialize YAWL exception.

        Parameters
        ----------
        message : str
            Exception message
        cause : Exception | None
            Underlying exception
        """
        super().__init__(message)
        self._message = message
        self._cause = cause

    def get_message(self) -> str:
        """Get exception message.

        Returns
        -------
        str
            Exception message

        Notes
        -----
        Java signature: String getMessage()
        """
        return self._message

    def set_message(self, message: str) -> None:
        """Set exception message.

        Parameters
        ----------
        message : str
            New message

        Notes
        -----
        Java signature: void setMessage(String message)
        """
        self._message = message

    def to_xml(self) -> str:
        """Convert exception to XML representation.

        Returns
        -------
        str
            XML string

        Notes
        -----
        Java signature: String toXML()
        """
        class_name = self.__class__.__name__
        return f"<{class_name}>{self._to_xml_guts()}</{class_name}>"

    def _to_xml_guts(self) -> str:
        """Get XML content (subclasses override).

        Returns
        -------
        str
            XML content

        Notes
        -----
        Java signature: protected String toXMLGuts()
        """
        return f"<{self.MESSAGE_NM}>{self._message}</{self.MESSAGE_NM}>"

    @staticmethod
    def unmarshal(exception_doc: ET.ElementTree | Element | str) -> YAWLException:
        """Unmarshal exception from XML document.

        Parameters
        ----------
        exception_doc : ET.ElementTree | Element | str
            XML document, element, or string

        Returns
        -------
        YAWLException
            Unmarshalled exception

        Raises
        ------
        ValueError
            If exception type is unknown

        Notes
        -----
        Java signature: static YAWLException unmarshal(Document exceptionDoc)
        """
        # Parse XML if string
        if isinstance(exception_doc, str):
            root = ET.fromstring(exception_doc)
        elif isinstance(exception_doc, ET.ElementTree):
            root = exception_doc.getroot()
        else:
            root = exception_doc

        exception_type = root.tag

        # Handle specific exception types
        if exception_type == "YDataStateException":
            return YDataStateException.unmarshall(root)
        elif exception_type == "YDataQueryException":
            return YDataQueryException.unmarshall(root)
        elif exception_type == "YDataValidationException":
            return YDataValidationException.unmarshall(root)

        # Create generic exception
        message = YAWLException._parse_message(root)
        if exception_type == "YStateException":
            return YStateException(message)
        elif exception_type == "YQueryException":
            return YQueryException(message)
        elif exception_type == "YPersistenceException":
            return YPersistenceException(message)
        elif exception_type == "YAuthenticationException":
            return YAuthenticationException(message)
        elif exception_type == "YConnectivityException":
            return YConnectivityException(message)
        elif exception_type == "YEngineStateException":
            return YEngineStateException(message)
        elif exception_type == "YExternalDataException":
            return YExternalDataException(message)
        elif exception_type == "YLogException":
            return YLogException(message)
        elif exception_type == "YSchemaBuildingException":
            return YSchemaBuildingException(message)
        elif exception_type == "YSyntaxException":
            return YSyntaxException(message)
        else:
            # Generic YAWLException
            exc = YAWLException(message)
            return exc

    @staticmethod
    def _parse_message(exception_doc: Element) -> str:
        """Parse message from exception document.

        Parameters
        ----------
        exception_doc : Element
            Exception element

        Returns
        -------
        str
            Message text
        """
        message_elem = exception_doc.find(YAWLException.MESSAGE_NM)
        if message_elem is not None and message_elem.text:
            return message_elem.text
        return ""

    def rethrow(self) -> None:
        """Rethrow as specific exception type.

        Raises
        ------
        YStateException
            If this is a YStateException
        YDataStateException
            If this is a YDataStateException
        YQueryException
            If this is a YQueryException
        YPersistenceException
            If this is a YPersistenceException

        Notes
        -----
        Java signature: void rethrow() throws YStateException, YDataStateException, YQueryException, YPersistenceException
        """
        if isinstance(self, YStateException):
            raise self
        elif isinstance(self, YDataStateException):
            raise self
        elif isinstance(self, YQueryException):
            raise self
        elif isinstance(self, YPersistenceException):
            raise self


class YStateException(YAWLException):
    """Exception for invalid state transitions (mirrors Java YStateException).

    Raised when a workflow operation is attempted in an invalid state,
    such as firing a task that is not enabled.

    Examples
    --------
    >>> raise YStateException("Task is not enabled")
    """

    def __init__(self, message: str = "") -> None:
        """Initialize state exception.

        Parameters
        ----------
        message : str
            Exception message
        """
        super().__init__(message)


class YDataStateException(YAWLException):
    """Exception for data state errors (mirrors Java YDataStateException).

    Raised when data operations fail due to invalid state,
    such as query failures or schema validation errors.

    Parameters
    ----------
    query_string : str | None
        XQuery that failed
    queried_data : Element | None
        Data that was queried
    schema : str | None
        Schema XML string
    data_input : Element | None
        Data that failed validation
    xerces_errors : str | None
        Validation error messages
    source : str | None
        Source task/element ID
    message : str
        Exception message

    Examples
    --------
    >>> raise YDataStateException(query="//order", source="ProcessOrder", message="Query returned no results")
    """

    QUERYSTRING_NM = "queryString"
    QUERIEDDATA_NM = "queriedData"
    SCHEMA_NM = "schema"
    DATAINPUT_NM = "dataInput"
    XERCESERRORS_NM = "xercesErrors"
    SOURCE_NM = "source"

    def __init__(
        self,
        query_string: str | None = None,
        queried_data: Element | None = None,
        schema: str | None = None,
        data_input: Element | None = None,
        xerces_errors: str | None = None,
        source: str | None = None,
        message: str = "",
    ) -> None:
        """Initialize data state exception.

        Parameters
        ----------
        query_string : str | None
            XQuery that failed
        queried_data : Element | None
            Data that was queried
        schema : str | None
            Schema XML string
        data_input : Element | None
            Data that failed validation
        xerces_errors : str | None
            Validation error messages
        source : str | None
            Source task/element ID
        message : str
            Exception message
        """
        super().__init__(message)
        self._query_string = query_string
        self._queried_data = queried_data
        self._data_input = data_input
        self._xerces_errors = xerces_errors
        self._source = source

        # Parse schema if provided
        self._schema: Element | None = None
        if schema:
            try:
                self._schema = ET.fromstring(schema)
            except Exception:
                self._schema = None

    def get_message(self) -> str:
        """Get formatted exception message.

        Returns
        -------
        str
            Formatted message with all context

        Notes
        -----
        Java signature: String getMessage()
        """
        from kgcl.yawl.util.xml import jdom_util

        parts = [self._message]
        if self._source:
            parts.append(f"\nTask [{self._source}]")
        if self._query_string:
            parts.append(f"\nXQuery [{self._query_string}]")
        if self._queried_data is not None:
            parts.append(f"\nDocument [{jdom_util.element_to_string(self._queried_data)}]")
        if self._schema is not None:
            parts.append(f"\nSchema for Expected [{jdom_util.element_to_string(self._schema)}]")
        if self._data_input is not None:
            parts.append(f"\nBut received [{jdom_util.element_to_string(self._data_input)}]")
        if self._xerces_errors:
            parts.append(f"\nValidation error message [{self._xerces_errors}]")

        return "".join(parts)

    def get_data_input(self) -> Element | None:
        """Get data input element.

        Returns
        -------
        Element | None
            Data input element

        Notes
        -----
        Java signature: Element get_dataInput()
        """
        return self._data_input

    def get_source(self) -> str | None:
        """Get source task/element ID.

        Returns
        -------
        str | None
            Source ID

        Notes
        -----
        Java signature: Object getSource()
        """
        return self._source

    def get_errors(self) -> str | None:
        """Get validation error messages.

        Returns
        -------
        str | None
            Error messages

        Notes
        -----
        Java signature: String getErrors()
        """
        return self._xerces_errors

    def get_schema(self) -> Element | None:
        """Get schema element.

        Returns
        -------
        Element | None
            Schema element

        Notes
        -----
        Java signature: Element getSchema()
        """
        return self._schema

    def _to_xml_guts(self) -> str:
        """Get XML content with all fields.

        Returns
        -------
        str
            XML content

        Notes
        -----
        Java signature: protected String toXMLGuts()
        """
        from kgcl.yawl.util import string_util
        from kgcl.yawl.util.xml import jdom_util

        parts = [super()._to_xml_guts()]

        if self._query_string:
            parts.append(string_util.wrap(self._query_string, self.QUERYSTRING_NM))
        if self._queried_data is not None:
            parts.append(
                string_util.wrap(jdom_util.element_to_string(self._queried_data, pretty=False), self.QUERIEDDATA_NM)
            )
        if self._schema is not None:
            parts.append(string_util.wrap(jdom_util.element_to_string(self._schema, pretty=False), self.SCHEMA_NM))
        if self._data_input is not None:
            parts.append(
                string_util.wrap(jdom_util.element_to_string(self._data_input, pretty=False), self.DATAINPUT_NM)
            )
        if self._xerces_errors:
            parts.append(string_util.wrap(self._xerces_errors, self.XERCESERRORS_NM))
        if self._source:
            parts.append(string_util.wrap(self._source, self.SOURCE_NM))
        if self._message:
            parts.append(string_util.wrap(self._message, self.MESSAGE_NM))

        return "".join(parts)

    @staticmethod
    def unmarshall(exception_doc: Element) -> YDataStateException:
        """Unmarshal from XML element.

        Parameters
        ----------
        exception_doc : Element
            Exception element

        Returns
        -------
        YDataStateException
            Unmarshalled exception

        Notes
        -----
        Java signature: static YDataStateException unmarshall(Document exceptionDoc)
        """
        from kgcl.yawl.util.xml import jdom_util

        root = exception_doc
        query_string = None
        if root.find(YDataStateException.QUERYSTRING_NM) is not None:
            query_elem = root.find(YDataStateException.QUERYSTRING_NM)
            query_string = query_elem.text if query_elem is not None else None

        queried_data = root.find(YDataStateException.QUERIEDDATA_NM)
        schema_elem = root.find(YDataStateException.SCHEMA_NM)
        schema = None
        if schema_elem is not None:
            schema = jdom_util.element_to_string(schema_elem)

        data_input = root.find(YDataStateException.DATAINPUT_NM)
        xerces_errors = None
        if root.find(YDataStateException.XERCESERRORS_NM) is not None:
            errors_elem = root.find(YDataStateException.XERCESERRORS_NM)
            xerces_errors = errors_elem.text if errors_elem is not None else None

        source = None
        if root.find(YDataStateException.SOURCE_NM) is not None:
            source_elem = root.find(YDataStateException.SOURCE_NM)
            source = source_elem.text if source_elem is not None else None

        message = YAWLException._parse_message(root)

        if query_string is None:
            return YDataValidationException(schema, data_input, xerces_errors, source, message)
        elif schema is None:
            return YDataQueryException(query_string, queried_data, source, message)

        return YDataStateException(query_string, queried_data, schema, data_input, xerces_errors, source, message)


class YDataQueryException(YDataStateException):
    """Exception for XQuery failures (mirrors Java YDataQueryException).

    Raised when an XQuery expression fails to execute or returns invalid results.

    Examples
    --------
    >>> raise YDataQueryException(
    ...     query="//order[@id='123']", source="ProcessOrder", message="Query returned no results"
    ... )
    """

    def __init__(
        self,
        query_string: str | None = None,
        queried_data: Element | None = None,
        source: str | None = None,
        message: str = "",
    ) -> None:
        """Initialize data query exception.

        Parameters
        ----------
        query_string : str | None
            XQuery that failed
        queried_data : Element | None
            Data that was queried
        source : str | None
            Source task/element ID
        message : str
            Exception message
        """
        super().__init__(
            query_string=query_string,
            queried_data=queried_data,
            schema=None,
            data_input=None,
            xerces_errors=None,
            source=source,
            message=message,
        )

    @staticmethod
    def unmarshall(exception_doc: Element) -> YDataQueryException:
        """Unmarshal from XML element.

        Parameters
        ----------
        exception_doc : Element
            Exception element

        Returns
        -------
        YDataQueryException
            Unmarshalled exception
        """
        root = exception_doc
        query_string = None
        if root.find(YDataStateException.QUERYSTRING_NM) is not None:
            query_elem = root.find(YDataStateException.QUERYSTRING_NM)
            query_string = query_elem.text if query_elem is not None else None

        queried_data = root.find(YDataStateException.QUERIEDDATA_NM)
        source = None
        if root.find(YDataStateException.SOURCE_NM) is not None:
            source_elem = root.find(YDataStateException.SOURCE_NM)
            source = source_elem.text if source_elem is not None else None

        message = YAWLException._parse_message(root)

        return YDataQueryException(query_string, queried_data, source, message)


class YDataValidationException(YDataStateException):
    """Exception for schema validation failures (mirrors Java YDataValidationException).

    Raised when data fails to validate against a schema.

    Examples
    --------
    >>> raise YDataValidationException(
    ...     schema=schema_xml,
    ...     data_input=data_elem,
    ...     xerces_errors="Invalid type",
    ...     source="ProcessOrder",
    ...     message="Data validation failed",
    ... )
    """

    def __init__(
        self,
        schema: str | None = None,
        data_input: Element | None = None,
        xerces_errors: str | None = None,
        source: str | None = None,
        message: str = "",
    ) -> None:
        """Initialize data validation exception.

        Parameters
        ----------
        schema : str | None
            Schema XML string
        data_input : Element | None
            Data that failed validation
        xerces_errors : str | None
            Validation error messages
        source : str | None
            Source task/element ID
        message : str
            Exception message
        """
        super().__init__(
            query_string=None,
            queried_data=None,
            schema=schema,
            data_input=data_input,
            xerces_errors=xerces_errors,
            source=source,
            message=message,
        )

    @staticmethod
    def unmarshall(exception_doc: Element) -> YDataValidationException:
        """Unmarshal from XML element.

        Parameters
        ----------
        exception_doc : Element
            Exception element

        Returns
        -------
        YDataValidationException
            Unmarshalled exception
        """
        from kgcl.yawl.util.xml import jdom_util

        root = exception_doc
        schema_elem = root.find(YDataStateException.SCHEMA_NM)
        schema = None
        if schema_elem is not None:
            schema = jdom_util.element_to_string(schema_elem)

        data_input = root.find(YDataStateException.DATAINPUT_NM)
        xerces_errors = None
        if root.find(YDataStateException.XERCESERRORS_NM) is not None:
            errors_elem = root.find(YDataStateException.XERCESERRORS_NM)
            xerces_errors = errors_elem.text if errors_elem is not None else None

        source = None
        if root.find(YDataStateException.SOURCE_NM) is not None:
            source_elem = root.find(YDataStateException.SOURCE_NM)
            source = source_elem.text if source_elem is not None else None

        message = YAWLException._parse_message(root)

        return YDataValidationException(schema, data_input, xerces_errors, source, message)


class YQueryException(YAWLException):
    """Exception for query execution failures (mirrors Java YQueryException).

    Raised when a query (XQuery, XPath, etc.) fails to execute.

    Examples
    --------
    >>> raise YQueryException("XQuery syntax error")
    """

    def __init__(self, message: str = "") -> None:
        """Initialize query exception.

        Parameters
        ----------
        message : str
            Exception message
        """
        super().__init__(message)


class YPersistenceException(YAWLException):
    """Exception for persistence failures (mirrors Java YPersistenceException).

    Raised when persistence operations (store, update, delete) fail.

    Examples
    --------
    >>> raise YPersistenceException("Failed to store work item")
    """

    def __init__(self, message: str = "") -> None:
        """Initialize persistence exception.

        Parameters
        ----------
        message : str
            Exception message
        """
        super().__init__(message)


class YAuthenticationException(YAWLException):
    """Exception for authentication failures (mirrors Java YAuthenticationException).

    Raised when authentication or authorization fails.

    Examples
    --------
    >>> raise YAuthenticationException("Invalid credentials")
    """

    def __init__(self, message: str = "") -> None:
        """Initialize authentication exception.

        Parameters
        ----------
        message : str
            Exception message
        """
        super().__init__(message)


class YConnectivityException(YAWLException):
    """Exception for connectivity failures (mirrors Java YConnectivityException).

    Raised when network or service connectivity fails.

    Examples
    --------
    >>> raise YConnectivityException("Cannot connect to engine")
    """

    def __init__(self, message: str = "") -> None:
        """Initialize connectivity exception.

        Parameters
        ----------
        message : str
            Exception message
        """
        super().__init__(message)


class YEngineStateException(YAWLException):
    """Exception for engine state errors (mirrors Java YEngineStateException).

    Raised when engine operations are attempted in invalid states.

    Examples
    --------
    >>> raise YEngineStateException("Engine is not started")
    """

    def __init__(self, message: str = "") -> None:
        """Initialize engine state exception.

        Parameters
        ----------
        message : str
            Exception message
        """
        super().__init__(message)


class YExternalDataException(YAWLException):
    """Exception for external data failures (mirrors Java YExternalDataException).

    Raised when external data gateway operations fail.

    Examples
    --------
    >>> raise YExternalDataException("Database connection failed")
    """

    def __init__(self, message: str = "") -> None:
        """Initialize external data exception.

        Parameters
        ----------
        message : str
            Exception message
        """
        super().__init__(message)


class YLogException(YAWLException):
    """Exception for logging failures (mirrors Java YLogException).

    Raised when logging operations fail.

    Examples
    --------
    >>> raise YLogException("Failed to write log entry")
    """

    def __init__(self, message: str = "") -> None:
        """Initialize log exception.

        Parameters
        ----------
        message : str
            Exception message
        """
        super().__init__(message)


class YSchemaBuildingException(YAWLException):
    """Exception for schema building failures (mirrors Java YSchemaBuildingException).

    Raised when XML schema construction fails.

    Examples
    --------
    >>> raise YSchemaBuildingException("Invalid schema definition")
    """

    def __init__(self, message: str = "") -> None:
        """Initialize schema building exception.

        Parameters
        ----------
        message : str
            Exception message
        """
        super().__init__(message)


class YSyntaxException(YAWLException):
    """Exception for syntax errors (mirrors Java YSyntaxException).

    Raised when parsing or syntax validation fails.

    Examples
    --------
    >>> raise YSyntaxException("Invalid XML syntax")
    """

    def __init__(self, message: str = "") -> None:
        """Initialize syntax exception.

        Parameters
        ----------
        message : str
            Exception message
        """
        super().__init__(message)


@dataclass
class Problem:
    """Problem record for error tracking (mirrors Java Problem).

    Represents a problem/error that occurred during workflow execution.

    Parameters
    ----------
    source : str
        Source of the problem
    problem_time : datetime
        When problem occurred
    message_type : str
        Type of message (e.g., "EmptyResourceSetType")
    message : str
        Problem message

    Examples
    --------
    >>> problem = Problem(
    ...     source="ResourceManager",
    ...     message_type=Problem.EMPTY_RESOURCE_SET_MESSAGETYPE,
    ...     message="No resources available",
    ... )
    """

    EMPTY_RESOURCE_SET_MESSAGETYPE = "EmptyResourceSetType"

    source: str
    problem_time: datetime
    message_type: str
    message: str

    def __hash__(self) -> int:
        """Hash by source and problem time.

        Returns
        -------
        int
            Hash value

        Notes
        -----
        Java signature: int hashCode()
        """
        return 29 * hash(self.source) + hash(self.problem_time)

    def __eq__(self, other: object) -> bool:
        """Equality by source and problem time.

        Parameters
        ----------
        other : object
            Other object

        Returns
        -------
        bool
            True if equal

        Notes
        -----
        Java signature: boolean equals(Object o)
        """
        if not isinstance(other, Problem):
            return False
        return self.problem_time == other.problem_time and self.source == other.source
