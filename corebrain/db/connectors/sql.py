"""
Conector para bases de datos SQL.
"""
import sqlite3
import time
from typing import Dict, Any, List, Optional, Callable

try:
    import mysql.connector
except ImportError:
    pass

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    pass

from corebrain.db.connector import DatabaseConnector

class SQLConnector(DatabaseConnector):
    """Optimized connector for SQL databases."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the SQL connector with the provided configuration.
        
        Args:
            config: Dictionary with the connection configuration
        """
        super().__init__(config)
        self.conn = None
        self.cursor = None
        self.engine = config.get("engine", "").lower()
        self.config = config
        self.connection_timeout = 30  # seconds
    
    def connect(self) -> bool:
        """
        Establishes a connection with optimized timeout.
        
        Returns:
            True if the connection was successful, False otherwise
        """
        try:
            start_time = time.time()
            
            # Attempt to connect with a time limit
            while time.time() - start_time < self.connection_timeout:
                try:
                    if self.engine == "sqlite":
                        if "connection_string" in self.config:
                            self.conn = sqlite3.connect(self.config["connection_string"], timeout=10.0)
                        else:
                            self.conn = sqlite3.connect(self.config.get("database", ""), timeout=10.0)
                        
                        # Configure to return rows as dictionaries
                        self.conn.row_factory = sqlite3.Row
                        
                    elif self.engine == "mysql":
                        if "connection_string" in self.config:
                            self.conn = mysql.connector.connect(
                                connection_string=self.config["connection_string"],
                                connection_timeout=10
                            )
                        else:
                            self.conn = mysql.connector.connect(
                                host=self.config.get("host", "localhost"),
                                user=self.config.get("user", ""),
                                password=self.config.get("password", ""),
                                database=self.config.get("database", ""),
                                port=self.config.get("port", 3306),
                                connection_timeout=10
                            )
                    
                    elif self.engine == "postgresql":
                        # Determine whether to use connection string or parameters
                        if "connection_string" in self.config:
                            # Add timeout to the connection string if not present
                            conn_str = self.config["connection_string"]
                            if "connect_timeout" not in conn_str:
                                if "?" in conn_str:
                                    conn_str += "&connect_timeout=10"
                                else:
                                    conn_str += "?connect_timeout=10"
                            
                            self.conn = psycopg2.connect(conn_str)
                        else:
                            self.conn = psycopg2.connect(
                                host=self.config.get("host", "localhost"),
                                user=self.config.get("user", ""),
                                password=self.config.get("password", ""),
                                dbname=self.config.get("database", ""),
                                port=self.config.get("port", 5432),
                                connect_timeout=10
                            )
                    
                    # If we get here, the connection was successful.
                    if self.conn:
                        # Check connection with a simple query
                        cursor = self.conn.cursor()
                        cursor.execute("SELECT 1")
                        cursor.close()
                        return True
                        
                except (sqlite3.Error, mysql.connector.Error, psycopg2.Error) as e:
                    # If the error is not a timeout, propagate the exception
                    if "timeout" not in str(e).lower() and "wait timeout" not in str(e).lower():
                        raise
                    
                    # If it is a timeout error, we wait a bit and try again.
                    time.sleep(1.0)
            
            # If we get here, the wait time is up.
            raise TimeoutError(f"Could not connect to the database in {self.connection_timeout} seconds")
                
        except Exception as e:
            if self.conn:
                try:
                    self.conn.close()
                except:
                    pass
                self.conn = None
            
            print(f"Error connecting to the database: {str(e)}")
            return False
    
    def extract_schema(self, sample_limit: int = 5, table_limit: Optional[int] = None, 
                      progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Extracts the schema with limits and progress.
        
        Args:
            sample_limit: Data sample limit per table
            table_limit: Limit of tables to process (None for all)
            progress_callback: Optional function to report progress
            
        Returns:
            Dictionary with the database schema
        """
        # Ensure we are connected
        if not self.conn and not self.connect():
            return {"type": "sql", "tables": {}, "tables_list": []}
        
        # Initialize schema
        schema = {
            "type": "sql",
            "engine": self.engine,
            "database": self.config.get("database", ""),
            "tables": {}
        }
        
        # Select the extractor function according to the motor
        if self.engine == "sqlite":
            return self._extract_sqlite_schema(sample_limit, table_limit, progress_callback)
        elif self.engine == "mysql":
            return self._extract_mysql_schema(sample_limit, table_limit, progress_callback)
        elif self.engine == "postgresql":
            return self._extract_postgresql_schema(sample_limit, table_limit, progress_callback)
        else:
            return schema  # Empty diagram if the engine is not recognized
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Executes an SQL query with improved error handling.
        
        Args:
            query: SQL query to execute
            
        Returns:
            List of resulting rows as dictionaries
        """
        if not self.conn and not self.connect():
            raise ConnectionError("No se pudo establecer conexión con la base de datos")
        
        try:
            # Execute query according to the engine
            if self.engine == "sqlite":
                return self._execute_sqlite_query(query)
            elif self.engine == "mysql":
                return self._execute_mysql_query(query)
            elif self.engine == "postgresql":
                return self._execute_postgresql_query(query)
            else:
                raise ValueError(f"Database engine not supported: {self.engine}")
        
        except Exception as e:
            # Try to reconnect and try again once
            try:
                self.close()
                if self.connect():
                    print("Reconnecting and retrying query...")
                    
                    if self.engine == "sqlite":
                        return self._execute_sqlite_query(query)
                    elif self.engine == "mysql":
                        return self._execute_mysql_query(query)
                    elif self.engine == "postgresql":
                        return self._execute_postgresql_query(query)
                    
            except Exception as retry_error:
                # If the retry fails, propagate the original error
                raise Exception(f"Error executing query: {str(e)}")
            
            # If we get here without returning, there was an error in the retry.
            raise Exception(f"Error executing query (after reconnection): {str(e)}")
    
    def _execute_sqlite_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a query in SQLite."""
        cursor = self.conn.cursor()
        cursor.execute(query)
        
        # Convert rows to dictionaries
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        result = []
        
        for row in rows:
            row_dict = {}
            for i, column in enumerate(columns):
                row_dict[column] = row[i]
            result.append(row_dict)
        
        cursor.close()
        return result
    
    def _execute_mysql_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a query in MySQL."""
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        return result
    
    def _execute_postgresql_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a query in PostgreSQL."""
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(query)
        results = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        return results
    
    def _extract_sqlite_schema(self, sample_limit: int, table_limit: Optional[int], progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """
        Extracts specific schema for SQLite.
        
        Args:
            sample_limit: Maximum number of sample rows per table
            table_limit: Maximum number of tables to extract
            progress_callback: Function to report progress
            
        Returns:
            Dictionary with the database schema
        """
        schema = {
            "type": "sql",
            "engine": "sqlite",
            "database": self.config.get("database", ""),
            "tables": {}
        }
        
        try:
            cursor = self.conn.cursor()
            
            # Get the list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Limit tables if necessary
            if table_limit is not None and table_limit > 0:
                tables = tables[:table_limit]
            
            # Process each table
            total_tables = len(tables)
            for i, table_name in enumerate(tables):
                # Report progress if there is a callback
                if progress_callback:
                    progress_callback(i, total_tables, f"Processing table {table_name}")
                
                # Extract information from columns
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = [{"name": col[1], "type": col[2]} for col in cursor.fetchall()]
                
                # Save basic table information
                schema["tables"][table_name] = {
                    "columns": columns,
                    "sample_data": []
                }
                
                # Get data sample
                try:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT {sample_limit};")
                    
                    # Get column names
                    col_names = [desc[0] for desc in cursor.description]
                    
                    # Process the rows
                    sample_data = []
                    for row in cursor.fetchall():
                        row_dict = {}
                        for j, value in enumerate(row):
                            # Convert values ​​that are not directly serializable to string
                            if isinstance(value, (bytes, bytearray)):
                                row_dict[col_names[j]] = f"<binary data: {len(value)} bytes>"
                            else:
                                row_dict[col_names[j]] = value
                        sample_data.append(row_dict)
                    
                    schema["tables"][table_name]["sample_data"] = sample_data
                    
                except Exception as e:
                    print(f"Error getting sample data for table {table_name}: {str(e)}") # TODO: Translate to English
            
            cursor.close()
            
        except Exception as e:
            print(f"Error extracting SQLite schema: {str(e)}") # TODO: Translate to English
        
        # Create the list of tables for compatibility
        table_list = []
        for table_name, table_info in schema["tables"].items():
            table_data = {"name": table_name}
            table_data.update(table_info)
            table_list.append(table_data)
        
        schema["tables_list"] = table_list
        return schema
    
    def _extract_mysql_schema(self, sample_limit: int, table_limit: Optional[int], progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """
        Extracts specific schema for MySQL.
        
        Args:
            sample_limit: Maximum number of sample rows per table
            table_limit: Maximum number of tables to extract
            progress_callback: Function to report progress
            
        Returns:
            Dictionary with the database schema
        """
        schema = {
            "type": "sql",
            "engine": "mysql",
            "database": self.config.get("database", ""),
            "tables": {}
        }
        
        try:
            cursor = self.conn.cursor(dictionary=True)
            
            # Get the list of tables
            cursor.execute("SHOW TABLES;")
            tables_result = cursor.fetchall()
            tables = []
            
            # Extract table names (format may vary depending on version)
            for row in tables_result:
                if len(row) == 1:  # If it is a simple list
                    tables.extend(row.values())
                else:  # If it has a complex structure
                    for value in row.values():
                        if isinstance(value, str):
                            tables.append(value)
                            break
            
            # Limit tables if necessary
            if table_limit is not None and table_limit > 0:
                tables = tables[:table_limit]
            
            # Process each table
            total_tables = len(tables)
            for i, table_name in enumerate(tables):
                # Report progress if there is a callback
                if progress_callback:
                    progress_callback(i, total_tables, f"Processing table {table_name}")
                
                # Extract information from columns
                cursor.execute(f"DESCRIBE `{table_name}`;")
                columns = [{"name": col.get("Field"), "type": col.get("Type")} for col in cursor.fetchall()]
                
                # Save basic table information
                schema["tables"][table_name] = {
                    "columns": columns,
                    "sample_data": []
                }
                
                # Get data sample
                try:
                    cursor.execute(f"SELECT * FROM `{table_name}` LIMIT {sample_limit};")
                    sample_data = cursor.fetchall()
                    
                    # Process values ​​that are not JSON serializable
                    processed_samples = []
                    for row in sample_data:
                        processed_row = {}
                        for key, value in row.items():
                            if isinstance(value, (bytes, bytearray)):
                                processed_row[key] = f"<binary data: {len(value)} bytes>"
                            elif hasattr(value, 'isoformat'):  # For dates and times
                                processed_row[key] = value.isoformat()
                            else:
                                processed_row[key] = value
                        processed_samples.append(processed_row)
                    
                    schema["tables"][table_name]["sample_data"] = processed_samples
                    
                except Exception as e:
                    print(f"Error getting sample data for table {table_name}: {str(e)}") # TODO: Translate to English
            
            cursor.close()
            
        except Exception as e:
            print(f"Error extracting MySQL schema: {str(e)}") # TODO: Translate to English
        
        # Create the list of tables for compatibility
        table_list = []
        for table_name, table_info in schema["tables"].items():
            table_data = {"name": table_name}
            table_data.update(table_info)
            table_list.append(table_data)
        
        schema["tables_list"] = table_list
        return schema
    
    def _extract_postgresql_schema(self, sample_limit: int, table_limit: Optional[int], progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """
        Extracts specific schema for PostgreSQL with optimizations.
        
        Args:
            sample_limit: Maximum number of sample rows per table
            table_limit: Maximum number of tables to extract
            progress_callback: Function to report progress
            
        Returns:
            Dictionary with the database schema
        """
        schema = {
            "type": "sql",
            "engine": "postgresql",
            "database": self.config.get("database", ""),
            "tables": {}
        }
        
        try:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Strategy 1: Search all accessible schemas
            cursor.execute("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                  AND table_type = 'BASE TABLE'
                ORDER BY table_schema, table_name;
            """)
            tables = cursor.fetchall()
            
            # If no tables were found, try alternative strategy
            if not tables:
                cursor.execute("""
                    SELECT schemaname AS table_schema, tablename AS table_name 
                    FROM pg_tables 
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY schemaname, tablename;
                """)
                tables = cursor.fetchall()
            
            # If there are no tables yet, try searching in specific schemas
            if not tables:
                cursor.execute("""
                    SELECT DISTINCT table_schema 
                    FROM information_schema.tables 
                    ORDER BY table_schema;
                """)
                schemas = cursor.fetchall()
                
                # Try non-system schemes
                user_schemas = [s[0] for s in schemas if s[0] not in ('pg_catalog', 'information_schema')]
                for schema_name in user_schemas:
                    cursor.execute(f"""
                        SELECT '{schema_name}' AS table_schema, table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = '{schema_name}'
                          AND table_type = 'BASE TABLE';
                    """)
                    schema_tables = cursor.fetchall()
                    if schema_tables:
                        tables.extend(schema_tables)
            
            # Limit tables if necessary
            if table_limit is not None and table_limit > 0:
                tables = tables[:table_limit]
            
            # Process each table
            total_tables = len(tables)
            for i, (schema_name, table_name) in enumerate(tables):
                # Report progress if there is a callback
                if progress_callback:
                    progress_callback(i, total_tables, f"Procesando tabla {schema_name}.{table_name}")
                
                # Determine the full name of the table
                full_name = f"{schema_name}.{table_name}" if schema_name != 'public' else table_name
                
                # Extract information from columns
                cursor.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = '{schema_name}' AND table_name = '{table_name}'
                    ORDER BY ordinal_position;
                """)
                
                columns_data = cursor.fetchall()
                if columns_data:
                    columns = [{"name": col[0], "type": col[1]} for col in columns_data]
                    schema["tables"][full_name] = {"columns": columns, "sample_data": []}
                    
                    # Get data sample
                    try:
                        cursor.execute(f"""
                            SELECT * FROM "{schema_name}"."{table_name}" LIMIT {sample_limit};
                        """)
                        rows = cursor.fetchall()
                        
                        # Get column names
                        col_names = [desc[0] for desc in cursor.description]
                        
                        # Convert rows to dictionaries
                        sample_data = []
                        for row in rows:
                            row_dict = {}
                            for j, value in enumerate(row):
                                # Convert to serializable format
                                if hasattr(value, 'isoformat'):  # For dates and times
                                    row_dict[col_names[j]] = value.isoformat()
                                elif isinstance(value, (bytes, bytearray)):
                                    row_dict[col_names[j]] = f"<binary data: {len(value)} bytes>"
                                else:
                                    row_dict[col_names[j]] = str(value) if value is not None else None
                            sample_data.append(row_dict)
                        
                        schema["tables"][full_name]["sample_data"] = sample_data
                        
                    except Exception as e:
                        print(f"Error getting sample data for table {full_name}: {str(e)}") # TODO: Translate to English
                else:
                    # Register the table even if it has no columns
                    schema["tables"][full_name] = {"columns": [], "sample_data": []}
            
            cursor.close()
            
        except Exception as e:
            print(f"Error extracting PostgreSQL schema: {str(e)}") # TODO: Translate to English
            
            # Recovery attempt to diagnose problems
            try:
                if self.conn and self.conn.closed == 0:  # 0 = open connection
                    recovery_cursor = self.conn.cursor()
                    
                    # Check version
                    recovery_cursor.execute("SELECT version();")
                    version = recovery_cursor.fetchone()
                    print(f"PostgreSQL version: {version[0] if version else 'Unknown'}")
                    
                    # Check permissions
                    recovery_cursor.execute("""
                        SELECT has_schema_privilege(current_user, 'public', 'USAGE') AS has_usage,
                               has_schema_privilege(current_user, 'public', 'CREATE') AS has_create;
                    """)
                    perms = recovery_cursor.fetchone()
                    if perms:
                        print(f"Permissions in public schema: USAGE={perms[0]}, CREATE={perms[1]}") # TODO: Translate to English
                        
                    recovery_cursor.close()
            except Exception as diag_err:
                print(f"Error during diagnosis: {str(diag_err)}") # TODO: Translate to English
        
        # Create the list of tables for compatibility
        table_list = []
        for table_name, table_info in schema["tables"].items():
            table_data = {"name": table_name}
            table_data.update(table_info)
            table_list.append(table_data)
        
        schema["tables_list"] = table_list
        return schema
    
    def close(self) -> None:
        """Closes the database connection."""
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
            finally:
                self.conn = None
    
    def __del__(self):
        """Destructor to ensure the connection is closed."""
        self.close()