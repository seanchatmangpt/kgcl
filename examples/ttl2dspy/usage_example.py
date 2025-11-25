"""Example usage of TTL2DSPy."""

from pathlib import Path
from kgcl.ttl2dspy import UltraOptimizer, ModuleWriter, CacheConfig


def main():
    """Demonstrate TTL2DSPy usage."""

    # Path to example ontology
    ontology_path = Path(__file__).parent / "example_ontology.ttl"
    output_dir = Path(__file__).parent / "generated"

    print("=" * 60)
    print("TTL2DSPy Example: Generate DSPy Signatures from SHACL")
    print("=" * 60)
    print()

    # Configure caching
    config = CacheConfig(
        memory_cache_enabled=True,
        disk_cache_enabled=True,
        max_disk_cache_age=3600,
    )

    # Create optimizer
    print("1. Creating optimizer with caching enabled...")
    optimizer = UltraOptimizer(config)
    print("   ✓ Optimizer ready")
    print()

    # Parse ontology
    print(f"2. Parsing ontology: {ontology_path.name}")
    shapes = optimizer.parse_with_cache(ontology_path)
    print(f"   ✓ Found {len(shapes)} SHACL shapes")
    print()

    # Show shape details
    print("3. Shape details:")
    for i, shape in enumerate(shapes, 1):
        print(f"   {i}. {shape.name}")
        print(f"      Signature: {shape.signature_name}")
        print(f"      Inputs: {len(shape.input_properties)}")
        print(f"      Outputs: {len(shape.output_properties)}")
        if shape.description:
            desc = shape.description[:60] + "..." if len(shape.description) > 60 else shape.description
            print(f"      Description: {desc}")
    print()

    # Generate code
    print("4. Generating DSPy signature code...")
    code = optimizer.generate_with_cache(shapes)
    print(f"   ✓ Generated {len(code.splitlines())} lines of code")
    print()

    # Show sample of generated code
    print("5. Sample of generated code:")
    print("   " + "-" * 56)
    for line in code.splitlines()[:20]:
        print(f"   {line}")
    print("   " + "-" * 56)
    print(f"   ... ({len(code.splitlines()) - 20} more lines)")
    print()

    # Write module
    print(f"6. Writing module to {output_dir}/")
    writer = ModuleWriter()
    result = writer.write_module(
        code=code,
        output_path=output_dir / "llm_signatures.py",
        shapes_count=len(shapes),
        ttl_source=ontology_path,
        format_code=True,
    )
    print(f"   ✓ Wrote {result.signatures_count} signatures")
    print(f"   ✓ Output: {result.output_path}")
    print(f"   ✓ Size: {result.file_size} bytes")
    print(f"   ✓ Lines: {result.lines_count}")
    print(f"   ✓ Time: {result.write_time:.3f}s")
    print()

    # Write receipt
    print("7. Writing JSON receipt...")
    receipt_path = writer.write_receipt(result)
    print(f"   ✓ Receipt: {receipt_path}")
    print()

    # Show cache statistics
    print("8. Cache statistics:")
    stats = optimizer.get_detailed_stats()
    cache_stats = stats["cache"]
    print(f"   Memory hits: {cache_stats['memory_hits']}")
    print(f"   Memory misses: {cache_stats['memory_misses']}")
    print(f"   Memory hit rate: {cache_stats['memory_hit_rate']:.2%}")
    print(f"   Parse time: {cache_stats['total_parse_time']:.3f}s")
    print(f"   Generate time: {cache_stats['total_generate_time']:.3f}s")
    print()

    print("=" * 60)
    print("✓ Complete! Generated signatures are ready to use.")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Import the generated signatures:")
    print(f"     from examples.ttl2dspy.generated.llm_signatures import *")
    print()
    print("  2. Use with DSPy:")
    print("     import dspy")
    print("     summarizer = dspy.Predict(TextSummarizationSignature)")
    print("     result = summarizer(text='...', max_length=100)")
    print()


if __name__ == "__main__":
    main()
