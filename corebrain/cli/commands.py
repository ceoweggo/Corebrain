"""
Main commands for the Corebrain CLI.
"""
import argparse
import os
import sys
import webbrowser
import requests

from typing import Optional, List

from corebrain.cli.common import DEFAULT_API_URL, DEFAULT_SSO_URL, DEFAULT_PORT, SSO_CLIENT_ID, SSO_CLIENT_SECRET
from corebrain.cli.auth.sso import authenticate_with_sso
from corebrain.cli.config import configure_sdk, get_api_credential
from corebrain.cli.utils import print_colored
from corebrain.config.manager import ConfigManager
from config.manager import export_config
from config.manager import validate_config
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
    __version__ = "0.1.0"

    try:
        print_colored("Corebrain CLI started. Version ", __version__, "blue")
        
        if argv is None:
            argv = sys.argv[1:]
        
        # Argument parser configuration
        parser = argparse.ArgumentParser(description="Corebrain SDK CLI")
        parser.add_argument("--version", action="store_true", help="Show SDK version")
        parser.add_argument("--configure", action="store_true", help="Configure the Corebrain SDK")
        parser.add_argument("--list-configs", action="store_true", help="List available configurations")
        parser.add_argument("--remove-config", action="store_true", help="Remove a configuration")
        parser.add_argument("--show-schema", action="store_true", help="Show the schema of the configured database")
        parser.add_argument("--extract-schema", action="store_true", help="Extract the database schema and save it to a file")
        parser.add_argument("--output-file", help="File to save the extracted schema")
        parser.add_argument("--config-id", help="Specific configuration ID to use")
        parser.add_argument("--token", help="Corebrain API token (any type)")
        parser.add_argument("--api-key", help="Specific API Key for Corebrain")
        parser.add_argument("--api-url", help="Corebrain API URL")
        parser.add_argument("--sso-url", help="Globodain SSO service URL")
        parser.add_argument("--login", action="store_true", help="Login via SSO")
        parser.add_argument("--test-auth", action="store_true", help="Test SSO authentication system")
        parser.add_argument("--whoami",action="store_true",help="Display information about the current user")
        parser.add_argument("--check-status",action="store_true",help="Checks status of task")
        parser.add_argument("--task-id",help="ID of the task to check status for")
        parser.add_argument("--validate-config",action="store_true",help="Validates the selected configuration without executing any operations")
        parser.add_argument("--test-connection",action="store_true",help="Tests the connection to the Corebrain API using the provide credentials")
        parser.add_argument("--export-config",action="store_true",help="Exports the current configuration to a file")
        
        
        args = parser.parse_args(argv)
        
        
        # Made by Lukasz
        if args.export_config:
            export_config(args.export_config)
            # --> config/manager.py --> export_config

        if args.validate_config:
            if not args.config_id:
                print_colored("Error: --config-id is required for validation", "red")
                return 1
            return validate_config(args.config_id)


        # Show version
        if args.version:
            try:
                from importlib.metadata import version
                sdk_version = version("corebrain")
                print(f"Corebrain SDK version {sdk_version}")
            except Exception:
                print(f"Corebrain SDK version {__version__}")
            return 0
        
        # Test SSO authentication
        if args.test_auth:
            sso_url = args.sso_url or os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
            
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
        
        # Login via SSO
        if args.login:
            sso_url = args.sso_url or os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
            api_key, user_data, api_token = authenticate_with_sso(sso_url)
            
            if api_token:
                # Save the general token for future use
                os.environ["COREBRAIN_API_TOKEN"] = api_token
            
            if api_key:
                # Save the specific API key for future use
                os.environ["COREBRAIN_API_KEY"] = api_key
                print_colored("✅ API Key successfully saved. You can use the SDK now.", "green")
                
                # If configuration was also requested, continue with the process
                if args.configure:
                    api_url = args.api_url or os.environ.get("COREBRAIN_API_URL") or DEFAULT_API_URL
                    configure_sdk(api_token, api_key, api_url, sso_url, user_data)
                
                return 0
            else:
                print_colored("❌ Could not obtain an API Key via SSO.", "red")
                if api_token:
                    print_colored("A general API token was obtained, but not a specific API Key.", "yellow")
                    print_colored("You can create an API Key in the Corebrain dashboard.", "yellow")
                return 1
            
        if args.check_status:
            if not args.task_id:
                print_colored("❌ Please provide a task ID using --task-id", "red")
                return 1
            
            # Get URLs
            api_url = args.api_url or os.environ.get("COREBRAIN_API_URL") or DEFAULT_API_URL
            sso_url = args.sso_url or os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
            
            # Prioritize api_key if explicitly provided
            token_arg = args.api_key if args.api_key else args.token
            
            # Get API credentials
            api_key, user_data, api_token = get_api_credential(token_arg, sso_url)

            if not api_key:
                print_colored("❌ API Key is required to check task status. Use --api-key or login via --login", "red")
                return 1

            try:
                task_id = args.task_id
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json"
                }
                url = f"{api_url}/tasks/{task_id}/status"
                response = requests.get(url, headers=headers)

                if response.status_code == 404:
                    print_colored(f"❌ Task with ID '{task_id}' not found.", "red")
                    return 1

                response.raise_for_status()
                data = response.json()
                status = data.get("status", "unknown")

                print_colored(f"✅ Task '{task_id}' status: {status}", "green")
                return 0
            except Exception as e:
                print_colored(f"❌ Failed to check status: {str(e)}", "red")
                return 1

        if args.whoami:
            try:
                #downloading user data
                sso_url = args.sso_url or os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
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
        
        # Operations that require credentials: configure, list, remove or show schema
        if args.configure or args.list_configs or args.remove_config or args.show_schema or args.extract_schema:
            # Get URLs
            api_url = args.api_url or os.environ.get("COREBRAIN_API_URL") or DEFAULT_API_URL
            sso_url = args.sso_url or os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
            
            # Prioritize api_key if explicitly provided
            token_arg = args.api_key if args.api_key else args.token
            
            # Get API credentials
            api_key, user_data, api_token = get_api_credential(token_arg, sso_url)
            
            if not api_key:
                print_colored("Error: An API Key is required. You can generate one at dashboard.corebrain.com", "red")
                print_colored("Or use the 'corebrain --login' command to login via SSO.", "blue")
                return 1
            
            from corebrain.db.schema_file import show_db_schema, extract_schema_to_file
            
            # Execute the selected operation
            if args.configure:
                configure_sdk(api_token, api_key, api_url, sso_url, user_data)
            elif args.list_configs:
                ConfigManager.list_configs(api_key, api_url)
            elif args.remove_config:
                ConfigManager.remove_config(api_key, api_url)
            elif args.show_schema:
                show_db_schema(api_key, args.config_id, api_url)
            elif args.extract_schema:
                extract_schema_to_file(api_key, args.config_id, args.output_file, api_url)
        
        if args.test_connection:
            # Test connection to the Corebrain API
            api_url = args.api_url or os.environ.get("COREBRAIN_API_URL", DEFAULT_API_URL)
            sso_url = args.sso_url or os.environ.get("COREBRAIN_SSO_URL", DEFAULT_SSO_URL)
            
            try:
                # Retrieve API credentials
                api_key, user_data, api_token = get_api_credential(args.token, sso_url)
            except Exception as e:
                print_colored(f"Error while retrieving API credentials: {e}", "red")
                return 1

            if not api_key:
                print_colored(
                    "Error: An API key is required. You can generate one at dashboard.corebrain.com.",
                    "red"
                )
                return 1

            try:
                # Test the connection
                from corebrain.db.schema_file import test_connection
                test_connection(api_key, api_url)
                print_colored("Successfully connected to Corebrain API.", "green")
            except Exception as e:
                print_colored(f"Failed to connect to Corebrain API: {e}", "red")
                return 1

        
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