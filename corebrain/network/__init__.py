"""
Componentes de red para Corebrain SDK.

Este paquete proporciona utilidades y clientes para comunicación 
con la API de Corebrain y otros servicios web.
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