# Guía de Despliegue - Sistema de Gestión de Asistencias

## 📋 Pre-despliegue

Antes de desplegar a producción, asegúrate de completar todos los pasos de validación.

### 1. Validación de Seguridad

Ejecuta todos los scripts de validación en orden:

```bash
# Validación básica de entorno
python scripts/validate_env.py

# Validación de producción (completa)
python scripts/deploy_validate.py

# Validación específica de Docker (si usas Docker)
python scripts/docker_validate.py
```

### 2. Checklist de Seguridad

- [ ] `.env` configurado correctamente
- [ ] `SECRET_KEY` único y seguro (mínimo 50 caracteres)
- [ ] `DEBUG=False` en producción
- [ ] `ALLOWED_HOSTS` con dominios específicos (sin wildcard)
- [ ] Credenciales de base de datos seguras
- [ ] Credenciales de email configuradas
- [ ] No hay secretos hardcodeados en el código
- [ ] `.env` está en `.gitignore`

## 🚀 Opciones de Despliegue

### Opción 1: Docker (Recomendado)

#### Construcción de la imagen

```bash
# Construir imagen de producción
docker build -t gestor-asistencias:latest .

# Etiquetar para registro (opcional)
docker tag gestor-asistencias:latest tu-registry.com/gestor-asistencias:latest
```

#### Despliegue con docker-compose

```bash
# En producción, usa variables de entorno externas
cp .env.example .env.production
# Edita .env.production con valores de producción

# Desplegar
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

#### docker-compose.prod.yml (Producción)

```yaml
version: '3.8'

services:
  web:
    environment:
      - DEBUG=False
      - ENVIRONMENT=production
    volumes:
      - static_volume:/app/static
      - media_volume:/app/media
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  db:
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - static_volume:/app/static
      - media_volume:/app/media
    depends_on:
      - web

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

### Opción 2: Despliegue Manual

#### 1. Preparar servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install python3-pip python3-venv postgresql nginx supervisor -y

# Crear usuario para la aplicación
sudo useradd -m -s /bin/bash django
```

#### 2. Configurar PostgreSQL

```bash
# Crear base de datos y usuario
sudo -u postgres psql
CREATE DATABASE asistencias;
CREATE USER asistencias WITH PASSWORD 'tu-contraseña-segura';
GRANT ALL PRIVILEGES ON DATABASE asistencias TO asistencias;
\q
```

#### 3. Configurar la aplicación

```bash
# Clonar repositorio
cd /home/django
git clone https://github.com/tu-usuario/gestor_asistencias.git
cd gestor_asistencias

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
nano .env  # Configura con valores de producción

# Migraciones
python manage.py migrate

# Colectar archivos estáticos
python manage.py collectstatic --noinput
```

#### 4. Configurar Gunicorn

Crear archivo `/etc/systemd/system/gunicorn.service`:

```ini
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
Type=notify
User=django
Group=www-data
RuntimeDirectory=gunicorn
WorkingDirectory=/home/django/gestor_asistencias/src
ExecStart=/home/django/gestor_asistencias/venv/bin/gunicorn \
    --access-logfile - \
    --workers 3 \
    --bind unix:/run/gunicorn.sock \
    asistencias.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

#### 5. Configurar Nginx

Crear archivo `/etc/nginx/sites-available/gestor-asistencias`:

```nginx
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tu-dominio.com www.tu-dominio.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/tu-dominio.com.crt;
    ssl_certificate_key /etc/ssl/private/tu-dominio.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Logging
    access_log /var/log/nginx/gestor-access.log;
    error_log /var/log/nginx/gestor-error.log;

    # Django media files
    location /media/ {
        alias /home/django/gestor_asistencias/media/;
    }

    # Django static files
    location /static/ {
        alias /home/django/gestor_asistencias/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Proxy to Gunicorn
    location / {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://unix:/run/gunicorn.sock;
    }

    # Health check endpoint
    location /health/ {
        access_log off;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```

Activar sitio:

