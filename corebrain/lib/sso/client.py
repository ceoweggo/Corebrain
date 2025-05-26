# /auth/sso_client.py
import requests

from typing import Dict, Any
from datetime import datetime, timedelta

class GlobodainSSOClient:
    """
    SDK client for Globodain services that connect to the central SSO
    """
    
    def __init__(
        self, 
        sso_url: str, 
        client_id: str, 
        client_secret: str, 
        service_id: int,
        redirect_uri: str
    ):
        """
        Initialize the SSO client

        Args:
            sso_url: Base URL of the SSO service (e.g., https://sso.globodain.com)
            client_id: Client ID of the service
            client_secret: Client secret of the service
            service_id: Numeric ID of the service on the SSO platform
            redirect_uri: Redirect URI for OAuth
        """
        self.sso_url = sso_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.service_id = service_id
        self.redirect_uri = redirect_uri
        self._token_cache = {}  # Cache de tokens verificados
        

    def get_login_url(self, provider: str = None) -> str:
        """
        Get URL to initiate SSO login

        Args:
            provider: OAuth provider (google, microsoft, github) or None for normal login

        Returns:
            URL to redirect the user
        """
        if provider:
            return f"{self.sso_url}/api/auth/oauth/{provider}?service_id={self.service_id}"
        else:
            return f"{self.sso_url}/login?service_id={self.service_id}&redirect_uri={self.redirect_uri}"
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify an access token and retrieve user information

        Args:
            token: JWT token to verify

        Returns:
            User information if the token is valid

        Raises:
            Exception: If the token is not valid
        """
        # Verificar si ya tenemos información cacheada y válida del token
        now = datetime.now()
        if token in self._token_cache:
            cache_data = self._token_cache[token]
            if cache_data['expires_at'] > now:
                return cache_data['user_info']
            else:
                # Eliminar token expirado del caché
                del self._token_cache[token]
        
        # Verificar token con el servicio SSO
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{self.sso_url}/api/auth/service-auth",
            headers=headers,
            json={"service_id": self.service_id}
        )
        
        if response.status_code != 200:
            raise Exception(f"Token inválido: {response.text}")
        
        # Obtener información del usuario
        user_response = requests.get(
            f"{self.sso_url}/api/users/me",
            headers=headers
        )
        
        if user_response.status_code != 200:
            raise Exception(f"Error al obtener información del usuario: {user_response.text}")
        
        user_info = user_response.json()
        
        # Guardar en caché (15 minutos)
        self._token_cache[token] = {
            'user_info': user_info,
            'expires_at': now + timedelta(minutes=15)
        }
        
        return user_info
    
    def authenticate_service(self, token: str) -> Dict[str, Any]:
        """
        Authenticate a token for use with this specific service

        Args:
            token: JWT token obtained from the SSO

        Returns:
            New service-specific token

        Raises:
            Exception: If there is an authentication error
        """
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{self.sso_url}/api/auth/service-auth",
            headers=headers,
            json={"service_id": self.service_id}
        )
        
        if response.status_code != 200:
            raise Exception(f"Error de autenticación: {response.text}")
        
        return response.json()
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Renew an access token using a refresh token

        Args:
            refresh_token: Refresh token

        Returns:
            New access token

        Raises:
            Exception: If there is an error renewing the token
        """
        response = requests.post(
            f"{self.sso_url}/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        if response.status_code != 200:
            raise Exception(f"Error al renovar token: {response.text}")
        
        return response.json()
    
    def logout(self, refresh_token: str, access_token: str) -> bool:
        """
        Log out (revoke refresh token)

        Args:
            refresh_token: Refresh token to revoke
            access_token: Valid access token

        Returns:
            True if the logout was successful

        Raises:
            Exception: If there is an error logging out
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{self.sso_url}/api/auth/logout",
            headers=headers,
            json={"refresh_token": refresh_token}
        )
        
        if response.status_code != 200:
            raise Exception(f"Error al cerrar sesión: {response.text}")
        
        # Limpiar cualquier token cacheado
        if access_token in self._token_cache:
            del self._token_cache[access_token]
        
        return True