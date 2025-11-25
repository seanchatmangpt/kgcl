"""Configuration management CLI command.

Edit and manage KGCL configuration settings.
"""

import json

import click

from kgcl.cli.utils import (
    confirm_action,
    get_config_file,
    load_config,
    print_error,
    print_info,
    print_json,
    print_success,
    print_table,
    save_config,
)

DEFAULT_CONFIG = {
    "exclusions": {
        "files": [".git", "__pycache__", "node_modules", ".venv", "*.pyc"],
        "directories": [".git", "__pycache__", "node_modules", ".venv"],
        "patterns": ["*.log", "*.tmp", "*.swp"],
    },
    "capabilities": {
        "auto_feature_discovery": True,
        "continuous_learning": True,
        "telemetry": False,
        "auto_updates": False,
    },
    "settings": {
        "default_model": "llama3.2",
        "sparql_endpoint": "http://localhost:3030/kgcl/sparql",
        "event_retention_days": 90,
        "max_feature_instances": 10000,
    },
}


@click.group()
def config() -> None:
    """Manage KGCL configuration.

    Configure exclusion lists, toggle capabilities, and adjust settings.

    Examples
    --------
        # Show current configuration
        $ kgc-config show

        # Add file exclusion
        $ kgc-config exclude add --file "*.backup"

        # Enable telemetry
        $ kgc-config capability enable telemetry

        # Set default model
        $ kgc-config set default_model llama3.3
    """


@config.command()
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "table"]),
    default="json",
    help="Output format",
)
def show(output_format: str) -> None:
    """Show current configuration."""
    try:
        cfg = load_config()

        if not cfg:
            print_info("No configuration found, showing defaults")
            cfg = DEFAULT_CONFIG

        if output_format == "json":
            print_json(cfg)
        else:
            # Display as tables by section
            _display_config_tables(cfg)

    except Exception as e:
        print_error(f"Failed to load configuration: {e}")


@config.command()
def init() -> None:
    """Initialize configuration with defaults."""
    try:
        config_file = get_config_file()

        if config_file.exists():
            if not confirm_action("Configuration already exists. Overwrite?", default=False):
                print_info("Aborted")
                return

        save_config(DEFAULT_CONFIG)
        print_success("Configuration initialized")

    except Exception as e:
        print_error(f"Failed to initialize configuration: {e}")


@config.group()
def exclude() -> None:
    """Manage exclusion lists."""


@exclude.command("add")
@click.option("--file", "file_pattern", type=str, help="File pattern to exclude")
@click.option("--directory", "dir_pattern", type=str, help="Directory pattern to exclude")
@click.option("--pattern", type=str, help="General pattern to exclude")
def exclude_add(file_pattern: str | None, dir_pattern: str | None, pattern: str | None) -> None:
    """Add exclusion pattern."""
    try:
        cfg = load_config() or DEFAULT_CONFIG.copy()

        if file_pattern:
            cfg.setdefault("exclusions", {}).setdefault("files", []).append(file_pattern)
            print_success(f"Added file exclusion: {file_pattern}")

        if dir_pattern:
            cfg.setdefault("exclusions", {}).setdefault("directories", []).append(dir_pattern)
            print_success(f"Added directory exclusion: {dir_pattern}")

        if pattern:
            cfg.setdefault("exclusions", {}).setdefault("patterns", []).append(pattern)
            print_success(f"Added pattern exclusion: {pattern}")

        save_config(cfg)

    except Exception as e:
        print_error(f"Failed to add exclusion: {e}")


@exclude.command("remove")
@click.option("--file", "file_pattern", type=str, help="File pattern to remove")
@click.option("--directory", "dir_pattern", type=str, help="Directory pattern to remove")
@click.option("--pattern", type=str, help="General pattern to remove")
def exclude_remove(file_pattern: str | None, dir_pattern: str | None, pattern: str | None) -> None:
    """Remove exclusion pattern."""
    try:
        cfg = load_config() or DEFAULT_CONFIG.copy()

        if file_pattern and file_pattern in cfg.get("exclusions", {}).get("files", []):
            cfg["exclusions"]["files"].remove(file_pattern)
            print_success(f"Removed file exclusion: {file_pattern}")

        if dir_pattern and dir_pattern in cfg.get("exclusions", {}).get("directories", []):
            cfg["exclusions"]["directories"].remove(dir_pattern)
            print_success(f"Removed directory exclusion: {dir_pattern}")

        if pattern and pattern in cfg.get("exclusions", {}).get("patterns", []):
            cfg["exclusions"]["patterns"].remove(pattern)
            print_success(f"Removed pattern exclusion: {pattern}")

        save_config(cfg)

    except Exception as e:
        print_error(f"Failed to remove exclusion: {e}")


