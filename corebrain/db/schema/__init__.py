"""
Components for extracting and optimizing database schemas.
"""
from .extractor import extract_schema
from .optimizer import SchemaOptimizer

# Alias for compatibility with existing code
extract_db_schema = extract_schema
schemaOptimizer = SchemaOptimizer

__all__ = ['extract_schema', 'extract_db_schema', 'schemaOptimizer']