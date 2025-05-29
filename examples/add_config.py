from corebrain import ConfigManager

# Initialize config manager
config_manager = ConfigManager()

# API key
api_key = "sk_bH8rnkIHCDF1BlRmgS9s6QAK"

# Database configuration
db_config = {
    "type": "sql",  # or "mongodb" for MongoDB
    "engine": "postgresql",  # or "mysql", "sqlite", etc.
    "host": "localhost",
    "port": 5432,
    "database": "your_database",
    "user": "your_username",
    "password": "your_password"
}

# Add configuration
config_id = config_manager.add_config(api_key, db_config)
print(f"Configuration added with ID: {config_id}")

# List all configurations
print("\nAvailable configurations:")
configs = config_manager.list_configs(api_key)
print(configs) 