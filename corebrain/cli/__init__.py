"""
Command-line interface for the Corebrain SDK.

This module provides a command-line interface to configure
and use the Corebrain SDK for natural language queries to databases.
"""
import sys
from typing import Optional, List

# Importar componentes principales para CLI
from corebrain.cli.commands import main_cli
from corebrain.cli.utils import print_colored, ProgressTracker, get_free_port
from corebrain.cli.config import (
    configure_sdk, 
    get_db_type, 
    get_db_engine, 
    get_connection_params,
    test_database_connection,
    select_excluded_tables
)
from corebrain.cli.auth import (
    authenticate_with_sso,
    fetch_api_keys,
    exchange_sso_token_for_api_token,
    verify_api_token
)


# Exportación explícita de componentes públicos
__all__ = [
    'main_cli',
    'run_cli',
    'print_colored',
    'ProgressTracker',
    'get_free_port',
    'configure_sdk',
    'authenticate_with_sso',
    'fetch_api_keys',
    'exchange_sso_token_for_api_token',
    'verify_api_token'
]

# Función de conveniencia para ejecutar CLI
def run_cli(argv: Optional[List[str]] = None) -> int:
    """
    Run the CLI with the provided arguments.
    
    Args:
        argv: List of arguments (use sys.argv if None)
        
    Returns:
        Exit code
    """
    if argv is None:
        argv = sys.argv[1:]
        
    return main_cli(argv)