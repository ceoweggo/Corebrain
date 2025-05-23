"""
Configuration functions for the CLI.
"""
import json
import uuid
import getpass
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from corebrain.cli.common import DEFAULT_API_URL, DEFAULT_SSO_URL
from corebrain.cli.auth.sso import authenticate_with_sso, authenticate_with_sso_and_api_key_request
from corebrain.cli.utils import print_colored, ProgressTracker
from corebrain.db.engines import get_available_engines
from corebrain.config.manager import ConfigManager
from corebrain.network.client import http_session
from corebrain.core.test_utils import test_natural_language_query
from corebrain.db.schema_file import extract_db_schema

def get_api_credential(args_token: Optional[str] = None, sso_url: Optional[str] = None) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
    """
    Obtains the API credential (API key), trying several methods in order:
    1. Token provided as argument
    2. Environment variable
    3. SSO authentication
    4. Manual user input
    
    Args:
        args_token: Token provided as argument
        sso_url: SSO service URL
        
    Returns:
        Tuple with (api_key, user_data, api_token) or (None, None, None) if couldn't be obtained
        - api_key: API key to use with SDK
        - user_data: User data
        - api_token: API token for general authentication
    """
    # 1. Check if provided as argument
    if args_token:
        print_colored("Using token provided as argument.", "blue")
        # Assume the provided token is directly an API key
        return args_token, None, args_token
    
    # 2. Check environment variable for API key
    env_api_key = os.environ.get("COREBRAIN_API_KEY")
    if env_api_key:
        print_colored("Using API key from COREBRAIN_API_KEY environment variable.", "blue")
        return env_api_key, None, env_api_key
    
    # 3. Check environment variable for API token
    env_api_token = os.environ.get("COREBRAIN_API_TOKEN")
    if env_api_token:
        print_colored("Using API token from COREBRAIN_API_TOKEN environment variable.", "blue")
        # Note: Here we return the same value as api_key and api_token
        # because we have no way to obtain a specific api_key
        return env_api_token, None, env_api_token
    
    # 4. Try SSO authentication
    print_colored("Attempting authentication via SSO...", "blue")
    api_key, user_data, api_token = authenticate_with_sso_and_api_key_request(sso_url or DEFAULT_SSO_URL)
    print("Exit from authenticate_with_sso: ", datetime.now())
    if api_key:
        # Save for future use
        os.environ["COREBRAIN_API_KEY"] = api_key
        os.environ["COREBRAIN_API_TOKEN"] = api_token
        return api_key, user_data, api_token
    
    # 5. Request manually
    print_colored("\nCouldn't complete SSO authentication.", "yellow")
    print_colored("You can directly enter an API key:", "blue")
    manual_input = input("Enter your Corebrain API key: ").strip()
    if manual_input:
        # Assume manual input is an API key
        return manual_input, None, manual_input
    
    # If we got here, we couldn't get a credential
    return None, None, None

def get_db_type() -> str:
    """
    Prompts the user to select a database type.
    
    Returns:
        Selected database type
    """
    print_colored("\n=== Select the database type ===", "blue")
    print("1. SQL (SQLite, MySQL, PostgreSQL)")
    print("2. NoSQL (MongoDB)")
    
    while True:
        try:
            choice = int(input("\nSelect an option (1-2): ").strip())
            if choice == 1:
                return "sql"
            elif choice == 2:
                return "nosql"
            else:
                print_colored("Invalid option. Try again.", "red")
        except ValueError:
            print_colored("Please enter a number.", "red")

def get_db_engine(db_type: str) -> str:
    """
    Prompts the user to select a database engine.
    
    Args:
        db_type: Selected database type
        
    Returns:
        Selected database engine
    """
    engines = get_available_engines()
    
    if db_type == "sql":
        available_engines = engines["sql"]
        print_colored("\n=== Select the SQL engine ===", "blue")
        for i, engine in enumerate(available_engines, 1):
            print(f"{i}. {engine.capitalize()}")
        
        while True:
            try:
                choice = int(input(f"\nSelect an option (1-{len(available_engines)}): ").strip())
                if 1 <= choice <= len(available_engines):
                    return available_engines[choice - 1]
                else:
                    print_colored("Invalid option. Try again.", "red")
            except ValueError:
                print_colored("Please enter a number.", "red")
    else:
        # For NoSQL, we only have MongoDB for now
        return "mongodb"

