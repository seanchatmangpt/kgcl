"""Codelet executor with timeout support.

Executes codelets with configurable timeouts to prevent
runaway automated tasks from blocking workflow execution.
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from kgcl.yawl.codelets.base import Codelet, CodeletContext, CodeletResult, CodeletStatus
from kgcl.yawl.codelets.registry import CodeletRegistry


@dataclass
class CodeletExecutor:
    """Executor for codelets with timeout support.

    Parameters
    ----------
    registry : CodeletRegistry
        Registry of available codelets
    default_timeout : float
        Default timeout in seconds
    max_workers : int
        Maximum concurrent executions
    """

    registry: CodeletRegistry = field(default_factory=CodeletRegistry)
    default_timeout: float = 30.0
    max_workers: int = 4

    def execute(self, codelet_name: str, context: CodeletContext, timeout: float | None = None) -> CodeletResult:
        """Execute a codelet by name with timeout.

        Parameters
        ----------
        codelet_name : str
            Name of registered codelet
        context : CodeletContext
            Execution context
        timeout : float | None
            Timeout in seconds (uses default if None)

        Returns
        -------
        CodeletResult
            Execution result
        """
        timeout = timeout if timeout is not None else self.default_timeout

        # Get codelet from registry
        codelet = self.registry.get(codelet_name)
        if codelet is None:
            return CodeletResult.failure_result(f"Codelet not found: {codelet_name}")

        # Execute with timeout
        return self._execute_with_timeout(codelet, context, timeout)

    def execute_codelet(self, codelet: Codelet, context: CodeletContext, timeout: float | None = None) -> CodeletResult:
        """Execute a codelet instance with timeout.

        Parameters
        ----------
        codelet : Codelet
            Codelet instance
        context : CodeletContext
            Execution context
        timeout : float | None
            Timeout in seconds

        Returns
        -------
        CodeletResult
            Execution result
        """
        timeout = timeout if timeout is not None else self.default_timeout
        return self._execute_with_timeout(codelet, context, timeout)

    def _execute_with_timeout(self, codelet: Codelet, context: CodeletContext, timeout: float) -> CodeletResult:
        """Execute codelet with timeout.

        Parameters
        ----------
        codelet : Codelet
            Codelet to execute
        context : CodeletContext
            Execution context
        timeout : float
            Timeout in seconds

        Returns
        -------
        CodeletResult
            Execution result
        """
        started = datetime.now()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(codelet.execute, context)

            try:
                result = future.result(timeout=timeout)
                return result

            except concurrent.futures.TimeoutError:
                future.cancel()
                result = CodeletResult.timeout_result(timeout)
                result.started = started
                return result

            except Exception as e:
                result = CodeletResult.error_result(e)
                result.started = started
                return result

    def execute_async(
        self, codelet_name: str, context: CodeletContext, callback: Any | None = None
    ) -> concurrent.futures.Future[CodeletResult]:
        """Execute a codelet asynchronously.

        Parameters
        ----------
        codelet_name : str
            Name of registered codelet
        context : CodeletContext
            Execution context
        callback : Any | None
            Optional callback function

        Returns
        -------
        Future[CodeletResult]
            Future for the result
        """
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)

        def execute_and_callback() -> CodeletResult:
            result = self.execute(codelet_name, context)
            if callback:
                callback(result)
            return result

        future = executor.submit(execute_and_callback)
        return future

    def register(self, name: str, codelet: Codelet) -> None:
        """Register a codelet.

        Parameters
        ----------
        name : str
            Codelet name
        codelet : Codelet
            Codelet instance
        """
        self.registry.register(name, codelet)

    def unregister(self, name: str) -> bool:
        """Unregister a codelet.

        Parameters
        ----------
        name : str
            Codelet name

        Returns
        -------
        bool
            True if unregistered
        """
        return self.registry.unregister(name)

    def is_registered(self, name: str) -> bool:
        """Check if codelet is registered.

        Parameters
        ----------
        name : str
            Codelet name

        Returns
        -------
        bool
            True if registered
        """
        return self.registry.is_registered(name)

    def list_codelets(self) -> list[str]:
        """List registered codelet names.

        Returns
        -------
        list[str]
            Codelet names
        """
        return self.registry.list_names()
