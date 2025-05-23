# db/schema/extractor.py (reemplaza la importación circular en db/schema.py)

"""
Independent database schema extractor.
"""

from typing import Dict, Any, Optional, Callable

from corebrain.utils.logging import get_logger

logger = get_logger(__name__)

def extract_db_schema(db_config: Dict[str, Any], client_factory: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Extracts the database schema with dependency injection.
    
    Args:
        db_config: Database configuration
        client_factory: Optional function to create a client (avoids circular imports)
    
    Returns:
        Dictionary with the database structure
    """
    db_type = db_config.get("type", "").lower()
    schema = {
        "type": db_type,
        "database": db_config.get("database", ""),
        "tables": {},
        "tables_list": []
    }
    
    try:
        # Si tenemos un cliente especializado, usarlo
        if client_factory:
            # La factoría crea un cliente y extrae el esquema
            client = client_factory(db_config)
            return client.extract_schema()
        
        # Extracción directa sin usar cliente de Corebrain
        if db_type == "sql":
            # Código para bases de datos SQL (sin dependencias circulares)
            engine = db_config.get("engine", "").lower()
            if engine == "sqlite":
                # Extraer esquema SQLite
                import sqlite3
                # (implementación...)
            elif engine == "mysql":
                # Extraer esquema MySQL
                import mysql.connector
                # (implementación...)
            elif engine == "postgresql":
                # Extraer esquema PostgreSQL
                import psycopg2
                # (implementación...)
                
        elif db_type in ["nosql", "mongodb"]:
            # Extraer esquema MongoDB
            import pymongo
            # (implementación...)
            
        # Convertir diccionario a lista para compatibilidad
        table_list = []
        for table_name, table_info in schema["tables"].items():
            table_data = {"name": table_name}
            table_data.update(table_info)
            table_list.append(table_data)
        
        schema["tables_list"] = table_list
        return schema
        
    except Exception as e:
        logger.error(f"Error al extraer esquema: {str(e)}")
        return {"type": db_type, "tables": {}, "tables_list": []}


def create_schema_from_corebrain() -> Callable:
    """
    Creates an extraction function that uses Corebrain internally.
    Loads dynamically to avoid circular imports.
    
    Returns:
        Function that extracts schema using Corebrain
    """
    def extract_with_corebrain(db_config: Dict[str, Any]) -> Dict[str, Any]:
        # Importar dinámicamente para evitar circular
        from corebrain.core.client import Corebrain
        
        # Crear cliente temporal solo para extraer el schema
        try:
            client = Corebrain(
                api_token="temp_token",
                db_config=db_config,
                skip_verification=True
            )
            schema = client.db_schema
            client.close()
            return schema
        except Exception as e:
            logger.error(f"Error al extraer schema con Corebrain: {str(e)}")
            return {"type": db_config.get("type", ""), "tables": {}, "tables_list": []}
    
    return extract_with_corebrain


# Función pública expuesta
def extract_schema(db_config: Dict[str, Any], use_corebrain: bool = False) -> Dict[str, Any]:
    """
    Public function that decides how to extract the schema.
    
    Args:
        db_config: Database configuration
        use_corebrain: If True, uses the Corebrain class for extraction
        
    Returns:
        Database schema
    """
    if use_corebrain:
        # Intentar usar Corebrain si se solicita
        factory = create_schema_from_corebrain()
        return extract_db_schema(db_config, client_factory=factory)
    else:
        # Usar extracción directa sin dependencias circulares
        return extract_db_schema(db_config)