def get_connection_params(db_type: str, engine: str) -> Dict[str, Any]:
    """
    Prompts for connection parameters according to the database type and engine.
    
    Args:
        db_type: Database type
        engine: Database engine
        
    Returns:
        Dictionary with connection parameters
    """
    params = {"type": db_type, "engine": engine}
    
    # Specific parameters by type and engine
    if db_type == "sql":
        if engine == "sqlite":
            path = input("\nPath to SQLite database file: ").strip()
            params["database"] = path
        else:
            # MySQL or PostgreSQL
            print_colored("\n=== Connection Parameters ===", "blue")
            params["host"] = input("Host (default: localhost): ").strip() or "localhost"
            
            if engine == "mysql":
                params["port"] = int(input("Port (default: 3306): ").strip() or "3306")
            else:  # PostgreSQL
                params["port"] = int(input("Port (default: 5432): ").strip() or "5432")
                
            params["user"] = input("User: ").strip()
            params["password"] = getpass.getpass("Password: ")
            params["database"] = input("Database name: ").strip()
    else:
        # MongoDB
        print_colored("\n=== MongoDB Connection Parameters ===", "blue")
        use_connection_string = input("Use connection string? (y/n): ").strip().lower() == "y"
        
        if use_connection_string:
            params["connection_string"] = input("MongoDB connection string: ").strip()
        else:
            params["host"] = input("Host (default: localhost): ").strip() or "localhost"
            params["port"] = int(input("Port (default: 27017): ").strip() or "27017")
            
            use_auth = input("Use authentication? (y/n): ").strip().lower() == "y"
            if use_auth:
                params["user"] = input("User: ").strip()
                params["password"] = getpass.getpass("Password: ")
                
        params["database"] = input("Database name: ").strip()
    
    # Add configuration ID
    params["config_id"] = str(uuid.uuid4())
    params["excluded_tables"] = []
    
    return params

