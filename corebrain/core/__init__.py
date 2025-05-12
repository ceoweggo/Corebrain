"""
Componentes principales del SDK de Corebrain.

Este paquete contiene los componentes centrales del SDK, 
incluyendo el cliente principal y el manejo de schemas.
"""
from corebrain.core.client import Corebrain, init
from corebrain.core.query import QueryCache, QueryAnalyzer, QueryTemplate
from corebrain.core.test_utils import test_natural_language_query, generate_test_question_from_schema

# Exportación explícita de componentes públicos
__all__ = [
    'Corebrain',
    'init',
    'QueryCache',
    'QueryAnalyzer',
    'QueryTemplate',
    'test_natural_language_query',
    'generate_test_question_from_schema'
]