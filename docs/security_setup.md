# Guía de Configuración Segura - Django Attendance System

## 📋 Resumen

Esta guía describe los pasos necesarios para configurar de forma segura el Sistema de Gestión de Asistencias. Se implementó una arquitectura de seguridad basada en variables de entorno para proteger credenciales sensibles.

## 🔐 Configuración de Variables de Entorno

### 1. Generar SECRET_KEY

El SECRET_KEY es una clave crítica para la seguridad de Django. **NUNCA** uses el valor por defecto.

```bash
# Generar una nueva clave secreta
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Alternativa segura con más entropía
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 2. Configurar Base de Datos

```bash
# PostgreSQL - Recomendado para producción
POSTGRES_DB=nombre_base_datos
POSTGRES_USER=usuario_postgres
POSTGRES_PASSWORD=contraseña_segura_aqui
DB_HOST=localhost
DB_PORT=5432
```

**Mejores prácticas para contraseñas de base de datos:**
- Mínimo 16 caracteres
- Incluir mayúsculas, minúsculas, números y símbolos
- No usar palabras del diccionario
- Generar con: `openssl rand -base64 32`

### 3. Configurar Email (SMTP)

```bash
EMAIL_HOST=smtp.purelymail.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=asistencias@asiatech.com.mx
EMAIL_HOST_PASSWORD=contraseña_email_aqui
```

**Verificación de configuración de email:**
```bash
# Probar conexión SMTP
python manage.py shell -c "from django.core.mail import send_mail; send_mail('Test', 'Mensaje de prueba', 'from@example.com', ['to@example.com'], fail_silently=False)"
```

### 4. Configuración de Dominios Permitidos

```bash
# Desarrollo
ALLOWED_HOSTS=localhost,127.0.0.1

# Producción (ejemplo)
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com,admin.tu-dominio.com
```

**Importante:** Nunca uses `ALLOWED_HOSTS=["*"]` en producción.

## 🚀 Despliegue a Producción

### 1. Configuración de Seguridad Obligatoria

```bash
# Desactivar modo debug
DEBUG=False

# Dominios específicos
ALLOWED_HOSTS=miapp.com,www.miapp.com

# HTTPS obligatorio
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

### 2. Headers de Seguridad

El sistema ya incluye estos headers por defecto:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`

### 3. Content Security Policy (CSP) - Django 6.0+

```bash
# Configuración básica de CSP
SECURE_CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
```

## 🐳 Docker

### Dockerfile para Producción

```dockerfile
FROM python:3.11-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=asistencias.settings

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN useradd -m -u 1000 django
USER django

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Copiar código
COPY --chown=django:django . /app
WORKDIR /app

# Validar configuración antes de ejecutar
RUN python scripts/validate_env.py

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "asistencias.wsgi:application"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    env_file: .env
    depends_on:
      - db
    ports:
      - "8000:8000"
    volumes:
      - static_volume:/app/static
      - media_volume:/app/media

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

## 🔧 CI/CD Pipeline

### GitHub Actions

```yaml
name: Django Security Check

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Validate environment configuration
      run: python scripts/validate_env.py

    - name: Run security checks
      run: |
        python manage.py check --deploy
        python manage.py check --tag security

    - name: Check for hardcoded secrets
      run: |
        grep -r "SECRET_KEY.*=" src/ || true
        grep -r "PASSWORD.*=" src/ || true
```

## 🔍 Validación de Seguridad

### Script de Validación

El proyecto incluye un script de validación que verifica:
- Variables de entorno críticas configuradas
- SECRET_KEY no usa valor por defecto
- ALLOWED_HOSTS no contiene wildcard en producción
- Credenciales de email configuradas

```bash
# Ejecutar validación
python scripts/validate_env.py

# Con salida detallada
python scripts/validate_env.py --verbose
```

### Comandos de Verificación

```bash
# Verificar configuración de Django
python manage.py check --deploy

# Verificar configuración de seguridad
python manage.py check --tag security

# Buscar credenciales hardcodeadas
grep -r "SECRET_KEY.*=" src/
grep -r "PASSWORD.*=" src/
grep -r "django-insecure" src/
```

## 🛡️ Mejores Prácticas

### 1. Generación de Contraseñas

```bash
# Contraseña segura de 32 caracteres
openssl rand -base64 32

# Alternativa con pwgen
pwgen -s 32 1

# Con Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Rotación de Claves

- SECRET_KEY: Rotar cada 90 días
- Database passwords: Rotar cada 180 días
- API keys: Rotar cada 30 días

### 3. Backup de Configuración

```bash
# Encriptar archivo .env antes de hacer backup
gpg --symmetric --cipher-algo AES256 .env

# Backup con ansible-vault
ansible-vault encrypt .env
```

### 4. Monitoreo de Seguridad

Configurar alertas para:
- Cambios en ALLOWED_HOSTS
- DEBUG=True en producción
- Fallos de validación de SECRET_KEY
- Intrusos detectados

## 🚨 Solución de Problemas

### Error: "SECRET_KEY not set"
```bash
# Solución: Generar y configurar SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" >> .env
```

### Error: "ALLOWED_HOSTS is empty"
```bash
# Solución: Configurar dominios permitidos
echo "ALLOWED_HOSTS=localhost,127.0.0.1" >> .env
```

### Error: "Database connection failed"
```bash
# Verificar credenciales
grep "POSTGRES_" .env

# Probar conexión
psql -h localhost -U $POSTGRES_USER -d $POSTGRES_DB
```

### Error: "Email configuration invalid"
```bash
# Verificar SMTP
python -c "import smtplib; s=smtplib.SMTP_SSL('$EMAIL_HOST', $EMAIL_PORT); s.login('$EMAIL_HOST_USER', '$EMAIL_HOST_PASSWORD'); print('OK')"
```

## 📚 Referencias

- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [HTTP Strict Transport Security](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security)

---

**Última actualización**: 2025-12-14
**Versión**: 1.0
**Autor**: Equipo de Seguridad