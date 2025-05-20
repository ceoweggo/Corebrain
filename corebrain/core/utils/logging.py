"""
Utilidades de logging para Corebrain SDK.

Este módulo proporciona funciones y clases para gestionar el logging
dentro del SDK de forma consistente.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Union

# Niveles de logging personalizados
VERBOSE = 15  # Entre DEBUG e INFO

# Configuración predeterminada
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_LEVEL = logging.INFO
DEFAULT_LOG_DIR = Path.home() / ".corebrain" / "logs"

# Colores para logging en terminal
LOG_COLORS = {
    "DEBUG": "\033[94m",     # Azul
    "VERBOSE": "\033[96m",   # Cian
    "INFO": "\033[92m",      # Verde
    "WARNING": "\033[93m",   # Amarillo
    "ERROR": "\033[91m",     # Rojo
    "CRITICAL": "\033[95m",  # Magenta
    "RESET": "\033[0m"       # Reset
}

class VerboseLogger(logging.Logger):
    """Logger personalizado con nivel VERBOSE."""
    
    def verbose(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Registra un mensaje con nivel VERBOSE.
        
        Args:
            msg: Mensaje a registrar
            *args: Argumentos para formatear el mensaje
            **kwargs: Argumentos adicionales para el logger
        """
        return self.log(VERBOSE, msg, *args, **kwargs)

class ColoredFormatter(logging.Formatter):
    """Formateador que agrega colores a los mensajes de log en terminal."""
    
    def __init__(self, fmt: str = DEFAULT_FORMAT, datefmt: str = DEFAULT_DATE_FORMAT, 
                 use_colors: bool = True):
        """
        Inicializa el formateador.
        
        Args:
            fmt: Formato del mensaje
            datefmt: Formato de fecha
            use_colors: Si es True, usa colores en terminal
        """
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formatea un registro con colores.
        
        Args:
            record: Registro a formatear
            
        Returns:
            Mensaje formateado
        """
        levelname = record.levelname
        message = super().format(record)
        
        if self.use_colors and levelname in LOG_COLORS:
            return f"{LOG_COLORS[levelname]}{message}{LOG_COLORS['RESET']}"
        return message

def setup_logger(name: str = "corebrain", 
                level: int = DEFAULT_LEVEL,
                file_path: Optional[Union[str, Path]] = None,
                format_string: Optional[str] = None,
                use_colors: bool = True,
                propagate: bool = False) -> logging.Logger:
    """
    Configura un logger con opciones personalizadas.
    
    Args:
        name: Nombre del logger
        level: Nivel de logging
        file_path: Ruta al archivo de log (opcional)
        format_string: Formato de mensajes personalizado
        use_colors: Si es True, usa colores en terminal
        propagate: Si es True, propaga mensajes a loggers padre
        
    Returns:
        Logger configurado
    """
    # Registrar nivel personalizado VERBOSE
    if not hasattr(logging, 'VERBOSE'):
        logging.addLevelName(VERBOSE, 'VERBOSE')
    
    # Registrar clase de logger personalizada
    logging.setLoggerClass(VerboseLogger)
    
    # Obtener o crear logger
    logger = logging.getLogger(name)
    
    # Limpiar handlers existentes
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Configurar nivel de logging
    logger.setLevel(level)
    logger.propagate = propagate
    
    # Formato predeterminado
    fmt = format_string or DEFAULT_FORMAT
    formatter = ColoredFormatter(fmt, use_colors=use_colors)
    
    # Handler de consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler de archivo si se proporciona ruta
    if file_path:
        # Asegurar que el directorio exista
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(file_path)
        # Para archivos, usar formateador sin colores
        file_formatter = logging.Formatter(fmt)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Mensajes de diagnóstico
    logger.debug(f"Logger '{name}' configurado con nivel {logging.getLevelName(level)}")
    if file_path:
        logger.debug(f"Logs escritos a {file_path}")
    
    return logger

def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Obtiene un logger existente o crea uno nuevo.
    
    Args:
        name: Nombre del logger
        level: Nivel de logging opcional
        
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    
    # Si el logger no tiene handlers, configurarlo
    if not logger.handlers:
        # Determinar si es un logger secundario
        if '.' in name:
            # Es un sublogger, configurar para propagar a logger padre
            logger.propagate = True
            if level is not None:
                logger.setLevel(level)
        else:
            # Es un logger principal, configurar completamente
            logger = setup_logger(name, level or DEFAULT_LEVEL)
    elif level is not None:
        # Solo actualizar el nivel si se especifica
        logger.setLevel(level)
    
    return logger

def enable_file_logging(logger_name: str = "corebrain", 
                        log_dir: Optional[Union[str, Path]] = None,
                        filename: Optional[str] = None) -> str:
    """
    Activa el logging a archivo para un logger existente.
    
    Args:
        logger_name: Nombre del logger
        log_dir: Directorio para los logs (opcional)
        filename: Nombre de archivo personalizado (opcional)
        
    Returns:
        Ruta al archivo de log
    """
    logger = logging.getLogger(logger_name)
    
    # Determinar la ruta del archivo de log
    log_dir = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Generar nombre de archivo si no se proporciona
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{logger_name}_{timestamp}.log"
    
    file_path = log_dir / filename
    
    # Verificar si ya hay un FileHandler
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)
    
    # Agregar nuevo FileHandler
    file_handler = logging.FileHandler(file_path)
    formatter = logging.Formatter(DEFAULT_FORMAT)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"Logging a archivo activado: {file_path}")
    return str(file_path)

def set_log_level(level: Union[int, str], 
                  logger_name: Optional[str] = None) -> None:
    """
    Establece el nivel de logging para uno o todos los loggers.
    
    Args:
        level: Nivel de logging (nombre o valor entero)
        logger_name: Nombre del logger específico (si es None, afecta a todos)
    """
    # Convertir nombre de nivel a valor si es necesario
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    if logger_name:
        # Afectar solo al logger especificado
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.info(f"Nivel de log cambiado a {logging.getLevelName(level)}")
    else:
        # Afectar al logger raíz y a todos los loggers existentes
        root = logging.getLogger()
        root.setLevel(level)
        
        # También afectar a loggers específicos del SDK
        for name in logging.root.manager.loggerDict:
            if name.startswith("corebrain"):
                logging.getLogger(name).setLevel(level)