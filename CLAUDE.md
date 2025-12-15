# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django 5.0.7 web application for employee attendance management (Sistema de Gestión de Asistencias) with PostgreSQL database. The system integrates with Frappe/ERPNext API for real-time attendance data and supports multiple work locations.

## Key Commands

### Development with Docker (Recommended)
```bash
# Start all services
docker compose up --build

# Run Django commands
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py collectstatic --noinput
docker compose exec web python manage.py test

# View logs
docker compose logs -f web
```

### Local Development (Without Docker)
```bash
cd src
python manage.py runserver
python manage.py migrate
python manage.py test
python manage.py collectstatic --noinput
```

### Security Validation
```bash
python scripts/validate_env.py
python manage.py check --tag security
python manage.py check --deploy
```

## Architecture Overview

### Django Apps Structure
- `asistencias/` - Project settings with environment-based configuration
- `core/` - Main application containing all business logic
  - Models use Spanish naming with `db_column` for database fields
  - Soft delete pattern implemented across entities
  - Integration with Frappe API via `api_client.py`

### Key Models
- **Empleado**: Employee data with soft delete support
- **Sucursal**: Work locations (Villas, 31pte, Nave, RioBlanco)
- **Horario**: Work schedules with entry/exit times
- **AsignacionHorario**: Employee schedule assignments
- **Asistencia**: Attendance records with API integration

### External Integration
The system fetches attendance data from Frappe/ERPNext API:
- Configuration in `core/config.py`
- API client in `core/api_client.py`
- Requires `ASIATECH_API_KEY` and `ASIATECH_API_SECRET` environment variables

### Business Rules
- Tardiness: 15-minute grace period
- Early departure: 15-minute tolerance
- Absence: 60-minute threshold for unjustified absence
- Special handling for midnight shifts

## Development Guidelines

### Code Conventions
- Use Spanish for variable names, comments, and user-facing strings
- Follow Django model naming: use `db_column` for Spanish field names
- Always specify `related_name` for foreign key relationships
- Use soft delete pattern (add `fecha_baja` and `motivo_baja` fields)

### Security Requirements
- All configuration via environment variables (see `.env.example`)
- Never commit secrets or credentials
- Use `@login_required` for protected views
- Validate all user input before processing
- CSRF protection enabled by default

### Database Patterns
- Use `get_object_or_404` for retrieving single objects
- Prefer `objects.filter()` over `objects.get()` when multiple results possible
- Use `select_related()` and `prefetch_related()` for query optimization
- Handle database connection errors in production

### Testing
- Write tests in `core/tests.py`
- Use Django's TestCase class
- Mock external API calls when testing
- Test both success and error scenarios

## Environment Configuration

Required environment variables:
```bash
# Database
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=asiatech
DB_HOST=db          # Use 'localhost' for local development
DB_PORT=5432        # Use 5433 for local development

# API Credentials
ASIATECH_API_KEY=your_api_key
ASIATECH_API_SECRET=your_api_secret

# Email SMTP
EMAIL_HOST=smtp.purelymail.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=asistencias@asiatech.com.mx
EMAIL_HOST_PASSWORD=your_email_password

# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com
```

## Deployment

Production deployment uses Docker Compose with:
- Nginx as reverse proxy
- Gunicorn as WSGI server
- PostgreSQL database
- Static files served by Nginx

Ensure all migrations are applied and static files are collected before deployment.