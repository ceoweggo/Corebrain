"""
Entry point to run the CLI as a module.
"""
import sys
from corebrain.cli.commands import main_cli

def main():
    """Main function for the entry point in pyproject.toml."""
    return main_cli()

if __name__ == "__main__":
    sys.exit(main())