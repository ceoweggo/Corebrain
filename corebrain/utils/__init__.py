"""
General utilities for Corebrain SDK.

This package provides utilities shared by different 
SDK components, such as serialization, encryption, and logging.
"""
import logging

from corebrain.utils.serializer import serialize_to_json, JSONEncoder
from corebrain.utils.encrypter import (
    create_cipher,
    generate_key,
    derive_key_from_password,
    ConfigEncrypter
)

logger = logging.getLogger('corebrain')

def setup_logger(level=logging.INFO, 
                file_path=None, 
                format_string=None):
    """
    Configures the main Corebrain logger.

    Args:
        level: Logging level
        file_path: Path to log file (optional)
        format_string: Custom log format
    """
    # Default format
    fmt = format_string or '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configure main logger
    logger.setLevel(level)
    logger.addHandler(console_handler)
    
    # File handler if path is provided
    if file_path:
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Diagnostic messages
    logger.debug(f"Logger configured with level {logging.getLevelName(level)}")
    if file_path:
        logger.debug(f"Logs written to {file_path}")
    
    return logger

# Explicit export of public components
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