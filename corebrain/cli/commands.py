"""
Main commands for the Corebrain CLI.
"""
import argparse
import os
import sys
import webbrowser

from typing import Optional, List

from corebrain.cli.common import DEFAULT_API_URL, DEFAULT_SSO_URL, DEFAULT_PORT, SSO_CLIENT_ID, SSO_CLIENT_SECRET
from corebrain.cli.auth.sso import authenticate_with_sso
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
        
        args = parser.parse_args(argv)
        
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