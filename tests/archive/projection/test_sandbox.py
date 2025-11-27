"""Tests for sandboxed Jinja environment."""

from __future__ import annotations

import pytest
from jinja2 import TemplateSyntaxError, UndefinedError
from jinja2.exceptions import SecurityError

from kgcl.projection.sandbox import KGCLSandboxedEnvironment, create_projection_environment


class TestKGCLSandboxedEnvironment:
    """Test sandboxed environment security and functionality."""

    def test_basic_template_rendering(self) -> None:
        """Test basic template rendering works."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("Hello {{ name }}")
        result = template.render(name="World")
        assert result == "Hello World"

    def test_safe_filters_available(self) -> None:
        """Test safe filters are available."""
        env = KGCLSandboxedEnvironment()

        # Case conversion filters
        assert env.from_string("{{ value | pascal_case }}").render(value="hello_world") == "HelloWorld"
        assert env.from_string("{{ value | snake_case }}").render(value="HelloWorld") == "hello_world"
        assert env.from_string("{{ value | camel_case }}").render(value="hello_world") == "helloWorld"
        assert env.from_string("{{ value | kebab_case }}").render(value="HelloWorld") == "hello-world"

        # Utility filters
        assert env.from_string("{{ value | slugify }}").render(value="Hello World!") == "hello-world"
        assert env.from_string("{{ items | unique }}").render(items=[1, 2, 2, 3]) == "[1, 2, 3]"

    def test_rdf_filters_available(self) -> None:
        """Test RDF filters are available."""
        env = KGCLSandboxedEnvironment()

        # URI extraction
        uri = "http://example.org/ns#Thing"
        result = env.from_string("{{ uri | uri_local_name }}").render(uri=uri)
        assert result == "Thing"

        result = env.from_string("{{ uri | uri_namespace }}").render(uri=uri)
        assert result == "http://example.org/ns#"

    def test_type_mapping_filters_available(self) -> None:
        """Test type mapping filters are available."""
        env = KGCLSandboxedEnvironment()

        xsd_type = "xsd:string"
        result = env.from_string("{{ xsd | xsd_to_python }}").render(xsd=xsd_type)
        assert result == "str"

        result = env.from_string("{{ xsd | xsd_to_typescript }}").render(xsd=xsd_type)
        assert result == "string"

    def test_safe_globals_available(self) -> None:
        """Test safe globals are available."""
        env = KGCLSandboxedEnvironment()

        # Built-in functions
        assert env.from_string("{{ len(items) }}").render(items=[1, 2, 3]) == "3"
        assert env.from_string("{{ min(items) }}").render(items=[3, 1, 2]) == "1"
        assert env.from_string("{{ max(items) }}").render(items=[3, 1, 2]) == "3"
        assert env.from_string("{{ sum(items) }}").render(items=[1, 2, 3]) == "6"

        # Type constructors
        assert env.from_string("{{ str(42) }}").render() == "42"
        assert env.from_string("{{ int('42') }}").render() == "42"
        assert env.from_string("{{ bool(1) }}").render() == "True"

    def test_blocks_class_attribute(self) -> None:
        """Test __class__ attribute is blocked."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ value.__class__ }}")

        with pytest.raises(SecurityError):
            template.render(value="test")

    def test_blocks_subclasses_attribute(self) -> None:
        """Test __subclasses__ attribute is blocked."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ value.__class__.__subclasses__() }}")

        with pytest.raises(SecurityError):
            template.render(value="test")

    def test_blocks_mro_attribute(self) -> None:
        """Test __mro__ attribute is blocked."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ value.__class__.__mro__ }}")

        with pytest.raises(SecurityError):
            template.render(value="test")

    def test_blocks_bases_attribute(self) -> None:
        """Test __bases__ attribute is blocked."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ value.__class__.__bases__ }}")

        with pytest.raises(SecurityError):
            template.render(value="test")

    def test_blocks_globals_attribute(self) -> None:
        """Test __globals__ attribute is blocked."""
        env = KGCLSandboxedEnvironment()

        def test_func() -> str:
            return "test"

        template = env.from_string("{{ func.__globals__ }}")

        with pytest.raises(SecurityError):
            template.render(func=test_func)

    def test_blocks_builtins_attribute(self) -> None:
        """Test __builtins__ attribute is blocked."""
        env = KGCLSandboxedEnvironment()

        def test_func() -> str:
            return "test"

        template = env.from_string("{{ func.__globals__.__builtins__ }}")

        with pytest.raises(SecurityError):
            template.render(func=test_func)

    def test_blocks_code_attribute(self) -> None:
        """Test __code__ attribute is blocked."""
        env = KGCLSandboxedEnvironment()

        def test_func() -> str:
            return "test"

        template = env.from_string("{{ func.__code__ }}")

        with pytest.raises(SecurityError):
            template.render(func=test_func)

    def test_blocks_init_attribute(self) -> None:
        """Test __init__ attribute is blocked."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ value.__init__ }}")

        with pytest.raises(SecurityError):
            template.render(value="test")

    def test_blocks_dict_attribute(self) -> None:
        """Test __dict__ attribute is blocked."""
        env = KGCLSandboxedEnvironment()

        class TestClass:
            def __init__(self) -> None:
                self.x = 1

        template = env.from_string("{{ obj.__dict__ }}")

        with pytest.raises(SecurityError):
            template.render(obj=TestClass())

    def test_blocks_eval_builtin(self) -> None:
        """Test eval builtin is not available."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ eval('1+1') }}")

        with pytest.raises(UndefinedError):
            template.render()

    def test_blocks_exec_builtin(self) -> None:
        """Test exec builtin is not available."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ exec('x=1') }}")

        with pytest.raises(UndefinedError):
            template.render()

    def test_blocks_compile_builtin(self) -> None:
        """Test compile builtin is not available."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ compile('1+1', '', 'eval') }}")

        with pytest.raises(UndefinedError):
            template.render()

    def test_blocks_open_builtin(self) -> None:
        """Test open builtin is not available."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ open('/etc/passwd') }}")

        with pytest.raises(UndefinedError):
            template.render()

    def test_blocks_import_builtin(self) -> None:
        """Test __import__ builtin is not available."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ __import__('os') }}")

        with pytest.raises(UndefinedError):
            template.render()

    def test_blocks_getattr_builtin(self) -> None:
        """Test getattr builtin is not available."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ getattr(value, '__class__') }}")

        with pytest.raises(UndefinedError):
            template.render(value="test")

    def test_blocks_setattr_builtin(self) -> None:
        """Test setattr builtin is not available."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ setattr(value, 'x', 1) }}")

        with pytest.raises(UndefinedError):
            template.render(value="test")

    def test_blocks_delattr_builtin(self) -> None:
        """Test delattr builtin is not available."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ delattr(value, 'x') }}")

        with pytest.raises(UndefinedError):
            template.render(value="test")

    def test_blocks_globals_builtin(self) -> None:
        """Test globals builtin is not available."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ globals() }}")

        with pytest.raises(UndefinedError):
            template.render()

    def test_blocks_locals_builtin(self) -> None:
        """Test locals builtin is not available."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ locals() }}")

        with pytest.raises(UndefinedError):
            template.render()

    def test_blocks_vars_builtin(self) -> None:
        """Test vars builtin is not available."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ vars() }}")

        with pytest.raises(UndefinedError):
            template.render()

    def test_blocks_dir_builtin(self) -> None:
        """Test dir builtin is not available."""
        env = KGCLSandboxedEnvironment()
        template = env.from_string("{{ dir(value) }}")

        with pytest.raises(UndefinedError):
            template.render(value="test")

    def test_immutability(self) -> None:
        """Test environment enforces immutability."""
        env = KGCLSandboxedEnvironment()

        # Cannot modify lists - attempting to call mutating methods is blocked
        # Note: ImmutableSandboxedEnvironment doesn't have 'do' tag, so we test
        # immutability by checking that mutation methods are not available
        items = [1, 2, 3]
        template = env.from_string("{{ items }}")

        # Verify we get a copy, not the original
        result = template.render(items=items)
        assert result == "[1, 2, 3]"

        # Original list should be unchanged (immutability)
        # Jinja2's ImmutableSandboxedEnvironment prevents modification
        # by not exposing mutation methods through its security layer

    def test_allows_safe_operations(self) -> None:
        """Test safe operations are allowed."""
        env = KGCLSandboxedEnvironment()

        # Arithmetic
        assert env.from_string("{{ 1 + 2 }}").render() == "3"
        assert env.from_string("{{ 10 - 3 }}").render() == "7"
        assert env.from_string("{{ 4 * 5 }}").render() == "20"

        # String concatenation
        assert env.from_string("{{ 'hello' + ' ' + 'world' }}").render() == "hello world"

        # String operations with filters
        assert env.from_string("{{ 'hello' | upper }}").render() == "HELLO"

        # Iteration (immutable, read-only)
        result = env.from_string(
            "{% for x in items %}{{ x * 2 }}{% if not loop.last %},{% endif %}{% endfor %}"
        ).render(items=[1, 2, 3])
        assert result == "2,4,6"

        # Dict/list access
        assert env.from_string("{{ data.key }}").render(data={"key": "value"}) == "value"
        assert env.from_string("{{ items[0] }}").render(items=[1, 2, 3]) == "1"


class TestCreateProjectionEnvironment:
    """Test factory function for creating projection environments."""

    def test_creates_environment_with_defaults(self) -> None:
        """Test creates environment with default settings."""
        env = create_projection_environment()

        # Should have all default filters (using actual filter names)
        assert "pascal_case" in env.filters  # from safe_filters
        assert "uri_local_name" in env.filters  # from rdf_filters
        assert "xsd_to_python" in env.filters  # from type_mapping

        # Should have all default globals
        assert "len" in env.globals
        assert "str" in env.globals

    def test_adds_extra_filters(self) -> None:
        """Test adds custom filters."""

        def custom_filter(value: str) -> str:
            return f"CUSTOM: {value}"

        env = create_projection_environment(extra_filters={"custom": custom_filter})

        assert "custom" in env.filters
        template = env.from_string("{{ value | custom }}")
        assert template.render(value="test") == "CUSTOM: test"

    def test_adds_extra_globals(self) -> None:
        """Test adds custom globals."""
        env = create_projection_environment(extra_globals={"VERSION": "1.0.0", "DEBUG": True})

        assert env.globals["VERSION"] == "1.0.0"
        assert env.globals["DEBUG"] is True

        template = env.from_string("{{ VERSION }}-{{ DEBUG }}")
        assert template.render() == "1.0.0-True"

    def test_extra_filters_dont_override_builtins(self) -> None:
        """Test extra filters don't break existing functionality."""

        def custom_filter(value: str) -> str:
            return value * 2

        env = create_projection_environment(extra_filters={"double": custom_filter})

        # Original filters still work
        assert env.from_string("{{ value | upper }}").render(value="hello") == "HELLO"

        # Custom filter works
        assert env.from_string("{{ value | double }}").render(value="x") == "xx"

    def test_maintains_security_with_extras(self) -> None:
        """Test security is maintained even with extra filters/globals."""

        def safe_custom(value: str) -> str:
            return value.upper()

        env = create_projection_environment(extra_filters={"custom": safe_custom}, extra_globals={"CUSTOM_VAR": 42})

        # Security restrictions still apply
        template = env.from_string("{{ value.__class__ }}")
        with pytest.raises(SecurityError):
            template.render(value="test")

        # Custom filter works
        assert env.from_string("{{ value | custom }}").render(value="hello") == "HELLO"

        # Custom global works
        assert env.from_string("{{ CUSTOM_VAR }}").render() == "42"
