"""Testcontainers infrastructure for KGCL integration tests.

This package provides Docker container fixtures for:
- RDF stores (Oxigraph Server, Fuseki)
- Databases (PostgreSQL, Redis)
- Message queues (RabbitMQ)
- Network configuration

All containers are managed via pytest fixtures with appropriate scoping
for efficient resource usage.
"""
