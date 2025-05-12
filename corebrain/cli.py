"""
Punto de entrada para la CLI de Corebrain para compatibilidad.
"""
from corebrain.cli.__main__ import main

if __name__ == "__main__":
    import sys
    sys.exit(main())