def test_database_connection(api_token: str, db_config: Dict[str, Any], api_url: Optional[str] = None, user_data: Optional[Dict[str, Any]] = None) -> bool:
    """
    Tests the database connection without verifying the API token.
    
    Args:
        api_token: API token
        db_config: Database configuration
        api_url: Optional API URL
        user_data: User data
        
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        print_colored("\nTesting database connection...", "blue")
        
        db_type = db_config["type"].lower()
        engine = db_config.get("engine", "").lower()
        
        if db_type == "sql":
            if engine == "sqlite":
                import sqlite3
                conn = sqlite3.connect(db_config.get("database", ""))
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                conn.close()
            
            elif engine == "mysql":
                import mysql.connector
                if "connection_string" in db_config:
                    conn = mysql.connector.connect(connection_string=db_config["connection_string"])
                else:
                    conn = mysql.connector.connect(
                        host=db_config.get("host", "localhost"),
                        user=db_config.get("user", ""),
                        password=db_config.get("password", ""),
                        database=db_config.get("database", ""),
                        port=db_config.get("port", 3306)
                    )
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                conn.close()
            
            elif engine == "postgresql":
                import psycopg2
                if "connection_string" in db_config:
                    conn = psycopg2.connect(db_config["connection_string"])
                else:
                    conn = psycopg2.connect(
                        host=db_config.get("host", "localhost"),
                        user=db_config.get("user", ""),
                        password=db_config.get("password", ""),
                        dbname=db_config.get("database", ""),
                        port=db_config.get("port", 5432)
                    )
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                conn.close()
        
        elif db_type == "nosql" and engine == "mongodb":
            import pymongo
            if "connection_string" in db_config:
                client = pymongo.MongoClient(db_config["connection_string"])
            else:
                client = pymongo.MongoClient(
                    host=db_config.get("host", "localhost"),
                    port=db_config.get("port", 27017),
                    username=db_config.get("user"),
                    password=db_config.get("password")
                )
            
            # Verify connection by trying to access the database
            db = client[db_config["database"]]
            # List collections to verify we can access
            _ = db.list_collection_names()
            client.close()
        
        # If we got here, the connection was successful
        print_colored("✅ Database connection successful!", "green")
        return True
    except Exception as e:
        print_colored(f"❌ Error connecting to the database: {str(e)}", "red")
        return False
  
def select_excluded_tables(api_token: str, db_config: Dict[str, Any], api_url: Optional[str] = None, user_data: Optional[Dict[str, Any]] = None) -> List[str]:

    """
    Allows the user to select tables/collections to exclude.
    
    Args:
        api_token: API token
        db_config: Database configuration
        api_url: Optional API URL
        user_data: User data
        
    Returns:
        List of excluded tables/collections
    """
    print_colored("\nRetrieving database schema...", "blue")
    
    # Get the database schema directly
    schema = extract_db_schema(db_config)
    
    if not schema or not schema.get("tables"):
        print_colored("No tables/collections found.", "yellow")
        return []
    
    print_colored("\n=== Tables/Collections found ===", "blue")
    print("Mark with 'n' the tables that should NOT be accessible (y for accessible)")
    
    # Use the tables list instead of the dictionary
    tables_list = schema.get("tables_list", [])
    excluded_tables = []
    
    if not tables_list:
        # If there's no table list, convert the tables dictionary to a list
        tables = schema.get("tables", {})
        for table_name in tables:
            choice = input(f"{table_name} (accessible? y/n): ").strip().lower()
            if choice == "n":
                excluded_tables.append(table_name)
    else:
        # If there's a table list, use it directly
        for i, table in enumerate(tables_list, 1):
            table_name = table["name"]
            choice = input(f"{i}. {table_name} (accessible? y/n): ").strip().lower()
            if choice == "n":
                excluded_tables.append(table_name)
    
    print_colored(f"\n{len(excluded_tables)} tables/collections have been excluded", "green")
    return excluded_tables

def save_configuration(sso_token: str, api_key: str, db_config: Dict[str, Any], api_url: Optional[str] = None) -> bool:
    """
    Saves the configuration locally and syncs it with the API server.
    
    Args:
        sso_token: SSO authentication token
        api_key: API Key to identify the configuration
        db_config: Database configuration
        api_url: Optional API URL
        
    Returns:
        True if saved correctly, False otherwise
    """
    config_id = db_config.get("config_id")
    if not config_id:
        config_id = str(uuid.uuid4())
        db_config["config_id"] = config_id
    
    print_colored(f"\nSaving configuration with ID: {config_id}...", "blue")
    
    try:
        config_manager = ConfigManager()
        config_manager.add_config(api_key, db_config, config_id)
        
        # 2. Verify that the configuration was saved locally
        saved_config = config_manager.get_config(api_key, config_id)
        if not saved_config:
            print_colored("⚠️ Could not verify local saving of configuration", "yellow")
        else:
            print_colored("✅ Configuration saved locally successfully", "green")
        
        # 3. Try to sync with the server
        try:
            if api_url:
                print_colored("Syncing configuration with server...", "blue")
                
                # Prepare URL
                if not api_url.startswith(("http://", "https://")):
                    api_url = "https://" + api_url
                
                if api_url.endswith('/'):
                    api_url = api_url[:-1]
                
                # Endpoint to update API key
                endpoint = f"{api_url}/api/auth/api-keys/{api_key}"
                
                # Create ApiKeyUpdate object according to your model
                update_data = {
                    "metadata": {
                        "config_id": config_id,
                        "db_config": db_config,
                        "corebrain_sdk": {
                            "version": "1.0.0",
                            "updated_at": datetime.now().isoformat()
                        }
                    }
                }
   
                print_colored(f"Updating API key with ID: {api_key}", "blue")
                
                # Send to server
                headers = {
                    "Authorization": f"Bearer {sso_token}",
                    "Content-Type": "application/json"
                }
         
                response = http_session.put(
                    endpoint,
                    headers=headers,
                    json=update_data,
                    timeout=5.0
                )
                
                if response.status_code in [200, 201, 204]:
                    print_colored("✅ Configuration successfully synced with server", "green")
                else:
                    print_colored(f"⚠️ Error syncing with server (Code: {response.status_code})", "yellow")
                    print_colored(f"Response: {response.text[:200]}...", "yellow")
            
        except Exception as e:
            print_colored(f"⚠️ Error syncing with server: {str(e)}", "yellow")
            print_colored("The configuration is still saved locally", "green")
        
        return True
        
    except Exception as e:
        print_colored(f"❌ Error saving configuration: {str(e)}", "red")
        return False

def configure_sdk(api_token: str, api_key: str, api_url: Optional[str] = None, sso_url: Optional[str] = None, user_data: Optional[Dict[str, Any]] = None) -> None:
    """
    Configures the Corebrain SDK with a step-by-step wizard.
    
    Args:
        api_token: API token for general authentication (obtained from SSO)
        api_key: Specific API key selected to use with the SDK
        api_url: Corebrain API URL
        sso_url: Globodain SSO service URL
        user_data: User data obtained from SSO
    """
    # Ensure default values for URLs
    api_url = api_url or DEFAULT_API_URL
    sso_url = sso_url or DEFAULT_SSO_URL
    
    print_colored("\n=== COREBRAIN SDK CONFIGURATION WIZARD ===", "bold")
    
    # PHASE 1-3: Already completed - User authentication
    
    # PHASE 4: Select database type
    print_colored("\n2. Selecting database type...", "blue")
    db_type = get_db_type()
    
    # PHASE 4: Select database engine
    print_colored("\n3. Selecting database engine...", "blue")
    engine = get_db_engine(db_type)
    
    # PHASE 5: Configure connection parameters
    print_colored("\n4. Configuring connection parameters...", "blue")
    db_config = get_connection_params(db_type, engine)
    
    # PHASE 5: Verify database connection
    print_colored("\n5. Verifying database connection...", "blue")
    if not test_database_connection(api_key, db_config, api_url, user_data):
        print_colored("❌ Configuration not completed due to connection errors.", "red")
        return
    
    # PHASE 6: Define non-accessible tables/collections
    print_colored("\n6. Defining non-accessible tables/collections...", "blue")
    excluded_tables = select_excluded_tables(api_key, db_config, api_url, user_data)
    db_config["excluded_tables"] = excluded_tables
    
    # PHASE 7: Save configuration
    print_colored("\n7. Saving configuration...", "blue")
    config_id = db_config["config_id"]
    
    # Save the configuration
    if not save_configuration(api_token, api_key, db_config, api_url):
        print_colored("❌ Error saving configuration.", "red")
        return
    
    """ # * --> Deactivated
    # PHASE 8: Test natural language query (optional depending on API status)
    try:
        print_colored("\n8. Testing natural language query...", "blue")
        test_natural_language_query(api_key, db_config, api_url, user_data)
    except Exception as e:
        print_colored(f"⚠️ Could not perform the query test: {str(e)}", "yellow")
        print_colored("This does not affect the saved configuration.", "yellow")
    """
    
    # Final message
    print_colored("\n✅ Configuration completed successfully!", "green")
    print_colored(f"\nYou can use this SDK in your code with:", "blue")
    print(f"""
        from corebrain import init

        # Initialize the SDK with API key and configuration ID
        corebrain = init(
            api_key="{api_key}",
            config_id="{config_id}"
        )

        # Perform natural language queries
        result = corebrain.ask("Your question in natural language")
        print(result["explanation"])
        """
    )