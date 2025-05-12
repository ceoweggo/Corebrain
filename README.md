# Corebrain

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Status](https://img.shields.io/badge/status-alpha-orange)
![License](https://img.shields.io/badge/license-MIT-green)

## What is Corebrain?

Corebrain is an open-source enterprise solution designed to centralize and optimize corporate data management. The project offers a scalable architecture for processing, analyzing, and visualizing critical information for decision-making.

**IMPORTANT NOTE**: In the current version (0.1.0-alpha), only the SQL code is functional. Other modules are under development.

## Current Status

- ✅ SQL queries for data extraction
- ✅ Database schemas
- ✅ Authentication service
- ❌ NoSQL (in development)
- ❌ Frontend (in development)
- ❌ REST API (in development)

## SDK Integration
Corebrain provides SDKs for multiple programming languages, making it easy to integrate with your existing systems. While only SQL in Python functionality is currently available, this SDK will support all features and most common languages as they are developed.

![Python](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10-blue)

## Available Versions

- **`main` Branch**: Stable version with verified functionality (currently only SQL is functional)
- **`pre-release` Branch**: Initial version with all features in development (may contain errors)

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/your-organization/corebrain.git

# Enter the directory
cd corebrain

# Install dependencies
npm install
```

### Configuration

1. Use `corebrain --configure` to start the configuration.
2. Once configuration has been completed, copy config_id and reemplace in your example code (see 'examples' folder).
3. Run the example code in Python and enjoy!

### Basic Usage

```bash
# Run SQL migrations
npm run migrate

# Start the SQL service
npm run sql:start
```

## Accessing the Pre-release Version

If you want to test all features under development (including unstable components), you can switch to the pre-release branch:

```bash
git checkout pre-release
npm install
```

**Warning**: The pre-release version contains experimental features that may have bugs or unexpected behaviors. Not recommended for production environments.

## Contributing

Corebrain is an open-source project, and we welcome all contributions. To contribute:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/new-feature`)
3. Make your changes
4. Run tests (`npm test`)
5. Commit your changes (`git commit -m 'Add new feature'`)
6. Push to your fork (`git push origin feature/new-feature`)
7. Open a Pull Request

Please read our [contribution guidelines](CONTRIBUTING.md) before you start.

## Roadmap

- **0.1.0**: Basic SQL operation. OpenAI connected. Authentication service Globodain SSO integrated. API Keys configuration integrated. 
- **0.2.0**: NoSQL (MongoDB) fixed. API Key creation by command "Corebrain --configure". Functional version.
- **0.3.0**: API deployment and integration at source. Functional version for third parties.
- **1.0.0**: First stable version with all features.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- **Email**: [ruben@globodain.com](mailto:ruben@globodain.com)
- **Issues**: [Report a problem](https://github.com/ceoweggo/corebrain/issues)

---

Developed with ❤️ by [Rubén Ayuso](https://github.com/ceoweggo)
