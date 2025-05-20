"""
Conectores base para diferentes tipos de bases de datos.
"""
from typing import Dict, Any, List, Optional, Callable

class DatabaseConnector:
    """Clase base para todos los conectores de base de datos"""
    
    def __init__(self, config: Dict[str, Any], timeout: int = 10):
        self.config = config
        self.timeout = timeout
        self.connection = None
    
    def connect(self):
        """Establece conexión a la base de datos"""
        raise NotImplementedError
    
    def extract_schema(self, sample_limit: int = 5, table_limit: Optional[int] = None, 
                      progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Extrae el esquema de la base de datos"""
        raise NotImplementedError
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Ejecuta una consulta en la base de datos"""
        raise NotImplementedError
    
    def close(self):
        """Cierra la conexión"""
        if self.connection:
            try:
                self.connection.close()
            except:
                pass