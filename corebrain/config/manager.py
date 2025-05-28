"""
Configuration manager for the Corebrain SDK.
"""

import json
import uuid
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from cryptography.fernet import Fernet
from corebrain.utils.serializer import serialize_to_json
from corebrain.core.common import logger
from corebrain.cli.config import DEFAULT_API_URL, DEFAULT_SSO_URL
from corebrain.db.schema_file import show_db_schema
from corebrain.cli.utils import print_colored
from tkinter import filedialog
import tkinter as tk


# Made by Lukasz
# get data from pyproject.toml
def load_project_metadata():
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        with open(pyproject_path, "rb") as f:
            data = tomli.load(f)
        return data.get("project", {})
    except (FileNotFoundError, tomli.TOMLDecodeError) as e:
        print(f"Warning: Could not load project metadata: {e}")
        return {}


# Made by Lukasz
# get the name, version, etc.
def get_config():
    metadata = load_project_metadata()  # ^
    return {
        "model": metadata.get("name", "unknown"),
        "version": metadata.get("version", "0.0.0"),
        "debug": False,
        "logging": {"level": "info"},
    }


# Made by Lukasz
# export config to file
def export_config(config, filepath="config.json", include_credentials=False, shareable=False):
    """
    Export configuration to a file with options for credentials and shareable formats.

    Args:
        config (dict): The configuration dictionary to export.
        filepath (str): Path to the file to export.
        include_credentials (bool): Whether to include sensitive fields like passwords or tokens.
        shareable (bool): Whether to create a sanitized, shareable version (removes credentials).
    """
    config_to_export = config.copy()

    sensitive_keys = {"password", "api_key", "token", "secret", "access_token", "credentials"}

    if shareable or not include_credentials:
        config_to_export = {
            k: ("***REDACTED***" if k in sensitive_keys else v)
            for k, v in config_to_export.items()
        }

    try:
        with open(filepath, "w") as f:
            json.dump(config_to_export, f, indent=4)
        _print_colored(f"Configuration exported to {filepath}", "green")
    except Exception as e:
        _print_colored(f"Failed to export configuration: {e}", "red")


