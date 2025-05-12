"""
Core functionalities shared across the Corebrain SDK.

This module contains common elements used throughout the SDK, including:
- Logging system configuration
- Common type definitions and aliases
- Custom exceptions for better error handling
- Component registry system for dependency management

These elements provide a common foundation for implementing
the rest of the SDK modules, ensuring consistency and facilitating
maintenance.
"""
import logging
from typing import Dict, Any, Optional, List, Callable, TypeVar, Union

# Global logging configuration
logger = logging.getLogger("corebrain")
logger.addHandler(logging.NullHandler())

# Type aliases to improve readability and maintenance
ConfigDict = Dict[str, Any]
"""
Type representing a configuration as a key-value dictionary.

Example:
```python
config: ConfigDict = {
    "type": "sql",
    "engine": "postgresql",
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "password",
    "database": "mydatabase"
}
```
"""

SchemaDict = Dict[str, Any]
"""
Type representing a database schema as a dictionary.

Example:
```python
schema: SchemaDict = {
    "tables": [
        {
            "name": "users",
            "columns": [
                {"name": "id", "type": "INTEGER", "primary_key": True},
                {"name": "name", "type": "TEXT"},
                {"name": "email", "type": "TEXT"}
            ]
        }
    ]
}
```
"""

# Generic component for typing
T = TypeVar('T')

# SDK exceptions
class CorebrainError(Exception):
    """
    Base exception for all Corebrain SDK errors.
    
    All other specific exceptions inherit from this class,
    allowing you to catch any SDK error with a single
    except block.
    
    Example:
    ```python
    try:
        result = client.ask("How many users are there?")
    except CorebrainError as e:
        print(f"Corebrain error: {e}")
    ```
    """
    pass

class ConfigError(CorebrainError):
    """
    Error related to SDK configuration.
    
    Raised when there are issues with the provided configuration,
    such as invalid credentials, missing parameters, or incorrect formats.
    
    Example:
    ```python
    try:
        client = init(api_key="invalid_key", db_config={})
    except ConfigError as e:
        print(f"Configuration error: {e}")
    ```
    """
    pass

class DatabaseError(CorebrainError):
    """
    Error related to database connection or query.
    
    Raised when there are problems connecting to the database,
    executing queries, or extracting schema information.
    
    Example:
    ```python
    try:
        result = client.ask("select * from a_table_that_does_not_exist")
    except DatabaseError as e:
        print(f"Database error: {e}")
    ```
    """
    pass

class APIError(CorebrainError):
    """
    Error related to communication with the Corebrain API.
    
    Raised when there are issues in communicating with the service,
    such as network errors, authentication failures, or unexpected responses.
    
    Example:
    ```python
    try:
        result = client.ask("How many users are there?")
    except APIError as e:
        print(f"API error: {e}")
        if e.status_code == 401:
            print("Please verify your API key")
    ```
    """
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict[str, Any]] = None):
        """
        Initialize an APIError exception.
        
        Args:
            message: Descriptive error message
            status_code: Optional HTTP status code (e.g., 401, 404, 500)
            response: Server response content if available
        """
        self.status_code = status_code
        self.response = response
        super().__init__(message)

# Component registry (to avoid circular imports)
_registry: Dict[str, Any] = {}

def register_component(name: str, component: Any) -> None:
    """
    Register a component in the global registry.
    
    This mechanism resolves circular dependencies between modules
    by providing a way to access components without importing them directly.
    
    Args:
        name: Unique name to identify the component
        component: The component to register (can be any object)
    
    Example:
    ```python
    # In the module that defines the component
    from core.common import register_component
    
    class DatabaseConnector:
        def connect(self):
            pass
    
    # Register the component
    connector = DatabaseConnector()
    register_component("db_connector", connector)
    ```
    """
    _registry[name] = component

def get_component(name: str) -> Any:
    """
    Get a component from the global registry.
    
    Args:
        name: Name of the component to retrieve
    
    Returns:
        The registered component or None if it doesn't exist
    
    Example:
    ```python
    # In another module that needs to use the component
    from core.common import get_component
    
    # Get the component
    connector = get_component("db_connector")
    if connector:
        connector.connect()
    ```
    """
    return _registry.get(name)

def safely_get_component(name: str, default: Optional[T] = None) -> Union[Any, T]:
    """
    Safely get a component from the global registry.
    
    If the component doesn't exist, it returns the provided default
    value instead of None.
    
    Args:
        name: Name of the component to retrieve
        default: Default value to return if the component doesn't exist
    
    Returns:
        The registered component or the default value
    
    Example:
    ```python
    # In another module
    from core.common import safely_get_component
    
    # Get the component with a default value
    connector = safely_get_component("db_connector", MyDefaultConnector())
    connector.connect()  # Guaranteed not to be None
    ```
    """
    component = _registry.get(name)
    return component if component is not None else default