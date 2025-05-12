"""
Punto de entrada para ejecutar la CLI como módulo.
"""
import sys
from corebrain.cli.commands import main_cli

def main():
    """Función principal para entry point en pyproject.toml"""
    return main_cli()

if __name__ == "__main__":
    sys.exit(main())