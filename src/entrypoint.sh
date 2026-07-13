#!/bin/sh
set -e

# Corriendo migraciones
echo "Corriendo migraciones..."
python manage.py migrate --noinput

# Recolectando archivos estáticos
echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# Inicia el servidor con los argumentos externos (CMD/comando del Dockerfile/compose)
echo "Iniciando servidor con argumentos externos..."
exec "$@"
