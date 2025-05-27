"""
Abstract interfaces for database connections.
"""
from typing import Dict, Any, List, Optional, Protocol
from abc import ABC, abstractmethod

from corebrain.core.common import ConfigDict, SchemaDict

class DatabaseConnector(ABC):
    """Abstract interface for database connectors."""
    
    @abstractmethod
    def connect(self, config: ConfigDict) -> Any:
        """Establishes a connection with the database."""
        pass
    
    @abstractmethod
    def extract_schema(self, connection: Any) -> SchemaDict:
        """Extracts the database schema."""
        pass
    
    @abstractmethod
    def execute_query(self, connection: Any, query: str) -> List[Dict[str, Any]]:
        """Executes a query and returns results."""
        pass
    
    @abstractmethod
    def close(self, connection: Any) -> None:
        """Closes the connection."""
        pass
