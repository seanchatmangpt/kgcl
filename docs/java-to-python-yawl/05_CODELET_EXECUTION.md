# Gap 5: External Service/Codelet Execution

## Problem Statement

YAWL supports automated tasks (codelets) that execute external code without human interaction. Currently, automated tasks are stubbed out.

## YAWL Codelet Types

| Type | Description | Example |
|------|-------------|---------|
| **Codelet** | Java class implementing YCodelet interface | Custom business logic |
| **Web Service** | SOAP/REST service invocation | External API call |
| **Shell Command** | OS command execution | Script runner |
| **Java Bean** | Spring-managed bean | Enterprise integration |

## Current State

```python
# src/kgcl/yawl/elements/y_atomic_task.py
@dataclass
class YAtomicTask(YTask):
    # ...
    codelet_class: str | None = None  # Defined but unused
    codelet_params: dict[str, str] = field(default_factory=dict)


# src/kgcl/yawl/engine/y_engine.py
def _resource_work_item(self, work_item, task):
    work_item.fire()

    if task.is_automated():
        # TODO: Execute codelet
        work_item.complete({})  # Stub: immediate completion
```

**Problem**: Automated tasks complete immediately without executing anything.

## Target Behavior

```
Automated Task becomes enabled
         │
         ▼
┌─────────────────────────────────┐
│  Create work item               │
│  status = EXECUTING             │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Load codelet/service config    │
│  from task definition           │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Execute based on type:         │
│  - Python callable              │
│  - HTTP service                 │
│  - Shell command                │
│  - Plugin                       │
└─────────────────────────────────┘
         │
         ├─► Success: complete_work_item(output)
         │
         └─► Failure: fail_work_item(error)
```

## Implementation Plan

### New Module: `src/kgcl/yawl/service/`

```
src/kgcl/yawl/service/
├── __init__.py
├── y_codelet.py        # Codelet base class and registry
├── y_http_service.py   # HTTP/REST service executor
├── y_shell_service.py  # Shell command executor
└── y_service_runner.py # Service execution coordinator
```

### Step 1: Codelet Base Class

```python
# src/kgcl/yawl/service/y_codelet.py
"""Codelet execution framework for YAWL automated tasks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class CodeletResult:
    """Result from codelet execution.

    Parameters
    ----------
    success : bool
        Whether execution succeeded
    output : dict[str, Any]
        Output data from codelet
    error : str | None
        Error message if failed
    """

    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class YCodelet(ABC):
    """Abstract base class for YAWL codelets.

    Implement this interface to create custom automated task handlers.

    Example
    -------
    >>> class ApprovalCodelet(YCodelet):
    ...     def execute(self, input_data, params):
    ...         amount = input_data.get("amount", 0)
    ...         if amount < params.get("threshold", 1000):
    ...             return CodeletResult(True, {"approved": True})
    ...         return CodeletResult(True, {"approved": False})
    """

    @abstractmethod
    def execute(
        self,
        input_data: dict[str, Any],
        params: dict[str, str],
    ) -> CodeletResult:
        """Execute the codelet.

        Parameters
        ----------
        input_data : dict[str, Any]
            Input data from work item
        params : dict[str, str]
            Codelet parameters from task definition

        Returns
        -------
        CodeletResult
            Execution result with output data or error
        """
        pass


class YCodeletRegistry:
    """Registry for codelet implementations.

    Codelets can be registered by name for lookup during execution.

    Example
    -------
    >>> registry = YCodeletRegistry()
    >>> registry.register("approval", ApprovalCodelet)
    >>> codelet = registry.get("approval")
    """

    def __init__(self) -> None:
        self._codelets: dict[str, type[YCodelet]] = {}
        self._callables: dict[str, Callable[..., CodeletResult]] = {}

    def register(self, name: str, codelet_class: type[YCodelet]) -> None:
        """Register a codelet class by name."""
        self._codelets[name] = codelet_class

    def register_callable(
        self,
        name: str,
        func: Callable[[dict[str, Any], dict[str, str]], CodeletResult],
    ) -> None:
        """Register a callable as a codelet."""
        self._callables[name] = func

    def get(self, name: str) -> YCodelet | None:
        """Get codelet instance by name."""
        if name in self._codelets:
            return self._codelets[name]()
        return None

    def get_callable(
        self, name: str
    ) -> Callable[[dict[str, Any], dict[str, str]], CodeletResult] | None:
        """Get callable by name."""
        return self._callables.get(name)

    def has(self, name: str) -> bool:
        """Check if codelet exists."""
        return name in self._codelets or name in self._callables


# Global registry
_default_registry = YCodeletRegistry()


def register_codelet(name: str) -> Callable[[type[YCodelet]], type[YCodelet]]:
    """Decorator to register a codelet class.

    Example
    -------
    >>> @register_codelet("my_codelet")
    ... class MyCodelet(YCodelet):
    ...     def execute(self, input_data, params):
    ...         return CodeletResult(True, {"result": "done"})
    """
    def decorator(cls: type[YCodelet]) -> type[YCodelet]:
        _default_registry.register(name, cls)
        return cls
    return decorator


def get_registry() -> YCodeletRegistry:
    """Get the default codelet registry."""
    return _default_registry
```

