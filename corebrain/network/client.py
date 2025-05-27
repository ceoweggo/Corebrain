"""
HTTP client for communication with the Corebrain API.
"""
import time
import logging
import httpx

from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
from httpx import Response, ConnectError, ReadTimeout, WriteTimeout, PoolTimeout

logger = logging.getLogger(__name__)
http_session = httpx.Client(timeout=10.0, verify=True)

def __init__(self, verbose=False):
    self.verbose = verbose

class APIError(Exception):
    """Generic error in the API."""
    def __init__(self, message: str, status_code: Optional[int] = None, 
                detail: Optional[str] = None, response: Optional[Response] = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        self.response = response
        super().__init__(message)

class APITimeoutError(APIError):
    """Timeout error in the API."""
    pass

class APIConnectionError(APIError):
    """Connection error to the API."""
    pass

class APIAuthError(APIError):
    """Authentication error in the API."""
    pass

class APIClient:
    """Optimized HTTP client for communication with the Corebrain API."""
    
    # Constants for retry handling and errors
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5  # segundos
    RETRY_STATUS_CODES = [408, 429, 500, 502, 503, 504]
    
    def __init__(self, base_url: str, default_timeout: int = 10, 
                verify_ssl: bool = True, user_agent: Optional[str] = None):
        """
        Initializes the API client with optimized configuration.

        Args:
            base_url: Base URL for all requests
            default_timeout: Default timeout in seconds
            verify_ssl: Whether to verify the SSL certificate
            user_agent: Custom user agent
        """
        # Normalize base URL to ensure it ends with '/'
        self.base_url = base_url if base_url.endswith('/') else base_url + '/'
        self.default_timeout = default_timeout
        self.verify_ssl = verify_ssl
        
        # Default headers
        self.default_headers = {
            'User-Agent': user_agent or 'CorebrainSDK/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Create HTTP session with optimized limits and timeouts
        self.session = httpx.Client(
            timeout=httpx.Timeout(timeout=default_timeout),
            verify=verify_ssl,
            http2=True,  # Use HTTP/2 if available
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
        
        # Statistics and metrics
        self.request_count = 0
        self.error_count = 0
        self.total_request_time = 0
        
        logger.debug(f"API Client initialized with base_url={base_url}, timeout={default_timeout}s")
    
    def __del__(self):
        """Ensure the session is closed when the client is deleted."""
        self.close()
    
    def close(self):
        """Closes the HTTP session."""
        if hasattr(self, 'session') and self.session:
            try:
                self.session.close()
                logger.debug("HTTP session closed correctly")
            except Exception as e:
                logger.warning(f"Error closing HTTP session: {e}")
    
    def get_full_url(self, endpoint: str) -> str:
        """
        Builds the full URL for an endpoint.

        Args:
            endpoint: Relative path of the endpoint

        Returns:
            Full URL
        """
        # Remove '/' if it exists at the beginning to avoid duplicate paths
        endpoint = endpoint.lstrip('/')
        return urljoin(self.base_url, endpoint)
    
    def prepare_headers(self, headers: Optional[Dict[str, str]] = None, 
                       auth_token: Optional[str] = None) -> Dict[str, str]:
        """
        Prepares the headers for a request.

        Args:
            headers: Additional headers
            auth_token: Authentication token

        Returns:
            Combined headers
        """
        # Start with default headers
        final_headers = self.default_headers.copy()
        
        # Add custom headers
        if headers:
            final_headers.update(headers)
        
        # Add authentication token if provided
        if auth_token:
            final_headers['Authorization'] = f'Bearer {auth_token}'
        
        return final_headers
    
    def handle_response(self, response: Response) -> Response:
        """
        Processes the response to handle common errors.

        Args:
            response: HTTP response

        Returns:
            The same response if there are no errors

        Raises:
            APIError: If there are errors in the response
        """
        status_code = response.status_code
        
        # Process errors according to status code
        if 400 <= status_code < 500:
            error_detail = None
            
            # Try to extract error details from JSON body
            try:
                json_data = response.json()
                if isinstance(json_data, dict):
                    error_detail = (
                        json_data.get('detail') or 
                        json_data.get('message') or 
                        json_data.get('error')
                    )
            except Exception:
                # If we can't parse JSON, use the full text
                error_detail = response.text[:200] + ('...' if len(response.text) > 200 else '')
            
            # Specific errors according to code
            if status_code == 401:
                msg = "Authentication error: invalid or expired token"
                logger.error(f"{msg} - {error_detail or ''}")
                raise APIAuthError(msg, status_code, error_detail, response)
            
            elif status_code == 403:
                msg = "Access denied: you don't have enough permissions"
                logger.error(f"{msg} - {error_detail or ''}")
                raise APIAuthError(msg, status_code, error_detail, response)
            
            elif status_code == 404:
                msg = f"Resource not found: {response.url}"
                logger.error(msg)
                raise APIError(msg, status_code, error_detail, response)
            
            elif status_code == 429:
                msg = "Too many requests: rate limit exceeded"
                logger.warning(msg)
                raise APIError(msg, status_code, error_detail, response)
            
            else:
                msg = f"Client error ({status_code}): {error_detail or 'no details'}"
                logger.error(msg)
                raise APIError(msg, status_code, error_detail, response)
        
        elif 500 <= status_code < 600:
            msg = f"Server error ({status_code}): the API server found an error"
            logger.error(msg)
            raise APIError(msg, status_code, response.text[:200], response)
        
        return response
    
    def request(self, method: str, endpoint: str, *, 
               headers: Optional[Dict[str, str]] = None, 
               json: Optional[Any] = None, 
               data: Optional[Any] = None,
               params: Optional[Dict[str, Any]] = None, 
               timeout: Optional[int] = None, 
               auth_token: Optional[str] = None,
               retry: bool = True) -> Response:
        """
        Makes an HTTP request with error handling and retries.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: Relative path of the endpoint
            headers: Additional headers
            json: Data to send as JSON
            data: Data to send as form or bytes
            params: Query string parameters
            timeout: Timeout in seconds (overrides the default)
            auth_token: Authentication token
            retry: Whether to retry failed requests

        Returns:
            Processed HTTP response

        Raises:
            APIError: If there are errors in the request or response
            APITimeoutError: If the request exceeds the timeout
            APIConnectionError: If there are connection errors
        """
        url = self.get_full_url(endpoint)
        final_headers = self.prepare_headers(headers, auth_token)
        
        # Set timeout
        request_timeout = timeout or self.default_timeout
        
        # Retry counter
        retries = 0
        last_error = None
        
        # Register start of request
        start_time = time.time()
        self.request_count += 1
        
        while retries <= (self.MAX_RETRIES if retry else 0):
            try:
                if retries > 0:
                    # Wait before retrying with exponential backoff
                    wait_time = self.RETRY_DELAY * (2 ** (retries - 1))
                    logger.info(f"Retrying request ({retries}/{self.MAX_RETRIES}) to {url} after {wait_time:.2f}s")
                    time.sleep(wait_time)
                
                # Make the request
                logger.debug(f"Sending {method} request to {url}")
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=final_headers,
                    json=json,
                    data=data,
                    params=params,
                    timeout=request_timeout
                )
                
                # Check if we should retry by status code
                if response.status_code in self.RETRY_STATUS_CODES and retry and retries < self.MAX_RETRIES:
                    logger.warning(f"Status code {response.status_code} received, retrying")
                    retries += 1
                    continue
                
                # Process the response
                processed_response = self.handle_response(response)
                
                # Register total time
                elapsed = time.time() - start_time
                self.total_request_time += elapsed
                logger.debug(f"Petición completada en {elapsed:.3f}s con estado {response.status_code}")
                
                return processed_response
                
            except (ConnectError, httpx.HTTPError) as e:
                last_error = e
                
                # Decide if we should retry depending on the error type
                if isinstance(e, (ReadTimeout, WriteTimeout, PoolTimeout, ConnectError)) and retry and retries < self.MAX_RETRIES:
                    logger.warning(f"Connection error: {str(e)}, retrying {retries+1}/{self.MAX_RETRIES}")
                    retries += 1
                    continue
                
                # No more retries or unrecoverable errors
                self.error_count += 1
                elapsed = time.time() - start_time
                
                if isinstance(e, (ReadTimeout, WriteTimeout, PoolTimeout)):
                    logger.error(f"Timeout in request to {url} after {elapsed:.3f}s: {str(e)}")
                    raise APITimeoutError(f"Request to {endpoint} exceeded the maximum time of {request_timeout}s", 
                                        response=getattr(e, 'response', None))
                else:
                    logger.error(f"Connection error to {url} after {elapsed:.3f}s: {str(e)}")
                    raise APIConnectionError(f"Connection error to {endpoint}: {str(e)}",
                                           response=getattr(e, 'response', None))
                
            except Exception as e:
                # Unexpected error
                self.error_count += 1
                elapsed = time.time() - start_time
                logger.error(f"Unexpected error in request to {url} after {elapsed:.3f}s: {str(e)}")
                raise APIError(f"Unexpected error in request to {endpoint}: {str(e)}")
        
        # If we get here, we have exhausted the retries
        if last_error:
            self.error_count += 1
            raise APIError(f"Request to {endpoint} failed after {retries} retries: {str(last_error)}")
        
        # This point should never be reached
        raise APIError(f"Unexpected error in request to {endpoint}")
    
    def get(self, endpoint: str, **kwargs) -> Response:
        """Makes a GET request."""
        return self.request("GET", endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> Response:
        """Makes a POST request."""
        return self.request("POST", endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> Response:
        """Makes a PUT request."""
        return self.request("PUT", endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Response:
        """Makes a DELETE request."""
        return self.request("DELETE", endpoint, **kwargs)
    
    def patch(self, endpoint: str, **kwargs) -> Response:
        """Makes a PATCH request."""
        return self.request("PATCH", endpoint, **kwargs)
    
    def get_json(self, endpoint: str, **kwargs) -> Any:
        """
        Makes a GET request and returns the JSON data.

        Args:
            endpoint: Endpoint to query
            **kwargs: Additional arguments for request()

        Returns:
            Parsed JSON data
        """
        response = self.get(endpoint, **kwargs)
        try:
            return response.json()
        except Exception as e:
            raise APIError(f"Error parsing JSON response: {str(e)}", response=response)
    
    def post_json(self, endpoint: str, **kwargs) -> Any:
        """
        Makes a POST request and returns the JSON data.

        Args:
            endpoint: Endpoint to query
            **kwargs: Additional arguments for request()

        Returns:
            Parsed JSON data
        """
        response = self.post(endpoint, **kwargs)
        try:
            return response.json()
        except Exception as e:
            raise APIError(f"Error parsing JSON response: {str(e)}", response=response)
    
    # High-level methods for common operations in the Corebrain API
    
    def check_health(self, timeout: int = 5) -> bool:
        """
        Checks if the API is available.

        Args:
            timeout: Maximum wait time

        Returns:
            True if the API is available
        """
        try:
            response = self.get("health", timeout=timeout, retry=False)
            return response.status_code == 200
        except Exception:
            return False
    
    def verify_token(self, token: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Verifies if a token is valid.

        Args:
            token: Token to verify
            timeout: Maximum wait time

        Returns:
            User information if the token is valid

        Raises:
            APIAuthError: If the token is invalid
        """
        try:
            response = self.get("api/auth/me", auth_token=token, timeout=timeout)
            return response.json()
        except APIAuthError:
            raise
        except Exception as e:
            raise APIAuthError(f"Error verifying token: {str(e)}")
    
    def get_api_keys(self, token: str) -> List[Dict[str, Any]]:
        """
        Retrieves the available API keys for a user.

        Args:
            token: Authentication token

        Returns:
            List of API keys
        """
        return self.get_json("api/auth/api-keys", auth_token=token)
    
    def update_api_key_metadata(self, token: str, api_key: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates the metadata of an API key.

        Args:
            token: Authentication token
            api_key: API key ID
            metadata: Metadata to update

        Returns:
            Updated API key data
        """
        data = {"metadata": metadata}
        return self.put_json(f"api/auth/api-keys/{api_key}", auth_token=token, json=data)
    
    def query_database(self, token: str, question: str, db_schema: Dict[str, Any], 
                     config_id: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Makes a natural language query.

        Args:
            token: Authentication token
            question: Natural language question
            db_schema: Database schema
            config_id: Configuration ID
            timeout: Maximum wait time

        Returns:
            Query result
        """
        data = {
            "question": question,
            "db_schema": db_schema,
            "config_id": config_id
        }
        return self.post_json("api/database/sdk/query", auth_token=token, json=data, timeout=timeout)
    
    def exchange_sso_token(self, sso_token: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exchanges an SSO token for an API token.

        Args:
            sso_token: SSO token
            user_data: User data

        Returns:
            API token data
        """
        headers = {"Authorization": f"Bearer {sso_token}"}
        data = {"user_data": user_data}
        return self.post_json("api/auth/sso/token", headers=headers, json=data)
    
    # Methods for statistics and diagnostics
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retrieves client usage statistics.

        Returns:
            Request statistics
        """
        avg_time = self.total_request_time / max(1, self.request_count)
        error_rate = (self.error_count / max(1, self.request_count)) * 100
        
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": f"{error_rate:.2f}%",
            "total_request_time": f"{self.total_request_time:.3f}s",
            "average_request_time": f"{avg_time:.3f}s",
        }
    
    def reset_stats(self) -> None:
        """Resets the usage statistics."""
        self.request_count = 0
        self.error_count = 0
        self.total_request_time = 0