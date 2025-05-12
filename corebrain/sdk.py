"""
SDK de Corebrain para compatibilidad.
"""
from corebrain.config.manager import ConfigManager

# Re-exportar elementos principales
list_configurations = ConfigManager().list_configs
remove_configuration = ConfigManager().remove_config