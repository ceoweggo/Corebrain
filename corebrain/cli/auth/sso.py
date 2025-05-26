"""
SSO Authentication for the CLI.
"""
import os
import webbrowser
import http.server
import socketserver
import threading
import urllib.parse
import time

from typing import Tuple, Dict, Any, Optional

from corebrain.cli.common import DEFAULT_API_URL, DEFAULT_SSO_URL, DEFAULT_PORT, SSO_CLIENT_ID, SSO_CLIENT_SECRET
from corebrain.cli.utils import print_colored
from corebrain.lib.sso.auth import GlobodainSSOAuth

class TokenHandler(http.server.SimpleHTTPRequestHandler):
    """
    Handler for the local HTTP server that processes the SSO authentication callback.
    """
    def __init__(self, *args, **kwargs):
        self.sso_auth = kwargs.pop('sso_auth', None)
        self.result = kwargs.pop('result', {})
        self.session_data = kwargs.pop('session_data', {})
        self.auth_completed = kwargs.pop('auth_completed', None)
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        # Parse the URL to get the parameters
        parsed_path = urllib.parse.urlparse(self.path)
        
        # Check if it's the callback path
        if parsed_path.path == "/auth/sso/callback":
            query = urllib.parse.parse_qs(parsed_path.query)
            
            if "code" in query:
                code = query["code"][0]
                
                try:
                    # Exchange code for token using the sso_auth object
                    token_data = self.sso_auth.exchange_code_for_token(code)
                    
                    if not token_data:
                        raise ValueError("Could not obtain the token")
                    
                    # Save token in the result and session
                    access_token = token_data.get('access_token')
                    if not access_token:
                        raise ValueError("The received token does not contain an access_token")
                        
                    # Updated: save as sso_token for clarity
                    self.result["sso_token"] = access_token
                    self.session_data['sso_token'] = token_data
                    
                    # Get user information
                    user_info = self.sso_auth.get_user_info(access_token)
                    if user_info:
                        self.session_data['user'] = user_info
                        # Extract email to identify the user
                        if 'email' in user_info:
                            self.session_data['email'] = user_info['email']
                        
                    # Signal that authentication has completed
                    self.auth_completed.set()
                    
                    # Send a success response to the browser
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    success_html = """
                    <html>
                    <head>
                        <title>Corebrain - Authentication Completed</title>
                        <style>
                            body {
                                font-family: Arial, sans-serif;
                                text-align: center;
                                padding: 40px;
                                background-color: #f7f9fc;
                            }
                            .container {
                                background-color: white;
                                border-radius: 8px;
                                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                                padding: 30px;
                                max-width: 500px;
                                margin: 0 auto;
                            }
                            h1 {
                                color: #4285F4;
                            }
                            p {
                                color: #333;
                                font-size: 16px;
                                line-height: 1.5;
                            }
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>Authentication Completed</h1>
                            <p>You have successfully logged in to Corebrain CLI.</p>
                            <p>You can close this window and return to the terminal.</p>
                        </div>
                    </body>
                    </html>
                    """
                    self.wfile.write(success_html.encode())
                except Exception as e:
                    # If there's an error, show error message
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    error_html = f"""
                    <html>
                    <head>
                        <title>Corebrain - Authentication Error</title>
                        <style>
                            body {{
                                font-family: Arial, sans-serif;
                                text-align: center;
                                padding: 40px;
                                background-color: #f7f9fc;
                            }}
                            .container {{
                                background-color: white;
                                border-radius: 8px;
                                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                                padding: 30px;
                                max-width: 500px;
                                margin: 0 auto;
                            }}
                            h1 {{
                                color: #EA4335;
                            }}
                            p {{
                                color: #333;
                                font-size: 16px;
                                line-height: 1.5;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>Authentication Error</h1>
                            <p>Error: {str(e)}</p>
                            <p>Please close this window and try again.</p>
                        </div>
                    </body>
                    </html>
                    """
                    self.wfile.write(error_html.encode())
            else:
                # If there's no code, it's an error
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                error_html = """
                <html>
                <head>
                    <title>Corebrain - Authentication Error</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            text-align: center;
                            padding: 40px;
                            background-color: #f7f9fc;
                        }
                        .container {
                            background-color: white;
                            border-radius: 8px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            padding: 30px;
                            max-width: 500px;
                            margin: 0 auto;
                        }
                        h1 {
                            color: #EA4335;
                        }
                        p {
                            color: #333;
                            font-size: 16px;
                            line-height: 1.5;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Authentication Error</h1>
                        <p>Could not complete the authentication process.</p>
                        <p>Please close this window and try again.</p>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(error_html.encode())
        else:
            # For any other path, show a 404 error
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
    
    def log_message(self, format, *args):
        # Silence server logs
        return

def authenticate_with_sso(sso_url: str) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
    """
    Initiates an SSO authentication flow through the browser and uses the callback system.
    
    Args:
        sso_url: Base URL of the SSO service
    
    Returns:
        Tuple with (api_key, user_data, api_token) or (None, None, None) if it fails
        - api_key: Selected API key to use with the SDK
        - user_data: Authenticated user data
        - api_token: API token obtained from SSO for general authentication
    """

    # Token to store the result
    result = {"sso_token": None}  # Renamed for clarity
    auth_completed = threading.Event()
    session_data = {}
    
    # Find an available port
    #port = get_free_port(DEFAULT_PORT)
    
    # SSO client configuration
    auth_config = {
        'GLOBODAIN_SSO_URL': sso_url or DEFAULT_SSO_URL,
        'GLOBODAIN_CLIENT_ID': SSO_CLIENT_ID,
        'GLOBODAIN_CLIENT_SECRET': SSO_CLIENT_SECRET,
        'GLOBODAIN_REDIRECT_URI': f"http://localhost:{DEFAULT_PORT}/auth/sso/callback",
        'GLOBODAIN_SUCCESS_REDIRECT': 'https://sso.globodain.com/cli/success'
    }
    
    sso_auth = GlobodainSSOAuth(config=auth_config)
    
    # Factory to create TokenHandler instances with the desired parameters
    def handler_factory(*args, **kwargs):
        return TokenHandler(
            *args,
            sso_auth=sso_auth,
            result=result,
            session_data=session_data,
            auth_completed=auth_completed,
            **kwargs
        )
    
    # Start server in the background
    server = socketserver.TCPServer(("", DEFAULT_PORT), handler_factory)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    try:
        # Build complete URL with protocol if missing
        if sso_url and not sso_url.startswith(("http://", "https://")):
            sso_url = "https://" + sso_url
        
        # URL to start the SSO flow
        login_url = sso_auth.get_login_url()
        auth_url = login_url
        
        print_colored(f"Opening browser for SSO authentication...", "blue")
        print_colored(f"If the browser doesn't open automatically, visit:", "blue")
        print_colored(f"{auth_url}", "bold")
        
        # Try to open the browser
        if not webbrowser.open(auth_url):
            print_colored("Could not open the browser automatically.", "yellow")
            print_colored(f"Please copy and paste the following URL into your browser:", "yellow")
            print_colored(f"{auth_url}", "bold")
        
        # Tell the user to wait
        print_colored("\nWaiting for you to complete authentication in the browser...", "blue")
        
        # Wait for authentication to complete (with timeout)
        timeout_seconds = 60
        start_time = time.time()
        
        # We use a loop with better feedback
        while not auth_completed.is_set() and (time.time() - start_time < timeout_seconds):
            elapsed = int(time.time() - start_time)
            if elapsed % 5 == 0:  # Every 5 seconds we show a message
                remaining = timeout_seconds - elapsed
                #print_colored(f"Waiting for authentication... ({remaining}s remaining)", "yellow")
            
            # Check every 0.5 seconds for better reactivity
            auth_completed.wait(0.5)
        
        # Verify if authentication was completed
        if auth_completed.is_set():
            print_colored("✅ SSO authentication completed successfully!", "green")
            return result["sso_token"], session_data['user']
        else:
            print_colored(f"❌ Could not complete SSO authentication in {timeout_seconds} seconds.", "red")
            print_colored("You can try again or use a token manually.", "yellow")
            return None, None, None
    except Exception as e:
        print_colored(f"❌ Error during SSO authentication: {str(e)}", "red")
        return None, None, None
    finally:
        # Stop the server
        try:
            server.shutdown()
            server.server_close()
        except:
            # If there's any error closing the server, we ignore it
            pass

def authenticate_with_sso_and_api_key_request(sso_url: str) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
    """
    Initiates an SSO authentication flow through the browser and uses the callback system.
    
    Args:
        sso_url: Base URL of the SSO service
    
    Returns:
        Tuple with (api_key, user_data, api_token) or (None, None, None) if it fails
        - api_key: Selected API key to use with the SDK
        - user_data: Authenticated user data
        - api_token: API token obtained from SSO for general authentication
    """
    # Import inside the function to avoid circular dependencies
    from corebrain.cli.auth.api_keys import fetch_api_keys, exchange_sso_token_for_api_token
    
    # Token to store the result
    result = {"sso_token": None}  # Renamed for clarity
    auth_completed = threading.Event()
    session_data = {}
    
    # Find an available port
    #port = get_free_port(DEFAULT_PORT)
    
    # SSO client configuration
    auth_config = {
        'GLOBODAIN_SSO_URL': sso_url or DEFAULT_SSO_URL,
        'GLOBODAIN_CLIENT_ID': SSO_CLIENT_ID,
        'GLOBODAIN_CLIENT_SECRET': SSO_CLIENT_SECRET,
        'GLOBODAIN_REDIRECT_URI': f"http://localhost:{DEFAULT_PORT}/auth/sso/callback",
        'GLOBODAIN_SUCCESS_REDIRECT': 'https://sso.globodain.com/cli/success'
    }
    
    sso_auth = GlobodainSSOAuth(config=auth_config)
    
    # Factory to create TokenHandler instances with the desired parameters
    def handler_factory(*args, **kwargs):
        return TokenHandler(
            *args,
            sso_auth=sso_auth,
            result=result,
            session_data=session_data,
            auth_completed=auth_completed,
            **kwargs
        )
    
    # Start server in the background
    server = socketserver.TCPServer(("", DEFAULT_PORT), handler_factory)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    try:
        # Build complete URL with protocol if missing
        if sso_url and not sso_url.startswith(("http://", "https://")):
            sso_url = "https://" + sso_url
        
        # URL to start the SSO flow
        login_url = sso_auth.get_login_url()
        auth_url = login_url
        
        print_colored(f"Opening browser for SSO authentication...", "blue")
        print_colored(f"If the browser doesn't open automatically, visit:", "blue")
        print_colored(f"{auth_url}", "bold")
        
        # Try to open the browser
        if not webbrowser.open(auth_url):
            print_colored("Could not open the browser automatically.", "yellow")
            print_colored(f"Please copy and paste the following URL into your browser:", "yellow")
            print_colored(f"{auth_url}", "bold")
        
        # Tell the user to wait
        print_colored("\nWaiting for you to complete authentication in the browser...", "blue")
        
        # Wait for authentication to complete (with timeout)
        timeout_seconds = 60
        start_time = time.time()
        
        # We use a loop with better feedback
        while not auth_completed.is_set() and (time.time() - start_time < timeout_seconds):
            elapsed = int(time.time() - start_time)
            if elapsed % 5 == 0:  # Every 5 seconds we show a message
                remaining = timeout_seconds - elapsed
                #print_colored(f"Waiting for authentication... ({remaining}s remaining)", "yellow")
            
            # Check every 0.5 seconds for better reactivity
            auth_completed.wait(0.5)
        
        # Verify if authentication was completed
        if auth_completed.is_set():
            user_data = None
            if 'user' in session_data:
                user_data = session_data['user']
                
                print_colored("✅ SSO authentication completed successfully!", "green")
                
                # Get and select an API key
                api_url = os.environ.get("COREBRAIN_API_URL", DEFAULT_API_URL)
                
                # Now we use the SSO token to get an API token and then the API keys
                # First we verify that we have a token
                if result["sso_token"]:
                    api_token = exchange_sso_token_for_api_token(api_url, result["sso_token"], user_data)
                    
                    if not api_token:
                        print_colored("⚠️ Could not obtain an API Token with the SSO Token", "yellow")
                        return None, None, None
                    
                    # Now that we have the API Token, we get the available API Keys
                    api_key_selected = fetch_api_keys(api_url, api_token, user_data)
                    
                    if api_key_selected:
                        # We return the selected api_key
                        return api_key_selected, user_data, api_token
                    else:
                        print_colored("⚠️ Could not obtain an API Key. Create a new one using the command", "yellow")
                        return None, user_data, api_token
                else:
                    print_colored("❌ No valid token was obtained during authentication.", "red")
                    return None, None, None
            
            # We don't have a token or user data
            print_colored("❌ Authentication did not produce a valid token.", "red")
            return None, None, None
        else:
            print_colored(f"❌ Could not complete SSO authentication in {timeout_seconds} seconds.", "red")
            print_colored("You can try again or use a token manually.", "yellow")
            return None, None, None
    except Exception as e:
        print_colored(f"❌ Error during SSO authentication: {str(e)}", "red")
        return None, None, None
    finally:
        # Stop the server
        try:
            server.shutdown()
            server.server_close()
        except:
            # If there's any error closing the server, we ignore it
            pass