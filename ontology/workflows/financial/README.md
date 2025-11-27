# Financial Domain Workflows

Domain-specific workflows for financial processing.

## Files

- **atm_transaction.ttl**
  - ATM transaction processing workflow
  - Demonstrates financial transaction patterns

- **payroll.ttl**
  - Payroll processing workflow
  - Employee payment processing

- **swift_payment.ttl**
  - SWIFT payment processing workflow
  - International payment processing

## Purpose

These workflows demonstrate:
- Real-world financial domain patterns
- Complex transaction processing
- Domain-specific workflow requirements

## Usage

```python
from rdflib import Graph

# Load a financial workflow
g = Graph()
g.parse("ontology/workflows/financial/swift_payment.ttl", format="turtle")
```

