#!/usr/bin/env python3
"""Proof script: Python generator actually works.

This script PROVES (not claims) that the Python generator:
1. Parses real OWL class definitions
2. Generates valid Python code (dataclass/pydantic/plain)
3. Code compiles and imports successfully
4. Contains actual class definitions with properties
"""

import sys
import tempfile
from pathlib import Path

from kgcl.codegen import CodeGenOrchestrator, GenerationConfig, OutputFormat


def test_style(style: OutputFormat, style_name: str) -> None:
    """Test a specific Python generation style."""
    print(f"\n--- Testing {style_name} style ---\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Real OWL class definition
        input_file = tmpdir_path / "classes.ttl"
        input_file.write_text(
            """
@prefix ex: <http://example.org/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:Person
    a owl:Class ;
    rdfs:label "Person" ;
    rdfs:comment "Represents a person in the system" .

ex:Employee
    a owl:Class ;
    rdfs:label "Employee" ;
    rdfs:subClassOf ex:Person ;
    rdfs:comment "An employee is a person with employment details" .

ex:name
    a owl:DatatypeProperty ;
    rdfs:domain ex:Person ;
    rdfs:range xsd:string ;
    rdfs:label "name" ;
    rdfs:comment "Person's full name" .

ex:email
    a owl:DatatypeProperty ;
    rdfs:domain ex:Person ;
    rdfs:range xsd:string ;
    rdfs:label "email" ;
    rdfs:comment "Email address" .

ex:age
    a owl:DatatypeProperty ;
    rdfs:domain ex:Person ;
    rdfs:range xsd:integer ;
    rdfs:label "age" .

ex:employeeId
    a owl:DatatypeProperty ;
    rdfs:domain ex:Employee ;
    rdfs:range xsd:string ;
    rdfs:label "employee_id" ;
    rdfs:comment "Unique employee identifier" .
"""
        )

        print(f"✓ Created test OWL file: {input_file}")

        # Generate Python module
        output_dir = tmpdir_path / "generated"
        template_dir = Path(__file__).parent.parent / "templates" / "python"

        config = GenerationConfig(format=style, output_dir=output_dir, template_dir=template_dir)

        orchestrator = CodeGenOrchestrator()
        result = orchestrator.generate(input_file, config)

        print(f"✓ Generated Python module: {result.output_path}")
        print(f"  Output size: {result.output_path.stat().st_size} bytes")

        # Verify source
        source = result.source
        print("\n✓ Source preview (first 800 chars):")
        print(f"  {source[:800]}\n")

        # Compile check
        try:
            compile(source, str(result.output_path), "exec")
            print("✓ Python code compiles successfully\n")
        except SyntaxError as e:
            print(f"✗ FAIL: Syntax error in generated code: {e}")
            print(f"  Full source:\n{source}")
            raise

        # Import check - actually try to import the module
        try:
            sys.path.insert(0, str(output_dir))
            module_name = result.output_path.stem

            # Execute the module to get its namespace
            namespace: dict[str, any] = {}
            exec(source, namespace)

            print("✓ Module executes successfully")

            # Verify classes exist
            assert "Person" in namespace, "Person class not found"
            assert "Employee" in namespace, "Employee class not found"
            print("✓ Found Person and Employee classes\n")

            # Verify class structure
            Person = namespace["Person"]
            print(f"✓ Person class: {Person}")

            # Try to instantiate (this proves it's real, not theater)
            if style == OutputFormat.PYTHON_DATACLASS:
                # Dataclass instantiation
                person = Person(name="Alice", email="alice@example.com", age=30)
                assert person.name == "Alice"
                assert person.email == "alice@example.com"
                assert person.age == 30
                print(f"✓ Dataclass instantiation works: {person}")
            elif style == OutputFormat.PYTHON_PYDANTIC:
                # Pydantic model instantiation
                person = Person(name="Bob", email="bob@example.com", age=25)
                assert person.name == "Bob"
                print(f"✓ Pydantic model instantiation works: {person}")
            else:
                # Plain class instantiation
                person = Person(name="Charlie", email="charlie@example.com", age=35)
                assert person.name == "Charlie"
                print(f"✓ Plain class instantiation works: {person}")

        except Exception as e:
            print(f"✗ FAIL: Import/execution error: {e}")
            print(f"  Full source:\n{source}")
            raise
        finally:
            sys.path.remove(str(output_dir))

        print(f"\n✓ {style_name} generator PROVEN to work")


def main() -> None:
    """Prove Python generator works for all styles."""
    print("=== Proof: Python Generator ===\n")

    # Test all three styles
    test_style(OutputFormat.PYTHON_DATACLASS, "Dataclass")
    test_style(OutputFormat.PYTHON_PYDANTIC, "Pydantic")
    test_style(OutputFormat.PYTHON_PLAIN, "Plain class")

    print("\n=== PROOF COMPLETE: Python generator works ===")
    print("✓ All three styles (dataclass/pydantic/plain) work")
    print("✓ Parsed real OWL class definitions")
    print("✓ Generated valid, compilable Python code")
    print("✓ Code imports and executes successfully")
    print("✓ Classes instantiate and work correctly")
    print("✓ Properties are accessible")


if __name__ == "__main__":
    main()
