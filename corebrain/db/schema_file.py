"""
Components for extracting and optimizing database schemas.
"""
import json

from typing import Dict, Any, Optional

def _print_colored(message: str, color: str) -> None:
    """Simplified version of _print_colored that doesn't depend on cli.utils."""
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
    Extracts the database schema directly without using the SDK.
    
    Args:
        db_config: Database configuration
    
    Returns:
        Dictionary with the database structure organized by tables/collections
    """
    db_type = db_config["type"].lower()
    schema = {
        "type": db_type,
        "database": db_config.get("database", ""),
        "tables": {}  # Changed to dictionary for direct table access by name
    }
    
    try:
        if db_type == "sql":
            pass
        
        # Handle both "nosql" and "mongodb" as valid types
        elif db_type == "nosql" or db_type == "mongodb":
            import pymongo
            
            # Determine the engine (if it exists)
            engine = db_config.get("engine", "").lower()
            
            # If the engine is not specified or is mongodb, proceed
            if not engine or engine == "mongodb":
                if "connection_string" in db_config:
                    client = pymongo.MongoClient(db_config["connection_string"])
                else:
                    # Dictionary of parameters for MongoClient
                    mongo_params = {
                        "host": db_config.get("host", "localhost"),
                        "port": db_config.get("port", 27017)
                    }
                    
                    # Add credentials only if they are present
                    if db_config.get("user"):
                        mongo_params["username"] = db_config["user"]
                    if db_config.get("password"):
                        mongo_params["password"] = db_config["password"]
                    
                    client = pymongo.MongoClient(**mongo_params)
                
                # Get the database
                db_name = db_config.get("database", "")
                if not db_name:
                    _print_colored("⚠️ Database name not specified", "yellow")
                    return schema
                
                try:
                    db = client[db_name]
                    collection_names = db.list_collection_names()
                    
                    # Process collections
                    for collection_name in collection_names:
                        collection = db[collection_name]
                        
                        # Get several sample documents  
                        try:
                            sample_docs = list(collection.find().limit(5))
                            
                            # Extract field structure from documents
                            field_types = {}
                            
                            for doc in sample_docs:
                                for field, value in doc.items():
                                    if field != "_id":  # Ignore the _id of MongoDB
                                        # Update the type if it doesn't exist or combine if there are different types
                                        field_type = type(value).__name__
                                        if field not in field_types:
                                            field_types[field] = field_type
                                        elif field_types[field] != field_type:
                                            field_types[field] = f"{field_types[field]}|{field_type}"
                            
                            # Convert to expected format
                            fields = [{"name": field, "type": type_name} for field, type_name in field_types.items()]
                            
                            # Convert documents to serializable format
                            sample_data = []
                            for doc in sample_docs:
                                serialized_doc = {}
                                for key, value in doc.items():
                                    if key == "_id":
                                        serialized_doc[key] = str(value)
                                    elif isinstance(value, (dict, list)):
                                        serialized_doc[key] = str(value)  # Simplify nested objects
                                    else:
                                        serialized_doc[key] = value
                                sample_data.append(serialized_doc)
                            
                            # Save collection information
                            schema["tables"][collection_name] = {
                                "fields": fields,
                                "sample_data": sample_data
                            }
                        except Exception as e:
                            _print_colored(f"Error processing collection {collection_name}: {str(e)}", "red")
                            schema["tables"][collection_name] = {
                                "fields": [],
                                "sample_data": [],
                                "error": str(e)
                            }
                
                except Exception as e:
                    _print_colored(f"Error accessing MongoDB database '{db_name}': {str(e)}", "red")
                
                finally:
                    # Close the connection
                    client.close()
            else:
                _print_colored(f"Database engine not supported: {engine}", "red")
        
        # Convert the dictionary of tables to a list to maintain compatibility with the previous format
        table_list = []
        for table_name, table_info in schema["tables"].items():
            table_data = {"name": table_name}
            table_data.update(table_info)
            table_list.append(table_data)
        
        # Save the list of tables to maintain compatibility
        schema["tables_list"] = table_list
        
        return schema
    
    except Exception as e:
        _print_colored(f"Error extracting database schema: {str(e)}", "red")
        # In case of error, return an empty schema
        return {"type": db_type, "tables": {}, "tables_list": []}

def extract_db_schema_direct(db_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts the schema directly without using the Corebrain client.
    This is a reduced version that doesn't require importing core.
    """
    db_type = db_config["type"].lower()
    schema = {
        "type": db_type,
        "database": db_config.get("database", ""),
        "tables": {},
        "tables_list": []  # Initially empty list
    }
    
    try:
        # [Existing implementation to extract schema without using Corebrain]
        # Add function to extract schema without using Corebrain

        return schema
    except Exception as e:
        _print_colored(f"Error extracting schema directly: {str(e)}", "red")
        return {"type": db_type, "tables": {}, "tables_list": []}

