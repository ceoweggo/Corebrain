"""
Database connectors for different engines.
"""

from typing import Dict, Any

from corebrain.db.connectors.sql import SQLConnector
from corebrain.db.connectors.nosql import NoSQLConnector

def get_connector(db_config: Dict[str, Any]):
    """
    Gets the appropriate connector based on the database configuration.
    
    Args:
        db_config: Database configuration
        
    Returns:
        Instance of the appropriate connector
    """
    db_type = db_config.get("type", "").lower()
    engine = db_config.get("engine", "").lower()

    match db_type:
        case "sql":
            return SQLConnector(db_config, engine)
        case "nosql":
            return NoSQLConnector(db_config, engine)
        case _:
            raise ValueError(f"Unsupported database type: {db_type}")