# check_imports.py
import os
import importlib
import sys

def check_imports(package_name, directory):
    """Verifica recursivamente las importaciones en un directorio."""
    for item in os.listdir(directory):
        path = os.path.join(directory, item)
        
        # Ignorar directorios ocultos o __pycache__
        if item.startswith('.') or item == '__pycache__':
            continue
            
        if os.path.isdir(path):
            # Es un directorio, intentar importar como subpaquete
            if os.path.exists(os.path.join(path, '__init__.py')):
                subpackage = f"{package_name}.{item}"
                try:
                    print(f"Verificando subpaquete: {subpackage}")
                    importlib.import_module(subpackage)
                    # Verificar recursivamente
                    check_imports(subpackage, path)
                except Exception as e:
                    print(f"ERROR en {subpackage}: {e}")
        
        elif item.endswith('.py') and item != '__init__.py':
            # Es un archivo Python, intentar importar
            module_name = f"{package_name}.{item[:-3]}"  # quitar .py
            try:
                print(f"Verificando módulo: {module_name}")
                importlib.import_module(module_name)
            except Exception as e:
                print(f"ERROR en {module_name}: {e}")

# Asegurar que el directorio actual esté en el path
sys.path.insert(0, '.')

# Verificar todos los módulos principales
for pkg in ['corebrain']:
    if os.path.exists(pkg):
        try:
            print(f"\nVerificando paquete: {pkg}")
            importlib.import_module(pkg)
            check_imports(pkg, pkg)
        except Exception as e:
            print(f"ERROR en paquete {pkg}: {e}")