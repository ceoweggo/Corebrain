# db/schema/extractor.py (replaces circular import in db/schema.py)

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
        # If we have a specialized client, use it
        if client_factory:
            # The factory creates a client and extracts the schema
            client = client_factory(db_config)
            return client.extract_schema()
        
        # Direct extraction without using Corebrain client
        if db_type == "sql":
            # Code for SQL databases (without circular dependencies)
            engine = db_config.get("engine", "").lower()
            if engine == "sqlite":
                # Extract SQLite schema
                import sqlite3
                # (implementation...)
            elif engine == "mysql":
                # Extraer esquema MySQL
                import mysql.connector
                # (implementation...)
            elif engine == "postgresql":
                # Extraer esquema PostgreSQL
                import psycopg2
                # (implementación...)
                
        elif db_type in ["nosql", "mongodb"]:
            # Extract MongoDB schema
            import pymongo
            # (implementation...)
            
        # Convert dictionary to list for compatibility
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
        # Import dynamically to avoid circularity
        from corebrain.core.client import Corebrain
        
        # Create temporary client just to extract the schema
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


# Public function exposed
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
        # Attempt to use Corebrain if requested
        factory = create_schema_from_corebrain()
        return extract_db_schema(db_config, client_factory=factory)
    else:
        # Use direct extraction without circular dependencies
        return extract_db_schema(db_config)