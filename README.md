# Sistema de Gestión de Asistencias

Sistema web desarrollado con Django para la gestión de asistencias de personal. Implementa medidas de seguridad robustas siguiendo las mejores prácticas de la industria.

## 🚀 Características

- Gestión completa de asistencias
- Panel de administración Django
- Sistema de autenticación seguro
- Configuración mediante variables de entorno
- Protección contra vulnerabilidades comunes (XSS, CSRF, Clickjacking)
- Soporte para HTTPS y cookies seguras
- Validación de configuración antes del inicio

## 📋 Requisitos

- Python 3.8+
- PostgreSQL 12+
- pip (gestor de paquetes Python)
- Virtualenv (recomendado)

## 🔧 Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/gestor_asistencias.git
cd gestor_asistencias
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar con tus configuraciones
nano .env  # Linux/Mac
# o
notepad .env  # Windows
```

### 5. Configurar base de datos
```bash
# Crear base de datos en PostgreSQL
createdb asistencias

# Aplicar migraciones
python manage.py migrate
```

### 6. Crear superusuario
```bash
python manage.py createsuperuser
```

### 7. Validar configuración
```bash
# Verificar que todo esté configurado correctamente
python scripts/validate_env.py
```

### 8. Ejecutar servidor de desarrollo
```bash
python manage.py runserver
```

## 🔐 Configuración de Seguridad

### Variables de entorno críticas:

```bash
# Django
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=False  # En producción
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com

# Base de datos
POSTGRES_DB=asistencias
POSTGRES_USER=postgres
POSTGRES_PASSWORD=contraseña-segura

# Email
EMAIL_HOST=smtp.purelymail.com
EMAIL_HOST_PASSWORD=contraseña-email
```

**⚠️ IMPORTANTE:** Nunca commitees el archivo `.env`. Ya está incluido en `.gitignore`.

### Generar SECRET_KEY segura:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Para más detalles sobre la configuración segura, consulta: [docs/security_setup.md](docs/security_setup.md)

## 🧪 Testing

```bash
# Ejecutar todas las pruebas
python manage.py test

# Pruebas específicas de seguridad
python manage.py check --tag security

# Validación de despliegue
python manage.py check --deploy
```

## 🐳 Docker

```bash
# Construir imagen
docker build -t gestor-asistencias .

# Ejecutar con docker-compose
docker-compose up -d
```

## 📚 Documentación Adicional

- [Análisis de Seguridad](docs/plan_seguridad_implementacion.md) - Plan completo de implementación de seguridad
- [Guía de Configuración Segura](docs/security_setup.md) - Configuración detallada para producción
- [Análisis del Código](docs/code_review_analysis.md) - Revisión de calidad del código

## 🔍 Verificación de Seguridad

El sistema incluye validaciones automáticas que verifican:
- ✅ SECRET_KEY no hardcodeado
- ✅ Variables de entorno configuradas
- ✅ ALLOWED_HOSTS sin wildcard en producción
- ✅ Headers de seguridad activos
- ✅ Cookies seguras en HTTPS

## 🚨 Soporte

Si encuentras problemas de seguridad:
1. Verifica la configuración con `python scripts/validate_env.py`
2. Consulta la guía de solución de problemas en [docs/security_setup.md](docs/security_setup.md)
3. Asegúrate de no tener credenciales hardcodeadas

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 👥 Autores

- Equipo de Desarrollo - Implementación inicial
- Equipo de Seguridad - Implementación de medidas de seguridad

---

**⚠️ Nota de Seguridad:** Este sistema implementa medidas de seguridad siguiendo las mejores prácticas de Django y OWASP. Siempre mantén tu instalación actualizada y revisa regularmente la configuración de seguridad.
