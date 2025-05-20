"""
Información sobre motores de bases de datos soportados.
"""
from typing import Dict, List

def get_available_engines() -> Dict[str, List[str]]:
    """
    Devuelve los motores de base de datos disponibles por tipo
    
    Returns:
        Dict con tipos de DB y lista de motores por tipo
    """
    return {
        "sql": ["sqlite", "mysql", "postgresql"],
        "nosql": ["mongodb"]
    }