### Step 2: HTTP Service Executor

```python
# src/kgcl/yawl/service/y_http_service.py
"""HTTP/REST service executor for YAWL automated tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from kgcl.yawl.service.y_codelet import CodeletResult


@dataclass
class HTTPServiceConfig:
    """Configuration for HTTP service invocation.

    Parameters
    ----------
    url : str
        Service endpoint URL
    method : str
        HTTP method (GET, POST, PUT, DELETE)
    headers : dict[str, str]
        Request headers
    timeout : float
        Request timeout in seconds
    """

    url: str
    method: str = "POST"
    headers: dict[str, str] | None = None
    timeout: float = 30.0


class YHTTPService:
    """HTTP service executor.

    Invokes REST services for automated tasks.

    Example
    -------
    >>> config = HTTPServiceConfig(
    ...     url="https://api.example.com/process",
    ...     method="POST",
    ... )
    >>> service = YHTTPService(config)
    >>> result = service.invoke({"order_id": "123"})
    """

    def __init__(self, config: HTTPServiceConfig) -> None:
        self.config = config

    def invoke(
        self,
        input_data: dict[str, Any],
        params: dict[str, str],
    ) -> CodeletResult:
        """Invoke HTTP service.

        Parameters
        ----------
        input_data : dict[str, Any]
            Request body data
        params : dict[str, str]
            Additional parameters (URL template variables)

        Returns
        -------
        CodeletResult
            Service response or error
        """
        try:
            import httpx
        except ImportError:
            return CodeletResult(
                success=False,
                error="httpx not installed. Run: uv add httpx"
            )

        try:
            # Build URL with params
            url = self.config.url.format(**params)

            # Make request
            with httpx.Client(timeout=self.config.timeout) as client:
                if self.config.method.upper() == "GET":
                    response = client.get(
                        url,
                        params=input_data,
                        headers=self.config.headers,
                    )
                else:
                    response = client.request(
                        self.config.method.upper(),
                        url,
                        json=input_data,
                        headers=self.config.headers,
                    )

                response.raise_for_status()

                # Parse response
                try:
                    output = response.json()
                except json.JSONDecodeError:
                    output = {"_response": response.text}

                return CodeletResult(success=True, output=output)

        except httpx.HTTPStatusError as e:
            return CodeletResult(
                success=False,
                error=f"HTTP {e.response.status_code}: {e.response.text}",
            )
        except httpx.RequestError as e:
            return CodeletResult(success=False, error=str(e))
```

### Step 3: Shell Command Executor

