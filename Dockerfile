FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# --- LÍNEA MODIFICADA ---
# Se añaden las dependencias de sistema para construir psycopg2 y otras librerías
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY src/requirements.txt .
RUN uv pip install -r requirements.txt --system

COPY src/ .

EXPOSE 8000

CMD ["./entrypoint.sh"]