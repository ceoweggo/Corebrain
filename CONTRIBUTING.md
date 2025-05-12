# Guía de contribución a CoreBrain SDK

¡Gracias por tu interés en contribuir a CoreBrain SDK! Este documento proporciona directrices para contribuir al proyecto.

## Código de conducta

Al participar en este proyecto, te comprometes a mantener un entorno respetuoso y colaborativo. 

## Cómo contribuir

### Reportar bugs

1. Verifica que el bug no haya sido reportado ya en los [issues](https://github.com/corebrain/sdk/issues)
2. Usa la plantilla de bug para crear un nuevo issue
3. Incluye tanto detalle como sea posible: pasos para reproducir, entorno, versiones, etc.
4. Si es posible, incluye un ejemplo mínimo que reproduzca el problema

### Sugerir mejoras

1. Revisa los [issues](https://github.com/corebrain/sdk/issues) para ver si ya se ha sugerido
2. Usa la plantilla de feature para crear un nuevo issue
3. Describe claramente la mejora y justifica su valor

### Enviar cambios

1. Haz fork del repositorio
2. Crea una rama para tu cambio (`git checkout -b feature/amazing-feature`)
3. Realiza tus cambios siguiendo las convenciones de código
4. Escribe tests para tus cambios
5. Asegúrate de que todos los tests pasan
6. Haz commit de tus cambios (`git commit -m 'Add amazing feature'`)
7. Sube tu rama (`git push origin feature/amazing-feature`)
8. Abre un Pull Request

## Entorno de desarrollo

### Instalación para desarrollo

```bash
# Clonar el repositorio
git clone https://github.com/corebrain/sdk.git
cd sdk

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar para desarrollo
pip install -e ".[dev]"
```

### Estructura del proyecto
