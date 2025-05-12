"""
Conectores de bases de datos para diferentes motores.
"""

from typing import Dict, Any

from corebrain.db.connectors.sql import SQLConnector
from corebrain.db.connectors.mongodb import MongoDBConnector

def get_connector(db_config: Dict[str, Any]):
    """
    Obtiene el conector adecuado según la configuración de la base de datos.
    
    Args:
        db_config: Configuración de la base de datos
        
    Returns:
        Instancia del conector apropiado
    """
    db_type = db_config.get("type", "").lower()
    
    if db_type == "sql":
        engine = db_config.get("engine", "").lower()
        return SQLConnector(db_config, engine)
    elif db_type == "nosql" or db_type == "mongodb":
        return MongoDBConnector(db_config)
    else:
        raise ValueError(f"Tipo de base de datos no soportado: {db_type}")