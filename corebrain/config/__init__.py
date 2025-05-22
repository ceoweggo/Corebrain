"""
Configuration management for the Corebrain SDK.

This package provides functionality to manage database connection configurations
and SDK preferences.
"""
from .manager import ConfigManager

# Exportación explícita de componentes públicos
__all__ = ['ConfigManager']