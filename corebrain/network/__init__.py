"""
Network components for Corebrain SDK.

This package provides utilities and clients for communication
with the Corebrain API and other web services.
"""
from corebrain.network.client import (
    APIClient,
    APIError,
    APITimeoutError,
    APIConnectionError,
    APIAuthError
)

# Exportación explícita de componentes públicos
__all__ = [
    'APIClient',
    'APIError',
    'APITimeoutError',
    'APIConnectionError',
    'APIAuthError'
]