# Function to print colored messages
def _print_colored(message: str, color: str) -> None:
    """Simplified version of _print_colored that does not depend on cli.utils."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "default": "\033[0m",
    }
    color_code = colors.get(color, colors["default"])
    print(f"{color_code}{message}{colors['default']}")


class ConfigManager:
    """SDK configuration manager with improved security and performance."""

    CONFIG_DIR = Path.home() / ".corebrain"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    SECRET_KEY_FILE = CONFIG_DIR / "secret.key"
    ACTIVE_CONFIG_FILE = CONFIG_DIR / "active_config.json"

    def __init__(self):
        self.configs = {}
        self.cipher = None
        self._ensure_config_dir()
        self._load_secret_key()
        self._load_configs()

    def _ensure_config_dir(self) -> None:
        """Ensures that the configuration directory exists."""
        try:
            self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Configuration directory ensured: {self.CONFIG_DIR}")
            _print_colored(f"Configuration dire:ctory ensured: {self.CONFIG_DIR}", "blue")
        except Exception as e:
            logger.error(f"Error creating configuration directory: {str(e)}")
            _print_colored(f"Error creating configuration directory: {str(e)}", "red")

    def _load_secret_key(self) -> None:
        """Loads or generates the secret key to encrypt sensitive data."""
        try:
            if not self.SECRET_KEY_FILE.exists():
                key = Fernet.generate_key()
                with open(self.SECRET_KEY_FILE, "wb") as key_file:
                    key_file.write(key)
                _print_colored(f"New secret key generated in: {self.SECRET_KEY_FILE}", "green")

            with open(self.SECRET_KEY_FILE, "rb") as key_file:
                self.secret_key = key_file.read()

            self.cipher = Fernet(self.secret_key)
        except Exception as e:
            _print_colored(f"Error loading/generating secret key: {str(e)}", "red")
            # Fallback a una clave temporal (menos segura pero funcional)
            self.secret_key = Fernet.generate_key()
            self.cipher = Fernet(self.secret_key)

    def _load_configs(self) -> Dict[str, Dict[str, Any]]:
        """Loads the saved configurations."""
        if not self.CONFIG_FILE.exists():
            _print_colored(f"Configuration file not found: {self.CONFIG_FILE}", "yellow")
            return {}

        try:
            with open(self.CONFIG_FILE, "r") as f:
                encrypted_data = f.read()

            if not encrypted_data:
                _print_colored("Configuration file is empty", "yellow")
                return {}

            try:
                # Trying to decipher the data
                decrypted_data = self.cipher.decrypt(encrypted_data.encode()).decode()
                configs = json.loads(decrypted_data)
            except Exception as e:
                # If decryption fails, attempt to load as plain JSON
                logger.warning(f"Error decrypting configuration: {e}")
                configs = json.loads(encrypted_data)

            if isinstance(configs, str):
                configs = json.loads(configs)

            _print_colored(f"Configuration loaded", "green")
            self.configs = configs
            return configs
        except Exception as e:
            _print_colored(f"Error loading configurations: {str(e)}", "red")
            return {}

    def _save_configs(self) -> None:
        """Saves the current configurations."""
        try:
            configs_json = serialize_to_json(self.configs)
            encrypted_data = self.cipher.encrypt(json.dumps(configs_json).encode()).decode()

            with open(self.CONFIG_FILE, "w") as f:
                f.write(encrypted_data)

            _print_colored(f"Configurations saved in: {self.CONFIG_FILE}", "green")
        except Exception as e:
            _print_colored(f"Error saving configurations: {str(e)}", "red")

    def add_config(
        self, api_key: str, db_config: Dict[str, Any], config_id: Optional[str] = None
    ) -> str:
        """
        Adds a new configuration.

        Args:
            api_key: Selected API Key
            db_config: Database configuration
            config_id: Optional ID for the configuration (one is generated if not provided)

        Returns:
            Configuration ID
        """
        if not config_id:
            config_id = str(uuid.uuid4())
            db_config["config_id"] = config_id

        # Create or update the entry for this token
        if api_key not in self.configs:
            self.configs[api_key] = {}

        # Add the configuration
        self.configs[api_key][config_id] = db_config
        self._save_configs()

        _print_colored(f"Configuration added: {config_id} for API Key: {api_key[:8]}...", "green")
        return config_id

    def get_config(self, api_key_selected: str, config_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific configuration.

        Args:
            api_key_selected: Selected API Key
            config_id: Configuration ID

        Returns:
            Configuration or None if it does not exist
        """
        return self.configs.get(api_key_selected, {}).get(config_id)

    """ --> Default version
    def list_configs(self, api_key_selected: str) -> List[str]:
        
        Lists the available configuration IDs for an API Key.
        
        Args:
            api_key_selected: Selected API Key
            
        Returns:
            List of configuration IDs
        
        return list(self.configs.get(api_key_selected, {}).keys())
    """

    def set_active_config(self, config_id_to_activate: str) -> bool:
        """
        Sets a given config as active, regardless of which API key it's under.

        Args:
            config_id_to_activate: The config ID to set as active globally.

        Returns:
            True if the config was found and activated, False otherwise.
        """
        found = False

        for api_key, configs in self.configs.items():
            for config_id, config_data in configs.items():
                if config_id == config_id_to_activate:
                    config_data["active"] = True
                    found = True
                else:
                    config_data.pop("active", None)

        if found:
            self._save_configs()
            _print_colored(f"Activated configuration {config_id_to_activate}", "green")
            return True
        else:
            _print_colored(f"Invalid Config ID: {config_id_to_activate}", "red")
            return False

    def get_active_config_id(self, api_key: str) -> Optional[str]:
        """
        Retrieve the currently active configuration ID for a given API key.

        Returns None if not set.
        """
        try:
            if self.ACTIVE_CONFIG_FILE.exists():
                with open(self.ACTIVE_CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    if data.get("api_key") == api_key:
                        return data.get("config_id")
        except Exception as e:
            _print_colored(f"Could not load active configuration: {e}", "yellow")
        return None

    def list_configs(self, api_key_selected: str, user_data=None, api_token=None) -> List[str]:
        """
        Interactively select an API key, then display and manage its configurations.

        Returns:
            ID of the selected or activated configuration (or None if nothing selected).
        """
        if not self.configs:
            print("No saved configurations found.")
            return None

        api_keys = list(self.configs.keys())
        print("\nAvailable API Keys:")
        for idx, key in enumerate(api_keys, 1):
            print(f"  {idx}. {key}")

        try:
            selected_index = int(input("Select an API Key by number: ").strip())
            selected_api_key = api_keys[selected_index - 1]
        except (ValueError, IndexError):
            _print_colored("Invalid selection.", "red")
            return None

        configs = self.configs[selected_api_key]
        if not configs:
            _print_colored("No configurations found for the selected API Key.", "yellow")
            return None

        print(f"\nConfigurations for API Key {selected_api_key}.")
        config_ids = list(configs.keys())
        for idx, config_id in enumerate(config_ids, 1):
            status = " [ACTIVE]" if configs[config_id].get("active") else ""
            if status == " [ACTIVE]":
                _print_colored(f"  {idx}. {config_id}{status}", "blue")
            else:
                print(f"  {idx}. {config_id}{status}")

            for k, v in configs[config_id].items():
                print(f"       {k}: {v}")

        action_prompt = input("\nWould you like to perform an action? (y/n): ").strip().lower()
        if action_prompt == "y":
            print("\nAvailable actions:")
            print("  1. Activate configuration")
            print("  2. Delete configuration")
            print("  3. Show schema")
            print("  4. Validate configuration")
            print("  5. Edit configuration")
            print("  6. Export configuration")
            print("  7. Improt configuration")
            print("  8. Create configuration")
            print("  q. Exit")

            choice = input("Enter your choice (1/2/3/4/5/6/7/8/q): ").strip()
            if choice == "1":
                selected_idx = input("Enter the number of the configuration to activate: ").strip()
                try:
                    config_id = config_ids[int(selected_idx) - 1]
                    self.set_active_config(config_id)
                    return config_id
                except (ValueError, IndexError):
                    _print_colored("Invalid configuration number.", "red")
            elif choice == "2":
                selected_idx = input("Enter the number of the configuration to delete: ").strip()
                try:
                    config_id = config_ids[int(selected_idx) - 1]
                    self.remove_config(selected_api_key, config_id)
                except (ValueError, IndexError):
                    _print_colored("Invalid configuration number.", "red")
            elif choice == "3":
                api_url = os.environ.get("COREBRAIN_API_URL") or DEFAULT_API_URL
                selected_idx = input("Enter the number of the configuration to show: ").strip()
                try:
                    config_id = config_ids[int(selected_idx) - 1]
                    config = self.get_config(api_key_selected, config_id)
                    show_db_schema(config, selected_api_key, config_id, api_url)
                except (ValueError, IndexError):
                    _print_colored("Invalid configuration number.", "red")
            elif choice == "4":
                api_url = os.environ.get("COREBRAIN_API_URL") or DEFAULT_API_URL
                selected_idx = input("Enter the number of the configuration to validate: ").strip()
                try:
                    config_id = config_ids[int(selected_idx) - 1]
                    self.validate_config(selected_api_key, config_id)
                except (ValueError, IndexError):
                    _print_colored("Invalid configuration number.", "red")
            elif choice == "5":
                selected_idx = input("Enter the number of the configuration to modify: ").strip()
                try:
                    config_id = config_ids[int(selected_idx) - 1]
                    self.modify_config(selected_api_key, config_id)
                except (ValueError, IndexError):
                    _print_colored("Invalid configuration number.", "red")
            elif choice == "6":
                selected_idx = input("Enter the number of the configuration to export: ").strip()
                try:
                    config_id = config_ids[int(selected_idx) - 1]
                    config = self.get_config(api_key_selected, config_id)
                    include_credentials = input("Include credentials in export? (y/n): ").strip().lower() == "y"
                    shareable = input("Export as shareable version? (y/n): ").strip().lower() == "y"
                    export_config(config, include_credentials=include_credentials, shareable=shareable)

                except (ValueError, IndexError):
                    _print_colored("Invalid configuration number.", "red")
            elif choice == "7":
                try:
                    self.validate_config(selected_api_key, config_id)
                    self.import_config(selected_api_key)
                except (ValueError, IndexError):
                    _print_colored("Invalid configuration number.", "red")
            elif choice == "8":
                api_url = os.environ.get("COREBRAIN_API_URL") or DEFAULT_API_URL
                sso_url = os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
                from corebrain.cli.config import configure_sdk

                configure_sdk(api_token, api_key_selected, api_url, sso_url, user_data)

            elif choice == "q":
                print("Exit selected.")
            else:
                print("Invalid action.")
        elif action_prompt != "n":
            print("Invalid input. Please enter 'y' or 'n'.")

        return None

    def modify_config(self, api_key_selected: str, config_id: str) -> None:
        """
        Allows the user to interactively modify multiple parameters of an existing configuration.
        """
        config = self.get_config(api_key_selected, config_id)
        if not config:
            _print_colored(f"Configuration with ID '{config_id}' not found", "red")
            return

        print_colored(f"\nEditing configuration: {config_id}", "blue")

        while True:
            keys = [key for key in config.keys() if key != "config_id"]
            print("\nCurrent parameters:")
            for idx, key in enumerate(keys, 1):
                print(f"  {idx}. {key}: {config[key]}")

            print("  0. Exit edit mode")

            try:
                key_idx = int(input("\nSelect parameter number to edit (or 0 to exit): ").strip())
                if key_idx == 0:
                    _print_colored("Exiting edit mode.", "yellow")
                    break

                key_to_edit = keys[key_idx - 1]
                new_value = input(f"Enter new value for '{key_to_edit}': ").strip()

                # Try to interpret value types
                if new_value.lower() in ["true", "false"]:
                    new_value = new_value.lower() == "true"
                elif new_value.isdigit():
                    new_value = int(new_value)
                elif new_value.lower() == "null":
                    new_value = None

                config[key_to_edit] = new_value
                self.configs[api_key_selected][config_id] = config
                self._save_configs()
                _print_colored(f"Updated '{key_to_edit}'", "green")

            except (ValueError, IndexError):
                _print_colored("Invalid selection.", "red")

        validate = (
            input("Would you like to validate the modified config now? (y/n): ").strip().lower()
        )
        if validate == "y":
            self.validate_config(api_key_selected, config_id)

    def import_config(self, api_key: str) -> str | None:
        """
        Opens a file dialog to select a JSON config file and imports it.

        Args:
            api_key: The API key under which to store the configuration.

        Returns:
            The ID of the imported configuration, or None if import failed or cancelled.
        """
        # Open file dialog for selecting config JSON file
        root = tk.Tk()
        filepath = filedialog.askopenfilename(
            title="Select configuration JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        root.destroy()

        if not filepath:
            _print_colored("Import cancelled or no file selected.", "yellow")
            return None

        try:
            with open(filepath, "r") as f:
                config = json.load(f)

            config_id = config.get("id") or str(uuid.uuid4())
            config["id"] = config_id

            self.add_config(api_key, config, config_id)
            _print_colored(f"Configuration imported as {config_id}", "green")
            return config_id

        except Exception as e:
            _print_colored(f"Failed to import configuration: {e}", "red")
            return None

    def validate_config(self, api_key, config_id):
        api_url = os.environ.get("COREBRAIN_API_URL") or DEFAULT_API_URL
        sso_url = os.environ.get("COREBRAIN_SSO_URL") or DEFAULT_SSO_URL
        if not api_key:
            print_colored(
                "Error: An API Key is required. Use --api-key or login via --login", "red"
            )
            return 1
        try:
            config = self.get_config(api_key, config_id)
            if not config:
                print_colored(f"Configuration with ID '{config_id}' not found", "red")
                return 1
            print_colored(
                f"✅ Validating configuration: {config_id}", "blue"
            )  # Create a temporary Corebrain instance to validate
            from corebrain.core.client import Corebrain

            try:
                temp_client = Corebrain(api_key=api_key, db_config=config, skip_verification=True)
                print_colored("✅ Configuration validation passed!", "green")
                print_colored(f"Database type: {config.get('type', 'Unknown')}", "blue")
                print_colored(f"Engine: {config.get('engine', 'Unknown')}", "blue")
                return 0
            except Exception as validation_error:
                print_colored(f"❌ Configuration validation failed: {str(validation_error)}", "red")
                return 1
        except Exception as e:
            print_colored(f"❌ Error during validation: {str(e)}", "red")
            return 1

    def remove_config(self, api_key_selected: str, config_id: str) -> bool:
        """
        Deletes a configuration.

        Args:
            api_key_selected: Selected API Key
            config_id: Configuration ID

        Returns:
            True if deleted successfully, False otherwise
        """
        if api_key_selected in self.configs and config_id in self.configs[api_key_selected]:
            del self.configs[api_key_selected][config_id]

            # If there are no configurations for this token, delete the entry
            if not self.configs[api_key_selected]:
                del self.configs[api_key_selected]

            self._save_configs()
            _print_colored(
                f"Configuration {config_id} removed for API Key: {api_key_selected[:8]}...", "green"
            )
            return True

        _print_colored(
            f"Configuration {config_id} not found for API Key: {api_key_selected[:8]}...", "yellow"
        )
        return False
