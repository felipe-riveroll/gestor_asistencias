#!/usr/bin/env python
"""Script para validar variables de entorno críticas"""
import os
import sys
from pathlib import Path

def validate_environment():
    """Valida que las variables de entorno críticas estén configuradas"""
    errors = []
    warnings = []

    # Validar variables críticas
    if not os.getenv('SECRET_KEY'):
        errors.append("SECRET_KEY no está configurado")
    elif 'django-insecure-79tr' in os.getenv('SECRET_KEY'):
        warnings.append("SECRET_KEY está usando el valor de desarrollo por defecto")

    if not os.getenv('EMAIL_HOST_PASSWORD'):
        warnings.append("EMAIL_HOST_PASSWORD no está configurado (email no funcionará)")

    if not os.getenv('POSTGRES_PASSWORD'):
        errors.append("POSTGRES_PASSWORD no está configurado")

    allowed_hosts = os.getenv('ALLOWED_HOSTS', '')
    if '*' in allowed_hosts and os.getenv('ENVIRONMENT') == 'production':
        errors.append("ALLOWED_HOSTS contiene '*' en producción")

    # Mostrar resultados
    if errors:
        print("❌ ERRORES CRÍTICOS DE CONFIGURACIÓN:")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print("⚠️  ADVERTENCIAS:")
        for warning in warnings:
            print(f"  - {warning}")

    return len(errors) == 0

if __name__ == '__main__':
    if validate_environment():
        print("✅ Configuración válida")
        sys.exit(0)
    else:
        print("\nPor favor configure las variables faltantes en el archivo .env")
        sys.exit(1)