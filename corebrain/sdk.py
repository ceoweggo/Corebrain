"""
Corebrain SDK for compatibility.
"""
from corebrain.config.manager import ConfigManager

# Re-export main elements
list_configurations = ConfigManager().list_configs
remove_configuration = ConfigManager().remove_config