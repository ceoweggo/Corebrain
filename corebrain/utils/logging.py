"""
Logging utilities for Corebrain SDK.

This module provides functions and classes to manage logging
within the SDK consistently.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Union

# Custom logging levels
VERBOSE = 15  # Entre DEBUG e INFO

# Default settings
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_LEVEL = logging.INFO
DEFAULT_LOG_DIR = Path.home() / ".corebrain" / "logs"

# Colors for logging in terminal
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
    """Custom logger with VERBOSE level."""
    
    def verbose(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """
        Logs a message with VERBOSE level.

        Args:
            msg: Message to log
            *args: Arguments to format the message
            **kwargs: Additional arguments for the logger
        """
        return self.log(VERBOSE, msg, *args, **kwargs)

class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors to log messages in the terminal."""
    
    def __init__(self, fmt: str = DEFAULT_FORMAT, datefmt: str = DEFAULT_DATE_FORMAT, 
                 use_colors: bool = True):
        """
        Initializes the formatter.

        Args:
            fmt: Message format
            datefmt: Date format
            use_colors: If True, uses colors in the terminal
        """
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formats a log record with colors.

        Args:
            record: Record to format

        Returns:
            Formatted message
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
    Configures a logger with custom options.

    Args:
        name: Logger name
        level: Logging level
        file_path: Path to the log file (optional)
        format_string: Custom message format
        use_colors: If True, uses colors in the terminal
        propagate: If True, propagates messages to parent loggers

    Returns:
        Configured logger
    """
    # Register custom level VERBOSE.
    if not hasattr(logging, 'VERBOSE'):
        logging.addLevelName(VERBOSE, 'VERBOSE')
    
    # Register custom logger class.
    logging.setLoggerClass(VerboseLogger)
    
    # Get or create logger.
    logger = logging.getLogger(name)
    
    # Clear existing handlers.
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Configure logging level.
    logger.setLevel(level)
    logger.propagate = propagate
    
    # Default format.
    fmt = format_string or DEFAULT_FORMAT
    formatter = ColoredFormatter(fmt, use_colors=use_colors)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if path is provided
    if file_path:
        # Ensure that the directory exists
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(file_path)
        # For files, use colorless formatter
        file_formatter = logging.Formatter(fmt)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Diagnostic messages
    logger.debug(f"Logger '{name}' configurado con nivel {logging.getLevelName(level)}")
    if file_path:
        logger.debug(f"Logs escritos a {file_path}")
    
    return logger

def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Retrieves an existing logger or creates a new one.

    Args:
        name: Logger name
        level: Optional logging level

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    # If the logger does not have handlers, configure it
    if not logger.handlers:
        # Determine if it is a secondary logger
        if '.' in name:
            # It is a sublogger, configure to propagate to parent logger
            logger.propagate = True
            if level is not None:
                logger.setLevel(level)
        else:
            # It is a main logger, fully configure
            logger = setup_logger(name, level or DEFAULT_LEVEL)
    elif level is not None:
        # Only update level if specified
        logger.setLevel(level)
    
    return logger

def enable_file_logging(logger_name: str = "corebrain", 
                        log_dir: Optional[Union[str, Path]] = None,
                        filename: Optional[str] = None) -> str:
    """
    Enables file logging for an existing logger.

    Args:
        logger_name: Logger name
        log_dir: Directory for the logs (optional)
        filename: Custom file name (optional)

    Returns:
        Path to the log file
    """
    logger = logging.getLogger(logger_name)
    
    # Determine the path of the log file
    log_dir = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename if not provided
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{logger_name}_{timestamp}.log"
    
    file_path = log_dir / filename
    
    # Check if a FileHandler already exists
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)
    
    # Add new FileHandler
    file_handler = logging.FileHandler(file_path)
    formatter = logging.Formatter(DEFAULT_FORMAT)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logger.info(f"Logging a archivo activado: {file_path}")
    return str(file_path)

def set_log_level(level: Union[int, str], 
                  logger_name: Optional[str] = None) -> None:
    """
    Sets the logging level for one or all loggers.

    Args:
        level: Logging level (name or integer value)
        logger_name: Specific logger name (if None, affects all)
    """
    # Convert level name to value if necessary
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    if logger_name:
        # Affect only the specified logger
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.info(f"Nivel de log cambiado a {logging.getLevelName(level)}")
    else:
        # Affect the root logger and all existing loggers
        root = logging.getLogger()
        root.setLevel(level)
        
        # Also affect SDK-specific loggers
        for name in logging.root.manager.loggerDict:
            if name.startswith("corebrain"):
                logging.getLogger(name).setLevel(level)