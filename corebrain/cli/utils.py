"""
Utilities for the Corebrain CLI.

This module provides utility functions and classes for the
Corebrain command-line interface.
"""
import sys
import time
import socket
import random
import logging
import threading
import socketserver

from typing import Optional, Dict, Any, List, Union
from pathlib import Path

from corebrain.cli.common import DEFAULT_PORT, DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)

# Terminal color definitions
COLORS = {
    "default": "\033[0m",
    "bold": "\033[1m",
    "green": "\033[92m",
    "red": "\033[91m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "white": "\033[97m",
    "black": "\033[30m",
    "bg_green": "\033[42m",
    "bg_red": "\033[41m",
    "bg_yellow": "\033[43m",
    "bg_blue": "\033[44m",
}

def print_colored(text: str, color: str = "default", return_str: bool = False) -> Optional[str]:
    """
    Prints colored text in the terminal or returns the colored text.
    
    Args:
        text: Text to color
        color: Color to use (default, green, red, yellow, blue, bold, etc.)
        return_str: If True, returns the colored text instead of printing it
        
    Returns:
        If return_str is True, returns the colored text, otherwise None
    """
    try:
        # Get color code
        start_color = COLORS.get(color, COLORS["default"])
        end_color = COLORS["default"]
        
        # Compose colored text
        colored_text = f"{start_color}{text}{end_color}"
        
        # Return or print
        if return_str:
            return colored_text
        else:
            print(colored_text)
            return None
    except Exception as e:
        # If there's an error with colors (e.g., terminal that doesn't support them)
        logger.debug(f"Error using colors: {e}")
        if return_str:
            return text
        else:
            print(text)
            return None

def format_table(data: List[Dict[str, Any]], columns: Optional[List[str]] = None, 
                max_width: int = 80) -> str:
    """
    Formats data as a text table for display in the terminal.
    
    Args:
        data: List of dictionaries with the data
        columns: List of columns to display (if None, uses all columns)
        max_width: Maximum width of the table
        
    Returns:
        Table formatted as text
    """
    if not data:
        return "No data to display"
    
    # Determine columns to display
    if not columns:
        # Use all columns from the first element
        columns = list(data[0].keys())
    
    # Get the maximum width for each column
    widths = {col: len(col) for col in columns}
    for row in data:
        for col in columns:
            if col in row:
                val = str(row[col])
                widths[col] = max(widths[col], min(len(val), 30))  # Limit to 30 characters
    
    # Adjust widths if they exceed the maximum
    total_width = sum(widths.values()) + (3 * len(columns)) - 1
    if total_width > max_width:
        # Reduce proportionally
        ratio = max_width / total_width
        for col in widths:
            widths[col] = max(8, int(widths[col] * ratio))
    
    # Header
    header = " | ".join(col.ljust(widths[col]) for col in columns)
    separator = "-+-".join("-" * widths[col] for col in columns)
    
    # Rows
    rows = []
    for row in data:
        row_str = " | ".join(
            str(row.get(col, "")).ljust(widths[col])[:widths[col]] 
            for col in columns
        )
        rows.append(row_str)
    
    # Compose table
    return "\n".join([header, separator] + rows)

def get_free_port(start_port: int = DEFAULT_PORT) -> int:
    """
    Finds an available port, starting with the suggested port.
    
    Args:
        start_port: Initial port to try
        
    Returns:
        Available port
    """
    try:
        # Try with the suggested port first
        with socketserver.TCPServer(("", start_port), None) as _:
            return start_port  # The port is available
    except OSError:
        # If the suggested port is busy, look for a free one
        for _ in range(10):  # Try 10 times
            # Choose a random port between 8000 and 9000
            port = random.randint(8000, 9000)
            try:
                with socketserver.TCPServer(("", port), None) as _:
                    return port  # Port available
            except OSError:
                continue  # Try with another port
        
        # If we can't find a free port, use a default high one
        return 10000 + random.randint(0, 1000)

def is_port_in_use(port: int) -> bool:
    """
    Checks if a port is in use.
    
    Args:
        port: Port number to check
        
    Returns:
        True if the port is in use
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def is_interactive() -> bool:
    """
    Determines if the current session is interactive.
    
    Returns:
        True if the session is interactive
    """
    return sys.stdin.isatty() and sys.stdout.isatty()

def confirm_action(message: str, default: bool = False) -> bool:
    """
    Asks the user for confirmation of an action.
    
    Args:
        message: Confirmation message
        default: Default value if the user just presses Enter
        
    Returns:
        True if the user confirms, False otherwise
    """
    if not is_interactive():
        return default
    
    default_text = "Y/n" if default else "y/N"
    response = input(f"{message} ({default_text}): ").strip().lower()
    
    if not response:
        return default
    
    return response.startswith('y')

def get_input_with_default(prompt: str, default: Optional[str] = None) -> str:
    """
    Requests input from the user with a default value.
    
    Args:
        prompt: Request message
        default: Default value
        
    Returns:
        Value entered by the user or default value
    """
    if default:
        full_prompt = f"{prompt} (default: {default}): "
    else:
        full_prompt = f"{prompt}: "
    
    response = input(full_prompt).strip()
    
    return response if response else (default or "")

def get_password_input(prompt: str = "Password") -> str:
    """
    Requests a password from the user without displaying it on screen.
    
    Args:
        prompt: Request message
        
    Returns:
        Password entered
    """
    import getpass
    return getpass.getpass(f"{prompt}: ")

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncates text if it exceeds the maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if the text is truncated
        
    Returns:
        Truncated text if necessary
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Ensures that a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Path object of the directory
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj

class ProgressTracker:
    """
    Displays progress of CLI operations with colors and timing.
    """
    
    def __init__(self, verbose: bool = False, spinner: bool = True):
        """
        Initializes the progress tracker.
        
        Args:
            verbose: Whether to show detailed information
            spinner: Whether to show an animated spinner
        """
        self.verbose = verbose
        self.use_spinner = spinner and is_interactive()
        self.start_time = None
        self.current_task = None
        self.total = None
        self.steps = 0
        self.spinner_thread = None
        self.stop_spinner = threading.Event()
        self.last_update_time = 0
        self.update_interval = 0.2  # Seconds between updates
    
    def _run_spinner(self):
        """Displays an animated spinner in the console."""
        spinner_chars = "|/-\\"
        idx = 0
        
        while not self.stop_spinner.is_set():
            if self.current_task:
                elapsed = time.time() - self.start_time
                status = f"{self.steps}/{self.total}" if self.total else f"step {self.steps}"
                sys.stdout.write(f"\r{COLORS['blue']}[{spinner_chars[idx]}] {self.current_task} ({status}, {elapsed:.1f}s){COLORS['default']}   ")
                sys.stdout.flush()
                idx = (idx + 1) % len(spinner_chars)
            time.sleep(0.1)
    
    def start(self, task: str, total: Optional[int] = None) -> None:
        """
        Starts tracking a task.
        
        Args:
            task: Task description
            total: Total number of steps (optional)
        """
        self.reset()  # Ensure there's no previous task
        
        self.current_task = task
        self.total = total
        self.start_time = time.time()
        self.steps = 0
        self.last_update_time = self.start_time
        
        # Show initial message
        print_colored(f"▶ {task}...", "blue")
        
        # Start spinner if enabled
        if self.use_spinner:
            self.stop_spinner.clear()
            self.spinner_thread = threading.Thread(target=self._run_spinner)
            self.spinner_thread.daemon = True
            self.spinner_thread.start()
    
    def update(self, message: Optional[str] = None, increment: int = 1) -> None:
        """
        Updates progress with optional message.
        
        Args:
            message: Progress message
            increment: Step increment
        """
        if not self.start_time:
            return  # No active task
        
        self.steps += increment
        current_time = time.time()
        
        # Limit update frequency to avoid saturating the output
        if (current_time - self.last_update_time < self.update_interval) and not message:
            return
        
        self.last_update_time = current_time
        
        # If there's an active spinner, temporarily stop it to show the message
        if self.use_spinner and self.spinner_thread and self.spinner_thread.is_alive():
            sys.stdout.write("\r" + " " * 80 + "\r")  # Clear current line
            sys.stdout.flush()
        
        if message or self.verbose:
            elapsed = current_time - self.start_time
            status = f"{self.steps}/{self.total}" if self.total else f"step {self.steps}"
            
            if message:
                print_colored(f"  • {message} ({status}, {elapsed:.1f}s)", "blue")
            elif self.verbose:
                print_colored(f"  • Progress: {status}, {elapsed:.1f}s", "blue")
    
    def finish(self, message: Optional[str] = None) -> None:
        """
        Finishes a task with success message.
        
        Args:
            message: Final message
        """
        if not self.start_time:
            return  # No active task
        
        # Stop spinner if active
        self._stop_spinner()
        
        elapsed = time.time() - self.start_time
        msg = message or f"{self.current_task} completed"
        print_colored(f"✅ {msg} in {elapsed:.2f}s", "green")
        
        self.reset()
    
    def fail(self, message: Optional[str] = None) -> None:
        """
        Marks a task as failed.
        
        Args:
            message: Error message
        """
        if not self.start_time:
            return  # No active task
        
        # Stop spinner if active
        self._stop_spinner()
        
        elapsed = time.time() - self.start_time
        msg = message or f"{self.current_task} failed"
        print_colored(f"❌ {msg} after {elapsed:.2f}s", "red")
        
        self.reset()
    
    def _stop_spinner(self) -> None:
        """Stops the spinner if active."""
        if self.use_spinner and self.spinner_thread and self.spinner_thread.is_alive():
            self.stop_spinner.set()
            self.spinner_thread.join(timeout=0.5)
            
            # Clear spinner line
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()
    
    def reset(self) -> None:
        """Resets the tracker."""
        self._stop_spinner()
        self.start_time = None
        self.current_task = None
        self.total = None
        self.steps = 0
        self.spinner_thread = None

class CliConfig:
    """
    Manages the CLI configuration.
    """
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """
        Initializes the CLI configuration.
        
        Args:
            config_dir: Directory for configuration files
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".corebrain" / "cli"
        
        self.config_file = self.config_dir / "config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Loads configuration from file.
        
        Returns:
            Loaded configuration
        """
        if not self.config_file.exists():
            return self._create_default_config()
        
        try:
            import json
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading configuration: {e}")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """
        Creates a default configuration.
        
        Returns:
            Default configuration
        """
        from corebrain.cli.common import DEFAULT_API_URL, DEFAULT_SSO_URL
        
        config = {
            "api_url": DEFAULT_API_URL,
            "sso_url": DEFAULT_SSO_URL,
            "verbose": False,
            "timeout": DEFAULT_TIMEOUT,
            "last_used": {
                "api_key": None,
                "config_id": None
            },
            "ui": {
                "use_colors": True,
                "use_spinner": True,
                "verbose": False
            }
        }
        
        # Ensure the directory exists
        ensure_dir(self.config_dir)
        
        # Save default configuration
        try:
            import json
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving configuration: {e}")
        
        return config
    
    def save(self) -> bool:
        """
        Saves current configuration.
        
        Returns:
            True if saved correctly
        """
        try:
            # Ensure the directory exists
            ensure_dir(self.config_dir)
            
            import json
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Gets a configuration value.
        
        Args:
            key: Configuration key
            default: Default value
            
        Returns:
            Configuration value
        """
        # Support for nested keys with dots
        if "." in key:
            parts = key.split(".")
            current = self.config
            for part in parts:
                if part not in current:
                    return default
                current = current[part]
            return current
        
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """
        Sets a configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
            
        Returns:
            True if set correctly
        """
        # Support for nested keys with dots
        if "." in key:
            parts = key.split(".")
            current = self.config
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        else:
            self.config[key] = value
        
        return self.save()
    
    def update(self, config_dict: Dict[str, Any]) -> bool:
        """
        Updates configuration with a dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            True if updated correctly
        """
        self.config.update(config_dict)
        return self.save()
    
    def update_last_used(self, api_key: Optional[str] = None, config_id: Optional[str] = None) -> bool:
        """
        Updates the last used configuration.
        
        Args:
            api_key: API key used
            config_id: Configuration ID used
            
        Returns:
            True if updated correctly
        """
        if not self.config.get("last_used"):
            self.config["last_used"] = {}
        
        if api_key:
            self.config["last_used"]["api_key"] = api_key
        
        if config_id:
            self.config["last_used"]["config_id"] = config_id
        
        return self.save()