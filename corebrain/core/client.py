"""
Corebrain SDK Main Client.

This module provides the main interface to interact with the Corebrain API
and enables natural language queries to relational and non-relational databases.
"""
import uuid
import re
import logging
import requests
import httpx
import sqlite3
import mysql.connector
import psycopg2
import pymongo
import json
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, inspect
from pathlib import Path
from datetime import datetime

from corebrain.core.common import logger, CorebrainError

class Corebrain:
    """
    Main client for the Corebrain SDK for natural language database queries.
    
    This class provides a unified interface to interact with different types of databases
    (SQL and NoSQL) using natural language. It manages the connection, schema extraction,
    and query processing through the Corebrain API.
    
    Attributes:
        api_key (str): Authentication key for the Corebrain API.
        db_config (Dict[str, Any]): Database connection configuration.
        config_id (str): Unique identifier for the current configuration.
        api_url (str): Base URL for the Corebrain API.
        user_info (Dict[str, Any]): Information about the authenticated user.
        db_connection: Active database connection.
        db_schema (Dict[str, Any]): Extracted database schema.
        
    Examples:
        SQLite initialization:
        ```python
        from corebrain import init
        
        # Connect to a SQLite database
        client = init(
            api_key="your_api_key",
            db_config={
                "type": "sql",
                "engine": "sqlite",
                "database": "my_database.db"
            }
        )
        
        # Make a query
        result = client.ask("How many registered users are there?")
        print(result["explanation"])
        ```
        
        PostgreSQL initialization:
        ```python
        # Connect to PostgreSQL
        client = init(
            api_key="your_api_key",
            db_config={
                "type": "sql",
                "engine": "postgresql",
                "host": "localhost",
                "port": 5432,
                "user": "postgres",
                "password": "your_password",
                "database": "my_database"
            }
        )
        ```
        
        MongoDB initialization:
        ```python
        # Connect to MongoDB
        client = init(
            api_key="your_api_key",
            db_config={
                "type": "mongodb",
                "host": "localhost",
                "port": 27017,
                "database": "my_database"
            }
        )
        ```
    """
    
    def __init__(
        self, 
        api_key: str, 
        db_config: Optional[Dict[str, Any]] = None,
        config_id: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None,
        api_url: str = "http://localhost:5000",
        skip_verification: bool = False
    ):
        """
        Initialize the Corebrain SDK client.
        
        Args:
            api_key (str): Required API key for authentication with the Corebrain service.
                Can be generated from the dashboard at https://dashboard.corebrain.com.
                
            db_config (Dict[str, Any], optional): Database configuration to query.
                This parameter is required if config_id is not provided. Must contain at least:
                - "type": Database type ("sql" or "mongodb")
                - For SQL: "engine" ("sqlite", "postgresql", "mysql")
                - Specific connection parameters depending on type and engine
                
                Example for SQLite:
                ```
                {
                    "type": "sql",
                    "engine": "sqlite",
                    "database": "path/to/database.db"
                }
                ```
                
                Example for PostgreSQL:
                ```
                {
                    "type": "sql",
                    "engine": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "user": "postgres",
                    "password": "password",
                    "database": "db_name"
                }
                ```
            
            config_id (str, optional): Identifier for a previously saved configuration.
                If provided, this configuration will be used instead of db_config.
                Useful for maintaining persistent configurations between sessions.
                
            user_data (Dict[str, Any], optional): Additional user information for verification.
                Can contain data like "email" for more precise token validation.
                
            api_url (str, optional): Base URL for the Corebrain API.
                Defaults to "http://localhost:5000" for local development.
                In production, it is typically "https://api.corebrain.com".
                
            skip_verification (bool, optional): If True, skips token verification with the server.
                Useful in offline environments or for local testing.
                Defaults to False.
        
        Raises:
            ValueError: If required parameters are missing or if the configuration is invalid.
            CorebrainError: If there are issues with the API connection or database.
        
        Example:
            ```python
            from corebrain import Corebrain
            
            # Basic initialization with SQLite
            client = Corebrain(
                api_key="your_api_key",
                db_config={
                    "type": "sql",
                    "engine": "sqlite",
                    "database": "my_db.db"
                }
            )
            ```
        """
        self.api_key = api_key
        self.user_data = user_data
        self.api_url = api_url.rstrip('/')
        self.db_connection = None
        self.db_schema = None
        
        # Import ConfigManager dynamically to avoid circular dependency
        try:
            from corebrain.config.manager import ConfigManager
            self.config_manager = ConfigManager()
        except ImportError as e:
            logger.error(f"Error importing ConfigManager: {e}")
            raise CorebrainError(f"Could not load configuration manager: {e}")
        
        # Determine which configuration to use
        if config_id:
            saved_config = self.config_manager.get_config(api_key, config_id)
            if not saved_config:
                # Try to load from old format
                old_config = self._load_old_config(api_key, config_id)
                if old_config:
                    self.db_config = old_config
                    self.config_id = config_id
                    # Save in new format
                    self.config_manager.add_config(api_key, old_config, config_id)
                else:
                    raise ValueError(f"Configuration with ID {config_id} not found for the provided key")
            else:
                self.db_config = saved_config
                self.config_id = config_id
        elif db_config:
            self.db_config = db_config
            
            # Generate config ID if it doesn't exist
            if "config_id" in db_config:
                self.config_id = db_config["config_id"]
            else:
                self.config_id = str(uuid.uuid4())
                db_config["config_id"] = self.config_id
                
            # Save the configuration
            self.config_manager.add_config(api_key, db_config, self.config_id)
        else:
            raise ValueError("db_config or config_id must be provided")
        
        # Validate configuration
        self._validate_config()
        
        # Verify the API token (only if necessary)
        if not skip_verification:
            self._verify_api_token()
        else:
            # Initialize user_info with basic information if not verifying
            self.user_info = {"token": api_key}
        
        # Connect to the database
        self._connect_to_database()
        
        # Extract database schema
        self.db_schema = self._extract_db_schema()

        self.metadata = {
            "config_id": self.config_id,
            "api_key": api_key,
            "db_config": self.db_config
        }

    def _load_old_config(self, api_key: str, config_id: str) -> Optional[Dict[str, Any]]:
        """
        Try to load configuration from old format.
        
        Args:
            api_key: API key
            config_id: Configuration ID
            
        Returns:
            Configuration dictionary if found, None otherwise
        """
        try:
            # Try to load from old config file
            old_config_path = Path.home() / ".corebrain" / "config.json"
            if old_config_path.exists():
                with open(old_config_path, 'r') as f:
                    old_configs = json.load(f)
                    if api_key in old_configs and config_id in old_configs[api_key]:
                        return old_configs[api_key][config_id]
        except Exception as e:
            logger.warning(f"Error loading old config: {e}")
        return None

    def _validate_config(self) -> None:
        """
        Validate the provided configuration.
        
        This internal function verifies that the database configuration
        contains all necessary fields according to the specified database type.
        
        Raises:
            ValueError: If the database configuration is invalid or incomplete.
        """
        if not self.api_key:
            raise ValueError("API key is required. Generate one at dashboard.corebrain.com")
        
        if not self.db_config:
            raise ValueError("Database configuration is required")
        
        if "type" not in self.db_config:
            raise ValueError("Database type is required in db_config")
        
        if "connection_string" not in self.db_config and self.db_config["type"] != "sqlite_memory":
            if self.db_config["type"] == "sql":
                if "engine" not in self.db_config:
                    raise ValueError("Database engine is required for 'sql' type")
                
                # Verify alternative configuration for SQL engines
                if self.db_config["engine"] == "mysql" or self.db_config["engine"] == "postgresql":
                    if not ("host" in self.db_config and "user" in self.db_config and 
                            "password" in self.db_config and "database" in self.db_config):
                        raise ValueError("host, user, password, and database are required for MySQL/PostgreSQL")
                elif self.db_config["engine"] == "sqlite":
                    if "database" not in self.db_config:
                        raise ValueError("database field is required for SQLite")
            elif self.db_config["type"] == "mongodb":
                if "database" not in self.db_config:
                    raise ValueError("database field is required for MongoDB")
                
                if "connection_string" not in self.db_config:
                    if not ("host" in self.db_config and "port" in self.db_config):
                        raise ValueError("host and port are required for MongoDB without connection_string")

    def _verify_api_token(self) -> None:
        """
        Verify the API token with the server.
        
        This internal function sends a request to the Corebrain server
        to validate that the provided API token is valid.
        If the user provided additional information (like email),
        it will be used for more precise verification.
        
        The verification results are stored in self.user_info.
        
        Raises:
            ValueError: If the API token is invalid.
        """
        try:
            # Use the user's email for verification if available
            if self.user_data and 'email' in self.user_data:
                endpoint = f"{self.api_url}/api/auth/users/{self.user_data['email']}"
                
                response = httpx.get(
                    endpoint,
                    headers={"X-API-Key": self.api_key},
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    raise ValueError(f"Invalid API token. Error code: {response.status_code}")
                
                # Store user information
                self.user_info = response.json()
            else:
                # If no email, do a simple verification with a generic endpoint
                endpoint = f"{self.api_url}/api/auth/verify"
                
                try:
                    response = httpx.get(
                        endpoint,
                        headers={"X-API-Key": self.api_key},
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        self.user_info = response.json()
                    else:
                        # If it fails, just store basic information
                        self.user_info = {"token": self.api_key}
                except Exception as e:
                    # If there's a connection error, don't fail, just store basic info
                    logger.warning(f"Could not verify token: {str(e)}")
                    self.user_info = {"token": self.api_key}
                    
        except httpx.RequestError as e:
            # Connection error shouldn't be fatal if we already have a configuration
            logger.warning(f"Error connecting to API: {str(e)}")
            self.user_info = {"token": self.api_key}
        except Exception as e:
            # Other errors are logged but not fatal
            logger.warning(f"Error in token verification: {str(e)}")
            self.user_info = {"token": self.api_key}

    def _connect_to_database(self) -> None:
        """
        Establish a connection to the database according to the configuration.
        
        This internal function creates a database connection using the parameters
        defined in self.db_config. It supports various database types:
        - SQLite (file or in-memory)
        - PostgreSQL
        - MySQL
        - MongoDB
        
        The connection is stored in self.db_connection for later use.
        
        Raises:
            CorebrainError: If the connection to the database cannot be established.
            NotImplementedError: If the database type is not supported.
        """
        db_type = self.db_config["type"].lower()
        
        try:
            if db_type == "sql":
                engine = self.db_config.get("engine", "").lower()
                
                if engine == "sqlite":
                    database = self.db_config.get("database", "")
                    if database:
                        self.db_connection = sqlite3.connect(database)
                    else:
                        self.db_connection = sqlite3.connect(self.db_config.get("connection_string", ""))
                
                elif engine == "mysql":
                    if "connection_string" in self.db_config:
                        self.db_connection = mysql.connector.connect(
                            connection_string=self.db_config["connection_string"]
                        )
                    else:
                        self.db_connection = mysql.connector.connect(
                            host=self.db_config.get("host", "localhost"),
                            user=self.db_config.get("user", ""),
                            password=self.db_config.get("password", ""),
                            database=self.db_config.get("database", ""),
                            port=self.db_config.get("port", 3306)
                        )
                
                elif engine == "postgresql":
                    if "connection_string" in self.db_config:
                        self.db_connection = psycopg2.connect(self.db_config["connection_string"])
                    else:
                        self.db_connection = psycopg2.connect(
                            host=self.db_config.get("host", "localhost"),
                            user=self.db_config.get("user", ""),
                            password=self.db_config.get("password", ""),
                            dbname=self.db_config.get("database", ""),
                            port=self.db_config.get("port", 5432)
                        )
                
                else:
                    # Use SQLAlchemy for other engines
                    self.db_connection = create_engine(self.db_config["connection_string"])
            
            # Improved code for MongoDB
            elif db_type == "nosql" or db_type == "mongodb":
                # If engine is mongodb or the type is directly mongodb
                engine = self.db_config.get("engine", "").lower()
                if not engine or engine == "mongodb":
                    # Create connection parameters
                    mongo_params = {}
                    
                    if "connection_string" in self.db_config:
                        # Save the MongoDB client to be able to close it correctly later
                        self.mongo_client = pymongo.MongoClient(self.db_config["connection_string"])
                    else:
                        # Configure host and port
                        mongo_params["host"] = self.db_config.get("host", "localhost")
                        if "port" in self.db_config:
                            mongo_params["port"] = self.db_config.get("port")
                        
                        # Add credentials if available
                        if "user" in self.db_config and self.db_config["user"]:
                            mongo_params["username"] = self.db_config["user"]
                        if "password" in self.db_config and self.db_config["password"]:
                            mongo_params["password"] = self.db_config["password"]
                        
                        # Create MongoDB client
                        self.mongo_client = pymongo.MongoClient(**mongo_params)
                    
                    # Get the database
                    db_name = self.db_config.get("database", "")
                    if db_name:
                        # Save reference to the database
                        self.db_connection = self.mongo_client[db_name]
                    else:
                        # If there's no database name, use 'admin' as fallback
                        logger.warning("Database name not specified for MongoDB, using 'admin'")
                        self.db_connection = self.mongo_client["admin"]
                else:
                    raise ValueError(f"Unsupported NoSQL database engine: {engine}")
            
            elif db_type == "sqlite_memory":
                self.db_connection = sqlite3.connect(":memory:")
            
            else:
                raise ValueError(f"Unsupported database type: {db_type}. Valid types: 'sql', 'nosql', 'mongodb'")
                
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            raise ConnectionError(f"Error connecting to database: {str(e)}")
    
    def _extract_db_schema(self, detail_level: str = "full", specific_collections: List[str] = None) -> Dict[str, Any]:
        """
        Extracts the database schema to provide context to the AI.
        
        Returns:
            Dictionary with the database structure organized by tables/collections
        """
        logger.info(f"Extrayendo esquema de base de datos. Tipo: {self.db_config['type']}, Motor: {self.db_config.get('engine')}")
        
        db_type = self.db_config["type"].lower()
        schema = {
            "type": db_type,
            "database": self.db_config.get("database", ""),
            "tables": {},
            "total_collections": 0,  # Añadir contador total
            "included_collections": 0  # Contador de incluidas
        }
        excluded_tables = set(self.db_config.get("excluded_tables", []))
        logger.info(f"Tablas excluidas: {excluded_tables}")
        
        try:
            if db_type == "sql":
                engine = self.db_config.get("engine", "").lower()
                logger.info(f"Procesando base de datos SQL con motor: {engine}")
                
                if engine in ["sqlite", "mysql", "postgresql"]:
                    cursor = self.db_connection.cursor()
                    
                    if engine == "sqlite":
                        logger.info("Obteniendo tablas de SQLite")
                        # Obtener listado de tablas
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                        tables = cursor.fetchall()
                        logger.info(f"Tablas encontradas en SQLite: {tables}")
                        
                    elif engine == "mysql":
                        logger.info("Obteniendo tablas de MySQL")
                        cursor.execute("SHOW TABLES;")
                        tables = cursor.fetchall()
                        logger.info(f"Tablas encontradas en MySQL: {tables}")
                        
                    elif engine == "postgresql":
                        logger.info("Obteniendo tablas de PostgreSQL")
                        cursor.execute("""
                            SELECT table_name FROM information_schema.tables 
                            WHERE table_schema = 'public';
                        """)
                        tables = cursor.fetchall()
                        logger.info(f"Tablas encontradas en PostgreSQL: {tables}")
                    
                    # Procesar las tablas encontradas
                    for table in tables:
                        table_name = table[0]
                        logger.info(f"Procesando tabla: {table_name}")
                        
                        # Saltar tablas excluidas
                        if table_name in excluded_tables:
                            logger.info(f"Saltando tabla excluida: {table_name}")
                            continue
                        
                        try:
                            # Obtener información de columnas según el motor
                            if engine == "sqlite":
                                cursor.execute(f"PRAGMA table_info({table_name});")
                            elif engine == "mysql":
                                cursor.execute(f"DESCRIBE {table_name};")
                            elif engine == "postgresql":
                                cursor.execute(f"""
                                    SELECT column_name, data_type 
                                    FROM information_schema.columns 
                                    WHERE table_name = '{table_name}';
                                """)
                            
                            columns = cursor.fetchall()
                            logger.info(f"Columnas encontradas para {table_name}: {columns}")
                            
                            # Estructura de columnas según el motor
                            if engine == "sqlite":
                                column_info = [{"name": col[1], "type": col[2]} for col in columns]
                            elif engine == "mysql":
                                column_info = [{"name": col[0], "type": col[1]} for col in columns]
                            elif engine == "postgresql":
                                column_info = [{"name": col[0], "type": col[1]} for col in columns]
                            
                            # Guardar información de la tabla
                            schema["tables"][table_name] = {
                                "columns": column_info,
                                "sample_data": []  # No obtenemos datos de muestra por defecto
                            }
                            
                        except Exception as e:
                            logger.error(f"Error procesando tabla {table_name}: {str(e)}")
                    
                else:
                    # Usando SQLAlchemy
                    logger.info("Usando SQLAlchemy para obtener el esquema")
                    inspector = inspect(self.db_connection)
                    table_names = inspector.get_table_names()
                    logger.info(f"Tablas encontradas con SQLAlchemy: {table_names}")
                    
                    for table_name in table_names:
                        if table_name in excluded_tables:
                            logger.info(f"Saltando tabla excluida: {table_name}")
                            continue
                            
                        try:
                            columns = inspector.get_columns(table_name)
                            column_info = [{"name": col["name"], "type": str(col["type"])} for col in columns]
                            
                            schema["tables"][table_name] = {
                                "columns": column_info,
                                "sample_data": []
                            }
                        except Exception as e:
                            logger.error(f"Error procesando tabla {table_name} con SQLAlchemy: {str(e)}")
            
            elif db_type in ["nosql", "mongodb"]:
                logger.info("Procesando base de datos MongoDB")
                if not hasattr(self, 'db_connection') or self.db_connection is None:
                    logger.error("La conexión a MongoDB no está disponible")
                    return schema
                
                try:
                    collection_names = []
                    try:
                        collection_names = self.db_connection.list_collection_names()
                        schema["total_collections"] = len(collection_names)
                        logger.info(f"Colecciones encontradas en MongoDB: {collection_names}")
                    except Exception as e:
                        logger.error(f"Error al obtener colecciones MongoDB: {str(e)}")
                        return schema
                    
                    # Si solo queremos los nombres
                    if detail_level == "names_only":
                        schema["collection_names"] = collection_names
                        return schema
                    
                    # Procesar cada colección
                    for collection_name in collection_names:
                        if collection_name in excluded_tables:
                            logger.info(f"Saltando colección excluida: {collection_name}")
                            continue
                            
                        try:
                            collection = self.db_connection[collection_name]
                            # Obtener un documento para inferir estructura
                            first_doc = collection.find_one()
                            
                            if first_doc:
                                fields = []
                                for field, value in first_doc.items():
                                    if field != "_id":
                                        field_type = type(value).__name__
                                        fields.append({"name": field, "type": field_type})
                                
                                schema["tables"][collection_name] = {
                                    "fields": fields,
                                    "doc_count": collection.estimated_document_count()
                                }
                                logger.info(f"Procesada colección {collection_name} con {len(fields)} campos")
                            else:
                                logger.info(f"Colección {collection_name} está vacía")
                                schema["tables"][collection_name] = {
                                    "fields": [],
                                    "doc_count": 0
                                }
                        except Exception as e:
                            logger.error(f"Error procesando colección {collection_name}: {str(e)}")
                
                except Exception as e:
                    logger.error(f"Error general procesando MongoDB: {str(e)}")
            
            # Convertir el diccionario de tablas en una lista
            table_list = []
            for table_name, table_info in schema["tables"].items():
                table_data = {"name": table_name}
                table_data.update(table_info)
                table_list.append(table_data)
            
            schema["tables_list"] = table_list
            logger.info(f"Esquema final - Tablas encontradas: {len(schema['tables'])}")
            logger.info(f"Nombres de tablas: {list(schema['tables'].keys())}")
            
            return schema
            
        except Exception as e:
            logger.error(f"Error al extraer el esquema de la base de datos: {str(e)}")
            return {"type": db_type, "tables": {}, "tables_list": []}

    def list_collections_name(self) -> List[str]:
        """
        Returns a list of the available collections or tables in the database.
        
        Returns:
            List of collections or tables
        """
        print("Excluded tables: ", self.db_schema.get("excluded_tables", []))
        return self.db_schema.get("tables", [])
    
    def ask(self, question: str, **kwargs) -> Dict:
        """
        Perform a natural language query to the database.
        
        Args:
            question: The natural language question
            **kwargs: Additional parameters:
                - collection_name: For MongoDB, the collection to query
                - limit: Maximum number of results
                - detail_level: Schema detail level ("names_only", "structure", "full")
                - auto_select: Whether to automatically select collections
                - max_collections: Maximum number of collections to include
                - execute_query: Whether to execute the query (True by default)
                - explain_results: Whether to generate an explanation of results (True by default)
                
        Returns:
            Dictionary with the query results and explanation
        """
        try:
            # Verificar opciones de comportamiento
            execute_query = kwargs.get("execute_query", True)
            explain_results = kwargs.get("explain_results", True)
            
            # Obtener esquema con el nivel de detalle apropiado
            detail_level = kwargs.get("detail_level", "full")
            schema = self._extract_db_schema(detail_level=detail_level)
            
            # Validar que el esquema tiene tablas/colecciones
            if not schema.get("tables"):
                print("Error: No se encontraron tablas/colecciones en la base de datos")
                return {"error": True, "explanation": "No se encontraron tablas/colecciones en la base de datos"}
            
            # Obtener nombres de tablas disponibles para validación
            available_tables = set()
            if isinstance(schema.get("tables"), dict):
                available_tables.update(schema["tables"].keys())
            elif isinstance(schema.get("tables_list"), list):
                available_tables.update(table["name"] for table in schema["tables_list"])
            
            # Preparar datos de la solicitud con información de esquema mejorada
            request_data = {
                "question": question,
                "db_schema": schema,
                "config_id": self.config_id,
                "metadata": {
                    "type": self.db_config["type"].lower(),
                    "engine": self.db_config.get("engine", "").lower(),
                    "database": self.db_config.get("database", ""),
                    "available_tables": list(available_tables),
                    "collections": list(available_tables)
                }
            }
            
            # Añadir configuración de la base de datos al request
            # Esto permite a la API ejecutar directamente las consultas si es necesario
            if execute_query:
                request_data["db_config"] = self.db_config
            
            # Añadir datos de usuario si están disponibles
            if self.user_data:
                request_data["user_data"] = self.user_data
            
            # Preparar headers para la solicitud
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Determinar el endpoint adecuado según el modo de ejecución
            if execute_query:
                # Usar el endpoint de ejecución completa
                endpoint = f"{self.api_url}/api/database/sdk/query"
            else:
                # Usar el endpoint de solo generación de consulta
                endpoint = f"{self.api_url}/api/database/generate"
            
            # Realizar solicitud a la API
            response = httpx.post(
                endpoint,
                headers=headers,
                content=json.dumps(request_data, default=str),
                timeout=60.0
            )
            
            # Verificar respuesta
            if response.status_code != 200:
                error_msg = f"Error {response.status_code} al realizar la consulta"
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict):
                        error_msg += f": {error_data.get('detail', error_data.get('message', response.text))}"
                except:
                    error_msg += f": {response.text}"
                return {"error": True, "explanation": error_msg}
            
            # Procesar respuesta de la API
            api_response = response.json()
            
            # Verificar si la API reportó un error
            if api_response.get("error", False):
                return api_response
            
            # Verificar si se generó una consulta válida
            if "query" not in api_response:
                return {
                    "error": True,
                    "explanation": "La API no generó una consulta válida."
                }
            
            # Si se debe ejecutar la consulta pero la API no lo hizo
            # (esto ocurriría solo en caso de cambios de configuración o fallbacks)
            if execute_query and "result" not in api_response:
                try:
                    # Preparar la consulta para ejecución local
                    query_type = self.db_config.get("engine", "").lower() if self.db_config["type"].lower() == "sql" else self.db_config["type"].lower()
                    query_value = api_response["query"]
                    
                    # Para SQL, asegurarse de que la consulta es un string
                    if query_type in ["sqlite", "mysql", "postgresql"]:
                        if isinstance(query_value, dict):
                            sql_candidate = query_value.get("sql") or query_value.get("query")
                            if isinstance(sql_candidate, str):
                                query_value = sql_candidate
                            else:
                                raise CorebrainError(f"La consulta SQL generada no es un string: {query_value}")
                    
                    # Preparar la consulta con el formato adecuado
                    query_to_execute = {
                        "type": query_type,
                        "query": query_value
                    }
                    
                    # Para MongoDB, añadir información específica
                    if query_type in ["nosql", "mongodb"]:
                        # Obtener nombre de colección
                        collection_name = None
                        if isinstance(api_response["query"], dict):
                            collection_name = api_response["query"].get("collection")
                        if not collection_name and "collection_name" in kwargs:
                            collection_name = kwargs["collection_name"]
                        if not collection_name and "collection" in self.db_config:
                            collection_name = self.db_config["collection"]
                        if not collection_name and available_tables:
                            collection_name = list(available_tables)[0]
                        
                        # Validar nombre de colección
                        if not collection_name:
                            raise CorebrainError("No se especificó colección y no se encontraron colecciones en el esquema")
                        if not isinstance(collection_name, str) or not collection_name.strip():
                            raise CorebrainError("Nombre de colección inválido: debe ser un string no vacío")
                        
                        # Añadir colección a la consulta
                        query_to_execute["collection"] = collection_name
                        
                        # Añadir tipo de operación
                        if isinstance(api_response["query"], dict):
                            query_to_execute["operation"] = api_response["query"].get("operation", "find")
                        
                        # Añadir límite si se especifica
                        if "limit" in kwargs:
                            query_to_execute["limit"] = kwargs["limit"]
                    
                    # Ejecutar la consulta
                    start_time = datetime.now()
                    query_result = self._execute_query(query_to_execute)
                    query_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                    
                    # Actualizar la respuesta con los resultados
                    api_response["result"] = {
                        "data": query_result,
                        "count": len(query_result) if isinstance(query_result, list) else 1,
                        "query_time_ms": query_time_ms,
                        "has_more": False
                    }
                    
                    # Si se debe generar explicación pero la API no lo hizo
                    if explain_results and (
                        "explanation" not in api_response or 
                        not isinstance(api_response.get("explanation"), str) or 
                        len(str(api_response.get("explanation", ""))) < 15  # Detectar explicaciones numéricas o muy cortas
                    ):
                        # Preparar datos para obtener explicación
                        explanation_data = {
                            "question": question,
                            "query": api_response["query"],
                            "result": query_result,
                            "query_time_ms": query_time_ms,
                            "config_id": self.config_id,
                            "metadata": {
                                "collections_used": [query_to_execute.get("collection")] if query_to_execute.get("collection") else [],
                                "execution_time_ms": query_time_ms,
                                "available_tables": list(available_tables)
                            }
                        }
                        
                        try:
                            # Obtener explicación de la API
                            explanation_response = httpx.post(
                                f"{self.api_url}/api/database/sdk/query/explain",
                                headers=headers,
                                content=json.dumps(explanation_data, default=str),
                                timeout=30.0
                            )
                            
                            if explanation_response.status_code == 200:
                                explanation_result = explanation_response.json()
                                api_response["explanation"] = explanation_result.get("explanation", "No se pudo generar una explicación.")
                            else:
                                api_response["explanation"] = self._generate_fallback_explanation(query_to_execute, query_result)
                        except Exception as explain_error:
                            logger.error(f"Error al obtener explicación: {str(explain_error)}")
                            api_response["explanation"] = self._generate_fallback_explanation(query_to_execute, query_result)
                
                except Exception as e:
                    error_msg = f"Error al ejecutar la consulta: {str(e)}"
                    logger.error(error_msg)
                    return {
                        "error": True,
                        "explanation": error_msg,
                        "query": api_response.get("query", {}),
                        "metadata": {
                            "available_tables": list(available_tables)
                        }
                    }
            
            # Verificar si la explicación es un número (probablemente el tiempo de ejecución) y corregirlo
            if "explanation" in api_response and not isinstance(api_response["explanation"], str):
                # Si la explicación es un número, reemplazarla con una explicación generada
                try:
                    is_sql = False
                    if "query" in api_response:
                        if isinstance(api_response["query"], dict) and "sql" in api_response["query"]:
                            is_sql = True
                    
                    if "result" in api_response:
                        result_data = api_response["result"]
                        if isinstance(result_data, dict) and "data" in result_data:
                            result_data = result_data["data"]
                        
                        if is_sql:
                            sql_query = api_response["query"].get("sql", "")
                            api_response["explanation"] = self._generate_sql_explanation(sql_query, result_data)
                        else:
                            # Para MongoDB o genérico
                            api_response["explanation"] = self._generate_generic_explanation(api_response["query"], result_data)
                    else:
                        api_response["explanation"] = "La consulta se ha ejecutado correctamente."
                except Exception as exp_fix_error:
                    logger.error(f"Error al corregir explicación: {str(exp_fix_error)}")
                    api_response["explanation"] = "La consulta se ha ejecutado correctamente."
            
            # Preparar la respuesta final
            result = {
                "question": question,
                "query": api_response["query"],
                "config_id": self.config_id,
                "metadata": {
                    "available_tables": list(available_tables)
                }
            }
            
            # Añadir resultados si están disponibles
            if "result" in api_response:
                if isinstance(api_response["result"], dict) and "data" in api_response["result"]:
                    result["result"] = api_response["result"]
                else:
                    result["result"] = {
                        "data": api_response["result"],
                        "count": len(api_response["result"]) if isinstance(api_response["result"], list) else 1,
                        "query_time_ms": api_response.get("query_time_ms", 0),
                        "has_more": False
                    }
            
            # Añadir explicación si está disponible
            if "explanation" in api_response:
                result["explanation"] = api_response["explanation"]
            
            return result
            
        except httpx.TimeoutException:
            return {"error": True, "explanation": "Tiempo de espera agotado al conectar con el servidor."}
            
        except httpx.RequestError as e:
            return {"error": True, "explanation": f"Error de conexión con el servidor: {str(e)}"}
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error inesperado en ask(): {error_details}")
            return {"error": True, "explanation": f"Error inesperado: {str(e)}"}
    
    def _generate_fallback_explanation(self, query, results):
        """
        Generates a fallback explanation when the explanation generation fails.
        
        Args:
            query: The executed query
            results: The obtained results
            
        Returns:
            Generated explanation
        """
        # Determinar si es SQL o MongoDB
        if isinstance(query, dict):
            query_type = query.get("type", "").lower()
            
            if query_type in ["sqlite", "mysql", "postgresql"]:
                return self._generate_sql_explanation(query.get("query", ""), results)
            elif query_type in ["nosql", "mongodb"]:
                return self._generate_mongodb_explanation(query, results)
        
        # Fallback genérico
        result_count = len(results) if isinstance(results, list) else (1 if results else 0)
        return f"La consulta devolvió {result_count} resultados."

    def _generate_sql_explanation(self, sql_query, results):
        """
        Generates a simple explanation for SQL queries.
        
        Args:
            sql_query: The executed SQL query
            results: The obtained results
            
        Returns:
            Generated explanation
        """
        sql_lower = sql_query.lower() if isinstance(sql_query, str) else ""
        result_count = len(results) if isinstance(results, list) else (1 if results else 0)
        
        # Extraer nombres de tablas si es posible
        tables = []
        from_match = re.search(r'from\s+([a-zA-Z0-9_]+)', sql_lower)
        if from_match:
            tables.append(from_match.group(1))
        
        join_matches = re.findall(r'join\s+([a-zA-Z0-9_]+)', sql_lower)
        if join_matches:
            tables.extend(join_matches)
        
        # Detectar tipo de consulta
        if "select" in sql_lower:
            if "join" in sql_lower:
                if len(tables) > 1:
                    if "where" in sql_lower:
                        return f"Se encontraron {result_count} registros que cumplen con los criterios especificados, relacionando información de las tablas {', '.join(tables)}."
                    else:
                        return f"Se obtuvieron {result_count} registros relacionando información de las tablas {', '.join(tables)}."
                else:
                    return f"Se obtuvieron {result_count} registros relacionando datos entre tablas."
                    
            elif "where" in sql_lower:
                return f"Se encontraron {result_count} registros que cumplen con los criterios de búsqueda."
                
            else:
                return f"La consulta devolvió {result_count} registros de la base de datos."
        
        # Para otros tipos de consultas (INSERT, UPDATE, DELETE)
        if "insert" in sql_lower:
            return "Se insertaron correctamente los datos en la base de datos."
        elif "update" in sql_lower:
            return "Se actualizaron correctamente los datos en la base de datos."
        elif "delete" in sql_lower:
            return "Se eliminaron correctamente los datos de la base de datos."
        
        # Fallback genérico
        return f"La consulta SQL se ejecutó correctamente y devolvió {result_count} resultados."


    def _generate_mongodb_explanation(self, query, results):
        """
        Generates a simple explanation for MongoDB queries.
        
        Args:
            query: The executed MongoDB query
            results: The obtained results
            
        Returns:
            Generated explanation
        """
        collection = query.get("collection", "la colección")
        operation = query.get("operation", "find")
        result_count = len(results) if isinstance(results, list) else (1 if results else 0)
        
        # Generar explicación según la operación
        if operation == "find":
            return f"Se encontraron {result_count} documentos en la colección {collection} que coinciden con los criterios de búsqueda."
        elif operation == "findOne":
            if result_count > 0:
                return f"Se encontró el documento solicitado en la colección {collection}."
            else:
                return f"No se encontró ningún documento en la colección {collection} que coincida con los criterios."
        elif operation == "aggregate":
            return f"La agregación en la colección {collection} devolvió {result_count} resultados."
        elif operation == "insertOne":
            return f"Se ha insertado correctamente un nuevo documento en la colección {collection}."
        elif operation == "updateOne":
            return f"Se ha actualizado correctamente un documento en la colección {collection}."
        elif operation == "deleteOne":
            return f"Se ha eliminado correctamente un documento de la colección {collection}."
        
        # Fallback genérico
        return f"La operación {operation} se ejecutó correctamente en la colección {collection} y devolvió {result_count} resultados."


    def _generate_generic_explanation(self, query, results):
        """
        Generates a generic explanation when the query type cannot be determined.
        
        Args:
            query: The executed query
            results: The obtained results
            
        Returns:
            Generated explanation
        """
        result_count = len(results) if isinstance(results, list) else (1 if results else 0)
        
        if result_count == 0:
            return "La consulta no devolvió ningún resultado."
        elif result_count == 1:
            return "La consulta devolvió 1 resultado."
        else:
            return f"La consulta devolvió {result_count} resultados."
    
    
    def close(self) -> None:
        """
        Close the database connection and release resources.
        
        This method should be called when the client is no longer needed to 
        ensure proper cleanup of resources.
        """
        if self.db_connection:
            db_type = self.db_config["type"].lower()
            
            try:
                if db_type == "sql":
                    engine = self.db_config.get("engine", "").lower()
                    if engine in ["sqlite", "mysql", "postgresql"]:
                        self.db_connection.close()
                    else:
                        # SQLAlchemy engine
                        self.db_connection.dispose()
                        
                elif db_type == "nosql" or db_type == "mongodb":
                    # For MongoDB, we close the client
                    if hasattr(self, 'mongo_client') and self.mongo_client:
                        self.mongo_client.close()
                        
                elif db_type == "sqlite_memory":
                    self.db_connection.close()
                    
            except Exception as e:
                logger.warning(f"Error closing database connection: {str(e)}")
            
            self.db_connection = None
            logger.info("Database connection closed")

    def _execute_query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a query based on its type.
        
        Args:
            query: Dictionary containing query information
            
        Returns:
            List of dictionaries containing query results
        """
        query_type = query.get("type", "").lower()
        
        if query_type in ["sqlite", "mysql", "postgresql"]:
            return self._execute_sql_query(query)
        elif query_type in ["nosql", "mongodb"]:
            return self._execute_mongodb_query(query)
        else:
            raise CorebrainError(f"Unsupported query type: {query_type}")
            
    def _execute_sql_query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a SQL query.
        
        Args:
            query: Dictionary containing SQL query information
            
        Returns:
            List of dictionaries containing query results
        """
        query_type = query.get("type", "").lower()
        
        if query_type in ["sqlite", "mysql", "postgresql"]:
            sql_query = query.get("query", "")
            if not sql_query:
                raise CorebrainError("No SQL query provided")
                
            engine = self.db_config.get("engine", "").lower()
            
            if engine == "sqlite":
                return self._execute_sqlite_query(sql_query)
            elif engine == "mysql":
                return self._execute_mysql_query(sql_query)
            elif engine == "postgresql":
                return self._execute_postgresql_query(sql_query)
            else:
                raise CorebrainError(f"Unsupported SQL engine: {engine}")
                
        else:
            raise CorebrainError(f"Unsupported SQL query type: {query_type}")
            
    def _execute_sqlite_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute a SQLite query.
        
        Args:
            sql_query (str): SQL query to execute
            
        Returns:
            List[Dict[str, Any]]: List of results as dictionaries
        """
        cursor = self.db_connection.cursor()
        cursor.execute(sql_query)
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        
        # Convert results to list of dictionaries
        results = []
        for row in cursor.fetchall():
            result = {}
            for i, value in enumerate(row):
                # Convert datetime objects to strings
                if hasattr(value, 'isoformat'):
                    result[columns[i]] = value.isoformat()
                else:
                    result[columns[i]] = value
            results.append(result)
            
        return results
        
    def _execute_mysql_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute a MySQL query.
        
        Args:
            sql_query (str): SQL query to execute
            
        Returns:
            List[Dict[str, Any]]: List of results as dictionaries
        """
        cursor = self.db_connection.cursor(dictionary=True)
        cursor.execute(sql_query)
        
        # Convert results to list of dictionaries
        results = []
        for row in cursor.fetchall():
            result = {}
            for key, value in row.items():
                # Convert datetime objects to strings
                if hasattr(value, 'isoformat'):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
            results.append(result)
            
        return results
        
    def _execute_postgresql_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute a PostgreSQL query.
        
        Args:
            sql_query (str): SQL query to execute
            
        Returns:
            List[Dict[str, Any]]: List of results as dictionaries
        """
        cursor = self.db_connection.cursor()
        cursor.execute(sql_query)
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        
        # Convert results to list of dictionaries
        results = []
        for row in cursor.fetchall():
            result = {}
            for i, value in enumerate(row):
                # Convert datetime objects to strings
                if hasattr(value, 'isoformat'):
                    result[columns[i]] = value.isoformat()
                else:
                    result[columns[i]] = value
            results.append(result)
            
        return results

    def _execute_mongodb_query(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a MongoDB query.
        
        Args:
            query: Dictionary containing MongoDB query information
            
        Returns:
            List of dictionaries containing query results
        """
        try:
            # Get collection name from query or use default
            collection_name = query.get("collection")
            if not collection_name:
                raise CorebrainError("No collection specified for MongoDB query")
                
            # Get MongoDB collection
            collection = self.mongo_client[self.db_config.get("database", "")][collection_name]
            
            # Execute query based on operation type
            operation = query.get("operation", "find")
            
            if operation == "find":
                # Handle find operation
                cursor = collection.find(
                    query.get("query", {}),
                    projection=query.get("projection"),
                    sort=query.get("sort"),
                    limit=query.get("limit", 10),
                    skip=query.get("skip", 0)
                )
                results = list(cursor)
                
            elif operation == "aggregate":
                # Handle aggregate operation
                pipeline = query.get("pipeline", [])
                cursor = collection.aggregate(pipeline)
                results = list(cursor)
                
            else:
                raise CorebrainError(f"Unsupported MongoDB operation: {operation}")
            
            # Convert results to dictionaries and handle datetime serialization
            serialized_results = []
            for doc in results:
                # Convert ObjectId to string
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                    
                # Handle datetime objects
                for key, value in doc.items():
                    if hasattr(value, 'isoformat'):
                        doc[key] = value.isoformat()
                        
                serialized_results.append(doc)
                
            return serialized_results
            
        except Exception as e:
            raise CorebrainError(f"Error executing MongoDB query: {str(e)}")


def init(
    api_key: str = None,
    db_config: Dict = None,
    config_id: str = None,
    user_data: Dict = None,
    api_url: str = None,
    skip_verification: bool = False
) -> Corebrain:
    """
    Initialize and return a Corebrain client instance.
    
    This function creates a new Corebrain SDK client with the provided configuration.
    It's a convenient factory function that wraps the Corebrain class initialization.
    
    Args:
        api_key (str, optional): Corebrain API key. If not provided, it will attempt
            to read from the COREBRAIN_API_KEY environment variable.
        db_config (Dict, optional): Database configuration dictionary. If not provided,
            it will attempt to read from the COREBRAIN_DB_CONFIG environment variable
            (expected in JSON format).
        config_id (str, optional): Configuration ID for saving/loading configurations.
        user_data (Dict, optional): Optional user data for personalization.
        api_url (str, optional): Corebrain API URL. Defaults to the production API.
        skip_verification (bool, optional): Skip API token verification. Default False.
    
    Returns:
        Corebrain: An initialized Corebrain client instance.
    
    Example:
        >>> client = init(api_key="your_api_key", db_config={"type": "sql", "engine": "sqlite", "database": "example.db"})
    """
    return Corebrain(
        api_key=api_key,
        db_config=db_config,
        config_id=config_id,
        user_data=user_data,
        api_url=api_url,
        skip_verification=skip_verification
    )

