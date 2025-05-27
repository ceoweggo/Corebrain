"""
Main commands for the Corebrain CLI.
"""
import argparse
import os
import sys
import webbrowser
import requests
import random 
import string

from typing import Optional, List

from corebrain.cli.common import DEFAULT_API_URL, DEFAULT_SSO_URL, DEFAULT_PORT, SSO_CLIENT_ID, SSO_CLIENT_SECRET
from corebrain.cli.auth.sso import authenticate_with_sso, authenticate_with_sso_and_api_key_request, save_api_token, load_api_token
from corebrain.cli.config import configure_sdk, get_api_credential
from corebrain.cli.utils import print_colored
from corebrain.config.manager import ConfigManager
from corebrain.lib.sso.auth import GlobodainSSOAuth 

def main_cli(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the Corebrain CLI.
    
    Args:
        argv: List of command line arguments (defaults to sys.argv[1:])
        
    Returns:
        Exit code (0 for success, other value for error)
    """
        
    # Package version
    __version__ = "0.2.0"

    try:
        print_colored("Corebrain CLI started. Version ", __version__, "blue")
        
        if argv is None:
            argv = sys.argv[1:]
        
        # Functions
        def authentication():
            sso_url = os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
            sso_token, sso_user = authenticate_with_sso(sso_url)
            if sso_token:
                try:
                    print_colored("✅ Returning SSO Token.", "green")
                    print_colored(f"{sso_token}", "blue")
                    print_colored("✅ Returning User data.", "green")
                    print_colored(f"{sso_user}", "blue")
                    return sso_token, sso_user
                
                except Exception as e:
                    print_colored("❌ Could not return SSO Token or SSO User data.", "red")
                    return sso_token, sso_user
                
            else:
                print_colored("❌ Could not authenticate with SSO.", "red")
                return None, None

        def authentication_with_api_key_return():
            sso_url = os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
            api_key_selected, user_data, api_token = authenticate_with_sso_and_api_key_request(sso_url)

            if api_token:
                try:
                    print_colored("✅ User authenticated and SDK is now connected to API.", "green")
                    print_colored("✅ Returning User data.", "green")
                    print_colored(f"{user_data}", "blue")
                    return api_key_selected, user_data, api_token
                
                except Exception as e:
                    print_colored("❌ Could not return SSO Token or SSO User data.", "red")
                    return api_key_selected, user_data, api_token
                
            else:
                print_colored("❌ Could not authenticate with SSO.", "red")
                return None, None, None

        # Argument parser configuration
        parser = argparse.ArgumentParser(description="Corebrain SDK CLI")

        # Arguments for development
        parser.add_argument("--version", action="store_true", help="Show SDK version")
        parser.add_argument("--check-status",action="store_true",help="Checks status of task")
        parser.add_argument("--authentication", action="store_true", help="Authenticate with SSO")
        parser.add_argument("--test-auth", action="store_true", help="Test SSO authentication system") # Is this command really useful?
        parser.add_argument("--create-api-key", action="store_true", help="Create a new API Key")
        parser.add_argument("--key-name", help="Sets name of the new API Key")
        parser.add_argument("--key-level", choices=["read", "write", "admin"], default="read", help="Specifies access level for the new API Key")

        # Arguments to use the SDK
        parser.add_argument("--create-user", action="store_true", help="Create an user and API Key by default")
        parser.add_argument("--configure", action="store_true", help="Configure the Corebrain SDK")
        parser.add_argument("--list-configs", action="store_true", help="List available configurations")
        parser.add_argument("--show-schema", action="store_true", help="Display database schema for a configuration")
        parser.add_argument("--woami",action="store_true",help="Display information about the current user")
        parser.add_argument("--gui", action="store_true", help="Check setup and launch the web interface")
        
        args = parser.parse_args(argv)

        # Common variables
        api_url = os.environ.get("COREBRAIN_API_URL", DEFAULT_API_URL)
        sso_url = os.environ.get("COREBRAIN_SSO_URL", DEFAULT_SSO_URL)

        ## ** For development ** ##
        if args.version:
            """
            Display the current version of the Corebrain SDK.
            
            This command shows the version of the installed Corebrain SDK package.
            It attempts to get the version from the package metadata first, and if that fails,
            it falls back to the hardcoded version in the CLI module.
            
            Usage: corebrain --version
            
            Example output:
            Corebrain SDK version 0.2.0
            """
            try:
                from importlib.metadata import version
                sdk_version = version("corebrain")
                print(f"Corebrain SDK version {sdk_version}")
            except Exception:
                print(f"Corebrain SDK version {__version__}")
            return 0

        if args.check_status:
            """
            If you're in development mode:

            Check that all requirements for developing code and performing tests or other functions are accessible:
            - Check that the API Server is runned
            - Check that the Redis is runned on port 6379
            - Check that the SSO Server is active (sso.globodain.com)
            - Check that MongoDB is runned on port 27017
            - Check that the all libraries are installed:         

            httpx>=0.23.0
            pymongo>=4.3.0
            psycopg2-binary>=2.9.5
            mysql-connector-python>=8.0.31
            sqlalchemy>=2.0.0
            cryptography>=39.0.0
            pydantic>=1.10.0


            If you're in production mode:

            Check that the API Server is active (api.etedata.com)
            Check that the SSO Server is active (sso.globodain.com)
            Check that the all libraries are installed:         

            httpx>=0.23.0
            pymongo>=4.3.0
            psycopg2-binary>=2.9.5
            mysql-connector-python>=8.0.31
            sqlalchemy>=2.0.0
            cryptography>=39.0.0
            pydantic>=1.10.0

            """            
        
            import socket
            import subprocess
            import importlib.util
            
            def check_port(host, port, service_name):
                """Check if a service is running on a specific port"""
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)
                    result = sock.connect_ex((host, port))
                    sock.close()
                    if result == 0:
                        print_colored(f"✅ {service_name} is running on {host}:{port}", "green")
                        return True
                    else:
                        print_colored(f"❌ {service_name} is not accessible on {host}:{port}", "red")
                        return False
                except Exception as e:
                    print_colored(f"❌ Error checking {service_name}: {str(e)}", "red")
                    return False
            
            def check_url(url, service_name):
                """Check if a service is accessible via HTTP"""
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code < 500:
                        print_colored(f"✅ {service_name} is accessible at {url}", "green")
                        return True
                    else:
                        print_colored(f"❌ {service_name} returned status {response.status_code} at {url}", "red")
                        return False
                except Exception as e:
                    print_colored(f"❌ {service_name} is not accessible at {url}: {str(e)}", "red")
                    return False
            
            def check_library(library_name, min_version):
                """Check if a library is installed with minimum version"""
                # Mapping of PyPI package names to import names
                package_import_mapping = {
                    'psycopg2-binary': 'psycopg2',
                    'mysql-connector-python': 'mysql.connector',
                    'httpx': 'httpx',
                    'pymongo': 'pymongo',
                    'sqlalchemy': 'sqlalchemy',
                    'cryptography': 'cryptography',
                    'pydantic': 'pydantic'
                }
                
                package_name = library_name.split('>=')[0]
                import_name = package_import_mapping.get(package_name, package_name)
                
                try:
                    # Check if the module can be imported
                    if '.' in import_name:
                        # For modules like mysql.connector
                        parts = import_name.split('.')
                        spec = importlib.util.find_spec(parts[0])
                        if spec is None:
                            print_colored(f"❌ {package_name} is not installed", "red")
                            return False
                        # Try to import the full module path
                        try:
                            __import__(import_name)
                        except ImportError:
                            print_colored(f"❌ {package_name} is not installed", "red")
                            return False
                    else:
                        spec = importlib.util.find_spec(import_name)
                        if spec is None:
                            print_colored(f"❌ {package_name} is not installed", "red")
                            return False
                    
                    # Try to get version using different methods
                    try:
                        from importlib.metadata import version
                        # Try with the package name first
                        try:
                            installed_version = version(package_name)
                        except:
                            # If that fails, try with common alternative names
                            alternative_names = {
                                'psycopg2-binary': ['psycopg2', 'psycopg2-binary'],
                                'mysql-connector-python': ['mysql-connector-python', 'mysql-connector']
                            }
                            
                            installed_version = None
                            for alt_name in alternative_names.get(package_name, [package_name]):
                                try:
                                    installed_version = version(alt_name)
                                    break
                                except:
                                    continue
                            
                            if installed_version is None:
                                raise Exception("Version not found")
                        
                        print_colored(f"✅ {package_name} {installed_version} is installed", "green")
                        return True
                        
                    except Exception:
                        # If version check fails, at least we know the module can be imported
                        print_colored(f"✅ {package_name} is installed (version check failed)", "yellow")
                        return True
                    
                except Exception as e:
                    print_colored(f"❌ Error checking {package_name}: {str(e)}", "red")
                    return False
            
            # Determine if in development or production mode
            api_url = os.environ.get("COREBRAIN_API_URL") or DEFAULT_API_URL
            is_development = "localhost" in api_url or "127.0.0.1" in api_url or api_url == DEFAULT_API_URL
            
            print_colored("🔍 Checking system status...", "blue")
            print_colored(f"Mode: {'Development' if is_development else 'Production'}", "blue")
            print_colored(f"API URL: {api_url}", "blue")
            print()
            
            all_checks_passed = True
            
            # Required libraries for both modes
            required_libraries = [
                "httpx>=0.23.0",
                "pymongo>=4.3.0", 
                "psycopg2-binary>=2.9.5",
                "mysql-connector-python>=8.0.31",
                "sqlalchemy>=2.0.0",
                "cryptography>=39.0.0",
                "pydantic>=1.10.0"
            ]
            
            # Check libraries
            print_colored("📚 Checking required libraries:", "blue")
            for library in required_libraries:
                if not check_library(library, library.split('>=')[1] if '>=' in library else None):
                    all_checks_passed = False
            print()
            
            # Check services based on mode
            if is_development:
                print_colored("🔧 Development mode - Checking local services:", "blue")
                
                # Check local API server
                if not check_url(api_url, "API Server"):
                    all_checks_passed = False
                
                # Check Redis
                if not check_port("localhost", 6379, "Redis"):
                    all_checks_passed = False
                
                # Check MongoDB  
                if not check_port("localhost", 27017, "MongoDB"):
                    all_checks_passed = False
                    
            else:
                print_colored("🌐 Production mode - Checking remote services:", "blue")
                
                # Check production API server
                if not check_url("https://api.etedata.com", "API Server (Production)"):
                    all_checks_passed = False
            
            # Check SSO service for both modes
            sso_url = os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
            if not check_url(sso_url, "SSO Server"):
                all_checks_passed = False
            
            print()
            if all_checks_passed:
                print_colored("✅ All system checks passed!", "green")
                return 0
            else:
                print_colored("❌ Some system checks failed. Please review the issues above.", "red")
                return 1

        if args.authentication:
            """
            Perform SSO authentication and display the obtained tokens and user data.
            
            This command initiates the SSO (Single Sign-On) authentication flow through the browser.
            It opens a browser window for the user to authenticate with their Globodain SSO credentials
            and returns the authentication token and user information.
            
            This is primarily used for testing authentication or when you need to see the raw
            authentication data. For normal usage, prefer --login which also obtains API keys.
            
            Usage: corebrain --authentication [--sso-url <url>]
            
            Returns:
            - SSO authentication token
            - User profile data (name, email, etc.)
            
            Note: This command only authenticates but doesn't save credentials for future use.
            """
            authentication()
            
        if args.test_auth:
            """
            Test the SSO (Single Sign-On) authentication system.
            
            This command performs a comprehensive test of the SSO authentication flow
            without saving any credentials or performing any actual operations. It's useful
            for diagnosing authentication issues and verifying that the SSO system is working.
            
            The test process:
            1. Configures the SSO authentication client
            2. Generates a login URL
            3. Opens the browser for user authentication
            4. Waits for user to complete the authentication process
            5. Reports success or failure
            
            Usage: corebrain --test-auth [--sso-url <url>]
            
            What it tests:
            - SSO server connectivity
            - Client configuration validity
            - Authentication flow completion
            - Browser integration
            
            Note: This is a diagnostic tool and doesn't save any authentication data.
            For actual login, use --login instead.
            """
            sso_url = os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
            
            print_colored("Testing SSO authentication...", "blue")
            
            # Authentication configuration
            auth_config = {
                'GLOBODAIN_SSO_URL': sso_url,
                'GLOBODAIN_CLIENT_ID': SSO_CLIENT_ID,
                'GLOBODAIN_CLIENT_SECRET': SSO_CLIENT_SECRET,
                'GLOBODAIN_REDIRECT_URI': f"http://localhost:{DEFAULT_PORT}/auth/sso/callback",
                'GLOBODAIN_SUCCESS_REDIRECT': f"http://localhost:{DEFAULT_PORT}/auth/sso/callback"
            }
            
            try:
                # Instantiate authentication client
                sso_auth = GlobodainSSOAuth(config=auth_config)
                
                # Get login URL
                login_url = sso_auth.get_login_url()
                
                print_colored(f"Login URL: {login_url}", "blue")
                print_colored("Opening browser for login...", "blue")
                
                # Open browser
                webbrowser.open(login_url)
                
                print_colored("Please complete the login process in the browser.", "blue")
                input("\nPress Enter when you've completed the process or to cancel...")
                
                print_colored("✅ SSO authentication test completed!", "green")
                return 0
            except Exception as e:
                print_colored(f"❌ Error during test: {str(e)}", "red")
                return 1
        

        ## ** SDK ** ##
        
        if args.create_user:
            """
            Create a new user account and generate an associated API Key.
            
            This command performs a complete user registration process:
            1. Authenticates the user through SSO (Single Sign-On)
            2. Creates a new user account in the Corebrain system using SSO data
            3. Automatically generates an API Key for the new user
            
            The user can choose to use their SSO password or create a new password
            specifically for their Corebrain account. If using SSO password fails,
            a random secure password will be generated.
            
            Usage: corebrain --create-user [--api-url <url>] [--sso-url <url>]
            
            Interactive prompts:
            - SSO authentication (browser-based)
            - Password choice (use SSO password or create new)
            - Password confirmation (if creating new)
            
            Requirements:
            - Valid Globodain SSO account
            - Internet connection for API communication
            
            On success: Creates user account and displays confirmation
            On failure: Shows specific error message
            """
            sso_token, sso_user = authentication() # Authentica use with SSO
            
            if sso_token and sso_user:
                print_colored("✅ Enter to create an user and API Key.", "green")
                
                # Get API URL from environment or use default
                api_url = os.environ.get("COREBRAIN_API_URL", DEFAULT_API_URL)
                
                """
                Create user data with SSO information.
                If the user wants to use a different password than their SSO account,
                they can specify it here.
                """
                # Ask if user wants to use SSO password or create a new one
                use_sso_password = input("Do you want to use your SSO password? (y/n): ").lower().strip() == 'y'
                
                if use_sso_password:
                    random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                    password = sso_user.get("password", random_password)
                else:
                    while True:
                        password = input("Enter new password: ").strip()
                        if len(password) >= 8:
                            break
                        print_colored("Password must be at least 8 characters long", "yellow")
                
                user_data = {
                    "email": sso_user["email"],
                    "name": f"{sso_user['first_name']} {sso_user['last_name']}",
                    "password": password
                }
                
                try:
                    # Make the API request
                    response = requests.post(
                        f"{api_url}/api/auth/users",
                        json=user_data,
                        headers={
                            "Authorization": f"Bearer {sso_token}",
                            "Content-Type": "application/json"
                        }
                    )
                    
                    # Check if the request was successful
                    print("response API: ", response)
                    if response.status_code == 200:
                        print_colored("✅ User and API Key created successfully!", "green")
                        return 0
                    else:
                        print_colored(f"❌ Error creating user: {response.text}", "red")
                        return 1
                        
                except requests.exceptions.RequestException as e:
                    print_colored(f"❌ Error connecting to API: {str(e)}", "red")
                    return 1
                
            else:
                print_colored("❌ Could not create the user or the API KEY.", "red")
                return 1
        
        if args.configure or args.list_configs or args.show_schema:
            """
            Configure, list or show schema of the configured database.

            Reuse the same authentication code for configure, list and show schema.
            """
            
            api_key_selected, user_data, api_token = authentication_with_api_key_return() # Authentica use with SSO
            
            if not api_key_selected:
                print_colored("Error: An API Key is required. You can generate one at dashboard.etedata.com", "red")
                print_colored("Or use the 'corebrain --create-api-key' command to create a new one using CLI.", "blue")
                return 1
            
            from corebrain.db.schema_file import show_db_schema
            
            # Execute the selected operation
            if args.configure:
                """
                Launch the comprehensive SDK configuration wizard.
                
                This is the main configuration command that guides you through setting up
                a complete database connection for use with the Corebrain SDK. The wizard
                walks you through each step of the configuration process interactively.
                
                Configuration phases:
                1. Authentication verification (already completed)
                2. Database type selection (SQL or MongoDB)
                3. Database engine selection (PostgreSQL, MySQL, SQLite, etc.)
                4. Connection parameters input (host, port, credentials, etc.)
                5. Database connection testing and validation
                6. Schema accessibility configuration (excluded tables/collections)
                7. Configuration saving and server synchronization
                8. Optional natural language query testing
                
                Usage: corebrain --configure [--api-key <key>] [--api-url <url>] [--sso-url <url>]
                
                Interactive prompts guide you through:
                - Database type (sql/mongodb)
                - Engine selection (postgresql, mysql, sqlite, etc.)
                - Connection details (host, port, database name)
                - Authentication credentials (username, password)
                - Connection string (alternative to individual parameters)
                - Table/collection exclusions for security
                - Configuration naming and saving
                
                Supported databases:
                SQL:
                - PostgreSQL (local and remote)
                - MySQL/MariaDB (local and remote)
                - SQLite (file-based and in-memory)
                
                NoSQL:
                - MongoDB (local and remote, with or without authentication)
                
                Security features:
                - Encrypted local storage of configurations
                - Secure credential handling
                - Table/collection access control
                - Server synchronization with encrypted transport
                
                After successful configuration:
                - Configuration is saved locally with encryption
                - Synchronization with Corebrain API server
                - Ready to use with SDK (init function)
                - Available for natural language queries
                
                Example usage after configuration:
                ```python
                from corebrain import init
                
                client = init(
                    api_key="your_api_key",
                    config_id="generated_config_id"
                )
                
                result = client.ask("How many users are in the database?")
                ```
                
                Prerequisites:
                - Valid API key (obtain via --login or --api-key)
                - Network access to target database
                - Appropriate database permissions for schema reading
                - Internet connectivity for API synchronization
                """
                configure_sdk(api_token, api_key_selected, api_url, sso_url, user_data)

            elif args.list_configs:
                """
                List and manage all saved database configurations for your API key.
                
                This command provides an interactive interface to view and manage all
                database configurations associated with your API key. It serves as a
                central hub for configuration management operations.
                
                Main features:
                - View all saved configurations with details
                - Interactive selection and management
                - Multiple management operations per configuration
                - Safe deletion with confirmation prompts
                - Configuration validation and testing
                - Import/export capabilities
                
                Usage: corebrain --list-configs [--api-key <key>]
                
                Available operations for each configuration:
                1. Show Schema: Display detailed database structure
                   - Tables/collections list
                   - Column details and types
                   - Indexes and relationships
                   - Safe read-only operation
                
                2. Validate Config: Comprehensive configuration validation
                   - Structure and format verification
                   - Database connectivity testing
                   - Permission and access verification
                   - Error reporting and diagnostics
                
                3. Remove Config: Safe configuration deletion
                   - Confirmation prompts
                   - Local storage cleanup
                   - Server synchronization
                   - Irreversible operation warning
                
                4. Modify Config: Update existing configuration
                   - Interactive parameter editing
                   - Connection parameter updates
                   - Excluded tables management
                   - Automatic validation after changes
                
                5. Export Config: Backup configuration to file
                   - JSON format export
                   - Credential handling options
                   - Shareable format creation
                   - Backup and migration support
                
                6. Import Config: Load configuration from file
                   - JSON file import
                   - Validation before saving
                   - Conflict resolution
                   - Batch import support
                
                7. Configure New: Launch configuration wizard
                   - Full setup process
                   - Database connection setup
                   - Testing and validation
                   - Save new configuration
                
                Information displayed for each configuration:
                - Configuration ID (unique identifier)
                - Database type and engine
                - Connection details (host, database name)
                - Creation and last modified dates
                - Validation status
                - Usage statistics
                
                Interactive navigation:
                - Arrow keys or numbers for selection
                - Enter to confirm operations
                - ESC or 'q' to exit
                - Help available with '?' key
                
                Security considerations:
                - Configurations stored with encryption
                - Sensitive data masked in display
                - Secure credential handling
                - Server synchronization with HTTPS
                
                Use cases:
                - Review existing database connections
                - Maintain multiple database configurations
                - Troubleshoot connection issues
                - Backup and restore configurations
                - Share configurations between environments
                - Clean up unused configurations
                
                Prerequisites:
                - Valid API key for authentication
                - Internet connectivity for server operations
                - Appropriate permissions for configuration management
                
                Note: This command provides a safe environment for configuration
                management with confirmation prompts for destructive operations.
                """
                ConfigManager.list_configs(api_key, api_url)

            elif args.show_schema:
                """
                Display the schema of a configured database without connecting through the SDK.
                
                This command allows you to explore the structure of a database by showing
                detailed information about tables, columns, indexes, and relationships.
                It's useful for understanding the database structure before writing queries.
                
                The command can work in two ways:
                1. With a saved configuration (using --config-id)
                2. By prompting you to select from available configurations
                
                Usage: corebrain --show-schema [--config-id <id>]
                
                Information displayed:
                - Database type and engine
                - List of all tables/collections
                - Column details (name, type, constraints)
                - Primary keys and foreign keys
                - Indexes and their properties
                - Table relationships and dependencies
                
                Supported databases:
                - SQL: PostgreSQL, MySQL, SQLite
                - NoSQL: MongoDB
                
                Note: This command only reads schema information and doesn't modify
                the database in any way. It's safe to run on production databases.
                """
                show_db_schema(api_key, args.config_id, api_url)



        # ** move to the config manager --> inside of the command --list-configs **

        # Handle validate-config and export-config commands
        #if args.validate_config:
            """
            Validate a saved configuration without executing any operations.
            
            This command performs comprehensive validation of a database configuration
            to ensure it's correctly formatted and all required parameters are present.
            It checks the configuration syntax, required fields, and optionally tests
            the database connection.
            
            Validation checks performed:
            1. Configuration format and structure
            2. Required fields presence (type, engine, credentials)
            3. Field value validity (ports, hostnames, database names)
            4. Database connection test (optional)
            5. Authentication and permissions verification
            
            Usage: corebrain --validate-config --config-id <id> [--api-key <key>]
            
            Validation levels:
            - Structure: Validates configuration format and required fields
            - Connection: Tests actual database connectivity
            - Permissions: Verifies database access permissions
            - Schema: Checks if the database schema can be read
            
            Exit codes:
            - 0: Configuration is valid
            - 1: Configuration has errors
            
            Use cases:
            - Verify configuration before deployment
            - Troubleshoot connection issues
            - Validate imported configurations
            - Check configuration after database changes
            
            Note: This command requires a valid API key to access saved configurations.
            """
        #    if not args.config_id:
        #        print_colored("Error: --config-id is required for validation", "red")
        #        return 1
            
            # Get credentials
        #    api_url = os.environ.get("COREBRAIN_API_URL") or DEFAULT_API_URL
        #    sso_url = os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
        #    token_arg = args.api_key if args.api_key else args.token
        #    api_key, user_data, api_token = get_api_credential(token_arg, sso_url)
            
        #    if not api_key:
        #        print_colored("Error: An API Key is required. Use --api-key or login via --login", "red")
        #        return 1
            
            # Validate the configuration
        #    try:
        #        config_manager = ConfigManager()
        #        config = config_manager.get_config(api_key, args.config_id)
                
        #        if not config:
        #            print_colored(f"Configuration with ID '{args.config_id}' not found", "red")
        #            return 1
                
        #        print_colored(f"✅ Validating configuration: {args.config_id}", "blue")
                
                # Create a temporary Corebrain instance to validate
        #        from corebrain.core.client import Corebrain
        #        try:
        #            temp_client = Corebrain(
        #                api_key=api_key,
        #                db_config=config,
        #                skip_verification=True
        #            )
        #            print_colored("✅ Configuration validation passed!", "green")
        #            print_colored(f"Database type: {config.get('type', 'Unknown')}", "blue")
        #            print_colored(f"Engine: {config.get('engine', 'Unknown')}", "blue")
        #            return 0
        #        except Exception as validation_error:
        #            print_colored(f"❌ Configuration validation failed: {str(validation_error)}", "red")
        #            return 1
                    
        #    except Exception as e:
        #        print_colored(f"❌ Error during validation: {str(e)}", "red")
        #        return 1

        #if args.export_config:
            """
            Export a saved configuration to a JSON file.
            
            This command exports a database configuration from the local storage
            to a JSON file that can be shared, backed up, or imported on another system.
            The exported file contains all connection parameters and settings needed
            to recreate the configuration.
            
            The export process:
            1. Retrieves the specified configuration from local storage
            2. Decrypts sensitive information (if encrypted)
            3. Formats the configuration as readable JSON
            4. Saves to the specified output file
            5. Optionally removes sensitive data for sharing
            
            Usage: corebrain --export-config --config-id <id> [--output-file <path>] [--api-key <key>]
            
            Options:
            --config-id: ID of the configuration to export (required)
            --output-file: Path for the exported file (default: config_<id>.json)
            --remove-credentials: Remove sensitive data for sharing (optional)
            --pretty-print: Format JSON with indentation for readability
            
            Exported data includes:
            - Database connection parameters
            - Engine and type information
            - Configuration metadata
            - Excluded tables/collections list
            - Custom settings and preferences
            
            Security considerations:
            - Exported files may contain sensitive credentials
            - Use --remove-credentials flag when sharing configurations
            - Store exported files in secure locations
            - Consider encrypting exported files for transmission
            
            Use cases:
            - Backup configurations before changes
            - Share configurations between team members
            - Migrate configurations to different environments
            - Create configuration templates
            - Document database connection settings
            """
        #    if not args.config_id:
        #        print_colored("Error: --config-id is required for export", "red")
        #        return 1
                
            # Get credentials
        #    api_url = os.environ.get("COREBRAIN_API_URL") or DEFAULT_API_URL
        #    sso_url = os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
        #    token_arg = args.api_key if args.api_key else args.token
        #    api_key, user_data, api_token = get_api_credential(token_arg, sso_url)
            
        #    if not api_key:
        #        print_colored("Error: An API Key is required. Use --api-key or login via --login", "red")
        #        return 1
            
            # Export the configuration
        #    try:
        #        config_manager = ConfigManager()
        #        config = config_manager.get_config(api_key, args.config_id)
                
        #        if not config:
        #            print_colored(f"Configuration with ID '{args.config_id}' not found", "red")
        #            return 1
                
                # Generate output filename if not provided
        #        output_file = getattr(args, 'output_file', None) or f"config_{args.config_id}.json"
                
                # Export to file
        #        import json
        #        with open(output_file, 'w', encoding='utf-8') as f:
        #            json.dump(config, f, indent=2, default=str)
                
        #        print_colored(f"✅ Configuration exported to: {output_file}", "green")
        #        return 0
                
        #    except Exception as e:
        #        print_colored(f"❌ Error exporting configuration: {str(e)}", "red")
        #        return 1


        if args.woami:
            """
            Display information about the currently authenticated user.
            
            This command shows detailed information about the user associated with the
            current authentication credentials. It's similar to the Unix 'whoami' command
            but for the Corebrain system.
            
            The command attempts to retrieve user data using the following credential sources
            (in order of priority):
            1. API key provided via --api-key argument
            2. Token provided via --token argument  
            3. COREBRAIN_API_KEY environment variable
            4. COREBRAIN_API_TOKEN environment variable
            5. SSO authentication (if no other credentials found)
            
            Usage: corebrain --woami [--api-key <key>] [--token <token>] [--sso-url <url>]
            
            Information displayed:
            - User ID and email
            - Name and profile details
            - Account creation and last login dates
            - Associated roles and permissions
            - Any other profile metadata from SSO
            
            Use cases:
            - Verify which user account is currently active
            - Debug authentication issues
            - Check user permissions and profile data
            - Confirm successful login
            
            Note: Requires valid authentication credentials to work.
            """
            try:
                #downloading user data
                sso_url = os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
                token_arg = args.api_key if args.api_key else args.token

                #using saved data about user 
                api_key, user_data, api_token = get_api_credential(token_arg, sso_url)
                #printing user data
                if user_data:
                    print_colored("User Data:", "blue")
                    for k, v in user_data.items():
                        print(f"{k}: {v}")
                else:
                    print_colored("❌ Can't find data about user, be sure that you are logged into  --login.", "red")
                    return 1

                return 0
            except Exception as e:
                print_colored(f"❌ Error when downloading data about user {str(e)}", "red")
                return 1

        if args.gui:
            """
            Check setup and launch the web-based graphical user interface.
            
            This command sets up and launches a complete web-based GUI for the Corebrain SDK,
            providing a user-friendly alternative to the command-line interface. The GUI includes
            both frontend and backend components and integrates with the Corebrain API.
            
            Components launched:
            1. React Frontend (client) - User interface running on port 5173
            2. Express Backend (server) - API server for the frontend
            3. Corebrain API wrapper (C#) - Additional API integration
            
            Setup process:
            1. Validates required directory structure
            2. Installs Node.js dependencies if not present
            3. Configures development tools (Vite, TypeScript)
            4. Starts all services concurrently
            5. Opens browser to the GUI automatically
            
            Usage: corebrain --gui
            
            Directory structure required:
            - CLI-UI/client/ (React frontend)
            - CLI-UI/server/ (Express backend)  
            - wrappers/csharp_cli_api/ (C# API wrapper)
            
            Dependencies installed automatically:
            Frontend (React):
            - Standard React dependencies
            - History library for routing
            - Vite for development and building
            - Concurrently for running multiple processes
            
            Backend (Express):
            - Standard Express dependencies
            - TypeScript development tools
            - ts-node-dev for hot reloading
            
            Access points:
            - Frontend GUI: http://localhost:5173/
            - Backend API: Usually http://localhost:3000/
            - C# API wrapper: Usually http://localhost:5000/
            
            Use cases:
            - Visual configuration of database connections
            - Interactive query building and testing
            - Graphical schema exploration
            - User-friendly alternative to CLI commands
            - Debugging and development interface
            
            Note: Requires Node.js, npm, and .NET runtime to be installed on the system.
            """
            import subprocess
            from pathlib import Path

            def run_cmd(cmd, cwd=None):
                print_colored(f"▶ {cmd}", "yellow")
                subprocess.run(cmd, shell=True, cwd=cwd, check=True)

            print("Checking GUI setup...")

            commands_path = Path(__file__).resolve()
            corebrain_root = commands_path.parents[1]

            cli_ui_path = corebrain_root / "CLI-UI"
            client_path = cli_ui_path / "client"
            server_path = cli_ui_path / "server"
            api_path = corebrain_root / "wrappers" / "csharp_cli_api"

            # Path validation
            if not client_path.exists():
                print_colored(f"Folder {client_path} does not exist!", "red")
                sys.exit(1)
            if not server_path.exists():
                print_colored(f"Folder {server_path} does not exist!", "red")
                sys.exit(1)
            if not api_path.exists():
                print_colored(f"Folder {api_path} does not exist!", "red")
                sys.exit(1)

            # Setup client
            if not (client_path / "node_modules").exists():
                print_colored("Installing frontend (React) dependencies...", "cyan")
                run_cmd("npm install", cwd=client_path)
                run_cmd("npm install history", cwd=client_path)
                run_cmd("npm install --save-dev vite", cwd=client_path)
                run_cmd("npm install concurrently --save-dev", cwd=client_path)

            # Setup server
            if not (server_path / "node_modules").exists():
                print_colored("Installing backend (Express) dependencies...", "cyan")
                run_cmd("npm install", cwd=server_path)
                run_cmd("npm install --save-dev ts-node-dev", cwd=server_path)

            # Start GUI: CLI UI + Corebrain API
            print("Starting GUI (CLI-UI + Corebrain API)...")

            def run_in_background_silent(cmd, cwd):
                return subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            run_in_background_silent("dotnet run", cwd=api_path)
            run_in_background_silent(
                'npx concurrently "npm --prefix server run dev" "npm --prefix client run dev"',
                cwd=cli_ui_path
            )

            url = "http://localhost:5173/"
            print_colored(f"GUI: {url}", "cyan")
            webbrowser.open(url)
        



        # Handles the CLI command to create a new API key using stored credentials (token from SSO)
        if args.create_api_key:
            sso_token, sso_user = authentication() # Authentica use with SSO

            key_name = args.key_name or "default-key"
            key_level = args.key_level or "read"

            api_url = args.api_url or os.environ.get("COREBRAIN_API_URL") or DEFAULT_API_URL

            # Sending request to Corebrain-API
            payload = {
                "name": key_name,
                "access_level": key_level
            }

            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            }

            try:
                response = requests.post(
                    f"{api_url}/api/auth/api-keys",
                    json=payload,
                    headers=headers
                )

                if response.status_code == 200:
                    key_data = response.json()
                    print_colored("✅ API Key was created successfully:", "green")
                    print_colored(f"Name: {key_data['name']}", "blue")
                    print_colored(f"Key: {key_data['key']}", "blue")
                else:
                    print_colored(f"❌ Error while creating API Key: {response.text}", "red")
                    return 1

            except Exception as e:
                print_colored(f"❌ Exception occurred while creating API Key: {str(e)}", "red")
                return 1

            return 0

        else:
            # If no option was specified, show help
            parser.print_help()
            print_colored("\nTip: Use 'corebrain --login' to login via SSO.", "blue")       
        return 0
    except Exception as e:
        print_colored(f"Error: {str(e)}", "red")
        import traceback
        traceback.print_exc()
        return 1
