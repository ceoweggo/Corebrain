"""
Componentes para extracción y optimización de esquemas de base de datos.
"""
import json

from typing import Dict, Any, Optional

def _print_colored(message: str, color: str) -> None:
    """Versión simplificada de _print_colored que no depende de cli.utils"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "default": "\033[0m"
    }
    color_code = colors.get(color, colors["default"])
    print(f"{color_code}{message}{colors['default']}")

def extract_db_schema(db_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae el esquema de la base de datos directamente sin usar el SDK.
    
    Args:
        db_config: Configuración de la base de datos
    
    Returns:
        Diccionario con la estructura de la base de datos organizada por tablas/colecciones
    """
    db_type = db_config["type"].lower()
    schema = {
        "type": db_type,
        "database": db_config.get("database", ""),
        "tables": {}  # Cambiado a diccionario para facilitar el acceso directo a tablas por nombre
    }
    
    try:
        if db_type == "sql":
            # Código para bases de datos SQL...
            # [Se mantiene igual]
            pass
        
        # Manejar tanto "nosql" como "mongodb" como tipos válidos
        elif db_type == "nosql" or db_type == "mongodb":
            import pymongo
            
            # Determinar el motor (si existe)
            engine = db_config.get("engine", "").lower()
            
            # Si no se especifica el engine o es mongodb, proceder
            if not engine or engine == "mongodb":
                if "connection_string" in db_config:
                    client = pymongo.MongoClient(db_config["connection_string"])
                else:
                    # Diccionario de parámetros para MongoClient
                    mongo_params = {
                        "host": db_config.get("host", "localhost"),
                        "port": db_config.get("port", 27017)
                    }
                    
                    # Añadir credenciales solo si están presentes
                    if db_config.get("user"):
                        mongo_params["username"] = db_config["user"]
                    if db_config.get("password"):
                        mongo_params["password"] = db_config["password"]
                    
                    client = pymongo.MongoClient(**mongo_params)
                
                # Obtener la base de datos
                db_name = db_config.get("database", "")
                if not db_name:
                    _print_colored("⚠️ Nombre de base de datos no especificado", "yellow")
                    return schema
                
                try:
                    db = client[db_name]
                    collection_names = db.list_collection_names()
                    
                    # Procesar colecciones
                    for collection_name in collection_names:
                        collection = db[collection_name]
                        
                        # Obtener varios documentos de muestra
                        try:
                            sample_docs = list(collection.find().limit(5))
                            
                            # Extraer estructura de campos a partir de los documentos
                            field_types = {}
                            
                            for doc in sample_docs:
                                for field, value in doc.items():
                                    if field != "_id":  # Ignoramos el _id de MongoDB
                                        # Actualizar el tipo si no existe o combinar si hay diferentes tipos
                                        field_type = type(value).__name__
                                        if field not in field_types:
                                            field_types[field] = field_type
                                        elif field_types[field] != field_type:
                                            field_types[field] = f"{field_types[field]}|{field_type}"
                            
                            # Convertir a formato esperado
                            fields = [{"name": field, "type": type_name} for field, type_name in field_types.items()]
                            
                            # Convertir documentos a formato serializable
                            sample_data = []
                            for doc in sample_docs:
                                serialized_doc = {}
                                for key, value in doc.items():
                                    if key == "_id":
                                        serialized_doc[key] = str(value)
                                    elif isinstance(value, (dict, list)):
                                        serialized_doc[key] = str(value)  # Simplificar objetos anidados
                                    else:
                                        serialized_doc[key] = value
                                sample_data.append(serialized_doc)
                            
                            # Guardar información de la colección
                            schema["tables"][collection_name] = {
                                "fields": fields,
                                "sample_data": sample_data
                            }
                        except Exception as e:
                            _print_colored(f"Error al procesar colección {collection_name}: {str(e)}", "red")
                            schema["tables"][collection_name] = {
                                "fields": [],
                                "sample_data": [],
                                "error": str(e)
                            }
                
                except Exception as e:
                    _print_colored(f"Error al acceder a la base de datos MongoDB '{db_name}': {str(e)}", "red")
                
                finally:
                    # Cerrar la conexión
                    client.close()
            else:
                _print_colored(f"Motor de base de datos NoSQL no soportado: {engine}", "red")
        
        # Convertir el diccionario de tablas en una lista para mantener compatibilidad con el formato anterior
        table_list = []
        for table_name, table_info in schema["tables"].items():
            table_data = {"name": table_name}
            table_data.update(table_info)
            table_list.append(table_data)
        
        # Guardar también la lista de tablas para mantener compatibilidad
        schema["tables_list"] = table_list
        
        return schema
    
    except Exception as e:
        _print_colored(f"Error al extraer el esquema de la base de datos: {str(e)}", "red")
        # En caso de error, devolver un esquema vacío
        return {"type": db_type, "tables": {}, "tables_list": []}

