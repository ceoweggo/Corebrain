"""
Corebrain SDK.

This package provides a Python SDK for interacting with the Corebrain API
and enables natural language queries to relational and non-relational databases.
"""
import logging
from typing import Dict, Any, List, Optional

# Configuración básica de logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Importaciones seguras (sin dependencias circulares)
from corebrain.db.engines import get_available_engines
from corebrain.core.client import Corebrain
from corebrain.config.manager import ConfigManager

# Exportación explícita de componentes públicos
__all__ = [
    'init',
    'extract_db_schema',
    'list_configurations',
    'remove_configuration',
    'get_available_engines',
    'get_config',
    '__version__'
]

# Variable de versión
__version__ = "1.0.0"

def init(api_key: str, config_id: str, skip_verification: bool = False) -> Corebrain:
    """
    Initialize the Corebrain SDK with the provided API key and configuration.
    
    Args:
        api_key: API Key de Corebrain
        config_id: ID de la configuración a usar
        
    Returns:
        Instancia de Corebrain configurada
    """
    return Corebrain(api_key=api_key, config_id=config_id, skip_verification=skip_verification)

# Funciones de conveniencia a nivel de paquete
def list_configurations(api_key: str) -> List[str]:
    """
    Lists the available configurations for an API key.
    
    Args:
        api_key: Corebrain API Key
        
    Returns:
        List of available configuration IDs
    """
    config_manager = ConfigManager()
    return config_manager.list_configs(api_key)

def remove_configuration(api_key: str, config_id: str) -> bool:
    """
    Deletes a specific configuration.
    
    Args:
        api_key: Corebrain API Key
        config_id: ID of the configuration to delete
        
    Returns:
        True if deleted successfully, False otherwise
    """
    config_manager = ConfigManager()
    return config_manager.remove_config(api_key, config_id)

def get_config(api_key: str, config_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a specific configuration.
    
    Args:
        api_key: Corebrain API Key
        config_id: ID of the configuration to retrieve
        
    Returns:
        Dictionary with the configuration or None if it does not exist
    """
    config_manager = ConfigManager()
    return config_manager.get_config(api_key, config_id)