"""
Encryption utilities for Corebrain SDK.
"""
import os
import base64
import logging

from pathlib import Path
from typing import Optional, Union
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

def derive_key_from_password(password: Union[str, bytes], salt: Optional[bytes] = None) -> bytes:
    """
    Derives a secure encryption key from a password and salt.

    Args:
        password: Password or passphrase
        salt: Cryptographic salt (generated if not provided)

    Returns:
        Derived key in bytes
    """
    if isinstance(password, str):
        password = password.encode()
    
    # Generar sal si no se proporciona
    if salt is None:
        salt = os.urandom(16)
    
    # Derivar clave usando PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000  # Mayor número de iteraciones = mayor seguridad
    )
    
    key = kdf.derive(password)
    return base64.urlsafe_b64encode(key)

def generate_key() -> str:
    """
    Generates a new random encryption key.

    Returns:
        Encryption key in base64 format
    """
    key = Fernet.generate_key()
    return key.decode()

def create_cipher(key: Optional[Union[str, bytes]] = None) -> Fernet:
    """
    Creates a Fernet encryption object with the given key or generates a new one.

    Args:
        key: Encryption key in base64 format or None to generate a new one

    Returns:
        Fernet object for encryption/decryption
    """
    if key is None:
        key = Fernet.generate_key()
    elif isinstance(key, str):
        key = key.encode()
    
    return Fernet(key)

class ConfigEncrypter:
    """
    Encryption manager for configurations with key management.
    """
    
    def __init__(self, key_path: Optional[Union[str, Path]] = None):
        """
        Initializes the encryptor with an optional key path.

        Args:
            key_path: Path to the key file (will be created if it doesn't exist)
        """
        self.key_path = Path(key_path) if key_path else None
        self.cipher = None
        self._init_cipher()
    
    def _init_cipher(self) -> None:
        """Initializes the encryption object, creating or loading the key as needed."""
        key = None
        
        # Si hay ruta de clave, intentar cargar o crear
        if self.key_path:
            try:
                if self.key_path.exists():
                    with open(self.key_path, 'rb') as f:
                        key = f.read().strip()
                        logger.debug(f"Clave cargada desde {self.key_path}")
                else:
                    # Crear directorio padre si no existe
                    self.key_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Generar nueva clave
                    key = Fernet.generate_key()
                    
                    # Guardar clave
                    with open(self.key_path, 'wb') as f:
                        f.write(key)
                    
                    # Asegurar permisos restrictivos (solo el propietario puede leer)
                    try:
                        os.chmod(self.key_path, 0o600)
                    except Exception as e:
                        logger.warning(f"No se pudieron establecer permisos en archivo de clave: {e}")
                    
                    logger.debug(f"Nueva clave generada y guardada en {self.key_path}")
            except Exception as e:
                logger.error(f"Error al gestionar clave en {self.key_path}: {e}")
                # En caso de error, generar clave efímera
                key = None
        
        # Si no tenemos clave, generar una efímera
        if not key:
            key = Fernet.generate_key()
            logger.debug("Usando clave efímera generada")
        
        self.cipher = Fernet(key)
    
    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """
        Encrypts data.

        Args:
            data: Data to encrypt

        Returns:
            Encrypted data in bytes
        """
        if isinstance(data, str):
            data = data.encode()
        
        try:
            return self.cipher.encrypt(data)
        except Exception as e:
            logger.error(f"Error al cifrar datos: {e}")
            raise
    
    def decrypt(self, encrypted_data: Union[str, bytes]) -> bytes:
        """
        Decrypts data.

        Args:
            encrypted_data: Encrypted data

        Returns:
            Decrypted data in bytes
        """
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        
        try:
            return self.cipher.decrypt(encrypted_data)
        except InvalidToken:
            logger.error("Token inválido o datos corruptos")
            raise ValueError("Los datos no pueden ser descifrados: token inválido o datos corruptos")
        except Exception as e:
            logger.error(f"Error al descifrar datos: {e}")
            raise
    
    def encrypt_file(self, input_path: Union[str, Path], output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Encrypts a complete file.

        Args:
            input_path: Path to the file to encrypt
            output_path: Path to save the encrypted file (if None, .enc is added)

        Returns:
            Path of the encrypted file
        """
        input_path = Path(input_path)
        
        if not output_path:
            output_path = input_path.with_suffix(input_path.suffix + '.enc')
        else:
            output_path = Path(output_path)
        
        try:
            with open(input_path, 'rb') as f:
                data = f.read()
            
            encrypted_data = self.encrypt(data)
            
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
            
            return output_path
        except Exception as e:
            logger.error(f"Error al cifrar archivo {input_path}: {e}")
            raise
    
    def decrypt_file(self, input_path: Union[str, Path], output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        Decrypts a complete file.

        Args:
            input_path: Path to the encrypted file
            output_path: Path to save the decrypted file

        Returns:
            Path of the decrypted file
        """
        input_path = Path(input_path)
        
        if not output_path:
            # Si termina en .enc, quitar esa extensión
            if input_path.suffix == '.enc':
                output_path = input_path.with_suffix('')
            else:
                output_path = input_path.with_suffix(input_path.suffix + '.dec')
        else:
            output_path = Path(output_path)
        
        try:
            with open(input_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.decrypt(encrypted_data)
            
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            return output_path
        except Exception as e:
            logger.error(f"Error al descifrar archivo {input_path}: {e}")
            raise
    
    @staticmethod
    def generate_key_file(key_path: Union[str, Path]) -> None:
        """
        Generates and saves a new key to a file.

        Args:
            key_path: Path to save the key
        """
        key_path = Path(key_path)
        
        # Crear directorio padre si no existe
        key_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generar clave
        key = Fernet.generate_key()
        
        # Guardar clave
        with open(key_path, 'wb') as f:
            f.write(key)
        
        # Establecer permisos restrictivos
        try:
            os.chmod(key_path, 0o600)
        except Exception as e:
            logger.warning(f"No se pudieron establecer permisos en archivo de clave: {e}")
        
        logger.info(f"Nueva clave generada y guardada en {key_path}")