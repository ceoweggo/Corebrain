# Corebrain SDK

![CI Status](https://github.com/ceoweggo/Corebrain/workflows/Corebrain%20SDK%20CI/CD/badge.svg)
[![PyPI version](https://badge.fury.io/py/corebrain.svg)](https://badge.fury.io/py/corebrain)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

SDK for natural language queries to relational and non-relational databases. Enables interaction with databases using natural language questions.

## ✨ Features

- **Natural Language Queries**: Transforms human language questions into database queries (SQL/NoSQL)
- **Multi-Database Support**: Compatible with SQLite, MySQL, PostgreSQL, and MongoDB
- **Unified Interface**: Consistent API across different database types
- **Built-in CLI**: Interact with your databases directly from the terminal
- **Strong Security**: Robust authentication and secure credential management
- **Highly Extensible**: Designed for easy integration with new engines and features
- **Comprehensive Documentation**: Usage examples, API reference, and step-by-step guides

## 📋 Requirements

- Python 3.8+
- Specific dependencies based on the database engine:
  - **SQLite**: Included in Python
  - **PostgreSQL**: `psycopg2-binary`
  - **MySQL**: `mysql-connector-python`
  - **MongoDB**: `pymongo`

## 🔧 Installation

### From PyPI (recommended)

```bash
# Minimal installation
pip install corebrain

### From source code

```bash
git clone https://github.com/ceoweggo/Corebrain.git
pip install -e .
```

## 🚀 Quick Start Guide

### Initialization

# > **⚠️ IMPORTANT:**  
# > * If you don't have an existing configuration, first run `corebrain --configure`
# > * If you need to generate a new API key, use `corebrain --create`
# > * Never share your API key in public repositories. Use environment variables instead.


```python
from corebrain import init

# Initialize with a previously saved configuration
corebrain = init(
    api_key="your_api_key",
    config_id="your_config_id"
)
```

### Making Natural Language Queries

```python
# Simple query
result = client.ask("How many active users are there?")
print(result["explanation"])  # Natural language explanation
print(result["query"])        # Generated SQL/NoSQL query
print(result["results"])      # Query results

# Query with additional parameters
result = client.ask(
    "Show the last 5 orders", 
    collection_name="orders",
    limit=5,
    filters={"status": "completed"}
)

# Iterate over the results
for item in result["results"]:
    print(item)
```

### Getting the Database Schema

```python
# Get the complete schema
schema = client.db_schema

# List all tables/collections
tables = client.list_collections_name()
print(tables)
```

### Closing the Connection

```python
# It's recommended to close the connection when finished
client.close()

# Or use the with context
with init(api_key="your_api_key", config_id="your_config_id") as client:
    result = client.ask("How many users are there?")
    print(result["explanation"])
```

## 🖥️ Command Line Interface Usage

### Configure Connection

```bash
# Init configuration
corebrain --configure
```

### Display Database Schema

```bash
# Show complete schema
corebrain --show-schema
```

### List Configurations

```bash
# List all configurations
corebrain --list-configs
```

## 📝 Advanced Documentation

### Configuration Management

```python
from corebrain import list_configurations, remove_configuration, get_config

# List all configurations
configs = list_configurations(api_token="your_api_token")
print(configs)

# Get details of a configuration
config = get_config(api_token="your_api_token", config_id="your_config_id")
print(config)

# Remove a configuration
removed = remove_configuration(api_token="your_api_token", config_id="your_config_id")
print(f"Configuration removed: {removed}")
```

## 🧪 Testing and Development

### Development Installation

```bash
# Clone the repository
git clone https://github.com/ceoweggo/Corebrain.git
cd corebrain

# Install in development mode with extra tools
pip install -e ".[dev,all_db]"
```

### Verifying Style and Typing

```bash
# Check style with flake8
flake8 .

# Check typing with mypy
mypy core db cli utils

# Format code with black
black .
```

### Continuous Integration and Deployment (CI/CD)

The project uses GitHub Actions to automate:

1. **Testing**: Runs tests on multiple Python versions (3.8-3.11)
2. **Quality Verification**: Checks style, typing, and formatting
3. **Coverage**: Generates code coverage reports
4. **Automatic Publication**: Publishes new versions to PyPI when tags are created
5. **Docker Images**: Builds and publishes Docker images with each version

You can see the complete configuration in `.github/workflows/ci.yml`.

## 🛠️ Contributions

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please make sure your changes pass all tests and comply with the style guidelines.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.