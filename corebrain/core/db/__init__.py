"""
Conectores de bases de datos para Corebrain SDK.

Este paquete proporciona conectores para diferentes tipos y 
motores de bases de datos soportados por Corebrain.
"""
from corebrain.core.db.connector import DatabaseConnector
from corebrain.core.db.factory import get_connector
from corebrain.core.db.engines import get_available_engines
from corebrain.core.db.connectors.sql import SQLConnector
from corebrain.core.db.connectors.mongodb import MongoDBConnector
from corebrain.core.db.schema_file import get_schema_with_dynamic_import
from corebrain.core.db.schema.optimizer import SchemaOptimizer
from corebrain.core.db.schema.extractor import extract_db_schema

# Exportación explícita de componentes públicos
__all__ = [
    'DatabaseConnector',
    'get_connector',
    'get_available_engines',
    'SQLConnector',
    'MongoDBConnector',
    'SchemaOptimizer',
    'extract_db_schema',
    'get_schema_with_dynamic_import'
]