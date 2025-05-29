"""
Configuration management for the Corebrain SDK.

This package provides functionality to manage database connection configurations
and SDK preferences.
"""
from .manager import ConfigManager

# Explicit export of public components
__all__ = ['ConfigManager']