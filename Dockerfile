FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# --- LÍNEA MODIFICADA ---
# Se añaden las dependencias de sistema para construir psycopg2 y otras librerías
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Aprovechamiento de caché por capas: primero requirements, luego el código
COPY src/requirements.txt .
RUN uv pip install -r requirements.txt --system

COPY src/ .

# El entrypoint se invoca vía "sh" (ENTRYPOINT) para no depender del bit +x,
# que se pierde al montar el volumen desde Windows. chmod por si se ejecuta sin bind mount.
RUN chmod +x entrypoint.sh

EXPOSE 8000

# Healthcheck sobre el endpoint público /health/ (devuelve JSON 200)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health/ || exit 1

# El entrypoint aplica migraciones y collectstatic, luego exec "$@" con el CMD/comando.
# Usar ENTRYPOINT (no CMD) evita que compose `command:` anule la ejecución de migraciones.
ENTRYPOINT ["sh", "./entrypoint.sh"]
CMD ["gunicorn", "asistencias.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