def extract_schema_with_lazy_init(api_key: str, db_config: Dict[str, Any], api_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Extracts the schema using late import of the client.
    
    This function avoids the circular import issue by dynamically loading 
    the Corebrain client only when necessary.
    """
    try:
        # The import is moved here to avoid the circular import problem
        # It is only executed when we really need to create the client
        import importlib
        core_module = importlib.import_module('core')
        init_func = getattr(core_module, 'init')
        
        # Create client with the configuration
        api_url_to_use = api_url or "https://api.etedata.com"
        cb = init_func(
            api_token=api_key,
            db_config=db_config,
            api_url=api_url_to_use,
            skip_verification=True  # We don't need to verify token to extract schema
        )
        
        # Get the schema and close the client
        schema = cb.db_schema
        cb.close()
        
        return schema
        
    except Exception as e:
        _print_colored(f"Error extracting schema with client: {str(e)}", "red")
        # As an alternative, use direct extraction without client
        return extract_db_schema_direct(db_config)
from typing import Dict, Any

def test_connection(db_config: Dict[str, Any]) -> bool:
    try:
        if db_config["type"].lower() == "sql":
            # Code to test SQL connection...
            pass
        elif db_config["type"].lower() == "nosql":
            if db_config["engine"].lower() == "mongodb":
                import pymongo
            else:
                raise ValueError(f"Unsupported NoSQL engine: {db_config['engine']}")
            
            # Create MongoDB client
            client = pymongo.MongoClient(db_config["connection_string"])
            client.admin.command('ping')  # Test connection
            
            return True
        else:
            _print_colored("Unsupported database type.", "red")
            return False
    except Exception as e:
        _print_colored(f"Failed to connect to the database: {str(e)}", "red")
        return False

def extract_schema_to_file(api_key: str, config_id: Optional[str] = None, output_file: Optional[str] = None, api_url: Optional[str] = None) -> bool:
    """
    Extracts the database schema and saves it to a file.
    
    Args:
        api_key: API Key to identify the configuration
        config_id: Specific configuration ID (optional)
        output_file: Path to the file where the schema will be saved
        api_url: Optional API URL
        
    Returns:
        True if extraction is successful, False otherwise
    """
    try:
    # Importación explícita con try-except para manejar errores
        try:
            from corebrain.config.manager import ConfigManager
        except ImportError as e:
            _print_colored(f"Error importing ConfigManager: {e}", "red")
            return False
        
        # Get the available configurations
        config_manager = ConfigManager()
        configs = config_manager.list_configs(api_key)
        
        if not configs:
            _print_colored("No configurations saved for this API Key.", "yellow")
            return False
            
        selected_config_id = config_id
        
        # If no config_id is specified, show list to select
        if not selected_config_id:
            _print_colored("\n=== Available configurations ===", "blue")
            for i, conf_id in enumerate(configs, 1):
                print(f"{i}. {conf_id}")
            
            try:
                choice = int(input(f"\nSelect a configuration (1-{len(configs)}): ").strip())
                if 1 <= choice <= len(configs):
                    selected_config_id = configs[choice - 1]
                else:
                    _print_colored("Invalid option.", "red")
                    return False
            except ValueError:
                _print_colored("Please enter a valid number.", "red")
                return False
        
        # Verify that the config_id exists
        if selected_config_id not in configs:
            _print_colored(f"No configuration found with ID: {selected_config_id}", "red")
            return False
        
        # Get the selected configuration
        db_config = config_manager.get_config(api_key, selected_config_id)
        
        if not db_config:
            _print_colored(f"Error getting configuration with ID: {selected_config_id}", "red")
            return False
        
        _print_colored(f"\nExtracting schema for configuration: {selected_config_id}", "blue")
        print(f"Type: {db_config['type'].upper()}, Engine: {db_config.get('engine', 'No specified').upper()}")
        print(f"Database: {db_config.get('database', 'No specified')}")
        
        # Extract the schema from the database
        _print_colored("\nExtracting schema from the database...", "blue")
        schema = extract_schema_with_lazy_init(api_key, db_config, api_url)
        
        # Verify if a valid schema was obtained
        if not schema or not schema.get("tables"):
            _print_colored("No tables/collections found in the database.", "yellow")
            return False
        
        # Save the schema in a file
        output_path = output_file or "db_schema.json"
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(schema, f, indent=2, default=str)
            _print_colored(f"✅ Schema extracted and saved in: {output_path}", "green")
        except Exception as e:
            _print_colored(f"❌ Error saving the file: {str(e)}", "red")
            return False
            
        # Show a summary of the tables/collections found
        tables = schema.get("tables", {})
        _print_colored(f"\nSummary of the extracted schema: {len(tables)} tables/collections", "green")
        
        for table_name in tables:
            print(f"- {table_name}")
            
        return True
        
    except Exception as e:
        _print_colored(f"❌ Error extracting schema: {str(e)}", "red")
        return False

def show_db_schema(api_token: str, config_id: Optional[str] = None, api_url: Optional[str] = None) -> None:
    """
    Displays the schema of the configured database.
    
    Args:
        api_token: API token
        config_id: Specific configuration ID (optional)
        api_url: Optional API URL
    """
    try:
        # Explicit import with try-except to handle errors
        try:
            from corebrain.config.manager import ConfigManager
        except ImportError as e:
            _print_colored(f"Error importing ConfigManager: {e}", "red")
            return False
        
        # Get the available configurations
        config_manager = ConfigManager()
        configs = config_manager.list_configs(api_token)
        
        if not configs:
            _print_colored("No configurations saved for this token.", "yellow")
            return
        
        selected_config_id = config_id
        
        # If no config_id is specified, show list to select
        if not selected_config_id:
            _print_colored("\n=== Available configurations ===", "blue")
            for i, conf_id in enumerate(configs, 1):
                print(f"{i}. {conf_id}")
            
            try:
                choice = int(input(f"\nSelect a configuration (1-{len(configs)}): ").strip())
                if 1 <= choice <= len(configs): 
                    selected_config_id = configs[choice - 1]
                else:
                    _print_colored("Invalid option.", "red")
                    return
            except ValueError:
                _print_colored("Please enter a valid number.", "red")
                return
        
        # Verify that the config_id exists
        if selected_config_id not in configs:
            _print_colored(f"No configuration found with ID: {selected_config_id}", "red")
            return
        
        if config_id and config_id in configs:
            db_config = config_manager.get_config(api_token, config_id)
        else:
            # Get the selected configuration
            db_config = config_manager.get_config(api_token, selected_config_id)
            
        if not db_config:
            _print_colored(f"Error getting configuration with ID: {selected_config_id}", "red")
            return
        
        _print_colored(f"\nGetting schema for configuration: {selected_config_id}", "blue")
        _print_colored("Database type:", "blue")
        print(f"  {db_config['type'].upper()}")
        
        if db_config.get('engine'):
            _print_colored("Motor:", "blue")
            print(f"  {db_config['engine'].upper()}")
        
        _print_colored("Database:", "blue")
        print(f"  {db_config.get('database', 'No specified')}")
        
        # Extract and show the schema
        _print_colored("\nExtracting schema from the database...", "blue")
        
        # Try to connect to the database and extract the schema
        try:
            
            # Create a Corebrain instance with the selected configuration
            """
            cb = init(
                api_token=api_token,
                config_id=selected_config_id,
                api_url=api_url,
                skip_verification=True  # Skip verification for simplicity
            )
            """
            
            import importlib
            core_module = importlib.import_module('core.client')
            init_func = getattr(core_module, 'init')
            
            # Create a Corebrain instance with the selected configuration
            cb = init_func(
                api_token=api_token,
                config_id=config_id,
                api_url=api_url,
                skip_verification=True  # Skip verification for simplicity
            )
            
            # The schema is extracted automatically when initializing
            schema = get_schema_with_dynamic_import(
                api_token=api_token,
                config_id=selected_config_id,
                db_config=db_config,
                api_url=api_url
            )
            
            # If there is no schema, try to extract it explicitly
            if not schema or not schema.get("tables"):
                _print_colored("Trying to extract schema explicitly...", "yellow")
                schema = cb._extract_db_schema()
            
            # Close the connection
            cb.close()
            
        except Exception as conn_error:
            _print_colored(f"Connection error: {str(conn_error)}", "red")
            print("Trying alternative method...")
            
            # Alternative method: use extract_db_schema directly
            schema = extract_db_schema(db_config)
        
        # Verify if a valid schema was obtained
        if not schema or not schema.get("tables"):
            _print_colored("No tables/collections found in the database.", "yellow")
            
            # Additional information to help diagnose the problem
            print("\nDebug information:")
            print(f"  Database type: {db_config.get('type', 'No specified')}")
            print(f"  Engine: {db_config.get('engine', 'No specified')}")
            print(f"  Host: {db_config.get('host', 'No specified')}")
            print(f"  Port: {db_config.get('port', 'No specified')}")
            print(f"  Database: {db_config.get('database', 'No specified')}")
            
            # For PostgreSQL, suggest verifying the schema
            if db_config.get('engine') == 'postgresql':
                print("\nFor PostgreSQL, verify that the tables exist in the 'public' schema or")
                print("that you have access to the schemas where the tables are.")
                print("You can verify the available schemas with: SELECT DISTINCT table_schema FROM information_schema.tables;")
            
            return
        
        # Show schema information
        tables = schema.get("tables", {})
        
        # Separate SQL tables and NoSQL collections to show them appropriately
        sql_tables = {}
        nosql_collections = {}
        
        for name, info in tables.items():
            if "columns" in info:
                sql_tables[name] = info
            elif "fields" in info:
                nosql_collections[name] = info
        
        # Show SQL tables
        if sql_tables:
            _print_colored(f"\nFound {len(sql_tables)} SQL tables:", "green")
            for table_name, table_info in sql_tables.items():
                _print_colored(f"\n=== Table: {table_name} ===", "bold")
                
                # Show columns
                columns = table_info.get("columns", [])
                if columns:
                    _print_colored("Columns:", "blue")
                    for column in columns:
                        print(f"  - {column['name']} ({column['type']})")
                else:
                    _print_colored("No columns found.", "yellow")
                
                # Show sample data if available
                sample_data = table_info.get("sample_data", [])
                if sample_data:
                    _print_colored("\nData sample:", "blue")
                    for i, row in enumerate(sample_data[:2], 1):  # Limitar a 2 filas para simplificar
                        print(f"  Record {i}: {row}")
                    
                    if len(sample_data) > 2:
                        print(f"  ... ({len(sample_data) - 2} more records)")
        
        # Show NoSQL collections
        if nosql_collections:
            _print_colored(f"\nFound {len(nosql_collections)} NoSQL collections:", "green")
            for coll_name, coll_info in nosql_collections.items():
                _print_colored(f"\n=== Collection: {coll_name} ===", "bold")
                
                # Show fields
                fields = coll_info.get("fields", [])
                if fields:
                    _print_colored("Fields:", "blue")
                    for field in fields:
                        print(f"  - {field['name']} ({field['type']})")
                else:
                    _print_colored("No fields found.", "yellow")
                
                # Show sample data if available
                sample_data = coll_info.get("sample_data", [])
                if sample_data:
                    _print_colored("\nData sample:", "blue")
                    for i, doc in enumerate(sample_data[:2], 1):  # Limit to 2 documents
                        # Simplify the visualization for large documents
                        if isinstance(doc, dict) and len(doc) > 5:
                            simplified = {k: doc[k] for k in list(doc.keys())[:5]}
                            print(f"  Document {i}: {simplified} ... (and {len(doc) - 5} more fields)")
                        else:
                            print(f"  Document {i}: {doc}")
                    
                    if len(sample_data) > 2:
                        print(f"  ... ({len(sample_data) - 2} more documents)")
        
        _print_colored("\n✅ Schema extracted correctly!", "green")
        
        # Ask if you want to save the schema in a file
        save_option = input("\nDo you want to save the schema in a file? (s/n): ").strip().lower()
        if save_option == "s":
            filename = input("File name (default: db_schema.json): ").strip() or "db_schema.json"
            try:
                with open(filename, 'w') as f:
                    json.dump(schema, f, indent=2, default=str)
                _print_colored(f"\n✅ Schema saved in: {filename}", "green")
            except Exception as e:
                _print_colored(f"❌ Error saving the file: {str(e)}", "red")
    
    except Exception as e:
        _print_colored(f"❌ Error showing the schema: {str(e)}", "red")
        import traceback
        traceback.print_exc()


def get_schema_with_dynamic_import(api_token: str, config_id: str, db_config: Dict[str, Any], api_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves the database schema using dynamic import.
    
    Args:
        api_token: API token
        config_id: Configuration ID
        db_config: Database configuration
        api_url: Optional API URL
        
    Returns:
        Database schema
    """
    try:
        # Importación dinámica del módulo core
        import importlib
        core_module = importlib.import_module('core.client')
        init_func = getattr(core_module, 'init')
        
        # Create a Corebrain instance with the selected configuration
        cb = init_func(
            api_token=api_token,
            config_id=config_id,
            api_url=api_url,
            skip_verification=True  # Skip verification for simplicity
        )
        
        # The schema is extracted automatically when initializing
        schema = cb.db_schema
        
        # If there is no schema, try to extract it explicitly
        if not schema or not schema.get("tables"):
            _print_colored("Trying to extract schema explicitly...", "yellow")
            schema = cb._extract_db_schema()
        
        # Close the connection
        cb.close()
        
        return schema
    
    except ImportError:
        # If dynamic import fails, try an alternative approach
        _print_colored("Could not import the client. Using alternative method.", "yellow")
        return extract_db_schema(db_config)
    
    except Exception as e:
        _print_colored(f"Error extracting schema with client: {str(e)}", "red")
        # Fallback to direct extraction
        return extract_db_schema(db_config)
