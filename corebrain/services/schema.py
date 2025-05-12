
# Nuevo directorio: services/
# Nuevo archivo: services/schema_service.py
"""
Servicios para manejo de esquemas de base de datos.
"""
from typing import Dict, Any, Optional

from corebrain.config.manager import ConfigManager
from corebrain.db.schema import extract_db_schema, SchemaOptimizer

class SchemaService:
    """Servicio para operaciones de esquema de base de datos."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.schema_optimizer = SchemaOptimizer()
    
    def get_schema(self, api_token: str, config_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el esquema para una configuración específica."""
        config = self.config_manager.get_config(api_token, config_id)
        if not config:
            return None
        
        return extract_db_schema(config)
    
    def optimize_schema(self, schema: Dict[str, Any], query: str = None) -> Dict[str, Any]:
        """Optimiza un esquema existente."""
        return self.schema_optimizer.optimize_schema(schema, query)
    
    # Otros métodos de servicio...