```python
# src/kgcl/yawl/service/y_shell_service.py
"""Shell command executor for YAWL automated tasks."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

from kgcl.yawl.service.y_codelet import CodeletResult


@dataclass
class ShellServiceConfig:
    """Configuration for shell command execution.

    Parameters
    ----------
    command : str
        Command to execute (with placeholders)
    timeout : float
        Execution timeout in seconds
    shell : bool
        Whether to run through shell
    env : dict[str, str] | None
        Environment variables
    working_dir : str | None
        Working directory
    """

    command: str
    timeout: float = 60.0
    shell: bool = True
    env: dict[str, str] | None = None
    working_dir: str | None = None


class YShellService:
    """Shell command executor.

    Executes shell commands for automated tasks.
    Input data is passed as JSON via stdin.
    Output is parsed from stdout.

    Example
    -------
    >>> config = ShellServiceConfig(command="python process.py")
    >>> service = YShellService(config)
    >>> result = service.invoke({"order_id": "123"}, {})
    """

    def __init__(self, config: ShellServiceConfig) -> None:
        self.config = config

    def invoke(
        self,
        input_data: dict[str, Any],
        params: dict[str, str],
    ) -> CodeletResult:
        """Execute shell command.

        Parameters
        ----------
        input_data : dict[str, Any]
            Data passed via stdin as JSON
        params : dict[str, str]
            Command template variables

        Returns
        -------
        CodeletResult
            Command output or error
        """
        try:
            # Build command with params
            command = self.config.command.format(**params)

            # Prepare input
            stdin_data = json.dumps(input_data)

            # Execute
            result = subprocess.run(
                command,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
                shell=self.config.shell,
                env=self.config.env,
                cwd=self.config.working_dir,
            )

            if result.returncode != 0:
                return CodeletResult(
                    success=False,
                    error=f"Exit code {result.returncode}: {result.stderr}",
                )

            # Parse output
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                output = {"_stdout": result.stdout, "_stderr": result.stderr}

            return CodeletResult(success=True, output=output)

        except subprocess.TimeoutExpired:
            return CodeletResult(success=False, error="Command timed out")
        except Exception as e:
            return CodeletResult(success=False, error=str(e))
```

### Step 4: Service Runner Coordinator

```python
# src/kgcl/yawl/service/y_service_runner.py
"""Service execution coordinator for YAWL automated tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kgcl.yawl.elements.y_atomic_task import YAtomicTask
from kgcl.yawl.service.y_codelet import (
    CodeletResult,
    YCodeletRegistry,
    get_registry,
)
from kgcl.yawl.service.y_http_service import HTTPServiceConfig, YHTTPService
from kgcl.yawl.service.y_shell_service import ShellServiceConfig, YShellService


@dataclass
class YServiceRunner:
    """Coordinator for executing automated task services.

    Routes task execution to appropriate service type:
    - Codelet (registered Python class/callable)
    - HTTP service
    - Shell command

    Parameters
    ----------
    codelet_registry : YCodeletRegistry
        Registry of codelet implementations
    http_configs : dict[str, HTTPServiceConfig]
        HTTP service configurations by name
    shell_configs : dict[str, ShellServiceConfig]
        Shell service configurations by name
    """

    codelet_registry: YCodeletRegistry = field(default_factory=get_registry)
    http_configs: dict[str, HTTPServiceConfig] = field(default_factory=dict)
    shell_configs: dict[str, ShellServiceConfig] = field(default_factory=dict)

    def register_http_service(
        self,
        name: str,
        config: HTTPServiceConfig,
    ) -> None:
        """Register HTTP service configuration."""
        self.http_configs[name] = config

    def register_shell_service(
        self,
        name: str,
        config: ShellServiceConfig,
    ) -> None:
        """Register shell service configuration."""
        self.shell_configs[name] = config

    def execute(
        self,
        task: YAtomicTask,
        input_data: dict[str, Any],
    ) -> CodeletResult:
        """Execute automated task.

        Parameters
        ----------
        task : YAtomicTask
            Task definition
        input_data : dict[str, Any]
            Input data for execution

        Returns
        -------
        CodeletResult
            Execution result
        """
        # Determine service type from task configuration
        codelet_name = task.codelet_class
        if codelet_name is None:
            return CodeletResult(
                success=False,
                error="No codelet/service configured for task",
            )

        params = task.codelet_params

        # Try codelet registry first
        if self.codelet_registry.has(codelet_name):
            codelet = self.codelet_registry.get(codelet_name)
            if codelet:
                return codelet.execute(input_data, params)

            callable_fn = self.codelet_registry.get_callable(codelet_name)
            if callable_fn:
                return callable_fn(input_data, params)

        # Try HTTP service
        if codelet_name in self.http_configs:
            service = YHTTPService(self.http_configs[codelet_name])
            return service.invoke(input_data, params)

        # Try shell service
        if codelet_name in self.shell_configs:
            service = YShellService(self.shell_configs[codelet_name])
            return service.invoke(input_data, params)

        return CodeletResult(
            success=False,
            error=f"Unknown codelet/service: {codelet_name}",
        )
```

### Step 5: Engine Integration

