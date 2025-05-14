# How to Contribute to Corebrain SDK

Thank you for your interest in contributing to CoreBrain SDK! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you commit to maintaining a respectful and collaborative environment.

## How to Contribute

### Reporting Bugs

1. Verify that the bug hasn't already been reported in the [issues](https://github.com/ceoweggo/Corebrain/issues)
2. Use the bug template to create a new issue
3. Include as much detail as possible: steps to reproduce, environment, versions, etc.
4. If possible, include a minimal example that reproduces the problem

### Suggesting Improvements

1. Check the [issues](https://github.com/ceoweggo/Corebrain/issues) to see if it has already been suggested
2. Use the feature template to create a new issue
3. Clearly describe the improvement and justify its value

### Submitting Changes

1. Fork the repository
2. Create a branch for your change (`git checkout -b feature/amazing-feature`)
3. Make your changes following the code conventions
4. Write tests for your changes
5. Ensure all tests pass
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push your branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Development Environment

### Installation for Development

```bash
# Clone the repository
git clone https://github.com/ceoweggo/Corebrain.git
cd sdk

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install for development
pip install -e ".[dev]"
```

### Project Structure

```
v1/
├── corebrain/                # Main package
│   ├── __init__.py
│   ├── _pycache_/
│   ├── cli/                  # Command-line interface
│   ├── config/               # Configuration management
│   ├── core/                 # Core functionality
│   ├── db/                   # Database interactions
│   ├── lib/                  # Library components
│       └── SSO/              # Globodain SSO Authentication
│   ├── network/              # Network functionality
│   ├── services/             # Service implementations
│   ├── utils/                # Utility functions
│   ├── cli.py                # CLI entry point
│   └── sdk.py                # SDK entry point
├── corebrain.egg-info/       # Package metadata
├── docs/                     # Documentation
├── examples/                 # Usage examples
├── screenshots/              # Project screenshots
├── venv/                     # Virtual environment (not to be committed)
├── .github/                  # GitHub files directory
├── _pycache_/                # Python cache files
├── .tofix/                   # Files to be fixed
├── .gitignore                # Git ignore rules
├── CONTRIBUTING.md           # Contribution guidelines
├── health.py                 # Health check script
├── LICENSE                   # License information
├── pyproject.toml            # Project configuration
├── README-no-valid.md        # Outdated README
├── README.md                 # Project overview
├── requirements.txt          # Production dependencies
└── setup.py                  # Package setup
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_specific.py

# Run tests with coverage
pytest --cov=corebrain
```

## Coding Standards

### Style Guide

- We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code
- Use 4 spaces for indentation
- Maximum line length is 88 characters
- Use descriptive variable and function names

### Documentation

- All modules, classes, and functions should have docstrings
- Follow the [Google docstring format](https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings)
- Keep documentation up-to-date with code changes

### Commit Messages

- Use clear, concise commit messages
- Start with a verb in the present tense (e.g., "Add feature" not "Added feature")
- Reference issue numbers when applicable (e.g., "Fix #123: Resolve memory leak")

## Pull Request Process

1. Update documentation if necessary
2. Add or update tests as needed
3. Ensure CI checks pass
4. Request a review from maintainers
5. Address review feedback
6. Maintainers will merge your PR once approved

## Release Process

Our maintainers follow semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR version for incompatible API changes
- MINOR version for backward-compatible functionality
- PATCH version for backward-compatible bug fixes

## Getting Help

If you need help with anything:
- Join our [Discord community](https://discord.gg/m2AXjPn2yV)
- Ask questions in the GitHub Discussions
- Contact the maintainers at ruben@globodain.com

Thank you for contributing to Corebrain SDK!