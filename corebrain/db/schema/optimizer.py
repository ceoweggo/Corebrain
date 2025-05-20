"""
Components for database schema optimization.
"""
import re
from typing import Dict, Any, Optional

from corebrain.utils.logging import get_logger

logger = get_logger(__name__)

class SchemaOptimizer:
    """Optimizes the database schema to reduce context size."""
    
    def __init__(self, max_tables: int = 10, max_columns_per_table: int = 15, max_samples: int = 2):
        """
        Initializes the schema optimizer.
        
        Args:
            max_tables: Maximum number of tables to include
            max_columns_per_table: Maximum number of columns per table
            max_samples: Maximum number of sample rows per table
        """
        self.max_tables = max_tables
        self.max_columns_per_table = max_columns_per_table
        self.max_samples = max_samples
        
        # Tablas importantes que siempre deben incluirse si existen
        self.priority_tables = set([
            "users", "customers", "products", "orders", "transactions",
            "invoices", "accounts", "clients", "employees", "services"
        ])
        
        # Tablas típicamente menos importantes
        self.low_priority_tables = set([
            "logs", "sessions", "tokens", "temp", "cache", "metrics",
            "statistics", "audit", "history", "archives", "settings"
        ])
    
    def optimize_schema(self, db_schema: Dict[str, Any], query: str = None) -> Dict[str, Any]:
        """
        Optimizes the schema to reduce its size.
        
        Args:
            db_schema: Original database schema
            query: User query (to prioritize relevant tables)
            
        Returns:
            Optimized schema
        """
        # Crear copia para no modificar el original
        optimized_schema = {
            "type": db_schema.get("type", ""),
            "database": db_schema.get("database", ""),
            "engine": db_schema.get("engine", ""),
            "tables": {},
            "tables_list": []
        }
        
        # Determinar tablas relevantes para la consulta
        query_relevant_tables = set()
        if query:
            # Extraer potenciales nombres de tablas de la consulta
            normalized_query = query.lower()
            
            # Obtener nombres de todas las tablas
            all_table_names = [
                name.lower() for name in db_schema.get("tables", {}).keys()
            ]
            
            # Buscar menciones a tablas en la consulta
            for table_name in all_table_names:
                # Buscar el nombre exacto (como palabra completa)
                if re.search(r'\b' + re.escape(table_name) + r'\b', normalized_query):
                    query_relevant_tables.add(table_name)
                
                # También buscar formas singulares/plurales simples
                if table_name.endswith('s') and re.search(r'\b' + re.escape(table_name[:-1]) + r'\b', normalized_query):
                    query_relevant_tables.add(table_name)
                elif not table_name.endswith('s') and re.search(r'\b' + re.escape(table_name + 's') + r'\b', normalized_query):
                    query_relevant_tables.add(table_name)
        
        # Priorizar tablas a incluir
        table_scores = {}
        for table_name in db_schema.get("tables", {}):
            score = 0
            
            # Tablas mencionadas en la consulta tienen máxima prioridad
            if table_name.lower() in query_relevant_tables:
                score += 100
            
            # Tablas importantes
            if table_name.lower() in self.priority_tables:
                score += 50
            
            # Tablas poco importantes
            if table_name.lower() in self.low_priority_tables:
                score -= 30
            
            # Tablas con más columnas pueden ser más relevantes
            table_info = db_schema["tables"].get(table_name, {})
            column_count = len(table_info.get("columns", []))
            score += min(column_count, 20)  # Limitar a 20 puntos máximo
            
            # Guardar puntuación
            table_scores[table_name] = score
        
        # Ordenar tablas por puntuación
        sorted_tables = sorted(table_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Limitar número de tablas
        selected_tables = [name for name, _ in sorted_tables[:self.max_tables]]
        
        # Copiar tablas seleccionadas con optimizaciones
        for table_name in selected_tables:
            table_info = db_schema["tables"].get(table_name, {})
            
            # Optimizar columnas
            columns = table_info.get("columns", [])
            if len(columns) > self.max_columns_per_table:
                # Mantener las columnas más importantes (id, nombre, clave primaria, etc)
                important_columns = []
                other_columns = []
                
                for col in columns:
                    col_name = col.get("name", "").lower()
                    if col_name in ["id", "uuid", "name", "key", "code"] or "id" in col_name:
                        important_columns.append(col)
                    else:
                        other_columns.append(col)
                
                # Tomar las columnas importantes y completar con otras hasta el límite
                optimized_columns = important_columns
                remaining_slots = self.max_columns_per_table - len(optimized_columns)
                if remaining_slots > 0:
                    optimized_columns.extend(other_columns[:remaining_slots])
            else:
                optimized_columns = columns
            
            # Optimizar datos de muestra
            sample_data = table_info.get("sample_data", [])
            optimized_samples = sample_data[:self.max_samples] if sample_data else []
            
            # Guardar tabla optimizada
            optimized_schema["tables"][table_name] = {
                "columns": optimized_columns,
                "sample_data": optimized_samples
            }
            
            # Añadir a la lista de tablas
            optimized_schema["tables_list"].append({
                "name": table_name,
                "columns": optimized_columns,
                "sample_data": optimized_samples
            })
        
        return optimized_schema

