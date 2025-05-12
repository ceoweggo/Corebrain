"""
Cliente HTTP para comunicación con la API de Corebrain.
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
    """Error genérico en la API."""
    def __init__(self, message: str, status_code: Optional[int] = None, 
                detail: Optional[str] = None, response: Optional[Response] = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        self.response = response
        super().__init__(message)

class APITimeoutError(APIError):
    """Error de timeout en la API."""
    pass

class APIConnectionError(APIError):
    """Error de conexión a la API."""
    pass

class APIAuthError(APIError):
    """Error de autenticación en la API."""
    pass

class APIClient:
    """Cliente HTTP optimizado para comunicación con la API de Corebrain."""
    
    # Constantes para manejo de reintentos y errores
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5  # segundos
    RETRY_STATUS_CODES = [408, 429, 500, 502, 503, 504]
    
    def __init__(self, base_url: str, default_timeout: int = 10, 
                verify_ssl: bool = True, user_agent: Optional[str] = None):
        """
        Inicializa el cliente API con configuración optimizada.
        
        Args:
            base_url: URL base para todas las peticiones
            default_timeout: Tiempo de espera predeterminado en segundos
            verify_ssl: Si se debe verificar el certificado SSL
            user_agent: Agente de usuario personalizado
        """
        # Normalizar URL base para asegurar que termina con '/'
        self.base_url = base_url if base_url.endswith('/') else base_url + '/'
        self.default_timeout = default_timeout
        self.verify_ssl = verify_ssl
        
        # Headers predeterminados
        self.default_headers = {
            'User-Agent': user_agent or 'CorebrainSDK/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Crear sesión HTTP con límites y timeouts optimizados
        self.session = httpx.Client(
            timeout=httpx.Timeout(timeout=default_timeout),
            verify=verify_ssl,
            http2=True,  # Usar HTTP/2 si está disponible
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
        
        # Estadísticas y métricas
        self.request_count = 0
        self.error_count = 0
        self.total_request_time = 0
        
        logger.debug(f"Cliente API inicializado con base_url={base_url}, timeout={default_timeout}s")
    
    def __del__(self):
        """Asegurar que la sesión se cierre al eliminar el cliente."""
        self.close()
    
    def close(self):
        """Cierra la sesión HTTP."""
        if hasattr(self, 'session') and self.session:
            try:
                self.session.close()
                logger.debug("Sesión HTTP cerrada correctamente")
            except Exception as e:
                logger.warning(f"Error al cerrar sesión HTTP: {e}")
    
    def get_full_url(self, endpoint: str) -> str:
        """
        Construye la URL completa para un endpoint.
        
        Args:
            endpoint: Ruta relativa del endpoint
            
        Returns:
            URL completa
        """
        # Eliminar '/' inicial si existe para evitar rutas duplicadas
        endpoint = endpoint.lstrip('/')
        return urljoin(self.base_url, endpoint)
    
    def prepare_headers(self, headers: Optional[Dict[str, str]] = None, 
                       auth_token: Optional[str] = None) -> Dict[str, str]:
        """
        Prepara los headers para una petición.
        
        Args:
            headers: Headers adicionales
            auth_token: Token de autenticación
            
        Returns:
            Headers combinados
        """
        # Comenzar con headers predeterminados
        final_headers = self.default_headers.copy()
        
        # Añadir headers personalizados
        if headers:
            final_headers.update(headers)
        
        # Añadir token de autenticación si se proporciona
        if auth_token:
            final_headers['Authorization'] = f'Bearer {auth_token}'
        
        return final_headers
    
    def handle_response(self, response: Response) -> Response:
        """
        Procesa la respuesta para manejar errores comunes.
        
        Args:
            response: Respuesta HTTP
            
        Returns:
            La misma respuesta si no hay errores
            
        Raises:
            APIError: Si hay errores en la respuesta
        """
        status_code = response.status_code
        
        # Procesar errores según código de estado
        if 400 <= status_code < 500:
            error_detail = None
            
            # Intentar extraer detalles del error del cuerpo JSON
            try:
                json_data = response.json()
                if isinstance(json_data, dict):
                    error_detail = (
                        json_data.get('detail') or 
                        json_data.get('message') or 
                        json_data.get('error')
                    )
            except Exception:
                # Si no podemos parsear JSON, usar el texto completo
                error_detail = response.text[:200] + ('...' if len(response.text) > 200 else '')
            
            # Errores específicos según código
            if status_code == 401:
                msg = "Error de autenticación: token inválido o expirado"
                logger.error(f"{msg} - {error_detail or ''}")
                raise APIAuthError(msg, status_code, error_detail, response)
            
            elif status_code == 403:
                msg = "Acceso prohibido: no tienes permisos suficientes"
                logger.error(f"{msg} - {error_detail or ''}")
                raise APIAuthError(msg, status_code, error_detail, response)
            
            elif status_code == 404:
                msg = f"Recurso no encontrado: {response.url}"
                logger.error(msg)
                raise APIError(msg, status_code, error_detail, response)
            
            elif status_code == 429:
                msg = "Demasiadas peticiones: límite de tasa excedido"
                logger.warning(msg)
                raise APIError(msg, status_code, error_detail, response)
            
            else:
                msg = f"Error del cliente ({status_code}): {error_detail or 'sin detalles'}"
                logger.error(msg)
                raise APIError(msg, status_code, error_detail, response)
        
        elif 500 <= status_code < 600:
            msg = f"Error del servidor ({status_code}): el servidor API encontró un error"
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
        Realiza una petición HTTP con manejo de errores y reintentos.
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Ruta relativa del endpoint
            headers: Headers adicionales
            json: Datos para enviar como JSON
            data: Datos para enviar como form o bytes
            params: Parámetros de query string
            timeout: Tiempo de espera en segundos (sobreescribe el predeterminado)
            auth_token: Token de autenticación
            retry: Si se deben reintentar peticiones fallidas
            
        Returns:
            Respuesta HTTP procesada
            
        Raises:
            APIError: Si hay errores en la petición o respuesta
            APITimeoutError: Si la petición excede el tiempo de espera
            APIConnectionError: Si hay errores de conexión
        """
        url = self.get_full_url(endpoint)
        final_headers = self.prepare_headers(headers, auth_token)
        
        # Configurar timeout
        request_timeout = timeout or self.default_timeout
        
        # Contador para reintentos
        retries = 0
        last_error = None
        
        # Registrar inicio de la petición
        start_time = time.time()
        self.request_count += 1
        
        while retries <= (self.MAX_RETRIES if retry else 0):
            try:
                if retries > 0:
                    # Esperar antes de reintentar con backoff exponencial
                    wait_time = self.RETRY_DELAY * (2 ** (retries - 1))
                    logger.info(f"Reintentando petición ({retries}/{self.MAX_RETRIES}) a {url} después de {wait_time:.2f}s")
                    time.sleep(wait_time)
                
                # Realizar la petición
                logger.debug(f"Enviando petición {method} a {url}")
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=final_headers,
                    json=json,
                    data=data,
                    params=params,
                    timeout=request_timeout
                )
                
                # Verificar si debemos reintentar por código de estado
                if response.status_code in self.RETRY_STATUS_CODES and retry and retries < self.MAX_RETRIES:
                    logger.warning(f"Código de estado {response.status_code} recibido, reintentando")
                    retries += 1
                    continue
                
                # Procesar la respuesta
                processed_response = self.handle_response(response)
                
                # Registrar tiempo total
                elapsed = time.time() - start_time
                self.total_request_time += elapsed
                logger.debug(f"Petición completada en {elapsed:.3f}s con estado {response.status_code}")
                
                return processed_response
                
            except (ConnectError, httpx.HTTPError) as e:
                last_error = e
                
                # Decidir si reintentamos dependiendo del tipo de error
                if isinstance(e, (ReadTimeout, WriteTimeout, PoolTimeout, ConnectError)) and retry and retries < self.MAX_RETRIES:
                    logger.warning(f"Error de conexión: {str(e)}, reintentando {retries+1}/{self.MAX_RETRIES}")
                    retries += 1
                    continue
                
                # No más reintentos o error no recuperable
                self.error_count += 1
                elapsed = time.time() - start_time
                
                if isinstance(e, (ReadTimeout, WriteTimeout, PoolTimeout)):
                    logger.error(f"Timeout en petición a {url} después de {elapsed:.3f}s: {str(e)}")
                    raise APITimeoutError(f"La petición a {endpoint} excedió el tiempo máximo de {request_timeout}s", 
                                        response=getattr(e, 'response', None))
                else:
                    logger.error(f"Error de conexión a {url} después de {elapsed:.3f}s: {str(e)}")
                    raise APIConnectionError(f"Error de conexión a {endpoint}: {str(e)}",
                                           response=getattr(e, 'response', None))
                
            except Exception as e:
                # Error inesperado
                self.error_count += 1
                elapsed = time.time() - start_time
                logger.error(f"Error inesperado en petición a {url} después de {elapsed:.3f}s: {str(e)}")
                raise APIError(f"Error inesperado en petición a {endpoint}: {str(e)}")
        
        # Si llegamos aquí es porque agotamos los reintentos
        if last_error:
            self.error_count += 1
            raise APIError(f"Petición a {endpoint} falló después de {retries} reintentos: {str(last_error)}")
        
        # Este punto nunca debería alcanzarse
        raise APIError(f"Error inesperado en petición a {endpoint}")
    
    def get(self, endpoint: str, **kwargs) -> Response:
        """Realiza una petición GET."""
        return self.request("GET", endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> Response:
        """Realiza una petición POST."""
        return self.request("POST", endpoint, **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> Response:
        """Realiza una petición PUT."""
        return self.request("PUT", endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Response:
        """Realiza una petición DELETE."""
        return self.request("DELETE", endpoint, **kwargs)
    
    def patch(self, endpoint: str, **kwargs) -> Response:
        """Realiza una petición PATCH."""
        return self.request("PATCH", endpoint, **kwargs)
    
    def get_json(self, endpoint: str, **kwargs) -> Any:
        """
        Realiza una petición GET y devuelve los datos JSON.
        
        Args:
            endpoint: Endpoint a consultar
            **kwargs: Argumentos adicionales para request()
            
        Returns:
            Datos JSON parseados
        """
        response = self.get(endpoint, **kwargs)
        try:
            return response.json()
        except Exception as e:
            raise APIError(f"Error al parsear respuesta JSON: {str(e)}", response=response)
    
    def post_json(self, endpoint: str, **kwargs) -> Any:
        """
        Realiza una petición POST y devuelve los datos JSON.
        
        Args:
            endpoint: Endpoint a consultar
            **kwargs: Argumentos adicionales para request()
            
        Returns:
            Datos JSON parseados
        """
        response = self.post(endpoint, **kwargs)
        try:
            return response.json()
        except Exception as e:
            raise APIError(f"Error al parsear respuesta JSON: {str(e)}", response=response)
    
    # Métodos de alto nivel para operaciones comunes en la API de Corebrain
    
    def check_health(self, timeout: int = 5) -> bool:
        """
        Comprueba si la API está disponible.
        
        Args:
            timeout: Tiempo máximo de espera
            
        Returns:
            True si la API está disponible
        """
        try:
            response = self.get("health", timeout=timeout, retry=False)
            return response.status_code == 200
        except Exception:
            return False
    
    def verify_token(self, token: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Verifica si un token es válido.
        
        Args:
            token: Token a verificar
            timeout: Tiempo máximo de espera
            
        Returns:
            Información del usuario si el token es válido
            
        Raises:
            APIAuthError: Si el token no es válido
        """
        try:
            response = self.get("api/auth/me", auth_token=token, timeout=timeout)
            return response.json()
        except APIAuthError:
            raise
        except Exception as e:
            raise APIAuthError(f"Error al verificar token: {str(e)}")
    
    def get_api_keys(self, token: str) -> List[Dict[str, Any]]:
        """
        Obtiene las API keys disponibles para un usuario.
        
        Args:
            token: Token de autenticación
            
        Returns:
            Lista de API keys
        """
        return self.get_json("api/auth/api-keys", auth_token=token)
    
    def update_api_key_metadata(self, token: str, api_key: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza los metadatos de una API key.
        
        Args:
            token: Token de autenticación
            api_key: ID de la API key
            metadata: Metadatos a actualizar
            
        Returns:
            Datos actualizados de la API key
        """
        data = {"metadata": metadata}
        return self.put_json(f"api/auth/api-keys/{api_key}", auth_token=token, json=data)
    
    def query_database(self, token: str, question: str, db_schema: Dict[str, Any], 
                     config_id: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Realiza una consulta en lenguaje natural.
        
        Args:
            token: Token de autenticación
            question: Pregunta en lenguaje natural
            db_schema: Esquema de la base de datos
            config_id: ID de la configuración
            timeout: Tiempo máximo de espera
            
        Returns:
            Resultado de la consulta
        """
        data = {
            "question": question,
            "db_schema": db_schema,
            "config_id": config_id
        }
        return self.post_json("api/database/sdk/query", auth_token=token, json=data, timeout=timeout)
    
    def exchange_sso_token(self, sso_token: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intercambia un token SSO por un token API.
        
        Args:
            sso_token: Token SSO
            user_data: Datos del usuario
            
        Returns:
            Datos del token API
        """
        headers = {"Authorization": f"Bearer {sso_token}"}
        data = {"user_data": user_data}
        return self.post_json("api/auth/sso/token", headers=headers, json=data)
    
    # Métodos para estadísticas y diagnóstico
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso del cliente.
        
        Returns:
            Estadísticas de peticiones
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
        """Resetea las estadísticas de uso."""
        self.request_count = 0
        self.error_count = 0
        self.total_request_time = 0