```bash
sudo ln -s /etc/nginx/sites-available/gestor-asistencias /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 6. Configurar Supervisor (opcional)

Crear archivo `/etc/supervisor/conf.d/gestor-asistencias.conf`:

```ini
[program:gestor-asistencias]
command=/home/django/gestor_asistencias/venv/bin/gunicorn --workers 3 --bind unix:/run/gunicorn.sock asistencias.wsgi:application
directory=/home/django/gestor_asistencias/src
user=django
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/gunicorn.log
environment=PATH="/home/django/gestor_asistencias/venv/bin",LANG="en_US.UTF-8",LC_ALL="en_US.UTF-8",LC_LANG="en_US.UTF-8"
```

## 🔒 Configuración Post-Despliegue

### 1. Firewall

```bash
# Configurar UFW
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. Fail2ban

```bash
# Instalar y configurar Fail2ban
sudo apt install fail2ban -y
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Configurar para Nginx
sudo tee /etc/fail2ban/jail.d/nginx.conf > /dev/null <<EOF
[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-noscript]
enabled = true
port = http,https
filter = nginx-noscript
logpath = /var/log/nginx/access.log
maxretry = 6
EOF

sudo systemctl restart fail2ban
```

### 3. Backup Automático

Crear script `/home/django/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/django/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Crear directorio si no existe
mkdir -p $BACKUP_DIR

# Backup de base de datos
sudo -u postgres pg_dump asistencias > $BACKUP_DIR/db_backup_$DATE.sql

# Backup de archivos media
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz -C /home/django/gestor_asistencias media/

# Backup de .env (encriptado)
tar -czf - -C /home/django/gestor_asistencias .env | gpg --symmetric --cipher-algo AES256 --output $BACKUP_DIR/env_backup_$DATE.tar.gz.gpg

# Eliminar backups antiguos (más de 30 días)
find $BACKUP_DIR -type f -mtime +30 -delete

# Log
logger "Backup completado: $DATE"
```

Programar en cron:

```bash
# Ejecutar backup diario a las 2 AM
0 2 * * * /home/django/backup.sh
```

### 4. Monitoreo

#### Health Check Endpoint

Asegúrate de tener un endpoint de health check en tu aplicación Django:

```python
# urls.py
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    """Endpoint para verificar el estado de la aplicación"""
    try:
        # Verificar conexión a BD
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)
```

#### Configurar Uptime Kuma (opcional)

```bash
# Instalar con Docker
docker run -d \
  --name uptime-kuma \
  -p 3001:3001 \
  -v uptime-kuma:/app/data \
  --restart=always \
  louislam/uptime-kuma:latest
```

## 🚨 Resolución de Problemas

### Verificación de Estado

```bash
# Verificar servicios
sudo systemctl status nginx
sudo systemctl status gunicorn

# Ver logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/gunicorn.log

# Verificar conexión a BD
python manage.py dbshell
```

### Comandos de Diagnóstico

```bash
# Verificar configuración de Django
python manage.py check --deploy

# Probar email
python manage.py shell -c "from django.core.mail import send_mail; send_mail('Test', 'Test', 'from@example.com', ['to@example.com'], fail_silently=False)"

# Verificar conexión SSL
curl -I https://tu-dominio.com

# Verificar headers de seguridad
curl -I -X GET https://tu-dominio.com
```

## 📊 Mantenimiento

### Actualizaciones de Seguridad

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Actualizar dependencias Python
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Verificar vulnerabilidades
pip install safety
safety check
```

### Logs y Monitoreo

```bash
# Rotación de logs
sudo logrotate -f /etc/logrotate.conf

# Análisis de logs
sudo goaccess /var/log/nginx/access.log -o report.html

# Alertas de seguridad
# Configura fail2ban para enviar emails
```

## 📚 Referencias

- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [OWASP Django Security](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05.6-Testing_for_NoSQL_Injection)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [Nginx Security Headers](https://www.nginx.com/blog/http-security-headers/)

---

**Última actualización**: 2025-12-14
**Versión**: 1.0
**Autor**: Equipo de DevOps y Seguridad