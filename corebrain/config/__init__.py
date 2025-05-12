"""
Gestión de configuración para Corebrain SDK.

Este paquete proporciona funcionalidades para gestionar configuraciones
de conexión a bases de datos y preferencias del SDK.
"""
from .manager import ConfigManager

# Exportación explícita de componentes públicos
__all__ = ['ConfigManager']