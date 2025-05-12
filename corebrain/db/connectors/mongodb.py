"""
Conector para bases de datos MongoDB.
"""

import time
import json
import re

from typing import Dict, Any, List, Optional, Callable, Tuple

try:
    import pymongo
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

from corebrain.db.connector import DatabaseConnector

class MongoDBConnector(DatabaseConnector):
    """Conector optimizado para MongoDB"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el conector MongoDB con la configuración proporcionada.
        
        Args:
            config: Diccionario con la configuración de conexión
        """
        super().__init__(config)
        self.client = None
        self.db = None
        self.config = config
        self.connection_timeout = 30  # segundos
        
        if not PYMONGO_AVAILABLE:
            print("Advertencia: pymongo no está instalado. Instálalo con 'pip install pymongo'")
    
    def connect(self) -> bool:
        """
        Establece conexión con timeout optimizado
        
        Returns:
            True si la conexión fue exitosa, False en caso contrario
        """
        if not PYMONGO_AVAILABLE:
            raise ImportError("pymongo no está instalado. Instálalo con 'pip install pymongo'")
        
        try:
            start_time = time.time()
            
            # Construir los parámetros de conexión
            if "connection_string" in self.config:
                connection_string = self.config["connection_string"]
                # Añadir timeout a la cadena de conexión si no está presente
                if "connectTimeoutMS=" not in connection_string:
                    if "?" in connection_string:
                        connection_string += "&connectTimeoutMS=10000"  # 10 segundos
                    else:
                        connection_string += "?connectTimeoutMS=10000"
                
                # Crear cliente MongoDB con la cadena de conexión
                self.client = pymongo.MongoClient(connection_string)
            else:
                # Diccionario de parámetros para MongoClient
                mongo_params = {
                    "host": self.config.get("host", "localhost"),
                    "port": int(self.config.get("port", 27017)),
                    "connectTimeoutMS": 10000,  # 10 segundos
                    "serverSelectionTimeoutMS": 10000
                }
                
                # Añadir credenciales solo si están presentes
                if self.config.get("user"):
                    mongo_params["username"] = self.config.get("user")
                if self.config.get("password"):
                    mongo_params["password"] = self.config.get("password")
                
                # Opcionalmente añadir opciones de autenticación
                if self.config.get("auth_source"):
                    mongo_params["authSource"] = self.config.get("auth_source")
                if self.config.get("auth_mechanism"):
                    mongo_params["authMechanism"] = self.config.get("auth_mechanism")
                
                # Crear cliente MongoDB con parámetros
                self.client = pymongo.MongoClient(**mongo_params)
            
            # Verificar que la conexión funciona
            self.client.admin.command('ping')
            
            # Seleccionar la base de datos
            db_name = self.config.get("database", "")
            if not db_name:
                # Si no hay base de datos especificada, listar las disponibles
                db_names = self.client.list_database_names()
                if not db_names:
                    raise ValueError("No se encontraron bases de datos disponibles")
                
                # Seleccionar la primera que no sea de sistema
                system_dbs = ["admin", "local", "config"]
                for name in db_names:
                    if name not in system_dbs:
                        db_name = name
                        break
                
                # Si no encontramos ninguna que no sea de sistema, usar la primera
                if not db_name:
                    db_name = db_names[0]
                
                print(f"No se especificó base de datos. Usando '{db_name}'")
            
            # Guardar la referencia a la base de datos
            self.db = self.client[db_name]
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            # Si es un error de timeout, reintentar
            if time.time() - start_time < self.connection_timeout:
                print(f"Timeout al conectar a MongoDB: {str(e)}. Reintentando...")
                time.sleep(2)  # Esperar antes de reintentar
                return self.connect()
            else:
                print(f"Error de conexión a MongoDB después de {self.connection_timeout}s: {str(e)}")
                self.close()
                return False
        except Exception as e:
            print(f"Error al conectar a MongoDB: {str(e)}")
            self.close()
            return False
    
    def extract_schema(self, sample_limit: int = 5, collection_limit: Optional[int] = None, 
                      progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Extrae el esquema con límites y progreso para mejorar rendimiento
        
        Args:
            sample_limit: Número máximo de documentos de muestra por colección
            collection_limit: Límite de colecciones a procesar (None para todas)
            progress_callback: Función opcional para reportar progreso
            
        Returns:
            Diccionario con el esquema de la base de datos
        """
        # Asegurar que estamos conectados
        if not self.client and not self.connect():
            return {"type": "mongodb", "tables": {}, "tables_list": []}
        
        # Inicializar el esquema
        schema = {
            "type": "mongodb",
            "database": self.db.name,
            "tables": {}  # En MongoDB, las "tablas" son colecciones
        }
        
        try:
            # Obtener la lista de colecciones
            collections = self.db.list_collection_names()
            
            # Limitar colecciones si es necesario
            if collection_limit is not None and collection_limit > 0:
                collections = collections[:collection_limit]
            
            # Procesar cada colección
            total_collections = len(collections)
            for i, collection_name in enumerate(collections):
                # Reportar progreso si hay callback
                if progress_callback:
                    progress_callback(i, total_collections, f"Procesando colección {collection_name}")
                
                collection = self.db[collection_name]
                
                try:
                    # Contar documentos
                    doc_count = collection.count_documents({})
                    
                    if doc_count > 0:
                        # Obtener muestra de documentos
                        sample_docs = list(collection.find().limit(sample_limit))
                        
                        # Extraer campos y sus tipos
                        fields = {}
                        for doc in sample_docs:
                            self._extract_document_fields(doc, fields)
                        
                        # Convertir a formato esperado
                        formatted_fields = [{"name": field, "type": type_name} for field, type_name in fields.items()]
                        
                        # Procesar documentos para sample_data
                        sample_data = []
                        for doc in sample_docs:
                            processed_doc = self._process_document_for_serialization(doc)
                            sample_data.append(processed_doc)
                        
                        # Guardar en el esquema
                        schema["tables"][collection_name] = {
                            "fields": formatted_fields,
                            "sample_data": sample_data,
                            "count": doc_count
                        }
                    else:
                        # Colección vacía
                        schema["tables"][collection_name] = {
                            "fields": [],
                            "sample_data": [],
                            "count": 0,
                            "empty": True
                        }
                        
                except Exception as e:
                    print(f"Error al procesar colección {collection_name}: {str(e)}")
                    schema["tables"][collection_name] = {
                        "fields": [],
                        "error": str(e)
                    }
            
            # Crear la lista de tablas/colecciones para compatibilidad
            table_list = []
            for collection_name, collection_info in schema["tables"].items():
                table_data = {"name": collection_name}
                table_data.update(collection_info)
                table_list.append(table_data)
            
            # Guardar también la lista de tablas para compatibilidad
            schema["tables_list"] = table_list
            
            return schema
            
        except Exception as e:
            print(f"Error al extraer el esquema MongoDB: {str(e)}")
            return {"type": "mongodb", "tables": {}, "tables_list": []}
    
    def _extract_document_fields(self, doc: Dict[str, Any], fields: Dict[str, str], 
                                prefix: str = "", max_depth: int = 3, current_depth: int = 0) -> None:
        """
        Extrae recursivamente los campos y tipos de un documento MongoDB.
        
        Args:
            doc: Documento a analizar
            fields: Diccionario donde guardar los campos y tipos
            prefix: Prefijo para campos anidados
            max_depth: Profundidad máxima para campos anidados
            current_depth: Profundidad actual
        """
        if current_depth >= max_depth:
            return
            
        for field, value in doc.items():
            # Para _id y otros campos especiales
            if field == "_id":
                field_type = "ObjectId"
            elif isinstance(value, dict):
                if current_depth < max_depth - 1:
                    # Recursión para campos anidados
                    self._extract_document_fields(value, fields, 
                                                f"{prefix}{field}.", max_depth, current_depth + 1)
                field_type = "object"
            elif isinstance(value, list):
                if value and current_depth < max_depth - 1:
                    # Si tenemos elementos en la lista, analizar el primero
                    if isinstance(value[0], dict):
                        self._extract_document_fields(value[0], fields, 
                                                    f"{prefix}{field}[].", max_depth, current_depth + 1)
                    else:
                        # Para listas de tipos primitivos
                        field_type = f"array<{type(value[0]).__name__}>"
                else:
                    field_type = "array"
            else:
                field_type = type(value).__name__
            
            # Guardar el tipo del campo actual
            field_key = f"{prefix}{field}"
            if field_key not in fields:
                fields[field_key] = field_type
    
    def _process_document_for_serialization(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un documento para ser serializable a JSON.
        
        Args:
            doc: Documento a procesar
            
        Returns:
            Documento procesado
        """
        processed_doc = {}
        for field, value in doc.items():
            # Convertir ObjectId a string
            if field == "_id":
                processed_doc[field] = str(value)
            # Manejar objetos anidados
            elif isinstance(value, dict):
                processed_doc[field] = self._process_document_for_serialization(value)
            # Manejar arrays
            elif isinstance(value, list):
                processed_items = []
                for item in value:
                    if isinstance(item, dict):
                        processed_items.append(self._process_document_for_serialization(item))
                    elif hasattr(item, "__str__"):
                        processed_items.append(str(item))
                    else:
                        processed_items.append(item)
                processed_doc[field] = processed_items
            # Convertir fechas a ISO
            elif hasattr(value, 'isoformat'):
                processed_doc[field] = value.isoformat()
            # Otros tipos de datos
            else:
                processed_doc[field] = value
                
        return processed_doc
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Ejecuta una consulta MongoDB con manejo de errores mejorado
        
        Args:
            query: Consulta MongoDB en formato JSON o lenguaje de consulta
            
        Returns:
            Lista de documentos resultantes
        """
        if not self.client and not self.connect():
            raise ConnectionError("No se pudo establecer conexión con MongoDB")
        
        try:
            # Determinar si la consulta es un string JSON o una consulta en otro formato
            filter_dict, projection, collection_name, limit = self._parse_query(query)
            
            # Obtener la colección
            if not collection_name:
                raise ValueError("No se especificó el nombre de la colección en la consulta")
                
            collection = self.db[collection_name]
            
            # Ejecutar la consulta
            if projection:
                cursor = collection.find(filter_dict, projection).limit(limit or 100)
            else:
                cursor = collection.find(filter_dict).limit(limit or 100)
            
            # Convertir los resultados a formato serializable
            results = []
            for doc in cursor:
                processed_doc = self._process_document_for_serialization(doc)
                results.append(processed_doc)
            
            return results
            
        except Exception as e:
            # Intentar reconectar y reintentar una vez
            try:
                self.close()
                if self.connect():
                    print("Reconectando y reintentando consulta...")
                    
                    # Reintentar la consulta
                    filter_dict, projection, collection_name, limit = self._parse_query(query)
                    collection = self.db[collection_name]
                    
                    if projection:
                        cursor = collection.find(filter_dict, projection).limit(limit or 100)
                    else:
                        cursor = collection.find(filter_dict).limit(limit or 100)
                    
                    results = []
                    for doc in cursor:
                        processed_doc = self._process_document_for_serialization(doc)
                        results.append(processed_doc)
                    
                    return results
            except Exception as retry_error:
                # Si falla el reintento, propagar el error original
                raise Exception(f"Error al ejecutar consulta MongoDB: {str(e)}")
            
            # Si llegamos aquí, ha habido un error en el reintento
            raise Exception(f"Error al ejecutar consulta MongoDB (después de reconexión): {str(e)}")
    
    def _parse_query(self, query: str) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]], str, Optional[int]]:
        """
        Analiza una consulta y extrae los componentes necesarios.
        
        Args:
            query: Consulta en formato string
            
        Returns:
            Tupla con (filtro, proyección, nombre de colección, límite)
        """
        # Intentar parsear como JSON
        try:
            query_dict = json.loads(query)
            
            # Extraer componentes de la consulta
            filter_dict = query_dict.get("filter", {})
            projection = query_dict.get("projection")
            collection_name = query_dict.get("collection")
            limit = query_dict.get("limit")
            
            return filter_dict, projection, collection_name, limit
            
        except json.JSONDecodeError:
            # Si no es JSON válido, intentar parsear el formato de consulta alternativo
            collection_match = re.search(r'from\s+([a-zA-Z0-9_]+)', query, re.IGNORECASE)
            collection_name = collection_match.group(1) if collection_match else None
            
            # Intentar extraer filtros
            filter_match = re.search(r'where\s+(.+?)(?:limit|$)', query, re.IGNORECASE | re.DOTALL)
            filter_str = filter_match.group(1).strip() if filter_match else "{}"
            
            # Intentar parsear los filtros como JSON
            try:
                filter_dict = json.loads(filter_str)
            except json.JSONDecodeError:
                # Si no se puede parsear, usar filtro vacío
                filter_dict = {}
            
            # Extraer límite si existe
            limit_match = re.search(r'limit\s+(\d+)', query, re.IGNORECASE)
            limit = int(limit_match.group(1)) if limit_match else None
            
            return filter_dict, None, collection_name, limit
    
    def count_documents(self, collection_name: str, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        """
        Cuenta documentos en una colección
        
        Args:
            collection_name: Nombre de la colección
            filter_dict: Filtro opcional
            
        Returns:
            Número de documentos
        """
        if not self.client and not self.connect():
            raise ConnectionError("No se pudo establecer conexión con MongoDB")
        
        try:
            collection = self.db[collection_name]
            return collection.count_documents(filter_dict or {})
        except Exception as e:
            print(f"Error al contar documentos: {str(e)}")
            return 0
    
    def list_collections(self) -> List[str]:
        """
        Devuelve una lista de colecciones en la base de datos
        
        Returns:
            Lista de nombres de colecciones
        """
        if not self.client and not self.connect():
            raise ConnectionError("No se pudo establecer conexión con MongoDB")
        
        try:
            return self.db.list_collection_names()
        except Exception as e:
            print(f"Error al listar colecciones: {str(e)}")
            return []
    
    def close(self) -> None:
        """Cierra la conexión a MongoDB"""
        if self.client:
            try:
                self.client.close()
            except:
                pass
            finally:
                self.client = None
                self.db = None
    
    def __del__(self):
        """Destructor para asegurar que la conexión se cierre"""
        self.close()