# check_imports.py
import os
import importlib
import sys

def check_imports(package_name, directory):
    """
    Recursively checks imports into a directory.
    """
    
    for item in os.listdir(directory):
        path = os.path.join(directory, item)
        
        # Ignore hidden folders or __pycache__
        if item.startswith('.') or item == '__pycache__':
            continue
            
        if os.path.isdir(path):

            if os.path.exists(os.path.join(path, '__init__.py')):
                subpackage = f"{package_name}.{item}"
                try:
                    print(f"Verificating subpackage: {subpackage}")
                    importlib.import_module(subpackage)
                    check_imports(subpackage, path)
                except Exception as e:
                    print(f"ERROR in {subpackage}: {e}")
        
        elif item.endswith('.py') and item != '__init__.py':
            module_name = f"{package_name}.{item[:-3]}"  # quitar .py
            try:
                print(f"Verificating module: {module_name}")
                importlib.import_module(module_name)
            except Exception as e:
                print(f"ERROR in {module_name}: {e}")

sys.path.insert(0, '.')

# Verify all main modules
for pkg in ['corebrain']:
    if os.path.exists(pkg):
        try:
            print(f"\Verificating pkg: {pkg}")
            importlib.import_module(pkg)
            check_imports(pkg, pkg)
        except Exception as e:
            print(f"ERROR in pkg {pkg}: {e}")