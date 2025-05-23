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
        self.connection_timeout = 30  # segundos
    
    def connect(self) -> bool:
        """
        Establishes a connection with optimized timeout.
        
        Returns:
            True if the connection was successful, False otherwise
        """
        try:
            start_time = time.time()
            
            # Intentar la conexión con un límite de tiempo
            while time.time() - start_time < self.connection_timeout:
                try:
                    if self.engine == "sqlite":
                        if "connection_string" in self.config:
                            self.conn = sqlite3.connect(self.config["connection_string"], timeout=10.0)
                        else:
                            self.conn = sqlite3.connect(self.config.get("database", ""), timeout=10.0)
                        
                        # Configurar para que devuelva filas como diccionarios
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
                        # Determinar si usar cadena de conexión o parámetros
                        if "connection_string" in self.config:
                            # Agregar timeout a la cadena de conexión si no está presente
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
                    
                    # Si llegamos aquí, la conexión fue exitosa
                    if self.conn:
                        # Verificar conexión con una consulta simple
                        cursor = self.conn.cursor()
                        cursor.execute("SELECT 1")
                        cursor.close()
                        return True
                        
                except (sqlite3.Error, mysql.connector.Error, psycopg2.Error) as e:
                    # Si el error no es de timeout, propagar la excepción
                    if "timeout" not in str(e).lower() and "tiempo de espera" not in str(e).lower():
                        raise
                    
                    # Si es un error de timeout, esperamos un poco y reintentamos
                    time.sleep(1.0)
            
            # Si llegamos aquí, se agotó el tiempo de espera
            raise TimeoutError(f"No se pudo conectar a la base de datos en {self.connection_timeout} segundos")
                
        except Exception as e:
            if self.conn:
                try:
                    self.conn.close()
                except:
                    pass
                self.conn = None
            
            print(f"Error al conectar a la base de datos: {str(e)}")
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
        # Asegurar que estamos conectados
        if not self.conn and not self.connect():
            return {"type": "sql", "tables": {}, "tables_list": []}
        
        # Inicializar esquema
        schema = {
            "type": "sql",
            "engine": self.engine,
            "database": self.config.get("database", ""),
            "tables": {}
        }
        
        # Seleccionar la función extractora según el motor
        if self.engine == "sqlite":
            return self._extract_sqlite_schema(sample_limit, table_limit, progress_callback)
        elif self.engine == "mysql":
            return self._extract_mysql_schema(sample_limit, table_limit, progress_callback)
        elif self.engine == "postgresql":
            return self._extract_postgresql_schema(sample_limit, table_limit, progress_callback)
        else:
            return schema  # Esquema vacío si no se reconoce el motor
    
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
            # Ejecutar query según el motor
            if self.engine == "sqlite":
                return self._execute_sqlite_query(query)
            elif self.engine == "mysql":
                return self._execute_mysql_query(query)
            elif self.engine == "postgresql":
                return self._execute_postgresql_query(query)
            else:
                raise ValueError(f"Motor de base de datos no soportado: {self.engine}")
        
        except Exception as e:
            # Intentar reconectar y reintentar una vez
            try:
                self.close()
                if self.connect():
                    print("Reconectando y reintentando consulta...")
                    
                    if self.engine == "sqlite":
                        return self._execute_sqlite_query(query)
                    elif self.engine == "mysql":
                        return self._execute_mysql_query(query)
                    elif self.engine == "postgresql":
                        return self._execute_postgresql_query(query)
                    
            except Exception as retry_error:
                # Si falla el reintento, propagar el error original
                raise Exception(f"Error al ejecutar consulta: {str(e)}")
            
            # Si llegamos aquí sin retornar, ha habido un error en el reintento
            raise Exception(f"Error al ejecutar consulta (después de reconexión): {str(e)}")
    
    def _execute_sqlite_query(self, query: str) -> List[Dict[str, Any]]:
        """Executes a query in SQLite."""
        cursor = self.conn.cursor()
        cursor.execute(query)
        
        # Convertir filas a diccionarios
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
            
            # Obtener la lista de tablas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Limitar tablas si es necesario
            if table_limit is not None and table_limit > 0:
                tables = tables[:table_limit]
            
            # Procesar cada tabla
            total_tables = len(tables)
            for i, table_name in enumerate(tables):
                # Reportar progreso si hay callback
                if progress_callback:
                    progress_callback(i, total_tables, f"Procesando tabla {table_name}")
                
                # Extraer información de columnas
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = [{"name": col[1], "type": col[2]} for col in cursor.fetchall()]
                
                # Guardar información básica de la tabla
                schema["tables"][table_name] = {
                    "columns": columns,
                    "sample_data": []
                }
                
                # Obtener muestra de datos
                try:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT {sample_limit};")
                    
                    # Obtener nombres de columnas
                    col_names = [desc[0] for desc in cursor.description]
                    
                    # Procesar las filas
                    sample_data = []
                    for row in cursor.fetchall():
                        row_dict = {}
                        for j, value in enumerate(row):
                            # Convertir a string los valores que no son serializable directamente
                            if isinstance(value, (bytes, bytearray)):
                                row_dict[col_names[j]] = f"<binary data: {len(value)} bytes>"
                            else:
                                row_dict[col_names[j]] = value
                        sample_data.append(row_dict)
                    
                    schema["tables"][table_name]["sample_data"] = sample_data
                    
                except Exception as e:
                    print(f"Error al obtener muestra de datos para tabla {table_name}: {str(e)}")
            
            cursor.close()
            
        except Exception as e:
            print(f"Error al extraer esquema SQLite: {str(e)}")
        
        # Crear la lista de tablas para compatibilidad
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
            
            # Obtener la lista de tablas
            cursor.execute("SHOW TABLES;")
            tables_result = cursor.fetchall()
            tables = []
            
            # Extraer nombres de tablas (el formato puede variar según versión)
            for row in tables_result:
                if len(row) == 1:  # Si es una lista simple
                    tables.extend(row.values())
                else:  # Si tiene estructura compleja
                    for value in row.values():
                        if isinstance(value, str):
                            tables.append(value)
                            break
            
            # Limitar tablas si es necesario
            if table_limit is not None and table_limit > 0:
                tables = tables[:table_limit]
            
            # Procesar cada tabla
            total_tables = len(tables)
            for i, table_name in enumerate(tables):
                # Reportar progreso si hay callback
                if progress_callback:
                    progress_callback(i, total_tables, f"Procesando tabla {table_name}")
                
                # Extraer información de columnas
                cursor.execute(f"DESCRIBE `{table_name}`;")
                columns = [{"name": col.get("Field"), "type": col.get("Type")} for col in cursor.fetchall()]
                
                # Guardar información básica de la tabla
                schema["tables"][table_name] = {
                    "columns": columns,
                    "sample_data": []
                }
                
                # Obtener muestra de datos
                try:
                    cursor.execute(f"SELECT * FROM `{table_name}` LIMIT {sample_limit};")
                    sample_data = cursor.fetchall()
                    
                    # Procesar valores que no son JSON serializable
                    processed_samples = []
                    for row in sample_data:
                        processed_row = {}
                        for key, value in row.items():
                            if isinstance(value, (bytes, bytearray)):
                                processed_row[key] = f"<binary data: {len(value)} bytes>"
                            elif hasattr(value, 'isoformat'):  # Para fechas y horas
                                processed_row[key] = value.isoformat()
                            else:
                                processed_row[key] = value
                        processed_samples.append(processed_row)
                    
                    schema["tables"][table_name]["sample_data"] = processed_samples
                    
                except Exception as e:
                    print(f"Error al obtener muestra de datos para tabla {table_name}: {str(e)}")
            
            cursor.close()
            
        except Exception as e:
            print(f"Error al extraer esquema MySQL: {str(e)}")
        
        # Crear la lista de tablas para compatibilidad
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
            
            # Estrategia 1: Buscar en todos los esquemas accesibles
            cursor.execute("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                  AND table_type = 'BASE TABLE'
                ORDER BY table_schema, table_name;
            """)
            tables = cursor.fetchall()
            
            # Si no se encontraron tablas, intentar estrategia alternativa
            if not tables:
                cursor.execute("""
                    SELECT schemaname AS table_schema, tablename AS table_name 
                    FROM pg_tables 
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY schemaname, tablename;
                """)
                tables = cursor.fetchall()
            
            # Si aún no hay tablas, intentar buscar en esquemas específicos
            if not tables:
                cursor.execute("""
                    SELECT DISTINCT table_schema 
                    FROM information_schema.tables 
                    ORDER BY table_schema;
                """)
                schemas = cursor.fetchall()
                
                # Intentar con esquemas que no sean del sistema
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
            
            # Limitar tablas si es necesario
            if table_limit is not None and table_limit > 0:
                tables = tables[:table_limit]
            
            # Procesar cada tabla
            total_tables = len(tables)
            for i, (schema_name, table_name) in enumerate(tables):
                # Reportar progreso si hay callback
                if progress_callback:
                    progress_callback(i, total_tables, f"Procesando tabla {schema_name}.{table_name}")
                
                # Determinar el nombre completo de la tabla
                full_name = f"{schema_name}.{table_name}" if schema_name != 'public' else table_name
                
                # Extraer información de columnas
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
                    
                    # Obtener muestra de datos
                    try:
                        cursor.execute(f"""
                            SELECT * FROM "{schema_name}"."{table_name}" LIMIT {sample_limit};
                        """)
                        rows = cursor.fetchall()
                        
                        # Obtener nombres de columnas
                        col_names = [desc[0] for desc in cursor.description]
                        
                        # Convertir filas a diccionarios
                        sample_data = []
                        for row in rows:
                            row_dict = {}
                            for j, value in enumerate(row):
                                # Convertir a formato serializable
                                if hasattr(value, 'isoformat'):  # Para fechas y horas
                                    row_dict[col_names[j]] = value.isoformat()
                                elif isinstance(value, (bytes, bytearray)):
                                    row_dict[col_names[j]] = f"<binary data: {len(value)} bytes>"
                                else:
                                    row_dict[col_names[j]] = str(value) if value is not None else None
                            sample_data.append(row_dict)
                        
                        schema["tables"][full_name]["sample_data"] = sample_data
                        
                    except Exception as e:
                        print(f"Error al obtener muestra de datos para tabla {full_name}: {str(e)}")
                else:
                    # Registrar la tabla aunque no tenga columnas
                    schema["tables"][full_name] = {"columns": [], "sample_data": []}
            
            cursor.close()
            
        except Exception as e:
            print(f"Error al extraer esquema PostgreSQL: {str(e)}")
            
            # Intento de recuperación para diagnosticar problemas
            try:
                if self.conn and self.conn.closed == 0:  # 0 = conexión abierta
                    recovery_cursor = self.conn.cursor()
                    
                    # Verificar versión
                    recovery_cursor.execute("SELECT version();")
                    version = recovery_cursor.fetchone()
                    print(f"Versión PostgreSQL: {version[0] if version else 'Desconocida'}")
                    
                    # Verificar permisos
                    recovery_cursor.execute("""
                        SELECT has_schema_privilege(current_user, 'public', 'USAGE') AS has_usage,
                               has_schema_privilege(current_user, 'public', 'CREATE') AS has_create;
                    """)
                    perms = recovery_cursor.fetchone()
                    if perms:
                        print(f"Permisos en esquema public: USAGE={perms[0]}, CREATE={perms[1]}")
                        
                    recovery_cursor.close()
            except Exception as diag_err:
                print(f"Error durante el diagnóstico: {str(diag_err)}")
        
        # Crear la lista de tablas para compatibilidad
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