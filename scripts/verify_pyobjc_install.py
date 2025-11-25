#!/usr/bin/env python3
"""
Verification script for PyObjC Agent installation.

Checks:
- Required PyObjC frameworks
- Directory structure
- Permissions
- Configuration
"""

import sys
from pathlib import Path


def check_framework(framework_name: str) -> bool:
    """Check if a PyObjC framework is available."""
    try:
        __import__(framework_name)
        print(f"✓ {framework_name}")
        return True
    except ImportError:
        print(f"✗ {framework_name} (install: pip install pyobjc-framework-{framework_name})")
        return False


def check_directory(path: str) -> bool:
    """Check if a directory exists."""
    p = Path(path)
    exists = p.exists()
    if exists:
        print(f"✓ {path}")
    else:
        print(f"✗ {path} (will be created on first run)")
    return exists


def check_module(module_name: str) -> bool:
    """Check if a Python module is available."""
    try:
        __import__(module_name)
        print(f"✓ {module_name}")
        return True
    except ImportError:
        print(f"✗ {module_name} (install: pip install {module_name})")
        return False


def main():
    """Run verification checks."""
    print("=" * 60)
    print("PyObjC Agent Installation Verification")
    print("=" * 60)

    all_ok = True

    # Check PyObjC frameworks
    print("\n1. PyObjC Frameworks:")
    frameworks = ["AppKit", "Foundation", "EventKit"]
    for fw in frameworks:
        if not check_framework(fw):
            all_ok = False

    # Check optional frameworks
    print("\n2. Optional PyObjC Frameworks:")
    optional = ["Quartz", "CoreLocation", "AVFoundation"]
    for fw in optional:
        check_framework(fw)

    # Check dependencies
    print("\n3. Dependencies:")
    deps = [
        "yaml",
        "opentelemetry.trace",
        "opentelemetry.sdk.trace",
        "opentelemetry.exporter.otlp.proto.grpc.trace_exporter"
    ]
    for dep in deps:
        if not check_module(dep):
            all_ok = False

    # Check directories
    print("\n4. Directories:")
    dirs = [
        "/Users/sac/dev/kgcl/data",
        "/Users/sac/dev/kgcl/logs",
        "/Users/sac/dev/kgcl/config"
    ]
    for d in dirs:
        check_directory(d)

    # Check module import
    print("\n5. PyObjC Agent Module:")
    try:
        from kgcl.pyobjc_agent import PyObjCAgent
        print("✓ kgcl.pyobjc_agent imports successfully")
    except ImportError as e:
        print(f"✗ kgcl.pyobjc_agent import failed: {e}")
        all_ok = False

    # Check configuration
    print("\n6. Configuration:")
    config_path = Path("/Users/sac/dev/kgcl/config/pyobjc_agent.yaml")
    if config_path.exists():
        print(f"✓ Configuration file exists: {config_path}")
    else:
        print(f"✗ Configuration file missing (run: python -m kgcl.pyobjc_agent config --generate)")
        all_ok = False

    # Summary
    print("\n" + "=" * 60)
    if all_ok:
        print("✓ All required components are installed!")
        print("\nNext steps:")
        print("  1. Grant required permissions in System Preferences")
        print("  2. Run: python -m kgcl.pyobjc_agent status")
        print("  3. Run: python -m kgcl.pyobjc_agent run")
        return 0
    else:
        print("✗ Some components are missing. Install them and run again.")
        print("\nQuick install:")
        print("  pip install pyobjc-framework-Cocoa pyobjc-framework-EventKit")
        print("  pip install opentelemetry-api opentelemetry-sdk")
        print("  pip install opentelemetry-exporter-otlp-proto-grpc")
        print("  pip install pyyaml")
        return 1


if __name__ == "__main__":
    sys.exit(main())
