# /auth/sso_client.py
import requests

from typing import Dict, Any
from datetime import datetime, timedelta

class GlobodainSSOClient:
    """
    Cliente SDK para servicios de Globodain que se conectan al SSO central
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
        Inicializar el cliente SSO
        
        Args:
            sso_url: URL base del servicio SSO (ej: https://sso.globodain.com)
            client_id: ID de cliente del servicio
            client_secret: Secreto de cliente del servicio
            service_id: ID numérico del servicio en la plataforma SSO
            redirect_uri: URI de redirección para OAuth
        """
        self.sso_url = sso_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.service_id = service_id
        self.redirect_uri = redirect_uri
        self._token_cache = {}  # Cache de tokens verificados
        

    def get_login_url(self, provider: str = None) -> str:
        """
        Obtener URL para iniciar sesión en SSO
        
        Args:
            provider: Proveedor de OAuth (google, microsoft, github) o None para login normal
            
        Returns:
            URL para redireccionar al usuario
        """
        if provider:
            return f"{self.sso_url}/api/auth/oauth/{provider}?service_id={self.service_id}"
        else:
            return f"{self.sso_url}/login?service_id={self.service_id}&redirect_uri={self.redirect_uri}"
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verificar un token de acceso y obtener información del usuario
        
        Args:
            token: Token JWT a verificar
            
        Returns:
            Información del usuario si el token es válido
            
        Raises:
            Exception: Si el token no es válido
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
        Autenticar un token para usarlo con este servicio específico
        
        Args:
            token: Token JWT obtenido del SSO
            
        Returns:
            Nuevo token específico para el servicio
            
        Raises:
            Exception: Si hay un error en la autenticación
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
        Renovar un token de acceso usando refresh token
        
        Args:
            refresh_token: Token de refresco
            
        Returns:
            Nuevo token de acceso
            
        Raises:
            Exception: Si hay un error al renovar el token
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
        Cerrar sesión (revoca refresh token)
        
        Args:
            refresh_token: Token de refresco a revocar
            access_token: Token de acceso válido
            
        Returns:
            True si se cerró sesión correctamente
            
        Raises:
            Exception: Si hay un error al cerrar sesión
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