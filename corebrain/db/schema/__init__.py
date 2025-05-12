"""
Componentes para extracción y optimización de esquemas de base de datos.
"""
from .extractor import extract_schema
from .optimizer import SchemaOptimizer

# Alias para compatibilidad con código existente
extract_db_schema = extract_schema
schemaOptimizer = SchemaOptimizer

__all__ = ['extract_schema', 'extract_db_schema', 'schemaOptimizer']