"""
Utilidades generales para Corebrain SDK.

Este paquete proporciona utilidades compartidas por diferentes 
componentes del SDK, como serialización, cifrado y logging.
"""
import logging

from corebrain.utils.serializer import serialize_to_json, JSONEncoder
from corebrain.utils.encrypter import (
    create_cipher,
    generate_key,
    derive_key_from_password,
    ConfigEncrypter
)

# Configuración de logging
logger = logging.getLogger('corebrain')

def setup_logger(level=logging.INFO, 
                file_path=None, 
                format_string=None):
    """
    Configura el logger principal de Corebrain.
    
    Args:
        level: Nivel de logging
        file_path: Ruta a archivo de log (opcional)
        format_string: Formato de log personalizado
    """
    # Formato predeterminado
    fmt = format_string or '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)
    
    # Handler de consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configurar logger principal
    logger.setLevel(level)
    logger.addHandler(console_handler)
    
    # Handler de archivo si se proporciona ruta
    if file_path:
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Mensajes de diagnóstico
    logger.debug(f"Logger configurado con nivel {logging.getLevelName(level)}")
    if file_path:
        logger.debug(f"Logs escritos a {file_path}")
    
    return logger

# Exportación explícita de componentes públicos
__all__ = [
    'serialize_to_json',
    'JSONEncoder',
    'create_cipher',
    'generate_key',
    'derive_key_from_password',
    'ConfigEncrypter',
    'setup_logger',
    'logger'
]