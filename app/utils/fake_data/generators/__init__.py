"""
Generadores modulares de datos fake
Cada archivo se auto-registra usando decorators cuando se escanea
No necesitas imports explícitos - el registry los encuentra automáticamente
"""

# Auto-discovery pattern: Los módulos se registran solos cuando se importan
# El registry hace pkgutil.iter_modules() y los encuentra dinámicamente