@exclude.command("list")
def exclude_list() -> None:
    """List all exclusions."""
    try:
        cfg = load_config() or DEFAULT_CONFIG.copy()
        exclusions = cfg.get("exclusions", {})

        print_info("File exclusions:")
        for pattern in exclusions.get("files", []):
            print(f"  - {pattern}")

        print_info("\nDirectory exclusions:")
        for pattern in exclusions.get("directories", []):
            print(f"  - {pattern}")

        print_info("\nGeneral patterns:")
        for pattern in exclusions.get("patterns", []):
            print(f"  - {pattern}")

    except Exception as e:
        print_error(f"Failed to list exclusions: {e}")


@config.group()
def capability() -> None:
    """Manage capability toggles."""


@capability.command("enable")
@click.argument("capability_name")
def capability_enable(capability_name: str) -> None:
    """Enable a capability."""
    try:
        cfg = load_config() or DEFAULT_CONFIG.copy()

        if capability_name not in cfg.get("capabilities", {}):
            print_error(f"Unknown capability: {capability_name}")
            return

        cfg["capabilities"][capability_name] = True
        save_config(cfg)
        print_success(f"Enabled capability: {capability_name}")

    except Exception as e:
        print_error(f"Failed to enable capability: {e}")


@capability.command("disable")
@click.argument("capability_name")
def capability_disable(capability_name: str) -> None:
    """Disable a capability."""
    try:
        cfg = load_config() or DEFAULT_CONFIG.copy()

        if capability_name not in cfg.get("capabilities", {}):
            print_error(f"Unknown capability: {capability_name}")
            return

        cfg["capabilities"][capability_name] = False
        save_config(cfg)
        print_success(f"Disabled capability: {capability_name}")

    except Exception as e:
        print_error(f"Failed to disable capability: {e}")


@capability.command("list")
def capability_list() -> None:
    """List all capabilities and their status."""
    try:
        cfg = load_config() or DEFAULT_CONFIG.copy()
        capabilities = cfg.get("capabilities", {})

        data = [{"capability": k, "enabled": v} for k, v in capabilities.items()]
        print_table(data, columns=["capability", "enabled"], title="Capabilities")

    except Exception as e:
        print_error(f"Failed to list capabilities: {e}")


@config.command("set")
@click.argument("key")
@click.argument("value")
def set_value(key: str, value: str) -> None:
    """Set a configuration value.

    Examples
    --------
        $ kgc-config set default_model llama3.3
        $ kgc-config set event_retention_days 30
    """
    try:
        cfg = load_config() or DEFAULT_CONFIG.copy()

        # Try to parse value as JSON for proper typing
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = value

        cfg.setdefault("settings", {})[key] = parsed_value
        save_config(cfg)
        print_success(f"Set {key} = {parsed_value}")

    except Exception as e:
        print_error(f"Failed to set configuration: {e}")


@config.command("get")
@click.argument("key")
def get_value(key: str) -> None:
    """Get a configuration value."""
    try:
        cfg = load_config() or DEFAULT_CONFIG.copy()

        if key in cfg.get("settings", {}):
            value = cfg["settings"][key]
            print_info(f"{key} = {value}")
        else:
            print_error(f"Configuration key not found: {key}")

    except Exception as e:
        print_error(f"Failed to get configuration: {e}")


@config.command("reset")
def reset() -> None:
    """Reset configuration to defaults."""
    try:
        if not confirm_action("Reset configuration to defaults?", default=False):
            print_info("Aborted")
            return

        save_config(DEFAULT_CONFIG)
        print_success("Configuration reset to defaults")

    except Exception as e:
        print_error(f"Failed to reset configuration: {e}")


def _display_config_tables(cfg: dict) -> None:
    """Display configuration as formatted tables.

    Parameters
    ----------
    cfg : dict
        Configuration dictionary

    """
    # Capabilities table
    if "capabilities" in cfg:
        cap_data = [{"capability": k, "enabled": v} for k, v in cfg["capabilities"].items()]
        print_table(cap_data, columns=["capability", "enabled"], title="Capabilities")
        print()

    # Settings table
    if "settings" in cfg:
        settings_data = [{"setting": k, "value": v} for k, v in cfg["settings"].items()]
        print_table(settings_data, columns=["setting", "value"], title="Settings")
        print()

    # Exclusions
    if "exclusions" in cfg:
        print_info("Exclusions:")
        for category, items in cfg["exclusions"].items():
            print(f"  {category}: {len(items)} patterns")


if __name__ == "__main__":
    config()
