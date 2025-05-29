"""
API Keys Management for the CLI.
"""
import uuid
import httpx

from typing import Optional, Dict, Any, Tuple

from corebrain.cli.utils import print_colored
from corebrain.network.client import http_session
from corebrain.core.client import Corebrain

def verify_api_token(token: str, api_url: Optional[str] = None, user_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:    
    """
    Verifies if an API token is valid.

    Args:
        token (str): API token to verify.
        api_url (str, optional): API URL. Defaults to None.
        user_data (dict, optional): User data. Defaults to None.

    Returns:
        tuple: (validity (bool), user information (dict)) if valid, else (False, None).
    """
    try:
        # Create a temporary SDK instance to verify the token
        config = {"type": "test", "config_id": str(uuid.uuid4())}
        kwargs = {"api_token": token, "db_config": config}
        
        if user_data:
            kwargs["user_data"] = user_data
            
        if api_url:
            kwargs["api_url"] = api_url
        
        sdk = Corebrain(**kwargs)
        return True, sdk.user_info
    except Exception as e:
        print_colored(f"Error verifying API token: {str(e)}", "red")
        return False, None

def fetch_api_keys(api_url: str, api_token: str, user_data: Dict[str, Any]) -> Optional[str]:
    """
    Retrieves the available API keys for the user and allows selecting one.
    
    Args:
        api_url: Base URL of the Corebrain API
        api_token: API token (exchanged from SSO token)
        user_data: User data
        
    Returns:
        Selected API key or None if none is selected
    """
    if not user_data or 'id' not in user_data:
        print_colored("Could not identify the user to retrieve their API keys.", "yellow")
        return None
    
    try:
        # Ensure protocol in URL
        if not api_url.startswith(("http://", "https://")):
            api_url = "https://" + api_url
        
        # Remove trailing slash if it exists
        if api_url.endswith('/'):
            api_url = api_url[:-1]
        
        # Build endpoint to get API keys
        endpoint = f"{api_url}/api/auth/api-keys"
        
        print_colored(f"Requesting user's API keys...", "blue")
        
        # Configure client with timeout and error handling
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        response = http_session.get(endpoint, headers=headers)
        
        # Verify response
        if response.status_code == 200:
            try:
                api_keys_data = response.json()
                # Verify response format
                if not isinstance(api_keys_data, (list, dict)):
                    print_colored(f"Unexpected response format: {type(api_keys_data)}", "yellow")
                    return None
                
                # Handle both direct list and dictionary with list
                api_keys = api_keys_data if isinstance(api_keys_data, list) else api_keys_data.get("data", [])
                
                if not api_keys:
                    print_colored("No API keys available for this user.", "yellow")
                    return None
                
                print_colored(f"\nFound {len(api_keys)} API keys", "green")
                print_colored("\n=== Available API Keys ===", "blue")
                
                # Show available API keys
                for i, key_info in enumerate(api_keys, 1):
                    key_id = key_info.get('id', 'No ID')
                    key_value = key_info.get('key', 'No value')
                    key_name = key_info.get('name', 'No name')
                    key_active = key_info.get('active')
                    
                    # Show status with color
                    status_color = "green" if key_active == True else "red"
                    status_text = "Active" if key_active == True else "Inactive"
                    
                    print(f"{i}. {key_name} - {print_colored(status_text, status_color, return_str=True)} (Value: {key_value})")
                
                # Ask user to select an API key
                while True:
                    try:
                        choice = input(f"\nSelect an API key (1-{len(api_keys)}) or press Enter to cancel: ").strip()
                        
                        # Allow canceling and using API token
                        if not choice:
                            print_colored("No API key selected.", "yellow")
                            return None
                            
                        choice_num = int(choice)
                        if 1 <= choice_num <= len(api_keys):
                            selected_key = api_keys[choice_num - 1]
                            
                            # Verify if the key is active
                            if selected_key.get('active') != True:
                                print_colored("⚠️ The selected API key is not active. Select another one.", "yellow")
                                continue
                            
                            # Get information of the selected key
                            key_name = selected_key.get('name', 'Unknown')
                            key_value = selected_key.get('key', None)
                            
                            if not key_value:
                                print_colored("⚠️ The selected API key does not have a valid value.", "yellow")
                                continue
                                
                            print_colored(f"✅ You selected: {key_name}", "green")
                            print_colored("Wait while we assign the API key to your SDK...", "yellow")
                            
                            return key_value
                        else:
                            print_colored("Invalid option. Try again.", "red")
                    except ValueError:
                        print_colored("Please enter a valid number.", "red")
            except Exception as e:
                print_colored(f"Error processing JSON response: {str(e)}", "red")
                return None
        else:
            # Handle error by status code
            error_message = f"Error retrieving API keys: {response.status_code}"
            
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_message += f" - {error_data['message']}"
                elif "detail" in error_data:
                    error_message += f" - {error_data['detail']}"
            except:
                # If we can't parse JSON, use the full text
                error_message += f" - {response.text[:100]}..."
                
            print_colored(error_message, "red")
            
            # Try to identify common problems
            if response.status_code == 401:
                print_colored("The authentication token has expired or is invalid.", "yellow")
            elif response.status_code == 403:
                print_colored("You don't have permissions to access the API keys.", "yellow")
            elif response.status_code == 404:
                print_colored("The API keys endpoint doesn't exist. Verify the API URL.", "yellow")
            elif response.status_code >= 500:
                print_colored("Server error. Try again later.", "yellow")
                
            return None
    
    except httpx.RequestError as e:
        print_colored(f"Connection error: {str(e)}", "red")
        print_colored("Verify the API URL and your internet connection.", "yellow")
        return None
    except Exception as e:
        print_colored(f"Unexpected error retrieving API keys: {str(e)}", "red")
        return None

def get_api_key_id_from_token(sso_token: str, api_token: str, api_url: str) -> Optional[str]:
    """
    Gets the ID of an API key from its token.
    
    Args:
        sso_token: SSO token
        api_token: API token
        api_url: API URL
        
    Returns:
        API key ID or None if it cannot be obtained
    """
    try:
        # Endpoint to get information of the current user
        endpoint = f"{api_url}/api/auth/api-keys/{api_token}"
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        response = httpx.get(
            endpoint,
            headers=headers
        )
        
        print("API keys response: ", response.json())
        
        if response.status_code == 200:
            key_data = response.json()
            key_id = key_data.get("id")
            return key_id
        else:
            print_colored("⚠️ Could not find the API key ID", "yellow")
            return None
            
    except Exception as e:
        print_colored(f"Error getting API key ID: {str(e)}", "red")
        return None

def exchange_sso_token_for_api_token(api_url: str, sso_token: str, user_data: Dict[str, Any]) -> Optional[str]:
    """
    Exchanges a Globodain SSO token for a Corebrain API token.
    
    Args:
        api_url: Base URL of the Corebrain API
        sso_token: Globodain SSO token
        user_data: User data
        
    Returns:
        API token or None if it fails
    """
    try:
        # Ensure protocol in URL
        if not api_url.startswith(("http://", "https://")):
            api_url = "https://" + api_url
        
        # Remove trailing slash if it exists
        if api_url.endswith('/'):
            api_url = api_url[:-1]
        
        # Endpoint to exchange token
        endpoint = f"{api_url}/api/auth/sso/token"
        
        print_colored(f"Exchanging SSO token for API token...", "blue")
        
        # Configure client with timeout and error handling
        headers = {
            'Authorization': f'Bearer {sso_token}',
            'Content-Type': 'application/json'
        }
        body = {
            "user_data": user_data
        }
            
        response = http_session.post(endpoint, json=body, headers=headers)
        
        if response.status_code == 200:
            try:
                token_data = response.json()
                api_token = token_data.get("access_token")
                
                if not api_token:
                    print_colored("The response does not contain a valid API token", "red")
                    return None
                
                print_colored("✅ API token successfully obtained", "green")
                return api_token
            except Exception as e:
                print_colored(f"Error processing JSON response: {str(e)}", "red")
                return None
        else:
            # Handle error by status code
            error_message = f"Error exchanging token: {response.status_code}"
            
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_message += f" - {error_data['message']}"
                elif "detail" in error_data:
                    error_message += f" - {error_data['detail']}"
            except:
                # If we can't parse JSON, use the full text
                error_message += f" - {response.text[:100]}..."
                
            print_colored(error_message, "red")
            return None
    
    except httpx.RequestError as e:
        print_colored(f"Connection error: {str(e)}", "red")
        return None
    except Exception as e:
        print_colored(f"Unexpected error exchanging token: {str(e)}", "red")
        return None