def extract_db_schema_direct(db_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae el esquema directamente sin usar el cliente de Corebrain.
    Esta es una versión reducida que no requiere importar core.
    """
    db_type = db_config["type"].lower()
    schema = {
        "type": db_type,
        "database": db_config.get("database", ""),
        "tables": {},
        "tables_list": []  # Lista inicialmente vacía
    }
    
    try:
        # [Implementación existente para extraer esquema sin usar Corebrain]
        # ...

        return schema
    except Exception as e:
        _print_colored(f"Error al extraer esquema directamente: {str(e)}", "red")
        return {"type": db_type, "tables": {}, "tables_list": []}

def extract_schema_with_lazy_init(api_key: str, db_config: Dict[str, Any], api_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Extrae esquema usando importación tardía del cliente.
    
    Esta función evita el problema de importación circular cargando
    dinámicamente el cliente de Corebrain solo cuando es necesario.
    """
    try:
        # La importación se mueve aquí para evitar el problema de circular import
        # Solo se ejecuta cuando realmente necesitamos crear el cliente
        import importlib
        core_module = importlib.import_module('core')
        init_func = getattr(core_module, 'init')
        
        # Crear cliente con la configuración
        api_url_to_use = api_url or "https://api.corebrain.com"
        cb = init_func(
            api_token=api_key,
            db_config=db_config,
            api_url=api_url_to_use,
            skip_verification=True  # No necesitamos verificar token para extraer schema
        )
        
        # Obtener el esquema y cerrar cliente
        schema = cb.db_schema
        cb.close()
        
        return schema
        
    except Exception as e:
        _print_colored(f"Error al extraer esquema con cliente: {str(e)}", "red")
        # Como alternativa, usar extracción directa sin cliente
        return extract_db_schema_direct(db_config)

def extract_schema_to_file(api_key: str, config_id: Optional[str] = None, output_file: Optional[str] = None, api_url: Optional[str] = None) -> bool:
    """
    Extrae el esquema de la base de datos y lo guarda en un archivo.
    
    Args:
        api_key: API Key para identificar la configuración
        config_id: ID de configuración específico (opcional)
        output_file: Ruta al archivo donde guardar el esquema
        api_url: URL opcional de la API
        
    Returns:
        True si se extrae correctamente, False en caso contrario
    """
    try:
    # Importación explícita con try-except para manejar errores
        try:
            from corebrain.config.manager import ConfigManager
        except ImportError as e:
            _print_colored(f"Error al importar ConfigManager: {e}", "red")
            return False
        
        # Obtener las configuraciones disponibles
        config_manager = ConfigManager()
        configs = config_manager.list_configs(api_key)
        
        if not configs:
            _print_colored("No hay configuraciones guardadas para esta API Key.", "yellow")
            return False
            
        selected_config_id = config_id
        
        # Si no se especifica un config_id, mostrar lista para seleccionar
        if not selected_config_id:
            _print_colored("\n=== Configuraciones disponibles ===", "blue")
            for i, conf_id in enumerate(configs, 1):
                print(f"{i}. {conf_id}")
            
            try:
                choice = int(input(f"\nSelecciona una configuración (1-{len(configs)}): ").strip())
                if 1 <= choice <= len(configs):
                    selected_config_id = configs[choice - 1]
                else:
                    _print_colored("Opción inválida.", "red")
                    return False
            except ValueError:
                _print_colored("Por favor, introduce un número válido.", "red")
                return False
        
        # Verificar que el config_id exista
        if selected_config_id not in configs:
            _print_colored(f"No se encontró la configuración con ID: {selected_config_id}", "red")
            return False
        
        # Obtener la configuración seleccionada
        db_config = config_manager.get_config(api_key, selected_config_id)
        
        if not db_config:
            _print_colored(f"Error al obtener la configuración con ID: {selected_config_id}", "red")
            return False
        
        _print_colored(f"\nExtrayendo esquema para configuración: {selected_config_id}", "blue")
        print(f"Tipo: {db_config['type'].upper()}, Motor: {db_config.get('engine', 'No especificado').upper()}")
        print(f"Base de datos: {db_config.get('database', 'No especificada')}")
        
        # Extraer el esquema de la base de datos
        _print_colored("\nExtrayendo esquema de la base de datos...", "blue")
        schema = extract_schema_with_lazy_init(api_key, db_config, api_url)
        
        # Verificar si se obtuvo un esquema válido
        if not schema or not schema.get("tables"):
            _print_colored("No se encontraron tablas/colecciones en la base de datos.", "yellow")
            return False
        
        # Guardar el esquema en un archivo
        output_path = output_file or "db_schema.json"
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(schema, f, indent=2, default=str)
            _print_colored(f"✅ Esquema extraído y guardado en: {output_path}", "green")
        except Exception as e:
            _print_colored(f"❌ Error al guardar el archivo: {str(e)}", "red")
            return False
            
        # Mostrar un resumen de las tablas/colecciones encontradas
        tables = schema.get("tables", {})
        _print_colored(f"\nResumen del esquema extraído: {len(tables)} tablas/colecciones", "green")
        
        for table_name in tables:
            print(f"- {table_name}")
            
        return True
        
    except Exception as e:
        _print_colored(f"❌ Error al extraer esquema: {str(e)}", "red")
        return False

def show_db_schema(api_token: str, config_id: Optional[str] = None, api_url: Optional[str] = None) -> None:
    """
    Muestra el esquema de la base de datos configurada.
    
    Args:
        api_token: Token de API
        config_id: ID de configuración específico (opcional)
        api_url: URL opcional de la API
    """
    try:
        # Importación explícita con try-except para manejar errores
        try:
            from corebrain.config.manager import ConfigManager
        except ImportError as e:
            _print_colored(f"Error al importar ConfigManager: {e}", "red")
            return False
        
        # Obtener las configuraciones disponibles
        config_manager = ConfigManager()
        configs = config_manager.list_configs(api_token)
        
        if not configs:
            _print_colored("No hay configuraciones guardadas para este token.", "yellow")
            return
        
        selected_config_id = config_id
        
        # Si no se especifica un config_id, mostrar lista para seleccionar
        if not selected_config_id:
            _print_colored("\n=== Configuraciones disponibles ===", "blue")
            for i, conf_id in enumerate(configs, 1):
                print(f"{i}. {conf_id}")
            
            try:
                choice = int(input(f"\nSelecciona una configuración (1-{len(configs)}): ").strip())
                if 1 <= choice <= len(configs):
                    selected_config_id = configs[choice - 1]
                else:
                    _print_colored("Opción inválida.", "red")
                    return
            except ValueError:
                _print_colored("Por favor, introduce un número válido.", "red")
                return
        
        # Verificar que el config_id exista
        if selected_config_id not in configs:
            _print_colored(f"No se encontró la configuración con ID: {selected_config_id}", "red")
            return
        
        if config_id and config_id in configs:
            db_config = config_manager.get_config(api_token, config_id)
        else:
            # Obtener la configuración seleccionada
            db_config = config_manager.get_config(api_token, selected_config_id)
            
        if not db_config:
            _print_colored(f"Error al obtener la configuración con ID: {selected_config_id}", "red")
            return
        
        _print_colored(f"\nObteniendo esquema para configuración: {selected_config_id}", "blue")
        _print_colored("Tipo de base de datos:", "blue")
        print(f"  {db_config['type'].upper()}")
        
        if db_config.get('engine'):
            _print_colored("Motor:", "blue")
            print(f"  {db_config['engine'].upper()}")
        
        _print_colored("Base de datos:", "blue")
        print(f"  {db_config.get('database', 'No especificada')}")
        
        # Extraer y mostrar el esquema
        _print_colored("\nExtrayendo esquema de la base de datos...", "blue")
        
        # Intenta conectarse a la base de datos y extraer el esquema
        try:
            
            # Creamos una instancia de Corebrain con la configuración seleccionada
            """
            cb = init(
                api_token=api_token,
                config_id=selected_config_id,
                api_url=api_url,
                skip_verification=True  # Omitimos verificación para simplificar
            )
            """
            
            import importlib
            core_module = importlib.import_module('core.client')
            init_func = getattr(core_module, 'init')
            
            # Creamos una instancia de Corebrain con la configuración seleccionada
            cb = init_func(
                api_token=api_token,
                config_id=config_id,
                api_url=api_url,
                skip_verification=True  # Omitimos verificación para simplificar
            )
            
            # El esquema se extrae automáticamente al inicializar
            schema = get_schema_with_dynamic_import(
                api_token=api_token,
                config_id=selected_config_id,
                db_config=db_config,
                api_url=api_url
            )
            
            # Si no hay esquema, intentamos extraerlo explícitamente
            if not schema or not schema.get("tables"):
                _print_colored("Intentando extraer esquema explícitamente...", "yellow")
                schema = cb._extract_db_schema()
            
            # Cerramos la conexión
            cb.close()
            
        except Exception as conn_error:
            _print_colored(f"Error de conexión: {str(conn_error)}", "red")
            print("Intentando método alternativo...")
            
            # Método alternativo: usar función extract_db_schema directamente
            schema = extract_db_schema(db_config)
        
        # Verificar si se obtuvo un esquema válido
        if not schema or not schema.get("tables"):
            _print_colored("No se encontraron tablas/colecciones en la base de datos.", "yellow")
            
            # Información adicional para ayudar a diagnosticar el problema
            print("\nInformación de depuración:")
            print(f"  Tipo de base de datos: {db_config.get('type', 'No especificado')}")
            print(f"  Motor: {db_config.get('engine', 'No especificado')}")
            print(f"  Host: {db_config.get('host', 'No especificado')}")
            print(f"  Puerto: {db_config.get('port', 'No especificado')}")
            print(f"  Base de datos: {db_config.get('database', 'No especificado')}")
            
            # Para PostgreSQL, sugerir verificar el esquema
            if db_config.get('engine') == 'postgresql':
                print("\nPara PostgreSQL, verifica que las tablas existan en el esquema 'public' o")
                print("que tengas acceso a los esquemas donde están las tablas.")
                print("Puedes verificar los esquemas disponibles con: SELECT DISTINCT table_schema FROM information_schema.tables;")
            
            return
        
        # Mostrar información del esquema
        tables = schema.get("tables", {})
        
        # Separar tablas SQL y colecciones NoSQL para mostrarlas apropiadamente
        sql_tables = {}
        nosql_collections = {}
        
        for name, info in tables.items():
            if "columns" in info:
                sql_tables[name] = info
            elif "fields" in info:
                nosql_collections[name] = info
        
        # Mostrar tablas SQL
        if sql_tables:
            _print_colored(f"\nSe encontraron {len(sql_tables)} tablas SQL:", "green")
            for table_name, table_info in sql_tables.items():
                _print_colored(f"\n=== Tabla: {table_name} ===", "bold")
                
                # Mostrar columnas
                columns = table_info.get("columns", [])
                if columns:
                    _print_colored("Columnas:", "blue")
                    for column in columns:
                        print(f"  - {column['name']} ({column['type']})")
                else:
                    _print_colored("No se encontraron columnas.", "yellow")
                
                # Mostrar muestra de datos si está disponible
                sample_data = table_info.get("sample_data", [])
                if sample_data:
                    _print_colored("\nMuestra de datos:", "blue")
                    for i, row in enumerate(sample_data[:2], 1):  # Limitar a 2 filas para simplificar
                        print(f"  Registro {i}: {row}")
                    
                    if len(sample_data) > 2:
                        print(f"  ... ({len(sample_data) - 2} registros más)")
        
        # Mostrar colecciones NoSQL
        if nosql_collections:
            _print_colored(f"\nSe encontraron {len(nosql_collections)} colecciones NoSQL:", "green")
            for coll_name, coll_info in nosql_collections.items():
                _print_colored(f"\n=== Colección: {coll_name} ===", "bold")
                
                # Mostrar campos
                fields = coll_info.get("fields", [])
                if fields:
                    _print_colored("Campos:", "blue")
                    for field in fields:
                        print(f"  - {field['name']} ({field['type']})")
                else:
                    _print_colored("No se encontraron campos.", "yellow")
                
                # Mostrar muestra de datos si está disponible
                sample_data = coll_info.get("sample_data", [])
                if sample_data:
                    _print_colored("\nMuestra de datos:", "blue")
                    for i, doc in enumerate(sample_data[:2], 1):  # Limitar a 2 documentos
                        # Simplificar la visualización para documentos grandes
                        if isinstance(doc, dict) and len(doc) > 5:
                            simplified = {k: doc[k] for k in list(doc.keys())[:5]}
                            print(f"  Documento {i}: {simplified} ... (y {len(doc) - 5} campos más)")
                        else:
                            print(f"  Documento {i}: {doc}")
                    
                    if len(sample_data) > 2:
                        print(f"  ... ({len(sample_data) - 2} documentos más)")
        
        _print_colored("\n✅ Esquema extraído correctamente!", "green")
        
        # Preguntar si quiere guardar el esquema en un archivo
        save_option = input("\n¿Deseas guardar el esquema en un archivo? (s/n): ").strip().lower()
        if save_option == "s":
            filename = input("Nombre del archivo (por defecto: db_schema.json): ").strip() or "db_schema.json"
            try:
                with open(filename, 'w') as f:
                    json.dump(schema, f, indent=2, default=str)
                _print_colored(f"\n✅ Esquema guardado en: {filename}", "green")
            except Exception as e:
                _print_colored(f"❌ Error al guardar el archivo: {str(e)}", "red")
    
    except Exception as e:
        _print_colored(f"❌ Error al mostrar el esquema: {str(e)}", "red")
        import traceback
        traceback.print_exc()


def get_schema_with_dynamic_import(api_token: str, config_id: str, db_config: Dict[str, Any], api_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Obtiene el esquema de la base de datos usando importación dinámica.
    
    Args:
        api_token: Token de API
        config_id: ID de configuración
        db_config: Configuración de la base de datos
        api_url: URL opcional de la API
        
    Returns:
        Esquema de la base de datos
    """
    try:
        # Importación dinámica del módulo core
        import importlib
        core_module = importlib.import_module('core.client')
        init_func = getattr(core_module, 'init')
        
        # Creamos una instancia de Corebrain con la configuración seleccionada
        cb = init_func(
            api_token=api_token,
            config_id=config_id,
            api_url=api_url,
            skip_verification=True  # Omitimos verificación para simplificar
        )
        
        # El esquema se extrae automáticamente al inicializar
        schema = cb.db_schema
        
        # Si no hay esquema, intentamos extraerlo explícitamente
        if not schema or not schema.get("tables"):
            _print_colored("Intentando extraer esquema explícitamente...", "yellow")
            schema = cb._extract_db_schema()
        
        # Cerramos la conexión
        cb.close()
        
        return schema
    
    except ImportError:
        # Si falla la importación dinámica, intentamos un enfoque alternativo
        _print_colored("No se pudo importar el cliente. Usando método alternativo.", "yellow")
        return extract_db_schema(db_config)
    
    except Exception as e:
        _print_colored(f"Error al extraer esquema con cliente: {str(e)}", "red")
        # Fallback a extracción directa
        return extract_db_schema(db_config)