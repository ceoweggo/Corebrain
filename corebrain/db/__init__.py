"""
Database connectors for Corebrain SDK.

This package provides connectors for different types and 
database engines supported by Corebrain.
"""
from corebrain.db.connector import DatabaseConnector
from corebrain.db.factory import get_connector
from corebrain.db.engines import get_available_engines
from corebrain.db.connectors.sql import SQLConnector
from corebrain.db.connectors.nosql import NoSQLConnector
from corebrain.db.schema_file import get_schema_with_dynamic_import
from corebrain.db.schema.optimizer import SchemaOptimizer
from corebrain.db.schema.extractor import extract_db_schema

# Export public components
__all__ = [
    'DatabaseConnector',
    'get_connector',
    'get_available_engines',
    'SQLConnector',
    'NoSQLConnector',
    'SchemaOptimizer',
    'extract_db_schema',
    'get_schema_with_dynamic_import'
]