import requests
import logging
from urllib.parse import urlencode

class GlobodainSSOAuth:
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Configuración por defecto
        self.sso_url = self.config.get('GLOBODAIN_SSO_URL', 'http://localhost:3000/login') # URL del SSO
        self.client_id = self.config.get('GLOBODAIN_CLIENT_ID', '')
        self.client_secret = self.config.get('GLOBODAIN_CLIENT_SECRET', '')
        self.redirect_uri = self.config.get('GLOBODAIN_REDIRECT_URI', '')
        self.success_redirect = self.config.get('GLOBODAIN_SUCCESS_REDIRECT', 'https://sso.globodain.com/cli/success')
    
    def requires_auth(self, session_handler):
        """
        Decorador genérico que verifica si el usuario está autenticado
        
        Args:
            session_handler: Función que obtiene el objeto de sesión actual
            
        Returns:
            Una función decoradora que puede aplicarse a rutas/vistas
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Obtener la sesión actual usando el manejador proporcionado
                session = session_handler()
                
                if 'user' not in session:
                    # Aquí retornamos información para que el framework redirija
                    return {
                        'authenticated': False,
                        'redirect_url': self.get_login_url()
                    }
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def get_login_url(self, state=None):
        """
        Genera la URL para iniciar la autenticación SSO
        
        Args:
            state: Parámetro opcional para mantener estado entre solicitudes
            
        Returns:
            URL completa para el inicio de sesión SSO
        """
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
        }
        
        if state:
            params['state'] = state
            
        return f"{self.sso_url}/api/auth/authorize?{urlencode(params)}"
    
    def verify_token(self, token):
        """
        Verifica el token con el servidor SSO
        
        Args:
            token: Token de acceso a verificar
            
        Returns:
            Datos del token si es válido, None en caso contrario
        """
        try:
            response = requests.post(
                f"{self.sso_url}/api/auth/service-auth",
                headers={'Authorization': f'Bearer {token}'},
                json={'service_id': self.client_id}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.logger.error(f"Error verificando token: {str(e)}")
            return None
    
    def get_user_info(self, token):
        """
        Obtiene información del usuario con el token
        
        Args:
            token: Token de acceso del usuario
            
        Returns:
            Información del perfil del usuario si el token es válido, None en caso contrario
        """
        try:
            response = requests.get(
                f"{self.sso_url}/api/users/me/profile",
                headers={'Authorization': f'Bearer {token}'}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.logger.error(f"Error obteniendo info de usuario: {str(e)}")
            return None
    
    def exchange_code_for_token(self, code):
        """
        Intercambia el código de autorización por un token de acceso
        
        Args:
            code: Código de autorización recibido del servidor SSO
            
        Returns:
            Datos del token de acceso si el intercambio es exitoso, None en caso contrario
        """
        try:
            response = requests.post(
                f"{self.sso_url}/api/auth/token",
                json={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'code': code,
                    'grant_type': 'authorization_code',
                    'redirect_uri': self.redirect_uri
                }
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.logger.error(f"Error intercambiando código: {str(e)}")
            return None

    def handle_callback(self, code, session_handler, store_user_func=None):
        """
        Maneja el callback del SSO procesando el código recibido
        
        Args:
            code: Código de autorización recibido
            session_handler: Función que obtiene el objeto de sesión actual
            store_user_func: Función opcional para almacenar datos de usuario en otro lugar
            
        Returns:
            URL de redirección después de procesar el código
        """
        # Intercambiar código por token
        token_data = self.exchange_code_for_token(code)
        if not token_data:
            # Error al obtener el token
            return self.get_login_url()
        
        # Obtener información del usuario
        user_info = self.get_user_info(token_data.get('access_token'))
        if not user_info:
            # Error al obtener información del usuario
            return self.get_login_url()
        
        # Guardar información en la sesión
        session = session_handler()
        session['user'] = user_info
        session['token'] = token_data
        
        # Si hay una función para almacenar el usuario, ejecutarla
        if store_user_func and callable(store_user_func):
            store_user_func(user_info, token_data)
        
        # Redirigir a la URL de éxito o a la URL guardada anteriormente
        next_url = session.pop('next_url', self.success_redirect)
        return next_url