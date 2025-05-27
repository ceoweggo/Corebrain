"""
Database connector factory.
"""
from typing import Dict, Any

from corebrain.db.connector import DatabaseConnector
from corebrain.db.connectors.sql import SQLConnector
from corebrain.db.connectors.nosql import NoSQLConnector

def get_connector(db_config: Dict[str, Any], timeout: int = 10) -> DatabaseConnector:
    """
    Database connector factory based on configuration.
    
    Args:
        db_config: Database configuration
        timeout: Timeout for DB operations
        
    Returns:
        Instance of the appropriate connector
    """
    db_type = db_config.get("type", "").lower()
    engine = db_config.get("engine", "").lower()
    
    if db_type == "sql":
        return SQLConnector(db_config, timeout)
    elif db_type == "nosql":
        if engine == "mongodb":
            return NoSQLConnector(db_config, timeout)
        else:
            raise ValueError(f"Unsupported NoSQL engine: {engine}")
    else:
        raise ValueError(f"Unsupported database type: {db_type}")