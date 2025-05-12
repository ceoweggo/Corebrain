"""
Interfaces abstractas para conexiones de bases de datos.
"""
from typing import Dict, Any, List, Optional, Protocol
from abc import ABC, abstractmethod

from corebrain.core.common import ConfigDict, SchemaDict

class DatabaseConnector(ABC):
    """Interfaz abstracta para conectores de bases de datos"""
    
    @abstractmethod
    def connect(self, config: ConfigDict) -> Any:
        """Establece conexión con la base de datos"""
        pass
    
    @abstractmethod
    def extract_schema(self, connection: Any) -> SchemaDict:
        """Extrae el esquema de la base de datos"""
        pass
    
    @abstractmethod
    def execute_query(self, connection: Any, query: str) -> List[Dict[str, Any]]:
        """Ejecuta una consulta y devuelve resultados"""
        pass
    
    @abstractmethod
    def close(self, connection: Any) -> None:
        """Cierra la conexión"""
        pass

# Posteriormente se podrían implementar conectores específicos:
# - SQLiteConnector
# - MySQLConnector
# - PostgresConnector
# - MongoDBConnector