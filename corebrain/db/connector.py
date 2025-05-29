"""
Base connectors for different types of databases.
"""
from typing import Dict, Any, List, Optional, Callable

class DatabaseConnector:
    """Base class for all database connectors."""
    
    def __init__(self, config: Dict[str, Any], timeout: int = 10):
        self.config = config
        self.timeout = timeout
        self.connection = None
    
    def connect(self):
        """Establishes a connection to the database."""
        raise NotImplementedError
    
    def extract_schema(self, sample_limit: int = 5, table_limit: Optional[int] = None, 
                      progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Extracts the database schema."""
        raise NotImplementedError
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a query on the database."""
        raise NotImplementedError
    
    def close(self):
        """Closes the connection."""
        if self.connection:
            try:
                self.connection.close()
            except:
                pass