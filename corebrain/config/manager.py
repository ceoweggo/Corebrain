"""
Gestor de configuraciones para Corebrain SDK.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from cryptography.fernet import Fernet

from corebrain.utils.serializer import serialize_to_json
from corebrain.core.common import logger

# Función para imprimir mensajes coloreados
def _print_colored(message: str, color: str) -> None:
    """Versión simplificada de _print_colored que no depende de cli.utils"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "default": "\033[0m"
    }
    color_code = colors.get(color, colors["default"])
    print(f"{color_code}{message}{colors['default']}")

class ConfigManager:
    """Gestor de configuraciones del SDK con seguridad y rendimiento mejorados"""
    
    CONFIG_DIR = Path.home() / ".corebrain"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    SECRET_KEY_FILE = CONFIG_DIR / "secret.key"
    
    def __init__(self):
        self.configs = {}
        self.cipher = None
        self._ensure_config_dir()
        self._load_secret_key()
        self._load_configs()
    
    def _ensure_config_dir(self) -> None:
        """Asegura que existe el directorio de configuración."""
        try:
            self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directorio de configuración asegurado: {self.CONFIG_DIR}")
            _print_colored(f"Directorio de configuración asegurado: {self.CONFIG_DIR}", "blue")
        except Exception as e:
            logger.error(f"Error al crear directorio de configuración: {str(e)}")
            _print_colored(f"Error al crear directorio de configuración: {str(e)}", "red")
    
    def _load_secret_key(self) -> None:
        """Carga o genera la clave secreta para encriptar datos sensibles."""
        try:
            if not self.SECRET_KEY_FILE.exists():
                key = Fernet.generate_key()
                with open(self.SECRET_KEY_FILE, 'wb') as key_file:
                    key_file.write(key)
                _print_colored(f"Nueva clave secreta generada en: {self.SECRET_KEY_FILE}", "green")
            
            with open(self.SECRET_KEY_FILE, 'rb') as key_file:
                self.secret_key = key_file.read()
            
            self.cipher = Fernet(self.secret_key)
        except Exception as e:
            _print_colored(f"Error al cargar/generar clave secreta: {str(e)}", "red")
            # Fallback a una clave temporal (menos segura pero funcional)
            self.secret_key = Fernet.generate_key()
            self.cipher = Fernet(self.secret_key)
    
    def _load_configs(self) -> Dict[str, Dict[str, Any]]:
        """Carga las configuraciones guardadas."""
        if not self.CONFIG_FILE.exists():
            _print_colored(f"Archivo de configuración no encontrado: {self.CONFIG_FILE}", "yellow")
            return {}
        
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                encrypted_data = f.read()
            
            if not encrypted_data:
                _print_colored("Archivo de configuración vacío", "yellow")
                return {}
            
            try:
                # Intentar descifrar los datos
                decrypted_data = self.cipher.decrypt(encrypted_data.encode()).decode()
                configs = json.loads(decrypted_data)
            except Exception as e:
                # Si falla el descifrado, intentar cargar como JSON plano
                logger.warning(f"Error al descifrar configuración: {e}")
                configs = json.loads(encrypted_data)
            
            if isinstance(configs, str):
                configs = json.loads(configs)
            
            _print_colored(f"Configuración cargada", "green")
            self.configs = configs
            return configs
        except Exception as e:
            _print_colored(f"Error al cargar configuraciones: {str(e)}", "red")
            return {}
    
    def _save_configs(self) -> None:
        """Guarda las configuraciones actuales."""
        try:
            configs_json = serialize_to_json(self.configs)
            encrypted_data = self.cipher.encrypt(json.dumps(configs_json).encode()).decode()
            
            with open(self.CONFIG_FILE, 'w') as f:
                f.write(encrypted_data)
                
            _print_colored(f"Configuraciones guardadas en: {self.CONFIG_FILE}", "green")
        except Exception as e:
            _print_colored(f"Error al guardar configuraciones: {str(e)}", "red")
    
    def add_config(self, api_key: str, db_config: Dict[str, Any], config_id: Optional[str] = None) -> str:
        """
        Añade una nueva configuración.
        
        Args:
            api_key: API Key seleccionada
            db_config: Configuración de la base de datos
            config_id: ID opcional para la configuración (se genera uno si no se proporciona)
            
        Returns:
            ID de la configuración
        """
        if not config_id:
            config_id = str(uuid.uuid4())
            db_config["config_id"] = config_id
        
        # Crear o actualizar la entrada para este token
        if api_key not in self.configs:
            self.configs[api_key] = {}
        
        # Añadir la configuración
        self.configs[api_key][config_id] = db_config
        self._save_configs()
        
        _print_colored(f"Configuración agregada: {config_id} para la API Key: {api_key[:8]}...", "green")
        return config_id
    
    def get_config(self, api_key_selected: str, config_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene una configuración específica.
        
        Args:
            api_key_selected: API Key seleccionada
            config_id: ID de la configuración
            
        Returns:
            Configuración o None si no existe
        """
        return self.configs.get(api_key_selected, {}).get(config_id)
    
    def list_configs(self, api_key_selected: str) -> List[str]:
        """
        Lista los IDs de configuración disponibles para una API Key.
        
        Args:
            api_key_selected: API Key seleccionada
            
        Returns:
            Lista de IDs de configuración
        """
        return list(self.configs.get(api_key_selected, {}).keys())
    
    def remove_config(self, api_key_selected: str, config_id: str) -> bool:
        """
        Elimina una configuración.
        
        Args:
            api_key_selected: API Key seleccionada
            config_id: ID de la configuración
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        if api_key_selected in self.configs and config_id in self.configs[api_key_selected]:
            del self.configs[api_key_selected][config_id]
            
            # Si no quedan configuraciones para este token, eliminar la entrada
            if not self.configs[api_key_selected]:
                del self.configs[api_key_selected]
            
            self._save_configs()
            _print_colored(f"Configuración {config_id} eliminada para API Key: {api_key_selected[:8]}...", "green")
            return True
        
        _print_colored(f"Configuración {config_id} no encontrada para API Key: {api_key_selected[:8]}...", "yellow")
        return False