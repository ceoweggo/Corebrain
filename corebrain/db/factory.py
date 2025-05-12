"""
Fábrica de conectores de base de datos.
"""
from typing import Dict, Any

from corebrain.db.connector import DatabaseConnector
from corebrain.db.connectors.sql import SQLConnector
from corebrain.db.connectors.mongodb import MongoDBConnector

def get_connector(db_config: Dict[str, Any], timeout: int = 10) -> DatabaseConnector:
    """
    Fábrica de conectores de base de datos según la configuración
    
    Args:
        db_config: Configuración de la base de datos
        timeout: Timeout para operaciones de DB
        
    Returns:
        Instancia de conector apropiado
    """
    db_type = db_config.get("type", "").lower()
    engine = db_config.get("engine", "").lower()
    
    if db_type == "sql":
        return SQLConnector(db_config, timeout)
    elif db_type in ["nosql", "mongodb"] or engine == "mongodb":
        return MongoDBConnector(db_config, timeout)
    else:
        raise ValueError(f"Tipo de base de datos no soportado: {db_type}")