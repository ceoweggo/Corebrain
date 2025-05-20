"""
Database connector factory.
"""
from typing import Dict, Any

from corebrain.db.connector import DatabaseConnector
from corebrain.db.connectors.sql import SQLConnector
from corebrain.db.connectors.mongodb import MongoDBConnector

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
    elif db_type in ["nosql", "mongodb"] or engine == "mongodb":
        return MongoDBConnector(db_config, timeout)
    else:
        raise ValueError(f"Tipo de base de datos no soportado: {db_type}")