```python
# src/kgcl/yawl/engine/y_engine.py

from kgcl.yawl.service.y_service_runner import YServiceRunner

@dataclass
class YEngine:
    # ... existing fields ...

    service_runner: YServiceRunner = field(default_factory=YServiceRunner)

    def _resource_work_item(
        self,
        work_item: YWorkItem,
        task: YTask,
    ) -> None:
        """Resource a work item based on task configuration."""
        work_item.fire()

        if isinstance(task, YAtomicTask) and task.is_automated():
            self._execute_automated_task(work_item, task)
        else:
            # Manual task: offer/allocate to resource
            # ... existing code ...

    def _execute_automated_task(
        self,
        work_item: YWorkItem,
        task: YAtomicTask,
    ) -> None:
        """Execute automated task via service runner.

        Parameters
        ----------
        work_item : YWorkItem
            Work item to execute
        task : YAtomicTask
            Task definition with codelet config
        """
        # Mark as executing
        work_item.status = WorkItemStatus.EXECUTING
        work_item.started_time = datetime.now()

        # Get input data
        case = self.cases.get(work_item.case_id)
        input_data = {}
        if case:
            input_data = dict(case.data.variables)

        # Execute service
        result = self.service_runner.execute(task, input_data)

        if result.success:
            self.complete_work_item(work_item.id, result.output)
            self._emit_event(
                "AUTOMATED_TASK_COMPLETED",
                case_id=work_item.case_id,
                work_item_id=work_item.id,
                task_id=task.id,
                data=result.output,
            )
        else:
            self.fail_work_item(work_item.id, result.error or "Unknown error")
            self._emit_event(
                "AUTOMATED_TASK_FAILED",
                case_id=work_item.case_id,
                work_item_id=work_item.id,
                task_id=task.id,
                data={"error": result.error},
            )
```

## Built-in Codelets

Provide common codelets out of the box:

```python
# src/kgcl/yawl/service/builtin_codelets.py
"""Built-in codelets for common operations."""

from kgcl.yawl.service.y_codelet import (
    CodeletResult,
    YCodelet,
    register_codelet,
)


@register_codelet("echo")
class EchoCodelet(YCodelet):
    """Echo input as output."""

    def execute(self, input_data, params):
        return CodeletResult(success=True, output=input_data)


@register_codelet("delay")
class DelayCodelet(YCodelet):
    """Delay execution for specified seconds."""

    def execute(self, input_data, params):
        import time
        seconds = float(params.get("seconds", "1"))
        time.sleep(seconds)
        return CodeletResult(success=True, output=input_data)


@register_codelet("validate")
class ValidateCodelet(YCodelet):
    """Validate input against JSON schema."""

    def execute(self, input_data, params):
        try:
            import jsonschema
            schema_str = params.get("schema", "{}")
            import json
            schema = json.loads(schema_str)
            jsonschema.validate(input_data, schema)
            return CodeletResult(success=True, output={"valid": True})
        except jsonschema.ValidationError as e:
            return CodeletResult(
                success=False,
                error=f"Validation failed: {e.message}",
            )
```

## Test Cases

```python
class TestCodeletExecution:
    """Tests for automated task execution."""

    def test_registered_codelet_executes(self) -> None:
        """Registered codelet is called with correct params."""
        # Register custom codelet
        # Create task with codelet_class = registered name
        # Assert: codelet.execute() called
        # Assert: work item completed with output

    def test_http_service_invokes_endpoint(self) -> None:
        """HTTP service makes correct request."""
        # Mock HTTP endpoint
        # Register HTTP service config
        # Execute task
        # Assert: correct URL, method, body

    def test_shell_service_runs_command(self) -> None:
        """Shell service executes command."""
        # Create shell config with echo command
        # Execute task
        # Assert: command ran, output captured

    def test_unknown_codelet_fails_task(self) -> None:
        """Unknown codelet name fails work item."""
        # Task with non-existent codelet_class
        # Assert: work item status == FAILED

    def test_codelet_failure_fails_work_item(self) -> None:
        """Codelet returning failure fails work item."""
        # Codelet returns CodeletResult(success=False)
        # Assert: work item status == FAILED
```

## Dependencies

- **Optional**: `httpx` for HTTP services
- **Optional**: `jsonschema` for validation codelet

## Complexity: MEDIUM

- Plugin architecture
- Multiple service types
- Error handling

## Estimated Effort

- Implementation: 6-8 hours
- Testing: 4-6 hours
- Total: 1.5-2 days

## Priority: MEDIUM

Enables fully automated workflows without manual intervention.
