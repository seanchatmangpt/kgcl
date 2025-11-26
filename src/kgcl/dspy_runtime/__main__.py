"""
CLI for DSPy runtime.

Provides command-line interface for invoking signatures, health checks,
model management, and testing.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from .ollama_config import OllamaLM, health_check
from .unrdf_bridge import UNRDFBridge

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def cmd_health(args) -> int:
    """Health check command."""
    print("Running health check...")

    health = health_check()

    # Print results
    print(json.dumps(health, indent=2))

    if health["status"] == "healthy":
        print("\n✓ All systems healthy")
        return 0
    if health["status"] == "degraded":
        print(f"\n⚠ System degraded: {health.get('message')}")
        return 1
    print(f"\n✗ System unhealthy: {health.get('message', health.get('error'))}")
    return 1


def cmd_models(args) -> int:
    """List models command."""
    try:
        lm = OllamaLM()

        if not lm.is_available():
            print("✗ Ollama service not available")
            return 1

        models = lm.list_models()

        if not models:
            print("No models available. Pull models with: ollama pull <model>")
            return 0

        print(f"Available models ({len(models)}):")
        for model in models:
            name = model.get("name", "unknown")
            size = model.get("size", 0)
            modified = model.get("modified_at", "unknown")

            size_gb = size / (1024**3)
            print(f"  • {name} ({size_gb:.2f} GB) - modified: {modified}")

        return 0
    except Exception as e:
        print(f"✗ Error listing models: {e}")
        return 1


def cmd_model_info(args) -> int:
    """Model info command."""
    try:
        lm = OllamaLM()

        if not lm.is_available():
            print("✗ Ollama service not available")
            return 1

        info = lm.get_model_info(args.model)
        print(json.dumps(info, indent=2, default=str))
        return 0
    except ValueError as e:
        print(f"✗ {e}")
        return 1
    except Exception as e:
        print(f"✗ Error getting model info: {e}")
        return 1


def cmd_invoke(args) -> int:
    """Invoke signature command."""
    try:
        # Parse inputs
        if args.inputs_file:
            with open(args.inputs_file) as f:
                inputs = json.load(f)
        elif args.inputs:
            inputs = json.loads(args.inputs)
        else:
            print("✗ Error: Must provide --inputs or --inputs-file")
            return 1

        # Initialize bridge
        bridge = UNRDFBridge()
        bridge.initialize()

        # Parse source features and signatures if provided
        source_features = None
        source_signatures = None

        if args.source_features:
            source_features = args.source_features.split(",")

        if args.source_signatures:
            source_signatures = args.source_signatures.split(",")

        # Invoke
        print(f"Invoking {args.signature} from {args.module}...")
        result = bridge.invoke(
            module_path=args.module,
            signature_name=args.signature,
            inputs=inputs,
            source_features=source_features,
            source_signatures=source_signatures,
        )

        # Print results
        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Results written to {args.output}")
        else:
            print(json.dumps(result, indent=2))

        if result["result"]["success"]:
            print(
                f"\n✓ Invocation successful (receipt: {result['receipt']['receipt_id']})"
            )
            return 0
        print(f"\n✗ Invocation failed: {result['result']['error']}")
        return 1

    except Exception as e:
        logger.error(f"Invocation error: {e}", exc_info=True)
        print(f"✗ Error: {e}")
        return 1


def cmd_receipts(args) -> int:
    """List receipts command."""
    try:
        bridge = UNRDFBridge()

        receipts = bridge.list_receipts(
            signature_name=args.signature, success=args.success, limit=args.limit
        )

        if not receipts:
            print("No receipts found")
            return 0

        print(f"Receipts ({len(receipts)}):")
        for receipt in receipts:
            status = "✓" if receipt["success"] else "✗"
            latency = receipt.get("latency_seconds", 0)
            print(
                f"  {status} {receipt['receipt_id']} - {receipt['signature_name']} - {latency:.3f}s"
            )

        return 0
    except Exception as e:
        print(f"✗ Error listing receipts: {e}")
        return 1


def cmd_stats(args) -> int:
    """Statistics command."""
    try:
        bridge = UNRDFBridge()
        stats = bridge.get_stats()
        print(json.dumps(stats, indent=2))
        return 0
    except Exception as e:
        print(f"✗ Error getting stats: {e}")
        return 1


def cmd_test(args) -> int:
    """Test invocation command."""
    try:
        # Create a simple test signature file
        test_signature = '''
import dspy

class SimpleQA(dspy.Signature):
    """Answer a question with a short response."""
    question = dspy.InputField()
    answer = dspy.OutputField()
'''

        # Write test signature to temp file
        test_dir = Path("/tmp/kgcl_dspy_test")
        test_dir.mkdir(exist_ok=True)
        test_file = test_dir / "test_signature.py"

        with open(test_file, "w") as f:
            f.write(test_signature)

        print(f"Created test signature at {test_file}")

        # Invoke test signature
        bridge = UNRDFBridge()
        bridge.initialize()

        inputs = {"question": "What is 2 + 2?"}
        print(f"Testing with inputs: {inputs}")

        result = bridge.invoke(
            module_path=str(test_file), signature_name="SimpleQA", inputs=inputs
        )

        print("\nTest Results:")
        print(json.dumps(result, indent=2))

        if result["result"]["success"]:
            print("\n✓ Test passed!")
            return 0
        print(f"\n✗ Test failed: {result['result']['error']}")
        return 1

    except Exception as e:
        logger.error(f"Test error: {e}", exc_info=True)
        print(f"✗ Error: {e}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DSPy runtime CLI for KGCL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Health check command
    health_parser = subparsers.add_parser(
        "health", help="Check health of Ollama service and DSPy runtime"
    )
    health_parser.set_defaults(func=cmd_health)

    # Models command
    models_parser = subparsers.add_parser("models", help="List available Ollama models")
    models_parser.set_defaults(func=cmd_models)

    # Model info command
    info_parser = subparsers.add_parser(
        "model-info", help="Get information about a specific model"
    )
    info_parser.add_argument("model", help="Model name")
    info_parser.set_defaults(func=cmd_model_info)

    # Invoke command
    invoke_parser = subparsers.add_parser("invoke", help="Invoke a DSPy signature")
    invoke_parser.add_argument("module", help="Path to signature module")
    invoke_parser.add_argument("signature", help="Signature class name")
    invoke_parser.add_argument("--inputs", help="JSON string of inputs")
    invoke_parser.add_argument("--inputs-file", help="Path to JSON file with inputs")
    invoke_parser.add_argument(
        "--output", help="Output file for results (default: stdout)"
    )
    invoke_parser.add_argument(
        "--source-features", help="Comma-separated source feature URIs"
    )
    invoke_parser.add_argument(
        "--source-signatures", help="Comma-separated source signature URIs"
    )
    invoke_parser.set_defaults(func=cmd_invoke)

    # Receipts command
    receipts_parser = subparsers.add_parser("receipts", help="List invocation receipts")
    receipts_parser.add_argument("--signature", help="Filter by signature name")
    receipts_parser.add_argument(
        "--success",
        type=lambda x: x.lower() == "true",
        help="Filter by success status (true/false)",
    )
    receipts_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of receipts (default: 100)",
    )
    receipts_parser.set_defaults(func=cmd_receipts)

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show runtime statistics")
    stats_parser.set_defaults(func=cmd_stats)

    # Test command
    test_parser = subparsers.add_parser("test", help="Run test invocation")
    test_parser.set_defaults(func=cmd_test)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
