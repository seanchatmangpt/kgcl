"""Timeout executor - Thread-based timeout for SPARQL queries.

This module provides a thread-based executor for running SPARQL queries
with configurable timeouts. When a query exceeds the timeout, a
QueryTimeoutError is raised.

Examples
--------
>>> from kgcl.projection.engine.timeout_executor import execute_with_timeout
>>> def slow_query() -> list[dict[str, object]]:
...     import time
...
...     time.sleep(0.1)
...     return [{"s": "ex:Entity1"}]
>>> result = execute_with_timeout(slow_query, timeout_seconds=1.0)
>>> len(result)
1
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

from kgcl.projection.domain.exceptions import QueryTimeoutError

__all__ = ["execute_with_timeout"]


def execute_with_timeout[T](func: Callable[[], T], timeout_seconds: float, query_name: str = "unnamed") -> T:
    """Execute a function with a timeout.

    Parameters
    ----------
    func : Callable[[], T]
        Zero-argument function to execute.
    timeout_seconds : float
        Maximum execution time in seconds.
    query_name : str
        Name of the query for error reporting.

    Returns
    -------
    T
        Result from func if completed within timeout.

    Raises
    ------
    QueryTimeoutError
        If execution exceeds timeout_seconds.

    Examples
    --------
    >>> def fast() -> str:
    ...     return "done"
    >>> execute_with_timeout(fast, 1.0)
    'done'

    >>> import time
    >>> def slow() -> str:
    ...     time.sleep(5)
    ...     return "done"
    >>> execute_with_timeout(slow, 0.01, "test")  # doctest: +SKIP
    Traceback (most recent call last):
        ...
    kgcl.projection.domain.exceptions.QueryTimeoutError: ...
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError as e:
            # Cancel the future (though Python can't truly interrupt threads)
            future.cancel()
            raise QueryTimeoutError(query_name, timeout_seconds) from e
