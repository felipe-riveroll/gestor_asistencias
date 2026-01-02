#!/bin/sh

# Corriendo migraciones
echo "Corriendo migraciones..."
python manage.py migrate --noinput

# Recolectando archivos estáticos
echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# --- CAMBIO AQUÍ ---
# Borra o comenta la línea vieja que forzaba los 30 segundos:
# exec gunicorn asistencias.wsgi:application --bind 0.0.0.0:8000 --workers=3

# Pon esta línea nueva que permite leer el timeout de 300s desde compose.yml:
echo "Iniciando servidor con argumentos externos..."
exec "$@"