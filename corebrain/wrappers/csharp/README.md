# CoreBrain-CS

[![NuGet Version](https://img.shields.io/nuget/v/CorebrainCS.svg)](https://www.nuget.org/packages/CorebrainCS/)
[![Python Requirement](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A C# wrapper for the CoreBrain Python CLI tool, providing seamless integration between .NET applications and CoreBrain's cognitive computing capabilities.

## Features

- 🚀 Native C# interface for CoreBrain functions
- 🛠️ Supports both development and production workflows

## Installation

### Prerequisites

- [.NET 8.0 SDK](https://dotnet.microsoft.com/download)
- [Python 3.8+](https://www.python.org/downloads/)

## Corebrain installation

See the main corebrain package installation on https://github.com/ceoweggo/Corebrain/blob/main/README.md#installation

## Basic Usage

```csharp
using CorebrainCS;

// Initialize wrapper (auto-detects Python environment)
var corebrain = new CorebrainCS();

// Get version
Console.WriteLine($"CoreBrain version: {corebrain.Version()}");
```

## Advanced Configuration

```csharp
// Custom configuration
var corebrain = new CorebrainCS(
    pythonPath: "path/to/python",   // Custom python path
    scriptPath: "path/to/cli",      // Custom CoreBrain CLI path
    verbose: true                   // Enable debug logging
);
```

## Common Commands

| Command | C# Method | Description |
|---------|-----------|-------------|
| `--version` | `.Version()` | Get CoreBrain version |

<!-- 
## Development

### Build Instructions

```bash
# Create release package
dotnet pack -c Release

# Run tests
dotnet test
``` -->

### File Structure

```
Corebrain-CS/
├── CorebrainCS/       # C# wrapper library
├── CorebrainCLI/      # Example consumer app
├── corebrain/            # Embedded Python package
```

## License

MIT License - See [LICENSE](LICENSE) for details.
