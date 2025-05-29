"""
Information about supported database engines.
"""
from typing import Dict, List

def get_available_engines() -> Dict[str, List[str]]:
    """
    Returns the available database engines by type.
    
    Returns:
        Dict with DB types and a list of engines per type
    """
    return {
        "sql": ["sqlite", "mysql", "postgresql"],
        "nosql": ["mongodb"]
    }